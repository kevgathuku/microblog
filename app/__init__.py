import os
from datetime import datetime, timezone

from bottle import Bottle, TEMPLATE_PATH, request

from app.auth import current_user, validate_csrf
from app.db import Session

app = Bottle()
TEMPLATE_PATH.insert(0, os.path.join(os.path.dirname(__file__), "templates"))


@app.hook("before_request")
def update_last_seen():
    user = current_user()
    if user.is_authenticated:
        user.last_seen = datetime.now(timezone.utc)
        Session.commit()


@app.hook("before_request")
def check_csrf():
    if request.method == "POST":
        validate_csrf()


@app.hook("after_request")
def shutdown_session():
    Session.remove()


# imported at the bottom to avoid circular imports
from app import routes, errors  # noqa: E402,F401
