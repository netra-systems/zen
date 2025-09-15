"""
SSOT Cross-Service Authentication Session Management E2E Test - ISSUE #814

PURPOSE: E2E test validating session management consistency across auth service and backend
EXPECTED: PASS after SSOT remediation - validates cross-service session consistency
TARGET: Session lifecycle managed by auth service, consistent across all backend services

BUSINESS VALUE: Ensures session reliability for $500K+ ARR user authentication experience
EXECUTION: Staging GCP environment - NO Docker dependency
"""
import logging
import pytest
import asyncio
import aiohttp
import websockets
import json
import time
from typing import Dict, Any, Optional, List
from test_framework.ssot.base_test_case import SSotAsyncTestCase
logger = logging.getLogger(__name__)

class TestCrossServiceAuthSessionMgmt(SSotAsyncTestCase):
    """
    E2E test validating cross-service authentication session management.
    Tests session consistency between auth service and backend services.
    """

    @classmethod
    async def asyncSetUpClass(cls):
        """Setup cross-service session testing environment"""
        await super().asyncSetUpClass()
        cls.auth_service_url = 'https://auth-service-staging.example.com'
        cls.backend_api_url = 'https://backend-staging.example.com'
        cls.websocket_url = 'wss://websocket-staging.example.com'
        cls.test_user_email = 'session-test@example.com'
        cls.test_user_password = 'SessionTest123!'

    async def asyncSetUp(self):
        """Setup individual test session"""
        await super().asyncSetUp()
        self.auth_token = None
        self.session_data = None
        self.http_session = None

    async def asyncTearDown(self):
        """Cleanup test session"""
        if self.http_session:
            await self.http_session.close()
        await super().asyncTearDown()

    async def test_session_creation_consistency_across_services(self):
        """
        E2E test: Session creation consistency between auth service and backend

        VALIDATES: Auth service creates session, backend recognizes same session
        ENSURES: Session ID consistent across all service interactions
        """
        logger.info('Creating session via auth service')
        await self._create_auth_service_session()
        logger.info('Validating session recognized by backend API')
        await self._validate_backend_session_recognition()
        logger.info('Validating session recognized by WebSocket service')
        await self._validate_websocket_session_recognition()
        logger.info('Cross-validating session consistency')
        await self._validate_cross_service_session_consistency()

    async def _create_auth_service_session(self):
        """Create authenticated session through auth service"""
        self.http_session = aiohttp.ClientSession()
        login_payload = {'email': self.test_user_email, 'password': self.test_user_password, 'create_session': True}
        async with self.http_session.post(f'{self.auth_service_url}/auth/login', json=login_payload) as response:
            assert response.status == 200, f'Auth service login failed: {response.status}'
            login_data = await response.json()
            self.auth_token = login_data['access_token']
            self.session_data = login_data['session']
            assert self.session_data is not None, 'Session data received from auth service'
            assert 'session_id' in self.session_data, 'Session ID provided by auth service'
            assert 'expires_at' in self.session_data, 'Session expiration from auth service'
            logger.info(f"Session created: {self.session_data['session_id']}")

    async def _validate_backend_session_recognition(self):
        """Validate backend API recognizes auth service session"""
        headers = {'Authorization': f'Bearer {self.auth_token}', 'X-Session-ID': self.session_data['session_id']}
        async with self.http_session.get(f'{self.backend_api_url}/api/v1/user/profile', headers=headers) as response:
            assert response.status == 200, 'Backend API recognizes auth service session'
            profile_data = await response.json()
            assert profile_data.get('session_id') == self.session_data['session_id'], 'Backend uses same session ID as auth service'
            assert profile_data.get('user_id') is not None, 'Backend provides user context from session'
            logger.info('Backend API session recognition successful')

    async def _validate_websocket_session_recognition(self):
        """Validate WebSocket service recognizes auth service session"""
        headers = {'Authorization': f'Bearer {self.auth_token}', 'X-Session-ID': self.session_data['session_id']}
        websocket_connection = await websockets.connect(self.websocket_url, extra_headers=headers, timeout=30)
        try:
            connection_msg = await asyncio.wait_for(websocket_connection.recv(), timeout=10)
            connection_data = json.loads(connection_msg)
            assert connection_data['type'] == 'connection_established', 'WebSocket connection established'
            assert connection_data.get('session_id') == self.session_data['session_id'], 'WebSocket uses same session ID as auth service'
            assert connection_data.get('user_id') is not None, 'WebSocket has user context from session'
            logger.info('WebSocket session recognition successful')
        finally:
            await websocket_connection.close()

    async def _validate_cross_service_session_consistency(self):
        """Validate session data consistent across all services"""
        auth_headers = {'Authorization': f'Bearer {self.auth_token}'}
        async with self.http_session.get(f'{self.auth_service_url}/auth/session/info', headers=auth_headers) as response:
            assert response.status == 200, 'Auth service session info accessible'
            auth_session_info = await response.json()
        backend_headers = {'Authorization': f'Bearer {self.auth_token}', 'X-Session-ID': self.session_data['session_id']}
        async with self.http_session.get(f'{self.backend_api_url}/api/v1/session/info', headers=backend_headers) as response:
            assert response.status == 200, 'Backend session info accessible'
            backend_session_info = await response.json()
        assert auth_session_info['session_id'] == backend_session_info['session_id'], 'Session ID consistent between auth service and backend'
        assert auth_session_info['user_id'] == backend_session_info['user_id'], 'User ID consistent between services'
        assert auth_session_info['expires_at'] == backend_session_info['expires_at'], 'Session expiration consistent between services'
        logger.info('Cross-service session consistency validated')

    async def test_session_refresh_consistency_across_services(self):
        """
        E2E test: Session refresh handled consistently across services

        VALIDATES: Session refresh through auth service updates all services
        ENSURES: Refreshed session recognized by backend and WebSocket
        """
        await self._create_auth_service_session()
        initial_session_id = self.session_data['session_id']
        logger.info('Refreshing session via auth service')
        await self._refresh_auth_service_session()
        logger.info('Validating backend recognizes refreshed session')
        await self._validate_backend_recognizes_refreshed_session(initial_session_id)
        logger.info('Validating WebSocket recognizes refreshed session')
        await self._validate_websocket_recognizes_refreshed_session()

    async def _refresh_auth_service_session(self):
        """Refresh session through auth service"""
        refresh_headers = {'Authorization': f'Bearer {self.auth_token}', 'X-Session-ID': self.session_data['session_id']}
        async with self.http_session.post(f'{self.auth_service_url}/auth/session/refresh', headers=refresh_headers) as response:
            assert response.status == 200, 'Session refresh successful'
            refresh_data = await response.json()
            self.auth_token = refresh_data.get('access_token', self.auth_token)
            self.session_data = refresh_data['session']
            assert 'session_id' in self.session_data, 'Refreshed session has ID'
            assert 'expires_at' in self.session_data, 'Refreshed session has new expiration'
            logger.info(f"Session refreshed: {self.session_data['session_id']}")

    async def _validate_backend_recognizes_refreshed_session(self, old_session_id: str):
        """Validate backend recognizes refreshed session"""
        headers = {'Authorization': f'Bearer {self.auth_token}', 'X-Session-ID': self.session_data['session_id']}
        async with self.http_session.get(f'{self.backend_api_url}/api/v1/user/profile', headers=headers) as response:
            assert response.status == 200, 'Backend recognizes refreshed session'
            profile_data = await response.json()
            assert profile_data.get('session_id') == self.session_data['session_id'], 'Backend uses refreshed session ID'
        old_headers = {'Authorization': f'Bearer {self.auth_token}', 'X-Session-ID': old_session_id}
        async with self.http_session.get(f'{self.backend_api_url}/api/v1/user/profile', headers=old_headers) as response:
            assert response.status == 401, 'Backend rejects old session after refresh'
        logger.info('Backend refreshed session recognition validated')

    async def _validate_websocket_recognizes_refreshed_session(self):
        """Validate WebSocket recognizes refreshed session"""
        headers = {'Authorization': f'Bearer {self.auth_token}', 'X-Session-ID': self.session_data['session_id']}
        websocket_connection = await websockets.connect(self.websocket_url, extra_headers=headers, timeout=30)
        try:
            connection_msg = await asyncio.wait_for(websocket_connection.recv(), timeout=10)
            connection_data = json.loads(connection_msg)
            assert connection_data.get('session_id') == self.session_data['session_id'], 'WebSocket recognizes refreshed session'
            logger.info('WebSocket refreshed session recognition validated')
        finally:
            await websocket_connection.close()

    async def test_session_expiration_handling_across_services(self):
        """
        E2E test: Session expiration handled consistently across services

        VALIDATES: Expired sessions rejected by all services
        ENSURES: Consistent session expiration behavior
        """
        await self._create_short_lived_session()
        logger.info('Waiting for session expiration')
        await asyncio.sleep(5)
        await self._validate_auth_service_rejects_expired_session()
        await self._validate_backend_rejects_expired_session()
        await self._validate_websocket_rejects_expired_session()

    async def _create_short_lived_session(self):
        """Create session with short expiration for testing"""
        self.http_session = aiohttp.ClientSession()
        login_payload = {'email': self.test_user_email, 'password': self.test_user_password, 'session_duration': 3}
        async with self.http_session.post(f'{self.auth_service_url}/auth/login', json=login_payload) as response:
            assert response.status == 200, 'Short-lived session created'
            login_data = await response.json()
            self.auth_token = login_data['access_token']
            self.session_data = login_data['session']

    async def _validate_auth_service_rejects_expired_session(self):
        """Validate auth service rejects expired session"""
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        async with self.http_session.get(f'{self.auth_service_url}/auth/validate', headers=headers) as response:
            assert response.status == 401, 'Auth service rejects expired session'
            error_data = await response.json()
            assert 'expired' in error_data.get('error', '').lower(), 'Session expiration error'

    async def _validate_backend_rejects_expired_session(self):
        """Validate backend rejects expired session"""
        headers = {'Authorization': f'Bearer {self.auth_token}', 'X-Session-ID': self.session_data['session_id']}
        async with self.http_session.get(f'{self.backend_api_url}/api/v1/user/profile', headers=headers) as response:
            assert response.status == 401, 'Backend rejects expired session'

    async def _validate_websocket_rejects_expired_session(self):
        """Validate WebSocket rejects expired session"""
        headers = {'Authorization': f'Bearer {self.auth_token}', 'X-Session-ID': self.session_data['session_id']}
        with pytest.raises(websockets.exceptions.ConnectionClosedError):
            websocket_connection = await websockets.connect(self.websocket_url, extra_headers=headers, timeout=10)
            await websocket_connection.recv()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')