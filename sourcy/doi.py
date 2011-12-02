import rdflib
import urllib2
from rdflib import plugin, Namespace
from StringIO import StringIO
from pprint import pprint
import sys

plugin.register(
    'sparql', rdflib.query.Processor,
    'rdfextras.sparql.processor', 'Processor')
plugin.register(
    'sparql', rdflib.query.Result,
    'rdfextras.sparql.query', 'SPARQLQueryResult')


# curl -D - -L -H "Accept: text/turtle" "http://dx.doi.org/10.1111/j.1095-8339.2011.01183.x"

# returns different object! (.g007 suffix)
#curl -D - -L -H "Accept: text/turtle" "http://dx.doi.org/10.1371/journal.pone.0024408"


def parseit(rdfxml_data,doi):
    """ parses out paper title, date, name of journal and authors from rdf xml """
    out = {}

    g = rdflib.Graph()
    g.parse(StringIO(rdfxml_data), format='xml')

    # NOTE:
    # PLoS ONE articles seem to return wrong doi (seems to be the doi of
    # the first figure in the article)

    qres = g.query(
        """SELECT DISTINCT ?title ?date ?journalname ?doi
           WHERE {
              ?paper <http://purl.org/ontology/bibo/doi> ?doi .
              ?paper <http://purl.org/dc/terms/title> ?title .
              ?paper a <http://purl.org/ontology/bibo/Article> .
              ?paper <http://purl.org/dc/terms/date> ?date .
              ?paper <http://purl.org/dc/terms/isPartOf> ?journal .
              ?journal <http://purl.org/dc/terms/title> ?journalname .
           }"""
#        initNs=dict(
#            foaf=Namespace("http://xmlns.com/foaf/0.1/"))
        )

    row = qres.result[0]
    out['title'] = unicode(row[0])
    out['date'] = unicode(row[1])
    out['journal'] = unicode(row[2])
    # might have returned the wrong doi - we'll still use it to query authors
    returned_doi = unicode(row[3])

    if doi != returned_doi:
        print "doi warning: expected '%s', got '%s'" % (doi,returned_doi)

    qres = g.query(
        """SELECT DISTINCT ?name ?paper
           WHERE {
              ?paper <http://purl.org/ontology/bibo/doi> '%s' .
              ?paper <http://purl.org/dc/terms/creator> ?creator .
              ?creator <http://xmlns.com/foaf/0.1/name> ?name .
              ?creator a <http://xmlns.com/foaf/0.1/Person> .
           }""" % (returned_doi,))
    out['authors'] = [unicode(row[0]) for row in qres.result]

    return out


def grabit(doi):
    url = 'http://dx.doi.org/' + doi

    headers = {'Accept': 'application/rdf+xml'}
    req = urllib2.Request(url, None, headers)
    response = urllib2.urlopen(req)
    body = response.read()

    content_type = response.info().get('content-type')
    content_type = content_type.split(";", 1)[0]
    assert content_type == 'application/rdf+xml'

    return body,content_type


def main():


    for doi in sys.argv[1:]:
        body,content_type = grabit(doi)
        meta = parseit(body, content_type, doi)
        pprint(meta)



if __name__ == "__main__":
    main()

