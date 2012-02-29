from base import BaseHandler
from sourcy.util import TornadoMultiDict
from sourcy.models import Comment,Action,Article

import tornado.auth

class PostCommentHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self,art_id):
        art = self.session.query(Article).get(art_id)
        if art is None:
            raise tornado.web.HTTPError(404, "Article not found")

        msg = self.get_argument("msg", None)
        if msg:
            comment = Comment(author=self.current_user, article=art, content=msg)
            self.session.add(comment)
            action = Action('comment', user=self.current_user, comment=comment, article=comment.article)
            self.session.add(action)
            self.session.commit()

        self.redirect("/art/%s" % (art_id,))

handlers = [
    (r"/art/([0-9]+)/postcomment", PostCommentHandler),
]

