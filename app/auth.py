"""Signed-cookie session, login helpers, CSRF, and the app middleware.

Replaces Flask-Login + Flask-WTF CSRF + Flask flash: everything lives in
one itsdangerous-signed cookie, no server-side state.
"""

import secrets
from datetime import datetime, timezone

import falcon
from itsdangerous import BadSignature, URLSafeSerializer

from config import Config
from app.models import User

SESSION_COOKIE = "session"
REMEMBER_AGE = 30 * 24 * 3600


class AnonymousUser:
    is_authenticated = False
    is_anonymous = True
    username = ""


def _serializer():
    return URLSafeSerializer(Config.SECRET_KEY, salt="microblog-session")


def load_session(req):
    token = req.cookies.get(SESSION_COOKIE)
    if not token:
        return {}
    try:
        data = _serializer().loads(token)
    except BadSignature:
        return {}
    return data if isinstance(data, dict) else {}


def save_session(resp, session):
    resp.set_cookie(
        SESSION_COOKIE,
        _serializer().dumps(session),
        path="/",
        http_only=True,
        same_site="Lax",
        # Falcon 4 defaults to Secure; dev/test run over plain HTTP.
        secure=False,
        max_age=REMEMBER_AGE if session.get("remember") else None,
    )


def login_user(session, user, remember=False):
    session["user_id"] = user.id
    if remember:
        session["remember"] = True
    else:
        session.pop("remember", None)


def logout_user(session):
    session.pop("user_id", None)
    session.pop("remember", None)


def flash(session, message):
    session.setdefault("flashes", []).append(message)


def csrf_token(session):
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(16)
        session["csrf_token"] = token
    return token


def valid_csrf(req):
    expected = req.context.session.get("csrf_token")
    return bool(expected) and form_data(req).get("csrf_token") == expected


def form_data(req):
    """URL-encoded POST body as a dict (Falcon 4: via req.get_media())."""
    if req.content_type and "application/x-www-form-urlencoded" in req.content_type:
        try:
            media = req.get_media()
        except Exception:
            return {}
        return media if isinstance(media, dict) else {}
    return {}


# Paths that require a login (mirrors the old @login_required routes).
PROTECTED_EXACT = {"/", "/index"}
PROTECTED_PREFIXES = ("/profile", "/edit_profile", "/follow", "/unfollow")


class AppMiddleware:
    """Session, current_user, last_seen, auth guard (DB comes from DatabaseMiddleware)."""

    def process_request(self, req, resp):
        session = load_session(req)
        req.context.session = session
        user = None
        if session.get("user_id") is not None:
            user = User.get_or_none(User.id == session["user_id"])
            if user is None:
                session.pop("user_id", None)
        req.context.current_user = user if user is not None else AnonymousUser()
        if user is not None:
            # Same as the old before_request hook.
            user.last_seen = datetime.now(timezone.utc)
            user.save()
        path = req.path
        if (path in PROTECTED_EXACT or path.startswith(PROTECTED_PREFIXES)) and (
            user is None
        ):
            resp.status = falcon.HTTP_302
            resp.location = f"/login?next={path}"
            resp.complete = True

    def process_response(self, req, resp, resource, req_succeeded):
        if hasattr(req.context, "session"):
            save_session(resp, req.context.session)
