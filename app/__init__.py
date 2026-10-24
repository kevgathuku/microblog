import os
import logging
import time
from logging.handlers import RotatingFileHandler

from flask import Flask, g, request
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
    g._t = time.perf_counter()
    db.connect(reuse_if_open=True)


@app.after_request
def _log_request(response):
    app.logger.info(
        "%s %s %s -> %s (%.3fs)",
        request.remote_addr,
        request.method,
        request.path,
        response.status_code,
        time.perf_counter() - g.get("_t", time.perf_counter()),
    )
    return response


@app.teardown_appcontext
def _db_close(exc):
    if not db.is_closed():
        db.close()


@login.user_loader
def load_user(id):
    return User.get_or_none(User.id == int(id))


# conftest sets MICROBLOG_ENV=testing; tests assert on responses, never logs.
# File logging only when debug is off
if not app.debug and os.environ.get("MICROBLOG_ENV") != "testing":
    os.makedirs("logs", exist_ok=True)
    # RotatingFileHandler opens logs/microblog.log on init (delay=False),
    # plus the "Microblog startup" line below guarantees the file exists
    # even on a fresh checkout.
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    )
    file_handler = RotatingFileHandler(
        "logs/microblog.log", maxBytes=10240, backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    # Console keeps Flask's default stderr handler untouched.
    # Peewee logs each SQL statement on the 'peewee' logger at DEBUG --
    # file only, never the console (propagate stays off).
    peewee_logger = logging.getLogger("peewee")
    peewee_logger.setLevel(logging.DEBUG)
    peewee_logger.addHandler(file_handler)
    # Don't double-log via the root logger's default handler.
    peewee_logger.propagate = False
    app.logger.info("Microblog startup")

# imported at the bottom to avoid circular imports
from app import routes, errors
