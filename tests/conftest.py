import atexit
import os
import tempfile

import pytest


def pytest_configure(config):
    # Runs in every pytest process (serial + each xdist worker) before
    # collection imports test modules, so `import app` still picks up
    # this DATABASE_PATH. mkstemp → fresh unique sqlite file per worker.
    # Always wins; external DATABASE_PATH is never read.
    worker = os.environ.get("PYTEST_XDIST_WORKER", "master")
    fd, path = tempfile.mkstemp(prefix=f"microblog-{worker}-", suffix=".db")
    os.close(fd)
    atexit.register(lambda: os.path.exists(path) and os.unlink(path))
    os.environ["DATABASE_PATH"] = path
    # Selects TestConfig in app. Must precede `import app`.
    os.environ["FLASK_CONFIG"] = "testing"


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    # One schema per worker process; per-test fixtures only roll back rows.
    # Local imports: app must bind DATABASE_PATH after pytest_configure.
    from app import db
    from app.models import TABLES

    db.connect(reuse_if_open=True)
    db.create_tables(TABLES, safe=True)
    yield
    db.close()
