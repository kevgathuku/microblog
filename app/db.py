import sqlalchemy as sa
import sqlalchemy.orm as so

from config import Config

engine = sa.create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = so.scoped_session(so.sessionmaker(bind=engine))


class Base(so.DeclarativeBase):
    pass
