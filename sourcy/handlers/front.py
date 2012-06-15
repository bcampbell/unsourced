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


def daily_breakdown(session):
    stats = {}

    helptag = session.query(Tag).filter(Tag.name=='help').one()
    q = session.query(cast(Article.pubdate,Date), Article).\
        options(subqueryload(Article.tags))

    for day,art in q:
        if day not in stats:
            foo = dict(total=0,done=0,help=0)
        else:
            foo = stats[day]
        foo['total'] += 1
        if not art.needs_sourcing:
            foo['done'] += 1
        if helptag in art.tags:
            foo['help'] += 1
        stats[day]=foo

    stats = sorted([(day,row) for day,row in stats.iteritems()], key=lambda x: x[0], reverse=True )


    for x in stats:
        perc = 0.0
        if x[1]['total'] > 0:
            perc = 100.0 * float(x[1]['done']) / float(x[1]['total'])
        x[1]['percent'] = int(perc)

    return stats


class DailyBreakdown(BaseHandler):
    def get(self):

        stats = daily_breakdown(self.session)
       
        self.render('daily.html', stats=stats)



class DailySummary(object):
    """ helper for X% percent complete by day """
    def __init__(self, session, day):
        self.day = day
        self.total = session.query(Article).\
            filter(cast(Article.pubdate, Date) == day).\
            count()

        self.sourced = session.query(Article).\
            filter(cast(Article.pubdate, Date) == day).\
            filter(Article.needs_sourcing==False).\
            count()

        if self.total>0:
            self.percent_sourced = (100*self.sourced) / self.total
        else:
            self.percent_sourced = 0





class FrontHandler(BaseHandler):
    def get(self):



        #TODO: top sourcers
        all_users = self.session.query(UserAccount).all()
        top_sourcers = [random.choice(all_users) for i in range(12)]


        today_summary = DailySummary(self.session, datetime.datetime.utcnow().date())


        if self.current_user:
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


            self.render('front_loggedin.html',
                unsourced_arts = unsourced_arts,
                helpreq_arts = helpreq_arts,
                top_sourcers = top_sourcers,
                today_summary = today_summary,
                recent_actions = recent_actions)


        else:
            recent_actions = self.session.query(Action).\
                filter(Action.what.in_(('src_add','art_add','mark_sourced','mark_unsourced','helpreq_open','helpreq_close'))).\
                order_by(Action.performed.desc()).slice(0,6)

            # some articles which need sourcing
            random_arts = self.session.query(Article).\
                options(subqueryload(Article.tags,Article.sources,Article.comments)).\
                filter(Article.needs_sourcing==True).\
                order_by(func.rand()).\
                limit(4).all()

            self.render('front.html',
                random_arts = random_arts,
                recent_actions = recent_actions,
                groupby = itertools.groupby,
                top_sourcers = top_sourcers,
                today_summary = today_summary)







class AboutHandler(BaseHandler):
    def get(self):
        self.render('about.html')

class AcademicPapersHandler(BaseHandler):
    def get(self):
        self.render('academicpapers.html')



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

        lookup = Lookup(self.kind, name, homepage)
        action = Action('lookup_add', self.current_user, lookup=lookup)
        self.session.add(lookup)
        self.session.add(action)
        self.session.commit()
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

        lookup = Lookup(self.kind, name, homepage)
        action = Action('lookup_add', self.current_user, lookup=lookup)
        self.session.add(lookup)
        self.session.add(action)
        self.session.commit()
        self.redirect(self.request.path)


def top_n(session, day_from, day_to, action_kinds=['src_add',], num_results=5):
    """ helper for league tables """
    cnts = session.query(Action.user_id, func.count('*').label('cnt')).\
            filter(Action.what.in_(action_kinds)).\
            filter(cast(Action.performed, Date) >= day_from).\
            filter(cast(Action.performed, Date) <= day_to).\
            group_by(Action.user_id).\
            subquery()

    return session.query(UserAccount, cnts.c.cnt).\
        join(cnts, UserAccount.id==cnts.c.user_id).\
        order_by(cnts.c.cnt.desc()).\
        limit(num_results).\
        all()




class LeagueTablesHandler(BaseHandler):

    def get(self):
        today= datetime.date.today()
    
        kinds = ('src_add',)
        top5_sourcers_today = top_n(self.session,today,today,kinds,5)
        top5_sourcers_7day = top_n(self.session,today-datetime.timedelta(days=7),today,kinds,5)
        top5_sourcers_30day = top_n(self.session,today-datetime.timedelta(days=30),today,kinds,5)

        kinds = ('tag_add',)
        top5_taggers_today = top_n(self.session,today,today,kinds,5)
        top5_taggers_7day = top_n(self.session,today-datetime.timedelta(days=7),today,kinds,5)
        top5_taggers_30day = top_n(self.session,today-datetime.timedelta(days=30),today,kinds,5)

        kinds = ('src_vote','tag_vote')
        top5_voters_today = top_n(self.session,today,today,kinds,5)
        top5_voters_7day = top_n(self.session,today-datetime.timedelta(days=7),today,kinds,5)
        top5_voters_30day = top_n(self.session,today-datetime.timedelta(days=30),today,kinds,5)

        self.render('leaguetables.html',
            top5_sourcers_today=top5_sourcers_today,
            top5_sourcers_7day=top5_sourcers_7day,
            top5_sourcers_30day=top5_sourcers_30day,
            top5_taggers_today=top5_taggers_today,
            top5_taggers_7day=top5_taggers_7day,
            top5_taggers_30day=top5_taggers_30day,
            top5_voters_today=top5_voters_today,
            top5_voters_7day=top5_voters_7day,
            top5_voters_30day=top5_voters_30day,
            )


handlers = [
    (r'/', FrontHandler),
    (r'/about', AboutHandler),
    (r'/academicpapers', AcademicPapersHandler),
    (r"/addjournal", AddJournalHandler),
    (r"/addinstitution", AddInstitutionHandler),
    (r"/leaguetables", LeagueTablesHandler),
    (r"/daily", DailyBreakdown),
    ]
