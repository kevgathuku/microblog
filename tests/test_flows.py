import os
import re
import tempfile

_tmp = tempfile.mkstemp(suffix=".db")[1]
os.environ["DATABASE_URL"] = "sqlite:///{}".format(_tmp)
os.environ["MICROBLOG_ENV"] = "testing"

from webtest import TestApp  # noqa: E402

from app import app  # noqa: E402
from app.db import Base, engine  # noqa: E402

Base.metadata.create_all(engine)


def csrf_token(body):
    return re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)


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


def test_auth_guard_redirects_anonymous():
    redirected_to(TestApp(app).get("/"), "/login?next=/")


def test_register_then_login_flow():
    client = TestApp(app)
    redirected_to(register(client), "/login")
    redirected_to(login(client), "/index")
    assert "Hi, tester" in client.get("/").text


def test_post_without_csrf_token_is_rejected():
    client = TestApp(app)
    client.get("/login")  # sets the cookie, but token is not submitted
    response = client.post("/login", {"username": "x"}, status=400)
    assert "Bad Request" in response.text


def test_bad_password_flashes_error():
    client = TestApp(app)
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


def test_edit_profile_renames_user():
    client = TestApp(app)
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


def test_custom_404_shows_path():
    body = TestApp(app).get("/no-such-page", status=404).text
    assert "Page Not Found" in body and "/no-such-page" in body
