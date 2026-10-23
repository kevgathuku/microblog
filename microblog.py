from app import app
from config import config

if __name__ == "__main__":
    if config.DEBUG:
        app.run(host="localhost", port=5001, debug=True, reloader=True)
    else:
        # production: serve with waitress (see README), e.g.
        # MICROBLOG_ENV=production uv run waitress-serve --listen=0.0.0.0:8000 microblog:app
        app.run(host="localhost", port=5001)
