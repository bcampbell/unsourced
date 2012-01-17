#import functools
#import urlparse

import tornado.auth

from base import BaseHandler
from sourcy.util import TornadoMultiDict
from sourcy.forms import AddTagForm
from sourcy.models import Article,Tag,Action


class AddTagHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self,article_id):
        article = self.session.query(Article).get(article_id)
        form = AddTagForm(TornadoMultiDict(self))
        self.render('add_tag.html', art=article, form=form)

    @tornado.web.authenticated
    def post(self,article_id):
        article = self.session.query(Article).get(article_id)
        form = AddTagForm(TornadoMultiDict(self))
        if form.validate():
            tag_name = form.tag.data
            if tag_name in [t.name for t in article.tags]:
                # already got it!
                self.redirect("/art/%s" % (article_id,))
                return


            tag = Tag(article,tag_name)
            action = Action('tag_add', self.current_user, article=article, tag=tag)
            self.session.add(tag)
            self.session.add(action)
            self.session.commit()

            self.redirect("/art/%s" % (article_id,))
        else:
            self.render('add_tag.html', art=article, form=form)



handlers = [
    (r"/art/([0-9]+)/addtag", AddTagHandler),
    ]

