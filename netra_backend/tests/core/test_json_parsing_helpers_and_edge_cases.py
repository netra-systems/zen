"""
Tests for JSON parsing helper functions and edge cases.
All functions ≤8 lines per requirements.
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import Mock, patch

import pytest

# Add project root to path
from netra_backend.app.core.json_parsing_utils import (
    _fix_dict_data,
    _fix_tool_params_list,
    _handle_json_error,
    _handle_unexpected_type,
    _parse_dict_to_string_list,
    _parse_string_to_dict,
    _parse_string_to_list,
    _parse_string_to_string_list,
    # Add project root to path
    _try_json_parse,
)


class TestHelperFunctions:
    """Test internal helper functions."""
    
    def test_try_json_parse_valid_json(self):
        """Test _try_json_parse with valid JSON."""
        json_str = '{"key": "value"}'
        result = _try_json_parse(json_str)
        expected = {"key": "value"}
        assert result == expected
    
    def test_try_json_parse_invalid_json(self):
        """Test _try_json_parse with invalid JSON."""
        json_str = 'invalid json'
        result = _try_json_parse(json_str)
        assert result == json_str
    
    def test_parse_string_to_dict_valid(self):
        """Test _parse_string_to_dict with valid string."""
        dict_str = '{"name": "test", "value": 42}'
        result = _parse_string_to_dict(dict_str)
        expected = {"name": "test", "value": 42}
        assert result == expected
    
    def test_parse_string_to_dict_invalid(self):
        """Test _parse_string_to_dict with invalid string."""
        invalid_str = 'not a dict'
        result = _parse_string_to_dict(invalid_str)
        assert result == {}
    
    def test_parse_string_to_list_valid(self):
        """Test _parse_string_to_list with valid string."""
        list_str = '[1, 2, 3, "test"]'
        result = _parse_string_to_list(list_str)
        expected = [1, 2, 3, "test"]
        assert result == expected
    
    def test_parse_string_to_list_invalid(self):
        """Test _parse_string_to_list with invalid string."""
        invalid_str = 'not a list'
        result = _parse_string_to_list(invalid_str)
        assert result == []
    
    def test_parse_string_to_string_list_valid(self):
        """Test _parse_string_to_string_list with valid string."""
        list_str = '["item1", "item2", "item3"]'
        result = _parse_string_to_string_list(list_str)
        expected = ["item1", "item2", "item3"]
        assert result == expected
    
    def test_parse_string_to_string_list_mixed(self):
        """Test _parse_string_to_string_list with mixed types."""
        list_str = '["string1", 42, "string2", true]'
        result = _parse_string_to_string_list(list_str)
        expected = ["string1", "string2"]
        assert result == expected
    
    def test_parse_dict_to_string_list(self):
        """Test _parse_dict_to_string_list."""
        dict_obj = {"key1": "value1", "key2": 42, "key3": "value3"}
        result = _parse_dict_to_string_list(dict_obj)
        expected = ["value1", "value3"]
        assert result == expected
    
    def test_fix_tool_params_list_valid(self):
        """Test _fix_tool_params_list with valid list."""
        params_list = [{"param1": "value1"}, {"param2": "value2"}]
        result = _fix_tool_params_list(params_list)
        expected = {"param1": "value1", "param2": "value2"}
        assert result == expected
    
    def test_fix_tool_params_list_with_invalid_items(self):
        """Test _fix_tool_params_list with some invalid items."""
        params_list = [{"valid": "param"}, "invalid", {"another": "param"}]
        result = _fix_tool_params_list(params_list)
        expected = {"valid": "param", "another": "param"}
        assert result == expected
    
    def test_fix_dict_data_valid(self):
        """Test _fix_dict_data with valid data."""
        data = {"key": "value"}
        result = _fix_dict_data(data)
        assert result == data
    
    def test_fix_dict_data_invalid(self):
        """Test _fix_dict_data with invalid data."""
        invalid_data = "not a dict"
        result = _fix_dict_data(invalid_data)
        assert result == {}
    
    def test_handle_unexpected_type(self):
        """Test _handle_unexpected_type function."""
        unexpected_value = set([1, 2, 3])  # Set is unexpected type
        result = _handle_unexpected_type(unexpected_value, "test_field")
        assert result == {}  # Should return empty dict for unexpected types
    
    def test_handle_json_error_logs_error(self):
        """Test _handle_json_error logs the error."""
        with patch('app.core.json_parsing_utils.logger') as mock_logger:
            error = ValueError("Test error")
            result = _handle_json_error(error, "test data")
            
            mock_logger.warning.assert_called_once()
            assert result == "test data"


class TestLoggingBehavior:
    """Test logging behavior of JSON parsing functions."""
    
    def test_safe_json_parse_logs_parse_errors(self):
        """Test that safe_json_parse logs parse errors."""
        from netra_backend.app.core.json_parsing_utils import safe_json_parse
        
        with patch('app.core.json_parsing_utils.logger') as mock_logger:
            result = safe_json_parse('invalid json {')
            
            mock_logger.warning.assert_called_once()
            assert result == 'invalid json {'
    
    def test_parse_dict_field_logs_type_errors(self):
        """Test that parse_dict_field logs type errors."""
        from netra_backend.app.core.json_parsing_utils import parse_dict_field
        
        with patch('app.core.json_parsing_utils.logger') as mock_logger:
            result = parse_dict_field([1, 2, 3])  # List instead of dict
            
            mock_logger.warning.assert_called_once()
            assert result == {}
    
    def test_parse_list_field_logs_type_errors(self):
        """Test that parse_list_field logs type errors."""
        from netra_backend.app.core.json_parsing_utils import parse_list_field
        
        with patch('app.core.json_parsing_utils.logger') as mock_logger:
            result = parse_list_field({"key": "value"})  # Dict instead of list
            
            mock_logger.warning.assert_called_once()
            assert result == []
    
    def test_comprehensive_json_fix_logs_fixes(self):
        """Test that comprehensive_json_fix logs when fixes are applied."""
        from netra_backend.app.core.json_parsing_utils import comprehensive_json_fix
        
        with patch('app.core.json_parsing_utils.logger') as mock_logger:
            data = {
                "tool_parameters": "invalid json",
                "list_recommendations": "invalid list"
            }
            result = comprehensive_json_fix(data)
            
            # Should log warnings for both invalid fields
            assert mock_logger.warning.call_count >= 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_large_json_string(self):
        """Test parsing very large JSON strings."""
        from netra_backend.app.core.json_parsing_utils import safe_json_parse
        
        # Create large JSON string
        large_dict = {f"key_{i}": f"value_{i}" for i in range(10000)}
        import json
        large_json = json.dumps(large_dict)
        
        result = safe_json_parse(large_json)
        assert result == large_dict
    
    def test_deeply_nested_json_structures(self):
        """Test parsing deeply nested JSON structures."""
        from netra_backend.app.core.json_parsing_utils import safe_json_parse
        
        # Create deeply nested structure
        nested = {"level": 1}
        for i in range(2, 21):  # 20 levels of nesting
            nested = {"level": i, "nested": nested}
        
        import json
        nested_json = json.dumps(nested)
        result = safe_json_parse(nested_json)
        assert result == nested
    
    def test_unicode_and_special_characters(self):
        """Test handling unicode and special characters."""
        from netra_backend.app.core.json_parsing_utils import safe_json_parse
        
        unicode_json = '{"message": "Hello 世界", "emoji": "😀🎉", "special": "\\n\\t\\r"}'
        result = safe_json_parse(unicode_json)
        
        assert "世界" in result["message"]
        assert "😀🎉" in result["emoji"]
        assert "\n\t\r" in result["special"]
    
    def test_memory_efficiency_with_large_data(self):
        """Test memory efficiency with large data structures."""
        from netra_backend.app.core.json_parsing_utils import parse_string_list_field
        
        large_list = self._create_large_mixed_list(10000)
        result = parse_string_list_field(large_list)
        
        self._assert_large_list_results(result)
    
    def _create_large_mixed_list(self, size: int) -> list:
        """Create large list with mixed types for testing"""
        large_list = []
        for i in range(size):
            if i % 2 == 0:
                large_list.append(f"string_{i}")
            else:
                large_list.append(i)  # Non-string to be filtered
        return large_list
    
    def _assert_large_list_results(self, result: list) -> None:
        """Assert results of large list processing"""
        # Should contain only string elements
        assert len(result) == 5000
        assert all(isinstance(item, str) for item in result)
    
    def test_circular_reference_handling(self):
        """Test handling of circular references."""
        from netra_backend.app.core.json_parsing_utils import parse_dict_field
        
        # Create object with circular reference
        circular_dict = {"key": "value"}
        circular_dict["self"] = circular_dict
        
        # Should handle gracefully (not crash)
        result = parse_dict_field(circular_dict)
        assert isinstance(result, dict)
    
    def test_malformed_json_recovery(self):
        """Test recovery from various malformed JSON."""
        from netra_backend.app.core.json_parsing_utils import safe_json_parse
        
        malformed_cases = self._get_malformed_json_cases()
        
        for case in malformed_cases:
            result = safe_json_parse(case)
            assert result == case  # Should return original string
    
    def _get_malformed_json_cases(self) -> list:
        """Get list of malformed JSON cases for testing"""
        return [
            '{"key": value}',  # Missing quotes
            '{"key": "value",}',  # Trailing comma
            '{key: "value"}',  # Unquoted key
            '{"key": "value"',  # Missing closing brace
            '"unclosed string',  # Unclosed string
        ]
    
    def test_empty_and_whitespace_inputs(self):
        """Test handling of empty and whitespace inputs."""
        from netra_backend.app.core.json_parsing_utils import (
            parse_dict_field,
            parse_list_field,
            safe_json_parse,
        )
        
        empty_cases = self._get_empty_cases()
        self._test_empty_cases_with_parsers(empty_cases, safe_json_parse, parse_dict_field, parse_list_field)
    
    def _get_empty_cases(self) -> list:
        """Get list of empty and whitespace cases for testing"""
        return ['', '   ', '\t\n\r', None]
    
    def _test_empty_cases_with_parsers(self, empty_cases, safe_parse, dict_parse, list_parse) -> None:
        """Test empty cases with different parsers"""
        for case in empty_cases:
            # Safe parse should return input as-is or None
            safe_result = safe_parse(case)
            assert safe_result == case
            
            # Dict and list parsers should return empty containers
            self._assert_empty_parse_results(dict_parse(case), list_parse(case))
    
    def _assert_empty_parse_results(self, dict_result, list_result) -> None:
        """Assert results of empty input parsing"""
        assert dict_result == {}
        assert list_result == []
    
    def test_extreme_nesting_limits(self):
        """Test behavior at extreme nesting limits."""
        from netra_backend.app.core.json_parsing_utils import safe_json_parse
        
        nested = self._create_extremely_nested_structure(500)
        
        import json
        self._test_extreme_nesting_parse(nested, json, safe_json_parse)
    
    def _create_extremely_nested_structure(self, depth: int) -> dict:
        """Create extremely nested structure for testing"""
        nested = "value"
        for i in range(depth):  # Very deep nesting
            nested = {"level": nested}
        return nested
    
    def _test_extreme_nesting_parse(self, nested, json_module, safe_parse_func) -> None:
        """Test parsing of extremely nested structure"""
        try:
            nested_json = json_module.dumps(nested)
            result = safe_parse_func(nested_json)
            # If it succeeds, result should match
            assert isinstance(result, dict)
        except RecursionError:
            # This is acceptable for extreme nesting
            pass