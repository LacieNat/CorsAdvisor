#!/usr/bin/env python
import webapp2
#import jinja2

#jinja_environment = jinja2.Environment(
	#loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + "/templates"))

##### Page Handlers #####
class MainHandler(webapp2.RequestHandler):
	def get(self):
		self.redirect("/app/index.html")
		#template = jinja_environment.get_template("index.html")
		#self.response.out.write(template.render())
		pass

app = webapp2.WSGIApplication([
	("/", MainHandler),
], debug=True)