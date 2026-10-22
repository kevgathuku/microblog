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
# run the app (no activation needed)
uv run flask run

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
