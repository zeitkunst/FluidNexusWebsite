import os

from sqlalchemy import desc

from pyramid.i18n import TranslationStringFactory
from pyramid.view import view_config

from fluidnexus.models import DBSession
from fluidnexus.models import User, NexusMessage
from pager import Pager

_ = TranslationStringFactory('fluidnexus')

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
    return doNexusMessages(request = request, page_num = int(page_num))

@view_config(route_name = "view_nexus_messages_nopagenum", renderer = "../templates/nexus_messages.pt")
def view_nexus_messages_nopagenum(request):
    return doNexusMessages(request = request, page_num = 1)

