import tornado.ioloop
import tornado.web
import tornado.options
from tornado import httpclient
from tornado.options import define, options
import tornado.auth
import os
import logging
import urllib
import json
import datetime

import analyser
import uimodules
from store import Store

from handlers.base import BaseHandler
from handlers.history import HistoryHandler
from handlers.user import UserHandler
from handlers.article import ArticleHandler
from handlers.addarticle import AddArticleHandler

define("port", default=8888, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', MainHandler),
            (r'/about', AboutHandler),
            (r'/academicpapers', AcademicPapersHandler),
            (r'/login', LoginHandler),
            (r'/login/google', GoogleLoginHandler),
            (r'/logout', LogoutHandler),
            (r"/user/([0-9]+)", UserHandler),
            (r"/art/([0-9]+)", ArticleHandler),
            (r"/([0-9]{4}-[0-9]{2}-[0-9]{2})", HistoryHandler),
            (r"/edit", EditHandler),
            (r"/addarticle", AddArticleHandler),
            (r"/addjournal", AddJournalHandler),
            (r"/addinstitution", AddInstitutionHandler),
        ]
        settings = dict(
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret = "SuperSecretKey(tm)",
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            ui_modules = uimodules,
            debug = True
            )
        tornado.web.Application.__init__(self, handlers, **settings)

        self.store = Store()


        self.institution_finder = analyser.Lookerupper(self.store,'institution')
        self.journal_finder = analyser.Lookerupper(self.store,'journal')




class LoginHandler(BaseHandler):
    def get(self):
        next = self.get_argument("next", None);
        self.render('login.html', next=next)



class GoogleLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()
    
    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")

        sourcy_user = self.store.user_get_by_email(user['email'])
        if sourcy_user is None:
            user_id = self.store.user_create(user['email'],user['name']);
        else:
            user_id = sourcy_user.id
        self.set_secure_cookie("user", unicode(user_id))
        self.redirect(self.get_argument("next", "/"))



class LogoutHandler(BaseHandler):

    def get(self):
        self.clear_cookie("user")
        self.redirect("/")







class MainHandler(BaseHandler):
    def get(self):

        days = []
        date = datetime.date.today()
        arts = self.store.art_get_by_date(date)
        days.append((date,arts))
#        date = date - datetime.timedelta(days=1)

        recent = self.store.action_get_recent(10)
        self.render('index.html', days=days, recent_actions=recent)




class AboutHandler(BaseHandler):
    def get(self):
        self.render('about.html')

class AcademicPapersHandler(BaseHandler):
    def get(self):
        self.render('academicpapers.html')




class EditHandler(BaseHandler):
    def post(self):
        url = self.get_argument('url')
        art_id = int(self.get_argument('art_id'))
        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None
        self.store.action_add_source(user_id, art_id, url)

        self.redirect("/art/%d" % (art_id,))


class AddInstitutionHandler(BaseHandler):
    kind = 'institution'

    def get(self):
        self.render('addlookup.html',kind=self.kind)

    def post(self):
        name = self.get_argument('name')
        homepage = self.get_argument('homepage')

        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None
        self.store.action_add_lookup(user_id, self.kind, name, homepage)
        self.redirect(self.request.path)


class AddJournalHandler(BaseHandler):
    kind = 'journal'

    def get(self):
        self.render('addlookup.html',kind=self.kind)

    def post(self):
        name = self.get_argument('name')
        homepage = self.get_argument('homepage')

        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None

        self.store.action_add_lookup(user_id, self.kind, name, homepage)
        self.redirect(self.request.path)

def main():
    tornado.options.parse_config_file("sourcy.conf")
    tornado.options.parse_command_line()
    app = Application()
    app.listen(8888)
    logging.info("start.")
    tornado.ioloop.IOLoop.instance().start()


