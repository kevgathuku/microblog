import logging
import os
import sys
import time

from flask import Flask, g, request
from loguru import logger
from config import config, resolve_db_path
from flask_login import LoginManager
from peewee import SqliteDatabase

app = Flask(__name__)
app.config.from_object(config[os.environ.get("FLASK_CONFIG", "default")])

login = LoginManager(app)
login.login_view = "login"

db = SqliteDatabase(None)
db.init(resolve_db_path(app.config["DATABASE_URL"]))


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


if app.testing:
    logger.remove()
elif not app.debug:
    os.makedirs("logs", exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(
        "logs/microblog.log",
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
from app import routes, errors
