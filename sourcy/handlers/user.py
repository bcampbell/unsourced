import itertools

import StringIO
from PIL import Image
import os
import logging

import tornado.auth
import tornado.web
from tornado import httpclient
from wtforms import Form, SelectField, HiddenField, BooleanField, TextField, PasswordField, FileField, validators
from sqlalchemy.orm import subqueryload


from base import BaseHandler
from sourcy.util import TornadoMultiDict
from sourcy.models import Action,UserAccount,UploadedFile,Token,comment_user_map
from sourcy.util import TornadoMultiDict
from sourcy.cache import cache
from sourcy.config import settings
from sourcy import mailer

class UserHandler(BaseHandler):
    """show summary for a given user"""
    def get(self,user_id):
        user = self.session.query(UserAccount).get(user_id)
        if user is None:
            raise tornado.web.HTTPError(404, "User not found")

        actions = self.session.query(Action)\
            .filter(Action.user==user)\
            .order_by(Action.performed.desc())\
            .slice(0,10)\
            .all()


        subq = self.session.query(comment_user_map.c.comment_id).\
            filter(comment_user_map.c.useraccount_id==user.id).\
            subquery()

        mentions = self.session.query(Action).\
            options(subqueryload(Action.comment,Action.article,Action.user)).\
            filter(Action.what=='comment').\
            filter(Action.comment_id.in_(subq)).\
            order_by(Action.performed.desc()).\
            slice(0,10).\
            all()


        self.render('user.html', user=user, actions=actions, mentions=mentions )






class EditProfileForm(Form):
    """ page for user to edit their profile """

    username     = TextField('Username', [
        validators.Required(),
        validators.Length(min=3, message=u"Username must be at lease %(min)d characters long"),
        validators.Length(max=25, message=u"Username too long - maximum %(max)d characters"),
        validators.Regexp(UserAccount.USERNAME_PAT, message=u"Alphanumerics only, please")])
    email        = TextField('Email Address', [validators.Optional(), validators.Email()])

    password = PasswordField(u'New Password', [
        validators.Optional(),
        validators.Length(min=5,message="Password must be at least %(min)d characters long")
    ], description="(Only if you want to set a new password)" )
    password_confirm = PasswordField(u'Confirm password', [
        validators.EqualTo('password', message='Passwords must match')]
    )
    photo = FileField(u'Upload a profile photo')





class EditProfileHandler(BaseHandler):
    """profile editing"""

    @tornado.web.authenticated
    def get(self):
        user=self.current_user
        form = EditProfileForm(obj=user)
        self.render('profile.html', user=user, form=form )

    @tornado.web.authenticated
    def post(self):
        user=self.current_user

        form = EditProfileForm(TornadoMultiDict(self))
        if not form.validate():
            self.render('profile.html', user=user, form=form)
            return

        # username already taken?
        foo = self.session.query(UserAccount.id).filter(UserAccount.username==form.username.data).first()
        if foo is not None and foo.id != user.id:
            form.username.errors.append("username already in use. Please pick another.")
            self.render('profile.html', user=user, form=form)
            return

        # update stuff.
        if form.password.data:
            user.set_password(form.password.data)

        user.username = form.username.data
        user.email = form.email.data

        # any photo uploaded?
        uploaded_photos = self.request.files.get('photo',[])
        photo = None
        if len(uploaded_photos)>0:
            photo = UploadedFile.create(uploaded_photos[0], creator=user)
            self.session.add(photo)

            old_photo = user.photo
            user.photo = photo
            if old_photo:
                self.session.delete(old_photo)


        self.session.commit()
        self.redirect('/user/%d' % (user.id,))



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
        if user is not None:
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
        username = google_user["email"].split("@")[0].replace(".", "_")

        # TODO: the rest of this could be shared between handlers...
        user = self.session.query(UserAccount).filter_by(auth_supplier=auth_supplier,auth_uid=auth_uid).first()
        if user is None:
            # new user
            username = UserAccount.calc_unique_username(self.session, username)
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
            username = UserAccount.calc_unique_username(self.session, username)
            user = UserAccount(username=username, prettyname=prettyname, email=email, auth_supplier=auth_supplier, auth_uid=auth_uid, verified=True)
            self.session.add(user)
            self.session.commit()

        self.set_secure_cookie("user", unicode(user.id))
        self.redirect(self.get_argument("next", "/"))


class LogoutHandler(BaseHandler):

    def get(self):
        self.clear_cookie("user")
        self.redirect("/")





class ForgotForm(Form):
    email = TextField(u'Email address', [
        validators.required(message="Please enter your email address"),
        validators.Email(message="Please enter a valid email address")
    ])


class ForgotHandler(BaseHandler):
    def get(self):
        form = ForgotForm(TornadoMultiDict(self))
        self.render('forgot.html', form=form)

    def post(self):
        form = ForgotForm(TornadoMultiDict(self))
        if not form.validate():
            self.render('forgot.html', form=form)
            return

        user = self.session.query(UserAccount).filter(UserAccount.email==form.email.data).first()
        # don't leak existence of email addresses.
        if user is not None:
            token = Token.create_login(user.id)
            email_template = 'email/forgotten_password.txt'
            email_subject = "%s - forgotten details" % settings.site_name

            self.session.add(token)
            self.session.commit()

            confirmation_url = "%s/t/%s" % (settings.root_url,token.name)
            email_body = self.render_string(email_template,
                confirmation_url=confirmation_url)

            if settings.bypass_email:
                self.render('token_sent.html',
                    bypass_email=settings.bypass_email,
                confirmation_url=confirmation_url,
                email_subject=email_subject,
                email_body=email_body)
            else:
                # send it
                mailer.send_email(addr_from=settings.site_email,
                    addr_to=form.email.data,
                    subject=email_subject,
                    content=email_body)

        # redirect to avoid multiple emails due to refresh clicking!
        self.redirect('/emailsent')





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
            token = Token.create_registration(
                form.email.data,
                form.password.data)
            email_template = 'email/confirm_register.txt'
            email_subject = "%s - confirm your account" % settings.site_name
        else:
            token = Token.create_login(user.id)
            email_template = 'email/forgotten_password.txt'
            email_subject = "%s - forgotten password" % settings.site_name

        self.session.add(token)
        self.session.commit()

        confirmation_url = "%s/t/%s" % (settings.root_url,token.name)
        email_body = self.render_string(email_template,
            confirmation_url=confirmation_url)

        if settings.bypass_email:
            self.render('token_sent.html',
                bypass_email=settings.bypass_email,
                confirmation_url=confirmation_url,
                email_subject=email_subject,
                email_body=email_body)
        else:
            # send it
            mailer.send_email(addr_from=settings.site_email,
                addr_to=form.email.data,
                subject=email_subject,
                content=email_body)

            # redirect to avoid multiple emails due to refresh clicking!
            self.redirect('/emailsent')


class TokenSentHandler(BaseHandler):
    def get(self):
        self.render('token_sent.html',bypass_email=False)


class ThumbHandler(BaseHandler):
    """ serve up thumbnail versions of uploaded images """
    def get(self, size, filename):
        if size not in settings.thumb_sizes:
            raise tornado.web.HTTPError(404)
        w,h = settings.thumb_sizes[size]
        content_type, raw_data = self.thumbnail(str(filename),w,h)
        self.set_header("Content-Type", content_type)
        self.write(raw_data)

    @cache.cache_on_arguments()
    def thumbnail(self, filename, w, h):
        original = Image.open(os.path.join(settings.uploads_path,filename))
        thumb = original.convert()   # convert() rather than copy() - copy leaves palette intact, which makes for crumby thumbs
        thumb.thumbnail((w,h), Image.ANTIALIAS)

        buf= StringIO.StringIO()
        thumb.save(buf, format='PNG')
        return 'image/png',buf.getvalue()


handlers = [
    (r'/login', LoginHandler),
    (r'/login/forgot', ForgotHandler),
    (r'/login/google', GoogleLoginHandler),
    (r'/login/twitter', TwitterLoginHandler),
    (r'/logout', LogoutHandler),
    (r"/user/([0-9]+)", UserHandler),
    (r"/editprofile", EditProfileHandler),
    (r"/register", RegisterHandler),
    (r"/emailsent", TokenSentHandler),
    (r"/thumb/([a-z0-9]+)/([^!#?&]+)", ThumbHandler),
]

