import re
import HTMLParser
import datetime
from urlparse import urlparse, urlunparse
import lxml.html
from tornado.options import define, options


htmlparser = HTMLParser.HTMLParser()

def from_html(html):
    txt = html
    # html entities
    txt = htmlparser.unescape(txt)
    # comments
    txt = re.compile(r'<!--.*-->',re.DOTALL).sub('',txt)
    # tags
    txt = re.compile(r'<[^<]*?>',re.DOTALL).sub('',txt)
    # compress spaces
    txt = re.compile(r'\s{2,}',re.DOTALL).sub(' ',txt)
    return txt





def highlight(html,strings,cls):
    for s in strings:
        pat = re.compile(re.escape(s), re.IGNORECASE)
        html = pat.sub('<span class="%s">%s</span>' % (cls,s), html)
    return html


def domain(url):
    """ return domain of url, stripped of www. prefix """
    o = urlparse(url)
    domain = o.hostname
    domain = re.sub('^www[.]', '', domain)
    return domain



# adaptor by James Crasta on WTForms mailing list
class TornadoMultiDict(object):
    def __init__(self, handler):
        self.handler = handler

    def __iter__(self):
        return iter(self.handler.request.arguments)

    def __len__(self):
        return len(self.handler.request.arguments)

    def __contains__(self, name):
        # We use request.arguments because get_arguments always returns a
        # value regardless of the existence of the key.
        return (name in self.handler.request.arguments)

    def getlist(self, name):
        # get_arguments by default strips whitespace from the input data,
        # so we pass strip=False to stop that in case we need to validate
        # on whitespace.
        return self.handler.get_arguments(name, strip=False)



def parse_config_file(path):
    """Rewrite tornado default parse_config_file.
    
    Parses and loads the Python config file at the given path.
    
    This version allow customize new options which are not defined before
    from a configuration file.
    """
    config = {}
    execfile(path, config, config)
    for name in config:
        if name in options:
            options[name].set(config[name])
        else:
            define(name, config[name])





def fix_url(url):
    """ prepend "http://" to protocoless urls """
    if url is None:
        return url
    o = urlparse(url)
    if not o[0]:
        url = 'http://' + url
    return url



def www_or_not(url):
    """ return tuple with both www. and non-www. prefixed versions of url """

    o = list(urlparse(url))
    if o[1].lower().startswith('www'):
        o[1] = re.sub('^www[.]', '', o[1])
    else:
        o[1] = 'www.' + o[1] 

    return (url, urlunparse(o))


def human_day(d):
    today = datetime.datetime.utcnow().date()

    dd = (today-d).days
    if dd==0:
        return u"Today"
    elif dd==-1:
        return u"Tomorrow"
    elif dd==1:
        return u"Yesterday"
    elif dd>1 and dd<7:
        return d.strftime('%A')
    elif d.year == today.year:
        return d.strftime('%a %d %b')
    else:
        return d.strftime('%d %b %Y')





