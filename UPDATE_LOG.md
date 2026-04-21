# Update Log

## 2025-04-22 - Major Refactoring & UI Improvements

### Phase 1: Security & Configuration
- **Created `config.py`** — Centralized configuration for MiniMax API, Tavily keys, and Flask settings
- **Fixed API credentials** — Research agents (`research_agent.py`, `research_coordinator.py`, `topic_detector.py`) now properly use MiniMax credentials instead of default Anthropic client
- **Model consistency** — All agents now use `MiniMax-M2.7-highspeed` via `config.MINIMAX_MODEL`
- **Security note** — `.env` should remain untracked (already in `.gitignore`)

### Phase 2: Code Deduplication & Shared Services
- **Created `services/llm_client.py`** — Unified LLM client with:
  - `call_llm()` — Configurable prompt, system message, max_tokens, streaming
  - `extract_text_from_response()` — Safe text extraction from response blocks
  - Retry logic with exponential backoff (3 attempts)
- **Created `services/tavily_client.py`** — Unified Tavily client with:
  - `get_tavily_client()` — Key rotation with lazy initialization and test query
  - `reset_tavily_client()` — For testing
- **Removed ~240 lines of duplicated code** across `app.py`, `research_agent.py`, `research_coordinator.py`, `topic_detector.py`
- **Populated `services/__init__.py`** — Public exports for clean imports

### Phase 3: Database Architecture
- **Created `db/connection.py`** — Context manager `get_db()` with:
  - Auto-commit on success
  - Rollback on exception
  - Guaranteed connection cleanup
- **Updated `db/queries.py`** — All 25+ functions now use `with get_db()` pattern
- **Schema normalization**:
  - Removed redundant `topic_name` columns from `qa_entries` and `user_knowledge`
  - Queries now JOIN with `topics` table to fetch names
  - Created `qa_entry_sources` junction table (replaces comma-separated strings)
- **Added database indexes**:
  - `idx_qa_topic_id_created` on `qa_entries(topic_id, created_at)`
  - `idx_qa_created_at` on `qa_entries(created_at)`
  - `idx_tags_name` on `tags(name)`
- **Removed dead code**: `learning_db.py`, `prompts.py`
- **Populated `db/__init__.py` and `agents/__init__.py`** — Clean public APIs

### Phase 4: Testing & Logging
- **Added dependencies**: `pytest`, `pytest-mock`, `anthropic` to `requirements.txt`
- **Created test infrastructure**:
  - `pytest.ini` — Test configuration
  - `tests/conftest.py` — Fixtures for temp DB, mocked LLM, mocked Tavily
  - `tests/test_db_queries.py` — Tests for topics, Q&A entries, user knowledge, tags
  - `tests/test_topic_detector.py` — Tests for topic extraction with mocked LLM
  - `tests/test_auto_log.py` — Tests for logging decisions and confidence estimation
- **Created `services/logging_config.py`** — Structured logging setup
- **Replaced `print()` with proper logging** in core modules

### UI Improvements
- **Removed Claude Haiku** from model selector (only MiniMax M2.7 available)
- **Fixed typing indicators** with breathing animation:
  - Mode-specific colored borders: Quicky (blue), Search (teal), Deep (purple)
  - Mode-specific text: "Thinking", "Searching", "Researching"
  - Typing indicator now persists until first token arrives (no empty bubble flash)
- **Activities moved to tool log** — Research steps and search activities appear in Activity panel instead of inline in messages
- **Added source links** for web search mode — Shows "Sources" section with clickable domain links below search results
- **Topic selector enhancement**:
  - Clicking a topic filters History sidebar to show only related sessions
  - Shows "History — Topic Name" with Clear button
  - Clicking Q&A entries creates and loads a full session with question+answer
  - Clicking topic again collapses and clears filter
- **Research progress indicator** — Pulsing dot (●) appears next to active research sessions in History sidebar

### Bug Fixes
- **Fixed schema migration** — `migrate_schema()` now checks if tables exist before adding indexes (prevents errors on fresh DB)
- **Fixed citation links in research mode** — Regex now properly converts `[1]`, `[2]` to clickable links without re-linking already-linked citations
- **Fixed `how many` queries not logging** — Added `how many|how much|how long|how far|how old` to `LOG_PATTERNS`
- **Fixed bubble continuity** — Assistant message bubble is created on first token instead of immediately, preventing empty bubble flash

### Data Migration
- Database must be rebuilt due to schema changes:
  ```bash
  rm learning.db
  python run.py --init-db
  ```

## Current Status
- ✅ All 4 phases complete
- ✅ Server running at http://127.0.0.1:5001
- ✅ 8 commits ahead of origin/master
