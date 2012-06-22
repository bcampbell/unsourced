from datetime import datetime,timedelta
import urllib

import tornado.auth
from sqlalchemy import Date,not_
from sqlalchemy.sql.expression import cast,func
from sqlalchemy.orm import subqueryload
from wtforms import Form, SelectField, RadioField, HiddenField, BooleanField, TextField, PasswordField, FileField, validators

from base import BaseHandler
from sourcy.models import Article,Action,Lookup,Tag,TagKind,UserAccount,Comment,article_tags
from sourcy.util import Paginator
from sourcy.util import TornadoMultiDict
from sourcy.uimodules import searchresults

date_defs = {
    'today': dict(
        order = 0,
        label = "Today",
        delta = timedelta(days=1),
        desc_fmt = "Today's %(articles)s%(mods)s"
    ),
    '1week': dict(
        order = 1,
        label = "Past week",
        delta = timedelta(days=7),
        desc_fmt = "%(articles)s from the past week%(mods)s"
    ),
    '30days': dict(
        order = 2,
        label = "Past 30 days",
        delta = timedelta(days=30),
        desc_fmt = "%(articles)s from the past 30 days%(mods)s"
    ),
    '1year': dict(
        order = 3,
        label = "Past year",
        delta = timedelta(days=365),
        desc_fmt = "%(articles)s from the past year%(mods)s"
    ),
    'all': dict(
        order = 4,
        label = "All dates",
        delta = None,
        desc_fmt = "All %(articles)s%(mods)s"
    ),
}

class FiltersForm(Form):
    DATE_CHOICES = sorted([(k, v['label']) for k,v in date_defs.items()], key=lambda x: date_defs[x[0]]['order'])
    date = RadioField("Narrow by Date", choices=DATE_CHOICES, default="today")
    sourced = RadioField("Sourced", choices=[('all','All'),('unsourced','Unsourced'),('sourced','Sourced')], default='all')

    help = BooleanField("Help requested")
    discussed = BooleanField("Discussed")

    def describe(self):
        """ create pretty description of filter, suitable for heading """

        date_def = date_defs.get(self.date.data, None)

        if date_def:
            fmt = date_def['desc_fmt']
        else:
            fmt= "(%articles)(%mods)"

        if self.sourced.data == 'sourced':
            articles = "sourced articles"
        elif self.sourced.data == 'unsourced':
            articles = "unsourced articles"
        else:
            articles = "articles"

        mod_parts = []
        if self.help.data:
            mod_parts.append("help requests")
        if self.discussed.data:
            mod_parts.append("comments")
        mods = ' and '.join(mod_parts)
        if mods:
            mods = " with " + mods

        desc = fmt % {'articles':articles,'mods':mods}

        # awful cheesey hack to ensure starts with uppercase
        desc = desc[0].upper() + desc[1:]
        return desc


#$('form').bind('submit', function(e){
#    e.preventDefault();
#    //do your stuff
#});

class BrowseHandler(BaseHandler):
    def get(self):
        page = int(self.get_argument('p',1))

        filters = FiltersForm(TornadoMultiDict(self))

        arts = self.session.query(Article)

        if filters.validate():
            date_def = date_defs.get(filters.date.data, None)
            if date_def:
                if date_def['delta'] is not None:
                    day_from = datetime.utcnow().date() - date_def['delta']
                    arts = arts.filter(cast(Article.pubdate, Date) >= day_from)

#            day_to = None
#            if day_to:
#                arts = arts.filter(cast(Article.pubdate, Date) <= day_to)

            if filters.help.data:
                arts = arts.filter(Article.help_reqs.any())

            if filters.discussed.data:
                arts = arts.filter(Article.comments.any())

            if filters.sourced.data=='unsourced':
                arts = arts.filter(Article.needs_sourcing==True)
            elif filters.sourced.data=='sourced':
                arts = arts.filter(Article.needs_sourcing==False)

        arts = arts.order_by(Article.pubdate.desc())

        def page_url(page):
            """ generate url for the given page of this query"""
            params = {}
            # preserve all request params, and override page number
            for k in self.request.arguments:
                params[k] = self.get_argument(k)
            params['p'] = page
            url = "/browse?" + urllib.urlencode(params)
            return url

        paged_results = Paginator(arts, 100, page, page_url)
        if self.is_xhr():
            # if ajax, just render a new #searchresults instead of whole page
            results = searchresults(self)
            self.finish(results.render(filters=filters,paged_results=paged_results))
        else:
            self.render("browse.html",filters=filters,paged_results=paged_results)


handlers = [
    (r'/browse', BrowseHandler),
    ]

