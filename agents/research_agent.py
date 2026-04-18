"""
Research Agent — answers questions, auto-logs to DB.
Uses web search (Tavily) for time-sensitive / evolving topics.
Uses MiniMax via OpenAI-compatible API for answers.
"""
import re
import time
from db.queries import (
    add_qa_entry,
    update_user_knowledge,
    get_user_topics,
    get_or_create_topic,
)
from services.auto_log import should_log, estimate_confidence
from services.topic_detector import extract_primary_topic, extract_tags
from services.staleness_detector import get_staleness
from db.queries import get_all_qa_entries

# Topics that are time-sensitive and warrant web search
WEB_SEARCH_TRIGGERS = [
    "gpt", "claude", "llm", "large language model", "chatgpt",
    "openai", "anthropic", "ai model", "language model",
    "machine learning model", "deep learning",
    "new release", "latest version", "latest model",
    "cursor", "copilot", "github copilot",
    "react", "nextjs", "vue", "angular", "svelte",
    "python 3", "typescript", "rust", "golang",
    "aws", "azure", "gcp", "google cloud",
    "docker", "kubernetes",
    "ios", "android", "swift", "kotlin",
    "web development", "frontend",
]

VERSION_PATTERN = re.compile(
    r"(gpt-\d|claude-?\d|react-?\d+|vue-?\d+|angular-?\d+|"
    r"python\s+v?3\.\d+|node\.js?\s*v?\d|typescript\s+v?\d|"
    r"version\s+\d|\d+\.\d+\.\d+)",
    re.IGNORECASE
)

# Tavily API keys from environment
def _get_tavily_keys():
    """Get Tavily API keys from environment variables."""
    import os
    keys = []
    key1 = os.environ.get('TAVILY_API_KEY_1')
    key2 = os.environ.get('TAVILY_API_KEY_2')
    if key1:
        keys.append(key1)
    if key2:
        keys.append(key2)
    return keys if keys else None


def _get_tavily_client():
    """Try each key until one works."""
    from tavily import TavilyClient
    keys = _get_tavily_keys()
    if not keys:
        return None
    for key in keys:
        try:
            client = TavilyClient(api_key=key)
            client.search("test", max_results=1)
            return client
        except Exception:
            continue
    return None


def _call_llm(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Call MiniMax via Anthropic-compatible SDK (routes to MiniMax internally)."""
    import anthropic

    client = anthropic.Anthropic()

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                system=system,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            # Extract text from response blocks
            for block in response.content:
                if block.type == "text" and getattr(block, "text", None):
                    return block.text
            # Fallback: return thinking content if no text block
            for block in response.content:
                if block.type == "thinking" and getattr(block, "thinking", None):
                    return block.thinking[:500]
            return "[No response content]"
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return f"[Error: {e}]"


class ResearchAgent:
    def __init__(self):
        self.user_topics = get_user_topics()
        self._tavily = None

    @property
    def tavily(self):
        if self._tavily is None:
            self._tavily = _get_tavily_client()
        return self._tavily

    def answer(self, question: str) -> tuple[str, bool]:
        """
        Returns (answer_text, was_logged).
        Optionally searches the web first for current topics, then asks MiniMax.
        """
        log, reason = should_log(question)
        if not log:
            return self._answer_without_logging(question), False

        # Web search for time-sensitive / evolving topics
        web_results = None
        if self._should_search_web(question):
            web_results = self._search_web(question)

        # Generate answer via MiniMax, enriched with web context if available
        answer = self._generate_answer(question, web_results)
        confidence = estimate_confidence(answer)
        topic_name, _ = extract_primary_topic(question, answer, self.user_topics)
        tags = extract_tags(question, answer)
        sources = self._extract_sources_from_web(web_results)
        topic_id = get_or_create_topic(topic_name)

        # Log to DB
        add_qa_entry(
            question=question,
            answer=answer,
            topic_name=topic_name,
            topic_id=topic_id,
            tags=tags,
            confidence_level=confidence,
            sources=sources,
        )

        update_user_knowledge(topic_name, proficiency=min(confidence, 4))
        self.user_topics = get_user_topics()

        return answer, True

    def _should_search_web(self, question: str) -> bool:
        """Decide whether to search the web for current info."""
        q = question.lower()
        if VERSION_PATTERN.search(question):
            return True
        return any(trigger in q for trigger in WEB_SEARCH_TRIGGERS)

    def _search_web(self, query: str) -> list[dict]:
        """Search the web using Tavily and return results."""
        if not self.tavily:
            return []
        try:
            results = self.tavily.search(query=query, max_results=5)
            return results.get("results", [])
        except Exception:
            return []

    def _generate_answer(self, question: str, web_results: list = None) -> str:
        """Call MiniMax API, optionally enriched with web search context."""
        user_context = self._build_user_context()

        extra_context = ""
        search_note = ""
        if web_results:
            extra_context = self._build_web_context(web_results)
            search_note = "\n\n[Note: I searched the web for the most up-to-date information on this topic.]"

        system = f"""You are a patient, knowledgeable tutor for a curious teacher with no coding experience.

{user_context}

CONVERSATION STYLE:
- Use simple, jargon-free language unless they use technical terms
- Break complex topics step by step
- Use everyday analogies when helpful
- Be encouraging{extra_context}{search_note}"""

        return _call_llm(question, system=system, max_tokens=1024)

    def _build_web_context(self, results: list) -> str:
        """Build a web search context string from Tavily results."""
        if not results:
            return ""
        lines = ["\n\nWEB SEARCH RESULTS (up-to-date information from the web):"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            url = r.get("url", "")
            snippet = r.get("content", "")[:300]
            lines.append(f"[{i}] {title} — {url}")
            lines.append(f"    {snippet}")
        return "\n".join(lines)

    def _extract_sources_from_web(self, results: list) -> str:
        """Extract source URLs from web results for logging."""
        if not results:
            return ""
        urls = [r.get("url", "") for r in results if r.get("url")]
        return ",".join(urls)

    def _build_user_context(self) -> str:
        if not self.user_topics:
            return "They haven't learned any topics yet — this appears to be a new area."

        lines = ["They have explored these topics:"]
        for t in self.user_topics[:10]:
            lvl = t.get("proficiency_level", 1)
            lvl_words = {1: "just heard of it", 2: "understands basics", 3: "can apply it", 4: "can teach it"}
            lines.append(f"  - {t['topic_name']}: {lvl_words.get(lvl, 'unknown')}")
        return "\n".join(lines)

    def _answer_without_logging(self, question: str) -> str:
        """Answer casual/meta questions without logging."""
        q = question.strip().lower()
        if any(q.startswith(w) for w in ["hi", "hello", "hey"]):
            return "Hello! What would you like to learn about today?"
        if any(w in q for w in ["how are you", "what's up", "how do you feel"]):
            return "I'm doing great, thanks for asking! Ready to help you learn something new. What question do you have?"
        if any(w in q for w in ["thanks", "thank you"]):
            return "You're welcome! Feel free to ask if you have more questions."
        if any(w in q for w in ["bye", "goodbye"]):
            return "Goodbye! Keep learning and feel free to come back anytime."
        return self._generate_answer(question)

    def check_and_flag_stale_entries(self) -> list:
        """Check all entries for staleness and flag them."""
        entries = get_all_qa_entries()
        flagged = []
        for entry in entries:
            stale, reason = get_staleness(entry)
            if stale:
                from db.queries import add_outdated_flag, mark_entry_outdated
                add_outdated_flag(entry["id"], reason)
                mark_entry_outdated(entry["id"], reason)
                flagged.append(entry)
        return flagged
