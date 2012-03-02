import sys
import os
import logging

import tornado.ioloop
import tornado.web
#import tornado.options
from tornado.options import define, options, parse_command_line

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import uimodules
import db

from handlers import history,user,article,addarticle,front,sources,tagging,comments
import analyser
from util import parse_config_file



class Application(tornado.web.Application):
    def __init__(self):

        handlers = []
        handlers.extend(front.handlers)
        handlers.extend(user.handlers)
        handlers.extend(article.handlers)
        handlers.extend(addarticle.handlers)
        handlers.extend(history.handlers)
        handlers.extend(sources.handlers)
        handlers.extend(tagging.handlers)
        handlers.extend(comments.handlers)

        ui_modules = [ uimodules, ]

        settings = dict(
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            ui_modules = ui_modules,
            debug=options.debug,
            cookie_secret=options.cookie_secret,
            login_url="/login",
            # auth secret
            twitter_consumer_key=options.twitter_consumer_key,
            twitter_consumer_secret=options.twitter_consumer_secret,
            #friendfeed_consumer_key=options.friendfeed_consumer_key,
            #friendfeed_consumer_secret=options.friendfeed_consumer_secret,
            #facebook_api_key=options.facebook_api_key,
            #facebook_secret=options.facebook_secret,
            )
        tornado.web.Application.__init__(self, handlers, **settings)

        self.engine = create_engine(db.engine_url(), echo=False, pool_recycle=3600)
        self.Session = sessionmaker(bind=self.engine)

        session = self.Session()
        self.institution_finder = analyser.Lookerupper(session,'institution')
        self.journal_finder = analyser.Lookerupper(session,'journal')


def main():
    config_file = os.path.join(os.path.dirname(__file__), "../sourcy.conf")
    parse_config_file(config_file)
    parse_command_line()

    app = Application()
    app.listen(8888)
    logging.info("start.")
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()

