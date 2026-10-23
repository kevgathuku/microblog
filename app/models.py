"""Peewee models for the Falcon port (SQLite, dev DB: falcon.db)."""

from datetime import datetime, timezone
from hashlib import md5

from peewee import (
    AutoField,
    CharField,
    CompositeKey,
    DateTimeField,
    ForeignKeyField,
    Model,
    SqliteDatabase,
    TextField,
)
from werkzeug.security import check_password_hash, generate_password_hash

# Deferred init: create_app() binds the real path (falcon.db, or a temp
# file under pytest)
db = SqliteDatabase(None)


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    id = AutoField()
    username = CharField(max_length=64, unique=True, index=True)
    email = CharField(max_length=120, unique=True, index=True)
    about_me = TextField(null=True)
    last_seen = DateTimeField(null=True, default=lambda: datetime.now(timezone.utc))
    password_hash = CharField(max_length=256, null=True)

    # Flask-Login compatible flags used by the templates.
    is_authenticated = True
    is_anonymous = False

    def get_id(self):
        return str(self.id)

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
        if not self.is_following(user):
            Follow.create(follower=self, followed=user)

    def unfollow(self, user):
        if self.is_following(user):
            (
                Follow.delete()
                .where((Follow.follower == self) & (Follow.followed == user))
                .execute()
            )

    def followers_count(self):
        return Follow.select().where(Follow.followed == self).count()

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


class Follow(BaseModel):
    follower = ForeignKeyField(User, backref="following_rel")
    followed = ForeignKeyField(User, backref="followers_rel")

    class Meta:
        primary_key = CompositeKey("follower", "followed")


class Post(BaseModel):
    id = AutoField()
    body = CharField(max_length=140)
    timestamp = DateTimeField(index=True, default=lambda: datetime.now(timezone.utc))
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


class DatabaseMiddleware:
    """Open a Peewee connection per request, close it afterwards."""

    def process_request(self, req, resp):
        # reuse_if_open: plain connect() raises if the thread already
        # holds one (e.g. tables created at startup in the same thread).
        db.connect(reuse_if_open=True)

    def process_response(self, req, resp, resource, req_succeeded):
        if not db.is_closed():
            db.close()
