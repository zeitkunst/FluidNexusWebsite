from sqlalchemy import *
from migrate import *

meta = MetaData()

forgotten_passwords = Table('forgotten_passwords', meta,
    Column("id", Integer, primary_key = True),
    Column("token", Unicode, nullable = False),
    Column("user_id", Integer, ForeignKey('users.id'), nullable = False),
)

def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind migrate_engine
    # to your metadata
    meta.bind = migrate_engine
    users = Table('users', meta, autoload = True, autoload_with = migrate_engine)
    forgotten_passwords.create()

def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta.bind = migrate_engine
    forgotten_passwords.drop()
