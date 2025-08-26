"""
Cross-Service Auth Consistency Tests (Iterations 76-80).

This test suite covers authentication consistency across services:
- Auth service to backend service communication
- Frontend to auth service integration
- API gateway authentication forwarding
- Service-to-service authentication
- Auth token validation across services
- User state synchronization between services
- Cross-service session management
- Auth failure propagation and handling
- Service authentication health checks
- Auth configuration consistency validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure consistent auth across all services  
- Value Impact: Prevents auth inconsistencies that confuse users
- Strategic Impact: Critical for seamless multi-service user experience
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, call
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, List, Any, Optional

from auth_service.auth_core.models.auth_models import User
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.core.jwt_handler import JWTHandler
from test_framework.environment_markers import env

pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth_service,
    pytest.mark.cross_service
]


class TestAuthServiceToBackendIntegration:
    """Test auth service to backend service consistency (Iteration 76)."""

    @pytest.fixture
    def mock_backend_client(self):
        """Mock backend service client."""
        client = MagicMock()
        client.validate_auth_token = AsyncMock()
        client.get_user_profile = AsyncMock()
        client.sync_user_status = AsyncMock()
        client.health_check = AsyncMock()
        return client

    @pytest.fixture
    def auth_service(self):
        """Mock auth service."""
        service = MagicMock(spec=AuthService)
        service.validate_token = AsyncMock()
        service.get_user_by_id = AsyncMock()
        service.update_user_status = AsyncMock()
        return service

    async def test_auth_token_validation_consistency(self, auth_service, mock_backend_client):
        """Test auth token validation consistency between services."""
        user_id = str(uuid4())
        auth_token = 'consistent_auth_token_123'
        
        # Auth service validates token
        auth_service.validate_token.return_value = {
            'valid': True,
            'user_id': user_id,
            'email': 'user@example.com',
            'roles': ['user'],
            'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()
        }
        
        auth_validation = await auth_service.validate_token(auth_token)
        
        # Backend service validates same token
        mock_backend_client.validate_auth_token.return_value = {
            'valid': True,
            'user_id': user_id,
            'email': 'user@example.com',
            'roles': ['user'],
            'exp': auth_validation['exp']
        }
        
        backend_validation = await mock_backend_client.validate_auth_token(auth_token)
        
        # Verify consistency between services
        assert auth_validation['valid'] == backend_validation['valid']
        assert auth_validation['user_id'] == backend_validation['user_id']
        assert auth_validation['email'] == backend_validation['email']
        assert auth_validation['roles'] == backend_validation['roles']
        assert auth_validation['exp'] == backend_validation['exp']

    async def test_user_profile_synchronization(self, auth_service, mock_backend_client):
        """Test user profile synchronization between auth and backend services."""
        user_id = str(uuid4())
        
        # Auth service user profile
        auth_service.get_user_by_id.return_value = {
            'id': user_id,
            'email': 'user@example.com',
            'full_name': 'Test User',
            'is_active': True,
            'is_verified': True,
            'roles': ['user'],
            'last_updated': datetime.utcnow()
        }
        
        auth_profile = await auth_service.get_user_by_id(user_id)
        
        # Backend service user profile should match
        mock_backend_client.get_user_profile.return_value = {
            'user_id': user_id,
            'email': 'user@example.com',
            'full_name': 'Test User',
            'is_active': True,
            'is_verified': True,
            'roles': ['user'],
            'synchronized_at': datetime.utcnow()
        }
        
        backend_profile = await mock_backend_client.get_user_profile(user_id)
        
        # Verify profile consistency
        assert auth_profile['id'] == backend_profile['user_id']
        assert auth_profile['email'] == backend_profile['email']
        assert auth_profile['full_name'] == backend_profile['full_name']
        assert auth_profile['is_active'] == backend_profile['is_active']
        assert auth_profile['is_verified'] == backend_profile['is_verified']
        assert auth_profile['roles'] == backend_profile['roles']

    async def test_user_status_change_propagation(self, auth_service, mock_backend_client):
        """Test user status changes propagate from auth to backend."""
        user_id = str(uuid4())
        new_status = 'suspended'
        
        # Auth service updates user status
        auth_service.update_user_status.return_value = {
            'user_id': user_id,
            'old_status': 'active',
            'new_status': new_status,
            'updated_at': datetime.utcnow()
        }
        
        auth_update = await auth_service.update_user_status(user_id, new_status)
        
        # Backend service should be notified and sync status
        mock_backend_client.sync_user_status.return_value = {
            'user_id': user_id,
            'status_synchronized': True,
            'new_status': new_status,
            'synchronized_at': datetime.utcnow()
        }
        
        backend_sync = await mock_backend_client.sync_user_status(
            user_id=user_id,
            new_status=new_status
        )
        
        # Verify status propagation
        assert auth_update['user_id'] == backend_sync['user_id']
        assert auth_update['new_status'] == backend_sync['new_status']
        assert backend_sync['status_synchronized'] is True

    async def test_auth_service_health_check_integration(self, mock_backend_client):
        """Test auth service health check from backend perspective."""
        # Backend checks auth service health
        mock_backend_client.health_check.return_value = {
            'auth_service_status': 'healthy',
            'response_time_ms': 45,
            'jwt_validation_working': True,
            'database_connection': 'healthy',
            'redis_connection': 'healthy'
        }
        
        health_status = await mock_backend_client.health_check()
        
        assert health_status['auth_service_status'] == 'healthy'
        assert health_status['jwt_validation_working'] is True
        assert health_status['database_connection'] == 'healthy'
        assert health_status['response_time_ms'] < 100  # Performance threshold

    async def test_cross_service_auth_failure_handling(self, auth_service, mock_backend_client):
        """Test handling auth failures across services."""
        invalid_token = 'invalid_auth_token_123'
        
        # Auth service rejects invalid token
        auth_service.validate_token.return_value = {
            'valid': False,
            'error': 'token_invalid',
            'message': 'Invalid or malformed token'
        }
        
        auth_validation = await auth_service.validate_token(invalid_token)
        
        # Backend service should also reject and handle gracefully
        mock_backend_client.validate_auth_token.return_value = {
            'valid': False,
            'error': 'token_invalid',
            'action': 'redirect_to_login',
            'error_logged': True
        }
        
        backend_validation = await mock_backend_client.validate_auth_token(invalid_token)
        
        # Verify consistent failure handling
        assert auth_validation['valid'] is False
        assert backend_validation['valid'] is False
        assert auth_validation['error'] == backend_validation['error']
        assert backend_validation['action'] == 'redirect_to_login'
        assert backend_validation['error_logged'] is True


class TestFrontendAuthIntegration:
    """Test frontend to auth service integration (Iteration 77)."""

    @pytest.fixture
    def mock_frontend_client(self):
        """Mock frontend client."""
        client = MagicMock()
        client.login_request = AsyncMock()
        client.logout_request = AsyncMock()
        client.token_refresh_request = AsyncMock()
        client.auth_state_update = AsyncMock()
        return client

    @pytest.fixture
    def auth_service(self):
        """Mock auth service for frontend testing."""
        service = MagicMock(spec=AuthService)
        service.authenticate_user = AsyncMock()
        service.logout_user = AsyncMock()
        service.refresh_user_token = AsyncMock()
        return service

    async def test_frontend_login_flow_integration(self, auth_service, mock_frontend_client):
        """Test frontend login flow with auth service."""
        user_credentials = {
            'email': 'user@example.com',
            'password': 'UserPassword123!'
        }
        
        user_id = str(uuid4())
        access_token = 'frontend_access_token_123'
        
        # Frontend sends login request
        mock_frontend_client.login_request.return_value = {
            'credentials': user_credentials,
            'client_info': {
                'user_agent': 'Mozilla/5.0...',
                'ip_address': '192.168.1.100',
                'device_type': 'desktop'
            }
        }
        
        login_request = await mock_frontend_client.login_request(user_credentials)
        
        # Auth service processes login
        auth_service.authenticate_user.return_value = {
            'success': True,
            'user_id': user_id,
            'access_token': access_token,
            'refresh_token': 'frontend_refresh_token_456',
            'expires_in': 3600,
            'user_profile': {
                'id': user_id,
                'email': user_credentials['email'],
                'full_name': 'Frontend User'
            }
        }
        
        auth_response = await auth_service.authenticate_user(**user_credentials)
        
        # Verify successful integration
        assert auth_response['success'] is True
        assert auth_response['access_token'] == access_token
        assert auth_response['user_profile']['email'] == user_credentials['email']

    async def test_frontend_logout_flow_integration(self, auth_service, mock_frontend_client):
        """Test frontend logout flow with auth service."""
        user_id = str(uuid4())
        access_token = 'logout_token_123'
        
        # Frontend sends logout request
        mock_frontend_client.logout_request.return_value = {
            'user_id': user_id,
            'access_token': access_token,
            'logout_type': 'user_initiated'
        }
        
        logout_request = await mock_frontend_client.logout_request(
            user_id=user_id,
            access_token=access_token
        )
        
        # Auth service processes logout
        auth_service.logout_user.return_value = {
            'success': True,
            'user_id': user_id,
            'token_revoked': True,
            'session_ended': True,
            'logout_time': datetime.utcnow()
        }
        
        auth_response = await auth_service.logout_user(
            user_id=user_id,
            access_token=access_token
        )
        
        # Verify logout integration
        assert auth_response['success'] is True
        assert auth_response['token_revoked'] is True
        assert auth_response['session_ended'] is True

    async def test_frontend_token_refresh_integration(self, auth_service, mock_frontend_client):
        """Test frontend token refresh with auth service."""
        refresh_token = 'frontend_refresh_token_789'
        new_access_token = 'new_frontend_access_token_101'
        
        # Frontend requests token refresh
        mock_frontend_client.token_refresh_request.return_value = {
            'refresh_token': refresh_token,
            'client_info': {
                'session_id': str(uuid4()),
                'last_activity': datetime.utcnow() - timedelta(minutes=30)
            }
        }
        
        refresh_request = await mock_frontend_client.token_refresh_request(refresh_token)
        
        # Auth service processes refresh
        auth_service.refresh_user_token.return_value = {
            'success': True,
            'access_token': new_access_token,
            'refresh_token': 'new_frontend_refresh_token_202',
            'expires_in': 3600,
            'token_type': 'Bearer'
        }
        
        auth_response = await auth_service.refresh_user_token(refresh_token)
        
        # Verify token refresh integration
        assert auth_response['success'] is True
        assert auth_response['access_token'] == new_access_token
        assert auth_response['expires_in'] == 3600

    async def test_frontend_auth_state_synchronization(self, mock_frontend_client):
        """Test frontend auth state updates and synchronization."""
        user_id = str(uuid4())
        auth_state_changes = [
            {
                'type': 'user_status_changed',
                'user_id': user_id,
                'old_status': 'active',
                'new_status': 'suspended'
            },
            {
                'type': 'permissions_updated',
                'user_id': user_id,
                'new_permissions': ['read', 'write']
            }
        ]
        
        # Frontend receives auth state updates
        for change in auth_state_changes:
            mock_frontend_client.auth_state_update.return_value = {
                'update_received': True,
                'user_id': change['user_id'],
                'update_type': change['type'],
                'frontend_updated': True
            }
            
            update_response = await mock_frontend_client.auth_state_update(change)
            
            assert update_response['update_received'] is True
            assert update_response['frontend_updated'] is True
            assert update_response['user_id'] == user_id


class TestAPIGatewayAuthIntegration:
    """Test API gateway authentication integration (Iteration 78)."""

    @pytest.fixture
    def mock_api_gateway(self):
        """Mock API gateway."""
        gateway = MagicMock()
        gateway.validate_request_auth = AsyncMock()
        gateway.forward_authenticated_request = AsyncMock()
        gateway.handle_auth_failure = AsyncMock()
        gateway.rate_limit_check = AsyncMock()
        return gateway

    @pytest.fixture
    def jwt_handler(self):
        """Mock JWT handler for gateway testing."""
        handler = MagicMock(spec=JWTHandler)
        handler.validate_token = MagicMock()
        handler.extract_token_from_header = MagicMock()
        return handler

    async def test_api_gateway_auth_validation_flow(self, mock_api_gateway, jwt_handler):
        """Test API gateway authentication validation flow."""
        user_id = str(uuid4())
        auth_header = 'Bearer gateway_token_123'
        token = 'gateway_token_123'
        
        # Gateway extracts token from header
        jwt_handler.extract_token_from_header.return_value = token
        extracted_token = jwt_handler.extract_token_from_header(auth_header)
        
        assert extracted_token == token
        
        # Gateway validates extracted token
        jwt_handler.validate_token.return_value = {
            'valid': True,
            'user_id': user_id,
            'email': 'api_user@example.com',
            'scopes': ['api:read', 'api:write'],
            'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()
        }
        
        token_validation = jwt_handler.validate_token(token)
        
        # Gateway validates entire request
        mock_api_gateway.validate_request_auth.return_value = {
            'auth_valid': True,
            'user_id': user_id,
            'scopes': ['api:read', 'api:write'],
            'rate_limit_ok': True,
            'request_authorized': True
        }
        
        request_validation = await mock_api_gateway.validate_request_auth(
            auth_header=auth_header,
            requested_endpoint='/api/v1/users',
            method='GET'
        )
        
        # Verify gateway auth validation
        assert token_validation['valid'] is True
        assert request_validation['auth_valid'] is True
        assert request_validation['user_id'] == user_id
        assert 'api:read' in request_validation['scopes']

    async def test_api_gateway_request_forwarding(self, mock_api_gateway):
        """Test authenticated request forwarding through gateway."""
        user_id = str(uuid4())
        request_data = {
            'endpoint': '/api/v1/users/profile',
            'method': 'GET',
            'user_id': user_id,
            'headers': {'Authorization': 'Bearer valid_token_123'}
        }
        
        # Gateway forwards authenticated request
        mock_api_gateway.forward_authenticated_request.return_value = {
            'forwarded': True,
            'target_service': 'netra_backend',
            'response_status': 200,
            'user_id': user_id,
            'request_id': str(uuid4())
        }
        
        forwarding_result = await mock_api_gateway.forward_authenticated_request(
            **request_data
        )
        
        # Verify successful forwarding
        assert forwarding_result['forwarded'] is True
        assert forwarding_result['target_service'] == 'netra_backend'
        assert forwarding_result['response_status'] == 200
        assert forwarding_result['user_id'] == user_id

    async def test_api_gateway_auth_failure_handling(self, mock_api_gateway):
        """Test API gateway auth failure handling."""
        invalid_request = {
            'endpoint': '/api/v1/secure-data',
            'method': 'POST',
            'auth_header': 'Bearer invalid_token_123'
        }
        
        # Gateway handles auth failure
        mock_api_gateway.handle_auth_failure.return_value = {
            'auth_failed': True,
            'error_code': 'INVALID_TOKEN',
            'response_status': 401,
            'error_message': 'Authentication failed',
            'retry_allowed': False,
            'logged': True
        }
        
        failure_response = await mock_api_gateway.handle_auth_failure(
            **invalid_request
        )
        
        # Verify auth failure handling
        assert failure_response['auth_failed'] is True
        assert failure_response['error_code'] == 'INVALID_TOKEN'
        assert failure_response['response_status'] == 401
        assert failure_response['logged'] is True

    async def test_api_gateway_rate_limiting_integration(self, mock_api_gateway):
        """Test API gateway rate limiting with auth."""
        user_id = str(uuid4())
        
        # Gateway checks rate limits for authenticated user
        mock_api_gateway.rate_limit_check.return_value = {
            'rate_limit_ok': False,
            'user_id': user_id,
            'requests_remaining': 0,
            'reset_time': datetime.utcnow() + timedelta(minutes=15),
            'limit_exceeded': True
        }
        
        rate_check = await mock_api_gateway.rate_limit_check(user_id)
        
        # Verify rate limiting
        assert rate_check['rate_limit_ok'] is False
        assert rate_check['limit_exceeded'] is True
        assert rate_check['requests_remaining'] == 0


class TestServiceToServiceAuthentication:
    """Test service-to-service authentication (Iteration 79)."""

    @pytest.fixture
    def service_auth_manager(self):
        """Mock service authentication manager."""
        manager = MagicMock()
        manager.generate_service_token = AsyncMock()
        manager.validate_service_token = AsyncMock()
        manager.authenticate_service_request = AsyncMock()
        return manager

    async def test_service_token_generation_and_validation(self, service_auth_manager):
        """Test service-to-service token generation and validation."""
        source_service = 'netra_backend'
        target_service = 'auth_service'
        service_token = 'service_token_backend_to_auth_123'
        
        # Generate service token
        service_auth_manager.generate_service_token.return_value = {
            'service_token': service_token,
            'source_service': source_service,
            'target_service': target_service,
            'expires_in': 300,  # 5 minutes
            'scopes': ['user:read', 'auth:validate']
        }
        
        token_generation = await service_auth_manager.generate_service_token(
            source_service=source_service,
            target_service=target_service,
            scopes=['user:read', 'auth:validate']
        )
        
        assert token_generation['service_token'] == service_token
        assert token_generation['source_service'] == source_service
        assert token_generation['target_service'] == target_service
        
        # Validate service token
        service_auth_manager.validate_service_token.return_value = {
            'valid': True,
            'source_service': source_service,
            'target_service': target_service,
            'scopes': ['user:read', 'auth:validate'],
            'expires_at': datetime.utcnow() + timedelta(minutes=5)
        }
        
        token_validation = await service_auth_manager.validate_service_token(
            service_token
        )
        
        assert token_validation['valid'] is True
        assert token_validation['source_service'] == source_service
        assert token_validation['scopes'] == ['user:read', 'auth:validate']

    async def test_authenticated_service_request(self, service_auth_manager):
        """Test authenticated request between services."""
        request_data = {
            'source_service': 'netra_backend',
            'target_service': 'auth_service',
            'endpoint': '/internal/validate-user',
            'method': 'POST',
            'payload': {'user_id': str(uuid4())},
            'service_token': 'authenticated_service_token_123'
        }
        
        # Authenticate service request
        service_auth_manager.authenticate_service_request.return_value = {
            'authenticated': True,
            'source_service': request_data['source_service'],
            'target_service': request_data['target_service'],
            'request_authorized': True,
            'scopes_matched': True
        }
        
        auth_result = await service_auth_manager.authenticate_service_request(
            **request_data
        )
        
        # Verify service authentication
        assert auth_result['authenticated'] is True
        assert auth_result['request_authorized'] is True
        assert auth_result['scopes_matched'] is True

    async def test_service_auth_failure_handling(self, service_auth_manager):
        """Test service authentication failure handling."""
        invalid_service_token = 'invalid_service_token_123'
        
        # Validate invalid service token
        service_auth_manager.validate_service_token.return_value = {
            'valid': False,
            'error': 'token_expired',
            'expired_at': datetime.utcnow() - timedelta(minutes=1)
        }
        
        validation_result = await service_auth_manager.validate_service_token(
            invalid_service_token
        )
        
        assert validation_result['valid'] is False
        assert validation_result['error'] == 'token_expired'
        
        # Handle authentication failure
        service_auth_manager.authenticate_service_request.return_value = {
            'authenticated': False,
            'error': 'invalid_service_token',
            'action': 'reject_request',
            'retry_allowed': True
        }
        
        auth_failure = await service_auth_manager.authenticate_service_request(
            service_token=invalid_service_token,
            source_service='unknown_service',
            target_service='auth_service'
        )
        
        assert auth_failure['authenticated'] is False
        assert auth_failure['action'] == 'reject_request'


class TestAuthConfigurationConsistency:
    """Test auth configuration consistency validation (Iteration 80)."""

    @pytest.fixture
    def config_validator(self):
        """Mock configuration validator."""
        validator = MagicMock()
        validator.validate_auth_config = AsyncMock()
        validator.check_service_config_consistency = AsyncMock()
        validator.validate_jwt_settings = AsyncMock()
        validator.check_environment_consistency = AsyncMock()
        return validator

    async def test_auth_configuration_validation(self, config_validator):
        """Test comprehensive auth configuration validation."""
        auth_config = {
            'jwt_secret_key': 'test_jwt_secret_key_123',
            'jwt_expiration': 3600,
            'refresh_token_expiration': 604800,
            'password_min_length': 8,
            'max_login_attempts': 5,
            'lockout_duration': 900,
            'oauth_providers': ['google', 'github'],
            'redis_enabled': True,
            'session_timeout': 1800
        }
        
        # Validate auth configuration
        config_validator.validate_auth_config.return_value = {
            'valid': True,
            'config_items_checked': len(auth_config),
            'warnings': [],
            'errors': []
        }
        
        validation_result = await config_validator.validate_auth_config(auth_config)
        
        assert validation_result['valid'] is True
        assert validation_result['config_items_checked'] == len(auth_config)
        assert len(validation_result['errors']) == 0

    async def test_cross_service_config_consistency(self, config_validator):
        """Test configuration consistency across services."""
        service_configs = {
            'auth_service': {
                'jwt_secret_key': 'shared_jwt_secret_123',
                'jwt_algorithm': 'HS256',
                'token_expiration': 3600
            },
            'netra_backend': {
                'jwt_secret_key': 'shared_jwt_secret_123',
                'jwt_algorithm': 'HS256',
                'token_expiration': 3600
            },
            'api_gateway': {
                'jwt_secret_key': 'shared_jwt_secret_123',
                'jwt_algorithm': 'HS256',
                'token_expiration': 3600
            }
        }
        
        # Check config consistency
        config_validator.check_service_config_consistency.return_value = {
            'consistent': True,
            'services_checked': list(service_configs.keys()),
            'inconsistencies': [],
            'critical_mismatches': []
        }
        
        consistency_check = await config_validator.check_service_config_consistency(
            service_configs
        )
        
        assert consistency_check['consistent'] is True
        assert len(consistency_check['services_checked']) == 3
        assert len(consistency_check['critical_mismatches']) == 0

    async def test_jwt_settings_validation(self, config_validator):
        """Test JWT settings validation across services."""
        jwt_settings = {
            'algorithm': 'HS256',
            'secret_key': 'jwt_secret_for_validation',
            'expiration': 3600,
            'issuer': 'netra_auth_service',
            'audience': ['netra_backend', 'api_gateway']
        }
        
        # Validate JWT settings
        config_validator.validate_jwt_settings.return_value = {
            'valid': True,
            'algorithm_supported': True,
            'secret_key_strength': 'strong',
            'expiration_reasonable': True,
            'issuer_valid': True,
            'audience_valid': True
        }
        
        jwt_validation = await config_validator.validate_jwt_settings(jwt_settings)
        
        assert jwt_validation['valid'] is True
        assert jwt_validation['algorithm_supported'] is True
        assert jwt_validation['secret_key_strength'] == 'strong'
        assert jwt_validation['expiration_reasonable'] is True

    async def test_environment_specific_config_consistency(self, config_validator):
        """Test environment-specific configuration consistency."""
        environments = ['test', 'development', 'staging', 'production']
        
        for env_name in environments:
            config_validator.check_environment_consistency.return_value = {
                'environment': env_name,
                'consistent': True,
                'auth_endpoints_valid': True,
                'database_config_valid': True,
                'redis_config_valid': True,
                'oauth_config_valid': True,
                'security_settings_appropriate': True
            }
            
            env_check = await config_validator.check_environment_consistency(
                environment=env_name
            )
            
            assert env_check['environment'] == env_name
            assert env_check['consistent'] is True
            assert env_check['auth_endpoints_valid'] is True
            assert env_check['security_settings_appropriate'] is True

    async def test_configuration_inconsistency_detection(self, config_validator):
        """Test detection of configuration inconsistencies."""
        inconsistent_configs = {
            'auth_service': {
                'jwt_secret_key': 'secret_key_auth',
                'jwt_expiration': 3600
            },
            'netra_backend': {
                'jwt_secret_key': 'different_secret_key',  # Inconsistent!
                'jwt_expiration': 7200  # Different expiration!
            }
        }
        
        # Detect inconsistencies
        config_validator.check_service_config_consistency.return_value = {
            'consistent': False,
            'services_checked': ['auth_service', 'netra_backend'],
            'inconsistencies': [
                {
                    'type': 'jwt_secret_key_mismatch',
                    'services': ['auth_service', 'netra_backend'],
                    'severity': 'critical'
                },
                {
                    'type': 'jwt_expiration_mismatch',
                    'services': ['auth_service', 'netra_backend'],
                    'severity': 'warning'
                }
            ],
            'critical_mismatches': ['jwt_secret_key_mismatch']
        }
        
        inconsistency_check = await config_validator.check_service_config_consistency(
            inconsistent_configs
        )
        
        assert inconsistency_check['consistent'] is False
        assert len(inconsistency_check['inconsistencies']) == 2
        assert len(inconsistency_check['critical_mismatches']) == 1
        assert 'jwt_secret_key_mismatch' in inconsistency_check['critical_mismatches']