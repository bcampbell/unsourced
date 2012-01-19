import datetime
from base import BaseHandler
import tornado.auth
import itertools

from sourcy.models import Article,Action,Lookup,Tag,UserAccount
from sqlalchemy import Date
from sqlalchemy.sql.expression import cast
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import subqueryload

from pprint import pprint



class MainHandler(BaseHandler):
    def get(self):

        days = []
        date = datetime.date.today()

        arts = self.session.query(Article).\
            options(subqueryload('tags'), subqueryload('sources')).\
            filter(cast(Article.pubdate, Date)== date).\
            all()

        days.append((date,arts))

        foo = self.session.query(Action).order_by(Action.performed.desc()).slice(0,10).all()

        # group by day
        recent = [(day,list(g)) for day,g in itertools.groupby(foo, lambda action:action.performed.date())]

        self.render('index.html', days=days, recent_actions=recent)




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
    (r'/', MainHandler),
    (r'/about', AboutHandler),
    (r'/academicpapers', AcademicPapersHandler),
    (r"/addjournal", AddJournalHandler),
    (r"/addinstitution", AddInstitutionHandler),
    (r"/leaguetables", LeagueTablesHandler),
    ]
