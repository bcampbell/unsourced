import datetime
from pprint import pprint
from collections import defaultdict
import itertools
import random

import tornado.auth
from sqlalchemy import Date,not_
from sqlalchemy.sql.expression import cast,func
from sqlalchemy.orm import subqueryload

from base import BaseHandler
from sourcy.models import Article,Action,Lookup,Tag,TagKind,UserAccount,Comment,article_tags

class DashboardHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):

        #TODO: top sourcers
        all_users = self.session.query(UserAccount).all()
        top_sourcers = [random.choice(all_users) for i in range(12)]


#        today_summary = DailySummary(self.session, datetime.datetime.utcnow().date())


        # logged-in "dashboard" version of front page
        today = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)

        unsourced_arts = self.session.query(Article).\
            filter(cast(Article.pubdate, Date) >= today).\
            filter(Article.needs_sourcing == True).\
            all()

        helpreq_arts = self.session.query(Article).\
            filter(Article.help_reqs.any()).\
            order_by(Article.pubdate.desc())


        recent_actions = self.session.query(Action).\
            filter(Action.what.in_(('src_add','art_add','mark_sourced','mark_unsourced','helpreq_open','helpreq_close'))).\
            order_by(Action.performed.desc()).slice(0,6)


        self.render('dashboard.html',
            unsourced_arts = unsourced_arts,
            helpreq_arts = helpreq_arts,
            top_sourcers = top_sourcers,
            today_summary = today_summary,
            recent_actions = recent_actions)



handlers = [
    (r'/dashboard', DashboardHandler),
    ]

