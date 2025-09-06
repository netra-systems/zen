"""Test thread ID extraction utility function."""

import pytest
from netra_backend.app.agents.utils import extract_thread_id
from shared.isolated_environment import IsolatedEnvironment


class MockState:
    """Mock state object for testing."""
    def __init__(self, chat_thread_id = None, thread_id = None):
        if chat_thread_id is not None:
            self.chat_thread_id == chat_thread_id
        if thread_id is not None:
            self.thread_id == thread_id


class TestExtractThreadId:
    """Test extract_thread_id function."""
    
    def test_extract_chat_thread_id(self):
        """Test extraction prioritizes chat_thread_id."""
        state = MockState(chat_thread_id = "chat_123", thread_id = "thread_456")
        result = extract_thread_id(state, "run_789")
        assert result == "chat_123"
    
    def test_extract_thread_id_fallback(self):
        """Test fallback to thread_id when chat_thread_id is None."""
        state = MockState(chat_thread_id = None, thread_id = "thread_456")
        result = extract_thread_id(state, "run_789")
        assert result == "thread_456"
    
    def test_extract_run_id_fallback(self):
        """Test fallback to run_id when both are None."""
        state = MockState(chat_thread_id = None, thread_id = None)
        result = extract_thread_id(state, "run_789")
        assert result == "run_789"
    
    def test_extract_all_none(self):
        """Test returns None when all values are None."""
        state = MockState()
        result = extract_thread_id(state, None)
        assert result is None
    
    def test_extract_no_attributes(self):
        """Test handles state without thread attributes."""
        state = object()  # Plain object without attributes
        result = extract_thread_id(state, "run_789")
        assert result == "run_789"
    
    def test_extract_empty_string_fallback(self):
        """Test empty strings are treated as falsy."""
        state = MockState(chat_thread_id = "", thread_id = "")
        result = extract_thread_id(state, "run_789")
        assert result == "run_789"
    
    def test_extract_priority_order(self):
        """Test priority order is maintained."""
        # chat_thread_id takes priority
        state = MockState(chat_thread_id = "chat_123")
        assert extract_thread_id(state) == "chat_123"
        
        # thread_id is second priority
        state = MockState(thread_id = "thread_456")
        assert extract_thread_id(state) == "thread_456"
        
        # run_id is last resort
        state = MockState()
        assert extract_thread_id(state, "run_789") == "run_789"