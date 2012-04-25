import datetime
import bcrypt
import StringIO
from PIL import Image
import os
import re

from tornado.options import define, options
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from sqlalchemy import event

import util


def is_image(content_type):
    if content_type.lower() in ("image/jpeg","image/gif","image/png"):
        return True
    return False

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
    performed = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    article_id = Column(Integer, ForeignKey('article.id'))
    source_id = Column(Integer, ForeignKey('source.id'))
    lookup_id = Column(Integer, ForeignKey('lookup.id'))
    tag_id = Column(Integer, ForeignKey('tag.id'))
    comment_id = Column(Integer, ForeignKey('comment.id'))
    value = Column(Integer, nullable=False, default=0)  # for votes

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
        elif self.what == 'tag_remove':
            frag = u"removed %s tag from '%s'" %(self.tag.name,art_link(self.article))
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
    added = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
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


class SourceKind(object):
    PAPER = 'paper'
    PR = 'pr'
    OTHER = 'other'


class Source(Base):
    __tablename__ = 'source'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('article.id'),nullable=False)
    creator_id = Column(Integer, ForeignKey('useraccount.id'),nullable=True)
    url = Column(String(512), nullable=False)
    title = Column(String(512), nullable=False, default='')
    pubdate = Column(Date)
    kind = Column(String(32), nullable=False, default=SourceKind.OTHER)
    doi = Column(String(32), nullable=False, default='')
    publication = Column(String(256), nullable=False,default='')
    score = Column(Integer, nullable=False, default=0)
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    actions = relationship("Action", backref="source", cascade="all, delete-orphan")
    creator = relationship("UserAccount")

    def __init__(self, **kw):
        for key,value in kw.iteritems():
            assert(hasattr(self,key))
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
    prettyname = Column(String(256), nullable=False, default=u'')
    hashed_password = Column(String(128), nullable=True)
    verified = Column(Boolean, nullable=False, default=False)
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    # eg "twitter", "google" etc...
    auth_supplier = Column(String(16), nullable=False, default=u'')
    # unique id on provider - email, twitter name, whatever makes sense
    auth_uid = Column(String(1024), nullable=False, default=u'')

    twitter_access_token = relationship("TwitterAccessToken", uselist=False, backref="user")

    photo_id = Column(Integer, ForeignKey('uploaded_file.id', use_alter=True, name='fk_useraccount_photo_id'), nullable=True)
    photo = relationship("UploadedFile", primaryjoin="UserAccount.photo_id==UploadedFile.id")

    def __init__(self, **kw):
        if 'password' in kw:
            kw['hashed_password'] = bcrypt.hashpw(kw['password'], bcrypt.gensalt())
            del kw['password']

        for key,value in kw.iteritems():
            assert(hasattr(self,key))
            setattr(self,key,value)

    def __repr__(self):
        return "<UserAccount(%s)>" % (self.username,)


    # TODO: could probably use sqlalchemy hybrid trickery to do this properly!
    def set_password(self,password):
        self.hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

    def check_password(self, password):
        hashed = bcrypt.hashpw(password, self.hashed_password)
        return hashed == self.hashed_password


    @staticmethod
    def calc_unique_username(session,base_username):
        """ return a unique username """
        foo = session.query(UserAccount.username).filter(UserAccount.username==base_username).first()
        if foo is None:
            return base_username
        # append a number, keep incrementing until free name found.
        i=1
        while True:
            u = "%s%d" %(base_username, i)
            foo = session.query(UserAccount.username).filter(UserAccount.username==u).first()
            if foo is None:
                return u
            i=i+1



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
    post_time = Column(DateTime,default=datetime.datetime.utcnow)
    content = Column(String(1024), nullable=False)

    author = relationship("UserAccount")

    def __init__(self, **kw):
        for key,value in kw.iteritems():
            assert(key in ('article','author','post_time','content'))
            setattr(self,key,value)


def sanitise_filename(filename):
    filename = os.path.basename(filename)
    filename = filename.lower()
    filename = re.compile('[^-._a-z0-9]').sub('',filename)
    return filename


def uniq_filename(filename):
    if not os.path.exists(filename):
        return filename
    i = 1
    base,ext = os.path.splitext(filename)
    while True:
        newname = "%s-%d%s" % (base,i,ext)
        if not os.path.exists(newname):
            return newname
        i=i+1



class UploadedFile(Base):
    __tablename__ = 'uploaded_file'

    id = Column(Integer, primary_key=True)
    # note: "use_alert" required to avoid annoying circular dependency error (shows up when using alembic)
    # base filename, as uploaded (eg "fook.jpeg"), but made unique by adding a suffix if necessary. Used to store in uploads dir.
    filename = Column(String(256), nullable=False, unique=True)
    content_type = Column(String(128), nullable=False)
    uploaded = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    is_img = Column(Boolean, nullable=False, default=False)
    # some extra data for images
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)


    def __init__(self, **kw):
        for key,value in kw.iteritems():
            assert(key in ('filename','content_type','uploaded','is_img','width','height'))
            setattr(self,key,value)
 
    @staticmethod
    def create(f, creator, app_settings):
        uploads_path = app_settings['uploads_path']
        thumbs_path = app_settings['thumbs_path']

        w,h=None,None

        # pick a unique, sane filename
        filename = sanitise_filename(f['filename'])
        full_path = os.path.join(uploads_path, filename)
        full_path = uniq_filename(full_path)
        filename = os.path.basename(full_path)
        is_img = is_image(f['content_type'])

        if is_img:
            im = Image.open(StringIO.StringIO(f['body']))
            w,h = im.size

            thumb_sizes = [(16,16),(64,64),(128,128)]
            UploadedFile.build_thumbnails(im, filename, thumb_sizes, thumbs_path)
        else:
            w,h = None,None

        fp = open(full_path, "wb")
        fp.write(f['body']);
        fp.close()

        foo = UploadedFile(filename=filename, content_type=f['content_type'],is_img=is_img, width=w, height=h)

        return foo

    def thumb_url(self,size):
        base,ext = os.path.splitext(self.filename)
        thumbfile = "%s_%dx%d%s" % (base, size[0],size[1],ext)
        # TODO: reconcile with thumbs_path setting
        return '/static/thumbs/' + thumbfile


    @staticmethod
    def build_thumbnails(img, filename, thumb_sizes, thumbs_path):
        if not os.path.exists(thumbs_path):
            os.makedirs(thumbs_path)

        for size in thumb_sizes:
            thumb = img.convert()   # convert() rather than copy() - copy leaves palette intact, which makes for crumby thumbs
            thumb.thumbnail(size, Image.ANTIALIAS)

            base,ext = os.path.splitext(filename)
            thumbfile = "%s_%dx%d%s" % (base, size[0],size[1],ext)
            thumb.save(os.path.join(thumbs_path, thumbfile))

    @staticmethod
    def on_delete(mapper,connection,target):
        # bookkeeping
        print "NOW DELETE ", target.filename

# hook in some bookkeeping to delete uploaded files/thumbs after removal from database
event.listen(UploadedFile, 'after_delete', UploadedFile.on_delete)


