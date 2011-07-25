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
    Column('created_time', Float)
)

user_type_col = Column('user_type', Integer)

def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind migrate_engine
    # to your metadata
    meta.bind = migrate_engine
    #print type(users)
    #print dir(users)
    users = Table('users', meta, autoload = True, autoload_with = migrate_engine)
    user_type_col.create(users, populate_default = True)

def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    users = Table('users', meta, autoload = True, autoload_with = migrate_engine)
    users.drop_column("user_type")
