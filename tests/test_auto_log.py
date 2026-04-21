"""
Tests for auto-logging decision logic.
"""
import pytest
from services.auto_log import should_log, estimate_confidence


class TestShouldLog:
    def test_should_log_learning_question(self):
        log, reason = should_log("What is machine learning?")
        assert log is True

    def test_should_not_log_greeting(self):
        log, reason = should_log("Hello!")
        assert log is False

    def test_should_not_log_thanks(self):
        log, reason = should_log("Thank you")
        assert log is False


class TestEstimateConfidence:
    def test_high_confidence_answer(self):
        answer = """
        Machine learning is a subset of artificial intelligence that enables systems 
        to learn and improve from experience. There are three main types: supervised 
        learning, unsupervised learning, and reinforcement learning.
        """
        confidence = estimate_confidence(answer)
        assert confidence >= 3

    def test_low_confidence_short_answer(self):
        answer = "I don't know."
        confidence = estimate_confidence(answer)
        assert confidence <= 2
