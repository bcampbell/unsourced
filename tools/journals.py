#!/usr/bin/env python

from SPARQLWrapper import SPARQLWrapper, JSON
from pprint import pprint
import time
import csv
from optparse import OptionParser
import logging
import sys

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

        logging.info("fetch %d", offset)
        results = sparql.query().convert()

        offset += limit
        if len(results['results']['bindings']) == 0:
            break

        for result in results["results"]["bindings"]:
            if 'homepage' in result:
                row = (result["name"]["value"], result["homepage"]["value"])
            else:
                row = (result["name"]["value"], u'')

            row = (row[0].strip(), row[1].strip())
            if row[0] != u'':
                fetched.append(row)
        time.sleep(2)
    fetched.sort(key=lambda tup: tup[0])
    return fetched


def main():
    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='store_true')
    (options, args) = parser.parse_args()

    log_level = logging.ERROR
    if options.verbose:
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format='%(message)s')

    if len(args) < 1:
        parser.error("must specify outfile")
    if args[0] == '-':
        outfile = sys.stdout
    else:
        outfile = open(args[0],'w')

    writer = csv.writer(outfile)

    data = fetchum()
    enc = 'utf-8'
    for row in data:
        row = [r.encode(enc) for r in row]
        writer.writerow(row)


if __name__ == "__main__":
    main()

