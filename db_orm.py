"""SQLAlchemy ORM integration module.

Works side-by-side with db.py (raw MySQL connector):
- SQLAlchemy ORM is used for type-safe CRUD operations, model validation, and entity updates.
- db.py is used for direct SQL reporting views, bulk matrix operations, and stored procedures.
"""
from contextlib import contextmanager

from flask import g
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from config import Config

_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        # Use mysqlconnector driver that is already tested and operational
        connection_url = (
            f"mysql+mysqlconnector://{Config.DB_USER}:{Config.DB_PASSWORD}"
            f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}?charset=utf8mb4"
        )
        _engine = create_engine(
            connection_url,
            pool_size=8,
            max_overflow=4,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionFactory


def get_orm_session():
    """Returns a request-scoped SQLAlchemy Session."""
    if "orm_session" not in g:
        g.orm_session = get_session_factory()()
    return g.orm_session


def close_orm_session(_exc=None):
    """Closes the ORM session on Flask request teardown."""
    sess = g.pop("orm_session", None)
    if sess is not None:
        sess.close()


def init_app(app):
    """Register teardown hook with the Flask application."""
    app.teardown_appcontext(close_orm_session)


@contextmanager
def orm_transaction():
    """Transactional context manager for ORM operations with auto rollback on error."""
    session = get_orm_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
