"""
Test Configuration SSOT: Configuration Validator Compliance

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent configuration validation fragmentation and ensure SSOT compliance
- Value Impact: Protects $120K+ MRR by ensuring consistent validation patterns across services
- Strategic Impact: Eliminates cascade failures from inconsistent configuration validation

This test validates that configuration validation follows SSOT patterns with
consistent validation rules, proper error escalation, and environment-appropriate
validation modes to prevent configuration cascade failures.
"""

import pytest
from unittest.mock import patch, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from netra_backend.app.core.configuration.validator import ConfigurationValidator
from netra_backend.app.core.configuration.base import UnifiedConfigManager


class TestConfigurationValidatorCompliance(BaseIntegrationTest):
    """Test Configuration Validator SSOT compliance."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_configuration_validator_ssot_validation_patterns(self, real_services_fixture):
        """
        Test that ConfigurationValidator provides SSOT validation patterns.
        
        Configuration validation must be centralized to prevent inconsistent
        validation rules across services. Different validators for different
        components (database, auth, LLM) must follow consistent SSOT patterns.
        """
        env = get_env()
        env.enable_isolation()
        
        # Set up comprehensive test configuration
        test_config = {
            'ENVIRONMENT': 'testing',
            # Database configuration (SSOT components)
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5434',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_password_32_chars_minimum',
            'POSTGRES_DB': 'netra_test',
            # Authentication configuration
            'JWT_SECRET_KEY': 'test_jwt_secret_key_minimum_32_characters_required',
            'SERVICE_SECRET': 'test_service_secret_minimum_32_characters_required',
            'SECRET_KEY': 'test_secret_key_minimum_32_characters_required',
            # Optional LLM configuration
            'LLM_ANTHROPIC_API_KEY': 'test_anthropic_key',
            # Optional OAuth configuration
            'GOOGLE_CLIENT_ID': 'test_google_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_google_client_secret',
            # Redis configuration
            'REDIS_URL': 'redis://localhost:6381'
        }
        
        for key, value in test_config.items():
            env.set(key, value, 'validator_test')
        
        try:
            # Test ConfigurationValidator creation and validation
            validator = ConfigurationValidator()
            
            # CRITICAL: Should provide comprehensive validation
            validation_result = validator.validate_complete_config()
            
            assert validation_result is not None, "Validator should return validation results"
            
            # Test validation result structure
            expected_attributes = ['is_valid', 'errors', 'warnings', 'health_score']
            for attr in expected_attributes:
                assert hasattr(validation_result, attr), f"Validation result should have {attr}"
            
            # Test health scoring (0-100 scale)
            health_score = validation_result.health_score
            assert 0 <= health_score <= 100, f"Health score should be 0-100: {health_score}"
            
            # With complete valid config, health score should be high
            assert health_score >= 80, f"Complete valid config should have high health score: {health_score}"
            
            # Test validation error detection
            # Remove critical configuration
            env.delete('JWT_SECRET_KEY')
            
            critical_missing_validator = ConfigurationValidator()
            critical_validation = critical_missing_validator.validate_complete_config()
            
            # Should detect missing critical configuration
            assert len(critical_validation.errors) > 0, "Should detect missing JWT secret"
            assert critical_validation.health_score < health_score, "Health score should decrease with errors"
            
            # Restore JWT secret
            env.set('JWT_SECRET_KEY', 'test_jwt_secret_key_minimum_32_characters_required', 'restore')
            
            # Test component-specific validation
            
            # Database validation should use DatabaseURLBuilder SSOT
            database_validator = ConfigurationValidator()
            db_validation = database_validator.validate_complete_config()
            
            # Should validate database components (not direct DATABASE_URL)
            assert db_validation is not None
            
            # Test that validator catches database component issues
            env.set('POSTGRES_PASSWORD', 'short', 'security_test')  # Too short password
            
            weak_password_validator = ConfigurationValidator()
            weak_validation = weak_password_validator.validate_complete_config()
            
            # Should generate warnings for weak passwords
            if hasattr(weak_validation, 'warnings'):
                security_warnings = [w for w in weak_validation.warnings 
                                   if 'password' in w.lower() or 'security' in w.lower()]
                # Note: This depends on validator implementation
            
            # Restore proper password
            env.set('POSTGRES_PASSWORD', 'test_password_32_chars_minimum', 'restore')
            
        finally:
            env.reset_to_original()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_configuration_validator_progressive_validation_modes(self, real_services_fixture):
        """
        Test ConfigurationValidator progressive validation modes.
        
        Validation strictness should adapt to environment:
        - WARN: Development environment, log warnings but continue
        - ENFORCE_CRITICAL: Staging environment, enforce critical configs
        - ENFORCE_ALL: Production environment, enforce all validations
        """
        env = get_env()
        env.enable_isolation()
        
        # Base configuration
        base_config = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_password',
            'POSTGRES_DB': 'test_db',
            'JWT_SECRET_KEY': 'test_jwt_secret_minimum_32_characters',
            'SERVICE_SECRET': 'test_service_secret_minimum_32_chars',
            'SECRET_KEY': 'test_secret_key_minimum_32_characters'
        }
        
        try:
            # Test WARN mode (Development)
            env.set('ENVIRONMENT', 'development', 'validation_mode_test')
            for key, value in base_config.items():
                env.set(key, value, 'validation_mode_test')
            
            dev_validator = ConfigurationValidator()
            dev_validation = dev_validator.validate_complete_config()
            
            # Development should be more lenient
            assert dev_validation is not None
            
            # Missing optional configs should generate warnings, not errors
            # (Depends on specific validator implementation)
            
            # Test ENFORCE_CRITICAL mode (Staging)
            env.set('ENVIRONMENT', 'staging', 'validation_mode_test')
            
            staging_validator = ConfigurationValidator()
            staging_validation = staging_validator.validate_complete_config()
            
            # Staging should enforce critical configurations
            assert staging_validation is not None
            
            # Test missing critical config in staging
            env.delete('SERVICE_SECRET')
            
            missing_critical_validator = ConfigurationValidator()
            missing_critical_validation = missing_critical_validator.validate_complete_config()
            
            # Should detect missing critical config
            assert len(missing_critical_validation.errors) > 0, "Should detect missing SERVICE_SECRET in staging"
            
            # Restore SERVICE_SECRET
            env.set('SERVICE_SECRET', 'test_service_secret_minimum_32_chars', 'restore')
            
            # Test ENFORCE_ALL mode (Production)
            env.set('ENVIRONMENT', 'production', 'validation_mode_test')
            
            # Add production-required configs
            production_additions = {
                'LLM_ANTHROPIC_API_KEY': 'prod_anthropic_key',
                'REDIS_URL': 'redis://prod-redis:6379',
                'GOOGLE_CLIENT_ID': 'prod_google_client',
                'GOOGLE_CLIENT_SECRET': 'prod_google_secret'
            }
            
            for key, value in production_additions.items():
                env.set(key, value, 'validation_mode_test')
            
            prod_validator = ConfigurationValidator()
            prod_validation = prod_validator.validate_complete_config()
            
            # Production should have high health score with complete config
            assert prod_validation.health_score >= 90, \
                f"Production with complete config should have high health: {prod_validation.health_score}"
            
            # Test missing production config
            env.delete('LLM_ANTHROPIC_API_KEY')
            
            incomplete_prod_validator = ConfigurationValidator()
            incomplete_prod_validation = incomplete_prod_validator.validate_complete_config()
            
            # Production should be strict about missing configs
            assert incomplete_prod_validation.health_score < prod_validation.health_score, \
                "Missing production config should reduce health score"
            
        finally:
            env.reset_to_original()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_configuration_validator_component_specific_validation(self, real_services_fixture):
        """
        Test ConfigurationValidator component-specific validation patterns.
        
        Different validators handle different components:
        - DatabaseValidator: Database configuration via DatabaseURLBuilder SSOT
        - AuthValidator: OAuth and JWT configuration
        - LLMValidator: LLM provider configuration  
        - EnvironmentValidator: External service configuration
        """
        env = get_env()
        env.enable_isolation()
        env.set('ENVIRONMENT', 'testing', 'component_test')
        
        try:
            # Test Database validation component
            database_config = {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_PORT': '5434',
                'POSTGRES_USER': 'test_user',
                'POSTGRES_PASSWORD': 'test_password',
                'POSTGRES_DB': 'netra_test'
            }
            
            for key, value in database_config.items():
                env.set(key, value, 'database_test')
            
            # Create validator and test database component validation
            db_validator = ConfigurationValidator()
            db_validation = db_validator.validate_complete_config()
            
            # Should validate database configuration successfully
            assert db_validation is not None
            
            # Test database component missing
            env.delete('POSTGRES_HOST')
            
            missing_db_validator = ConfigurationValidator()
            missing_db_validation = missing_db_validator.validate_complete_config()
            
            # Should detect missing database host
            db_errors = [error for error in missing_db_validation.errors 
                        if 'postgres' in error.lower() or 'database' in error.lower()]
            assert len(db_errors) > 0, "Should detect missing database configuration"
            
            # Restore database host
            env.set('POSTGRES_HOST', 'localhost', 'restore')
            
            # Test Auth validation component
            auth_config = {
                'JWT_SECRET_KEY': 'auth_test_jwt_secret_minimum_32_characters_required',
                'SERVICE_SECRET': 'auth_test_service_secret_minimum_32_characters',
                'SECRET_KEY': 'auth_test_secret_key_minimum_32_characters_req'
            }
            
            for key, value in auth_config.items():
                env.set(key, value, 'auth_test')
            
            auth_validator = ConfigurationValidator()
            auth_validation = auth_validator.validate_complete_config()
            
            # Should validate authentication configuration
            assert auth_validation is not None
            
            # Test weak secret key (security validation)
            env.set('JWT_SECRET_KEY', 'short', 'security_test')
            
            weak_auth_validator = ConfigurationValidator()
            weak_auth_validation = weak_auth_validator.validate_complete_config()
            
            # Should detect weak JWT secret
            auth_errors = [error for error in weak_auth_validation.errors 
                          if 'jwt' in error.lower() or 'secret' in error.lower()]
            assert len(auth_errors) > 0, "Should detect weak JWT secret"
            
            # Restore proper JWT secret
            env.set('JWT_SECRET_KEY', 'auth_test_jwt_secret_minimum_32_characters_required', 'restore')
            
            # Test LLM validation component
            llm_config = {
                'LLM_ANTHROPIC_API_KEY': 'test_anthropic_api_key'
            }
            
            for key, value in llm_config.items():
                env.set(key, value, 'llm_test')
            
            llm_validator = ConfigurationValidator()
            llm_validation = llm_validator.validate_complete_config()
            
            # Should validate LLM configuration
            assert llm_validation is not None
            
            # Test invalid LLM API key format
            env.set('LLM_ANTHROPIC_API_KEY', 'invalid_key', 'format_test')
            
            invalid_llm_validator = ConfigurationValidator()
            invalid_llm_validation = invalid_llm_validator.validate_complete_config()
            
            # May generate warnings about API key format (depends on implementation)
            
            # Test Environment validation component
            external_config = {
                'REDIS_URL': 'redis://localhost:6381',
                'GOOGLE_CLIENT_ID': 'test_google_client_id',
                'GOOGLE_CLIENT_SECRET': 'test_google_client_secret'
            }
            
            for key, value in external_config.items():
                env.set(key, value, 'external_test')
            
            env_validator = ConfigurationValidator()
            env_validation = env_validator.validate_complete_config()
            
            # Should validate external service configuration
            assert env_validation is not None
            
            # Test comprehensive validation with all components
            comprehensive_validator = ConfigurationValidator()
            comprehensive_validation = comprehensive_validator.validate_complete_config()
            
            # With all components configured, should have high health score
            assert comprehensive_validation.health_score >= 85, \
                f"Comprehensive config should have high health: {comprehensive_validation.health_score}"
            
        finally:
            env.reset_to_original()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_configuration_validator_integration_with_unified_config_manager(self, real_services_fixture):
        """
        Test ConfigurationValidator integration with UnifiedConfigManager.
        
        The validator must integrate seamlessly with UnifiedConfigManager
        to provide comprehensive configuration validation and health monitoring
        as part of the SSOT configuration architecture.
        """
        env = get_env()
        env.enable_isolation()
        
        # Set up complete configuration for integration testing
        complete_config = {
            'ENVIRONMENT': 'testing',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5434',
            'POSTGRES_USER': 'integration_test_user',
            'POSTGRES_PASSWORD': 'integration_test_password_32_chars',
            'POSTGRES_DB': 'netra_integration_test',
            'REDIS_URL': 'redis://localhost:6381',
            'JWT_SECRET_KEY': 'integration_jwt_secret_minimum_32_characters_required',
            'SERVICE_SECRET': 'integration_service_secret_minimum_32_characters',
            'SECRET_KEY': 'integration_secret_key_minimum_32_characters_req',
            'LLM_ANTHROPIC_API_KEY': 'integration_test_anthropic_key',
            'GOOGLE_CLIENT_ID': 'integration_test_google_client_id',
            'GOOGLE_CLIENT_SECRET': 'integration_test_google_client_secret'
        }
        
        for key, value in complete_config.items():
            env.set(key, value, 'integration_test')
        
        try:
            # Test UnifiedConfigManager uses ConfigurationValidator
            unified_manager = UnifiedConfigManager()
            
            # Should integrate validator for comprehensive validation
            unified_validation = unified_manager.validate_configuration()
            
            assert unified_validation is not None, "UnifiedConfigManager should provide validation"
            
            # Should have high health score with complete configuration
            assert unified_validation.health_score >= 90, \
                f"Complete config should have high health: {unified_validation.health_score}"
            
            # Test that UnifiedConfigManager configuration passes validator scrutiny
            app_config = unified_manager.get_configuration()
            assert app_config is not None, "Should create valid configuration object"
            
            # Test validator detects issues in UnifiedConfigManager context
            env.delete('SERVICE_SECRET')  # Remove critical config
            
            degraded_manager = UnifiedConfigManager()
            degraded_validation = degraded_manager.validate_configuration()
            
            # Should detect the missing critical configuration
            assert degraded_validation.health_score < unified_validation.health_score, \
                "Missing critical config should reduce health score"
            
            assert len(degraded_validation.errors) > 0, "Should detect missing SERVICE_SECRET"
            
            # Test validation-driven configuration correction
            env.set('SERVICE_SECRET', 'corrected_service_secret_minimum_32_characters', 'correction')
            
            corrected_manager = UnifiedConfigManager()
            corrected_validation = corrected_manager.validate_configuration()
            
            # Health score should improve after correction
            assert corrected_validation.health_score > degraded_validation.health_score, \
                "Corrected configuration should improve health score"
            
            # Test environment-specific validation integration
            env.set('ENVIRONMENT', 'production', 'env_test')
            
            prod_manager = UnifiedConfigManager()
            prod_validation = prod_manager.validate_configuration()
            
            # Production environment should have appropriate validation
            assert prod_validation is not None
            
            # Test that validator provides actionable feedback
            if hasattr(prod_validation, 'suggestions'):
                # Validator may provide suggestions for improvement
                pass
            
            # Test validation error categorization
            errors_by_category = {}
            if hasattr(prod_validation, 'errors'):
                for error in prod_validation.errors:
                    category = 'unknown'
                    if 'database' in error.lower() or 'postgres' in error.lower():
                        category = 'database'
                    elif 'jwt' in error.lower() or 'secret' in error.lower():
                        category = 'authentication'
                    elif 'llm' in error.lower() or 'anthropic' in error.lower():
                        category = 'llm'
                    elif 'oauth' in error.lower() or 'google' in error.lower():
                        category = 'oauth'
                    
                    if category not in errors_by_category:
                        errors_by_category[category] = []
                    errors_by_category[category].append(error)
            
            # Error categorization helps with targeted fixes
            
        finally:
            env.reset_to_original()