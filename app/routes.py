from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import app
from app.email import send_password_reset_email
from app.forms import (
    EditProfileForm,
    EmptyForm,
    LoginForm,
    PostForm,
    RegistrationForm,
    ResetPasswordForm,
    ResetPasswordRequestForm,
)
from app.models import Post, User


@app.before_request
def before_request():
    if current_user.is_authenticated:
        # Throttled: last_seen only needs minute precision, and writing on
        # every request locks SQLite under concurrent (threaded) traffic.
        now = datetime.now(UTC)
        last = current_user.last_seen
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        if last is None or (now - last) > timedelta(minutes=5):
            current_user.last_seen = now
            current_user.save(only=[User.last_seen])


def _paginate(query, page, per_page=app.config["POSTS_PER_PAGE"]):
    # Peewee's paginate() only slices (LIMIT/OFFSET)
    # Derive next_num/has_next from a count taken before slicing.
    total = query.count()
    return query.paginate(page, per_page), page * per_page < total


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        Post.create(body=form.post.data, author=current_user)
        flash("Your post is now live!")
        return redirect(url_for("index"))

    page = max(1, request.args.get("page", 1, type=int))
    posts, has_next = _paginate(current_user.following_posts(), page)
    if page > 1 and len(posts) == 0:
        return redirect(url_for("index"))
    next_url = url_for("index", page=page + 1) if has_next else None
    prev_url = url_for("index", page=page - 1) if page > 1 else None
    return render_template(
        "index.html",
        title="Home",
        form=form,
        posts=posts,
        next_url=next_url,
        prev_url=prev_url,
    )


@app.route("/explore")
@login_required
def explore():
    page = max(1, request.args.get("page", 1, type=int))
    posts, has_next = _paginate(Post.select().order_by(Post.timestamp.desc()), page)
    if page > 1 and len(posts) == 0:
        return redirect(url_for("explore"))
    next_url = url_for("explore", page=page + 1) if has_next else None
    prev_url = url_for("explore", page=page - 1) if page > 1 else None
    return render_template(
        "index.html",
        title="Explore",
        posts=posts,
        next_url=next_url,
        prev_url=prev_url,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_or_none(User.username == form.username.data)
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = url_for("index")
        return redirect(next_page)
    return render_template("login.html", title="Sign In", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.save()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.get_or_none(User.email == form.email.data)
        if user:
            send_password_reset_email(user)
        flash("Check your email for the instructions to reset your password")
        return redirect(url_for("login"))
    return render_template(
        "reset_password_request.html", title="Reset Password", form=form
    )


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for("index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.save()
        flash("Your password has been reset.")
        return redirect(url_for("login"))
    return render_template("reset_password.html", form=form)


@app.route("/profile/<username>")
@login_required
def profile(username):
    user = User.get_or_none(User.username == username)
    if user is None:
        abort(404)
    form = EmptyForm()

    page = max(1, request.args.get("page", 1, type=int))
    posts, has_next = _paginate(
        user.posts.order_by(Post.timestamp.desc()),
        page,
    )
    next_url = (
        url_for("profile", username=user.username, page=page + 1) if has_next else None
    )
    prev_url = (
        url_for("profile", username=user.username, page=page - 1) if page > 1 else None
    )
    return render_template(
        "profile.html",
        user=user,
        posts=posts,
        next_url=next_url,
        prev_url=prev_url,
        form=form,
    )


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    # Username needed for uniqueness check on submit
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        current_user.save(only=[User.username, User.about_me])
        flash("Your changes have been saved.")
        return redirect(url_for("profile", username=current_user.username))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", title="Edit Profile", form=form)


@app.route("/follow/<username>", methods=["POST"])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.get_or_none(User.username == username)
        if user is None:
            flash(f"User {username} not found.")
            return redirect(url_for("index"))
        if user == current_user:
            flash("You cannot follow yourself!")
            return redirect(url_for("profile", username=username))
        current_user.follow(user)
        flash(f"You are following {username}!")
        return redirect(url_for("profile", username=username))
    else:
        return redirect(url_for("index"))


@app.route("/unfollow/<username>", methods=["POST"])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.get_or_none(User.username == username)
        if user is None:
            flash(f"User {username} not found.")
            return redirect(url_for("index"))
        if user == current_user:
            flash("You cannot unfollow yourself!")
            return redirect(url_for("profile", username=username))
        current_user.unfollow(user)
        flash(f"You are not following {username}.")
        return redirect(url_for("profile", username=username))
    else:
        return redirect(url_for("index"))


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))
