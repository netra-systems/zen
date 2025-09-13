"""
Integration tests for Issue #378: Database Auto-Initialization May Hide Configuration Issues

This test suite demonstrates how the current auto-initialization pattern can mask
configuration problems and validates that the proposed fix catches these issues early.

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: Platform Stability & Issue Prevention
- Value Impact: Prevents configuration issues from causing production failures
- Revenue Impact: Critical for operational reliability
"""

import asyncio
import logging
import os
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Optional, Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager
from netra_backend.app.core.startup_validation import StartupValidator, validate_startup
from shared.isolated_environment import IsolatedEnvironment


class TestDatabaseConfigurationValidation(SSotAsyncTestCase):
    """Test suite for database configuration validation during startup."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        # Get logger using proper SSOT method
        from shared.logging.unified_logging_ssot import get_logger
        self.logger = get_logger(__name__)
        self.original_manager = None
        
    def teardown_method(self, method):
        """Clean up test environment."""
        # Restore original database manager if we modified it
        if self.original_manager:
            global _database_manager
            from netra_backend.app.db import database_manager
            database_manager._database_manager = self.original_manager
        super().teardown_method(method)
    
    async def test_auto_initialization_masks_invalid_configuration(self):
        """
        TEST: Demonstrate how auto-initialization can mask configuration issues.
        
        This test shows the current problematic behavior where invalid database
        configuration is only discovered when first database operation is attempted,
        not during startup validation.
        """
        self.logger.info("Testing auto-initialization with invalid configuration")
        
        # Create a fresh database manager with invalid configuration
        invalid_manager = DatabaseManager()
        
        # Mock invalid database configuration
        with patch.object(invalid_manager, '_get_database_url') as mock_get_url:
            mock_get_url.return_value = "postgresql://invalid_user:wrong_pass@nonexistent_host:5432/missing_db"
            
            # The get_engine() method should trigger auto-initialization
            with pytest.raises(RuntimeError) as exc_info:
                # This should fail, but the error is masked by auto-initialization attempts
                engine = invalid_manager.get_engine()
                
            # The error message should indicate the configuration problem was discovered late
            assert "auto-initialization failed" in str(exc_info.value).lower()
            self.logger.info(f"Auto-initialization attempted to mask config error: {exc_info.value}")
    
    async def test_startup_validation_missing_database_config_validation(self):
        """
        TEST: Show that current startup validation doesn't catch config issues early.
        
        This demonstrates the gap in current startup validation where database
        configuration problems aren't validated before initialization attempts.
        """
        self.logger.info("Testing startup validation with invalid database configuration")
        
        # Create a mock app with invalid database configuration
        mock_app = Mock()
        mock_app.state = Mock()
        
        # Mock database session factory as None (indicating initialization failure)
        mock_app.state.db_session_factory = None
        mock_app.state.database_mock_mode = False
        
        # Create startup validator
        validator = StartupValidator()
        
        # Run validation - this should pass the database check despite config issues
        success, report = await validator.validate_startup(mock_app)
        
        # Check that validation identifies database as critical failure
        database_validations = [
            v for v in validator.validations 
            if v.category == "Database" and v.status.value in ["critical", "failed"]
        ]
        
        # Should have at least one critical database validation
        assert len(database_validations) > 0, "Startup validation should identify database initialization failure"
        
        # But it doesn't validate configuration BEFORE initialization
        self.logger.info(f"Found {len(database_validations)} database validation issues")
        for validation in database_validations:
            self.logger.info(f"Database validation: {validation.name} - {validation.message}")
    
    async def test_configuration_validation_should_occur_before_initialization(self):
        """
        TEST: Demonstrate what proper configuration validation should look like.
        
        This test shows how configuration validation should occur BEFORE any
        initialization attempts to catch issues early.
        """
        self.logger.info("Testing early configuration validation approach")
        
        # Test invalid configuration scenarios
        invalid_configs = [
            {
                "name": "missing_host",
                "env_vars": {"POSTGRES_HOST": ""},
                "expected_error": "host"
            },
            {
                "name": "invalid_port", 
                "env_vars": {"POSTGRES_PORT": "invalid"},
                "expected_error": "port"
            },
            {
                "name": "missing_credentials",
                "env_vars": {"POSTGRES_USER": "", "POSTGRES_PASSWORD": ""},
                "expected_error": "credentials"
            }
        ]
        
        for config_test in invalid_configs:
            # Mock invalid environment configuration
            with patch.dict(os.environ, config_test["env_vars"], clear=False):
                # This is what SHOULD happen - configuration validation before initialization
                validation_result = await self._validate_database_configuration_early()
                
                # Should detect configuration issue without attempting initialization
                assert not validation_result["valid"], f"Should detect {config_test['name']} configuration issue"
                assert config_test["expected_error"] in validation_result["error"].lower()
                self.logger.info(f"Detected {config_test['name']} configuration issue: {validation_result['error']}")
    
    async def _validate_database_configuration_early(self) -> Dict[str, Any]:
        """
        Helper method that demonstrates proper early configuration validation.
        
        This is what the enhanced startup validation should do - validate
        configuration BEFORE attempting any database operations.
        """
        try:
            from shared.database_url_builder import DatabaseURLBuilder
            from shared.isolated_environment import get_env
            
            # Get environment configuration
            env = get_env()
            
            # Validate configuration without attempting connection
            try:
                url_builder = DatabaseURLBuilder(env.as_dict())
                database_url = url_builder.get_url_for_environment(sync=False)
                
                if not database_url:
                    return {
                        "valid": False,
                        "error": "Failed to construct database URL from environment variables"
                    }
                
                # Parse URL to validate components
                from urllib.parse import urlparse
                parsed = urlparse(database_url)
                
                # Validate required components
                if not parsed.hostname:
                    return {"valid": False, "error": "Missing database host configuration"}
                
                if not parsed.port:
                    return {"valid": False, "error": "Missing database port configuration"}
                
                if not parsed.username:
                    return {"valid": False, "error": "Missing database user credentials"}
                
                # Configuration appears valid
                return {"valid": True, "error": None}
                
            except ValueError as e:
                return {"valid": False, "error": f"Invalid database configuration: {e}"}
            except Exception as e:
                return {"valid": False, "error": f"Configuration validation error: {e}"}
                
        except ImportError as e:
            return {"valid": False, "error": f"Missing database configuration dependencies: {e}"}
    
    async def test_startup_validation_with_configuration_validation_enhancement(self):
        """
        TEST: Show how enhanced startup validation should work.
        
        This test demonstrates the proposed fix where startup validation
        includes early configuration validation before initialization attempts.
        """
        self.logger.info("Testing enhanced startup validation with configuration validation")
        
        # Create mock app with proper structure
        mock_app = Mock()
        mock_app.state = Mock()
        
        # Mock that configuration validation is performed first
        with patch('netra_backend.app.core.startup_validation.StartupValidator._validate_database') as mock_db_validation:
            # Mock the enhanced database validation that includes config validation
            async def enhanced_database_validation(app):
                # First validate configuration
                config_result = await self._validate_database_configuration_early()
                
                if not config_result["valid"]:
                    # Add validation for configuration failure
                    from netra_backend.app.core.startup_validation import ComponentValidation, ComponentStatus
                    validation = ComponentValidation(
                        name="Database Configuration",
                        category="Database",
                        expected_min=1,
                        actual_count=0,
                        status=ComponentStatus.CRITICAL,
                        message=f"Configuration validation failed: {config_result['error']}",
                        is_critical=True,
                        metadata={"config_error": config_result["error"]}
                    )
                    # Add to validator's validations
                    self.validations.append(validation)
                    return
                
                # Configuration is valid, proceed with normal database validation
                # ... normal database validation logic here ...
                
            mock_db_validation.side_effect = enhanced_database_validation
            
            # Run enhanced startup validation
            validator = StartupValidator()
            
            # Simulate invalid configuration
            with patch.dict(os.environ, {"POSTGRES_HOST": ""}, clear=False):
                success, report = await validator.validate_startup(mock_app)
                
                # Should detect configuration issue early
                config_validations = [
                    v for v in validator.validations 
                    if "Configuration" in v.name and v.status.value == "critical"
                ]
                
                assert len(config_validations) > 0, "Enhanced validation should catch configuration issues"
                self.logger.info(f"Enhanced validation caught {len(config_validations)} configuration issues")
    
    async def test_configuration_error_messages_are_actionable(self):
        """
        TEST: Validate that configuration error messages provide actionable guidance.
        
        Configuration errors should include specific guidance on what needs to be fixed.
        """
        self.logger.info("Testing actionable configuration error messages")
        
        # Test different configuration error scenarios
        error_scenarios = [
            {
                "description": "Missing required environment variables",
                "env_override": {"POSTGRES_HOST": "", "POSTGRES_PORT": "", "POSTGRES_DB": ""},
                "expected_guidance": ["environment variables", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB"]
            },
            {
                "description": "Invalid port configuration", 
                "env_override": {"POSTGRES_PORT": "invalid_port"},
                "expected_guidance": ["port", "numeric", "POSTGRES_PORT"]
            },
            {
                "description": "Missing credentials",
                "env_override": {"POSTGRES_USER": "", "POSTGRES_PASSWORD": ""},
                "expected_guidance": ["credentials", "POSTGRES_USER", "POSTGRES_PASSWORD"]
            }
        ]
        
        for scenario in error_scenarios:
            with patch.dict(os.environ, scenario["env_override"], clear=False):
                validation_result = await self._validate_database_configuration_early()
                
                assert not validation_result["valid"], f"Should detect issue: {scenario['description']}"
                
                error_message = validation_result["error"].lower()
                
                # Check that error message contains actionable guidance
                guidance_found = []
                for guidance in scenario["expected_guidance"]:
                    if guidance.lower() in error_message:
                        guidance_found.append(guidance)
                
                assert len(guidance_found) > 0, f"Error message should contain actionable guidance. Got: {validation_result['error']}"
                self.logger.info(f"Error message contains guidance: {guidance_found}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])