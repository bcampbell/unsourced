import re
import HTMLParser
from urlparse import urlparse
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





tagopenpat = re.compile( "<(\w+)(\s+.*?)?\s*(/\s*)?>", re.UNICODE|re.DOTALL )
tagclosepat = re.compile( "<\s*/\s*(\w+)\s*>", re.UNICODE|re.DOTALL )
emptylinkpat = re.compile ( "<a[^>]*?>\s*</a>", re.UNICODE )
emptylinkpat2 = re.compile ( "<a\s*>(.*?)</a>", re.UNICODE|re.DOTALL )
acceptabletags = [ 'p', 'h1','h2','h3','h4','h5','br','b','i','em','li','ul','ol','strong', 'blockquote', 'a' ]

commentkillpat = re.compile( u"<!--.*?-->", re.UNICODE|re.DOTALL )
emptyparapat = re.compile( u"<p>\s*</p>", re.IGNORECASE|re.UNICODE|re.DOTALL )

def SanitiseHTML_handleopen(m):
    tag = m.group(1).lower()

    if tag in acceptabletags:
        # special case - allow <a> to keep href attr:
        if tag == 'a':
            m2 = re.search( ('(href=\".*?\")'), m.group(2) or '')
            if m2:
                return u"<a %s>" % (m2.group(1) )

        return u"<%s>" % (tag)
    else:
        return u''

def SanitiseHTML_handleclose(m):
    tag = m.group(1).lower()
    if tag in acceptabletags:
        return u"</%s>" % (tag)
    else:
        return u' '

def sanitise_html(html):
    """Strip out all non-essential tags and attrs"""
    html = html.replace('>>', '>')

    # some tags we want to excise completely:
    for tag in ('script','noscript','style' ):
        pattxt = r'<\s*' + tag + r'\b.*?\s*>.*?</\s*' + tag + r'\s*>'
        pat = re.compile(pattxt, re.DOTALL|re.IGNORECASE )
        html = pat.sub('',html)
    # others, we might want to kill but keep the content
    html = tagopenpat.sub( SanitiseHTML_handleopen, html )
    html = tagclosepat.sub( SanitiseHTML_handleclose, html )
    html = emptyparapat.sub( u'', html )
    html = commentkillpat.sub( u'', html )
    html = emptylinkpat.sub( u'', html )
    html = emptylinkpat2.sub( ur'\1', html )
    return html.lstrip()


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
