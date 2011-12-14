from base import BaseHandler

from sourcy.forms import AddSourceForm


class AddSourceHandler(BaseHandler):
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



class ThanksHandler(BaseHandler):
    def get(self,action_id):
        action_id=int(action_id)
        action = self.store.action_get(action_id)
        self.render('thanks.html',action=action)


handlers = [
    (r"/addsource", AddSourceHandler),
    (r"/thanks/(\d+)", ThanksHandler),
    ]

