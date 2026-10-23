from html.parser import HTMLParser
from urllib.parse import unquote

import pytest  # noqa: E402
from webtest import TestApp  # noqa: E402

from app import create_app, db  # noqa: E402
from app.models import TABLES  # noqa: E402


@pytest.fixture
def client():
    db.connect(reuse_if_open=True)
    db.drop_tables(TABLES, safe=True)
    db.create_tables(TABLES, safe=True)
    yield TestApp(create_app())
    db.drop_tables(TABLES, safe=True)
    db.close()


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
    # Login guard quotes next (…?next=%2F); unquote before comparing.
    assert unquote(response.location).endswith(suffix)


def register(client, username, email):
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


def login(client, username):
    token = csrf_token(client.get("/login").text)
    return client.post(
        "/login",
        {"csrf_token": token, "username": username, "password": "secret123"},
    )


def test_auth_guard_redirects_anonymous(client):
    redirected_to(client.get("/"), "/login?next=/")


def test_register_then_login_flow(client):
    redirected_to(
        register(client, username="tester", email="tester@example.com"), "/login"
    )
    redirected_to(login(client, username="tester"), "/index")
    assert "Hi, tester" in client.get("/").text


def test_post_without_csrf_token_is_rejected(client):
    # A missing token is a form error (200 re-render), not a 400 - but the
    # login must not go through.
    client.get("/login")  # sets the session cookie, but token is not submitted
    response = client.post("/login", {"username": "x"}, status=200)
    assert "Sign In" in response.text
    redirected_to(client.get("/"), "/login?next=/")


def test_bad_password_flashes_error(client):
    register(client, username="tester", email="tester@example.com")
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


def test_follow_unfollow_flow(client):
    register(client, username="tester", email="tester@example.com")
    register(client, username="followed", email="followed@example.com")
    login(client, username="tester")
    page = client.get("/profile/followed").text
    assert 'value="Follow"' in page and "0 followers" in page
    redirected_to(
        client.post("/follow/followed", {"csrf_token": csrf_token(page)}),
        "/profile/followed",
    )
    page = client.get("/profile/followed").text
    assert "You are following followed!" in page
    assert 'value="Unfollow"' in page and "1 followers" in page
    redirected_to(
        client.post("/unfollow/followed", {"csrf_token": csrf_token(page)}),
        "/profile/followed",
    )
    page = client.get("/profile/followed").text
    assert "You are not following followed." in page
    assert 'value="Follow"' in page and "0 followers" in page


def test_follow_without_csrf_token_goes_index(client):
    register(client, username="tester", email="tester@example.com")
    register(client, username="followed", email="followed@example.com")
    login(client, username="tester")
    redirected_to(client.post("/follow/followed", {}), "/index")


def test_follow_self_post_is_rejected(client):
    # Backstop behind the hidden button: a forged POST with a valid token
    # (harvested from another page) must still be refused.
    register(client, username="tester", email="tester@example.com")
    register(client, username="other", email="other@example.com")
    login(client, username="tester")
    token = csrf_token(client.get("/profile/other").text)
    redirected_to(
        client.post("/follow/tester", {"csrf_token": token}),
        "/profile/tester",
    )
    assert "You cannot follow yourself!" in client.get("/profile/tester").text


def test_own_profile_shows_no_follow_button(client):
    register(client, username="tester", email="tester@example.com")
    login(client, username="tester")
    page = client.get("/profile/tester").text
    assert "Edit your profile" in page
    assert 'value="Follow"' not in page
    assert 'value="Unfollow"' not in page


def test_404_while_logged_in_shows_path(client):
    register(client, username="tester", email="tester@example.com")
    login(client, username="tester")
    body = client.get("/no-such-page", status=404).text
    assert "Page Not Found" in body and "/no-such-page" in body


def test_custom_404_shows_path(client):
    body = client.get("/no-such-page", status=404).text
    assert "Page Not Found" in body and "/no-such-page" in body
