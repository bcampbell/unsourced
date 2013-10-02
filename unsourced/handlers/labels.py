import urllib

import tornado.auth
from wtforms import Form, SelectField, HiddenField, BooleanField, TextField, PasswordField, FileField, validators

from base import BaseHandler
from unsourced.models import Article,ArticleURL,ArticleLabel,Label,Action
from unsourced.util import TornadoMultiDict
from unsourced.forms import EnterArticleForm
from unsourced import config,scrape


class AddLabelHandler(BaseHandler):
    """ add a label to an article """

    @tornado.web.authenticated
    def post(self, art_id):
        art = self.session.query(Article).get(art_id)
        if art is None:
            raise tornado.web.HTTPError(404, "Article not found")

        label_id = self.get_argument('label')
        label = self.session.query(Label).get(label_id)
        if label is None:
            raise tornado.web.HTTPError(400) 

        if label in [l.label for l in art.labels]:
            self.redirect("/art/%s" % (art.id,))
            return

        artlabel = ArticleLabel(creator=self.current_user)
        artlabel.label = label
        artlabel.article = art
        art.labels.append(artlabel)

        self.session.add(Action('label_add', self.current_user, article=art, label=label))
        self.session.commit()

        self.redirect("/art/%s" % (art.id,))


class RemoveLabelHandler(BaseHandler):
    """ remove a label from an article """

    @tornado.web.authenticated
    def post(self, art_id, label_id):

        artlabel = self.session.query(ArticleLabel).\
            filter(ArticleLabel.article_id==art_id).\
            filter(ArticleLabel.label_id==label_id).\
            one()

        if artlabel is None:
            raise tornado.web.HTTPError(404, "Label not found")

        # let anyone zap a label
        #if artlabel.creator != self.current_user:
        #    raise tornado.web.HTTPError(403)

        art = artlabel.article
        label = artlabel.label

        art.labels.remove(artlabel)
        self.session.add(Action('label_remove', self.current_user, article=art, label=label))
        self.session.commit()
        self.redirect("/art/%s" % (art.id,))


class AddLabelByURLHandler(BaseHandler):

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        label_id = self.get_argument('label')
        url = self.get_argument('url')
        #reason = self.get_argument('reason')

        label = self.session.query(Label).get(label_id)
        if label is None:
            raise tornado.web.HTTPError(400) 

        # article already in db?
        art = self.session.query(Article).join(ArticleURL).\
                filter(ArticleURL.url==url).first()

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
                # BUG: the label details will be lost going through the manual entry process...

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

        # ok, now we can add the label!
        if label not in [l.label for l in art.labels]:

            artlabel = ArticleLabel(creator=self.current_user)
            artlabel.label = label
            artlabel.article = art
            art.labels.append(artlabel)

            self.session.add(Action('label_add', self.current_user, article=art, label=label))

        self.session.commit()

        # all done
        self.redirect("/art/%d" % (art.id,))
        return
 
handlers = [
    (r"/art/([0-9]+)/addlabel", AddLabelHandler),
    (r"/art/([0-9]+)/removelabel/([_a-z]+)", RemoveLabelHandler),
    (r"/addlabel", AddLabelByURLHandler),
    ]

