"""
Generates weekly learning digest from the database.
"""

from datetime import datetime, timedelta
from db.queries import (
    get_recent_qa_entries,
    get_pending_outdated_flags,
    get_user_knowledge,
    save_review_summary,
)


def generate_weekly_digest() -> str:
    """Build a human-readable weekly digest."""
    now = datetime.now()
    week_start = now - timedelta(days=7)

    # Gather stats
    recent = get_recent_qa_entries(limit=50)
    knowledge = get_user_knowledge()
    pending_flags = get_pending_outdated_flags()

    # Filter to this week's entries
    this_week = [
        e
        for e in recent
        if e.get("created_at") and datetime.fromisoformat(e["created_at"]) >= week_start
    ]

    lines = [
        "=" * 50,
        "WEEKLY LEARNING DIGEST",
        f"Week of {week_start.strftime('%Y-%m-%d')} → {now.strftime('%Y-%m-%d')}",
        "=" * 50,
        "",
    ]

    # New knowledge
    lines.append(f"📚 NEW KNOWLEDGE: {len(this_week)} entries")
    if this_week:
        for e in this_week[:10]:
            topic = e.get("topic_name", "General")
            lines.append(f"  • [{topic}] {e['question'][:60]}")
        if len(this_week) > 10:
            lines.append(f"  ... and {len(this_week) - 10} more")
    lines.append("")

    # Topics covered
    topics_this_week = set(e.get("topic_name") for e in this_week if e.get("topic_name"))
    lines.append(f"🗂️  TOPICS COVERED: {len(topics_this_week)}")
    for t in sorted(topics_this_week):
        lines.append(f"  • {t}")
    lines.append("")

    # Content needing review
    if pending_flags:
        lines.append(f"⚠️  CONTENT NEEDS REVIEW: {len(pending_flags)} flagged")
        for f in pending_flags[:5]:
            lines.append(f"  • [{f['topic_name']}] {f['question'][:50]}")
        if len(pending_flags) > 5:
            lines.append(f"  ... and {len(pending_flags) - 5} more")
    else:
        lines.append("✅ NO CONTENT NEEDS REVIEW")
    lines.append("")

    # User knowledge summary
    lines.append(f"🧠 YOUR KNOWLEDGE: {len(knowledge)} topics tracked")
    for k in knowledge[:5]:
        lvl = k.get("proficiency_level", 1)
        bar = "█" * lvl + "░" * (4 - lvl)
        lines.append(f"  • {k['topic_name']}: {bar} ({lvl}/4)")
    if len(knowledge) > 5:
        lines.append(f"  ... and {len(knowledge) - 5} more")
    lines.append("")

    # Save to DB
    save_review_summary(
        week_start=str(week_start.date()),
        new_entries=len(this_week),
        topics_covered=len(topics_this_week),
        outdated_flagged=len(pending_flags),
        digest="\n".join(lines),
    )

    return "\n".join(lines)
