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
    assert list(u1.following) == []
    assert list(u2.followers) == []

    u1.follow(u2)
    assert u1.is_following(u2)
    assert u1.following_count == 1
    assert u2.followers_count == 1
    assert list(u1.following) == [u2]
    assert list(u2.followers) == [u1]

    u1.unfollow(u2)
    assert not u1.is_following(u2)
    assert u1.following_count == 0
    assert u2.followers_count == 0


def test_follow_posts():
    # create four users
    u1 = User.create(username="john", email="john@example.com")
    u2 = User.create(username="susan", email="susan@example.com")
    u3 = User.create(username="mary", email="mary@example.com")
    u4 = User.create(username="david", email="david@example.com")

    # create four posts
    now = datetime.now(timezone.utc)
    p1 = Post.create(
        body="post from john", author=u1, timestamp=now + timedelta(seconds=1)
    )
    p2 = Post.create(
        body="post from susan", author=u2, timestamp=now + timedelta(seconds=4)
    )
    p3 = Post.create(
        body="post from mary", author=u3, timestamp=now + timedelta(seconds=3)
    )
    p4 = Post.create(
        body="post from david", author=u4, timestamp=now + timedelta(seconds=2)
    )

    # setup the followers
    u1.follow(u2)  # john follows susan
    u1.follow(u4)  # john follows david
    u2.follow(u3)  # susan follows mary
    u3.follow(u4)  # mary follows david

    # check the following posts of each user
    f1 = list(u1.following_posts())
    f2 = list(u2.following_posts())
    f3 = list(u3.following_posts())
    f4 = list(u4.following_posts())
    assert f1 == [p2, p4, p1]
    assert f2 == [p2, p3]
    assert f3 == [p3, p4]
    assert f4 == [p4]
