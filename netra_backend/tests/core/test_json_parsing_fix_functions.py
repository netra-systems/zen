"""
Tests for JSON fix utility functions.
All functions ≤8 lines per requirements.
"""

import pytest
from unittest.mock import patch
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.core.json_parsing_utils import (

# Add project root to path
    fix_tool_parameters,
    fix_list_recommendations,
    comprehensive_json_fix
)


class TestFixToolParameters:
    """Test the fix_tool_parameters function."""
    
    def test_fix_valid_tool_params_dict(self):
        """Test fixing valid tool parameters dict."""
        params = {"param1": "value1", "param2": 42}
        result = fix_tool_parameters(params)
        assert result == params
    
    def test_fix_tool_params_string(self):
        """Test fixing tool parameters from string."""
        params_str = '{"param1": "value1", "param2": 42}'
        result = fix_tool_parameters(params_str)
        expected = {"param1": "value1", "param2": 42}
        assert result == expected
    
    def test_fix_tool_params_list_of_dicts(self):
        """Test fixing tool parameters from list of dicts."""
        params_list = [{"param1": "value1"}, {"param2": "value2"}]
        result = fix_tool_parameters(params_list)
        expected = {"param1": "value1", "param2": "value2"}
        assert result == expected
    
    def test_fix_tool_params_invalid_input(self):
        """Test fixing invalid tool parameters input."""
        invalid_params = "invalid params"
        result = fix_tool_parameters(invalid_params)
        assert result == {}
    
    def test_fix_tool_params_none_input(self):
        """Test fixing None tool parameters."""
        result = fix_tool_parameters(None)
        assert result == {}
    
    def test_fix_tool_params_empty_string(self):
        """Test fixing empty string tool parameters."""
        result = fix_tool_parameters('')
        assert result == {}
    
    def test_fix_tool_params_empty_list(self):
        """Test fixing empty list tool parameters."""
        result = fix_tool_parameters([])
        assert result == {}
    
    def test_fix_tool_params_nested_structure(self):
        """Test fixing nested tool parameters structure."""
        params = {"config": {"nested": "value"}, "simple": "param"}
        result = fix_tool_parameters(params)
        assert result == params
    
    def test_fix_tool_params_list_with_invalid_items(self):
        """Test fixing list with some invalid items."""
        params_list = [{"valid": "param"}, "invalid_item", {"another": "param"}]
        result = fix_tool_parameters(params_list)
        expected = {"valid": "param", "another": "param"}
        assert result == expected
    
    def test_fix_tool_params_string_representation_of_dict(self):
        """Test fixing string that looks like dict but isn't valid JSON."""
        params_str = '{param1: value1, param2: value2}'  # No quotes
        result = fix_tool_parameters(params_str)
        assert result == {}


class TestFixListRecommendations:
    """Test the fix_list_recommendations function."""
    
    def test_fix_valid_recommendations_list(self):
        """Test fixing valid recommendations list."""
        recommendations = ["rec1", "rec2", "rec3"]
        result = fix_list_recommendations(recommendations)
        assert result == recommendations
    
    def test_fix_recommendations_string(self):
        """Test fixing recommendations from string."""
        rec_str = '["rec1", "rec2", "rec3"]'
        result = fix_list_recommendations(rec_str)
        expected = ["rec1", "rec2", "rec3"]
        assert result == expected
    
    def test_fix_recommendations_mixed_types(self):
        """Test fixing recommendations with mixed types."""
        rec_mixed = '["rec1", 42, "rec2", true, "rec3"]'
        result = fix_list_recommendations(rec_mixed)
        expected = ["rec1", "rec2", "rec3"]
        assert result == expected
    
    def test_fix_recommendations_dict_values(self):
        """Test fixing recommendations from dict values."""
        rec_dict = {"item1": "rec1", "item2": "rec2", "item3": 42}
        result = fix_list_recommendations(rec_dict)
        expected = ["rec1", "rec2"]
        assert result == expected
    
    def test_fix_recommendations_invalid_input(self):
        """Test fixing invalid recommendations input."""
        invalid_rec = "invalid recommendations"
        result = fix_list_recommendations(invalid_rec)
        assert result == []
    
    def test_fix_recommendations_none_input(self):
        """Test fixing None recommendations."""
        result = fix_list_recommendations(None)
        assert result == []
    
    def test_fix_recommendations_empty_input(self):
        """Test fixing empty recommendations."""
        result = fix_list_recommendations([])
        assert result == []
    
    def test_fix_recommendations_single_string(self):
        """Test fixing single string as recommendations."""
        rec_str = "single_recommendation"
        result = fix_list_recommendations(rec_str)
        expected = ["single_recommendation"]
        assert result == expected


class TestComprehensiveJsonFix:
    """Test the comprehensive_json_fix function."""
    
    def test_fix_complete_valid_data(self):
        """Test fixing complete valid data."""
        data = {
            "tool_parameters": {"param1": "value1"},
            "list_recommendations": ["rec1", "rec2"]
        }
        result = comprehensive_json_fix(data)
        assert result == data
    
    def test_fix_data_with_string_fields(self):
        """Test fixing data with string JSON fields."""
        data = {
            "tool_parameters": '{"param1": "value1", "param2": 42}',
            "list_recommendations": '["rec1", "rec2", "rec3"]'
        }
        result = comprehensive_json_fix(data)
        expected = {
            "tool_parameters": {"param1": "value1", "param2": 42},
            "list_recommendations": ["rec1", "rec2", "rec3"]
        }
        assert result == expected
    
    def test_fix_data_with_missing_fields(self):
        """Test fixing data with missing fields."""
        data = {"other_field": "value"}
        result = comprehensive_json_fix(data)
        expected = {
            "other_field": "value",
            "tool_parameters": {},
            "list_recommendations": []
        }
        assert result == expected
    
    def test_fix_empty_data(self):
        """Test fixing empty data."""
        data = {}
        result = comprehensive_json_fix(data)
        expected = {
            "tool_parameters": {},
            "list_recommendations": []
        }
        assert result == expected
    
    def test_fix_none_data(self):
        """Test fixing None data."""
        result = comprehensive_json_fix(None)
        expected = {
            "tool_parameters": {},
            "list_recommendations": []
        }
        assert result == expected
    
    def test_fix_data_with_invalid_fields(self):
        """Test fixing data with invalid field values."""
        data = {
            "tool_parameters": "invalid json",
            "list_recommendations": "invalid list",
            "other_field": "preserved"
        }
        result = comprehensive_json_fix(data)
        expected = {
            "tool_parameters": {},
            "list_recommendations": [],
            "other_field": "preserved"
        }
        assert result == expected
    
    def test_fix_data_preserves_other_fields(self):
        """Test that comprehensive fix preserves other fields."""
        data = {
            "tool_parameters": '{"param": "value"}',
            "list_recommendations": '["rec1"]',
            "preserved_field": "should_remain",
            "another_field": {"nested": "data"}
        }
        result = comprehensive_json_fix(data)
        
        assert result["preserved_field"] == "should_remain"
        assert result["another_field"] == {"nested": "data"}
        assert result["tool_parameters"] == {"param": "value"}
        assert result["list_recommendations"] == ["rec1"]
    
    def test_fix_data_with_nested_structures(self):
        """Test fixing data with nested structures."""
        data = {
            "tool_parameters": {
                "config": {"nested": "value"},
                "simple": "param"
            },
            "list_recommendations": [
                "rec1",
                "rec2"
            ]
        }
        result = comprehensive_json_fix(data)
        assert result == data
    
    def test_fix_data_logging_behavior(self):
        """Test that comprehensive fix logs appropriately."""
        data = {
            "tool_parameters": "invalid json",
            "list_recommendations": "invalid list"
        }
        
        with patch('app.core.json_parsing_utils.logger') as mock_logger:
            result = comprehensive_json_fix(data)
            
            # Should log warnings for invalid fields
            assert mock_logger.warning.call_count >= 1