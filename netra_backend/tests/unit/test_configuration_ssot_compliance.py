"""
Test Configuration SSOT (Single Source of Truth) Compliance - Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - Configuration SSOT validation and compliance
- Business Goal: Ensure single source of truth for all configuration patterns
- Value Impact: Prevents configuration duplication that leads to inconsistencies and failures
- Strategic Impact: CRITICAL - Configuration drift costs $12K MRR through cascade failures

CRITICAL: These tests validate SSOT compliance for configuration management,
preventing the "duplicate configuration" anti-pattern that causes cascade failures.
"""

import pytest
from unittest.mock import Mock, patch
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.configuration.central_config_validator import CentralConfigurationValidator


class TestConfigurationSSOTCompliance(BaseTestCase):
    """Test SSOT compliance validation for configuration management."""
    
    def setup_method(self):
        """Setup test environment with SSOT validation."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
        
        # Set test environment
        self.env.set("ENVIRONMENT", "test", "test_setup")
        self.env.set("TESTING", "true", "test_setup")
        
        self.validator = CentralConfigurationValidator(env_manager=self.env)
        
    def teardown_method(self):
        """Clean up test environment."""
        self.env.reset_to_original() 
        super().teardown_method()

    @pytest.mark.unit
    def test_database_url_ssot_validation_prevents_duplication(self):
        """Test that database URL SSOT validation prevents configuration duplication."""
        # Test SSOT-compliant configuration (component-based)
        ssot_config = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass", 
            "POSTGRES_DB": "testdb",
            "POSTGRES_PORT": "5432"
        }
        
        for key, value in ssot_config.items():
            self.env.set(key, value, "ssot_compliant")
            
        # Should pass SSOT validation
        result = self.validator.validate_database_ssot_compliance(ssot_config)
        assert result.is_valid, f"SSOT-compliant database config should pass: {result.errors}"
        
        # Test non-SSOT configuration (direct DATABASE_URL)
        non_ssot_config = {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
            # Missing component variables - violates SSOT
        }
        
        result = self.validator.validate_database_ssot_compliance(non_ssot_config)
        assert not result.is_valid, "Direct DATABASE_URL access should violate SSOT"
        
        error_text = " ".join(result.errors)
        assert "ssot" in error_text.lower() or "single source" in error_text.lower(), \
            "Should identify SSOT violation"
            
        # Test duplicate configuration (both SSOT and non-SSOT present)
        duplicate_config = ssot_config.copy()
        duplicate_config["DATABASE_URL"] = "postgresql://duplicate:config@localhost:5432/db"
        
        result = self.validator.validate_database_ssot_compliance(duplicate_config)
        assert not result.is_valid, "Duplicate database configuration should be rejected"
        
        error_text = " ".join(result.errors)
        assert "duplicate" in error_text.lower(), "Should identify configuration duplication"
        
    @pytest.mark.unit
    def test_jwt_secret_ssot_validation_prevents_inconsistency(self):
        """Test that JWT secret SSOT validation prevents cross-service inconsistencies."""
        # Mock unified JWT secret manager
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret') as mock_jwt:
            mock_jwt.return_value = "unified-jwt-secret-32-characters-minimum"
            
            # Test SSOT-compliant JWT usage
            self.env.set("JWT_SECRET_KEY", "service-specific-but-consistent-32-chars", "service_config")
            
            result = self.validator.validate_jwt_ssot_compliance()
            
            # Should either pass (if using unified manager) or warn about inconsistency
            if not result.is_valid:
                warning_text = " ".join(result.warnings)
                assert "unified" in warning_text.lower() or "consistency" in warning_text.lower(), \
                    "Should warn about JWT consistency"
                    
            # Test multiple JWT configurations (violates SSOT)
            jwt_configs = {
                "JWT_SECRET_KEY": "backend-jwt-secret-32-characters-minimum",
                "JWT_SECRET_STAGING": "staging-jwt-secret-32-characters-minimum", 
                "JWT_SECRET_PRODUCTION": "production-jwt-secret-32-characters-minimum"
            }
            
            for key, value in jwt_configs.items():
                self.env.set(key, value, "multiple_jwt_config")
                
            result = self.validator.validate_jwt_ssot_compliance()
            assert not result.is_valid, "Multiple JWT configurations should violate SSOT"
            
            error_text = " ".join(result.errors)
            assert "multiple" in error_text.lower() or "ssot" in error_text.lower(), \
                "Should identify multiple JWT configuration violation"
                
    @pytest.mark.unit
    def test_oauth_configuration_ssot_validation_dual_pattern(self):
        """Test SSOT validation for OAuth dual naming pattern compliance."""
        # Test backend service SSOT pattern (simplified names)
        backend_oauth_ssot = {
            "GOOGLE_CLIENT_ID": "backend-oauth-client-unified",
            "GOOGLE_CLIENT_SECRET": "backend-oauth-secret-unified",
            "oauth_pattern": "backend_simplified"
        }
        
        result = self.validator.validate_oauth_ssot_compliance(backend_oauth_ssot, "backend")
        assert result.is_valid, f"Backend OAuth SSOT pattern should pass: {result.errors}"
        
        # Test auth service SSOT pattern (environment-specific names)
        auth_oauth_ssot = {
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "auth-staging-client-unified",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "auth-staging-secret-unified", 
            "oauth_pattern": "auth_environment_specific"
        }
        
        result = self.validator.validate_oauth_ssot_compliance(auth_oauth_ssot, "auth")
        assert result.is_valid, f"Auth OAuth SSOT pattern should pass: {result.errors}"
        
        # Test mixed OAuth patterns (violates SSOT consistency)
        mixed_oauth = {
            "GOOGLE_CLIENT_ID": "backend-style",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "auth-style",
            "GOOGLE_CLIENT_SECRET": "backend-secret",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "auth-secret"
        }
        
        result = self.validator.validate_oauth_ssot_compliance(mixed_oauth, "mixed")
        assert len(result.warnings) > 0, "Mixed OAuth patterns should generate SSOT warnings"
        
        warning_text = " ".join(result.warnings) 
        assert "pattern" in warning_text.lower() or "consistency" in warning_text.lower(), \
            "Should warn about pattern consistency"
            
    @pytest.mark.unit
    def test_environment_configuration_ssot_prevents_duplication(self):
        """Test that environment configuration SSOT prevents duplicate environment definitions."""
        # Test single environment definition (SSOT compliant)
        single_env_config = {
            "ENVIRONMENT": "staging",
            # No duplicates
        }
        
        self.env.set("ENVIRONMENT", "staging", "ssot_env")
        
        result = self.validator.validate_environment_ssot_compliance(single_env_config)
        assert result.is_valid, f"Single environment definition should pass: {result.errors}"
        
        # Test duplicate environment definitions (violates SSOT)
        duplicate_env_config = {
            "ENVIRONMENT": "staging",
            "ENV": "staging", 
            "RUNTIME_ENV": "staging",
            "APP_ENV": "staging"  # Multiple ways to define environment violates SSOT
        }
        
        result = self.validator.validate_environment_ssot_compliance(duplicate_env_config)
        assert not result.is_valid, "Duplicate environment definitions should violate SSOT"
        
        error_text = " ".join(result.errors)
        assert "duplicate" in error_text.lower() or "multiple" in error_text.lower(), \
            "Should identify duplicate environment definitions"
            
        # Test environment-specific variable consolidation
        # Instead of separate variables for each environment, should use single variable with environment detection
        non_consolidated_config = {
            "DATABASE_URL_DEV": "postgresql://localhost:5432/dev",
            "DATABASE_URL_STAGING": "postgresql://staging:5432/staging",
            "DATABASE_URL_PROD": "postgresql://prod:5432/prod"  # Violates SSOT - should use single DATABASE_URL with environment detection
        }
        
        result = self.validator.validate_environment_ssot_compliance(non_consolidated_config)
        assert not result.is_valid, "Environment-specific variable duplication should violate SSOT"
        
    @pytest.mark.unit
    def test_service_configuration_ssot_consolidation_validation(self):
        """Test that service configuration consolidation follows SSOT principles."""
        # Test consolidated service configuration (SSOT compliant)
        consolidated_config = {
            "service_configs": {
                "backend": {
                    "port": 8000,
                    "name": "netra-backend"
                },
                "auth": {
                    "port": 8081, 
                    "name": "netra-auth"
                }
            },
            "configuration_pattern": "consolidated"
        }
        
        result = self.validator.validate_service_ssot_compliance(consolidated_config)
        assert result.is_valid, f"Consolidated service config should pass: {result.errors}"
        
        # Test fragmented service configuration (violates SSOT)
        fragmented_config = {
            "BACKEND_PORT": 8000,
            "BACKEND_NAME": "netra-backend",
            "BACKEND_HOST": "localhost",
            "AUTH_PORT": 8081,
            "AUTH_NAME": "netra-auth", 
            "AUTH_HOST": "localhost",
            "FRONTEND_PORT": 3000,
            "FRONTEND_NAME": "netra-frontend",
            "FRONTEND_HOST": "localhost",  # Fragmented across multiple variables
            "configuration_pattern": "fragmented"
        }
        
        result = self.validator.validate_service_ssot_compliance(fragmented_config)
        assert not result.is_valid, "Fragmented service configuration should violate SSOT"
        
        error_text = " ".join(result.errors)
        assert "consolidation" in error_text.lower() or "ssot" in error_text.lower(), \
            "Should identify need for configuration consolidation"
            
    @pytest.mark.unit
    def test_websocket_event_ssot_validation_prevents_duplication(self):
        """Test WebSocket event SSOT validation prevents duplicate event definitions."""
        # Test SSOT-compliant WebSocket events (centralized definition)
        ssot_events = {
            "event_definitions": {
                "agent_started": {"payload": ["run_id", "agent_name"], "critical": True},
                "agent_thinking": {"payload": ["run_id", "thought"], "critical": True},
                "tool_executing": {"payload": ["run_id", "tool_name", "args"], "critical": True},
                "tool_completed": {"payload": ["run_id", "tool_name", "result"], "critical": True},
                "agent_completed": {"payload": ["run_id", "result"], "critical": True}
            },
            "definition_source": "central_websocket_events.py"
        }
        
        result = self.validator.validate_websocket_events_ssot_compliance(ssot_events)
        assert result.is_valid, f"SSOT WebSocket events should pass: {result.errors}"
        
        # Test duplicate event definitions (violates SSOT)
        duplicate_events = {
            # Events defined in multiple places
            "backend_events": {
                "agent_started": {"payload": ["run_id", "agent_name"]},
            },
            "supervisor_events": {
                "agent_started": {"payload": ["run_id", "agent_name", "context"]}, # Different payload!
            },
            "websocket_events": {
                "agent_started": {"payload": ["run_id"]}, # Yet another definition!
            }
        }
        
        result = self.validator.validate_websocket_events_ssot_compliance(duplicate_events)
        assert not result.is_valid, "Duplicate WebSocket event definitions should violate SSOT"
        
        error_text = " ".join(result.errors)
        assert "duplicate" in error_text.lower() and "agent_started" in error_text, \
            "Should identify duplicate agent_started definitions"
            
        # Test event payload inconsistency
        inconsistent_events = {
            "event_definitions": {
                "agent_started": {"payload": ["run_id", "agent_name"]},
                "agent_started_v2": {"payload": ["run_id", "agent_name", "extra_field"]}, # Similar but different
            }
        }
        
        result = self.validator.validate_websocket_events_ssot_compliance(inconsistent_events)
        assert len(result.warnings) > 0, "Similar event definitions should generate warnings"
        
    @pytest.mark.unit
    def test_configuration_consolidation_detection_algorithm(self):
        """Test algorithm that detects opportunities for configuration consolidation."""
        # Test configuration that needs consolidation
        needs_consolidation = {
            # Multiple similar variables that should be consolidated
            "POSTGRES_HOST": "localhost",
            "REDIS_HOST": "localhost", 
            "CLICKHOUSE_HOST": "localhost",
            "LANGFUSE_HOST": "localhost",  # Pattern: multiple *_HOST variables
            
            "POSTGRES_PORT": "5432",
            "REDIS_PORT": "6379",
            "CLICKHOUSE_PORT": "8123",  # Pattern: multiple *_PORT variables
            
            "POSTGRES_PASSWORD": "pass1",
            "REDIS_PASSWORD": "pass2", 
            "CLICKHOUSE_PASSWORD": "pass3"  # Pattern: multiple *_PASSWORD variables
        }
        
        consolidation_opportunities = self.validator.detect_consolidation_opportunities(needs_consolidation)
        
        assert len(consolidation_opportunities) > 0, "Should detect consolidation opportunities"
        
        # Should detect HOST pattern
        host_pattern = next((opp for opp in consolidation_opportunities if "HOST" in opp["pattern"]), None)
        assert host_pattern is not None, "Should detect HOST variable pattern"
        assert len(host_pattern["variables"]) >= 3, "Should identify multiple HOST variables"
        
        # Should detect PORT pattern  
        port_pattern = next((opp for opp in consolidation_opportunities if "PORT" in opp["pattern"]), None)
        assert port_pattern is not None, "Should detect PORT variable pattern"
        
        # Test already consolidated configuration
        consolidated = {
            "database_connections": {
                "postgres": {"host": "localhost", "port": 5432, "password": "pass1"},
                "redis": {"host": "localhost", "port": 6379, "password": "pass2"},
                "clickhouse": {"host": "localhost", "port": 8123, "password": "pass3"}
            }
        }
        
        consolidation_opportunities = self.validator.detect_consolidation_opportunities(consolidated)
        assert len(consolidation_opportunities) == 0, "Consolidated config should not need further consolidation"