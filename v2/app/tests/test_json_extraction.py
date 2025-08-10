"""Test JSON extraction utility improvements."""

import pytest
from app.agents.utils import extract_json_from_response, fix_common_json_errors


class TestJSONExtraction:
    """Test cases for improved JSON extraction."""
    
    def test_extract_valid_json(self):
        """Test extraction of valid JSON."""
        response = '{"key": "value", "number": 123}'
        result = extract_json_from_response(response)
        assert result == {"key": "value", "number": 123}
    
    def test_extract_json_from_markdown(self):
        """Test extraction from markdown code blocks."""
        response = '''
        Here's the JSON response:
        ```json
        {
            "action_plan_summary": "Test plan",
            "actions": []
        }
        ```
        '''
        result = extract_json_from_response(response)
        assert result == {"action_plan_summary": "Test plan", "actions": []}
    
    def test_extract_json_with_text_before_after(self):
        """Test extraction when JSON has explanatory text."""
        response = '''
        Based on the analysis, here's the action plan:
        {
            "action_plan_summary": "Optimization plan",
            "total_estimated_time": "2 hours",
            "actions": [
                {"action_id": "1", "name": "Update config"}
            ]
        }
        This plan will improve performance by 20%.
        '''
        result = extract_json_from_response(response)
        assert result is not None
        assert result["action_plan_summary"] == "Optimization plan"
        assert len(result["actions"]) == 1
    
    def test_extract_json_with_trailing_comma(self):
        """Test extraction with trailing comma (common LLM error)."""
        response = '''
        {
            "key1": "value1",
            "key2": "value2",
        }
        '''
        result = extract_json_from_response(response)
        assert result == {"key1": "value1", "key2": "value2"}
    
    def test_extract_json_with_single_quotes(self):
        """Test extraction with single quotes instead of double."""
        response = "{'key': 'value', 'number': 42}"
        result = extract_json_from_response(response)
        assert result == {"key": "value", "number": 42}
    
    def test_extract_json_array(self):
        """Test extraction of JSON array."""
        response = '[{"id": 1}, {"id": 2}]'
        result = extract_json_from_response(response)
        assert result == [{"id": 1}, {"id": 2}]
    
    def test_extract_nested_json(self):
        """Test extraction of deeply nested JSON."""
        response = '''
        {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }
        '''
        result = extract_json_from_response(response)
        assert result["level1"]["level2"]["level3"]["value"] == "deep"
    
    def test_extract_json_with_comments(self):
        """Test extraction with JSON comments (non-standard but common)."""
        response = '''
        {
            // This is a comment
            "key": "value",
            /* Multi-line
               comment */
            "number": 123
        }
        '''
        result = extract_json_from_response(response)
        assert result == {"key": "value", "number": 123}
    
    def test_extract_malformed_json_returns_none(self):
        """Test that completely malformed JSON returns None."""
        response = "This is not JSON at all"
        result = extract_json_from_response(response)
        assert result is None
    
    def test_extract_empty_response_returns_none(self):
        """Test that empty response returns None."""
        result = extract_json_from_response("")
        assert result is None
        result = extract_json_from_response(None)
        assert result is None
    
    def test_fix_common_json_errors(self):
        """Test the fix_common_json_errors helper function."""
        # Test trailing comma fix
        json_str = '{"key": "value",}'
        fixed = fix_common_json_errors(json_str)
        assert fixed == '{"key": "value"}'
        
        # Test unquoted property names
        json_str = '{key: "value", number: 123}'
        fixed = fix_common_json_errors(json_str)
        assert '"key"' in fixed and '"number"' in fixed
        
        # Test comment removal
        json_str = '{"key": "value" // comment\n}'
        fixed = fix_common_json_errors(json_str)
        assert '//' not in fixed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])