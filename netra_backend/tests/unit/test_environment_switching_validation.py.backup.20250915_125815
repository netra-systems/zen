"""
Test Environment Switching and Variable Validation Logic - Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - Environment management and switching logic  
- Business Goal: Ensure safe environment transitions without configuration corruption
- Value Impact: Prevents environment-specific configuration leakage between dev/staging/production
- Strategic Impact: CRITICAL - Environment confusion causes data corruption and compliance violations

CRITICAL: These tests validate environment switching logic that prevents configuration
leakage between environments, which can cause data corruption costing enterprise contracts.
"""

import pytest
from unittest.mock import patch, Mock
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment, EnvironmentValidator


class TestEnvironmentSwitchingValidation(BaseTestCase):
    """Test environment switching and validation logic prevents configuration corruption."""
    
    def setup_method(self):
        """Setup test environment with proper isolation."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
        self.validator = EnvironmentValidator(env=self.env)
        
        # Set base test environment
        self.env.set("TESTING", "true", "test_setup")
        
    def teardown_method(self):
        """Clean up test environment."""
        self.env.reset_to_original()
        super().teardown_method()

    @pytest.mark.unit
    def test_environment_detection_algorithm_accuracy(self):
        """Test that environment detection algorithm correctly identifies all environments."""
        test_cases = [
            # (env_vars, expected_environment)
            ({"ENVIRONMENT": "development"}, "development"),
            ({"ENVIRONMENT": "dev"}, "development"),
            ({"ENVIRONMENT": "local"}, "development"),
            ({"ENVIRONMENT": "test"}, "test"),
            ({"ENVIRONMENT": "testing"}, "test"),
            ({"ENVIRONMENT": "staging"}, "staging"), 
            ({"ENVIRONMENT": "production"}, "production"),
            ({"ENVIRONMENT": "prod"}, "production"),
            # Test pytest context detection
            ({"PYTEST_CURRENT_TEST": "test_something"}, "test"),
            ({"TESTING": "true"}, "test"),
            ({"TEST_MODE": "1"}, "test"),
            # Test default behavior
            ({}, "development")  # Default when no environment specified
        ]
        
        for env_vars, expected in test_cases:
            # Clear environment and set test variables
            test_env = IsolatedEnvironment()
            test_env.enable_isolation()
            
            for key, value in env_vars.items():
                test_env.set(key, value, "environment_detection_test")
                
            detected = test_env.get_environment_name()
            assert detected == expected, \
                f"Environment detection failed for {env_vars}: expected {expected}, got {detected}"
                
            test_env.reset_to_original()
            
    @pytest.mark.unit
    def test_environment_specific_variable_validation(self):
        """Test that variable validation adapts correctly to environment requirements."""
        # Test development environment (most permissive)
        self.env.set("ENVIRONMENT", "development", "env_test")
        
        result = self.validator.validate_environment_specific_behavior("development")
        assert result.is_valid or len(result.warnings) > 0, \
            "Development should be permissive or provide helpful warnings"
            
        # Test staging environment requirements
        self.env.set("ENVIRONMENT", "staging", "env_test")
        
        # Staging should reject localhost URLs
        self.env.set("NEXT_PUBLIC_API_URL", "http://localhost:8000", "staging_test")
        
        result = self.validator.validate_staging_domain_configuration()
        assert not result.is_valid, "Staging should reject localhost URLs"
        error_text = " ".join(result.errors)
        assert "localhost" in error_text, "Should identify localhost in staging as error"
        
        # Test production environment (most strict)
        self.env.set("ENVIRONMENT", "production", "env_test")
        
        # Production should require strong secrets
        weak_jwt = "weak123"
        self.env.set("JWT_SECRET_KEY", weak_jwt, "production_test")
        
        result = self.validator.validate_critical_service_variables("backend") 
        assert not result.is_valid, "Production should reject weak JWT secrets"
        error_text = " ".join(result.errors)
        assert "JWT_SECRET_KEY" in error_text, "Should identify weak JWT in production"
        
    @pytest.mark.unit
    def test_environment_variable_isolation_between_switches(self):
        """Test that environment switches properly isolate variables."""
        # Set development environment variables
        dev_vars = {
            "DATABASE_URL": "postgresql://localhost:5432/netra_dev",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "ENVIRONMENT": "development"
        }
        
        for key, value in dev_vars.items():
            self.env.set(key, value, "development_config")
            
        # Switch to staging environment
        staging_vars = {
            "DATABASE_URL": "postgresql://staging-db.gcp:5432/netra_staging", 
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
            "ENVIRONMENT": "staging"
        }
        
        # Clear and set staging variables
        for key in dev_vars.keys():
            self.env.delete(key, "environment_switch")
            
        for key, value in staging_vars.items():
            self.env.set(key, value, "staging_config")
            
        # Verify staging configuration is active
        assert self.env.get("DATABASE_URL") == staging_vars["DATABASE_URL"], \
            "Staging DATABASE_URL should be active"
        assert self.env.get("DEBUG") == "false", "Staging should disable DEBUG"
        assert self.env.get_environment_name() == "staging", "Environment should be staging"
        
        # Verify no development configuration leaked
        for key in dev_vars.keys():
            current_value = self.env.get(key)
            dev_value = dev_vars[key]
            assert current_value != dev_value or key == "ENVIRONMENT", \
                f"Development value for {key} should not leak into staging"
                
    @pytest.mark.unit  
    def test_service_id_stability_validation_prevents_auth_failures(self):
        """Test SERVICE_ID stability validation prevents authentication cascade failures."""
        # Test stable SERVICE_ID (should pass)
        result = self.validator.validate_service_id_stability()
        
        self.env.set("SERVICE_ID", "netra-backend", "stability_test")
        result = self.validator.validate_service_id_stability()
        assert result.is_valid, f"Stable SERVICE_ID should pass validation: {result.errors}"
        
        # Test SERVICE_ID with timestamp (should fail - causes auth failures every minute)
        timestamp_service_id = "netra-backend-20250908-143022"
        self.env.set("SERVICE_ID", timestamp_service_id, "stability_test")
        
        result = self.validator.validate_service_id_stability()
        assert not result.is_valid, "SERVICE_ID with timestamp should fail validation"
        
        error_text = " ".join(result.errors)
        assert "timestamp" in error_text.lower(), "Should identify timestamp in SERVICE_ID"
        assert "stable" in error_text.lower(), "Should mention stability requirement"
        
        # Test SERVICE_ID with multiple dashes (potential timestamp pattern)
        multi_dash_id = "netra-backend-staging-2025-01-08"
        self.env.set("SERVICE_ID", multi_dash_id, "stability_test")
        
        result = self.validator.validate_service_id_stability()
        assert not result.is_valid, "SERVICE_ID with multiple dashes should be flagged"
        
        # Test missing SERVICE_ID 
        self.env.delete("SERVICE_ID", "stability_test")
        result = self.validator.validate_service_id_stability()
        assert not result.is_valid, "Missing SERVICE_ID should fail validation"
        
    @pytest.mark.unit
    def test_frontend_critical_variables_cascade_prevention(self):
        """Test validation of frontend variables that prevent cascade failures."""
        # Test all frontend critical variables from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
        critical_frontend_vars = [
            "NEXT_PUBLIC_API_URL", 
            "NEXT_PUBLIC_WS_URL",
            "NEXT_PUBLIC_AUTH_URL", 
            "NEXT_PUBLIC_ENVIRONMENT"
        ]
        
        # Test missing critical variables (each causes specific cascade failure)
        for critical_var in critical_frontend_vars:
            # Clear all variables
            for var in critical_frontend_vars:
                self.env.delete(var, "cascade_test")
                
            # Set environment to staging
            self.env.set("ENVIRONMENT", "staging", "cascade_test")
                
            result = self.validator.validate_frontend_critical_variables()
            assert not result.is_valid, f"Missing {critical_var} should fail validation"
            
            error_text = " ".join(result.errors) 
            assert critical_var in error_text, f"Should identify missing {critical_var}"
            
        # Test complete valid configuration
        staging_frontend_config = {
            "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
            "NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai", 
            "NEXT_PUBLIC_AUTH_URL": "https://auth.staging.netrasystems.ai",
            "NEXT_PUBLIC_ENVIRONMENT": "staging"
        }
        
        for key, value in staging_frontend_config.items():
            self.env.set(key, value, "staging_frontend")
            
        result = self.validator.validate_frontend_critical_variables()
        assert result.is_valid, f"Complete staging frontend config should pass: {result.errors}"
        
        # Test environment mismatch detection
        self.env.set("NEXT_PUBLIC_ENVIRONMENT", "production", "mismatch_test")  # Mismatch
        self.env.set("ENVIRONMENT", "staging", "mismatch_test")  # Backend thinks staging
        
        # This should create inconsistency warnings
        backend_env = self.env.get_environment_name()
        frontend_env = self.env.get("NEXT_PUBLIC_ENVIRONMENT")
        
        assert backend_env != frontend_env, "Test should create environment mismatch"
        
    @pytest.mark.unit
    def test_discovery_endpoint_configuration_validation(self):
        """Test validation of discovery endpoint configuration that prevents service connection failures."""
        # Test valid discovery configuration
        valid_discovery_data = {
            "backend_url": "https://api.staging.netrasystems.ai",
            "auth_url": "https://auth.staging.netrasystems.ai", 
            "websocket_url": "wss://api.staging.netrasystems.ai",
            "environment": "staging"
        }
        
        self.env.set("ENVIRONMENT", "staging", "discovery_test")
        result = self.validator.validate_discovery_endpoint_configuration(valid_discovery_data)
        assert result.is_valid, f"Valid discovery config should pass: {result.errors}"
        
        # Test localhost URLs in staging (should fail)
        localhost_discovery = valid_discovery_data.copy()
        localhost_discovery["backend_url"] = "http://localhost:8000"  # Wrong for staging
        
        result = self.validator.validate_discovery_endpoint_configuration(localhost_discovery)
        assert not result.is_valid, "Localhost URLs should fail in staging"
        error_text = " ".join(result.errors)
        assert "localhost" in error_text, "Should identify localhost URL issue"
        
        # Test development environment (should allow localhost)
        self.env.set("ENVIRONMENT", "development", "discovery_test") 
        
        dev_discovery_data = {
            "backend_url": "http://localhost:8000",
            "auth_url": "http://localhost:8081",
            "websocket_url": "ws://localhost:8000",
            "environment": "development"
        }
        
        result = self.validator.validate_discovery_endpoint_configuration(dev_discovery_data) 
        assert result.is_valid, f"Development localhost URLs should pass: {result.errors}"