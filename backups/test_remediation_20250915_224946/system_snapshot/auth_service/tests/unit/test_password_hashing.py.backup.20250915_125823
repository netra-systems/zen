"""
Unit Tests for Password Hashing Security

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Protect user credentials with industry-standard security
- Value Impact: Prevents credential theft and maintains user trust
- Strategic Impact: Critical security foundation - password breaches = reputation damage

This module tests password hashing security including:
- Secure password hashing with bcrypt
- Password verification against hashes
- Hash strength and salt randomness
- Performance optimization for auth flows
- Security compliance with industry standards
- Protection against timing attacks
"""

import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
import bcrypt

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from auth_service.services.password_service import PasswordService, PasswordPolicyError
from auth_service.auth_core.config import AuthConfig


class TestPasswordHashing(SSotBaseTestCase):
    """Unit tests for password hashing security business logic."""
    
    def setup_method(self, method=None):
        """Setup test environment and mocks."""
        super().setup_method(method)
        
        # Mock auth configuration
        self.mock_auth_config = MagicMock(spec=AuthConfig)
        self.mock_auth_config.password_min_length = 8
        self.mock_auth_config.password_require_uppercase = True
        self.mock_auth_config.password_require_lowercase = True
        self.mock_auth_config.password_require_numbers = True
        self.mock_auth_config.password_require_symbols = True
        
        # Mock Redis service
        self.mock_redis_service = MagicMock()
        
        # Create password service instance
        self.password_service = PasswordService(
            auth_config=self.mock_auth_config,
            redis_service=self.mock_redis_service
        )
        
        # Test passwords
        self.valid_password = "SecureP@ss123"
        self.weak_password = "weak"
        self.simple_password = "password"
        
    @pytest.mark.unit
    def test_password_hashing_with_bcrypt(self):
        """Test password hashing uses bcrypt for security."""
        # Business logic: Passwords should be hashed with bcrypt
        password_hash = self.password_service.hash_password(self.valid_password)
        
        # Verify hash format (bcrypt hashes start with $2b$)
        assert password_hash.startswith('$2b$')
        
        # Verify hash is different from original password
        assert password_hash != self.valid_password
        
        # Verify hash length is appropriate for bcrypt
        assert len(password_hash) >= 60  # bcrypt hashes are typically 60 characters
        
        # Record business metric: Secure hashing success
        self.record_metric("password_hashing_success", True)
        
    @pytest.mark.unit
    def test_password_verification_with_valid_hash(self):
        """Test password verification against valid hash."""
        # Create hash for password
        password_hash = self.password_service.hash_password(self.valid_password)
        
        # Business logic: Correct password should verify against its hash
        is_valid = self.password_service.verify_password(self.valid_password, password_hash)
        
        assert is_valid == True
        
        # Record business metric: Password verification success
        self.record_metric("password_verification_success", True)
        
    @pytest.mark.unit
    def test_password_verification_with_wrong_password(self):
        """Test password verification rejects wrong password."""
        # Create hash for one password
        password_hash = self.password_service.hash_password(self.valid_password)
        
        # Business logic: Wrong password should not verify
        is_valid = self.password_service.verify_password("WrongPassword123!", password_hash)
        
        assert is_valid == False
        
        # Record business metric: Wrong password rejection
        self.record_metric("wrong_password_rejected", True)
        
    @pytest.mark.unit
    def test_hash_uniqueness_with_same_password(self):
        """Test that same password produces different hashes (salt randomness)."""
        # Business requirement: Same password should produce different hashes
        hash1 = self.password_service.hash_password(self.valid_password)
        hash2 = self.password_service.hash_password(self.valid_password)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2
        
        # Both hashes should verify the same password
        assert self.password_service.verify_password(self.valid_password, hash1) == True
        assert self.password_service.verify_password(self.valid_password, hash2) == True
        
        # Record business metric: Hash uniqueness validation
        self.record_metric("hash_uniqueness_validated", True)
        
    @pytest.mark.unit
    def test_hash_strength_with_work_factor(self):
        """Test that password hashes use appropriate work factor for security."""
        # Create hash
        password_hash = self.password_service.hash_password(self.valid_password)
        
        # Extract work factor from bcrypt hash
        # bcrypt hash format: $2b$rounds$salt+hash
        hash_parts = password_hash.split('$')
        assert len(hash_parts) >= 4
        
        work_factor = int(hash_parts[2])
        
        # Business requirement: Work factor should be secure (>= 12)
        assert work_factor >= 12, f"Work factor too low: {work_factor}"
        assert work_factor <= 15, f"Work factor too high for performance: {work_factor}"
        
        # Record business metric: Hash strength validation
        self.record_metric("hash_work_factor", work_factor)
        self.record_metric("hash_strength_validated", True)
        
    @pytest.mark.unit
    def test_password_policy_validation(self):
        """Test password policy enforcement for security."""
        # Test cases for password policy validation
        policy_test_cases = [
            # (password, should_be_valid, reason)
            (self.valid_password, True, "meets_all_requirements"),
            ("short", False, "too_short"),
            ("nouppercase123!", False, "no_uppercase"),
            ("NOLOWERCASE123!", False, "no_lowercase"),
            ("NoNumbers!", False, "no_numbers"),
            ("NoSymbols123", False, "no_symbols"),
            ("", False, "empty_password"),
        ]
        
        for password, should_be_valid, reason in policy_test_cases:
            # Business logic: Password policy should be enforced
            try:
                result = self.password_service.validate_password_policy(password)
                
                if should_be_valid:
                    assert result == True, f"Password should be valid: {reason}"
                else:
                    # Should have raised exception or returned False
                    assert False, f"Password should be invalid: {reason}"
                    
            except PasswordPolicyError:
                if should_be_valid:
                    assert False, f"Password should be valid: {reason}"
                # Exception expected for invalid passwords
                
        # Record business metric: Policy validation
        self.record_metric("password_policy_cases_tested", len(policy_test_cases))
        
    @pytest.mark.unit
    def test_hashing_performance_requirements(self):
        """Test password hashing performance for user experience."""
        import time
        
        # Business requirement: Hashing should be secure but not too slow
        start_time = time.time()
        
        # Hash multiple passwords
        passwords = [f"TestPass{i}@123" for i in range(10)]
        hashes = []
        
        for password in passwords:
            password_hash = self.password_service.hash_password(password)
            hashes.append(password_hash)
            
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_hash = total_time / len(passwords)
        
        # Business requirement: Should hash password in reasonable time
        # bcrypt with work factor 12-14 should take ~100-500ms per hash
        assert avg_time_per_hash < 1.0, f"Hashing too slow: {avg_time_per_hash}s per password"
        assert avg_time_per_hash > 0.05, f"Hashing too fast (insecure): {avg_time_per_hash}s per password"
        
        # Verify all hashes are unique
        unique_hashes = set(hashes)
        assert len(unique_hashes) == len(passwords), "All hashes should be unique"
        
        # Record performance metrics
        self.record_metric("hash_time_ms_per_password", avg_time_per_hash * 1000)
        self.record_metric("passwords_per_second", 1 / avg_time_per_hash)
        
    @pytest.mark.unit
    def test_verification_performance_requirements(self):
        """Test password verification performance for user experience."""
        import time
        
        # Pre-hash passwords for verification testing
        test_passwords = [f"TestPass{i}@123" for i in range(20)]
        password_hashes = [
            self.password_service.hash_password(password) 
            for password in test_passwords
        ]
        
        # Business requirement: Verification should be fast
        start_time = time.time()
        
        verification_results = []
        for password, password_hash in zip(test_passwords, password_hashes):
            is_valid = self.password_service.verify_password(password, password_hash)
            verification_results.append(is_valid)
            
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_verification = total_time / len(test_passwords)
        
        # Business requirement: Verification should be faster than hashing
        assert avg_time_per_verification < 1.0, f"Verification too slow: {avg_time_per_verification}s"
        
        # All verifications should succeed
        assert all(verification_results), "All password verifications should succeed"
        
        # Record performance metrics
        self.record_metric("verification_time_ms_per_password", avg_time_per_verification * 1000)
        self.record_metric("verifications_per_second", 1 / avg_time_per_verification)
        
    @pytest.mark.unit
    def test_timing_attack_resistance(self):
        """Test password verification resistance to timing attacks."""
        import time
        
        # Create hash for comparison
        password_hash = self.password_service.hash_password(self.valid_password)
        
        # Test verification times for correct vs incorrect passwords
        correct_times = []
        incorrect_times = []
        
        # Measure correct password verification times
        for _ in range(10):
            start_time = time.time()
            self.password_service.verify_password(self.valid_password, password_hash)
            end_time = time.time()
            correct_times.append(end_time - start_time)
            
        # Measure incorrect password verification times
        for i in range(10):
            start_time = time.time()
            self.password_service.verify_password(f"wrong_password_{i}", password_hash)
            end_time = time.time()
            incorrect_times.append(end_time - start_time)
            
        # Business requirement: Timing should be similar (resistant to timing attacks)
        avg_correct_time = sum(correct_times) / len(correct_times)
        avg_incorrect_time = sum(incorrect_times) / len(incorrect_times)
        
        # Timing difference should be minimal (bcrypt provides this naturally)
        time_difference_ratio = abs(avg_correct_time - avg_incorrect_time) / avg_correct_time
        assert time_difference_ratio < 0.3, f"Timing attack vulnerability: {time_difference_ratio * 100}% difference"
        
        # Record security metric: Timing attack resistance
        self.record_metric("timing_attack_resistance_validated", True)
        self.record_metric("timing_difference_percentage", time_difference_ratio * 100)
        
    @pytest.mark.unit
    def test_password_service_initialization(self):
        """Test password service initialization with proper dependencies."""
        # Verify service was initialized correctly
        assert self.password_service.auth_config == self.mock_auth_config
        assert hasattr(self.password_service, 'redis_service')
        
        # Verify Redis service is properly configured
        assert self.password_service.redis_service is not None
        
        # Verify reset token prefix is set
        assert hasattr(self.password_service, 'reset_token_prefix')
        assert self.password_service.reset_token_prefix == "password_reset:"
        
        # Record business metric: Service initialization success
        self.record_metric("password_service_initialization_success", True)
        
    @pytest.mark.unit
    def test_security_compliance_standards(self):
        """Test password hashing meets security compliance standards."""
        # Test multiple passwords to ensure consistent behavior
        test_passwords = [
            "BusinessPassword1!",
            "EnterpriseAccess@2023",
            "SecureLogin#456"
        ]
        
        for password in test_passwords:
            # Create hash
            password_hash = self.password_service.hash_password(password)
            
            # Verify bcrypt format compliance
            assert password_hash.startswith('$2b$'), "Hash should use bcrypt format"
            
            # Verify hash contains salt (bcrypt includes salt in hash)
            hash_parts = password_hash.split('$')
            assert len(hash_parts) >= 4, "Hash should contain algorithm, cost, salt, and hash"
            
            # Verify verification works
            assert self.password_service.verify_password(password, password_hash) == True
            
            # Verify wrong password fails
            assert self.password_service.verify_password("WrongPassword", password_hash) == False
            
        # Record business metric: Security compliance validation
        self.record_metric("security_compliance_validated", True)
        self.record_metric("compliance_test_passwords", len(test_passwords))
        
    def teardown_method(self, method=None):
        """Clean up test environment."""
        # Log business metrics for security monitoring
        final_metrics = self.get_all_metrics()
        
        # Set password security validation flags
        if final_metrics.get("password_hashing_success"):
            self.set_env_var("LAST_PASSWORD_HASHING_TEST_SUCCESS", "true")
            
        if final_metrics.get("security_compliance_validated"):
            self.set_env_var("PASSWORD_SECURITY_COMPLIANCE_VALIDATED", "true")
            
        if final_metrics.get("timing_attack_resistance_validated"):
            self.set_env_var("TIMING_ATTACK_RESISTANCE_VALIDATED", "true")
            
        # Performance validation
        hash_time = final_metrics.get("hash_time_ms_per_password", 999)
        if hash_time < 500:  # Under 500ms per password hash
            self.set_env_var("PASSWORD_HASHING_PERFORMANCE_ACCEPTABLE", "true")
            
        super().teardown_method(method)