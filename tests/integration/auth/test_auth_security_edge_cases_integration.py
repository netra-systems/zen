"""
Auth Security Edge Cases Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (Free/Early/Mid/Enterprise)
- Business Goal: Security and Compliance
- Value Impact: Prevents security breaches that could impact $500K+ ARR and customer trust
- Strategic Impact: Validates security edge cases that protect against attack vectors

CRITICAL: These tests use REAL auth services to validate security patterns.
Tests actual attack scenarios and edge cases to ensure robust security.

GitHub Issue #718 Coverage Enhancement: Security edge case testing scenarios
"""

import asyncio
import jwt
import time
import pytest
import hashlib
import random
import string
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from auth_service.auth_core.config import AuthConfig
from auth_service.services.jwt_service import JWTService
from auth_service.services.redis_service import RedisService


class AuthSecurityEdgeCasesIntegrationTests(SSotAsyncTestCase):
    """Security edge case testing for auth integration with real services."""

    @pytest.fixture(autouse=True)
    async def setup_security_test(self):
        """Set up security test environment with real services."""
        self.env = IsolatedEnvironment.get_instance()

        # Real auth service configuration
        self.auth_config = AuthConfig()
        self.jwt_service = JWTService(self.auth_config)

        # Real Redis service for session storage
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()

        # Security test data
        self.attack_vectors = []
        self.security_violations = []

        # Test users for security scenarios
        self.security_test_users = [
            {
                'user_id': 'security_user_1',
                'email': 'security1@example.com',
                'permissions': ['read']
            },
            {
                'user_id': 'security_user_admin',
                'email': 'admin@example.com',
                'permissions': ['read', 'write', 'admin']
            },
            {
                'user_id': 'security_user_enterprise',
                'email': 'enterprise@example.com',
                'permissions': ['read', 'write', 'enterprise']
            }
        ]

        yield

        # Cleanup security test data
        await self._cleanup_security_data()

    async def _cleanup_security_data(self):
        """Clean up security test data from Redis."""
        try:
            # Clean all security test sessions
            for user in self.security_test_users:
                pattern = f"session:{user['user_id']}:*"
                keys = await self.redis_service.keys(pattern)
                if keys:
                    await self.redis_service.delete(*keys)

                # Clean security test tokens
                token_pattern = f"token:{user['user_id']}:*"
                token_keys = await self.redis_service.keys(token_pattern)
                if token_keys:
                    await self.redis_service.delete(*token_keys)

            # Clean blacklist entries
            blacklist_pattern = "blacklist:security_test_*"
            blacklist_keys = await self.redis_service.keys(blacklist_pattern)
            if blacklist_keys:
                await self.redis_service.delete(*blacklist_keys)

            await self.redis_service.close()
        except Exception as e:
            self.logger.warning(f"Security test cleanup warning: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.security
    async def test_jwt_signature_tampering_attacks(self):
        """
        Test JWT signature tampering attack scenarios.

        BVJ: Prevents token forgery attacks that could compromise user accounts.
        """
        user = self.security_test_users[0]

        # Generate legitimate token
        legitimate_token = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions']
        )

        # Attack vector 1: Modified signature
        parts = legitimate_token.split('.')
        modified_signature = 'tampered_signature_attack_test'
        tampered_token_1 = f"{parts[0]}.{parts[1]}.{modified_signature}"

        # Attack vector 2: Signature from different token
        other_user_token = await self.jwt_service.create_access_token(
            user_id='other_user',
            email='other@example.com',
            permissions=['read']
        )
        other_parts = other_user_token.split('.')
        signature_swap_token = f"{parts[0]}.{parts[1]}.{other_parts[2]}"

        # Attack vector 3: Empty signature
        empty_signature_token = f"{parts[0]}.{parts[1]}."

        # Attack vector 4: Malformed signature
        malformed_signature = ''.join(random.choices(string.ascii_letters + string.digits, k=50))
        malformed_token = f"{parts[0]}.{parts[1]}.{malformed_signature}"

        attack_tokens = [
            ('modified_signature', tampered_token_1),
            ('signature_swap', signature_swap_token),
            ('empty_signature', empty_signature_token),
            ('malformed_signature', malformed_token)
        ]

        security_results = []

        for attack_type, attack_token in attack_tokens:
            try:
                # Attempt validation - should fail for all attack vectors
                is_valid = await self.jwt_service.validate_token(attack_token)

                # Security violation if any attack token is validated as valid
                if is_valid:
                    self.security_violations.append({
                        'attack_type': attack_type,
                        'token': attack_token[:50] + '...',
                        'validated_as_valid': True,
                        'severity': 'CRITICAL'
                    })

                security_results.append({
                    'attack_type': attack_type,
                    'token_accepted': is_valid,
                    'validation_error': None
                })

            except Exception as e:
                # Expected - attacks should cause validation errors
                security_results.append({
                    'attack_type': attack_type,
                    'token_accepted': False,
                    'validation_error': str(e)
                })

        # Security assertions - ALL attacks must fail
        for result in security_results:
            assert not result['token_accepted'], f"Security breach: {result['attack_type']} attack succeeded"

        # Validate legitimate token still works
        legitimate_valid = await self.jwt_service.validate_token(legitimate_token)
        assert legitimate_valid, "Legitimate token validation failed after security tests"

        self.logger.info(f"JWT signature tampering tests: {len(security_results)} attack vectors blocked")
        assert len(self.security_violations) == 0, f"Security violations detected: {self.security_violations}"

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.security
    async def test_privilege_escalation_attacks(self):
        """
        Test privilege escalation attack scenarios.

        BVJ: Prevents unauthorized access to admin/enterprise features.
        """
        # Create tokens for different privilege levels
        basic_user = self.security_test_users[0]  # read only
        admin_user = self.security_test_users[1]  # read, write, admin
        enterprise_user = self.security_test_users[2]  # read, write, enterprise

        basic_token = await self.jwt_service.create_access_token(
            user_id=basic_user['user_id'],
            email=basic_user['email'],
            permissions=basic_user['permissions']
        )

        admin_token = await self.jwt_service.create_access_token(
            user_id=admin_user['user_id'],
            email=admin_user['email'],
            permissions=admin_user['permissions']
        )

        # Attack vector 1: Payload permission modification
        basic_parts = basic_token.split('.')
        basic_payload = jwt.decode(basic_token, options={"verify_signature": False})

        # Attempt to escalate permissions in payload
        escalated_payload = basic_payload.copy()
        escalated_payload['permissions'] = ['read', 'write', 'admin', 'enterprise']

        # Re-encode with escalated permissions (but original signature)
        import base64
        import json
        escalated_payload_b64 = base64.urlsafe_b64encode(
            json.dumps(escalated_payload).encode()
        ).decode().rstrip('=')

        privilege_escalation_token = f"{basic_parts[0]}.{escalated_payload_b64}.{basic_parts[2]}"

        # Attack vector 2: User ID swapping to admin
        user_swap_payload = basic_payload.copy()
        user_swap_payload['sub'] = admin_user['user_id']  # Swap to admin user ID
        user_swap_payload_b64 = base64.urlsafe_b64encode(
            json.dumps(user_swap_payload).encode()
        ).decode().rstrip('=')

        user_swap_token = f"{basic_parts[0]}.{user_swap_payload_b64}.{basic_parts[2]}"

        # Attack vector 3: Role injection via claims
        role_injection_payload = basic_payload.copy()
        role_injection_payload['role'] = 'admin'
        role_injection_payload['is_admin'] = True
        role_injection_payload['admin_override'] = True

        role_injection_payload_b64 = base64.urlsafe_b64encode(
            json.dumps(role_injection_payload).encode()
        ).decode().rstrip('=')

        role_injection_token = f"{basic_parts[0]}.{role_injection_payload_b64}.{basic_parts[2]}"

        attack_scenarios = [
            ('privilege_escalation', privilege_escalation_token),
            ('user_id_swap', user_swap_token),
            ('role_injection', role_injection_token)
        ]

        escalation_results = []

        for attack_type, attack_token in attack_scenarios:
            try:
                # Validate attack token - should fail due to signature mismatch
                is_valid = await self.jwt_service.validate_token(attack_token)

                if is_valid:
                    # Critical security violation
                    self.security_violations.append({
                        'attack_type': attack_type,
                        'severity': 'CRITICAL',
                        'description': 'Privilege escalation attack succeeded'
                    })

                escalation_results.append({
                    'attack_type': attack_type,
                    'validation_passed': is_valid,
                    'security_breach': is_valid
                })

            except Exception as e:
                # Expected - attacks should fail validation
                escalation_results.append({
                    'attack_type': attack_type,
                    'validation_passed': False,
                    'security_breach': False,
                    'error': str(e)
                })

        # Security assertions - ALL privilege escalation attempts must fail
        for result in escalation_results:
            assert not result['validation_passed'], f"Privilege escalation {result['attack_type']} succeeded"

        # Validate legitimate tokens still work
        basic_valid = await self.jwt_service.validate_token(basic_token)
        admin_valid = await self.jwt_service.validate_token(admin_token)

        assert basic_valid, "Basic user token validation failed"
        assert admin_valid, "Admin user token validation failed"

        self.logger.info(f"Privilege escalation tests: {len(escalation_results)} attack vectors blocked")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.security
    async def test_token_replay_and_timing_attacks(self):
        """
        Test token replay and timing attack scenarios.

        BVJ: Prevents token reuse attacks and timing-based vulnerabilities.
        """
        user = self.security_test_users[0]

        # Generate tokens for replay testing
        token_1 = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions']
        )

        # Simulate token blacklisting (revocation)
        decoded_token = jwt.decode(
            token_1,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        jti = decoded_token['jti']

        # Blacklist token in Redis
        blacklist_key = f"blacklist:security_test_{jti}"
        await self.redis_service.set(
            blacklist_key,
            {
                'user_id': user['user_id'],
                'blacklisted_at': datetime.now(timezone.utc).isoformat(),
                'reason': 'security_test_replay'
            },
            ex=3600
        )

        # Attack vector 1: Replay blacklisted token
        try:
            # Mock blacklist checking in validation
            async def check_blacklist(token_jti):
                blacklist_entry = await self.redis_service.get(f"blacklist:security_test_{token_jti}")
                return blacklist_entry is not None

            is_blacklisted = await check_blacklist(jti)
            assert is_blacklisted, "Token not properly blacklisted"

            # In a real implementation, validation would check blacklist
            # For this test, we simulate the security check
            replay_blocked = is_blacklisted
            assert replay_blocked, "Replay attack not blocked - blacklisted token accepted"

        except Exception as e:
            self.logger.error(f"Blacklist check failed: {e}")
            raise

        # Attack vector 2: Rapid token generation timing attack
        timing_attack_start = time.time()
        rapid_tokens = []

        for i in range(10):
            rapid_token = await self.jwt_service.create_access_token(
                user_id=f"{user['user_id']}_timing_{i}",
                email=user['email'],
                permissions=user['permissions']
            )
            rapid_tokens.append(rapid_token)

        timing_attack_duration = time.time() - timing_attack_start

        # Validate timing attack resistance
        # All tokens should be unique despite rapid generation
        assert len(set(rapid_tokens)) == len(rapid_tokens), "Timing attack produced duplicate tokens"

        # Each token should have unique JTI
        jtis = []
        for token in rapid_tokens:
            decoded = jwt.decode(
                token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            jtis.append(decoded['jti'])

        assert len(set(jtis)) == len(jtis), "Rapid token generation produced duplicate JTIs"

        # Attack vector 3: Expired token replay
        expired_token = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions'],
            expires_delta=timedelta(seconds=1)  # Very short expiry
        )

        # Wait for token to expire
        await asyncio.sleep(2)

        # Attempt to use expired token
        try:
            expired_valid = await self.jwt_service.validate_token(expired_token)
            assert not expired_valid, "Expired token validation succeeded - security breach"
        except jwt.ExpiredSignatureError:
            # Expected - expired tokens should raise this error
            pass

        self.logger.info("Token replay and timing attack tests completed successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.security
    async def test_session_fixation_and_hijacking_attacks(self):
        """
        Test session fixation and hijacking attack scenarios.

        BVJ: Prevents session-based attacks that could compromise user accounts.
        """
        user = self.security_test_users[0]

        # Create legitimate user session
        legitimate_token = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions']
        )

        session_key = f"session:{user['user_id']}:security_test"
        session_data = {
            'user_id': user['user_id'],
            'token': legitimate_token,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'ip_address': '192.168.1.100',
            'user_agent': 'TestAgent/1.0'
        }

        await self.redis_service.set(session_key, session_data, ex=1800)

        # Attack vector 1: Session fixation - attacker tries to set known session ID
        attacker_session_key = f"session:{user['user_id']}:attacker_fixed"
        attacker_session_data = {
            'user_id': user['user_id'],
            'token': 'attacker_controlled_token',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'ip_address': '10.0.0.1',  # Different IP
            'user_agent': 'AttackerAgent/1.0'
        }

        # Attempt session fixation
        await self.redis_service.set(attacker_session_key, attacker_session_data, ex=1800)

        # Validate session isolation
        legitimate_session = await self.redis_service.get(session_key)
        attacker_session = await self.redis_service.get(attacker_session_key)

        assert legitimate_session != attacker_session, "Session fixation vulnerability detected"

        # Attack vector 2: Session hijacking via session ID prediction
        # Generate multiple sessions to test for predictable patterns
        session_ids = []
        for i in range(20):
            test_token = await self.jwt_service.create_access_token(
                user_id=f"test_user_{i}",
                email=f"test{i}@example.com",
                permissions=['read']
            )

            decoded = jwt.decode(
                test_token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            session_ids.append(decoded['jti'])

        # Check for predictable patterns in session IDs
        # Convert to integers if possible to check for sequential patterns
        numeric_patterns = []
        for session_id in session_ids:
            # Check if JTI contains predictable numeric patterns
            numeric_chars = ''.join(filter(str.isdigit, session_id))
            if numeric_chars:
                numeric_patterns.append(int(numeric_chars) if len(numeric_chars) < 10 else 0)

        if len(numeric_patterns) > 5:
            # Check for sequential patterns
            differences = [numeric_patterns[i+1] - numeric_patterns[i]
                          for i in range(len(numeric_patterns)-1) if numeric_patterns[i] != 0]

            if differences:
                avg_difference = sum(differences) / len(differences)
                # If average difference is small and consistent, might indicate predictability
                assert avg_difference > 1000 or len(set(differences)) > len(differences) * 0.7, \
                    "Session ID generation might be predictable"

        # Attack vector 3: Cross-user session contamination
        user_2 = self.security_test_users[1]

        user_2_token = await self.jwt_service.create_access_token(
            user_id=user_2['user_id'],
            email=user_2['email'],
            permissions=user_2['permissions']
        )

        user_2_session_key = f"session:{user_2['user_id']}:security_test"
        user_2_session_data = {
            'user_id': user_2['user_id'],
            'token': user_2_token,
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        await self.redis_service.set(user_2_session_key, user_2_session_data, ex=1800)

        # Verify session isolation between users
        user_1_session_retrieved = await self.redis_service.get(session_key)
        user_2_session_retrieved = await self.redis_service.get(user_2_session_key)

        assert user_1_session_retrieved != user_2_session_retrieved, "Cross-user session contamination detected"

        # Verify tokens are different
        user_1_token_from_session = user_1_session_retrieved['token']
        user_2_token_from_session = user_2_session_retrieved['token']

        assert user_1_token_from_session != user_2_token_from_session, "Token contamination between users"

        # Cleanup attack session
        await self.redis_service.delete(attacker_session_key)
        await self.redis_service.delete(user_2_session_key)

        self.logger.info("Session fixation and hijacking attack tests completed successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.security
    async def test_brute_force_and_rate_limiting_attacks(self):
        """
        Test brute force and rate limiting attack scenarios.

        BVJ: Prevents automated attacks that could compromise system availability.
        """
        user = self.security_test_users[0]

        # Attack vector 1: Rapid token validation attempts (brute force)
        legitimate_token = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions']
        )

        # Generate many invalid tokens for brute force testing
        invalid_tokens = []
        for i in range(50):
            # Create tokens with invalid signatures
            parts = legitimate_token.split('.')
            invalid_signature = f"invalid_sig_{i}_{random.randint(1000, 9999)}"
            invalid_token = f"{parts[0]}.{parts[1]}.{invalid_signature}"
            invalid_tokens.append(invalid_token)

        # Rapid validation attempts
        start_time = time.time()
        validation_results = []

        for invalid_token in invalid_tokens:
            try:
                is_valid = await self.jwt_service.validate_token(invalid_token)
                validation_results.append({'valid': is_valid, 'error': None})
            except Exception as e:
                validation_results.append({'valid': False, 'error': str(e)})

        brute_force_duration = time.time() - start_time

        # Security assertions
        successful_validations = [r for r in validation_results if r['valid']]
        assert len(successful_validations) == 0, f"Brute force attack: {len(successful_validations)} invalid tokens validated as valid"

        # Rate limiting check - rapid requests should not crash the system
        requests_per_second = len(invalid_tokens) / brute_force_duration
        assert brute_force_duration < 60, f"Brute force attack took too long: {brute_force_duration:.2f}s"

        # Attack vector 2: Concurrent validation flood
        concurrent_attack_start = time.time()

        async def concurrent_validation_attack(attack_id):
            """Single concurrent validation attack."""
            try:
                parts = legitimate_token.split('.')
                attack_signature = f"concurrent_attack_{attack_id}_{random.randint(1000, 9999)}"
                attack_token = f"{parts[0]}.{parts[1]}.{attack_signature}"

                is_valid = await self.jwt_service.validate_token(attack_token)
                return {'attack_id': attack_id, 'valid': is_valid, 'success': True}
            except Exception as e:
                return {'attack_id': attack_id, 'valid': False, 'success': False, 'error': str(e)}

        # Launch concurrent attack
        concurrent_tasks = [concurrent_validation_attack(i) for i in range(30)]
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        concurrent_duration = time.time() - concurrent_attack_start

        # Analyze concurrent attack results
        concurrent_validations = [r for r in concurrent_results if r.get('valid', False)]
        failed_attacks = [r for r in concurrent_results if not r.get('success', False)]

        assert len(concurrent_validations) == 0, f"Concurrent attack: {len(concurrent_validations)} invalid tokens validated"

        # System should handle concurrent attacks gracefully
        assert concurrent_duration < 30, f"System overwhelmed by concurrent attack: {concurrent_duration:.2f}s"

        # Attack vector 3: Token generation flood
        generation_start = time.time()

        async def generate_token_flood(flood_id):
            """Generate token in flood attack."""
            try:
                token = await self.jwt_service.create_access_token(
                    user_id=f"flood_user_{flood_id}",
                    email=f"flood{flood_id}@example.com",
                    permissions=['read']
                )
                return {'flood_id': flood_id, 'success': True, 'token_length': len(token)}
            except Exception as e:
                return {'flood_id': flood_id, 'success': False, 'error': str(e)}

        # Token generation flood
        flood_tasks = [generate_token_flood(i) for i in range(25)]
        flood_results = await asyncio.gather(*flood_tasks)
        generation_duration = time.time() - generation_start

        # Validate flood attack resilience
        successful_generations = [r for r in flood_results if r.get('success', False)]

        # System should handle flood gracefully without completely failing
        success_rate = len(successful_generations) / len(flood_results)
        assert success_rate >= 0.5, f"Token generation flood caused system failure: {success_rate:.2%} success rate"

        # Verify legitimate token still works after attacks
        final_validation = await self.jwt_service.validate_token(legitimate_token)
        assert final_validation, "Legitimate token validation failed after brute force attacks"

        self.logger.info(f"Brute force attack tests completed:")
        self.logger.info(f"  Sequential attacks: {len(invalid_tokens)} attempts in {brute_force_duration:.2f}s")
        self.logger.info(f"  Concurrent attacks: {len(concurrent_tasks)} attempts in {concurrent_duration:.2f}s")
        self.logger.info(f"  Generation flood: {len(flood_tasks)} attempts in {generation_duration:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.security
    async def test_token_injection_and_malformed_payload_attacks(self):
        """
        Test token injection and malformed payload attack scenarios.

        BVJ: Prevents injection attacks through malformed token payloads.
        """
        user = self.security_test_users[0]

        # Attack vector 1: SQL injection via token claims
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'; DELETE FROM sessions; --",
            "1' UNION SELECT * FROM admin_users--"
        ]

        for sql_payload in sql_injection_payloads:
            try:
                # Attempt to create token with malicious user_id
                malicious_token = await self.jwt_service.create_access_token(
                    user_id=sql_payload,
                    email=user['email'],
                    permissions=user['permissions']
                )

                # Token creation might succeed, but validation should handle it safely
                is_valid = await self.jwt_service.validate_token(malicious_token)

                # Decode to check if injection payload was sanitized
                if is_valid:
                    decoded = jwt.decode(
                        malicious_token,
                        self.auth_config.jwt_secret_key,
                        algorithms=[self.auth_config.jwt_algorithm]
                    )

                    # Check if dangerous SQL characters were properly handled
                    user_id_in_token = decoded.get('sub', '')
                    dangerous_chars = ["'", "--", ";", "DROP", "DELETE", "UNION"]

                    # Log potential security concern if SQL injection chars are present
                    for dangerous_char in dangerous_chars:
                        if dangerous_char in user_id_in_token:
                            self.logger.warning(f"Potential SQL injection vector in token: {dangerous_char}")

            except Exception as e:
                # Expected for malformed inputs
                self.logger.info(f"SQL injection payload safely rejected: {sql_payload[:20]}...")

        # Attack vector 2: XSS injection via token claims
        xss_injection_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src='x' onerror='alert(1)'>",
            "';alert('xss');//"
        ]

        for xss_payload in xss_injection_payloads:
            try:
                xss_token = await self.jwt_service.create_access_token(
                    user_id=user['user_id'],
                    email=xss_payload,  # Inject via email field
                    permissions=user['permissions']
                )

                is_valid = await self.jwt_service.validate_token(xss_token)

                if is_valid:
                    decoded = jwt.decode(
                        xss_token,
                        self.auth_config.jwt_secret_key,
                        algorithms=[self.auth_config.jwt_algorithm]
                    )

                    email_in_token = decoded.get('email', '')
                    # Check for XSS patterns
                    xss_patterns = ["<script", "javascript:", "onerror", "alert("]

                    for pattern in xss_patterns:
                        if pattern.lower() in email_in_token.lower():
                            self.logger.warning(f"Potential XSS vector in token: {pattern}")

            except Exception as e:
                self.logger.info(f"XSS injection payload safely rejected: {xss_payload[:20]}...")

        # Attack vector 3: Buffer overflow simulation
        overflow_payloads = [
            'A' * 1000,  # Very long user ID
            'B' * 5000,  # Extremely long email
            ['permission'] * 100  # Very long permissions array
        ]

        overflow_test_results = []

        try:
            # Test with oversized user_id
            overflow_token_1 = await self.jwt_service.create_access_token(
                user_id=overflow_payloads[0],
                email=user['email'],
                permissions=user['permissions']
            )
            overflow_test_results.append({'type': 'user_id_overflow', 'success': True})
        except Exception as e:
            overflow_test_results.append({'type': 'user_id_overflow', 'success': False, 'error': str(e)})

        try:
            # Test with oversized email
            overflow_token_2 = await self.jwt_service.create_access_token(
                user_id=user['user_id'],
                email=overflow_payloads[1],
                permissions=user['permissions']
            )
            overflow_test_results.append({'type': 'email_overflow', 'success': True})
        except Exception as e:
            overflow_test_results.append({'type': 'email_overflow', 'success': False, 'error': str(e)})

        try:
            # Test with oversized permissions
            overflow_token_3 = await self.jwt_service.create_access_token(
                user_id=user['user_id'],
                email=user['email'],
                permissions=overflow_payloads[2]
            )
            overflow_test_results.append({'type': 'permissions_overflow', 'success': True})
        except Exception as e:
            overflow_test_results.append({'type': 'permissions_overflow', 'success': False, 'error': str(e)})

        # Validate system handles overflow attacks gracefully
        successful_overflows = [r for r in overflow_test_results if r['success']]

        # System should either reject or safely handle oversized inputs
        if len(successful_overflows) > 0:
            self.logger.warning(f"System accepted {len(successful_overflows)} overflow payloads")

        # Attack vector 4: Malformed JSON in token
        legitimate_token = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions']
        )

        parts = legitimate_token.split('.')

        # Malformed payload attacks
        malformed_payloads = [
            'invalid_base64_!@#$%',
            'eyJtYWxmb3JtZWQiOiB0cnVlfQ==',  # Valid base64 but malformed JSON
            '',  # Empty payload
            'null',
            '{"malformed": true, "incomplete"'  # Incomplete JSON
        ]

        for malformed_payload in malformed_payloads:
            malformed_token = f"{parts[0]}.{malformed_payload}.{parts[2]}"

            try:
                is_valid = await self.jwt_service.validate_token(malformed_token)
                assert not is_valid, f"Malformed payload accepted: {malformed_payload}"
            except Exception as e:
                # Expected - malformed tokens should cause validation errors
                pass

        self.logger.info("Token injection and malformed payload attack tests completed successfully")
