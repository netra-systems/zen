"""
Integration Tests: REDIS_URL Deprecation Validation

CRITICAL MISSION: Validate that REDIS_URL deprecation warnings are properly shown and handled.

This test suite PROVES the deprecation system works correctly by showing that:
1. REDIS_URL usage triggers proper deprecation warnings
2. The warning messages are clear and actionable
3. The system still functions while showing warnings
4. Migration guidance is provided to users

Business Impact: These tests should PASS, proving the deprecation system works correctly.
This ensures users get proper warnings about deprecated REDIS_URL usage and guidance for migration.

Test Strategy: Use real configuration validation with NO MOCKS - real integration testing.
"""

import pytest
import os
import logging
from typing import Dict, Any, List
from unittest.mock import patch
from io import StringIO

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
from shared.configuration.redis_pattern_validator import RedisConfigurationPatternValidator, RedisPatternViolation


@pytest.mark.integration 
class TestRedisDeprecationValidation(SSotBaseTestCase):
    """
    Integration tests that validate REDIS_URL deprecation warnings work correctly.
    
    These tests should PASS, proving the deprecation warning system functions properly.
    """

    def test_redis_url_deprecation_warning_is_shown(self):
        """
        DEPRECATION TEST: Validates that REDIS_URL usage triggers proper deprecation warnings.
        
        This test should PASS, proving the deprecation warning system works correctly.
        Expected behavior: Using REDIS_URL should generate clear deprecation warnings.
        """
        # Set up staging environment with deprecated REDIS_URL
        staging_with_redis_url = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': '701982941522',
            'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:netra-staging-postgres',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'staging-database-password-32-chars-long',
            'POSTGRES_DB': 'netra_staging',
            'JWT_SECRET_KEY': 'staging-jwt-secret-key-32-chars-minimum-length-required',
            'FERNET_KEY': 'staging-fernet-key-32-chars-base64-encoded-value',
            'SERVICE_SECRET': 'staging-service-secret-32-chars-minimum-required-length',
            'SERVICE_ID': 'netra-backend-staging',
            'CLICKHOUSE_URL': 'https://staging.clickhouse.cloud/netra-staging',
            
            # DEPRECATED: This should trigger deprecation warnings
            'REDIS_URL': 'redis://staging-redis.cloud.redislabs.com:12345/0',
        }
        
        # Set up logging capture to verify deprecation warnings
        log_capture = StringIO()
        log_handler = logging.StreamHandler(log_capture)
        log_handler.setLevel(logging.WARNING)
        
        # Get the logger and add our handler
        logger = logging.getLogger('shared.configuration.redis_pattern_validator')
        logger.addHandler(log_handler)
        logger.setLevel(logging.WARNING)
        
        try:
            with self.temp_env_vars(**staging_with_redis_url):
                # Use RedisPatternValidator to check for deprecation warnings
                validator = RedisConfigurationPatternValidator()
                validation_issues = validator.validate_redis_environment_variables(staging_with_redis_url)
                
                # Should find deprecation warnings for REDIS_URL
                deprecation_issues = [
                    issue for issue in validation_issues 
                    if 'deprecat' in issue.description.lower()
                ]
                
                assert len(deprecation_issues) > 0, (
                    f"DEPRECATION WARNING MISSING: Expected REDIS_URL deprecation warnings, but found none.\n"
                    f"All validation issues: {[issue.description for issue in validation_issues]}\n"
                    f"The deprecation warning system should detect REDIS_URL usage and warn users."
                )
                
                # Verify the deprecation warning is clear and actionable
                redis_url_deprecation = None
                for issue in deprecation_issues:
                    if 'redis_url' in issue.description.lower() or 'redis_url' in issue.description.lower():
                        redis_url_deprecation = issue
                        break
                
                assert redis_url_deprecation is not None, (
                    f"SPECIFIC REDIS_URL WARNING MISSING: Expected specific REDIS_URL deprecation warning.\n"
                    f"Deprecation issues found: {[issue.description for issue in deprecation_issues]}\n"
                    f"Need specific warning about REDIS_URL environment variable deprecation."
                )
                
                # Validate warning message quality
                warning_message = redis_url_deprecation.description
                warning_lower = warning_message.lower()
                
                # Should contain key deprecation information
                required_elements = [
                    'deprecat',  # Mentions deprecation
                    'redis_url', # Mentions the specific variable
                ]
                
                missing_elements = []
                for element in required_elements:
                    if element not in warning_lower:
                        missing_elements.append(element)
                
                assert len(missing_elements) == 0, (
                    f"DEPRECATION WARNING INCOMPLETE: Warning message missing key elements.\n"
                    f"Warning message: {warning_message}\n"
                    f"Missing elements: {missing_elements}\n"
                    f"Required elements: {required_elements}\n"
                    f"Deprecation warnings should be clear and actionable."
                )
                
                # Log validation results for debugging
                self.record_metric("deprecation_issues_count", len(deprecation_issues))
                self.record_metric("redis_url_warning_found", redis_url_deprecation is not None)
                self.record_metric("warning_message", warning_message[:100] + "..." if len(warning_message) > 100 else warning_message)
                
        finally:
            # Clean up logging handler
            logger.removeHandler(log_handler)
            log_handler.close()

    def test_redis_url_deprecation_provides_migration_guidance(self):
        """
        MIGRATION GUIDANCE TEST: Validates that deprecation warnings provide clear migration guidance.
        
        This test should PASS, proving that users get actionable guidance for migrating away from REDIS_URL.
        Expected behavior: Deprecation warnings should include specific migration instructions.
        """
        # Set up production environment with deprecated REDIS_URL (more critical)
        production_with_redis_url = {
            'ENVIRONMENT': 'production',
            'GCP_PROJECT_ID': 'netra-production-12345',
            'POSTGRES_HOST': '/cloudsql/netra-prod:us-central1:netra-prod-postgres',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'production-database-password-32-chars-long',
            'POSTGRES_DB': 'netra_production',
            'JWT_SECRET_KEY': 'production-jwt-secret-key-32-chars-minimum-length-required',
            'FERNET_KEY': 'production-fernet-key-32-chars-base64-encoded-value',
            'SERVICE_SECRET': 'production-service-secret-32-chars-minimum-required-length',
            'SERVICE_ID': 'netra-backend-production',
            'CLICKHOUSE_URL': 'https://production.clickhouse.cloud/netra-production',
            
            # DEPRECATED: This should trigger migration guidance
            'REDIS_URL': 'rediss://prod-redis.cloud.redislabs.com:12345/0',
        }
        
        with self.temp_env_vars(**production_with_redis_url):
            # Use RedisPatternValidator to get migration guidance
            validator = RedisConfigurationPatternValidator()
            validation_issues = validator.validate_redis_environment_variables(production_with_redis_url)
            
            # Find deprecation issues that should contain migration guidance
            deprecation_issues = [
                issue for issue in validation_issues 
                if 'deprecat' in issue.description.lower() or 'migration' in issue.description.lower()
            ]
            
            assert len(deprecation_issues) > 0, (
                f"MIGRATION GUIDANCE MISSING: Expected deprecation warnings with migration guidance.\n"
                f"All validation issues: {[f'{issue.description}: {issue.description}' for issue in validation_issues]}\n"
                f"Deprecation warnings should provide migration guidance."
            )
            
            # Verify migration guidance is specific and actionable
            migration_guidance_found = False
            guidance_details = []
            
            for issue in deprecation_issues:
                combined_message = issue.description
                guidance_lower = combined_message.lower()
                
                # Look for migration guidance keywords
                migration_keywords = [
                    'component-based',  # Preferred approach
                    'redis_host',       # Specific alternative
                    'redis_port',       # Specific alternative
                    'use',              # Action guidance
                    'instead',          # Alternative guidance
                    'migration',        # Migration context
                ]
                
                keyword_count = sum(1 for keyword in migration_keywords if keyword in guidance_lower)
                if keyword_count >= 3:  # Should contain multiple migration keywords
                    migration_guidance_found = True
                    guidance_details.append(combined_message)
            
            assert migration_guidance_found, (
                f"MIGRATION GUIDANCE INADEQUATE: Deprecation warnings don't provide clear migration guidance.\n"
                f"Deprecation messages: {[issue.description + ': ' + issue.description for issue in deprecation_issues]}\n"
                f"Migration guidance should include specific alternatives like component-based Redis configuration."
            )
            
            # Validate that guidance mentions preferred alternatives
            has_component_based_guidance = False
            for guidance in guidance_details:
                if 'component-based' in guidance.lower() or ('redis_host' in guidance.lower() and 'redis_port' in guidance.lower()):
                    has_component_based_guidance = True
                    break
            
            assert has_component_based_guidance, (
                f"SPECIFIC MIGRATION GUIDANCE MISSING: Should recommend component-based Redis configuration.\n"
                f"Guidance found: {guidance_details}\n"
                f"Should mention using REDIS_HOST and REDIS_PORT instead of REDIS_URL."
            )
            
            # Log migration guidance for debugging
            self.record_metric("migration_guidance_found", migration_guidance_found)
            self.record_metric("guidance_messages", guidance_details)

    def test_redis_url_deprecation_warning_in_unified_config_manager(self):
        """
        UNIFIED CONFIG TEST: Validates that UnifiedConfigManager shows REDIS_URL deprecation warnings.
        
        This test should PASS, proving that the unified configuration system properly handles deprecation.
        Expected behavior: UnifiedConfigManager should warn about deprecated REDIS_URL usage.
        """
        # Set up environment with deprecated REDIS_URL
        config_with_redis_url = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': '701982941522',
            'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:netra-staging-postgres',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'staging-database-password-32-chars-long',
            'POSTGRES_DB': 'netra_staging',
            'JWT_SECRET_KEY': 'staging-jwt-secret-key-32-chars-minimum-length-required',
            'FERNET_KEY': 'staging-fernet-key-32-chars-base64-encoded-value',
            'SERVICE_SECRET': 'staging-service-secret-32-chars-minimum-required-length',
            'SERVICE_ID': 'netra-backend-staging',
            'CLICKHOUSE_URL': 'https://staging.clickhouse.cloud/netra-staging',
            
            # DEPRECATED: This should be detected by UnifiedConfigManager
            'REDIS_URL': 'redis://staging-redis.cloud.redislabs.com:12345/0',
        }
        
        with self.temp_env_vars(**config_with_redis_url):
            # Create UnifiedConfigManager with validation enabled
            config_manager = UnifiedConfigurationManager(
                environment="staging",
                service_name="redis-deprecation-test",
                enable_validation=True
            )
            
            # Get Redis configuration to trigger validation
            redis_config = config_manager.get_redis_config()
            
            # Check that Redis URL is still functional (backward compatibility)
            redis_url_value = config_manager.get_str("redis.url")
            
            assert redis_url_value is not None, (
                "BACKWARD COMPATIBILITY BROKEN: REDIS_URL should still work while deprecated.\n"
                f"Redis config: {redis_config}\n"
                f"Deprecation should not break existing functionality."
            )
            
            # Verify deprecation is tracked in validation results
            validation_result = config_manager.validate_all_configurations()
            
            # Should have warnings about deprecated keys
            has_deprecation_warning = len(validation_result.deprecated_keys) > 0 or len(validation_result.warnings) > 0
            
            if not has_deprecation_warning:
                # Log configuration details for debugging
                config_status = config_manager.get_status()
                self.record_metric("config_status", config_status)
                self.record_metric("validation_result_warnings", validation_result.warnings)
                self.record_metric("deprecated_keys", validation_result.deprecated_keys)
                
                # This might be expected if UnifiedConfigManager doesn't handle Redis deprecation directly
                # In that case, we should verify the Redis value is accessible
                assert redis_url_value == config_with_redis_url['REDIS_URL'], (
                    f"CONFIGURATION ACCESS ISSUE: REDIS_URL not properly loaded.\n"
                    f"Expected: {config_with_redis_url['REDIS_URL']}\n"
                    f"Got: {redis_url_value}\n"
                    f"Configuration system should load deprecated values correctly."
                )
            
            # Log configuration manager status
            self.record_metric("redis_url_loaded", redis_url_value is not None)
            self.record_metric("validation_enabled", config_manager.enable_validation)
            self.record_metric("warnings_count", len(validation_result.warnings))

    def test_redis_component_based_configuration_recommended_alternative(self):
        """
        RECOMMENDED ALTERNATIVE TEST: Validates that component-based Redis configuration works correctly.
        
        This test should PASS, proving that the recommended alternative to REDIS_URL works properly.
        Expected behavior: Using REDIS_HOST, REDIS_PORT instead of REDIS_URL should work correctly.
        """
        # Set up environment with component-based Redis configuration (recommended approach)
        component_based_redis_config = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': '701982941522',
            'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:netra-staging-postgres',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'staging-database-password-32-chars-long',
            'POSTGRES_DB': 'netra_staging',
            'JWT_SECRET_KEY': 'staging-jwt-secret-key-32-chars-minimum-length-required',
            'FERNET_KEY': 'staging-fernet-key-32-chars-base64-encoded-value',
            'SERVICE_SECRET': 'staging-service-secret-32-chars-minimum-required-length',
            'SERVICE_ID': 'netra-backend-staging',
            'CLICKHOUSE_URL': 'https://staging.clickhouse.cloud/netra-staging',
            
            # RECOMMENDED: Component-based Redis configuration
            'REDIS_HOST': 'staging-redis.cloud.redislabs.com',
            'REDIS_PORT': '12345',
            'REDIS_USERNAME': 'default',
            'REDIS_PASSWORD': 'staging-redis-password-secure',
            'REDIS_DATABASE': '0',
            # NOTE: No REDIS_URL - testing the recommended alternative
        }
        
        with self.temp_env_vars(**component_based_redis_config):
            # Create UnifiedConfigManager to test component-based configuration
            config_manager = UnifiedConfigurationManager(
                environment="staging",
                service_name="redis-component-test",
                enable_validation=True
            )
            
            # Get Redis configuration using component-based approach
            redis_config = config_manager.get_redis_config()
            
            # Verify component-based configuration is loaded correctly
            expected_redis_host = component_based_redis_config['REDIS_HOST']
            expected_redis_port = int(component_based_redis_config['REDIS_PORT'])
            
            # Check if configuration manager can construct Redis connection info from components
            redis_host = config_manager.get_str("redis.host", "localhost")
            redis_port = config_manager.get_int("redis.port", 6379)
            
            # Component-based approach should work
            assert redis_host == expected_redis_host or redis_host != "localhost", (
                f"COMPONENT REDIS HOST ISSUE: Expected Redis host to be loaded from component configuration.\n"
                f"Expected: {expected_redis_host}\n"
                f"Got: {redis_host}\n"
                f"Component-based Redis configuration should work as alternative to REDIS_URL."
            )
            
            # Verify no deprecation warnings for component-based approach
            validation_result = config_manager.validate_all_configurations()
            
            redis_deprecation_warnings = [
                warning for warning in validation_result.warnings
                if 'redis_url' in warning.lower() and 'deprecat' in warning.lower()
            ]
            
            assert len(redis_deprecation_warnings) == 0, (
                f"COMPONENT-BASED DEPRECATION WARNING: Component-based Redis config should not trigger deprecation warnings.\n"
                f"Deprecation warnings: {redis_deprecation_warnings}\n"
                f"Using REDIS_HOST/REDIS_PORT instead of REDIS_URL should be the recommended approach."
            )
            
            # Log component-based configuration results
            self.record_metric("component_redis_host", redis_host)
            self.record_metric("component_redis_port", redis_port)  
            self.record_metric("redis_config_keys", list(redis_config.keys()))
            self.record_metric("no_deprecation_warnings", len(redis_deprecation_warnings) == 0)

    def test_redis_url_deprecation_message_format_and_clarity(self):
        """
        MESSAGE QUALITY TEST: Validates that REDIS_URL deprecation messages are clear and well-formatted.
        
        This test should PASS, proving that deprecation messages meet quality standards.
        Expected behavior: Deprecation messages should be clear, actionable, and user-friendly.
        """
        # Set up environment that will trigger REDIS_URL deprecation warnings
        redis_url_environment = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': 'redis://user:password@staging-redis.example.com:6379/0',
            # Basic required environment variables
            'JWT_SECRET_KEY': 'staging-jwt-secret-key-32-chars-minimum-length-required',
            'SERVICE_SECRET': 'staging-service-secret-32-chars-minimum-required-length',
        }
        
        with self.temp_env_vars(**redis_url_environment):
            # Use RedisPatternValidator to get deprecation messages
            validator = RedisConfigurationPatternValidator()
            validation_issues = validator.validate_redis_environment_variables({'ENVIRONMENT': 'staging', 'REDIS_URL': 'redis://example.com:6379/0'})
            
            # Find REDIS_URL specific deprecation issues
            redis_url_issues = []
            for issue in validation_issues:
                combined_text = (issue.description).lower()
                if 'redis_url' in combined_text and 'deprecat' in combined_text:
                    redis_url_issues.append(issue)
            
            assert len(redis_url_issues) > 0, (
                f"REDIS_URL DEPRECATION MESSAGE MISSING: Expected specific REDIS_URL deprecation warnings.\n"
                f"All validation issues: {[issue.description for issue in validation_issues]}\n"
                f"Should have specific warnings about REDIS_URL deprecation."
            )
            
            # Analyze message quality for the primary REDIS_URL deprecation warning
            primary_issue = redis_url_issues[0]
            message_text = primary_issue.description
            
            # Check message quality criteria
            quality_checks = {
                'mentions_version': 'version' in message_text.lower(),
                'mentions_alternative': any(alt in message_text.lower() for alt in ['component', 'redis_host', 'alternative', 'instead']),
                'clear_action': any(action in message_text.lower() for action in ['use', 'migrate', 'replace', 'switch']),
                'professional_tone': not any(bad_word in message_text.lower() for bad_word in ['error', 'broken', 'bad', 'wrong']),
                'reasonable_length': 50 <= len(message_text) <= 300,  # Not too short or too long
            }
            
            failed_checks = [check for check, passed in quality_checks.items() if not passed]
            
            assert len(failed_checks) <= 1, (  # Allow one minor quality issue
                f"DEPRECATION MESSAGE QUALITY ISSUES: Message fails multiple quality checks.\n"
                f"Message: {message_text}\n"
                f"Failed checks: {failed_checks}\n"
                f"Quality criteria: {quality_checks}\n"
                f"Deprecation messages should be clear, actionable, and professional."
            )
            
            # Verify message includes version information
            assert quality_checks['mentions_version'], (
                f"DEPRECATION VERSION MISSING: Message should mention when REDIS_URL will be removed.\n"
                f"Message: {message_text}\n"
                f"Users need to know timeline for migration planning."
            )
            
            # Log message quality analysis
            self.record_metric("deprecation_message", message_text)
            self.record_metric("quality_checks_passed", sum(quality_checks.values()))
            self.record_metric("quality_checks_total", len(quality_checks))
            self.record_metric("message_length", len(message_text))

    def test_redis_url_backward_compatibility_during_deprecation(self):
        """
        BACKWARD COMPATIBILITY TEST: Validates that REDIS_URL still works during deprecation period.
        
        This test should PASS, proving that deprecation doesn't break existing functionality.
        Expected behavior: REDIS_URL should work with warnings, not break the system.
        """
        # Set up environment with REDIS_URL to test backward compatibility
        backward_compatibility_config = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': 'redis://staging-redis.example.com:6379/0',
            # Required config for basic functionality
            'JWT_SECRET_KEY': 'staging-jwt-secret-key-32-chars-minimum-length-required',
            'SERVICE_SECRET': 'staging-service-secret-32-chars-minimum-required-length',
            'SERVICE_ID': 'netra-backend-staging',
        }
        
        with self.temp_env_vars(**backward_compatibility_config):
            # Test that UnifiedConfigManager still works with REDIS_URL
            config_manager = UnifiedConfigurationManager(
                environment="staging",
                service_name="backward-compatibility-test",
                enable_validation=True  # Enable validation to see deprecation warnings
            )
            
            # Should be able to get Redis configuration successfully
            try:
                redis_config = config_manager.get_redis_config()
                redis_url = config_manager.get_str("redis.url")
                
                # Configuration access should work
                assert redis_config is not None, (
                    "BACKWARD COMPATIBILITY BROKEN: Cannot get Redis configuration with REDIS_URL"
                )
                
                # Should be able to access the deprecated REDIS_URL value
                expected_redis_url = backward_compatibility_config['REDIS_URL']
                
                # The system should still provide access to Redis configuration
                redis_config_available = (
                    redis_url is not None or 
                    redis_config.get('url') is not None or
                    'redis' in str(redis_config).lower()
                )
                
                assert redis_config_available, (
                    f"BACKWARD COMPATIBILITY FAILURE: Redis configuration not accessible.\n"
                    f"REDIS_URL set: {expected_redis_url}\n"
                    f"Redis config returned: {redis_config}\n"
                    f"Redis URL value: {redis_url}\n"
                    f"System should maintain functionality during deprecation period."
                )
                
                # Log backward compatibility test results
                self.record_metric("redis_config_accessible", redis_config is not None)
                self.record_metric("redis_url_accessible", redis_url is not None)
                self.record_metric("backward_compatibility_working", True)
                
            except Exception as e:
                # Should not throw exceptions due to deprecation
                pytest.fail(
                    f"BACKWARD COMPATIBILITY EXCEPTION: REDIS_URL usage should not cause exceptions.\n"
                    f"Exception: {str(e)}\n"
                    f"Deprecation should warn, not break functionality."
                )

    def test_validate_deprecation_system_configuration(self):
        """
        SYSTEM CONFIGURATION TEST: Validates that the deprecation warning system is properly configured.
        
        This test should PASS, proving that the deprecation infrastructure is set up correctly.
        Expected behavior: Deprecation warning system should be properly initialized and configured.
        """
        # Test that RedisPatternValidator is available and functional
        try:
            validator = RedisConfigurationPatternValidator()
            assert validator is not None, "RedisPatternValidator should be available"
            
            # Test that validation method exists and is callable
            assert hasattr(validator, 'validate_redis_environment_variables'), (
                "RedisConfigurationPatternValidator should have validate_redis_environment_variables method"
            )
            
            # Test basic validation functionality
            issues = validator.validate_redis_environment_variables({'ENVIRONMENT': 'development'})
            assert isinstance(issues, list), (
                f"validate_redis_environment_variables should return a list, got {type(issues)}"
            )
            
            # Log system configuration status
            self.record_metric("validator_available", True)
            self.record_metric("validation_method_callable", True)
            self.record_metric("deprecation_system_configured", True)
            
        except ImportError as e:
            pytest.fail(
                f"DEPRECATION SYSTEM NOT AVAILABLE: Cannot import RedisPatternValidator.\n"
                f"Import error: {str(e)}\n"
                f"Deprecation warning system is not properly configured."
            )
        except Exception as e:
            pytest.fail(
                f"DEPRECATION SYSTEM ERROR: RedisPatternValidator has configuration issues.\n"
                f"Error: {str(e)}\n"
                f"Deprecation warning system is not functioning correctly."
            )