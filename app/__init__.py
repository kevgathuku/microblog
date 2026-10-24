import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from config import Config
from flask_login import LoginManager

from app.models import User, db

app = Flask(__name__)
app.config.from_object(Config)

login = LoginManager(app)
login.login_view = "login"


@app.before_request
def _db_connect():
    # Registered before routes' handlers so they can query immediately.
    db.connect(reuse_if_open=True)


@app.teardown_appcontext
def _db_close(exc):
    if not db.is_closed():
        db.close()


@login.user_loader
def load_user(id):
    return User.get_or_none(User.id == int(id))


# conftest sets MICROBLOG_ENV=testing; tests assert on responses, never logs.
if not app.debug and os.environ.get("MICROBLOG_ENV") != "testing":
    if not os.path.exists("logs"):
        os.mkdir("logs")
    file_handler = RotatingFileHandler(
        "logs/microblog.log", maxBytes=10240, backupCount=10
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
    )
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info("Microblog startup")

# imported at the bottom to avoid circular imports
from app import routes, errors
