from datetime import datetime, timedelta, timezone

import pytest  # noqa: E402

from app.models import TABLES, Post, User, db  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    db.connect(reuse_if_open=True)
    db.drop_tables(TABLES, safe=True)
    db.create_tables(TABLES, safe=True)
    yield
    db.drop_tables(TABLES, safe=True)
    db.close()


def usernames(query):
    return [u.username for u in query]


def test_password_hashing():
    u = User(username="susan", email="susan@example.com")
    u.set_password("cat")
    assert not u.check_password("dog")
    assert u.check_password("cat")


def test_avatar():
    u = User(username="john", email="john@example.com")
    assert (
        u.avatar(128) == "https://www.gravatar.com/avatar/"
        "d4c74594d841139328695756648b6bd6"
        "?d=identicon&s=128"
    )


def test_follow():
    u1 = User.create(username="john", email="john@example.com")
    u2 = User.create(username="susan", email="susan@example.com")
    assert usernames(u1.following) == []
    assert usernames(u2.followers) == []

    u1.follow(u2)
    assert u1.is_following(u2)
    assert u1.following_count() == 1
    assert u2.followers_count() == 1
    assert usernames(u1.following) == ["susan"]
    assert usernames(u2.followers) == ["john"]

    u1.unfollow(u2)
    assert not u1.is_following(u2)
    assert u1.following_count() == 0
    assert u2.followers_count() == 0


def test_follow_posts():
    # create four users
    u1 = User.create(username="john", email="john@example.com")
    u2 = User.create(username="susan", email="susan@example.com")
    u3 = User.create(username="mary", email="mary@example.com")
    u4 = User.create(username="david", email="david@example.com")

    # create four posts
    now = datetime.now(timezone.utc)
    Post.create(body="post from john", author=u1, timestamp=now + timedelta(seconds=1))
    Post.create(body="post from susan", author=u2, timestamp=now + timedelta(seconds=4))
    Post.create(body="post from mary", author=u3, timestamp=now + timedelta(seconds=3))
    Post.create(body="post from david", author=u4, timestamp=now + timedelta(seconds=2))

    # setup the followers
    u1.follow(u2)  # john follows susan
    u1.follow(u4)  # john follows david
    u2.follow(u3)  # susan follows mary
    u3.follow(u4)  # mary follows david

    # check the following posts of each user
    f1 = [p.body for p in u1.following_posts()]
    f2 = [p.body for p in u2.following_posts()]
    f3 = [p.body for p in u3.following_posts()]
    f4 = [p.body for p in u4.following_posts()]
    assert f1 == ["post from susan", "post from david", "post from john"]
    assert f2 == ["post from susan", "post from mary"]
    assert f3 == ["post from mary", "post from david"]
    assert f4 == ["post from david"]
