### Flask Mega-Tutorial

Following along the [Flask Mega tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)

### Bottle port

This branch ports the app from Flask to [Bottle](https://bottlepy.org/).
Same pages and behavior; framework pieces replaced:

- routing / templates: Bottle + Jinja2 (`jinja2_template`), paths written out
  literally (Bottle has no `url_for`)
- auth: signed cookies (`user_id`) instead of Flask-Login; `remember me`
  sets a 30-day cookie, otherwise a session cookie
- forms: plain WTForms (no Flask-WTF); CSRF via synchronizer token in a
  signed cookie, enforced for every POST by a `before_request` hook
- db: plain SQLAlchemy (`app/db.py`) with standalone Alembic migrations
- flash messages: single-message signed cookie instead of Flask sessions

### Fresh-clone setup

Managed with [uv](https://docs.astral.sh/uv/). Python version is pinned via
`.python-version` (`uv python pin 3.15`) and `requires-python` in `pyproject.toml`.

```sh
uv sync                 # create .venv with the exact locked env (fetches Python itself if needed)
uv run pre-commit install   # enable the black pre-commit hook (downloads hook env on first run)
direnv allow            # optional: auto-activates .venv on cd
uv run alembic upgrade head   # create / migrate the local database
```

```sh
# run the app (debug + auto-reload, http://localhost:5000)
uv run python microblog.py
```

### Environments

`MICROBLOG_ENV` selects `config.py` settings (`development` default,
`testing` for pytest, `production` for deploy):

```sh
MICROBLOG_ENV=production SECRET_KEY=<long-random> uv run waitress-serve --listen=0.0.0.0:8000 microblog:app
```

Production enables `Secure` cookies (needs HTTPS) and disables debug.
`SECRET_KEY` is required — startup fails loudly without it.

# add / remove dependencies
uv add <pkg>
uv remove <pkg>

# upgrade one package, or everything
uv lock --upgrade-package <pkg>
uv sync --upgrade
```

Schema changes: edit `app/models.py`, then

```sh
uv run alembic revision --autogenerate -m "describe change"
# review migrations/versions/*.py, then
uv run alembic upgrade head
```

The branch uses `bottle.db` (gitignored) so it never touches the Flask
branch's `app.db`.

Start a Python interpreter with the app loaded:

```sh
uv run ipython
```

```python
from app.db import Session
from app.models import User
import sqlalchemy as sa
Session.scalars(sa.select(User)).all()
```
