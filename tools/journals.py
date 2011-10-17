#!/usr/bin/env python

from SPARQLWrapper import SPARQLWrapper, JSON
from pprint import pprint
import time
import csv


def fetchum():
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    fetched = []
    offset = 0
    limit = 2000
    while True:
        sparql.setQuery("""
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>

            SELECT DISTINCT ?name ?homepage WHERE {
                 ?j rdf:type dbo:AcademicJournal.
                 ?j foaf:name ?name.
                 OPTIONAL{ ?j foaf:homepage ?homepage }
            }
            ORDER BY ?name
            LIMIT %d OFFSET %d
        """ % (limit,offset))
        sparql.setReturnFormat(JSON)

        print "fetch %d" % (offset,)
        results = sparql.query().convert()

        offset += limit
        if len(results['results']['bindings']) == 0:
            break

        for result in results["results"]["bindings"]:
            if 'homepage' in result:
                fetched.append((result["name"]["value"], result["homepage"]["value"]))
            else:
                fetched.append((result["name"]["value"], u''))
        time.sleep(2)
    return fetched


def main():
    data = fetchum()
    writer = csv.writer(open('journals.csv', 'w'))
    enc = 'utf-8'
    for row in data:
        row = [r.encode(enc) for r in row]
        writer.writerow(row)


if __name__ == "__main__":
    main()
