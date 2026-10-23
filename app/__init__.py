"""Falcon WSGI app factory (Peewee + Jinja).

Importing this package has no side effects: the app is only built (and the
database only verified) when create_app() is called. That keeps `pwmigrate`
working — it imports app.models, which must not boot the app.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

import falcon

from config import Config, resolve_db_path
from app.auth import AppMiddleware
from app.models import TABLES, DatabaseMiddleware, db
from app.routes import add_routes, render

logger = logging.getLogger("microblog")


def configure_logging():
    # Prod-like only: never in tests, never with DEBUG on
    if os.environ.get("MICROBLOG_ENV") == "testing":
        return
    if os.environ.get("DEBUG", "").lower() in ("1", "true", "yes"):
        return
    if logger.handlers:
        return
    if not os.path.exists("falcon-logs"):
        os.mkdir("falcon-logs")
    handler = RotatingFileHandler(
        "falcon-logs/microblog.log", maxBytes=10240, backupCount=10
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
    )
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("Microblog startup")


def not_found(req, resp, ex, params):
    render(req, resp, "404.html", status=falcon.HTTP_404)


def internal_error(req, resp, ex, params):
    logger.exception("Unhandled exception")
    render(req, resp, "500.html", status=falcon.HTTP_500)


def create_app(database_url=None):
    # Tables are managed with `pwmigrate up`, not here. Re-init only when
    # an explicit URL is passed; otherwise db was bound at import.
    if database_url:
        db.init(resolve_db_path(database_url))
    configure_logging()
    if os.environ.get("MICROBLOG_ENV") != "testing":
        # Tables come from `pwmigrate up`, never from the app. Fail here
        # with a clear message instead of 500ing on the first query
        # (e.g. inside a form validator).
        db.connect(reuse_if_open=True)
        try:
            missing = [m._meta.table_name for m in TABLES if not m.table_exists()]
        finally:
            db.close()
        if missing:
            raise RuntimeError(
                "Database tables missing (%s); run `pwmigrate up`." % ", ".join(missing)
            )
    # Request: connect runs before session/auth (which queries User).
    # Response (reverse order): session cookie is saved before close.
    app = falcon.App(middleware=[DatabaseMiddleware(), AppMiddleware()])
    add_routes(app)
    app.add_error_handler(falcon.HTTPNotFound, not_found)
    app.add_error_handler(Exception, internal_error)
    return app
