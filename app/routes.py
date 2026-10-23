"""Falcon resources (one class per route) plus Jinja rendering."""

import os

import falcon
from jinja2 import Environment, FileSystemLoader

from app.auth import csrf_token, flash, form_data, login_user, logout_user, valid_csrf
from app.forms import EditProfileForm, EmptyForm, LoginForm, RegistrationForm
from app.models import User

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)

ROUTES = {
    "index": "/index",
    "login": "/login",
    "register": "/register",
    "profile": "/profile/{username}",
    "edit_profile": "/edit_profile",
    "follow": "/follow/{username}",
    "unfollow": "/unfollow/{username}",
    "logout": "/logout",
}


def url_for(endpoint, **values):
    pattern = ROUTES[endpoint]
    return pattern.format(**values) if values else pattern


env.globals["url_for"] = url_for


def render(req, resp, template, status=falcon.HTTP_200, **ctx):
    # Flashes live in the session and are consumed on first render.
    messages = req.context.session.pop("flashes", [])
    resp.text = env.get_template(template).render(
        request=req,
        current_user=req.context.current_user,
        get_flashed_messages=lambda: messages,
        **ctx,
    )
    resp.content_type = falcon.MEDIA_HTML
    resp.status = status


def redirect(resp, location):
    resp.status = falcon.HTTP_302
    resp.location = location


INDEX_POSTS = [
    {"author": {"username": "John"}, "body": "Beautiful day in Portland!"},
    {"author": {"username": "Susan"}, "body": "The Avengers movie was so cool!"},
    {"author": {"username": "Vaite"}, "body": "Cash money vaite!"},
]


class IndexResource:
    def on_get(self, req, resp):
        render(req, resp, "index.html", title="Home", posts=INDEX_POSTS)


class LoginResource:
    def on_get(self, req, resp):
        if req.context.current_user.is_authenticated:
            return redirect(resp, url_for("index"))
        form = LoginForm()
        form.csrf_token_value = csrf_token(req.context.session)
        render(req, resp, "login.html", title="Sign In", form=form)

    def on_post(self, req, resp):
        if req.context.current_user.is_authenticated:
            return redirect(resp, url_for("index"))
        session = req.context.session
        params = form_data(req)
        form = LoginForm(
            data={
                "username": params.get("username"),
                "password": params.get("password"),
                "remember_me": params.get("remember_me"),
            }
        )
        form.csrf_token_value = csrf_token(session)
        if not valid_csrf(req) or not form.validate():
            # Bad/missing token is a form error: re-render, don't log in.
            return render(req, resp, "login.html", title="Sign In", form=form)
        user = User.get_or_none(User.username == form.username.data)
        if user is None or not user.check_password(form.password.data):
            flash(session, "Invalid username or password")
            return redirect(resp, url_for("login"))
        login_user(session, user, remember=bool(form.remember_me.data))
        return redirect(resp, url_for("index"))


class RegisterResource:
    def on_get(self, req, resp):
        if req.context.current_user.is_authenticated:
            return redirect(resp, url_for("index"))
        form = RegistrationForm()
        form.csrf_token_value = csrf_token(req.context.session)
        render(req, resp, "register.html", title="Register", form=form)

    def on_post(self, req, resp):
        if req.context.current_user.is_authenticated:
            return redirect(resp, url_for("index"))
        session = req.context.session
        params = form_data(req)
        form = RegistrationForm(
            data={
                "username": params.get("username"),
                "email": params.get("email"),
                "password": params.get("password"),
                "password2": params.get("password2"),
            }
        )
        form.csrf_token_value = csrf_token(session)
        if not valid_csrf(req) or not form.validate():
            return render(req, resp, "register.html", title="Register", form=form)
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.save()
        flash(session, "Congratulations, you are now a registered user!")
        return redirect(resp, url_for("login"))


class ProfileResource:
    def on_get(self, req, resp, username):
        user = User.get_or_none(User.username == username)
        if user is None:
            raise falcon.HTTPNotFound()
        posts = [
            {"author": user, "body": "Test post #1"},
            {"author": user, "body": "Test post #2"},
        ]
        form = EmptyForm()
        form.csrf_token_value = csrf_token(req.context.session)
        render(req, resp, "profile.html", user=user, posts=posts, form=form)


class EditProfileResource:
    def on_get(self, req, resp):
        me = req.context.current_user
        form = EditProfileForm(
            me.username, data={"username": me.username, "about_me": me.about_me}
        )
        form.csrf_token_value = csrf_token(req.context.session)
        render(req, resp, "edit_profile.html", title="Edit Profile", form=form)

    def on_post(self, req, resp):
        me = req.context.current_user
        session = req.context.session
        params = form_data(req)
        form = EditProfileForm(
            me.username,
            data={
                "username": params.get("username"),
                "about_me": params.get("about_me"),
            },
        )
        form.csrf_token_value = csrf_token(session)
        if not valid_csrf(req) or not form.validate():
            return render(
                req, resp, "edit_profile.html", title="Edit Profile", form=form
            )
        me.username = form.username.data
        me.about_me = form.about_me.data
        me.save()
        flash(session, "Your changes have been saved.")
        return redirect(resp, url_for("edit_profile"))


class FollowResource:
    def on_post(self, req, resp, username):
        session = req.context.session
        if not valid_csrf(req):
            return redirect(resp, url_for("index"))
        user = User.get_or_none(User.username == username)
        if user is None:
            flash(session, f"User {username} not found.")
            return redirect(resp, url_for("index"))
        if user == req.context.current_user:
            flash(session, "You cannot follow yourself!")
            return redirect(resp, url_for("profile", username=username))
        req.context.current_user.follow(user)
        flash(session, f"You are following {username}!")
        return redirect(resp, url_for("profile", username=username))


class UnfollowResource:
    def on_post(self, req, resp, username):
        session = req.context.session
        if not valid_csrf(req):
            return redirect(resp, url_for("index"))
        user = User.get_or_none(User.username == username)
        if user is None:
            flash(session, f"User {username} not found.")
            return redirect(resp, url_for("index"))
        if user == req.context.current_user:
            flash(session, "You cannot unfollow yourself!")
            return redirect(resp, url_for("profile", username=username))
        req.context.current_user.unfollow(user)
        flash(session, f"You are not following {username}.")
        return redirect(resp, url_for("profile", username=username))


class LogoutResource:
    def on_get(self, req, resp):
        logout_user(req.context.session)
        return redirect(resp, url_for("index"))


def add_routes(app):
    index = IndexResource()
    app.add_route("/", index)
    app.add_route("/index", index)
    app.add_route("/login", LoginResource())
    app.add_route("/register", RegisterResource())
    app.add_route("/profile/{username}", ProfileResource())
    app.add_route("/edit_profile", EditProfileResource())
    app.add_route("/follow/{username}", FollowResource())
    app.add_route("/unfollow/{username}", UnfollowResource())
    app.add_route("/logout", LogoutResource())
