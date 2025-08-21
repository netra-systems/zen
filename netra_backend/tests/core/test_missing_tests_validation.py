"""
Validation and Type Checking Tests - Focused module for validation logic
Tests 11, 12, 14 from original missing tests covering:
- Configuration validator schema validation
- Error context capture and validation
- Custom exception types and validation
"""

import pytest
from unittest.mock import Mock
from cryptography.fernet import Fernet
from pydantic import ValidationError


# Test 11: config_validator_schema_validation
class TestConfigValidator:
    """Test configuration schema validation."""
    
    @pytest.fixture
    def validator(self):
        from netra_backend.app.core.config_validator import ConfigValidator
        return ConfigValidator()
    
    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.environment = "production"
        config.database_url = "postgresql://user:pass@localhost/db"
        config.jwt_secret_key = "a" * 32
        config.fernet_key = Fernet.generate_key()
        config.clickhouse_logging = Mock(enabled=True)
        config.clickhouse_native = Mock(host="localhost", password="pass")
        config.clickhouse_https = Mock(host="localhost", password="pass")
        config.oauth_config = Mock(client_id="id", client_secret="secret")
        config.llm_configs = {
            "default": Mock(api_key="key", model_name="model", provider="openai")
        }
        config.redis = Mock(host="localhost", password="pass")
        config.langfuse = Mock(secret_key="key", public_key="pub")
        return config
    
    def test_valid_config_passes_validation(self, validator, mock_config):
        """Test that valid configuration passes validation."""
        validator.validate_config(mock_config)
    
    def test_invalid_database_url_rejected(self, validator, mock_config):
        """Test that invalid database URL is rejected."""
        from netra_backend.app.core.config_validator import ConfigurationValidationError
        
        mock_config.database_url = "mysql://user:pass@localhost/db"
        with pytest.raises(ConfigurationValidationError, match="Database URL must be a PostgreSQL"):
            validator.validate_config(mock_config)
    
    def test_missing_jwt_secret_rejected(self, validator, mock_config):
        """Test that missing JWT secret is rejected."""
        from netra_backend.app.core.config_validator import ConfigurationValidationError
        
        mock_config.jwt_secret_key = None
        with pytest.raises(ConfigurationValidationError, match="JWT secret key is not configured"):
            validator.validate_config(mock_config)
    
    def test_weak_jwt_secret_in_production_rejected(self, validator, mock_config):
        """Test that weak JWT secret in production is rejected."""
        from netra_backend.app.core.config_validator import ConfigurationValidationError
        
        mock_config.jwt_secret_key = "short"
        with pytest.raises(ConfigurationValidationError, match="JWT secret key must be at least 32"):
            validator.validate_config(mock_config)
    
    def test_validation_report_generation(self, validator, mock_config):
        """Test validation report generation."""
        report = validator.get_validation_report(mock_config)
        assert any("✓" in line for line in report)
        assert any("Environment: production" in line for line in report)
    
    def test_environment_specific_validation(self, validator, mock_config):
        """Test validation rules change by environment."""
        # Development should allow weaker secrets
        mock_config.environment = "development"
        mock_config.jwt_secret_key = "dev_secret"
        validator.validate_config(mock_config)  # Should not raise
        
        # Production requires stronger secrets
        mock_config.environment = "production"
        from netra_backend.app.core.config_validator import ConfigurationValidationError
        with pytest.raises(ConfigurationValidationError):
            validator.validate_config(mock_config)
    
    def test_required_field_validation(self, validator, mock_config):
        """Test required fields are validated."""
        from netra_backend.app.core.config_validator import ConfigurationValidationError
        
        # Remove required field
        delattr(mock_config, 'database_url')
        with pytest.raises(ConfigurationValidationError, match="database_url is required"):
            validator.validate_config(mock_config)


# Test 12: error_context_capture
class TestErrorContext:
    """Test error context preservation and validation."""
    
    @pytest.fixture
    def error_context(self):
        from netra_backend.app.core.error_context import ErrorContext
        return ErrorContext()
    
    def test_trace_id_management(self, error_context):
        """Test trace ID generation and retrieval."""
        trace_id = error_context.generate_trace_id()
        assert trace_id != None
        assert error_context.get_trace_id() == trace_id
        
        # Set a specific trace ID
        new_trace_id = "test-trace-123"
        error_context.set_trace_id(new_trace_id)
        assert error_context.get_trace_id() == new_trace_id
    
    def test_request_id_context(self, error_context):
        """Test request ID context management."""
        request_id = "req-456"
        error_context.set_request_id(request_id)
        assert error_context.get_request_id() == request_id
    
    def test_user_id_context(self, error_context):
        """Test user ID context management."""
        user_id = "user-789"
        error_context.set_user_id(user_id)
        assert error_context.get_user_id() == user_id
    
    def test_context_validation(self, error_context):
        """Test context data validation."""
        # Valid UUID format
        valid_trace_id = "12345678-1234-5678-9012-123456789012"
        error_context.set_trace_id(valid_trace_id)
        assert error_context.get_trace_id() == valid_trace_id
        
        # Invalid format should be rejected
        with pytest.raises(ValueError, match="Invalid trace ID format"):
            error_context.set_trace_id("invalid-trace-id")
    
    def test_context_serialization(self, error_context):
        """Test context can be serialized for logging."""
        error_context.set_trace_id("trace-123")
        error_context.set_request_id("req-456")
        error_context.set_user_id("user-789")
        
        serialized = error_context.serialize()
        assert serialized["trace_id"] == "trace-123"
        assert serialized["request_id"] == "req-456"
        assert serialized["user_id"] == "user-789"
    
    def test_context_cleanup(self, error_context):
        """Test context cleanup after request."""
        error_context.set_trace_id("trace-123")
        error_context.set_request_id("req-456")
        
        error_context.clear_context()
        assert error_context.get_trace_id() is None
        assert error_context.get_request_id() is None


# Test 14: exceptions_custom_types
class TestCustomExceptions:
    """Test custom exception behaviors and validation."""
    
    def test_netra_exception_hierarchy(self):
        """Test NetraException hierarchy."""
        from netra_backend.app.core.exceptions import NetraException, ValidationException, AuthenticationException
        
        assert issubclass(ValidationException, NetraException)
        assert issubclass(AuthenticationException, NetraException)
    
    def test_exception_with_context(self):
        """Test exceptions with context data."""
        from netra_backend.app.core.exceptions import NetraException
        
        exc = NetraException("Test error", context={"user_id": "123"})
        assert str(exc) == "Test error"
        assert exc.context["user_id"] == "123"
    
    def test_exception_serialization(self):
        """Test exception can be serialized."""
        from netra_backend.app.core.exceptions import ValidationException
        
        exc = ValidationException("Invalid input", field="email", value="invalid")
        exc_dict = exc.to_dict()
        assert exc_dict["message"] == "Invalid input"
        assert exc_dict["field"] == "email"
        assert exc_dict["value"] == "invalid"
    
    def test_validation_exception_details(self):
        """Test validation exception includes detailed info."""
        from netra_backend.app.core.exceptions import ValidationException
        
        exc = ValidationException(
            "Field validation failed",
            field="age",
            value=-5,
            constraint="must be positive",
            error_code="FIELD_CONSTRAINT_VIOLATION"
        )
        
        assert exc.field == "age"
        assert exc.value == -5
        assert exc.constraint == "must be positive"
        assert exc.error_code == "FIELD_CONSTRAINT_VIOLATION"
    
    def test_authentication_exception_details(self):
        """Test authentication exception includes auth details."""
        from netra_backend.app.core.exceptions import AuthenticationError
        
        exc = AuthenticationError(
            "Invalid credentials",
            auth_method="jwt",
            user_id="123",
            failure_reason="token_expired"
        )
        
        assert exc.auth_method == "jwt"
        assert exc.user_id == "123"
        assert exc.failure_reason == "token_expired"
    
    def test_exception_chaining(self):
        """Test exception chaining for root cause analysis."""
        from netra_backend.app.core.exceptions import NetraException, ValidationException
        
        try:
            raise ValueError("Original error")
        except ValueError as e:
            chained_exc = ValidationException("Validation failed", caused_by=e)
            assert chained_exc.caused_by is e
            assert isinstance(chained_exc.caused_by, ValueError)
    
    def test_exception_severity_levels(self):
        """Test exception severity classification."""
        from netra_backend.app.core.exceptions import NetraException
        
        critical_exc = NetraException("Critical error", severity="critical")
        warning_exc = NetraException("Warning message", severity="warning")
        
        assert critical_exc.severity == "critical"
        assert warning_exc.severity == "warning"
        assert critical_exc.is_critical()
        assert not warning_exc.is_critical()


# Additional validation utilities
class TestValidationUtilities:
    """Test validation utility functions."""
    
    def test_pydantic_model_validation(self):
        """Test Pydantic model validation integration."""
        model = self._create_test_model()
        self._test_valid_model_data(model)
        self._test_invalid_model_data()
    
    def _create_test_model(self):
        """Helper to create test model."""
        from pydantic import BaseModel
        from typing import Optional
        
        class TestModel(BaseModel):
            name: str
            age: int
            email: Optional[str] = None
        return TestModel
    
    def _test_valid_model_data(self, TestModel):
        """Test valid model data."""
        valid_data = {"name": "John", "age": 30}
        model = TestModel(**valid_data)
        assert model.name == "John"
        assert model.age == 30
    
    def _test_invalid_model_data(self):
        """Test invalid model data raises validation error."""
        from pydantic import ValidationError
        TestModel = self._create_test_model()
        invalid_data = {"name": "John", "age": "not_a_number"}
        with pytest.raises(ValidationError):
            TestModel(**invalid_data)
    
    def test_input_sanitization(self):
        """Test input sanitization for security."""
        from netra_backend.app.core.validation_utils import sanitize_input
        
        # SQL injection attempt
        malicious_input = "'; DROP TABLE users; --"
        sanitized = sanitize_input(malicious_input)
        assert "DROP TABLE" not in sanitized
        
        # XSS attempt
        xss_input = "<script>alert('xss')</script>"
        sanitized = sanitize_input(xss_input)
        assert "<script>" not in sanitized
    
    def test_data_type_validation(self):
        """Test data type validation utilities."""
        from netra_backend.app.core.validation_utils import validate_data_type
        
        assert validate_data_type(123, int) == True
        assert validate_data_type("123", int) == False
        assert validate_data_type(["a", "b"], list) == True
        assert validate_data_type({"key": "value"}, dict) == True


# Run validation tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-k", "validation"])
