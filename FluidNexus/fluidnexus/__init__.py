from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from sqlalchemy import engine_from_config

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
    config = Configurator(settings=settings,
                         root_factory='fluidnexus.models.RootFactory',
                         authentication_policy = authn_policy,
                         authorization_policy=authz_policy)
    config.include("pyramid_formalchemy")
    config.include("fa.jquery")
    config.add_static_view('static', 'fluidnexus:static')

    # USERS/LOGIN
    config.add_route('login', '/login',
                     view = 'fluidnexus.login.login',
                     view_renderer='fluidnexus:templates/login.pt')
    config.add_route('logout', '/logout',
                    view = 'fluidnexus.login.logout')
    config.add_route("edit_users", "/admin/users", view="fluidnexus.views.edit_users", view_renderer="fluidnexus:templates/edit_users.pt")
    config.add_route("edit_user", "/admin/users/edit/{user_id}", view="fluidnexus.views.edit_user", view_renderer="fluidnexus:templates/edit_user.pt")

    # BLOG POSTS
    config.add_route("view_blog", "/blog", view="fluidnexus.views.view_blog", view_renderer="fluidnexus:templates/blog.pt")
    config.add_route("view_blog_post", "/blog/{post_id}", view="fluidnexus.views.view_blog_post", view_renderer="fluidnexus:templates/blog_post.pt")
    config.add_route("edit_blog", "/admin/blog", 
                     view="fluidnexus.views.edit_blog", 
                     view_renderer="fluidnexus:templates/edit_blog.pt", permission="edit_blog")
    config.add_route("edit_blog_post", "/admin/blog/edit/{post_id}", view="fluidnexus.views.edit_blog_post", view_renderer="fluidnexus:templates/edit_blog_post.pt", permission="edit_blog")
    config.add_route("new_blog_post", "/admin/blog/new", 
                     view="fluidnexus.views.new_blog_post", 
                     view_renderer="fluidnexus:templates/new_blog_post.pt", permission="edit_blog")

    # PAGES
    config.add_route("new_page", "/admin/page/new", 
                     view="fluidnexus.views.new_page", 
                     view_renderer="fluidnexus:templates/new_page.pt", permission="edit_pages")
    config.add_route("edit_pages", "/admin/pages", 
                     view="fluidnexus.views.edit_pages", 
                     view_renderer="fluidnexus:templates/edit_pages.pt", permission="edit_pages")
    config.add_route("edit_page", "/admin/pages/edit/{page_id}", view="fluidnexus.views.edit_page", view_renderer="fluidnexus:templates/edit_page.pt", permission="edit_pages")
    config.add_route("view_page", "/{page_location}", view="fluidnexus.views.view_page", view_renderer="fluidnexus:templates/view_page.pt")

    config.add_view('fluidnexus.login.login',
                    renderer='fluidnexus:templates/login.pt',
                    context='pyramid.exceptions.Forbidden')
    config.formalchemy_admin('/admin', package="fluidnexus", view="fa.jquery.pyramid.ModelView", factory=FormAlchemyRootFactory)
    config.scan()
    return config.make_wsgi_app()

