from formalchemy import forms, tables, types, Field, FieldSet, Grid, validators

from pyramid.i18n import TranslationStringFactory

from fluidnexus.models import User

_ = TranslationStringFactory('fluidnexus_forms')

def password_match(value, field):
    if field.parent.password1.value != value:
        raise validators.ValidationError(_("Passwords do not match"))

class RegisterUserFieldSet(FieldSet):
    """Used to edit users."""

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
