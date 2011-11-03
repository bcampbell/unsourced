import csv
import re

# tools to analyse text to find mentions of institutions, journals, researchers...
# Lots of brute force string matching at the moment, so lots of scope to improve!

unis = None
journals = None

def load(filename):
    out = []
    f = open(filename,'r')
    reader = csv.reader(f)
    for row in reader:
        s = unicode(row[0],'utf-8').strip()
        url = unicode(row[1],'utf-8').strip()
        if url:
            flags = re.UNICODE|re.IGNORECASE
            if len(s.split())==1:
                flags = re.UNICODE
                pat = s
                pat = re.escape(pat)
                pat = ur'\bjournal[,]?\s+(' + pat + ur')\b'
                out.append((re.compile(pat,flags),s,url))
                pat = s
                pat = re.escape(pat)
                pat = ur'\b(' + pat + ur')\s+(?:journal|magazine)\b'
                out.append((re.compile(pat,flags),s,url))
            else:
                pat = s
                pat = re.escape(pat)
                # special case because we're really searching html
                pat = pat.replace(r'\&','&amp;')
                pat = ur'\b(' + pat + ur')\b'
                out.append((re.compile(pat,flags),s,url))
    return out


def find_institutions(txt):
    """ returns a list of (name,url,kind,spans) tuples for matched names """
    hits = {}
    for pat,s,url in unis:
        if s not in txt:
            continue
        spans = []
        for m in pat.finditer(txt):
            spans.append(m.span(1))
        if len(spans)>0:
            hits[s] = (s,url,'institution',spans)
    return hits.values()

def find_journals(txt):
    """ returns a list of (name,url,kind,spans) tuples for matched names """
    hits = {}
    for pat,s,url in journals:
        spans = []
        if s not in txt:
            continue
        for m in pat.finditer(txt):
            spans.append(m.span(1))
        if len(spans)>0:
            hits[s] = (s,url,'journal',spans)
    return hits.values()


researcher_pats = [
    # TODO: support other apostrophe chars for O'Shay etc...
    re.compile(r"led by\s+(?P<name>(([A-Z][-'\w]+)\b\s*){2,4})",re.UNICODE|re.DOTALL),
    re.compile(r"(?P<title>([Dd]r|(?:\w+ist)|[Pp]rofessor|[Pp]rof)[.]?)\s+(?P<name>(([A-Z][-'\w]+)\b\s*){2,4})",re.UNICODE|re.DOTALL),
    re.compile(r"(?P<title>([Dd]r|(?:\w+ist)|[Pp]rofessor|[Pp]rof)[.]?)?\s*(?P<name>(([A-Z][-'\w]+)\b\s*){2,4}),?\s+(((one of the)|a|the)\s+)?(scientist|author|researcher)",re.UNICODE|re.DOTALL),
    re.compile(r"[Rr]esearcher\s+(?P<title>([Dd]r|(?:\w+ist)|[Pp]rofessor|[Pp]rof)[.]?)?\s*(?P<name>(([A-Z][-'\w]{2,})\b\s*){2,4})",re.UNICODE|re.DOTALL),
]

def find_researchers(txt):
    hits = {}
    for pat in researcher_pats:
        for m in pat.finditer(txt):
            name = m.group('name')
            if name not in hits:
                hits[name] = []
            hits[name].append(m.span('name'))


    return [(name,u'','researcher',spans) for name,spans in hits.iteritems()]



unis = load('tools/unis.csv')
journals = load('tools/journals.csv')

