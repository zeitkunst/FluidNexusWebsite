from fluidnexus.models import DBSession, User, Group, GroupInfo

USERS = {'editor':'editor',
         'viewer':'viewer'}
GROUPS = {'editor':['group:blog']}

def groupfinderOld(userid, request):
    if userid in USERS:
        return GROUPS.get(userid, [])

def groupfinder(userid, request):
    session = DBSession()
    user = session.query(User).join(User.groups).join(Group.group_info).filter(User.id==userid).one()
    groupNames = []
    if (user is not None):
        groups = user.groups
        for group in groups:
            groupNames.append("group:" + group.group_info.name)

    return groupNames


