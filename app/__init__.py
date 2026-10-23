"""Falcon WSGI app factory (Peewee + Jinja)."""

import falcon

from config import Config, resolve_db_path
from app.auth import AppMiddleware
from app.models import DatabaseMiddleware, db
from app.routes import add_routes, render


def not_found(req, resp, ex, params):
    render(req, resp, "404.html", status=falcon.HTTP_404)


def internal_error(req, resp, ex, params):
    render(req, resp, "500.html", status=falcon.HTTP_500)


def create_app(database_url=None):
    # Tables are managed with `pwmigrate up`, not here. Re-init only when
    # an explicit URL is passed; otherwise db was bound at import.
    if database_url:
        db.init(resolve_db_path(database_url))
    # Request: connect runs before session/auth (which queries User).
    # Response (reverse order): session cookie is saved before close.
    app = falcon.App(middleware=[DatabaseMiddleware(), AppMiddleware()])
    add_routes(app)
    app.add_error_handler(falcon.HTTPNotFound, not_found)
    app.add_error_handler(Exception, internal_error)
    return app


# WSGI entry point; dev DB is falcon.db unless DATABASE_URL says otherwise.
app = create_app()
