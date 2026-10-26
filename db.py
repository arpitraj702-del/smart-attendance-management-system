"""Thin MySQL helper: one pooled connection per Flask request."""
import os
from contextlib import contextmanager
from decimal import Decimal

from flask import g
from mysql.connector import pooling

from config import Config

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        pool_kwargs = {
            "pool_name": "attendance_pool",
            "pool_size": 8,
            "pool_reset_session": True,
            "host": Config.DB_HOST,
            "port": Config.DB_PORT,
            "user": Config.DB_USER,
            "password": Config.DB_PASSWORD,
            "database": Config.DB_NAME,
            "charset": "utf8mb4",
            "autocommit": True,   # every statement commits; use transaction() for groups
            "use_pure": True,
            "ssl_disabled": False,
        }
        if Config.DB_SSL_CA and os.path.exists(Config.DB_SSL_CA):
            pool_kwargs["ssl_ca"] = Config.DB_SSL_CA

        _pool = pooling.MySQLConnectionPool(**pool_kwargs)
    return _pool


def get_db():
    if "db" not in g:
        g.db = _get_pool().get_connection()
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()  # returns it to the pool


def init_app(app):
    app.teardown_appcontext(close_db)


def _clean(row):
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in row.items()}


def query(sql, args=(), one=False):
    cur = get_db().cursor(dictionary=True)
    try:
        cur.execute(sql, args)
        rows = [_clean(r) for r in cur.fetchall()]
    finally:
        cur.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, args=()):
    """Run INSERT/UPDATE/DELETE. Returns (last_insert_id, affected_rows)."""
    cur = get_db().cursor()
    try:
        cur.execute(sql, args)
        return cur.lastrowid, cur.rowcount
    finally:
        cur.close()


@contextmanager
def transaction():
    conn = get_db()
    conn.start_transaction()
    try:
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise
