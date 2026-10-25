import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DATABASE_PATH = os.environ.get("DATABASE_PATH") or os.path.join(basedir, "app.db")
    POSTS_PER_PAGE = 3
    LOG_FILE = os.path.join(basedir, "logs", "microblog.log")


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-for-pytest"
    LOG_FILE = os.path.join(basedir, "logs", "microblog-test.log")


config = {
    "development": Config,
    "testing": TestConfig,
    "default": Config,
}
