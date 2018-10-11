from flask import Flask

app = Flask(__name__)

# imported at the bottom to avoid circular imports
from app import routes
