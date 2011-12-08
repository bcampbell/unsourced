#!/usr/bin/env python

# scrapeomat
#
# Server for scraping news articles, returning parsed text and metadata
#
# eg
# $ lynx --source "http://localhost:8889/scrape?url=<url-of-article>"
#
# results returned as json object with fields:
#
# status
#  result of operation
#  0 OK
#  1 net error (eg newspaper site returned 404)
#  2 bad url
#  3 paywalled site
#  4 parse error
#
# article
#   only present if status is 0 (OK)
#   fields with article data.

import logging
import datetime
import time
import pickle
import re
import urlparse

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado import httpclient
from tornado.options import define, options

import decruft
import metareadability

define("port", default=8889, help="run on the given port", type=int)
define("cachefile", default=".scrapecache", help="file to dump the cache into", type=str)


paywall_domains = ['ft.com','thetimes.co.uk','thesundaytimes.co.uk']


class ScrapeHandler(tornado.web.RequestHandler):

    # TODO: store up http redirects and look for rel-canonical to collect alternative URLs for articles.
    # TODO: offload parsing to worker processes (see https://gist.github.com/312676 for example)

    @tornado.web.asynchronous
    def get(self):
        self.url = self.get_argument('url','').strip()

        o = urlparse.urlparse(self.url)
        domain = re.compile('^www[.]',re.I).sub('',o.hostname)
        if domain in paywall_domains:
            results = {'status': 3}   # 3=paywall site
            self.write(results)
            self.finish()
            return


        logging.debug( "%s: fetching...", self.url)
        if self.url == '':
            results = {'status': 2}   # 2=bad req
            self.write(results)
            self.finish()
            return

        art = self.application.fetch(self.url)
        if art is not None:
            logging.debug('%s: retrieved from cache', self.url)
            results = {'status': 0, 'article': art}   # 0=success
            self.write(results)
            self.finish()
            return
        else:
            # not in cache - need to actually scrape it
            http = tornado.httpclient.AsyncHTTPClient()
            http.fetch(self.url, callback=self.on_response)


    def on_response(self, response):
        if response.error:
            results = {'status':1}  # net error
        else:
            try:
                scrape_time = datetime.datetime.utcnow()
                html = response.body

                logging.debug("%s: processing...", self.url)
                txt = decruft.Document(html).summary()
                headline,byline,pubdate = metareadability.extract(html,self.url)

                logging.debug("%s: done.", self.url)

                headline = headline.encode('utf-8')
                txt = txt.encode('utf-8')

                urls = [self.url]
                permalink = self.url

                # convert times to unix timestamps to avoid json encoding ambiguity
                pubdate = int(time.mktime(pubdate.timetuple()))
                scrape_time = int(time.mktime(scrape_time.timetuple()))

                art = {'headline':headline,
                    'pubdate': pubdate,
                    'content': txt,
                    'permalink': permalink,
                    'urls': urls,
                    'scrapetime':scrape_time }
                self.application.stash(art)
                results = {'status':0, 'article':art}
            except Exception as e:
                logging.error("%s: exception: %s", self.url, e)
                results = {'status':4}   # error during parse

        self.write(results)
        self.finish()



class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/scrape', ScrapeHandler),
        ]
        settings = dict(
            cookie_secret = "SuperSecretKey(tm)",
            debug = True
            )

        self.cache_unsaved = False
        try:
            f = open(options.cachefile, 'r')
            self.art_cache = pickle.load(f)
            f.close()
            logging.debug("loaded %s (%d entries)", options.cachefile, len(self.art_cache))
        except:
            logging.warn("couldn't load %s", options.cachefile)
            self.art_cache = {}


        tornado.web.Application.__init__(self, handlers, **settings)
        logging.info("running")


    def fetch(self,url):
        """ return a cached article (or None) """
        return self.art_cache.get(url,None)

    def stash(self,art):
        """ store an article in the cache, indexed by url """
        for url in art['urls']:
            assert url not in self.art_cache
            self.art_cache[url] = art
        self.cache_unsaved = True
        self.save_cache()


    def save_cache(self):
        if self.cache_unsaved:
            f = open(options.cachefile,'w')
            pickle.dump(self.art_cache,f)
            f.close()
            self.cache_unsaved = False



def main():
    tornado.options.parse_command_line()
    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()

