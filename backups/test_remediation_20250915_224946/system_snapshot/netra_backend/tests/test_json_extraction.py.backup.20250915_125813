"""Test JSON extraction utility improvements."""
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment
import pytest
from netra_backend.app.agents.utils import extract_json_from_response, extract_partial_json, fix_common_json_errors, recover_truncated_json

class TestJSONExtraction:
    """Test cases for improved JSON extraction."""

    def test_extract_valid_json(self):
        """Test extraction of valid JSON."""
        response = '{"key": "value", "number": 123}'
        result = llm_parser.extract_json_from_response(response)
        assert result == {'key': 'value', 'number': 123}

    def test_extract_json_from_markdown(self):
        """Test extraction from markdown code blocks."""
        response = '\n        Here\'s the JSON response:\n        ```json\n        {\n            "action_plan_summary": "Test plan",\n            "actions": []\n        }\n        ```\n        '
        result = llm_parser.extract_json_from_response(response)
        assert result == {'action_plan_summary': 'Test plan', 'actions': []}

    def test_extract_json_with_text_before_after(self):
        """Test extraction when JSON has explanatory text."""
        response = '\n        Based on the analysis, here\'s the action plan:\n        {\n            "action_plan_summary": "Optimization plan",\n            "total_estimated_time": "2 hours",\n            "actions": [\n                {"action_id": "1", "name": "Update config"}\n            ]\n        }\n        This plan will improve performance by 20%.\n        '
        result = llm_parser.extract_json_from_response(response)
        assert result != None
        assert result['action_plan_summary'] == 'Optimization plan'
        assert len(result['actions']) == 1

    def test_extract_json_with_trailing_comma(self):
        """Test extraction with trailing comma (common LLM error)."""
        response = '\n        {\n            "key1": "value1",\n            "key2": "value2",\n        }\n        '
        result = llm_parser.extract_json_from_response(response)
        assert result == {'key1': 'value1', 'key2': 'value2'}

    def test_extract_json_with_single_quotes(self):
        """Test extraction with single quotes instead of double."""
        response = "{'key': 'value', 'number': 42}"
        result = llm_parser.extract_json_from_response(response)
        assert result == {'key': 'value', 'number': 42}

    def test_extract_json_array(self):
        """Test extraction of JSON array."""
        response = '[{"id": 1}, {"id": 2}]'
        result = llm_parser.extract_json_from_response(response)
        assert result == [{'id': 1}, {'id': 2}]

    def test_extract_nested_json(self):
        """Test extraction of deeply nested JSON."""
        response = '\n        {\n            "level1": {\n                "level2": {\n                    "level3": {\n                        "value": "deep"\n                    }\n                }\n            }\n        }\n        '
        result = llm_parser.extract_json_from_response(response)
        assert result['level1']['level2']['level3']['value'] == 'deep'

    def test_extract_json_with_comments(self):
        """Test extraction with JSON comments (non-standard but common)."""
        response = '\n        {\n            // This is a comment\n            "key": "value",\n            /* Multi-line\n               comment */\n            "number": 123\n        }\n        '
        result = llm_parser.extract_json_from_response(response)
        assert result == {'key': 'value', 'number': 123}

    def test_extract_malformed_json_returns_none(self):
        """Test that completely malformed JSON returns None."""
        response = 'This is not JSON at all'
        result = llm_parser.extract_json_from_response(response)
        assert result == None

    def test_extract_empty_response_returns_none(self):
        """Test that empty response returns None."""
        result = llm_parser.extract_json_from_response('')
        assert result == None
        result = llm_parser.extract_json_from_response(None)
        assert result == None

    def test_fix_common_json_errors(self):
        """Test the fix_common_json_errors helper function."""
        json_str = '{"key": "value",}'
        fixed = fix_common_json_errors(json_str)
        assert fixed == '{"key": "value"}'
        json_str = '{key: "value", number: 123}'
        fixed = fix_common_json_errors(json_str)
        assert '"key"' in fixed and '"number"' in fixed
        json_str = '{"key": "value" // comment\n}'
        fixed = fix_common_json_errors(json_str)
        assert '//' not in fixed

class TestTruncatedJSONRecovery:
    """Test cases for truncated JSON recovery functionality."""

    def test_recover_complete_json(self):
        """Test that complete JSON is returned as-is."""
        json_str = '{"complete": true, "value": 123}'
        result = error_fixer.recover_truncated_json(json_str)
        assert result == {'complete': True, 'value': 123}

    def test_recover_missing_closing_brace(self):
        """Test recovery when closing brace is missing."""
        json_str = '{"action_plan_summary": "Test plan", "actions": []'
        result = error_fixer.recover_truncated_json(json_str)
        assert result != None
        assert result['action_plan_summary'] == 'Test plan'
        assert result['actions'] == []

    def test_recover_nested_missing_braces(self):
        """Test recovery with nested structures missing closing."""
        json_str = '{"outer": {"inner": {"value": "test"'
        result = error_fixer.recover_truncated_json(json_str)
        assert result != None
        assert result['outer']['inner']['value'] == 'test'

    def test_recover_array_missing_bracket(self):
        """Test recovery when array closing bracket is missing."""
        json_str = '{"items": [{"id": 1}, {"id": 2}'
        result = error_fixer.recover_truncated_json(json_str)
        assert result != None
        assert len(result['items']) == 2
        assert result['items'][0]['id'] == 1

    def test_recover_incomplete_string_value(self):
        """Test recovery when string value is incomplete."""
        json_str = '{"action_plan_summary": "This is an incomplete'
        result = error_fixer.recover_truncated_json(json_str)
        assert result != None
        assert 'action_plan_summary' in result

    def test_recover_with_trailing_comma(self):
        """Test recovery with trailing comma and missing closing."""
        json_str = '{"key1": "value1", "key2": "value2",'
        result = error_fixer.recover_truncated_json(json_str)
        assert result != None
        assert result['key1'] == 'value1'
        assert result['key2'] == 'value2'

    def test_recover_deeply_truncated(self):
        """Test recovery when JSON is severely truncated."""
        json_str = '{"action_plan_summary": "Test", "total_estimated_time": "2 hours", "actions": [{"id'
        result = error_fixer.recover_truncated_json(json_str, max_retries=5)
        assert result != None
        assert 'action_plan_summary' in result
        assert result['action_plan_summary'] == 'Test'

    def test_recover_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = error_fixer.recover_truncated_json('')
        assert result == None
        result = error_fixer.recover_truncated_json(None)
        assert result == None

class TestPartialJSONExtraction:
    """Test cases for partial JSON extraction functionality."""

    def test_extract_partial_basic(self):
        """Test basic partial extraction."""
        response = '\n        Some text before\n        "action_plan_summary": "Test plan",\n        "total_estimated_time": "2 hours",\n        "required_approvals": ["manager", "security"]\n        Some text after\n        '
        result = llm_parser.extract_partial_json(response)
        assert result != None
        assert result['action_plan_summary'] == 'Test plan'
        assert result['total_estimated_time'] == '2 hours'

    def test_extract_partial_with_required_fields(self):
        """Test partial extraction with required fields."""
        response = '\n        "field1": "value1",\n        "field2": "value2",\n        "field3": "value3"\n        '
        result = llm_parser.extract_partial_json(response, required_fields=['field1', 'field2'])
        assert result != None
        assert result['field1'] == 'value1'
        assert result['field2'] == 'value2'

    def test_extract_partial_missing_required_fields(self):
        """Test that None is returned when required fields are missing."""
        response = '\n        "field1": "value1",\n        "field3": "value3"\n        '
        result = llm_parser.extract_partial_json(response, required_fields=['field1', 'field2'])
        assert result == None

    def test_extract_partial_numeric_values(self):
        """Test extraction of numeric values."""
        response = '\n        "effort_hours": 10,\n        "cost": 1500.50,\n        "percentage": 85\n        '
        result = llm_parser.extract_partial_json(response)
        assert result != None
        assert result['effort_hours'] == 10
        assert result['cost'] == 1500.5
        assert result['percentage'] == 85

    def test_extract_partial_boolean_values(self):
        """Test extraction of boolean values."""
        response = '\n        "is_active": true,\n        "has_errors": false,\n        "completed": true\n        '
        result = llm_parser.extract_partial_json(response)
        assert result != None
        assert result['is_active'] == True
        assert result['has_errors'] == False

    def test_extract_partial_from_truncated_response(self):
        """Test extraction from a truncated LLM response."""
        response = '```json\n{\n    "action_plan_summary": "A phased action plan focused first on resolving the critical \'NO_COMMON_TYPE\' error in the ClickHouse analytics database",\n    "total_estimated_time": "13-20 business days",\n    "required_approvals": [\n        "Database Administrator approval for schema changes",\n        "Security team review for data handling modifications"'
        result = llm_parser.extract_partial_json(response)
        assert result != None
        assert 'action_plan_summary' in result
        assert 'total_estimated_time' in result
        assert result['total_estimated_time'] == '13-20 business days'

    def test_extract_partial_empty_response(self):
        """Test that empty response returns None."""
        result = llm_parser.extract_partial_json('')
        assert result == None
        result = llm_parser.extract_partial_json(None)
        assert result == None

class TestLargeResponseHandling:
    """Test cases for handling large JSON responses."""

    def test_extract_from_large_response(self):
        """Test extraction from a large response (similar to the error case)."""
        large_response = '{"action_plan_summary": "' + 'x' * 15000 + '", "actions": []}'
        result = llm_parser.extract_json_from_response(large_response, max_retries=5)
        assert result != None
        assert len(result['action_plan_summary']) == 15000
        assert result['actions'] == []

    def test_handle_truncated_large_response(self):
        """Test handling of truncated large response."""
        truncated_response = '```json\n{\n    "action_plan_summary": "A phased action plan focused first on resolving the critical \'NO_COMMON_TYPE\' error in the ClickHouse analytics database. Once data integrity is restored and a performance baseline is established, the plan proceeds with implementing a semantic caching layer and a performance-based smart routing strategy to achieve the user\'s goal of a 3x latency reduction with cost neutrality.",\n    "total_estimated_time": "13-20 business days",\n    "required_approvals": [' + ' ' * 19000
        result = llm_parser.extract_json_from_response(truncated_response, max_retries=5)
        if result == None:
            result = llm_parser.extract_partial_json(truncated_response)
        assert result != None
        assert 'action_plan_summary' in result
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')