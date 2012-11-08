
import tornado.auth
from wtforms import Form, SelectField, HiddenField, BooleanField, TextField, PasswordField, FileField, validators

from base import BaseHandler
from unsourced.models import Article,ArticleLabel,Label,Action
from unsourced.util import TornadoMultiDict





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

 
handlers = [
    (r"/art/([0-9]+)/addlabel", AddLabelHandler),
    (r"/art/([0-9]+)/removelabel/([_a-z]+)", RemoveLabelHandler),
    ]

