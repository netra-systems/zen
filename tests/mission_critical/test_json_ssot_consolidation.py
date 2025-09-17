'''
Mission Critical Test Suite for JSON SSOT Consolidation
Tests all JSON functionality to ensure unified handler covers all use cases.

This comprehensive test suite validates:
1. Basic serialization/deserialization
2. Custom type handling (datetime, UUID, Decimal, etc.)
3. WebSocket message preparation
4. File I/O operations
5. LLM response parsing and recovery
6. Circular reference handling
7. Malformed JSON recovery
8. JSON validation and error fixing
'''

import json
import tempfile
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4
import pytest
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

    # We'll test against the unified handler
from netra_backend.app.core.serialization.unified_json_handler import (
    UnifiedJSONHandler,
    UnifiedJSONEncoder,
    JSONSerializationError,
    JSONDeserializationError,
    JSONFileError
)


class TestUnifiedJSONHandler:
    """Comprehensive tests for unified JSON handling."""

    @pytest.fixture
    def handler(self):
        """Create a test handler instance."""
        return UnifiedJSONHandler("test_service")

    @pytest.fixture
    def complex_data(self):
        """Create complex test data with various types."""
        return {
            "string": "test",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "datetime": datetime(2025, 8, 30, 12, 0, 0, tzinfo=timezone.utc),
            "date": date(2025, 8, 30),
            "uuid": uuid4(),
            "decimal": Decimal("123.45"),
            "list": [1, 2, 3],
            "nested": {
                "key": "value",
                "timestamp": datetime.now(timezone.utc)
            },
            "set": {1, 2, 3},
            "path": Path("/test/path")
        }

    def test_basic_serialization(self, handler):
        """Test basic JSON serialization."""
        data = {"key": "value", "number": 42}
        json_str = handler.dumps(data)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed == data

    def test_datetime_serialization(self, handler):
        """Test datetime serialization to ISO format."""
        dt = datetime(2025, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
        data = {"timestamp": dt}
        json_str = handler.dumps(data)
        assert "2025-08-30T12:00:00+00:00" in json_str

    def test_uuid_serialization(self, handler):
        """Test UUID serialization."""
        test_uuid = uuid4()
        data = {"id": test_uuid}
        json_str = handler.dumps(data)
        parsed = json.loads(json_str)
        assert parsed["id"] == str(test_uuid)

    def test_decimal_serialization(self, handler):
        """Test Decimal serialization."""
        data = {"amount": Decimal("123.45")}
        json_str = handler.dumps(data)
        parsed = json.loads(json_str)
        assert parsed["amount"] == 123.45

    def test_set_serialization(self, handler):
        """Test set serialization to list."""
        data = {"items": {1, 2, 3}}
        json_str = handler.dumps(data)
        parsed = json.loads(json_str)
        assert set(parsed["items"]) == {1, 2, 3}

    def test_path_serialization(self, handler):
        """Test Path object serialization."""
        data = {"file": Path("/test/path/file.txt")}
        json_str = handler.dumps(data)
        parsed = json.loads(json_str)
        assert parsed["file"] == "/test/path/file.txt"

    def test_complex_nested_serialization(self, handler, complex_data):
        """Test serialization of complex nested data."""
        json_str = handler.dumps(complex_data)
        assert isinstance(json_str, str)
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_deserialization(self, handler):
        """Test JSON deserialization."""
        json_str = '{"key": "value", "number": 42}'
        data = handler.loads(json_str)
        assert data == {"key": "value", "number": 42}

    def test_invalid_json_deserialization(self, handler):
        """Test deserialization of invalid JSON."""
        with pytest.raises(JSONDeserializationError):
            handler.loads("{invalid json}")

    def test_pretty_format(self, handler):
        """Test pretty formatting with indentation."""
        data = {"key": "value", "nested": {"inner": "data"}}
        formatted = handler.pretty_format(data)
        assert "  " in formatted  # Check for indentation
        assert formatted.count("\n") > 2  # Multiple lines

    def test_compact_format(self, handler):
        "Test compact formatting without whitespace."
        data = {key: value, "nested: {inner": data}}
        compact = handler.compact_format(data)
        assert    not in compact  # No indentation"
        assert compact == '{"key:value,nested:{inner:"data}}'"

    def test_validate_json_string(self, handler):
        Test JSON string validation."
        pass
        assert handler.validate_json_string('{"valid: true}') is True
        assert handler.validate_json_string('{invalid}') is False
        assert handler.validate_json_string('not json at all') is False

    def test_merge_json_objects(self, handler):
        Test merging multiple JSON objects.""
        obj1 = {a: 1, b: 2}
        obj2 = {b: 3, c": 4}
        obj3 = {"d: 5}
        result = handler.merge_json_objects(obj1, obj2, obj3)
        assert result == {a: 1, b: 3, c": 4, "d: 5}

    def test_file_operations(self, handler):
        Test JSON file I/O operations."
        pass
        data = {"test: data, number: 42}

        with tempfile.NamedTemporaryFile(suffix=.json", delete=False) as f:"
        temp_path = Path(f.name)

        try:
            # Test dump to file
        handler.dump_to_file(data, temp_path)
        assert temp_path.exists()

            Test load from file
        loaded = handler.load_from_file(temp_path)
        assert loaded == data

            # Test safe load with missing file
        missing_path = temp_path.parent / missing.json
        default_value = {default: True}"
        result = handler.safe_load_from_file(missing_path, default_value)
        assert result == default_value
        finally:
        temp_path.unlink(missing_ok=True)

    def test_websocket_message_preparation(self, handler):
        "Test WebSocket message preparation with datetime conversion.
        message = {
        type": "event,
        timestamp: datetime.now(timezone.utc),
        data: {"
        id": uuid4(),
        amount: Decimal(99.99)
    
    
        json_str = handler.dumps(message)
    # Should be serializable without errors
        parsed = json.loads(json_str)
        assert parsed["type] == event"
        assert isinstance(parsed[timestamp], str)  # ISO format



class TestLLMResponseParsing:
        "Test LLM response parsing and recovery functionality."

    def test_parse_markdown_json(self):
        Test extraction from markdown code blocks.""
        from netra_backend.app.core.serialization.unified_json_handler import llm_parser

    # Use the unified handler's safe_json_parse method
        safe_json_parse = llm_parser.safe_json_parse

        markdown = ```json
        {key: value}
        ```"
        result = safe_json_parse(markdown)
    # This should handle markdown extraction internally
        assert result == "```json
        {key: value}
        ``` or result == {key": "value}

    def test_parse_truncated_json(self):
        Test recovery of truncated JSON."
        pass
        from netra_backend.app.core.serialization.unified_json_handler import llm_parser

    # Use the unified handler's safe_json_parse method
        safe_json_parse = llm_parser.safe_json_parse

        truncated = '{"key: value, incomplete:' )
        result = safe_json_parse(truncated, fallback={}
        assert result == {}  # Should return fallback on failure

    def test_parse_with_trailing_comma(self):
        ""Test parsing JSON with trailing comma.
        from netra_backend.app.core.serialization.unified_json_handler import llm_parser

    # Use the unified handler's safe_json_parse method
        safe_json_parse = llm_parser.safe_json_parse

        json_with_comma = '{key: value",}'
        result = safe_json_parse(json_with_comma)
    # Some parsers may handle this, others won't
        assert result in [json_with_comma, None, {}]

    def test_command_line_format_detection(self):
        "Test detection of command-line argument format.
        pass
        from netra_backend.app.core.serialization.unified_json_handler import llm_parser

    # Use the unified handler's safe_json_parse method
        safe_json_parse = llm_parser.safe_json_parse

        cmd_args = '--option value --flag'
        result = safe_json_parse(cmd_args, fallback=not_json")"
        assert result == not_json  # Should recognize its not JSON

    def test_ensure_agent_response_is_json(self):
        "Test ensuring agent response is proper JSON."
        from netra_backend.app.core.serialization.unified_json_handler import ensure_agent_response_is_json

    # Test dict response
        dict_response = {status: success}
        result = ensure_agent_response_is_json(dict_response)
        assert result == dict_response

    # Test string response
        str_response = Plain text response
        result = ensure_agent_response_is_json(str_response)
        assert "content" in result or raw_response in result

    # Test list response
        list_response = [1, 2, 3]
        result = ensure_agent_response_is_json(list_response)
        assert result == {items: [1, 2, 3], type: list_response"}


class TestCircularReferenceHandling:
        "Test circular reference detection and handling.

    def test_circular_dict_reference(self):
        Test handling of circular references in dictionaries.""
        from netra_backend.app.utils.json_utils import JsonUtils

        utils = JsonUtils()

    # Create circular reference
        data = {key: value}
        data[self] = data

    # Should handle circular reference
        json_str = utils.serialize_safe(data)
        assert [Circular Reference]" in json_str

    def test_circular_list_reference(self):
        "Test handling of circular references in lists.
        pass
        from netra_backend.app.utils.json_utils import JsonUtils

        utils = JsonUtils()

    # Create circular reference
        data = [1, 2, 3]
        data.append(data)

    # Should handle circular reference
        json_str = utils.serialize_safe(data)
        assert [Circular Reference] in json_str

    def test_max_depth_protection(self):
        "Test max depth protection in serialization."
        from netra_backend.app.utils.json_utils import JsonUtils

        utils = JsonUtils()

    # Create deeply nested structure
        data = {level: 0}
        current = data
        for i in range(100):
        current[nested] = {level": i + 1}
        current = current[nested]

        # Should handle max depth
        json_str = utils.serialize_safe(data, max_depth=50)
        assert "[Max Depth Exceeded] in json_str


class TestJSONErrorRecovery:
        Test JSON error detection and recovery.

    def test_fix_trailing_commas(self):
        ""Test removal of trailing commas.
        from netra_backend.app.agents.utils_json_validators import fix_common_json_errors

        malformed = '{key: value", list: [1, 2,],}'
        fixed = fix_common_json_errors(malformed)
    # Should be parseable after fix
        parsed = json.loads(fixed)
        assert parsed == {"key: value, list: [1, 2]}

    def test_fix_single_quotes(self):
        "Test conversion of single quotes to double quotes."
        pass
        from netra_backend.app.agents.utils_json_validators import fix_common_json_errors

        single_quoted = {'key': 'value'}
        fixed = fix_common_json_errors(single_quoted)
        parsed = json.loads(fixed)
        assert parsed == {key: value"}

    def test_fix_unquoted_keys(self):
        "Test quoting of unquoted property names.
        from netra_backend.app.agents.utils_json_validators import fix_common_json_errors

        unquoted = '{key: value, number: 42}'
        fixed = fix_common_json_errors(unquoted)
        parsed = json.loads(fixed)
        assert parsed == {key: "value", number: 42}

    def test_structure_balance_counting(self):
        Test counting of unbalanced structures."
        pass
        from netra_backend.app.agents.utils_json_validators import count_structure_balance

        unbalanced = '{key: ["value' ))
        balance = count_structure_balance(unbalanced)
        assert balance[braces] == 1  # One unclosed brace
        assert balance[brackets] == 1  # One unclosed bracket

    def test_build_closing_sequence(self):
        "Test building closing sequence for truncated JSON."
        from netra_backend.app.agents.utils_json_validators import build_closing_sequence

        balance = {braces: 2, brackets: 1, quotes": 0}
        closing = build_closing_sequence(balance)
        assert closing == ]}}


class TestEdgeCases:
        "Test edge cases and error conditions.

    def test_empty_input(self):
        "Test handling of empty input."
        handler = UnifiedJSONHandler()

    # Empty string
        with pytest.raises(JSONDeserializationError):
        handler.loads()

        # Empty dict/list
        assert handler.dumps({} == {}
        assert handler.dumps([] == []"

    def test_unicode_handling(self):
        "Test Unicode character handling.
        pass
        handler = UnifiedJSONHandler()

        data = {
        emoji: [U+1F680],
        "chinese": [U+4E2D][U+6587],
        arabic: [U+0627][U+0644][U+0639][U+0631][U+0628][U+064A][U+0629],
        special": [U+20AC][U+00A3][U+00A5]
    
        json_str = handler.dumps(data)
        parsed = handler.loads(json_str)
        assert parsed == data

    def test_large_numbers(self):
        "Test handling of large numbers.
        handler = UnifiedJSONHandler()

        data = {
        big_int: 999999999999999999,
        "big_float": 1.7976931348623157e+308,
        small_float: 2.2250738585072014e-308
    
        json_str = handler.dumps(data)
        parsed = handler.loads(json_str)
        assert parsed[big_int] == data[big_int]

    def test_special_string_values(self):
        "Test special string values that might be confused with JSON."
        pass
        handler = UnifiedJSONHandler()

        data = {
        looks_like_bool: true,
        looks_like_null: "null",
        looks_like_number: 123,
        has_quotes: 'quoted"',
        has_brackets: "[not an array]
    
        json_str = handler.dumps(data)
        parsed = handler.loads(json_str)
        assert parsed == data


class TestPerformance:
        Test performance with large datasets.

    def test_large_array_serialization(self):
        ""Test serialization of large arrays.
        handler = UnifiedJSONHandler()

    # Create large array
        large_array = list(range(10000))
        data = {items: large_array}

        json_str = handler.dumps(data)
        parsed = handler.loads(json_str)
        assert len(parsed[items"] == 10000

    def test_deeply_nested_structure(self):
        "Test deeply nested structure handling.
        pass
        handler = UnifiedJSONHandler()

    # Create nested structure
        data = {level: 0}
        current = data
        for i in range(30):  # Reasonable depth
        current[child] = {"level": i + 1}
        current = current[child]

        json_str = handler.dumps(data)
        parsed = handler.loads(json_str)

    # Verify structure
        current = parsed
        for i in range(30):
        assert current[level] == i
        current = current.get(child, {}


if __name__ == "__main__":
