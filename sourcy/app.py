import sys
import os
import logging

import tornado.ioloop
import tornado.web
import tornado.options
from tornado.options import define, options

import uimodules

from handlers import history,user,article,addarticle,front
from store import Store
import analyser


#define("port", default=8888, help="run on the given port", type=int)

#try:
#    import sourcy
#except ImportError:
#    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
#sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
#sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
#ROOT = os.path.dirname(os.path.abspath(__file__))
#site.addsitedir(os.path.join(ROOT,'FOOOK'))

def parse_config_file(path):
    """Rewrite tornado default parse_config_file.
    
    Parses and loads the Python config file at the given path.
    
    This version allow customize new options which are not defined before
    from a configuration file.
    """
    config = {}
    execfile(path, config, config)
    for name in config:
        if name in options:
            options[name].set(config[name])
        else:
            define(name, config[name])




class Application(tornado.web.Application):
    def __init__(self):

        handlers = []
        handlers.extend(front.handlers)
        handlers.extend(user.handlers)
        handlers.extend(article.handlers)
        handlers.extend(addarticle.handlers)
        handlers.extend(history.handlers)

        settings = dict(
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            ui_modules = uimodules,
            debug=options.debug,
            cookie_secret=options.cookie_secret,
            # auth secret
            twitter_consumer_key=options.twitter_consumer_key,
            twitter_consumer_secret=options.twitter_consumer_secret,
            #friendfeed_consumer_key=options.friendfeed_consumer_key,
            #friendfeed_consumer_secret=options.friendfeed_consumer_secret,
            #facebook_api_key=options.facebook_api_key,
            #facebook_secret=options.facebook_secret,
            )
        tornado.web.Application.__init__(self, handlers, **settings)

        self.store = Store()


        self.institution_finder = analyser.Lookerupper(self.store,'institution')
        self.journal_finder = analyser.Lookerupper(self.store,'journal')


def main():
    config_file = os.path.join(os.path.dirname(__file__), "../sourcy.conf")
    #tornado.options.parse_config_file(config_file)
    parse_config_file(config_file)
    tornado.options.parse_command_line()
    app = Application()
    app.listen(8888)
    logging.info("start.")
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()

