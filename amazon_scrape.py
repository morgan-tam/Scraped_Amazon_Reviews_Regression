from lxml import html  
import csv,os,json, re
import requests
from exceptions import ValueError
from dateutil import parser as dateparser
from time import sleep
from collections import OrderedDict
from bs4 import BeautifulSoup

def AmzonParser(ASIN):
	# Added Retrying 
	for i in range(5):
		try:
			#This script has only been tested with Amazon.com
			amazon_url  = 'http://www.amazon.com/dp/'+ASIN
			# Add some recent user agent to prevent amazon from blocking the request 
			# Find some chrome user agent strings  here https://udger.com/resources/ua-list/browser-detail?browser=Chrome
			headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'}
			page = requests.get(amazon_url, headers = headers) #Enter proxies and user agent in headers
			page_response = page.text

			parser = html.fromstring(page_response)
			XPATH_AGGREGATE = '//span[@id="acrCustomerReviewText"]'
			XPATH_REVIEW_SECTION_1 = '//div[contains(@id,"reviews-summary")]'
			XPATH_REVIEW_SECTION_2 = '//div[@data-hook="review"]'
			XPATH_AGGREGATE_RATING = '//table[@id="histogramTable"]//tr'
			XPATH_PRODUCT_NAME = '//h1//span[@id="productTitle"]//text()'
			XPATH_SALE_PRICE = '//span[contains(@id,"ourprice") or contains(@id,"saleprice")]/text()'
			XPATH_ORIGINAL_PRICE = '//td[contains(text(),"List Price") or contains(text(),"M.R.P") or contains(text(),"Price")]/following-sibling::td/text()'
			XPATH_CATEGORY = '//a[@class="a-link-normal a-color-tertiary"]//text()'
			XPATH_AVAILABILITY = '//div[@id="availability"]//text()'
			XPATH_REVIEW_COUNT =  '//span[@data-hook="total-review-count"]//text()'
			XPATH_GROSS_RATING = '//span[@data-hook="rating-out-of-text"]//text()'
			XPATH_ANSWERS = '//a[@id="askATFLink"]/span//text()'

			#Product details table
			soup = BeautifulSoup(page.content,'lxml')
			prod = {}
			tables = soup.find_all('table', attrs={'class':'a-keyvalue prodDetTable'})
			tables = soup.find_all('table', attrs={'class':'a-keyvalue prodDetTable'})
			for rows in tables:
			    for row in rows.find_all('tr'):
					key = row.find('th').get_text().strip()
					if (key not in ['International Shipping', 'Domestic Shipping', 'Customer Reviews']):
						value = row.find('td').get_text().strip()
						prod[key] = value

			raw_sales_price = parser.xpath(XPATH_SALE_PRICE)
			sales_price = ' '.join(''.join(raw_sales_price).split()).strip() if raw_sales_price else None
			raw_original_price = parser.xpath(XPATH_ORIGINAL_PRICE)
			original_price = ''.join(raw_original_price).strip() if raw_original_price else None
			raw_category = parser.xpath(XPATH_CATEGORY)
			category = ' > '.join([i.strip() for i in raw_category]) if raw_category else None
			raw_availability = parser.xpath(XPATH_AVAILABILITY)
			availability = ''.join(raw_availability).strip()
			raw_product_name = parser.xpath(XPATH_PRODUCT_NAME)
			product_name = ''.join(raw_product_name).strip()
			raw_review_count = parser.xpath(XPATH_REVIEW_COUNT)
			review_count = ''.join(raw_review_count).strip()
			raw_gross_rating = parser.xpath(XPATH_GROSS_RATING)
			gross_rating = ''.join(raw_gross_rating).strip()
			raw_answers = parser.xpath(XPATH_ANSWERS)
			answers = ''.join(raw_answers).strip()

			total_ratings  = parser.xpath(XPATH_AGGREGATE_RATING)

			reviews = parser.xpath(XPATH_REVIEW_SECTION_1)
			if not reviews:
				reviews = parser.xpath(XPATH_REVIEW_SECTION_2)

			ratings_dict = {}
			reviews_list = []
			
			if not reviews:
				raise ValueError('unable to find reviews in page')

			#grabing the rating  section in product page
			for ratings in total_ratings:
				extracted_rating = ratings.xpath('./td//a//text()')
				if extracted_rating:
					rating_key = extracted_rating[0] 
					raw_raing_value = extracted_rating[1]
					rating_value = raw_raing_value
					if rating_key:
						ratings_dict.update({rating_key:rating_value})

			#Parsing individual reviews
			for review in reviews:
				XPATH_TOTAL_RATING = '//span[@data-hook="total-review-count"]//text()'
				XPATH_RATING  = './/i[@data-hook="review-star-rating"]//text()'
				XPATH_REVIEW_HEADER = './/a[@data-hook="review-title"]//text()'
				XPATH_REVIEW_POSTED_DATE = './/a[contains(@href,"/profile/")]/parent::span/following-sibling::span/text()'
				XPATH_REVIEW_TEXT_1 = './/div[@data-hook="review-collapsed"]//text()'
				XPATH_REVIEW_TEXT_2 = './/div//span[@data-action="columnbalancing-showfullreview"]/@data-columnbalancing-showfullreview'
				XPATH_REVIEW_COMMENTS = './/span[@data-hook="review-comment"]//text()'
				XPATH_AUTHOR  = './/a[contains(@href,"/profile/")]/parent::span//text()'
				XPATH_REVIEW_TEXT_3  = './/div[contains(@id,"dpReviews")]/div/text()'
				raw_review_author = review.xpath(XPATH_AUTHOR)
				raw_review_rating = review.xpath(XPATH_RATING)
				raw_review_header = review.xpath(XPATH_REVIEW_HEADER)
				raw_review_posted_date = review.xpath(XPATH_REVIEW_POSTED_DATE)
				raw_review_text1 = review.xpath(XPATH_REVIEW_TEXT_1)
				raw_review_text2 = review.xpath(XPATH_REVIEW_TEXT_2)
				raw_review_text3 = review.xpath(XPATH_REVIEW_TEXT_3)

				author = ' '.join(' '.join(raw_review_author).split()).strip('By')

				#cleaning data
				review_rating = ''.join(raw_review_rating).replace('out of 5 stars','')
				review_header = ' '.join(' '.join(raw_review_header).split())
				review_posted_date = dateparser.parse(''.join(raw_review_posted_date)).strftime('%d %b %Y')
				review_text = ' '.join(' '.join(raw_review_text1).split())

				#grabbing hidden comments if present
				if raw_review_text2:
					json_loaded_review_data = json.loads(raw_review_text2[0])
					json_loaded_review_data_text = json_loaded_review_data['rest']
					cleaned_json_loaded_review_data_text = re.sub('<.*?>','',json_loaded_review_data_text)
					full_review_text = review_text+cleaned_json_loaded_review_data_text
				else:
					full_review_text = review_text
				if not raw_review_text1:
					full_review_text = ' '.join(' '.join(raw_review_text3).split())

				raw_review_comments = review.xpath(XPATH_REVIEW_COMMENTS)
				review_comments = ''.join(raw_review_comments)
				review_comments = re.sub('[A-Za-z]','',review_comments).strip()
				review_dict = {
									'review_comment_count':review_comments,
									'review_text':full_review_text,
									'review_posted_date':review_posted_date,
									'review_header':review_header,
									'review_rating':review_rating,
									'review_author':author

								}
				reviews_list.append(review_dict)

			data = OrderedDict()
			data['name'] = product_name
			data['sales_price'] = sales_price
			data['original_price'] = original_price
			data['category'] = category
			data['availability'] = availability
			data['total_ratings'] = gross_rating
			data['customer_reviews'] = review_count
			data['#_of_answers'] = answers
			data['Product_Details'] = prod
			data['ratings'] = ratings_dict
			data['reviews'] = reviews_list
			data['url'] = amazon_url		

			return data

		except ValueError:
			print "Retrying to get the correct response"
	
	return {"error":"failed to process the page","asin":asin}



def ReadASIN():
	# AsinList = csv.DictReader(open(os.path.join(os.path.dirname(__file__),"Asinfeed.csv")))
    ASINList = ['B06Y15DWXR']
    extracted_data = []

    for ASIN in ASINList:
		print "Downloading and processing page http://www.amazon.com/dp/" + ASIN
		extracted_data.append(AmzonParser(ASIN))
		sleep(10)

    f = open('data.json','w')
    json.dump(extracted_data,f,indent=4)


if __name__ == "__main__":
    ReadASIN()



