from html.parser import HTMLParser
from urllib.parse import unquote

import pytest  # noqa: E402
from webtest import TestApp  # noqa: E402

from app import app, db  # noqa: E402


@pytest.fixture
def client():
    ctx = app.app_context()
    ctx.push()
    db.session.remove()
    db.drop_all()
    db.create_all()
    yield TestApp(app)
    db.session.remove()
    ctx.pop()


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
    # Flask-Login quotes next (…?next=%2F); unquote before comparing.
    assert unquote(response.location).endswith(suffix)


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
    # Flask-WTF treats a missing token as a form error (200 re-render),
    # not a 400 - but the login must not go through.
    client.get("/login")  # sets the session cookie, but token is not submitted
    response = client.post("/login", {"username": "x"}, status=200)
    assert "Sign In" in response.text
    redirected_to(client.get("/"), "/login?next=/")


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


def test_404_while_logged_in_shows_path(client):
    register(client)
    login(client)
    body = client.get("/no-such-page", status=404).text
    assert "Page Not Found" in body and "/no-such-page" in body


def test_custom_404_shows_path(client):
    body = client.get("/no-such-page", status=404).text
    assert "Page Not Found" in body and "/no-such-page" in body
