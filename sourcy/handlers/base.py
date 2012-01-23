import sys


import tornado.web

from sourcy.models import UserAccount

class BaseHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.dbsession = None

    @property
    def session(self):
        if self.dbsession is None:
            self.dbsession = self.application.Session()
        return self.dbsession

    def get_current_user(self):
        user_id = self.get_secure_cookie("user")
        if user_id is None:
            return None
        return self.session.query(UserAccount).filter_by(id=user_id).first()



