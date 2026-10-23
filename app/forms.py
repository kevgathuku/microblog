"""Plain WTForms forms (no Flask-WTF). CSRF is handled by app.auth."""

from markupsafe import Markup
from wtforms import (
    BooleanField,
    Form,
    PasswordField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.models import User


class BaseForm(Form):
    # Set per request from the signed session; rendered by hidden_tag().
    csrf_token_value = ""

    def hidden_tag(self):
        return Markup(
            f'<input type="hidden" name="csrf_token" value="{self.csrf_token_value}">'
        )


class LoginForm(BaseForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(BaseForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")

    def validate_username(self, field):
        if User.select().where(User.username == field.data).exists():
            raise ValidationError("Please use a different username")

    def validate_email(self, field):
        if User.select().where(User.email == field.data).exists():
            raise ValidationError("Please use a different email address.")


class EditProfileForm(BaseForm):
    username = StringField("Username", validators=[DataRequired()])
    about_me = TextAreaField("About me", validators=[Length(min=0, max=140)])
    submit = SubmitField("Submit")

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, field):
        # Only check if the user submits a different username
        if field.data != self.original_username:
            if User.select().where(User.username == field.data).exists():
                raise ValidationError("Please use a different username")


class EmptyForm(BaseForm):
    submit = SubmitField("Submit")
