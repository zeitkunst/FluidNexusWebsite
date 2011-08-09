# This file is part of the Fluid Nexus Website.
# 
# the Fluid Nexus Website is free software: you can redistribute it and/or 
# modify it under the terms of the GNU Affero General Public License as 
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
# 
# the Fluid Nexus Website is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with the Fluid Nexus Website.  If not, see 
# <http://www.gnu.org/licenses/>.


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


