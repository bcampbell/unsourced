from datetime import datetime,timedelta

import time

import urllib

import tornado.auth
from sqlalchemy import Date,not_
from sqlalchemy.sql.expression import cast,func
from sqlalchemy.orm import subqueryload
from wtforms import Form, Field, SelectField, RadioField, HiddenField, BooleanField, TextField, PasswordField, FileField, validators,DateField
#from wtforms.ext.dateutil.fields import DateField
from wtforms import widgets

from base import BaseHandler
from unsourced.models import Article,Action,Lookup,Tag,TagKind,UserAccount,Comment,article_tags
from unsourced.paginator import Paginator
from unsourced.util import TornadoMultiDict
from unsourced import uimodules

date_defs = {
    'today': dict(
        order = 0,
        label = "Today",
        from_delta = timedelta(days=1),
        desc_fmt = "Today's %(articles)s%(mods)s"
    ),
    '1week': dict(
        order = 1,
        label = "Past week",
        from_delta = timedelta(days=7),
        desc_fmt = "%(articles)s from the past week%(mods)s"
    ),
    '30days': dict(
        order = 2,
        label = "Past 30 days",
        from_delta = timedelta(days=30),
        desc_fmt = "%(articles)s from the past 30 days%(mods)s"
    ),
    '1year': dict(
        order = 3,
        label = "Past year",
        from_delta = timedelta(days=365),
        desc_fmt = "%(articles)s from the past year%(mods)s"
    ),
    'all': dict(
        order = 4,
        label = "All dates",
        desc_fmt = "All %(articles)s%(mods)s"
    ),
    'range': dict(
        order = 5,
        label = "In range...",
        use_date_range = True,
        desc_fmt = "%(articles)s %(daterange)s%(mods)s"
    ),
}



class MyCrapDateField(Field):
    """
    A text field which stores a `datetime.datetime` matching a format.
    (the standard wtforms dates don't provide a decent error message for
    unparsable dates)
    """
    widget = widgets.TextInput()

    def __init__(self, label=None, validators=None, format='%Y-%m-%d', **kwargs):
        super(MyCrapDateField, self).__init__(label, validators, **kwargs)
        self.format = format

    def _value(self):
        if self.raw_data:
            return u' '.join(self.raw_data)
        else:
            return self.data and self.data.strftime(self.format) or u''

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = u' '.join(valuelist)
            try:
                self.data = datetime.strptime(date_str, self.format).date()
            except ValueError:
                self.data = None
                raise ValueError(u"Invalid date. Please use YYYY-MM-DD")

def IgnoreUnless(otherfield, value):
    """ validator - stop validation chain unless otherfield contains value """
    def _ignore_unless(form, field):
        if getattr(form,otherfield).data != value:
            raise validators.StopValidation()
    return _ignore_unless


class RequireOneOf(object):
    """ validator - fail unless at least one of the given fields is set """

    def __init__(self, fields, message=None):
        self.fields = fields
        self.message = message

    def __call__(self, form, field):

        got_one = False
        for field_name in self.fields:
            f = getattr(form,field_name)
            if not f.raw_data or isinstance(f.raw_data[0], basestring) and not f.raw_data[0].strip():
                pass
            else:
                got_one = True
                break

        if not got_one:
            if self.message is None:
                self.message = field.gettext(u'At least one of these is required.')
            raise validators.ValidationError(self.message)




class FiltersForm(Form):
    DATE_CHOICES = sorted([(k, v['label']) for k,v in date_defs.items()], key=lambda x: date_defs[x[0]]['order'])
    date = RadioField("Narrow by Date", choices=DATE_CHOICES, default="today")
    dayfrom = MyCrapDateField("from (yyyy-mm-dd)",
        [IgnoreUnless('date','range'),
        RequireOneOf(['dayfrom','dayto']) ])
    dayto = MyCrapDateField("to (yyyy-mm-dd)",[IgnoreUnless('date','range')])
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

        daterange = ''
        if date_def.get('use_date_range',False):
            day_from = self.dayfrom.data
            day_to = self.dayto.data
            if day_from and not day_to:
                daterange = 'since ' + day_from.strftime("%Y-%m-%d")
            elif not day_from and day_to:
                daterange = 'before ' + day_to.strftime("%Y-%m-%d")
            elif day_from and day_to:
                if day_from == day_to:
                    daterange = 'for ' + day_from.strftime("%Y-%m-%d")
                else:
                    daterange = 'between %s and %s' %(day_from.strftime("%Y-%m-%d"),day_to.strftime("%Y-%m-%d"))



        desc = fmt % {'articles':articles,'mods':mods,'daterange':daterange}

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

        filters_form = FiltersForm(TornadoMultiDict(self))

        arts = self.session.query(Article)

        if not filters_form.validate():
            # uh-oh - form is bad.
            if self.is_xhr():
                # if ajax, just send the errors
                errs = {}
                for field in filters_form:
                    if field.errors:
                        errs[field.name] = field.errors
                self.finish({'status': 'badfilters', 'errors': errs})

                return
            else:
                paged_results = Paginator()
                self.render("browse.html",filters=filters_form,paged_results=paged_results)
                return

        # build up the query

        date_def = date_defs.get(filters_form.date.data, None)
        day_from = None
        day_to = None
        if date_def:
            if date_def.get('from_delta',None) is not None:
                day_from = datetime.utcnow().date() - date_def['from_delta']
            if date_def.get('to_delta',None) is not None:
                day_to = datetime.utcnow().date() - date_def['to_delta']
            if date_def.get('use_date_range',False):
                day_from = filters_form.dayfrom.data
                day_to = filters_form.dayto.data

        if day_from:
            arts = arts.filter(cast(Article.pubdate, Date) >= day_from)
        if day_to:
            arts = arts.filter(cast(Article.pubdate, Date) <= day_to)

        if filters_form.help.data:
            arts = arts.filter(Article.help_reqs.any())

        if filters_form.discussed.data:
            arts = arts.filter(Article.comments.any())

        if filters_form.sourced.data=='unsourced':
            arts = arts.filter(Article.needs_sourcing==True)
        elif filters_form.sourced.data=='sourced':
            arts = arts.filter(Article.needs_sourcing==False)

        arts = arts.order_by(Article.pubdate.desc())



        # paginate the results

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
            module = uimodules.searchresults(self)
            html = module.render(filters=filters_form,paged_results=paged_results) 
            self.finish({'status':'ok', 'results_html': html})
        else:
            self.render("browse.html",filters=filters_form,paged_results=paged_results)


handlers = [
    (r'/browse', BrowseHandler),
    ]

