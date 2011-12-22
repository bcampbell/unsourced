import functools
import urlparse

import tornado.auth
from wtforms import Form, BooleanField, TextField, validators

from base import BaseHandler
from util import TornadoMultiDict
from sourcy.forms import AddSourceForm



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
            action_id = self.store.action_add_source(user_id, art_id, form.vars['url'],form.vars['kind'])

            self.redirect("/thanks/%d" % (action_id,))
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
        action_id=int(action_id)
        action = self.store.action_get(action_id)

        access_token = self.store.user_get_twitter_access_token(self.current_user)

        if access_token is not None:
            msg = build_action_message(self.request.protocol + "://" + self.request.host, action)
            form = TweetForm(message=msg)
        else:
            form = None
        self.render('thanks.html',action=action, form=form)



class TweetHandler(BaseHandler, tornado.auth.TwitterMixin):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def get(self, action_id):
        action_id=int(action_id)
        action = self.store.action_get(action_id)

        # already have access token?
        access_token = self.store.user_get_twitter_access_token(self.current_user)
        if access_token is None:
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
        access_token = twit_user["access_token"]

        # store access_token with the user
        self.store.user_set_twitter_access_token(self.current_user, access_token)
        self.redirect(self.request.uri)


    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self, action_id):
        action_id=int(action_id)
        action = self.store.action_get(action_id)

        access_token = self.store.user_get_twitter_access_token(self.current_user)
        if access_token is None:
            raise tornado.web.HTTPError(500, "Unexpected lack of Twitter authorisation")

        form = TweetForm(TornadoMultiDict(self))
        if form.validate():
            message = form.message.data
            self.twitter_request(
                "/statuses/update",
                post_args={"status": message},
                access_token=access_token,
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


class UpvoteHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self,source_id):
        source = self.store.source_get(source_id)

        self.store.action_upvote_source(self.current_user, source)

        self.redirect("/art/%s" % (source.article_id,))


class DownvoteHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self,source_id):
        source = self.store.source_get(source_id)

        self.store.action_downvote_source(self.current_user, source)

        self.redirect("/art/%s" % (source.article_id,))



handlers = [
    (r"/addsource", AddSourceHandler),
    (r"/thanks/(\d+)", ThanksHandler),
    (r"/thanks/(\d+)/tweet", TweetHandler),
    (r"/source/(\d+)/upvote", UpvoteHandler),
    (r"/source/(\d+)/downvote", DownvoteHandler),
    ]

