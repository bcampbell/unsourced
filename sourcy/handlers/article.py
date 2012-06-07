import tornado.web
from tornado import httpclient
#import tornado.auth

#import logging
import urllib
import collections
import json
from pprint import pprint

from sourcy import util,analyser,highlight
from sourcy.models import Article,Source,Tag,TagKind,Action
from sourcy.forms import AddPaperForm, AddPRForm, AddOtherForm

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
            html = util.sanitise_html(html)

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


        all_tags = self.session.query(Tag).all()
        donetag = self.session.query(Tag).filter(Tag.name=='done').one()
        helptag = self.session.query(Tag).filter(Tag.name=='help').one()

        recent_actions = self.session.query(Action).\
            filter(Action.article_id==art.id).\
            filter(Action.what.in_(('src_add','src_remove','art_add','tag_add','tag_remove'))).\
            order_by(Action.performed.desc()).slice(0,10)

        recent_comments = self.session.query(Action).\
            filter(Action.article_id==art.id).\
            filter(Action.what.in_(('comment',))).\
            order_by(Action.performed.desc()).slice(0,10)



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
            all_tags = all_tags,
            TagKind=TagKind,
            helptag=helptag,
            recent_actions=recent_actions,
            recent_comments=recent_comments,
#            add_tag_form=add_tag_form
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





handlers = [
    (r"/art/([0-9]+)", ArticleHandler),
    (r"/art/([0-9]+)/mark-sourced",MarkSourcedHandler),
    (r"/art/([0-9]+)/mark-unsourced", MarkUnsourcedHandler),
]


