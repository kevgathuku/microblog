from app import app
from app.models import Follow, Post, User, db


@app.shell_context_processor
def make_shell_context():
    return {"db": db, "User": User, "Post": Post, "Follow": Follow}
