"""Peewee models"""

from contextlib import suppress
from datetime import UTC, datetime
from hashlib import md5
from time import time

import jwt
from flask_login import UserMixin
from peewee import (
    AutoField,
    CharField,
    CompositeKey,
    DateTimeField,
    ForeignKeyField,
    IntegrityError,
    Model,
)
from werkzeug.security import check_password_hash, generate_password_hash

from app import app, db, login


class BaseModel(Model):
    class Meta:
        database = db


class User(UserMixin, BaseModel):
    id = AutoField()
    username = CharField(max_length=64, unique=True, index=True)
    email = CharField(max_length=120, unique=True, index=True)
    about_me = CharField(null=True, max_length=140)
    last_seen = DateTimeField(null=True, default=lambda: datetime.now(UTC))
    password_hash = CharField(max_length=256, null=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash or "", password or "")

    def avatar(self, size):
        digest = md5((self.email or "").lower().encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}"

    def is_following(self, user):
        return (
            Follow.select()
            .where((Follow.follower == self) & (Follow.followed == user))
            .exists()
        )

    def follow(self, user):
        if self.is_following(user):
            return
        # lost a concurrent follow race; the row already exists
        with suppress(IntegrityError):
            Follow.create(follower=self, followed=user)

    def unfollow(self, user):
        if self.is_following(user):
            (
                Follow.delete()
                .where((Follow.follower == self) & (Follow.followed == user))
                .execute()
            )

    @property
    def followers_count(self):
        return Follow.select().where(Follow.followed == self).count()

    @property
    def following_count(self):
        return Follow.select().where(Follow.follower == self).count()

    @property
    def following(self):
        return (
            User.select()
            .join(Follow, on=(Follow.followed == User.id))
            .where(Follow.follower == self)
            .order_by(User.id)
        )

    @property
    def followers(self):
        return (
            User.select()
            .join(Follow, on=(Follow.follower == User.id))
            .where(Follow.followed == self)
            .order_by(User.id)
        )

    def following_posts(self):
        followed_ids = [
            row.followed_id
            for row in Follow.select(Follow.followed).where(Follow.follower == self)
        ]
        return (
            Post.select()
            .where(Post.user.in_(followed_ids + [self.id]))
            .order_by(Post.timestamp.desc())
        )

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {"reset_password": self.id, "exp": time() + expires_in},
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])[
                "reset_password"
            ]
        except jwt.InvalidTokenError, KeyError:
            return
        return User.get_or_none(User.id == id)

    # Instances are often loaded twice (session user vs. page user);
    # identity must mean "same row" for `user == current_user` checks.
    def __eq__(self, other):
        if isinstance(other, User):
            return self.id is not None and self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"<User {self.username}>"


@login.user_loader
def load_user(id):
    return User.get_or_none(User.id == int(id))


class Follow(BaseModel):
    follower = ForeignKeyField(User, backref="following_rel")
    followed = ForeignKeyField(User, backref="followers_rel")

    class Meta:
        primary_key = CompositeKey("follower", "followed")


class Post(BaseModel):
    id = AutoField()
    body = CharField(max_length=140)
    timestamp = DateTimeField(index=True, default=lambda: datetime.now(UTC))
    user = ForeignKeyField(User, backref="posts", index=True)

    @property
    def author(self):
        return self.user

    @author.setter
    def author(self, value):
        self.user = value

    def __repr__(self):
        return f"<Post {self.body}>"


TABLES = [User, Follow, Post]
