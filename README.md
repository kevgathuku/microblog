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
uv run flask db upgrade # create / migrate the local database
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
# Downgrade all migrations
flask db downgrade base

# Migrate up to the latest migration
flask db upgrade
```

Start a Python interpreter in the context of the application

```sh
flask shell
```

### Querying (`flask shell`)

```python
from app import db
from app.models import User, Post

u = db.session.get(User, 1)                                        # by primary key
susan = db.session.scalar(db.select(User).where(User.username == "susan"))

# followers / following are WriteOnlyMapped: select through them
# list of User
db.session.scalars(u.followers.select()).all()
db.session.scalars(u.following.select()).all()

# just the number
u.followers_count()
u.following_count()

# homepage feed: followed users' posts plus your own, newest first
db.session.scalars(u.following_posts()).all()
```

### Tests

```sh
uv run pytest -q            # serial
uv run pytest -n auto -q    # parallel, one worker per CPU
uv run pytest -n 2 -q       # parallel, explicit worker count
```

Each pytest-xdist worker gets its own temp sqlite file and every test
starts from a wiped DB, so tests stay isolated in both modes.
