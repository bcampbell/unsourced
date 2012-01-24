import logging
import datetime
import time
import pickle
import re
import urlparse

import tornado.httpserver
import tornado.web
from tornado import httpclient

import decruft
import metareadability


paywall_domains = ['ft.com','thetimes.co.uk','thesundaytimes.co.uk']



class ArticleCache(object):

    def __init__(self, cachefile):
        self.cachefile = cachefile
        self.unsaved = False
        try:
            f = open(self.cachefile, 'r')
            self.art_cache = pickle.load(f)
            f.close()
            logging.debug("loaded %s (%d entries)", self.cachefile, len(self.art_cache))
        except:
            logging.warn("couldn't load %s", self.cachefile)
            self.art_cache = {}


    def fetch(self,url):
        """ return a cached article (or None) """
        return self.art_cache.get(url,None)

    def stash(self,art):
        """ store an article in the cache, indexed by url """
        for url in art['urls']:
            assert url not in self.art_cache
            self.art_cache[url] = art
        self.unsaved = True
        self.save_cache()


    def save_cache(self):
        if self.unsaved:
            f = open(self.cachefile,'w')
            pickle.dump(self.art_cache,f)
            f.close()
            self.unsaved = False






class ArticleHandler(tornado.web.RequestHandler):
    # scrape an article, return data as json

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

        art = self.application.artcache.fetch(self.url)
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
                self.application.artcache.stash(art)
                results = {'status':0, 'article':art}
            except Exception as e:
                logging.error("%s: exception: %s", self.url, e)
                results = {'status':4}   # error during parse

        self.write(results)
        self.finish()


