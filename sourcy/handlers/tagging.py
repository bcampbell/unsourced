#import functools
#import urlparse

import tornado.auth
from sqlalchemy.sql import func

from base import BaseHandler
from sourcy.util import TornadoMultiDict
from sourcy.forms import AddTagForm
from sourcy.models import Article,Tag,Action


class SetTagsHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self,article_id):
        article = self.session.query(Article).get(article_id)

        target_set = self.session.query(Tag).filter(Tag.name.in_(self.get_arguments('tags'))).all()
        removals = [t for t in article.tags if t not in target_set]
        additions = [t for t in target_set if t not in article.tags]


        article.tags = target_set

        # TODO: create actions
        self.session.commit()
        self.redirect("/art/%s" % (article_id,))



handlers = [
    (r"/art/([0-9]+)/settags", SetTagsHandler),
    ]

