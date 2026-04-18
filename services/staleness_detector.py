"""
Detects stale/outdated content based on topic type and age.
"""
from datetime import datetime, timedelta

# Months after which a topic is considered potentially stale
EVOLVING_THRESHOLDS = {
    "gpt": 3,
    "llm": 6,
    "large language model": 6,
    "claude": 3,
    "ai": 8,
    "artificial intelligence": 8,
    "machine learning": 8,
    "deep learning": 8,
    "neural network": 8,
    "python": 18,
    "javascript": 12,
    "react": 12,
    "node": 12,
    "typescript": 12,
    "html": 24,
    "css": 24,
    "sql": 24,
    "postgresql": 12,
    "sqlite": 24,
    "docker": 12,
    "kubernetes": 12,
    "aws": 12,
    "azure": 12,
    "linux": 36,
    "git": 36,
    "agile": 24,
}

# Patterns that indicate version-specific content (always flag)
VERSION_PATTERNS = [
    r"gpt-\d",
    r"claude-?\d",
    r"gpt\s*\d",
    r"react-?\d+",
    r"angular-?\d+",
    r"vue-?\d+",
    r"node\.js?\s*v?\d",
    r"python\s+v?3\.\d+",
    r"typescript\s+v?\d",
    r"version\s+\d",
    r"(\d+)\.(\d+)\.(\d+)",  # semver
]

import re


def is_version_specific(text: str) -> tuple[bool, str]:
    """Check if text mentions specific versions — always potentially stale."""
    for pat in VERSION_PATTERNS:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return True, f"mentions '{match.group()}'"
    return False, ""


def get_staleness(entry: dict) -> tuple[bool, str]:
    """
    Returns (is_stale, reason) for a qa_entry dict.
    """
    topic_name = (entry.get("topic_name") or "").lower()
    answer = entry.get("answer", "")
    created_at = entry.get("created_at", "")

    # Check for version-specific content first
    stale, reason = is_version_specific(answer)
    if stale:
        return True, f"version-specific content: {reason}"

    # Check age-based thresholds
    if created_at:
        try:
            created = datetime.fromisoformat(created_at)
            age_months = (datetime.now() - created).days / 30

            for keyword, threshold in EVOLVING_THRESHOLDS.items():
                if keyword in topic_name:
                    if age_months > threshold:
                        return True, f"topic '{topic_name}' older than {threshold}mo threshold"
                    break
        except (ValueError, TypeError):
            pass

    return False, ""
