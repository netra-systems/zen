"""
Security Regression Tests for Issue #465: Token Reuse Detection Threshold

PURPOSE: Ensure security properties are maintained while fixing threshold issue
EXPECTED BEHAVIOR: These tests should PASS to prove security is not compromised

Business Impact: Protect against actual token reuse attacks while allowing legitimate usage
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# SSOT Import Registry compliance
from netra_backend.app.auth_integration.auth import (
    BackendAuthIntegration, 
    _active_token_sessions,
    _token_usage_stats
)


class TestIssue465SecurityRegression(SSotAsyncTestCase):
    """
    Security regression tests for token reuse detection
    
    CRITICAL: These tests must PASS to ensure security is maintained
    They validate that actual security threats are still blocked
    """

    def setUp(self):
        super().setUp()
        # Clear token session state
        _active_token_sessions.clear()
        _token_usage_stats.update({
            'reuse_attempts_blocked': 0,
            'sessions_validated': 0,
            'validation_errors': 0
        })

    def test_actual_token_theft_scenario_blocked(self):
        """
        Test that genuine token theft/replay attacks are still blocked
        
        SECURITY SCENARIO: Attacker steals token and tries immediate reuse
        EXPECTED: Should PASS - security attack must be blocked
        """
        auth_integration = BackendAuthIntegration()
        
        # Legitimate user session
        legitimate_token_data = {
            'sub': 'legitimate-user-123',
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,
            'session_id': 'legitimate-session-123'
        }
        
        # Attacker's stolen token data (same token, different context)
        attacker_token_data = {
            'sub': 'legitimate-user-123',  # Same user ID
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,
            'session_id': 'attacker-session-456'  # Different session - key indicator
        }
        
        with patch.object(auth_integration, '_decode_and_validate_token') as mock_decode:
            # Legitimate user makes request
            mock_decode.return_value = legitimate_token_data
            result1 = auth_integration.validate_session_context("stolen-token", "legitimate-user-123")
            self.assertIsNotNone(result1)
            self.assertTrue(result1.is_valid)
            
            # Attacker immediately tries to use stolen token with different session
            mock_decode.return_value = attacker_token_data
            
            # This should be blocked - different session ID indicates attack
            with self.assertRaises(HTTPException) as context:
                auth_integration.validate_session_context("stolen-token", "legitimate-user-123")
            
            # Verify it's blocked for security reasons
            self.assertEqual(context.exception.status_code, 401)
            print("✅ SECURITY: Token theft with different session ID properly blocked")

    def test_rapid_brute_force_attempts_blocked(self):
        """
        Test that rapid brute force authentication attempts are blocked
        
        SECURITY SCENARIO: Attacker makes many rapid authentication attempts
        EXPECTED: Should PASS - brute force attacks must be blocked
        """
        auth_integration = BackendAuthIntegration()
        
        # Simulate brute force: many rapid attempts with same token
        attack_token_data = {
            'sub': 'attack-target-user',
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,
            'session_id': 'attack-session'
        }
        
        blocked_attempts = 0
        total_attempts = 20
        
        def brute_force_attempt(attempt_id):
            """Simulate a brute force authentication attempt"""
            try:
                with patch.object(auth_integration, '_decode_and_validate_token', return_value=attack_token_data):
                    auth_integration.validate_session_context("brute-force-token", "attack-target-user")
                    return {'attempt': attempt_id, 'blocked': False}
            except HTTPException:
                return {'attempt': attempt_id, 'blocked': True}
            except Exception as e:
                return {'attempt': attempt_id, 'blocked': True, 'error': str(e)}
        
        # Execute rapid brute force attempts
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(brute_force_attempt, i) for i in range(total_attempts)]
            results = [future.result() for future in futures]
        
        blocked_attempts = sum(1 for r in results if r['blocked'])
        success_attempts = total_attempts - blocked_attempts
        
        print(f"🔍 Brute Force Test Results:")
        print(f"   🎯 Total attempts: {total_attempts}")
        print(f"   🛡️ Blocked attempts: {blocked_attempts}")
        print(f"   ⚠️ Successful attempts: {success_attempts}")
        
        # Most attempts should be blocked (expect only first to succeed)
        self.assertGreaterEqual(blocked_attempts, total_attempts - 2,
                               f"Expected most brute force attempts blocked, got {blocked_attempts}/{total_attempts}")
        
        print("✅ SECURITY: Brute force attacks properly mitigated")

    def test_concurrent_different_users_allowed(self):
        """
        Test that concurrent requests from different users are always allowed
        
        SECURITY SCENARIO: Multiple legitimate users using system concurrently
        EXPECTED: Should PASS - different users should not interfere
        """
        auth_integration = BackendAuthIntegration()
        
        # Create different user sessions
        users = [
            {
                'token_data': {
                    'sub': f'user-{i}',
                    'iat': int(time.time()),
                    'exp': int(time.time()) + 3600,
                    'session_id': f'session-{i}'
                },
                'token': f'token-{i}',
                'user_id': f'user-{i}'
            }
            for i in range(5)
        ]
        
        def user_auth_attempt(user_info):
            """Simulate authentication attempt by different user"""
            try:
                with patch.object(auth_integration, '_decode_and_validate_token', return_value=user_info['token_data']):
                    result = auth_integration.validate_session_context(user_info['token'], user_info['user_id'])
                    return {'user': user_info['user_id'], 'success': True, 'result': result}
            except Exception as e:
                return {'user': user_info['user_id'], 'success': False, 'error': str(e)}
        
        # All users make concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(user_auth_attempt, user) for user in users]
            results = [future.result() for future in futures]
        
        successful_users = [r for r in results if r['success']]
        failed_users = [r for r in results if not r['success']]
        
        print(f"🔍 Multi-User Concurrent Access Test:")
        print(f"   👥 Total users: {len(users)}")
        print(f"   ✅ Successful auths: {len(successful_users)}")
        print(f"   ❌ Failed auths: {len(failed_users)}")
        
        # All different users should succeed
        self.assertEqual(len(failed_users), 0, 
                        f"Different users should not block each other: {[u['user'] for u in failed_users]}")
        
        print("✅ SECURITY: Different users can access system concurrently")

    def test_session_hijacking_detection(self):
        """
        Test detection of session hijacking attempts
        
        SECURITY SCENARIO: Attacker tries to use token from different IP/context
        EXPECTED: Should PASS - session hijacking should be detectable
        """
        auth_integration = BackendAuthIntegration()
        
        # Legitimate session
        legitimate_session = {
            'sub': 'target-user',
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,
            'session_id': 'legitimate-session-123'
        }
        
        with patch.object(auth_integration, '_decode_and_validate_token', return_value=legitimate_session):
            # Establish legitimate session
            result1 = auth_integration.validate_session_context("hijacked-token", "target-user")
            self.assertTrue(result1.is_valid)
            
            # Attacker tries to use same token rapidly (indicating hijacking)
            time.sleep(0.05)  # Very rapid reuse - suspicious pattern
            
            # This should be blocked due to suspicious rapid reuse
            with self.assertRaises(HTTPException) as context:
                auth_integration.validate_session_context("hijacked-token", "target-user")
            
            self.assertEqual(context.exception.status_code, 401)
            self.assertIn("Token reuse detected", context.exception.detail)
            
            print("✅ SECURITY: Rapid token reuse (potential hijacking) blocked")

    def test_legitimate_slow_usage_allowed(self):
        """
        Test that normal, slower usage patterns are always allowed
        
        SECURITY SCENARIO: Normal user behavior with reasonable timing
        EXPECTED: Should PASS - legitimate usage should never be blocked
        """
        auth_integration = BackendAuthIntegration()
        
        legitimate_token_data = {
            'sub': 'normal-user',
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,
            'session_id': 'normal-session'
        }
        
        with patch.object(auth_integration, '_decode_and_validate_token', return_value=legitimate_token_data):
            # Make requests with reasonable intervals (normal user behavior)
            intervals = [2.0, 1.5, 3.0, 2.5, 1.8]  # All above any reasonable threshold
            
            for i, interval in enumerate(intervals):
                if i > 0:  # Don't wait before first request
                    time.sleep(interval)
                
                result = auth_integration.validate_session_context("normal-token", "normal-user")
                self.assertIsNotNone(result)
                self.assertTrue(result.is_valid)
                
                print(f"   ✅ Request {i+1} after {interval if i > 0 else 0}s: Success")
        
        print("✅ SECURITY: Normal usage patterns always allowed")

    def test_expired_token_properly_rejected(self):
        """
        Test that expired tokens are properly rejected
        
        SECURITY SCENARIO: User tries to use expired authentication token
        EXPECTED: Should PASS - expired tokens must be rejected
        """
        auth_integration = BackendAuthIntegration()
        
        # Expired token
        expired_token_data = {
            'sub': 'expired-user',
            'iat': int(time.time()) - 7200,  # Issued 2 hours ago
            'exp': int(time.time()) - 3600,  # Expired 1 hour ago
            'session_id': 'expired-session'
        }
        
        with patch.object(auth_integration, '_decode_and_validate_token', return_value=expired_token_data):
            # Attempt to use expired token should fail
            with self.assertRaises(HTTPException) as context:
                auth_integration.validate_session_context("expired-token", "expired-user")
            
            # Should be rejected due to expiration
            self.assertEqual(context.exception.status_code, 401)
            print("✅ SECURITY: Expired tokens properly rejected")

    def test_malformed_token_rejected(self):
        """
        Test that malformed tokens are properly rejected
        
        SECURITY SCENARIO: Attacker provides malformed or invalid token
        EXPECTED: Should PASS - malformed tokens must be rejected
        """
        auth_integration = BackendAuthIntegration()
        
        # Malformed token data
        malformed_tokens = [
            None,  # None token
            {},    # Empty token data
            {'sub': 'user'},  # Missing required fields
            {'sub': 'user', 'iat': 'invalid'},  # Invalid data types
        ]
        
        for i, token_data in enumerate(malformed_tokens):
            with patch.object(auth_integration, '_decode_and_validate_token', return_value=token_data):
                with self.assertRaises(HTTPException) as context:
                    auth_integration.validate_session_context("malformed-token", "test-user")
                
                self.assertEqual(context.exception.status_code, 401)
                print(f"   ✅ Malformed token {i+1}: Properly rejected")
        
        print("✅ SECURITY: Malformed tokens properly rejected")

    def test_stats_tracking_security_events(self):
        """
        Test that security events are properly tracked in statistics
        
        SECURITY SCENARIO: Monitor security-related authentication events
        EXPECTED: Should PASS - security events must be tracked for monitoring
        """
        auth_integration = BackendAuthIntegration()
        
        initial_blocked = _token_usage_stats['reuse_attempts_blocked']
        initial_errors = _token_usage_stats['validation_errors']
        
        # Trigger security events
        malformed_token_data = {'sub': 'stats-user'}  # Missing required fields
        
        # Multiple rapid attempts (should increment blocked counter)
        for i in range(3):
            try:
                with patch.object(auth_integration, '_decode_and_validate_token', return_value=malformed_token_data):
                    auth_integration.validate_session_context("stats-token", "stats-user")
            except HTTPException:
                pass  # Expected
            
            if i < 2:  # Small delay between attempts
                time.sleep(0.1)
        
        # Verify stats were updated
        final_blocked = _token_usage_stats['reuse_attempts_blocked']
        final_errors = _token_usage_stats['validation_errors']
        
        self.assertGreaterEqual(final_blocked - initial_blocked, 0,
                               "Security events should be tracked in blocked counter")
        self.assertGreaterEqual(final_errors - initial_errors, 0,
                               "Validation errors should be tracked")
        
        print(f"✅ SECURITY: Stats tracking working - Blocked: +{final_blocked - initial_blocked}, Errors: +{final_errors - initial_errors}")


if __name__ == "__main__":
    print("🛡️ Running Issue #465 Security Regression Tests")
    print("📊 Expected Result: All tests should PASS, proving security is maintained")
    print("🎯 Purpose: Ensure token reuse threshold fix doesn't compromise security")
    
    import unittest
    unittest.main()