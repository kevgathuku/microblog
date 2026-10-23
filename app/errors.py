from bottle import jinja2_template, request, response

from app import app
from app.auth import current_user, get_flashed_messages
from app.db import Session
from app.urls import url


def render_error(tpl):
    # reset the session so a failed transaction can't break rendering below
    Session.rollback()
    return jinja2_template(
        tpl,
        current_user=current_user(request),
        messages=get_flashed_messages(),
        request=request,
        url=url,
    )


@app.error(400)
def bad_request(error):
    response.status = 400
    return render_error("400.html")


@app.error(404)
def not_found(error):
    response.status = 404
    return render_error("404.html")


@app.error(500)
def internal_error(error):
    response.status = 500
    return render_error("500.html")
