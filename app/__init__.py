import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from bottle import TEMPLATE_PATH, Bottle, abort, request
from result import Err, Ok

from app.auth import current_user, validate_csrf
from app.db import Session
from config import config

app = Bottle()
TEMPLATE_PATH.insert(0, os.path.join(os.path.dirname(__file__), "templates"))

logger = logging.getLogger("microblog")
if config.TESTING:
    # Tests assert on responses, never on logs - stay silent (also silences
    # the 500 handler, which reuses this named logger). No handlers, no files.
    logger.disabled = True
elif not config.DEBUG and not logger.handlers:
    os.makedirs("bottle-logs", exist_ok=True)
    file_handler = RotatingFileHandler(
        "bottle-logs/microblog.log", maxBytes=10240, backupCount=10
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
    )
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.info("Microblog startup")


@app.hook("before_request")
def update_last_seen():
    user = current_user(request)
    if user.is_authenticated:
        user.last_seen = datetime.now(timezone.utc)
        Session.commit()


@app.hook("before_request")
def check_csrf():
    if request.method == "POST":
        match validate_csrf(request):
            case Ok():
                return
            case Err(e):
                abort(400, "CSRF validation failed: {}".format(e))


@app.hook("after_request")
def shutdown_session():
    Session.remove()


# imported at the bottom to avoid circular imports
from app import errors, routes  # noqa: E402,F401
