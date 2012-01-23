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

from handlers import history,user,article,addarticle,front,sources,tagging
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

        settings = dict(
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            ui_modules = uimodules,
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

        eng_url = "mysql+mysqldb://%(user)s:%(password)s@%(host)s/%(db)s?charset=utf8" % {
            'user': options.mysql_user,
            'password': options.mysql_password,
            'host': options.mysql_host,
            'db': options.mysql_database
        }
        self.engine = create_engine(eng_url, echo=False, pool_recycle=3600)
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

