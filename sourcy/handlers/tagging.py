#import functools
#import urlparse

import tornado.auth
from sqlalchemy.sql import func

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


class TagVoteHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self,tag_id):
        tag = self.session.query(Tag).get(tag_id)
        assert tag is not None

        prev = self.session.query(Action).filter_by(what='tag_vote',tag=tag,user=self.current_user).first()
        if prev:
            self.session.delete(prev)
        else:
            # perform the vote
            vote = Action('tag_vote',user=self.current_user, value=self.VALUE, tag=tag, article=tag.article)
            self.session.add(vote)

        # update the score on the tag
        tag.score = self.session.query(func.sum(Action.value)).filter((Action.what=='tag_vote') & (Action.tag==tag)).scalar()

        self.session.commit()

        self.redirect("/art/%s" % (tag.article.id,))


class UpvoteHandler(TagVoteHandler):
    VALUE = 1

class DownvoteHandler(TagVoteHandler):
    VALUE = -1


handlers = [
    (r"/art/([0-9]+)/addtag", AddTagHandler),
    (r"/tag/(\d+)/upvote", UpvoteHandler),
    (r"/tag/(\d+)/downvote", DownvoteHandler),
    ]

