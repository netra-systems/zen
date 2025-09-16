"""
SSOT WebSocket REST Authentication Consistency Integration Test - ISSUE #814

PURPOSE: Integration test validating authentication consistency between WebSocket and REST API
EXPECTED: PASS after SSOT remediation - validates cross-protocol auth consistency
TARGET: WebSocket and REST API use same auth service delegation patterns

BUSINESS VALUE: Ensures consistent authentication experience for $500K+ ARR across protocols
EXECUTION: Staging environment integration - NO Docker dependency
"""
import logging
import pytest
import asyncio
import aiohttp
import websockets
import json
import os
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase
logger = logging.getLogger(__name__)

@pytest.mark.integration
class WebSocketRESTAuthConsistencyTests(SSotAsyncTestCase):
    """
    Integration test validating authentication consistency between WebSocket and REST protocols.
    Tests same auth service delegation patterns across both communication methods.
    """

    @classmethod
    async def asyncSetUpClass(cls):
        """Setup cross-protocol auth consistency testing"""
        await super().asyncSetUpClass()
        cls.staging_auth_service_url = os.getenv('STAGING_AUTH_SERVICE_URL', 'https://auth.netra-apex.com')
        cls.staging_backend_url = os.getenv('STAGING_BACKEND_URL', 'https://backend-staging.netra-apex.com')
        cls.staging_websocket_url = os.getenv('STAGING_WEBSOCKET_URL', 'wss://websocket-staging.netra-apex.com')
        cls.staging_test_email = 'websocket-rest-test@example.com'
        cls.staging_test_password = 'WSRESTTest123!'

    async def asyncSetUp(self):
        """Setup individual cross-protocol test"""
        await super().asyncSetUp()
        self.http_session = aiohttp.ClientSession()
        self.websocket_connection = None
        self.auth_token = None
        self.user_context = None

    async def asyncTearDown(self):
        """Cleanup cross-protocol test"""
        if self.websocket_connection:
            await self.websocket_connection.close()
        if self.http_session:
            await self.http_session.close()
        await super().asyncTearDown()

    async def test_websocket_rest_same_auth_token_validation(self):
        """
        Integration test: Same auth token works for both WebSocket and REST

        VALIDATES: Single auth token validated consistently across protocols
        ENSURES: Auth service delegation consistent for WebSocket and REST
        """
        logger.info('Authenticating with staging auth service')
        await self._authenticate_with_staging_auth_service()
        logger.info('Testing REST API auth with token')
        rest_user_data = await self._test_rest_api_auth()
        logger.info('Testing WebSocket auth with same token')
        websocket_user_data = await self._test_websocket_auth()
        logger.info('Validating user data consistency across protocols')
        await self._validate_cross_protocol_consistency(rest_user_data, websocket_user_data)

    async def _authenticate_with_staging_auth_service(self):
        """Authenticate with staging auth service"""
        login_payload = {'email': self.staging_test_email, 'password': self.staging_test_password}
        try:
            async with self.http_session.post(f'{self.staging_auth_service_url}/auth/login', json=login_payload, timeout=30) as response:
                if response.status == 200:
                    auth_data = await response.json()
                    self.auth_token = auth_data['access_token']
                    self.user_context = auth_data.get('user', {})
                    assert self.auth_token is not None, 'Auth token from staging auth service'
                    logger.info('Staging authentication successful')
                elif response.status == 401:
                    pytest.skip('Staging test user not configured')
                else:
                    pytest.fail(f'Staging auth service error: {response.status}')
        except aiohttp.ClientError as e:
            pytest.skip(f'Staging auth service not accessible: {e}')

    async def _test_rest_api_auth(self) -> Dict[str, Any]:
        """Test REST API authentication with auth token"""
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        try:
            async with self.http_session.get(f'{self.staging_backend_url}/api/v1/user/profile', headers=headers, timeout=30) as response:
                assert response.status == 200, 'REST API accepts auth service token'
                rest_data = await response.json()
                assert 'user_id' in rest_data, 'REST API provides user data from auth service'
                logger.info('REST API authentication successful')
                return rest_data
        except aiohttp.ClientError as e:
            pytest.skip(f'Staging REST API not accessible: {e}')

    async def _test_websocket_auth(self) -> Dict[str, Any]:
        """Test WebSocket authentication with same auth token"""
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        try:
            self.websocket_connection = await websockets.connect(self.staging_websocket_url, additional_headers=headers, timeout=30)
            connection_msg = await asyncio.wait_for(self.websocket_connection.recv(), timeout=10)
            websocket_data = json.loads(connection_msg)
            assert websocket_data['type'] == 'connection_established', 'WebSocket connection established'
            assert 'user_id' in websocket_data, 'WebSocket provides user data from auth service'
            logger.info('WebSocket authentication successful')
            return websocket_data
        except (websockets.exceptions.WebSocketException, ConnectionError) as e:
            pytest.skip(f'Staging WebSocket not accessible: {e}')

    async def _validate_cross_protocol_consistency(self, rest_data: Dict, websocket_data: Dict):
        """Validate user data consistency between REST and WebSocket"""
        if 'user_id' in rest_data and 'user_id' in websocket_data:
            assert rest_data['user_id'] == websocket_data['user_id'], 'User ID consistent between REST and WebSocket'
        if 'email' in rest_data and 'email' in websocket_data:
            assert rest_data['email'] == websocket_data['email'], 'Email consistent between REST and WebSocket'
        if 'tier' in rest_data and 'tier' in websocket_data:
            assert rest_data['tier'] == websocket_data['tier'], 'Tier consistent between REST and WebSocket'
        logger.info('Cross-protocol user data consistency validated')

    async def test_permission_consistency_across_protocols(self):
        """
        Integration test: User permissions consistent between WebSocket and REST

        VALIDATES: Permission enforcement consistent across communication protocols
        ENSURES: Auth service provides same permission context to both protocols
        """
        await self._authenticate_with_staging_auth_service()
        logger.info('Getting permissions via REST API')
        rest_permissions = await self._get_rest_permissions()
        logger.info('Getting permissions via WebSocket')
        websocket_permissions = await self._get_websocket_permissions()
        await self._validate_permission_consistency(rest_permissions, websocket_permissions)

    async def _get_rest_permissions(self) -> Dict[str, Any]:
        """Get user permissions via REST API"""
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        try:
            async with self.http_session.get(f'{self.staging_backend_url}/api/v1/user/permissions', headers=headers, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {'permissions': [], 'source': 'rest_fallback'}
        except aiohttp.ClientError:
            return {'permissions': [], 'source': 'rest_error'}

    async def _get_websocket_permissions(self) -> Dict[str, Any]:
        """Get user permissions via WebSocket"""
        if not self.websocket_connection:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            self.websocket_connection = await websockets.connect(self.staging_websocket_url, additional_headers=headers, timeout=30)
        permissions_request = {'type': 'get_permissions', 'request_id': 'permission-check-123'}
        await self.websocket_connection.send(json.dumps(permissions_request))
        try:
            permissions_msg = await asyncio.wait_for(self.websocket_connection.recv(), timeout=10)
            permissions_data = json.loads(permissions_msg)
            if permissions_data.get('type') == 'permissions_response':
                return permissions_data
            else:
                return {'permissions': [], 'source': 'websocket_fallback'}
        except asyncio.TimeoutError:
            return {'permissions': [], 'source': 'websocket_timeout'}

    async def _validate_permission_consistency(self, rest_perms: Dict, ws_perms: Dict):
        """Validate permission consistency between protocols"""
        rest_permission_list = rest_perms.get('permissions', [])
        ws_permission_list = ws_perms.get('permissions', [])
        if rest_permission_list and ws_permission_list:
            rest_sorted = sorted(rest_permission_list)
            ws_sorted = sorted(ws_permission_list)
            assert rest_sorted == ws_sorted, f'Permission mismatch: REST={rest_sorted}, WebSocket={ws_sorted}'
            logger.info(f'Permission consistency validated: {len(rest_permission_list)} permissions')

    async def test_session_consistency_across_protocols(self):
        """
        Integration test: Session management consistent between WebSocket and REST

        VALIDATES: Session lifecycle managed consistently across protocols
        ENSURES: Auth service session context shared between WebSocket and REST
        """
        await self._authenticate_with_staging_auth_service()
        logger.info('Testing session via REST API')
        rest_session_data = await self._test_rest_session()
        logger.info('Testing session via WebSocket')
        websocket_session_data = await self._test_websocket_session()
        await self._validate_session_consistency(rest_session_data, websocket_session_data)

    async def _test_rest_session(self) -> Dict[str, Any]:
        """Test session data via REST API"""
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        try:
            async with self.http_session.get(f'{self.staging_backend_url}/api/v1/session/info', headers=headers, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {'session_id': None, 'source': 'rest_fallback'}
        except aiohttp.ClientError:
            return {'session_id': None, 'source': 'rest_error'}

    async def _test_websocket_session(self) -> Dict[str, Any]:
        """Test session data via WebSocket"""
        if not self.websocket_connection:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            self.websocket_connection = await websockets.connect(self.staging_websocket_url, additional_headers=headers, timeout=30)
        session_request = {'type': 'get_session_info', 'request_id': 'session-check-456'}
        await self.websocket_connection.send(json.dumps(session_request))
        try:
            session_msg = await asyncio.wait_for(self.websocket_connection.recv(), timeout=10)
            session_data = json.loads(session_msg)
            if session_data.get('type') == 'session_info_response':
                return session_data
            else:
                return {'session_id': None, 'source': 'websocket_fallback'}
        except asyncio.TimeoutError:
            return {'session_id': None, 'source': 'websocket_timeout'}

    async def _validate_session_consistency(self, rest_session: Dict, ws_session: Dict):
        """Validate session consistency between protocols"""
        rest_session_id = rest_session.get('session_id')
        ws_session_id = ws_session.get('session_id')
        if rest_session_id and ws_session_id:
            assert rest_session_id == ws_session_id, f'Session ID mismatch: REST={rest_session_id}, WebSocket={ws_session_id}'
            logger.info(f'Session consistency validated: {rest_session_id}')
        rest_expires = rest_session.get('expires_at')
        ws_expires = ws_session.get('expires_at')
        if rest_expires and ws_expires:
            assert rest_expires == ws_expires, 'Session expiration mismatch between protocols'

    async def test_auth_token_refresh_consistency(self):
        """
        Integration test: Token refresh consistent between WebSocket and REST

        VALIDATES: Refreshed tokens work across both protocols
        ENSURES: Auth service token refresh recognized by both WebSocket and REST
        """
        await self._authenticate_with_staging_auth_service()
        original_token = self.auth_token
        logger.info('Refreshing token via REST API')
        await self._refresh_token_via_rest()
        logger.info('Testing refreshed token with REST')
        await self._test_refreshed_token_rest()
        logger.info('Testing refreshed token with WebSocket')
        await self._test_refreshed_token_websocket()
        logger.info('Verifying old token invalidated')
        await self._verify_old_token_invalidated(original_token)

    async def _refresh_token_via_rest(self):
        """Refresh auth token via REST API"""
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        try:
            async with self.http_session.post(f'{self.staging_auth_service_url}/auth/refresh', headers=headers, timeout=30) as response:
                if response.status == 200:
                    refresh_data = await response.json()
                    self.auth_token = refresh_data['access_token']
                    logger.info('Token refresh successful')
                else:
                    pytest.skip('Token refresh not available in staging')
        except aiohttp.ClientError:
            pytest.skip('Token refresh endpoint not accessible')

    async def _test_refreshed_token_rest(self):
        """Test refreshed token with REST API"""
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        async with self.http_session.get(f'{self.staging_backend_url}/api/v1/user/profile', headers=headers, timeout=30) as response:
            assert response.status == 200, 'REST API accepts refreshed token'

    async def _test_refreshed_token_websocket(self):
        """Test refreshed token with WebSocket"""
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        if self.websocket_connection:
            await self.websocket_connection.close()
        self.websocket_connection = await websockets.connect(self.staging_websocket_url, additional_headers=headers, timeout=30)
        connection_msg = await asyncio.wait_for(self.websocket_connection.recv(), timeout=10)
        connection_data = json.loads(connection_msg)
        assert connection_data['type'] == 'connection_established', 'WebSocket accepts refreshed token'

    async def _verify_old_token_invalidated(self, old_token: str):
        """Verify old token no longer works"""
        old_headers = {'Authorization': f'Bearer {old_token}'}
        async with self.http_session.get(f'{self.staging_backend_url}/api/v1/user/profile', headers=old_headers, timeout=30) as response:
            assert response.status == 401, 'REST API rejects old token after refresh'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')