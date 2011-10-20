#!/usr/bin/env python
import tornado.ioloop
import tornado.web
import tornado.database
import tornado.options
import os
from tornado.options import define, options


define("port", default=8888, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1:3306", help="database host")
define("mysql_database", default="sourcy", help="database name")
define("mysql_user", default="sourcy", help="database user")
define("mysql_password", default="sourcy", help="database password")

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', MainHandler),
            (r'/login', LoginHandler),
            (r'/logout', LogoutHandler),
            (r"/art/([0-9]+)", ArticleHandler),
            (r"/edit", EditHandler),
        ]
        settings = dict(
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret = "SuperSecretKey(tm)",
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            )
        tornado.web.Application.__init__(self, handlers, **settings)

        self.db = tornado.database.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user_id = self.get_secure_cookie("user")
        if user_id is None:
            return None
        return self.db.get("SELECT * FROM useraccount WHERE id=%s", int(user_id))

    @property
    def db(self):
        return self.application.db


class LoginHandler(BaseHandler):
    def get(self):
        self.render('login.html',badness={})

    def post(self):
        name = self.get_argument('name','').strip()
        if name=='':
            self.render('login.html', badness={'name':'Please enter your user name'})
            return

        user =  self.db.get("SELECT * FROM useraccount WHERE name=%s", name)
        if user is None:
            # create one
            user_id = self.db.execute(
                "INSERT INTO useraccount (email,name,anonymous,created) VALUES (%s,%s,FALSE,NOW())",
                '', name)
        else:
            user_id = user.id

        self.set_secure_cookie("user", unicode(user_id))
        self.redirect("/")


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect("/")



class ArticleHandler(BaseHandler):
    def get(self,art_id):
        art_id = int(art_id)
        art = self.db.get("SELECT * FROM article WHERE id=%s", art_id)
        sources = self.db.query("SELECT * FROM source WHERE article_id=%s", art_id)
        self.render('article.html', art=art, sources=sources)


class MainHandler(BaseHandler):
    def get(self):
        arts = self.db.query("SELECT * FROM article")
        self.render('index.html', articles=arts)


class EditHandler(BaseHandler):
    def post(self):
        url = self.get_argument('url')
        art_id = int(self.get_argument('art_id'))
        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None
        self.db.execute("INSERT INTO source (article_id,url,doi,title,creator,created) VALUES (%s,%s,%s,%s,%s,NOW())", art_id, url,'','',user_id)

        self.redirect("/art/%d" % (art_id,))

def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()

