from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from sqlalchemy import engine_from_config

from pyramid_beaker import session_factory_from_settings

from fluidnexus.models import initialize_sql, create_session
from fluidnexus.models import FormAlchemyRootFactory

from fluidnexus.security import groupfinder

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    create_session(engine)
    #initialize_sql()
    authn_policy = AuthTktAuthenticationPolicy('fluidnexus', callback=groupfinder)
    authz_policy = ACLAuthorizationPolicy()
    session_factory = session_factory_from_settings(settings)
    config = Configurator(settings=settings,
                          session_factory = session_factory,
                         root_factory='fluidnexus.models.RootFactory',
                         authentication_policy = authn_policy,
                         authorization_policy=authz_policy)
    config.include("pyramid_formalchemy")
    config.include("fa.jquery")
    config.add_static_view('static', 'fluidnexus:static')

    config.add_route('home', '/')
    config.add_route('openid', '/openid')
    config.add_route("check_openid", pattern = "/check_openid")
    config.add_route("verify_openid", pattern = "/do_openid", view = "pyramid_openid.verify_openid")
    #config.add_view(route_name = "verify_openid", view = "pyramid_openid.verify_openid")

    # USERS/LOGIN
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('register_user', "/register")
    config.add_route('register_user_openid', "/register_openid")
    config.add_route("edit_users", "/admin/users")
    config.add_route("edit_user", "/admin/users/edit/{user_id}")
    config.add_route("view_user", "/users/{user_id}")

    # BLOG POSTS
    config.add_route("view_blog", "/blog")
    config.add_route("view_blog_post", "/blog/{post_id}")
    config.add_route("edit_blog", "/admin/blog") 
    config.add_route("edit_blog_post", "/admin/blog/edit/{post_id}")
    config.add_route("new_blog_post", "/admin/blog/new")

    # PAGES
    config.add_route("new_page", "/admin/page/new")
    config.add_route("edit_pages", "/admin/pages")
    config.add_route("edit_page", "/admin/pages/edit/{page_id}")
    config.add_route("view_page", "/{page_location}")

    # NEXUS
    config.add_route("nexus_messages", "/nexus")

    # API
    #

    config.add_view('fluidnexus.views.views.forbidden',
                    context='pyramid.exceptions.Forbidden')
    config.formalchemy_admin('/admin', package="fluidnexus", view="fa.jquery.pyramid.ModelView", factory=FormAlchemyRootFactory)
    config.scan()
    return config.make_wsgi_app()

