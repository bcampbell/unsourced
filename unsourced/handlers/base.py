import sys
import urllib
import logging
import datetime

SQLTAP=False    # cheesy hack for dumping per-request queries
if SQLTAP:
    import sqltap

import tornado.web

from unsourced.models import UserAccount

class BaseHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.dbsession = None


    def on_finish(self):
        # NOTE: if client closes connection, it's possible on_finish() won't trigger.
        # see https://github.com/facebook/tornado/issues/473
        if self.dbsession is not None:
            self.dbsession.close()
            if SQLTAP:
                statistics = sqltap.collect()
                print len(statistics)," queries"
                sqltap.report(statistics, "/tmp/report.html")


    @property
    def session(self):
        if self.dbsession is None:
            self.dbsession = self.application.Session()
            if SQLTAP:   
                sqltap.start(self.application.engine)
        return self.dbsession

    def get_current_user(self):
        user_id = self.get_secure_cookie("user")
        if user_id is None:
            return None
        user = self.session.query(UserAccount).filter_by(id=user_id).first()

        # periodically update the users last_seen field
        now = datetime.datetime.utcnow()
        if user.last_seen is None or user.last_seen < now-datetime.timedelta(hours=1):
            user.last_seen = now
            self.session.commit()

        return user

    def is_xhr(self):
        """check if request AJAX"""
        return self.request.headers.get('X-requested-with', '').lower() == 'xmlhttprequest'

    def write_error(self, status_code, **kwargs):
        self.render("error.html", status_code=status_code)

    def get_login_url(self):
        if self.request.uri == '/':
            return '/login'
        else:
            return '/login?' + urllib.urlencode(dict(next=self.request.uri))


class MissingHandler(BaseHandler):
    """catch-all handler to generate 404s"""
    def prepare(self):
        super(MissingHandler, self).prepare()
        raise tornado.web.HTTPError(404, "Page not found")

