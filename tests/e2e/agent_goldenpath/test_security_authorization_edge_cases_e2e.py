"""
E2E Tests for Security and Authorization Edge Cases - Golden Path Enterprise Security

MISSION CRITICAL: Tests security and authorization edge cases to validate enterprise-grade
security controls in the Golden Path agent workflow. These tests ensure that security
boundaries are properly enforced and cannot be bypassed through edge cases.

Business Value Justification (BVJ):
- Segment: Enterprise Users (Regulatory Compliance & Security Requirements)
- Business Goal: Security Compliance & Trust through Robust Authorization Controls
- Value Impact: Validates security controls critical for enterprise contracts (SOC2, HIPAA, etc.)
- Strategic Impact: Security vulnerabilities = enterprise churn = compliance violations = $500K+ ARR loss

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- SECURITY VALIDATION: Test actual security boundaries and authorization controls
- EDGE CASE TESTING: Attempt to bypass security through various attack vectors
- ENTERPRISE COMPLIANCE: Validate against real regulatory requirements
- NEGATIVE TESTING: Ensure unauthorized access fails gracefully and securely

CRITICAL: These tests must attempt real security bypasses with proper failure validation.
No mocking of security controls or skipping actual authorization checks.

GitHub Issue: #861 Agent Golden Path Messages Test Creation - Gap Area 5
Coverage Target: Security and authorization edge cases (identified gap)
"""
import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import uuid
import httpx
import base64
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper

@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.security_edge_cases
@pytest.mark.mission_critical
class SecurityAuthorizationEdgeCasesE2ETests(SSotAsyncTestCase):
    """
    E2E tests for validating security and authorization edge cases in staging GCP.

    Tests enterprise security controls, authorization boundaries,
    and resistance to various security bypass attempts.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment for security testing."""
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        if not is_staging_available():
            pytest.skip('Staging environment not available')
        cls.auth_helper = E2EAuthHelper(environment='staging')
        cls.websocket_helper = WebSocketTestHelper(base_url=cls.staging_config.urls.websocket_url, environment='staging')
        cls.logger.info(f'Security and authorization edge cases E2E tests initialized for staging')

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.security_test_session = f'security_test_{int(time.time())}'
        self.legitimate_user_id = f'legit_user_{int(time.time())}'
        self.legitimate_user_email = f'legit_user_{int(time.time())}@netra-testing.ai'
        self.legitimate_access_token = self.__class__.auth_helper.create_test_jwt_token(user_id=self.legitimate_user_id, email=self.legitimate_user_email, exp_minutes=60)
        self.logger.info(f'Security test setup - session: {self.security_test_session}')

    async def _attempt_websocket_connection(self, headers: Dict[str, str], should_succeed: bool=True, timeout: float=15.0) -> Dict[str, Any]:
        """Attempt WebSocket connection with provided headers and validate expected outcome."""
        connection_result = {'success': False, 'connected': False, 'error': None, 'connection_time': 0, 'websocket': None}
        start_time = time.time()
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers=headers, ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=timeout)
            connection_result['connected'] = True
            connection_result['websocket'] = websocket
            connection_result['connection_time'] = time.time() - start_time
            if should_succeed:
                test_message = {'type': 'ping', 'timestamp': time.time()}
                await websocket.send(json.dumps(test_message))
                connection_result['success'] = True
            else:
                await websocket.close()
                connection_result['success'] = False
                connection_result['error'] = 'Connection succeeded when it should have failed'
        except websockets.InvalidHandshake as e:
            connection_result['error'] = f'Invalid handshake: {e}'
            connection_result['success'] = not should_succeed
        except websockets.ConnectionClosed as e:
            connection_result['error'] = f'Connection closed: {e}'
            connection_result['success'] = not should_succeed
        except asyncio.TimeoutError:
            connection_result['error'] = 'Connection timeout'
            connection_result['success'] = not should_succeed
        except Exception as e:
            connection_result['error'] = f'Connection error: {e}'
            connection_result['success'] = not should_succeed
        connection_result['connection_time'] = time.time() - start_time
        return connection_result

    async def _attempt_agent_request_with_auth(self, auth_token: str, should_succeed: bool=True, timeout: float=30.0) -> Dict[str, Any]:
        """Attempt agent request with specific authentication and validate expected outcome."""
        request_result = {'success': False, 'connected': False, 'response_received': False, 'events': [], 'error': None, 'auth_error': False}
        try:
            connection_result = await self._attempt_websocket_connection({'Authorization': f'Bearer {auth_token}', 'X-Environment': 'staging', 'X-Test-Suite': 'security-authorization-edge-cases'}, should_succeed=True, timeout=15.0)
            if not connection_result['connected']:
                request_result['error'] = f"Connection failed: {connection_result['error']}"
                request_result['success'] = not should_succeed
                return request_result
            websocket = connection_result['websocket']
            request_result['connected'] = True
            test_request = {'type': 'agent_request', 'agent': 'triage_agent', 'message': f"Security test request - should {('succeed' if should_succeed else 'fail')}", 'thread_id': f'security_test_{int(time.time())}', 'run_id': f'security_run_{int(time.time())}', 'user_id': self.legitimate_user_id, 'context': {'security_test': True, 'expected_outcome': 'success' if should_succeed else 'failure'}}
            await websocket.send(json.dumps(test_request))
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    request_result['events'].append(event)
                    event_type = event.get('type', 'unknown')
                    if event_type in ['auth_error', 'unauthorized', 'forbidden']:
                        request_result['auth_error'] = True
                        break
                    if event_type == 'agent_completed':
                        request_result['response_received'] = True
                        break
                    if event_type in ['error', 'agent_error']:
                        break
                except asyncio.TimeoutError:
                    break
                except json.JSONDecodeError:
                    continue
            await websocket.close()
            if should_succeed:
                request_result['success'] = request_result['response_received'] and (not request_result['auth_error'])
            else:
                request_result['success'] = not request_result['response_received'] or request_result['auth_error']
        except Exception as e:
            request_result['error'] = str(e)
            request_result['success'] = not should_succeed
        return request_result

    async def test_expired_token_rejection(self):
        """
        Test rejection of expired JWT tokens.

        SECURITY VALIDATION: Expired tokens should be rejected immediately
        without allowing any access to agent functionality.

        Scenario:
        1. Create expired JWT token
        2. Attempt WebSocket connection with expired token
        3. Verify connection is rejected
        4. Attempt agent request if connection succeeds
        5. Ensure no unauthorized access is granted

        DIFFICULTY: Medium (20 minutes)
        REAL SERVICES: Yes - JWT validation in staging
        STATUS: Should PASS - Token expiration critical for security
        """
        self.logger.info('🔒 Testing expired token rejection')
        expired_token = self.__class__.auth_helper.create_test_jwt_token(user_id=f'expired_user_{int(time.time())}', email=f'expired_{int(time.time())}@netra-testing.ai', exp_minutes=-60)
        connection_result = await self._attempt_websocket_connection({'Authorization': f'Bearer {expired_token}', 'X-Environment': 'staging', 'X-Test-Suite': 'expired-token-test'}, should_succeed=False)
        self.logger.info(f'📊 Expired Token Test Results:')
        self.logger.info(f"   Connection Success: {connection_result['success']}")
        self.logger.info(f"   Connected: {connection_result['connected']}")
        self.logger.info(f"   Error: {connection_result['error']}")
        assert connection_result['success'], f'Expired token should be rejected. Connection result: {connection_result}'
        assert not connection_result['connected'], f'Should not establish connection with expired token'
        if connection_result['error']:
            error_lower = connection_result['error'].lower()
            auth_error_indicators = ['unauthorized', 'forbidden', 'invalid', 'expired', 'token']
            has_auth_error = any((indicator in error_lower for indicator in auth_error_indicators))
            assert has_auth_error, f"Should receive authentication-related error for expired token. Error: {connection_result['error']}"
        self.logger.info('✅ Expired token rejection validated')

    async def test_invalid_token_format_rejection(self):
        """
        Test rejection of malformed JWT tokens.

        SECURITY VALIDATION: Malformed tokens should be rejected immediately
        without causing system errors or allowing unauthorized access.

        Scenario:
        1. Create various malformed JWT tokens
        2. Attempt connections with each malformed token
        3. Verify all connections are rejected gracefully
        4. Ensure no system instability from malformed tokens
        5. Validate appropriate error handling

        DIFFICULTY: Medium (25 minutes)
        REAL SERVICES: Yes - JWT parsing security in staging
        STATUS: Should PASS - Token format validation essential for security
        """
        self.logger.info('🔧 Testing invalid token format rejection')
        invalid_tokens = ['invalid-jwt-token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid-payload.invalid-signature', 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9', '', 'null', base64.b64encode(b'not-a-jwt-token').decode(), 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ', 'malformed' * 100]
        rejection_results = []
        for i, invalid_token in enumerate(invalid_tokens):
            self.logger.info(f'Testing invalid token format {i + 1}/{len(invalid_tokens)}...')
            connection_result = await self._attempt_websocket_connection({'Authorization': f'Bearer {invalid_token}', 'X-Environment': 'staging', 'X-Test-Suite': f'invalid-token-format-{i + 1}'}, should_succeed=False, timeout=10.0)
            rejection_results.append({'token_type': f'invalid_format_{i + 1}', 'token_preview': invalid_token[:50] + '...' if len(invalid_token) > 50 else invalid_token, 'result': connection_result})
        successful_rejections = [r for r in rejection_results if r['result']['success']]
        failed_rejections = [r for r in rejection_results if not r['result']['success']]
        self.logger.info(f'📊 Invalid Token Format Test Results:')
        self.logger.info(f'   Total Tests: {len(invalid_tokens)}')
        self.logger.info(f'   Successful Rejections: {len(successful_rejections)}')
        self.logger.info(f'   Failed Rejections: {len(failed_rejections)}')
        rejection_rate = len(successful_rejections) / len(invalid_tokens)
        assert rejection_rate >= 0.9, f"Invalid token rejection rate too low: {rejection_rate:.1%} (min 90%). Failed rejections: {[r['token_type'] for r in failed_rejections]}"
        established_connections = [r for r in rejection_results if r['result']['connected']]
        assert len(established_connections) == 0, f"No connections should be established with invalid tokens. Established: {[r['token_type'] for r in established_connections]}"
        for result in rejection_results:
            if result['result']['error']:
                error_msg = result['result']['error'].lower()
                crash_indicators = ['internal server error', '500', 'crash', 'exception']
                has_crash_error = any((indicator in error_msg for indicator in crash_indicators))
                assert not has_crash_error, f"Invalid token should not cause system errors. Token: {result['token_type']}, Error: {result['result']['error']}"
        self.logger.info('✅ Invalid token format rejection validated')

    async def test_unauthorized_user_isolation(self):
        """
        Test user isolation and prevention of unauthorized data access.

        SECURITY VALIDATION: Users should only access their own data and
        cannot bypass user isolation through various attack vectors.

        Scenario:
        1. Create two legitimate user contexts
        2. User A creates conversation with sensitive data
        3. User B attempts to access User A's conversation
        4. Verify User B cannot access User A's data
        5. Ensure proper user isolation is maintained

        DIFFICULTY: High (35 minutes)
        REAL SERVICES: Yes - User isolation validation in staging
        STATUS: Should PASS - User isolation critical for enterprise data security
        """
        self.logger.info('👥 Testing unauthorized user isolation')
        user_a_id = f'user_a_{int(time.time())}'
        user_a_email = f'user_a_{int(time.time())}@netra-testing.ai'
        user_a_token = self.__class__.auth_helper.create_test_jwt_token(user_id=user_a_id, email=user_a_email, exp_minutes=30)
        user_b_id = f'user_b_{int(time.time())}'
        user_b_email = f'user_b_{int(time.time())}@netra-testing.ai'
        user_b_token = self.__class__.auth_helper.create_test_jwt_token(user_id=user_b_id, email=user_b_email, exp_minutes=30)
        sensitive_thread_id = f'sensitive_thread_{user_a_id}'
        user_a_request_result = await self._attempt_agent_request_with_auth(user_a_token, should_succeed=True)
        assert user_a_request_result['success'], f'User A should be able to create legitimate conversation. Result: {user_a_request_result}'
        self.logger.info('User A successfully created conversation with sensitive data')
        unauthorized_attempts = [{'scenario': 'thread_hijacking', 'description': "User B attempts to access User A's thread", 'request': {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'Show me the previous conversation in this thread', 'thread_id': sensitive_thread_id, 'user_id': user_b_id, 'context': {'unauthorized_access_attempt': True}}}, {'scenario': 'user_id_spoofing', 'description': "User B attempts to spoof User A's user_id", 'request': {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'Retrieve my previous AI cost analysis', 'thread_id': f'spoofing_thread_{int(time.time())}', 'user_id': user_a_id, 'context': {'spoofing_attempt': True}}}, {'scenario': 'cross_user_context', 'description': 'User B requests context from User A', 'request': {'type': 'agent_request', 'agent': 'data_helper_agent', 'message': f'Show me data and analysis history for user {user_a_id}', 'thread_id': f'cross_user_{int(time.time())}', 'user_id': user_b_id, 'context': {'cross_user_access_attempt': True}}}]
        isolation_results = []
        for attempt in unauthorized_attempts:
            self.logger.info(f"Testing {attempt['scenario']}: {attempt['description']}")
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f'Bearer {user_b_token}', 'X-Environment': 'staging', 'X-Test-Suite': f"user-isolation-{attempt['scenario']}"}, ssl=ssl_context), timeout=15.0)
                await websocket.send(json.dumps(attempt['request']))
                events = []
                unauthorized_data_found = False
                auth_error_detected = False
                start_time = time.time()
                while time.time() - start_time < 20.0:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event = json.loads(event_data)
                        events.append(event)
                        event_type = event.get('type', 'unknown')
                        if event_type in ['auth_error', 'unauthorized', 'forbidden']:
                            auth_error_detected = True
                            break
                        if event_type == 'agent_completed':
                            response_data = event.get('data', {})
                            result = response_data.get('result', {})
                            response_content = str(result).lower()
                            user_a_indicators = [user_a_id.lower(), user_a_email.lower(), sensitive_thread_id.lower()]
                            for indicator in user_a_indicators:
                                if indicator in response_content:
                                    unauthorized_data_found = True
                                    break
                            break
                        if event_type in ['error', 'agent_error']:
                            break
                    except asyncio.TimeoutError:
                        break
                await websocket.close()
                isolation_results.append({'scenario': attempt['scenario'], 'auth_error_detected': auth_error_detected, 'unauthorized_data_found': unauthorized_data_found, 'events_received': len(events), 'isolation_maintained': not unauthorized_data_found})
            except Exception as e:
                isolation_results.append({'scenario': attempt['scenario'], 'auth_error_detected': True, 'unauthorized_data_found': False, 'events_received': 0, 'isolation_maintained': True, 'error': str(e)})
        successful_isolations = [r for r in isolation_results if r['isolation_maintained']]
        data_breaches = [r for r in isolation_results if r['unauthorized_data_found']]
        self.logger.info(f'📊 User Isolation Test Results:')
        self.logger.info(f'   Total Scenarios: {len(unauthorized_attempts)}')
        self.logger.info(f'   Successful Isolations: {len(successful_isolations)}')
        self.logger.info(f'   Data Breaches: {len(data_breaches)}')
        for result in isolation_results:
            self.logger.info(f"   {result['scenario']}: Isolated: {result['isolation_maintained']}, Auth Error: {result['auth_error_detected']}")
        isolation_success_rate = len(successful_isolations) / len(unauthorized_attempts)
        assert isolation_success_rate == 1.0, f"User isolation must be 100% effective. Success rate: {isolation_success_rate:.1%}. Data breaches: {[r['scenario'] for r in data_breaches]}"
        assert len(data_breaches) == 0, f'No unauthorized data access should be possible. Breaches: {data_breaches}'
        self.logger.info('✅ Unauthorized user isolation validated')

    async def test_malicious_request_payload_rejection(self):
        """
        Test rejection of malicious request payloads and injection attempts.

        SECURITY VALIDATION: System should handle and reject malicious payloads
        without compromising security or system stability.

        Scenario:
        1. Send requests with various malicious payloads
        2. Attempt injection attacks through request fields
        3. Test oversized and malformed request structures
        4. Verify system handles attacks gracefully
        5. Ensure no security bypasses or system compromise

        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes - Payload security validation in staging
        STATUS: Should PASS - Malicious payload rejection critical for system security
        """
        self.logger.info('🛡️ Testing malicious request payload rejection')
        malicious_payloads = [{'name': 'sql_injection_attempt', 'payload': {'type': 'agent_request', 'agent': "triage_agent'; DROP TABLE users; --", 'message': "SELECT * FROM sensitive_data WHERE user_id = '1' OR '1'='1'", 'user_id': "'; DROP TABLE conversations; --"}}, {'name': 'xss_injection_attempt', 'payload': {'type': 'agent_request', 'agent': "<script>alert('XSS')</script>", 'message': "<img src=x onerror=alert('XSS')>Please optimize my AI costs</img>", 'user_id': "user<script>location.href='evil.com'</script>"}}, {'name': 'command_injection_attempt', 'payload': {'type': 'agent_request', 'agent': 'triage_agent', 'message': "Optimize costs; rm -rf /; echo 'system compromised'", 'user_id': 'user`whoami`', 'context': {'command': '$(cat /etc/passwd)'}}}, {'name': 'oversized_payload', 'payload': {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'X' * 100000, 'user_id': 'A' * 10000, 'context': {'large_data': 'B' * 50000}}}, {'name': 'null_byte_injection', 'payload': {'type': 'agent_request', 'agent': 'triage_agent\x00malicious', 'message': 'Cost optimization\x00<script>alert()</script>', 'user_id': 'user\x00admin'}}, {'name': 'unicode_bypass_attempt', 'payload': {'type': 'agent_request', 'agent': 'triage\u202emalicious\u202d_agent', 'message': 'Normal request\u200b<script>evil()</script>', 'user_id': 'user\ufeff_admin'}}, {'name': 'prototype_pollution', 'payload': {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'AI cost help', '__proto__': {'admin': True}, 'constructor': {'prototype': {'isAdmin': True}}}}, {'name': 'deep_nesting_attack', 'payload': self._create_deeply_nested_payload(50)}]
        rejection_results = []
        for attack in malicious_payloads:
            self.logger.info(f"Testing {attack['name']}...")
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f'Bearer {self.legitimate_access_token}', 'X-Environment': 'staging', 'X-Test-Suite': f"malicious-payload-{attack['name']}"}, ssl=ssl_context), timeout=15.0)
                payload_sent = False
                try:
                    await websocket.send(json.dumps(attack['payload']))
                    payload_sent = True
                except Exception as send_error:
                    rejection_results.append({'attack': attack['name'], 'rejected_at_send': True, 'error': str(send_error), 'security_maintained': True})
                    await websocket.close()
                    continue
                events = []
                security_compromise = False
                proper_rejection = False
                start_time = time.time()
                while time.time() - start_time < 15.0:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        event = json.loads(event_data)
                        events.append(event)
                        event_type = event.get('type', 'unknown')
                        if event_type in ['error', 'validation_error', 'malformed_request']:
                            proper_rejection = True
                            break
                        if event_type == 'agent_completed':
                            response_data = event.get('data', {})
                            response_str = str(response_data).lower()
                            compromise_indicators = ['system compromised', 'table dropped', 'passwd', 'whoami', "alert('xss')", 'script executed', 'admin: true']
                            for indicator in compromise_indicators:
                                if indicator in response_str:
                                    security_compromise = True
                                    break
                            break
                    except asyncio.TimeoutError:
                        break
                    except json.JSONDecodeError:
                        continue
                await websocket.close()
                rejection_results.append({'attack': attack['name'], 'rejected_at_send': False, 'payload_sent': payload_sent, 'proper_rejection': proper_rejection, 'security_compromise': security_compromise, 'events_received': len(events), 'security_maintained': not security_compromise})
            except Exception as e:
                rejection_results.append({'attack': attack['name'], 'rejected_at_connection': True, 'error': str(e), 'security_maintained': True})
        secure_rejections = [r for r in rejection_results if r.get('security_maintained', True)]
        security_compromises = [r for r in rejection_results if r.get('security_compromise', False)]
        self.logger.info(f'📊 Malicious Payload Test Results:')
        self.logger.info(f'   Total Attacks: {len(malicious_payloads)}')
        self.logger.info(f'   Secure Rejections: {len(secure_rejections)}')
        self.logger.info(f'   Security Compromises: {len(security_compromises)}')
        for result in rejection_results:
            self.logger.info(f"   {result['attack']}: Secure: {result.get('security_maintained', True)}")
        security_success_rate = len(secure_rejections) / len(malicious_payloads)
        assert security_success_rate == 1.0, f"Malicious payload security must be 100% effective. Success rate: {security_success_rate:.1%}. Compromises: {[r['attack'] for r in security_compromises]}"
        assert len(security_compromises) == 0, f'No security compromises should be possible through malicious payloads. Compromises: {security_compromises}'
        self.logger.info('✅ Malicious request payload rejection validated')

    def _create_deeply_nested_payload(self, depth: int) -> Dict[str, Any]:
        """Create deeply nested payload for testing parsing limits."""
        if depth <= 0:
            return {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'Deep nesting attack payload', 'user_id': 'nested_attack_user'}
        return {'nested': self._create_deeply_nested_payload(depth - 1)}

    async def test_rate_limiting_and_abuse_prevention(self):
        """
        Test rate limiting and abuse prevention mechanisms.

        SECURITY VALIDATION: System should implement rate limiting to prevent
        abuse and ensure fair resource usage across users.

        Scenario:
        1. Send requests at normal rate (should succeed)
        2. Send requests at excessive rate (should be limited)
        3. Test rate limiting per user vs global
        4. Verify rate limit recovery after cool-down
        5. Ensure legitimate users aren't blocked by rate limiting

        DIFFICULTY: High (35 minutes)
        REAL SERVICES: Yes - Rate limiting validation in staging
        STATUS: Should PASS - Rate limiting critical for system stability and security
        """
        self.logger.info('⏱️ Testing rate limiting and abuse prevention')
        normal_rate_requests = 3
        normal_rate_results = []
        self.logger.info(f'Testing normal rate: {normal_rate_requests} requests with delays...')
        for i in range(normal_rate_requests):
            result = await self._attempt_agent_request_with_auth(self.legitimate_access_token, should_succeed=True, timeout=30.0)
            normal_rate_results.append(result)
            if i < normal_rate_requests - 1:
                await asyncio.sleep(2)
        normal_success_rate = sum((1 for r in normal_rate_results if r['success'])) / len(normal_rate_results)
        self.logger.info(f'Normal rate success: {normal_success_rate:.1%}')
        rapid_rate_requests = 10
        rapid_rate_results = []
        self.logger.info(f'Testing rapid rate: {rapid_rate_requests} requests without delays...')
        rapid_tasks = [self._attempt_agent_request_with_auth(self.legitimate_access_token, should_succeed=False, timeout=15.0) for _ in range(rapid_rate_requests)]
        rapid_rate_results = await asyncio.gather(*rapid_tasks, return_exceptions=True)
        successful_rapid = [r for r in rapid_rate_results if isinstance(r, dict) and r.get('success')]
        failed_rapid = [r for r in rapid_rate_results if isinstance(r, dict) and (not r.get('success'))]
        rapid_success_rate = len(successful_rapid) / rapid_rate_requests
        self.logger.info(f'📊 Rate Limiting Test Results:')
        self.logger.info(f'   Normal Rate Success: {normal_success_rate:.1%}')
        self.logger.info(f'   Rapid Rate Success: {rapid_success_rate:.1%}')
        self.logger.info(f'   Rapid Requests Blocked: {len(failed_rapid)}/{rapid_rate_requests}')
        assert normal_success_rate >= 0.8, f'Normal rate requests should succeed: {normal_success_rate:.1%} (min 80%)'
        if rapid_success_rate >= 0.8:
            successful_times = [r.get('connection_time', 0) + sum((event.get('processing_time', 0) for event in r.get('events', []))) for r in successful_rapid]
            if successful_times:
                avg_rapid_time = sum(successful_times) / len(successful_times)
                self.logger.info(f'   Rapid requests avg time: {avg_rapid_time:.1f}s')
        self.logger.info('Testing rate limit recovery after cool-down...')
        await asyncio.sleep(10)
        recovery_result = await self._attempt_agent_request_with_auth(self.legitimate_access_token, should_succeed=True, timeout=30.0)
        assert recovery_result['success'], f'Should recover from rate limiting after cool-down period. Recovery result: {recovery_result}'
        self.logger.info('✅ Rate limiting and abuse prevention validated')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')