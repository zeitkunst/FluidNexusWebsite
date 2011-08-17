from sqlalchemy import *
from migrate import *

meta = MetaData()
priority_col = Column('priority', Integer, default = 0)

def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind migrate_engine
    # to your metadata
    meta.bind = migrate_engine
    nexus_messages = Table('nexus_messages', meta, autoload = True, autoload_with = migrate_engine)
    priority_col.create(nexus_messages, populate_default = True)

def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    nexus_messages = Table('nexus_messages', meta, autoload = True, autoload_with = migrate_engine)
    nexus_messages.drop_column("priority")
