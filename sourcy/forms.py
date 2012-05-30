import urlparse
from wtforms import Form, SelectField, HiddenField, BooleanField, TextField, PasswordField, validators

from sourcy.util import TornadoMultiDict,fix_url
from sourcy.models import SourceKind





class AddPaperForm(Form):
    # TODO: allow DOI instead of url when adding papers
    url = TextField(u'Url', [validators.required(),validators.URL()], filters=[fix_url])

class AddPRForm(Form):
    url = TextField(u'Url', [validators.required(),validators.URL()], filters=[fix_url])

class AddOtherForm(Form):
    url = TextField(u'Url', [validators.required(),validators.URL()], filters=[fix_url])

