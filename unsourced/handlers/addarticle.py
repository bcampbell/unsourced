import urllib
import collections
import json
import datetime

from wtforms import Form, TextField, validators, HiddenField, DateField
import tornado.web
import tornado.gen
from tornado import httpclient

from unsourced import util,analyser,highlight
from base import BaseHandler
from unsourced.models import Article,ArticleURL,Action
from unsourced.util import TornadoMultiDict, fix_url



class SubmitArticleForm(Form):
    url = TextField(u'Url of article', [validators.required(),validators.URL()], filters=[fix_url])



class EnterArticleForm(Form):
    """ form for manually entering the details of an article """
    url = TextField(u'Url of article', [validators.required(),validators.URL()], filters=[fix_url])
    title = TextField(u'Title', [validators.required()])
    pubdate = DateField(u'Date of publication', [validators.required(),] ,description='yyyy-mm-dd' )




class Status:
    """ status codes returned by scrapomat """
    SUCCESS = 0
    NET_ERROR = 1
    BAD_REQ = 2
    PAYWALLED = 3
    PARSE_ERROR = 4



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

        # already in database?
        art_url = self.session.query(ArticleURL).filter_by(url=url).first()
        if art_url is not None:
            # yep - jump to it and we're done.
            self.redirect("/art/%d" % (art_url.article.id,))
            return

        # nope. try scraping it.
        params = {'url': url}
        scrape_url = 'http://localhost:8889/scrape?' + urllib.urlencode(params)
        http = tornado.httpclient.AsyncHTTPClient()

        response = yield tornado.gen.Task(http.fetch, scrape_url)

        scraped_art = None
        enter_form = EnterArticleForm(url=url)
        err_msg = None
        if response.error:
            # scrapomat down :-(
            err_msg = "Sorry, there was a problem. Please try again later."
        else:
            results = json.loads(response.body)
            if results['status'] == Status.SUCCESS:
                scraped_art = results['article']
                scraped_art['pubdate'] = datetime.datetime.fromtimestamp(scraped_art['pubdate'])
                # use entry form to validate everything's there
                enter_form.url.data = url
                enter_form.title.data = scraped_art['headline']
                enter_form.pubdate.data = scraped_art['pubdate']
                if not enter_form.validate():
                    scraped_art = None
                    err_msg = u"Sorry, we weren't able to automatically read all the details"
            else:
                error_messages = {
                    Status.PAYWALLED: u"Sorry, that article seems to be behind a paywall.",
                    Status.PARSE_ERROR: u"Sorry, we couldn't read the article",
                    Status.BAD_REQ: u"Sorry, that URL doesn't look like an article",
                    Status.NET_ERROR: u"Sorry, we couldn't read that article - is the URL correct?",
                }
                err_msg = error_messages.get(results['status'],"Unknown error")


        if scraped_art is None:
            # uhoh... we weren't able to scrape it. If user wants article, they'll have to log
            # in and enter the details themselves...

            login_next_url = None
            if self.current_user is None:
                params = {'url': url}
                login_next_url = '/enterarticle?' + urllib.urlencode(params)
            self.render("enterarticle.html", form=enter_form, notice=err_msg, login_next_url=login_next_url)
            return


        # if we've got this far, we now have all the details needed to load the article into the DB. Yay!
        url_objs = [ArticleURL(url=u) for u in scraped_art['urls']]
        art = Article(scraped_art['headline'],scraped_art['permalink'], scraped_art['pubdate'], url_objs)
        action = Action('art_add', self.current_user, article=art)
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

