import datetime
from collections import defaultdict
import itertools
import random

import tornado.auth
from sqlalchemy import Date,not_
from sqlalchemy.sql.expression import cast,func
from sqlalchemy.orm import subqueryload,joinedload

from base import BaseHandler
from unsourced.models import Source,Article,Action,Lookup,Tag,TagKind,UserAccount,Comment,article_tags
from unsourced.cache import cache


def calc_top_sourcers(session):
    """ returns list of (user, src_cnt) tuples """
    def _calc():
        day_to = datetime.datetime.utcnow()
        day_from = day_to - datetime.timedelta(days=30)


        src_cnts = session.query(Source.creator_id, func.count('*').label('cnt')).\
                filter(cast(Source.created, Date) >= day_from).\
                filter(cast(Source.created, Date) <= day_to).\
                group_by(Source.creator_id).\
                subquery()

        top_sourcers = session.query(UserAccount, src_cnts.c.cnt).\
            options(joinedload('photo')).\
            join(src_cnts, UserAccount.id==src_cnts.c.creator_id).\
            order_by(src_cnts.c.cnt.desc()).\
            limit(12).\
            all()

        return top_sourcers 

    return cache.get_or_create('top_sourcers', _calc, expiration_time=60*5)



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

        # TODO: do the work in the database.
        q = session.query(cast(Article.pubdate,Date), Article)

        if day_from is not None:
            q = q.filter(cast(Article.pubdate, Date) >= day_from)
        if day_to is not None:
            q = q.filter(cast(Article.pubdate, Date) <= day_to)

        for day,art in q:
            if day not in stats:
                foo = dict(total=0,done=0,help=0)
            else:
                foo = stats[day]
            foo['total'] += 1
            if not art.needs_sourcing:
                foo['done'] += 1
            stats[day]=foo

        stats = sorted([(day,row) for day,row in stats.iteritems()], key=lambda x: x[0], reverse=True )

        return [DailyStats(x[0], x[1]['total'], x[1]['done']) for x in stats]

    k = "daily_breakdown_from_%s_to_%s" % (day_from, day_to)
    return cache.get_or_create(k, _calc, 60*1)





class DailyBreakdown(BaseHandler):
    def get(self):

        stats = daily_breakdown(self.session)
        max_arts = max(stats, key=lambda x: x.total).total
 
        self.render('daily.html', stats=stats, max_arts=max_arts)





class FrontHandler(BaseHandler):
    def get(self):

        top_sourcers = calc_top_sourcers(self.session)

        # daily breakdown for the week
        today = datetime.datetime.utcnow().date()
        stats = daily_breakdown(self.session, today-datetime.timedelta(days=7), today)
        max_arts = max(stats, key=lambda x: x.total).total


        def _get_recent_actions():
            recent_actions = self.session.query(Action).\
                options(joinedload('article'),joinedload('user'),joinedload('source'),joinedload('comment')).\
                filter(Action.what.in_(('src_add','art_add','mark_sourced','mark_unsourced','helpreq_open','helpreq_close'))).\
                order_by(Action.performed.desc()).slice(0,6).all()
            return recent_actions

        recent_actions = cache.get_or_create("recent_actions", _get_recent_actions, 10)



        # 4 sample articles (3 unsourced, one sourced as an example)
        # TODO: should probably bias these toward being >1day old
        def _recent_arts_unsourced():
            return self.session.query(Article).\
                options(joinedload('sources'),joinedload('comments')).\
                filter(Article.needs_sourcing==True).\
                order_by(Article.pubdate.desc()).\
                limit(50).\
                all()

        def _recent_arts_sourced():
            return self.session.query(Article).\
                options(joinedload('sources'),joinedload('comments')).\
                filter(Article.needs_sourcing==False).\
                order_by(Article.pubdate.desc()).\
                limit(50).\
                all()

        sourced_arts = cache.get_or_create("recent_arts_sourced",_recent_arts_sourced, 60*17)
        unsourced_arts = cache.get_or_create("recent_arts_unsourced",_recent_arts_unsourced, 60*15)
        random_arts = random.sample(unsourced_arts, 3)
        random_arts += random.sample(sourced_arts, 1)
        random.shuffle(random_arts)

        # note: because of caching, a lot of the sqlalchemy objects will be
        # session-less (detached), so the template will fail if any further
        # database queries are triggered.
        # we could merge cached objects back into the session, but
        # that's silly - we should be avoiding fine-grained on-the-fly
        # additional queries anyway.
        self.render('front.html',
            random_arts = random_arts,
            recent_actions = recent_actions,
            groupby = itertools.groupby,
            top_sourcers = top_sourcers,
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
    (r'/help', HelpHandler),
    (r'/academicpapers', AcademicPapersHandler),
    (r"/addjournal", AddJournalHandler),
    (r"/addinstitution", AddInstitutionHandler),
    (r"/leaguetables", LeagueTablesHandler),
    (r"/daily", DailyBreakdown),
    ]
