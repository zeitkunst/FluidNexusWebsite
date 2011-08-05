# standard imports
import datetime
import hashlib
from operator import itemgetter, attrgetter
import random
import time

# Other module imports
import textile
import bcrypt
import PyRSS2Gen

from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound

from pyramid.exceptions import Forbidden, NotFound
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPForbidden
from pyramid.i18n import TranslationStringFactory
from pyramid.response import Response
from pyramid.security import authenticated_userid
from pyramid.security import remember
from pyramid.url import route_url
from pyramid.view import view_config

from formalchemy import types, Field, FieldSet, Grid

# My imports
from fluidnexus.models import DBSession
from fluidnexus.models import Post, User, Group, Comment, Page, OpenID, ConsumerKeySecret, Token, NexusMessage, ForgotPassword
from fluidnexus.forms import UserFieldSet, UserNoPasswordFieldSet, RegisterUserFieldSet, OpenIDUserFieldSet, CommentFieldSet, ForgotPasswordFieldSet, ResetPasswordFieldSet
from pager import Pager


_ = TranslationStringFactory('fluidnexus')

save_name = _("Save")
delete_name = _("Delete")


def doViewBlog(request = None, page_num = 1, limit = 10):
    session = DBSession()


    p = Pager(session.query(Post).join(User).order_by(desc(Post.created_time)), page_num, limit)
    posts = p.results

    # TODO
    # horribly inefficient; probably a much better way of doing things, perhaps in the template itself?
    modifiedPosts = []
    for post in posts:
        # TODO
        # move these to classmethod
        post.username = post.user.username
        post.post_url = route_url("view_blog_post", request, post_id = post.id)
        modifiedPosts.append(post)

    if (page_num < p.pages):
        next_page = page_num + 1
    else:
        next_page = 0

    if (page_num > 1):
        previous_page = page_num - 1
    else:
        previous_page = 0

    return dict(title = _("Nexus Messages"), posts = modifiedPosts, pages = p.pages, page_num = page_num, previous_page = previous_page, next_page = next_page)

@view_config(route_name = "home", renderer = "../templates/home.pt")
def home(request):
    return dict(title = "Fluid Nexus")

@view_config(route_name = "view_blog", renderer = "../templates/blog.pt")
def view_blog(request):
    session = DBSession()

    matchdict = request.matchdict
    page_num = matchdict["page_num"]

    return doViewBlog(request, page_num = int(page_num))

@view_config(route_name = "view_blog_nopagenum", renderer = "../templates/blog.pt")
def view_blog_nopagenum(request):
    session = DBSession()

    return doViewBlog(request, page_num = 1)


@view_config(route_name = "view_blog_post", renderer = "../templates/blog_post.pt")
def view_blog_post(request):
    session = DBSession()
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
        fs = CommentFieldSet().bind(Comment, session = session, data = request.POST or None)
        valid = fs.validate()
        if valid:
            comment.name = fs.name.value
            comment.email = fs.email.value
            comment.homepage = fs.homepage.value
            comment.content = fs.content.value
            now = time.time()
            comment.created_time = now
            comment.post_id = post.id
            session.add(comment)
            request.session.flash(_("Your comment was successfully posted."))
            fs = None

    comments = session.query(Comment).filter(Comment.post_id == post.id).order_by(desc(Comment.created_time))

    if (fs is None):
        fs = CommentFieldSet().bind(Comment, session = session)

    comment_form = fs.render()

    return dict(title = post.title + _(" || Fluid Nexus Blog Post"), post = post, comments = comments, comment_form = comment_form, post_comment_url = post_comment_url) 

@view_config(route_name = "edit_users", renderer = "../templates/edit_users.pt", permission = "admin")
def edit_users(request):
    session = DBSession()
    users = session.query(User).order_by(User.id).all()

    modifiedUsers = []
    for user in users:
        user.edit_url = route_url("edit_user", request, user_id = user.id)
        modifiedUsers.append(user)

    return dict(users = modifiedUsers, title = _("Edit users"))

@view_config(route_name = "edit_user", renderer = "../templates/edit_user.pt")
def edit_user(request):
    session = DBSession()
    matchdict = request.matchdict

    if (request.logged_in != int(matchdict["user_id"])):
        return HTTPForbidden(_("You are not allowed to view information about a user other than yourself."))

    user = session.query(User).join(User.groups).join(Group.group_info).filter(User.id == matchdict["user_id"]).one()

    if (user.user_type == User.OPENID):
        fs = UserNoPasswordFieldSet().bind(user, session = session, data = request.POST or None)
    else:
        fs = UserFieldSet().bind(user, session = session, data = request.POST or None)
    if 'submitted' in request.params:
        valid = fs.validate()
        if valid:
            if user.user_type == User.NORMAL:
                user.password = bcrypt.hashpw(fs.password1.value, bcrypt.gensalt())
            fs.sync()
            return HTTPFound(location = route_url("view_user", request, user_id = request.logged_in))

    form = fs.render()
    return dict(form = form, title = _("Edit") + " " + user.username)

@view_config(route_name = "register_user", renderer = "../templates/register_user.pt")
def register_user(request):
    session = DBSession()
    matchdict = request.matchdict

    if (request.logged_in):
        request.session.flash(_("You are already logged in and therefore cannot register for a new account."))
        return HTTPFound(location = route_url("home", request))

    login_url = route_url('login', request)
    referrer = request.url
    if (referrer == login_url):
        referrer = '/' # never use the login form itself as came_from
    
    came_from = request.params.get('came_from', referrer)

    fs = None

    if 'submitted' in request.params:
        fs = RegisterUserFieldSet().bind(User, session = session, data = request.params or None)
        valid = fs.validate()
        if valid:
            user = User()
            password = bcrypt.hashpw(fs.password1.value, bcrypt.gensalt())

            # TODO
            # Shouldn't have to do this, but doing it for simplicity now
            user.username = fs.username.value
            user.password = password
            user.given_name = fs.given_name.value
            user.surname = fs.surname.value
            user.homepage = fs.homepage.value
            #user.email = fs.email.value
            user.email = bcrypt.hashpw(fs.email.value, bcrypt.gensalt())
            user.created_time =  time.time()
            user.user_type = User.NORMAL
            session.add(user)
            session.flush()

            User.addToGroup(fs.username.value, "nexus")
            request.session["username"] = fs.username.value
            headers = remember(request, User.getID(fs.username.value))
            request.session.flash(_("You have successfully created a new account!"))
            return HTTPFound(location = route_url("home", request), headers = headers)

    if (fs is None):
        fs = RegisterUserFieldSet().bind(User, session = session)
    form = fs.render()
    return dict(form = form, title = _("Register new user"))

@view_config(route_name = "register_user_openid", renderer = "../templates/register_user.pt")
def register_user_openid(request):
    session = DBSession()
    matchdict = request.matchdict

    if (request.logged_in):
        request.session.flash(_("You are already logged in and therefore cannot register for a new account."))
        return HTTPFound(location = route_url("home", request))

    fs = OpenIDUserFieldSet().bind(User, session = session)
    fs.append(Field("openid_url", value = request.params.get("openid_url", "")).hidden())

    if 'submitted' in request.params:
        fs = OpenIDUserFieldSet().bind(User, session = session, data = request.params or None)
        valid = fs.validate()
        if valid:
            user = User()

            # TODO
            # Shouldn't have to do this, but doing it for simplicity now
            # Should validate that the username is unique
            user.username = fs.username.value
            user.given_name = fs.given_name.value
            user.surname = fs.surname.value
            user.homepage = fs.homepage.value
            user.user_type = User.OPENID
            now = time.time()
            user.created_time = now
            user.password = bcrypt.hashpw(str(int(now)), bcrypt.gensalt())
            session.add(user)
            session.flush()

            User.addToGroup(fs.username.value, "nexus")
            request.session["username"] = fs.username.value
            user_id = User.getID(fs.username.value)

            openid = OpenID(openid_url = request.params.get("openid_url", ""), user_id = user_id)
            session.add(openid)

            headers = remember(request, user_id)
            request.session["username"] = fs.username.value
            request.session.flash(_("You have successfully registered!"))
            return HTTPFound(location = route_url("home", request), headers = headers)

    form = fs.render()
    return dict(form = form, title = _("Register new user"))

@view_config(route_name = "reset_password", renderer = "../templates/reset_password.pt")
def reset_password(request):
    session = DBSession()
    matchdict = request.matchdict
    token = matchdict["token"]

    forgotPassword = ForgotPassword.getByToken(token)
    if (not forgotPassword):
        request.session.flash(_("Reset password token not found in database."))
        return HTTPFound(location = route_url("home", request))

    if (request.logged_in):
        request.session.flash(_("You are already logged in and therefore cannot reset a password."))
        return HTTPFound(location = route_url("home", request))

    login_url = route_url('login', request)
    referrer = request.url
    if (referrer == login_url):
        referrer = '/' # never use the login form itself as came_from
    
    came_from = request.params.get('came_from', referrer)

    user = User.getByID(forgotPassword.user.id)

    fs = None
    
    if 'submitted' in request.params:
        fs = ResetPasswordFieldSet().bind(User, session = session, data = request.params or None)
        valid = fs.validate()
        if valid:
            user = User.getByID(request.params["user_id"])
            password = bcrypt.hashpw(fs.password1.value, bcrypt.gensalt())
            user.password = password
            user.user_type = User.NORMAL
            session.add(user)
            session.flush()

            session.query(ForgotPassword).filter(ForgotPassword.user_id == user.id).delete()

            request.session["username"] = user.username
            headers = remember(request, user.id)
            request.session.flash(_("You have successfully updated your password!"))
            return HTTPFound(location = route_url("home", request), headers = headers)

    if (fs is None):
        fs = ResetPasswordFieldSet().bind(User, session = session)
    form = fs.render()
    return dict(form = form, user_id = user.id, title = _("Forgot your password?"))

@view_config(route_name = "forgot_password", renderer = "../templates/forgot_password.pt")
def forgot_password(request):
    session = DBSession()
    matchdict = request.matchdict

    if (request.logged_in):
        request.session.flash(_("You are already logged in and therefore cannot request a new password."))
        return HTTPFound(location = route_url("home", request))

    login_url = route_url('login', request)
    referrer = request.url
    if (referrer == login_url):
        referrer = '/' # never use the login form itself as came_from
    
    came_from = request.params.get('came_from', referrer)

    fs = None

    if 'submitted' in request.params:
        fs = ForgotPasswordFieldSet().bind(User, session = session, data = request.params or None)
        valid_user = User.checkEmail(fs.username.value, fs.email.value)

        if (not valid_user):
            request.session.flash(_("E-mail and password combination do not match."))
            return HTTPFound(location = route_url("home", request))

        #user = User.getByEmail(fs.email.value)

        token = str(time.time())

        # Generate salt
        for x in xrange(0, 10):
            token += str(random.randint(0, 100))
        token = hashlib.sha256(token).hexdigest()

        fp = ForgotPassword(token = token)
        fp.user_id = valid_user.id
        session.add(fp)

        valid_user.user_type = User.FORGOT_PASSWORD
        session.add(valid_user)

        # Import smtplib for the actual sending function
        import smtplib
        
        # Import the email modules we'll need
        from email.mime.text import MIMEText

        text = """Please go to the following link to reset your password:

http://fluidnexus.net/reset_password/%s

If you have any questions please reply to this e-mail.

Best,

fluidnexus.net""" % token
        msg = MIMEText(text)
        msg["Subject"] = "Forgotten password for %s" % (fs.email.value)
        msg["From"] = "fluidnexux@fluidnexus.net"
        msg["To"] = fs.email.value
        s = smtplib.SMTP("localhost")
        s.sendmail("fluidnexus@fluidNexus.net", [fs.email.value], msg.as_string())
        s.quit()

        request.session.flash(_("Please check your e-mail for the link to reset your password."))
        return HTTPFound(location = route_url("home", request))

    if (fs is None):
        fs = ForgotPasswordFieldSet().bind(User, session = session)
    form = fs.render()
    return dict(form = form, title = _("Forgot your password?"))


@view_config(route_name = "view_user", renderer = "../templates/view_user.pt")
def view_user(request):
    # TODO
    # Add in auth tokens (if exists) and access tokens (if exists)
    session = DBSession()
    matchdict = request.matchdict
    
    if (request.logged_in != int(matchdict["user_id"])):
        return HTTPForbidden(_("You are not allowed to view information about a user other than yourself."))

    user = session.query(User).join(User.groups).join(Group.group_info).filter(User.id == matchdict["user_id"]).one()


    request_key_url = ""
    key = ""
    secret = ""
    token = ""
    token_secret = ""

    keySecret = ConsumerKeySecret.getByUserID(request.logged_in)
    if (keySecret):
        key = keySecret.consumer_key
        secret = keySecret.consumer_secret

        tokenData = Token.getTokenByConsumerID(keySecret.id)
        if (tokenData):
            token = tokenData.token
            token_secret = tokenData.token_secret

    else:
        request_key_url = route_url("api_request_key", request)

    return dict(username = user.username, homepage = user.homepage, title = _("Viewing ") + " " + user.username, key = key, secret = secret, token = token, token_secret = token_secret, request_key_url = request_key_url)



@view_config(route_name = "edit_blog", renderer = "../templates/edit_blog.pt", permission = "edit_blog")
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
    return dict(title = _("Edit blog posts"), posts = modifiedPosts, new_blog_post_url = new_blog_post_url)

@view_config(route_name = "new_blog_post", renderer = "../templates/new_blog_post.pt", permission = "edit_blog")
def new_blog_post(request):
    session = DBSession()

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
    return dict(title = _("New Fluid Nexus Blog Post"), form = form, new_blog_post_url = new_blog_post_url)

@view_config(route_name = "edit_blog_post", renderer = "../templates/edit_blog_post.pt", permission = "edit_blog")
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

@view_config(route_name = "infos", renderer = "../templates/infos.pt")
def infos(request):
    """Infos page."""
    session = DBSession()

    return dict(title = _("Fluid Nexus Infos"))


@view_config(route_name = "infos_concept", renderer = "../templates/concept.pt")
def concept(request):
    """Concept page."""
    session = DBSession()

    return dict(title = _("Fluid Nexus Concept"))

@view_config(route_name = "infos_faq", renderer = "../templates/faq.pt")
def faq(request):
    """FAQ page."""
    session = DBSession()

    return dict(title = _("Fluid Nexus FAQ"))

@view_config(route_name = "infos_videos", renderer = "../templates/videos.pt")
def videos(request):
    """Videos page."""
    session = DBSession()

    return dict(title = _("Fluid Nexus Videos"))


@view_config(route_name = "infos_manual", renderer = "../templates/manual.pt")
def manual(request):
    """Manual page."""
    session = DBSession()

    return dict(title = _("Fluid Nexus Manual"))

@view_config(route_name = "infos_screenshots", renderer = "../templates/screenshots.pt")
def screenshots(request):
    """Screenshots page."""
    session = DBSession()

    return dict(title = _("Fluid Nexus Screenshots"))

@view_config(route_name = "infos_nexus", renderer = "../templates/nexus.pt")
def nexus(request):
    """Nexus info page."""
    session = DBSession()

    return dict(title = _("Nexus Information"))


@view_config(route_name = "credits", renderer = "../templates/credits.pt")
def credits(request):
    """Credits page."""

    return dict(title = _("Fluid Nexus Credits"))

@view_config(route_name = "download", renderer = "../templates/download.pt")
def download(request):
    """Download page."""

    return dict(title = _("Fluid Nexus Download"))


@view_config(route_name = "view_page", renderer = "../templates/view_page.pt")
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

@view_config(route_name = "edit_pages", renderer="../templates/edit_pages.pt", permission = "edit_pages")
def edit_pages(request):
    """List pages to edit."""
    session = DBSession()
    pages = session.query(Page).join(User).order_by(desc(Page.modified_time)).all()
    modifiedPages = []
    for page in pages:
        page.formatted_time = time.ctime(page.modified_time)
        page.username = page.user.username
        page.page_url = route_url("edit_page", request, page_id = page.id)
        modifiedPages.append(page)

    # TODO
    # Figure out how to delete using checkboxes
    new_page_url = route_url("new_page", request)
    return dict(title = "Edit pages", new_page_url = new_page_url, pages = modifiedPages)

@view_config(route_name = "edit_page", renderer = "../templates/edit_page.pt", permission = "edit_pages")
def edit_page(request):
    """Edit a given page."""
    session = DBSession()
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
    return dict(title = "Edit '%s'" % page.title, save_name = save_name, delete_name = delete_name, form = form)

@view_config(route_name = "new_page", renderer = "../templates/new_page.pt", permission="edit_pages")
def new_page(request):
    session = DBSession()

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
    return dict(title = "Create new Fluid Nexus page", save_name = save_name, form = form)

@view_config(renderer = "../templates/forbidden.pt", context = Forbidden)
def forbidden_view(request):
    """We get here if somebody tries to access a resource they do not have access to."""
    request.session.flash(_("You do not have access to the requested resource.  Either login using an account that does have access, or contact the administrators of the site."))
    return dict(title = _("403 Forbidden"), forbidden = request.exception)
    #return HTTPFound(location = route_url("home", request))

@view_config(renderer = "../templates/notfound.pt", context = NotFound)
def notfound_view(request):
    return dict(title = _("404 Not Found"), notfound = request.exception.args[0])

@view_config(route_name = "openid", renderer = "../templates/openid.pt")
def openid(request):

    if (request.logged_in):
        request.session.flash(_("You are already logged in and therefore cannot register for a new account."))
        return HTTPFound(location = route_url("home", request))
    
    return dict(title = _("OpenID login"), login = "") 

# Callback for openid library
def remember_me(context, request, result):
    openid_url = result["identity_url"]
    
    user = OpenID.checkOpenIDURL(openid_url)
    if (user):
        request.session["username"] = user.username
        headers = remember(request, user.id)
        request.session.flash(_("Successfully logged in!"))
        return HTTPFound(location = route_url("home", request), headers = headers)
    else:
        request.session.flash(_("You now need to register after validating your OpenID"))
        return HTTPFound(location = route_url("register_user_openid", request, _query = {"openid_url": openid_url}))


@view_config(route_name = "rss")
def rss(request):
    num_posts = 10
    num_nexus = 10
    session = DBSession()

    posts = session.query(Post).join(User).order_by(desc(Post.created_time)).limit(num_posts)
    nexus = session.query(NexusMessage).join(User).order_by(desc(NexusMessage.created_time)).limit(num_nexus)

    items = []

    # add a link to each item
    newPosts = []
    for post in posts:
        link = "http://fluidnexus.net/blog/post/" + str(post.id)
        setattr(post, "link", link)
        setattr(post, "guid", link)
        setattr(post, "categories", ["blog"])
        newPosts.append(post)
    [items.append(post) for post in newPosts]

    newNexus = []
    for message in nexus:
        link = "http://fluidnexus.net/nexus"
        setattr(message, "link", link)
        setattr(message, "guid", message.message_hash)
        setattr(message, "categories", ["nexus"])
        newNexus.append(message)
    [items.append(message) for message in newNexus]

    items = sorted(items, key=attrgetter("created_time"), reverse = True)    

    rssItems = []

    for item in items:
        rssItem = PyRSS2Gen.RSSItem(title = item.title,
            description = item.content,
            pubDate = datetime.datetime.fromtimestamp(item.created_time),
            link = item.link,
            guid = PyRSS2Gen.Guid(item.guid),
            categories = item.categories,
            author = item.user.username)
        rssItems.append(rssItem)

    rss = PyRSS2Gen.RSS2(
        title = "Fluid Nexus RSS Feed",
        link = "http://fluidnexus.net/feed/rss",
        description = "RSS feed of Nexus and Blog posts from Fluid Nexus",
        lastBuildDate = datetime.datetime.utcnow(),
        items = rssItems
    )

    return Response(rss.to_xml(encoding = "utf-8"), content_type="application/rss+xml")
