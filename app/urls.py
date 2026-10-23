import re


def url(name, **params):
    """Build a URL from a route name, e.g. url('profile', username='ann')."""
    from app import app  # lazy: app only exists after app/__init__ runs

    for route in app.routes:
        if route.name == name:
            return re.sub(
                r"<(\w+)(?::[^>]*)?>", lambda m: str(params[m.group(1)]), route.rule
            )
    raise ValueError("unknown route: {}".format(name))
