import hashlib, time

import textile

import transaction

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Boolean

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import NoResultFound

from pyramid.security import Allow
from pyramid.security import Everyone
from pyramid.security import ALL_PERMISSIONS

from pyramid_formalchemy.resources import Models

from zope.sqlalchemy import ZopeTransactionExtension

import bcrypt

class RootFactory(object):
    __acl__ = [(Allow, Everyone, 'view'),
               (Allow, 'group:admin', 'admin'),
               (Allow, 'group:pages', 'edit_pages'),
               (Allow, 'group:nexus', 'post_nexus'),
                (Allow, 'group:blog', 'edit_blog')]

    def __init__(self, request):
        pass


class FormAlchemyRootFactory(Models):
    __acl__ = [
        (Allow, 'group:admin', ('new', 'edit', 'view', 'delete')),
    ]

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

class User(Base):
    __label__ = 'User'
    __plural__ = 'Users'
    __tablename__ = "users"
    id = Column(Integer, primary_key = True)
    username = Column(Unicode, nullable = False)
    password = Column(Unicode, nullable = False)
    given_name = Column(Unicode)
    surname = Column(Unicode)
    homepage = Column(Unicode)
    created_time = Column(Float)
    user_type = Column(Integer)

    NORMAL = 0
    OPENID = 1

    def __repr__(self):
        return "<User '%s'>" % self.username

    @classmethod
    def getByUsername(cls, username):
        return DBSession.query(cls).filter(cls.username == username).first()

    @classmethod
    def getByID(cls, user_id):
        return DBSession.query(cls).filter(cls.id == user_id).first()

    @classmethod
    def checkPassword(cls, username, password):
        user = cls.getByUsername(username)
        if not user:
            return False

        hashed_password = DBSession.query(User.password).filter(User.username == username).one()[0]

        if bcrypt.hashpw(password, hashed_password) == hashed_password:
            return True
        else:
            return False

    @classmethod
    def getID(cls, username):
        return DBSession.query(cls.id).filter(cls.username == username).one()[0]

    @classmethod
    def addToGroup(cls, username, groupname):
        group_info_id = DBSession.query(GroupInfo.id).filter(GroupInfo.group_name == groupname).one()[0]
        user_id = DBSession.query(cls.id).filter(cls.username == username).one()[0]
        group = Group()
        group.group_info_id = group_info_id
        group.user_id = user_id
        DBSession.add(group)

class OpenID(Base):
    __label__ = 'OpenID'
    __plural__ = 'OpenIDs'
    __tablename__ = "openids"
    id = Column(Integer, primary_key = True)
    openid_url = Column(Unicode, nullable = False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable = False)

    user = relationship(User, backref=backref('openids', order_by=id))

    def __init__(self, openid_url = "", user_id = -1):
        self.openid_url = openid_url
        self.user_id = user_id

    def __repr__(self):
        return "<OpenID '%s'>" % self.openid_url

    @classmethod
    def checkOpenIDURL(cls, openid_url):
        try:
            user_id = DBSession.query(cls.user_id).filter(cls.openid_url == openid_url).one()[0]
            user = User.getByID(user_id)
            return user
        except NoResultFound, e:
            return False

class GroupInfo(Base):
    __label__ = "GroupInfo"
    __plural__ = "GroupInfos"
    __tablename__ = "group_info"

    id = Column(Integer, primary_key = True)
    group_name = Column(Unicode, nullable = False)
    description = Column(Unicode, nullable = False)

    def __repr__(self):
        return "<GroupInfo '%s'>" % self.group_name

    def __init__(self, group_name = "", description = ""):
        self.group_name = group_name
        self.description = description

class Group(Base):
    __label__ = "Group"
    __plural__ = "Groups"
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key = True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable = False)
    group_info_id = Column(Integer, ForeignKey('group_info.id'), nullable = False)

    user = relationship(User, backref=backref('groups', order_by=id))
    group_info = relationship(GroupInfo, backref=backref('groups', order_by=id))
    
    def __repr__(self):
        return "<Group '%d'>" % self.id

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    title = Column(Unicode, nullable = False)
    content = Column(Unicode, nullable = False)
    created_time = Column(Float)
    modified_time = Column(Float)
    user_id = Column(Integer, ForeignKey('users.id'), nullable = False)

    user = relationship(User, backref=backref('posts', order_by=id))

    def __init__(self, title = "", content = ""):
        self.title = title
        self.content = content

    def __repr__(self):
        return "<Post '%s'>" % self.title

    def getISOTime(self):
        """Format the time for display."""
        timetuple = time.gmtime(self.created_time)
        return time.strftime("%Y-%m-%dT%H:%M:%S", timetuple)

    def getFormattedTime(self):
        return time.ctime(self.created_time)

    def getFormattedContent(self):
        return textile.textile(self.content)

class Page(Base):
    __tablename__ = 'pages'
    id = Column(Integer, primary_key=True)
    title = Column(Unicode, nullable = False)
    content = Column(Unicode, nullable = False)
    location = Column(Unicode, nullable = False, unique = True)
    created_time = Column(Float)
    modified_time = Column(Float)
    user_id = Column(Integer, ForeignKey('users.id'), nullable = False)

    user = relationship(User, backref=backref('pages', order_by=id))

    def __init__(self, title = "", content = ""):
        self.title = title
        self.content = content

    def __repr__(self):
        return "<Page '%s' (%s) >" % (self.title, self.location)


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key = True)
    name = Column(Unicode, nullable = False)
    email = Column(Unicode, nullable = False)
    homepage = Column(Unicode)
    content = Column(Unicode, nullable = False)
    created_time = Column(Float, nullable = False)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable = False)

    post = relationship(Post, backref=backref('comments', order_by=id))

    def __repr__(self):
        if (len(self.content) > 20):
            value = self.content[0:20]
        else:
            value = self.content

        return "<Comment '%s'>" % self.content

    def getISOTime(self):
        """Format the time for display."""
        timetuple = time.gmtime(self.created_time)
        return time.strftime("%Y-%m-%dT%H:%M:%S", timetuple)

    def getFormattedTime(self):
        return time.ctime(self.created_time)

class NexusMessage(Base):
    __tablename__ = "nexus_messages"

    id = Column('id', Integer, primary_key=True)
    message_type = Column('type', Integer, nullable = False, default = 0)
    title = Column('title', String, nullable = False)
    content = Column('content', String, nullable = False)
    message_hash = Column('hash', String(length = 64), nullable = False, unique = True) 
    message_type = Column('type', Integer, nullable = False) 
    created_time = Column('time', Float, default = float(0.0))
    attachment_path = Column('attachment_path', String, default = "")
    attachment_original_filename = Column('attachment_original_filename',       String, default = "")
    user_id = Column(Integer, ForeignKey('users.id'), nullable = False)

    user = relationship(User, backref=backref('nexus_messages', order_by=id))

    def __repr__(self):
        return "<NexusMessage '%s'>" % self.message_hash

    @classmethod
    def getByMessageHash(cls, message_hash):
        return DBSession.query(cls).filter(cls.message_hash == message_hash).first()

    def getISOTime(self):
        """Format the time for display."""
        timetuple = time.gmtime(self.created_time)
        return time.strftime("%Y-%m-%dT%H:%M:%S", timetuple)

    def getFormattedTime(self):
        return time.ctime(self.created_time)

    def getFormattedContent(self):
        return textile.textile(self.content)

class ConsumerKeySecret(Base):
    __label__ = 'ConsumerKeySecret'
    __plural__ = 'ConsumerKeySecrets'
    __tablename__ = "consumer_key_secrets"
    id = Column(Integer, primary_key = True)
    consumer_key = Column(Unicode, nullable = False)
    consumer_secret = Column(Unicode, nullable = False)
    status = Column(Integer, nullable = False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable = False, unique = True)

    user = relationship(User, backref=backref('consumer_key_secrets', order_by=id))

    NORMAL = 0
    THROTTLED = 1
    BLACKLISTED = 2

    def __repr__(self):
        return "<ConsumerKeySecret '%s'>" % self.consumer_key

    @classmethod
    def getByUserID(cls, user_id):
        try:
            return DBSession.query(cls).filter(cls.user_id == user_id).one()
        except NoResultFound, e:
            return False

    @classmethod
    def getByConsumerID(cls, consumer_id):
        try:
            return DBSession.query(cls).filter(cls.id == consumer_id).one()
        except NoResultFound, e:
            return False


    @classmethod
    def getByConsumerKey(cls, consumer_key):
        try:
            keySecret = DBSession.query(cls).filter(cls.consumer_key == consumer_key).one()
            keySecret.key = keySecret.consumer_key
            keySecret.secret = keySecret.consumer_secret
            return keySecret
        except NoResultFound, e:
            return False

    def setNormalStatus(self):
        self.status = self.NORMAL

    def setThrottledStatus(self):
        self.status = self.THROTTLED

    def setBlacklistedStatus(self):
        self.status = self.BLACKLISTED

class ConsumerNonce(Base):
    __tablename__ = "consumer_nonces"

    id = Column(Integer, primary_key = True)
    consumer_id = Column(Integer, ForeignKey('consumer_key_secrets.id'), nullable = False)
    nonce = Column(String, nullable = False)
    timestamp = Column(Float, nullable = False)

    consumer_key_secret = relationship(ConsumerKeySecret, backref=backref('consumer_nonces', order_by=id))

    def __repr__(self):
        return "<ConsumerNonce '%s'>" % self.nonce

    @classmethod
    def getByNonce(cls, nonce):
        try:
            result = DBSession.query(cls).filter(cls.nonce == nonce).one()
            return result
        except NoResultFound, e:
            return False

    @classmethod
    def checkNonce(cls, nonce, delta = 60 * 60 * 2):
        try:
            result = DBSession.query(cls).filter(cls.nonce == nonce).one()
            now = time.time()
            if (now > (result.timestamp + delta)):
                return False
            else:
                return True
        except NoResultFound, e:
            return False
       
class Token(Base):
    __tablename__ = "tokens"

    DISABLED = 0
    AUTHORIZATION = 1
    ACCESS = 2


    id = Column(Integer, primary_key = True)
    token_type = Column(Integer, nullable = False)
    consumer_id = Column(Integer, ForeignKey('consumer_key_secrets.id'), nullable = False)
    token = Column(String, nullable = False)
    token_secret = Column(String, nullable = False)
    timestamp = Column(Float, nullable = False)
    callback_url = Column(String)
    verifier = Column(String)

    consumer_key_secret = relationship(ConsumerKeySecret, backref=backref('tokens', order_by=id))

    def __repr__(self):
        return "<Token '%s'>" % self.token

    @classmethod
    def getByToken(cls, token):
        try:
            foundToken = DBSession.query(cls).filter(cls.token == token).one()
            foundToken.key = foundToken.token
            foundToken.secret = foundToken.token_secret
            return foundToken
        except NoResultFound, e:
            return False

    @classmethod
    def getByConsumerID(cls, consumer_id):
        try:
            foundToken = DBSession.query(cls).filter(cls.consumer_id == consumer_id).one()
            foundToken.key = foundToken.token
            foundToken.secret = foundToken.token_secret
            return foundToken
        except NoResultFound, e:
            return False

    @classmethod
    def getByUserID(cls, user_id):
        try:
            foundToken = DBSession.query(cls).filter(cls.consumer_key_secret.user.id == user_id).one()
            foundToken.key = foundToken.token
            foundToken.secret = foundToken.token_secret
            return foundToken
        except NoResultFound, e:
            return False

    @classmethod
    def getTokenByConsumerID(cls, consumer_id):
        try:
            foundToken = DBSession.query(cls).filter(cls.consumer_id == consumer_id).filter(cls.token_type == cls.ACCESS).one()
            foundToken.token= foundToken.token
            foundToken.token_secret = foundToken.token_secret
            return foundToken
        except NoResultFound, e:
            return False


    def setAuthorizationType(self):
        self.token_type = self.AUTHORIZATION

    def setAccessType(self):
        self.token_type = self.ACCESS

    def setDisabledType(self):
        self.token_type = self.DISABLED

def initialize_sql():
    try:
        session = DBSession()
    
        import bcrypt, time
        now = time.time()
        user = User()
        user.username = "admin"
        #user.password = hashlib.sha256("password").hexdigest()
        user.password = bcrypt.hashpw("password", bcrypt.gensalt())
        user.given_name = "Admin"
        user.surname = "Admin"
        user.homepage = "http://example.com"
        user.created_time = now
        session.add(user)
    
        group_info = GroupInfo(group_name = "admin", description = "Admin Group")
        session.add(group_info)
    
        group_info = GroupInfo(group_name = "blog", description = "Blog Group")
        session.add(group_info)
    
        group_info = GroupInfo(group_name = "nexus", description = "Nexus Group")
        session.add(group_info)

        group_info = GroupInfo(group_name = "pages", description = "Pages Group")
        session.add(group_info)

        group = Group()
        group.user_id = 1
        group.group_info_id = 1
        session.add(group)

        group = Group()
        group.user_id = 1
        group.group_info_id = 2
        session.add(group)

        group = Group()
        group.user_id = 1
        group.group_info_id = 3
        session.add(group)

        group = Group()
        group.user_id = 1
        group.group_info_id = 4
        session.add(group)

        # Fake openid info
        openid = OpenID()
        openid.openid = "blank"
        openid.openid_url = "http://example.com"
        openid.user_id = "0"

        post = Post()
        now = time.time()
        post.title = "First post!"
        post.content = "First post content!"
        post.created_time = now
        post.modified_time = now
        post.user_id = 1
        session.add(post)

        comment = Comment()
        now = time.time()
        comment.name = "user"
        comment.email = "foo@example.com"
        comment.content = "This is a test comment, nothing more, nothing less."
        comment.created_time = now
        comment.post_id = 1
        session.add(comment)

        page = Page()
        now = time.time()
        page.title = "Concept"
        page.content = "Regarding the project"
        page.created_time = now
        page.modified_time = now
        page.location = "concept"
        page.user_id = 1
        session.add(page)

        message = NexusMessage()
        now = time.time()
        message.title = "First Nexus message"
        message.content = "Nexus message content"
        message.created_time = now
        message.user_id = 1
        message.message_hash = hashlib.sha256(message.title + message.content).hexdigest()
        session.add(message)

        transaction.commit()
    except IntegrityError:
        DBSession.rollback()


def create_session(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)

