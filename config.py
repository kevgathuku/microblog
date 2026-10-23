import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # required to sign login/flash/csrf cookies; override per environment
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "bottle.db")
    DEBUG = False
    TESTING = False
    # Secure cookies need HTTPS; only enabled in production
    COOKIE_SECURE = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    SECRET_KEY = os.environ.get("SECRET_KEY")
    COOKIE_SECURE = True


configs = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

if os.environ.get("MICROBLOG_ENV", "development") == "production":
    if not os.environ.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY must be set in the environment "
            "when MICROBLOG_ENV=production (no fallback allowed)"
        )

config = configs[os.environ.get("MICROBLOG_ENV", "development")]
