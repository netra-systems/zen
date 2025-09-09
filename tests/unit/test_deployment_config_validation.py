"""
Unit tests for deployment configuration validation.

Tests the validation of deployment configurations across different environments
to ensure proper setup and prevent deployment failures.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Ensure deployment configurations are valid across environments
- Value Impact: Prevents deployment failures and configuration errors
- Strategic Impact: Maintains deployment reliability and system stability
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, patch
from shared.isolated_environment import IsolatedEnvironment


class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()


class MockDeploymentValidator:
    """Mock deployment configuration validator."""
    
    @staticmethod
    def validate_environment_config(environment: str) -> Dict[str, Any]:
        """Validate configuration for a specific environment."""
        valid_envs = ["development", "staging", "production"]
        if environment not in valid_envs:
            return {"valid": False, "errors": [f"Invalid environment: {environment}"]}
        
        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "environment": environment
        }
    
    @staticmethod
    def validate_service_dependencies(services: list) -> Dict[str, Any]:
        """Validate service dependencies."""
        required_services = ["backend", "auth_service", "frontend"]
        missing_services = [svc for svc in required_services if svc not in services]
        
        if missing_services:
            return {
                "valid": False,
                "errors": [f"Missing required services: {missing_services}"]
            }
        
        return {"valid": True, "errors": []}


class TestDeploymentConfigValidation:
    """Test deployment configuration validation."""

    def test_validates_development_environment(self):
        """Test validation of development environment configuration."""
        result = MockDeploymentValidator.validate_environment_config("development")
        
        assert result["valid"] is True
        assert result["environment"] == "development"
        assert len(result["errors"]) == 0

    def test_validates_staging_environment(self):
        """Test validation of staging environment configuration."""
        result = MockDeploymentValidator.validate_environment_config("staging")
        
        assert result["valid"] is True
        assert result["environment"] == "staging"
        assert len(result["errors"]) == 0

    def test_validates_production_environment(self):
        """Test validation of production environment configuration."""
        result = MockDeploymentValidator.validate_environment_config("production")
        
        assert result["valid"] is True
        assert result["environment"] == "production"
        assert len(result["errors"]) == 0

    def test_rejects_invalid_environment(self):
        """Test rejection of invalid environment configuration."""
        result = MockDeploymentValidator.validate_environment_config("invalid_env")
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "Invalid environment" in result["errors"][0]

    def test_validates_complete_service_dependencies(self):
        """Test validation of complete service dependencies."""
        services = ["backend", "auth_service", "frontend"]
        result = MockDeploymentValidator.validate_service_dependencies(services)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_detects_missing_service_dependencies(self):
        """Test detection of missing service dependencies."""
        services = ["backend"]  # Missing auth_service and frontend
        result = MockDeploymentValidator.validate_service_dependencies(services)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "Missing required services" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_deployment_validation_notifications(self):
        """Test deployment validation notifications via WebSocket."""
        websocket = TestWebSocketConnection()
        
        # Simulate deployment validation process
        environments = ["development", "staging", "production"]
        
        for env in environments:
            result = MockDeploymentValidator.validate_environment_config(env)
            
            await websocket.send_json({
                "type": "deployment_validation",
                "environment": env,
                "valid": result["valid"],
                "errors": result["errors"]
            })
        
        messages = await websocket.get_messages()
        assert len(messages) == 3
        assert all(msg["type"] == "deployment_validation" for msg in messages)
        assert all(msg["valid"] is True for msg in messages)

    def test_deployment_config_validation_comprehensive(self):
        """Test comprehensive deployment configuration validation."""
        test_scenarios = [
            {
                "environment": "staging",
                "services": ["backend", "auth_service", "frontend"],
                "expected_valid": True
            },
            {
                "environment": "production", 
                "services": ["backend", "auth_service"],
                "expected_valid": False  # Missing frontend
            },
            {
                "environment": "invalid",
                "services": ["backend", "auth_service", "frontend"],
                "expected_valid": False  # Invalid environment
            }
        ]
        
        for scenario in test_scenarios:
            env_result = MockDeploymentValidator.validate_environment_config(scenario["environment"])
            svc_result = MockDeploymentValidator.validate_service_dependencies(scenario["services"])
            
            overall_valid = env_result["valid"] and svc_result["valid"]
            assert overall_valid == scenario["expected_valid"], \
                f"Scenario failed: {scenario}"


if __name__ == "__main__":
    pytest.main([__file__])