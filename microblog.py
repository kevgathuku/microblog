"""WSGI entry point + dev server for the Falcon port (DB: falcon.db)."""

from app import create_app

# Built here (not on `import app`) so importing the package — e.g. from the
# `pwmigrate` CLI — never boots the app or touches the database.
# Dev DB is falcon.db unless DATABASE_URL says otherwise.
app = create_app()

application = app

if __name__ == "__main__":
    # Tables come from `pwmigrate up`; this only serves.
    from wsgiref.simple_server import make_server

    with make_server("127.0.0.1", 8000, app) as httpd:
        print("Serving on http://127.0.0.1:8000 (DB: falcon.db)")
        httpd.serve_forever()
