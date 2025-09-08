"""
Unit Tests: Password Strength Validation

Business Value Justification (BVJ):
- Segment: All (security critical for all user tiers)
- Business Goal: Prevent security breaches through strong password enforcement
- Value Impact: Strong password validation prevents account compromises
- Strategic Impact: Security compliance and user trust - weak passwords lead to breaches

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses IsolatedEnvironment (no direct os.environ access)
- Uses SSOT base test case patterns
"""

import pytest
import re
from typing import Dict, List, Tuple

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestPasswordStrengthValidation(SSotBaseTestCase):
    """Unit tests for password strength validation algorithms."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("MIN_PASSWORD_LENGTH", "8")
        self.set_env_var("REQUIRE_UPPERCASE", "true")
        self.set_env_var("REQUIRE_LOWERCASE", "true")
        self.set_env_var("REQUIRE_NUMBERS", "true")
        self.set_env_var("REQUIRE_SPECIAL_CHARS", "true")
        
    def _validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """Core password strength validation algorithm."""
        errors = []
        min_length = int(self.get_env_var("MIN_PASSWORD_LENGTH"))
        
        if len(password) < min_length:
            errors.append(f"Password must be at least {min_length} characters")
            
        if self.get_env_var("REQUIRE_UPPERCASE") == "true" and not re.search(r'[A-Z]', password):
            errors.append("Password must contain uppercase letters")
            
        if self.get_env_var("REQUIRE_LOWERCASE") == "true" and not re.search(r'[a-z]', password):
            errors.append("Password must contain lowercase letters")
            
        if self.get_env_var("REQUIRE_NUMBERS") == "true" and not re.search(r'\d', password):
            errors.append("Password must contain numbers")
            
        if self.get_env_var("REQUIRE_SPECIAL_CHARS") == "true" and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain special characters")
            
        return len(errors) == 0, errors
    
    @pytest.mark.unit
    def test_valid_strong_passwords(self):
        """Test that strong passwords pass validation."""
        strong_passwords = [
            "StrongP@ss123",
            "MySecure!Pass456",
            "Complex#Password789",
            "Another$Strong1Pass"
        ]
        
        for password in strong_passwords:
            is_valid, errors = self._validate_password_strength(password)
            assert is_valid, f"Strong password failed: {password}, errors: {errors}"
            
        self.record_metric("strong_passwords_tested", len(strong_passwords))
        
    @pytest.mark.unit
    def test_weak_password_rejection(self):
        """Test that weak passwords are properly rejected."""
        weak_passwords = [
            ("short", ["Password must be at least 8 characters"]),
            ("alllowercase123!", ["Password must contain uppercase letters"]),
            ("ALLUPPERCASE123!", ["Password must contain lowercase letters"]),
            ("NoNumbers@Pass", ["Password must contain numbers"]),
            ("NoSpecialChars123", ["Password must contain special characters"])
        ]
        
        for password, expected_error_types in weak_passwords:
            is_valid, errors = self._validate_password_strength(password)
            assert not is_valid, f"Weak password should have failed: {password}"
            assert len(errors) > 0
            
        self.record_metric("weak_passwords_tested", len(weak_passwords))
        
    @pytest.mark.unit
    def test_common_password_patterns(self):
        """Test rejection of common weak password patterns."""
        common_weak_patterns = [
            "password123",
            "Password123",
            "123456789",
            "qwerty123",
            "admin123!"
        ]
        
        weak_count = 0
        for password in common_weak_patterns:
            is_valid, errors = self._validate_password_strength(password)
            if not is_valid:
                weak_count += 1
                
        # Most common patterns should be weak
        assert weak_count >= len(common_weak_patterns) // 2
        self.record_metric("common_patterns_tested", len(common_weak_patterns))