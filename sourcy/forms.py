import urlparse
from sourcy.util import TornadoMultiDict
from wtforms import Form, SelectField, HiddenField, BooleanField, TextField, PasswordField, validators




def fix_url(url):
    if url is None:
        return url
    o = urlparse.urlparse(url)
    if not o[0]:
        url = 'http://' + url
    return url



class AddPaperForm(Form):
    url = TextField(u'Url (or <abbr title="Digital Object Identifier">DOI</abbr>)', [validators.required(),validators.URL()], filters=[fix_url])
    kind= HiddenField(default='paper')  # TODO: use SourceKind def

