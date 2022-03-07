import requests
import re
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from urllib.parse import urlparse
from datetime import datetime
from peewee import *
from model import Website
from time import sleep


def logError(error, etype, message):
	with open('error_log.txt', 'a') as elog:
		elog.write('\n{} - {} - {}\n'.format(datetime.now(), etype, message))
		if error != '':
			elog.write(str(error) + '\n')
		elog.close()


def initDb():
	db = SqliteDatabase('websites.db', timeout=10)
	db.create_tables([Website], safe=True)
	db.connect()
	return db


def insertDb(domain, securityTxtUrl, email):
	website = Website.create(
		domain = domain,
		securityTxtUrl = securityTxtUrl,
		email = email
	)
	website.save()


def exists(domain):
	query = Website.select().where(Website.domain == domain)
	return query.exists()


def getUrls(pageLimit=1000, waitDuration=5):
	pageStart = 0
	links = []

	while True:
		try:
			googleUrl = 'https://www.google.com/search?q=filetype%3Atxt+inurl%3Awell-known%2Fsecurity.txt&start=' + str(pageStart)

			res = requests.get(googleUrl, timeout=30)

			if re.search(r'Your search - .+ - did not match any documents', res.text) != None:
				print('[+] End of search reached')
				break
			elif res.status_code >= 300:
				logError('', 'Google Search Scrape Error', 'Received status code {} ({})'.format(res.status_code, googleUrl))
				sleep(waitDuration)
				continue
			elif pageStart > pageLimit:
				break

			print('[+] Scraping ' + googleUrl)

			soup = BeautifulSoup(res.text, 'html.parser')

			for link in soup.find_all("a",href=re.compile("(?<=/url\\?q=)(htt.*://.*)")):
			    # links.append(re.split(":(?=http)",link["href"].replace("/url?q=",""))[0])
			    match = re.search(r'https://.+\.well-known/security\.txt', link['href'])
			    if match != None:
			    	links.append(match.group(0))

			pageStart = pageStart + 10
			sleep(waitDuration)

		except Exception as e:
			print('\n[-] Failed to scrape Google results, check error log.')
			logError(e, 'Google Search Scrape Error', 'Failed to scrape Google results ({})'.format(googleUrl))
			break

	if len(links) == 0:
		logError('', 'Google Search Scrape Error', 'Scrape produced no results')

	return links


def getEmailFromSecurityTxt(url):
	try:
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0'
		}
		res = requests.get(url, headers=headers, timeout=5)

		# replaced space after Contact: with nothing, see if this works
		match = re.search(r'Contact:.+@.+', res.text)

		if match != None:
			# email = match.group(0).split(' ')[1].replace('mailto:', '')
			email = match.group(0).strip().replace(' ', '').replace('\t', '').replace('mailto:', '')
			return email
		else:
			logError('', 'Email Extraction Error', 'No email contact in security.txt ({})'.format(url))
			return None

	except Exception as e:
		logError(e, 'Email Extraction Error', 'Connection error ({})'.format(url))
		return None


def sendEmail(to='saular.raffi@yahoo.com'):
	with open('email_body.txt', 'rb') as mail:
	    msg = MIMEText(mail.read())

	sender = 'saular.raffi@yahoo.com'

	msg['Subject'] = 'Bug Bounty Inquiry'
	msg['From'] = sender
	msg['To'] = to

	USERNAME = 'saular.raffi@yahoo.com'
	PASSWORD = 'ecawjjyuwmqfemro'

	try:
		# print('\n[+] Connecting to Yahoo server')
		conn = smtplib.SMTP_SSL('smtp.mail.yahoo.com', 465)

		# print("\n[+] Authenticating with email server")
		conn.login(USERNAME, PASSWORD)
		conn.sendmail(sender, [to], msg.as_string())

	except Exception as e:
		logError(e, 'Email Send Error', 'Failed to send email to ({})'.format(to))
		return False

	finally:
		return True



if __name__ == '__main__':

	with open('error_log.txt', 'w') as elog:
		elog.close()

	# font - rectangles
	banner = '''                                                                  
	 _____           _ _    _____     _                 _   _         
	|   __|_____ ___|_| |  |  _  |_ _| |_ ___ _____ ___| |_|_|___ ___ 
	|   __|     | .'| | |  |     | | |  _| . |     | .'|  _| | . |   |
	|_____|_|_|_|__,|_|_|  |__|__|___|_| |___|_|_|_|__,|_| |_|___|_|_|

	'''

	print(banner)                                                

	# Scraping URLs

	webWaitDuration = 5
	emailWaitDuration = 3
	googlePageSearchLimit = 1000

	db = initDb()
	links = getUrls(googlePageSearchLimit, webWaitDuration)
	websites = []

	print('\n[+] {} links found'.format(len(links)))

	# Scraping emails from website with a valid security.txt file

	print('\n[+] Emails scraped:')
	print('---------------------')

	emailsAdded = 0
	emailsFound = 0

	for link in links:
		print('  ' + email)
		domain = urlparse(link).netloc

		if exists(domain):
			continue

		email = getEmailFromSecurityTxt(link)

		if email != None:
			emailsFound = emailsFound + 1
			website = {
				'domain': domain,
				'securityTxtUrl': link,
				'email': email
			}
			websites.append(website)
			insertDb(domain, link, email)
			emailsAdded = emailsAdded + 1

		sleep(webWaitDuration)

	print('\n[+] {} Email(s) found, {} email(s) added to database'.format(emailsFound, emailsAdded))

	# Sending out emails

	if len(websites) == 0:
		print('\n\n[+] No emails to send out at this time\n')
	else:
		print('\n[+] Sending out emails...\n')

		for website in websites:
			# sent = sendEmail('saular.raffi@yahoo.com')
			sent = True
			if sent:
				print('[+] Successfully sent email to {}'.format(website['email']))
			else:
				print('[-] Failed to send email')

			sleep(emailWaitDuration)

		print('\n\n[+] Email automation task complete, hopefully they respond!\n')

	db.close()