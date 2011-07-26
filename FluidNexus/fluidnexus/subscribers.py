from pyramid.renderers import get_renderer
from pyramid.events import subscriber
from pyramid.events import BeforeRender, NewRequest
from pyramid.security import authenticated_userid

@subscriber(BeforeRender)
def add_base_template(event):
    base = get_renderer('templates/base.pt').implementation()
    event.update({'base': base})

@subscriber(NewRequest)
def addRequestVariables(event):
    event.request.title = "Fluid Nexus"
    event.request.logged_in = authenticated_userid(event.request)
