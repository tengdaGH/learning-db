from datetime import datetime, timedelta
from db.connection import get_db

# ─── Topics ───────────────────────────────────────────────────────────────────

def get_or_create_topic(name: str, is_evolving: int = 1) -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM topics WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute(
            "INSERT INTO topics (name, is_evolving) VALUES (?, ?)",
            (name, is_evolving)
        )
        return cur.lastrowid

def get_all_topics():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM topics ORDER BY name")
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def get_all_topics_with_counts():
    """Return topics with qa_count for tree display."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.*, COUNT(q.id) as qa_count
            FROM topics t
            LEFT JOIN qa_entries q ON t.id = q.topic_id
            GROUP BY t.id
            ORDER BY qa_count DESC, t.name
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def get_topic_by_name(name: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM topics WHERE name = ?", (name,))
        row = cur.fetchone()
        return dict(row) if row else None

# ─── Q&A Entries ──────────────────────────────────────────────────────────────

def _get_sources_for_entry(cur, entry_id: int) -> list:
    """Fetch source URLs for a Q&A entry from junction table."""
    cur.execute(
        "SELECT source_url FROM qa_entry_sources WHERE qa_entry_id = ?",
        (entry_id,)
    )
    return [row["source_url"] for row in cur.fetchall()]

def _format_entry(row: sqlite3.Row, cur) -> dict:
    """Format a row into a dict and fetch sources."""
    entry = dict(row)
    entry["sources"] = _get_sources_for_entry(cur, entry["id"])
    return entry

def add_qa_entry(
    question: str,
    answer: str,
    topic_id: int = None,
    tags: str = "",
    confidence_level: int = 3,
    sources: list = None
) -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO qa_entries
            (question, answer, topic_id, tags, confidence_level)
            VALUES (?, ?, ?, ?, ?)
        """, (question, answer, topic_id, tags, confidence_level))
        entry_id = cur.lastrowid
        
        # Insert sources into junction table
        if sources:
            for url in sources:
                if url:
                    cur.execute(
                        "INSERT OR IGNORE INTO qa_entry_sources (qa_entry_id, source_url) VALUES (?, ?)",
                        (entry_id, url)
                    )
        
        return entry_id

def get_qa_entry(entry_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT q.*, t.name as topic_name
            FROM qa_entries q
            LEFT JOIN topics t ON q.topic_id = t.id
            WHERE q.id = ?
        """, (entry_id,))
        row = cur.fetchone()
        if row:
            return _format_entry(row, cur)
        return None

def get_recent_qa_entries(limit: int = 20):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT q.*, t.name as topic_name
            FROM qa_entries q
            LEFT JOIN topics t ON q.topic_id = t.id
            ORDER BY q.created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        return [_format_entry(r, cur) for r in rows]

def get_qa_entries_by_topic(topic_name: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT q.*, t.name as topic_name
            FROM qa_entries q
            JOIN topics t ON q.topic_id = t.id
            WHERE t.name = ?
            ORDER BY q.created_at DESC
        """, (topic_name,))
        rows = cur.fetchall()
        return [_format_entry(r, cur) for r in rows]

def get_qa_entries_by_topic_id(topic_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT q.id, q.question, q.answer, q.created_at, t.name as topic_name
            FROM qa_entries q
            LEFT JOIN topics t ON q.topic_id = t.id
            WHERE q.topic_id = ?
            ORDER BY q.created_at DESC
        """, (topic_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def mark_entry_outdated(entry_id: int, reason: str = ""):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE qa_entries SET is_outdated = 1, outdated_reason = ? WHERE id = ?",
            (reason, entry_id)
        )

def update_qa_entry(entry_id: int, answer: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE qa_entries
            SET answer = ?, is_outdated = 0, outdated_reason = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (answer, entry_id))

def get_all_qa_entries():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT q.*, t.name as topic_name
            FROM qa_entries q
            LEFT JOIN topics t ON q.topic_id = t.id
            ORDER BY q.created_at DESC
        """)
        rows = cur.fetchall()
        return [_format_entry(r, cur) for r in rows]

# ─── User Knowledge ───────────────────────────────────────────────────────────

def update_user_knowledge(topic_id: int, proficiency: int = None):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM user_knowledge WHERE topic_id = ?",
            (topic_id,)
        )
        row = cur.fetchone()
        if row:
            new_count = row["mention_count"] + 1
            if proficiency and proficiency > row["proficiency_level"]:
                cur.execute("""
                    UPDATE user_knowledge
                    SET mention_count = ?, proficiency_level = ?,
                        last_mentioned = CURRENT_TIMESTAMP
                    WHERE topic_id = ?
                """, (new_count, proficiency, topic_id))
            else:
                cur.execute("""
                    UPDATE user_knowledge
                    SET mention_count = ?, last_mentioned = CURRENT_TIMESTAMP
                    WHERE topic_id = ?
                """, (new_count, topic_id))
        else:
            cur.execute("""
                INSERT INTO user_knowledge (topic_id, proficiency_level)
                VALUES (?, ?)
            """, (topic_id, proficiency or 1))

def get_user_knowledge():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT uk.*, t.name as topic_name
            FROM user_knowledge uk
            JOIN topics t ON uk.topic_id = t.id
            ORDER BY uk.last_mentioned DESC
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def get_user_topics():
    """Return list of topic names user has engaged with."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.name as topic_name, uk.proficiency_level
            FROM user_knowledge uk
            JOIN topics t ON uk.topic_id = t.id
            ORDER BY uk.last_mentioned DESC
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

# ─── Outdated Flags ───────────────────────────────────────────────────────────

def add_outdated_flag(qa_entry_id: int, reason: str = "") -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO outdated_flags (qa_entry_id, reason) VALUES (?, ?)
        """, (qa_entry_id, reason))
        return cur.lastrowid

def get_pending_outdated_flags():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT of.*, q.question, q.answer
            FROM outdated_flags of
            JOIN qa_entries q ON of.qa_entry_id = q.id
            WHERE of.status = 'pending'
            ORDER BY of.flagged_at DESC
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def resolve_outdated_flag(flag_id: int, status: str = "verified_current"):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE outdated_flags
            SET status = ?, resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, flag_id))

# ─── Review Summaries ─────────────────────────────────────────────────────────

def save_review_summary(week_start: str, new_entries: int, topics_covered: int,
                         outdated_flagged: int, digest: str) -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO review_summaries
            (week_start, new_entries, topics_covered, outdated_flagged, digest)
            VALUES (?, ?, ?, ?, ?)
        """, (week_start, new_entries, topics_covered, outdated_flagged, digest))
        return cur.lastrowid

def get_latest_review_summary():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM review_summaries
            ORDER BY week_start DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        return dict(row) if row else None

def get_review_summaries(limit: int = 4):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM review_summaries
            ORDER BY week_start DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

# ─── Gap Detection ─────────────────────────────────────────────────────────────

def get_knowledge_graph():
    """Return all topics with their Q&A counts and recency for gap analysis."""
    with get_db() as conn:
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
        return [dict(r) for r in rows]

def get_new_entries_today():
    """Return count of Q&A entries created today."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as count FROM qa_entries
            WHERE DATE(created_at) = DATE('now')
        """)
        row = cur.fetchone()
        return row["count"] if row else 0

# ─── Tags ───────────────────────────────────────────────────────────────────────

def get_or_create_tag(name: str) -> int:
    """Get existing tag id or create new one."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM tags WHERE name = ?", (name.lower(),))
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute("INSERT INTO tags (name) VALUES (?)", (name.lower(),))
        return cur.lastrowid

def get_all_tags():
    """Return all tags with entry counts."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id, t.name, COUNT(qet.qa_entry_id) as entry_count
            FROM tags t
            LEFT JOIN qa_entry_tags qet ON t.id = qet.tag_id
            GROUP BY t.id
            ORDER BY entry_count DESC, t.name
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def get_tags_for_entry(qa_entry_id: int):
    """Get all tags for a specific Q&A entry."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id, t.name FROM tags t
            JOIN qa_entry_tags qet ON t.id = qet.tag_id
            WHERE qet.qa_entry_id = ?
        """, (qa_entry_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def set_tags_for_entry(qa_entry_id: int, tag_names: list):
    """Replace all tags for a Q&A entry with new set."""
    with get_db() as conn:
        cur = conn.cursor()
        # Remove existing tags
        cur.execute("DELETE FROM qa_entry_tags WHERE qa_entry_id = ?", (qa_entry_id,))
        # Add new tags
        for name in tag_names:
            if name and len(name) > 1:
                tag_id = get_or_create_tag(name.strip())
                cur.execute(
                    "INSERT OR IGNORE INTO qa_entry_tags (qa_entry_id, tag_id) VALUES (?, ?)",
                    (qa_entry_id, tag_id)
                )

def get_entries_by_tag(tag_name: str):
    """Get all Q&A entries with a specific tag."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT q.*, t.name as topic_name
            FROM qa_entries q
            JOIN qa_entry_tags qet ON q.id = qet.qa_entry_id
            JOIN tags t ON qet.tag_id = t.id
            WHERE t.name = ?
            ORDER BY q.created_at DESC
        """, (tag_name.lower(),))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def delete_unused_tags():
    """Remove tags with no associated entries."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM tags WHERE id NOT IN (
                SELECT DISTINCT tag_id FROM qa_entry_tags
            )
        """)
        return cur.rowcount

def find_similar_tags():
    """Find tags that might be duplicates (similar names)."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM tags ORDER BY name")
        tags = [dict(r) for r in cur.fetchall()]

    similar = []
    for i, t1 in enumerate(tags):
        for t2 in tags[i+1:]:
            # Check if one is prefix/suffix of other or very similar
            n1, n2 = t1["name"], t2["name"]
            if n1.startswith(n2[:4]) or n2.startswith(n1[:4]):
                similar.append((t1, t2))
    return similar

def merge_tags(source_tag_id: int, target_tag_id: int):
    """Move all entries from source tag to target tag, then delete source."""
    with get_db() as conn:
        cur = conn.cursor()
        # Update entry tags to use target
        cur.execute("""
            UPDATE qa_entry_tags SET tag_id = ?
            WHERE tag_id = ? AND qa_entry_id IN (
                SELECT qa_entry_id FROM qa_entry_tags WHERE tag_id = ?
            )
        """, (target_tag_id, source_tag_id, source_tag_id))
        # Delete source tag
        cur.execute("DELETE FROM tags WHERE id = ?", (source_tag_id,))
