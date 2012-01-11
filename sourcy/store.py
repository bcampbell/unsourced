import collections
import json

import tornado.database
from tornado.options import define, options

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


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
        eng_url = "mysql+mysqldb://%(user)s:%(password)s@%(host)s/%(db)s?charset=utf8" % {
            'user': options.mysql_user,
            'password': options.mysql_password,
            'host': options.mysql_host,
            'db': options.mysql_database
        }
        engine = create_engine(eng_url, echo=False)
        Session = sessionmaker(bind=engine)
        self.session = Session()

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
        art = self.db.get("SELECT * FROM article WHERE id=%s", art_id)
        art['tags'] = self.db.query("SELECT * FROM tag WHERE article=%s", art_id)
        return art

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
        sql = "SELECT * FROM action WHERE what IN ('art_add','src_add','tag_add')"
        if user_id is not None:
            sql += " AND who=%s"
            params.append(user_id)
        sql += " ORDER BY performed DESC LIMIT %s"
        params.append(limit)
        actions = self.db.query(sql, *params)

        return self._augment_actions(actions)



    def _augment_actions(self,actions):
        """ attach users, articles, sources etc... to a bunch of actions"""

        # grab all responsible users and attach to actions
        cache = {}
        for act in actions:
            id = act.who
            if id is not None:
                if id not in cache:
                    cache[id] = self.db.get("SELECT * FROM useraccount WHERE id=%s", id)
                act.who = cache[id]

        cache = {}
        for act in actions:
            id = act.source
            if id is not None:
                if id not in cache:
                    cache[id] = self.db.get("SELECT * FROM source WHERE id=%s", id)
                act['source'] = cache[id]

        cache = {}
        for act in actions:
            id = act.article
            if id is not None:
                if id not in cache:
                    cache[id] = self.db.get("SELECT * FROM article WHERE id=%s", id)
                act['article'] = cache[id]

        cache = {}
        for act in actions:
            id = act.lookup
            if id is not None:
                if id not in cache:
                    cache[id] = self.db.get("SELECT * FROM lookup WHERE id=%s", id)
                act['lookup'] = cache[id]

        cache = {}
        for act in actions:
            id = act.tag
            if id is not None:
                if id not in cache:
                    cache[id] = self.db.get("SELECT * FROM tag WHERE id=%s", id)
                act['tag'] = cache[id]
        return actions


    def action_add_article(self,user_id,url,headline,pubdate):
        """ add an article, return article id """
        try:
            self.db.execute("BEGIN")
            art_id = self.db.execute("INSERT INTO article (headline,permalink,pubdate) VALUES (%s,%s,%s)",headline,url,pubdate)
            self.db.execute("INSERT INTO article_url (article_id,url) VALUES (%s,%s)", art_id, url)

            # log the action
            action_id = self.db.execute("INSERT INTO action (what,who,performed,article,meta) VALUES ('art_add',%s,NOW(),%s,'')", user_id, art_id)

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
            action_id = self.db.execute("INSERT INTO action (what,who,performed,meta,article,source) VALUES ('src_add',%s,NOW(),'',%s,%s)", user_id, art_id, src_id)
        except Exception as e:
            self.db.execute("ROLLBACK")
            raise
        self.db.execute("COMMIT")
        return action_id


    def user_get_source_vote(self, user, source):
        action = self.db.get("SELECT * FROM action WHERE who=%s AND what IN ('src_upvote','src_downvote') AND source=%s", user.id, source.id)
        return action


    def _remove_source_vote(self,vote):
        scores = {'src_upvote':1,'src_downvote':-1}
        assert vote.what in scores
        assert vote.source is not None
        self.db.execute("UPDATE source SET score=score-%s WHERE id=%s", scores[vote.what], vote.source)
        self.db.execute("DELETE FROM action WHERE id=%s", vote.id)

    def action_upvote_source(self, user, source):
        # check for previous vote...
        prev_vote = self.user_get_source_vote(user, source)
        if prev_vote is not None:
            if prev_vote.what != 'src_upvote':
                self._remove_source_vote(prev_vote)
            return


        self.db.execute("UPDATE source SET score=score+1 WHERE id=%s", source.id)
        action_id = self.db.execute("INSERT INTO action (what,who,performed,meta,article,source) VALUES ('src_upvote',%s,NOW(),'',%s,%s)",
            user.id, source.article_id, source.id)

    def action_downvote_source(self, user, source):
        # check for previous vote...
        prev_vote = self.user_get_source_vote(user, source)
        if prev_vote is not None:
            if prev_vote.what != 'src_downvote':
                self._remove_source_vote(prev_vote)
            return

        self.db.execute("UPDATE source SET score=score-1 WHERE id=%s", source.id)
        action_id = self.db.execute("INSERT INTO action (what,who,performed,meta,article,source) VALUES ('src_downvote',%s,NOW(),'',%s,%s)",
            user.id, source.article_id, source.id)


    def action_add_tag(self,user,article,tag_name):
        existing = self.db.get("SELECT * FROM tag WHERE article=%s AND name=%s", article.id, tag_name)
        if existing is not None:
            return
        tag_id = self.db.execute("INSERT INTO tag (name,article) VALUES (%s,%s)", tag_name, article.id)

        self.db.execute("INSERT INTO action (what,who,performed,meta,article,tag) VALUES ('tag_add',%s,NOW(),'',%s,%s)",
            user.id, article.id, tag_id)



    def action_add_lookup(self,user_id, kind, name, url):
        """ add a lookup entry, return the new lookup id"""
        try:
            assert name.strip() != u''
            self.db.execute("BEGIN")
            lookup_id = self.db.execute("INSERT INTO lookup (kind,name,url) VALUES (%s,%s,%s)", kind,name,url)

            # log the action against both source and article
            action_id = self.db.execute("INSERT INTO action (what,who,performed,meta,lookup) VALUES ('lookup_add',%s,NOW(),'',%s)", user_id, lookup_id)

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

