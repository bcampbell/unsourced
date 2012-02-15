import tornado.web
from tornado import httpclient
#import tornado.auth

#import logging
import urllib
import collections
import json
from pprint import pprint

from sourcy import util,analyser,highlight
from sourcy.models import Article,Source
from sourcy.forms import AddSourceForm, AddTagForm

from base import BaseHandler

class ArticleHandler(BaseHandler):

    @tornado.web.asynchronous
    def get(self,art_id):
        self.art = self.session.query(Article).get(art_id)
        if self.art is None:
            raise tornado.web.HTTPError(404, "Article not found")
 
        http = tornado.httpclient.AsyncHTTPClient()

        # ask the scrapeomat for the article text
        # TODO: don't need to scrape article metadata here...
        params = {'url': self.art.permalink}
        url = "http://localhost:8889/scrape?" + urllib.urlencode(params)

        http.fetch(url, callback=self.on_response)

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

        if scrape_err is None:
            html = results['article']['content']
            html = util.sanitise_html(html)
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

        add_source_form = AddSourceForm()
        add_tag_form = AddTagForm()

        self.render('article.html',
            art=art,
            article_content=html,
            warnings = self.cook_warnings(art),
            researchers=researchers,
            institutions=institutions,
            journals=journals,
            scrape_err=scrape_err,
            add_source_form=add_source_form,
            add_tag_form=add_tag_form)
        #self.finish()


    def cook_warnings(self,art):
        details = {
            'warn_wikipedia': ('This article contains unsourced, unverified information from Wikipedia.',),
            'warn_anon':('This article is based on an unverified, anonymous tipoff.',),
            'warn_soft':('To ensure future interviews with subject, important questions were not asked.',),
            'warn_churn':('This article is basically just a press release, copied and pasted.',),
            'warn_pr': ('Statistics, survey results and/or equations in this article were sponsored by a PR company.',) }

        warns = []
        for tag in art.tags:
            warn = tag.name
            if warn in details:
                warns.append((details[warn][0],'/static/%s.png' %(warn,)))
        return warns

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


handlers = [
    (r"/art/([0-9]+)", ArticleHandler),
]

