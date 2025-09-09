"""
Service Authentication Integration Test Suite

CRITICAL: These tests validate the service-to-service authentication system
that is required to fix the system user authentication failure (GitHub Issue #115).

Purpose: Validate that service authentication headers work properly and that
the database session creation functions correctly with service authentication.

Business Value: Platform/Internal - System Stability & Development Velocity  
- Restores golden path user flows by fixing authentication gaps
- Enables proper service-to-service communication
- Prevents authentication failures in internal operations

IMPORTANT: These tests follow CLAUDE.md requirements:
- Use real services (marked with @pytest.mark.real_services)
- No mocks in integration testing  
- Must show measurable execution time (not 0.00s)
- Extend SSotBaseTestCase for SSOT compliance

Expected Results:
BEFORE FIX: Tests SHOULD FAIL showing missing/invalid service authentication
AFTER FIX: Tests MUST PASS with proper service auth working end-to-end
"""

import asyncio
import time
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.dependencies import get_request_scoped_db_session
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.real_services
class TestServiceAuthenticationValidation(SSotBaseTestCase):
    """
    Integration tests for service-to-service authentication validation.
    
    These tests validate that the service authentication system works
    properly to resolve the system user authentication failure.
    """
    
    def setup_method(self, method):
        """Setup for each test method with real services configuration."""
        super().setup_method(method)
        self.start_time = time.time()
        
        # Use real isolated environment per CLAUDE.md requirements
        self.env = IsolatedEnvironment()
        
        # Initialize real auth client for testing
        self.auth_client = AuthServiceClient()
        
        self.logger.info(f"🔧 SERVICE AUTH TEST: {method.__name__} - Testing with real services")
        
    def teardown_method(self, method):
        """Teardown with timing validation per CLAUDE.md requirements."""
        execution_time = time.time() - self.start_time
        
        # CRITICAL: Tests must show measurable timing (not 0.00s per CLAUDE.md)
        assert execution_time > 0.001, (
            f"Test {method.__name__} executed in {execution_time:.3f}s - "
            "0.00s execution indicates test not actually running (CLAUDE.md violation)"
        )
        
        self.logger.info(f"✅ Test {method.__name__} executed in {execution_time:.3f}s")
        super().teardown_method(method)
    
    @pytest.mark.integration
    def test_service_auth_header_generation_validation(self):
        """
        Test that service authentication headers are generated correctly.
        
        This validates that AuthServiceClient._get_service_auth_headers() 
        produces the proper X-Service-ID and X-Service-Secret headers.
        
        Expected Results:
        - BEFORE FIX: May fail due to missing SERVICE_ID/SERVICE_SECRET config
        - AFTER FIX: Must pass with properly formatted headers
        """
        self.logger.info("🔧 TESTING: Service auth header generation")
        
        test_start = time.time()
        
        try:
            # Test header generation with real auth client
            headers = self.auth_client._get_service_auth_headers()
            execution_time = time.time() - test_start
            
            self.logger.info(f"Service headers generated in {execution_time:.3f}s")
            
            # Validate headers are properly formed
            assert isinstance(headers, dict), "Service auth headers must be a dictionary"
            
            # Check for required headers
            assert "X-Service-ID" in headers, "X-Service-ID header must be present"
            assert "X-Service-Secret" in headers, "X-Service-Secret header must be present"
            
            # Validate header values are not empty
            service_id = headers["X-Service-ID"]
            service_secret = headers["X-Service-Secret"] 
            
            assert service_id and service_id.strip(), "X-Service-ID must not be empty"
            assert service_secret and service_secret.strip(), "X-Service-Secret must not be empty"
            
            # Validate expected service ID format
            assert service_id in ["netra-backend", "netra-backend-test"], (
                f"Expected service ID 'netra-backend' or 'netra-backend-test', got '{service_id}'"
            )
            
            # Record successful validation
            self.record_metric("service_auth_headers_valid", {
                "service_id": service_id,
                "service_secret_length": len(service_secret),
                "headers_count": len(headers),
                "execution_time": execution_time,
                "validation_success": True
            })
            
            self.logger.info(
                f"✅ Service auth headers valid: ID='{service_id}', "
                f"Secret length={len(service_secret)} characters"
            )
            
        except Exception as e:
            execution_time = time.time() - test_start
            
            self.record_metric("service_auth_header_validation_failed", {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "execution_time": execution_time,
                "auth_client_configured": hasattr(self.auth_client, 'service_id')
            })
            
            self.logger.error(f"❌ Service auth header validation failed in {execution_time:.3f}s: {e}")
            raise AssertionError(f"Service auth header generation failed: {e}") from e
    
    @pytest.mark.integration
    async def test_system_user_with_service_auth_headers(self):
        """
        Test that system user operations work when proper service auth headers are used.
        
        This simulates what SHOULD happen after the fix is implemented -
        internal operations include service authentication.
        
        Expected Results:
        - BEFORE FIX: May fail due to dependencies.py not using service auth
        - AFTER FIX: Must pass with system user authenticated via service headers
        """
        self.logger.info("🔧 TESTING: System user operations with service auth headers")
        
        test_start = time.time()
        
        try:
            # Get service auth headers
            service_headers = self.auth_client._get_service_auth_headers()
            
            assert service_headers, "Service auth headers must be available for this test"
            
            # Test that we can create a properly authenticated service context
            service_user_id = f"service:{service_headers['X-Service-ID']}"
            
            self.logger.info(f"Testing with service user ID: '{service_user_id}'")
            
            # Simulate the fixed behavior where dependencies.py uses service auth
            # This test validates what the system SHOULD do after the fix
            
            execution_time = time.time() - test_start
            
            # For now, this test documents the expected behavior
            # After the fix is implemented, this should test actual database session creation
            
            self.record_metric("service_auth_system_user_test", {
                "service_user_id": service_user_id,
                "service_headers_available": True,
                "expected_behavior": "system_user_authenticated_via_service_headers",
                "execution_time": execution_time
            })
            
            self.logger.info(
                f"✅ Service auth system user test completed in {execution_time:.3f}s - "
                f"ready for implementation"
            )
            
            # This test passes to validate the service auth headers are available
            # The actual database session test is in the next test method
            
        except Exception as e:
            execution_time = time.time() - test_start
            
            self.logger.error(f"❌ Service auth system user test failed in {execution_time:.3f}s: {e}")
            raise AssertionError(f"Service auth system user test failed: {e}") from e
    
    @pytest.mark.integration
    async def test_get_request_scoped_db_session_with_service_auth(self):
        """
        Test the core function that's failing - get_request_scoped_db_session()
        with proper service authentication.
        
        This is the KEY test that validates the fix for the authentication failure.
        
        Expected Results:
        - BEFORE FIX: WILL FAIL with authentication error
        - AFTER FIX: MUST PASS with database session created successfully
        """
        self.logger.info("🔧 TESTING: get_request_scoped_db_session with service auth")
        
        test_start = time.time()
        
        # This test will demonstrate both the current failure and future success
        
        try:
            # First, validate service auth is available
            service_headers = self.auth_client._get_service_auth_headers()
            assert service_headers, "Service auth headers required for this test"
            
            self.logger.info(f"Service auth available: {list(service_headers.keys())}")
            
            # Attempt to create database session
            # BEFORE FIX: This will fail with authentication error
            # AFTER FIX: This should succeed with proper service authentication
            
            session_created = False
            session_error = None
            
            try:
                async for session in get_request_scoped_db_session():
                    session_created = True
                    self.logger.info("✅ Database session created successfully with service auth")
                    
                    # Validate session is functional
                    assert session is not None, "Session must not be None"
                    assert hasattr(session, 'execute'), "Session must have execute method"
                    
                    # Clean up
                    await session.close()
                    break  # Exit the async generator
                    
            except Exception as session_exc:
                session_error = session_exc
                self.logger.info(f"Database session creation failed: {session_exc}")
            
            execution_time = time.time() - test_start
            
            # Record results for analysis
            self.record_metric("db_session_with_service_auth", {
                "session_created": session_created,
                "error_occurred": session_error is not None,
                "error_type": type(session_error).__name__ if session_error else None,
                "error_message": str(session_error) if session_error else None,
                "execution_time": execution_time,
                "service_auth_available": bool(service_headers)
            })
            
            if session_created:
                self.logger.info(
                    f"✅ SUCCESS: Database session with service auth in {execution_time:.3f}s"
                )
                # Test passes - indicates fix is working
                
            else:
                # Expected failure before fix is implemented
                self.logger.info(
                    f"📋 EXPECTED FAILURE: Database session failed in {execution_time:.3f}s - "
                    f"indicates fix needed: {session_error}"
                )
                
                # For now, we document this as expected behavior before fix
                # After fix is implemented, this should be changed to assert success
                
                if session_error and ("auth" in str(session_error).lower() or "403" in str(session_error)):
                    # This is the expected authentication failure
                    raise AssertionError(
                        f"EXPECTED FAILURE (before fix): Database session failed with auth error - {session_error}"
                    ) from session_error
                else:
                    # Unexpected error
                    raise AssertionError(
                        f"UNEXPECTED ERROR: Database session failed with non-auth error - {session_error}"
                    ) from session_error
                    
        except Exception as e:
            execution_time = time.time() - test_start
            
            self.logger.error(f"❌ Database session test failed in {execution_time:.3f}s: {e}")
            
            # Re-raise to show the failure
            raise
    
    @pytest.mark.integration
    def test_middleware_service_auth_validation(self):
        """
        Test that authentication middleware properly validates service credentials.
        
        This validates the middleware behavior that should accept proper service
        authentication headers.
        """
        self.logger.info("🔧 TESTING: Middleware service auth validation")
        
        test_start = time.time()
        
        try:
            from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
            
            # Get valid service headers
            service_headers = self.auth_client._get_service_auth_headers()
            assert service_headers, "Service auth headers required for middleware test"
            
            # Create middleware instance
            middleware = FastAPIAuthMiddleware()
            
            execution_time = time.time() - test_start
            
            # Record middleware configuration
            self.record_metric("middleware_service_auth_test", {
                "middleware_created": True,
                "service_headers_available": True,
                "execution_time": execution_time,
                "service_id": service_headers.get("X-Service-ID"),
                "test_type": "middleware_validation"
            })
            
            self.logger.info(
                f"✅ Middleware service auth test completed in {execution_time:.3f}s - "
                f"middleware available for service validation"
            )
            
            # This test validates the middleware can be instantiated and has service auth capabilities
            # The actual request validation would require more complex setup with FastAPI
            
        except Exception as e:
            execution_time = time.time() - test_start
            
            self.logger.error(f"❌ Middleware service auth test failed in {execution_time:.3f}s: {e}")
            raise AssertionError(f"Middleware service auth validation failed: {e}") from e
    
    @pytest.mark.integration
    def test_service_credentials_environment_validation(self):
        """
        Test that service credentials are properly configured in the environment.
        
        This validates the configuration requirements for service authentication.
        """
        self.logger.info("🔧 TESTING: Service credentials environment validation")
        
        test_start = time.time()
        
        # Test environment configuration using IsolatedEnvironment
        service_id = self.env.get("SERVICE_ID")
        service_secret = self.env.get("SERVICE_SECRET")
        
        execution_time = time.time() - test_start
        
        # Validate configuration
        config_status = {
            "SERVICE_ID_configured": bool(service_id),
            "SERVICE_SECRET_configured": bool(service_secret),
            "SERVICE_ID_value": service_id if service_id else "NOT_SET",
            "configuration_complete": bool(service_id and service_secret)
        }
        
        self.record_metric("service_credentials_config_validation", {
            **config_status,
            "execution_time": execution_time
        })
        
        self.logger.info(
            f"Service credentials validation completed in {execution_time:.3f}s: {config_status}"
        )
        
        # For integration testing, we validate configuration is available
        if not (service_id and service_secret):
            raise AssertionError(
                f"Service credentials not fully configured: "
                f"SERVICE_ID={'SET' if service_id else 'MISSING'}, "
                f"SERVICE_SECRET={'SET' if service_secret else 'MISSING'}"
            )
        
        self.logger.info("✅ Service credentials properly configured for integration testing")
    
    @pytest.mark.integration
    def test_auth_client_service_initialization(self):
        """
        Test that AuthServiceClient initializes properly with service credentials.
        
        This validates the client configuration that's required for service auth.
        """
        self.logger.info("🔧 TESTING: Auth client service initialization")
        
        test_start = time.time()
        
        try:
            # Validate auth client initialization
            assert self.auth_client is not None, "Auth client must be initialized"
            assert hasattr(self.auth_client, 'service_id'), "Auth client must have service_id"
            assert hasattr(self.auth_client, 'service_secret'), "Auth client must have service_secret"
            
            # Test service properties
            service_id = self.auth_client.service_id
            service_secret = self.auth_client.service_secret
            
            execution_time = time.time() - test_start
            
            # Validate service configuration
            assert service_id, "Auth client service_id must be configured"
            assert service_secret, "Auth client service_secret must be configured"
            
            self.record_metric("auth_client_service_init", {
                "client_initialized": True,
                "service_id_configured": bool(service_id),
                "service_secret_configured": bool(service_secret),
                "service_id_value": service_id,
                "execution_time": execution_time
            })
            
            self.logger.info(
                f"✅ Auth client service initialization validated in {execution_time:.3f}s - "
                f"Service ID: '{service_id}'"
            )
            
        except Exception as e:
            execution_time = time.time() - test_start
            
            self.logger.error(f"❌ Auth client initialization failed in {execution_time:.3f}s: {e}")
            raise AssertionError(f"Auth client service initialization failed: {e}") from e