from html.parser import HTMLParser

import pytest  # noqa: E402
from webtest import TestApp  # noqa: E402

from app import app  # noqa: E402
from app.db import Base, Session, engine  # noqa: E402

Base.metadata.create_all(engine)


@pytest.fixture
def client():
    # Pre-test remove: discard session leaked from the prior test (cached
    # objects, connections bound to the pre-drop schema) so DDL starts clean.
    Session.remove()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # Setup code above the yield
    yield TestApp(app)
    # Teardown code below the yield
    # Post-test remove: release connections + clear identity map so nothing
    # stale carries over and the sqlite file isn't held open at unlink time.
    Session.remove()


class CSRFParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = None

    def handle_starttag(self, tag, attrs):
        if tag == "input":
            fields = dict(attrs)
            if fields.get("name") == "csrf_token":
                self.token = fields.get("value")


def csrf_token(body):
    parser = CSRFParser()
    parser.feed(body)
    return parser.token


def redirected_to(response, suffix):
    assert response.status_int in (302, 303)
    assert response.location.endswith(suffix)


def register(client, username="tester", email="tester@example.com"):
    token = csrf_token(client.get("/register").text)
    return client.post(
        "/register",
        {
            "csrf_token": token,
            "username": username,
            "email": email,
            "password": "secret123",
            "password2": "secret123",
        },
    )


def login(client, username="tester"):
    token = csrf_token(client.get("/login").text)
    return client.post(
        "/login",
        {"csrf_token": token, "username": username, "password": "secret123"},
    )


def test_auth_guard_redirects_anonymous(client):
    redirected_to(client.get("/"), "/login?next=/")


def test_register_then_login_flow(client):
    redirected_to(register(client), "/login")
    redirected_to(login(client), "/index")
    assert "Hi, tester" in client.get("/").text


def test_post_without_csrf_token_is_rejected(client):
    client.get("/login")  # sets the cookie, but token is not submitted
    response = client.post("/login", {"username": "x"}, status=400)
    assert "Bad Request" in response.text


def test_bad_password_flashes_error(client):
    register(client)
    token = csrf_token(client.get("/login").text)
    redirected_to(
        client.post(
            "/login",
            {"csrf_token": token, "username": "tester", "password": "wrong"},
        ),
        "/login",
    )
    assert "Invalid username or password" in client.get("/login").text


def test_edit_profile_renames_user(client):
    register(client, username="renamer", email="renamer@example.com")
    login(client, username="renamer")
    token = csrf_token(client.get("/edit_profile").text)
    redirected_to(
        client.post(
            "/edit_profile",
            {"csrf_token": token, "username": "renamed", "about_me": "hi"},
        ),
        "/edit_profile",
    )
    assert "User: renamed" in client.get("/profile/renamed").text


class StubRequest:
    def __init__(self, *, form_token, cookie_token, cookie_secret=None):
        from config import config as cfg

        self.forms = {"csrf_token": form_token}
        self._cookie_token = cookie_token
        self._cookie_secret = cfg.SECRET_KEY if cookie_secret is None else cookie_secret

    def get_cookie(self, name, secret=None):
        assert name == "csrf_token"
        if secret != self._cookie_secret:
            return None
        return self._cookie_token


def test_validate_csrf_unit():
    from app.auth import validate_csrf

    assert validate_csrf(StubRequest(form_token="abc", cookie_token="abc")).is_ok()
    assert (
        validate_csrf(StubRequest(form_token="abc", cookie_token="xyz")).unwrap_err()
        == "csrf token mismatch"
    )
    assert (
        validate_csrf(StubRequest(form_token=None, cookie_token="abc")).unwrap_err()
        == "missing csrf token"
    )
    assert (
        validate_csrf(
            StubRequest(
                form_token="abc", cookie_token="abc", cookie_secret="wrong-secret"
            )
        ).unwrap_err()
        == "missing csrf token"
    )


def test_url_reversing():
    from app.urls import url

    assert url("index") == "/"
    assert url("login") == "/login"
    assert url("profile", username="ann") == "/profile/ann"


def test_custom_404_shows_path(client):
    body = client.get("/no-such-page", status=404).text
    assert "Page Not Found" in body and "/no-such-page" in body
