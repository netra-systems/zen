"""Test fallback response factory handles different response types correctly."""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.llm.fallback_responses import FallbackResponseFactory

class FallbackResponseFactoryTests:
    """Test fallback response factory behavior."""
    
    @pytest.fixture
    def factory(self):
        """Create factory instance."""
        return FallbackResponseFactory()
    
    def test_general_fallback_returns_string(self, factory):
        """Test general fallback returns string without error."""
        response = factory.create_response("general")
        assert isinstance(response, str)
        assert response == factory.DEFAULT_GENERAL_MESSAGE
    
    def test_general_fallback_with_error(self, factory):
        """Test general fallback with error doesn't crash."""
        error = Exception("Test error")
        response = factory.create_response("general", error)
        assert isinstance(response, str)
        assert response == factory.DEFAULT_GENERAL_MESSAGE
    
    def test_triage_fallback_returns_dict(self, factory):
        """Test triage fallback returns dict."""
        response = factory.create_response("triage")
        assert isinstance(response, dict)
        assert "metadata" in response
    
    def test_triage_fallback_with_error(self, factory):
        """Test triage fallback with error adds metadata."""
        error = Exception("Test error")
        response = factory.create_response("triage", error)
        assert isinstance(response, dict)
        assert "metadata" in response
        assert response["metadata"]["error"] == "Test error"
    
    def test_data_analysis_fallback_returns_dict(self, factory):
        """Test data_analysis fallback returns dict."""
        response = factory.create_response("data_analysis")
        assert isinstance(response, dict)
        assert "metadata" in response
    
    def test_data_analysis_fallback_with_error(self, factory):
        """Test data_analysis fallback with error adds metadata."""
        error = Exception("Analysis failed")
        response = factory.create_response("data_analysis", error)
        assert isinstance(response, dict)
        assert "metadata" in response
        assert response["metadata"]["error"] == "Analysis failed"
    
    def test_unknown_fallback_type(self, factory):
        """Test unknown fallback type defaults to general."""
        response = factory.create_response("unknown_type")
        assert response == factory.DEFAULT_GENERAL_MESSAGE
    
    def test_dict_response_is_copied(self, factory):
        """Test dict responses are copied to prevent mutation."""
        response1 = factory.create_response("triage")
        response2 = factory.create_response("triage")
        # Modifying one shouldn't affect the other
        response1["test_key"] = "test_value"
        assert "test_key" not in response2
    
    def test_enhance_response_handles_mixed_types(self, factory):
        """Test _enhance_response_with_error handles both string and dict."""
        error = Exception("Mixed type test")
        
        # Test with string response (general)
        string_response = factory._enhance_response_with_error("general", error)
        assert isinstance(string_response, str)
        
        # Test with dict response (triage)
        dict_response = factory._enhance_response_with_error("triage", error)
        assert isinstance(dict_response, dict)
        assert dict_response["metadata"]["error"] == "Mixed type test"