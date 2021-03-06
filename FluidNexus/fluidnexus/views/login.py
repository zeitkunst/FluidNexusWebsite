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

import hashlib
import bcrypt

from sqlalchemy.orm.exc import NoResultFound

from pyramid.httpexceptions import HTTPFound
from pyramid.i18n import TranslationStringFactory
from pyramid.security import authenticated_userid
from pyramid.security import remember
from pyramid.security import forget
from pyramid.url import route_url
from pyramid.view import view_config

from fluidnexus.models import DBSession, User

_ = TranslationStringFactory('fluidnexus')

@view_config(route_name = "login", renderer = "../templates/login.pt")
def login(request):
    login_url = route_url('login', request)
    logged_in = authenticated_userid(request)

    if (logged_in):
        request.session.flash(_("You are already logged in and therefore cannot register for a new account."))
        return HTTPFound(location = route_url("home", request))

    referrer = request.url
    if (referrer == login_url):
        referrer = '/' # never use the login form itself as came_from
    
    came_from = request.params.get('came_from', referrer)
    login = ''
    password = ''

    if 'submitted' in request.params:
        session = DBSession()
        login = request.params['login']
        password = request.params['password']

        if (User.checkPassword(login, password) and (User.checkTypeByUsername(login) != User.FORGOT_PASSWORD)):
            request.session["username"] = login
            headers = remember(request, User.getID(login))
            return HTTPFound(location = came_from, headers = headers)

        request.session.flash('Failed login')

    return dict(url = request.application_url + "/login",
                came_from = came_from,
                login = login,
                title = "Fluid Nexus login",
                logged_in = logged_in,
                password = password,
               )

@view_config(route_name = "logout")
def logout(request):
    headers = forget(request)
    request.session.flash(_("You have successfully logged out"))
    return HTTPFound(location = route_url('home', request),
                     headers = headers)
