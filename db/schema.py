import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "learning.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def migrate_schema():
    """Add missing columns and tables (safe migrations)."""
    conn = get_connection()
    cur = conn.cursor()

    # Check if topics table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='topics'")
    if cur.fetchone():
        # topics.is_evolving
        cur.execute("PRAGMA table_info(topics)")
        existing = {col[1] for col in cur.fetchall()}
        if "is_evolving" not in existing:
            cur.execute("ALTER TABLE topics ADD COLUMN is_evolving INTEGER DEFAULT 1")

    # Add indexes for performance (only if tables exist)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qa_entries'")
    if cur.fetchone():
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_qa_topic_id_created
            ON qa_entries(topic_id, created_at)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_qa_created_at
            ON qa_entries(created_at)
        """)

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tags'")
    if cur.fetchone():
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_name
            ON tags(name)
        """)

    conn.commit()
    conn.close()


def init_schema():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    # Topics
    cur.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_evolving INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Q&A entries (normalized: no topic_name, uses topic_id FK)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qa_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
            tags TEXT,
            confidence_level INTEGER DEFAULT 3,
            is_outdated INTEGER DEFAULT 0,
            outdated_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_reviewed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Q&A entry sources (junction table, replaces comma-separated sources string)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qa_entry_sources (
            qa_entry_id INTEGER REFERENCES qa_entries(id) ON DELETE CASCADE,
            source_url TEXT NOT NULL,
            PRIMARY KEY (qa_entry_id, source_url)
        )
    """)

    # User knowledge tracking (normalized: no topic_name, uses topic_id FK)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
            proficiency_level INTEGER DEFAULT 1,
            last_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mention_count INTEGER DEFAULT 1
        )
    """)

    # Outdated content flags
    cur.execute("""
        CREATE TABLE IF NOT EXISTS outdated_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qa_entry_id INTEGER REFERENCES qa_entries(id) ON DELETE CASCADE,
            flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            resolved_at TIMESTAMP
        )
    """)

    # Review summaries
    cur.execute("""
        CREATE TABLE IF NOT EXISTS review_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start DATE NOT NULL,
            new_entries INTEGER DEFAULT 0,
            topics_covered INTEGER DEFAULT 0,
            outdated_flagged INTEGER DEFAULT 0,
            digest TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tags
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Q&A Entry Tags (many-to-many)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qa_entry_tags (
            qa_entry_id INTEGER REFERENCES qa_entries(id) ON DELETE CASCADE,
            tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (qa_entry_id, tag_id)
        )
    """)

    conn.commit()
    conn.close()
    import logging

    logging.getLogger(__name__).info("Schema initialized.")
