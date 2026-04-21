"""
Decides whether a user question/answer pair should be auto-logged to the DB.
"""

import re

# Questions that are NOT factual — skip logging
SKIP_PATTERNS = [
    r"^(hi|hello|hey|howdy|greetings)",
    r"^(thanks|thank you|thx|ty)",
    r"^(sorry|apologies|my bad)",
    r"^(bye|goodbye|see ya|exit|quit)",
    r"^(how are you|what'?s up|whassup)",
    r"^(can you|would you|could you|will you)\s+(help me|do something)",  # meta requests
    r"^(what do you|who are you|are you)",
    r"^(tell me about yourself|about you)",
]

# Patterns that indicate a factual question — log it
LOG_PATTERNS = [
    r"^(what is|what are|what'?s)",
    r"^(how do|how does|how did|how can|how to)",
    r"^(why do|why does|why is|why are)",
    r"^(who is|who are|who was|who did)",
    r"^(when did|when is|when was|when were)",
    r"^(where is|where are|where did)",
    r"^(define|definition of)",
    r"^(explain|describe)",
    r"^(what'?s the difference|diff between)",
    r"^(list|give me)",
    r"^(can (i|you)|is it possible|do (i|you) need)",
    r"^(which|what kind|what type)",
    r"^(how many|how much|how long|how far|how old)",
]

SKIP_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SKIP_PATTERNS]
LOG_PATTERNS = [re.compile(p, re.IGNORECASE) for p in LOG_PATTERNS]


def should_log(question: str) -> tuple[bool, str]:
    """
    Returns (should_log, reason).
    """
    q = question.strip()

    # Explicit skip patterns
    for pat in SKIP_PATTERNS:
        if pat.match(q):
            return False, "casual/meta — skipped"

    # Explicit log patterns
    for pat in LOG_PATTERNS:
        if pat.match(q):
            return True, "factual question"

    # Default: if it looks like a question mark and has substance, log it
    if "?" in q and len(q) > 10:
        return True, "question with '?'"

    # Short or vague — skip
    return False, "too short/vague"


def estimate_confidence(answer: str) -> int:
    """
    Rough heuristic: short answers or hedged language → lower confidence.
    Returns 1-5.
    """
    answer = answer.strip()

    low_confidence_signals = [
        "i'm not sure",
        "i think",
        "probably",
        "might be",
        "may be",
        "could be",
        "not certain",
        "don't know",
        "verify",
        "check",
        "i believe",
        "as far as i know",
    ]
    high_confidence_signals = [
        "for example",
        "specifically",
        "according to",
        "research shows",
        "is defined as",
        "the process",
    ]

    score = 3  # baseline
    lower = answer.lower()
    for sig in low_confidence_signals:
        if sig in lower:
            score -= 1
    for sig in high_confidence_signals:
        if sig in lower:
            score += 1

    return max(1, min(5, score))
