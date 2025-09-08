"""
Test IsolatedEnvironment Usage Validation - CLAUDE.md Compliance Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - System stability and configuration compliance
- Business Goal: Prevent cascade failures from improper environment variable access
- Value Impact: Ensures CLAUDE.md mandate compliance - all env access goes through IsolatedEnvironment
- Strategic Impact: CRITICAL - Direct os.environ access causes cascade failures costing $12K MRR

CRITICAL: These tests validate the CLAUDE.md mandate that ALL environment variable access
must go through IsolatedEnvironment, preventing configuration pollution and cascade failures.
"""

import pytest
import os
from unittest.mock import patch, Mock
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.backend_environment import BackendEnvironment


class TestIsolatedEnvironmentUsageValidation(BaseTestCase):
    """Validate IsolatedEnvironment usage enforces CLAUDE.md compliance for environment access."""
    
    def setup_method(self):
        """Setup test environment with proper isolation."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
        
        # Set test defaults to prevent cascade failures
        self.env.set("ENVIRONMENT", "test", "test_setup")
        self.env.set("JWT_SECRET_KEY", "test-jwt-secret-32-chars-minimum-length", "test_setup")
        self.env.set("SERVICE_SECRET", "test-service-secret-32-chars-minimum", "test_setup")
        
    def teardown_method(self):
        """Clean up test environment."""
        self.env.reset_to_original()
        super().teardown_method()

    @pytest.mark.unit
    def test_isolated_environment_prevents_os_environ_pollution(self):
        """Test that IsolatedEnvironment prevents os.environ pollution between tests."""
        # Set value in isolated environment
        test_key = "ISOLATED_TEST_VAR"
        test_value = "isolated_test_value"
        
        self.env.set(test_key, test_value, "test_isolation")
        
        # Verify isolated environment has the value
        assert self.env.get(test_key) == test_value, "Isolated environment should contain test value"
        
        # Verify os.environ does NOT have the value (proper isolation)
        assert test_key not in os.environ, "os.environ should not contain isolated test value"
        
        # Test that isolation prevents test pollution
        self.env.set("GLOBAL_POLLUTION_TEST", "polluted_value", "pollution_test")
        
        # Clear isolated environment
        self.env.reset_to_original()
        
        # Verify cleanup worked
        assert self.env.get("GLOBAL_POLLUTION_TEST") is None, "Reset should clear isolated values"
        assert "GLOBAL_POLLUTION_TEST" not in os.environ, "os.environ should not be polluted"
        
    @pytest.mark.unit
    def test_isolated_environment_source_tracking_prevents_cascade_failures(self):
        """Test that source tracking helps prevent cascade failures by identifying configuration origins."""
        # Set multiple values with different sources
        critical_configs = [
            ("SERVICE_SECRET", "production-secret-32-chars-minimum", "deployment_script"),
            ("DATABASE_URL", "postgresql://user:pass@localhost/db", "docker_compose"),
            ("JWT_SECRET_KEY", "jwt-secret-32-characters-minimum-length", "secret_manager")
        ]
        
        for key, value, source in critical_configs:
            self.env.set(key, value, source)
            
        # Verify source tracking works
        for key, value, expected_source in critical_configs:
            actual_source = self.env.get_variable_source(key)
            assert actual_source == expected_source, \
                f"Source tracking failed for {key}: expected {expected_source}, got {actual_source}"
                
        # Test that source tracking helps with debugging cascade failures
        sources_report = self.env.get_sources()
        
        # Verify critical sources are tracked
        assert "deployment_script" in sources_report, "Deployment script sources should be tracked"
        assert "docker_compose" in sources_report, "Docker compose sources should be tracked"
        assert "secret_manager" in sources_report, "Secret manager sources should be tracked"
        
        # Verify specific critical variables are properly attributed
        deployment_vars = sources_report["deployment_script"]
        assert "SERVICE_SECRET" in deployment_vars, "SERVICE_SECRET source should be tracked"
        
    @pytest.mark.unit
    def test_isolated_environment_singleton_consistency_prevents_config_drift(self):
        """Test that singleton pattern prevents configuration drift across modules."""
        # Get singleton instance multiple ways
        env1 = IsolatedEnvironment()
        env2 = get_env()
        env3 = IsolatedEnvironment.get_instance()
        
        # Verify all instances are the same object (singleton)
        assert env1 is env2, "get_env() should return same singleton instance"
        assert env2 is env3, "get_instance() should return same singleton instance"
        assert env1 is env3, "All access methods should return same singleton"
        
        # Test configuration consistency across all access methods
        test_config_key = "SINGLETON_CONSISTENCY_TEST"
        test_config_value = "consistent_across_all_instances"
        
        env1.set(test_config_key, test_config_value, "singleton_test")
        
        # Verify all instances see the same configuration
        assert env2.get(test_config_key) == test_config_value, "Second instance should see same config"
        assert env3.get(test_config_key) == test_config_value, "Third instance should see same config"
        
        # Test that configuration changes are visible across all instances
        updated_value = "updated_consistent_value"
        env2.set(test_config_key, updated_value, "singleton_update_test")
        
        assert env1.get(test_config_key) == updated_value, "First instance should see update"
        assert env3.get(test_config_key) == updated_value, "Third instance should see update"
        
    @pytest.mark.unit
    def test_isolated_environment_validation_prevents_mission_critical_failures(self):
        """Test that environment validation prevents mission-critical cascade failures."""
        # Test validation of mission-critical variables from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
        
        # Clear environment to test validation
        test_env = IsolatedEnvironment()
        test_env.enable_isolation()
        
        # Test SERVICE_SECRET validation (ULTRA_CRITICAL)
        validation_result = test_env.validate_all()
        
        # Should fail without SERVICE_SECRET
        assert not validation_result.is_valid, "Validation should fail without SERVICE_SECRET"
        error_messages = " ".join(validation_result.errors)
        assert "SERVICE_SECRET" in error_messages or "JWT_SECRET_KEY" in error_messages, \
            "Validation should identify missing critical secrets"
            
        # Set SERVICE_SECRET and test again
        test_env.set("SERVICE_SECRET", "valid-service-secret-32-chars-minimum", "validation_test")
        test_env.set("JWT_SECRET_KEY", "valid-jwt-secret-32-characters-minimum", "validation_test")
        test_env.set("SECRET_KEY", "valid-secret-key-32-characters-minimum", "validation_test")
        test_env.set("DATABASE_URL", "postgresql://user:pass@localhost/db", "validation_test")
        
        validation_result = test_env.validate_all()
        assert validation_result.is_valid, f"Validation should pass with required secrets: {validation_result.errors}"
        
        test_env.reset_to_original()
        
    @pytest.mark.unit  
    def test_isolated_environment_test_context_detection_enables_proper_defaults(self):
        """Test that test context detection enables proper defaults preventing test failures."""
        # Create new environment to test context detection
        test_env = IsolatedEnvironment()
        
        # Simulate test context
        with patch.object(test_env, '_is_test_context', return_value=True):
            test_env.enable_isolation()
            
            # Test that OAuth test credentials are available
            oauth_client_id = test_env.get("GOOGLE_OAUTH_CLIENT_ID_TEST")
            assert oauth_client_id is not None, "Test context should provide OAuth test credentials"
            assert "test" in oauth_client_id.lower(), "OAuth credentials should be test-specific"
            
            # Test that E2E simulation key is available
            e2e_key = test_env.get("E2E_OAUTH_SIMULATION_KEY")
            assert e2e_key is not None, "Test context should provide E2E simulation key"
            assert "test" in e2e_key.lower(), "E2E key should be test-specific"
            
            # Test that JWT secrets are available
            jwt_secret = test_env.get("JWT_SECRET_KEY")
            assert jwt_secret is not None, "Test context should provide JWT secret"
            assert len(jwt_secret) >= 32, "JWT secret should meet minimum length requirement"
            
            # Test that database defaults are provided
            db_host = test_env.get("POSTGRES_HOST")
            assert db_host == "localhost", "Test context should provide localhost database"
            
            db_port = test_env.get("POSTGRES_PORT") 
            assert db_port == "5434", "Test context should use test database port"
            
        test_env.reset_to_original()
        
    @pytest.mark.unit
    def test_isolated_environment_variable_protection_prevents_accidental_overwrites(self):
        """Test that variable protection prevents accidental overwrites of critical configuration."""
        # Set critical configuration values
        critical_configs = {
            "SERVICE_SECRET": "critical-service-secret-32-chars-minimum",
            "JWT_SECRET_KEY": "critical-jwt-secret-32-characters-minimum",
            "DATABASE_URL": "postgresql://critical:config@localhost/production"
        }
        
        for key, value in critical_configs.items():
            self.env.set(key, value, "critical_config")
            # Protect the critical variable
            self.env.protect_variable(key)
            
        # Attempt to overwrite protected variables (should fail)
        for key in critical_configs.keys():
            original_value = self.env.get(key)
            
            # Try to overwrite without force (should fail)
            success = self.env.set(key, "malicious_overwrite", "attack_vector")
            assert not success, f"Protected variable {key} should not be overwritable"
            
            # Verify original value is preserved
            current_value = self.env.get(key)
            assert current_value == original_value, f"Protected variable {key} should retain original value"
            
            # Verify protection status
            assert self.env.is_protected(key), f"Variable {key} should show as protected"
            
        # Test that force override works when needed (for emergency fixes)
        emergency_key = "SERVICE_SECRET"
        emergency_value = "emergency-override-secret-32-chars-minimum"
        
        success = self.env.set(emergency_key, emergency_value, "emergency_override", force=True)
        assert success, "Force override should work for emergency configuration changes"
        
        current_value = self.env.get(emergency_key)
        assert current_value == emergency_value, "Force override should update the value"