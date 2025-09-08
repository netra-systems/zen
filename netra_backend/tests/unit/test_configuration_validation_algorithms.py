"""
Test Configuration Validation Algorithms - Core Business Logic Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - Configuration validation core algorithms
- Business Goal: Prevent deployment failures through robust configuration validation
- Value Impact: Catches configuration errors before they cause cascade failures
- Strategic Impact: CRITICAL - Configuration errors cause 60% of production outages per Google SRE data

CRITICAL: These tests validate the core algorithms that prevent configuration-related
cascade failures that can cost $12K MRR in lost business value.
"""

import pytest
from unittest.mock import Mock, patch
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.configuration.central_config_validator import CentralConfigurationValidator


class TestConfigurationValidationAlgorithms(BaseTestCase):
    """Test core configuration validation algorithms that prevent cascade failures."""
    
    def setup_method(self):
        """Setup test environment with isolated configuration."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
        
        # Set required test environment variables
        self.env.set("ENVIRONMENT", "test", "test_setup")
        self.env.set("TESTING", "true", "test_setup")
        
        self.validator = CentralConfigurationValidator(env_manager=self.env)
        
    def teardown_method(self):
        """Clean up test environment."""
        self.env.reset_to_original()
        super().teardown_method()

    @pytest.mark.unit
    def test_mission_critical_variable_validation_algorithm(self):
        """Test validation algorithm for mission-critical variables from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml."""
        # Test SERVICE_SECRET validation (ULTRA_CRITICAL)
        # This variable causes "complete authentication failure and circuit breaker permanent open"
        
        # Test missing SERVICE_SECRET
        result = self.validator.validate_service_variable("SERVICE_SECRET", None, "staging")
        assert not result.is_valid, "Missing SERVICE_SECRET should fail validation"
        assert "authentication failure" in " ".join(result.errors).lower(), \
            "Error should describe authentication impact"
            
        # Test SERVICE_SECRET too short
        result = self.validator.validate_service_variable("SERVICE_SECRET", "short", "staging")  
        assert not result.is_valid, "Short SERVICE_SECRET should fail validation"
        assert "at least" in " ".join(result.errors), "Error should specify minimum length"
        
        # Test valid SERVICE_SECRET
        valid_secret = "valid-service-secret-32-characters-minimum-length"
        result = self.validator.validate_service_variable("SERVICE_SECRET", valid_secret, "staging")
        assert result.is_valid, f"Valid SERVICE_SECRET should pass: {result.errors}"
        
        # Test SERVICE_ID validation (ULTRA_CRITICAL - must be stable value "netra-backend")
        # Timestamp suffixes cause authentication failures every minute
        
        # Test SERVICE_ID with timestamp (should fail)
        timestamp_id = "netra-backend-20250908-143022"
        result = self.validator.validate_service_variable("SERVICE_ID", timestamp_id, "staging")
        assert not result.is_valid, "SERVICE_ID with timestamp should fail validation"
        assert "stable" in " ".join(result.errors).lower(), "Error should mention stability requirement"
        
        # Test correct SERVICE_ID
        result = self.validator.validate_service_variable("SERVICE_ID", "netra-backend", "staging")
        assert result.is_valid, f"Correct SERVICE_ID should pass: {result.errors}"
        
    @pytest.mark.unit
    def test_environment_specific_validation_algorithm(self):
        """Test that validation algorithms adapt correctly to different environments."""
        environments = ["development", "test", "staging", "production"]
        test_configs = {
            "JWT_SECRET_KEY": {
                "weak": "weak123",
                "dev_ok": "dev-jwt-secret-for-testing-32-chars",
                "production": "secure-production-jwt-secret-32-characters-minimum"
            }
        }
        
        for environment in environments:
            # Test weak JWT secret
            result = self.validator.validate_security_variable(
                "JWT_SECRET_KEY", test_configs["JWT_SECRET_KEY"]["weak"], environment
            )
            
            if environment == "production":
                assert not result.is_valid, f"Weak JWT should fail in {environment}"
                assert "32 characters" in " ".join(result.errors), \
                    "Production should enforce strong JWT requirements"
            else:
                # Development/test environments should be more permissive
                if not result.is_valid:
                    # Should at least provide warnings, not hard failures
                    assert len(result.warnings) > 0, f"Non-prod should warn about weak JWT in {environment}"
                    
            # Test production-grade secret in all environments
            result = self.validator.validate_security_variable(
                "JWT_SECRET_KEY", test_configs["JWT_SECRET_KEY"]["production"], environment
            )
            assert result.is_valid, f"Strong JWT should pass in all environments: {environment}"
            
    @pytest.mark.unit
    def test_cascade_failure_detection_algorithm(self):
        """Test algorithm that detects configuration patterns leading to cascade failures."""
        # Test URL consistency algorithm (prevents frontend-backend connection failures)
        frontend_config = {
            "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
            "NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai", 
            "NEXT_PUBLIC_AUTH_URL": "https://auth.staging.netrasystems.ai"
        }
        
        backend_config = {
            "ENVIRONMENT": "staging",
            "CORS_ALLOWED_ORIGINS": "https://app.staging.netrasystems.ai,https://api.staging.netrasystems.ai"
        }
        
        # Test consistent configuration (should pass)
        result = self.validator.validate_cross_service_consistency(frontend_config, backend_config)
        assert result.is_valid, f"Consistent staging config should pass: {result.errors}"
        
        # Test inconsistent configuration (should detect cascade failure risk)
        inconsistent_frontend = frontend_config.copy()
        inconsistent_frontend["NEXT_PUBLIC_API_URL"] = "https://localhost:8000"  # Wrong for staging
        
        result = self.validator.validate_cross_service_consistency(inconsistent_frontend, backend_config)
        assert not result.is_valid, "Inconsistent config should be detected"
        assert "localhost" in " ".join(result.errors), "Should detect localhost in non-dev environment"
        
        # Test CORS mismatch detection
        cors_mismatch_backend = backend_config.copy()
        cors_mismatch_backend["CORS_ALLOWED_ORIGINS"] = "https://wrong-domain.com"
        
        result = self.validator.validate_cross_service_consistency(frontend_config, cors_mismatch_backend)
        assert not result.is_valid, "CORS mismatch should be detected"
        assert "cors" in " ".join(result.errors).lower(), "Should identify CORS configuration issue"
        
    @pytest.mark.unit
    def test_websocket_event_configuration_validation_algorithm(self):
        """Test validation of WebSocket event configuration critical for chat functionality."""
        # Test mission-critical WebSocket events from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
        required_events = [
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed"
        ]
        
        # Test complete event configuration
        complete_config = {event: {"enabled": True, "payload_required": ["run_id"]} for event in required_events}
        
        result = self.validator.validate_websocket_events(complete_config)
        assert result.is_valid, f"Complete WebSocket event config should pass: {result.errors}"
        
        # Test missing critical events
        incomplete_config = complete_config.copy()
        del incomplete_config["agent_started"]  # Missing critical event
        
        result = self.validator.validate_websocket_events(incomplete_config)
        assert not result.is_valid, "Missing critical WebSocket event should fail validation"
        assert "agent_started" in " ".join(result.errors), "Should identify missing agent_started event"
        
        # Test missing run_id requirement (causes "Events not routed to correct user, messages lost")
        no_run_id_config = complete_config.copy()
        no_run_id_config["agent_started"]["payload_required"] = []  # Missing run_id
        
        result = self.validator.validate_websocket_events(no_run_id_config) 
        assert not result.is_valid, "Missing run_id requirement should fail validation"
        assert "run_id" in " ".join(result.errors), "Should identify missing run_id requirement"
        
    @pytest.mark.unit
    def test_database_url_ssot_validation_algorithm(self):
        """Test validation algorithm for database URL SSOT compliance."""
        # Test direct DATABASE_URL access (should warn/fail)
        direct_db_config = {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "database_access_method": "direct_env_var"
        }
        
        result = self.validator.validate_database_configuration(direct_db_config)
        assert len(result.warnings) > 0 or not result.is_valid, \
            "Direct DATABASE_URL access should generate warnings or fail"
            
        warning_text = " ".join(result.warnings)
        assert "ssot" in warning_text.lower() or "database" in warning_text.lower(), \
            "Should warn about SSOT compliance"
            
        # Test SSOT-compliant configuration (should pass)
        ssot_config = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_USER": "testuser", 
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_DB": "testdb",
            "POSTGRES_PORT": "5432",
            "database_access_method": "DatabaseURLBuilder"
        }
        
        result = self.validator.validate_database_configuration(ssot_config)
        assert result.is_valid, f"SSOT-compliant database config should pass: {result.errors}"
        
        # Test missing required component variables
        incomplete_ssot = ssot_config.copy()
        del incomplete_ssot["POSTGRES_PASSWORD"]  # Missing required component
        
        result = self.validator.validate_database_configuration(incomplete_ssot)
        assert not result.is_valid, "Incomplete SSOT config should fail validation"
        assert "POSTGRES_PASSWORD" in " ".join(result.errors), "Should identify missing component"
        
    @pytest.mark.unit
    def test_oauth_dual_naming_validation_algorithm(self):
        """Test validation algorithm for OAuth dual naming convention compliance."""
        # Test backend service OAuth pattern (simplified names)
        backend_oauth = {
            "GOOGLE_CLIENT_ID": "backend-oauth-client-id",
            "GOOGLE_CLIENT_SECRET": "backend-oauth-client-secret",
            "service_type": "backend"
        }
        
        result = self.validator.validate_oauth_configuration(backend_oauth, "backend")
        assert result.is_valid, f"Backend OAuth pattern should pass: {result.errors}"
        
        # Test auth service OAuth pattern (environment-specific names)
        auth_oauth = {
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "auth-staging-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "auth-staging-client-secret",
            "service_type": "auth"
        }
        
        result = self.validator.validate_oauth_configuration(auth_oauth, "auth")
        assert result.is_valid, f"Auth OAuth pattern should pass: {result.errors}"
        
        # Test mixed pattern (should warn about consistency)
        mixed_oauth = {
            "GOOGLE_CLIENT_ID": "backend-style",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "auth-style",
            "service_type": "mixed"
        }
        
        result = self.validator.validate_oauth_configuration(mixed_oauth, "backend")
        assert len(result.warnings) > 0, "Mixed OAuth patterns should generate warnings"
        warning_text = " ".join(result.warnings)
        assert "consistency" in warning_text.lower() or "pattern" in warning_text.lower(), \
            "Should warn about pattern consistency"
            
    @pytest.mark.unit
    def test_configuration_drift_detection_algorithm(self):
        """Test algorithm that detects configuration drift between environments."""
        # Baseline staging configuration
        staging_baseline = {
            "ENVIRONMENT": "staging",
            "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
            "SERVICE_SECRET": "staging-service-secret-32-chars-minimum",
            "config_timestamp": "2025-01-08T10:00:00Z"
        }
        
        # Current staging configuration (with drift)
        staging_current = staging_baseline.copy()
        staging_current["NEXT_PUBLIC_API_URL"] = "https://localhost:8000"  # Drift detected
        staging_current["config_timestamp"] = "2025-01-08T15:00:00Z"
        
        result = self.validator.detect_configuration_drift(staging_baseline, staging_current)
        assert not result.is_valid, "Configuration drift should be detected"
        
        drift_errors = " ".join(result.errors)
        assert "NEXT_PUBLIC_API_URL" in drift_errors, "Should identify drifted variable"
        assert "localhost" in drift_errors, "Should identify problematic value"
        
        # Test acceptable configuration evolution (should pass)
        staging_evolution = staging_baseline.copy()
        staging_evolution["NEW_FEATURE_FLAG"] = "enabled"  # New feature, not drift
        staging_evolution["config_timestamp"] = "2025-01-08T15:00:00Z"
        
        result = self.validator.detect_configuration_drift(staging_baseline, staging_evolution)
        if not result.is_valid:
            # Should only warn about new variables, not error
            assert len(result.warnings) > 0, "New variables should generate warnings, not errors"
            assert "NEW_FEATURE_FLAG" in " ".join(result.warnings), "Should identify new variable"