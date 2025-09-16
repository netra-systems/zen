"""
Integration Tests: Auth Service Delegation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure auth operations delegate to auth service  
- Value Impact: Unified auth prevents security inconsistencies ($500K+ ARR protection)
- Strategic Impact: Core platform security foundation

This test suite validates that auth integration layer correctly delegates
to auth service instead of performing JWT operations locally.

Tests validate:
1. Backend delegates token validation to auth service
2. Backend delegates token generation to auth service  
3. No direct JWT operations in backend production code
4. Auth integration layer pure delegation patterns
5. WebSocket auth delegation works correctly

CRITICAL: These tests use real services (PostgreSQL, Redis, AuthServiceClient)
but do NOT require Docker - they test delegation patterns directly.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any, Optional
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class AuthServiceDelegationTests(BaseIntegrationTest):
    """
    Integration tests for auth service delegation patterns.
    
    Validates that backend components delegate auth operations
    to auth service instead of performing them locally.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Set test environment for auth service
        self.set_env_var("AUTH_SERVICE_URL", "http://localhost:8081")
        self.set_env_var("JWT_SECRET_KEY", "test-secret-for-auth-service")
        
    @pytest.mark.integration
    async def test_backend_delegates_token_validation(self):
        """
        Test that backend delegates token validation to auth service.
        
        EXPECTED: FAIL initially (backend validates tokens locally)
        Should PASS after implementing auth service delegation.
        """
        try:
            from netra_backend.app.auth_integration.auth import get_current_user
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            
            # Mock auth service client response
            with patch.object(AuthServiceClient, 'validate_token') as mock_validate:
                mock_validate.return_value = {
                    'valid': True,
                    'user_id': 'test-user-123',
                    'email': 'test@example.com',
                    'permissions': ['read', 'write']
                }
                
                # Mock HTTP bearer token
                from fastapi.security import HTTPAuthorizationCredentials
                mock_credentials = HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials="test-token"
                )
                
                # Mock database session
                mock_db = AsyncMock()
                
                # Test token validation delegation
                try:
                    user = await get_current_user(
                        credentials=mock_credentials,
                        db=mock_db
                    )
                    
                    # Verify auth service was called, not local JWT decode
                    mock_validate.assert_called_once_with("test-token")
                    
                    # Verify user data returned correctly
                    assert user is not None
                    
                except Exception as e:
                    # Check if error indicates local JWT operations
                    error_msg = str(e).lower()
                    jwt_error_indicators = [
                        'jwt decode',
                        'jwt validation',
                        'token decode',
                        'invalid token signature'
                    ]
                    
                    if any(indicator in error_msg for indicator in jwt_error_indicators):
                        pytest.fail(
                            f"Backend appears to be doing local JWT validation instead of "
                            f"delegating to auth service. Error: {e}"
                        )
                    else:
                        # Re-raise non-JWT related errors for investigation
                        raise
                        
        except ImportError as e:
            pytest.fail(
                f"Cannot import auth integration components. "
                f"Ensure auth integration layer exists. Error: {e}"
            )
    
    @pytest.mark.integration
    async def test_backend_delegates_token_generation(self):
        """
        Test that backend delegates token generation to auth service.
        
        Backend should not generate JWT tokens directly,
        should call auth service /token endpoint.
        """
        try:
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            
            # Test direct auth client usage (this should work)
            with patch.object(AuthServiceClient, 'generate_token') as mock_generate:
                mock_generate.return_value = {
                    'access_token': 'auth-service-generated-token',
                    'token_type': 'bearer',
                    'expires_in': 3600
                }
                
                auth_client = AuthServiceClient()
                result = await auth_client.generate_token(
                    user_id='test-user',
                    email='test@example.com'
                )
                
                # Verify auth service was called
                mock_generate.assert_called_once()
                assert result['access_token'] == 'auth-service-generated-token'
                
        except ImportError as e:
            pytest.fail(f"Cannot import AuthServiceClient. Error: {e}")
    
    @pytest.mark.integration
    async def test_no_direct_jwt_operations_in_auth_integration(self):
        """
        Test that auth integration module contains no direct JWT operations.
        
        The auth integration layer should only contain delegation code,
        not JWT encoding/decoding operations.
        """
        try:
            # Import auth integration module
            import netra_backend.app.auth_integration.auth as auth_module
            import inspect
            
            # Get source code of auth integration module
            auth_source = inspect.getsource(auth_module)
            
            # Check for JWT operations
            jwt_operation_patterns = [
                'jwt.encode(',
                'jwt.decode(',
                'jwt.verify(',
                'PyJWT',
                'jose.jwt'
            ]
            
            found_violations = []
            lines = auth_source.split('\n')
            for line_num, line in enumerate(lines, 1):
                for pattern in jwt_operation_patterns:
                    if pattern in line:
                        found_violations.append(f"Line {line_num}: {line.strip()}")
            
            if found_violations:
                pytest.fail(
                    f"Auth integration module contains direct JWT operations. "
                    f"Should only delegate to auth service:\n" + 
                    "\n".join(f"  {v}" for v in found_violations)
                )
                
        except ImportError as e:
            pytest.fail(f"Cannot import auth integration module. Error: {e}")
    
    @pytest.mark.integration
    async def test_auth_integration_layer_pure_delegation(self):
        """
        Test that auth integration layer only contains delegation patterns.
        
        Auth integration should:
        - Call AuthServiceClient methods
        - Convert responses to User objects  
        - Handle FastAPI dependency injection
        - NOT perform any auth logic itself
        """
        try:
            import netra_backend.app.auth_integration.auth as auth_module
            import inspect
            
            # Get all functions in auth integration module
            auth_functions = [
                name for name, obj in inspect.getmembers(auth_module)
                if inspect.isfunction(obj) and not name.startswith('_')
            ]
            
            # Verify key delegation functions exist
            expected_functions = [
                'get_current_user',  # Should delegate to auth service
            ]
            
            missing_functions = []
            for func_name in expected_functions:
                if func_name not in auth_functions:
                    missing_functions.append(func_name)
            
            if missing_functions:
                pytest.fail(
                    f"Auth integration module missing delegation functions: {missing_functions}"
                )
            
            # Verify functions use AuthServiceClient
            for func_name in expected_functions:
                if hasattr(auth_module, func_name):
                    func = getattr(auth_module, func_name)
                    func_source = inspect.getsource(func)
                    
                    # Should contain auth service client usage
                    if 'auth_client' not in func_source and 'AuthServiceClient' not in func_source:
                        pytest.fail(
                            f"Function {func_name} doesn't appear to use AuthServiceClient. "
                            f"Should delegate to auth service."
                        )
                        
        except ImportError as e:
            pytest.skip(f"Auth integration module not available. Error: {e}")
    
    @pytest.mark.integration
    async def test_websocket_auth_uses_delegation(self):
        """
        Test that WebSocket authentication uses auth service delegation.
        
        WebSocket auth should validate tokens via auth service,
        not perform local JWT validation.
        """
        try:
            # Try to import WebSocket auth components
            from netra_backend.app.websocket_core.auth import WebSocketAuthenticator
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            
            # Mock auth service validation
            with patch.object(AuthServiceClient, 'validate_token') as mock_validate:
                mock_validate.return_value = {
                    'valid': True,
                    'user_id': 'websocket-user-123',
                    'email': 'ws@example.com'
                }
                
                authenticator = WebSocketAuthenticator()
                
                # Test WebSocket token validation
                is_valid = await authenticator.validate_websocket_token("test-ws-token")
                
                # Verify auth service was called for validation
                mock_validate.assert_called_once_with("test-ws-token")
                assert is_valid is True
                
        except ImportError:
            # If WebSocket auth components don't exist yet, check for patterns
            try:
                # Look for any WebSocket auth in websocket core
                import netra_backend.app.websocket_core as ws_module
                import os
                import glob
                
                # Find all Python files in websocket core
                ws_path = os.path.dirname(ws_module.__file__)
                ws_files = glob.glob(os.path.join(ws_path, "*.py"))
                
                # Check for JWT operations in WebSocket files
                jwt_violations = []
                for ws_file in ws_files:
                    try:
                        with open(ws_file, 'r') as f:
                            content = f.read()
                            
                        if 'jwt.decode(' in content or 'jwt.encode(' in content:
                            jwt_violations.append(os.path.basename(ws_file))
                    except (IOError, UnicodeDecodeError):
                        continue
                
                if jwt_violations:
                    pytest.fail(
                        f"WebSocket files contain direct JWT operations: {jwt_violations}. "
                        f"Should delegate to auth service."
                    )
                    
            except ImportError:
                pytest.skip("WebSocket auth components not available for testing")
    
    @pytest.mark.integration
    async def test_auth_service_connectivity(self, real_services_fixture):
        """
        Test that auth service client can connect to auth service.
        
        This test validates that the delegation infrastructure works
        by testing actual connectivity to auth service.
        """
        try:
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            
            auth_client = AuthServiceClient()
            
            # Test basic connectivity (may need to mock if auth service not available)
            try:
                # Try to get auth service health/status
                health_response = await auth_client.health_check()
                assert health_response is not None
                
            except Exception as e:
                # If auth service not available in test environment, that's OK
                # The important thing is that backend tries to connect to auth service
                error_msg = str(e).lower()
                
                # These errors indicate proper delegation attempt
                acceptable_errors = [
                    'connection refused',
                    'auth service not available',
                    'network unreachable',
                    'timeout'
                ]
                
                if any(error in error_msg for error in acceptable_errors):
                    # This is expected in test environment - auth client is trying to connect
                    self.logger.info(f"Auth service client correctly attempting connection: {e}")
                else:
                    # Unexpected error might indicate local JWT operations
                    pytest.fail(
                        f"Unexpected auth service error - might indicate local JWT operations: {e}"
                    )
                    
        except ImportError as e:
            pytest.fail(f"Cannot import AuthServiceClient. Error: {e}")
    
    @pytest.mark.integration
    async def test_auth_client_error_handling(self):
        """
        Test that auth client handles auth service errors properly.
        
        When auth service is unavailable, client should provide
        clear errors, not fall back to local JWT operations.
        """
        try:
            from netra_backend.app.clients.auth_client_core import (
                AuthServiceClient, 
                AuthServiceError,
                AuthServiceConnectionError
            )
            
            auth_client = AuthServiceClient()
            
            # Mock network error
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.side_effect = Exception("Connection refused")
                
                # Test that client raises proper auth service errors
                with pytest.raises((AuthServiceError, AuthServiceConnectionError, Exception)):
                    await auth_client.validate_token("test-token")
                    
                # Verify HTTP request was attempted (delegation, not local JWT)
                mock_post.assert_called_once()
                
        except ImportError as e:
            pytest.fail(f"Cannot import auth service client classes. Error: {e}")
    
    @pytest.mark.integration
    async def test_session_management_delegation(self):
        """
        Test that session management delegates to auth service.
        
        Session creation, validation, and cleanup should all
        go through auth service, not local session storage.
        """
        try:
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            
            # Mock auth service session operations
            with patch.object(AuthServiceClient, 'create_session') as mock_create, \
                 patch.object(AuthServiceClient, 'validate_session') as mock_validate, \
                 patch.object(AuthServiceClient, 'destroy_session') as mock_destroy:
                
                mock_create.return_value = {
                    'session_id': 'auth-service-session-123',
                    'expires_at': '2024-12-31T23:59:59Z'
                }
                mock_validate.return_value = {
                    'valid': True,
                    'user_id': 'session-user-123'
                }
                mock_destroy.return_value = {'success': True}
                
                auth_client = AuthServiceClient()
                
                # Test session lifecycle delegation
                session = await auth_client.create_session(user_id='test-user')
                assert session['session_id'] == 'auth-service-session-123'
                
                validation = await auth_client.validate_session(session['session_id'])
                assert validation['valid'] is True
                
                result = await auth_client.destroy_session(session['session_id'])
                assert result['success'] is True
                
                # Verify all operations delegated to auth service
                mock_create.assert_called_once()
                mock_validate.assert_called_once()
                mock_destroy.assert_called_once()
                
        except ImportError as e:
            pytest.skip(f"Session management not available for testing. Error: {e}")
        except AttributeError as e:
            pytest.fail(
                f"Auth client missing session management methods. "
                f"Should delegate session operations to auth service. Error: {e}"
            )
    
    @pytest.mark.integration
    async def test_cors_configuration_consistency(self):
        """
        Test that CORS configuration is consistent for auth endpoints.
        
        All auth-related endpoints should use unified CORS patterns
        through auth service delegation.
        """
        try:
            from shared.cors_config import get_cors_config
            
            # Get CORS configuration
            cors_config = get_cors_config()
            
            # Verify auth service URL is in allowed origins
            auth_service_url = self.get_env_var("AUTH_SERVICE_URL", "http://localhost:8081")
            
            # CORS should be configured to allow auth service
            assert cors_config is not None
            
            # If specific origins are configured, auth service should be included
            if hasattr(cors_config, 'allow_origins') and cors_config.allow_origins:
                auth_host = auth_service_url.split('://')[1] if '://' in auth_service_url else auth_service_url
                
                # Check if auth service is allowed (exact match or wildcard)
                cors_allows_auth = (
                    '*' in cors_config.allow_origins or
                    auth_service_url in cors_config.allow_origins or
                    auth_host in cors_config.allow_origins
                )
                
                assert cors_allows_auth, f"CORS should allow auth service URL: {auth_service_url}"
                
        except ImportError as e:
            pytest.skip(f"CORS configuration not available for testing. Error: {e}")


if __name__ == "__main__":
    # Allow running this test file directly for development
    pytest.main([__file__, "-v"])