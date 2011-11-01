import tornado.database
import tornado.options
from tornado.options import define, options

import urllib2
import json
import logging

from pprint import pprint

define("port", default=8888, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1:3306", help="database host")
define("mysql_database", default="sourcy", help="database name")
define("mysql_user", default="sourcy", help="database user")
define("mysql_password", default="sourcy", help="database password")

def jl_fetch():

    url = "http://journalisted.com/api/findArticles?search=%22scientists+say%22+OR+%22paper+published%22&output=js&limit=100"
    return json.load(urllib2.urlopen(url), encoding='utf-8')

def main():
    tornado.options.parse_config_file("sourcy.conf")
    tornado.options.parse_command_line()

    db = tornado.database.Connection(
        host=options.mysql_host, database=options.mysql_database,
        user=options.mysql_user, password=options.mysql_password)

    results = jl_fetch()
    for art in results['results']:
        if db.get("SELECT id FROM article WHERE permalink=%s",art['permalink']) is None:
            art_id = db.execute("INSERT INTO article (headline,publication,permalink,pubdate,created) VALUES (%s,'',%s,%s,NOW())",art['title'],art['permalink'],art['pubdate'])
            logging.info("added %s",art['permalink'])
        else:
            logging.info("already had %s",art['permalink'])

if __name__ == "__main__":
    main()


