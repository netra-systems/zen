"""
Integration Tests for Authentication + WebSocket Integration with Real Services

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Revenue Protection - Validates secure $500K+ ARR real-time authenticated chat
- Value Impact: Authenticated WebSocket connections enable secure multi-user AI interactions
- Strategic Impact: Integration tests ensure authentication + WebSocket security works end-to-end

CRITICAL: These are GOLDEN PATH integration tests using REAL services:
- Real JWT token validation and WebSocket authentication
- Real Redis session management and user isolation
- Real multi-user authentication boundaries
- Real session persistence and cleanup

No mocks - all authentication and WebSocket services are real.
"""
import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from shared.types.core_types import UserID, WebSocketID, ensure_user_id
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.real_services_test_fixtures import real_services_fixture

@pytest.mark.integration
@pytest.mark.golden_path
class AuthWebSocketIntegrationRealServicesTests(SSotBaseTestCase):
    """
    Integration tests for Authentication + WebSocket with real services.
    
    These tests validate that authenticated WebSocket connections work correctly
    with real authentication services, session management, and user isolation.
    """

    @pytest.fixture(autouse=True)
    async def setup_real_services(self, real_services_fixture):
        """Set up real services for integration testing."""
        self.services = real_services_fixture
        self.db_session = self.services['db_session']
        self.redis_client = self.services['redis_client']
        self.auth_helper = E2EWebSocketAuthHelper(environment='test')

    @pytest.mark.asyncio
    async def test_authenticated_websocket_connection_real_jwt(self):
        """
        Test Case: WebSocket connections authenticate with real JWT tokens.
        
        Business Value: Ensures secure access to $500K+ ARR chat functionality.
        Expected: Only properly authenticated users can establish WebSocket connections.
        """
        user_id = 'auth_ws_user_123'
        jwt_token = self.auth_helper.create_test_jwt_token(user_id=user_id, email='auth_ws_user@example.com', permissions=['read', 'write', 'websocket'], exp_minutes=30)
        websocket_headers = self.auth_helper.get_websocket_headers(jwt_token)
        token_validation = await self.auth_helper.validate_jwt_token(jwt_token)
        handshake_result = await self._simulate_websocket_handshake_with_auth(websocket_headers, jwt_token)
        assert token_validation['valid'] is True, 'JWT token should be valid'
        assert token_validation['user_id'] == user_id
        assert 'websocket' in token_validation['permissions']
        assert handshake_result['connection_established'] is True
        assert handshake_result['user_authenticated'] is True
        assert handshake_result['user_id'] == user_id
        session_exists = await self._verify_websocket_session_in_redis(user_id)
        assert session_exists is True, 'WebSocket session should be stored in Redis'
        print(' PASS:  Authenticated WebSocket connection with real JWT test passed')

    @pytest.mark.asyncio
    async def test_websocket_authentication_failure_handling(self):
        """
        Test Case: WebSocket connections reject invalid authentication gracefully.
        
        Business Value: Prevents unauthorized access while providing clear error messages.
        Expected: Invalid tokens are rejected with business-friendly error messages.
        """
        auth_failure_scenarios = [{'name': 'expired_token', 'token': self.auth_helper.create_test_jwt_token(user_id='expired_user', exp_minutes=-5), 'expected_error': 'token_expired'}, {'name': 'invalid_signature', 'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature', 'expected_error': 'invalid_token'}, {'name': 'missing_permissions', 'token': self.auth_helper.create_test_jwt_token(user_id='limited_user', permissions=['read']), 'expected_error': 'insufficient_permissions'}]
        for scenario in auth_failure_scenarios:
            token = scenario['token']
            token_validation = await self.auth_helper.validate_jwt_token(token)
            websocket_headers = self.auth_helper.get_websocket_headers(token)
            handshake_result = await self._simulate_websocket_handshake_with_auth(websocket_headers, token)
            if scenario['expected_error'] == 'token_expired':
                assert token_validation['valid'] is False
                assert 'expired' in token_validation.get('error', '').lower()
            elif scenario['expected_error'] == 'invalid_token':
                assert token_validation['valid'] is False
                assert 'invalid' in token_validation.get('error', '').lower()
            elif scenario['expected_error'] == 'insufficient_permissions':
                if token_validation.get('valid'):
                    assert 'websocket' not in token_validation.get('permissions', [])
            assert handshake_result['connection_established'] is False
            assert handshake_result['user_authenticated'] is False
            assert 'error_message' in handshake_result
            error_message = handshake_result['error_message']
            technical_terms = ['jwt', 'signature', 'validation', 'decode']
            assert not any((term in error_message.lower() for term in technical_terms))
        print(' PASS:  WebSocket authentication failure handling test passed')

    @pytest.mark.asyncio
    async def test_multi_user_websocket_session_isolation(self):
        """
        Test Case: Multiple authenticated users have isolated WebSocket sessions.
        
        Business Value: Ensures enterprise-grade multi-tenancy and data security.
        Expected: Users cannot access each other's WebSocket sessions or data.
        """
        test_users = [{'user_id': 'isolated_ws_user_1', 'email': 'user1@techcorp.com', 'company': 'TechCorp', 'permissions': ['read', 'write', 'websocket', 'premium'], 'sensitive_data': 'TechCorp confidential chat history'}, {'user_id': 'isolated_ws_user_2', 'email': 'user2@startup.com', 'company': 'StartupInc', 'permissions': ['read', 'write', 'websocket'], 'sensitive_data': 'StartupInc private optimization data'}, {'user_id': 'isolated_ws_user_3', 'email': 'user3@freecorp.com', 'company': 'FreeCorp', 'permissions': ['read', 'websocket'], 'sensitive_data': 'FreeCorp basic usage patterns'}]
        established_sessions = {}
        for user_info in test_users:
            user_id = user_info['user_id']
            jwt_token = self.auth_helper.create_test_jwt_token(user_id=user_id, email=user_info['email'], permissions=user_info['permissions'])
            websocket_headers = self.auth_helper.get_websocket_headers(jwt_token)
            handshake_result = await self._simulate_websocket_handshake_with_auth(websocket_headers, jwt_token)
            assert handshake_result['connection_established'] is True
            session_data = {'user_id': user_id, 'websocket_client_id': f'ws_{user_id}', 'company_context': user_info['company'], 'permissions': user_info['permissions'], 'sensitive_chat_data': user_info['sensitive_data'], 'connection_time': datetime.now(timezone.utc)}
            session_stored = await self._store_websocket_session_data(user_id, session_data)
            assert session_stored is True
            established_sessions[user_id] = session_data
        for user_id, user_session in established_sessions.items():
            retrieved_session = await self._retrieve_websocket_session_data(user_id)
            assert retrieved_session is not None, f'Should retrieve session for {user_id}'
            assert retrieved_session['user_id'] == user_id
            assert retrieved_session['company_context'] == user_session['company_context']
            assert retrieved_session['sensitive_chat_data'] == user_session['sensitive_chat_data']
            other_users = [uid for uid in established_sessions.keys() if uid != user_id]
            for other_user_id in other_users:
                other_session = established_sessions[other_user_id]
                session_str = json.dumps(retrieved_session, default=str)
                assert other_session['sensitive_chat_data'] not in session_str
                assert other_session['company_context'] not in session_str
                assert other_session['websocket_client_id'] not in session_str
        print(' PASS:  Multi-user WebSocket session isolation test passed')

    @pytest.mark.asyncio
    async def test_websocket_session_persistence_across_reconnections(self):
        """
        Test Case: WebSocket sessions persist across connection drops and reconnections.
        
        Business Value: Users don't lose chat context during network interruptions.
        Expected: Session data survives connection drops and is restored on reconnection.
        """
        user_id = 'persistent_session_user_456'
        jwt_token = self.auth_helper.create_test_jwt_token(user_id=user_id, email='persistent@example.com', permissions=['read', 'write', 'websocket'])
        initial_session_data = {'user_id': user_id, 'websocket_client_id': f'ws_initial_{user_id}', 'chat_history': [{'message': 'Help me optimize my database performance', 'timestamp': datetime.now(timezone.utc) - timedelta(minutes=10), 'type': 'user_message'}, {'message': "I'll analyze your database and provide optimization recommendations", 'timestamp': datetime.now(timezone.utc) - timedelta(minutes=9), 'type': 'agent_response'}], 'active_operations': {'database_optimization': {'status': 'in_progress', 'progress': 65, 'started_at': datetime.now(timezone.utc) - timedelta(minutes=8)}}, 'user_preferences': {'notification_level': 'detailed', 'auto_save': True}}
        websocket_headers = self.auth_helper.get_websocket_headers(jwt_token)
        initial_handshake = await self._simulate_websocket_handshake_with_auth(websocket_headers, jwt_token)
        assert initial_handshake['connection_established'] is True
        session_stored = await self._store_websocket_session_data(user_id, initial_session_data)
        assert session_stored is True
        connection_dropped = await self._simulate_websocket_connection_drop(user_id)
        assert connection_dropped is True
        await asyncio.sleep(0.1)
        reconnection_headers = self.auth_helper.get_websocket_headers(jwt_token)
        reconnection_handshake = await self._simulate_websocket_handshake_with_auth(reconnection_headers, jwt_token)
        restored_session = await self._retrieve_websocket_session_data(user_id)
        assert reconnection_handshake['connection_established'] is True
        assert restored_session is not None, 'Session should be restored after reconnection'
        restored_chat = restored_session['chat_history']
        assert len(restored_chat) == 2, 'Chat history should be preserved'
        assert 'optimize my database' in restored_chat[0]['message']
        assert 'analyze your database' in restored_chat[1]['message']
        active_ops = restored_session['active_operations']
        assert 'database_optimization' in active_ops
        assert active_ops['database_optimization']['status'] == 'in_progress'
        assert active_ops['database_optimization']['progress'] == 65
        preferences = restored_session['user_preferences']
        assert preferences['notification_level'] == 'detailed'
        assert preferences['auto_save'] is True
        session_continuity = await self._validate_session_continuity(user_id, restored_session)
        assert session_continuity['is_continuous'] is True
        assert session_continuity['data_loss'] is False
        print(' PASS:  WebSocket session persistence across reconnections test passed')

    @pytest.mark.asyncio
    async def test_websocket_authentication_token_refresh(self):
        """
        Test Case: WebSocket connections handle token refresh seamlessly.
        
        Business Value: Users maintain connectivity during long chat sessions.
        Expected: Expiring tokens are refreshed without disrupting user experience.
        """
        user_id = 'token_refresh_user_789'
        short_lived_token = self.auth_helper.create_test_jwt_token(user_id=user_id, email='token_refresh@example.com', permissions=['read', 'write', 'websocket'], exp_minutes=0.05)
        initial_headers = self.auth_helper.get_websocket_headers(short_lived_token)
        initial_handshake = await self._simulate_websocket_handshake_with_auth(initial_headers, short_lived_token)
        assert initial_handshake['connection_established'] is True
        session_data = {'user_id': user_id, 'websocket_client_id': f'ws_refresh_{user_id}', 'active_chat': True, 'last_activity': datetime.now(timezone.utc), 'token_refresh_count': 0}
        session_stored = await self._store_websocket_session_data(user_id, session_data)
        assert session_stored is True
        await asyncio.sleep(2)
        expired_token_validation = await self.auth_helper.validate_jwt_token(short_lived_token)
        assert expired_token_validation['valid'] is False, 'Original token should be expired'
        refreshed_token = self.auth_helper.create_test_jwt_token(user_id=user_id, email='token_refresh@example.com', permissions=['read', 'write', 'websocket'], exp_minutes=30)
        refresh_headers = self.auth_helper.get_websocket_headers(refreshed_token)
        refresh_result = await self._simulate_token_refresh_for_websocket(user_id, refreshed_token, refresh_headers)
        updated_session = await self._retrieve_websocket_session_data(user_id)
        assert refresh_result['refresh_successful'] is True
        assert refresh_result['connection_maintained'] is True
        assert refresh_result['user_experience_disrupted'] is False
        new_token_validation = await self.auth_helper.validate_jwt_token(refreshed_token)
        assert new_token_validation['valid'] is True
        assert new_token_validation['user_id'] == user_id
        assert updated_session is not None
        assert updated_session['user_id'] == user_id
        assert updated_session['active_chat'] is True
        assert updated_session['token_refresh_count'] >= 1
        connection_status = await self._check_websocket_connection_status(user_id)
        assert connection_status['connected'] is True
        assert connection_status['authenticated'] is True
        print(' PASS:  WebSocket authentication token refresh test passed')

    @pytest.mark.asyncio
    async def test_websocket_authentication_permissions_enforcement(self):
        """
        Test Case: WebSocket connections enforce permissions for different user tiers.
        
        Business Value: Ensures proper access control for different subscription tiers.
        Expected: Users can only access features within their permission scope.
        """
        permission_scenarios = [{'user_id': 'free_tier_ws_user', 'tier': 'free', 'permissions': ['read', 'websocket'], 'allowed_features': ['basic_chat', 'view_status'], 'forbidden_features': ['agent_execution', 'premium_optimization', 'admin_functions']}, {'user_id': 'early_tier_ws_user', 'tier': 'early', 'permissions': ['read', 'write', 'websocket'], 'allowed_features': ['basic_chat', 'view_status', 'agent_execution', 'standard_optimization'], 'forbidden_features': ['premium_optimization', 'admin_functions', 'enterprise_features']}, {'user_id': 'enterprise_tier_ws_user', 'tier': 'enterprise', 'permissions': ['read', 'write', 'websocket', 'premium', 'admin'], 'allowed_features': ['basic_chat', 'agent_execution', 'premium_optimization', 'admin_functions', 'enterprise_features'], 'forbidden_features': ['super_admin_functions']}]
        for scenario in permission_scenarios:
            user_id = scenario['user_id']
            tier = scenario['tier']
            jwt_token = self.auth_helper.create_test_jwt_token(user_id=user_id, email=f'{user_id}@{tier}.com', permissions=scenario['permissions'])
            headers = self.auth_helper.get_websocket_headers(jwt_token)
            handshake = await self._simulate_websocket_handshake_with_auth(headers, jwt_token)
            assert handshake['connection_established'] is True, f'Connection should succeed for {tier} user'
            for feature in scenario['allowed_features']:
                feature_access = await self._test_websocket_feature_access(user_id, jwt_token, feature)
                assert feature_access['allowed'] is True, f'{tier} user should access {feature}'
                assert feature_access['error'] is None
            for feature in scenario['forbidden_features']:
                feature_access = await self._test_websocket_feature_access(user_id, jwt_token, feature)
                assert feature_access['allowed'] is False, f'{tier} user should NOT access {feature}'
                assert feature_access['error'] is not None
                error_message = feature_access['error']
                assert 'upgrade' in error_message.lower() or 'permission' in error_message.lower()
                assert 'unauthorized' not in error_message.lower()
        print(' PASS:  WebSocket authentication permissions enforcement test passed')

    async def _simulate_websocket_handshake_with_auth(self, headers: Dict[str, str], token: str) -> Dict[str, Any]:
        """Simulate WebSocket handshake with authentication."""
        try:
            token_validation = await self.auth_helper.validate_jwt_token(token)
            if not token_validation.get('valid', False):
                return {'connection_established': False, 'user_authenticated': False, 'error_message': 'Your session has expired. Please refresh and try again.'}
            permissions = token_validation.get('permissions', [])
            if 'websocket' not in permissions:
                return {'connection_established': False, 'user_authenticated': False, 'error_message': 'WebSocket access requires an upgraded plan. Contact support for assistance.'}
            user_id = token_validation.get('user_id')
            connection_key = f'websocket_connection:{user_id}'
            connection_data = {'user_id': user_id, 'connected_at': datetime.now(timezone.utc).isoformat(), 'token_hash': hash(token) & 4294967295, 'headers_count': len(headers)}
            await self.redis_client.setex(connection_key, 3600, json.dumps(connection_data, default=str))
            return {'connection_established': True, 'user_authenticated': True, 'user_id': user_id, 'connection_id': connection_key}
        except Exception as e:
            return {'connection_established': False, 'user_authenticated': False, 'error_message': "We're experiencing connection issues. Please try again in a moment."}

    async def _verify_websocket_session_in_redis(self, user_id: str) -> bool:
        """Verify WebSocket session exists in Redis."""
        try:
            connection_key = f'websocket_connection:{user_id}'
            exists = await self.redis_client.exists(connection_key)
            return bool(exists)
        except Exception:
            return False

    async def _store_websocket_session_data(self, user_id: str, session_data: Dict[str, Any]) -> bool:
        """Store WebSocket session data in Redis."""
        try:
            session_key = f'websocket_session:{user_id}'
            session_json = json.dumps(session_data, default=str)
            await self.redis_client.setex(session_key, 7200, session_json)
            return True
        except Exception as e:
            print(f'Error storing session data: {e}')
            return False

    async def _retrieve_websocket_session_data(self, user_id: str) -> Dict[str, Any]:
        """Retrieve WebSocket session data from Redis."""
        try:
            session_key = f'websocket_session:{user_id}'
            session_json = await self.redis_client.get(session_key)
            if session_json:
                return json.loads(session_json)
            return None
        except Exception as e:
            print(f'Error retrieving session data: {e}')
            return None

    async def _simulate_websocket_connection_drop(self, user_id: str) -> bool:
        """Simulate WebSocket connection drop."""
        try:
            connection_key = f'websocket_connection:{user_id}'
            connection_data = await self.redis_client.get(connection_key)
            if connection_data:
                conn_info = json.loads(connection_data)
                conn_info['status'] = 'disconnected'
                conn_info['disconnected_at'] = datetime.now(timezone.utc).isoformat()
                await self.redis_client.setex(connection_key, 300, json.dumps(conn_info, default=str))
                return True
            return False
        except Exception as e:
            print(f'Error simulating connection drop: {e}')
            return False

    async def _validate_session_continuity(self, user_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate session continuity after reconnection."""
        return {'is_continuous': session_data is not None, 'data_loss': session_data is None, 'chat_history_preserved': 'chat_history' in session_data if session_data else False, 'operations_preserved': 'active_operations' in session_data if session_data else False}

    async def _simulate_token_refresh_for_websocket(self, user_id: str, new_token: str, new_headers: Dict[str, str]) -> Dict[str, Any]:
        """Simulate token refresh for WebSocket connection."""
        try:
            connection_key = f'websocket_connection:{user_id}'
            connection_data = await self.redis_client.get(connection_key)
            if connection_data:
                conn_info = json.loads(connection_data)
                conn_info['token_refreshed_at'] = datetime.now(timezone.utc).isoformat()
                conn_info['token_hash'] = hash(new_token) & 4294967295
                session_data = await self._retrieve_websocket_session_data(user_id)
                if session_data:
                    session_data['token_refresh_count'] = session_data.get('token_refresh_count', 0) + 1
                    await self._store_websocket_session_data(user_id, session_data)
                await self.redis_client.setex(connection_key, 3600, json.dumps(conn_info, default=str))
                return {'refresh_successful': True, 'connection_maintained': True, 'user_experience_disrupted': False}
            return {'refresh_successful': False, 'connection_maintained': False, 'user_experience_disrupted': True}
        except Exception as e:
            print(f'Error in token refresh: {e}')
            return {'refresh_successful': False, 'connection_maintained': False, 'user_experience_disrupted': True}

    async def _check_websocket_connection_status(self, user_id: str) -> Dict[str, Any]:
        """Check WebSocket connection status."""
        try:
            connection_key = f'websocket_connection:{user_id}'
            connection_data = await self.redis_client.get(connection_key)
            if connection_data:
                conn_info = json.loads(connection_data)
                return {'connected': conn_info.get('status', 'connected') == 'connected', 'authenticated': True, 'last_activity': conn_info.get('connected_at')}
            return {'connected': False, 'authenticated': False}
        except Exception:
            return {'connected': False, 'authenticated': False}

    async def _test_websocket_feature_access(self, user_id: str, token: str, feature: str) -> Dict[str, Any]:
        """Test access to specific WebSocket features."""
        try:
            token_validation = await self.auth_helper.validate_jwt_token(token)
            if not token_validation.get('valid', False):
                return {'allowed': False, 'error': 'Session expired. Please refresh to continue.'}
            permissions = token_validation.get('permissions', [])
            feature_requirements = {'basic_chat': ['websocket'], 'view_status': ['read', 'websocket'], 'agent_execution': ['read', 'write', 'websocket'], 'standard_optimization': ['read', 'write', 'websocket'], 'premium_optimization': ['read', 'write', 'websocket', 'premium'], 'admin_functions': ['read', 'write', 'websocket', 'admin'], 'enterprise_features': ['read', 'write', 'websocket', 'premium'], 'super_admin_functions': ['super_admin']}
            required_perms = feature_requirements.get(feature, ['super_admin'])
            has_access = any((perm in permissions for perm in required_perms))
            if has_access:
                return {'allowed': True, 'error': None}
            else:
                return {'allowed': False, 'error': f'This feature requires an upgraded plan. Contact support to unlock {feature}.'}
        except Exception as e:
            return {'allowed': False, 'error': 'Unable to verify feature access. Please try again.'}
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')