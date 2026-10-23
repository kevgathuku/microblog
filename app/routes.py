from urllib.parse import urlsplit

from bottle import jinja2_template, request, redirect, abort

import sqlalchemy as sa
from app import app
from app.auth import current_user, flash, get_flashed_messages, login_required
from app.auth import get_or_set_csrf_token, login_user, logout_user
from app.db import Session
from app.forms import BottleFormData, EditProfileForm, LoginForm, RegistrationForm
from app.models import User


def render(tpl, **ctx):
    ctx.setdefault("current_user", current_user())
    ctx.setdefault("messages", get_flashed_messages())
    ctx.setdefault("csrf_token", get_or_set_csrf_token())
    return jinja2_template(tpl, **ctx)


@app.route("/")
@app.route("/index")
@login_required
def index():
    posts = [
        {"author": {"username": "John"}, "body": "Beautiful day in Portland!"},
        {"author": {"username": "Susan"}, "body": "The Avengers movie was so cool!"},
        {"author": {"username": "Vaite"}, "body": "Cash money vaite!"},
    ]
    return render("index.html", title="Home", posts=posts)


@app.route("/login", method=["GET", "POST"])
def login():
    if current_user().is_authenticated:
        return redirect("/index")
    form = (
        LoginForm(BottleFormData(request.forms))
        if request.method == "POST"
        else LoginForm()
    )
    if request.method == "POST" and form.validate():
        user = Session.scalar(
            sa.select(User).where(User.username == form.username.data)
        )
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect("/login")
        login_user(user, remember=form.remember_me.data)
        next_page = request.query.next
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = "/index"
        return redirect(next_page)
    return render("login.html", title="Sign In", form=form)


@app.route("/register", method=["GET", "POST"])
def register():
    if current_user().is_authenticated:
        return redirect("/index")
    form = (
        RegistrationForm(BottleFormData(request.forms))
        if request.method == "POST"
        else RegistrationForm()
    )
    if request.method == "POST" and form.validate():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        Session.add(user)
        Session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect("/login")
    return render("register.html", title="Register", form=form)


@app.route("/profile/<username>")
@login_required
def profile(username):
    user = Session.scalar(sa.select(User).where(User.username == username))
    if user is None:
        abort(404)
    posts = [
        {"author": user, "body": "Test post #1"},
        {"author": user, "body": "Test post #2"},
    ]
    return render("profile.html", user=user, posts=posts)


@app.route("/edit_profile", method=["GET", "POST"])
@login_required
def edit_profile():
    me = current_user()
    form = (
        EditProfileForm(me.username, BottleFormData(request.forms))
        if request.method == "POST"
        else EditProfileForm(me.username)
    )
    if request.method == "POST" and form.validate():
        me.username = form.username.data
        me.about_me = form.about_me.data
        Session.commit()
        flash("Your changes have been saved.")
        return redirect("/edit_profile")
    elif request.method == "GET":
        form.username.data = me.username
        form.about_me.data = me.about_me
    return render("edit_profile.html", title="Edit Profile", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect("/index")
