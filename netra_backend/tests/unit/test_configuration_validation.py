"""
Test Configuration Validation Business Logic - Core Unit Tests

Business Value Justification (BVJ):
- Segment: All (Configuration validation affects all deployment environments)
- Business Goal: System reliability and security through proper configuration management
- Value Impact: Prevents deployment failures and security vulnerabilities from misconfiguration
- Strategic Impact: CRITICAL - Configuration errors can cause service outages and data breaches

This test suite validates the core business logic for configuration validation
that ensures system deployments are secure and functional across all environments.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.config_validator import (
    ConfigValidator,
    ConfigurationValidationError
)


class TestConfigurationValidation(BaseTestCase):
    """Test configuration validation delivers deployment reliability for business operations."""
    
    def setup_method(self):
        """Setup test environment with isolated configuration."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.validator = ConfigValidator()
        
        # Create mock config for testing
        self.mock_config = Mock()
        self.mock_config.environment = "testing"
        self.mock_config.database_url = "postgresql://test:test@localhost/test"
        self.mock_config.jwt_secret_key = "test-jwt-secret-key-minimum-32-chars"
        self.mock_config.fernet_key = "test-fernet-key"
        
        # Setup OAuth config
        self.mock_config.oauth_config = Mock()
        self.mock_config.oauth_config.client_id = "test-oauth-client-id"
        self.mock_config.oauth_config.client_secret = "test-oauth-client-secret"
        
        # Setup ClickHouse config
        self.mock_config.clickhouse_logging = Mock()
        self.mock_config.clickhouse_logging.enabled = False
        self.mock_config.clickhouse_native = Mock()
        self.mock_config.clickhouse_native.host = ""
        self.mock_config.clickhouse_native.password = ""
        self.mock_config.clickhouse_https = Mock() 
        self.mock_config.clickhouse_https.host = ""
        self.mock_config.clickhouse_https.password = ""
        
        # Setup LLM config
        self.mock_config.llm_configs = {
            "gemini": Mock(model_name="gemini-pro", provider="google", api_key="test-api-key")
        }
        
        # Setup Redis config
        self.mock_config.redis = Mock()
        self.mock_config.redis.host = "localhost"
        self.mock_config.redis.password = "test-redis-password"
        
        # Setup Langfuse config
        self.mock_config.langfuse = Mock()
        self.mock_config.langfuse.secret_key = "test-langfuse-secret"
        self.mock_config.langfuse.public_key = "test-langfuse-public"
        
    def teardown_method(self):
        """Clean up test environment."""
        super().teardown_method()
        
    @pytest.mark.unit
    @patch('netra_backend.app.core.config_validator.get_unified_config')
    def test_database_configuration_business_requirements(self, mock_get_unified_config):
        """Test that database configuration validates business-critical requirements."""
        # Setup unified config mock
        mock_unified = Mock()
        mock_unified.deployment.is_cloud_run = False
        mock_get_unified_config.return_value = mock_unified
        
        # Test production database URL requirement
        self.mock_config.environment = "production"
        self.mock_config.database_url = None
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "Database URL is not configured" in error_message, \
            "Production environment should require database URL"
            
        # Test database URL format validation
        self.mock_config.database_url = "mysql://invalid:url@localhost/db"
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "PostgreSQL connection string" in error_message, \
            "Should enforce PostgreSQL URL format for business data consistency"
            
        # Test valid PostgreSQL URL
        self.mock_config.database_url = "postgresql+asyncpg://user:pass@localhost/netra"
        
        # Should not raise exception with valid config
        try:
            self.validator.validate_config(self.mock_config)
        except ConfigurationValidationError:
            pytest.fail("Valid PostgreSQL URL should pass validation")
            
    @pytest.mark.unit
    def test_authentication_security_requirements(self):
        """Test that authentication configuration enforces security requirements."""
        # Test JWT secret key requirement
        self.mock_config.jwt_secret_key = None
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        assert "JWT secret key is not configured" in str(exc_info.value), \
            "JWT secret key should be required for user authentication"
            
        # Test production JWT key strength
        self.mock_config.environment = "production"
        self.mock_config.jwt_secret_key = "weak"  # Too short
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "at least 32 characters" in error_message, \
            "Production JWT keys should meet minimum security requirements"
            
        # Test development key detection in production
        self.mock_config.jwt_secret_key = "development-key-not-for-production-use"
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "development/test key" in error_message, \
            "Production should not allow development keys"
            
        # Test Fernet key requirement
        self.mock_config.jwt_secret_key = "production-grade-jwt-secret-key-32-chars-min"
        self.mock_config.fernet_key = None
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        assert "Fernet key is not configured" in str(exc_info.value), \
            "Fernet key should be required for data encryption"
            
    @pytest.mark.unit
    def test_oauth_configuration_environment_awareness(self):
        """Test that OAuth configuration requirements adapt to business environment needs."""
        # Test OAuth requirement in production
        self.mock_config.environment = "production"
        self.mock_config.oauth_config.client_id = None
        self.mock_config.oauth_config.client_secret = None
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "OAuth client ID is not configured" in error_message, \
            "Production should require OAuth client ID"
        assert "OAuth client secret is not configured" in error_message, \
            "Production should require OAuth client secret"
            
        # Test OAuth flexibility in development
        self.mock_config.environment = "development"
        
        # Should not raise OAuth errors in development
        try:
            self.validator.validate_config(self.mock_config)
        except ConfigurationValidationError as e:
            error_message = str(e)
            assert "OAuth" not in error_message, \
                f"Development environment should not require OAuth: {error_message}"
                
        # Test staging environment flexibility
        self.mock_config.environment = "staging"
        
        try:
            self.validator.validate_config(self.mock_config)
        except ConfigurationValidationError as e:
            error_message = str(e)
            assert "OAuth" not in error_message, \
                f"Staging environment should not require OAuth: {error_message}"
                
    @pytest.mark.unit
    def test_clickhouse_configuration_business_logic(self):
        """Test that ClickHouse configuration validates business analytics requirements."""
        # Test ClickHouse enabled scenario
        self.mock_config.clickhouse_logging.enabled = True
        self.mock_config.clickhouse_native.host = ""
        self.mock_config.clickhouse_https.host = ""
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "clickhouse_native host is not configured" in error_message, \
            "ClickHouse native host should be required when enabled"
        assert "clickhouse_https host is not configured" in error_message, \
            "ClickHouse HTTPS host should be required when enabled"
            
        # Test production password requirement
        self.mock_config.environment = "production"
        self.mock_config.clickhouse_native.host = "clickhouse.company.com"
        self.mock_config.clickhouse_https.host = "clickhouse-https.company.com"
        self.mock_config.clickhouse_native.password = ""
        self.mock_config.clickhouse_https.password = ""
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "password is required in production" in error_message, \
            "Production ClickHouse should require passwords for security"
            
        # Test dev mode ClickHouse bypass
        self.mock_config.dev_mode_clickhouse_enabled = False
        
        # Should skip ClickHouse validation when disabled in dev mode
        try:
            self.validator.validate_config(self.mock_config)
        except ConfigurationValidationError as e:
            error_message = str(e)
            assert "clickhouse" not in error_message.lower(), \
                f"Dev mode should skip ClickHouse validation: {error_message}"
                
    @pytest.mark.unit
    def test_llm_configuration_business_requirements(self):
        """Test that LLM configuration validates business AI operation requirements."""
        # Test missing LLM configs
        self.mock_config.llm_configs = {}
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "No LLM configurations defined" in error_message, \
            "LLM configs should be required for AI operations"
            
        # Test incomplete LLM config
        self.mock_config.llm_configs = {
            "incomplete": Mock(model_name="", provider="", api_key="")
        }
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "missing model name" in error_message, \
            "LLM configs should require model name"
        assert "missing provider" in error_message, \
            "LLM configs should require provider"
            
        # Test Gemini API key requirement for production
        self.mock_config.environment = "production"
        self.mock_config.llm_configs = {
            "gemini": Mock(model_name="gemini-pro", provider="google", api_key="")
        }
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "Gemini API key is not configured" in error_message, \
            "Production should require Gemini API key for AI operations"
            
        # Test dev mode LLM bypass
        self.mock_config.dev_mode_llm_enabled = False
        
        # Should skip LLM validation when disabled in dev mode  
        try:
            self.validator.validate_config(self.mock_config)
        except ConfigurationValidationError as e:
            error_message = str(e)
            assert "llm" not in error_message.lower(), \
                f"Dev mode should skip LLM validation: {error_message}"
                
    @pytest.mark.unit
    def test_redis_configuration_caching_requirements(self):
        """Test that Redis configuration validates business caching requirements."""
        # Test Redis host requirement
        self.mock_config.redis.host = ""
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "Redis host is not configured" in error_message, \
            "Redis host should be required for caching operations"
            
        # Test production password requirement
        self.mock_config.environment = "production"
        self.mock_config.redis.host = "redis.company.com"
        self.mock_config.redis.password = ""
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        assert "Redis password is required in production" in error_message, \
            "Production Redis should require password for security"
            
        # Test dev mode Redis bypass
        self.mock_config.dev_mode_redis_enabled = False
        
        # Should skip Redis validation when disabled in dev mode
        try:
            self.validator.validate_config(self.mock_config)
        except ConfigurationValidationError as e:
            error_message = str(e)
            assert "redis" not in error_message.lower(), \
                f"Dev mode should skip Redis validation: {error_message}"
                
    @pytest.mark.unit
    def test_validation_report_business_intelligence(self):
        """Test that validation report provides business intelligence for operations."""
        # Test successful validation report
        self.mock_config.environment = "testing"
        
        report = self.validator.get_validation_report(self.mock_config)
        
        assert isinstance(report, list), "Report should be a list of status items"
        assert len(report) > 0, "Report should contain status information"
        
        # Should contain key business information
        report_text = " ".join(report)
        assert "Environment:" in report_text, "Report should include environment info"
        assert "Database:" in report_text, "Report should include database status"
        assert "LLM Configs:" in report_text, "Report should include LLM config count"
        assert "Auth:" in report_text, "Report should include auth status"
        
        # Check for success indicator
        success_found = any("✓" in item and "passed" in item for item in report)
        assert success_found, f"Report should indicate success: {report}"
        
    @pytest.mark.unit
    def test_configuration_validation_error_handling(self):
        """Test that configuration validation provides clear error messages for operations."""
        # Test multiple validation errors
        self.mock_config.environment = "production"
        self.mock_config.database_url = None
        self.mock_config.jwt_secret_key = "short"
        self.mock_config.oauth_config.client_id = None
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            self.validator.validate_config(self.mock_config)
            
        error_message = str(exc_info.value)
        
        # Error message should be comprehensive for troubleshooting
        assert len(error_message) > 50, \
            "Error messages should be detailed for operational troubleshooting"
            
        # Should identify the configuration category that failed
        assert any(keyword in error_message for keyword in 
                  ["Database", "Authentication", "OAuth"]), \
            f"Error should identify configuration category: {error_message}"
            
    @pytest.mark.unit
    def test_environment_specific_validation_logic(self):
        """Test that validation logic adapts to different deployment environments."""
        environments_to_test = ["testing", "development", "staging", "production"]
        
        for environment in environments_to_test:
            self.mock_config.environment = environment
            
            # Reset to basic valid config
            self.mock_config.database_url = "postgresql://test:test@localhost/test"
            self.mock_config.jwt_secret_key = "test-jwt-secret-key-minimum-32-chars"
            
            # Testing environment should be most permissive
            if environment == "testing":
                self.mock_config.oauth_config.client_id = None
                self.mock_config.oauth_config.client_secret = None
                
                try:
                    self.validator.validate_config(self.mock_config)
                except ConfigurationValidationError:
                    pytest.fail(f"Testing environment should be permissive")
                    
            # Production should be most strict
            elif environment == "production":
                # Should require all security configurations
                self.mock_config.jwt_secret_key = "short"  # Too short for production
                
                with pytest.raises(ConfigurationValidationError):
                    self.validator.validate_config(self.mock_config)
                    
    @pytest.mark.unit
    def test_langfuse_monitoring_configuration(self):
        """Test that Langfuse configuration supports business monitoring requirements."""
        # Test production monitoring requirements
        self.mock_config.environment = "production"
        self.mock_config.langfuse.secret_key = None
        self.mock_config.langfuse.public_key = None
        
        # Should not raise exception but should log warnings
        with patch.object(self.validator, '_logger') as mock_logger:
            self.validator.validate_config(self.mock_config)
            
            # Should warn about missing monitoring keys
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if "Langfuse" in str(call)]
            assert len(warning_calls) > 0, \
                "Should warn about missing Langfuse keys in production"
                
    @pytest.mark.unit
    def test_auth_status_determination_business_logic(self):
        """Test that auth status determination provides accurate business intelligence."""
        # Test full auth configuration
        self.mock_config.jwt_secret_key = "valid-jwt-secret-key-32-characters"
        self.mock_config.oauth_config.client_id = "valid-oauth-client-id"
        
        auth_status = self.validator._get_auth_status(self.mock_config)
        assert auth_status == "JWT+OAuth", \
            "Full auth config should be identified as JWT+OAuth"
            
        # Test partial auth configuration
        self.mock_config.oauth_config.client_id = None
        
        auth_status = self.validator._get_auth_status(self.mock_config)
        assert auth_status == "Partial", \
            "Incomplete auth config should be identified as Partial"
            
        # Test no auth configuration
        self.mock_config.jwt_secret_key = None
        
        auth_status = self.validator._get_auth_status(self.mock_config)
        assert auth_status == "Partial", \
            "No auth config should be identified as Partial"