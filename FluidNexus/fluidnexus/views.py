from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationStringFactory
from pyramid.renderers import get_renderer
from pyramid.security import authenticated_userid
from pyramid.url import route_url
from pyramid.view import view_config

from formalchemy import types, Field, FieldSet, Grid

import textile

from fluidnexus.models import DBSession
from fluidnexus.models import Post, User, Group, Comment, Page
import time

_ = TranslationStringFactory('fluidnexus')

save_name = _("Save")
delete_name = _("Delete")

@view_config(route_name = "home", renderer = "templates/home.pt")
def home(request):
    logged_in = authenticated_userid(request)
    return dict(title = "Fluid Nexus", logged_in = logged_in)

@view_config(route_name = "view_blog", renderer = "templates/blog.pt")
def view_blog(request):
    session = DBSession()
    posts = session.query(Post).join(User).order_by(desc(Post.modified_time)).all()

    # TODO
    # horribly inefficient; probably a much better way of doing things, perhaps in the template itself?
    modifiedPosts = []
    logged_in = authenticated_userid(request)
    for post in posts:
        # TODO
        # move these to classmethod
        post.username = post.user.username
        post.post_url = route_url("view_blog_post", request, post_id = post.id)
        modifiedPosts.append(post)

    return dict(title = _("Fluid Nexus Blog posts"), posts = modifiedPosts, logged_in = logged_in)

@view_config(route_name = "view_blog_post", renderer = "templates/blog_post.pt")
def view_blog_post(request):
    session = DBSession()
    logged_in = authenticated_userid(request)
    matchdict = request.matchdict
    post = session.query(Post).filter(Post.id == matchdict["post_id"]).one()
    user = session.query(User).filter(User.id == post.user_id).one()
    post.username = user.username
    post_comment_url = route_url("view_blog_post", request, post_id = post.id)

    fs = None

    # TODO
    # * make form validation better and more attractive
    # * add in field that asks for user to type word to submit form
    if 'submitted' in request.params:
        comment = Comment()
        fs = FieldSet(Comment, session = session, data=request.params)
        fs.configure(options = [fs.content.textarea(size=(45, 10)), fs.created_time.hidden(), fs.post_id.hidden()], exclude = [fs.post])
        valid = fs.validate()
        if valid:
            fs = None
            comment.name = fs.name.value
            comment.email = fs.email.value
            comment.homepage = fs.homepage.value
            comment.content = fs.content.value
            now = time.time()
            comment.created_time = now
            comment.post_id = post.id
            session.add(comment)

    comments = session.query(Comment).filter(Comment.post_id == post.id).order_by(desc(Comment.created_time))

    if (fs is None):
        fs = FieldSet(Comment, session = session)
        fs.configure(options = [fs.email.label(fs.email.label() + _(" (will not be shared)")), fs.content.textarea(size=(45, 10)), fs.created_time.hidden(), fs.post_id.hidden()], exclude = [fs.post])
    comment_form = fs.render()

    return dict(title = post.title + _(" || Fluid Nexus Blog Post"), post = post, logged_in = logged_in, comments = comments, comment_form = comment_form, post_comment_url = post_comment_url) 

@view_config(route_name = "edit_users", renderer = "templates/edit_users.pt")
def edit_users(request):
    session = DBSession()
    users = session.query(User).order_by(User.id).all()

    modifiedUsers = []
    for user in users:
        user.edit_url = route_url("edit_user", request, user_id = user.id)
        modifiedUsers.append(user)

    return dict(users = modifiedUsers)

@view_config(route_name = "edit_user", renderer = "templates/edit_user.pt")
def edit_user(request):
    session = DBSession()
    matchdict = request.matchdict
    user = session.query(User).join(User.groups).join(Group.group_info).filter(User.id == matchdict["user_id"]).one()

    fs = FieldSet(user)
    fs.configure(exclude = [fs["password"], fs["created_time"]])
    form = fs.render()
    return dict(form = form, username = user.username)

@view_config(route_name = "edit_blog", renderer = "templates/edit_blog.pt", permission = "edit_blog")
def edit_blog(request):
    session = DBSession()
    posts = session.query(Post).join(User).order_by(desc(Post.modified_time)).all()
    new_blog_post_url = route_url("new_blog_post", request)

    modifiedPosts = []
    for post in posts:
        post.formatted_time = time.ctime(post.modified_time)
        post.username = post.user.username
        post.post_url = route_url("edit_blog_post", request, post_id = post.id)
        modifiedPosts.append(post)

    # TODO
    # Figure out how to delete using checkboxes
    #g = Grid(Post, posts)
    #g.configure(options = [g["title"].readonly()], exclude = [g["modified_time"], g["user"], g["created_time"], g["content"]])
    #form = g.render()
    return dict(posts = modifiedPosts, new_blog_post_url = new_blog_post_url)

@view_config(route_name = "new_blog_post", renderer = "templates/new_blog_post.pt", permission = "edit_blog")
def new_blog_post(request):
    session = DBSession()
    print authenticated_userid(request)

    if 'submitted' in request.params:
        post = Post()
        fs = FieldSet(Post, data=request.params)
        post.title = fs.title.value
        post.content = fs.content.value
        now = time.time()
        post.modified_time = now
        post.created_time = now
        post.user_id = authenticated_userid(request)
        session.add(post)

        return HTTPFound(location = route_url("edit_blog", request))

    new_blog_post_url = route_url("new_blog_post", request)
    fs = FieldSet(Post, session = session)
    fs.configure(options=[fs.content.textarea(size=(45, 10))], exclude = [fs["modified_time"], fs["user"], fs["comments"], fs["created_time"]])
    form = fs.render()
    return dict(form = form, new_blog_post_url = new_blog_post_url)

@view_config(route_name = "edit_blog_post", renderer = "templates/edit_blog_post.pt", permission = "edit_blog")
def edit_blog_post(request):
    session = DBSession()
    matchdict = request.matchdict
    post = session.query(Post).filter(Post.id == matchdict["post_id"]).one()

    if 'submitted' in request.params:
        fs = FieldSet(post, data=request.params)
        # TODO
        # Not sure why this is necessary...shouldn't I just be able to pass the session to FieldSet and have it sync?
        post.title = fs.title.value
        post.content = fs.content.value
        post.modified_time = time.time()
        session.add(post)

        return HTTPFound(location = route_url("view_blog_post", request, post_id = post.id))

    if 'delete' in request.params:
        session.delete(post)

        return HTTPFound(location = route_url("edit_blog", request))


    edit_blog_post_url = route_url("edit_blog_post", request, post_id = post.id)
    fs = FieldSet(post)
    fs.configure(options=[fs.content.textarea(size=(45, 10))], exclude = [fs["modified_time"], fs["created_time"], fs["user"]])
    form = fs.render()
    return dict(form = form, title = post.title, edit_blog_post_url = edit_blog_post_url)

@view_config(route_name = "view_page", renderer = "templates/view_page.pt")
def view_page(request):
    """View a given page."""
    session = DBSession()
    matchdict = request.matchdict
    page_location = matchdict["page_location"]
    try:
        page = session.query(Page).filter(Page.location == page_location).one()
    except NoResultFound:
        return HTTPNotFound(detail = "Requested page not found.")

    return dict(title = page.title, content = textile.textile(page.content))

@view_config(route_name = "edit_pages", renderer="templates/edit_pages.pt", permission = "edit_pages")
def edit_pages(request):
    """List pages to edit."""
    session = DBSession()
    main = get_renderer('templates/admin.pt').implementation()
    pages = session.query(Page).join(User).order_by(desc(Page.modified_time)).all()
    logged_in = authenticated_userid(request)

    modifiedPages = []
    for page in pages:
        page.formatted_time = time.ctime(page.modified_time)
        page.username = page.user.username
        page.page_url = route_url("edit_page", request, page_id = page.id)
        modifiedPages.append(page)

    # TODO
    # Figure out how to delete using checkboxes
    new_page_url = route_url("new_page", request)
    return dict(main = main, title = "Edit pages", new_page_url = new_page_url, pages = modifiedPages, logged_in = logged_in)

@view_config(route_name = "edit_page", renderer = "templates/edit_page.pt", permission = "edit_pages")
def edit_page(request):
    """Edit a given page."""
    session = DBSession()
    logged_in = authenticated_userid(request)
    main = get_renderer('templates/admin.pt').implementation()
    matchdict = request.matchdict
    page = session.query(Page).join(User).filter(Page.id == matchdict["page_id"]).order_by(desc(Page.modified_time)).one()

    if 'submitted' in request.params:
        fs = FieldSet(page, data=request.params)
        # TODO
        # add validation
        # Not sure why this is necessary...shouldn't I just be able to pass the session to FieldSet and have it sync?
        page.title = fs.title.value
        page.content = fs.content.value
        page.modified_time = time.time()
        page.location = fs.location.value
        session.add(page)
        return HTTPFound(location = route_url("view_page", request, page_location = page.location))

    elif 'delete' in request.params:
        session.delete(page)
        return HTTPFound(location = route_url("edit_pages", request))



    edit_blog_post_url = route_url("edit_page", request, page_id = page.id)
    fs = FieldSet(page)
    fs.configure(options=[fs.content.textarea(size=(45, 10))], exclude = [fs["modified_time"], fs["created_time"], fs["user"]])
    form = fs.render()

    # TODO
    # Figure out how to delete using checkboxes
    return dict(main = main, title = "Edit '%s'" % page.title, save_name = save_name, delete_name = delete_name, form = form, logged_in = logged_in)

@view_config(route_name = "new_page", renderer = "templates/new_page.pt", permission="edit_pages")
def new_page(request):
    session = DBSession()
    main = get_renderer('templates/admin.pt').implementation()
    logged_in = authenticated_userid(request)

    if 'submitted' in request.params:
        page = Page()
        fs = FieldSet(Page, data=request.params)
        page.title = fs.title.value
        page.content = fs.content.value
        page.location = fs.location.value.lower()
        now = time.time()
        page.modified_time = now
        page.created_time = now
        page.user_id = authenticated_userid(request)
        session.add(page)

        return HTTPFound(location = route_url("edit_pages", request))

    new_page_url = route_url("new_page", request)
    fs = FieldSet(Page, session = session)
    fs.configure(options=[fs.content.textarea(size=(45, 10))], exclude = [fs["modified_time"], fs["user"], fs["created_time"]])
    form = fs.render()
    return dict(main = main, title = "Create new Fluid Nexus page", save_name = save_name, logged_in = logged_in, form = form)

@view_config(route_name = "openid", renderer = "templates/openid.pt")
def openid(request):
    logged_in = authenticated_userid(request)
    return dict(title = "OpenID login", logged_in = logged_in, message = "", login = "")

# Callback for openid library
def remember_me(context, request, result):
    print result

    return HTTPFound(location = route_url("openid", request))
