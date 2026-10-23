import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    # required to sign login/flash cookies; override per environment
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "bottle.db")
