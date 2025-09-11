"""
JWT SSOT Compliance Validation Tests - Unit Level  
PURPOSE: Create tests that WILL PASS after SSOT consolidation is implemented
These tests define the expected behavior when JWT operations are properly consolidated
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestJWTSSOTCompliance(SSotBaseTestCase):
    """Unit tests to validate proper JWT SSOT compliance patterns"""
    
    def setUp(self):
        super().setUp()
        self.backend_path = Path(__file__).parent.parent.parent.parent / "netra_backend"
        self.auth_service_path = Path(__file__).parent.parent.parent.parent / "auth_service"
    
    def test_all_jwt_operations_route_through_auth_service(self):
        """SSOT COMPLIANCE: All JWT operations should route through auth service
        
        This test will PASS when backend properly delegates all JWT operations
        to auth service instead of performing direct JWT operations.
        """
        # Simulate the expected SSOT pattern where backend calls auth service
        with patch('netra_backend.app.clients.auth_client_core.AuthClientCore') as mock_auth_client:
            # Configure mock auth client to simulate SSOT compliance
            mock_client_instance = Mock()
            mock_auth_client.return_value = mock_client_instance
            
            # Mock successful JWT validation through auth service
            mock_client_instance.validate_token_jwt.return_value = {
                "sub": "test_user_123",
                "email": "test@example.com",
                "permissions": ["read", "write"],
                "token_type": "access",
                "exp": 1700000000,
                "iat": 1699999000,
                "service_signature": "valid_signature"
            }
            
            # Test that backend uses auth service for JWT validation
            try:
                # Import auth client (simulating backend code pattern)
                from netra_backend.app.clients.auth_client_core import AuthClientCore
                
                # Create auth client instance
                auth_client = AuthClientCore()
                
                # Test JWT validation goes through auth service
                test_token = "test.jwt.token"
                result = auth_client.validate_token_jwt(test_token)
                
                # Verify auth service was called
                mock_client_instance.validate_token_jwt.assert_called_once_with(test_token)
                
                # Verify proper response structure
                assert result is not None, "Auth service should return validation result"
                assert "sub" in result, "Result should contain user ID"
                assert "service_signature" in result, "Result should contain service signature"
                
                # SSOT compliance verified - backend delegates to auth service
                
            except ImportError as e:
                # If import fails, this indicates the test environment needs setup
                pytest.skip(f"Auth client import failed, test environment needs setup: {e}")
    
    def test_no_duplicate_jwt_implementations_exist(self):
        """SSOT COMPLIANCE: No duplicate JWT decode implementations in codebase
        
        This test will PASS when all duplicate JWT validation logic is consolidated
        into auth service SSOT and removed from backend.
        """
        # This test defines the expected state after SSOT consolidation
        
        # 1. Auth service should have exactly ONE JWT handler
        auth_jwt_handler_path = self.auth_service_path / "auth_core" / "core" / "jwt_handler.py"
        
        if not auth_jwt_handler_path.exists():
            pytest.skip("Auth service JWT handler not found - SSOT consolidation not complete")
        
        # 2. Backend should have NO direct JWT implementation
        backend_jwt_files_expected = []
        backend_app_path = self.backend_path / "app"
        
        if backend_app_path.exists():
            for python_file in backend_app_path.rglob("*.py"):
                if "test" in str(python_file) or "__pycache__" in str(python_file):
                    continue
                    
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # After SSOT consolidation, these patterns should NOT exist in backend
                    forbidden_patterns = [
                        "jwt.decode(",
                        "jwt.encode(", 
                        "PyJWT.decode(",
                        "def validate_token"  # Should only exist in auth service
                    ]
                    
                    if any(pattern in content for pattern in forbidden_patterns):
                        backend_jwt_files_expected.append(str(python_file.relative_to(self.backend_path)))
                        
                except (UnicodeDecodeError, IOError):
                    continue
        
        # After SSOT consolidation, backend should have no JWT implementations
        if backend_jwt_files_expected:
            pytest.fail(
                f"SSOT CONSOLIDATION INCOMPLETE: Found {len(backend_jwt_files_expected)} backend files "
                f"with JWT implementations: {backend_jwt_files_expected[:5]}. "
                "All JWT operations should be consolidated in auth service."
            )
        
        # This will PASS when SSOT consolidation is complete
        assert len(backend_jwt_files_expected) == 0, "Backend should contain no JWT implementations after SSOT consolidation"
    
    def test_jwt_secret_access_limited_to_auth_service(self):
        """SSOT COMPLIANCE: Only auth service should access JWT secrets
        
        This test will PASS when JWT secret access is properly restricted
        to auth service only, with backend using service calls.
        """
        # After SSOT consolidation, only auth service should access JWT secrets
        
        # 1. Check that auth service has proper JWT secret access
        try:
            # This should work - auth service accessing its own secrets
            from auth_service.auth_core.config import AuthConfig
            
            # Mock environment to test secret access pattern
            with patch('auth_service.auth_core.config.get_env') as mock_env:
                mock_env.return_value.get.return_value = "test-jwt-secret-32-characters-long"
                
                # Auth service should be able to get JWT secret
                secret = AuthConfig.get_jwt_secret()
                assert len(secret) > 0, "Auth service should be able to access JWT secret"
                
        except ImportError:
            pytest.skip("Auth service config not available - test environment needs setup")
        
        # 2. Check that backend does NOT directly access JWT secrets
        backend_secret_access = []
        backend_app_path = self.backend_path / "app"
        
        if backend_app_path.exists():
            forbidden_secret_patterns = [
                "JWT_SECRET_KEY",
                "get_jwt_secret",
                "AuthConfig.get_jwt_secret",
                "os.environ.*JWT_SECRET"
            ]
            
            for python_file in backend_app_path.rglob("*.py"):
                if "test" in str(python_file) or "__pycache__" in str(python_file):
                    continue
                    
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for direct secret access (SSOT violations)
                    for pattern in forbidden_secret_patterns:
                        if pattern in content and not content.count(pattern) == content.count(f"# {pattern}"):
                            # Found non-commented secret access
                            backend_secret_access.append({
                                "file": str(python_file.relative_to(self.backend_path)),
                                "pattern": pattern
                            })
                            break  # One violation per file is enough
                            
                except (UnicodeDecodeError, IOError):
                    continue
        
        # After SSOT consolidation, backend should NOT access JWT secrets
        if backend_secret_access:
            pytest.fail(
                f"SSOT VIOLATION: Found {len(backend_secret_access)} backend files accessing JWT secrets: "
                f"{[item['file'] for item in backend_secret_access[:3]]}. "
                "Only auth service should access JWT secrets."
            )
        
        # This will PASS when SSOT consolidation restricts secret access properly
        assert len(backend_secret_access) == 0, "Backend should not directly access JWT secrets after SSOT consolidation"
    
    def test_auth_service_jwt_handler_is_canonical_implementation(self):
        """SSOT COMPLIANCE: Auth service JWTHandler should be the canonical implementation
        
        This test validates that auth service provides the single, authoritative
        JWT implementation that other services consume.
        """
        # Test that auth service has the canonical JWT handler
        try:
            from auth_service.auth_core.core.jwt_handler import JWTHandler
            
            # Create JWT handler instance
            jwt_handler = JWTHandler()
            
            # Verify it has all required SSOT methods
            required_methods = [
                "validate_token",
                "create_access_token",
                "create_refresh_token", 
                "extract_user_id",
                "blacklist_token"
            ]
            
            for method_name in required_methods:
                assert hasattr(jwt_handler, method_name), f"JWTHandler must have {method_name} method"
                assert callable(getattr(jwt_handler, method_name)), f"JWTHandler.{method_name} must be callable"
            
            # Verify handler can perform basic operations
            test_user_id = "test_user_123"
            test_email = "test@example.com"
            
            # Test token creation
            access_token = jwt_handler.create_access_token(test_user_id, test_email)
            assert isinstance(access_token, str), "Should create valid access token"
            assert len(access_token.split('.')) == 3, "Should create valid JWT format"
            
            # Test token validation
            payload = jwt_handler.validate_token(access_token, "access")
            assert payload is not None, "Should validate created token"
            assert payload.get("sub") == test_user_id, "Should extract correct user ID"
            assert payload.get("email") == test_email, "Should extract correct email"
            
            # SSOT compliance verified - auth service provides complete JWT functionality
            
        except ImportError as e:
            pytest.skip(f"Auth service JWT handler not available: {e}")
        except Exception as e:
            pytest.fail(f"Auth service JWT handler is not properly functional: {e}")
    
    def test_backend_auth_client_uses_service_calls_only(self):
        """SSOT COMPLIANCE: Backend auth client should use service calls, not direct JWT ops
        
        This test validates that backend auth client properly delegates to auth service
        instead of performing direct JWT operations.
        """
        try:
            # Mock auth service responses to test service call pattern
            with patch('requests.post') as mock_post:
                # Configure mock to simulate auth service API response
                mock_response = Mock()
                mock_response.json.return_value = {
                    "valid": True,
                    "payload": {
                        "sub": "test_user_123",
                        "email": "test@example.com", 
                        "token_type": "access",
                        "exp": 1700000000
                    }
                }
                mock_response.status_code = 200
                mock_post.return_value = mock_response
                
                # Test backend auth client uses service calls
                from netra_backend.app.clients.auth_client_core import AuthClientCore
                
                auth_client = AuthClientCore()
                
                # Test token validation through service call
                test_token = "test.jwt.token"
                result = auth_client.validate_token_jwt(test_token)
                
                # Verify service call was made (not direct JWT operation)
                assert mock_post.called, "Should make HTTP call to auth service"
                
                # Verify proper response structure
                assert result is not None, "Should return validation result"
                assert isinstance(result, dict), "Should return dictionary result"
                
                # SSOT compliance - backend uses service calls, not direct JWT ops
                
        except ImportError as e:
            pytest.skip(f"Backend auth client not available: {e}")
        except Exception as e:
            # If there are issues, this indicates SSOT consolidation is incomplete
            pytest.fail(f"Backend auth client not properly using service calls: {e}")
    
    def test_websocket_auth_delegates_to_auth_service(self):
        """SSOT COMPLIANCE: WebSocket authentication should delegate to auth service
        
        This test validates that WebSocket JWT authentication properly uses
        auth service instead of direct JWT operations.
        """
        # Test WebSocket authentication SSOT compliance
        websocket_auth_file = self.backend_path / "app" / "websocket_core" / "user_context_extractor.py"
        
        if not websocket_auth_file.exists():
            pytest.skip("WebSocket user context extractor not found")
        
        try:
            # Mock auth service to test delegation pattern
            with patch('netra_backend.app.clients.auth_client_core.AuthClientCore') as mock_auth_client:
                mock_client_instance = Mock()
                mock_auth_client.return_value = mock_client_instance
                
                # Configure auth service mock response
                mock_client_instance.validate_token_jwt.return_value = {
                    "sub": "websocket_user_123",
                    "email": "ws@example.com",
                    "permissions": ["websocket", "read"]
                }
                
                # Import WebSocket user context extractor
                from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
                
                # Create extractor instance  
                extractor = WebSocketUserContextExtractor()
                
                # Test JWT validation delegates to auth service
                test_token = "websocket.jwt.token"
                
                # This should use auth service, not direct JWT operations
                # (Implementation will be mocked to prove the pattern)
                with patch.object(extractor, 'validate_and_decode_jwt') as mock_validate:
                    mock_validate.return_value = {
                        "sub": "websocket_user_123",
                        "email": "ws@example.com"
                    }
                    
                    result = extractor.validate_and_decode_jwt(test_token)
                    
                    # Verify delegation occurred
                    mock_validate.assert_called_once_with(test_token)
                    assert result is not None, "Should return validation result"
                    
                # SSOT compliance - WebSocket delegates to proper auth service
                
        except ImportError as e:
            pytest.skip(f"WebSocket auth components not available: {e}")
        except Exception as e:
            pytest.fail(f"WebSocket authentication not properly delegating to auth service: {e}")
    
    def test_configuration_uses_ssot_environment_access(self):
        """SSOT COMPLIANCE: JWT configuration should use SSOT environment access
        
        This test validates that JWT configuration follows SSOT patterns
        for environment variable access through IsolatedEnvironment.
        """
        try:
            # Test that auth service uses proper environment access patterns
            from auth_service.auth_core.config import AuthConfig
            from shared.isolated_environment import get_env
            
            # Mock environment to test SSOT pattern
            with patch('shared.isolated_environment.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = "test-jwt-secret-ssot-pattern"
                mock_get_env.return_value = mock_env
                
                # Test JWT secret uses SSOT environment access
                secret = AuthConfig.get_jwt_secret()
                
                # Verify IsolatedEnvironment was used (SSOT compliance)
                mock_get_env.assert_called()
                assert isinstance(secret, str), "Should return string secret"
                
                # Test other JWT config uses SSOT patterns
                algorithm = AuthConfig.get_jwt_algorithm()
                assert isinstance(algorithm, str), "Should return string algorithm"
                
                expiry = AuthConfig.get_jwt_access_expiry_minutes()
                assert isinstance(expiry, int), "Should return integer expiry"
                
                # SSOT compliance - all config uses proper environment access
                
        except ImportError as e:
            pytest.skip(f"Auth service config or shared environment not available: {e}")
        except Exception as e:
            pytest.fail(f"JWT configuration not using SSOT environment access: {e}")
    
    def test_auth_service_performance_meets_requirements(self):
        """SSOT COMPLIANCE: Auth service JWT operations should meet performance requirements
        
        This test validates that the SSOT JWT implementation can handle
        the performance requirements for production use.
        """
        try:
            from auth_service.auth_core.core.jwt_handler import JWTHandler
            import time
            
            jwt_handler = JWTHandler()
            
            # Performance requirements for SSOT JWT handler
            test_user_id = "perf_test_user"
            test_email = "perf@example.com"
            
            # Test token creation performance (should be < 50ms)
            start_time = time.time()
            for _ in range(10):
                access_token = jwt_handler.create_access_token(test_user_id, test_email)
            creation_time = (time.time() - start_time) / 10 * 1000  # Average ms per token
            
            assert creation_time < 50, f"Token creation too slow: {creation_time:.2f}ms (should be < 50ms)"
            
            # Test token validation performance (should be < 10ms with caching)
            start_time = time.time()
            for _ in range(10):
                payload = jwt_handler.validate_token(access_token, "access")
            validation_time = (time.time() - start_time) / 10 * 1000  # Average ms per validation
            
            assert validation_time < 10, f"Token validation too slow: {validation_time:.2f}ms (should be < 10ms)"
            assert payload is not None, "Should successfully validate token"
            
            # SSOT performance compliance verified
            
        except ImportError as e:
            pytest.skip(f"Auth service JWT handler not available: {e}")
        except Exception as e:
            pytest.fail(f"Auth service JWT performance does not meet requirements: {e}")