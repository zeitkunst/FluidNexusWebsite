from formalchemy import forms, tables, types, Field, FieldSet, Grid, validators

from pyramid.i18n import TranslationStringFactory

from fluidnexus.models import Comment, User, Token

_ = TranslationStringFactory('fluidnexus_forms')

def password_match(value, field):
    if field.parent.password1.value != value:
        raise validators.ValidationError(_("Passwords do not match"))

def username_different(value, field):
    if (field.parent.model.getByUsername(value) is not None):
        raise validators.ValidationError(_("Your username cannot be the same as one that already exists in the database."))

class OpenIDUserFieldSet(FieldSet):
    """Used to register a user with their openID."""

    def __init__(self):
        """Pre-configuration"""
        FieldSet.__init__(self, User)

        inc = [self.username.label(_("Username (will be used publicly to identify you on the website)")).validate(username_different),
               self.given_name.label(_("* Given name")),
               self.surname.label(_("* Surname")),
               self.homepage.label(_("Homepage (please include 'http://')"))
              ]
        self.configure(include = inc)


class RegisterUserFieldSet(FieldSet):
    """Used to register users."""

    def __init__(self, user = None):
        """Pre-configuration"""
        FieldSet.__init__(self, User)

        self.append(Field('password1'))
        self.append(Field('password2'))

        inc = [self.username.label(_("Username")),
               self.password1.password().label(_("* Password")),
               self.password2.password().label(_("* Confirm password")).validate(password_match),
               self.given_name.label(_("* Given name")),
               self.surname.label(_("* Surname")),
               self.homepage.label(_("Homepage (please include 'http://')"))
              ]
        self.configure(include = inc)

class UserFieldSet(FieldSet):
    """Used to edit users."""

    def __init__(self, user = None):
        """Pre-configuration"""
        FieldSet.__init__(self, User)

        self.append(Field('password1'))
        self.append(Field('password2'))

        inc = [self.username.readonly().label(_("Username")),
               self.password1.password().label(_("* Password")),
               self.password2.password().label(_("* Confirm password")).validate(password_match),
               self.given_name.label(_("* Given name")),
               self.surname.label(_("* Surname")),
               self.homepage.label(_("Homepage (please include 'http://')"))
              ]
        self.configure(include = inc)

class UserNoPasswordFieldSet(FieldSet):
    """Used to edit users."""

    def __init__(self, user = None):
        """Pre-configuration"""
        FieldSet.__init__(self, User)

        inc = [self.username.readonly().label(_("Username")),
               self.given_name.label(_("* Given name")),
               self.surname.label(_("* Surname")),
               self.homepage.label(_("Homepage (please include 'http://')"))
              ]
        self.configure(include = inc)

class CommentFieldSet(FieldSet):
    """Used to present a basic comment form."""

    def __init__(self):
        FieldSet.__init__(self, Comment)

        options = [self.content.textarea(size = (45,20))]
        inc = [self.name.label(_("Name")),
               self.email.label(_("E-mail (will not be shared)")),
               self.homepage.label(_("Homepage")),
               self.content.label(_("Comment")).required()
              ]
        self.configure(include = inc, options = options)

class AuthorizeTokenFieldSet(FieldSet):
    """Used to present a form for authorizing a token."""

    def __init__(self):
        FieldSet.__init__(self, Token)

        include = [self.token.hidden(), self.token_secret.hidden(), self.callback_url.hidden()]
        self.configure(include = include)
