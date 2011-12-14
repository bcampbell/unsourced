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
    
    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")

        sourcy_user = self.store.user_get_by_email(user['email'])
        if sourcy_user is None:
            user_id = self.store.user_create(user['email'],user['name']);
        else:
            user_id = sourcy_user.id
        self.set_secure_cookie("user", unicode(user_id))
        self.redirect(self.get_argument("next", "/"))



class LogoutHandler(BaseHandler):

    def get(self):
        self.clear_cookie("user")
        self.redirect("/")




handlers = [
    (r'/login', LoginHandler),
    (r'/login/google', GoogleLoginHandler),
    (r'/logout', LogoutHandler),
    (r"/user/([0-9]+)", UserHandler),
]

