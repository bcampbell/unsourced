from tornado.options import define, options
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from sqlalchemy import create_engine

import util


Base = declarative_base()

class Action(Base):
    __tablename__ = 'action'

    id = Column(Integer, primary_key=True)
    what = Column(String(32), nullable=False)

    # 'tag_add','art_add', 'lookup_add',
    # 'src_add',
    # 'src_downvote',
    # 'src_upvote',

    user_id = Column(Integer, ForeignKey('useraccount.id'))
    performed = Column(DateTime, nullable=False, default=func.current_timestamp())
    article_id = Column(Integer, ForeignKey('article.id'))
    source_id = Column(Integer, ForeignKey('source.id'))
    lookup_id = Column(Integer, ForeignKey('lookup.id'))
    tag_id = Column(Integer, ForeignKey('tag.id'))
    comment_id = Column(Integer, ForeignKey('comment.id'))
    value = Column(Integer, nullable=False, default=0)

    user = relationship("UserAccount", backref="actions", uselist=False )
    comment = relationship("Comment")   #, uselist=False )

    def __init__(self, what, user, **kw):
        self.what=what
        self.user=user
        for key,value in kw.iteritems():
            assert key in ('article','lookup','tag','source','value','comment')
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
        elif self.what == 'tag_vote':
            if self.article is not None:
                assert self.value != 0
                if self.value<0:
                    frag = u"voted down '%s' tag on %s" % (self.tag.name,art_link(self.article))
                else: 
                    frag = u"voted up '%s' tag on %s" % (self.tag.name,art_link(self.article))
        elif self.what == 'comment':
            if self.article is not None:
                frag = u"left a comment on '%s': '%s'" % (art_link(self.article),self.comment.content)
            else:
                frag = u"left a comment: '%s'" % (self.comment.content,)

        if frag is None:
            frag = "unknown ('%s' id=%d)" % (self.what, self.id,)
        return frag


class ArticleURL(Base):
    __tablename__ = 'article_url'
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('article.id'))
    url = Column(String(512), nullable=False)

    def __init__(self,url,**kw):
        self.url=url
        if 'article' in kw:
            self.article = kw['article']

    def __repr__(self):
        return "<ArticleURL(%s)>" % (self.url,)



article_tags = Table('article_tag', Base.metadata,
    Column('article_id', Integer, ForeignKey('article.id')),
    Column('tag_id', Integer, ForeignKey('tag.id'))
)


class Article(Base):
    __tablename__ = 'article'

    id = Column(Integer, primary_key=True)
    headline = Column(String(512), nullable=False)
    permalink = Column(String(512), nullable=False)
    pubdate = Column(DateTime)

    tags = relationship("Tag", secondary=article_tags, backref="articles" )

    sources = relationship("Source", backref="article", cascade="all, delete-orphan")
    urls = relationship("ArticleURL", backref="article", cascade="all, delete-orphan")
    comments = relationship("Comment", backref="article", cascade="all, delete-orphan", order_by="Comment.post_time")

    actions = relationship("Action", backref="article", cascade="all, delete-orphan")

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
    article_id = Column(Integer, ForeignKey('article.id'),nullable=False)
    creator_id = Column(Integer, ForeignKey('useraccount.id'),nullable=True)
    url = Column(String(512), nullable=False)
    title = Column(String(512), nullable=False, default='')
    pubdate = Column(Date)
    kind = Column(String(32), nullable=False)
    doi = Column(String(32), nullable=False, default='')
    publication = Column(String(256), nullable=False,default='')
    score = Column(Integer, nullable=False, default=0)

    actions = relationship("Action", backref="source", cascade="all, delete-orphan")
    creator = relationship("UserAccount")

    def __init__(self, **kw):
        for key,value in kw.iteritems():
            assert(key in ('creator','url','article','title','pubdate','doi','score','kind','publication'))
            setattr(self,key,value)


    def __repr__(self):
        return "<Source(%s)>" % (self.url,)

class Lookup(Base):
    __tablename__ = 'lookup'
    id = Column(Integer, primary_key=True)
    kind = Column(String(16), nullable=False)
    name = Column(String(256), nullable=False)
    url = Column(String(512), nullable=False)

    actions = relationship("Action", backref="lookup")

    def __init__(self, kind, name, url):
        self.kind = kind
        self.name = name
        self.url = url

    def __repr__(self):
        return "<Lookup(%s: %s %s)>" % (self.kind, self.name, self.url)



class TagKind(object):
    GENERAL=0   # general categorisation tags
    WARNING=1   # warning label
    ADMIN=2     # eg help wanted, sources missing etc....


class Tag(Base):
    """ tag defintion """
    __tablename__ = 'tag'
    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)
    description = Column(String(256), nullable=False)
    kind = Column(Integer, nullable=False, default=TagKind.GENERAL)
    icon = Column(String(32), nullable=False, default="")

    actions = relationship("Action", backref="tag")

    def __init__(self, **kw):
        for key,value in kw.iteritems():
            assert(hasattr(self,key))
            setattr(self,key,value)

    def __repr__(self):
        return "<Tag(%s)>" % (self.name,)

    def small_icon(self):
        return "/static/tag_small/%s.png" % (self.icon)

    def med_icon(self):
        return "/static/tag_med/%s.png" % (self.icon)

    def big_icon(self):
        return "/static/tag_big/%s.png" % (self.icon)



class UserAccount(Base):
    __tablename__ = 'useraccount'

    id = Column(Integer, primary_key=True)
    email = Column(String(256), nullable=False)
    username = Column(String(64), nullable=False, unique=True)
    prettyname = Column(String(256), nullable=False)
    anonymous = Column(Boolean, nullable=False, default=False)
    created = Column(DateTime, nullable=False, default=func.current_timestamp())
    # eg "twitter", "google" etc...
    auth_supplier = Column(String(16), nullable=False)
    # unique id on provider - email, twitter name, whatever makes sense
    auth_uid = Column(String(1024), nullable=False)

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
    token = Column(String(1024), nullable=False)

    def __init__(self, user, token):
        self.user = user
        self.token = token

    def __repr__(self):
        return "<TwitterAccessToken(%s)>" % (self.token,)


class Comment(Base):
    __tablename__ = 'comment'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('article.id'),nullable=True)
    author_id = Column(Integer, ForeignKey('useraccount.id'), nullable=False)
    post_time = Column(DateTime,default=func.current_timestamp())
    content = Column(String(1024), nullable=False)

    author = relationship("UserAccount")

    def __init__(self, **kw):
        for key,value in kw.iteritems():
            assert(key in ('article','author','post_time','content'))
            setattr(self,key,value)

