import datetime
from collections import defaultdict
import itertools
import random
import urllib

import tornado.auth
from sqlalchemy import Date,not_
from sqlalchemy.sql.expression import cast,func
from sqlalchemy.orm import subqueryload,joinedload

from base import BaseHandler
from unsourced.models import Source,Article,Action,Lookup,Tag,TagKind,UserAccount,Comment,article_tags,comment_user_map
from unsourced.cache import cache
from unsourced.queries import build_action_query
from unsourced.paginator import SAPaginator
import util

def calc_top_sourcers(session, ndays=7, cache_expiration_time=60*5):
    """ returns list of (user, src_cnt) tuples """
    def _calc():

        src_cnts = session.query(Source.creator_id, func.count('*').label('cnt'))

        if ndays is not None:
            day_to = datetime.datetime.utcnow()
            day_from = day_to - datetime.timedelta(days=ndays)
            src_cnts = src_cnts.\
                filter(cast(Source.created, Date) >= day_from).\
                filter(cast(Source.created, Date) <= day_to)

        src_cnts = src_cnts.\
            group_by(Source.creator_id).\
            subquery()

        top_sourcers = session.query(UserAccount, src_cnts.c.cnt).\
            options(joinedload('photo')).\
            join(src_cnts, UserAccount.id==src_cnts.c.creator_id).\
            order_by(src_cnts.c.cnt.desc()).\
            limit(6).\
            all()

        return top_sourcers 

    if ndays is None:
        cachename = 'top_sourcers_alltime'
    else:
        cachename = 'top_sourcers_%d_days' % (ndays) 
    return cache.get_or_create(cachename, _calc, expiration_time=cache_expiration_time)



class DailyStats:
    """ helper class for wrangling summary stats for a single day """
    def __init__(self, day, total, sourced):
        self.day = day
        self.total = total
        self.sourced = sourced

    @property
    def unsourced(self):
        return self.total-self.sourced

    def percent_complete(self):
        if self.total>0:
            return int(float(100*self.sourced) / float(self.total))
        else:
            return 0

    def browse(self):
        """ return browse url for all articles on this day """
        return "/browse?date=range&dayfrom=%s&dayto=%s" % (self.day,self.day)

    def browse_unsourced(self):
        """ return browse url for all unsourced articles on this day """
        return "/browse?date=range&dayfrom=%s&dayto=%s&sourced=unsourced" % (self.day,self.day)

    def browse_sourced(self):
        """ return browse url for all sourced articles on this day """
        return "/browse?date=range&dayfrom=%s&dayto=%s&sourced=sourced" % (self.day,self.day)



def daily_breakdown(session, day_from=None, day_to=None):

    def _calc():
        stats = {}
        if day_from is not None and day_to is not None:
            # fill in gaps
            for day in util.daterange(day_from,day_to):
                stats[day] = dict(total=0,done=0,help=0)

        # TODO: do the work in the database.
        q = session.query(cast(Article.pubdate,Date), Article)

        if day_from is not None:
            q = q.filter(cast(Article.pubdate, Date) >= day_from)
        if day_to is not None:
            q = q.filter(cast(Article.pubdate, Date) <= day_to)

        for day,art in q:
            if day not in stats:
                stats[day] = dict(total=0,done=0,help=0)
            stats[day]['total'] += 1
            if not art.needs_sourcing:
                stats[day]['done'] += 1

        stats = sorted([(day,row) for day,row in stats.iteritems()], key=lambda x: x[0], reverse=True )

        return [DailyStats(x[0], x[1]['total'], x[1]['done']) for x in stats]

    k = "daily_breakdown_from_%s_to_%s" % (day_from, day_to)
    return cache.get_or_create(k, _calc, 60*1)





class DailyBreakdown(BaseHandler):
    def get(self):

        stats = daily_breakdown(self.session)
        max_arts = max(stats, key=lambda x: x.total).total
 
        self.render('daily.html', stats=stats, max_arts=max_arts)


class ExtensionHandler(BaseHandler):
    def get(self):
        self.render('front.html')



class FrontHandler(BaseHandler):
    def get(self):
        if self.current_user is None:
            self.render('front.html')
            return

        page = int(self.get_argument('p',1))
        view = self.get_argument('view','recent')

        top_sourcers_7days = calc_top_sourcers(self.session, ndays=7, cache_expiration_time=60*5)
        top_sourcers_alltime = calc_top_sourcers(self.session, ndays=None, cache_expiration_time=60*60*12)

        # daily breakdown for the week
        today = datetime.datetime.utcnow().date()
        stats = daily_breakdown(self.session, today-datetime.timedelta(days=6), today)
        max_arts = max(stats, key=lambda x: x.total).total


        # outstanding help requests
        helpreq_cnt = self.session.query(Article).\
            filter(Article.help_reqs.any()).\
            order_by(Article.pubdate.desc()).count()


        def page_url(page):
            """ generate url for the given page of this query"""
            params = {}
            # preserve all request params, and override page number
            for k in self.request.arguments:
                params[k] = self.get_argument(k)
            params['p'] = page
            url = "/?" + urllib.urlencode(params)
            return url

        interesting_cnt = build_action_query(self.session,'interesting',current_user=self.current_user).count()
        mentions_cnt = build_action_query(self.session,'mentions',current_user=self.current_user).count()

        actions = build_action_query(self.session,view,current_user=self.current_user)
        paged_actions = SAPaginator(actions, page, page_url, per_page=100)


        self.render('front_loggedin.html',
            filters = dict(),
            view=view,
            helpreq_cnt = helpreq_cnt,
            paged_actions = paged_actions,
            interesting_cnt = interesting_cnt,
            mentions_cnt = mentions_cnt,
            groupby = itertools.groupby,
            top_sourcers_7days = top_sourcers_7days,
            top_sourcers_alltime = top_sourcers_alltime,
            week_stats=stats,
            week_stats_max_arts=max_arts)




class AboutHandler(BaseHandler):
    def get(self):
        self.render('about.html')

class HelpHandler(BaseHandler):
    def get(self):


        doi_examples = [
            ("http://www.sciencedirect.com/science/article/pii/S1752928X08001728","/static/doi_1.png"),
            ("http://journals.lww.com/neuroreport/abstract/2009/08050/swearing_as_a_response_to_pain.4.aspx", "/static/doi_2.png"),
            ("http://aghist.metapress.com/content/q3224660874x8q51/", "/static/doi_3.png"),
        ]

        ex = random.choice(doi_examples)

        self.render('help.html', doi_example_img=ex[1], doi_example_url=ex[0])

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
            options(joinedload('article'),joinedload('user'),joinedload('comment')).\
            filter(Action.what=='cjjjjomment').\
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
    (r'/', FrontHandler),
    (r'/about', AboutHandler),
    (r'/help', HelpHandler),
    (r'/academicpapers', AcademicPapersHandler),
    (r"/addjournal", AddJournalHandler),
    (r"/addinstitution", AddInstitutionHandler),
    (r"/daily", DailyBreakdown),
    (r'/dashboard', DashboardHandler),
    (r'/extension', ExtensionHandler),
    ]

