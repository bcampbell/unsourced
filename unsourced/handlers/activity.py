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
from unsourced.queries import build_action_query
from unsourced.cache import cache
from unsourced.paginator import SAPaginator
from unsourced import uimodules

import util








class ActionBrowseHandler(BaseHandler):
    def get(self):
        page = int(self.get_argument('p',1))
        view = self.get_argument('view',None)

        filters = {}

        # paginate the results

        def page_url(page):
            """ generate url for the given page of this query"""
            params = {}
            # preserve all request params, and override page number
            for k in self.request.arguments:
                params[k] = self.get_argument(k)
            params['p'] = page
            url = "/activity?" + urllib.urlencode(params)
            return url

        actions = build_action_query(self.session,view,current_user=self.current_user)
        paged_results = SAPaginator(actions, page, page_url, per_page=100)

        if self.is_xhr():
            # if ajax, just render a new #searchresults instead of whole page
            module = uimodules.actionbrowser(self)
            html = module.render(filters=filters,paged_results=paged_results) 
            self.finish({'status':'ok', 'results_html': html})
        else:
            self.render("activity.html",filters=filters,paged_results=paged_results)


handlers = [
    (r'/activity', ActionBrowseHandler),
    ]

