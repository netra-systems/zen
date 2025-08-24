"""
Data validation tests for SupplyResearchService
Tests comprehensive data validation logic and boundary conditions
"""

import sys
from pathlib import Path

from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from netra_backend.app.services.supply_research_service import SupplyResearchService

@pytest.fixture
def service(db_session):
    """Create SupplyResearchService instance with real database"""
    return SupplyResearchService(db_session)

class TestDataValidation:
    """Test comprehensive data validation logic"""
    
    def test_validate_supply_data_valid_complete(self, service):
        """Test validation with complete valid data"""
        valid_data: Dict[str, Any] = self._create_valid_supply_data()
        
        is_valid, errors = service.validate_supply_data(valid_data)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_supply_data_missing_required_fields(self, service):
        """Test validation with missing critical fields"""
        incomplete_data: Dict[str, Any] = {
            "pricing_input": "0.03"  # Missing provider and model_name
        }
        
        is_valid, errors = service.validate_supply_data(incomplete_data)
        
        assert is_valid is False
        assert len(errors) >= 2
        self._verify_missing_field_errors(errors)
    
    def test_validate_supply_data_negative_pricing(self, service):
        """Test validation with negative pricing values"""
        invalid_data: Dict[str, Any] = self._create_negative_pricing_data()
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        
        assert is_valid is False
        self._verify_negative_pricing_errors(errors)
    
    def test_validate_supply_data_unrealistic_high_pricing(self, service):
        """Test validation with unrealistically high pricing"""
        unrealistic_data: Dict[str, Any] = self._create_unrealistic_pricing_data()
        
        is_valid, errors = service.validate_supply_data(unrealistic_data)
        
        assert is_valid is False
        assert any("pricing seems unrealistically high" in error for error in errors)
    
    def test_validate_supply_data_invalid_formats(self, service):
        """Test validation with invalid data formats"""
        malformed_data: Dict[str, Any] = self._create_malformed_data()
        
        is_valid, errors = service.validate_supply_data(malformed_data)
        
        assert is_valid is False
        self._verify_format_errors(errors)
    
    def test_validate_supply_data_boundary_values(self, service):
        """Test validation with boundary values"""
        boundary_data: Dict[str, Any] = self._create_boundary_data()
        
        is_valid, errors = service.validate_supply_data(boundary_data)
        
        assert is_valid is False
        self._verify_boundary_errors(errors)
    
    def test_validate_all_valid_availability_statuses(self, service):
        """Test all valid availability status values"""
        valid_statuses = ["available", "deprecated", "preview", "waitlist"]
        
        for status in valid_statuses:
            data: Dict[str, Any] = self._create_status_data(status)
            
            is_valid, errors = service.validate_supply_data(data)
            assert is_valid is True, f"Status '{status}' should be valid but got errors: {errors}"
    
    def test_validate_context_window_edge_cases(self, service):
        """Test context window validation edge cases"""
        test_cases = [
            {"context_window": 0, "should_be_valid": True},       # Zero is valid
            {"context_window": 1, "should_be_valid": True},       # Small value
            {"context_window": 1000000, "should_be_valid": True}, # Large but reasonable
            {"context_window": 50000000, "should_be_valid": False} # Too large
        ]
        
        for case in test_cases:
            data = self._create_base_data()
            data.update({"context_window": case["context_window"]})
            
            is_valid, errors = service.validate_supply_data(data)
            
            if case["should_be_valid"]:
                assert is_valid, f"Context window {case['context_window']} should be valid"
            else:
                assert not is_valid, f"Context window {case['context_window']} should be invalid"
    
    def test_validate_confidence_score_edge_cases(self, service):
        """Test confidence score validation edge cases"""
        test_cases = [
            {"confidence_score": 0.0, "should_be_valid": True},   # Minimum valid
            {"confidence_score": 1.0, "should_be_valid": True},   # Maximum valid
            {"confidence_score": 0.5, "should_be_valid": True},   # Middle range
            {"confidence_score": -0.1, "should_be_valid": False}, # Too low
            {"confidence_score": 1.1, "should_be_valid": False}   # Too high
        ]
        
        for case in test_cases:
            data = self._create_base_data()
            data.update({"confidence_score": case["confidence_score"]})
            
            is_valid, errors = service.validate_supply_data(data)
            
            if case["should_be_valid"]:
                assert is_valid, f"Confidence {case['confidence_score']} should be valid"
            else:
                assert not is_valid, f"Confidence {case['confidence_score']} should be invalid"
    
    def _create_valid_supply_data(self) -> Dict[str, Any]:
        """Helper to create valid supply data"""
        return {
            "provider": "openai",
            "model_name": "gpt-4",
            "pricing_input": "0.03",
            "pricing_output": "0.06",
            "context_window": 8192,
            "confidence_score": 0.9,
            "availability_status": "available"
        }
    
    def _create_base_data(self) -> Dict[str, Any]:
        """Helper to create base valid data for edge case testing"""
        return {
            "provider": "openai",
            "model_name": "gpt-4"
        }
    
    def _create_negative_pricing_data(self) -> Dict[str, Any]:
        """Helper to create data with negative pricing"""
        return {
            "provider": "openai",
            "model_name": "gpt-4",
            "pricing_input": "-0.03",
            "pricing_output": "-0.06"
        }
    
    def _create_unrealistic_pricing_data(self) -> Dict[str, Any]:
        """Helper to create data with unrealistic pricing"""
        return {
            "provider": "openai",
            "model_name": "gpt-4",
            "pricing_input": "15000",  # Extremely high
            "pricing_output": "20000"
        }
    
    def _create_malformed_data(self) -> Dict[str, Any]:
        """Helper to create malformed data"""
        return {
            "provider": "openai",
            "model_name": "gpt-4",
            "pricing_input": "not-a-number",
            "context_window": "also-not-a-number",
            "confidence_score": "invalid-score"
        }
    
    def _create_boundary_data(self) -> Dict[str, Any]:
        """Helper to create boundary value data"""
        return {
            "provider": "openai",
            "model_name": "gpt-4",
            "context_window": -1000,  # Negative
            "confidence_score": 1.5,   # Out of range
            "availability_status": "invalid_status"
        }
    
    def _create_status_data(self, status: str) -> Dict[str, Any]:
        """Helper to create data with specific status"""
        return {
            "provider": "openai",
            "model_name": "gpt-4",
            "availability_status": status
        }
    
    def _verify_missing_field_errors(self, errors: List[str]):
        """Helper to verify missing field errors"""
        assert any("Missing required field: provider" in error for error in errors)
        assert any("Missing required field: model_name" in error for error in errors)
    
    def _verify_negative_pricing_errors(self, errors: List[str]):
        """Helper to verify negative pricing errors"""
        assert any("Input pricing cannot be negative" in error for error in errors)
        assert any("Output pricing cannot be negative" in error for error in errors)
    
    def _verify_format_errors(self, errors: List[str]):
        """Helper to verify format errors"""
        assert any("Invalid input pricing format" in error for error in errors)
        assert any("Invalid context window format" in error for error in errors)
        assert any("Invalid confidence score format" in error for error in errors)
    
    def _verify_boundary_errors(self, errors: List[str]):
        """Helper to verify boundary value errors"""
        assert any("Context window cannot be negative" in error for error in errors)
        assert any("Confidence score must be between 0 and 1" in error for error in errors)
        assert any("Invalid availability status" in error for error in errors)

class TestValidationHelpers:
    """Test validation helper methods"""
    
    def test_pricing_format_validation(self, service):
        """Test pricing format validation specifically"""
        valid_formats = ["0.03", "0", "100.50", "0.001"]
        invalid_formats = ["abc", "", "0.03.05", "not-a-number", None]
        
        base_data = {"provider": "openai", "model_name": "gpt-4"}
        
        for valid_price in valid_formats:
            data = {**base_data, "pricing_input": valid_price}
            is_valid, errors = service.validate_supply_data(data)
            pricing_errors = [e for e in errors if "Invalid input pricing format" in e]
            assert len(pricing_errors) == 0, f"Price '{valid_price}' should be valid format"
        
        for invalid_price in invalid_formats:
            data = {**base_data, "pricing_input": invalid_price}
            is_valid, errors = service.validate_supply_data(data)
            pricing_errors = [e for e in errors if "Invalid input pricing format" in e]
            if invalid_price is not None:  # None is handled differently (missing field)
                assert len(pricing_errors) > 0, f"Price '{invalid_price}' should be invalid format"
    
    def test_provider_name_validation(self, service):
        """Test provider name validation"""
        valid_providers = ["openai", "anthropic", "google", "mistral", "cohere"]
        
        for provider in valid_providers:
            data = {"provider": provider, "model_name": "test-model"}
            is_valid, errors = service.validate_supply_data(data)
            
            # Provider name itself should be valid (other validation may fail)
            provider_errors = [e for e in errors if "Invalid provider" in e]
            assert len(provider_errors) == 0, f"Provider '{provider}' should be valid"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])