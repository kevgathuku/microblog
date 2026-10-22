### Flask Mega-Tutorial

Following along the [Flask Mega tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)

## Development

Managed with [uv](https://docs.astral.sh/uv/). Python version is pinned via
`.python-version` (`uv python pin 3.15`) and `requires-python` in `pyproject.toml`.

```sh
# first-time setup (reproduces the exact locked env)
uv sync

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
