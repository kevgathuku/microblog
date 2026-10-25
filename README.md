### Flask Mega-Tutorial

Following along the [Flask Mega tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)

## Development

Managed with [uv](https://docs.astral.sh/uv/). Python version is pinned via
`.python-version` (`uv python pin 3.15`) and `requires-python` in `pyproject.toml`.

### Fresh-clone setup

```sh
uv sync                 # create .venv with the exact locked env (fetches Python itself if needed)
uv run pre-commit install   # enable the black pre-commit hook (downloads hook env on first run)
direnv allow            # optional: auto-activates .venv on cd, so bare `flask` works
uv run pwmigrate up    # create / migrate the local database (pwmigrate, see .pwmigrate)
```

```sh
# run the app
uv run flask run

# run the app in debug mode
uv run flask run --debug

# add / remove dependencies
uv add <pkg>
uv remove <pkg>

# upgrade one package, or everything
uv lock --upgrade-package <pkg>
uv sync --upgrade
```

DB operations

```sh
# Show applied vs pending migrations
uv run pwmigrate status

# Apply pending migrations
uv run pwmigrate up

# Revert the most recent migration
uv run pwmigrate down

# Show schema drift: live DB vs app.models
uv run pwmigrate diff

# Write a migration from the diff
uv run pwmigrate generate <name>
```

Start a Python interpreter in the context of the application

```sh
flask shell
```

### Querying (`flask shell`)

```python
from app.models import User, Post

u = User.get_by_id(1)  # by primary key
susan = User.get_or_none(User.username == "susan")

# followers / following are model properties returning queries
list(u.followers)
list(u.following)

# just the numbers (properties, not methods)
u.followers_count
u.following_count

# homepage feed: followed users' posts plus your own, newest first
list(u.following_posts())
```

### Tests

```sh
uv run pytest -q            # serial
uv run pytest -n auto -q    # parallel, one worker per CPU
uv run pytest -n 2 -q       # parallel, explicit worker count
```

### Test isolation (how and why)

Tests never touch `app.db`. Isolation works in three phases, split by *when*
they must run:

1. **DB path before app import (`tests/conftest.py::pytest_configure`).**
   Each pytest process (serial run, or every xdist worker) `mkstemp`s a fresh
   `microblog-<worker>-*.db` file and sets `DATABASE_URL` (+ `FLASK_CONFIG=testing`)
   in the environment. This must happen in the configure hook — not a fixture —
   because `config.py` reads the environment at import time, and test modules
   `import app` during collection, before any fixture runs. A fixture would be
   too late; the app would bind the dev database.
2. **Static test settings (`config.TestConfig`, selected by `FLASK_CONFIG`).**
   `TESTING = True` and a fixed `SECRET_KEY` (CSRF/sessions need one) are the
   same for every worker, so they live in config. `DATABASE_URL` stays on the
environment because it differs per worker — no static config can hold it.
3. **Schema once per worker (session fixture `_create_schema`).** Creates all
   tables a single time per process. Fixtures *can* do DDL (they run after
   imports); they just can't set the DB path.
4. **Rows per test (function fixtures `clean_db` / `client`).** Each test runs
   inside `db.begin()` and tears down with `db.rollback()` — no per-test DDL.
   Rollback also cleans up failed tests, and is faster than drop/create.

Why one file per worker instead of sharing: xdist workers are separate
processes and SQLite allows a single writer per file. Every test holds a write
transaction open for its full duration, so sharing would mean constant
`database is locked` errors. Separate files also keep identical usernames
(e.g. `tester`) from colliding across workers.

Debugging: tests log to the console at `INFO` (pytest shows captured stderr
for failed tests, nothing extra needed) with the full `DEBUG` trace —
including peewee SQL — in `logs/microblog-test.log`, which CI uploads as an
artifact on every run (`if: always()`).
