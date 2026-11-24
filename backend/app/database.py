from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import DATABASE_URL, ensure_database_directory

class Base(DeclarativeBase):
    pass

ensure_database_directory(DATABASE_URL)

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False, 'timeout': 15})

@event.listens_for(engine, 'connect')
def sqlite_settings(connection, _):
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA busy_timeout=15000')
    connection.execute('PRAGMA journal_mode=WAL')

SessionLocal = sessionmaker(engine, expire_on_commit=False)

@contextmanager
def transaction():
    # Serialize read/validate/write transactions before reading booking state.
    with SessionLocal() as db:
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
