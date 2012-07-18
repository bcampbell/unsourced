from base import BaseHandler
from unsourced.util import TornadoMultiDict
from unsourced.models import Comment,Action,Article

import tornado.auth

class PostCommentHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self,art_id):
        art = self.session.query(Article).get(art_id)
        if art is None:
            raise tornado.web.HTTPError(404, "Article not found")

        msg = self.get_argument("msg", None)
        if msg:
            # mark up and record any "@user" occurrances
            content,mentioned_users = Comment.extract_users(self.session, msg)

            print content, mentioned_users

            comment = Comment(author=self.current_user, article=art, content=content, mentioned_users=mentioned_users)

            self.session.add(comment)
            action = Action('comment', user=self.current_user, comment=comment, article=comment.article)
            self.session.add(action)
            self.session.commit()

        self.redirect("/art/%s" % (art_id,))

handlers = [
    (r"/art/([0-9]+)/postcomment", PostCommentHandler),
]

