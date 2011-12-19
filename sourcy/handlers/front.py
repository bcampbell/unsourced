import datetime
from base import BaseHandler
import tornado.auth


from pprint import pprint

class MainHandler(BaseHandler):
    def get(self):

        days = []
        date = datetime.date.today()
        arts = self.store.art_get_by_date(date)
        days.append((date,arts))
#        date = date - datetime.timedelta(days=1)

        recent = self.store.action_get_recent(10)

        self.render('index.html', days=days, recent_actions=recent)




class AboutHandler(BaseHandler):
    def get(self):
        self.render('about.html')

class AcademicPapersHandler(BaseHandler):
    def get(self):
        self.render('academicpapers.html')



class AddInstitutionHandler(BaseHandler):
    kind = 'institution'

    def get(self):
        self.render('addlookup.html',kind=self.kind)

    def post(self):
        name = self.get_argument('name')
        homepage = self.get_argument('homepage')

        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None
        self.store.action_add_lookup(user_id, self.kind, name, homepage)
        self.redirect(self.request.path)


class AddJournalHandler(BaseHandler):
    kind = 'journal'

    def get(self):
        self.render('addlookup.html',kind=self.kind)

    def post(self):
        name = self.get_argument('name')
        homepage = self.get_argument('homepage')

        if self.current_user is not None:
            user_id = self.current_user.id
        else:
            user_id = None

        self.store.action_add_lookup(user_id, self.kind, name, homepage)
        self.redirect(self.request.path)


class TweetTestHandler(BaseHandler, tornado.auth.TwitterMixin):
    @tornado.web.asynchronous
    def get(self):

        # already logged in and have access token?
        if self.current_user is not None:
            access_token = self.store.user_get_twitter_access_token(self.current_user)
            if access_token is not None:
                self.send_it(access_token)
                return

        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return

        self.authorize_redirect("/tweet")

    def _on_auth(self, twit_user):
        if not twit_user:
            raise tornado.web.HTTPError(500, "Twitter auth failed")
        access_token = twit_user["access_token"]
        if self.current_user is not None:
            # if we're logged in, store access_token
            self.store.user_set_twitter_access_token(self.current_user, access_token)
        self.send_it(access_token)


    def send_it(self,access_token):
        self.twitter_request(
            "/statuses/update",
            post_args={"status": "Testing testing..."},
            access_token=access_token,
            callback=self.async_callback(self._on_post))

    def _on_post(self, new_entry):
        if not new_entry:
            # Call failed; perhaps missing permission?
            self.authorize_redirect("/tweet")
            return
        self.finish("Posted a message!")





handlers = [
    (r'/', MainHandler),
    (r'/about', AboutHandler),
    (r'/tweet', TweetTestHandler),
    (r'/academicpapers', AcademicPapersHandler),
    (r"/addjournal", AddJournalHandler),
    (r"/addinstitution", AddInstitutionHandler),
    ]
