import functools
import urlparse
from pprint import pprint
import json

import tornado.auth
from wtforms import Form, BooleanField, TextField, validators

from sqlalchemy.sql import func


from base import BaseHandler
from sourcy.util import TornadoMultiDict
from sourcy.forms import AddSourceForm
from sourcy.models import Source,Action,Article,TwitterAccessToken


class AddSourceHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        form = AddSourceForm(self,None)

        if form.is_valid():

            if self.current_user is not None:
                user_id = self.current_user.id
            else:
                user_id = None
            art_id = form.vars['art_id']

            art = self.session.query(Article).get(art_id)
            assert art is not None

            src = Source(article=art,
                url=form.vars['url'],
                kind=form.vars['kind'])
            action = Action('src_add', self.current_user,
                article=art,
                source=src)
            self.session.add(src)
            self.session.add(action)
            self.session.commit()

            self.redirect("/thanks/%d" % (action.id,))
        else:
            self.render('add_source.html',add_source_form=form)


class TweetForm(Form):
    message = TextField('Message', [validators.Length(min=4, max=140)])



def build_action_message(site_root,action):
    """ build a default tweet message describing an action """
    if action.what=='src_add':
        what = u"Added a source"
    else:
        what = u"Did something"

    if action.article is not None:
        full_art_url = urlparse.urljoin(site_root, "/art/" + str(action.article.id))
        return u"%s to %s" % (what,full_art_url)
    else:
        return u"%s on %s" % (what,site_root)



class ThanksHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self,action_id):
        action = self.session.query(Action).get(action_id)
        assert action is not None

        tok = self.session.query(TwitterAccessToken).filter_by(user=self.current_user).first()

        if tok is not None:
            msg = build_action_message(self.request.protocol + "://" + self.request.host, action)
            form = TweetForm(message=msg)
        else:
            form = None
        self.render('thanks.html',action=action, form=form)



class TweetHandler(BaseHandler, tornado.auth.TwitterMixin):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def get(self, action_id):
        action = self.session.query(Action).get(action_id)
        assert action is not None

        # already have access token?
        tok = self.session.query(TwitterAccessToken).filter_by(user=self.current_user).first()
        if tok is None:
            if self.get_argument("oauth_token", None):
                self.get_authenticated_user(functools.partial(self._on_auth, action=action))
            else:
                self.authorize_redirect(self.request.uri)
            return

        # OK, we're all set up for tweeting!

        msg = build_action_message(self.request.protocol + "://" + self.request.host, action)
        form = TweetForm(message=msg)
        self.render('tweet.html',action=action, form=form)




    def _on_auth(self, twit_user,action):
        if not twit_user:
            raise tornado.web.HTTPError(500, "Twitter auth failed")

        # store access_token with the user
        self.session.query(TwitterAccessToken).filter_by(user=self.current_user).delete()
        tok = TwitterAccessToken(user=self.current_user, token=json.dumps(twit_user['access_token']))
        self.session.add(tok)
        pprint(tok)
        self.session.commit()

        self.redirect(self.request.uri)


    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self, action_id):
        action = self.session.query(Action).get(action_id)
        assert action is not None

        tok = self.session.query(TwitterAccessToken).filter_by(user=self.current_user).first()
        if tok is None:
            raise tornado.web.HTTPError(500, "Unexpected lack of Twitter authorisation")

        form = TweetForm(TornadoMultiDict(self))
        if form.validate():
            message = form.message.data
            self.twitter_request(
                "/statuses/update",
                post_args={"status": message},
                access_token=json.loads(tok.token),
                callback=functools.partial(self._on_post,action=action))
            return
        else:
            self.render('tweet.html',action=action, form=form)



    def _on_post(self, new_entry, action):
        """ tweet completed """
        if not new_entry:
            # Call failed; perhaps access_token expired?
            # TODO: does tornado provide any more information about what when wrong?
            raise tornado.web.HTTPError(500, "Tweet failed")

        if action.what == 'src_add':
            self.redirect("/art/" + str(action.article.id));
        else:
            self.redirect("/");


class SrcVoteHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self,source_id):
        source = self.session.query(Source).get(source_id)
        assert source is not None

        prev = self.session.query(Action).filter_by(what='src_vote',source=source,who=self.current_user).first()
        if prev:
            self.session.delete(prev)
        else:
            # perform the vote
            vote = Action('src_vote',who=self.current_user, value=self.VALUE, source=source, article=source.article)
            self.session.add(vote)

        # update the score on the source
        source.score = self.session.query(func.sum(Action.value)).filter((Action.what=='src_vote') & (Action.source==source)).scalar()

        self.session.commit()

        self.redirect("/art/%s" % (source.article.id,))


class UpvoteHandler(SrcVoteHandler):
    VALUE = 1

class DownvoteHandler(SrcVoteHandler):
    VALUE = -1


handlers = [
    (r"/addsource", AddSourceHandler),
    (r"/thanks/(\d+)", ThanksHandler),
    (r"/thanks/(\d+)/tweet", TweetHandler),
    (r"/source/(\d+)/upvote", UpvoteHandler),
    (r"/source/(\d+)/downvote", DownvoteHandler),
    ]

