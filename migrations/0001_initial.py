# Generated from a schema diff on 2026-10-23 23:03.
import datetime
from peewee import *

utcnow = lambda: datetime.datetime.now(datetime.timezone.utc)


def up(migrator, db):
    class User(Model):
        username = CharField(unique=True, max_length=64)
        email = CharField(unique=True, max_length=120)
        about_me = CharField(null=True, max_length=140)
        last_seen = DateTimeField(null=True, default=utcnow)
        password_hash = CharField(null=True, max_length=256)

        class Meta:
            database = db
            table_name = "user"

    db.create_tables([User])

    class Follow(Model):
        follower = ForeignKeyField(User)
        followed = ForeignKeyField(User)

        class Meta:
            database = db
            table_name = "follow"
            primary_key = CompositeKey("follower", "followed")

    db.create_tables([Follow])

    class Post(Model):
        body = CharField(max_length=140)
        timestamp = DateTimeField(index=True, default=utcnow)
        user = ForeignKeyField(User)

        class Meta:
            database = db
            table_name = "post"

    db.create_tables([Post])


def down(migrator, db):
    migrator.migrate(migrator.drop_table("post"))
    migrator.migrate(migrator.drop_table("follow"))
    migrator.migrate(migrator.drop_table("user"))
