import urlparse
from wtforms import Form, SelectField, HiddenField, BooleanField, TextField, PasswordField, validators

from sourcy.util import TornadoMultiDict,fix_url
from sourcy.models import SourceKind





class AddPaperForm(Form):
    url = TextField(u'Url (or <abbr title="Digital Object Identifier">DOI</abbr>)', [validators.required(),validators.URL()], filters=[fix_url])
    kind= HiddenField(default=SourceKind.PAPER)

class AddPRForm(Form):
    url = TextField(u'Url', [validators.required(),validators.URL()], filters=[fix_url])
    kind= HiddenField(default=SourceKind.PR)

class AddOtherForm(Form):
    url = TextField(u'Url', [validators.required(),validators.URL()], filters=[fix_url])
    kind= HiddenField(default=SourceKind.OTHER)

