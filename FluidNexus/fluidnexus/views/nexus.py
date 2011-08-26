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
import os

from sqlalchemy import desc

from beaker.cache import cache_region, CacheManager
from beaker.util import parse_cache_config_options

from pyramid.i18n import TranslationStringFactory
from pyramid.url import route_url
from pyramid.view import view_config

from fluidnexus.models import DBSession
from fluidnexus.models import User, NexusMessage
from pager import Pager

_ = TranslationStringFactory('fluidnexus')

cache_opts = {
    'cache.data_dir': '/tmp/cache/data',
    'cache.lock_dir': '/tmp/cache/lock',
    'cache.regions': 'short_term, long_term',
    'cache.short_term.type': 'ext:memcached',
    'cache.short_term.url': '127.0.0.1:11211',
    'cache.short_term.expire': '60',
    'cache.medium_term.type': 'ext:memcached',
    'cache.medium_term.url': '127.0.0.1:11211',
    'cache.medium_term.expire': '3600',
    'cache.long_term.type': 'ext:memcached',
    'cache.long_term.url': '127.0.0.1:11211',
    'cache.long_term.expire': '86400',
}
cache = CacheManager(**parse_cache_config_options(cache_opts))

def doNexusMessages(request = None, page_num = 1, limit = 10):
    session = DBSession()
    #messages = session.query(NexusMessage).join(User).order_by(desc(NexusMessage.created_time)).all()

    p = Pager(session.query(NexusMessage).join(User).order_by(desc(NexusMessage.created_time)), page_num, limit)
    messages = p.results

    # TODO
    # horribly inefficient; probably a much better way of doing things, perhaps in the template itself?
    modifiedMessages= []
    for message in messages:
        # TODO
        # move these to classmethod
        message.username = message.user.username
        message.message_url = route_url("view_nexus_message", request, message_id = message.id)
        message.formattedContent = message.getFormattedContent()
        message.ISOTime = message.getISOTime()
        message.formattedTime = message.getFormattedTime()
        if (message.attachment_path != ""):
            fullPath, extension = os.path.splitext(message.attachment_original_filename)
            message.massaged_attachment_path = "/static/attachments/" + os.path.basename(message.attachment_path) + extension
            message.massaged_attachment_path_tn = "/static/attachments/" + os.path.basename(message.attachment_path) + "_tn" + extension
        modifiedMessages.append(message)

    if (page_num < p.pages):
        next_page = page_num + 1
    else:
        next_page = 0

    if (page_num > 1):
        previous_page = page_num - 1
    else:
        previous_page = 0

    return dict(title = _("Nexus Messages"), messages = modifiedMessages, pages = p.pages, page_num = page_num, previous_page = previous_page, next_page = next_page)

@view_config(route_name = "view_nexus_messages", renderer = "../templates/nexus_messages.pt")
def view_nexus_messages(request):
    matchdict = request.matchdict
    page_num = matchdict["page_num"]
    short_term = cache.regions["short_term"]
    view_nexus_cache = cache.get_cache("view_nexus", **short_term)

    def nexusMessages():
        result = doNexusMessages(request = request, page_num = int(page_num))
        return result

    results = view_nexus_cache.get(key = hashlib.sha256(str(request) + str(page_num)).hexdigest(),
        createfunc = nexusMessages
    )
    return results
@view_config(route_name = "view_nexus_messages_nopagenum", renderer = "../templates/nexus_messages.pt")
def view_nexus_messages_nopagenum(request):

    short_term = cache.regions["short_term"]
    view_nexus_cache = cache.get_cache("view_nexus", **short_term)
    page_num = 1

    def nexusMessages():
        result = doNexusMessages(request = request, page_num = page_num)
        return result

    results = view_nexus_cache.get(key = hashlib.sha256(str(request) + str(page_num)).hexdigest(),
        createfunc = nexusMessages
    )
    return results

@view_config(route_name = "view_nexus_message", renderer = "../templates/nexus_message.pt")
def view_nexus_message(request):
    session = DBSession()
    matchdict = request.matchdict
    message = session.query(NexusMessage).filter(NexusMessage.id == matchdict["message_id"]).one()
    user = session.query(User).filter(User.id == message.user_id).one()
    message.username = user.username
    message.formattedContent = message.getFormattedContent()
    message.ISOTime = message.getISOTime()
    message.formattedTime = message.getFormattedTime()

    # TODO
    # Add in comment supports; needs a new, separate NexusComment table
    #message_comment_url = route_url("view_nexus_message", request, message_id = message.id)

    return dict(title = message.title + _(" || Nexus Message"), message = message) 
