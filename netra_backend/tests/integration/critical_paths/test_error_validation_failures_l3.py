"""
L3 Integration Test: Validation Error Handling
Tests error handling for validation failures
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from unittest.mock import patch, AsyncMock

# Add project root to path

from netra_backend.app.services.validation_service import ValidationService
from netra_backend.app.config import settings
import json

# Add project root to path


class TestErrorValidationFailuresL3:
    """Test validation error handling scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_schema_validation_failure(self):
        """Test handling of schema validation failures"""
        validator = ValidationService()
        
        invalid_data = {
            "name": 123,  # Should be string
            "age": "twenty",  # Should be number
            "email": "not-an-email"  # Invalid format
        }
        
        result = await validator.validate_user_data(invalid_data)
        
        assert result.is_valid is False
        assert len(result.errors) >= 3
        assert any("name" in str(e) for e in result.errors)
        assert any("age" in str(e) for e in result.errors)
        assert any("email" in str(e) for e in result.errors)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_business_rule_validation_failure(self):
        """Test handling of business rule violations"""
        validator = ValidationService()
        
        data = {
            "quantity": -5,  # Negative quantity
            "price": 0,  # Zero price
            "discount": 150  # Discount > 100%
        }
        
        result = await validator.validate_order(data)
        
        assert result.is_valid is False
        assert "quantity must be positive" in str(result.errors).lower()
        assert "price must be greater than zero" in str(result.errors).lower()
        assert "discount cannot exceed" in str(result.errors).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_nested_validation_errors(self):
        """Test handling of nested object validation errors"""
        validator = ValidationService()
        
        nested_data = {
            "user": {
                "name": "",  # Empty required field
                "profile": {
                    "age": -1,  # Invalid age
                    "preferences": "invalid"  # Should be object
                }
            }
        }
        
        result = await validator.validate_nested(nested_data)
        
        assert result.is_valid is False
        assert result.get_error_path("user.name") is not None
        assert result.get_error_path("user.profile.age") is not None
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_custom_validator_exceptions(self):
        """Test handling of custom validator exceptions"""
        validator = ValidationService()
        
        with patch.object(validator, 'custom_validate') as mock_validate:
            mock_validate.side_effect = ValueError("Custom validation failed")
            
            result = await validator.validate_with_custom({"data": "test"})
            
            assert result.is_valid is False
            assert "custom validation failed" in str(result.errors).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_validation_timeout_handling(self):
        """Test handling of validation timeouts"""
        validator = ValidationService()
        
        async def slow_validation(data):
            await asyncio.sleep(5)
            return True
        
        with patch.object(validator, 'async_validate', side_effect=slow_validation):
            try:
                result = await asyncio.wait_for(
                    validator.validate_complex({"data": "test"}),
                    timeout=1
                )
                assert False, "Should have timed out"
            except asyncio.TimeoutError:
                assert True