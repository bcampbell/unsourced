import collections
import json

import tornado.database
from tornado.options import define, options


#define("mysql_host", default="127.0.0.1:3306", help="database host")
#define("mysql_database", default="sourcy", help="database name")
#define("mysql_user", default="sourcy", help="database user")
#define("mysql_password", default="sourcy", help="database password")

class Store(object):
    """ the database abstraction layer!
    
    All db interaction should happen through here.
    It's pretty ad-hoc, but simple enough.
    """

    SOURCE_KINDS = ['other','pr','paper']

    def __init__(self):
        self.db = tornado.database.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)
        self.lookup_listeners = set()

    def register_lookup_listener(self, listener):
        """ register interest in lookups """
        self.lookup_listeners.add(listener)


    def user_get(self, user_id):
        """ return user or None """
        return self.db.get("SELECT * FROM useraccount WHERE id=%s", int(user_id))

    def user_get_by_username(self,username):
        """ return user or None """
        return self.db.get("SELECT * FROM useraccount WHERE username=%s", username)

    def user_get_by_email(self,email):
        """ return user or None """
        return self.db.get("SELECT * FROM useraccount WHERE email=%s", email)

    def user_get_by_auth_uid(self,auth_supplier,auth_uid):
        """ return user or None """
        return self.db.get("SELECT * FROM useraccount WHERE auth_supplier=%s AND auth_uid=%s", auth_supplier, auth_uid)

    def user_create(self,username,prettyname,email,auth_supplier,auth_uid):
        """ return new user id """

        user_id = self.db.execute(
            "INSERT INTO useraccount (email,username,prettyname,anonymous,created,auth_supplier,auth_uid) VALUES (%s,%s,%s,FALSE,NOW(),%s,%s)",
            email, username,prettyname,auth_supplier,auth_uid)
        return user_id

    def user_set_twitter_access_token(self,user,access_token=None):
        """ set a twitter access_token on this user, so we can tweet on their behalf (pass None to remove token)"""
        self.db.execute("DELETE FROM twitter_access_token WHERE user_id=%s", user.id)
        if access_token is not None:
            data = json.dumps(access_token)
            self.db.execute("INSERT INTO twitter_access_token (user_id,token) VALUES (%s,%s)", user.id, data)

    def user_get_twitter_access_token(self, user):
        row = self.db.get("SELECT token FROM twitter_access_token WHERE user_id=%s", user.id)
        if row is None:
            return None
        return json.loads(row.token)




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

    def art_get_by_date(self,date):
        """ Get a selection of acticles which look like they need work"""

        arts = self.db.query("SELECT * FROM article WHERE CAST(pubdate AS DATE)=%s", date.strftime('%Y-%m-%d'))

        sources = self.db.query("""
            SELECT * FROM source
                WHERE article_id IN (
                    SELECT id FROM article WHERE CAST(pubdate AS DATE)=%s
                )
                """, date.strftime('%Y-%m-%d'))
        # add the sources to the articles
        art_lookup = {}
        for a in arts:
            art_lookup[a.id] = a
            a.sources = []
        for s in sources:
            art_lookup[s.article_id].sources.append(s)
        return arts


    def action_get(self, action_id):
        """ retrieve a single action """

        actions = self.db.query("SELECT * FROM action WHERE id=%s", action_id)
        actions = self._augment_actions(actions)
        assert len(actions)==1
        return actions[0]


    def action_get_recent(self,limit,user_id=None):
        """ return list of actions, most recent first """

        params = []
        sql = "SELECT * FROM action"
        if user_id is not None:
            sql += " WHERE who=%s"
            params.append(user_id)
        sql += " ORDER BY performed DESC LIMIT %s"
        params.append(limit)
        actions = self.db.query(sql, *params)

        return self._augment_actions(actions)



    def _augment_actions(self,actions):
        """ attach users, articles, sources etc... to a bunch of actions"""
        #index by id
        action_map = {}
        for act in actions:
            action_map[act.id] = act
            act.source = None
            act.article = None
            act.lookup = None

        # grab all responsible users and attach to actions
        user_ids = set([act.who for act in actions if act.who is not None])

        if user_ids:
            users = self.db.query("SELECT * FROM useraccount WHERE id IN (" + ','.join([str(id) for id in user_ids]) + ")")
            user_map = {}
            for user in users:
                user_map[user.id] = user
            for act in actions:
                if act.who is not None:
                    # flesh out into full user
                    act.who = user_map[act.who]

        action_ids = ','.join(["'%d'" % (k,) for k in action_map.keys()])
        # grab and attach sources
        sources = self.db.query("SELECT s.*,sa.source_id,sa.action_id FROM (source s INNER JOIN source_action sa ON sa.source_id=s.id) WHERE sa.action_id IN (" + action_ids +")")
        for source in sources:
            action_map[source.action_id].source = source

        # grab and attach lookups
        lookups = self.db.query("SELECT l.*,la.lookup_id,la.action_id FROM (lookup l INNER JOIN lookup_action la ON la.lookup_id=l.id) WHERE la.action_id IN (" + action_ids + ")") 
        for lookup in lookups:
            action_map[lookup.action_id].lookup = lookup

        # grab and attach articles
        articles = self.db.query("SELECT a.*,aa.article_id,aa.action_id FROM (article a INNER JOIN article_action aa ON aa.article_id=a.id) WHERE aa.action_id IN (" + action_ids +")") 
        for article in articles:
            action_map[article.action_id].article = article

        return actions


    def action_add_article(self,user_id,url,headline,pubdate):
        """ add an article, return article id """
        try:
            self.db.execute("BEGIN")
            art_id = self.db.execute("INSERT INTO article (headline,permalink,pubdate) VALUES (%s,%s,%s)",headline,url,pubdate)
            self.db.execute("INSERT INTO article_url (article_id,url) VALUES (%s,%s)", art_id, url)

            # log the action
            action_id = self.db.execute("INSERT INTO action (what,who,performed) VALUES ('art_add',%s,NOW())", user_id)
            self.db.execute("INSERT INTO article_action (article_id,action_id) VALUES (%s,%s)",art_id,action_id)

        except Exception as e:
            self.db.execute("ROLLBACK")
            raise
        self.db.execute("COMMIT")
        return art_id


    def action_add_source(self,user_id, art_id, src_url, kind, doi=u''):
        """ add a source link to an article, return the action id"""

        assert kind in Store.SOURCE_KINDS
        try:
            self.db.execute("BEGIN")
            src_id = self.db.execute("INSERT INTO source (article_id,url,title,kind,doi) VALUES (%s,%s,%s,%s,%s)", art_id, src_url, '', kind, doi)

            # log the action against both source and article
            action_id = self.db.execute("INSERT INTO action (what,who,performed) VALUES ('src_add',%s,NOW())", user_id)
            self.db.execute("INSERT INTO source_action (source_id,action_id) VALUES (%s,%s)",src_id,action_id)
            self.db.execute("INSERT INTO article_action (article_id,action_id) VALUES (%s,%s)",art_id,action_id)
        except Exception as e:
            self.db.execute("ROLLBACK")
            raise
        self.db.execute("COMMIT")
        return action_id


    def action_add_lookup(self,user_id, kind, name, url):
        """ add a lookup entry, return the new lookup id"""
        try:
            assert name.strip() != u''
            self.db.execute("BEGIN")
            lookup_id = self.db.execute("INSERT INTO lookup (kind,name,url) VALUES (%s,%s,%s)", kind,name,url)

            # log the action against both source and article
            action_id = self.db.execute("INSERT INTO action (what,who,performed) VALUES ('lookup_add',%s,NOW())", user_id)
            self.db.execute("INSERT INTO lookup_action (lookup_id,action_id) VALUES (%s,%s)",lookup_id,action_id)

            for l in self.lookup_listeners:
                l.on_lookup_added(lookup_id, kind, name, url)

        except Exception as e:
            self.db.execute("ROLLBACK")
            raise
        self.db.execute("COMMIT")
        return lookup_id

    def import_lookups(self, kind, lookups):
        self.db.execute("BEGIN")
        for name,url in lookups:
            self.db.execute("INSERT INTO lookup (kind,name,url) VALUES (%s,%s,%s)", kind, name, url)
        self.db.execute("COMMIT")


    def lookup_iter(self,kind):
        results = self.db.query("SELECT id,name,url FROM lookup WHERE kind=%s", kind)
        for row in results:
            yield row


    def art_bulk_import(self, articles):
        """ import a bunch of articles (without creating an action) """
        self.db.execute("BEGIN")

        for art in articles:
            if self.art_get_by_url(art['permalink']) is None:
                art_id = self.db.execute("INSERT INTO article (headline,permalink,pubdate) VALUES (%s,%s,%s)",art['title'],art['permalink'],art['pubdate'])
                self.db.execute("INSERT INTO article_url (article_id,url) VALUES (%s,%s)",art_id, art['permalink'])

        self.db.execute("COMMIT")


    def source_get(self, source_id):
        """ return source or None """
        return self.db.get("SELECT * FROM source WHERE id=%s", int(source_id))

