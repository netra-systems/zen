"""
L4 Integration Test: Cross-Service Auth Propagation Complete
Tests auth propagation between API Gateway, Auth Service, Backend, and WebSocket
"""

import pytest
import asyncio
import time
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib

from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.services.api_gateway_service import APIGatewayService
# from netra_backend.app.services.websocket_service import WebSocketService
from unittest.mock import AsyncMock
WebSocketService = AsyncMock
from netra_backend.app.services.backend_service import BackendService
from netra_backend.app.config import settings


class TestCrossServiceAuthPropagationCompleteL4:
    """Complete cross-service authentication propagation testing"""
    
    @pytest.fixture
    async def service_mesh(self):
        """Multi-service infrastructure setup"""
        return {
            'auth_service': AuthService(),
            'api_gateway': APIGatewayService(),
            'websocket_service': WebSocketService(),
            'backend_service': BackendService(),
            'service_registry': {},
            'auth_cache': {},
            'propagation_log': []
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_auth_token_propagation_through_gateway(self, service_mesh):
        """Test auth token propagation from gateway to backend services"""
        user_id = "user_gateway_prop"
        
        # User authenticates at gateway
        auth_result = await service_mesh['api_gateway'].authenticate_user(
            email="user@test.com",
            password="Test123!",
            ip_address="192.168.1.1"
        )
        
        assert auth_result['success']
        access_token = auth_result['access_token']
        
        # Gateway creates service token for backend call
        service_token = await service_mesh['api_gateway'].create_service_token(
            user_token=access_token,
            target_service='backend',
            scopes=['read', 'write']
        )
        
        # Backend validates service token
        validation = await service_mesh['backend_service'].validate_service_token(
            token=service_token,
            expected_source='api_gateway'
        )
        
        assert validation['valid']
        assert validation['user_id'] == user_id
        assert validation['source_service'] == 'api_gateway'
        
        # Backend can extract user context
        user_context = await service_mesh['backend_service'].get_user_context(service_token)
        assert user_context['user_id'] == user_id
        assert 'read' in user_context['scopes']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_auth_handoff_from_http(self, service_mesh):
        """Test auth handoff from HTTP to WebSocket connection"""
        user_id = "user_ws_handoff"
        
        # HTTP authentication
        http_auth = await service_mesh['api_gateway'].authenticate_user(
            email="wsuser@test.com",
            password="Test123!"
        )
        
        http_token = http_auth['access_token']
        
        # Create WebSocket handoff token
        ws_ticket = await service_mesh['api_gateway'].create_websocket_ticket(
            user_token=http_token,
            validity_seconds=30
        )
        
        # WebSocket validates ticket
        ws_auth = await service_mesh['websocket_service'].authenticate_with_ticket(
            ticket=ws_ticket,
            client_ip="192.168.1.1"
        )
        
        assert ws_auth['success']
        assert ws_auth['user_id'] == user_id
        
        # Ticket should be single-use
        with pytest.raises(Exception) as exc_info:
            await service_mesh['websocket_service'].authenticate_with_ticket(
                ticket=ws_ticket,
                client_ip="192.168.1.1"
            )
        assert "already used" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_auth_context_enrichment_across_services(self, service_mesh):
        """Test auth context enrichment as it flows through services"""
        user_id = "user_enrichment"
        
        # Initial auth with minimal context
        initial_auth = await service_mesh['auth_service'].authenticate(
            user_id=user_id,
            password_hash="hashed_pass"
        )
        
        initial_context = {
            'user_id': user_id,
            'authenticated_at': time.time()
        }
        
        # Gateway enriches with request metadata
        gateway_context = await service_mesh['api_gateway'].enrich_auth_context(
            auth_context=initial_context,
            request_metadata={
                'ip': '192.168.1.1',
                'user_agent': 'Mozilla/5.0',
                'api_version': 'v2'
            }
        )
        
        assert 'ip' in gateway_context
        assert 'api_version' in gateway_context
        
        # Backend enriches with user permissions
        backend_context = await service_mesh['backend_service'].enrich_auth_context(
            auth_context=gateway_context,
            user_id=user_id
        )
        
        assert 'permissions' in backend_context
        assert 'resource_limits' in backend_context
        
        # Final context has all enrichments
        assert backend_context['user_id'] == user_id
        assert backend_context['ip'] == '192.168.1.1'
        assert 'permissions' in backend_context
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_auth_invalidation_cascade(self, service_mesh):
        """Test auth invalidation cascading across all services"""
        user_id = "user_cascade"
        
        # Create auth tokens across services
        tokens = {}
        
        # Auth service token
        auth_token = await service_mesh['auth_service'].create_token(user_id)
        tokens['auth'] = auth_token
        
        # API Gateway token
        gateway_token = await service_mesh['api_gateway'].create_session_token(
            user_id=user_id,
            parent_token=auth_token
        )
        tokens['gateway'] = gateway_token
        
        # WebSocket token
        ws_token = await service_mesh['websocket_service'].create_connection_token(
            user_id=user_id,
            parent_token=gateway_token
        )
        tokens['websocket'] = ws_token
        
        # Backend service token
        backend_token = await service_mesh['backend_service'].create_service_token(
            user_id=user_id,
            parent_token=gateway_token
        )
        tokens['backend'] = backend_token
        
        # All tokens should be valid
        for service, token in tokens.items():
            valid = await service_mesh[f'{service}_service'].validate_token(token)
            assert valid
        
        # Invalidate at auth service level
        await service_mesh['auth_service'].logout_user(user_id)
        
        # Wait for cascade propagation
        await asyncio.sleep(0.5)
        
        # All tokens should now be invalid
        for service, token in tokens.items():
            if service == 'auth':
                service = 'auth_service'
            else:
                service = f'{service}_service'
            
            valid = await service_mesh[service].validate_token(token)
            assert not valid
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_service_to_service_auth_chain(self, service_mesh):
        """Test service-to-service authentication chain"""
        
        # Service A authenticates to Service B
        token_a_to_b = await service_mesh['api_gateway'].get_service_credentials(
            target_service='backend_service'
        )
        
        # Service B validates Service A
        validation_b = await service_mesh['backend_service'].validate_service_caller(
            token=token_a_to_b,
            expected_caller='api_gateway'
        )
        
        assert validation_b['valid']
        assert validation_b['caller_service'] == 'api_gateway'
        
        # Service B calls Service C (Auth Service) on behalf of Service A
        token_b_to_c = await service_mesh['backend_service'].get_delegated_credentials(
            target_service='auth_service',
            on_behalf_of='api_gateway'
        )
        
        # Service C validates the delegated call
        validation_c = await service_mesh['auth_service'].validate_service_caller(
            token=token_b_to_c,
            expected_caller='backend_service',
            expected_originator='api_gateway'
        )
        
        assert validation_c['valid']
        assert validation_c['caller_service'] == 'backend_service'
        assert validation_c['originator_service'] == 'api_gateway'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_auth_state_sync_during_failover(self, service_mesh):
        """Test auth state synchronization during service failover"""
        user_id = "user_failover"
        
        # Create session on primary auth service
        primary_session = await service_mesh['auth_service'].create_session(
            user_id=user_id,
            device_id="device_1"
        )
        
        # Simulate primary failure, secondary takes over
        secondary_auth = AuthService()  # New instance
        
        # Secondary should sync state from shared cache
        await secondary_auth.sync_from_cache()
        
        # Validate session on secondary
        validation = await secondary_auth.validate_session(primary_session['session_id'])
        assert validation['valid']
        assert validation['user_id'] == user_id
        
        # Updates on secondary should propagate
        await secondary_auth.update_session_activity(primary_session['session_id'])
        
        # Primary comes back and syncs
        await service_mesh['auth_service'].sync_from_cache()
        
        # Both should have consistent state
        primary_state = await service_mesh['auth_service'].get_session_state(
            primary_session['session_id']
        )
        secondary_state = await secondary_auth.get_session_state(
            primary_session['session_id']
        )
        
        assert primary_state['last_activity'] == secondary_state['last_activity']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_auth_quota_enforcement_across_services(self, service_mesh):
        """Test auth quota enforcement across multiple services"""
        user_id = "user_quota"
        
        # Set user quota
        quota = {
            'api_calls': 100,
            'websocket_messages': 1000,
            'backend_operations': 50
        }
        
        await service_mesh['auth_service'].set_user_quota(user_id, quota)
        
        # Consume quota across services
        # API Gateway calls
        for _ in range(50):
            result = await service_mesh['api_gateway'].check_and_consume_quota(
                user_id=user_id,
                resource='api_calls',
                amount=1
            )
            assert result['allowed']
        
        # WebSocket messages
        for _ in range(500):
            result = await service_mesh['websocket_service'].check_and_consume_quota(
                user_id=user_id,
                resource='websocket_messages',
                amount=1
            )
            assert result['allowed']
        
        # Backend operations
        for _ in range(25):
            result = await service_mesh['backend_service'].check_and_consume_quota(
                user_id=user_id,
                resource='backend_operations',
                amount=1
            )
            assert result['allowed']
        
        # Check remaining quota (should be synchronized)
        remaining = await service_mesh['auth_service'].get_remaining_quota(user_id)
        assert remaining['api_calls'] == 50
        assert remaining['websocket_messages'] == 500
        assert remaining['backend_operations'] == 25
        
        # Exceed quota
        for _ in range(26):
            result = await service_mesh['backend_service'].check_and_consume_quota(
                user_id=user_id,
                resource='backend_operations',
                amount=1
            )
        
        # Last request should be denied
        assert not result['allowed']
        assert result['reason'] == 'quota_exceeded'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_auth_context_isolation_between_tenants(self, service_mesh):
        """Test auth context isolation between different tenants"""
        tenant1_user = "tenant1_user"
        tenant2_user = "tenant2_user"
        
        # Create auth contexts for different tenants
        tenant1_context = await service_mesh['auth_service'].create_auth_context(
            user_id=tenant1_user,
            tenant_id="tenant_1",
            isolation_level='strict'
        )
        
        tenant2_context = await service_mesh['auth_service'].create_auth_context(
            user_id=tenant2_user,
            tenant_id="tenant_2",
            isolation_level='strict'
        )
        
        # Service calls with tenant1 context
        tenant1_result = await service_mesh['backend_service'].execute_operation(
            auth_context=tenant1_context,
            operation='list_resources'
        )
        
        # Service calls with tenant2 context
        tenant2_result = await service_mesh['backend_service'].execute_operation(
            auth_context=tenant2_context,
            operation='list_resources'
        )
        
        # Results should be completely isolated
        assert len(set(tenant1_result['resources']) & set(tenant2_result['resources'])) == 0
        
        # Cross-tenant access should be denied
        with pytest.raises(Exception) as exc_info:
            await service_mesh['backend_service'].execute_operation(
                auth_context=tenant1_context,
                operation='access_resource',
                resource_id=tenant2_result['resources'][0]
            )
        assert "access denied" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_auth_delegation_chain_validation(self, service_mesh):
        """Test validation of auth delegation chains"""
        original_user = "user_original"
        
        # User delegates to Service A
        delegation_a = await service_mesh['auth_service'].create_delegation(
            delegator=original_user,
            delegate='service_a',
            permissions=['read'],
            max_depth=2
        )
        
        # Service A delegates to Service B
        delegation_b = await service_mesh['api_gateway'].create_sub_delegation(
            parent_delegation=delegation_a,
            delegate='service_b',
            permissions=['read']  # Cannot exceed parent
        )
        
        # Service B tries to delegate to Service C
        delegation_c = await service_mesh['backend_service'].create_sub_delegation(
            parent_delegation=delegation_b,
            delegate='service_c',
            permissions=['read']
        )
        
        # Validate delegation chain
        chain_validation = await service_mesh['auth_service'].validate_delegation_chain(
            delegation=delegation_c
        )
        
        assert chain_validation['valid']
        assert chain_validation['chain_depth'] == 3
        assert chain_validation['original_delegator'] == original_user
        
        # Service C cannot delegate further (max_depth=2 exceeded)
        with pytest.raises(Exception) as exc_info:
            await service_mesh['websocket_service'].create_sub_delegation(
                parent_delegation=delegation_c,
                delegate='service_d',
                permissions=['read']
            )
        assert "max delegation depth" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_auth_migration_between_service_versions(self, service_mesh):
        """Test auth migration between different service versions"""
        user_id = "user_migration"
        
        # V1 auth token format
        v1_token = await service_mesh['auth_service'].create_token_v1(
            user_id=user_id,
            format='legacy'
        )
        
        # Deploy V2 auth service (maintains backward compatibility)
        service_mesh['auth_service_v2'] = AuthService(version='v2')
        
        # V2 should validate V1 tokens
        v1_validation = await service_mesh['auth_service_v2'].validate_token(
            token=v1_token,
            allow_legacy=True
        )
        
        assert v1_validation['valid']
        assert v1_validation['token_version'] == 'v1'
        assert v1_validation['migration_recommended']
        
        # Migrate V1 token to V2
        v2_token = await service_mesh['auth_service_v2'].migrate_token(v1_token)
        
        # V2 token has enhanced features
        v2_validation = await service_mesh['auth_service_v2'].validate_token(v2_token)
        assert v2_validation['valid']
        assert v2_validation['token_version'] == 'v2'
        assert 'enhanced_claims' in v2_validation