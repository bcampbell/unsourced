#import functools
#import urlparse

import tornado.auth

from base import BaseHandler
from sourcy.util import TornadoMultiDict
from sourcy.forms import AddTagForm



class AddTagHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self,article_id):
        article = self.store.art_get(article_id)
        form = AddTagForm(TornadoMultiDict(self))
        self.render('add_tag.html', art=article, form=form)

    @tornado.web.authenticated
    def post(self,article_id):
        article = self.store.art_get(article_id)
        form = AddTagForm(TornadoMultiDict(self))
        if form.validate():
            action_id = self.store.action_add_tag(self.current_user, article, form.tag.data)

            self.redirect("/art/%s" % (article_id,))
        else:
            self.render('add_tag.html', art=article, form=form)



handlers = [
    (r"/art/([0-9]+)/addtag", AddTagHandler),
    ]

