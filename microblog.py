"""WSGI entry point + dev server for the Falcon port (DB: falcon.db)."""

from app import app
from app.models import Follow, Post, User, db

application = app

if __name__ == "__main__":
    db.connect(reuse_if_open=True)
    db.create_tables([User, Follow, Post], safe=True)
    db.close()
    from wsgiref.simple_server import make_server

    with make_server("127.0.0.1", 8000, app) as httpd:
        print("Serving on http://127.0.0.1:8000 (DB: falcon.db)")
        httpd.serve_forever()
