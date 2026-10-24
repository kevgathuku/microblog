"""Peewee models"""

from datetime import datetime, timezone
from hashlib import md5

from flask_login import UserMixin
from peewee import (
    AutoField,
    CharField,
    CompositeKey,
    DateTimeField,
    ForeignKeyField,
    IntegrityError,
    Model,
    SqliteDatabase,
    TextField,
)
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config, resolve_db_path

# Bound at import from Config (app.db, or a temp file under pytest via
# DATABASE_URL) so `pwmigrate` can resolve `app.models.db`.
db = SqliteDatabase(None)
db.init(resolve_db_path(Config.DATABASE_URL))


class BaseModel(Model):
    class Meta:
        database = db


class User(UserMixin, BaseModel):
    id = AutoField()
    username = CharField(max_length=64, unique=True, index=True)
    email = CharField(max_length=120, unique=True, index=True)
    about_me = TextField(null=True)
    last_seen = DateTimeField(null=True, default=lambda: datetime.now(timezone.utc))
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
        try:
            Follow.create(follower=self, followed=user)
        except IntegrityError:
            pass  # lost a concurrent follow race; the row already exists

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
