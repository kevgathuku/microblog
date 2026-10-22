import sqlalchemy as sa
import sqlalchemy.orm as so

# import the flask instance from the app package
from app import app


@app.shell_context_processor
def make_shell_context():
    return {"sa": sa, "so": so}
