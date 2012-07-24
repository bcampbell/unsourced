#import logging
import urllib
import collections
import json
from pprint import pprint
import re

import tornado.web
from tornado import httpclient
#import tornado.auth
from lxml.html.clean import Cleaner


from unsourced import util,analyser,highlight
from unsourced.models import Article,Source,Tag,TagKind,Action,HelpReq
from unsourced.forms import AddPaperForm, AddPRForm, AddOtherForm
from unsourced.paginator import SAPaginator

from base import BaseHandler

class ArticleHandler(BaseHandler):

    @tornado.web.asynchronous
    def get(self,art_id):
        self.art = self.session.query(Article).get(art_id)
        if self.art is None:
            raise tornado.web.HTTPError(404, "Article not found")

        # manually pasted text (stored in a cookie for persistance)
        txt = self.get_argument('text',None)
        txt_cookie_name = "a%d" %(self.art.id,)
        if txt is None:
            txt = self.get_secure_cookie(txt_cookie_name)
        else:
            # text was pasted
            # save in a cookie for cheesy client-side persistance
            self.set_secure_cookie(txt_cookie_name, txt, expires_days=2)


        if txt is not None:
            self.go(txt,None)
        else:
            http = tornado.httpclient.AsyncHTTPClient()

            # ask the scrapeomat for the article text
            # TODO: don't need to scrape article metadata here...
            params = {'url': self.art.permalink}
            url = "http://localhost:8889/scrape?" + urllib.urlencode(params)

            http.fetch(url, callback=self.on_response)


    # post() usually called as a result of manually pasting text
    def post(self,art_id):
        self.get(art_id)


    def on_response(self, response):
        art = self.art

        errs = {0: None,
            1: u"Error while trying to read article",
            2: u"Bad article URL",
            3: u"Site is paywalled",
            4: u"Couldn't extract text from the article"
        }
        scrape_err = None

        if response.error:
            scrape_err = "Internal error"
        else:
            results = json.loads(response.body)
            if results['status']!=0:
                scrape_err = errs[results['status']]

        html = None
        if scrape_err is None:
            html = results['article']['content']



            cleaner = Cleaner(
                page_structure=False,
                kill_tags = ['h1','h2','h3','h4','h5'],
                remove_tags = ['a','strong'],
                allow_tags = ['p','br','b','i','em','li','ul','ol','blockquote', 'a'],
                remove_unknown_tags = False)
            html = cleaner.clean_html(html)


        self.go(html,scrape_err)




    def go(self, html, scrape_err=None):

        art = self.art
        if html is not None:
            highlight_spans = self.analyse_text(html)
            # mark up the html
            html = highlight.html_highlight(html, highlight_spans)

            # now find the unique matches for each kind
            uniq = collections.defaultdict(set)
            for (start,end,kind,name,url) in highlight_spans:
                uniq[kind].add((name,url))
    
            rs = uniq['researcher']
            institutions = uniq['institution']
            journals = uniq['journal']
            researchers = []
            for (name,url) in rs:
                parts = name.split()
                initial = parts[0][0]
                surname = parts[-1]
                researchers.append({'name': name, 'search_value': '"%s %s"' % (initial,surname)})

        else:
            # don't have any text available :-(
            html = ''
            researchers,institutions,journals = [],[],[]


        n_actions=6    # show most recent N actions
        recent_actions = self.session.query(Action).\
            filter(Action.article_id==art.id).\
            filter(Action.what.in_(('src_add','src_remove','art_add','tag_add','tag_remove','mark_sourced','mark_unsourced','helpreq_open','helpreq_close','comment'))).\
            order_by(Action.performed.desc()).\
            slice(0,n_actions+1).\
            all()
        more_actions = False
        if len(recent_actions)>n_actions:
            more_actions = True
            recent_actions = recent_actions[:n_actions]
        recent_actions = reversed(recent_actions)



        add_paper_form = AddPaperForm()
        add_pr_form = AddPRForm()
        add_other_form = AddOtherForm()

        self.render('article.html',
            art=art,
            article_content=html,
            researchers=researchers,
            institutions=institutions,
            journals=journals,
            scrape_err=scrape_err,
            add_paper_form=add_paper_form,
            add_pr_form=add_pr_form,
            add_other_form=add_other_form,
            recent_actions=recent_actions,
            more_actions=more_actions,
        )
        #self.finish()

    def analyse_text(self,html):
        researchers = analyser.find_researchers(html)

        journals = self.application.journal_finder.find(html)
        institutions = self.application.institution_finder.find(html)

        highlight_spans = [] 
        for name,url,kind,spans in researchers:
            highlight_spans += [(s[0],s[1],kind,name,url) for s in spans]
        highlight_spans += journals
        highlight_spans += institutions

        # remove spans contained within other spans
        highlight_spans = highlight.remove_contained_spans(highlight_spans)

        return highlight_spans

class MarkSourcedHandler(BaseHandler):
    """ mark an article as sourced """

    @tornado.web.authenticated
    def post(self,art_id):
        art = self.session.query(Article).get(art_id)
        if art is None:
            raise tornado.web.HTTPError(404, "Article not found")

        act = Action('mark_sourced', self.current_user, article=art)
        art.needs_sourcing = False
        self.session.add(act)
        self.session.commit()

        self.redirect('/art/%s' %(art.id,))


class MarkUnsourcedHandler(BaseHandler):
    """ mark an article as not sourced """

    @tornado.web.authenticated
    def post(self,art_id):
        art = self.session.query(Article).get(art_id)
        if art is None:
            raise tornado.web.HTTPError(404, "Article not found")

        act = Action('mark_unsourced', self.current_user, article=art)
        art.needs_sourcing = True
        self.session.add(act)
        self.session.commit()

        self.redirect('/art/%s' %(art.id,))


class OpenHelpReqHandler(BaseHandler):
    """ open a help request on the article """

    @tornado.web.authenticated
    def post(self,art_id):
        art = self.session.query(Article).get(art_id)
        if art is None:
            raise tornado.web.HTTPError(404, "Article not found")

        act = Action('helpreq_open', self.current_user, article=art)
        self.session.add(act)
        helpreq = HelpReq(article=art,user=self.current_user)
        self.session.add(helpreq)
        self.session.commit()

        self.redirect('/art/%s' %(art.id,))


class CloseHelpReqHandler(BaseHandler):
    """ close a help request on article """

    @tornado.web.authenticated
    def post(self,art_id):
        art = self.session.query(Article).get(art_id)
        if art is None:
            raise tornado.web.HTTPError(404, "Article not found")

        helpreqs = self.session.query(HelpReq).\
            filter(HelpReq.article==art).\
            all()
        if helpreqs:
            [self.session.delete(req) for req in helpreqs]
            act = Action('helpreq_close', self.current_user, article=art)
            self.session.add(act)
            self.session.commit()

        self.redirect('/art/%s' %(art.id,))


class HistoryHandler(BaseHandler):
    """ browse an article's history """


    def get(self,art_id):
        art = self.session.query(Article).get(art_id)
        if art is None:
            raise tornado.web.HTTPError(404, "Article not found")

        page = int(self.get_argument('p',1))

        actions = self.session.query(Action).\
            filter(Action.article_id==art.id).\
            order_by(Action.performed.asc())

        def page_url(page):
            """ generate url for the given page of this query"""
            params = {}
            # preserve all request params, and override page number
            for k in self.request.arguments:
                params[k] = self.get_argument(k)
            params['p'] = page
            url = "/art/%d/history?%s" % (art.id, urllib.urlencode(params))
            return url

        paged_results = SAPaginator(actions, page, page_url, per_page=100)
        self.render("art_history.html", art=art,paged_results=paged_results)


handlers = [
    (r"/art/([0-9]+)", ArticleHandler),
    (r"/art/([0-9]+)/history",HistoryHandler),
    (r"/art/([0-9]+)/mark-sourced",MarkSourcedHandler),
    (r"/art/([0-9]+)/mark-unsourced", MarkUnsourcedHandler),
    (r"/art/([0-9]+)/open-helpreq",OpenHelpReqHandler),
    (r"/art/([0-9]+)/close-helpreq", CloseHelpReqHandler),
]


