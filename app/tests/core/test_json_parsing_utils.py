"""Comprehensive unit tests for JSON parsing utilities."""

import pytest
import json
from unittest.mock import patch, Mock
from typing import Any, Dict, List

# Import the functions we're testing
from app.core.json_parsing_utils import (
    safe_json_parse,
    parse_dict_field,
    parse_list_field,
    parse_string_list_field,
    fix_tool_parameters,
    fix_list_recommendations,
    comprehensive_json_fix,
    _try_json_parse,
    _parse_string_to_dict,
    _parse_string_to_list,
    _parse_string_to_string_list,
    _parse_dict_to_string_list,
    _fix_tool_params_list,
    _fix_dict_data,
    _handle_unexpected_type,
    _handle_json_error
)


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
        json_str = '42.5'
        result = safe_json_parse(json_str)
        assert result == 42.5
    
    def test_parse_valid_json_boolean(self):
        """Test parsing valid JSON boolean."""
        json_str = 'true'
        result = safe_json_parse(json_str)
        assert result is True
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON returns fallback."""
        json_str = '{"invalid": json}'
        result = safe_json_parse(json_str)
        assert result == {}
    
    def test_parse_invalid_json_with_custom_fallback(self):
        """Test parsing invalid JSON with custom fallback."""
        json_str = '{"invalid": json}'
        fallback = {"fallback": "value"}
        result = safe_json_parse(json_str, fallback)
        assert result == fallback
    
    def test_parse_empty_string(self):
        """Test parsing empty string returns fallback."""
        result = safe_json_parse("")
        assert result == {}
    
    def test_parse_whitespace_string(self):
        """Test parsing whitespace-only string returns fallback."""
        result = safe_json_parse("   \n\t  ")
        assert result == {}
    
    def test_parse_non_string_returns_value(self):
        """Test passing non-string value returns the value unchanged."""
        test_dict = {"already": "parsed"}
        result = safe_json_parse(test_dict)
        assert result == test_dict
        
        test_list = [1, 2, 3]
        result = safe_json_parse(test_list)
        assert result == test_list
        
        result = safe_json_parse(42)
        assert result == 42
        
        result = safe_json_parse(None)
        assert result is None


class TestParseDictField:
    """Test the parse_dict_field function."""
    
    def test_parse_dict_returns_dict(self):
        """Test passing dict returns the dict unchanged."""
        test_dict = {"key": "value", "nested": {"inner": "data"}}
        result = parse_dict_field(test_dict)
        assert result == test_dict
    
    def test_parse_valid_json_string_to_dict(self):
        """Test parsing valid JSON string to dict."""
        json_str = '{"name": "test", "value": 123}'
        result = parse_dict_field(json_str)
        expected = {"name": "test", "value": 123}
        assert result == expected
    
    def test_parse_invalid_json_string_returns_empty_dict(self):
        """Test parsing invalid JSON string returns empty dict."""
        invalid_json = '{"invalid": json syntax}'
        result = parse_dict_field(invalid_json)
        assert result == {}
    
    def test_parse_json_list_string_returns_empty_dict(self):
        """Test parsing JSON list string returns empty dict."""
        json_list = '[1, 2, 3]'
        result = parse_dict_field(json_list)
        assert result == {}
    
    def test_parse_non_dict_non_string_returns_empty_dict(self):
        """Test passing non-dict, non-string returns empty dict."""
        result = parse_dict_field(123)
        assert result == {}
        
        result = parse_dict_field([1, 2, 3])
        assert result == {}
        
        result = parse_dict_field(None)
        assert result == {}


class TestParseListField:
    """Test the parse_list_field function."""
    
    def test_parse_list_returns_list(self):
        """Test passing list returns the list unchanged."""
        test_list = [1, "two", {"three": 3}]
        result = parse_list_field(test_list)
        assert result == test_list
    
    def test_parse_valid_json_string_to_list(self):
        """Test parsing valid JSON string to list."""
        json_str = '[1, "two", {"three": 3}]'
        result = parse_list_field(json_str)
        expected = [1, "two", {"three": 3}]
        assert result == expected
    
    def test_parse_invalid_json_string_returns_empty_list(self):
        """Test parsing invalid JSON string returns empty list."""
        invalid_json = '[1, 2, invalid]'
        result = parse_list_field(invalid_json)
        assert result == []
    
    def test_parse_json_dict_string_returns_empty_list(self):
        """Test parsing JSON dict string returns empty list."""
        json_dict = '{"key": "value"}'
        result = parse_list_field(json_dict)
        assert result == []
    
    def test_parse_non_list_non_string_returns_empty_list(self):
        """Test passing non-list, non-string returns empty list."""
        result = parse_list_field(123)
        assert result == []
        
        result = parse_list_field({"key": "value"})
        assert result == []
        
        result = parse_list_field(None)
        assert result == []


class TestParseStringListField:
    """Test the parse_string_list_field function."""
    
    def test_parse_string_list_returns_string_list(self):
        """Test passing list of strings returns list of strings."""
        test_list = ["one", "two", "three"]
        result = parse_string_list_field(test_list)
        assert result == test_list
    
    def test_parse_mixed_list_converts_to_string_list(self):
        """Test passing mixed list converts all items to strings."""
        test_list = ["one", 2, {"three": 3}, None]
        result = parse_string_list_field(test_list)
        expected = ["one", "2", "{'three': 3}", "None"]
        assert result == expected
    
    def test_parse_json_array_string_to_string_list(self):
        """Test parsing JSON array string to string list."""
        json_str = '["one", "two", "three"]'
        result = parse_string_list_field(json_str)
        expected = ["one", "two", "three"]
        assert result == expected
    
    def test_parse_json_mixed_array_string_to_string_list(self):
        """Test parsing JSON mixed array string to string list."""
        json_str = '["one", 2, true, null]'
        result = parse_string_list_field(json_str)
        expected = ["one", "2", "True", "None"]
        assert result == expected
    
    def test_parse_json_object_string_to_string_list(self):
        """Test parsing JSON object string to string list."""
        json_str = '{"key1": "value1", "key2": "value2"}'
        result = parse_string_list_field(json_str)
        # Should return single item with the original string
        assert result == [json_str]
    
    def test_parse_plain_string_returns_single_item_list(self):
        """Test parsing plain string returns single-item list."""
        test_str = "simple string"
        result = parse_string_list_field(test_str)
        assert result == ["simple string"]
    
    def test_parse_dict_with_description_key(self):
        """Test parsing dict with description key."""
        test_dict = {"description": "test description", "other": "ignored"}
        result = parse_string_list_field(test_dict)
        assert result == ["test description"]
    
    def test_parse_dict_without_description_key(self):
        """Test parsing dict without description key."""
        test_dict = {"key1": "value1", "key2": "value2", "key3": None}
        result = parse_string_list_field(test_dict)
        # Should include non-None values
        assert len(result) == 2
        assert "value1" in result
        assert "value2" in result
        assert "None" not in result
    
    def test_parse_unexpected_type_returns_empty_list(self):
        """Test parsing unexpected type returns empty list."""
        result = parse_string_list_field(123)
        assert result == []
        
        result = parse_string_list_field(None)
        assert result == []


class TestFixToolParameters:
    """Test the fix_tool_parameters function."""
    
    def test_fix_tool_parameters_with_string_params(self):
        """Test fixing tool parameters that are JSON strings."""
        data = {
            "tool_recommendations": [
                {
                    "tool": "test_tool",
                    "parameters": '{"param1": "value1", "param2": 123}'
                }
            ]
        }
        
        result = fix_tool_parameters(data)
        
        expected_params = {"param1": "value1", "param2": 123}
        assert result["tool_recommendations"][0]["parameters"] == expected_params
    
    def test_fix_tool_parameters_with_dict_params(self):
        """Test fixing tool parameters that are already dicts."""
        data = {
            "tool_recommendations": [
                {
                    "tool": "test_tool",
                    "parameters": {"param1": "value1", "param2": 123}
                }
            ]
        }
        
        result = fix_tool_parameters(data)
        
        # Should remain unchanged
        expected_params = {"param1": "value1", "param2": 123}
        assert result["tool_recommendations"][0]["parameters"] == expected_params
    
    def test_fix_tool_parameters_no_tool_recommendations(self):
        """Test fixing data without tool_recommendations key."""
        data = {"other_key": "value"}
        result = fix_tool_parameters(data)
        assert result == data
    
    def test_fix_tool_parameters_empty_tool_recommendations(self):
        """Test fixing data with empty tool_recommendations."""
        data = {"tool_recommendations": []}
        result = fix_tool_parameters(data)
        assert result == data
    
    def test_fix_tool_parameters_invalid_structure(self):
        """Test fixing data with invalid tool_recommendations structure."""
        data = {"tool_recommendations": "not a list"}
        result = fix_tool_parameters(data)
        assert result == data
    
    def test_fix_tool_parameters_non_dict_input(self):
        """Test fixing non-dict input returns unchanged."""
        assert fix_tool_parameters("string") == "string"
        assert fix_tool_parameters([1, 2, 3]) == [1, 2, 3]
        assert fix_tool_parameters(None) is None


class TestFixListRecommendations:
    """Test the fix_list_recommendations function."""
    
    def test_fix_recommendations_string_list(self):
        """Test fixing recommendations that are JSON string."""
        data = {
            "recommendations": '["rec1", "rec2", "rec3"]'
        }
        
        result = fix_list_recommendations(data)
        
        assert result["recommendations"] == ["rec1", "rec2", "rec3"]
    
    def test_fix_recommendations_already_list(self):
        """Test fixing recommendations that are already a list."""
        data = {
            "recommendations": ["rec1", "rec2", "rec3"]
        }
        
        result = fix_list_recommendations(data)
        
        assert result["recommendations"] == ["rec1", "rec2", "rec3"]
    
    def test_fix_recommendations_no_recommendations_key(self):
        """Test fixing data without recommendations key."""
        data = {"other_key": "value"}
        result = fix_list_recommendations(data)
        assert result == data
    
    def test_fix_recommendations_non_dict_input(self):
        """Test fixing non-dict input returns unchanged."""
        assert fix_list_recommendations("string") == "string"
        assert fix_list_recommendations([1, 2, 3]) == [1, 2, 3]
        assert fix_list_recommendations(None) is None


class TestComprehensiveJsonFix:
    """Test the comprehensive_json_fix function."""
    
    def test_fix_nested_dict_structure(self):
        """Test fixing complex nested dictionary structure."""
        data = {
            "tool_recommendations": [
                {
                    "tool": "test_tool",
                    "parameters": '{"param1": "value1"}'
                }
            ],
            "recommendations": '["rec1", "rec2"]',
            "nested": {
                "tool_recommendations": [
                    {
                        "tool": "nested_tool",
                        "parameters": '{"nested_param": "nested_value"}'
                    }
                ]
            }
        }
        
        result = comprehensive_json_fix(data)
        
        # Check top-level fixes
        assert result["tool_recommendations"][0]["parameters"] == {"param1": "value1"}
        assert result["recommendations"] == ["rec1", "rec2"]
        
        # Check nested fixes
        nested_params = {"nested_param": "nested_value"}
        assert result["nested"]["tool_recommendations"][0]["parameters"] == nested_params
    
    def test_fix_list_of_dicts(self):
        """Test fixing list containing dictionaries."""
        data = [
            {
                "tool_recommendations": [
                    {"tool": "tool1", "parameters": '{"p1": "v1"}'}
                ]
            },
            {
                "recommendations": '["r1", "r2"]'
            }
        ]
        
        result = comprehensive_json_fix(data)
        
        assert len(result) == 2
        assert result[0]["tool_recommendations"][0]["parameters"] == {"p1": "v1"}
        assert result[1]["recommendations"] == ["r1", "r2"]
    
    def test_fix_primitive_values(self):
        """Test fixing primitive values returns unchanged."""
        assert comprehensive_json_fix("string") == "string"
        assert comprehensive_json_fix(123) == 123
        assert comprehensive_json_fix(True) is True
        assert comprehensive_json_fix(None) is None
    
    def test_fix_mixed_nested_structure(self):
        """Test fixing complex mixed structure."""
        data = {
            "level1": {
                "level2": [
                    {
                        "tool_recommendations": [
                            {"parameters": '{"deep": "value"}'}
                        ],
                        "recommendations": '["deep1", "deep2"]'
                    }
                ]
            }
        }
        
        result = comprehensive_json_fix(data)
        
        deep_item = result["level1"]["level2"][0]
        assert deep_item["tool_recommendations"][0]["parameters"] == {"deep": "value"}
        assert deep_item["recommendations"] == ["deep1", "deep2"]


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_try_json_parse_success(self):
        """Test successful JSON parsing."""
        json_str = '{"key": "value"}'
        fallback = {"fallback": True}
        
        result = _try_json_parse(json_str, fallback)
        assert result == {"key": "value"}
    
    def test_try_json_parse_failure(self):
        """Test failed JSON parsing returns fallback."""
        invalid_json = '{"invalid": json}'
        fallback = {"fallback": True}
        
        result = _try_json_parse(invalid_json, fallback)
        assert result == fallback
    
    def test_parse_string_to_dict_success(self):
        """Test successful string to dict parsing."""
        json_str = '{"key": "value"}'
        result = _parse_string_to_dict(json_str)
        assert result == {"key": "value"}
    
    def test_parse_string_to_dict_non_dict_result(self):
        """Test string parsing that results in non-dict."""
        json_str = '[1, 2, 3]'
        result = _parse_string_to_dict(json_str)
        assert result == {}
    
    def test_parse_string_to_list_success(self):
        """Test successful string to list parsing."""
        json_str = '[1, 2, 3]'
        result = _parse_string_to_list(json_str)
        assert result == [1, 2, 3]
    
    def test_parse_string_to_list_non_list_result(self):
        """Test string parsing that results in non-list."""
        json_str = '{"key": "value"}'
        result = _parse_string_to_list(json_str)
        assert result == []
    
    def test_parse_string_to_string_list_json_array(self):
        """Test parsing JSON array string to string list."""
        json_str = '["one", "two", "three"]'
        result = _parse_string_to_string_list(json_str)
        assert result == ["one", "two", "three"]
    
    def test_parse_string_to_string_list_json_object(self):
        """Test parsing JSON object string returns original string."""
        json_str = '{"key": "value"}'
        result = _parse_string_to_string_list(json_str)
        assert result == [json_str]
    
    def test_parse_string_to_string_list_plain_string(self):
        """Test parsing plain string returns single-item list."""
        plain_str = "plain string"
        result = _parse_string_to_string_list(plain_str)
        assert result == [plain_str]
    
    def test_parse_dict_to_string_list_with_description(self):
        """Test parsing dict with description key."""
        test_dict = {"description": "test desc", "other": "value"}
        result = _parse_dict_to_string_list(test_dict)
        assert result == ["test desc"]
    
    def test_parse_dict_to_string_list_without_description(self):
        """Test parsing dict without description key."""
        test_dict = {"key1": "value1", "key2": "value2", "key3": None}
        result = _parse_dict_to_string_list(test_dict)
        
        # Should include non-None values as strings
        assert len(result) == 2
        assert "value1" in result
        assert "value2" in result
    
    def test_fix_tool_params_list(self):
        """Test fixing parameters in tool recommendation list."""
        tool_list = [
            {"tool": "tool1", "parameters": '{"p1": "v1"}'},
            {"tool": "tool2", "parameters": {"p2": "v2"}},
            {"tool": "tool3"}  # No parameters key
        ]
        
        _fix_tool_params_list(tool_list)
        
        assert tool_list[0]["parameters"] == {"p1": "v1"}
        assert tool_list[1]["parameters"] == {"p2": "v2"}
        assert "parameters" not in tool_list[2] or tool_list[2].get("parameters") is None
    
    def test_fix_dict_data(self):
        """Test fixing dictionary data."""
        data = {
            "tool_recommendations": [
                {"parameters": '{"p1": "v1"}'}
            ],
            "recommendations": '["r1", "r2"]',
            "nested": {
                "recommendations": '["nested"]'
            }
        }
        
        result = _fix_dict_data(data)
        
        assert result["tool_recommendations"][0]["parameters"] == {"p1": "v1"}
        assert result["recommendations"] == ["r1", "r2"]
        assert result["nested"]["recommendations"] == ["nested"]
    
    def test_handle_unexpected_type(self):
        """Test handling unexpected types."""
        result = _handle_unexpected_type(123)
        assert result == []
        
        result = _handle_unexpected_type(None)
        assert result == []
    
    def test_handle_json_error(self):
        """Test handling JSON errors."""
        error = json.JSONDecodeError("test error", "doc", 0)
        fallback = {"error": "fallback"}
        
        result = _handle_json_error("invalid json", error, fallback)
        assert result == fallback
        
        result = _handle_json_error("invalid json", error, None)
        assert result == {}


class TestLoggingBehavior:
    """Test logging behavior of JSON parsing functions."""
    
    @patch('app.core.json_parsing_utils.logger')
    def test_safe_json_parse_logs_debug_on_success(self, mock_logger):
        """Test that successful parsing logs debug message."""
        json_str = '{"key": "value"}'
        safe_json_parse(json_str)
        
        mock_logger.debug.assert_called_once()
        debug_call = mock_logger.debug.call_args[0][0]
        assert "Successfully parsed JSON string" in debug_call
    
    @patch('app.core.json_parsing_utils.logger')
    def test_safe_json_parse_logs_warning_on_failure(self, mock_logger):
        """Test that failed parsing logs warning message."""
        invalid_json = '{"invalid": json}'
        safe_json_parse(invalid_json)
        
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Failed to parse JSON string" in warning_call
    
    @patch('app.core.json_parsing_utils.logger')
    def test_parse_dict_field_logs_warning_for_unexpected_type(self, mock_logger):
        """Test that unexpected type logs warning."""
        parse_dict_field(123)
        
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Expected dict or string" in warning_call
    
    @patch('app.core.json_parsing_utils.logger')
    def test_parse_list_field_logs_warning_for_unexpected_type(self, mock_logger):
        """Test that unexpected type logs warning."""
        parse_list_field(123)
        
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Expected list or string" in warning_call
    
    @patch('app.core.json_parsing_utils.logger')
    def test_parse_string_list_field_logs_warning_for_unexpected_type(self, mock_logger):
        """Test that unexpected type logs warning."""
        parse_string_list_field(123)
        
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Expected list/string/dict" in warning_call


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_deeply_nested_json(self):
        """Test parsing deeply nested JSON structure."""
        nested_json = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "deep"
                        }
                    }
                }
            }
        }
        json_str = json.dumps(nested_json)
        
        result = safe_json_parse(json_str)
        assert result == nested_json
    
    def test_large_json_string(self):
        """Test parsing large JSON string."""
        large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
        json_str = json.dumps(large_dict)
        
        result = safe_json_parse(json_str)
        assert result == large_dict
    
    def test_unicode_in_json(self):
        """Test parsing JSON with unicode characters."""
        unicode_json = '{"unicode": "Hello 世界 🌍", "emoji": "😀"}'
        result = safe_json_parse(unicode_json)
        
        expected = {"unicode": "Hello 世界 🌍", "emoji": "😀"}
        assert result == expected
    
    def test_json_with_special_characters(self):
        """Test parsing JSON with special characters."""
        special_json = '{"quotes": "\\"nested quotes\\"", "newlines": "line1\\nline2"}'
        result = safe_json_parse(special_json)
        
        expected = {"quotes": '"nested quotes"', "newlines": "line1\nline2"}
        assert result == expected
    
    def test_malformed_json_variations(self):
        """Test various malformed JSON strings."""
        malformed_cases = [
            '{"missing_quote: "value"}',
            '{"trailing_comma": "value",}',
            '{missing_quotes: "value"}',
            '{"unclosed_brace": "value"',
            '{"double_comma":, "value"}',
            '{"invalid_value": undefined}',
        ]
        
        for malformed_json in malformed_cases:
            result = safe_json_parse(malformed_json)
            assert result == {}
    
    def test_empty_and_whitespace_variations(self):
        """Test various empty and whitespace strings."""
        empty_cases = ["", " ", "\t", "\n", "\r\n", "   \t\n  "]
        
        for empty_str in empty_cases:
            result = safe_json_parse(empty_str)
            assert result == {}
    
    def test_json_null_values(self):
        """Test parsing JSON with null values."""
        json_with_nulls = '{"null_value": null, "empty_string": "", "zero": 0}'
        result = safe_json_parse(json_with_nulls)
        
        expected = {"null_value": None, "empty_string": "", "zero": 0}
        assert result == expected