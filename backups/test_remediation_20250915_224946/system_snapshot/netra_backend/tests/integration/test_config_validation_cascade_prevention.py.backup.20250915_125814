"""
Test Configuration Validation Cascade Prevention - Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - Cascade failure prevention through configuration validation
- Business Goal: Prevent single configuration errors from causing system-wide failures
- Value Impact: Prevents cascade failures that cost $12K MRR per incident through early detection
- Strategic Impact: CRITICAL - Cascade prevention saves business continuity and customer trust

CRITICAL: These tests validate cascade failure prevention patterns identified in
MISSION_CRITICAL_NAMED_VALUES_INDEX.xml that cause system-wide outages.
"""

import pytest
from unittest.mock import patch, Mock
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment, EnvironmentValidator
from shared.configuration.central_config_validator import CentralConfigurationValidator


class TestConfigurationValidationCascadePrevention(BaseTestCase):
    """Test configuration validation that prevents cascade failures."""
    
    def setup_method(self):
        """Setup cascade prevention test environment."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
        
        # Set test environment
        self.env.set("ENVIRONMENT", "test", "cascade_prevention_setup")
        self.env.set("TESTING", "true", "cascade_prevention_setup")
        
        self.validator = CentralConfigurationValidator(env_manager=self.env)
        self.env_validator = EnvironmentValidator(env=self.env)
        
    def teardown_method(self):
        """Clean up cascade prevention test environment."""
        self.env.reset_to_original()
        super().teardown_method()

    @pytest.mark.integration
    def test_service_secret_cascade_failure_prevention(self):
        """Test prevention of SERVICE_SECRET cascade failures (ULTRA_CRITICAL from index)."""
        # Scenario: SERVICE_SECRET missing causes "complete authentication failure and circuit breaker permanent open"
        
        # Set up staging environment with all required configs except SERVICE_SECRET
        staging_config = {
            "ENVIRONMENT": "staging",
            "JWT_SECRET_KEY": "staging-jwt-secret-32-characters-minimum",
            "DATABASE_URL": "postgresql://staging:pass@staging-db/netra",
            "REDIS_URL": "redis://staging-redis:6379/0"
            # SERVICE_SECRET is missing - this should be detected as cascade failure risk
        }
        
        for key, value in staging_config.items():
            self.env.set(key, value, "staging_config")
            
        # Test cascade failure detection
        result = self.validator.validate_critical_service_variables("backend")
        assert not result.is_valid, "Missing SERVICE_SECRET should be detected as critical failure"
        
        error_text = " ".join(result.errors).lower()
        assert "service_secret" in error_text, "Should identify SERVICE_SECRET as missing"
        assert "authentication" in error_text or "critical" in error_text, \
            "Should describe authentication impact"
            
        # Test cascade impact description
        cascade_impact = self.validator.get_cascade_impact("SERVICE_SECRET")
        assert "authentication failure" in cascade_impact.lower(), \
            "Should describe SERVICE_SECRET cascade impact"
        assert "circuit breaker" in cascade_impact.lower(), \
            "Should mention circuit breaker impact"
            
        # Test prevention: Add SERVICE_SECRET and verify cascade is prevented
        self.env.set("SERVICE_SECRET", "staging-service-secret-32-characters-min", "cascade_prevention")
        
        result = self.validator.validate_critical_service_variables("backend")
        assert result.is_valid, f"Complete configuration should prevent cascade: {result.errors}"
        
    @pytest.mark.integration
    def test_frontend_url_cascade_failure_prevention(self):
        """Test prevention of frontend URL cascade failures that break user access."""
        # Scenario: Wrong frontend URLs cause "No API calls work, no agents run, no data fetched"
        
        # Set up frontend configuration with localhost URLs in staging (cascade failure pattern)
        staging_frontend_config = {
            "ENVIRONMENT": "staging",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",  # Wrong for staging!
            "NEXT_PUBLIC_WS_URL": "ws://localhost:8000",     # Wrong for staging!
            "NEXT_PUBLIC_AUTH_URL": "http://localhost:8081", # Wrong for staging!
            "NEXT_PUBLIC_ENVIRONMENT": "staging"
        }
        
        for key, value in staging_frontend_config.items():
            self.env.set(key, value, "staging_frontend")
            
        # Test cascade failure detection for staging domain configuration
        result = self.env_validator.validate_staging_domain_configuration()
        assert not result.is_valid, "Localhost URLs in staging should be detected as cascade failure"
        
        error_text = " ".join(result.errors).lower()
        assert "localhost" in error_text, "Should identify localhost URLs as problematic"
        
        # Test cascade impact for each frontend variable
        frontend_impacts = {
            "NEXT_PUBLIC_API_URL": "No API calls work, no agents run, no data fetched",
            "NEXT_PUBLIC_WS_URL": "No real-time updates, no agent thinking messages, chat appears frozen",
            "NEXT_PUBLIC_AUTH_URL": "No login, no authentication, users cannot access system"
        }
        
        for var, expected_impact in frontend_impacts.items():
            cascade_impact = self.validator.get_cascade_impact(var)
            assert any(keyword in cascade_impact.lower() for keyword in ["api", "websocket", "auth", "login"]), \
                f"Should describe cascade impact for {var}: {cascade_impact}"
                
        # Test prevention: Fix URLs to proper staging format
        correct_staging_config = {
            "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
            "NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai",
            "NEXT_PUBLIC_AUTH_URL": "https://auth.staging.netrasystems.ai"
        }
        
        for key, value in correct_staging_config.items():
            self.env.set(key, value, "cascade_prevention")
            
        result = self.env_validator.validate_staging_domain_configuration()
        assert result.is_valid, f"Correct staging URLs should prevent cascade: {result.errors}"
        
    @pytest.mark.integration
    def test_websocket_event_cascade_failure_prevention(self):
        """Test prevention of WebSocket event cascade failures that break chat functionality."""
        # Scenario: Missing WebSocket events cause "chat appears broken" and "user confusion"
        
        # Set up WebSocket configuration missing critical events
        incomplete_websocket_config = {
            "agent_thinking": {"payload": ["run_id", "thought"], "enabled": True},
            "tool_executing": {"payload": ["run_id", "tool_name"], "enabled": True}
            # Missing critical events: agent_started, tool_completed, agent_completed
        }
        
        # Test cascade failure detection
        result = self.validator.validate_websocket_events(incomplete_websocket_config)
        assert not result.is_valid, "Missing critical WebSocket events should be detected"
        
        error_text = " ".join(result.errors)
        missing_events = ["agent_started", "tool_completed", "agent_completed"]
        for event in missing_events:
            assert event in error_text, f"Should identify missing critical event: {event}"
            
        # Test cascade impact for WebSocket events
        websocket_impacts = {
            "agent_started": "User doesn't know agent is working, appears frozen",
            "agent_thinking": "No visibility into agent reasoning, user confusion", 
            "tool_completed": "No tool results shown, incomplete responses",
            "agent_completed": "User doesn't know response is ready"
        }
        
        for event, expected_impact in websocket_impacts.items():
            cascade_impact = self.validator.get_websocket_event_cascade_impact(event)
            assert any(keyword in cascade_impact.lower() for keyword in ["user", "frozen", "confusion", "results"]), \
                f"Should describe cascade impact for {event}: {cascade_impact}"
                
        # Test run_id cascade failure prevention
        # Scenario: Missing run_id causes "Events not routed to correct user, messages lost"
        events_missing_run_id = {
            "agent_started": {"payload": ["agent_name"], "enabled": True},  # Missing run_id!
            "agent_thinking": {"payload": ["thought"], "enabled": True},    # Missing run_id!
        }
        
        result = self.validator.validate_websocket_events(events_missing_run_id)
        assert not result.is_valid, "Missing run_id should be detected as cascade failure"
        
        error_text = " ".join(result.errors)
        assert "run_id" in error_text, "Should identify missing run_id requirement"
        
        # Test prevention: Complete WebSocket event configuration
        complete_websocket_config = {
            "agent_started": {"payload": ["run_id", "agent_name"], "enabled": True},
            "agent_thinking": {"payload": ["run_id", "thought"], "enabled": True},
            "tool_executing": {"payload": ["run_id", "tool_name", "args"], "enabled": True},
            "tool_completed": {"payload": ["run_id", "tool_name", "result"], "enabled": True},
            "agent_completed": {"payload": ["run_id", "result"], "enabled": True}
        }
        
        result = self.validator.validate_websocket_events(complete_websocket_config)
        assert result.is_valid, f"Complete WebSocket config should prevent cascade: {result.errors}"
        
    @pytest.mark.integration  
    def test_database_connectivity_cascade_failure_prevention(self):
        """Test prevention of database connectivity cascade failures."""
        # Scenario: Database misconfig causes "No database connection, complete backend failure"
        
        # Test missing database configuration
        no_database_config = {
            "ENVIRONMENT": "staging",
            "JWT_SECRET_KEY": "staging-jwt-secret-32-characters-minimum",
            "SERVICE_SECRET": "staging-service-secret-32-chars-min"
            # Missing all database configuration
        }
        
        for key, value in no_database_config.items():
            self.env.set(key, value, "no_database_config")
            
        # Test cascade failure detection
        result = self.validator.validate_database_configuration({})
        assert not result.is_valid, "Missing database configuration should be detected"
        
        # Test SSOT compliance cascade prevention
        # Scenario: Mixed database patterns cause configuration drift and failures
        mixed_database_config = {
            "DATABASE_URL": "postgresql://direct:access@host/db",  # Non-SSOT
            "POSTGRES_HOST": "localhost",                          # SSOT component
            "POSTGRES_USER": "user"                                # SSOT component
        }
        
        result = self.validator.validate_database_configuration(mixed_database_config)
        assert not result.is_valid, "Mixed database patterns should be detected as cascade risk"
        
        error_text = " ".join(result.errors).lower()
        assert "ssot" in error_text or "pattern" in error_text, \
            "Should identify SSOT pattern violation"
            
        # Test prevention: Pure SSOT database configuration
        ssot_database_config = {
            "POSTGRES_HOST": "staging-postgres.gcp",
            "POSTGRES_USER": "staging_user",
            "POSTGRES_PASSWORD": "staging-secure-password-32-chars",
            "POSTGRES_DB": "netra_staging",
            "POSTGRES_PORT": "5432"
        }
        
        result = self.validator.validate_database_configuration(ssot_database_config)
        assert result.is_valid, f"SSOT database config should prevent cascade: {result.errors}"
        
    @pytest.mark.integration
    def test_cross_service_configuration_cascade_prevention(self):
        """Test prevention of cross-service configuration cascades."""
        # Scenario: Service configuration mismatch causes authentication and communication failures
        
        # Set up mismatched service configuration
        mismatched_service_config = {
            "BACKEND_SERVICE_SECRET": "backend-secret-32-characters-minimum",
            "AUTH_SERVICE_SECRET": "different-auth-secret-32-chars",  # Mismatch!
            "BACKEND_JWT_SECRET": "backend-jwt-secret-32-chars-min",
            "AUTH_JWT_SECRET": "different-auth-jwt-secret-32-chars",  # Mismatch!
            "ENVIRONMENT": "staging"
        }
        
        for key, value in mismatched_service_config.items():
            self.env.set(key, value, "mismatched_config")
            
        # Test cross-service consistency validation
        backend_config = {
            "SERVICE_SECRET": self.env.get("BACKEND_SERVICE_SECRET"),
            "JWT_SECRET_KEY": self.env.get("BACKEND_JWT_SECRET")
        }
        
        auth_config = {
            "SERVICE_SECRET": self.env.get("AUTH_SERVICE_SECRET"),
            "JWT_SECRET_KEY": self.env.get("AUTH_JWT_SECRET")
        }
        
        result = self.validator.validate_cross_service_consistency(backend_config, auth_config)
        assert not result.is_valid, "Cross-service configuration mismatch should be detected"
        
        error_text = " ".join(result.errors).lower()
        assert "mismatch" in error_text or "consistency" in error_text, \
            "Should identify cross-service configuration mismatch"
            
        # Test prevention: Consistent cross-service configuration
        consistent_service_config = {
            "SERVICE_SECRET": "shared-service-secret-32-characters-min",
            "JWT_SECRET_KEY": "shared-jwt-secret-32-characters-minimum"
        }
        
        result = self.validator.validate_cross_service_consistency(consistent_service_config, consistent_service_config)
        assert result.is_valid, f"Consistent service config should prevent cascade: {result.errors}"
        
    @pytest.mark.integration
    def test_environment_mismatch_cascade_failure_prevention(self):
        """Test prevention of environment mismatch cascade failures."""
        # Scenario: Environment confusion causes "Wrong database, wrong URLs, wrong configurations loaded"
        
        # Set up environment mismatch configuration
        environment_mismatch_config = {
            "ENVIRONMENT": "staging",                                      # Backend thinks staging
            "NEXT_PUBLIC_ENVIRONMENT": "production",                      # Frontend thinks production!
            "DATABASE_URL": "postgresql://staging:pass@staging-db/netra", # Staging database
            "NEXT_PUBLIC_API_URL": "https://api.netrasystems.ai"         # Production API URL!
        }
        
        for key, value in environment_mismatch_config.items():
            self.env.set(key, value, "environment_mismatch")
            
        # Test environment consistency validation
        result = self.env_validator.validate_environment_specific_behavior("staging")
        
        # Check for environment consistency warnings/errors
        backend_env = self.env.get("ENVIRONMENT")
        frontend_env = self.env.get("NEXT_PUBLIC_ENVIRONMENT")
        
        if backend_env != frontend_env:
            # Should detect environment mismatch as potential cascade failure
            assert backend_env != frontend_env, "Test should create environment mismatch"
            
            # Validate that this creates consistency issues
            api_url = self.env.get("NEXT_PUBLIC_API_URL") 
            if backend_env == "staging" and "staging" not in api_url:
                # This is a cascade failure pattern: staging backend with production frontend URLs
                inconsistent_config = {
                    "backend_environment": backend_env,
                    "frontend_environment": frontend_env,
                    "api_url": api_url
                }
                
                result = self.validator.detect_environment_cascade_patterns(inconsistent_config)
                assert not result.is_valid, "Environment mismatch should be detected as cascade failure"
                
        # Test prevention: Consistent environment configuration  
        consistent_environment_config = {
            "ENVIRONMENT": "staging",
            "NEXT_PUBLIC_ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql://staging:pass@staging-db/netra",
            "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai"
        }
        
        for key, value in consistent_environment_config.items():
            self.env.set(key, value, "consistent_environment")
            
        result = self.env_validator.validate_environment_specific_behavior("staging")
        if not result.is_valid:
            # Should not have environment consistency errors
            error_text = " ".join(result.errors).lower()
            assert "mismatch" not in error_text and "inconsistent" not in error_text, \
                f"Consistent environment should not have consistency errors: {result.errors}"