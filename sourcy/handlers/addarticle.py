import tornado.web
from tornado import httpclient
import urllib
import collections
import json
import datetime

from sourcy import util,analyser,highlight
from base import BaseHandler
from sourcy.models import Article,ArticleURL,Action

class AddArticleHandler(BaseHandler):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self):
        url = self.get_argument('url')
        art_url = self.session.query(ArticleURL).filter_by(url=url).first()
        if art_url is not None:
            art = art_url.article
            self.redirect("/art/%d" % (art.id,))
        else:
            # need to scrape the article metadata to add it to database
            # TODO: don't need to scrape article text here...
            params = {'url': url}
            scrape_url = 'http://localhost:8889/scrape?' + urllib.urlencode(params)
            http = tornado.httpclient.AsyncHTTPClient()
            http.fetch(scrape_url, callback=self.on_response)


    def on_response(self, response):
        worked = True
        if response.error:
            worked = False
        else:
            results = json.loads(response.body)
            if results['status']!=0:
                worked = False

        if not worked:
            # sorry, couldn't add that article for some reason...
            # TODO: provide form for manually entering details?
            self.write("Sorry... error grabbing details for that article.")
            self.finish()
            return

        scraped_art = results['article']

        scraped_art['scrapetime'] = datetime.datetime.fromtimestamp(scraped_art['scrapetime'])
        scraped_art['pubdate'] = datetime.datetime.fromtimestamp(scraped_art['pubdate'])

        url_objs = [ArticleURL(url=u) for u in scraped_art['urls']]
        art = Article(scraped_art['headline'],scraped_art['permalink'],scraped_art['pubdate'],url_objs)
        action = Action('art_add', self.current_user, article=art)
        self.session.add(art)
        self.session.add(action)
        self.session.commit()

        self.redirect("/art/%d" % (art.id,))



handlers = [
    (r"/addarticle", AddArticleHandler),
]

