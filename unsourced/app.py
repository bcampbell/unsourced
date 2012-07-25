import sys
import os
import logging
import logging.config
import site


# so handlers can import model etc...
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
site.addsitedir(parent_dir)


import tornado.ioloop
import tornado.web
import tornado.options

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


import uimodules
import db
import config

from handlers import base,user,article,addarticle,front,sources,tagging,comments,browse,tokens,dashboard,api

import analyser



class Application(tornado.web.Application):
    def __init__(self):
        handlers = []
        handlers.extend(front.handlers)
        handlers.extend(user.handlers)
        handlers.extend(article.handlers)
        handlers.extend(addarticle.handlers)
        handlers.extend(sources.handlers)
        handlers.extend(tagging.handlers)
        handlers.extend(comments.handlers)
        handlers.extend(browse.handlers)
        handlers.extend(tokens.handlers)
        handlers.extend(dashboard.handlers)
        handlers.extend(api.handlers)

        handlers.append((r".*", base.MissingHandler))

        ui_modules = [ uimodules, ]

        static_path = os.path.join(os.path.dirname(__file__), "static")

        settings = dict(
            static_path = static_path,
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            ui_modules = ui_modules,
            debug=config.settings.debug,
            cookie_secret=config.settings.cookie_secret,
            login_url="/login",
            xsrf_cookies = True,
            # auth secret
            twitter_consumer_key=config.settings.twitter_consumer_key,
            twitter_consumer_secret=config.settings.twitter_consumer_secret,

        )
        tornado.web.Application.__init__(self, handlers, **settings)

        self.engine = create_engine(db.engine_url(),
            pool_size=10,
            max_overflow=10,
            pool_timeout=10,
            pool_recycle=3600)
        self.Session = sessionmaker(bind=self.engine)

        session = self.Session()
        self.institution_finder = analyser.Lookerupper(session,'institution')
        self.journal_finder = analyser.Lookerupper(session,'journal')


tornado.options.define("port", default="8888", help="port number")

def main():
    tornado.options.parse_command_line()

    log_conf = os.path.join(os.path.dirname(__file__), "logging.ini")
    logging.config.fileConfig(log_conf)

    app = Application()
    app.listen(tornado.options.options.port)
    logging.info("start.")
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
