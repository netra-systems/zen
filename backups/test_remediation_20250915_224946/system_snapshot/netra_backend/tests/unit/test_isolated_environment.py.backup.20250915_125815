"""
Comprehensive Unit Tests for IsolatedEnvironment - Configuration Management
Tests critical environment variable management business logic without external dependencies.

Business Value: Platform/Internal - Configuration Stability & Service Independence  
Validates that environment variables are managed consistently across services, preventing cascade failures.

Following CLAUDE.md guidelines:
- NO MOCKS in integration/E2E tests - unit tests can have limited mocks if needed
- Use SSOT patterns from test_framework/ssot/
- Each test MUST be designed to FAIL HARD - no try/except blocks in tests
- Tests must validate real business value
- Use descriptive test names that explain what is being tested
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

# Absolute imports per CLAUDE.md requirements
from shared.isolated_environment import IsolatedEnvironment, get_env, ValidationResult


class TestIsolatedEnvironmentCore:
    """Test core IsolatedEnvironment functionality that ensures configuration consistency."""
    
    def setup_method(self):
        """Setup clean environment for each test."""
        # Create fresh instance for each test to avoid state pollution
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
    
    def teardown_method(self):
        """Cleanup after each test."""
        if hasattr(self, 'env'):
            self.env.disable_isolation()
    
    def test_isolated_environment_prevents_os_environ_pollution_during_testing(self):
        """Test that IsolatedEnvironment prevents test variables from polluting os.environ."""
        # Arrange
        test_key = "TEST_POLLUTION_PREVENTION_KEY"
        test_value = "test-value-that-should-not-pollute-os-environ"
        original_os_environ_size = len(os.environ)
        
        # Ensure key doesn't exist initially
        assert test_key not in os.environ, f"Test key {test_key} must not exist in os.environ initially"
        assert self.env.get(test_key) is None, f"Test key {test_key} must not exist in isolated environment initially"
        
        # Act - Set variable in isolated environment
        set_result = self.env.set(test_key, test_value, "test_pollution_prevention")
        
        # Assert - Variable exists in isolated environment but NOT in os.environ
        assert set_result is True, "Setting variable in isolated environment must succeed"
        assert self.env.get(test_key) == test_value, f"Variable must be retrievable from isolated environment: expected {test_value}, got {self.env.get(test_key)}"
        assert test_key not in os.environ, f"Isolated environment variable must NOT pollute os.environ"
        assert len(os.environ) == original_os_environ_size, f"os.environ size must remain unchanged: expected {original_os_environ_size}, got {len(os.environ)}"
        
        # Verify isolation works both ways
        os_test_key = "TEST_OS_ENVIRON_ISOLATION_KEY"
        os_test_value = "os-environ-value-should-not-appear-in-isolation"
        os.environ[os_test_key] = os_test_value
        
        # In isolation mode, new os.environ changes may or may not appear depending on implementation
        # The key point is that isolated variables don't pollute os.environ
        isolated_value = self.env.get(os_test_key)
        if isolated_value == os_test_value:
            # If it appears, that's OK - isolation mainly prevents pollution TO os.environ
            pass
        else:
            # If it doesn't appear, that's also OK - strict isolation
            assert isolated_value is None, "If isolated, new os.environ variables should not appear"
        
        # Cleanup
        del os.environ[os_test_key]
    
    def test_isolated_environment_singleton_consistency_prevents_configuration_drift(self):
        """Test that IsolatedEnvironment maintains singleton consistency to prevent config drift."""
        # Arrange & Act
        instance1 = IsolatedEnvironment()
        instance2 = IsolatedEnvironment() 
        instance3 = get_env()
        
        # Assert - All instances must be the same object (singleton pattern)
        assert instance1 is instance2, "IsolatedEnvironment() calls must return same singleton instance"
        assert instance2 is instance3, "get_env() must return same singleton instance as IsolatedEnvironment()"
        assert id(instance1) == id(instance2) == id(instance3), f"All instances must have same memory ID: {id(instance1)}, {id(instance2)}, {id(instance3)}"
        
        # Test that configuration changes are consistent across references
        test_key = "SINGLETON_CONSISTENCY_TEST"
        test_value = "consistent-value-across-all-references"
        
        # Set via instance1
        instance1.set(test_key, test_value, "singleton_test")
        
        # Verify via all other references
        assert instance2.get(test_key) == test_value, f"Value set via instance1 must be accessible via instance2: expected {test_value}, got {instance2.get(test_key)}"
        assert instance3.get(test_key) == test_value, f"Value set via instance1 must be accessible via get_env(): expected {test_value}, got {instance3.get(test_key)}"
        
        # Modify via instance2, verify via others
        new_value = "updated-consistent-value"
        instance2.set(test_key, new_value, "singleton_test_update")
        
        assert instance1.get(test_key) == new_value, f"Value updated via instance2 must be accessible via instance1: expected {new_value}, got {instance1.get(test_key)}"
        assert instance3.get(test_key) == new_value, f"Value updated via instance2 must be accessible via get_env(): expected {new_value}, got {instance3.get(test_key)}"
    
    def test_isolated_environment_provides_test_defaults_preventing_configuration_failures(self):
        """Test that IsolatedEnvironment provides OAuth test defaults to prevent CentralConfigurationValidator failures."""
        # Arrange
        self.env.disable_isolation()  # Start without isolation
        
        # Simulate test context by setting test indicators
        with patch.dict(os.environ, {'PYTEST_CURRENT_TEST': 'test_session', 'ENVIRONMENT': 'test', 'TESTING': 'true'}):
            # Create new instance that will detect test context
            test_env = IsolatedEnvironment()
            test_env.enable_isolation()  # Ensure isolation is enabled to get test defaults
            
            # Assert - Critical OAuth test credentials must be available
            oauth_client_id = test_env.get("GOOGLE_OAUTH_CLIENT_ID_TEST")
            assert oauth_client_id is not None, "OAuth client ID test default must be provided"
            assert oauth_client_id == "test-oauth-client-id-for-automated-testing", f"OAuth client ID must match expected test default: got {oauth_client_id}"
            
            oauth_client_secret = test_env.get("GOOGLE_OAUTH_CLIENT_SECRET_TEST")
            assert oauth_client_secret is not None, "OAuth client secret test default must be provided" 
            assert oauth_client_secret == "test-oauth-client-secret-for-automated-testing", f"OAuth client secret must match expected test default: got {oauth_client_secret}"
            
            # E2E OAuth simulation key must be available
            e2e_oauth_key = test_env.get("E2E_OAUTH_SIMULATION_KEY")
            assert e2e_oauth_key is not None, "E2E OAuth simulation key must be provided"
            assert e2e_oauth_key == "test-e2e-oauth-bypass-key-for-testing-only-unified-2025", f"E2E OAuth key must match expected default: got {e2e_oauth_key}"
            
            # JWT secret must be available for auth tests
            jwt_secret = test_env.get("JWT_SECRET_KEY")
            assert jwt_secret is not None, "JWT secret test default must be provided"
            assert len(jwt_secret) >= 32, f"JWT secret must be at least 32 characters for security: got {len(jwt_secret)} chars"
            
            # Database test defaults must be available
            postgres_host = test_env.get("POSTGRES_HOST")
            assert postgres_host == "localhost", f"Test database host must be localhost: got {postgres_host}"
            
            postgres_port = test_env.get("POSTGRES_PORT")
            assert postgres_port == "5434", f"Test database port must be 5434: got {postgres_port}"
    
    def test_isolated_environment_loads_env_file_without_overriding_existing_values(self):
        """Test that IsolatedEnvironment loads .env files without overriding existing environment values."""
        # Arrange - Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_env_file:
            temp_env_file.write("TEST_ENV_FILE_KEY1=env_file_value1\n")
            temp_env_file.write("TEST_ENV_FILE_KEY2=env_file_value2\n")
            temp_env_file.write("# This is a comment\n")
            temp_env_file.write("TEST_ENV_FILE_KEY3=\"quoted_value_3\"\n")
            temp_env_file.write("TEST_OVERRIDE_KEY=env_file_value_should_not_override\n")
            temp_env_file_path = temp_env_file.name
        
        # Set existing value that should NOT be overridden
        self.env.set("TEST_OVERRIDE_KEY", "existing_value_should_remain", "test_setup")
        original_override_value = self.env.get("TEST_OVERRIDE_KEY")
        
        try:
            # Act - Load env file
            loaded_count, errors = self.env.load_from_file(temp_env_file_path, "test_env_file", override_existing=False)
            
            # Assert - File must be loaded successfully
            assert loaded_count > 0, f"Env file must load some variables: loaded {loaded_count}"
            assert len(errors) == 0, f"Env file loading must not produce errors: {errors}"
            
            # New variables from file must be available
            assert self.env.get("TEST_ENV_FILE_KEY1") == "env_file_value1", "New env file variable must be loaded"
            assert self.env.get("TEST_ENV_FILE_KEY2") == "env_file_value2", "Second env file variable must be loaded"
            assert self.env.get("TEST_ENV_FILE_KEY3") == "quoted_value_3", "Quoted env file variable must be loaded without quotes"
            
            # Existing values must NOT be overridden
            assert self.env.get("TEST_OVERRIDE_KEY") == original_override_value, f"Existing variable must not be overridden: expected {original_override_value}, got {self.env.get('TEST_OVERRIDE_KEY')}"
            
            # Test loading with override enabled
            loaded_count_override, errors_override = self.env.load_from_file(temp_env_file_path, "test_env_file_override", override_existing=True)
            assert loaded_count_override > 0, "Override loading must work"
            assert self.env.get("TEST_OVERRIDE_KEY") == "env_file_value_should_not_override", "With override=True, existing values should be overridden"
            
        finally:
            # Cleanup
            os.unlink(temp_env_file_path)
    
    def test_isolated_environment_validates_staging_database_credentials_preventing_failures(self):
        """Test that IsolatedEnvironment validates staging database credentials to prevent connection failures."""
        # Arrange - Set up staging environment
        staging_env = IsolatedEnvironment()
        staging_env.enable_isolation()
        staging_env.set("ENVIRONMENT", "staging", "test_setup")
        
        # Test valid staging database credentials
        staging_env.set("POSTGRES_HOST", "staging-db.googleapis.com", "test_staging_db")
        staging_env.set("POSTGRES_USER", "postgres", "test_staging_db")
        staging_env.set("POSTGRES_PASSWORD", "secure_staging_password_123", "test_staging_db")
        staging_env.set("POSTGRES_DB", "netra_staging", "test_staging_db")
        
        # Act - Validate staging database credentials
        validation_result = staging_env.validate_staging_database_credentials()
        
        # Assert - Valid credentials must pass validation
        assert validation_result["valid"] is True, f"Valid staging credentials must pass validation: {validation_result['issues']}"
        assert len(validation_result["issues"]) == 0, f"Valid staging credentials must have no issues: {validation_result['issues']}"
        
        # Test invalid scenarios that must be detected
        
        # Invalid host (localhost not allowed in staging)
        staging_env.set("POSTGRES_HOST", "localhost", "test_invalid_host")
        invalid_host_result = staging_env.validate_staging_database_credentials()
        assert invalid_host_result["valid"] is False, "Localhost host must be rejected in staging"
        assert any("localhost" in issue.lower() for issue in invalid_host_result["issues"]), f"Validation must identify localhost issue: {invalid_host_result['issues']}"
        
        # Invalid user pattern
        staging_env.set("POSTGRES_HOST", "staging-db.googleapis.com", "test_fix_host")  # Fix host
        staging_env.set("POSTGRES_USER", "user_pr-4", "test_invalid_user")
        invalid_user_result = staging_env.validate_staging_database_credentials()
        assert invalid_user_result["valid"] is False, "Invalid user pattern must be rejected"
        assert any("user_pr-4" in issue for issue in invalid_user_result["issues"]), f"Validation must identify invalid user pattern: {invalid_user_result['issues']}"
        
        # Weak password
        staging_env.set("POSTGRES_USER", "postgres", "test_fix_user")  # Fix user
        staging_env.set("POSTGRES_PASSWORD", "123", "test_weak_password")
        weak_password_result = staging_env.validate_staging_database_credentials()
        assert weak_password_result["valid"] is False, "Weak password must be rejected"
        assert any("too short" in issue.lower() for issue in weak_password_result["issues"]), f"Validation must identify weak password: {weak_password_result['issues']}"


class TestIsolatedEnvironmentValueSanitization:
    """Test environment value sanitization that prevents corruption and security issues."""
    
    def setup_method(self):
        """Setup clean environment for each test."""
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
    
    def teardown_method(self):
        """Cleanup after each test."""
        self.env.disable_isolation()
    
    def test_isolated_environment_sanitizes_database_urls_preserving_passwords_with_special_characters(self):
        """Test that database URL sanitization preserves password integrity while removing control characters."""
        # Arrange - Database URLs with various password complexities
        test_cases = [
            {
                "name": "complex_password_with_special_chars",
                "url": "postgresql://user:P@ssw0rd_simple@host:5432/db",
                "expected_password": "P@ssw0rd_simple",
                "description": "Complex password with some special characters must be preserved"
            },
            {
                "name": "password_with_control_chars", 
                "url": "postgresql://user:password\n\r\twith\x00control@host:5432/db",
                "expected_clean": True,
                "description": "Control characters must be removed from password"
            },
            {
                "name": "password_with_unicode",
                "url": "postgresql://user:[U+043F]apo[U+043B][U+044C]123@host:5432/db",
                "expected_password": "[U+043F]apo[U+043B][U+044C]123",
                "description": "Unicode characters in password must be preserved"
            }
        ]
        
        for test_case in test_cases:
            # Act - Set database URL (triggers sanitization)
            result = self.env.set("DATABASE_URL", test_case["url"], f"test_{test_case['name']}")
            
            # Assert - Sanitization must succeed
            assert result is True, f"Setting database URL must succeed for {test_case['name']}"
            
            # Get sanitized URL
            sanitized_url = self.env.get("DATABASE_URL")
            assert sanitized_url is not None, f"Sanitized URL must be retrievable for {test_case['name']}"
            
            # Verify password preservation or cleaning as expected
            if "expected_password" in test_case:
                # Password must be preserved exactly
                assert test_case["expected_password"] in sanitized_url, f"Password must be preserved in {test_case['name']}: {sanitized_url}"
            
            if test_case.get("expected_clean"):
                # Control characters must be removed
                assert "\n" not in sanitized_url, f"Newline must be removed from {test_case['name']}: {sanitized_url}"
                assert "\r" not in sanitized_url, f"Carriage return must be removed from {test_case['name']}: {sanitized_url}"
                assert "\t" not in sanitized_url, f"Tab must be removed from {test_case['name']}: {sanitized_url}"
                assert "\x00" not in sanitized_url, f"Null byte must be removed from {test_case['name']}: {sanitized_url}"
            
            # URL must still be parseable after sanitization
            from urllib.parse import urlparse
            try:
                parsed = urlparse(sanitized_url)
                assert parsed.scheme in ["postgresql", "mysql", "sqlite"], f"URL scheme must be preserved for {test_case['name']}: {parsed.scheme}"
                assert parsed.hostname is not None, f"Hostname must be preserved for {test_case['name']}: {parsed.hostname}"
            except Exception as e:
                pytest.fail(f"Sanitized URL must be parseable for {test_case['name']}: {e}")