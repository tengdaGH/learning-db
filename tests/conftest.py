"""
Pytest fixtures for Personal Learning Database tests.
"""
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_db_path():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def temp_db(temp_db_path):
    """Create an in-memory database with full schema for testing."""
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    
    # Create schema
    conn.executescript("""
        CREATE TABLE topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_evolving INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE qa_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
            tags TEXT,
            confidence_level INTEGER DEFAULT 3,
            is_outdated INTEGER DEFAULT 0,
            outdated_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_reviewed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE qa_entry_sources (
            qa_entry_id INTEGER REFERENCES qa_entries(id) ON DELETE CASCADE,
            source_url TEXT NOT NULL,
            PRIMARY KEY (qa_entry_id, source_url)
        );
        
        CREATE TABLE user_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
            proficiency_level INTEGER DEFAULT 1,
            last_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mention_count INTEGER DEFAULT 1
        );
        
        CREATE TABLE outdated_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qa_entry_id INTEGER REFERENCES qa_entries(id) ON DELETE CASCADE,
            flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            resolved_at TIMESTAMP
        );
        
        CREATE TABLE review_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start DATE NOT NULL,
            new_entries INTEGER DEFAULT 0,
            topics_covered INTEGER DEFAULT 0,
            outdated_flagged INTEGER DEFAULT 0,
            digest TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE qa_entry_tags (
            qa_entry_id INTEGER REFERENCES qa_entries(id) ON DELETE CASCADE,
            tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (qa_entry_id, tag_id)
        );
    """)
    
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mock_llm(mocker):
    """Mock call_llm to return predictable responses."""
    return mocker.patch(
        "services.llm_client.call_llm",
        return_value=type("obj", (object,), {
            "content": [type("obj", (object,), {"type": "text", "text": "Test response"})]
        })()
    )


@pytest.fixture
def mock_tavily(mocker):
    """Mock TavilyClient.search."""
    mock_client = mocker.MagicMock()
    mock_client.search.return_value = {"results": []}
    return mocker.patch("services.tavily_client.TavilyClient", return_value=mock_client)
