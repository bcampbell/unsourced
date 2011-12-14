import tornado.auth

from base import BaseHandler



class UserHandler(BaseHandler):
    """show summary for a given day"""
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


class TwitterLoginHandler(BaseHandler, tornado.auth.TwitterMixin):
    @tornado.web.asynchronous
    def get(self):

        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return

        site = self.request.protocol + "://" + self.request.host
        self.authorize_redirect(callback_uri=site+"/login/twitter")

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




handlers = [
    (r'/login', LoginHandler),
    (r'/login/google', GoogleLoginHandler),
    (r'/login/twitter', TwitterLoginHandler),
    (r'/logout', LogoutHandler),
    (r"/user/([0-9]+)", UserHandler),
]

