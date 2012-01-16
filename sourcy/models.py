from tornado.options import define, options
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from sqlalchemy import create_engine

import util

#define("mysql_host", default="127.0.0.1:3306", help="database host")
#define("mysql_database", default="sourcy", help="database name")
#define("mysql_user", default="root", help="database user")
#define("mysql_password", default="sourcy", help="database password")

Base = declarative_base()

#eng_url = "mysql://%s:%s@%s/%s" % (options.mysql_user, options.mysql_password, options.mysql_host, options.mysql_database)
#eng_url = "mysql://root:@localhost/sourcy"

# using the "mysql+mysqldb" driver to support unicode...
eng_url = "mysql+mysqldb://root:@localhost/sourcy?charset=utf8"
engine = create_engine(eng_url, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

class Action(Base):
    __tablename__ = 'action'

    id = Column(Integer, primary_key=True)
    what = Column(String, nullable=False)

    # 'tag_add','art_add', 'lookup_add',
    # 'src_add',
    # 'src_downvote',
    # 'src_upvote',

    user_id = Column(Integer, ForeignKey('useraccount.id'))
    performed = Column(DateTime, nullable=False, default=func.current_timestamp())
#    meta = Column(String, nullable=False, default='')
    article_id = Column(Integer, ForeignKey('article.id'))
    source_id = Column(Integer, ForeignKey('source.id'))
    lookup_id = Column(Integer, ForeignKey('lookup.id'))
    tag_id = Column(Integer, ForeignKey('tag.id'))
    value = Column(Integer, nullable=False, default=0)

    user = relationship("UserAccount", backref="actions", uselist=False )

    def __init__(self, what, user, **kw):
        self.what=what
        self.user=user
        for key,value in kw.iteritems():
            assert key in ('article','lookup','tag','source','value')
            setattr(self,key,value)

    def __repr__(self):
        return "<Action(%s, %s, %s)>" % (self.what,self.performed, self.user)


    def describe(self):
        """describe the action with a short html snippet"""
        frag = None

        def art_link(art):
            return '<a href="/art/%s">%s</a> (%s)' % (art.id, art.headline, util.domain(art.permalink))

        if self.what == 'tag_add':
            frag = u"tagged '%s' as %s" %(art_link(self.article),self.tag.name)
        elif self.what == 'art_add':
            frag = u'added an article: %s' %(art_link(self.article),)
        elif self.what == 'src_add':
            if self.source.kind=='pr':
                thing = u'a press release'
            elif self.source.kind=='paper':
                thing = u'an academic paper'
            else:
                thing = u'a source'

            frag = u'added %s to %s' %(thing,art_link(self.article),)
        elif self.what == 'lookup_add':
            if self.lookup is not None:
                frag = u'added a %s: %s' %(self.lookup.kind, self.lookup.name)
#        elif self.what == 'src_upvote':
#            if self.article is not None:
#                frag = u'voted up a source on %s' % (art_link(self.article))
#        elif self.what == 'src_downvote':
#            if self.article is not None:
#                frag = u'voted down a source on %s' % (art_link(self.article))
        elif self.what == 'src_vote':
            if self.article is not None:
                assert self.value != 0
                if self.value<0:
                    frag = u'voted down a source on %s' % (art_link(self.article))
                else: 
                    frag = u'voted up a source on %s' % (art_link(self.article))

        if frag is None:
            frag = "err (id=%d)" % (self.id,)
        return frag


class ArticleURL(Base):
    __tablename__ = 'article_url'
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('article.id'))
    url = Column(String, nullable=False)

    def __init__(self,url,**kw):
        self.url=url
        if 'article' in kw:
            self.article = kw['article']

    def __repr__(self):
        return "<ArticleURL(%s)>" % (self.url,)

class Article(Base):
    __tablename__ = 'article'

    id = Column(Integer, primary_key=True)
    headline = Column(String)
    permalink = Column(String)
    pubdate = Column(DateTime)

    sources = relationship("Source", backref="article")
    tags = relationship("Tag", backref="article")
    urls = relationship("ArticleURL", backref="article")

    actions = relationship("Action", backref="article")

    def __init__(self, headline, permalink, pubdate, urls):
        self.headline = headline
        self.permalink = permalink
        self.pubdate = pubdate
        self.urls = urls

    def __repr__(self):
        return "<Article('%s','%s', '%s')>" % (self.headline, self.permalink, self.pubdate)



class Source(Base):
    __tablename__ = 'source'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('article.id'))
    url = Column(String, nullable=False)
    title = Column(String, nullable=False, default='')
    kind = Column(String, nullable=False)
    doi = Column(String, nullable=False, default='')
    meta = Column(String, nullable=False, default='')
    score = Column(Integer, nullable=False, default=0)

    actions = relationship("Action", backref="source")

    def __init__(self, **kw):
        for key,value in kw.iteritems():
            assert(key in ('url','article','title','doi','score','kind'))
            setattr(self,key,value)


    def __repr__(self):
        return "<Source(%s)>" % (self.url,)

class Lookup(Base):
    __tablename__ = 'lookup'
    id = Column(Integer, primary_key=True)
    kind = Column(String, nullable=False)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)

    actions = relationship("Action", backref="lookup")

    def __init__(self, kind, name, url):
        self.kind = kind
        self.name = name
        self.url = url

    def __repr__(self):
        return "<Lookup(%s: %s %s)>" % (self.kind, self.name, self.url)

class Tag(Base):
    __tablename__ = 'tag'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    article_id = Column(Integer, ForeignKey('article.id'),name="article_id")

    actions = relationship("Action", backref="tag")

    def __init__(self,article,name):
        self.article=article
        self.name = name

    def __repr__(self):
        return "<Tag(%s)>" % (self.name,)

class UserAccount(Base):
    __tablename__ = 'useraccount'

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True)
    prettyname = Column(String, nullable=False)
    anonymous = Column(Boolean, nullable=False, default=False)
    created = Column(DateTime, nullable=False, default=func.current_timestamp())
    # eg "twitter", "google" etc...
    auth_supplier = Column(String, nullable=False)
    # unique id on provider - email, twitter name, whatever makes sense
    auth_uid = Column(String, nullable=False)

    twitter_access_token = relationship("TwitterAccessToken", uselist=False, backref="user")

    def __init__(self, username, prettyname, email, auth_supplier, auth_uid):
        self.username = username
        self.prettyname = prettyname
        self.email = email
        self.auth_supplier = auth_supplier
        self.auth_uid = auth_uid


    def __repr__(self):
        return "<UserAccount(%s)>" % (self.username,)

class TwitterAccessToken(Base):
    __tablename__ = 'twitter_access_token'
    user_id = Column(Integer, ForeignKey('useraccount.id'), primary_key=True)
    token = Column(String, nullable=False)

    def __init__(self, user, token):
        self.user = user
        self.token = token

    def __repr__(self):
        return "<TwitterAccessToken(%s)>" % (self.token,)



