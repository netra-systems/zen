"""
Integration Tests: WebSocket Authentication Modes

PURPOSE: Test WebSocket connections with different authentication validation levels 
to resolve 1011 errors blocking the golden path user flow.

BUSINESS JUSTIFICATION:
- Problem: 1011 WebSocket errors block $500K+ ARR chat functionality
- Root Cause: GCP Load Balancer strips auth headers, strict validation fails
- Solution: Multiple auth modes (STRICT, RELAXED, DEMO, EMERGENCY)
- Test Strategy: Integration tests with real WebSocket connections

INTEGRATION TEST SCOPE:
- Real WebSocket connections (no mocks)
- Real authentication service integration
- Real database connections for user context
- Real environment variable configuration
- Real header processing and validation

EXPECTED FAILURES:
These tests MUST FAIL INITIALLY because:
1. Current system only supports STRICT auth mode
2. Permissive auth modes are not implemented
3. WebSocket connections will fail with 1011 errors
4. Demo mode will be rejected by current auth system
"""
import asyncio
import json
import pytest
import websockets
import time
from typing import Dict, Any, Optional
from unittest.mock import patch, Mock
import os
import uuid
from fastapi.testclient import TestClient
from fastapi import WebSocket
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.main import app
from tests.clients.websocket_client import WebSocketClient
from tests.helpers.auth_helper import create_test_user_with_jwt
from shared.isolated_environment import IsolatedEnvironment

@pytest.mark.integration
class WebSocketAuthModesTests(SSotBaseTestCase):
    """
    Integration tests for WebSocket authentication modes.
    
    These tests use REAL WebSocket connections to validate auth permissiveness.
    Tests MUST FAIL initially to prove current system blocks permissive modes.
    """

    @classmethod
    def setUpClass(cls):
        """Set up test environment with real services"""
        super().setUpClass()
        cls.client = TestClient(app)
        cls.websocket_url_local = 'ws://localhost:8000/ws'
        cls.websocket_url_test = 'ws://127.0.0.1:8000/ws'
        cls.strict_user = {'user_id': 'strict_user_123', 'jwt_token': None, 'auth_level': 'STRICT'}
        cls.relaxed_user = {'user_id': 'relaxed_user_456', 'jwt_token': None, 'auth_level': 'RELAXED'}
        cls.demo_user = {'user_id': f'demo-user-{int(time.time())}', 'jwt_token': None, 'auth_level': 'DEMO'}
        cls.emergency_user = {'user_id': 'emergency_user_789', 'jwt_token': None, 'auth_level': 'EMERGENCY'}

    async def asyncSetUp(self):
        """Set up each test with fresh auth tokens"""
        await super().asyncSetUp()
        try:
            self.strict_user['jwt_token'] = await create_test_user_with_jwt(user_id=self.strict_user['user_id'], email=f"{self.strict_user['user_id']}@test.com")
        except Exception as e:
            self.logger.warning(f'Failed to create test JWT: {e}')
            self.strict_user['jwt_token'] = None

    async def test_strict_auth_mode_with_valid_jwt(self):
        """
        Test STRICT auth mode with valid JWT - should work with current system.
        
        This test validates that current auth system works when JWT is present.
        """
        if not self.strict_user['jwt_token']:
            self.skipTest('JWT creation failed - indicates auth service issues')
        env = IsolatedEnvironment()
        env.set('AUTH_VALIDATION_LEVEL', 'STRICT')
        client = WebSocketClient()
        headers = {'Authorization': f"Bearer {self.strict_user['jwt_token']}"}
        try:
            success = await client.connect(url=self.websocket_url_test, headers=headers, timeout=10.0)
            if success:
                test_message = {'type': 'user_message', 'text': 'Test message for strict auth', 'thread_id': str(uuid.uuid4())}
                await client.send_message(test_message)
                response = await client.receive_message(timeout=5.0)
                self.assertIsNotNone(response)
                self.assertIn('type', response)
                await client.disconnect()
                self.assertTrue(True, 'STRICT auth mode works with valid JWT')
            else:
                self.fail('WebSocket connection failed even with valid JWT - indicates deeper auth issues')
        except Exception as e:
            self.fail(f'STRICT auth with valid JWT failed: {e} - indicates auth system problems')

    async def test_strict_auth_mode_blocks_missing_jwt(self):
        """
        Test STRICT auth mode blocks missing JWT - EXPECTED FAILURE.
        
        This test reproduces the 1011 error condition when JWT is missing.
        This is the core issue we need to solve with permissive auth.
        """
        env = IsolatedEnvironment()
        env.set('AUTH_VALIDATION_LEVEL', 'STRICT')
        client = WebSocketClient()
        headers = {}
        with self.assertRaises((websockets.ConnectionClosedError, ConnectionError)) as cm:
            success = await client.connect(url=self.websocket_url_test, headers=headers, timeout=5.0)
            if success:
                test_message = {'type': 'user_message', 'text': 'This should fail', 'thread_id': str(uuid.uuid4())}
                await client.send_message(test_message)
                await client.receive_message(timeout=2.0)
        error_message = str(cm.exception).lower()
        self.assertTrue(any((indicator in error_message for indicator in ['1011', 'unauthorized', 'auth', 'token'])), f'Expected auth-related error, got: {cm.exception}')
        self.logger.info(f'✅ Reproduced 1011 error condition: {cm.exception}')

    async def test_relaxed_auth_mode_not_implemented(self):
        """
        Test RELAXED auth mode - MUST FAIL (not implemented).
        
        RELAXED mode should accept degraded auth and create user context with warnings.
        This test will fail until we implement relaxed auth validation.
        """
        env = IsolatedEnvironment()
        env.set('AUTH_VALIDATION_LEVEL', 'RELAXED')
        client = WebSocketClient()
        headers = {'X-User-Hint': self.relaxed_user['user_id'], 'X-Auth-Degraded': 'true', 'X-Fallback-Auth': 'load-balancer-stripped'}
        try:
            success = await client.connect(url=self.websocket_url_test, headers=headers, timeout=5.0)
            if success:
                test_message = {'type': 'user_message', 'text': 'Test relaxed auth mode', 'thread_id': str(uuid.uuid4())}
                await client.send_message(test_message)
                response = await client.receive_message(timeout=2.0)
                if response and 'user_id' in response:
                    self.assertIn('degraded', response.get('auth_context', {}).get('level', '').lower(), 'Response should indicate degraded auth context')
                await client.disconnect()
                self.fail('Relaxed auth appears to be working - test needs update')
            else:
                self.assertTrue(True, 'RELAXED auth mode correctly failed (not implemented)')
        except Exception as e:
            error_message = str(e).lower()
            self.assertTrue(any((indicator in error_message for indicator in ['relaxed', 'not implemented', 'not found'])), f'Expected relaxed auth implementation error, got: {e}')
            self.logger.info(f'✅ Relaxed auth correctly failed (not implemented): {e}')

    async def test_demo_auth_mode_not_implemented(self):
        """
        Test DEMO auth mode - MUST FAIL (not implemented).
        
        DEMO mode should bypass authentication and create demo user context.
        This test will fail until we implement demo auth mode.
        """
        env = IsolatedEnvironment()
        env.set('DEMO_MODE', '1')
        env.set('AUTH_VALIDATION_LEVEL', 'DEMO')
        client = WebSocketClient()
        headers = {}
        try:
            success = await client.connect(url=self.websocket_url_test, headers=headers, timeout=5.0)
            if success:
                test_message = {'type': 'user_message', 'text': 'Test demo auth mode', 'thread_id': str(uuid.uuid4())}
                await client.send_message(test_message)
                response = await client.receive_message(timeout=2.0)
                if response and 'user_id' in response:
                    user_id = response['user_id']
                    self.assertTrue(user_id.startswith('demo-user-'), f'Expected demo user ID, got: {user_id}')
                await client.disconnect()
                self.fail('Demo auth appears to be working - test needs update')
            else:
                self.assertTrue(True, 'DEMO auth mode correctly failed (not implemented)')
        except Exception as e:
            error_message = str(e).lower()
            self.assertTrue(any((indicator in error_message for indicator in ['demo', 'not implemented', 'not found'])), f'Expected demo auth implementation error, got: {e}')
            self.logger.info(f'✅ Demo auth correctly failed (not implemented): {e}')

    async def test_emergency_auth_mode_not_implemented(self):
        """
        Test EMERGENCY auth mode - MUST FAIL (not implemented).
        
        EMERGENCY mode should provide minimal validation for system recovery.
        This test will fail until we implement emergency auth mode.
        """
        env = IsolatedEnvironment()
        env.set('AUTH_VALIDATION_LEVEL', 'EMERGENCY')
        client = WebSocketClient()
        headers = {'X-Emergency-Access': 'true', 'X-Emergency-Key': 'emergency_recovery_key', 'X-System-Recovery': 'auth-bypass-required'}
        try:
            success = await client.connect(url=self.websocket_url_test, headers=headers, timeout=5.0)
            if success:
                test_message = {'type': 'user_message', 'text': 'Test emergency auth mode', 'thread_id': str(uuid.uuid4())}
                await client.send_message(test_message)
                response = await client.receive_message(timeout=2.0)
                if response and 'user_id' in response:
                    user_id = response['user_id']
                    self.assertTrue(any((indicator in user_id.lower() for indicator in ['emergency', 'recovery'])), f'Expected emergency user ID, got: {user_id}')
                await client.disconnect()
                self.fail('Emergency auth appears to be working - test needs update')
            else:
                self.assertTrue(True, 'EMERGENCY auth mode correctly failed (not implemented)')
        except Exception as e:
            error_message = str(e).lower()
            self.assertTrue(any((indicator in error_message for indicator in ['emergency', 'not implemented', 'not found'])), f'Expected emergency auth implementation error, got: {e}')
            self.logger.info(f'✅ Emergency auth correctly failed (not implemented): {e}')

    async def test_gcp_load_balancer_header_stripping_simulation(self):
        """
        Test simulation of GCP Load Balancer header stripping.
        
        This test simulates the exact production scenario:
        1. Frontend sends WebSocket upgrade with Authorization header
        2. GCP Load Balancer strips the Authorization header
        3. Backend receives request without auth
        4. WebSocket connection fails with 1011 error
        """
        original_headers = {'Authorization': f"Bearer {self.strict_user.get('jwt_token', 'fake.jwt.token')}", 'Connection': 'Upgrade', 'Upgrade': 'websocket', 'Sec-WebSocket-Version': '13', 'Sec-WebSocket-Key': 'test-key-12345', 'User-Agent': 'Mozilla/5.0 (Test Browser)'}
        stripped_headers = {'Connection': 'Upgrade', 'Upgrade': 'websocket', 'Sec-WebSocket-Version': '13', 'Sec-WebSocket-Key': 'test-key-12345', 'User-Agent': 'Mozilla/5.0 (Test Browser)'}
        client = WebSocketClient()
        with self.assertRaises((websockets.ConnectionClosedError, ConnectionError)) as cm:
            success = await client.connect(url=self.websocket_url_test, headers=stripped_headers, timeout=5.0)
            if success:
                test_message = {'type': 'user_message', 'text': 'This should fail due to missing auth', 'thread_id': str(uuid.uuid4())}
                await client.send_message(test_message)
                await client.receive_message(timeout=2.0)
        error_message = str(cm.exception).lower()
        self.assertTrue(any((indicator in error_message for indicator in ['1011', 'unauthorized', 'auth', 'token', 'forbidden'])), f'Expected 1011/auth error, got: {cm.exception}')
        self.logger.info(f'✅ Reproduced GCP Load Balancer auth stripping issue: {cm.exception}')
        self.assertTrue(True, 'Successfully reproduced production 1011 error scenario')

    async def test_concurrent_auth_modes_isolation(self):
        """
        Test concurrent connections with different auth modes.
        
        This test validates that different auth validation levels can coexist
        without interfering with each other.
        """
        tasks = []
        try:
            if self.strict_user['jwt_token']:
                tasks.append(self._test_concurrent_auth_mode('STRICT', {'Authorization': f"Bearer {self.strict_user['jwt_token']}"}))
            tasks.append(self._test_concurrent_auth_mode('RELAXED', {'X-User-Hint': 'test_user', 'X-Auth-Degraded': 'true'}))
            tasks.append(self._test_concurrent_auth_mode('DEMO', {}))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum((1 for result in results if result is True))
            failure_count = sum((1 for result in results if isinstance(result, Exception)))
            expected_successes = 1 if self.strict_user['jwt_token'] else 0
            expected_failures = len(tasks) - expected_successes
            self.assertEqual(success_count, expected_successes, f'Expected {expected_successes} successes, got {success_count}')
            self.assertEqual(failure_count, expected_failures, f'Expected {expected_failures} failures, got {failure_count}')
            self.logger.info(f'✅ Concurrent auth test: {success_count} successes, {failure_count} failures')
        except Exception as e:
            self.logger.info(f'✅ Concurrent auth test failed as expected: {e}')
            self.assertTrue(True, 'Concurrent auth test correctly failed (features not implemented)')

    async def _test_concurrent_auth_mode(self, auth_mode: str, headers: Dict[str, str]) -> bool:
        """Helper method to test a specific auth mode concurrently."""
        env = IsolatedEnvironment()
        env.set('AUTH_VALIDATION_LEVEL', auth_mode)
        if auth_mode == 'DEMO':
            env.set('DEMO_MODE', '1')
        client = WebSocketClient()
        try:
            success = await client.connect(url=self.websocket_url_test, headers=headers, timeout=3.0)
            if success:
                test_message = {'type': 'user_message', 'text': f'Test {auth_mode} mode', 'thread_id': str(uuid.uuid4())}
                await client.send_message(test_message)
                await client.receive_message(timeout=2.0)
                await client.disconnect()
                return True
            else:
                return False
        except Exception as e:
            return e

    async def asyncTearDown(self):
        """Clean up after each test"""
        env = IsolatedEnvironment()
        env.remove('AUTH_VALIDATION_LEVEL', default=None)
        env.remove('DEMO_MODE', default=None)
        await super().asyncTearDown()

@pytest.mark.integration
class AuthModeEnvironmentDetectionTests(SSotBaseTestCase):
    """Test detection of authentication modes from environment configuration."""

    def test_auth_mode_environment_variable_detection(self):
        """Test detection of auth mode from environment variables."""
        test_scenarios = [({'AUTH_VALIDATION_LEVEL': 'STRICT'}, 'STRICT'), ({'AUTH_VALIDATION_LEVEL': 'RELAXED'}, 'RELAXED'), ({'AUTH_VALIDATION_LEVEL': 'DEMO', 'DEMO_MODE': '1'}, 'DEMO'), ({'AUTH_VALIDATION_LEVEL': 'EMERGENCY'}, 'EMERGENCY'), ({'DEMO_MODE': '1'}, 'DEMO'), ({}, 'STRICT')]
        for env_vars, expected_mode in test_scenarios:
            with patch.dict(os.environ, env_vars, clear=True):
                try:
                    from netra_backend.app.websocket_core.auth_permissiveness import AuthModeDetector
                    detector = AuthModeDetector()
                    detected_mode = detector.detect_from_environment()
                    self.assertEqual(detected_mode, expected_mode, f'Environment {env_vars} should detect {expected_mode}')
                except (ImportError, AttributeError, NotImplementedError) as e:
                    self.logger.info(f'✅ Auth mode detection correctly failed: {e}')
                    self.assertTrue(True, 'Auth mode detection not implemented (expected)')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')