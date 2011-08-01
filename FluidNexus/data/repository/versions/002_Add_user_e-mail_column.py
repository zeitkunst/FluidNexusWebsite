from sqlalchemy import *
from migrate import *

meta = MetaData()

users = Table('users', meta,
    Column('id', Integer, primary_key = True),
    Column('username', Unicode, nullable = False),
    Column('password', Unicode, nullable = False),
    Column('given_name', Unicode),
    Column('surname', Unicode),
    Column('homepage', Unicode),
    Column('created_time', Float),
    Column('user_type', Integer)
)

email_col = Column('email', Unicode, default = u"")

def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind migrate_engine
    # to your metadata
    meta.bind = migrate_engine
    #print type(users)
    #print dir(users)
    users = Table('users', meta, autoload = True, autoload_with = migrate_engine)
    email_col.create(users, populate_default = True)

def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta.bind = migrate_engine
    users = Table('users', meta, autoload = True, autoload_with = migrate_engine)
    users.drop_column("email")
