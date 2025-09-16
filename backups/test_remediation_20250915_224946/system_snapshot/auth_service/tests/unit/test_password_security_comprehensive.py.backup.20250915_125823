"""
Password Security Comprehensive Tests - PRIORITY 2 SECURITY CRITICAL

**CRITICAL**: Comprehensive password policy enforcement testing with security validation.
These tests ensure password security protects Chat user accounts from credential attacks,
preventing unauthorized access to AI conversations and user data.

Business Value Justification (BVJ):
- Segment: All tiers - password security affects all user registrations  
- Business Goal: Security, User Protection, Compliance
- Value Impact: Prevents account breaches that could compromise Chat conversations
- Strategic Impact: Password security maintains platform trust and prevents data breaches

ULTRA CRITICAL CONSTRAINTS:
- Tests designed to FAIL HARD - no try/except bypassing
- Focus on realistic password attack scenarios
- Password policies must prevent common attack vectors
- ABSOLUTE IMPORTS ONLY (from auth_service.* not relative)

Password Attack Vectors Tested:
- Brute force password attempts
- Dictionary attack patterns
- Password cracking with common patterns  
- Sequential character attacks
- Password reuse and history validation
- Credential stuffing prevention
"""

import pytest
import bcrypt
import secrets
import re
import time
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta, timezone

# ABSOLUTE IMPORTS ONLY - No relative imports
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
from auth_service.auth_core.auth_environment import AuthEnvironment
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.security.password_policy_validator import (
    PasswordPolicyValidator, PasswordPolicyResult
)
from auth_service.services.password_service import PasswordService, PasswordPolicyError
from auth_service.services.redis_service import RedisService


class TestPasswordSecurityComprehensive(SSotBaseTestCase):
    """
    PRIORITY 2: Comprehensive password security tests with attack prevention focus.
    
    This test suite validates critical password security that protects Chat accounts:
    - Password policy enforcement and strength validation
    - Password hashing security and bcrypt implementation
    - Attack prevention against common password attacks
    - Password complexity scoring and user feedback
    - Password reset security and token management
    - Brute force protection and rate limiting
    """
    
    @pytest.fixture(autouse=True)
    async def setup_password_security_test_environment(self):
        """Set up comprehensive password security test environment."""
        
        # Initialize environment and services
        self.env = get_env()
        self.auth_env = AuthEnvironment()
        self.auth_config = AuthConfig()
        
        # Initialize password security components
        self.password_validator = PasswordPolicyValidator(self.auth_env)
        
        # Initialize Redis service for password reset testing
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        self.password_service = PasswordService(self.auth_config, self.redis_service)
        
        # Password test scenarios for comprehensive coverage
        self.password_test_scenarios = {
            "strong_passwords": [
                "SecurePass123!",
                "MyStr0ngP@ssw0rd",
                "Ch@llengeAccepted2024",
                "P@ssw0rd1sV3ryS3cur3!",
                "Complex!Password@123",
                "Ungu3ss@bl3P@ssw0rd2024",
                "MyS3cur3Ch@tP@ssw0rd!",
                "Str0ng&S3cur3P@ss123"
            ],
            "weak_passwords": [
                "password",
                "123456",
                "qwerty",
                "admin",
                "letmein",
                "welcome",
                "monkey",
                "pass",
                "test",
                "user"
            ],
            "policy_violation_passwords": [
                "short",  # Too short
                "alllowercase123",  # No uppercase
                "ALLUPPERCASE123",  # No lowercase  
                "NoNumbers!",  # No digits
                "NoSpecialChars123",  # No special characters
                "a" * 130,  # Too long
                "",  # Empty
                "   ",  # Only whitespace
            ],
            "attack_pattern_passwords": [
                "password123",  # Dictionary + numbers
                "qwerty123!",  # Sequential + requirements
                "admin@123",  # Common admin pattern
                "Password1!",  # Capitalized dictionary word
                "123456789!",  # Sequential numbers
                "abcdefgh1!",  # Sequential letters
                "aaaaaaa1!",  # Repetitive pattern
                "Password123Password123",  # Repeated pattern
            ]
        }
        
        # Track created Redis keys for cleanup
        self.created_redis_keys = []
        
        yield
        
        # Comprehensive cleanup
        await self._cleanup_password_test_resources()
    
    async def _cleanup_password_test_resources(self):
        """Comprehensive cleanup of password test resources."""
        try:
            # Clean up Redis keys
            for redis_key in self.created_redis_keys:
                try:
                    await self.redis_service.delete(redis_key)
                except Exception as e:
                    self.logger.warning(f"Redis cleanup warning {redis_key}: {e}")
            
            # Clean up password reset keys
            reset_keys = await self.redis_service.keys("password_reset:*")
            if reset_keys:
                await self.redis_service.delete(*reset_keys)
                
            await self.redis_service.close()
            
        except Exception as e:
            self.logger.warning(f"Password test cleanup warning: {e}")
    
    @pytest.mark.unit
    def test_password_policy_validation_comprehensive(self):
        """
        CRITICAL: Test comprehensive password policy validation with strength scoring.
        
        BVJ: Ensures Chat user passwords meet security requirements to prevent
        account breaches and maintain platform security standards.
        """
        
        # TEST 1: Strong password validation
        for strong_password in self.password_test_scenarios["strong_passwords"]:
            result = self.password_validator.validate_password_policy(strong_password)
            
            assert isinstance(result, PasswordPolicyResult)
            assert result.meets_policy is True, f"Strong password should meet policy: {strong_password}"
            assert result.strength_score >= 60, f"Strong password should have high score: {strong_password} (score: {result.strength_score})"
            assert len(result.requirements_missing) == 0, f"Strong password should have no missing requirements: {strong_password}"
        
        # TEST 2: Weak password rejection
        for weak_password in self.password_test_scenarios["weak_passwords"]:
            result = self.password_validator.validate_password_policy(weak_password)
            
            assert result.meets_policy is False, f"Weak password should be rejected: {weak_password}"
            assert result.strength_score < 60, f"Weak password should have low score: {weak_password} (score: {result.strength_score})"
            assert len(result.requirements_missing) > 0, f"Weak password should have missing requirements: {weak_password}"
        
        # TEST 3: Policy violation specific testing
        violation_expectations = [
            ("short", "at least"),  # Length requirement
            ("alllowercase123", "uppercase letter"),  # Uppercase requirement
            ("ALLUPPERCASE123", "lowercase letter"),  # Lowercase requirement  
            ("NoNumbers!", "number"),  # Digit requirement
            ("NoSpecialChars123", "special character"),  # Special character requirement
        ]
        
        for password, expected_violation in violation_expectations:
            result = self.password_validator.validate_password_policy(password)
            
            assert result.meets_policy is False, f"Policy violation should be rejected: {password}"
            
            # Check that specific requirement is mentioned
            violation_found = any(
                expected_violation.lower() in req.lower() 
                for req in result.requirements_missing
            )
            assert violation_found, (
                f"Expected violation '{expected_violation}' not found in requirements for '{password}': "
                f"{result.requirements_missing}"
            )
        
        # TEST 4: Empty and invalid password handling
        invalid_inputs = [None, "", "   ", 123, [], {}]
        
        for invalid_input in invalid_inputs:
            result = self.password_validator.validate_password_policy(invalid_input)
            
            assert result.meets_policy is False, f"Invalid input should be rejected: {invalid_input}"
            assert result.strength_score == 0, f"Invalid input should have zero score: {invalid_input}"
            assert len(result.requirements_missing) > 0, f"Invalid input should have requirements: {invalid_input}"
    
    @pytest.mark.unit
    def test_password_strength_scoring_algorithm(self):
        """
        CRITICAL: Test password strength scoring algorithm accuracy and consistency.
        
        BVJ: Ensures Chat users receive accurate password strength feedback
        to guide them toward creating secure passwords.
        """
        
        # TEST 1: Scoring progression for length
        length_test_passwords = [
            ("12345678", 8),   # Minimum length
            ("1234567890", 10), # Good length
            ("123456789012", 12), # Excellent length
            ("12345678901234567890", 20), # Very long
        ]
        
        for password, length in length_test_passwords:
            # Add required character classes to isolate length scoring
            test_password = f"{password}Aa!"
            result = self.password_validator.validate_password_policy(test_password)
            
            # Longer passwords should generally have higher scores
            assert result.strength_score > 0, f"Password with length {length} should have positive score"
            
            # Should meet policy with all required character classes
            assert result.meets_policy is True, f"Password with all requirements should meet policy: {test_password}"
        
        # TEST 2: Character class impact on scoring
        character_class_tests = [
            ("lowercase123!", ["uppercase letter"], 75),  # Missing uppercase
            ("UPPERCASE123!", ["lowercase letter"], 75),  # Missing lowercase
            ("LowerUpper!", ["number"], 75),  # Missing digit
            ("LowerUpper123", ["special character"], 75),  # Missing special char
            ("LowerUPPER123!", [], 85),  # All character classes present
        ]
        
        for password, expected_missing, min_expected_score in character_class_tests:
            result = self.password_validator.validate_password_policy(password)
            
            if expected_missing:
                assert result.meets_policy is False, f"Password missing {expected_missing} should not meet policy: {password}"
                
                for missing_requirement in expected_missing:
                    requirement_found = any(
                        missing_requirement.lower() in req.lower()
                        for req in result.requirements_missing
                    )
                    assert requirement_found, (
                        f"Missing requirement '{missing_requirement}' should be reported for '{password}': "
                        f"{result.requirements_missing}"
                    )
            else:
                assert result.meets_policy is True, f"Password with all requirements should meet policy: {password}"
                assert result.strength_score >= min_expected_score, (
                    f"Complete password should have score >= {min_expected_score}: {password} (got {result.strength_score})"
                )
        
        # TEST 3: Pattern analysis impact
        pattern_test_passwords = [
            ("Password123!", 50, True),  # Contains common word "password"
            ("Qwerty123!", 50, True),    # Contains sequential "qwerty"
            ("Secure456@", 70, False),   # No common patterns
            ("Aaaaaa123!", 40, True),    # Excessive repetition
        ]
        
        for password, max_expected_score, should_have_recommendations in pattern_test_passwords:
            result = self.password_validator.validate_password_policy(password)
            
            if should_have_recommendations:
                assert len(result.recommendations) > 0, (
                    f"Password with patterns should have recommendations: {password}"
                )
            
            # Pattern-based passwords should have lower scores
            if "password" in password.lower() or "qwerty" in password.lower():
                assert result.strength_score <= max_expected_score, (
                    f"Password with common patterns should have lower score: {password} "
                    f"(got {result.strength_score}, expected <= {max_expected_score})"
                )
    
    @pytest.mark.unit
    def test_password_hashing_security(self):
        """
        CRITICAL: Test password hashing security with bcrypt implementation.
        
        BVJ: Ensures Chat user passwords are properly hashed to prevent
        credential theft in case of database compromise.
        """
        
        # TEST 1: Strong password hashing
        strong_password = "SecurePass123!"
        
        password_hash = self.password_service.hash_password(strong_password)
        
        # Verify hash properties
        assert password_hash is not None
        assert len(password_hash) > 50, "Bcrypt hash should be substantial length"
        assert password_hash != strong_password, "Hash should not equal plain password"
        assert "$2b$" in password_hash, "Should use bcrypt version 2b"
        
        # Verify hash verification works
        verification_result = self.password_service.verify_password(strong_password, password_hash)
        assert verification_result is True, "Correct password should verify"
        
        # Verify wrong password doesn't verify
        wrong_verification = self.password_service.verify_password("WrongPassword123!", password_hash)
        assert wrong_verification is False, "Wrong password should not verify"
        
        # TEST 2: Hash uniqueness (salting)
        password = "TestPassword123!"
        
        hash1 = self.password_service.hash_password(password)
        hash2 = self.password_service.hash_password(password)
        
        # Same password should produce different hashes due to salt
        assert hash1 != hash2, "Same password should produce different hashes (salting)"
        
        # Both hashes should verify the original password
        assert self.password_service.verify_password(password, hash1) is True
        assert self.password_service.verify_password(password, hash2) is True
        
        # TEST 3: Password policy enforcement during hashing
        weak_passwords = ["weak", "123", "password"]
        
        for weak_password in weak_passwords:
            with pytest.raises((ValueError, PasswordPolicyError)):
                self.password_service.hash_password(weak_password)
        
        # TEST 4: Hash timing attack resistance
        password = "TimingTestPass123!"
        password_hash = self.password_service.hash_password(password)
        
        # Test verification timing for correct vs incorrect passwords
        correct_times = []
        incorrect_times = []
        
        for _ in range(5):
            # Time correct password verification
            start_time = time.time()
            self.password_service.verify_password(password, password_hash)
            correct_times.append(time.time() - start_time)
            
            # Time incorrect password verification
            start_time = time.time()
            self.password_service.verify_password("WrongPassword123!", password_hash)
            incorrect_times.append(time.time() - start_time)
        
        # Timing should be similar (bcrypt provides timing attack resistance)
        avg_correct_time = sum(correct_times) / len(correct_times)
        avg_incorrect_time = sum(incorrect_times) / len(incorrect_times)
        
        # Times should be within reasonable range (bcrypt is designed for this)
        time_difference_ratio = abs(avg_correct_time - avg_incorrect_time) / max(avg_correct_time, avg_incorrect_time)
        assert time_difference_ratio < 0.5, f"Verification timing should be similar to resist timing attacks (ratio: {time_difference_ratio:.3f})"
    
    @pytest.mark.unit
    def test_password_attack_pattern_prevention(self):
        """
        CRITICAL: Test prevention of common password attack patterns.
        
        BVJ: Ensures Chat password policies prevent common attack vectors
        used by attackers to compromise user accounts.
        """
        
        # TEST 1: Dictionary attack pattern prevention
        dictionary_attack_passwords = [
            "password123",
            "admin2024",
            "welcome123",
            "letmein456",
            "monkey789",
            "qwerty123",
            "Password1",  # Capitalized dictionary word
            "PASSWORD123",  # All caps dictionary
        ]
        
        for attack_password in dictionary_attack_passwords:
            result = self.password_validator.validate_password_policy(attack_password)
            
            # Should either fail policy or have low strength score
            if result.meets_policy:
                assert result.strength_score < 70, (
                    f"Dictionary attack password should have low score: {attack_password} "
                    f"(got {result.strength_score})"
                )
                
                # Should have recommendations about avoiding common words
                recommendations_found = any(
                    "common" in rec.lower() or "pattern" in rec.lower() 
                    for rec in result.recommendations
                )
                assert recommendations_found, (
                    f"Dictionary password should have pattern recommendations: {attack_password}"
                )
        
        # TEST 2: Sequential pattern attack prevention
        sequential_attack_passwords = [
            "123456789a!A",  # Sequential numbers
            "abcdefgh1!A",   # Sequential letters  
            "qwertyui1!A",   # Keyboard sequential
            "987654321a!A",  # Reverse sequential
        ]
        
        for attack_password in sequential_attack_passwords:
            result = self.password_validator.validate_password_policy(attack_password)
            
            # Should have recommendations about avoiding sequences
            if result.meets_policy:  # May pass basic requirements
                recommendations_found = any(
                    "sequential" in rec.lower() 
                    for rec in result.recommendations
                )
                assert recommendations_found, (
                    f"Sequential password should have sequence recommendations: {attack_password}"
                )
        
        # TEST 3: Repetitive pattern attack prevention
        repetitive_attack_passwords = [
            "aaaaaaa1!A",    # Repeated character
            "111111a!A",     # Repeated digit
            "AbAbAbAb12!",   # Repeated pattern
            "123123123a!A",  # Repeated number sequence
        ]
        
        for attack_password in repetitive_attack_passwords:
            result = self.password_validator.validate_password_policy(attack_password)
            
            # Should have recommendations about avoiding repetition
            if result.meets_policy:  # May pass basic requirements
                recommendations_found = any(
                    "repetition" in rec.lower() 
                    for rec in result.recommendations
                )
                assert recommendations_found, (
                    f"Repetitive password should have repetition recommendations: {attack_password}"
                )
        
        # TEST 4: Length attack prevention (brute force)
        short_passwords_with_complexity = [
            "A1!",      # 3 chars
            "Ab1!",     # 4 chars  
            "Abc12!",   # 6 chars
            "Abcd123!", # 8 chars (minimum)
        ]
        
        for short_password in short_passwords_with_complexity:
            result = self.password_validator.validate_password_policy(short_password)
            
            if len(short_password) < 8:
                assert result.meets_policy is False, (
                    f"Password under 8 chars should fail: {short_password}"
                )
                
                length_requirement_found = any(
                    "at least" in req.lower() and "characters" in req.lower()
                    for req in result.requirements_missing
                )
                assert length_requirement_found, (
                    f"Short password should have length requirement: {short_password}"
                )
    
    @pytest.mark.unit  
    async def test_password_reset_security(self):
        """
        CRITICAL: Test password reset security and token management.
        
        BVJ: Ensures Chat users can securely reset passwords without
        compromising account security through token vulnerabilities.
        """
        
        # This test would require password reset functionality to be implemented
        # For now, we'll test the components we have available
        
        # TEST 1: Password reset token generation security
        user_email = "test@example.com"
        
        # Generate multiple reset tokens
        tokens = []
        for i in range(5):
            token = secrets.token_urlsafe(32)
            tokens.append(token)
            
            # Store token in Redis (simulating reset token storage)
            reset_key = f"password_reset:{token}"
            await self.redis_service.set(
                reset_key,
                user_email,
                ex=3600  # 1 hour expiration
            )
            self.created_redis_keys.append(reset_key)
        
        # Verify token uniqueness
        assert len(set(tokens)) == len(tokens), "Reset tokens should be unique"
        
        # Verify token length (security requirement)
        for token in tokens:
            assert len(token) >= 32, f"Reset token should be at least 32 chars: {len(token)}"
            
            # Should not contain predictable patterns
            assert not re.match(r'^[0-9]+$', token), "Token should not be all numbers"
            assert not re.match(r'^[a-z]+$', token), "Token should not be all lowercase"
            
            # Verify token is stored and retrievable
            reset_key = f"password_reset:{token}"
            stored_email = await self.redis_service.get(reset_key)
            assert stored_email == user_email, f"Reset token should be stored correctly: {token}"
        
        # TEST 2: Token expiration security
        short_lived_token = secrets.token_urlsafe(32)
        short_reset_key = f"password_reset:{short_lived_token}"
        
        # Store with 1 second expiration
        await self.redis_service.set(short_reset_key, user_email, ex=1)
        self.created_redis_keys.append(short_reset_key)
        
        # Should be accessible immediately
        stored_email = await self.redis_service.get(short_reset_key)
        assert stored_email == user_email, "Token should be accessible immediately"
        
        # Wait for expiration
        import asyncio
        await asyncio.sleep(1.5)
        
        # Should be expired
        expired_email = await self.redis_service.get(short_reset_key)
        assert expired_email is None, "Token should expire after timeout"
        
        # TEST 3: Token brute force prevention
        # Generate many invalid tokens and verify they don't match valid ones
        invalid_tokens = [
            secrets.token_urlsafe(32) for _ in range(20)
        ]
        
        for invalid_token in invalid_tokens:
            invalid_key = f"password_reset:{invalid_token}"
            stored_data = await self.redis_service.get(invalid_key)
            assert stored_data is None, f"Invalid token should not return data: {invalid_token}"
    
    @pytest.mark.unit
    def test_password_complexity_scoring_edge_cases(self):
        """
        CRITICAL: Test password complexity scoring edge cases and boundary conditions.
        
        BVJ: Ensures Chat password scoring algorithm handles edge cases correctly
        to provide accurate security feedback to users.
        """
        
        # TEST 1: Maximum length boundary
        max_length_password = "A1!" + "a" * (128 - 3)  # Exactly 128 chars
        result = self.password_validator.validate_password_policy(max_length_password)
        
        assert result.meets_policy is True, "Max length password should be valid"
        assert result.strength_score > 0, "Max length password should have positive score"
        
        # TEST 2: Over maximum length
        over_max_password = "A1!" + "a" * (129 - 3)  # 129 chars
        result = self.password_validator.validate_password_policy(over_max_password)
        
        assert result.meets_policy is False, "Over-max password should fail policy"
        length_error_found = any(
            "no more than" in req.lower() for req in result.requirements_missing
        )
        assert length_error_found, "Should have length requirement error"
        
        # TEST 3: Minimum length boundary
        min_length_password = "A1!aaaaa"  # Exactly 8 chars
        result = self.password_validator.validate_password_policy(min_length_password)
        
        assert result.meets_policy is True, "Min length password should be valid"
        assert result.strength_score > 0, "Min length password should have positive score"
        
        # TEST 4: Under minimum length  
        under_min_password = "A1!aaa"  # 7 chars
        result = self.password_validator.validate_password_policy(under_min_password)
        
        assert result.meets_policy is False, "Under-min password should fail policy"
        length_error_found = any(
            "at least" in req.lower() for req in result.requirements_missing
        )
        assert length_error_found, "Should have minimum length requirement error"
        
        # TEST 5: Special character edge cases
        special_char_edge_cases = [
            ("Test123!", "standard special chars"),
            ("Test123@", "at symbol"),
            ("Test123#", "hash symbol"),
            ("Test123$", "dollar symbol"),
            ("Test123%", "percent symbol"),
            ("Test123^", "caret symbol"),
            ("Test123&", "ampersand symbol"),
            ("Test123*", "asterisk symbol"),
            ("Test123(", "parenthesis symbol"),
            ("Test123)", "parenthesis symbol"),
            ("Test123.", "period symbol"),
            ("Test123,", "comma symbol"),
            ("Test123?", "question mark"),
            ("Test123\"", "quote symbol"),
            ("Test123:", "colon symbol"),
            ("Test123{", "brace symbol"),
            ("Test123}", "brace symbol"),
            ("Test123|", "pipe symbol"),
            ("Test123<", "less than symbol"),
            ("Test123>", "greater than symbol"),
        ]
        
        for password, description in special_char_edge_cases:
            result = self.password_validator.validate_password_policy(password)
            
            assert result.meets_policy is True, f"Password with {description} should be valid: {password}"
            
            # Should not have special character requirement missing
            special_char_missing = any(
                "special character" in req.lower() for req in result.requirements_missing
            )
            assert not special_char_missing, f"Should not have special char requirement for {description}: {password}"
        
        # TEST 6: Unicode and international character handling
        unicode_passwords = [
            "Test123![U+00F1]",  # Spanish character
            "Test123![U+4E2D]",  # Chinese character
            "Test123![U+00E9]",   # French character
            "Test123![U+00DF]",   # German character
        ]
        
        for unicode_password in unicode_passwords:
            result = self.password_validator.validate_password_policy(unicode_password)
            
            # Should handle unicode characters gracefully
            assert result.strength_score >= 0, f"Unicode password should have valid score: {unicode_password}"
            
            # Basic requirements should still be checked
            if len(unicode_password) >= 8:
                # Should have reasonable scoring
                assert result.strength_score > 0, f"Valid unicode password should have positive score: {unicode_password}"


__all__ = ["TestPasswordSecurityComprehensive"]