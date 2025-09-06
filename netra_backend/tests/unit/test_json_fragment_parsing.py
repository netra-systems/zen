import json
"""Test JSON fragment parsing improvements."""

import pytest
from netra_backend.app.core.serialization.unified_json_handler import llm_parser
from shared.isolated_environment import IsolatedEnvironment


class TestJSONFragmentParsing:
    """Test handling of JSON fragments."""
    
    def test_detects_json_fragments(self):
        """Test detection of JSON fragments."""
        # These are the exact fragments from the error logs
        fragment1 = '"model_name": "chatbot"'
        fragment2 = '"target_metric": "response_time", "constraint": "cost"'
        
        assert llm_parser._is_json_fragment(fragment1) is True
        assert llm_parser._is_json_fragment(fragment2) is True
        
        # Valid JSON should not be detected as fragment
        valid_json = '{"model_name": "chatbot"}'
        assert llm_parser._is_json_fragment(valid_json) is False
        
        # Plain text should not be detected as fragment
        plain_text = "just some text"
        assert llm_parser._is_json_fragment(plain_text) is False
    
    def test_handles_json_fragments_gracefully(self):
        """Test that JSON fragments are handled without warnings."""
        # Single key-value pair fragment
        fragment1 = '"model_name": "chatbot"'
        result1 = llm_parser.safe_json_parse(fragment1, fallback = {})
        assert result1 == {"model_name": "chatbot"}
        
        # Multiple key-value pairs fragment
        fragment2 = '"target_metric": "response_time", "constraint": "cost"'
        result2 = llm_parser.safe_json_parse(fragment2, fallback = {})
        assert result2 == {"target_metric": "response_time", "constraint": "cost"}
    
    def test_json_fragment_wrapping(self):
        """Test the JSON fragment wrapping functionality."""
        # Single key-value pair
        fragment1 = '"model_name": "chatbot"'
        result1 = llm_parser._handle_json_fragment(fragment1, fallback = {})
        assert result1 == {"model_name": "chatbot"}
        
        # Multiple key-value pairs
        fragment2 = '"target_metric": "response_time", "constraint": "cost"'
        result2 = llm_parser._handle_json_fragment(fragment2, fallback = {})
        assert result2 == {"target_metric": "response_time", "constraint": "cost"}
        
        # Invalid fragment that can't be wrapped'
        invalid = '"incomplete": '
        result3 = llm_parser._handle_json_fragment(invalid, fallback = {"default": True})
        assert result3 == {"default": True}
    
    def test_preserves_valid_json(self):
        """Test that valid JSON is still parsed correctly."""
        valid_json = '{"model_name": "chatbot", "version": 1}'
        result = llm_parser.safe_json_parse(valid_json)
        assert result == {"model_name": "chatbot", "version": 1}
        
        valid_array = '["item1", "item2"]'
        result = llm_parser.safe_json_parse(valid_array)
        assert result == ["item1", "item2"]
    
    def test_fallback_behavior(self):
        """Test fallback behavior for unparseable strings."""
        # Completely invalid JSON
        invalid = "not json at all"
        result = llm_parser.safe_json_parse(invalid, fallback = {"error": "invalid"})
        assert result == {"error": "invalid"}
        
        # Empty string with explicit None fallback returns empty string
        # (because fallback = None means "use default behavior")
        empty = ""
        result = llm_parser.safe_json_parse(empty, fallback = None)
        assert result == ""
        
        # Empty string with dict(fallback)
        empty = ""
        result = llm_parser.safe_json_parse(empty, fallback = {})
        assert result == {}