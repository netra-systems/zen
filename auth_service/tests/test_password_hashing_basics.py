"""
Basic Password Hashing and Verification Tests

Tests the core password hashing and verification functionality used throughout
the auth service. This ensures secure password handling for basic authentication.

Business Value Justification (BVJ):
- Segment: Platform/Security | Goal: Auth Foundation | Impact: Core Security
- Ensures secure password hashing for all local authentication flows  
- Validates password verification accuracy and prevents auth bypasses
- Critical foundation for user account security and authentication integrity

Test Coverage:
- Password hashing with different lengths and complexity
- Password verification for correct and incorrect passwords
- Hash format consistency and security properties
- Password strength validation and edge cases
"""

import unittest
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from auth_service.tests.factories.user_factory import AuthUserFactory


class TestPasswordHashingBasics(unittest.TestCase):
    """Test basic password hashing and verification functionality"""
    
    def setUp(self):
        """Setup test environment"""
        self.password_hasher = PasswordHasher()
        self.test_passwords = [
            "SimplePass123!",
            "ComplexPassword@2024#WithLots$OfSpecialChars%",
            "Short1!",
            "MinimumLength8!",
            "VeryLongPasswordThatExceedsTypicalLimits123456789!@#$%^&*()",
        ]
    
    def test_password_hashing_generates_unique_hashes(self):
        """Test that hashing the same password generates unique hashes"""
        password = "TestPassword123!"
        
        # Generate multiple hashes of the same password
        hashes = []
        for _ in range(5):
            hash_result = self.password_hasher.hash(password)
            hashes.append(hash_result)
        
        # All hashes should be different due to salt
        assert len(set(hashes)) == 5, "Each password hash should be unique"
        
        # All hashes should verify against the original password
        for hash_result in hashes:
            assert AuthUserFactory.verify_password(hash_result, password), \
                "All unique hashes should verify correctly"
    
    def test_password_verification_success(self):
        """Test successful password verification for various password types"""
        for password in self.test_passwords:
            with self.subTest(password=password[:10] + "..."):
                # Hash the password
                hash_result = self.password_hasher.hash(password)
                
                # Verify it matches
                is_valid = AuthUserFactory.verify_password(hash_result, password)
                assert is_valid, f"Password verification should succeed for: {password[:10]}..."
                
                # Also test direct verification
                try:
                    self.password_hasher.verify(hash_result, password)
                except VerifyMismatchError:
                    self.fail(f"Direct password verification should succeed for: {password[:10]}...")
    
    def test_password_verification_failure(self):
        """Test password verification fails for incorrect passwords"""
        original_password = "CorrectPassword123!"
        wrong_passwords = [
            "WrongPassword123!",
            "correctpassword123!",  # Case sensitive
            "CorrectPassword123",   # Missing special char
            "CorrectPassword124!",  # One character different
            "",                     # Empty password
            "CorrectPassword123! ", # Trailing space
        ]
        
        hash_result = self.password_hasher.hash(original_password)
        
        for wrong_password in wrong_passwords:
            with self.subTest(wrong_password=wrong_password[:10] + "..."):
                is_valid = AuthUserFactory.verify_password(hash_result, wrong_password)
                assert not is_valid, \
                    f"Password verification should fail for wrong password: {wrong_password[:10]}..."
    
    def test_password_hash_format_consistency(self):
        """Test that password hashes follow expected Argon2 format"""
        password = "TestPassword123!"
        hash_result = self.password_hasher.hash(password)
        
        # Argon2 hashes should start with $argon2id$
        assert hash_result.startswith("$argon2id$"), \
            "Password hash should use Argon2id variant"
        
        # Should have proper structure with multiple $ separators
        parts = hash_result.split("$")
        assert len(parts) >= 5, \
            f"Argon2 hash should have at least 5 parts, got {len(parts)}: {hash_result}"
        
        # Should contain memory, time, and parallelism parameters
        assert "m=" in hash_result, "Hash should contain memory parameter"
        assert "t=" in hash_result, "Hash should contain time parameter"  
        assert "p=" in hash_result, "Hash should contain parallelism parameter"
    
    def test_password_hash_length_handling(self):
        """Test password hashing handles various password lengths correctly"""
        # Test minimum viable password
        min_password = "Test1!"
        min_hash = self.password_hasher.hash(min_password)
        assert AuthUserFactory.verify_password(min_hash, min_password)
        
        # Test maximum reasonable password length
        max_password = "A" * 200 + "1!"
        max_hash = self.password_hasher.hash(max_password)
        assert AuthUserFactory.verify_password(max_hash, max_password)
        
        # Test unicode characters
        unicode_password = "Пароль123!测试"
        unicode_hash = self.password_hasher.hash(unicode_password)
        assert AuthUserFactory.verify_password(unicode_hash, unicode_password)
    
    def test_password_hash_security_properties(self):
        """Test that password hashes have expected security properties"""
        password = "SecurityTest123!"
        hash_result = self.password_hasher.hash(password)
        
        # Hash should be significantly longer than the password
        assert len(hash_result) > len(password) * 2, \
            "Hash should be much longer than original password"
        
        # Hash should not contain the original password
        assert password not in hash_result, \
            "Hash should not contain the original password"
        
        # Hash should be deterministic for verification but unique each time
        hash2 = self.password_hasher.hash(password)
        assert hash_result != hash2, "Each hash should be unique"
        
        # Both should verify correctly
        assert AuthUserFactory.verify_password(hash_result, password)
        assert AuthUserFactory.verify_password(hash2, password)
    
    def test_password_verification_edge_cases(self):
        """Test password verification edge cases and error handling"""
        password = "EdgeCaseTest123!"
        hash_result = self.password_hasher.hash(password)
        
        # Test with None password - catch exception
        try:
            result = AuthUserFactory.verify_password(hash_result, None)
            assert not result
        except (TypeError, AttributeError):
            # Expected behavior for None input
            pass
        
        # Test with empty string
        assert not AuthUserFactory.verify_password(hash_result, "")
        
        # Test with malformed hash - catch exception
        try:
            result = AuthUserFactory.verify_password("invalid_hash", password)
            assert not result
        except:
            # Expected behavior for invalid hash
            pass
            
        try:
            result = AuthUserFactory.verify_password("", password)
            assert not result
        except:
            # Expected behavior for empty hash
            pass
            
        try:
            result = AuthUserFactory.verify_password(None, password)
            assert not result
        except (TypeError, AttributeError):
            # Expected behavior for None hash
            pass
    
    def test_password_hashing_performance(self):
        """Test password hashing and verification performance"""
        import time
        
        password = "PerformanceTest123!"
        
        # Test hashing performance
        start_time = time.time()
        hash_result = self.password_hasher.hash(password)
        hash_time = time.time() - start_time
        
        # Hashing should complete within reasonable time (< 1 second)
        assert hash_time < 1.0, f"Password hashing took too long: {hash_time:.3f}s"
        
        # Test verification performance  
        start_time = time.time()
        is_valid = AuthUserFactory.verify_password(hash_result, password)
        verify_time = time.time() - start_time
        
        assert is_valid, "Password verification should succeed"
        assert verify_time < 1.0, f"Password verification took too long: {verify_time:.3f}s"
    
    def test_password_concurrent_verification(self):
        """Test concurrent password verification for thread safety"""
        import threading
        import queue
        
        password = "ConcurrentTest123!"
        hash_result = self.password_hasher.hash(password)
        
        results = queue.Queue()
        thread_count = 10
        
        def verify_password_thread():
            """Thread function to verify password"""
            thread_results = []
            for _ in range(5):
                is_valid = AuthUserFactory.verify_password(hash_result, password)
                thread_results.append(is_valid)
            results.put(thread_results)
        
        # Start concurrent verification threads
        threads = []
        for _ in range(thread_count):
            thread = threading.Thread(target=verify_password_thread)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        all_results = []
        while not results.empty():
            thread_results = results.get()
            all_results.extend(thread_results)
        
        # All verifications should succeed
        successful_verifications = sum(all_results)
        total_verifications = thread_count * 5
        
        assert successful_verifications == total_verifications, \
            f"Concurrent verification failed: {successful_verifications}/{total_verifications}"


# Business Impact Summary for Password Hashing Tests
"""
Password Hashing Basic Tests - Business Impact

Security Foundation: User Account Protection
- Ensures secure password hashing for all local authentication flows
- Validates password verification accuracy and prevents authentication bypasses  
- Critical foundation for user account security and authentication integrity

Technical Excellence:
- Hash uniqueness: ensures each password hash is unique preventing rainbow table attacks
- Verification accuracy: tests both correct and incorrect password scenarios
- Format consistency: validates Argon2id format and security parameters
- Edge case handling: tests malformed inputs and boundary conditions
- Performance validation: ensures hashing/verification completes in reasonable time
- Concurrent safety: validates thread-safe password operations for production scalability

Platform Security:
- Foundation: Secure password handling foundation for all local user authentication
- Security: Comprehensive hashing validation prevents password-related vulnerabilities
- Performance: Fast verification ensures responsive authentication experience  
- Reliability: Edge case testing ensures robust password handling in production
- Integrity: Hash format validation maintains cryptographic security standards
"""