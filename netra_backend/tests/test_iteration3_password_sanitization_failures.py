"""
PostgreSQL Password Sanitization Failure Tests - Iteration 3 Persistent Issues

These tests WILL FAIL until password sanitization corruption is fixed.
Purpose: Replicate specific password corruption issues found in iteration 3.

Critical Issue: Secret sanitization corrupting passwords causing auth failures.
"""

import pytest
import re
from sqlalchemy.exc import OperationalError
import psycopg2
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.db.database_manager import DatabaseManager


class TestPasswordSanitizationCorruption:
    """Tests that demonstrate password corruption during sanitization"""
    
    def test_password_with_special_characters_corrupted_by_sanitization(self):
        """
        Test: Passwords with special characters get corrupted during sanitization
        This test SHOULD FAIL until sanitization preserves password integrity
        """
        # Passwords that commonly get corrupted by over-aggressive sanitization
        passwords_with_special_chars = [
            "myP@ssw0rd!",  # Common special chars
            "p@ss#w$rd%",   # Multiple special chars  
            "password@123", # @ symbol (common in emails/passwords)
            "P@$$w0rd!",    # Dollar signs
            "test#pass$",   # Hash and dollar
            "my!pass@word", # Exclamation and @
        ]
        
        for password in passwords_with_special_chars:
            # Create URL with special character password
            original_url = f"postgresql://postgres:{password}@localhost:5432/netra_db"
            
            # Mock the sanitization process that might corrupt passwords
            with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment._sanitize_value') as mock_sanitize:
                # Simulate over-aggressive sanitization that corrupts passwords
                mock_sanitize.return_value = re.sub(r'[!@#$%^&*]', '', password)  # Remove special chars
                
                env = IsolatedEnvironment(isolation_mode=True)
                env.set("DATABASE_URL", original_url, "test")
                
                # Get sanitized URL
                sanitized_url = env.get("DATABASE_URL")
                
                # Verify password was corrupted
                assert password not in sanitized_url, f"Password '{password}' should be corrupted by sanitization"
                
                # This should fail because sanitized password won't work for auth
                with pytest.raises((ValueError, OperationalError)) as exc_info:
                    # Try to create connection with corrupted password
                    manager = DatabaseManager()
                    # This should detect that sanitization corrupted the password
                    manager._validate_password_integrity(original_url, sanitized_url)
                
                error_msg = str(exc_info.value).lower()
                assert any(phrase in error_msg for phrase in [
                    "password corrupted",
                    "sanitization error", 
                    "password integrity",
                    "authentication will fail"
                ]), f"Expected password corruption error for '{password}', got: {exc_info.value}"

    def test_url_encoding_corruption_in_passwords(self):
        """
        Test: URL encoding/decoding corrupts passwords during sanitization
        This test SHOULD FAIL until URL encoding is handled correctly
        """
        # Passwords that get corrupted by URL encoding issues
        passwords_with_url_chars = [
            "pass%20word",    # Space encoded as %20
            "my%40password",  # @ encoded as %40  
            "test%23pass",    # # encoded as %23
            "pass+word",      # Plus sign
            "my&password",    # Ampersand
            "test=pass",      # Equals sign
        ]
        
        for password in passwords_with_url_chars:
            original_url = f"postgresql://postgres:{password}@localhost:5432/netra_db"
            
            # Mock URL sanitization that corrupts encoding
            with patch('urllib.parse.unquote') as mock_unquote:
                # Simulate incorrect URL decoding
                mock_unquote.return_value = password.replace('%20', '').replace('%40', '').replace('%23', '')
                
                # Should fail because password encoding/decoding is wrong
                with pytest.raises(ValueError) as exc_info:
                    env = IsolatedEnvironment(isolation_mode=True)
                    env.set("DATABASE_URL", original_url, "test")
                    
                    # This should validate that URL encoding doesn't corrupt passwords
                    manager = DatabaseManager()
                    manager._validate_url_encoding_integrity(original_url)
                
                assert "url encoding" in str(exc_info.value).lower(), \
                    f"Expected URL encoding error for password '{password}'"

    def test_environment_variable_sanitization_strips_password_content(self):
        """
        Test: Environment variable sanitization removes password content
        This test SHOULD FAIL until env var sanitization preserves passwords
        """
        # Test passwords that might be treated as "dangerous" content
        sensitive_passwords = [
            "javascript:alert(1)",  # Might be treated as XSS
            "<script>alert(1)</script>",  # HTML tags
            "DROP TABLE users;",    # SQL injection pattern
            "../../etc/passwd",     # Path traversal pattern
            "${jndi:ldap://",      # Log4j pattern
            "password'; DROP--",    # SQL injection
        ]
        
        for password in sensitive_passwords:
            original_url = f"postgresql://postgres:{password}@localhost:5432/netra_db"
            
            env = IsolatedEnvironment(isolation_mode=True)
            env.set("DATABASE_URL", original_url, "test")
            
            # Should fail because sanitization removes "dangerous" password content
            with pytest.raises(ValueError) as exc_info:
                sanitized_url = env.get("DATABASE_URL") 
                
                # Validate that password wasn't stripped/corrupted by security sanitization
                if password not in sanitized_url:
                    raise ValueError(f"Password was corrupted by security sanitization: {password}")
            
            error_msg = str(exc_info.value).lower()
            assert "sanitization" in error_msg or "corrupted" in error_msg, \
                f"Expected sanitization corruption error for password: {password}"

    def test_database_url_password_extraction_integrity(self):
        """
        Test: Password extraction from database URL maintains integrity
        This test SHOULD FAIL until password extraction is robust
        """
        complex_passwords = [
            "p@ss:w0rd",      # Contains colon (URL delimiter)
            "pass@host:5432", # Contains host-like pattern
            "user:pass@db",   # Contains @ (URL delimiter)
            "my//password",   # Contains // (URL scheme separator)
            "pass?query=1",   # Contains query parameters
            "pass#fragment",  # Contains URL fragment
        ]
        
        for password in complex_passwords:
            url = f"postgresql://postgres:{password}@localhost:5432/netra_db"
            
            # Should fail because password extraction gets confused by URL delimiters
            with pytest.raises(ValueError) as exc_info:
                manager = DatabaseManager()
                extracted_password = manager._extract_password_from_url(url)
                
                if extracted_password != password:
                    raise ValueError(f"Password extraction failed: expected '{password}', got '{extracted_password}'")
            
            assert "extraction failed" in str(exc_info.value).lower(), \
                f"Expected password extraction error for: {password}"


class TestPasswordValidationBeforeConnection:
    """Tests for password validation before attempting database connections"""
    
    def test_empty_password_after_sanitization_detected(self):
        """
        Test: Empty passwords after sanitization should be detected
        This test SHOULD FAIL until pre-connection validation exists
        """
        # Password that becomes empty after sanitization
        original_password = "!@#$%^&*()"  # Only special characters
        original_url = f"postgresql://postgres:{original_password}@localhost:5432/netra_db"
        
        # Mock sanitization that removes all special characters
        with patch.object(IsolatedEnvironment, '_sanitize_value') as mock_sanitize:
            mock_sanitize.return_value = ""  # All characters removed
            
            env = IsolatedEnvironment(isolation_mode=True)
            env.set("DATABASE_URL", original_url, "test")
            
            # Should fail because empty password after sanitization should be caught
            with pytest.raises(ValueError) as exc_info:
                manager = DatabaseManager()
                sanitized_url = env.get("DATABASE_URL")
                manager._validate_credentials_before_connection(sanitized_url)
            
            error_msg = str(exc_info.value).lower()
            assert any(phrase in error_msg for phrase in [
                "empty password",
                "missing password",
                "password required",
                "invalid credentials"
            ]), f"Expected empty password validation error, got: {exc_info.value}"

    def test_placeholder_password_after_sanitization_detected(self):
        """
        Test: Placeholder passwords after sanitization should be rejected
        This test SHOULD FAIL until placeholder detection exists
        """
        # Passwords that might become placeholders after sanitization
        problematic_passwords = [
            "********",      # Might be sanitization result
            "REDACTED",      # Common redaction placeholder
            "[FILTERED]",    # Filter placeholder
            "***HIDDEN***",  # Hidden placeholder
            "PASSWORD",      # Generic placeholder
            "SECRET",        # Generic secret placeholder
        ]
        
        for placeholder in problematic_passwords:
            url = f"postgresql://postgres:{placeholder}@localhost:5432/netra_db"
            
            # Should fail because placeholders should be rejected
            with pytest.raises(ValueError) as exc_info:
                manager = DatabaseManager()
                manager._validate_credentials_before_connection(url)
            
            error_msg = str(exc_info.value).lower()
            assert any(phrase in error_msg for phrase in [
                "placeholder",
                "invalid password",
                "generic password",
                "not allowed"
            ]), f"Expected placeholder rejection for '{placeholder}', got: {exc_info.value}"

    def test_password_length_validation_after_sanitization(self):
        """
        Test: Password length validation after sanitization
        This test SHOULD FAIL until length validation exists
        """
        # Test passwords that might become too short after sanitization
        test_cases = [
            ("a!b", 1),     # Special chars removed, too short
            ("!!!", 0),     # All removed, empty
            ("a@b#c", 3),   # Some chars removed
            ("!@#$%", 0),   # All special chars removed
        ]
        
        for original_password, expected_length_after_sanitization in test_cases:
            url = f"postgresql://postgres:{original_password}@localhost:5432/netra_db"
            
            # Mock sanitization that removes special characters  
            with patch.object(IsolatedEnvironment, '_sanitize_value') as mock_sanitize:
                # Remove special characters
                sanitized = re.sub(r'[!@#$%^&*]', '', original_password)
                mock_sanitize.return_value = sanitized
                
                if len(sanitized) < 6:  # Assuming minimum password length
                    # Should fail because password too short after sanitization
                    with pytest.raises(ValueError) as exc_info:
                        env = IsolatedEnvironment(isolation_mode=True)
                        env.set("DATABASE_URL", url, "test")
                        
                        manager = DatabaseManager()
                        sanitized_url = env.get("DATABASE_URL")
                        manager._validate_password_length(sanitized_url)
                    
                    assert "password length" in str(exc_info.value).lower(), \
                        f"Expected password length validation error for '{original_password}'"


class TestStagingPasswordRequirements:
    """Tests for strict password requirements in staging environment"""
    
    def test_staging_rejects_passwords_corrupted_by_sanitization(self):
        """
        Test: Staging environment should reject corrupted passwords
        This test SHOULD FAIL until staging validation is strict
        """
        staging_env_vars = {
            'ENVIRONMENT': 'staging',
        }
        
        # Passwords that get corrupted by sanitization
        corrupted_password_cases = [
            ("P@ssw0rd!", "Pssw0rd"),      # Special chars removed
            ("my#pass$", "mypass"),        # Special chars removed  
            ("test@123", "test123"),       # @ removed
            ("pass!word", "password"),     # ! removed
        ]
        
        for original, corrupted in corrupted_password_cases:
            url_original = f"postgresql://postgres:{original}@localhost:5432/netra_staging"
            url_corrupted = f"postgresql://postgres:{corrupted}@localhost:5432/netra_staging"
            
            with patch.dict('os.environ', staging_env_vars):
                # Should fail because staging should detect password corruption
                with pytest.raises(ValueError) as exc_info:
                    env = IsolatedEnvironment(isolation_mode=False)  # Use real env
                    
                    # Simulate the sanitization corruption
                    env._environment_vars["DATABASE_URL"] = url_corrupted
                    
                    # Staging should validate that password wasn't corrupted
                    if env.get('ENVIRONMENT') == 'staging':
                        manager = DatabaseManager()
                        manager._validate_staging_password_integrity(url_original, url_corrupted)
                
                error_msg = str(exc_info.value).lower()
                assert any(phrase in error_msg for phrase in [
                    "password corrupted",
                    "staging validation",
                    "password integrity",
                    "sanitization error"
                ]), f"Staging should detect password corruption from '{original}' to '{corrupted}'"

    def test_staging_password_entropy_validation(self):
        """
        Test: Staging should validate password entropy after sanitization
        This test SHOULD FAIL until entropy validation exists
        """
        staging_env_vars = {
            'ENVIRONMENT': 'staging',
        }
        
        # Passwords with low entropy after sanitization
        low_entropy_after_sanitization = [
            ("!@#$%abcd", "abcd"),        # Only 4 chars left
            ("!!!aaa!!!", "aaa"),         # Only 3 repeated chars
            ("@@@123@@@", "123"),         # Only 3 chars left
            ("$$$test$$$", "test"),       # Common word left
        ]
        
        for original, after_sanitization in low_entropy_after_sanitization:
            with patch.dict('os.environ', staging_env_vars):
                # Should fail because low entropy passwords should be rejected in staging
                with pytest.raises(ValueError) as exc_info:
                    env = IsolatedEnvironment(isolation_mode=False)
                    
                    if env.get('ENVIRONMENT') == 'staging':
                        manager = DatabaseManager()
                        manager._validate_password_entropy(after_sanitization)
                
                error_msg = str(exc_info.value).lower()
                assert any(phrase in error_msg for phrase in [
                    "entropy",
                    "weak password", 
                    "password complexity",
                    "insufficient randomness"
                ]), f"Staging should reject low entropy password '{after_sanitization}'"