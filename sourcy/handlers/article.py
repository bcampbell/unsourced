import tornado.web
from tornado import httpclient
#import tornado.auth

#import logging
import urllib
import collections
import json


from sourcy import util,analyser,highlight
from sourcy.store import Store
from base import BaseHandler
from sourcy.forms import AddSourceForm

from pprint import pprint

class ArticleHandler(BaseHandler):

    @tornado.web.asynchronous
    def get(self,art_id):
        art_id = int(art_id)
        self.art = self.store.art_get(art_id)
        
        http = tornado.httpclient.AsyncHTTPClient()

        # ask the scrapeomat for the article text
        # TODO: don't need to scrape article metadata here...
        params = {'url': self.art.permalink}
        url = "http://localhost:8889/scrape?" + urllib.urlencode(params)

        http.fetch(url, callback=self.on_response)

    def on_response(self, response):
        art = self.art
        art_id = art.id

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

        sources = self.store.art_get_sources(art_id)

        add_source_form = AddSourceForm(self,art_id)

        self.render('article.html', art=art, article_content=html, sources=sources,researchers=researchers, institutions=institutions, journals=journals, scrape_err=scrape_err, add_source_form=add_source_form) 
        #self.finish()



    def analyse_text(self,html):
        researchers = analyser.find_researchers(html)

        journals = self.application.journal_finder.find(html)
        institutions = self.application.institution_finder.find(html)

        highlight_spans = journals + institutions
        
        for name,url,kind,spans in researchers:
            highlight_spans += [(s[0],s[1],kind,name,url) for s in spans]

        # remove spans contained within other spans
        highlight_spans = highlight.remove_contained_spans(highlight_spans)
        return highlight_spans


handlers = [
    (r"/art/([0-9]+)", ArticleHandler),
]

