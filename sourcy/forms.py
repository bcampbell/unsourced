import urlparse
from sourcy.util import TornadoMultiDict
from wtforms import Form, SelectField, HiddenField, BooleanField, TextField, validators




def fix_url(url):
    if url is None:
        return url
    o = urlparse.urlparse(url)
    if not o[0]:
        url = 'http://' + url
    return url


class AddSourceForm(Form):
    KIND_CHOICES = [
        ('pr','Press release'),
        ('paper','Academic paper'),
        ('other','Other')]
    kind = SelectField(u'Kind', choices=KIND_CHOICES)
    url = TextField(u'Url', [validators.required(),validators.URL()], filters=[fix_url])



