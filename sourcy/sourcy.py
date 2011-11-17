import tornado.ioloop
import tornado.web
import tornado.options
import os
from tornado.options import define, options
import logging
import urllib

import scrape
import util
import analyser
import uimodules
import highlight
from store import Store

define("port", default=8888, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', MainHandler),
            (r'/login', LoginHandler),
            (r'/logout', LogoutHandler),
            (r"/art/([0-9]+)", ArticleHandler),
            (r"/edit", EditHandler),
            (r"/addarticle", AddArticleHandler),
        ]
        settings = dict(
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret = "SuperSecretKey(tm)",
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            ui_modules = uimodules,
            debug = True
            )
        tornado.web.Application.__init__(self, handlers, **settings)

        self.store = Store()


        self.institution_finder = analyser.Lookerupper(self.store,'institution')
        self.journal_finder = analyser.Lookerupper(self.store,'journal')


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user_id = self.get_secure_cookie("user")
        if user_id is None:
            return None
        return self.store.user_get(user_id)

    @property
    def store(self):
        return self.application.store


class LoginHandler(BaseHandler):
    def get(self):
        self.render('login.html',badness={})

    def post(self):
        name = self.get_argument('name','').strip()
        if name=='':
            self.render('login.html', badness={'name':'Please enter your user name'})
            return

        user =  self.store.user_get_by_name(name)
        if user is None:
            user_id = self.store.user_create(name)
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
        art = self.store.art_get(art_id)
        sources = self.store.art_get_sources(art_id)
        html,headline,byline,pubdate = scrape.scrape(art.permalink)

        html = util.sanitise_html(html)
        researchers = analyser.find_researchers(html)
        journals = self.application.journal_finder.find(html)
        institutions = self.application.institution_finder.find(html)

        highlight_spans = []
        for name,url,kind,spans in journals:
            highlight_spans += [(s[0],s[1],kind) for s in spans]
        for name,url,kind,spans in institutions:
            highlight_spans += [(s[0],s[1],kind) for s in spans]
        for name,url,kind,spans in researchers:
            highlight_spans += [(s[0],s[1],kind) for s in spans]

        html = highlight.html_highlight(html, highlight_spans)

        rs = []
        for name,url,kind,spans in researchers:
            parts = name.split()
            initial = parts[0][0]
            surname = parts[-1]
            rs.append({'name': name, 'search_value': '"%s %s"' % (initial,surname)})

        self.render('article.html', art=art, article_content=html, sources=sources,researchers=rs, institutions=institutions, journals=journals) 


class MainHandler(BaseHandler):
    def get(self):
        arts = self.store.art_get_interesting(10)

#        sql = """select a.id as art_id, a.headline as art_headline, a.permalink as art_permalink,s.id,s.url,s.created,u.name as user_name,u.id as user_id from (source s left join useraccount u ON s.creator=u.id) inner join article a on a.id=s.article_id ORDER BY created DESC LIMIT 10"""

        recent = self.store.action_get_recent(10)
        self.render('index.html', articles=arts, recent_actions=recent)



class EditHandler(BaseHandler):
    def post(self):
        url = self.get_argument('url')
        art_id = int(self.get_argument('art_id'))
        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None
        self.store.action_add_source(user_id, art_id, url)

        self.redirect("/art/%d" % (art_id,))


class AddArticleHandler(BaseHandler):
    def post(self):
        url = self.get_argument('url')
        art = self.store.art_get_by_url(url)
        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None
        if art is None:
            txt,headline,byline,pubdate = scrape.scrape(url)
            art_id = self.store.action_add_article(user_id, url, headline, pubdate)
        else:
            art_id = art.id
        self.redirect("/art/%d" % (art_id,))

def main():
    tornado.options.parse_config_file("sourcy.conf")
    tornado.options.parse_command_line()
    app = Application()
    app.listen(8888)
    logging.info("start.")
    tornado.ioloop.IOLoop.instance().start()


