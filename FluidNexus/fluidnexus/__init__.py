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


from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.exceptions import Forbidden, NotFound
from sqlalchemy import engine_from_config

from pyramid_beaker import session_factory_from_settings, set_cache_regions_from_settings

from fluidnexus.models import initialize_sql, create_session
from fluidnexus.models import FormAlchemyRootFactory
from fluidnexus.views.views import notfound_view

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
    set_cache_regions_from_settings(settings)
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
    config.add_route('rss', '/feed/rss')

    # USERS/LOGIN
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('forgot_password', '/forgot_password')
    config.add_route('reset_password', '/reset_password/{token}')
    config.add_route('register_user', "/register")
    config.add_route('register_user_openid', "/register_openid")
    config.add_route("edit_users", "/admin/users")
    config.add_route("edit_user", "/admin/users/edit/{user_id}")
    config.add_route("view_user", "/users/{user_id}")

    # BLOG POSTS
    config.add_route("view_blog", "/blog/{page_num}")
    config.add_route("view_blog_nopagenum", "/blog")
    config.add_route("view_blog_post", "/blog/post/{post_id}")
    config.add_route("edit_blog", "/admin/blog") 
    config.add_route("edit_blog_post", "/admin/blog/edit/{post_id}")
    config.add_route("new_blog_post", "/admin/blog/new")

    # PAGES
    config.add_route("new_page", "/admin/page/new")
    config.add_route("edit_pages", "/admin/pages")
    config.add_route("edit_page", "/admin/pages/edit/{page_id}")
    #config.add_route("view_page", "/{page_location}")

    # SITE PAGES
    config.add_route("credits", "/credits")
    config.add_route("download", "/download")
    config.add_route("infos", "/infos")
    config.add_route("infos_concept", "/infos/concept")
    config.add_route("infos_manual", "/infos/manual")
    config.add_route("infos_screenshots", "/infos/screenshots")
    config.add_route("infos_nexus", "/infos/nexus")
    config.add_route("infos_faq", "/infos/faq")
    config.add_route("infos_videos", "/infos/videos")


    # NEXUS
    config.add_route("view_nexus_messages", "/nexus/{page_num}")
    config.add_route("view_nexus_messages_nopagenum", "/nexus")
    config.add_route("view_nexus_message", "/nexus/message/{message_id}")

    # API
    config.add_route("api_request_key", "/api/01/request_key")
    config.add_route("api_request_token", "/api/01/request_token/{appType}")
    config.add_route("api_authorize_token", "/api/01/authorize_token/{appType}")
    config.add_route("api_do_authorize_token", "/api/01/do_authorize_token/{appType}")
    config.add_route("api_access_token", "/api/01/access_token")
    config.add_route("api_nexus_messages_json", "/api/01/nexus/messages.json")
    config.add_route("api_nexus_messages_hash_json", "/api/01/nexus/messages/{hash}.json")
    config.add_route("api_nexus_hashes_json", "/api/01/nexus/hashes.json")
    config.add_route("api_nexus_hashes_hash_json", "/api/01/nexus/hashes/{hash}.json")
    # The following API method requires oauth authorization
    config.add_route("api_nexus_message_nonce", "/api/01/nexus/message/nonce.json") 
    # This API call requires the nonce retrieved through the previous call
    config.add_route("api_nexus_message_update", "/api/01/nexus/message/update.json") 


    config.formalchemy_admin('/admin', package="fluidnexus", view="fa.jquery.pyramid.ModelView", factory=FormAlchemyRootFactory)
    config.scan()
    return config.make_wsgi_app()

