import tornado.database
from tornado.options import define, options

define("mysql_host", default="127.0.0.1:3306", help="database host")
define("mysql_database", default="sourcy", help="database name")
define("mysql_user", default="sourcy", help="database user")
define("mysql_password", default="sourcy", help="database password")

class Store(object):
    """ the database abstraction layer!
    
    All db interaction should happen through here.
    It's pretty ad-hoc, but simple enough.
    """

    def __init__(self):
        self.db = tornado.database.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)



    def user_get(self, user_id):
        """ return user or None """
        return self.db.get("SELECT * FROM useraccount WHERE id=%s", int(user_id))

    def user_get_by_name(self,user_name):
        """ return user or None """
        return self.db.get("SELECT * FROM useraccount WHERE name=%s", user_name)

    def user_create(self,name):
        """ return new user id """

        user_id = self.db.execute(
            "INSERT INTO useraccount (email,name,anonymous,created) VALUES (%s,%s,FALSE,NOW())",
            '', name)
        return user_id


    def art_get(self, art_id):
        return self.db.get("SELECT * FROM article WHERE id=%s", art_id)


    def art_get_by_url(self, url):
        art = self.db.get("SELECT id FROM article_url WHERE url=%s", url)
        if art is None:
            return None
        return self.art_get(art['id'])


    def art_get_sources(self, art_id):
        return self.db.query("SELECT * FROM source WHERE article_id=%s", art_id)

    def art_get_interesting(self,limit):
        """ Get a selection of acticles which look like they need work"""
        return self.db.query("SELECT * FROM article ORDER BY RAND() LIMIT %s", limit)


    def action_get_recent(self,limit):
        """ return list of actions, most recent first """

        actions = self.db.query("""
            SELECT act.*,
                    article_action.article_id,
                    source_action.source_id,
                    lookup_action.lookup_id
                FROM action act
                    LEFT JOIN article_action ON act.id = article_action.action_id
                    LEFT JOIN source_action on act.id = source_action.action_id
                    LEFT JOIN lookup_action on act.id = lookup_action.action_id
                ORDER BY performed DESC
                LIMIT %s
                """, limit)

        for act in actions:
            if act.who is not None:
                act.who = self.db.get("SELECT * FROM useraccount WHERE id=%s",act.who)
            if act.article_id is not None:
                act.article = self.art_get(act.article_id)
            else:
                act.article = None

            if act.source_id is not None:
                act.source = self.db.get("SELECT * FROM source WHERE id=%s",act.source_id)
            else:
                act.source = None

            if act.lookup_id is not None:
                act.lookup = self.db.get("SELECT * FROM lookup WHERE id=%s",act.lookup_id)
            else:
                act.lookup = None
        return actions



    def action_add_article(self,user_id,url,headline,pubdate):
        """ add an article, return article id """
        try:
            self.db.execute("BEGIN");
            art_id = self.db.execute("INSERT INTO article (headline,publication,permalink,pubdate) VALUES (%s,'',%s,%s)",headline,url,pubdate)
            self.db.execute("INSERT INTO article_url (article_id,url) VALUES (%s,%s)", art_id, url)

            # log the action
            action_id = self.db.execute("INSERT INTO action (what,who,performed) VALUES ('art_add',%s,NOW())", user_id)
            self.db.execute("INSERT INTO article_action (article_id,action_id) VALUES (%s,%s)",art_id,action_id)

        except Exception as e:
            self.db.execute("ROLLBACK")
            raise
        self.db.execute("COMMIT")
        return art_id


    def action_add_source(self,user_id, art_id, src_url):
        """ add a source link to an article, return the new source id"""
        try:
            self.db.execute("BEGIN")
            src_id = self.db.execute("INSERT INTO source (article_id,url,title) VALUES (%s,%s,%s)", art_id, src_url,'')

            # log the action against both source and article
            action_id = self.db.execute("INSERT INTO action (what,who,performed) VALUES ('src_add',%s,NOW())", user_id)
            self.db.execute("INSERT INTO source_action (source_id,action_id) VALUES (%s,%s)",src_id,action_id)
            self.db.execute("INSERT INTO article_action (article_id,action_id) VALUES (%s,%s)",art_id,action_id)
        except Exception as e:
            self.db.execute("ROLLBACK")
            raise
        self.db.execute("COMMIT")
        return src_id


    def import_lookups(self, kind, lookups):
        self.db.execute("BEGIN")
        for name,url in lookups:
            self.db.execute("INSERT INTO lookup (kind,name,url) VALUES (%s,%s,%s)", kind, name, url)
        self.db.execute("COMMIT")


    def lookup_iter(self,kind):
        results = self.db.query("SELECT id,name,url FROM lookup WHERE kind=%s", kind)
        for row in results:
            yield row


