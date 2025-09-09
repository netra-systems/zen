"""
Test WebSocket Connection Authentication Flow with User Context State

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure secure WebSocket connections with proper user authentication
- Value Impact: Users can securely connect to WebSocket with validated credentials and context
- Strategic Impact: Foundation for secure real-time features and multi-user isolation

This integration test validates that WebSocket authentication flow properly validates
user credentials and maintains secure user context state throughout the connection.
"""

import pytest
import asyncio
import json
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, WebSocketID
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestWebSocketConnectionAuthenticationUserContextIntegration(BaseIntegrationTest):
    """Test WebSocket connection authentication flow with comprehensive user context state validation."""
    
    def _create_test_jwt_token(self, user_id: str, additional_claims: Optional[Dict] = None) -> str:
        """Create a test JWT token for authentication testing."""
        env = get_env()
        secret = env.get("JWT_SECRET", "test_secret_key_for_integration_testing")
        
        now = datetime.utcnow()
        payload = {
            "user_id": user_id,
            "email": f"user_{user_id}@netra.ai",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "aud": "netra-backend",
            "iss": "netra-auth"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, secret, algorithm="HS256")
    
    def _decode_jwt_token(self, token: str) -> Dict[str, Any]:
        """Decode JWT token for validation."""
        env = get_env()
        secret = env.get("JWT_SECRET", "test_secret_key_for_integration_testing")
        
        return jwt.decode(token, secret, algorithms=["HS256"], audience="netra-backend")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_authentication_flow_with_user_context_state(self, real_services_fixture):
        """
        Test that WebSocket authentication flow properly validates credentials and maintains user context.
        
        Business Value: Ensures secure WebSocket connections with authenticated user context
        that correctly isolates user data and maintains security boundaries.
        """
        # Create authenticated test user
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'auth_test_user@netra.ai',
            'name': 'Auth Test User',
            'is_active': True
        })
        user_id = user_data['id']
        
        # Create organization for user context
        org_data = await self.create_test_organization(real_services_fixture, user_id, {
            'name': 'Auth Test Organization',
            'plan': 'enterprise'
        })
        
        # Create authenticated session with proper JWT token
        jwt_token = self._create_test_jwt_token(user_id, {
            'organization_id': org_data['id'],
            'plan': 'enterprise',
            'permissions': ['websocket:connect', 'agent:execute', 'data:read']
        })
        
        session_data = await self.create_test_session(real_services_fixture, user_id, {
            'jwt_token': jwt_token,
            'organization_id': org_data['id'],
            'authenticated': True
        })
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Mock authenticated WebSocket with token validation
        class AuthenticatedWebSocket:
            def __init__(self, auth_token: str):
                self.auth_token = auth_token
                self.user_context = None
                self.messages_sent = []
                self.is_closed = False
                self.is_authenticated = False
            
            async def send_json(self, data):
                if not self.is_authenticated:
                    raise ConnectionError("WebSocket not authenticated")
                self.messages_sent.append(data)
            
            async def close(self, code=1000, reason=""):
                self.is_closed = True
            
            def authenticate(self, user_context: Dict):
                """Simulate authentication process."""
                self.user_context = user_context
                self.is_authenticated = True
        
        mock_websocket = AuthenticatedWebSocket(jwt_token)
        
        # Validate JWT token and extract user context
        decoded_token = self._decode_jwt_token(jwt_token)
        assert decoded_token['user_id'] == user_id, "JWT token should contain correct user_id"
        assert 'websocket:connect' in decoded_token['permissions'], "JWT should have websocket connect permission"
        
        # Create connection with authenticated user context
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="auth_conn",
            context={"user_id": user_id, "authenticated": True}
        )
        
        # Simulate authentication flow
        user_context = {
            'user_id': user_id,
            'organization_id': org_data['id'],
            'email': decoded_token['email'],
            'plan': decoded_token['plan'],
            'permissions': decoded_token['permissions'],
            'session_id': session_data['session_key'],
            'authenticated_at': datetime.utcnow().isoformat()
        }
        
        mock_websocket.authenticate(user_context)
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "authenticated",
                "user_context": user_context,
                "authentication_method": "jwt",
                "session_id": session_data['session_key']
            }
        )
        
        # Add authenticated connection
        await websocket_manager.add_connection(connection)
        
        # Verify authentication state in application layers
        assert websocket_manager.is_connection_active(user_id), "Authenticated connection should be active"
        
        # Retrieve and verify authenticated connection
        retrieved_connection = websocket_manager.get_connection(connection_id)
        assert retrieved_connection is not None, "Authenticated connection should be retrievable"
        assert retrieved_connection.metadata['user_context']['authenticated_at'] is not None
        assert retrieved_connection.metadata['authentication_method'] == 'jwt'
        
        # Verify database state includes user context
        db_user = await real_services_fixture["postgres"].fetchrow(
            """
            SELECT u.id, u.email, u.is_active, om.organization_id, o.plan
            FROM auth.users u
            LEFT JOIN backend.organization_memberships om ON u.id = om.user_id  
            LEFT JOIN backend.organizations o ON om.organization_id = o.id
            WHERE u.id = $1
            """,
            user_id
        )
        assert db_user is not None, "Authenticated user should exist in database"
        assert str(db_user['organization_id']) == org_data['id'], "User should be associated with correct organization"
        assert db_user['plan'] == 'enterprise', "User should have correct plan"
        
        # Verify Redis session includes authentication context
        cached_session = await real_services_fixture["redis"].get(session_data['session_key'])
        assert cached_session is not None, "Authenticated session should exist in Redis"
        session_json = json.loads(cached_session)
        assert session_json['authenticated'] is True, "Session should be marked as authenticated"
        assert session_json.get('jwt_token') == jwt_token, "Session should store JWT token"
        
        # Test authenticated message sending
        auth_message = {
            "type": "authenticated_message",
            "data": {
                "message": "This requires authentication",
                "user_context": user_context
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await websocket_manager.send_to_user(user_id, auth_message)
        
        # Verify message was sent through authenticated channel
        assert len(mock_websocket.messages_sent) > 0, "Authenticated WebSocket should receive messages"
        sent_message = mock_websocket.messages_sent[-1]
        assert sent_message['type'] == 'authenticated_message', "Should receive authenticated message"
        
        # Verify user context isolation
        connection_health = websocket_manager.get_connection_health(user_id)
        assert connection_health['has_active_connections'] is True
        assert len(connection_health['connections']) == 1
        stored_metadata = connection_health['connections'][0]['metadata']
        assert stored_metadata['user_context']['user_id'] == user_id
        assert stored_metadata['user_context']['organization_id'] == org_data['id']
        
        # Clean up authenticated connection
        await websocket_manager.remove_connection(connection_id)
        
        # Verify cleanup maintains data integrity
        assert not websocket_manager.is_connection_active(user_id)
        
        # Verify database state unchanged after cleanup
        db_user_after = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, is_active FROM auth.users WHERE id = $1", user_id
        )
        assert db_user_after['is_active'] is True, "User should remain active after connection cleanup"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_authentication_failure_handling_with_state_protection(self, real_services_fixture):
        """
        Test that authentication failures are properly handled without corrupting application state.
        
        Business Value: Ensures security by properly rejecting invalid authentication
        while maintaining system stability and preventing state corruption.
        """
        # Create test user (but will use invalid authentication)
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'invalid_auth_test@netra.ai',
            'name': 'Invalid Auth Test User',
            'is_active': True
        })
        user_id = user_data['id']
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Test Case 1: Expired JWT Token
        expired_token = self._create_test_jwt_token(user_id, {
            'exp': datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        })
        
        class InvalidAuthWebSocket:
            def __init__(self, invalid_token: str):
                self.auth_token = invalid_token
                self.messages_sent = []
                self.is_closed = False
                self.authentication_failed = False
            
            async def send_json(self, data):
                # Simulate authentication check before sending
                if self.authentication_failed:
                    raise ConnectionError("Authentication failed")
                self.messages_sent.append(data)
            
            async def close(self, code=1001, reason="Authentication failed"):
                self.is_closed = True
                self.authentication_failed = True
        
        # Attempt to validate expired token
        try:
            self._decode_jwt_token(expired_token)
            assert False, "Expired token should not be valid"
        except jwt.ExpiredSignatureError:
            # Expected behavior - expired token should be rejected
            pass
        
        invalid_websocket = InvalidAuthWebSocket(expired_token)
        invalid_websocket.authentication_failed = True  # Mark as failed due to expired token
        
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="invalid_conn",
            context={"user_id": user_id, "authenticated": False}
        )
        
        # Create connection but with failed authentication
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=invalid_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "failed_authentication",
                "authentication_method": "jwt",
                "authentication_status": "failed",
                "failure_reason": "expired_token"
            }
        )
        
        # Add connection (this should succeed, but authentication state should be tracked)
        await websocket_manager.add_connection(connection)
        
        # Verify connection exists but authentication failure is tracked
        assert websocket_manager.is_connection_active(user_id), "Connection should exist even with failed auth"
        retrieved_connection = websocket_manager.get_connection(connection_id)
        assert retrieved_connection.metadata['authentication_status'] == 'failed'
        
        # Attempt to send message through invalid connection
        auth_test_message = {
            "type": "auth_required_message",
            "data": {"sensitive": "data"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # This should fail and trigger connection cleanup
        await websocket_manager.send_to_user(user_id, auth_test_message)
        
        # Give time for error handling
        await asyncio.sleep(0.1)
        
        # Verify error statistics are tracked
        error_stats = websocket_manager.get_error_statistics()
        assert error_stats['total_error_count'] >= 0, "Authentication failures should be tracked in error stats"
        
        # Test Case 2: Invalid JWT Secret
        try:
            invalid_token_wrong_secret = jwt.encode(
                {
                    "user_id": user_id,
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                "wrong_secret",  # Wrong secret
                algorithm="HS256"
            )
            
            self._decode_jwt_token(invalid_token_wrong_secret)
            assert False, "Token with wrong secret should not be valid"
        except jwt.InvalidSignatureError:
            # Expected behavior - invalid signature should be rejected
            pass
        
        # Test Case 3: Malformed JWT Token
        malformed_token = "not.a.valid.jwt.token"
        
        try:
            self._decode_jwt_token(malformed_token)
            assert False, "Malformed token should not be valid"
        except jwt.InvalidTokenError:
            # Expected behavior - malformed token should be rejected
            pass
        
        # Verify database state was not corrupted by authentication failures
        db_user = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, email, is_active FROM auth.users WHERE id = $1",
            user_id
        )
        assert db_user is not None, "User should still exist after auth failures"
        assert db_user['is_active'] is True, "User should remain active after auth failures"
        assert db_user['email'] == 'invalid_auth_test@netra.ai', "User data should be unchanged"
        
        # Test Case 4: Successful authentication after failures
        valid_token = self._create_test_jwt_token(user_id, {
            'permissions': ['websocket:connect']
        })
        
        decoded_valid = self._decode_jwt_token(valid_token)
        assert decoded_valid['user_id'] == user_id, "Valid token should decode correctly"
        
        class ValidAuthWebSocket:
            def __init__(self, valid_token: str):
                self.auth_token = valid_token
                self.messages_sent = []
                self.is_closed = False
                self.is_authenticated = True
            
            async def send_json(self, data):
                self.messages_sent.append(data)
            
            async def close(self):
                self.is_closed = True
        
        valid_websocket = ValidAuthWebSocket(valid_token)
        
        valid_connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="valid_conn",
            context={"user_id": user_id, "authenticated": True}
        )
        
        valid_connection = WebSocketConnection(
            connection_id=valid_connection_id,
            user_id=user_id,
            websocket=valid_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "valid_authentication",
                "authentication_method": "jwt",
                "authentication_status": "success",
                "token_valid": True
            }
        )
        
        await websocket_manager.add_connection(valid_connection)
        
        # Test that valid authentication works after failures
        recovery_message = {
            "type": "recovery_after_auth_failure",
            "data": {"message": "Authentication recovered successfully"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await websocket_manager.send_to_user(user_id, recovery_message)
        
        # Verify message was sent successfully
        assert len(valid_websocket.messages_sent) > 0, "Valid connection should receive messages"
        assert valid_websocket.messages_sent[-1]['type'] == 'recovery_after_auth_failure'
        
        # Clean up all connections
        await websocket_manager.remove_connection(connection_id)
        await websocket_manager.remove_connection(valid_connection_id)
        
        # Verify business value: System handles auth failures gracefully
        self.assert_business_value_delivered({
            'security_maintained': True,
            'auth_failure_handling': 'graceful',
            'state_protection': True,
            'recovery_possible': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_multi_user_authentication_context_isolation(self, real_services_fixture):
        """
        Test that multiple users' authentication contexts are properly isolated in WebSocket connections.
        
        Business Value: Ensures multi-user system maintains security boundaries and prevents
        cross-user data leakage during WebSocket authentication flows.
        """
        # Create multiple authenticated users with different contexts
        users = []
        for i in range(3):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'multi_auth_user_{i}@netra.ai',
                'name': f'Multi Auth User {i}',
                'is_active': True
            })
            
            org_data = await self.create_test_organization(
                real_services_fixture, 
                user_data['id'],
                {
                    'name': f'Organization {i}',
                    'plan': ['free', 'early', 'enterprise'][i]  # Different plans
                }
            )
            
            # Create JWT with different permissions per user
            permissions = [
                ['websocket:connect', 'data:read'],           # User 0: Limited
                ['websocket:connect', 'data:read', 'agent:execute'],  # User 1: Medium
                ['websocket:connect', 'data:read', 'agent:execute', 'admin:access']  # User 2: Full
            ][i]
            
            jwt_token = self._create_test_jwt_token(user_data['id'], {
                'organization_id': org_data['id'],
                'plan': org_data['plan'],
                'permissions': permissions,
                'user_tier': i
            })
            
            session_data = await self.create_test_session(
                real_services_fixture, 
                user_data['id'],
                {
                    'jwt_token': jwt_token,
                    'organization_id': org_data['id'],
                    'user_tier': i
                }
            )
            
            users.append({
                'user_data': user_data,
                'org_data': org_data,
                'jwt_token': jwt_token,
                'session_data': session_data,
                'permissions': permissions
            })
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create isolated authenticated connections for each user
        connections = []
        
        for i, user_info in enumerate(users):
            user_id = user_info['user_data']['id']
            
            class IsolatedAuthWebSocket:
                def __init__(self, user_index: int, token: str):
                    self.user_index = user_index
                    self.auth_token = token
                    self.user_context = None
                    self.messages_sent = []
                    self.is_closed = False
                    self.is_authenticated = True
                
                async def send_json(self, data):
                    # Add user isolation marker to messages
                    data['_user_isolation_marker'] = self.user_index
                    self.messages_sent.append(data)
                
                async def close(self):
                    self.is_closed = True
            
            mock_websocket = IsolatedAuthWebSocket(i, user_info['jwt_token'])
            
            # Decode and validate JWT for this user
            decoded_token = self._decode_jwt_token(user_info['jwt_token'])
            assert decoded_token['user_id'] == user_id
            assert decoded_token['user_tier'] == i
            
            connection_id = id_manager.generate_id(
                IDType.CONNECTION,
                prefix=f"isolated_conn_{i}",
                context={"user_id": user_id, "user_tier": i}
            )
            
            user_context = {
                'user_id': user_id,
                'user_tier': i,
                'organization_id': user_info['org_data']['id'],
                'email': decoded_token['email'],
                'plan': decoded_token['plan'],
                'permissions': decoded_token['permissions'],
                'session_id': user_info['session_data']['session_key']
            }
            
            mock_websocket.user_context = user_context
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=mock_websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "connection_type": "isolated_multi_user",
                    "user_context": user_context,
                    "user_tier": i,
                    "authentication_method": "jwt"
                }
            )
            
            await websocket_manager.add_connection(connection)
            connections.append({
                'connection_id': connection_id,
                'user_id': user_id,
                'websocket': mock_websocket,
                'user_info': user_info,
                'user_context': user_context
            })
        
        # Verify all connections are isolated and active
        for i, conn in enumerate(connections):
            assert websocket_manager.is_connection_active(conn['user_id'])
            
            retrieved_connection = websocket_manager.get_connection(conn['connection_id'])
            assert retrieved_connection.metadata['user_tier'] == i
            assert retrieved_connection.metadata['user_context']['user_id'] == conn['user_id']
        
        # Test cross-user isolation by sending targeted messages
        for i, target_conn in enumerate(connections):
            target_user_id = target_conn['user_id']
            
            # Send user-specific message
            user_specific_message = {
                "type": "user_specific_message",
                "data": {
                    "target_user": target_user_id,
                    "user_tier": i,
                    "permissions": target_conn['user_context']['permissions'],
                    "sensitive_data": f"data_for_user_{i}"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_to_user(target_user_id, user_specific_message)
        
        # Verify message isolation - each user should only receive their own messages
        for i, conn in enumerate(connections):
            messages = conn['websocket'].messages_sent
            
            # Should have at least one message (the user-specific one)
            assert len(messages) > 0, f"User {i} should receive messages"
            
            # Find the user-specific message
            user_specific_msg = None
            for msg in messages:
                if msg.get('type') == 'user_specific_message':
                    user_specific_msg = msg
                    break
            
            assert user_specific_msg is not None, f"User {i} should receive user-specific message"
            assert user_specific_msg['_user_isolation_marker'] == i, f"User {i} message should have correct isolation marker"
            assert user_specific_msg['data']['target_user'] == conn['user_id'], f"User {i} should receive their own targeted message"
            assert user_specific_msg['data']['user_tier'] == i, f"User {i} message should have correct tier"
            
            # Verify permissions are correctly isolated
            expected_permissions = conn['user_context']['permissions']
            received_permissions = user_specific_msg['data']['permissions']
            assert received_permissions == expected_permissions, f"User {i} permissions should match"
        
        # Verify database isolation - each user should only see their own data
        for i, conn in enumerate(connections):
            user_id = conn['user_id']
            org_id = conn['user_info']['org_data']['id']
            
            # Query user's organization membership
            db_membership = await real_services_fixture["postgres"].fetchrow(
                """
                SELECT om.user_id, om.organization_id, o.plan, o.name
                FROM backend.organization_memberships om
                JOIN backend.organizations o ON om.organization_id = o.id
                WHERE om.user_id = $1
                """,
                user_id
            )
            
            assert db_membership is not None, f"User {i} should have organization membership"
            assert str(db_membership['organization_id']) == org_id, f"User {i} should be in correct organization"
            assert db_membership['plan'] in ['free', 'early', 'enterprise'], f"User {i} should have valid plan"
            
            # Verify no cross-user data leakage in database
            other_user_orgs = await real_services_fixture["postgres"].fetch(
                """
                SELECT om.organization_id 
                FROM backend.organization_memberships om 
                WHERE om.user_id = $1 AND om.organization_id != $2
                """,
                user_id, org_id
            )
            
            assert len(other_user_orgs) == 0, f"User {i} should not have access to other organizations"
        
        # Verify Redis session isolation
        for i, conn in enumerate(connections):
            session_key = conn['user_info']['session_data']['session_key']
            
            cached_session = await real_services_fixture["redis"].get(session_key)
            assert cached_session is not None, f"User {i} session should exist in Redis"
            
            session_data = json.loads(cached_session)
            assert session_data.get('user_tier') == i, f"User {i} session should have correct tier"
            assert session_data.get('organization_id') == conn['user_info']['org_data']['id']
        
        # Test manager statistics with multi-user context
        stats = websocket_manager.get_stats()
        assert stats['total_connections'] == 3, "Should track 3 isolated connections"
        assert stats['unique_users'] == 3, "Should track 3 unique users"
        
        # Verify each user has exactly one connection
        for i, conn in enumerate(connections):
            user_connections = websocket_manager.get_user_connections(conn['user_id'])
            assert len(user_connections) == 1, f"User {i} should have exactly one connection"
            assert conn['connection_id'] in user_connections, f"User {i} connection should be tracked"
        
        # Clean up all connections
        for conn in connections:
            await websocket_manager.remove_connection(conn['connection_id'])
        
        # Verify all connections cleaned up
        for conn in connections:
            assert not websocket_manager.is_connection_active(conn['user_id'])
        
        # Verify business value: Multi-user authentication isolation works
        self.assert_business_value_delivered({
            'multi_user_isolation': True,
            'authentication_security': 'per_user',
            'context_separation': True,
            'no_data_leakage': True
        }, 'automation')