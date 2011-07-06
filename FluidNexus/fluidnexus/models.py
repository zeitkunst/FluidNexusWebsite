import transaction

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import Float
from sqlalchemy import ForeignKey

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship, backref

from pyramid.security import Allow
from pyramid.security import Everyone
from pyramid.security import ALL_PERMISSIONS

from pyramid_formalchemy.resources import Models

from zope.sqlalchemy import ZopeTransactionExtension

class RootFactory(object):
    __acl__ = [(Allow, Everyone, 'view'),
               (Allow, 'group:admin', 'admin'),
               (Allow, 'group:pages', 'edit_pages'),
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

    def __repr__(self):
        return "<User '%s'>" % self.username

class GroupInfo(Base):
    __label__ = "GroupInfo"
    __plural__ = "GroupInfos"
    __tablename__ = "group_info"

    id = Column(Integer, primary_key = True)
    name = Column(Unicode, nullable = False)
    description = Column(Unicode, nullable = False)

    def __repr__(self):
        return "<GroupInfo '%s'>" % self.name

    def __init__(self, name = "", description = ""):
        self.name = name
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

def initialize_sql():
    try:
        session = DBSession()
    
        import hashlib, time
        now = time.time()
        user = User()
        user.username = "admin"
        user.password = hashlib.sha256("password").hexdigest()
        user.given_name = "Admin"
        user.surname = "Admin"
        user.homepage = "http://example.com"
        user.created_time = now
        session.add(user)
    
        group_info = GroupInfo(name = "admin", description = "Admin Group")
        session.add(group_info)
    
        group_info = GroupInfo(name = "blog", description = "Blog Group")
        session.add(group_info)
    
        group_info = GroupInfo(name = "nexus", description = "Nexus Group")
        session.add(group_info)

        group_info = GroupInfo(name = "pages", description = "Pages Group")
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
        page.title = "About"
        page.content = "About the project"
        page.created_time = now
        page.modified_time = now
        page.location = "about"
        page.user_id = 1
        session.add(page)

        transaction.commit()
    except IntegrityError:
        DBSession.rollback()


def create_session(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)

