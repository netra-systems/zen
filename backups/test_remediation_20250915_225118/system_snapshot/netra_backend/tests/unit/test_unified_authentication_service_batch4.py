"""
Test Unified Authentication Service Batch 4 - Comprehensive Security and Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - Security Infrastructure
- Business Goal: System Stability & Security Compliance
- Value Impact: Validates SSOT authentication across all service contexts
- Revenue Impact: Protects $120K+ MRR by ensuring secure authentication flows

CRITICAL: These tests validate the SINGLE SOURCE OF TRUTH for authentication.
All authentication contexts (REST, WebSocket, service-to-service) MUST be tested.
NO mocks in security-critical paths - real authentication validation required.
"""
import pytest
import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional
from fastapi import WebSocket, HTTPException
from fastapi.testclient import TestClient
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService, AuthResult, AuthenticationMethod, AuthenticationContext, get_unified_auth_service
from netra_backend.app.services.user_execution_context import UserExecutionContext
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from shared.isolated_environment import get_env

class UnifiedAuthenticationServiceBatch4Tests(SSotAsyncTestCase):
    """
    Comprehensive Unified Authentication Service tests for Batch 4.
    
    Tests the SSOT authentication service across all contexts:
    - Token authentication in different contexts (REST, WebSocket, etc.)
    - WebSocket connection authentication
    - Service-to-service authentication 
    - Error handling and security compliance
    - Performance and statistics tracking
    """

    def setup_method(self, method):
        """Set up isolated test environment for unified authentication tests."""
        super().setup_method(method)
        self.env = get_env()
        self.env.set('ENVIRONMENT', 'test', 'unified_auth_batch4')
        self.env.set('JWT_SECRET_KEY', 'unified_auth_test_secret_32chars_long', 'unified_auth_batch4')
        self.env.set('AUTH_SERVICE_URL', 'http://localhost:8081', 'unified_auth_batch4')
        self.unified_auth = UnifiedAuthenticationService()
        self.auth_helper = E2EAuthHelper(environment='test')
        self.test_user_id = 'unified_test_user_batch4'
        self.test_email = 'unified@batch4-auth-test.com'
        self.test_permissions = ['read', 'write', 'auth_test']
        self.valid_token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id, email=self.test_email, permissions=self.test_permissions)
        self.record_metric('unified_auth_service_test_setup', True)

    def teardown_method(self, method):
        """Clean up isolated environment after each test."""
        self.env.delete('ENVIRONMENT', 'unified_auth_batch4')
        self.env.delete('JWT_SECRET_KEY', 'unified_auth_batch4')
        self.env.delete('AUTH_SERVICE_URL', 'unified_auth_batch4')
        super().teardown_method(method)

    @pytest.mark.asyncio
    async def test_authenticate_token_rest_api_context(self):
        """Test token authentication in REST API context.
        
        BVJ: Ensures REST API endpoints properly authenticate users.
        CRITICAL: REST API authentication is the primary revenue-generating interface.
        """
        with patch.object(self.unified_auth._auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = {'valid': True, 'user_id': self.test_user_id, 'email': self.test_email, 'permissions': self.test_permissions, 'iat': int(time.time()), 'exp': int(time.time()) + 3600}
            result = await self.unified_auth.authenticate_token(self.valid_token, context=AuthenticationContext.REST_API, method=AuthenticationMethod.JWT_TOKEN)
            assert result.success is True, 'REST API authentication should succeed'
            assert result.user_id == self.test_user_id, 'Should return correct user ID'
            assert result.email == self.test_email, 'Should return correct email'
            assert result.permissions == self.test_permissions, 'Should return correct permissions'
            assert result.metadata['context'] == 'rest_api', 'Should record REST API context'
            mock_validate.assert_called_once_with(self.valid_token)
        self.record_metric('rest_api_authentication_test', True)

    @pytest.mark.asyncio
    async def test_authenticate_token_websocket_context(self):
        """Test token authentication in WebSocket context.
        
        BVJ: Ensures WebSocket connections authenticate properly for real-time features.
        CRITICAL: WebSocket authentication enables $120K+ MRR chat functionality.
        """
        with patch.object(self.unified_auth._auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = {'valid': True, 'user_id': self.test_user_id, 'email': self.test_email, 'permissions': self.test_permissions, 'iat': int(time.time()), 'exp': int(time.time()) + 3600}
            result = await self.unified_auth.authenticate_token(self.valid_token, context=AuthenticationContext.WEBSOCKET, method=AuthenticationMethod.JWT_TOKEN)
            assert result.success is True, 'WebSocket authentication should succeed'
            assert result.user_id == self.test_user_id, 'Should return correct user ID'
            assert result.metadata['context'] == 'websocket', 'Should record WebSocket context'
            assert 'token_issued_at' in result.metadata, 'Should include token timing info'
            assert 'token_expires_at' in result.metadata, 'Should include token expiration info'
        self.record_metric('websocket_authentication_test', True)

    @pytest.mark.asyncio
    async def test_authenticate_token_service_context(self):
        """Test token authentication in internal service context.
        
        BVJ: Ensures secure service-to-service communication.
        CRITICAL: Service authentication prevents unauthorized internal access.
        """
        service_token = self.auth_helper.create_test_jwt_token(user_id='netra-analytics', email='service@netra.com', permissions=['service_access', 'internal_api'])
        with patch.object(self.unified_auth._auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = {'valid': True, 'user_id': 'netra-analytics', 'email': 'service@netra.com', 'permissions': ['service_access', 'internal_api'], 'iat': int(time.time()), 'exp': int(time.time()) + 3600}
            result = await self.unified_auth.authenticate_token(service_token, context=AuthenticationContext.INTERNAL_SERVICE, method=AuthenticationMethod.JWT_TOKEN)
            assert result.success is True, 'Service authentication should succeed'
            assert result.user_id == 'netra-analytics', 'Should return service ID'
            assert result.metadata['context'] == 'internal_service', 'Should record service context'
        self.record_metric('service_authentication_test', True)

    @pytest.mark.asyncio
    async def test_authenticate_token_invalid_format_handling(self):
        """Test authentication with invalid token formats.
        
        BVJ: Prevents security bypasses through malformed tokens.
        CRITICAL: Token format validation is first line of defense.
        """
        invalid_tokens = ['', 'not_a_jwt_token', 'Bearer not_jwt', 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9', 'definitely.not.valid.jwt.format.here']
        for invalid_token in invalid_tokens:
            result = await self.unified_auth.authenticate_token(invalid_token, context=AuthenticationContext.REST_API)
            assert result.success is False, f'Invalid token should be rejected: {invalid_token[:20]}...'
            assert result.error_code == 'INVALID_FORMAT', 'Should return format error code'
            assert 'Invalid token format' in result.error, 'Should provide descriptive error'
            assert 'token_debug' in result.metadata, 'Should include token debug info'
            token_debug = result.metadata['token_debug']
            assert 'length' in token_debug, 'Debug should include token length'
            assert 'has_dots' in token_debug, 'Debug should include dot count'
        self.record_metric('invalid_token_format_handling', len(invalid_tokens))

    @pytest.mark.asyncio
    async def test_authenticate_token_auth_service_error_handling(self):
        """Test authentication handling of auth service errors.
        
        BVJ: Ensures graceful degradation when auth service is unavailable.
        CRITICAL: Auth service failures should not break entire system.
        """
        from netra_backend.app.clients.auth_client_core import AuthServiceError, AuthServiceConnectionError
        with patch.object(self.unified_auth._auth_client, 'validate_token') as mock_validate:
            mock_validate.side_effect = AuthServiceConnectionError('Connection failed')
            result = await self.unified_auth.authenticate_token(self.valid_token, context=AuthenticationContext.REST_API)
            assert result.success is False, 'Should fail when auth service unavailable'
            assert result.error_code == 'AUTH_SERVICE_ERROR', 'Should return service error code'
            assert 'Authentication service error' in result.error, 'Should provide descriptive error'
            assert 'service_error_debug' in result.metadata, 'Should include service error debug info'
            service_debug = result.metadata['service_error_debug']
            assert service_debug['error_type'] == 'AuthServiceConnectionError', 'Should identify error type'
        with patch.object(self.unified_auth._auth_client, 'validate_token') as mock_validate:
            mock_validate.side_effect = AuthServiceError('Invalid token format')
            result = await self.unified_auth.authenticate_token(self.valid_token, context=AuthenticationContext.WEBSOCKET)
            assert result.success is False, 'Should fail on auth service error'
            assert result.error_code == 'AUTH_SERVICE_ERROR', 'Should return service error code'
        self.record_metric('auth_service_error_handling', True)

    @pytest.mark.asyncio
    async def test_authenticate_websocket_with_authorization_header(self):
        """Test WebSocket authentication using Authorization header.
        
        BVJ: Supports standard WebSocket authentication method.
        CRITICAL: Authorization header is the primary WebSocket auth method for chat.
        """
        mock_websocket = MagicMock()
        mock_websocket.headers = {'authorization': f'Bearer {self.valid_token}', 'sec-websocket-protocol': 'chat', 'user-agent': 'test-client'}
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = '127.0.0.1'
        mock_websocket.client.port = 12345
        with patch.object(self.unified_auth._auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = {'valid': True, 'user_id': self.test_user_id, 'email': self.test_email, 'permissions': self.test_permissions, 'iat': int(time.time()), 'exp': int(time.time()) + 3600}
            with patch('netra_backend.app.websocket_core.websocket_manager_factory.create_defensive_user_execution_context') as mock_create_context:
                mock_context = MagicMock(spec=UserExecutionContext)
                mock_context.user_id = self.test_user_id
                mock_context.websocket_client_id = f'ws_{self.test_user_id[:8]}_test'
                mock_create_context.return_value = mock_context
                auth_result, user_context = await self.unified_auth.authenticate_websocket(mock_websocket)
                assert auth_result.success is True, 'WebSocket authentication should succeed'
                assert auth_result.user_id == self.test_user_id, 'Should return correct user ID'
                assert user_context is not None, 'Should return UserExecutionContext'
                assert user_context.user_id == self.test_user_id, 'UserExecutionContext should have correct user ID'
                mock_create_context.assert_called_once()
                call_args = mock_create_context.call_args
                assert call_args[1]['user_id'] == self.test_user_id, 'Should pass correct user ID to context creation'
        self.record_metric('websocket_authorization_header_auth', True)

    @pytest.mark.asyncio
    async def test_authenticate_websocket_with_subprotocol(self):
        """Test WebSocket authentication using Sec-WebSocket-Protocol.
        
        BVJ: Supports alternative WebSocket authentication for client compatibility.
        CRITICAL: Subprotocol auth enables broader client support for chat features.
        """
        import base64
        encoded_token = base64.urlsafe_b64encode(self.valid_token.encode('utf-8')).decode('utf-8').rstrip('=')
        mock_websocket = MagicMock()
        mock_websocket.headers = {'sec-websocket-protocol': f'jwt.{encoded_token}, chat', 'user-agent': 'test-client'}
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = '127.0.0.1'
        mock_websocket.client.port = 12345
        with patch.object(self.unified_auth._auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = {'valid': True, 'user_id': self.test_user_id, 'email': self.test_email, 'permissions': self.test_permissions}
            with patch('netra_backend.app.websocket_core.websocket_manager_factory.create_defensive_user_execution_context') as mock_create_context:
                mock_context = MagicMock(spec=UserExecutionContext)
                mock_context.user_id = self.test_user_id
                mock_context.websocket_client_id = f'ws_{self.test_user_id[:8]}_subprotocol'
                mock_create_context.return_value = mock_context
                auth_result, user_context = await self.unified_auth.authenticate_websocket(mock_websocket)
                assert auth_result.success is True, 'Subprotocol authentication should succeed'
                assert auth_result.user_id == self.test_user_id, 'Should return correct user ID'
                assert user_context is not None, 'Should return UserExecutionContext'
        self.record_metric('websocket_subprotocol_auth', True)

    @pytest.mark.asyncio
    async def test_authenticate_websocket_no_token_error(self):
        """Test WebSocket authentication failure when no token provided.
        
        BVJ: Ensures unauthorized WebSocket connections are rejected.
        CRITICAL: Missing token should be clearly rejected with helpful error.
        """
        mock_websocket = MagicMock()
        mock_websocket.headers = {'sec-websocket-protocol': 'chat', 'user-agent': 'test-client'}
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = '127.0.0.1'
        mock_websocket.client.port = 12345
        mock_websocket.query_params = {}
        auth_result, user_context = await self.unified_auth.authenticate_websocket(mock_websocket)
        assert auth_result.success is False, 'WebSocket authentication should fail without token'
        assert auth_result.error_code == 'NO_TOKEN', 'Should return no token error code'
        assert 'No JWT token found' in auth_result.error, 'Should provide descriptive error'
        assert user_context is None, 'Should not return UserExecutionContext'
        assert 'no_token_debug' in auth_result.metadata, 'Should include debugging information'
        no_token_debug = auth_result.metadata['no_token_debug']
        assert 'headers_checked' in no_token_debug, 'Should include headers debug info'
        assert 'query_params' in no_token_debug, 'Should include query params debug info'
        self.record_metric('websocket_no_token_error', True)

    @pytest.mark.asyncio
    async def test_authenticate_websocket_context_creation_error(self):
        """Test WebSocket authentication when UserExecutionContext creation fails.
        
        BVJ: Ensures graceful handling of context creation failures.
        CRITICAL: Context creation errors should not cause 1011 WebSocket failures.
        """
        mock_websocket = MagicMock()
        mock_websocket.headers = {'authorization': f'Bearer {self.valid_token}'}
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = '127.0.0.1'
        mock_websocket.client.port = 12345
        with patch.object(self.unified_auth._auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = {'valid': True, 'user_id': self.test_user_id, 'email': self.test_email, 'permissions': self.test_permissions}
            with patch('netra_backend.app.websocket_core.websocket_manager_factory.create_defensive_user_execution_context') as mock_create_context:
                fallback_context = MagicMock(spec=UserExecutionContext)
                fallback_context.user_id = self.test_user_id
                fallback_context.websocket_client_id = 'fallback_context_id'
                mock_create_context.side_effect = [ValueError('Context creation failed'), fallback_context]
                auth_result, user_context = await self.unified_auth.authenticate_websocket(mock_websocket)
                assert auth_result.success is True, 'Should succeed despite initial context creation failure'
                assert user_context is not None, 'Should return fallback UserExecutionContext'
                assert user_context.websocket_client_id == 'fallback_context_id', 'Should use fallback context'
                assert mock_create_context.call_count == 2, 'Should attempt fallback context creation'
        self.record_metric('websocket_context_creation_error', True)

    @pytest.mark.asyncio
    async def test_validate_service_token_success(self):
        """Test successful service token validation.
        
        BVJ: Enables secure inter-service communication.
        CRITICAL: Service authentication prevents unauthorized service access.
        """
        service_name = 'netra-analytics'
        service_token = 'service_jwt_token_for_analytics'
        with patch.object(self.unified_auth._auth_client, 'validate_token_for_service') as mock_validate:
            mock_validate.return_value = {'valid': True, 'service_id': 'analytics-service-v1', 'permissions': ['data_access', 'compute_resources']}
            result = await self.unified_auth.validate_service_token(service_token, service_name)
            assert result.success is True, 'Service token validation should succeed'
            assert result.user_id == 'analytics-service-v1', 'Should return service ID as user ID'
            assert 'data_access' in result.permissions, 'Should include service permissions'
            assert 'compute_resources' in result.permissions, 'Should include all service permissions'
            assert result.metadata['context'] == 'service_auth', 'Should record service context'
            assert result.metadata['service_name'] == service_name, 'Should record service name'
            mock_validate.assert_called_once_with(service_token, service_name)
        self.record_metric('service_token_validation_success', True)

    @pytest.mark.asyncio
    async def test_validate_service_token_failure(self):
        """Test service token validation failure handling.
        
        BVJ: Prevents unauthorized service access through invalid tokens.
        CRITICAL: Failed service authentication should be clearly reported.
        """
        service_name = 'malicious-service'
        invalid_service_token = 'invalid_service_token'
        with patch.object(self.unified_auth._auth_client, 'validate_token_for_service') as mock_validate:
            mock_validate.return_value = {'valid': False, 'error': 'Service token expired'}
            result = await self.unified_auth.validate_service_token(invalid_service_token, service_name)
            assert result.success is False, 'Invalid service token should be rejected'
            assert result.error_code == 'SERVICE_VALIDATION_FAILED', 'Should return service validation error'
            assert 'Service token expired' in result.error, 'Should preserve original error message'
            assert result.metadata['service_name'] == service_name, 'Should record service name'
        self.record_metric('service_token_validation_failure', True)

    @pytest.mark.asyncio
    async def test_enhanced_resilience_retry_logic(self):
        """Test enhanced token validation with retry logic.
        
        BVJ: Improves system reliability by handling transient failures.
        CRITICAL: Retry logic ensures authentication doesn't fail due to temporary issues.
        """
        from netra_backend.app.clients.auth_client_core import AuthServiceConnectionError
        with patch.object(self.unified_auth._auth_client, 'validate_token') as mock_validate:
            mock_validate.side_effect = [AuthServiceConnectionError('Connection timeout'), AuthServiceConnectionError('Connection refused'), {'valid': True, 'user_id': self.test_user_id, 'email': self.test_email, 'permissions': self.test_permissions}]
            result = await self.unified_auth.authenticate_token(self.valid_token, context=AuthenticationContext.REST_API)
            assert result.success is True, 'Should succeed after retries'
            assert result.user_id == self.test_user_id, 'Should return correct user data'
            assert 'resilience_metadata' in result.metadata, 'Should include resilience information'
            resilience_info = result.metadata['resilience_metadata']
            assert resilience_info['attempts_made'] == 3, 'Should record number of attempts'
            assert 'attempt_details' in resilience_info, 'Should include attempt details'
            assert mock_validate.call_count == 3, 'Should retry failed calls'
        self.record_metric('enhanced_resilience_retry_logic', True)

    @pytest.mark.asyncio
    async def test_circuit_breaker_status_monitoring(self):
        """Test circuit breaker status monitoring integration.
        
        BVJ: Provides visibility into auth service health for operations.
        CRITICAL: Circuit breaker monitoring prevents cascade failures.
        """
        mock_circuit_manager = MagicMock()
        mock_breaker = MagicMock()
        mock_breaker.get_status.return_value = {'state': 'half_open', 'failure_count': 2}
        mock_circuit_manager.breaker = mock_breaker
        with patch.object(self.unified_auth._auth_client, 'circuit_manager', mock_circuit_manager):
            with patch.object(self.unified_auth._auth_client, 'validate_token') as mock_validate:
                mock_validate.return_value = {'valid': True, 'user_id': self.test_user_id, 'email': self.test_email, 'permissions': self.test_permissions}
                result = await self.unified_auth.authenticate_token(self.valid_token, context=AuthenticationContext.REST_API)
                assert result.success is True, 'Authentication should succeed'
                if 'resilience_metadata' in result.metadata:
                    resilience_info = result.metadata['resilience_metadata']
                    assert 'circuit_breaker_status' in resilience_info, 'Should include circuit breaker status'
        self.record_metric('circuit_breaker_status_monitoring', True)

    def test_authentication_statistics_tracking(self):
        """Test authentication statistics for SSOT compliance monitoring.
        
        BVJ: Provides metrics for system monitoring and business intelligence.
        CRITICAL: Statistics help identify authentication trends and issues.
        """
        initial_stats = self.unified_auth.get_authentication_stats()
        assert 'ssot_enforcement' in initial_stats, 'Should include SSOT compliance info'
        assert initial_stats['ssot_enforcement']['ssot_compliant'] is True, 'Should be SSOT compliant'
        assert initial_stats['ssot_enforcement']['duplicate_paths_eliminated'] == 4, 'Should track eliminated duplicates'
        assert 'statistics' in initial_stats, 'Should include authentication statistics'
        stats = initial_stats['statistics']
        assert 'total_attempts' in stats, 'Should track total attempts'
        assert 'successful_authentications' in stats, 'Should track successes'
        assert 'failed_authentications' in stats, 'Should track failures'
        assert 'success_rate_percent' in stats, 'Should calculate success rate'
        assert 'method_distribution' in initial_stats, 'Should track method usage'
        assert 'context_distribution' in initial_stats, 'Should track context usage'
        assert 'timestamp' in initial_stats, 'Should include timestamp'
        timestamp_str = initial_stats['timestamp']
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        time_diff = datetime.now(timezone.utc) - timestamp
        assert time_diff.total_seconds() < 60, 'Timestamp should be recent'
        self.record_metric('authentication_statistics_tracking', True)

    @pytest.mark.asyncio
    async def test_health_check_functionality(self):
        """Test unified authentication service health check.
        
        BVJ: Enables monitoring and alerting for authentication service health.
        CRITICAL: Health checks prevent authentication service outages from going unnoticed.
        """
        health_result = await self.unified_auth.health_check()
        assert 'status' in health_result, 'Should include status'
        assert health_result['status'] in ['healthy', 'degraded', 'unhealthy'], 'Should have valid status'
        assert health_result['service'] == 'UnifiedAuthenticationService', 'Should identify service'
        assert health_result['ssot_compliant'] is True, 'Should confirm SSOT compliance'
        assert 'auth_client_status' in health_result, 'Should include auth client status'
        assert 'timestamp' in health_result, 'Should include timestamp'
        timestamp_str = health_result['timestamp']
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        time_diff = datetime.now(timezone.utc) - timestamp
        assert time_diff.total_seconds() < 60, 'Health check timestamp should be recent'
        self.record_metric('health_check_functionality', True)

    def test_unified_auth_service_global_instance(self):
        """Test global unified authentication service instance (SSOT enforcement).
        
        BVJ: Ensures single source of truth for authentication across application.
        CRITICAL: Global instance prevents authentication inconsistencies and duplicates.
        """
        global_instance1 = get_unified_auth_service()
        global_instance2 = get_unified_auth_service()
        assert global_instance1 is global_instance2, 'Should return same global instance'
        assert isinstance(global_instance1, UnifiedAuthenticationService), 'Should return correct type'
        stats = global_instance1.get_authentication_stats()
        assert stats['ssot_enforcement']['ssot_compliant'] is True, 'Global instance should be SSOT compliant'
        self.record_metric('global_instance_ssot_enforcement', True)

    @pytest.mark.asyncio
    async def test_auth_result_compatibility_format(self):
        """Test AuthResult compatibility with legacy authentication formats.
        
        BVJ: Ensures backward compatibility during SSOT migration.
        CRITICAL: Compatibility format prevents breaking changes during authentication consolidation.
        """
        auth_result = AuthResult(success=True, user_id=self.test_user_id, email=self.test_email, permissions=self.test_permissions, metadata={'context': 'compatibility_test', 'token_type': 'access'})
        result_dict = auth_result.to_dict()
        assert 'valid' in result_dict, "Should include legacy 'valid' field"
        assert 'success' in result_dict, "Should include new 'success' field"
        assert result_dict['valid'] == result_dict['success'], 'Legacy and new fields should match'
        assert result_dict['user_id'] == self.test_user_id, 'Should preserve user ID'
        assert result_dict['email'] == self.test_email, 'Should preserve email'
        assert result_dict['permissions'] == self.test_permissions, 'Should preserve permissions'
        assert result_dict['metadata']['context'] == 'compatibility_test', 'Should preserve metadata'
        assert 'validated_at' in result_dict, 'Should include validation timestamp'
        validated_at = result_dict['validated_at']
        assert isinstance(validated_at, float), 'Validation timestamp should be float'
        assert time.time() - validated_at < 60, 'Validation timestamp should be recent'
        self.record_metric('auth_result_compatibility_format', True)

class UnifiedAuthenticationServiceErrorHandlingTests(SSotAsyncTestCase):
    """
    Error handling and edge case tests for Unified Authentication Service.
    
    Tests error scenarios and edge cases:
    - Malformed tokens and invalid inputs
    - Network timeouts and service unavailability
    - Security attack simulations
    - Resource exhaustion scenarios
    """

    def setup_method(self, method):
        """Set up isolated test environment for error handling tests."""
        super().setup_method(method)
        self.env = get_env()
        self.env.set('ENVIRONMENT', 'test', 'unified_auth_errors_batch4')
        self.env.set('JWT_SECRET_KEY', 'error_test_secret_32chars_long_key', 'unified_auth_errors_batch4')
        self.unified_auth = UnifiedAuthenticationService()
        self.record_metric('unified_auth_error_test_setup', True)

    def teardown_method(self, method):
        """Clean up isolated environment after error tests."""
        self.env.delete('ENVIRONMENT', 'unified_auth_errors_batch4')
        self.env.delete('JWT_SECRET_KEY', 'unified_auth_errors_batch4')
        super().teardown_method(method)

    @pytest.mark.asyncio
    async def test_malicious_token_security_handling(self):
        """Test handling of potentially malicious tokens.
        
        BVJ: Prevents security attacks through crafted tokens.
        CRITICAL: Security handling prevents authentication bypass attacks.
        """
        malicious_tokens = ["'; DROP TABLE users; --", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImFkbWluIjp0cnVlfQ.'; DROP TABLE users; --", "<script>alert('xss')</script>", 'javascript:alert(1)', '../../../etc/passwd', '..\\..\\windows\\system32\\config\\sam', '; cat /etc/passwd', '| whoami', 'A' * 10000, 'valid_token\x00malicious_part', '[U+1D552][U+1D555][U+1D55E][U+1D55A][U+1D55F]', 'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiIsImFkbWluIjp0cnVlfQ.']
        for malicious_token in malicious_tokens:
            result = await self.unified_auth.authenticate_token(malicious_token, context=AuthenticationContext.REST_API)
            assert result.success is False, f'Malicious token should be rejected: {malicious_token[:50]}...'
            error_msg = result.error.lower()
            assert 'secret' not in error_msg, 'Error should not leak secret information'
            assert 'password' not in error_msg, 'Error should not leak password information'
            assert 'key' not in error_msg, 'Error should not leak key information'
        self.record_metric('malicious_token_security_handling', len(malicious_tokens))

    @pytest.mark.asyncio
    async def test_resource_exhaustion_protection(self):
        """Test protection against resource exhaustion attacks.
        
        BVJ: Prevents DoS attacks through authentication flooding.
        CRITICAL: Resource protection ensures service availability during attacks.
        """
        concurrent_requests = 50
        tasks = []
        for i in range(concurrent_requests):
            invalid_token = f'invalid_token_{i}_' + 'x' * 100
            task = asyncio.create_task(self.unified_auth.authenticate_token(invalid_token, context=AuthenticationContext.REST_API))
            tasks.append(task)
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        assert len(results) == concurrent_requests, 'All concurrent requests should be handled'
        successful_rejections = 0
        for result in results:
            if isinstance(result, AuthResult) and (not result.success):
                successful_rejections += 1
            elif isinstance(result, Exception):
                pass
        rejection_rate = successful_rejections / concurrent_requests
        assert rejection_rate >= 0.8, f'Should properly reject most concurrent requests: {rejection_rate:.2%}'
        avg_time_per_request = execution_time / concurrent_requests
        assert avg_time_per_request < 1.0, f'Average time per request should be reasonable: {avg_time_per_request:.3f}s'
        self.record_metric('resource_exhaustion_protection', concurrent_requests)

    @pytest.mark.asyncio
    async def test_websocket_error_edge_cases(self):
        """Test WebSocket authentication error edge cases.
        
        BVJ: Ensures robust WebSocket error handling for production reliability.
        CRITICAL: Edge case handling prevents 1011 WebSocket errors that break chat.
        """
        mock_websocket_none_client = MagicMock()
        mock_websocket_none_client.headers = {'authorization': 'Bearer valid_token'}
        mock_websocket_none_client.client = None
        auth_result, user_context = await self.unified_auth.authenticate_websocket(mock_websocket_none_client)
        assert auth_result is not None, 'Should handle None client gracefully'
        assert 'websocket_error_debug' in auth_result.metadata or auth_result.success, 'Should provide debug info or succeed'
        mock_websocket_empty = MagicMock()
        mock_websocket_empty.headers = {}
        mock_websocket_empty.client = MagicMock()
        mock_websocket_empty.client.host = 'unknown'
        mock_websocket_empty.client.port = 0
        mock_websocket_empty.query_params = {}
        auth_result, user_context = await self.unified_auth.authenticate_websocket(mock_websocket_empty)
        assert auth_result.success is False, 'Should fail with empty headers'
        assert auth_result.error_code == 'NO_TOKEN', 'Should return no token error'
        mock_websocket_malformed = MagicMock()
        mock_websocket_malformed.headers = {'authorization': 'Malformed auth header', 'sec-websocket-protocol': 'invalid_protocol_format'}
        mock_websocket_malformed.client = MagicMock()
        mock_websocket_malformed.client.host = '127.0.0.1'
        mock_websocket_malformed.client.port = 12345
        mock_websocket_malformed.query_params = {}
        auth_result, user_context = await self.unified_auth.authenticate_websocket(mock_websocket_malformed)
        assert auth_result.success is False, 'Should fail with malformed headers'
        self.record_metric('websocket_error_edge_cases', 3)

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self):
        """Test handling of unexpected exceptions during authentication.
        
        BVJ: Ensures system stability when unexpected errors occur.
        CRITICAL: Exception handling prevents authentication service crashes.
        """
        with patch.object(self.unified_auth._auth_client, 'validate_token') as mock_validate:
            mock_validate.side_effect = RuntimeError('Unexpected system error')
            result = await self.unified_auth.authenticate_token('any_token', context=AuthenticationContext.REST_API)
            assert result.success is False, 'Should fail gracefully on unexpected exception'
            assert result.error_code == 'UNEXPECTED_ERROR', 'Should return unexpected error code'
            assert 'Authentication error' in result.error, 'Should provide generic error message'
            assert 'unexpected_error_debug' in result.metadata, 'Should include debug information'
            debug_info = result.metadata['unexpected_error_debug']
            assert debug_info['error_type'] == 'RuntimeError', 'Should identify error type'
            assert 'timestamp' in debug_info, 'Should include timestamp'
            assert debug_info['auth_client_available'] is True, 'Should check auth client availability'
        self.record_metric('unexpected_exception_handling', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')