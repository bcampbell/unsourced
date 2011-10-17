#!/usr/bin/env python
import tornado.ioloop
import tornado.web
import os

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', MainHandler),
        ]
        settings = dict(
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            )
        tornado.web.Application.__init__(self, handlers, **settings)

class BaseHandler(tornado.web.RequestHandler):
    pass


class MainHandler(BaseHandler):
    def get(self):
        self.render('index.html')


def main():
    app = Application()
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()

