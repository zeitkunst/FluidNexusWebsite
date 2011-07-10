import hashlib
import bcrypt

from sqlalchemy.orm.exc import NoResultFound

from pyramid.httpexceptions import HTTPFound
from pyramid.security import authenticated_userid
from pyramid.security import remember
from pyramid.security import forget
from pyramid.url import route_url
from pyramid.view import view_config

from fluidnexus.models import DBSession, User
from fluidnexus.security import USERS

@view_config(route_name = "login", renderer = "templates/login.pt")
def login(request):
    login_url = route_url('login', request)
    logged_in = authenticated_userid(request)
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

        if (User.checkPassword(login, password)):
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
    return HTTPFound(location = route_url('home', request),
                     headers = headers)
