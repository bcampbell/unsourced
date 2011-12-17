import tornado.auth
from tornado import httpclient

from base import BaseHandler







class UserHandler(BaseHandler):
    """show summary for a given user"""
    def get(self,user_id):
        user = self.store.user_get(user_id)

        actions = self.store.action_get_recent(100,user_id=user.id)
        self.render('user.html', user=user, actions=actions)


class LoginHandler(BaseHandler):
    def get(self):
        next = self.get_argument("next", None);
        self.render('login.html', next=next)



class GoogleLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()
    
    def _on_auth(self, google_user):
        if not google_user:
            raise tornado.web.HTTPError(500, "Google auth failed")

        # map the google data to stuff we use
        email = google_user['email']
        prettyname = google_user['name']
        auth_supplier = 'google'
        auth_uid = email
        username = google_user["email"].split("@")[0].replace(".", "_").lower()

        # TODO: the rest of this could be shared between handlers...
        user = self.store.user_get_by_auth_uid(auth_supplier,auth_uid)
        if user is None:
            # new user
            # TODO: should check for and handle username clashes!
            id = self.store.user_create(username, prettyname, email, auth_supplier, auth_uid)
            user = self.store.user_get(id)

        self.set_secure_cookie("user", unicode(user.id))
        self.redirect(self.get_argument("next", "/"))


class MyTwitterMixin(tornado.auth.TwitterMixin):
    """ hacked authenticate_redirect() to pass in callback uri """

    def authenticate_redirect(self, callback_uri=None):
        """Just like authorize_redirect(), but auto-redirects if authorized.

        This is generally the right interface to use if you are using
        Twitter for single-sign on.
        """
        http = httpclient.AsyncHTTPClient()
        http.fetch(self._oauth_request_token_url(callback_uri=callback_uri), self.async_callback(
            self._on_request_token, self._OAUTH_AUTHENTICATE_URL, None))

class TwitterLoginHandler(BaseHandler, MyTwitterMixin):
    @tornado.web.asynchronous
    def get(self):

        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return

        site = self.request.protocol + "://" + self.request.host
#        self.authorize_redirect(callback_uri=site+"/login/twitter")
        self.authenticate_redirect("/login/twitter")


    def _on_auth(self, twit_user):
        if not twit_user:
            raise tornado.web.HTTPError(500, "Twitter auth failed")

        user = self.store.user_get_by_auth_uid('twitter',twit_user['username'])
        if user is None:
            # new user
            username = twit_user['username']
            prettyname = twit_user['name']
            email = u''
            id = self.store.user_create(username, prettyname, email, 'twitter', twit_user['username'])
            user = self.store.user_get(id)

        self.set_secure_cookie("user", unicode(user.id))
        self.redirect(self.get_argument("next", "/"))


class LogoutHandler(BaseHandler):

    def get(self):
        self.clear_cookie("user")
        self.redirect("/")




# adaptor by James Crasta on WTForms mailing list
class TornadoMultiDict(object):
    def __init__(self, handler):
        self.handler = handler

    def __iter__(self):
        return iter(self.handler.request.arguments)

    def __len__(self):
        return len(self.handler.request.arguments)

    def __contains__(self, name):
        # We use request.arguments because get_arguments always returns a
        # value regardless of the existence of the key.
        return (name in self.handler.request.arguments)

    def getlist(self, name):
        # get_arguments by default strips whitespace from the input data,
        # so we pass strip=False to stop that in case we need to validate
        # on whitespace.
        return self.handler.get_arguments(name, strip=False)


from wtforms import Form, BooleanField, TextField, validators

class ProfileForm(Form):
    username     = TextField('Username', [validators.Length(min=4, max=25)])
    email        = TextField('Email Address', [validators.Length(min=6, max=35),validators.Email()])
    accept_rules = BooleanField('I accept the site rules', [validators.Required()])



class ProfileHandler(BaseHandler):
    """profile editing"""

    @tornado.web.authenticated
    def get(self):
        user=self.current_user
#        user = self.store.user_get(user.id)

        form = ProfileForm()
        form.validate()
        self.render('profile.html', user=user, form=form)

    @tornado.web.authenticated
    def post(self):
        user=self.current_user

        form = ProfileForm(TornadoMultiDict(self),user)
        form.validate()
        self.render('profile.html', user=user, form=form)

handlers = [
    (r'/login', LoginHandler),
    (r'/login/google', GoogleLoginHandler),
    (r'/login/twitter', TwitterLoginHandler),
    (r'/logout', LogoutHandler),
    (r"/user/([0-9]+)", UserHandler),
    (r"/profile", ProfileHandler),
]

