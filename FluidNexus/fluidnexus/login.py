import hashlib
import bcrypt

from sqlalchemy.orm.exc import NoResultFound

from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from pyramid.security import forget
from pyramid.url import route_url
from pyramid.view import view_config

from fluidnexus.models import DBSession, User
from fluidnexus.security import USERS

@view_config(route_name = "login", renderer = "templates/login.pt")
def login(request):
    login_url = route_url('login', request)
    referrer = request.url
    if (referrer == login_url):
        referrer = '/blog' # never use the login form itself as came_from
    
    came_from = request.params.get('came_from', referrer)
    message = ''
    login = ''
    password = ''

    if 'submitted' in request.params:
        session = DBSession()
        login = request.params['login']
        password = request.params['password']
        try:
            hashed_password = session.query(User.password).filter(User.username==login).one()[0]
            #user = session.query(User).filter(User.username==login).filter(User.password==hashlib.sha256(password).hexdigest()).one()
            user = session.query(User).filter(User.username==login).filter(User.password==bcrypt.hashpw(password, hashed_password)).one()
        except NoResultFound:
            user = None
        if (user is not None):
            headers = remember(request, user.id)
            return HTTPFound(location = came_from, headers = headers)

        message = 'Failed login'

    return dict(message = message,
                url = request.application_url + "/login",
                came_from = came_from,
                login = login,
                password = password,
               )

@view_config(route_name = "logout")
def logout(request):
    headers = forget(request)
    return HTTPFound(location = route_url('view_blog', request),
                     headers = headers)
