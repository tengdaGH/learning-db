# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal Learning Database — an AI-powered learning assistant that logs Q&A pairs to SQLite, tracks knowledge/proficiency per topic, detects stale content, and generates weekly learning digests. Built with Flask (web UI) and a CLI interface.

## Commands

```bash
python run.py --init-db    # Initialize database schema
python app.py              # Start Flask web server (http://localhost:5000)
python run.py chat         # Start CLI chat interface
python run.py review        # Run weekly review
```

## Architecture

**Entry Points**: `app.py` (Flask), `run.py` (CLI)

**Key Layers**:
- `agents/` — AI agents: `research_agent.py` (answers questions, searches web), `learning_assistant.py` (suggests topics, finds gaps), `review_agent.py` (weekly review)
- `services/` — Business logic: `auto_log.py` (decides when to log Q&A), `topic_detector.py`, `staleness_detector.py`, `digest_generator.py`
- `db/` — `schema.py` (tables), `queries.py` (CRUD operations)
- `cli/` — `chat.py` (interactive CLI with commands: `/help`, `/gaps`, `/suggest`, `/next`, `/digest`, `/topics`, `/quit`)

**Database**: SQLite at `learning.db` (auto-created on init)

**AI Models**: Uses MiniMax's Anthropic-compatible API endpoint. Primary model: `MiniMax-M2.7-highspeed`. Alternate: `claude-haiku-4-5-20251001`. Web search via Tavily API.

**API**: Flask web UI provides SSE streaming `/chat` endpoint. Models called via `https://api.minimaxi.com/anthropic`.

## Database Schema

Core tables: `topics`, `qa_entries`, `user_knowledge`, `outdated_flags`, `review_summaries`. Legacy tables still present: `notes`, `flashcards`, `study_sessions`.

## Environment

Requires `.env` with `MINIMAX_API_KEY`, `MINIMAX_BASE_URL` (https://api.minimax.io/v1), `MINIMAX_MODEL`. Tavily API keys should be set as `TAVILY_API_KEY_1` and `TAVILY_API_KEY_2` environment variables.
