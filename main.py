import cgi
import os
import urllib
import logging
import pickle
import webapp2

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.api import memcache

# Set the debug level
_DEBUG = True

class GreetingUser(db.Model):
  greeting_user = db.UserProperty()
  joined = db.DateTimeProperty(auto_now_add=True)
  picture = db.StringProperty()
  seated = db.StringProperty()
  website = db.StringProperty()
  
class Greeting(db.Model):
  author = db.UserProperty()
  content = db.StringProperty(multiline=True)
  date = db.DateTimeProperty(auto_now_add=True)

class BaseRequestHandler(webapp.RequestHandler):
  """Base request handler extends webapp.Request handler

     It defines the generate method, which renders a Django template
     in response to a web request
  """

  def generate(self, template_name, template_values={}):
    """Generate takes renders and HTML template along with values
       passed to that template

       Args:
         template_name: A string that represents the name of the HTML template
         template_values: A dictionary that associates objects with a string
           assigned to that object to call in the HTML template.  The defualt
           is an empty dictionary.
    """
    # We check if there is a current user and generate a login or logout URL
    user = users.get_current_user()

    if user:
      log_in_out_url = users.create_logout_url('/')
    else:
      log_in_out_url = users.create_login_url(self.request.path)

    # We'll display the user name if available and the URL on all pages
    values = {'user': user, 'log_in_out_url': log_in_out_url}
    values.update(template_values)

    # Construct the path to the template
    directory = os.path.dirname(__file__)
    path = os.path.join(directory, 'templates', template_name)

    # Respond to the request by rendering the template
    return template.render(path, values, debug=_DEBUG)
    
class MainRequestHandler(BaseRequestHandler):
  def get(self):
    if users.get_current_user():
      url = users.create_logout_url(self.request.uri)
      url_linktext = 'Logout'
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'

    template_values = {
      'url': url,
      'url_linktext': url_linktext,
      }

    self.response.out.write(self.generate('index.html', template_values));
    
class MainRequestHandlerGoogle(BaseRequestHandler):
  def get(self):
    if users.get_current_user():
      url = users.create_logout_url(self.request.uri)
      url_linktext = 'Logout'
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'

    template_values = {
      'url': url,
      'url_linktext': url_linktext,
      }

    self.response.out.write(self.generate('googleed33af2b819fc228.html', template_values));

class ChatsRequestHandler(BaseRequestHandler):
  MEMCACHE_KEY = 'greetings'
  MEMCACHE_TEMPLATE = 'greetings_template'
  
  def get(self):
    template = memcache.get(self.MEMCACHE_TEMPLATE)
    self.response.out.write(template)
    
  def post(self):
    greeting = Greeting()

    if users.get_current_user():
      greeting.author = users.get_current_user()
    
    greeting.content = self.request.get('content')
    greeting.put()
    
    greetingsString = memcache.get(self.MEMCACHE_KEY)
    if greetingsString is None:
      greetingsList = []
    else:
      greetingsList = pickle.loads(greetingsString)
      if len(greetingsList) >= 40:
        greetingsList.pop(0)
    greetingsList.append(greeting)
    
    if not memcache.set(self.MEMCACHE_KEY, pickle.dumps(greetingsList)):
        logging.debug("Memcache set failed:")  

    template_values = {
      'greetings': greetingsList,
    }
    template = self.generate('chats.html', template_values)
    if not memcache.set(self.MEMCACHE_TEMPLATE, template):
        logging.debug("Memcache set failed:")          
    
    self.response.out.write(template)

    
class EditUserProfileHandler(BaseRequestHandler):
  """This allows a user to edit his or her wiki profile.  The user can upload
     a picture and set a feed URL for personal data
  """
  def get(self, user):
    # Get the user information
    unescaped_user = urllib.unquote(user)
    greeting_user_object = users.User(unescaped_user)
    # Only that user can edit his or her profile
    if users.get_current_user() != greeting_user_object:
      self.redirect('/view/StartPage')

    greeting_user = GreetingUser.gql('WHERE greeting_user = :1', greeting_user_object).get()
    if not greeting_user:
      greeting_user = GreetingUser(greeting_user=greeting_user_object)
      greeting_user.put()

    self.response.out.write(self.generate('edit_user.html', template_values={'queried_user': greeting_user}))

  def post(self, user):
    # Get the user information
    unescaped_user = urllib.unquote(user)
    greeting_user_object = users.User(unescaped_user)
    # Only that user can edit his or her profile
    if users.get_current_user() != greeting_user_object:
      self.redirect('/')

    greeting_user = GreetingUser.gql('WHERE greeting_user = :1', greeting_user_object).get()

    greeting_user.picture = self.request.get('user_picture')
    greeting_user.website = self.request.get('user_website')
    greeting_user.seated = self.request.get('user_seated')
    greeting_user.put()


    self.redirect('/user/%s' % user)
    
class UserProfileHandler(BaseRequestHandler):
  """Allows a user to view another user's profile.  All users are able to
     view this information by requesting http://wikiapp.appspot.com/user/*
  """

  def get(self, user):
    """When requesting the URL, we find out that user's WikiUser information.
       We also retrieve articles written by the user
    """
    # Webob over quotes the request URI, so we have to unquote twice
    unescaped_user = urllib.unquote(urllib.unquote(user))

    # Query for the user information
    greeting_user_object = users.User(unescaped_user)
    greeting_user = GreetingUser.gql('WHERE greeting_user = :1', greeting_user_object).get()

    # Generate the user profile
    self.response.out.write(self.generate('user.html', template_values={'queried_user': greeting_user}))

                                                
app = webapp2.WSGIApplication([('/', MainRequestHandler), ('/googleed33af2b819fc228.html', MainRequestHandlerGoogle)], debug=True)

def main():
  run_wsgi_app(app)

if __name__ == "__main__":
  main()