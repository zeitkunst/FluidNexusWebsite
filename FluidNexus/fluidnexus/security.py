from fluidnexus.models import DBSession, User, Group, GroupInfo

def groupfinder(userid, request):
    session = DBSession()
    user = session.query(User).join(User.groups).join(Group.group_info).filter(User.id==userid).one()
    groupNames = []
    if (user is not None):
        groups = user.groups
        for group in groups:
            groupNames.append("group:" + group.group_info.group_name)

    return groupNames


