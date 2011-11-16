import csv
import re
import pickle
import logging
import store

# tools to analyse text to find mentions of institutions, journals, researchers...
# Lots of brute force string matching at the moment, so lots of scope to improve!

class Lookerupper:
    def __init__(self,store,kind):
        self.kind = kind
        self.store = store
        self.table = {}

#        filename = kind + ".pickle"
#        try:
#            self.table = pickle.load(open(filename,'rb'))
#            logging.info("Lookerupper for %s (from cache)" % (kind,))
#        except:
#            for l in store.lookup_iter(kind):
#                name = l.name
#                self.table[id] = (unicode(name).lower(),name,l.url)
#            logging.info("Lookerupper for %s" % (kind,))
#            pickle.dump(self.table, open(filename,'wb'))

        for l in store.lookup_iter(kind):
            name = l.name
            self.table[l.id] = (unicode(name).lower(),name,l.url)
        logging.info("Lookerupper for %s (%d entries)" % (kind,len(self.table)))

    def find(self,html):
        """ returns matching lookups as list of (name,url,kind,spans) tuples """

        html = html.lower()

        found = []
        # first pass - find ones which are present
        for id,l in self.table.iteritems():
            if l[0] in html:
                found.append(id)

        print found
        # second pass - find exact spans in text (might occur more than once)
        hits = {}
        for id in found:
            lookup = self.table[id]
            pat = re.compile(self.to_regex(lookup[1]),re.I)
            spans = []
            for m in pat.finditer(html):
                spans.append(m.span(0))
            if len(spans)>0:
                # name, url, kind, spans
                hits[id] = (lookup[1],lookup[2],self.kind,spans)
        return hits.values()

    def to_regex(self,s):
        return re.escape(s)


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



