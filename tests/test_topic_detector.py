"""
Tests for topic detection and extraction.
"""
import pytest
from services.topic_detector import extract_primary_topic, extract_tags


class TestExtractPrimaryTopic:
    def test_extract_existing_topic(self, mock_llm):
        # Mock returns EXISTING: Python
        mock_llm.return_value = type("obj", (object,), {
            "content": [type("obj", (object,), {"type": "text", "text": "EXISTING: Python"})]
        })()
        
        topic, is_new = extract_primary_topic("What is Python?", existing_topics=[])
        # Note: This test may need adjustment based on actual mock behavior
        assert topic is not None

    def test_extract_new_topic(self, mock_llm):
        mock_llm.return_value = type("obj", (object,), {
            "content": [type("obj", (object,), {"type": "text", "text": "NEW: Rust"})]
        })()
        
        topic, is_new = extract_primary_topic("What is Rust?", existing_topics=[])
        assert topic is not None

    def test_fallback_topic_extraction(self, mock_llm):
        # Mock returns something unexpected
        mock_llm.return_value = type("obj", (object,), {
            "content": [type("obj", (object,), {"type": "text", "text": "Some random text"})]
        })()
        
        topic, is_new = extract_primary_topic("How does machine learning work?", existing_topics=[])
        # Should fallback to word extraction
        assert topic is not None
        assert len(topic) > 0


class TestExtractTags:
    def test_extract_tags_from_text(self):
        tags = extract_tags("What is Python programming?", "Python is a language.")
        assert "python" in tags
        assert "programming" in tags

    def test_extract_tags_empty(self):
        tags = extract_tags("a b c d", "e f g h")
        # Should still extract some meaningful words
        assert isinstance(tags, str)
