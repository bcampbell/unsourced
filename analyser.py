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
            out.append((s,url))
    return out


def find_institutions(txt):
    """ returns a list of (name,url) tuples for matched names """
    hits = {}
    for s,url in unis:
        if s in txt:
            hits[s] = url
    return hits.items()

def find_journals(txt):
    hits = {}
    for s,url in journals:
        if s in txt:
            hits[s] = url
    return hits.items()


researcher_pats = [
    # TODO: support other apostrophe chars for O'Shay etc...
    re.compile(r"(?P<title>([Dd]r|[Pp]rofessor|[Pp]rof)[.]?)\s+(?P<name>(([A-Z][-'\w]+)\b\s*){2,4})",re.UNICODE|re.DOTALL),
    re.compile(r"(?P<title>([Dd]r|[Pp]rofessor|[Pp]rof)[.]?)?\s*(?P<name>(([A-Z][-'\w]+)\b\s*){2,4}),?\s+(((one of the)|a|the)\s+)?(scientist|author|researcher)",re.UNICODE|re.DOTALL)
]

def find_researchers(txt):
    hits = []
    for pat in researcher_pats:
        for m in pat.finditer(txt):
            name = m.group('name')
            hits.append((name,))
    return hits


unis = load('tools/unis.csv')
journals = load('tools/journals.csv')

