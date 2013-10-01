import urlparse
import re

from wtforms import Form, SelectField, HiddenField, BooleanField, TextField, PasswordField, DateField, validators

from util import TornadoMultiDict,fix_url
from models import SourceKind

doi_pat = re.compile(r'\s*(?:doi:\s*|http://dx.doi.org/|dx.doi.org/)?(10.(\d)+/([^(\s\>\"\<)])+)\s*', re.I)

def URL_or_DOI():
    """ validator - ensure either valid URL or DOI """

    url_validator = validators.URL()

    doi_validator = validators.Regexp(doi_pat)

    def _url_or_doi(form, field):
        try:
            url_validator(form,field)
            # if it's an OK url, don't need to check DOIness :-)
        except validators.ValidationError:
            # not a url. is it a DOI?
            try:
                doi_validator(form,field)
                return  # yay!
            except validators.ValidationError:
                raise validators.ValidationError("Please enter a valid URL or DOI")

    return _url_or_doi



class AddPaperForm(Form):
    url = TextField(u'URL (or DOI)', [validators.required(), URL_or_DOI()])

    def get_as_doi(self):
        m = doi_pat.match(self.url.data)
        if m is not None:
            return m.group(1)
        else:
            return None
 






class AddPRForm(Form):
    url = TextField(u'Url', [validators.required(),validators.URL()], filters=[fix_url])

class AddOtherForm(Form):
    url = TextField(u'Url', [validators.required(),validators.URL()], filters=[fix_url])





class SubmitArticleForm(Form):
    url = TextField(u'Url of article', [validators.required(),validators.URL()], filters=[fix_url])


class EnterArticleForm(Form):
    """ form for manually entering the details of an article """
    url = TextField(u'Url of article', [validators.required(),validators.URL()], filters=[fix_url])
    title = TextField(u'Title', [validators.required()])
    pubdate = DateField(u'Date of publication', [validators.required(),] ,description='yyyy-mm-dd' )


