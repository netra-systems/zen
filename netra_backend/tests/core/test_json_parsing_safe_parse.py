"""
Tests for safe JSON parsing functionality.
All functions ≤8 lines per requirements.
"""

import pytest
import json
from netra_backend.app.core.json_parsing_utils import safe_json_parse

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class TestSafeJsonParse:
    """Test the safe_json_parse function."""
    
    def test_parse_valid_json_dict(self):
        """Test parsing valid JSON dict string."""
        json_str = '{"key": "value", "number": 42}'
        result = safe_json_parse(json_str)
        expected = {"key": "value", "number": 42}
        assert result == expected
    
    def test_parse_valid_json_list(self):
        """Test parsing valid JSON list string."""
        json_str = '[1, 2, 3, "test"]'
        result = safe_json_parse(json_str)
        expected = [1, 2, 3, "test"]
        assert result == expected
    
    def test_parse_valid_json_string(self):
        """Test parsing valid JSON string value."""
        json_str = '"simple string"'
        result = safe_json_parse(json_str)
        assert result == "simple string"
    
    def test_parse_valid_json_number(self):
        """Test parsing valid JSON number."""
        json_str = '123.45'
        result = safe_json_parse(json_str)
        assert result == 123.45
    
    def test_parse_valid_json_boolean(self):
        """Test parsing valid JSON boolean."""
        json_str = 'true'
        result = safe_json_parse(json_str)
        assert result is True
    
    def test_parse_valid_json_null(self):
        """Test parsing valid JSON null."""
        json_str = 'null'
        result = safe_json_parse(json_str)
        assert result is None
    
    def test_parse_invalid_json_returns_original(self):
        """Test that invalid JSON returns original string."""
        json_str = 'invalid json'
        result = safe_json_parse(json_str)
        assert result == json_str
    
    def test_parse_empty_string(self):
        """Test parsing empty string."""
        json_str = ''
        result = safe_json_parse(json_str)
        assert result == ''
    
    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only string."""
        json_str = '   '
        result = safe_json_parse(json_str)
        assert result == '   '
    
    def test_parse_malformed_dict(self):
        """Test parsing malformed dict returns original."""
        json_str = '{"key": value}'  # Missing quotes around value
        result = safe_json_parse(json_str)
        assert result == json_str
    
    def test_parse_malformed_list(self):
        """Test parsing malformed list returns original."""
        json_str = '[1, 2, 3,]'  # Trailing comma
        result = safe_json_parse(json_str)
        assert result == json_str
    
    def test_parse_nested_valid_json(self):
        """Test parsing nested valid JSON."""
        json_str = '{"outer": {"inner": ["item1", "item2"]}, "count": 5}'
        result = safe_json_parse(json_str)
        expected = {"outer": {"inner": ["item1", "item2"]}, "count": 5}
        assert result == expected
    
    def test_parse_unicode_json(self):
        """Test parsing JSON with unicode characters."""
        json_str = '{"message": "Hello 世界", "emoji": "😀"}'
        result = safe_json_parse(json_str)
        expected = {"message": "Hello 世界", "emoji": "😀"}
        assert result == expected
    
    def test_parse_escaped_characters(self):
        """Test parsing JSON with escaped characters."""
        json_str = '{"path": "C:\\\\Users\\\\test", "quote": "He said \\"Hello\\""}'
        result = safe_json_parse(json_str)
        expected = {"path": "C:\\Users\\test", "quote": 'He said "Hello"'}
        assert result == expected
    
    def test_parse_already_parsed_object(self):
        """Test parsing already parsed object returns as-is."""
        json_obj = {"key": "value"}
        result = safe_json_parse(json_obj)
        assert result == json_obj
    
    def test_parse_none_input(self):
        """Test parsing None input returns None."""
        result = safe_json_parse(None)
        assert result is None
    
    def test_parse_numeric_string(self):
        """Test parsing numeric string that's not JSON."""
        json_str = '123abc'
        result = safe_json_parse(json_str)
        assert result == json_str
    
    def test_parse_partial_json(self):
        """Test parsing partial JSON returns original."""
        json_str = '{"incomplete":'
        result = safe_json_parse(json_str)
        assert result == json_str
    
    def test_parse_json_with_comments(self):
        """Test parsing JSON with comments returns original."""
        json_str = '{"key": "value", // comment}'
        result = safe_json_parse(json_str)
        assert result == json_str
    
    def test_parse_single_quotes_json(self):
        """Test parsing JSON with single quotes returns original."""
        json_str = "{'key': 'value'}"
        result = safe_json_parse(json_str)
        assert result == json_str
    
    def test_parse_very_large_json(self):
        """Test parsing very large JSON string."""
        large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
        json_str = json.dumps(large_dict)
        result = safe_json_parse(json_str)
        assert result == large_dict
    
    def test_parse_deeply_nested_json(self):
        """Test parsing deeply nested JSON."""
        nested = {"level": 1}
        for i in range(2, 11):  # Create 10 levels of nesting
            nested = {"level": i, "nested": nested}
        
        json_str = json.dumps(nested)
        result = safe_json_parse(json_str)
        assert result == nested