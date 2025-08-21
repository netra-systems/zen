"""
Tests for JSON field parsing functions.
All functions ≤8 lines per requirements.
"""

import pytest
from netra_backend.app.core.json_parsing_utils import (
    parse_dict_field,
    parse_list_field,
    parse_string_list_field
)


class TestParseDictField:
    """Test the parse_dict_field function."""
    
    def test_parse_valid_dict_string(self):
        """Test parsing valid dict string."""
        dict_str = '{"name": "test", "value": 42}'
        result = parse_dict_field(dict_str)
        expected = {"name": "test", "value": 42}
        assert result == expected
    
    def test_parse_empty_dict_string(self):
        """Test parsing empty dict string."""
        dict_str = '{}'
        result = parse_dict_field(dict_str)
        assert result == {}
    
    def test_parse_already_dict(self):
        """Test parsing already parsed dict."""
        dict_obj = {"key": "value"}
        result = parse_dict_field(dict_obj)
        assert result == dict_obj
    
    def test_parse_invalid_dict_string(self):
        """Test parsing invalid dict string returns empty dict."""
        dict_str = 'invalid dict'
        result = parse_dict_field(dict_str)
        assert result == {}
    
    def test_parse_none_returns_empty_dict(self):
        """Test parsing None returns empty dict."""
        result = parse_dict_field(None)
        assert result == {}
    
    def test_parse_empty_string_returns_empty_dict(self):
        """Test parsing empty string returns empty dict."""
        result = parse_dict_field('')
        assert result == {}
    
    def test_parse_list_returns_empty_dict(self):
        """Test parsing list returns empty dict."""
        list_obj = [1, 2, 3]
        result = parse_dict_field(list_obj)
        assert result == {}
    
    def test_parse_nested_dict(self):
        """Test parsing nested dict string."""
        dict_str = '{"outer": {"inner": "value"}, "count": 5}'
        result = parse_dict_field(dict_str)
        expected = {"outer": {"inner": "value"}, "count": 5}
        assert result == expected
    
    def test_parse_dict_with_list_values(self):
        """Test parsing dict with list values."""
        dict_str = '{"items": [1, 2, 3], "name": "test"}'
        result = parse_dict_field(dict_str)
        expected = {"items": [1, 2, 3], "name": "test"}
        assert result == expected


class TestParseListField:
    """Test the parse_list_field function."""
    
    def test_parse_valid_list_string(self):
        """Test parsing valid list string."""
        list_str = '[1, 2, 3, "test"]'
        result = parse_list_field(list_str)
        expected = [1, 2, 3, "test"]
        assert result == expected
    
    def test_parse_empty_list_string(self):
        """Test parsing empty list string."""
        list_str = '[]'
        result = parse_list_field(list_str)
        assert result == []
    
    def test_parse_already_list(self):
        """Test parsing already parsed list."""
        list_obj = [1, 2, 3]
        result = parse_list_field(list_obj)
        assert result == list_obj
    
    def test_parse_invalid_list_string(self):
        """Test parsing invalid list string returns empty list."""
        list_str = 'invalid list'
        result = parse_list_field(list_str)
        assert result == []
    
    def test_parse_none_returns_empty_list(self):
        """Test parsing None returns empty list."""
        result = parse_list_field(None)
        assert result == []
    
    def test_parse_empty_string_returns_empty_list(self):
        """Test parsing empty string returns empty list."""
        result = parse_list_field('')
        assert result == []
    
    def test_parse_dict_returns_empty_list(self):
        """Test parsing dict returns empty list."""
        dict_obj = {"key": "value"}
        result = parse_list_field(dict_obj)
        assert result == []
    
    def test_parse_nested_list(self):
        """Test parsing nested list string."""
        list_str = '[[1, 2], [3, 4], "test"]'
        result = parse_list_field(list_str)
        expected = [[1, 2], [3, 4], "test"]
        assert result == expected
    
    def test_parse_list_with_dict_items(self):
        """Test parsing list with dict items."""
        list_str = '[{"name": "item1"}, {"name": "item2"}]'
        result = parse_list_field(list_str)
        expected = [{"name": "item1"}, {"name": "item2"}]
        assert result == expected


class TestParseStringListField:
    """Test the parse_string_list_field function."""
    
    def test_parse_valid_string_list(self):
        """Test parsing valid string list."""
        list_str = '["item1", "item2", "item3"]'
        result = parse_string_list_field(list_str)
        expected = ["item1", "item2", "item3"]
        assert result == expected
    
    def test_parse_mixed_type_list_filters_strings(self):
        """Test parsing mixed type list filters to strings only."""
        list_str = '["string1", 42, "string2", true, "string3"]'
        result = parse_string_list_field(list_str)
        expected = ["string1", "string2", "string3"]
        assert result == expected
    
    def test_parse_already_string_list(self):
        """Test parsing already parsed string list."""
        list_obj = ["item1", "item2"]
        result = parse_string_list_field(list_obj)
        assert result == list_obj
    
    def test_parse_mixed_list_object(self):
        """Test parsing mixed type list object."""
        list_obj = ["string1", 42, "string2", None, "string3"]
        result = parse_string_list_field(list_obj)
        expected = ["string1", "string2", "string3"]
        assert result == expected
    
    def test_parse_dict_with_string_values(self):
        """Test parsing dict extracts string values."""
        dict_obj = {"key1": "value1", "key2": 42, "key3": "value3"}
        result = parse_string_list_field(dict_obj)
        expected = ["value1", "value3"]
        assert result == expected
    
    def test_parse_single_string(self):
        """Test parsing single string converts to list."""
        string_val = "single_item"
        result = parse_string_list_field(string_val)
        expected = ["single_item"]
        assert result == expected
    
    def test_parse_invalid_string_returns_empty_list(self):
        """Test parsing invalid string returns empty list."""
        invalid_str = 'invalid list'
        result = parse_string_list_field(invalid_str)
        assert result == []
    
    def test_parse_none_returns_empty_list(self):
        """Test parsing None returns empty list."""
        result = parse_string_list_field(None)
        assert result == []
    
    def test_parse_empty_string_returns_empty_list(self):
        """Test parsing empty string returns empty list."""
        result = parse_string_list_field('')
        assert result == []
    
    def test_parse_numeric_values_filtered_out(self):
        """Test numeric values are filtered out."""
        list_str = '[123, 45.6, "string1", "string2"]'
        result = parse_string_list_field(list_str)
        expected = ["string1", "string2"]
        assert result == expected
    
    def test_parse_boolean_values_filtered_out(self):
        """Test boolean values are filtered out."""
        list_str = '[true, false, "string1", "string2"]'
        result = parse_string_list_field(list_str)
        expected = ["string1", "string2"]
        assert result == expected
    
    def test_parse_null_values_filtered_out(self):
        """Test null values are filtered out."""
        list_str = '[null, "string1", null, "string2"]'
        result = parse_string_list_field(list_str)
        expected = ["string1", "string2"]
        assert result == expected
    
    def test_parse_nested_structures_filtered_out(self):
        """Test nested structures are filtered out."""
        list_str = '[{"nested": "dict"}, ["nested", "list"], "string1"]'
        result = parse_string_list_field(list_str)
        expected = ["string1"]
        assert result == expected
    
    def test_parse_empty_list_returns_empty_list(self):
        """Test parsing empty list returns empty list."""
        list_str = '[]'
        result = parse_string_list_field(list_str)
        assert result == []
    
    def test_parse_all_non_string_list(self):
        """Test parsing list with no strings returns empty."""
        list_str = '[123, true, null, {"key": "value"}]'
        result = parse_string_list_field(list_str)
        assert result == []