import itertools

import tornado.auth
import tornado.web
from tornado import httpclient
from wtforms import Form, SelectField, HiddenField, BooleanField, TextField, PasswordField, validators

from base import BaseHandler
from sourcy.util import TornadoMultiDict
from sourcy.models import Action,UserAccount
from sourcy.util import TornadoMultiDict




class UserHandler(BaseHandler):
    """show summary for a given user"""
    def get(self,user_id):
        user = self.session.query(UserAccount).get(user_id)
        if user is None:
            raise tornado.web.HTTPError(404, "User not found")

        actions = self.session.query(Action)\
            .filter(Action.user==user)\
            .order_by(Action.performed.desc())\
            .slice(0,100)\
            .all()
        self.render('user.html', user=user, actions=actions, groupby=itertools.groupby)



class EditProfileForm(Form):
    """ page for user to edit their profile """

    username     = TextField('Username', [validators.Length(min=1, max=25)])
    email        = TextField('Email Address', [validators.Email()])

    password = PasswordField(u'New Password', [
        validators.Optional(),
        validators.Length(min=5,message="Password must be at least %(min)d characters long")
    ], description="(Only if you want to set a new password)" )
    password_confirm = PasswordField(u'Confirm password', [
        validators.EqualTo('password', message='Passwords must match')]
    )


class EditProfileHandler(BaseHandler):
    """profile editing"""

    @tornado.web.authenticated
    def get(self):
        user=self.current_user
        form = EditProfileForm(obj=user)
        self.render('profile.html', user=user, form=form, msgs=[])

    @tornado.web.authenticated
    def post(self):
        user=self.current_user

        msgs = []

        form = EditProfileForm(TornadoMultiDict(self))
        if not form.validate():
            self.render('profile.html', user=user, form=form, msgs=msgs)
            return


        # update stuff.
        if form.password.data:
            user.set_password(form.password.data)

        user.username = form.username.data
        user.email = form.email.data

        msgs.append("Your account has been updated")

        self.session.commit()
        self.render('profile.html', user=user, form=form, msgs=msgs)



class LoginForm(Form):
    email = TextField(u'Email address', [
        validators.required(message="Please enter your email address"),
        validators.Email(message="Please enter a valid email address")
    ])
    password = PasswordField(u'Password', [validators.required(message="Password required"),] )
    remember_me = BooleanField(u'Remember me', description="don't use this on a shared computer!")
    next = HiddenField()


class LoginHandler(BaseHandler):
    def get(self):
        next = self.get_argument("next", None);
        form = LoginForm(TornadoMultiDict(self))
        if next is None:
            del form.next
        self.render('login.html', form=form)

    def post(self):

        next = self.get_argument("next", None);
        form = LoginForm(TornadoMultiDict(self))
        if next is None:
            del form.next
        if not form.validate():
            self.render('login.html', form=form)
            return

        # user exists?
        user = self.session.query(UserAccount).filter(UserAccount.email==form.email.data).first()
        # password ok?
        if not user.check_password(form.password.data):
            user = None


        if user is None:
            form.email.errors.append("Either your email address or password was not recognised. Please try again.")
            self.render('login.html', form=form)
            return

        # logged in successfully
        if next is None:
            next = '/'
        print "logged in:", user
        self.set_secure_cookie("user", unicode(user.id))
        self.redirect(next)








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
        user = self.session.query(UserAccount).filter_by(auth_supplier=auth_supplier,auth_uid=auth_uid).first()
        if user is None:
            # new user
            # TODO: should check for and handle username clashes!
            user = UserAccount(username=username, prettyname=prettyname, email=email, auth_supplier=auth_supplier, auth_uid=auth_uid, verified=True)
            self.session.add(user)
            self.session.commit()

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

        # map the twitter data to stuff we use
        email = u''
        prettyname = twit_user['name']
        auth_supplier = 'twitter'
        auth_uid = twit_user['username']
        username = twit_user['username']

        # TODO: the rest of this could be shared between handlers...
        user = self.session.query(UserAccount).filter_by(auth_supplier=auth_supplier,auth_uid=auth_uid).first()
        if user is None:
            # new user
            # TODO: should check for and handle username clashes!

            user = UserAccount(username, prettyname, email, auth_supplier, auth_uid, verified=True)
            self.session.add(user)
            self.session.commit()

        self.set_secure_cookie("user", unicode(user.id))
        self.redirect(self.get_argument("next", "/"))


class LogoutHandler(BaseHandler):

    def get(self):
        self.clear_cookie("user")
        self.redirect("/")







class RegisterForm(Form):
    email = TextField(u'Email address', [
        validators.required(message="Please enter your email address"),
        validators.Email(message="Please enter a valid email address")
    ])
    password = PasswordField(u'Password', [
        validators.required(message="Password required"),
        validators.Length(min=5,message="Password must be at least %(min)d characters long")
    ] )
    password_confirm = PasswordField(u'Confirm password', [
        validators.required(message="Password confirmation required"),
        validators.EqualTo('password', message='Passwords must match')]
    )
    # for passing on a redirection after registration/login is complete
    next = HiddenField()



def username_from_email(email):
    username = email.split("@")[0].lower()
    return username




class RegisterHandler(BaseHandler):
    def get(self):
        next = self.get_argument("next", None);
        form = RegisterForm(TornadoMultiDict(self))
        if next is None:
            del form.next
        self.render('register.html', form=form)

    def post(self):
        next = self.get_argument("next", None);
        form = RegisterForm(TornadoMultiDict(self))
        if next is None:
            del form.next

        if not form.validate():
            self.render('register.html', form=form)
            return

        # user might already exist - people _do_ forget.
        # outwardly, we don't want to reflect that an email address is
        # already registered, but we can send a different email.
        user = self.session.query(UserAccount).filter(UserAccount.email==form.email.data).first()
        if user is None:

            # ok - let's create the new user then!
            username = username_from_email(form.email.data)
            username = UserAccount.calc_unique_username(self.session, username)

            user = UserAccount( username=username,
                email=form.email.data,
                password=form.password.data,
                verified=False)
            self.session.add(user)
            self.session.commit()
            # TODO: send them a verification email

        else:
            # TODO: send them a reminder email
            pass

        self.render('register.html',form=None)


handlers = [
    (r'/login', LoginHandler),
    (r'/login/google', GoogleLoginHandler),
    (r'/login/twitter', TwitterLoginHandler),
    (r'/logout', LogoutHandler),
    (r"/user/([0-9]+)", UserHandler),
    (r"/editprofile", EditProfileHandler),
    (r'/register', RegisterHandler),
]

