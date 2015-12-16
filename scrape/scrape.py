import urlparse
import re
from google.appengine.ext import db
from google.appengine.api import urlfetch
from bs4 import BeautifulSoup
import webapp2
import jinja2
import os
import logging
from operator import itemgetter, attrgetter

JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + "/templates"),
	extensions=['jinja2.ext.autoescape'])

class Module(db.Model):
	module_name = db.StringProperty()
	
class Bid_Info(db.Model):
	module = db.ReferenceProperty(Module)
	group = db.StringProperty()
	quota = db.IntegerProperty()
	no_of_bidders = db.IntegerProperty()
	lowest_bid = db.IntegerProperty()
	lowest_succ_bid = db.IntegerProperty()
	highest_bid = db.IntegerProperty()
	faculty = db.StringProperty()
	student_type = db.StringProperty()
	round = db.StringProperty()
	year = db.IntegerProperty()
	semester = db.IntegerProperty()


class MainPage(webapp2.RequestHandler):

	def get(self):	
		template_values = {
			'bidArray' : []
		}
			   
		template = JINJA_ENVIRONMENT.get_template('index2.html')
		self.response.write(template.render(template_values))
		
class Crawler(webapp2.RequestHandler):
	
	def get(self):
		url = "http://www.nus.edu.sg/cors/archive.html"
		
		#To read url
		htmltext = (urlfetch.fetch(url, deadline=60)).content

		soup = BeautifulSoup(htmltext)
	
		rnd = ''
		
		#To store the regular expression of a module into code_regex
		code_regex = re.compile(r"\b[a-zA-Z]{2,3}[0-9]{4,4}[a-zA-Z]?\b", re.IGNORECASE)
		module = None
		
		#Loop to extract all relevant websites for the datastore
		for tag in soup.find_all(href=re.compile("Archive/201213_Sem1/successbid_1A_20122013s1.html")):
			tag = tag.get('href')
			
			#Some href tags do not have the full url but rather replaced with a . in the beginning
			if tag.startswith('.'):
				tag = 'http://www.nus.edu.sg/cors' + tag[1:]
			
			#To extract the year and the sem from the url
			index = tag.find("2")
			yr = int(tag[index:index+6])
			sem = int(tag[index+10:index+11])
			rnd = tag[index+23:index+25]
			
			logging.info("Loading page %s" % tag)
			
			text = (urlfetch.fetch(tag, deadline=60)).content
			text = text.replace("<br>", "")
			asoup = BeautifulSoup(text)
			
			bidInfo = None
			
			counter = 1
			
			excludeUrls = ["avg", "averagepoints", "200304", "200405"]
			
			#For each string in the url, find the data and store it into the datastore
			for string in asoup.stripped_strings:
				if any(exclude in tag for exclude in excludeUrls):
					logging.info("Breaking!")
					break
				elif code_regex.search(string) is not None:
					module = Module.all().filter('module_name =', string).get()
					if module is None:
						logging.info("Inserting new module %s" %string)
						module = Module(module_name = string)
						module.put()
					bidInfo = Bid_Info(round = rnd, year = yr, semester = sem, module = module)
					logging.info("Reading module %s" % string)
					counter = 2
					
				elif counter==2:
					bidInfo.group = string
					grp = string
					counter += 1
				
				elif counter==3:
					bidInfo.quota = int(string)
					counter += 1
				
				elif counter==4:
					bidInfo.no_of_bidders = int(string)
					counter += 1
				
				elif counter==5:
					bidInfo.lowest_bid = int(string)
					counter += 1
					
				elif counter==6:
					bidInfo.lowest_succ_bid = int(string)
					counter += 1
				
				elif counter==7:
					bidInfo.highest_bid = int(string)
					counter += 1
					
				elif counter==8:
					bidInfo.faculty = string
					counter += 1
				
				elif counter==9:
					bidInfo.student_type = string
					counter += 1
					bidInfo.put()
					
				elif counter==10:
					bidInfo = Bid_Info(round = rnd, year = yr, semester = sem, module = module, group = grp)
					bidInfo.quota = int(string)
					counter = 4
			
class CorsAdvisor(webapp2.RequestHandler):

	def post(self):
		mod = self.request.get('mod')
		mod = mod.upper()
	   
		if len(mod) <1:
			self.redirect("/error")
			
		fac = self.request.get('fac')
		round = self.request.get('round')
		sem = self.request.get('sem')
		
		module = Module.all().filter('module_name =', mod).get()
		logging.info("Faculty = %s" % fac)
		if fac == 'ALL FACULTIES':
			if sem == '1':
				bid_info_query = Bid_Info.all().filter('module =', module).filter('round =', round).filter('semester =', 1)
			elif sem == '2':
				bid_info_query = Bid_Info.all().filter('module =', module).filter('round =', round).filter('semester =', 2)
		else:
			if sem == '1':
				bid_info_query = Bid_Info.all().filter('module =', module).filter('round =', round).filter('faculty =', fac).filter('semester =', 1)
			elif sem == '2':
				bid_info_query = Bid_Info.all().filter('module =', module).filter('round =', round).filter('faculty =', fac).filter('semester =', 2)
		bidArray = bid_info_query.fetch(limit=None)
		bidArray = sorted(bidArray, key=attrgetter('year', 'semester', 'faculty', 'student_type'), reverse=True)
		
		totalPts = 0
		totalQta = 0
		for bidInf in bidArray:
			totalPts = totalPts + bidInf.lowest_succ_bid*bidInf.quota
			totalQta = totalQta + bidInf.quota
		logging.info("Total quota = %s" % totalQta)
		if totalQta != 0:
			avg = totalPts/totalQta
		else:
			avg = -1
			
		template_values = {
			'module' : module,
			'bidArray' : bidArray,
			'avg' : avg,
			'fac' : fac,
			'round' : round,
			'sem' : sem
		}
		 
		template = JINJA_ENVIRONMENT.get_template('index.html')
		self.response.write(template.render(template_values))
		
class Error(webapp2.RequestHandler):

	def get(self):

		template = JINJA_ENVIRONMENT.get_template('index3.html')
		self.response.write(template.render(""))
		
		
application = webapp2.WSGIApplication([
	('/', MainPage),
	('/sign', CorsAdvisor),
	('/crawl', Crawler),
	('/error', Error),
], debug=True)
		
#		 module_code = read module code
#		 try get datastore by module code
#		 if dont exist then make new module
#		 and insert
#		 
#		 take out all columns
#		 insert into new BiddingInfo object
#		 insert object into datastore
		
		
#		 print string