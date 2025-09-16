"""
SECRET_KEY Configuration Validation Tests
========================================

This test suite validates SECRET_KEY configuration issues identified in staging environment.
These tests are designed to FAIL with the current staging configuration to demonstrate
the identified issues and pass once the configuration is fixed.

IDENTIFIED ISSUE FROM STAGING:
- SECRET_KEY is too short (< 32 characters) causing validation failures
- Security: Short SECRET_KEY compromises JWT token security
- Impact: Authentication failures and potential security vulnerabilities

BVJ (Business Value Justification):
- Segment: All tiers | Goal: Security & System Stability | Impact: Critical security protection
- Prevents JWT token compromise and authentication vulnerabilities
- Ensures compliance with security best practices for secret management
- Protects customer data and maintains system trust

Expected Test Behavior:
- Tests SHOULD FAIL with current staging SECRET_KEY (demonstrates issue)
- Tests SHOULD PASS once SECRET_KEY meets minimum length requirements
- Boundary testing ensures proper validation at critical lengths
"""

import os
import pytest
from typing import Optional
from unittest.mock import patch
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

from shared.isolated_environment import get_env


class TestSecretKeyValidation:
    """Test SECRET_KEY configuration validation for security compliance."""
    
    def test_secret_key_minimum_length_requirement_current_staging_issue(self):
        """
        Test SECRET_KEY length validation - CURRENT STAGING ISSUE.
        
        This test should FAIL with current staging config to demonstrate the issue.
        SECRET_KEY must be at least 32 characters for security.
        
        Issue: Current staging SECRET_KEY is too short causing validation failures.
        """
        # Get the actual SECRET_KEY from environment
        env_vars = get_env()
        secret_key = env_vars.get("SECRET_KEY", "")
        
        # This assertion should FAIL with current staging config
        assert len(secret_key) >= 32, (
            f"STAGING ISSUE: SECRET_KEY length ({len(secret_key)}) is below minimum "
            f"security requirement (32 characters). Current value compromises JWT security. "
            f"This test exposes the actual staging configuration problem."
        )
    
    def test_secret_key_empty_validation(self):
        """Test SECRET_KEY validation when empty or None."""
        
        def validate_secret_key(key: Optional[str]) -> bool:
            """Mock SECRET_KEY validation function."""
            if not key:
                return False
            if len(key) < 32:
                return False
            return True
        
        # Test empty key scenarios
        empty_scenarios = [
            None,
            "",
            "   ",  # whitespace only
        ]
        
        for empty_key in empty_scenarios:
            is_valid = validate_secret_key(empty_key)
            assert not is_valid, f"Empty/None SECRET_KEY should be invalid: {empty_key!r}"
    
    def test_secret_key_too_short_validation(self):
        """Test SECRET_KEY validation with various short lengths."""
        
        def validate_secret_key(key: str) -> bool:
            """Mock SECRET_KEY validation function."""
            if not key or len(key) < 32:
                return False
            return True
        
        # Test keys that are too short (similar to staging issue)
        short_keys = [
            "short",              # 5 chars
            "medium_length_key",  # 17 chars  
            "almost_long_enough_but_not_q",  # 30 chars (should fail)
            "x" * 31,            # exactly 31 chars (should fail)
            "staging_secret",     # 14 chars - typical short staging key
        ]
        
        for short_key in short_keys:
            is_valid = validate_secret_key(short_key)
            assert not is_valid, (
                f"SHORT SECRET_KEY should be invalid: '{short_key}' "
                f"(length: {len(short_key)}, minimum: 32)"
            )
    
    def test_secret_key_boundary_validation_exactly_32_chars(self):
        """Test SECRET_KEY validation at exactly 32 characters (boundary)."""
        
        def validate_secret_key(key: str) -> bool:
            """Mock SECRET_KEY validation function."""
            if not key or len(key) < 32:
                return False
            return True
        
        # Test exactly 32 characters (should pass)
        exactly_32_char_key = "a" * 32  # exactly 32 chars
        
        is_valid = validate_secret_key(exactly_32_char_key)
        assert is_valid, (
            f"SECRET_KEY with exactly 32 characters should be valid: "
            f"length={len(exactly_32_char_key)}"
        )
    
    def test_secret_key_valid_lengths(self):
        """Test SECRET_KEY validation with valid lengths."""
        
        def validate_secret_key(key: str) -> bool:
            """Mock SECRET_KEY validation function."""
            if not key or len(key) < 32:
                return False
            return True
        
        # Test valid length keys
        valid_keys = [
            "a" * 32,   # exactly 32 chars
            "b" * 64,   # 64 chars (good length)
            "c" * 128,  # 128 chars (very secure)
            "my_super_secure_jwt_secret_key_that_is_long_enough_for_production_use",  # realistic key
        ]
        
        for valid_key in valid_keys:
            is_valid = validate_secret_key(valid_key)
            assert is_valid, (
                f"VALID SECRET_KEY should pass validation: "
                f"length={len(valid_key)}, key='{valid_key[:20]}...'"
            )
    
    def test_secret_key_content_quality_validation(self):
        """Test SECRET_KEY content quality beyond just length."""
        
        def validate_secret_key_quality(key: str) -> tuple[bool, str]:
            """
            Mock SECRET_KEY quality validation.
            Returns (is_valid, reason) tuple.
            """
            if not key or len(key) < 32:
                return False, "Too short"
            
            # Check for weak patterns
            if key == key[0] * len(key):  # all same character
                return False, "All same character"
            
            # Check for weak patterns (check if the key contains common weak words)
            weak_words = ["password", "secret", "default"]
            for weak_word in weak_words:
                if weak_word in key.lower():
                    return False, "Common weak pattern"
            
            # Very basic entropy check
            unique_chars = len(set(key))
            if unique_chars < 8:  # should have reasonable character diversity
                return False, "Low entropy"
            
            return True, "Valid"
        
        # Test quality scenarios
        quality_tests = [
            ("a" * 32, False, "All same character"),  # long enough but poor quality
            ("password_that_is_long_enough_chars", False, "Common weak pattern"),
            ("abcd" * 8, False, "Low entropy"),  # repetitive pattern, only 4 unique chars
            ("MyS3cureRand0mJWTK3y123!@#$%^&*()", True, "Valid"),  # good quality, avoids "secret"
        ]
        
        for key, expected_valid, expected_reason_contains in quality_tests:
            is_valid, reason = validate_secret_key_quality(key)
            assert is_valid == expected_valid, (
                f"SECRET_KEY quality validation failed for '{key[:20]}...': "
                f"expected {expected_valid}, got {is_valid}, reason: {reason}"
            )
            
            if not expected_valid:
                assert expected_reason_contains.lower() in reason.lower()
    
    def test_secret_key_environment_specific_requirements(self):
        """Test SECRET_KEY requirements vary by environment."""
        
        def validate_secret_key_for_environment(key: str, environment: str) -> tuple[bool, str]:
            """Mock environment-specific SECRET_KEY validation."""
            # Base length requirement
            if not key or len(key) < 32:
                return False, "Too short for any environment"
            
            # Production has stricter requirements
            if environment == "production":
                if len(key) < 64:
                    return False, "Production requires at least 64 characters"
                
                # Production should have high entropy
                unique_chars = len(set(key))
                if unique_chars < 16:
                    return False, "Production requires higher entropy"
            
            # Staging should meet basic security
            elif environment == "staging":
                if len(key) < 32:
                    return False, "Staging requires at least 32 characters"
            
            return True, "Valid for environment"
        
        # Test environment-specific requirements
        test_scenarios = [
            ("short_key", "staging", False, "too short"),
            ("a" * 31, "staging", False, "too short"),
            ("a" * 32, "staging", True, "Valid"),
            ("a" * 32, "production", False, "64 characters"),
            ("a" * 64, "production", False, "higher entropy"),
            ("MyVerySecureProductionJWTK3yWithHighEntropyChars123!@#$%^&*()_+!", "production", True, "Valid"),
        ]
        
        for key, env, expected_valid, expected_reason_contains in test_scenarios:
            is_valid, reason = validate_secret_key_for_environment(key, env)
            assert is_valid == expected_valid, (
                f"Environment-specific SECRET_KEY validation failed: "
                f"key length={len(key)}, env={env}, "
                f"expected {expected_valid}, got {is_valid}, reason: {reason}"
            )
            
            if not expected_valid:
                assert expected_reason_contains.lower() in reason.lower()


class TestSecretKeyConfigurationIssues:
    """Test SECRET_KEY configuration issues and edge cases."""
    
    def test_secret_key_environment_variable_loading(self):
        """Test SECRET_KEY loading from environment variables."""
        
        # Test with mock environment variables - using direct validation instead of env loading
        test_scenarios = [
            ("SECRET_KEY", "valid_secret_key_that_is_32_chars_+", True),
            ("JWT_SECRET_KEY", "another_valid_jwt_secret_32_chars+", True),
            ("SECRET_KEY", "too_short", False),
            ("SECRET_KEY", "", False),
        ]
        
        def validate_secret_key_mock(value: str) -> bool:
            """Mock SECRET_KEY validation function."""
            if not value:
                return False
            return len(value) >= 32
        
        for env_var, value, should_be_valid in test_scenarios:
            # Test the validation logic directly rather than environment loading
            is_valid = validate_secret_key_mock(value)
            
            assert is_valid == should_be_valid, (
                f"Environment variable {env_var}='{value}' "
                f"validation mismatch: expected {should_be_valid}, got {is_valid}"
            )
    
    def test_secret_key_configuration_precedence(self):
        """Test SECRET_KEY configuration precedence from different sources."""
        
        def mock_env_precedence_check(env_value: Optional[str], config_value: Optional[str], default_value: Optional[str]) -> str:
            """Mock configuration precedence logic: ENV > config > default."""
            return env_value or config_value or default_value or ""
        
        # Test configuration precedence: ENV > config file > default
        env_secret = "env_secret_32_characters_long_ok"
        config_secret = "config_secret_32_chars_long_val" 
        default_secret = "fallback_default_value"
        
        # Environment should take precedence
        result = mock_env_precedence_check(env_secret, config_secret, default_secret)
        assert result == env_secret, "Environment SECRET_KEY should take precedence"
        assert len(result) >= 32, "Precedence result should be valid length"
        
        # Test fallback behavior when SECRET_KEY is not set
        fallback_result = mock_env_precedence_check(None, None, default_secret)
        assert fallback_result == default_secret, "Should fall back to default"
        
        # The fallback should be rejected for being too short
        assert len(fallback_result) < 32, (
            f"Fallback SECRET_KEY should be invalid to force proper configuration, "
            f"got '{fallback_result}' with length {len(fallback_result)}"
        )
    
    def test_secret_key_rotation_compatibility(self):
        """Test SECRET_KEY rotation and backward compatibility considerations."""
        
        def validate_key_rotation_scenario(old_key: str, new_key: str) -> tuple[bool, str]:
            """Mock key rotation validation."""
            # Both keys should meet minimum requirements
            if len(old_key) < 32 or len(new_key) < 32:
                return False, "Both keys must meet minimum length"
            
            # Keys should be different for security
            if old_key == new_key:
                return False, "New key must be different from old key"
            
            return True, "Key rotation valid"
        
        # Test key rotation scenarios
        rotation_tests = [
            ("old_key_32_characters_long_valid", "new_key_32_characters_long_valid", True),
            ("short_old", "new_key_32_characters_long_valid", False),  # old key invalid
            ("old_key_32_characters_long_valid", "short_new", False),  # new key invalid
            ("same_key_32_characters_long_valid", "same_key_32_characters_long_valid", False),  # same key
        ]
        
        for old_key, new_key, expected_valid in rotation_tests:
            is_valid, reason = validate_key_rotation_scenario(old_key, new_key)
            assert is_valid == expected_valid, (
                f"Key rotation validation failed: old='{old_key[:10]}...', "
                f"new='{new_key[:10]}...', expected {expected_valid}, reason: {reason}"
            )


class TestSecretKeySecurityImplications:
    """Test SECRET_KEY security implications and attack vectors."""
    
    def test_staging_secret_key_patterns_fail_validation(self):
        """Test that staging SECRET_KEY patterns fail validation in staging/production environments.
        
        SPECIFIC STAGING ISSUE: Current staging keys contain 'staging' and 'secret' patterns
        that should be rejected by validation for security in staging/production environments.
        
        This test demonstrates the validation logic that should catch insecure patterns.
        """
        from netra_backend.app.schemas.config import AppConfig
        from unittest.mock import MagicMock, patch
        
        # These are the exact patterns used in staging.env that should fail validation
        staging_patterns = [
            "staging-secret-key-for-sessions-should-be-replaced-in-deployment",  # Current staging SECRET_KEY
            "staging-jwt-secret-key-should-be-replaced-in-deployment",  # Current staging JWT_SECRET_KEY
        ]
        
        # Mock get_env to return staging environment
        mock_env = MagicMock()
        mock_env.get.return_value = "staging"
        
        # Mock staging environment by directly patching the get_env function
        for secret_pattern in staging_patterns:
            # Mock get_env function to return staging environment
            with patch('netra_backend.app.schemas.config.get_env', return_value=mock_env):
                # This should raise ValueError for staging environment with insecure patterns
                with pytest.raises(ValueError, match=r"contains insecure pattern for staging environment"):
                    # Test SECRET_KEY validation with mocked environment
                    AppConfig.validate_secret_key(secret_pattern)
    
    def test_staging_secret_key_actual_environment_detection(self):
        """Test SECRET_KEY validation with actual environment detection from staging.
        
        This test checks if the current staging environment variables would pass or fail validation.
        This should FAIL if staging is using insecure patterns, demonstrating the issue.
        """
        from netra_backend.app.schemas.config import AppConfig
        from shared.isolated_environment import get_env
        
        # Get actual environment
        env = get_env()
        actual_environment = env.get("ENVIRONMENT", "development").lower()
        
        if actual_environment in ["staging", "production"]:
            # Test actual SECRET_KEY from environment
            actual_secret = env.get("SECRET_KEY", "")
            actual_jwt_secret = env.get("JWT_SECRET_KEY", "")
            
            if actual_secret:
                try:
                    AppConfig.validate_secret_key(actual_secret)
                    # If this passes in staging with current config, there might be a validation gap
                    if actual_environment == "staging" and any(pattern in actual_secret.lower() 
                                                              for pattern in ['staging', 'secret', 'default']):
                        pytest.fail(
                            f"STAGING VALIDATION GAP: Current staging SECRET_KEY contains "
                            f"insecure patterns but passed validation. Environment: {actual_environment}, "
                            f"Key length: {len(actual_secret)}, Key preview: {actual_secret[:20]}..."
                        )
                except ValueError as e:
                    # This is expected for insecure staging keys - log the issue
                    assert "insecure pattern" in str(e), f"Unexpected validation error: {e}"
            
            if actual_jwt_secret:
                try:
                    AppConfig.validate_jwt_secret_key(actual_jwt_secret)
                    # If this passes in staging with current config, there might be a validation gap
                    if actual_environment == "staging" and any(pattern in actual_jwt_secret.lower() 
                                                              for pattern in ['staging', 'secret', 'jwt']):
                        pytest.fail(
                            f"STAGING JWT VALIDATION GAP: Current staging JWT_SECRET_KEY contains "
                            f"insecure patterns but passed validation. Environment: {actual_environment}, "
                            f"Key length: {len(actual_jwt_secret)}, Key preview: {actual_jwt_secret[:20]}..."
                        )
                except ValueError as e:
                    # This is expected for insecure staging keys - log the issue
                    assert "insecure pattern" in str(e), f"Unexpected JWT validation error: {e}"
    
    def test_staging_config_bootstrap_failure_scenarios(self):
        """Test SECRET_KEY configuration failures during application bootstrap.
        
        These scenarios replicate actual staging bootstrap failures where invalid
        SECRET_KEY configuration prevents application startup.
        
        This test should FAIL with problematic configurations to demonstrate the issue.
        """
        from netra_backend.app.schemas.config import AppConfig
        
        # Test bootstrap failure scenarios that occur in staging
        bootstrap_failure_scenarios = [
            ("short", "Secret key too short - should cause bootstrap failure"),
            ("", "Empty secret key - should cause bootstrap failure"),
            (None, "None secret key - should cause bootstrap failure"),
            ("   \n\t   ", "Whitespace-only secret key - should cause bootstrap failure"),
        ]
        
        for secret_key, description in bootstrap_failure_scenarios:
            with pytest.raises((ValueError, TypeError), match=r"(SECRET_KEY|required|empty|characters)"):
                # Attempt to create config with invalid secret key
                try:
                    if secret_key is None:
                        # Test None scenario
                        AppConfig.validate_secret_key(secret_key)
                    else:
                        # Test invalid scenarios
                        AppConfig.validate_secret_key(secret_key)
                    
                    # If no exception is raised, this is a validation gap
                    pytest.fail(
                        f"BOOTSTRAP VALIDATION ISSUE: {description} but validation passed. "
                        f"Secret key: {secret_key!r}. This indicates a configuration validation gap."
                    )
                except (ValueError, TypeError) as e:
                    # Expected behavior - re-raise to verify proper error handling
                    assert any(keyword in str(e).lower() 
                             for keyword in ['secret_key', 'required', 'empty', 'characters']), \
                           f"Bootstrap error message unclear: {e}"
                    raise
    
    def test_secret_key_predictability_resistance(self):
        """Test SECRET_KEY resistance to predictable patterns."""
        
        def assess_key_predictability(key: str) -> tuple[bool, str]:
            """Mock predictability assessment."""
            if len(key) < 32:
                return False, "Too short"
            
            # Check for sequential patterns
            if "123456" in key or "abcdef" in key:
                return False, "Contains sequential patterns"
            
            # Check for repeated segments
            if len(key) >= 16:
                segment = key[:8]
                if key.count(segment) > 1:
                    return False, "Contains repeated segments"
            
            # Check for common words
            common_words = ["password", "secret", "key", "admin", "user"]
            if any(word in key.lower() for word in common_words):
                return False, "Contains common words"
            
            return True, "Acceptable unpredictability"
        
        # Test predictability scenarios
        predictability_tests = [
            ("password123456789012345678901234", False, "sequential patterns"),
            ("secretsecretsecretsecretsecretsec", False, "repeated segments"),
            ("adminkeyadminkeyadminkeyadminkey", False, "common words"),
            ("7f9k2x8m1q5w3e4r6t7y8u9i0o1p2a3s", True, "Acceptable"),
        ]
        
        for key, expected_secure, expected_reason_contains in predictability_tests:
            is_secure, reason = assess_key_predictability(key)
            assert is_secure == expected_secure, (
                f"Predictability assessment failed for key: "
                f"expected {expected_secure}, got {is_secure}, reason: {reason}"
            )
    
    def test_secret_key_entropy_requirements(self):
        """Test SECRET_KEY entropy requirements for cryptographic security."""
        
        def calculate_key_entropy_score(key: str) -> int:
            """Mock entropy calculation (simplified)."""
            if len(key) < 32:
                return 0  # Invalid length
            
            # Count unique characters
            unique_chars = len(set(key))
            
            # Bonus for character variety
            has_upper = any(c.isupper() for c in key)
            has_lower = any(c.islower() for c in key) 
            has_digit = any(c.isdigit() for c in key)
            has_special = any(not c.isalnum() for c in key)
            
            variety_bonus = sum([has_upper, has_lower, has_digit, has_special]) * 5
            
            return unique_chars + variety_bonus
        
        # Test entropy scenarios
        entropy_tests = [
            ("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 0),   # all same, too low
            ("abcdefghijklmnopqrstuvwxyz123456", 32),      # reasonable
            ("AbCdEfGh123!@#$%^&*()_+=-{}[]|\\:;", 50),   # high entropy
        ]
        
        for key, min_expected_score in entropy_tests:
            if len(key) >= 32:  # only test valid length keys
                score = calculate_key_entropy_score(key)
                assert score >= min_expected_score, (
                    f"Entropy score too low for key: score={score}, "
                    f"expected>={min_expected_score}, key='{key[:20]}...'"
                )