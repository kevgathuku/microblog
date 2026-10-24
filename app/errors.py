from flask import render_template, request
from app import app


@app.errorhandler(404)
def not_found_error(error):
    # Flask doesn't log handled HTTP errors like 404s, so do it here.
    app.logger.warning("404 at %s", request.path)
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500
