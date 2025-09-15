"""
INTEGRATION TESTS - WebSocket User ID Validation Bug Reproduction

These integration tests validate WebSocket connections with problematic user ID patterns
that currently cause "Invalid user_id format" errors in real WebSocket scenarios.

Business Value Justification:
- Segment: Platform/Internal + All User Segments
- Business Goal: Bug Fix & User Experience Reliability  
- Value Impact: Prevents WebSocket connection failures for deployment/staging users
- Strategic Impact: Ensures consistent WebSocket connectivity across all environments

ROOT CAUSE: Missing regex pattern ^e2e-[a-zA-Z]+-[a-zA-Z0-9_-]+$ in ID validation

CRITICAL BUG CONTEXT:
- Issue: WebSocket error "Invalid user_id format: e2e-staging_pipeline" 
- Location: WebSocket authentication flow calling shared/types/core_types.py:336
- GitHub Issue: https://github.com/netra-systems/netra-apex/issues/105

INTEGRATION SCOPE: 
- Real WebSocket authentication components
- Real JWT token generation and validation
- Real ID validation logic (not mocked)
- Mock transport layer only (no actual network connections)

EXPECTED BEHAVIOR:
- Tests 1-2: MUST FAIL initially (proving bug exists in WebSocket flow)
- Tests 3-5: MUST PASS (proving regression protection)
"""
import pytest
import asyncio
import jwt
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.websocket_helpers import MockWebSocketConnection
from netra_backend.app.websocket_core.unified_websocket_auth import WebSocketAuthenticator
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService
from shared.types.core_types import ensure_user_id, UserID
from shared.jwt_secret_manager import get_unified_jwt_secret
from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

@pytest.mark.integration
class WebSocketUserIDValidationIntegrationTests(BaseIntegrationTest):
    """
    Integration tests for WebSocket user ID validation bug reproduction.
    
    Uses real authentication and ID validation components with mocked transport
    to isolate the specific user ID validation bug in WebSocket flows.
    """

    @pytest.fixture
    def jwt_secret(self) -> str:
        """Get JWT secret for test token generation."""
        return get_unified_jwt_secret()

    @pytest.fixture
    def failing_user_patterns(self) -> List[str]:
        """User ID patterns that currently fail WebSocket authentication."""
        return ['e2e-staging_pipeline', 'e2e-production_deploy', 'e2e-test_environment', 'e2e-dev_pipeline_123', 'e2e-staging_release-v2.1']

    @pytest.fixture
    def valid_user_patterns(self) -> List[str]:
        """User ID patterns that should continue working."""
        return ['test-user-123', 'mock-user-session', 'concurrent_user_0', str(uuid.uuid4()), 'ssot-test-user']

    def _create_jwt_token(self, user_id: str, jwt_secret: str) -> str:
        """Create a valid JWT token for the given user ID."""
        payload = {'user_id': user_id, 'email': f'{user_id}@example.com', 'iat': datetime.now(timezone.utc), 'exp': datetime.now(timezone.utc) + timedelta(hours=1), 'iss': 'netra-test-issuer'}
        return jwt.encode(payload, jwt_secret, algorithm='HS256')

    def _create_websocket_connection_message(self, user_id: str, token: str) -> Dict[str, Any]:
        """Create WebSocket connection message with authentication."""
        return {'type': 'connection', 'data': {'token': token, 'user_id': user_id, 'connection_id': f'conn_{user_id}_{int(time.time())}'}}

    @pytest.mark.asyncio
    async def test_websocket_connection_with_e2e_staging_user(self, jwt_secret):
        """
        TEST 1: CRITICAL - WebSocket connection with e2e-staging_pipeline user.
        
        This test MUST FAIL initially, proving the bug exists in the WebSocket flow.
        The error should occur during user ID validation, not JWT validation.
        
        EXPECTED: FAILURE (before fix) - "Invalid user_id format: e2e-staging_pipeline"
        """
        failing_user_id = 'e2e-staging_pipeline'
        token = self._create_jwt_token(failing_user_id, jwt_secret)
        decoded = jwt.decode(token, jwt_secret, algorithms=['HS256'])
        assert decoded['user_id'] == failing_user_id
        authenticator = WebSocketAuthenticator()
        connection_msg = self._create_websocket_connection_message(failing_user_id, token)
        mock_websocket = MockWebSocketConnection()
        with pytest.raises(ValueError, match='Invalid user_id format'):
            await authenticator.authenticate_connection(mock_websocket, connection_msg)
        pytest.fail(f"EXPECTED FAILURE: User ID '{failing_user_id}' should fail validation in WebSocket authentication but passed. Bug may be already fixed.")

    @pytest.mark.asyncio
    async def test_websocket_authentication_flow_various_formats(self, failing_user_patterns, jwt_secret):
        """
        TEST 2: Multiple deployment user patterns in WebSocket authentication.
        
        Tests various deployment-style user IDs that should work after fix.
        
        EXPECTED: FAILURE initially (proving bug scope), SUCCESS after fix
        """
        authenticator = WebSocketAuthenticator()
        for user_pattern in failing_user_patterns:
            token = self._create_jwt_token(user_pattern, jwt_secret)
            connection_msg = self._create_websocket_connection_message(user_pattern, token)
            mock_websocket = MockWebSocketConnection()
            try:
                auth_result = await authenticator.authenticate_connection(mock_websocket, connection_msg)
                assert auth_result is not None
                assert auth_result.get('user_id') == user_pattern
                assert auth_result.get('authenticated') is True
            except ValueError as e:
                if 'Invalid user_id format' in str(e):
                    pytest.fail(f"User pattern '{user_pattern}' should be valid for WebSocket authentication but failed with: {e}")
                else:
                    raise

    @pytest.mark.asyncio
    async def test_websocket_connection_rejection_invalid_formats(self):
        """
        TEST 3: Ensure invalid user ID formats are still properly rejected.
        
        This validates that our fix doesn't make WebSocket auth too permissive.
        
        EXPECTED: SUCCESS (always) - invalid patterns should be rejected
        """
        jwt_secret = get_unified_jwt_secret()
        authenticator = WebSocketAuthenticator()
        invalid_patterns = ['', '   ', 'e2e-', 'invalid@#$%', 'toolong' * 100]
        for invalid_pattern in invalid_patterns:
            token = self._create_jwt_token(invalid_pattern, jwt_secret)
            connection_msg = self._create_websocket_connection_message(invalid_pattern, token)
            mock_websocket = MockWebSocketConnection()
            with pytest.raises(ValueError, match='Invalid user_id format'):
                await authenticator.authenticate_connection(mock_websocket, connection_msg)

    @pytest.mark.asyncio
    async def test_websocket_thread_creation_valid_formats(self, valid_user_patterns, jwt_secret):
        """
        TEST 4: REGRESSION PREVENTION - Ensure existing user patterns still work.
        
        This validates that our fix doesn't break existing WebSocket functionality.
        
        EXPECTED: SUCCESS (always)
        """
        authenticator = WebSocketAuthenticator()
        for user_pattern in valid_user_patterns:
            token = self._create_jwt_token(user_pattern, jwt_secret)
            connection_msg = self._create_websocket_connection_message(user_pattern, token)
            mock_websocket = MockWebSocketConnection()
            try:
                auth_result = await authenticator.authenticate_connection(mock_websocket, connection_msg)
                assert auth_result is not None
                assert auth_result.get('user_id') == user_pattern
                assert auth_result.get('authenticated') is True
            except Exception as e:
                pytest.fail(f"REGRESSION: Previously valid user pattern '{user_pattern}' now fails WebSocket authentication: {e}")

    @pytest.mark.asyncio
    async def test_websocket_manager_user_id_handling(self, failing_user_patterns, jwt_secret):
        """
        TEST 5: Test WebSocket manager handling of problematic user IDs.
        
        This tests the complete WebSocket manager flow with the failing user patterns.
        
        EXPECTED: SUCCESS after fix
        """
        with patch('netra_backend.app.websocket_core.unified_manager.get_database_manager'):
            manager = get_websocket_manager(user_context=getattr(self, 'user_context', None))
            for user_pattern in failing_user_patterns:
                token = self._create_jwt_token(user_pattern, jwt_secret)
                mock_websocket = MockWebSocketConnection()
                connection_data = {'user_id': user_pattern, 'token': token, 'connection_id': f'conn_{user_pattern}_{int(time.time())}'}
                try:
                    result = await manager.handle_connection(mock_websocket, connection_data)
                    assert result is not None
                except ValueError as e:
                    if 'Invalid user_id format' in str(e):
                        pytest.fail(f"WebSocket manager should handle user pattern '{user_pattern}' after fix but failed with: {e}")
                    else:
                        raise

    @pytest.mark.asyncio
    async def test_websocket_authentication_performance_with_deployment_users(self, failing_user_patterns, jwt_secret):
        """
        TEST 6: Performance test for WebSocket authentication with deployment users.
        
        Ensures the fix doesn't significantly impact authentication performance.
        
        EXPECTED: SUCCESS - reasonable performance maintained
        """
        import time
        authenticator = WebSocketAuthenticator()
        test_data = []
        for user_pattern in failing_user_patterns * 10:
            token = self._create_jwt_token(user_pattern, jwt_secret)
            msg = self._create_websocket_connection_message(user_pattern, token)
            test_data.append((user_pattern, token, msg))
        start_time = time.time()
        for user_pattern, token, connection_msg in test_data:
            mock_websocket = MockWebSocketConnection()
            try:
                await authenticator.authenticate_connection(mock_websocket, connection_msg)
            except ValueError:
                pass
        end_time = time.time()
        duration = end_time - start_time
        assert duration < 1.0, f'WebSocket authentication performance degraded: 50 authentications took {duration:.3f}s, should be under 1.0s'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')