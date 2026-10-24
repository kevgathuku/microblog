import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(
        basedir, "app.db"
    )
    POSTS_PER_PAGE = 3


def resolve_db_path(url=None):
    """Map a sqlite URL (or plain path) to a filesystem path."""
    url = url or Config.DATABASE_URL
    for prefix in ("sqlite:///", "sqlite://", "sqlite:"):
        if url.startswith(prefix):
            return url[len(prefix) :]
    return url
