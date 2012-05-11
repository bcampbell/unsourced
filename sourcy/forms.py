import urlparse
from wtforms import Form, SelectField, HiddenField, BooleanField, TextField, PasswordField, validators

from sourcy.util import TornadoMultiDict
from sourcy.models import SourceKind



def fix_url(url):
    if url is None:
        return url
    o = urlparse.urlparse(url)
    if not o[0]:
        url = 'http://' + url
    return url



class AddPaperForm(Form):
    url = TextField(u'Url (or <abbr title="Digital Object Identifier">DOI</abbr>)', [validators.required(),validators.URL()], filters=[fix_url])
    kind= HiddenField(default=SourceKind.PAPER)

class AddPRForm(Form):
    url = TextField(u'Url', [validators.required(),validators.URL()], filters=[fix_url])
    kind= HiddenField(default=SourceKind.PR)

class AddOtherForm(Form):
    url = TextField(u'Url', [validators.required(),validators.URL()], filters=[fix_url])
    kind= HiddenField(default=SourceKind.OTHER)

