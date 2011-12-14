import tornado.web
from tornado import httpclient
import urllib
import collections
import json
import datetime


from sourcy import util,analyser,highlight
from sourcy.store import Store
from base import BaseHandler


class AddArticleHandler(BaseHandler):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self):
        url = self.get_argument('url')
        art = self.store.art_get_by_url(url)
        if art is not None:
            art_id = art.id
            self.redirect("/art/%d" % (art.id,))
            self.finish()
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

        art = results['article']

        art['scrapetime'] = datetime.datetime.fromtimestamp(art['scrapetime'])
        art['pubdate'] = datetime.datetime.fromtimestamp(art['pubdate'])

        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None
        # TODO: add non-canonical url list if any
        art_id = self.store.action_add_article(user_id, art['permalink'], art['headline'], art['pubdate'])
        self.redirect("/art/%d" % (art_id,))
        self.finish()



handlers = [
    (r"/addarticle", AddArticleHandler),
]

