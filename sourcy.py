#!/usr/bin/env python
import tornado.ioloop
import tornado.web
import tornado.database
import tornado.options
import os
from tornado.options import define, options

import store

define("port", default=8888, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1:3306", help="database host")
define("mysql_database", default="sourcy", help="database name")
define("mysql_user", default="sourcy", help="database user")
define("mysql_password", default="sourcy", help="database password")

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', MainHandler),
            (r"/art/([0-9]+)", ArticlePage),
        ]
        settings = dict(
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            )
        tornado.web.Application.__init__(self, handlers, **settings)

        self.db = tornado.database.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)

class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db


class ArticlePage(BaseHandler):
    def get(self,article_id):
        arts = self.db.query("SELECT * FROM article WHERE id=%s", (int(article_id)))
        self.render('article.html', art=arts[0])

class MainHandler(BaseHandler):
    def get(self):
        self.render('index.html')


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()

