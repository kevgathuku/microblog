import hmac
import secrets
from functools import wraps

from bottle import redirect, request, response
from result import Err, Ok, Result

from app.db import Session
from app.models import User
from app.urls import url
from config import config


class AnonymousUser:
    is_authenticated = False
    is_anonymous = True
    username = None


def current_user():
    if "microblog.user" not in request.environ:
        user_id = request.get_cookie("user_id", secret=config.SECRET_KEY)
        user = Session.get(User, int(user_id)) if user_id is not None else None
        request.environ["microblog.user"] = user or AnonymousUser()
    return request.environ["microblog.user"]


def cookie_options():
    return {
        "secret": config.SECRET_KEY,
        "path": "/",
        "httponly": True,
        "samesite": "Lax",
        "secure": config.COOKIE_SECURE,
    }


def login_user(user, remember=False):
    kwargs = cookie_options()
    if remember:
        kwargs["max_age"] = 30 * 24 * 3600
    response.set_cookie("user_id", str(user.id), **kwargs)


def logout_user():
    response.delete_cookie("user_id", path="/")


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user().is_authenticated:
            redirect(url("login") + "?next={}".format(request.path))
        return func(*args, **kwargs)

    return wrapper


def flash(message):
    response.set_cookie("flash", message, **cookie_options())


def get_flashed_messages():
    message = request.get_cookie("flash", secret=config.SECRET_KEY)
    if message is not None:
        response.delete_cookie("flash", path="/")
        return [message]
    return []


def get_or_set_csrf_token():
    token = request.get_cookie("csrf_token", secret=config.SECRET_KEY)
    if token is None:
        token = secrets.token_urlsafe(32)
        response.set_cookie("csrf_token", token, **cookie_options())
    return token


def validate_csrf(req) -> Result[None, str]:
    submitted = req.forms.get("csrf_token")
    expected = req.get_cookie("csrf_token", secret=config.SECRET_KEY)
    if not submitted or not expected:
        return Err("missing csrf token")
    if not hmac.compare_digest(submitted, expected):
        return Err("csrf token mismatch")
    return Ok(None)
