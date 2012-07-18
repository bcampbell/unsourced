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
from unsourced.models import Article,Action,Lookup,Tag,TagKind,UserAccount,Comment,article_tags,comment_user_map



class DashboardHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):

        today = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)

        unsourced_arts = self.session.query(Article).\
            filter(cast(Article.pubdate, Date) >= today).\
            filter(Article.needs_sourcing == True).\
            order_by(Article.pubdate.desc()).\
            all()

        helpreq_arts = self.session.query(Article).\
            filter(Article.help_reqs.any()).\
            order_by(Article.pubdate.desc()).\
            limit(5)



        # find actions performed by other people on articles this user has touched
        arts_of_interest = self.session.query(Action.article_id).\
            distinct().\
            filter(Action.article_id != None).\
            filter(Action.user==self.current_user)

        actions_of_interest = self.session.query(Action).\
            filter(Action.article_id.in_(arts_of_interest)).\
            filter(Action.user!=self.current_user).\
            order_by(Action.performed.desc()).\
            limit(10)


#            filter(Action.what.in_(('src_add','art_add','mark_sourced','mark_unsourced','helpreq_open','helpreq_close'))).\
#           order_by(Action.performed.desc()).slice(0,6)

        subq = self.session.query(comment_user_map.c.comment_id).\
            filter(comment_user_map.c.useraccount_id==self.current_user.id).\
            subquery()
        recent_mentions = self.session.query(Action).\
            options(subqueryload(Action.comment,Action.article,Action.user)).\
            filter(Action.what=='comment').\
            filter(Action.comment_id.in_(subq)).\
            order_by(Action.performed.desc()).\
            slice(0,10).\
            all()


        self.render('dashboard.html',
            unsourced_arts = unsourced_arts,
            helpreq_arts = helpreq_arts,
            actions_of_interest = actions_of_interest,
            recent_mentions = recent_mentions)
        




handlers = [
    (r'/dashboard', DashboardHandler),
    ]

