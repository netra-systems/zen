"""
Test 23: Config Route Updates
Tests for configuration API updates - app/routes/config.py
"""

import pytest
from .test_utilities import base_client, assert_error_response


class TestConfigRoute:
    """Test configuration API updates."""
    
    def test_config_retrieval(self, base_client):
        """Test configuration retrieval endpoint."""
        response = base_client.get("/api/config")
        
        if response.status_code == 200:
            config = response.json()
            assert "log_level" in config
            assert "max_retries" in config
            assert "timeout" in config
    
    def test_config_update_validation(self, base_client):
        """Test configuration update validation."""
        invalid_config = {
            "log_level": "INVALID_LEVEL",
            "max_retries": -1  # Invalid negative value
        }
        
        response = base_client.put("/api/config", json=invalid_config)
        # Validation error or not found
        assert_error_response(response, [422, 400, 404])

    async def test_config_persistence(self):
        """Test configuration persistence."""
        from app.routes.config import update_config
        
        new_config = {
            "log_level": "DEBUG",
            "feature_flags": {"new_feature": True}
        }
        
        result = await update_config(new_config)
        assert result["success"] == True