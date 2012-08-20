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
    url = TextField(u'Url of article', [validators.required(),validators.URL()], filters=[fix_url])
    prev_url = HiddenField(u'', [validators.required(),validators.URL()])
    title = TextField(u'Title', [validators.required()])
    pubdate = DateField(u'Date of publication', [validators.required(),] ,description='yyyy-mm-dd' )
    step = HiddenField(u'',default="confirm")


class AddArticleHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        form = SubmitArticleForm(TornadoMultiDict(self))
        self.render("addarticle.html", form=form, message='',step="submit")

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        # flow of this handler is a little... muddy. There are three steps:
        # 1) user submits URL
        # 2) show user automatically-scraped details (title, pubdate)
        #    user can fix 'em, then clicks to confirm
        # 3) we store article in database and jump to it

        step = self.get_argument('step','submit')

        if step=='confirm':
            form = EnterArticleForm(TornadoMultiDict(self))
            if not form.validate():
                self.render("addarticle.html", form=form, message='', step=step)
                return

            if form.url.data == form.prev_url.data:
                # done - add the article to the db

                url = form.url.data
                title = form.title.data
                pubdate = form.pubdate.data

                # TODO: should collect alternative URLs
                # (scrapomat caches, so would be quick enough to just rescrape)
                # and we need to make sure we set permalink to the canonical url,
                # rather than what user initially entered
                url_objs = [ArticleURL(url=url),]
                art = Article(title,url, pubdate, url_objs)
                action = Action('art_add', self.current_user, article=art)
                self.session.add(art)
                self.session.add(action)
                self.session.commit()

                # all done. phew.
                self.redirect("/art/%d" % (art.id,))
                return
            else:
                # url has changed - treat as a new submit
                step = 'submit'


        if step =='submit':
            # a raw url has been submitted - validate it
            form = SubmitArticleForm(TornadoMultiDict(self))
            if not form.validate():
                self.render("addarticle.html", form=form, message='', step=step)
                return

            url = form.url.data
            # already in database?
            art_url = self.session.query(ArticleURL).filter_by(url=url).first()
            if art_url is not None:
                # yep - jump to it and we're done.
                self.redirect("/art/%d" % (art_url.article.id,))
                return

            # need to scrape the article metadata to add it to database
            # TODO: don't need to scrape article text here...
            params = {'url': url}
            scrape_url = 'http://localhost:8889/scrape?' + urllib.urlencode(params)
            http = tornado.httpclient.AsyncHTTPClient()

            response = yield tornado.gen.Task(http.fetch, scrape_url)

            worked = True
            bad_url = False
            if response.error:
                worked = False
            else:
                results = json.loads(response.body)
                if results['status']!=0:
                    worked = False
                    if results['status'] in (1,2):   # net error, bad url
                        bad_url = True

            if not worked:
                if bad_url:
                    # start from scratch
                    form = SubmitArticleForm(TornadoMultiDict(self))
                    form.prev_url.data = form.url.data
                    form.step.data = "submit"
                    form.validate()
                    form.url.errors.append("Can't access this URL")
                    self.render("addarticle.html", form=form, message='', step=step)
                    return

                message = "Sorry, we couldn't read the details for the article. Please enter them manually."
                form = EnterArticleForm(TornadoMultiDict(self))
                form.prev_url.data = form.url.data
                form.step.data = "confirm"
                self.render("addarticle.html", form=form, message=message, step='confirm')
                return

            # fill out the details, get user to check 'em
            scraped_art = results['article']

            scraped_art['pubdate'] = datetime.datetime.fromtimestamp(scraped_art['pubdate'])
            form = EnterArticleForm(prev_url=url, url=url, title=scraped_art['headline'], pubdate=scraped_art['pubdate'] )
            message = "Have we got these details right? If not, please fix them before going on!"
            self.render("addarticle.html", form=form, message=message, step='confirm')
            return







handlers = [
    (r"/addarticle", AddArticleHandler),
]

