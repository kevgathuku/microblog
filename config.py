import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DATABASE_PATH = os.environ.get("DATABASE_PATH") or os.path.join(basedir, "app.db")
    POSTS_PER_PAGE = 3

    LOG_FILE = os.path.join(basedir, "logs", "microblog.log")

    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 25)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") is not None
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    ADMINS = [os.environ.get("ADMIN_EMAIL")]


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-for-pytest"
    LOG_FILE = os.path.join(basedir, "logs", "microblog-test.log")
    ADMINS = ["your-email@example.com"]
    MAIL_SERVER = "localhost"
    MAIL_PORT = 8025


config = {
    "development": Config,
    "testing": TestConfig,
    "default": Config,
}
