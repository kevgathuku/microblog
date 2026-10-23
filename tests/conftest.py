import atexit
import os
import tempfile

# Module-level (not a hook): conftest imports before any test module in every
# pytest process, so this runs ahead of `import app` serially and in each
# pytest-xdist worker. mkstemp per process → per-worker sqlite file.
# Always wins; external DATABASE_URL is never read.
_worker = os.environ.get("PYTEST_XDIST_WORKER", "master")
_fd, _path = tempfile.mkstemp(prefix="microblog-{}-".format(_worker), suffix=".db")
os.close(_fd)
atexit.register(lambda: os.path.exists(_path) and os.unlink(_path))
os.environ["DATABASE_URL"] = "sqlite:///{}".format(_path)
os.environ["MICROBLOG_ENV"] = "testing"
