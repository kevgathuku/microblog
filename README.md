### Microblog, on Falcon + Peewee

A port of the [Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)
microblog to [Falcon](https://falconframework.org/) (WSGI, class-based resources)
with [Peewee](https://docs.peewee-orm.com/) as the ORM and Jinja templates.
Same pages and behavior: register/login, profiles with follow/unfollow,
edit profile, signed-cookie sessions, per-request DB connections.

## Development

Managed with [uv](https://docs.astral.sh/uv/). Python version is pinned via
`.python-version` (`uv python pin 3.15`) and `requires-python` in `pyproject.toml`.

### Fresh-clone setup

```sh
uv sync                    # create .venv with the exact locked env (fetches Python itself if needed)
uv run pre-commit install  # enable the black pre-commit hook (downloads hook env on first run)
direnv allow               # optional: auto-activates .venv on cd (see .envrc)
uv run pwmigrate up        # create / migrate the local database (falcon.db)
```

```sh
# run the app (no activation needed) — serves http://127.0.0.1:8000
uv run python microblog.py

# add / remove dependencies
uv add <pkg>
uv remove <pkg>

# upgrade one package, or everything
uv lock --upgrade-package <pkg>
uv sync --upgrade
```

Any WSGI server can serve it instead (`app` in `microblog.py` is the
Falcon app): e.g. `uv run --with waitress waitress-serve app:app`.

### Environment variables

| Name           | Default                              | Purpose                                    |
|----------------|--------------------------------------|--------------------------------------------|
| `SECRET_KEY`   | `dev-secret-key-change-me`           | Signs the session cookie. Local dev gets a real one from `.env` (see below); set a proper one anywhere beyond local dev. |
| `DATABASE_URL` | `sqlite:///<repo>/falcon.db`        | SQLite file (or any `sqlite://` URL) the app and `pwmigrate` use. Tests override this per worker (see below). |

`app.db` and `bottle.db` are live databases from earlier iterations —
nothing here reads or writes them.

`SECRET_KEY` for local dev lives in `.env` (gitignored), auto-loaded by
direnv via `.envrc` (`layout uv` + `dotenv`), so no `export`/prefix is
needed once you `direnv allow`. Without direnv, either `export SECRET_KEY=…`
first or prefix each command (`SECRET_KEY=… uv run …`).

### Migrations (`pwmigrate`, via `.pwmigrate`)

Schema changes go through migration files in `migrations/`, tracked in the
`schema_migration` table. The `.pwmigrate` file pins `database = app.models.db`
and `models = app.models`, so commands run bare:

```sh
uv run pwmigrate status    # list migrations ([ ] pending, [x] applied)
uv run pwmigrate up        # apply pending migrations (dev/prod database setup)
uv run pwmigrate down      # revert the most recent migration
uv run pwmigrate diff      # print schema drift between models and the database

# after changing app/models.py:
uv run pwmigrate generate <name>   # write a migration from the schema diff
uv run pwmigrate fake              # mark pending migrations applied without running them
```

App code never creates tables (only `pwmigrate up` and the test suite do).
If the server 500s on missing tables, you skipped `pwmigrate up`.

### Querying (plain `python` shell)

```sh
uv run ipython   # SECRET_KEY comes from .env via direnv
```

```python
from app.models import User, Post, Follow, db

db.connect(reuse_if_open=True)
u = User(username="john", email="john@example.com")
u.set_password("cat")
u.save()

User.get_by_id(1).username                       # by primary key
User.get_or_none(User.username == "john").email # first match or None

# following / followers are queries of User
[x.username for x in u.following]
[x.username for x in u.followers]
u.followers_count()
u.following_count()

# homepage feed: followed users' posts plus your own, newest first
[p.body for p in u.following_posts()]

Post(body="hello", author=u).save()  # author= accepts a User; timestamp defaults to utcnow
db.close()
```

### Tests

```sh
uv run pytest -q            # serial
uv run pytest -n auto -q    # parallel, one worker per CPU
uv run pytest -n 2 -q       # parallel, explicit worker count
```

Each pytest-xdist worker gets its own temp sqlite file (via `DATABASE_URL`
in `tests/conftest.py`) and every test starts from a wiped DB, so tests
stay isolated in both modes. Manual `create_tables` lives only in the test
fixtures — the app itself relies on migrations.

### Layout

- `app/__init__.py` — `create_app()` factory + WSGI `app`, error handlers
- `app/models.py` — Peewee models, `db`, per-request `DatabaseMiddleware`
- `app/auth.py` — signed-cookie session, login helpers, CSRF, auth middleware
- `app/routes.py` — one Falcon resource class per route + Jinja rendering
- `app/templates/` — Jinja templates (unchanged from the Flask version)
- `migrations/` — pwmigrate history (`0001_initial.py`, …)
- `microblog.py` — WSGI entry point + `wsgiref` dev server

### Troubleshooting

- `Address already in use` from `python microblog.py` — something else holds
  port 8000; stop it or serve on another port (e.g. edit the port in
  `microblog.py`, or use waitress with `--port`).
- `pwmigrate` reports a deferred/uninitialized database — `app/models.py`
  binds `db` at import from `DATABASE_URL`; make sure you run it from the
  repo root so `app` is importable.
