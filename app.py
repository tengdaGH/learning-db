"""
Flask web UI for Personal Learning Database.
"""
import os
import re
import time
import json
import logging
from flask import Flask, render_template, request, Response, stream_with_context
from dotenv import load_dotenv

load_dotenv(override=True)

import config

logger = logging.getLogger(__name__)

from db.queries import (
    get_all_topics,
    get_all_topics_with_counts,
    get_user_knowledge,
    get_recent_qa_entries,
    add_qa_entry,
    get_or_create_topic,
    update_user_knowledge,
    get_qa_entries_by_topic_id,
    get_new_entries_today,
    set_tags_for_entry,
)
from agents.tag_manager import tag_entry
from services.auto_log import should_log, estimate_confidence
from services.topic_detector import extract_primary_topic, extract_tags
from services.llm_client import call_llm
from services.tavily_client import get_tavily_client


def link_citations_in_markdown(text: str, sources: list) -> str:
    """Convert [N] citation markers to proper markdown links using source URLs."""
    if not sources:
        return text

    # Build citation number -> url mapping
    citation_map = {}
    for i, url in enumerate(sources, 1):
        citation_map[str(i)] = url

    def replace_citation(match):
        num = match.group(1)
        if num in citation_map:
            url = citation_map[num]
            return f'[{num}]({url})'
        return match.group(0)

    # Replace [N] citation markers in the body (not in URLs or the Sources header line)
    # Only replace [N] that appear outside of URLs and outside of the Sources section definition
    lines = text.split('\n')
    in_sources_section = False
    result_lines = []

    for line in lines:
        if re.match(r'^##?\s*Sources', line, re.IGNORECASE):
            in_sources_section = True
            result_lines.append(line)
            continue

        if in_sources_section:
            # In Sources section, convert numbered list items to markdown links
            # Format might be: [1] https://url or 1. https://url or - https://url
            numbered_link = re.sub(r'\[(\d+)\]\s+(https?://\S+)', r'[\1](\2)', line)
            result_lines.append(numbered_link)
        else:
            # Outside Sources section, replace [N] with [N](url) if we have that citation
            # Be careful not to replace [N] inside URLs or already-linked markdown
            # Replace [N] followed by whitespace or end of line (not part of a URL)
            replaced = re.sub(r'\[(\d+)\](?=\s|$|(?=[^[]*\]))', replace_citation, line)
            result_lines.append(replaced)

    return '\n'.join(result_lines)


app = Flask(__name__, static_folder="web/static", template_folder="web/templates")

# Topics that warrant web search
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


def _should_search_web(question: str) -> bool:
    """Decide whether to search the web for current info."""
    q = question.lower()
    if re.search(r"gpt-\d|claude-?\d|react-?\d+|vue-?\d+|angular-?\d+|python\s+v?3\.\d+|typescript\s+v?\d|version\s+\d", question, re.IGNORECASE):
        return True
    return any(trigger in q for trigger in WEB_SEARCH_TRIGGERS)


def _search_web(query: str, tavily_client) -> list:
    """Search the web using Tavily and return results."""
    if not tavily_client:
        return []
    try:
        results = tavily_client.search(query=query, max_results=5)
        return results.get("results", [])
    except Exception:
        return []


def _build_web_context(results: list) -> str:
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


def _build_user_context(user_topics: list) -> str:
    if not user_topics:
        return "They haven't learned any topics yet — this appears to be a new area."

    lines = ["They have explored these topics:"]
    for t in user_topics[:10]:
        lvl = t.get("proficiency_level", 1)
        lvl_words = {1: "just heard of it", 2: "understands basics", 3: "can apply it", 4: "can teach it"}
        lines.append(f"  - {t['topic_name']}: {lvl_words.get(lvl, 'unknown')}")
    return "\n".join(lines)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Render the main UI."""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """
    Receive a message, stream SSE response.
    Form data: message, model (optional, defaults to MiniMax)
    """
    message = request.form.get("message", "").strip()
    model = request.form.get("model", config.MINIMAX_MODEL)

    if not message:
        return {"error": "No message provided"}, 400

    # Get user topics for context
    from db.queries import get_user_topics
    user_topics = get_user_topics()

    # Build system prompt
    user_context = _build_user_context(user_topics)
    system = f"""You are a patient, knowledgeable tutor for a curious teacher with no coding experience.

{user_context}

CONVERSATION STYLE:
- Use simple, jargon-free language unless they use technical terms
- Break complex topics step by step
- Use everyday analogies when helpful
- Be encouraging"""

    # Check if we should do web search
    tavily_client = None
    web_results = None
    if _should_search_web(message):
        tavily_client = get_tavily_client()
        if tavily_client:
            web_results = _search_web(message, tavily_client)
            if web_results:
                extra_context = _build_web_context(web_results)
                system = f"""You are a patient, knowledgeable tutor for a curious teacher with no coding experience.

{user_context}

CONVERSATION STYLE:
- Use simple, jargon-free language unless they use technical terms
- Break complex topics step by step
- Use everyday analogies when helpful
- Be encouraging{extra_context}

[Note: I searched the web for the most up-to-date information on this topic.]"""

    # Call LLM with streaming
    llm_stream = call_llm(message, system=system, max_tokens=1024, stream=True)

    def generate():
        full_response = ""

        # Send model info event
        yield f"event: model\ndata: {model}\n\n"

        # Handle Anthropic SDK streaming events
        for event in llm_stream:
            # content_block_delta events have the streaming text
            if hasattr(event, 'type') and event.type == 'content_block_delta':
                if hasattr(event, 'delta') and hasattr(event.delta, 'text') and event.delta.text:
                    token = event.delta.text
                    full_response += token
                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

        # Determine if we should log
        log, _ = should_log(message)
        was_logged = False

        if log and full_response:
            try:
                confidence = estimate_confidence(full_response)
                topic_name, _ = extract_primary_topic(message, full_response, user_topics)
                tags = extract_tags(message, full_response)
                sources = [r.get("url", "") for r in web_results] if web_results else []
                topic_id = get_or_create_topic(topic_name)

                entry_id = add_qa_entry(
                    question=message,
                    answer=full_response,
                    topic_id=topic_id,
                    tags=tags,
                    confidence_level=confidence,
                    sources=sources,
                )
                # Auto-tag the entry
                tag_entry(entry_id, message, full_response)
                update_user_knowledge(topic_id, proficiency=min(confidence, 4))
                was_logged = True
            except Exception as e:
                logger.error(f"Error logging to DB: {e}")

        yield f"event: done\ndata: {json.dumps({'was_logged': was_logged})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/chat/deep", methods=["POST"])
def chat_deep():
    """
    Deep research mode — uses ResearchCoordinator for comprehensive answers.
    Receives message, streams SSE response.
    """
    message = request.form.get("message", "").strip()
    model = request.form.get("model", config.MINIMAX_MODEL)

    if not message:
        return {"error": "No message provided"}, 400

    from agents.research_coordinator import ResearchCoordinator

    def generate():
        full_response = ""
        research_sources = []

        yield f"event: mode\ndata: deep\n\n"

        try:
            coordinator = ResearchCoordinator()

            for event_type, data in coordinator.deep_research_stream(message):
                if event_type == 'tool':
                    yield f"event: tool\ndata: {json.dumps({'tool': data})}\n\n"
                elif event_type == 'done':
                    research_sources = data.get('sources', [])
                    full_response = data.get('answer', '')
                    was_logged = data.get('was_logged', False)

                    # Link citations in markdown
                    full_response = link_citations_in_markdown(full_response, research_sources)

                    # Stream the final answer with small chunks
                    chunk_size = 20
                    for i in range(0, len(full_response), chunk_size):
                        chunk = full_response[i:i+chunk_size]
                        yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
                        time.sleep(0.01)

        except Exception as e:
            error_msg = f"Deep research error: {str(e)}"
            yield f"event: token\ndata: {json.dumps({'token': error_msg})}\n\n"
            full_response = error_msg

        yield f"event: done\ndata: {json.dumps({'was_logged': was_logged, 'sources_count': len(research_sources)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/chat/web", methods=["POST"])
def chat_web():
    """
    Single agent mode — uses Tavily web search for comprehensive answers.
    """
    message = request.form.get("message", "").strip()
    model = request.form.get("model", config.MINIMAX_MODEL)

    if not message:
        return {"error": "No message provided"}, 400

    from db.queries import get_user_topics
    user_topics = get_user_topics()

    # Always do Tavily search for web mode
    tavily_client = get_tavily_client()
    web_results = None
    extra_context = ""

    def generate():
        nonlocal tavily_client, web_results, extra_context

        full_response = ""
        sources = []

        yield f"event: mode\ndata: web\n\n"
        yield f"event: model\ndata: {model}\n\n"

        # Emit search tool event
        tool_data = json.dumps({'tool': {'type': 'search', 'message': 'Searching the web for relevant information...'}})
        yield f"event: tool\ndata: {tool_data}\n\n"

        if tavily_client:
            web_results = _search_web(message, tavily_client)
            if web_results:
                result_count = len(web_results)
                tool_data = json.dumps({'tool': {'type': 'search', 'message': f'Found {result_count} web results'}})
                yield f"event: tool\ndata: {tool_data}\n\n"
                extra_context = _build_web_context(web_results)
            else:
                tool_data = json.dumps({'tool': {'type': 'search', 'message': 'No web results found'}})
                yield f"event: tool\ndata: {tool_data}\n\n"

        tool_data = json.dumps({'tool': {'type': 'thinking', 'message': 'Generating answer with web context...'}})
        yield f"event: tool\ndata: {tool_data}\n\n"

        user_context = _build_user_context(user_topics)
        system = f"""You are a patient, knowledgeable tutor for a curious teacher with no coding experience.

{user_context}

CONVERSATION STYLE:
- Use simple, jargon-free language unless they use technical terms
- Break complex topics step by step
- Use everyday analogies when helpful
- Be encouraging{extra_context}

[Note: I searched the web for the most up-to-date information on this topic.]"""

        llm_stream = call_llm(message, system=system, max_tokens=1024, stream=True)

        for event in llm_stream:
            if hasattr(event, 'type') and event.type == 'content_block_delta':
                if hasattr(event, 'delta') and hasattr(event.delta, 'text') and event.delta.text:
                    token = event.delta.text
                    full_response += token
                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

        # Collect sources
        if web_results:
            sources = [r.get("url", "") for r in web_results if r.get("url")]

        # Link citations in markdown
        full_response = link_citations_in_markdown(full_response, sources)

        # Log if appropriate
        log, _ = should_log(message)
        was_logged = False

        if log and full_response:
            try:
                confidence = estimate_confidence(full_response)
                topic_name, _ = extract_primary_topic(message, full_response, user_topics)
                tags = extract_tags(message, full_response)
                topic_id = get_or_create_topic(topic_name)

                entry_id = add_qa_entry(
                    question=message,
                    answer=full_response,
                    topic_id=topic_id,
                    tags=tags,
                    confidence_level=confidence,
                    sources=sources,
                )
                # Auto-tag the entry
                tag_entry(entry_id, message, full_response)
                update_user_knowledge(topic_id, proficiency=min(confidence, 4))
                was_logged = True
            except Exception as e:
                logger.error(f"Error logging to DB: {e}")

        tool_data = json.dumps({'tool': {'type': 'complete', 'message': 'Answer complete'}})
        yield f"event: tool\ndata: {tool_data}\n\n"
        yield f"event: done\ndata: {json.dumps({'was_logged': was_logged, 'sources_count': len(sources)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/topics", methods=["GET"])
def api_topics():
    """Return all topics as JSON."""
    topics = get_all_topics_with_counts()
    return {"topics": topics}


@app.route("/api/topics/<int:topic_id>/entries", methods=["GET"])
def api_topic_entries(topic_id):
    """Return Q&A entries for a specific topic as JSON."""
    entries = get_qa_entries_by_topic_id(topic_id)
    return {"entries": entries}


@app.route("/api/knowledge", methods=["GET"])
def api_knowledge():
    """Return user knowledge stats as JSON."""
    knowledge = get_user_knowledge()
    total = len(knowledge)
    proficiency_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for k in knowledge:
        lvl = k.get("proficiency_level", 1)
        if lvl in proficiency_counts:
            proficiency_counts[lvl] += 1

    return {
        "total_topics": total,
        "proficiency_levels": proficiency_counts,
        "topics": knowledge,
    }


@app.route("/api/recent", methods=["GET"])
def api_recent():
    """Return recent Q&A entries as JSON."""
    entries = get_recent_qa_entries(limit=20)
    return {"entries": entries}


@app.route("/api/stats/today", methods=["GET"])
def api_stats_today():
    """Return count of new entries learned today."""
    count = get_new_entries_today()
    return {"count": count}


@app.route("/api/review", methods=["POST"])
def api_review():
    """Trigger review agent, return digest."""
    from agents.review_agent import run_review
    digest = run_review()
    return {"digest": digest}


@app.route("/api/tags", methods=["GET"])
def api_tags():
    """Return all tags with entry counts."""
    from db.queries import get_all_tags
    tags = get_all_tags()
    return {"tags": tags}


@app.route("/api/tags/cleanup", methods=["POST"])
def api_tags_cleanup():
    """Run tag maintenance: remove orphans and merge similar tags."""
    from agents.tag_manager import cleanup_tags
    report = cleanup_tags()
    return {"report": report}


if __name__ == "__main__":
    from db.schema import migrate_schema
    migrate_schema()
    app.run(debug=True, port=5001)