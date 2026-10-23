import sqlalchemy as sa
import sqlalchemy.orm as so

from config import config

engine = sa.create_engine(config.SQLALCHEMY_DATABASE_URI)
Session = so.scoped_session(so.sessionmaker(bind=engine))


class Base(so.DeclarativeBase):
    pass
