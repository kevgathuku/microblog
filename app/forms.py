import sqlalchemy as sa
from wtforms import (
    BooleanField,
    Form,
    PasswordField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.db import Session
from app.models import User


class BottleFormData:
    """Adapt bottle's FormsDict to the getlist interface WTForms expects."""

    def __init__(self, forms):
        self.forms = forms

    def getlist(self, key):
        return self.forms.getall(key)

    def __contains__(self, key):
        return key in self.forms


class LoginForm(Form):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(Form):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")

    def validate_username(self, username):
        user = Session.scalar(sa.select(User).where(User.username == username.data))
        if user is not None:
            raise ValidationError("Please use a different username")

    def validate_email(self, email):
        user = Session.scalar(sa.select(User).where(User.email == email.data))
        if user is not None:
            raise ValidationError("Please use a different email address.")


class EditProfileForm(Form):
    username = StringField("Username", validators=[DataRequired()])
    about_me = TextAreaField("About me", validators=[Length(min=0, max=140)])
    submit = SubmitField("Submit")

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        # Only check if the user submits a different username
        if username.data != self.original_username:
            # Check if the submitted username is already in use
            user = Session.scalar(sa.select(User).where(User.username == username.data))
            if user is not None:
                raise ValidationError("Please use a different username")
