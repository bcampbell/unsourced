import tornado.ioloop
import tornado.web
import tornado.options
from tornado import httpclient
from tornado.options import define, options
import tornado.auth
import os
import logging
import urllib
import collections
import json
import datetime

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
            (r'/about', AboutHandler),
            (r'/academicpapers', AcademicPapersHandler),
            (r'/login', LoginHandler),
            (r'/login/google', GoogleLoginHandler),
            (r'/logout', LogoutHandler),
            (r"/art/([0-9]+)", ArticleHandler),
            (r"/([0-9]{4}-[0-9]{2}-[0-9]{2})", DayHandler),
            (r"/edit", EditHandler),
            (r"/addarticle", AddArticleHandler),
            (r"/addjournal", AddJournalHandler),
            (r"/addinstitution", AddInstitutionHandler),
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
        next = self.get_argument("next", None);
        self.render('login.html', next=next)



class GoogleLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()
    
    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")

        sourcy_user = self.store.user_get_by_email(user['email'])
        if sourcy_user is None:
            user_id = self.store.user_create(user['email'],user['name']);
        else:
            user_id = sourcy_user.id
        self.set_secure_cookie("user", unicode(user_id))
        self.redirect(self.get_argument("next", "/"))



class LogoutHandler(BaseHandler):

    def get(self):
        self.clear_cookie("user")
        self.redirect("/")






class ArticleHandler(BaseHandler):

    @tornado.web.asynchronous
    def get(self,art_id):
        art_id = int(art_id)
        self.art = self.store.art_get(art_id)
        
        http = tornado.httpclient.AsyncHTTPClient()

        # ask the scrapeomat for the article text
        # TODO: don't need to scrape article metadata here...
        params = {'url': self.art.permalink}
        url = "http://localhost:8889/scrape?" + urllib.urlencode(params)

        http.fetch(url, callback=self.on_response)

    def on_response(self, response):
        art = self.art
        art_id = art.id

        worked = True
        if response.error:
            worked = False
        else:
            results = json.loads(response.body)
            if results['status']!=0:
                worked = False

        if not worked:
            # sorry, couldn't add that article for some reason...
            # TODO: provide form for manually entering details?
            self.write("Sorry... error adding that article.")
            self.finish()
            return

        html = results['article']['content']

        sources = self.store.art_get_sources(art_id)

        html = util.sanitise_html(html)
        researchers = analyser.find_researchers(html)

        journals = self.application.journal_finder.find(html)
        institutions = self.application.institution_finder.find(html)

        highlight_spans = journals + institutions
        
        for name,url,kind,spans in researchers:
            highlight_spans += [(s[0],s[1],kind,name,url) for s in spans]

        # remove spans contained within other spans
        highlight_spans = highlight.remove_contained_spans(highlight_spans)

        # mark up the html
        html = highlight.html_highlight(html, highlight_spans)

        # now find the unique matches for each kind
        uniq = collections.defaultdict(set)
        for (start,end,kind,name,url) in highlight_spans:
            uniq[kind].add((name,url))

        researchers = uniq['researcher']
        institutions = uniq['institution']
        journals = uniq['journal']

        rs = []
        for (name,url) in researchers:
            parts = name.split()
            initial = parts[0][0]
            surname = parts[-1]
            rs.append({'name': name, 'search_value': '"%s %s"' % (initial,surname)})

        self.render('article.html', art=art, article_content=html, sources=sources,researchers=rs, institutions=institutions, journals=journals) 
        #self.finish()



class MainHandler(BaseHandler):
    def get(self):

        days = []
        date = datetime.date.today()
        for n in range(5):
            arts = self.store.art_get_by_date(date)
            days.append((date,arts))
            date = date - datetime.timedelta(days=1)

#        arts = self.store.art_get_interesting(10)

        recent = self.store.action_get_recent(10)
        self.render('index.html', days=days, recent_actions=recent)


class DayHandler(BaseHandler):
    """show summary for a given day"""
    def get(self,datestr):
        date = datetime.datetime.strptime(datestr,'%Y-%m-%d').date()
        arts = self.store.art_get_by_date(date)
        self.render('day.html', date=date, arts=arts)


class AboutHandler(BaseHandler):
    def get(self):
        self.render('about.html')

class AcademicPapersHandler(BaseHandler):
    def get(self):
        self.render('academicpapers.html')




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
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self):
        url = self.get_argument('url')
        art = self.store.art_get_by_url(url)
        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None
        if art is not None:
            art_id = art.id
            self.redirect("/art/%d" % (art.id,))
            self.finish()
        else:
            # need to scrape the article metadata to add it to database
            # TODO: don't need to scrape article text here...
            params = {'url': url}
            scrape_url = 'http://localhost:8889/scrape?' + urllib.urlencode(params)
            http = tornado.httpclient.AsyncHTTPClient()
            http.fetch(scrape_url, callback=self.on_response)


    def on_response(self, response):
        worked = True
        if response.error:
            worked = False
        else:
            results = json.loads(response.body)
            if results['status']!=0:
                worked = False

        if not worked:
            # sorry, couldn't add that article for some reason...
            # TODO: provide form for manually entering details?
            self.write("Sorry... error grabbing text for that article.")
            self.finish()
            return

        art = results['article']

        art['scrapetime'] = datetime.datetime.fromtimestamp(art['scrapetime'])
        art['pubdate'] = datetime.datetime.fromtimestamp(art['pubdate'])

        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None
        # TODO: add non-canonical url list if any
        art_id = self.store.action_add_article(user_id, art['permalink'], art['headline'], art['pubdate'])
        self.redirect("/art/%d" % (art_id,))
        self.finish()


class AddInstitutionHandler(BaseHandler):
    kind = 'institution'

    def get(self):
        self.render('addlookup.html',kind=self.kind)

    def post(self):
        name = self.get_argument('name')
        homepage = self.get_argument('homepage')

        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None

        self.store.action_add_lookup(user_id, self.kind, name, homepage)
        self.redirect(self.request.path)


class AddJournalHandler(BaseHandler):
    kind = 'journal'

    def get(self):
        self.render('addlookup.html',kind=self.kind)

    def post(self):
        name = self.get_argument('name')
        homepage = self.get_argument('homepage')

        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None

        self.store.action_add_lookup(user_id, self.kind, name, homepage)
        self.redirect(self.request.path)

def main():
    tornado.options.parse_config_file("sourcy.conf")
    tornado.options.parse_command_line()
    app = Application()
    app.listen(8888)
    logging.info("start.")
    tornado.ioloop.IOLoop.instance().start()


