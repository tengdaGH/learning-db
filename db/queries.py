from datetime import datetime, timedelta
from db.schema import get_connection

# ─── Topics ───────────────────────────────────────────────────────────────────

def get_or_create_topic(name: str, is_evolving: int = 1) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM topics WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        conn.close()
        return row["id"]
    cur.execute(
        "INSERT INTO topics (name, is_evolving) VALUES (?, ?)",
        (name, is_evolving)
    )
    conn.commit()
    topic_id = cur.lastrowid
    conn.close()
    return topic_id

def get_all_topics():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM topics ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_topics_with_counts():
    """Return topics with qa_count for tree display."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.*, COUNT(q.id) as qa_count
        FROM topics t
        LEFT JOIN qa_entries q ON t.id = q.topic_id
        GROUP BY t.id
        ORDER BY t.name
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_topic_by_name(name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM topics WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

# ─── Q&A Entries ──────────────────────────────────────────────────────────────

def add_qa_entry(
    question: str,
    answer: str,
    topic_name: str = None,
    topic_id: int = None,
    tags: str = "",
    confidence_level: int = 3,
    sources: str = ""
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO qa_entries
        (question, answer, topic_name, topic_id, tags, confidence_level, sources)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (question, answer, topic_name, topic_id, tags, confidence_level, sources))
    conn.commit()
    entry_id = cur.lastrowid
    conn.close()
    return entry_id

def get_recent_qa_entries(limit: int = 20):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM qa_entries
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_qa_entries_by_topic(topic_name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM qa_entries WHERE topic_name = ? ORDER BY created_at DESC",
        (topic_name,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_qa_entries_by_topic_id(topic_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, question, answer, created_at FROM qa_entries WHERE topic_id = ? ORDER BY created_at DESC",
        (topic_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_entry_outdated(entry_id: int, reason: str = ""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE qa_entries SET is_outdated = 1, outdated_reason = ? WHERE id = ?",
        (reason, entry_id)
    )
    conn.commit()
    conn.close()

def update_qa_entry(entry_id: int, answer: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE qa_entries
        SET answer = ?, is_outdated = 0, outdated_reason = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (answer, entry_id))
    conn.commit()
    conn.close()

def get_all_qa_entries():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM qa_entries ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── User Knowledge ───────────────────────────────────────────────────────────

def update_user_knowledge(topic_name: str, proficiency: int = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM user_knowledge WHERE topic_name = ?",
        (topic_name,)
    )
    row = cur.fetchone()
    if row:
        new_count = row["mention_count"] + 1
        if proficiency and proficiency > row["proficiency_level"]:
            cur.execute("""
                UPDATE user_knowledge
                SET mention_count = ?, proficiency_level = ?,
                    last_mentioned = CURRENT_TIMESTAMP
                WHERE topic_name = ?
            """, (new_count, proficiency, topic_name))
        else:
            cur.execute("""
                UPDATE user_knowledge
                SET mention_count = ?, last_mentioned = CURRENT_TIMESTAMP
                WHERE topic_name = ?
            """, (new_count, topic_name))
    else:
        pid = get_or_create_topic(topic_name)
        cur.execute("""
            INSERT INTO user_knowledge (topic_id, topic_name, proficiency_level)
            VALUES (?, ?, ?)
        """, (pid, topic_name, proficiency or 1))
    conn.commit()
    conn.close()

def get_user_knowledge():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_knowledge ORDER BY last_mentioned DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_topics():
    """Return list of topic names user has engaged with."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT topic_name, proficiency_level FROM user_knowledge ORDER BY last_mentioned DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── Outdated Flags ───────────────────────────────────────────────────────────

def add_outdated_flag(qa_entry_id: int, reason: str = "") -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO outdated_flags (qa_entry_id, reason) VALUES (?, ?)
    """, (qa_entry_id, reason))
    conn.commit()
    flag_id = cur.lastrowid
    conn.close()
    return flag_id

def get_pending_outdated_flags():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT of.*, q.question, q.answer, q.topic_name
        FROM outdated_flags of
        JOIN qa_entries q ON of.qa_entry_id = q.id
        WHERE of.status = 'pending'
        ORDER BY of.flagged_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def resolve_outdated_flag(flag_id: int, status: str = "verified_current"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE outdated_flags
        SET status = ?, resolved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, flag_id))
    conn.commit()
    conn.close()

# ─── Review Summaries ─────────────────────────────────────────────────────────

def save_review_summary(week_start: str, new_entries: int, topics_covered: int,
                         outdated_flagged: int, digest: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO review_summaries
        (week_start, new_entries, topics_covered, outdated_flagged, digest)
        VALUES (?, ?, ?, ?, ?)
    """, (week_start, new_entries, topics_covered, outdated_flagged, digest))
    conn.commit()
    summary_id = cur.lastrowid
    conn.close()
    return summary_id

def get_latest_review_summary():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM review_summaries
        ORDER BY week_start DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_review_summaries(limit: int = 4):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM review_summaries
        ORDER BY week_start DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── Gap Detection ─────────────────────────────────────────────────────────────

def get_knowledge_graph():
    """Return all topics with their Q&A counts and recency for gap analysis."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            t.name,
            t.is_evolving,
            COUNT(q.id) as qa_count,
            MAX(q.created_at) as last_qa
        FROM topics t
        LEFT JOIN qa_entries q ON t.id = q.topic_id
        GROUP BY t.id
        ORDER BY qa_count ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
