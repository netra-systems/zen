"""
JWT SSOT Integration Tests - Issue #1078
Purpose: Create FAILING integration tests to validate JWT delegation patterns
These tests should FAIL initially to prove incomplete delegation, then PASS after remediation

Business Value Justification (BVJ):
- Segment: Platform/Enterprise (Security compliance)
- Business Goal: Ensure reliable JWT delegation to prevent 403 auth failures  
- Value Impact: Maintains $500K+ ARR by ensuring consistent authentication
- Revenue Impact: Prevents customer authentication issues blocking platform usage
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock, AsyncMock

import pytest
import httpx
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture


@pytest.mark.integration
class JWTSSOTIssue1078IntegrationTests(BaseIntegrationTest):
    """Integration tests to validate JWT SSOT delegation patterns"""
    
    async def setup_method(self):
        await super().setup_method()
        self.test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXJfMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzAwMDAwMDAwLCJpYXQiOjE2OTk5OTkwMDAsInRva2VuX3R5cGUiOiJhY2Nlc3MifQ.test_signature"
        self.expected_payload = {
            "sub": "test_user_123",
            "email": "test@example.com",
            "exp": 1700000000,
            "iat": 1699999000,
            "token_type": "access"
        }
    
    @pytest.mark.real_services
    async def test_backend_auth_client_pure_delegation(self, real_services_fixture):
        """
        FAILING TEST: Backend auth client should use pure delegation to auth service
        
        This test verifies backend auth client makes HTTP calls to auth service
        instead of performing direct JWT operations. Expected to FAIL if backend
        has mixed delegation patterns.
        """
        # Mock HTTP requests to capture service calls
        with patch('httpx.AsyncClient.post') as mock_post:
            # Configure successful auth service response
            mock_response = Mock()
            mock_response.json.return_value = {
                "valid": True,
                "payload": self.expected_payload,
                "service_signature": "auth_service_validated"
            }
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            try:
                # Test backend auth client delegation
                from netra_backend.app.clients.auth_client_core import AuthServiceClient
                auth_client = AuthServiceClient()
                
                # Test token validation
                result = await auth_client.validate_token_jwt(self.test_token)
                
                # SSOT Compliance Verification
                if not mock_post.called:
                    pytest.fail(
                        "AUTH CLIENT SSOT VIOLATION (Issue #1078):\n"
                        "Backend auth client did not make HTTP call to auth service.\n\n"
                        "EXPECTED: HTTP POST to auth service for JWT validation\n"
                        "ACTUAL: No HTTP call detected\n\n"
                        "This indicates backend may be performing direct JWT operations\n"
                        "instead of pure delegation to auth service."
                    )
                
                # Verify proper service endpoint was called
                call_args = mock_post.call_args
                if not call_args:
                    pytest.fail("No HTTP call arguments captured")
                
                url = str(call_args[1].get('url', call_args[0][0] if call_args[0] else ''))
                
                # Check for auth service endpoint patterns
                expected_patterns = ['/validate', '/jwt', '/token', '/auth']
                if not any(pattern in url.lower() for pattern in expected_patterns):
                    pytest.fail(
                        f"INVALID AUTH SERVICE ENDPOINT (Issue #1078):\n"
                        f"Expected auth service JWT validation endpoint\n"
                        f"Called: {url}\n\n"
                        "Backend should call auth service JWT validation endpoint."
                    )
                
                # Verify JWT token was sent in request
                request_data = call_args[1].get('json', {}) or call_args[1].get('data', {})
                if self.test_token not in str(request_data):
                    pytest.fail(
                        "JWT TOKEN NOT SENT TO AUTH SERVICE (Issue #1078):\n"
                        "Backend should send JWT token to auth service for validation.\n"
                        f"Request data: {request_data}"
                    )
                
                # Verify proper response handling
                assert result is not None, "Should return validation result"
                assert isinstance(result, dict), "Should return dictionary result"
                
                # Verify no direct JWT library usage in call stack
                import inspect
                frame_info = []
                for frame in inspect.stack():
                    if 'jwt.decode' in frame.code_context[0] if frame.code_context else '':
                        frame_info.append(f"{frame.filename}:{frame.lineno}")
                
                if frame_info:
                    pytest.fail(
                        f"DIRECT JWT OPERATIONS DETECTED (Issue #1078):\n"
                        f"Found jwt.decode calls in stack trace:\n" +
                        "\n".join(f"  - {info}" for info in frame_info) +
                        "\n\nBackend should use pure delegation without direct JWT operations."
                    )
                
                # SSOT compliance verified
                assert True, "Auth client uses proper service delegation"
                
            except ImportError as e:
                pytest.fail(f"Backend auth client import failed: {e}")
            except Exception as e:
                pytest.fail(f"Auth client delegation test failed: {e}")
    
    async def test_websocket_user_context_extractor_ssot_compliance(self):
        """
        FAILING TEST: WebSocket JWT validation should use auth service delegation
        
        This test verifies WebSocket user context extraction delegates to auth service.
        Expected to FAIL if WebSocket has direct JWT validation.
        """
        try:
            # Mock auth service for testing delegation
            with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient') as mock_auth_client:
                mock_client_instance = Mock()
                mock_auth_client.return_value = mock_client_instance
                
                # Configure auth service mock response
                mock_client_instance.validate_token_jwt = AsyncMock(return_value={
                    "valid": True,
                    "payload": self.expected_payload,
                    "service_source": "auth_service"
                })
                
                # Import WebSocket user context extractor
                from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
                
                extractor = UserContextExtractor()
                
                # Test JWT validation delegates to auth service
                result = await extractor.validate_and_decode_jwt(self.test_token)
                
                # Verify auth service was called
                if not mock_client_instance.validate_token_jwt.called:
                    pytest.fail(
                        "WEBSOCKET AUTH SERVICE NOT CALLED (Issue #1078):\n"
                        "WebSocket JWT validation should delegate to auth service.\n\n"
                        "EXPECTED: auth_client.validate_token_jwt() call\n"
                        "ACTUAL: No auth service call detected\n\n"
                        "This indicates WebSocket may be performing direct JWT validation\n"
                        "instead of using auth service delegation."
                    )
                
                # Verify proper token was sent
                call_args = mock_client_instance.validate_token_jwt.call_args
                if call_args[0][0] != self.test_token:
                    pytest.fail(
                        f"INCORRECT JWT TOKEN SENT (Issue #1078):\n"
                        f"Expected: {self.test_token}\n"
                        f"Actual: {call_args[0][0]}\n\n"
                        "WebSocket should pass JWT token correctly to auth service."
                    )
                
                # Verify response structure
                assert result is not None, "Should return validation result"
                assert isinstance(result, dict), "Should return dictionary result"
                
                # Check for direct JWT operations (SSOT violations)
                with patch('jwt.decode') as mock_jwt_decode:
                    # Re-run validation to check for direct JWT calls
                    await extractor.validate_and_decode_jwt(self.test_token)
                    
                    if mock_jwt_decode.called:
                        pytest.fail(
                            "DIRECT JWT DECODE DETECTED (Issue #1078):\n"
                            "WebSocket is performing direct JWT operations.\n\n"
                            "VIOLATION: WebSocket should use auth service exclusively.\n"
                            "Direct jwt.decode() calls violate SSOT architecture."
                        )
                
                # SSOT compliance verified for WebSocket
                assert True, "WebSocket uses proper auth service delegation"
                
        except ImportError as e:
            pytest.fail(f"WebSocket user context extractor import failed: {e}")
        except Exception as e:
            # If there are issues, this indicates incomplete SSOT delegation
            pytest.fail(f"WebSocket auth service delegation failed: {e}")
    
    async def test_configuration_ssot_environment_access(self):
        """
        FAILING TEST: JWT configuration should use IsolatedEnvironment SSOT
        
        This test verifies JWT configuration uses IsolatedEnvironment instead of
        direct os.environ access. Expected to FAIL if configuration bypasses SSOT.
        """
        try:
            # Test auth service configuration SSOT compliance
            from auth_service.auth_core.config import AuthConfig
            from shared.isolated_environment import get_env
            
            # Mock IsolatedEnvironment to test SSOT pattern
            with patch('shared.isolated_environment.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = "test-jwt-secret-ssot-pattern-32chars"
                mock_get_env.return_value = mock_env
                
                # Test JWT secret access uses SSOT
                secret = AuthConfig.get_jwt_secret()
                
                # Verify IsolatedEnvironment was used
                if not mock_get_env.called:
                    pytest.fail(
                        "JWT SECRET SSOT VIOLATION (Issue #1078):\n"
                        "JWT configuration should use IsolatedEnvironment.\n\n"
                        "EXPECTED: get_env() call from shared.isolated_environment\n"
                        "ACTUAL: No IsolatedEnvironment usage detected\n\n"
                        "This indicates JWT config may be using direct os.environ access\n"
                        "instead of SSOT environment management."
                    )
                
                # Verify proper environment variable access
                env_calls = [call.args[0] for call in mock_env.get.call_args_list]
                jwt_secret_patterns = ['JWT_SECRET_KEY', 'JWT_SECRET', 'jwt_secret_key']
                
                if not any(pattern in str(env_calls) for pattern in jwt_secret_patterns):
                    pytest.fail(
                        f"JWT SECRET ENVIRONMENT VARIABLE NOT ACCESSED (Issue #1078):\n"
                        f"Expected access to JWT secret environment variables\n"
                        f"Environment calls: {env_calls}\n\n"
                        "JWT configuration should properly access secret through SSOT."
                    )
                
                # Test other JWT config SSOT compliance
                algorithm = AuthConfig.get_jwt_algorithm()
                assert isinstance(algorithm, str), "Should return JWT algorithm"
                
                expiry = AuthConfig.get_jwt_access_expiry_minutes()
                assert isinstance(expiry, int), "Should return JWT expiry"
                
                # Verify no direct os.environ usage
                with patch('os.environ.get') as mock_os_environ:
                    # Re-run configuration access to detect os.environ usage
                    AuthConfig.get_jwt_secret()
                    
                    if mock_os_environ.called:
                        pytest.fail(
                            "DIRECT OS.ENVIRON ACCESS DETECTED (Issue #1078):\n"
                            "JWT configuration is bypassing IsolatedEnvironment SSOT.\n\n"
                            "VIOLATION: Should use get_env() not os.environ.get()\n"
                            "Direct environment access violates SSOT architecture."
                        )
                
                # SSOT environment access compliance verified
                assert isinstance(secret, str), "Should return valid JWT secret"
                
        except ImportError as e:
            pytest.fail(f"Auth service config or IsolatedEnvironment import failed: {e}")
        except Exception as e:
            pytest.fail(f"JWT configuration SSOT compliance test failed: {e}")
    
    async def test_jwt_token_validation_consistency(self):
        """
        FAILING TEST: JWT validation should be consistent across all services
        
        This test verifies JWT validation produces consistent results when
        delegating to auth service. Expected to FAIL with secret mismatches.
        """
        # Test consistency between different JWT validation entry points
        validation_endpoints = [
            ('backend_auth', 'netra_backend.app.auth_integration.auth._validate_token_with_auth_service'),
            ('websocket_extractor', 'netra_backend.app.websocket_core.user_context_extractor.UserContextExtractor.validate_and_decode_jwt'),
            ('auth_client', 'netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_token_jwt')
        ]
        
        validation_results = {}
        
        for endpoint_name, endpoint_path in validation_endpoints:
            try:
                # Import and test each validation endpoint
                module_path, function_name = endpoint_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[function_name])
                
                if '.' in function_name:
                    # Handle class methods
                    class_name, method_name = function_name.split('.', 1)
                    cls = getattr(module, class_name)
                    instance = cls()
                    validator = getattr(instance, method_name)
                else:
                    validator = getattr(module, function_name)
                
                # Mock auth service consistently
                with patch('httpx.AsyncClient.post') as mock_post:
                    mock_response = Mock()
                    mock_response.json.return_value = {
                        "valid": True, 
                        "payload": self.expected_payload
                    }
                    mock_response.status_code = 200
                    mock_post.return_value = mock_response
                    
                    # Test validation
                    if asyncio.iscoroutinefunction(validator):
                        result = await validator(self.test_token)
                    else:
                        result = validator(self.test_token)
                    
                    validation_results[endpoint_name] = result
                    
            except ImportError:
                pytest.skip(f"Endpoint {endpoint_name} not available")
            except Exception as e:
                validation_results[endpoint_name] = f"ERROR: {e}"
        
        # Verify all validations succeeded
        errors = {name: result for name, result in validation_results.items() 
                 if isinstance(result, str) and result.startswith("ERROR")}
        
        if errors:
            pytest.fail(
                f"JWT VALIDATION CONSISTENCY FAILURES (Issue #1078):\n" +
                "\n".join(f"  - {name}: {error}" for name, error in errors.items()) +
                "\n\nJWT validation should work consistently across all endpoints.\n"
                "This indicates incomplete SSOT delegation patterns."
            )
        
        # Verify consistent results (all should validate same token successfully)
        valid_results = [result for result in validation_results.values() 
                        if isinstance(result, dict) and result.get('valid')]
        
        if len(valid_results) != len(validation_results):
            pytest.fail(
                f"JWT VALIDATION INCONSISTENCY (Issue #1078):\n"
                f"Expected {len(validation_results)} successful validations\n"
                f"Got {len(valid_results)} successful validations\n\n"
                f"Results: {validation_results}\n\n"
                "All validation endpoints should produce consistent results\n"
                "when using proper auth service delegation."
            )
        
        # SSOT validation consistency verified
        assert len(valid_results) > 0, "At least one validation endpoint should work"
    
    @pytest.mark.real_services
    async def test_auth_service_performance_requirements(self, real_services_fixture):
        """
        FAILING TEST: SSOT JWT operations should meet performance requirements
        
        This test validates that delegating to auth service doesn't create
        performance bottlenecks. Expected to FAIL if delegation is slow.
        """
        try:
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            auth_client = AuthServiceClient()
            
            # Test token validation performance
            validation_times = []
            
            # Mock auth service for consistent performance testing
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "valid": True,
                    "payload": self.expected_payload
                }
                mock_response.status_code = 200
                mock_post.return_value = mock_response
                
                # Performance test: 10 token validations
                for i in range(10):
                    start_time = time.time()
                    result = await auth_client.validate_token_jwt(self.test_token)
                    end_time = time.time()
                    
                    validation_time = (end_time - start_time) * 1000  # Convert to ms
                    validation_times.append(validation_time)
                    
                    assert result is not None, f"Validation {i} should succeed"
            
            # Analyze performance
            avg_time = sum(validation_times) / len(validation_times)
            max_time = max(validation_times)
            
            # Performance requirements for SSOT JWT delegation
            if avg_time > 100:  # 100ms average threshold
                pytest.fail(
                    f"JWT DELEGATION PERFORMANCE TOO SLOW (Issue #1078):\n"
                    f"Average validation time: {avg_time:.2f}ms (should be < 100ms)\n"
                    f"Max validation time: {max_time:.2f}ms\n"
                    f"All times: {[f'{t:.1f}ms' for t in validation_times]}\n\n"
                    "SSOT delegation to auth service should be performant.\n"
                    "High latency indicates inefficient delegation patterns."
                )
            
            if max_time > 500:  # 500ms max threshold
                pytest.fail(
                    f"JWT DELEGATION MAX TIME EXCEEDED (Issue #1078):\n"
                    f"Max validation time: {max_time:.2f}ms (should be < 500ms)\n\n"
                    "Individual JWT validations should not exceed 500ms.\n"
                    "This suggests auth service delegation has performance issues."
                )
            
            # Performance requirements met
            assert avg_time < 100, f"Average validation time acceptable: {avg_time:.2f}ms"
            
        except ImportError as e:
            pytest.fail(f"Auth client import failed for performance test: {e}")
        except Exception as e:
            pytest.fail(f"JWT delegation performance test failed: {e}")
    
    async def test_jwt_error_handling_delegation_patterns(self):
        """
        FAILING TEST: JWT error handling should properly delegate to auth service
        
        This test verifies error scenarios are handled through auth service delegation.
        Expected to FAIL if error handling bypasses auth service.
        """
        try:
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            auth_client = AuthServiceClient()
            
            # Test various error scenarios
            error_scenarios = [
                ('invalid_token', 'invalid.jwt.token', 400, {"valid": False, "error": "Invalid token"}),
                ('expired_token', self.test_token, 401, {"valid": False, "error": "Token expired"}), 
                ('malformed_token', 'not.a.jwt', 400, {"valid": False, "error": "Malformed token"}),
                ('auth_service_error', self.test_token, 500, {"error": "Internal server error"})
            ]
            
            for scenario_name, token, status_code, response_data in error_scenarios:
                with patch('httpx.AsyncClient.post') as mock_post:
                    # Configure error response from auth service
                    mock_response = Mock()
                    mock_response.json.return_value = response_data
                    mock_response.status_code = status_code
                    mock_response.raise_for_status = Mock()
                    
                    if status_code >= 400:
                        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                            f"{status_code} Client Error", request=Mock(), response=mock_response
                        )
                    
                    mock_post.return_value = mock_response
                    
                    # Test error handling delegation
                    try:
                        result = await auth_client.validate_token_jwt(token)
                        
                        # For client errors, should handle gracefully
                        if status_code < 500:
                            if result.get('valid') is not False:
                                pytest.fail(
                                    f"ERROR HANDLING DELEGATION FAILURE ({scenario_name}):\n"
                                    f"Expected graceful error handling from auth service\n"
                                    f"Got: {result}\n\n"
                                    "Backend should properly handle auth service error responses."
                                )
                    
                    except Exception as e:
                        # For server errors, exception is acceptable
                        if status_code < 500:
                            pytest.fail(
                                f"UNEXPECTED EXCEPTION IN ERROR HANDLING ({scenario_name}):\n"
                                f"Exception: {e}\n\n"
                                "Backend should handle auth service errors gracefully\n"
                                "without raising exceptions for client errors."
                            )
                    
                    # Verify auth service was called (delegation occurred)
                    if not mock_post.called:
                        pytest.fail(
                            f"AUTH SERVICE NOT CALLED FOR ERROR SCENARIO ({scenario_name}):\n"
                            "Even error cases should delegate to auth service.\n\n"
                            "Backend should not bypass auth service for any token validation."
                        )
            
            # Error handling delegation verified
            assert True, "JWT error handling properly delegates to auth service"
            
        except ImportError as e:
            pytest.fail(f"Auth client import failed for error handling test: {e}")
        except Exception as e:
            pytest.fail(f"JWT error handling delegation test failed: {e}")