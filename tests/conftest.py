import atexit
import os
import tempfile


def pytest_configure(config):
    # Runs in every pytest process (serial + each xdist worker) before
    # collection imports test modules, so `import app` still picks up
    # this DATABASE_URL. mkstemp → fresh unique sqlite file per worker.
    # Always wins; external DATABASE_URL is never read.
    worker = os.environ.get("PYTEST_XDIST_WORKER", "master")
    fd, path = tempfile.mkstemp(prefix=f"microblog-{worker}-", suffix=".db")
    os.close(fd)
    atexit.register(lambda: os.path.exists(path) and os.unlink(path))
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"
    # Selects TestConfig in app. Must precede `import app`.
    os.environ["FLASK_CONFIG"] = "testing"
