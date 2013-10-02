import urllib
import json
import datetime

from wtforms import Form, TextField, validators, HiddenField, DateField
import tornado.web
import tornado.gen
from tornado import httpclient

from unsourced import util,analyser,highlight,scrape,config
from base import BaseHandler
from unsourced.models import Article,ArticleURL,Action
from unsourced.util import TornadoMultiDict, fix_url

from unsourced.forms import EnterArticleForm,SubmitArticleForm






class AddArticleHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        url = self.get_argument('url',None)
        if url is None:
            # blank url - prompt for one
            form = SubmitArticleForm()
            self.render("addarticle.html", form=form, notice='')
            return

        # basic validation
        form = SubmitArticleForm(TornadoMultiDict(self))
        if not form.validate():
            self.render("addarticle.html", form=form, notice='')
            return

        # article already in db?
        art = self.session.query(Article).join(ArticleURL).\
                filter(ArticleURL.url==url).first()
        print "ART: ",art

        if art is None:
            
            # nope. try scraping it.
            params = {'url': url}
            scrape_url = config.settings.scrapeomat + '/scrape?' + urllib.urlencode(params)
            http = tornado.httpclient.AsyncHTTPClient()

            response = yield tornado.gen.Task(http.fetch, scrape_url)


            try:
                art = scrape.process_scraped(url,response);
            except Exception as err:
                # uhoh... we weren't able to scrape it. If user wants article, they'll have to log
                # in and enter the details themselves...

                login_next_url = None
                enter_form = EnterArticleForm(url=url)
                if self.current_user is None:
                    params = {'url': url}
                    login_next_url = '/enterarticle?' + urllib.urlencode(params)
                notice = unicode(err)
                notice += " Please enter the details manually (or try again later)."
                self.render("enterarticle.html", form=enter_form, notice=notice, login_next_url=login_next_url)
                return

            # ok, add the new article to the db (with an action)
            user = self.current_user
            if user is None:
                user = self.get_anon_user()
            action = Action('art_add', user, article=art)
            self.session.add(art)
            self.session.add(action)
            self.session.commit()

        # all done
        self.redirect("/art/%d" % (art.id,))
        return


    def post(self):
        self.get()




class EnterArticleHandler(BaseHandler):
    """ allow user to manually enter article details (url, headline, date)

    Requires user to be logged in.
    """
    @tornado.web.authenticated
    def get(self):
        form = EnterArticleForm(TornadoMultiDict(self))
        self.render("enterarticle.html", form=form, notice=None)

    @tornado.web.authenticated
    def post(self):
        form = EnterArticleForm(TornadoMultiDict(self))
        if not form.validate():
            self.render("enterarticle.html", form=form, notice=None)
            return

        # done - add the article to the db
        url = form.url.data
        title = form.title.data
        pubdate = form.pubdate.data

        url_objs = [ArticleURL(url=url),]
        art = Article(title,url, pubdate, url_objs)
        action = Action('art_add', self.current_user, article=art)
        self.session.add(art)
        self.session.add(action)
        self.session.commit()

        # all done. phew.
        self.redirect("/art/%d" % (art.id,))





handlers = [
    (r"/addarticle", AddArticleHandler),
    (r"/enterarticle", EnterArticleHandler),
]

