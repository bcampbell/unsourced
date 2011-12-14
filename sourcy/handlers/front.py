import datetime
from base import BaseHandler

from sourcy.forms import AddSourceForm

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



class AddSourceHandler(BaseHandler):
    def post(self):
        form = AddSourceForm(self,None)

        if form.is_valid():

            if self.current_user is not None:
                user_id = self.current_user.id
            else:
                user_id = None
            art_id = form.vars['art_id']
            self.store.action_add_source(user_id, art_id, form.vars['url'],form.vars['kind'])

            self.redirect("/art/%d" % (art_id,))
        else:
            self.render('add_source.html',add_source_form=form)


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



handlers = [
    (r'/', MainHandler),
    (r'/about', AboutHandler),
    (r'/academicpapers', AcademicPapersHandler),
    (r"/addsource", AddSourceHandler),
    (r"/addjournal", AddJournalHandler),
    (r"/addinstitution", AddInstitutionHandler),
    ]
