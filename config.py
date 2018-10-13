import os


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "\xfe8sR\xfbC\xf6\xdb\x11\xa0\xce\rJ\xed\x19a\xdb\xe3n\x12\x0fS\r\x08"
