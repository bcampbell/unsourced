import datetime
import bcrypt
import StringIO
from urlparse import urlparse
from PIL import Image
import os
import re
import logging
import json
import base64

from tornado.options import define, options
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref, validates, sessionmaker
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from sqlalchemy import event

import util
from config import settings

def is_image(content_type):
    if content_type.lower() in ("image/jpeg","image/gif","image/png"):
        return True
    return False

Base = declarative_base()

class Action(Base):
    __tablename__ = 'action'

    id = Column(Integer, primary_key=True)
    what = Column(String(32), nullable=False, index=True)

    # 'tag_add','art_add', 'lookup_add',
    # 'src_add',
    # 'src_downvote',
    # 'src_upvote',

    user_id = Column(Integer, ForeignKey('useraccount.id'), index=True)
    performed = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    article_id = Column(Integer, ForeignKey('article.id'), index=True)
    source_id = Column(Integer, ForeignKey('source.id'))
    lookup_id = Column(Integer, ForeignKey('lookup.id'))
    tag_id = Column(Integer, ForeignKey('tag.id'))
    comment_id = Column(Integer, ForeignKey('comment.id'))
    value = Column(Integer, nullable=False, default=0)  # for votes

    user = relationship("UserAccount", backref="actions", uselist=False)
    comment = relationship("Comment")   #, uselist=False )

    def __init__(self, what, user, **kw):
        self.what=what
        self.user=user
        for key,value in kw.iteritems():
            assert key in ('article','lookup','tag','source','value','comment')
            setattr(self,key,value)

    def __repr__(self):
        return "<Action(%s, %s, %s)>" % (self.what,self.performed, self.user)


class HelpReq(Base):
    """ a help request on an article """
    __tablename__ = 'help_req'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('article.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('useraccount.id'), nullable=False)
    created = Column(DateTime,default=datetime.datetime.utcnow)

    user = relationship("UserAccount", backref="help_reqs")

    def __init__(self, **kw):
        for key,value in kw.iteritems():
            assert(key in ('article','user','created'))
            setattr(self,key,value)


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
    pubdate = Column(DateTime, index=True)
    added = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    needs_sourcing = Column(Boolean, nullable=False, default=True)

    tags = relationship("Tag", secondary=article_tags, backref="articles", lazy='joined')

    sources = relationship("Source", backref="article", cascade="all, delete-orphan", lazy='joined')
    urls = relationship("ArticleURL", backref="article", cascade="all, delete-orphan")
    comments = relationship("Comment", backref="article", cascade="all, delete-orphan", order_by="Comment.post_time", lazy='joined')

    actions = relationship("Action", backref="article", cascade="all, delete-orphan")

    help_reqs = relationship("HelpReq", backref="article", cascade="all, delete-orphan", lazy='joined')

    def __init__(self, headline, permalink, pubdate, urls):
        self.headline = headline
        self.permalink = permalink
        self.pubdate = pubdate
        self.urls = urls

    def __repr__(self):
        return "<Article('%s','%s', '%s')>" % (self.headline, self.permalink, self.pubdate)


    def publisher_favicon_url(self):
        """ return a url for a favicon for publisher of this article """
        o = urlparse(self.permalink)
        return "%s://%s/favicon.ico" % (o.scheme,o.hostname)


    def papers(self):
        return [src for src in self.sources if src.kind==SourceKind.PAPER]
    def press_releases(self):
        return [src for src in self.sources if src.kind==SourceKind.PR]
    def other_links(self):
        return [src for src in self.sources if src.kind==SourceKind.OTHER]

    def art_url(self):
        return "/art/%d" % (self.id)


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
    creator = relationship("UserAccount", lazy="joined")

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

    USERNAME_PAT = re.compile('^[A-Za-z0-9_]+$')

    id = Column(Integer, primary_key=True)
    email = Column(String(256), nullable=False, index=True)
    username = Column(String(64), nullable=False, unique=True, index=True)
    prettyname = Column(String(256), nullable=False, default=u'')
    hashed_password = Column(String(128), nullable=True)

    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    last_seen = Column(DateTime, nullable=True)

    # which supplier authenticated the user eg "twitter", "google" etc...
    # empty if user signed up via email verification.
    auth_supplier = Column(String(16), nullable=False, default=u'')
    # unique id on provider - email, twitter name, whatever makes sense
    auth_uid = Column(String(1024), nullable=False, default=u'')

    twitter_access_token = relationship("TwitterAccessToken", uselist=False, backref="user")

    photo_id = Column(Integer, ForeignKey('uploaded_file.id', use_alter=True, name='fk_useraccount_photo_id'), nullable=True)
    photo = relationship("UploadedFile", primaryjoin="UserAccount.photo_id==UploadedFile.id",lazy="joined")

    @validates('username')
    def validate_username(self, key, username):
        print "BING!"
        assert self.USERNAME_PAT.match(username) is not None
        return username


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
        if self.hashed_password is None:
            return False
        hashed = bcrypt.hashpw(password, self.hashed_password)
        return hashed == self.hashed_password

    def profile_url(self):
        """ url for public profile of this user """
        return "/user/%d" %(self.id,)

    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password, bcrypt.gensalt())

    @staticmethod
    def calc_unique_username(session,base_username):
        """ return a unique, valid username based on some existing name """

        # scrub and sanitise
        base_username = re.sub('[^a-zA-Z0-9_]','',base_username)
        assert UserAccount.USERNAME_PAT.match(base_username) is not None;

        foo = session.query(UserAccount.username).filter(func.lower(UserAccount.username)==func.lower(base_username)).first()
        if foo is None:
            return base_username

        # append a number, keep incrementing until free name found.
        i=1
        while True:
            u = "%s%d" %(base_username, i)
            foo = session.query(UserAccount.username).filter(func.lower(UserAccount.username)==func.lower(u)).first()
            if foo is None:
                return u
            i=i+1

    def photo_img(self, size):
        assert size in settings.thumb_sizes
        if self.photo:
            assert self.photo.is_img
            url = self.photo.thumb_url(size)
        else:
            url = '/static/%s' % (settings.default_user_photos[size],)

        w,h = settings.thumb_sizes[size]
        return '<img src="%s" width="%d" height="%d" alt="%s"/>' % (url,w,h,self.username)



class TwitterAccessToken(Base):
    __tablename__ = 'twitter_access_token'
    user_id = Column(Integer, ForeignKey('useraccount.id'), primary_key=True)
    token = Column(String(1024), nullable=False)

    def __init__(self, user, token):
        self.user = user
        self.token = token

    def __repr__(self):
        return "<TwitterAccessToken(%s)>" % (self.token,)

comment_user_map = Table('comment_user_map', Base.metadata,
    Column('comment_id', Integer, ForeignKey('comment.id')),
    Column('useraccount_id', Integer, ForeignKey('useraccount.id'))
)

class Comment(Base):
    __tablename__ = 'comment'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('article.id'),nullable=True)
    author_id = Column(Integer, ForeignKey('useraccount.id'), nullable=False)
    post_time = Column(DateTime,default=datetime.datetime.utcnow)
    content = Column(String(1024), nullable=False)

    author = relationship("UserAccount")

    mentioned_users = relationship("UserAccount", secondary=comment_user_map, backref="comment_refs" )

    def __init__(self, **kw):
        for key,value in kw.iteritems():
            assert(key in ('article','author','post_time','content','mentioned_users'))
            setattr(self,key,value)


    @staticmethod
    def extract_users(session, comment_txt):
        """ extract referenced users from a message

        replaces "@name" with "@NN" where NN is userid (because username might change, but id won't)
        returns new comment string and list of resolved users
        """

        userpat = re.compile('@([a-zA-Z0-9_]+)', re.I)

        # look them all up in the db
        usernames = set(m.group(1) for m in userpat.finditer(comment_txt))
        users = session.query(UserAccount).\
            filter(func.lower(UserAccount.username).in_([u.lower() for u in usernames])).\
            all()
        user_lookup = dict((u.username.lower(),u) for u in users)

        def user_replace(m):
            if m.group(1).lower() not in user_lookup:
                return m.group(0)
            user = user_lookup[m.group(1).lower()]
            return u"@%d" % (user.id,)

        comment_txt = userpat.sub(user_replace, comment_txt)

        return comment_txt,users


    def format(self):
        """ mark up links to mentioned users in the comment """
        user_map = dict((u.id,u) for u in self.mentioned_users)

        userpat = re.compile('@(\d+)', re.I)
        def mkup(m):
            uid = int(m.group(1))
            u = user_map.get(uid,None)
            if u is not None:
                return '@<a href="/user/%d">%s</a>' %(u.id,u.username)
            else:
                return m.group(0)

        txt = userpat.sub(mkup, self.content)
        return txt


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
    def create(f, creator):
        uploads_path = settings.uploads_path

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
        else:
            w,h = None,None

        fp = open(full_path, "wb")
        fp.write(f['body']);
        fp.close()

        foo = UploadedFile(filename=filename, content_type=f['content_type'],is_img=is_img, width=w, height=h)

        return foo

    def thumb_url(self,size):
        assert size in settings.thumb_sizes
        return "/thumb/%s/%s" % (size,self.filename)

    @staticmethod
    def on_delete(mapper,connection,target):
        # bookkeeping
        # TODO: actually delete the file!

        print "NOW DELETE ", target.filename

# hook in some bookkeeping to delete uploaded files/thumbs after removal from database
event.listen(UploadedFile, 'after_delete', UploadedFile.on_delete)



class Token(Base):
    """ Token with payload, for email verification tasks """
    __tablename__ = 'token'

    name = Column(String(64), primary_key=True, default=lambda: base64.urlsafe_b64encode(os.urandom(12)))
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    expires = Column(DateTime, nullable=False, default=lambda: datetime.datetime.utcnow() + datetime.timedelta(days=7))
    payload = Column(String(2048), nullable=False)

    def __init__(self, **kw):
        for key,value in kw.iteritems():
            assert(key in ('name','expires','payload'))
            setattr(self,key,value)

    def set_payload_from_dict(self,d):
        self.payload = json.dumps(d)
        
    def get_payload_as_dict(self):
        return json.loads(self.payload)


    @staticmethod
    def create_registration(email, password):
        """ create a token which will register a new user when used """

        # we don't _ever_ want to store raw passwords
        hashed_password = UserAccount.hash_password(password)

        payload=dict(
            op='register',
            email=email,
            hashed_password=hashed_password)
        tok = Token()
        tok.set_payload_from_dict(payload)
        return tok

    @staticmethod
    def create_login(user_id, next=None):
        """ create a token which will log in an existing user """
        payload=dict(op='login', user_id=user_id)
        if next is not None:
            payload['next'] = next

        tok = Token()
        tok.set_payload_from_dict(payload)
        return tok


