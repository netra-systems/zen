"""
Comprehensive Integration Tests for Configuration Management and Environment Isolation

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Deployment Reliability
- Business Goal: Prevent configuration cascade failures that cause complete system outages
- Value Impact: Configuration errors have caused 100% service outages (SERVICE_SECRET missing, wrong domains)
- Strategic Impact: Deployment stability, environment isolation, and configuration correctness are critical
  for multi-environment reliability and preventing the cascade failures documented in 
  MISSION_CRITICAL_NAMED_VALUES_INDEX.xml

Testing Strategy:
- Real configuration systems integration (NO MOCKS)
- Critical environment variables validation from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
- Configuration cascade failure prevention scenarios
- Service configuration discovery and validation
- Multi-environment configuration isolation (dev/staging/prod)
- Configuration regression prevention patterns based on past incidents
- IsolatedEnvironment enforcement (NO direct os.environ access allowed)

CRITICAL SCENARIOS FROM PAST INCIDENTS:
- SERVICE_SECRET missing caused complete system outage (2025-09-05)
- SERVICE_ID with timestamp suffix caused auth failures (2025-09-07)
- Frontend deployment missing environment variables (2025-09-03)
- Discovery endpoint returning localhost URLs in staging (2025-09-02)
- Wrong staging subdomain usage (staging.netrasystems.ai vs api.staging.netrasystems.ai)

This test suite validates configuration integration behavior to prevent the specific
cascade failures that have caused production outages.
"""

import asyncio
import json
import os
import pytest
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4
from urllib.parse import urlparse

# Import SSOT test framework
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.configuration_validator import (
    TestConfigurationValidator,
    get_config_validator,
    validate_test_config,
    is_service_enabled,
    get_service_port
)
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper

# Import shared configuration system
from shared.constants.service_identifiers import SERVICE_ID
from shared.isolated_environment import (
    IsolatedEnvironment,
    get_env,
    ValidationResult,
    SecretLoader,
    EnvironmentValidator
)
from shared.cors_config_builder import CORSConfigurationBuilder
from shared.security_origins_config import SecurityOriginsConfig
from shared.port_discovery import PortDiscovery


class TestConfigurationManagementCriticalIntegration(BaseIntegrationTest):
    """
    Integration tests for configuration management and environment isolation.
    
    These tests validate the real configuration systems that prevent cascade failures.
    """
    
    def setup_method(self):
        """Set up isolated test environment for each test."""
        super().setup_method()
        self.env = get_env()
        self.isolated_helper = IsolatedTestHelper()
        self.config_validator = get_config_validator()
        
    def teardown_method(self):
        """Clean up isolated environment after each test."""
        self.isolated_helper.cleanup_all()
        super().teardown_method()

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_isolated_environment_mandatory_usage(self):
        """
        Test that IsolatedEnvironment is enforced and direct os.environ access is prevented.
        
        Business Value: Prevents configuration drift and environment variable leakage
        between services and users (multi-user isolation requirement).
        
        Critical Scenario: Service configuration must be isolated to prevent cross-service
        contamination that can cause authentication failures.
        """
        # GIVEN: A clean isolated environment
        with self.isolated_helper.create_isolated_context("test_service") as context:
            
            # WHEN: Setting variables through IsolatedEnvironment
            context.env.set("TEST_SERVICE_VAR", "isolated_value", source="test")
            context.env.set("CRITICAL_CONFIG", "secure_value", source="service")
            
            # THEN: Variables are accessible through IsolatedEnvironment
            assert context.env.get("TEST_SERVICE_VAR") == "isolated_value"
            assert context.env.get("CRITICAL_CONFIG") == "secure_value"
            
            # AND: Variables are not leaked to global os.environ
            assert "TEST_SERVICE_VAR" not in os.environ
            assert "CRITICAL_CONFIG" not in os.environ
            
            # AND: Source tracking works
            sources = context.env.get_sources()
            assert "TEST_SERVICE_VAR" in sources["test"]
            assert "CRITICAL_CONFIG" in sources["service"]

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_service_secret_missing_cascade_failure_prevention(self):
        """
        Test prevention of SERVICE_SECRET missing cascade failure.
        
        Business Value: Prevents complete system outage caused by missing SERVICE_SECRET
        that triggers circuit breaker permanent failure state.
        
        Critical Scenario: Missing SERVICE_SECRET caused complete staging outage on 2025-09-05
        with 100% user authentication failure. This test ensures we detect and prevent this.
        """
        # GIVEN: Backend service configuration without SERVICE_SECRET
        with self.isolated_helper.create_isolated_context("backend") as context:
            # Set up minimal backend config without SERVICE_SECRET
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            context.env.set("SERVICE_ID", SERVICE_ID, source="service")
            context.env.set("DATABASE_URL", "postgresql://test:test@localhost:5434/test_db", source="service")
            
            # WHEN: Validating configuration for critical variables
            validator = EnvironmentValidator(context.env)
            result = validator.validate_critical_service_variables("backend")
            
            # THEN: Validation fails due to missing SERVICE_SECRET
            assert not result.is_valid, "Should fail validation without SERVICE_SECRET"
            assert "SERVICE_SECRET" in str(result.errors), "Should specifically identify missing SERVICE_SECRET"
            
            # AND: Error message provides remediation guidance
            error_messages = [str(error) for error in result.errors]
            service_secret_errors = [msg for msg in error_messages if "SERVICE_SECRET" in msg]
            assert len(service_secret_errors) > 0, "Should have specific SERVICE_SECRET error"
            
        # GIVEN: Backend service configuration WITH SERVICE_SECRET
        with self.isolated_helper.create_isolated_context("backend_fixed") as context:
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            context.env.set("SERVICE_ID", SERVICE_ID, source="service")
            context.env.set("SERVICE_SECRET", "test_secret_value", source="secret_manager")
            context.env.set("DATABASE_URL", "postgresql://test:test@localhost:5434/test_db", source="service")
            
            # WHEN: Validating with SERVICE_SECRET present
            validator = EnvironmentValidator(context.env)
            result = validator.validate_critical_service_variables("backend")
            
            # THEN: Validation passes
            assert result.is_valid, f"Should pass validation with SERVICE_SECRET: {result.errors}"

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_service_id_stability_requirement(self):
        """
        Test SERVICE_ID stability requirement prevents authentication failures.
        
        Business Value: Prevents recurring authentication failures caused by SERVICE_ID
        with timestamp suffixes that change every minute.
        
        Critical Scenario: SERVICE_ID with timestamp suffix caused auth failures every
        60 seconds on 2025-09-07. Auth service expects stable SSOT SERVICE_ID value.
        """
        # GIVEN: Service configuration with unstable SERVICE_ID (bad pattern)
        with self.isolated_helper.create_isolated_context("auth_test") as context:
            timestamp_suffix = str(int(time.time()))
            unstable_service_id = f"netra-backend-staging-{timestamp_suffix}"
            
            context.env.set("SERVICE_ID", unstable_service_id, source="environment")
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            
            # WHEN: Validating SERVICE_ID stability
            validator = EnvironmentValidator(context.env)
            result = validator.validate_service_id_stability()
            
            # THEN: Validation fails for unstable SERVICE_ID
            assert not result.is_valid, "Should fail validation for unstable SERVICE_ID"
            error_msg = str(result.errors)
            assert "stable" in error_msg.lower() or "timestamp" in error_msg.lower()
            
        # GIVEN: Service configuration with stable SERVICE_ID (correct pattern)
        with self.isolated_helper.create_isolated_context("auth_test_fixed") as context:
            context.env.set("SERVICE_ID", SERVICE_ID, source="service")
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            
            # WHEN: Validating stable SERVICE_ID
            validator = EnvironmentValidator(context.env)
            result = validator.validate_service_id_stability()
            
            # THEN: Validation passes for stable SERVICE_ID
            assert result.is_valid, f"Should pass validation for stable SERVICE_ID: {result.errors}"

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_frontend_critical_environment_variables_validation(self):
        """
        Test validation of critical frontend environment variables.
        
        Business Value: Prevents frontend deployment failures that break all user access.
        
        Critical Scenario: Frontend deployment missing environment variables on 2025-09-03
        caused complete frontend failure with no WebSocket, no auth, no API access.
        """
        critical_frontend_vars = [
            "NEXT_PUBLIC_API_URL",
            "NEXT_PUBLIC_WS_URL", 
            "NEXT_PUBLIC_AUTH_URL",
            "NEXT_PUBLIC_ENVIRONMENT"
        ]
        
        # Test each critical variable missing
        for missing_var in critical_frontend_vars:
            with self.isolated_helper.create_isolated_context(f"frontend_missing_{missing_var}") as context:
                # GIVEN: Frontend config missing one critical variable
                for var in critical_frontend_vars:
                    if var != missing_var:
                        if var == "NEXT_PUBLIC_API_URL":
                            context.env.set(var, "https://api.staging.netrasystems.ai", source="deployment")
                        elif var == "NEXT_PUBLIC_WS_URL":
                            context.env.set(var, "wss://api.staging.netrasystems.ai", source="deployment")
                        elif var == "NEXT_PUBLIC_AUTH_URL":
                            context.env.set(var, "https://auth.staging.netrasystems.ai", source="deployment")
                        elif var == "NEXT_PUBLIC_ENVIRONMENT":
                            context.env.set(var, "staging", source="deployment")
                
                # WHEN: Validating frontend configuration
                validator = EnvironmentValidator(context.env)
                result = validator.validate_frontend_critical_variables()
                
                # THEN: Validation fails for missing critical variable
                assert not result.is_valid, f"Should fail validation missing {missing_var}"
                assert missing_var in str(result.errors), f"Should identify missing {missing_var}"

        # GIVEN: Complete frontend configuration
        with self.isolated_helper.create_isolated_context("frontend_complete") as context:
            context.env.set("NEXT_PUBLIC_API_URL", "https://api.staging.netrasystems.ai", source="deployment")
            context.env.set("NEXT_PUBLIC_WS_URL", "wss://api.staging.netrasystems.ai", source="deployment")
            context.env.set("NEXT_PUBLIC_AUTH_URL", "https://auth.staging.netrasystems.ai", source="deployment")
            context.env.set("NEXT_PUBLIC_ENVIRONMENT", "staging", source="deployment")
            
            # WHEN: Validating complete frontend config
            validator = EnvironmentValidator(context.env)
            result = validator.validate_frontend_critical_variables()
            
            # THEN: Validation passes with all variables present
            assert result.is_valid, f"Should pass validation with all frontend vars: {result.errors}"

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_staging_domain_configuration_validation(self):
        """
        Test correct staging domain configuration to prevent API connection failures.
        
        Business Value: Prevents staging domain confusion that breaks API connectivity.
        
        Critical Scenario: Wrong staging subdomain usage (staging.netrasystems.ai vs 
        api.staging.netrasystems.ai) caused API calls to fail and WebSocket connection failures.
        """
        incorrect_staging_patterns = [
            "https://staging.netrasystems.ai",  # Wrong: should be api.staging
            "http://staging.netrasystems.ai",   # Wrong: HTTP + wrong subdomain
            "https://netra-staging.com",        # Wrong: completely wrong domain
            "http://localhost:8000",            # Wrong: localhost in staging
        ]
        
        # Test each incorrect pattern
        for incorrect_url in incorrect_staging_patterns:
            with self.isolated_helper.create_isolated_context(f"staging_domain_test") as context:
                context.env.set("ENVIRONMENT", "staging", source="deployment")
                context.env.set("NEXT_PUBLIC_API_URL", incorrect_url, source="deployment")
                
                # WHEN: Validating staging domain configuration
                validator = EnvironmentValidator(context.env)
                result = validator.validate_staging_domain_configuration()
                
                # THEN: Validation fails for incorrect domain patterns
                assert not result.is_valid, f"Should fail validation for incorrect URL: {incorrect_url}"
                error_msg = str(result.errors).lower()
                assert any(keyword in error_msg for keyword in ["domain", "staging", "api"]), \
                    f"Should provide domain-related error for {incorrect_url}"

        # GIVEN: Correct staging domain configuration
        with self.isolated_helper.create_isolated_context("staging_domain_correct") as context:
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            context.env.set("NEXT_PUBLIC_API_URL", "https://api.staging.netrasystems.ai", source="deployment")
            context.env.set("NEXT_PUBLIC_WS_URL", "wss://api.staging.netrasystems.ai", source="deployment")
            context.env.set("NEXT_PUBLIC_AUTH_URL", "https://auth.staging.netrasystems.ai", source="deployment")
            
            # WHEN: Validating correct staging domains
            validator = EnvironmentValidator(context.env)
            result = validator.validate_staging_domain_configuration()
            
            # THEN: Validation passes for correct domains
            assert result.is_valid, f"Should pass validation for correct staging domains: {result.errors}"

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_cors_configuration_validation(self):
        """
        Test CORS configuration validation for preventing cross-origin issues.
        
        Business Value: Prevents CORS-related API access failures that break frontend functionality.
        
        Critical Scenario: Incorrect CORS allowed origins can block frontend from accessing APIs,
        causing complete frontend dysfunction even when services are running.
        """
        # GIVEN: CORS configuration builder
        with self.isolated_helper.create_isolated_context("cors_test") as context:
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            
            cors_builder = CORSConfigurationBuilder(context.env)
            
            # WHEN: Building CORS config for staging
            cors_config = cors_builder.build_cors_config()
            
            # THEN: CORS config includes expected staging origins
            expected_origins = [
                "https://app.staging.netrasystems.ai",
                "https://api.staging.netrasystems.ai", 
                "https://auth.staging.netrasystems.ai"
            ]
            
            actual_origins = cors_config.get("allow_origins", [])
            for expected in expected_origins:
                assert expected in actual_origins, f"Missing expected CORS origin: {expected}"
            
            # AND: No localhost origins in staging
            localhost_origins = [origin for origin in actual_origins if "localhost" in origin]
            assert len(localhost_origins) == 0, f"Staging should not have localhost origins: {localhost_origins}"
            
            # AND: Only HTTPS origins in staging (no HTTP)
            http_origins = [origin for origin in actual_origins if origin.startswith("http://")]
            assert len(http_origins) == 0, f"Staging should only have HTTPS origins: {http_origins}"

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_discovery_endpoint_localhost_prevention(self):
        """
        Test prevention of localhost URLs in discovery endpoint for non-local environments.
        
        Business Value: Prevents discovery endpoint configuration errors that break service connectivity.
        
        Critical Scenario: Discovery endpoint returning localhost URLs in staging on 2025-09-02
        caused frontend to be unable to connect to services.
        """
        # GIVEN: Discovery configuration for staging environment
        with self.isolated_helper.create_isolated_context("discovery_staging") as context:
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            context.env.set("SERVICE_DISCOVERY_MODE", "environment_based", source="service")
            
            # Mock discovery data with localhost URLs (bad configuration)
            discovery_data = {
                "backend_url": "http://localhost:8000",  # Wrong: localhost in staging
                "auth_url": "http://localhost:8081",     # Wrong: localhost in staging
                "websocket_url": "ws://localhost:8000/ws"  # Wrong: localhost in staging
            }
            
            # WHEN: Validating discovery endpoint configuration
            validator = EnvironmentValidator(context.env)
            result = validator.validate_discovery_endpoint_configuration(discovery_data)
            
            # THEN: Validation fails for localhost URLs in staging
            assert not result.is_valid, "Should fail validation for localhost URLs in staging"
            error_msg = str(result.errors).lower()
            assert "localhost" in error_msg, "Should specifically identify localhost issue"

        # GIVEN: Correct discovery configuration for staging
        with self.isolated_helper.create_isolated_context("discovery_staging_fixed") as context:
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            context.env.set("SERVICE_DISCOVERY_MODE", "environment_based", source="service")
            
            # Correct discovery data with proper staging URLs
            discovery_data = {
                "backend_url": "https://api.staging.netrasystems.ai",
                "auth_url": "https://auth.staging.netrasystems.ai",
                "websocket_url": "wss://api.staging.netrasystems.ai/ws"
            }
            
            # WHEN: Validating correct discovery configuration
            validator = EnvironmentValidator(context.env)
            result = validator.validate_discovery_endpoint_configuration(discovery_data)
            
            # THEN: Validation passes for proper staging URLs
            assert result.is_valid, f"Should pass validation for proper staging URLs: {result.errors}"

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_multi_environment_configuration_isolation(self):
        """
        Test that different environments have properly isolated configurations.
        
        Business Value: Ensures environment-specific configurations don't leak between
        development, staging, and production environments.
        
        Critical Scenario: Configuration leakage between environments can cause data 
        corruption, wrong database access, or security breaches.
        """
        environments = ["development", "staging", "production"]
        
        # Test each environment has isolated configuration
        env_contexts = {}
        for env_name in environments:
            context = self.isolated_helper.create_isolated_context(f"env_{env_name}")
            env_contexts[env_name] = context.__enter__()
            
            # Set environment-specific configuration
            context = env_contexts[env_name]
            context.env.set("ENVIRONMENT", env_name, source="deployment")
            
            if env_name == "development":
                context.env.set("DATABASE_URL", "postgresql://dev:dev@localhost:5432/dev_db", source="service")
                context.env.set("NEXT_PUBLIC_API_URL", "http://localhost:8000", source="service")
                context.env.set("DEBUG", "true", source="development")
            elif env_name == "staging":
                context.env.set("DATABASE_URL", "postgresql://staging:staging@staging-db:5432/staging_db", source="service")
                context.env.set("NEXT_PUBLIC_API_URL", "https://api.staging.netrasystems.ai", source="service")
                context.env.set("DEBUG", "false", source="deployment")
            elif env_name == "production":
                context.env.set("DATABASE_URL", "postgresql://prod:prod@prod-db:5432/prod_db", source="service")
                context.env.set("NEXT_PUBLIC_API_URL", "https://api.netrasystems.ai", source="service")
                context.env.set("DEBUG", "false", source="deployment")
        
        try:
            # WHEN: Checking environment isolation
            dev_context = env_contexts["development"]
            staging_context = env_contexts["staging"]
            prod_context = env_contexts["production"]
            
            # THEN: Each environment has its own isolated configuration
            assert dev_context.env.get("DATABASE_URL") != staging_context.env.get("DATABASE_URL")
            assert staging_context.env.get("DATABASE_URL") != prod_context.env.get("DATABASE_URL")
            assert dev_context.env.get("NEXT_PUBLIC_API_URL") != staging_context.env.get("NEXT_PUBLIC_API_URL")
            
            # AND: Environment-specific values are correct
            assert "localhost" in dev_context.env.get("NEXT_PUBLIC_API_URL")
            assert "staging.netrasystems.ai" in staging_context.env.get("NEXT_PUBLIC_API_URL")
            assert "api.netrasystems.ai" in prod_context.env.get("NEXT_PUBLIC_API_URL")
            assert "staging.netrasystems.ai" not in prod_context.env.get("NEXT_PUBLIC_API_URL")
            
            # AND: Debug settings are environment-appropriate
            assert dev_context.env.get("DEBUG") == "true"
            assert staging_context.env.get("DEBUG") == "false"
            assert prod_context.env.get("DEBUG") == "false"
            
        finally:
            # Clean up all environment contexts
            for context in env_contexts.values():
                context.__exit__(None, None, None)

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_configuration_validation_integration(self):
        """
        Test integration of configuration validation with real SSOT validator.
        
        Business Value: Validates that the SSOT configuration validator correctly
        identifies real configuration issues before they cause outages.
        """
        # GIVEN: Configuration with multiple validation issues
        with self.isolated_helper.create_isolated_context("validation_test") as context:
            # Set up problematic configuration
            context.env.set("ENVIRONMENT", "invalid_env", source="test")  # Invalid environment
            context.env.set("POSTGRES_PORT", "not_a_number", source="test")  # Invalid port
            context.env.set("CLICKHOUSE_ENABLED", "true", source="test")
            context.env.set("TEST_DISABLE_CLICKHOUSE", "true", source="test")  # Conflicting flags
            
            # WHEN: Running comprehensive configuration validation
            validator = TestConfigurationValidator()
            validator.env = context.env
            
            env_valid, env_errors = validator.validate_test_environment("backend")
            flags_valid, flag_errors = validator.validate_service_flags()
            
            # THEN: Validation correctly identifies multiple issues
            assert not env_valid, "Should fail environment validation"
            assert not flags_valid, "Should fail service flag validation"
            
            # AND: Specific errors are identified
            all_errors = env_errors + flag_errors
            error_text = " ".join(all_errors).lower()
            assert "environment" in error_text or "invalid" in error_text
            assert "clickhouse" in error_text or "conflict" in error_text

        # GIVEN: Correct configuration
        with self.isolated_helper.create_isolated_context("validation_correct") as context:
            context.env.set("ENVIRONMENT", "testing", source="test")
            context.env.set("TESTING", "1", source="test")
            context.env.set("JWT_SECRET_KEY", "test_jwt_key", source="test")
            context.env.set("SERVICE_SECRET", "test_service_secret", source="test")
            context.env.set("POSTGRES_PORT", "5434", source="test")
            context.env.set("CLICKHOUSE_ENABLED", "false", source="test")
            
            # WHEN: Running validation on correct configuration
            validator = TestConfigurationValidator()
            validator.env = context.env
            
            env_valid, env_errors = validator.validate_test_environment("backend")
            flags_valid, flag_errors = validator.validate_service_flags()
            
            # THEN: Validation passes
            assert env_valid, f"Should pass environment validation: {env_errors}"
            assert flags_valid, f"Should pass service flag validation: {flag_errors}"

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_port_discovery_and_allocation(self):
        """
        Test port discovery and allocation to prevent port conflicts.
        
        Business Value: Prevents service startup failures due to port conflicts
        that can cascade to test failures and deployment issues.
        """
        # GIVEN: Port discovery configuration
        with self.isolated_helper.create_isolated_context("port_discovery") as context:
            context.env.set("ENVIRONMENT", "testing", source="test")
            
            port_discovery = PortDiscovery(context.env)
            
            # WHEN: Discovering ports for different services
            backend_port = port_discovery.get_service_port("backend", "postgres")
            auth_port = port_discovery.get_service_port("auth", "postgres") 
            redis_port = port_discovery.get_service_port("backend", "redis")
            
            # THEN: Each service gets a unique port
            assert backend_port != auth_port, "Backend and auth should have different PostgreSQL ports"
            assert backend_port != redis_port, "PostgreSQL and Redis should have different ports"
            
            # AND: Ports are in expected ranges
            assert 5433 <= backend_port <= 5436, f"Backend PostgreSQL port should be in test range: {backend_port}"
            assert 6380 <= redis_port <= 6382, f"Redis port should be in test range: {redis_port}"

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_secret_loading_and_masking(self):
        """
        Test secret loading and masking functionality for security.
        
        Business Value: Ensures sensitive configuration values are properly handled
        and not exposed in logs or error messages.
        """
        # GIVEN: Configuration with sensitive values
        with self.isolated_helper.create_isolated_context("secrets_test") as context:
            secret_loader = SecretLoader(context.env)
            
            sensitive_values = {
                "JWT_SECRET_KEY": "super_secret_jwt_key_12345",
                "SERVICE_SECRET": "inter_service_secret_67890", 
                "DATABASE_PASSWORD": "db_password_abcdef",
                "API_KEY": "api_key_xyz123"
            }
            
            # WHEN: Loading and masking sensitive values
            for key, value in sensitive_values.items():
                context.env.set(key, value, source="secret_manager")
                
                # Get masked value for logging
                masked_value = secret_loader.get_masked_value(key)
                
                # THEN: Sensitive values are properly masked
                assert masked_value != value, f"Value should be masked: {key}"
                assert len(masked_value) < len(value), f"Masked value should be shorter: {key}"
                assert "*" in masked_value or "..." in masked_value, f"Masked value should contain masking chars: {key}"
            
            # AND: Non-sensitive values are not masked
            context.env.set("ENVIRONMENT", "testing", source="test")
            context.env.set("DEBUG", "true", source="test")
            
            env_masked = secret_loader.get_masked_value("ENVIRONMENT")
            debug_masked = secret_loader.get_masked_value("DEBUG")
            
            assert env_masked == "testing", "Non-sensitive values should not be masked"
            assert debug_masked == "true", "Non-sensitive values should not be masked"

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_configuration_change_tracking(self):
        """
        Test configuration change tracking for debugging and audit purposes.
        
        Business Value: Enables debugging of configuration issues by tracking
        when and where configuration values were set.
        """
        # GIVEN: Configuration tracking setup
        with self.isolated_helper.create_isolated_context("change_tracking") as context:
            # WHEN: Setting configuration values from different sources
            context.env.set("DATABASE_URL", "initial_value", source="default")
            context.env.set("DATABASE_URL", "env_override", source="environment")
            context.env.set("DEBUG", "false", source="deployment")
            context.env.set("DEBUG", "true", source="development_override")
            
            # THEN: Change history is tracked
            db_history = context.env.get_change_history("DATABASE_URL")
            debug_history = context.env.get_change_history("DEBUG")
            
            assert len(db_history) == 2, "Should track both DATABASE_URL changes"
            assert len(debug_history) == 2, "Should track both DEBUG changes"
            
            # AND: Latest values are correct
            assert context.env.get("DATABASE_URL") == "env_override"
            assert context.env.get("DEBUG") == "true"
            
            # AND: Sources are tracked correctly
            sources = context.env.get_sources()
            assert "DATABASE_URL" in sources["environment"]
            assert "DEBUG" in sources["development_override"]

    @pytest.mark.integration 
    @pytest.mark.configuration
    def test_configuration_validation_error_reporting(self):
        """
        Test comprehensive error reporting for configuration validation issues.
        
        Business Value: Provides clear, actionable error messages that help developers
        quickly identify and fix configuration issues before deployment.
        """
        # GIVEN: Multiple configuration validation issues
        with self.isolated_helper.create_isolated_context("error_reporting") as context:
            # Set up configuration with multiple issues
            context.env.set("ENVIRONMENT", "staging", source="test")
            context.env.set("NEXT_PUBLIC_API_URL", "http://localhost:8000", source="test")  # Wrong for staging
            # Missing SERVICE_SECRET (critical)
            # Missing JWT_SECRET_KEY (critical)
            context.env.set("POSTGRES_PORT", "invalid_port", source="test")  # Invalid format
            
            # WHEN: Running validation and collecting all errors
            validator = EnvironmentValidator(context.env)
            
            # Validate different aspects
            service_result = validator.validate_critical_service_variables("backend")
            frontend_result = validator.validate_frontend_critical_variables()
            staging_result = validator.validate_staging_domain_configuration()
            
            # THEN: All validation results provide detailed error information
            assert not service_result.is_valid
            assert not frontend_result.is_valid  
            assert not staging_result.is_valid
            
            # AND: Error messages are actionable and specific
            all_errors = []
            all_errors.extend(service_result.errors)
            all_errors.extend(frontend_result.errors)
            all_errors.extend(staging_result.errors)
            
            error_text = " ".join(str(error) for error in all_errors).lower()
            
            # Should identify specific missing variables
            assert "service_secret" in error_text
            assert "jwt_secret" in error_text
            
            # Should identify staging domain issue
            assert "localhost" in error_text or "staging" in error_text
            
            # Should provide remediation guidance
            remediation_keywords = ["remedy", "set", "should", "use", "fix"]
            has_remediation = any(keyword in error_text for keyword in remediation_keywords)
            assert has_remediation, "Error messages should provide remediation guidance"

    @pytest.mark.integration
    @pytest.mark.configuration
    def test_environment_specific_behavior_validation(self):
        """
        Test validation of environment-specific behavior requirements.
        
        Business Value: Ensures that each environment (dev/staging/prod) has
        appropriate configuration that matches its intended usage patterns.
        """
        environment_configs = {
            "development": {
                "DEBUG": "true",
                "DATABASE_URL": "sqlite:///dev.db",
                "NEXT_PUBLIC_API_URL": "http://localhost:8000",
                "ALLOW_ORIGIN": "*",
                "LOG_LEVEL": "DEBUG"
            },
            "staging": {
                "DEBUG": "false", 
                "DATABASE_URL": "postgresql://staging:staging@staging-db/staging_db",
                "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
                "ALLOW_ORIGIN": "https://app.staging.netrasystems.ai",
                "LOG_LEVEL": "INFO"
            },
            "production": {
                "DEBUG": "false",
                "DATABASE_URL": "postgresql://prod:prod@prod-db/prod_db", 
                "NEXT_PUBLIC_API_URL": "https://api.netrasystems.ai",
                "ALLOW_ORIGIN": "https://app.netrasystems.ai",
                "LOG_LEVEL": "WARNING"
            }
        }
        
        for env_name, config in environment_configs.items():
            with self.isolated_helper.create_isolated_context(f"env_behavior_{env_name}") as context:
                # GIVEN: Environment-specific configuration
                context.env.set("ENVIRONMENT", env_name, source="deployment")
                for key, value in config.items():
                    context.env.set(key, value, source="environment")
                
                # WHEN: Validating environment-specific behavior
                validator = EnvironmentValidator(context.env)
                result = validator.validate_environment_specific_behavior(env_name)
                
                # THEN: Environment configuration is appropriate
                assert result.is_valid, f"Environment {env_name} should have valid config: {result.errors}"
                
                # AND: Verify specific environment characteristics
                if env_name == "development":
                    assert context.env.get("DEBUG") == "true", "Development should have debug enabled"
                    assert "localhost" in context.env.get("NEXT_PUBLIC_API_URL"), "Development should use localhost"
                
                elif env_name == "staging":
                    assert context.env.get("DEBUG") == "false", "Staging should have debug disabled"
                    assert "staging.netrasystems.ai" in context.env.get("NEXT_PUBLIC_API_URL"), "Staging should use staging domain"
                    assert "localhost" not in context.env.get("NEXT_PUBLIC_API_URL"), "Staging should not use localhost"
                
                elif env_name == "production":
                    assert context.env.get("DEBUG") == "false", "Production should have debug disabled"
                    assert "netrasystems.ai" in context.env.get("NEXT_PUBLIC_API_URL"), "Production should use production domain"
                    assert "staging" not in context.env.get("NEXT_PUBLIC_API_URL"), "Production should not use staging domain"
                    assert "localhost" not in context.env.get("NEXT_PUBLIC_API_URL"), "Production should not use localhost"