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
# TODO: errors should be divided up into:
#    bad url - 404, invalid/badly formed url
#    can't process - paywall, parser failed etc
#
# article
#   only present if status is 0 (OK)
#   fields with article data.

import sys
import os
import logging
import logging.config

import tornado.ioloop
import tornado.web
from tornado.options import define, options, parse_command_line

from articlehandler import ArticleCache,ArticleHandler
from doihandler import DOIHandler

define("port", default=8889, help="run on the given port", type=int)
define("cachefile", default=".scrapecache", help="file to dump the cache into", type=str)
define("debug", default=False, help="run on the given port", type=bool)



class Application(tornado.web.Application):
    def __init__(self):

        self.artcache = ArticleCache(options.cachefile)

        handlers = [
            (r'/scrape', ArticleHandler),
            (r'/doi', DOIHandler),
        ]

        settings = dict(
            debug=options.debug,
#            cookie_secret=options.cookie_secret,
            )
        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    parse_command_line()

    app = Application()
    app.listen(options.port)

    log_conf = os.path.join(os.path.dirname(__file__), "logging.ini")
    logging.config.fileConfig(log_conf)
    logger = logging.getLogger('art')

    logger.info("start.")
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()

