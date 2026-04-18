import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "learning.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
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

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def add_topic(name: str, description: str = "") -> int:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO topics (name, description) VALUES (?, ?)", (name, description))
    conn.commit()
    topic_id = cur.lastrowid
    conn.close()
    return topic_id

def add_note(topic_id: int, title: str, content: str, tags: str = "") -> int:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notes (topic_id, title, content, tags) VALUES (?, ?, ?, ?)",
        (topic_id, title, content, tags)
    )
    conn.commit()
    note_id = cur.lastrowid
    conn.close()
    return note_id

def add_flashcard(topic_id: int, front: str, back: str) -> int:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO flashcards (topic_id, front, back) VALUES (?, ?, ?)",
        (topic_id, front, back)
    )
    conn.commit()
    card_id = cur.lastrowid
    conn.close()
    return card_id

def get_topics():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM topics ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_flashcards(topic_id: int = None):
    conn = get_db()
    cur = conn.cursor()
    if topic_id:
        cur.execute("SELECT * FROM flashcards WHERE topic_id = ? ORDER BY id", (topic_id,))
    else:
        cur.execute("SELECT * FROM flashcards ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_notes(topic_id: int = None):
    conn = get_db()
    cur = conn.cursor()
    if topic_id:
        cur.execute("SELECT * FROM notes WHERE topic_id = ? ORDER BY id", (topic_id,))
    else:
        cur.execute("SELECT * FROM notes ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    init_db()

    # Demo: add a sample topic and flashcard
    topic_id = add_topic("Python Basics", "Fundamental Python programming concepts")
    add_flashcard(topic_id, "What is a list?", "An ordered, mutable collection of items")
    add_flashcard(topic_id, "What is a dictionary?", "A key-value pair data structure")
    add_note(topic_id, "Python Intro", "# Python\nPython is a high-level programming language.", "python,intro")

    print("\nTopics:", get_topics())
    print("Flashcards:", get_flashcards(topic_id))
    print("Notes:", get_notes(topic_id))
    print("\nDone! Your learning database is ready.")
