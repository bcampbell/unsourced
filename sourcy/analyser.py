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
        store.register_lookup_listener(self)
        logging.info("Lookerupper for %s (%d entries)" % (kind,len(self.table)))

    def on_lookup_added(self,lookup_id, kind, name, url):
        if kind != self.kind:
            return
        logging.info("added %s: [%s](%s)", kind, name, url)
        self.table[lookup_id] = (name.lower(),name,url)


    def find(self,html):
        """ returns matching lookups as list of (start,end,kind,name,url) tuples """

        html = html.lower()

        found = []
        # first pass - find ones which are present
        for id,l in self.table.iteritems():
            if l[0] in html:
                found.append(id)

        # second pass - find exact spans in text (might occur more than once)
        # we can be a bit more picky here (eg to filter out crap matches for
        # journals with generic names (science, nature, etc))
        hits = []
        for id in found:
            lookup = self.table[id]
            pat = self.to_regex(lookup[1])
            spans = []
            for m in pat.finditer(html):
                if 'name' in m.groupdict():
                    span = m.span('name')
                else:
                    span = m.span('name2')

                # start,end,kind,name,url
                hits.append((span[0],span[1], self.kind, lookup[1], lookup[2]))
        return hits

    def to_regex(self,s):
        s = re.escape(s)
        # TODO: this is cheesy as hell! 
        if self.kind == 'journal' and len(s.split()) <=1:
            s = r'((journal|magazine|published in|printed in)[,]?\s+(?P<name>%s))|((?P<name2>)%s\s+(journal|magazine))' % (s,s)
        else:
            s = r'\b(?P<name>%s)\b' % (s,)
        return re.compile(s,re.I)



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


# "graduate student Kim Volterman"
# "Study leader Brian Timmons"
# "Lead researcher Dr Maria Karayiorgou"

