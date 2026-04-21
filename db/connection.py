"""
Database connection management with context managers for safe transactions.
"""

from contextlib import contextmanager
from db.schema import get_connection


@contextmanager
def get_db():
    """
    Context manager for database connections.

    Usage:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM topics")
            rows = cur.fetchall()

    Automatically commits on success, rolls back on exception, and closes connection.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
