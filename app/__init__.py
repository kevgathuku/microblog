import logging
import os
import sys
import time

from flask import Flask, g, request
from flask_login import LoginManager
from loguru import logger
from peewee import SqliteDatabase

from config import config

app = Flask(__name__)
app.config.from_object(config[os.environ.get("FLASK_CONFIG", "default")])

login = LoginManager(app)
login.login_view = "login"

db = SqliteDatabase(None)
db.init(app.config["DATABASE_PATH"])


@app.before_request
def _db_connect():
    # Registered before routes' handlers so they can query immediately.
    g._t = time.perf_counter()
    db.connect(reuse_if_open=True)


@app.after_request
def _log_request(response):
    duration_s = time.perf_counter() - g.get("_t", time.perf_counter())
    qs = request.query_string.decode()
    url = request.path + (f"?{qs}" if qs else "")
    logger.bind(
        ip=request.remote_addr,
        method=request.method,
        path=request.path,
        query=qs,
        status=response.status_code,
        duration_ms=round(duration_s * 1000, 3),
    ).info(
        "{} {} {} -> {} ({:.3f}s)",
        request.remote_addr,
        request.method,
        url,
        response.status_code,
        duration_s,
    )
    return response


@app.teardown_appcontext
def _db_close(exc):
    if not db.is_closed():
        db.close()


# Logging via loguru: stdlib records (Flask's 500 tracebacks, peewee SQL)
# are funneled into loguru's sinks by InterceptHandler. File logging only
# when debug is off; conftest sets FLASK_CONFIG=testing to keep tests quiet.
class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Start outside the handler machinery, then skip any remaining
        # stdlib logging frames so the location points at the real caller.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


os.makedirs(os.path.dirname(app.config["LOG_FILE"]), exist_ok=True)
if app.testing:
    # pytest captures stderr per test and shows it on failure; the file
    # keeps the full DEBUG trace (peewee SQL) out of the console.
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(
        app.config["LOG_FILE"],
        level="DEBUG",
        serialize=True,
        rotation="1 MB",
        retention=10,
    )
    # Route peewee's stdlib SQL records into loguru (file gets them at
    # DEBUG); without this they never reach any loguru sink under tests.
    peewee_logger = logging.getLogger("peewee")
    peewee_logger.addHandler(InterceptHandler())
    peewee_logger.setLevel(logging.DEBUG)
    peewee_logger.propagate = False
elif not app.debug:
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(
        app.config["LOG_FILE"],
        level="DEBUG",  # peewee SQL is DEBUG: file only, never the console
        serialize=True,
        rotation="1 MB",
        retention=10,
    )
    # Flask's default stderr handler must go, or every app log prints twice
    # (once in Flask's format, once in loguru's).
    from flask.logging import default_handler

    app.logger.removeHandler(default_handler)
    app.logger.addHandler(InterceptHandler())
    app.logger.setLevel(logging.INFO)
    # Don't propagate: root handlers (gunicorn, pytest) must not re-emit.
    app.logger.propagate = False
    peewee_logger = logging.getLogger("peewee")
    peewee_logger.addHandler(InterceptHandler())
    peewee_logger.setLevel(logging.DEBUG)
    peewee_logger.propagate = False
    logger.info("Microblog startup")

# imported at the bottom to avoid circular imports
from app import errors, routes  # noqa: E402, F401
