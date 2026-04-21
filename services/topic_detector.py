"""
Extracts topics and tags from a Q&A pair.
Uses LLM to dynamically determine topics and cluster around existing ones.
"""
import os
import time


def _call_llm(prompt: str, system: str = "", max_tokens: int = 100) -> str:
    """Call MiniMax via Anthropic-compatible SDK."""
    import anthropic
    import config

    client = anthropic.Anthropic(
        auth_token=config.MINIMAX_API_KEY,
        base_url=config.MINIMAX_BASE_URL,
    )

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(3):
        try:
            response = client.messages.create(
                model=config.MINIMAX_MODEL,
                max_tokens=max_tokens,
                messages=messages,
                stream=False,
            )
            for block in response.content:
                if block.type == "text" and getattr(block, "text", None):
                    return block.text
            return "[No response content]"
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return f"[Error: {e}]"


def extract_primary_topic(question: str, answer: str = "", existing_topics: list = None) -> tuple[str, bool]:
    """
    Determine the best topic for a question using the LLM.

    Returns (topic_name, is_new_topic):
    - topic_name: the determined topic (clustered with existing or new)
    - is_new_topic: True if this is a genuinely new topic not in existing_topics

    Uses LLM for all questions to ensure any topic can be properly categorized.
    Clusters new questions around similar existing topics when semantically appropriate.
    """
    # Build context of existing topics to encourage clustering
    topics_context = ""
    if existing_topics:
        topic_names = [t['topic_name'] for t in existing_topics[:20]]
        topics_context = "Existing topics: " + ", ".join(topic_names)

    system = f"""You are a topic classifier for a personal learning database.
{topics_context}

Analyze the question and determine the best topic.

Rules:
- If the question fits an existing topic, respond with: EXISTING: <topic name>
- If the question is genuinely new, respond with: NEW: <topic name>
- Keep topic names short (1-3 words) and consistent with existing naming style
- Be specific but not overly narrow
- For questions about concepts, theories, or thinkers, use the broader field (e.g., "Philosophy", "Physics", "History")
- For how-to questions, use the subject area (e.g., "Cooking", "Photography")

Examples:
Q: "what is the capital of france" → EXISTING: Geography (if exists) or NEW: Geography
Q: "how do neural networks learn" → EXISTING: Machine Learning (if exists) or NEW: Machine Learning
Q: "what did aristotle say about virtue" → EXISTING: Philosophy or NEW: Philosophy
Q: "best way to cook rice" → EXISTING: Cooking or NEW: Cooking"""

    response = _call_llm(question, system=system, max_tokens=50)

    if response.startswith("EXISTING:"):
        topic = response.split("EXISTING:")[1].strip()
        return topic, False
    elif response.startswith("NEW:"):
        topic = response.split("NEW:")[1].strip()
        return topic, True
    else:
        # Fallback - extract a likely topic from the question
        words = question.split()
        for word in reversed(words):
            if len(word) > 4 and word.lower() not in {
                "what", "which", "about", "from", "with", "this", "that",
                "have", "been", "were", "they", "their", "would", "could",
                "should", "would", "could", "according", "braun's",
            }:
                return word.capitalize(), True
        return "General", True


def extract_tags(question: str, answer: str = "") -> str:
    """Extract comma-separated tags from question and answer."""
    import re

    text = (question + " " + answer).lower()

    tags = set()

    # Extract capitalized terms (potential proper nouns / tech terms)
    combined = question + " " + answer
    caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", combined)
    for cap in caps:
        if len(cap) > 3 and cap.lower() not in {"what", "which", "where", "when", "how", "this", "that", "aristotle", "braun"}:
            tags.add(cap.lower().replace(" ", "-"))

    # Extract significant words
    words = re.findall(r'\b[a-z]{4,}\b', text)
    stopwords = {'what', 'which', 'about', 'from', 'with', 'this', 'that', 'have', 'been', 'were', 'they', 'their', 'would', 'could', 'should', 'when', 'where', 'there', 'here', 'about'}
    for word in words:
        if word not in stopwords:
            tags.add(word)

    return ",".join(sorted(tags)) if tags else ""


def extract_sources(answer: str) -> str:
    """Find URLs or citations in the answer."""
    import re
    urls = re.findall(r"https?://[^\s\),\"]+", answer)
    return ",".join(urls) if urls else ""
