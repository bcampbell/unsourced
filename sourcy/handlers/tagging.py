import tornado.auth

from base import BaseHandler
from sourcy.models import Article,Tag,Action



class SetTagsHandler(BaseHandler):
    """ handler to set the tags on an article """
    @tornado.web.authenticated
    def post(self,article_id):
        article = self.session.query(Article).get(article_id)

        target_set = self.session.query(Tag).filter(Tag.name.in_(self.get_arguments('tags'))).all()
        removals = [t for t in article.tags if t not in target_set]
        additions = [t for t in target_set if t not in article.tags]


        article.tags = target_set

        for t in removals:
            self.session.add(Action('tag_remove', self.current_user, article=article, tag=t))
        for t in additions:
            self.session.add(Action('tag_add', self.current_user, article=article, tag=t))

        self.session.commit()
        self.redirect("/art/%s" % (article_id,))

class AddTagsHandler(BaseHandler):
    """ handler to add tags to an article """
    @tornado.web.authenticated
    def post(self,article_id):
        article = self.session.query(Article).get(article_id)

        additions = self.session.query(Tag).filter(Tag.name.in_(self.get_arguments('tags'))).all()

        article.tags += additions

        for t in additions:
            self.session.add(Action('tag_add', self.current_user, article=article, tag=t))

        self.session.commit()
        self.redirect("/art/%s" % (article_id,))


class AddTagHandler(BaseHandler):
    """ handler to add a tag on an article """
    @tornado.web.authenticated
    def post(self,article_id):
        article = self.session.query(Article).get(article_id)

        tag = self.session.query(Tag).filter(Tag.name==self.get_argument('tag')).first()
#        removals = [t for t in article.tags if t not in target_set]
#        additions = [t for t in target_set if t not in article.tags]

        article.tags.append(tag)
        self.session.add(Action('tag_add', self.current_user, article=article, tag=tag))

        self.session.commit()
        self.redirect("/art/%s" % (article_id,))

class DelTagHandler(BaseHandler):
    """ handler to remove a tag on an article """
    @tornado.web.authenticated
    def post(self,article_id):
        article = self.session.query(Article).get(article_id)

        tag = self.session.query(Tag).filter(Tag.name==self.get_argument('tag')).first()
        article.tags.remove(tag)
        self.session.add(Action('tag_remove', self.current_user, article=article, tag=tag))

        self.session.commit()
        self.redirect("/art/%s" % (article_id,))


handlers = [
    (r"/art/([0-9]+)/settags", SetTagsHandler),
    (r"/art/([0-9]+)/addtags", AddTagsHandler),
    (r"/art/([0-9]+)/addtag", AddTagHandler),
    (r"/art/([0-9]+)/deltag", DelTagHandler),
    ]

