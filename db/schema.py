import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "learning.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def migrate_schema():
    """Add missing columns to existing tables (safe migrations)."""
    conn = get_connection()
    cur = conn.cursor()

    # topics.is_evolving
    cur.execute("PRAGMA table_info(topics)")
    existing = {col[1] for col in cur.fetchall()}
    if "is_evolving" not in existing:
        cur.execute("ALTER TABLE topics ADD COLUMN is_evolving INTEGER DEFAULT 1")

    conn.commit()
    conn.close()


def init_schema():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    # Existing tables (from learning_db.py)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_evolving INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
            front TEXT NOT NULL,
            back TEXT NOT NULL,
            difficulty INTEGER DEFAULT 2,
            last_reviewed TIMESTAMP,
            next_review TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
            cards_reviewed INTEGER DEFAULT 0,
            cards_correct INTEGER DEFAULT 0,
            duration_minutes INTEGER,
            studied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # New: Q&A entries
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qa_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
            topic_name TEXT,
            tags TEXT,
            confidence_level INTEGER DEFAULT 3,
            sources TEXT,
            is_outdated INTEGER DEFAULT 0,
            outdated_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_reviewed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # New: User knowledge tracking
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
            topic_name TEXT NOT NULL UNIQUE,
            proficiency_level INTEGER DEFAULT 1,
            last_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mention_count INTEGER DEFAULT 1
        )
    """)

    # New: Outdated content flags
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

    # New: Review summaries
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

    # New: Tags
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # New: Q&A Entry Tags (many-to-many)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qa_entry_tags (
            qa_entry_id INTEGER REFERENCES qa_entries(id) ON DELETE CASCADE,
            tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (qa_entry_id, tag_id)
        )
    """)

    conn.commit()
    conn.close()
    print("Schema initialized.")
