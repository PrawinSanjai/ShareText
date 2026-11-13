from contextlib import contextmanager
from sqlalchemy import create_engine

from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.schema import MetaData

from config import Configuration


config = Configuration()

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=NAMING_CONVENTION)
base = declarative_base(metadata=metadata)
engine = create_engine(
    url=config.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=config.DB_POOL_SIZE,
    max_overflow=config.DB_MAX_OVERFLOW,
)
db_session = sessionmaker(autocommit=False, expire_on_commit=False, autoflush=True, bind=engine)


@contextmanager
def get_db():
    """Open a session, commit on success, and roll back on failure."""
    db = db_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
