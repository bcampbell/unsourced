from sourcy.util import TornadoMultiDict
from wtforms import Form, SelectField, HiddenField, BooleanField, TextField, validators

TAG_CHOICES = [
    ('science','Science'),
    ('warn_wikipedia','Warning - Wikipedia'),
    ('warn_anon','Warning - Based on anonymous tipoff'),
    ('warn_soft','Warning - Soft interview'),
    ('warn_churn','Warning - Article is churn'),
    ('warn_pr','Warning - survey/stats sponsored by PR company'),
]


class AddTagForm(Form):

    tag = SelectField(u'Tag', choices=TAG_CHOICES)




# TODO: kill and replace with wtforms version...
class AddSourceForm:
    def __init__(self, handler, art_id=None):
        self.handler = handler
        self.errs = {}
        vars = {}
        if handler.request.method=='POST':
            vars['art_id'] = int(handler.get_argument('art_id'))
        else:
            vars['art_id'] = int(art_id)
        vars['url'] = handler.get_argument('url',u'')
        vars['kind'] = handler.get_argument('kind',u'')
        self.vars = vars

        if handler.request.method=='POST':
            if not vars['url'].startswith('http'):
                self.errs['url'] = 'Invalid url'


    def render_string(self, path, **kwargs):
        """Renders a template and returns it as a string."""
        return self.handler.render_string(path, **kwargs)

    def render(self):
        return self.render_string('modules/add_source_form.html', vars=self.vars,errs=self.errs)

    def is_valid(self):
        return False if self.errs else True

