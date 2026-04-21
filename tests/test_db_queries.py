"""
Tests for database query operations.
"""
import pytest
from db.queries import (
    get_or_create_topic,
    add_qa_entry,
    get_qa_entry,
    get_all_qa_entries,
    update_user_knowledge,
    get_user_knowledge,
    get_user_topics,
    get_or_create_tag,
    set_tags_for_entry,
    get_tags_for_entry,
)


class TestTopics:
    def test_get_or_create_topic_creates_new(self, temp_db):
        topic_id = get_or_create_topic("Python")
        assert topic_id is not None
        assert isinstance(topic_id, int)

    def test_get_or_create_topic_returns_existing(self, temp_db):
        topic_id1 = get_or_create_topic("Python")
        topic_id2 = get_or_create_topic("Python")
        assert topic_id1 == topic_id2


class TestQAEntries:
    def test_add_qa_entry_basic(self, temp_db):
        topic_id = get_or_create_topic("Python")
        entry_id = add_qa_entry(
            question="What is Python?",
            answer="A programming language",
            topic_id=topic_id,
        )
        assert entry_id is not None

    def test_add_qa_entry_with_sources(self, temp_db):
        topic_id = get_or_create_topic("Python")
        entry_id = add_qa_entry(
            question="What is Python?",
            answer="A programming language",
            topic_id=topic_id,
            sources=["https://python.org", "https://docs.python.org"],
        )
        
        entry = get_qa_entry(entry_id)
        assert entry is not None
        assert len(entry["sources"]) == 2
        assert "https://python.org" in entry["sources"]

    def test_get_all_qa_entries(self, temp_db):
        topic_id = get_or_create_topic("Python")
        add_qa_entry("Q1", "A1", topic_id=topic_id)
        add_qa_entry("Q2", "A2", topic_id=topic_id)
        
        entries = get_all_qa_entries()
        assert len(entries) == 2


class TestUserKnowledge:
    def test_update_user_knowledge_creates_new(self, temp_db):
        topic_id = get_or_create_topic("Python")
        update_user_knowledge(topic_id, proficiency=3)
        
        knowledge = get_user_knowledge()
        assert len(knowledge) == 1
        assert knowledge[0]["topic_id"] == topic_id
        assert knowledge[0]["proficiency_level"] == 3

    def test_update_user_knowledge_increments_count(self, temp_db):
        topic_id = get_or_create_topic("Python")
        update_user_knowledge(topic_id, proficiency=2)
        update_user_knowledge(topic_id, proficiency=3)
        
        knowledge = get_user_knowledge()
        assert knowledge[0]["mention_count"] == 2
        assert knowledge[0]["proficiency_level"] == 3

    def test_get_user_topics(self, temp_db):
        topic_id = get_or_create_topic("Python")
        update_user_knowledge(topic_id)
        
        topics = get_user_topics()
        assert len(topics) == 1
        assert topics[0]["topic_name"] == "Python"


class TestTags:
    def test_get_or_create_tag(self, temp_db):
        tag_id = get_or_create_tag("python")
        assert tag_id is not None
        
        # Should return same ID
        tag_id2 = get_or_create_tag("python")
        assert tag_id == tag_id2

    def test_set_and_get_tags_for_entry(self, temp_db):
        topic_id = get_or_create_topic("Python")
        entry_id = add_qa_entry("Q1", "A1", topic_id=topic_id)
        
        set_tags_for_entry(entry_id, ["python", "programming"])
        tags = get_tags_for_entry(entry_id)
        
        tag_names = [t["name"] for t in tags]
        assert "python" in tag_names
        assert "programming" in tag_names
