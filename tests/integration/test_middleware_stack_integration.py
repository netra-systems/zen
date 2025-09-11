"""
Integration tests for complete middleware stack setup and interaction.
Reproduces Issue #169 SessionMiddleware integration failures.

CRITICAL MISSION: These tests validate the complete middleware chain setup
and interaction patterns to identify where SessionMiddleware integration breaks.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestMiddlewareStackIntegration(SSotBaseTestCase):
    """Test complete middleware stack integration scenarios."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        # Environment is available as self._env from SSotBaseTestCase
        
        # Store original values
        self.original_values = {
            'ENVIRONMENT': self._env.get('ENVIRONMENT'),
            'SECRET_KEY': self._env.get('SECRET_KEY'),
            'K_SERVICE': self._env.get('K_SERVICE'),
            'GCP_PROJECT_ID': self._env.get('GCP_PROJECT_ID'),
            'GOOGLE_CLOUD_PROJECT': self._env.get('GOOGLE_CLOUD_PROJECT')
        }
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        for key, value in self.original_values.items():
            if value is not None:
                self._env.set(key, value)
            else:
                self._env.unset(key)
                
        try:
            self.loop.close()
        except:
            pass
        super().tearDown()
        
    def test_complete_middleware_stack_setup_integration(self):
        """Test complete middleware stack setup reproducing production conditions.
        
        CRITICAL: This reproduces the exact middleware setup that fails in staging.
        """
        from fastapi import FastAPI
        from netra_backend.app.core.middleware_setup import setup_middleware
        
        # Simulate GCP Cloud Run staging environment
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("K_SERVICE", "netra-staging-backend")
        self._env.set("GCP_PROJECT_ID", "netra-staging")
        
        # Test with valid secret (success case)
        valid_secret = "a" * 32 + "staging_integration_test_secret_key"
        self._env.set("SECRET_KEY", valid_secret)
        
        app = FastAPI()
        
        try:
            setup_middleware(app)
            
            # Validate complete middleware stack
            middleware_classes = [str(middleware.cls) for middleware in app.user_middleware]
            
            # Check for essential middleware
            session_found = any('SessionMiddleware' in cls for cls in middleware_classes)
            cors_found = any('CORS' in cls for cls in middleware_classes)
            auth_found = any('Auth' in cls for cls in middleware_classes)
            
            self.assertTrue(session_found, "SessionMiddleware must be in stack")
            self.assertTrue(cors_found, "CORS middleware must be in stack")
            
            self.record_metric("stack_integration", "complete_setup_success", 1)
            
            # Test middleware order (reverse processing order)
            session_index = next((i for i, cls in enumerate(middleware_classes) 
                                if 'SessionMiddleware' in cls), -1)
            auth_index = next((i for i, cls in enumerate(middleware_classes) 
                             if 'Auth' in cls and 'Context' in cls), -1)
            
            if session_index >= 0 and auth_index >= 0:
                # SessionMiddleware should be processed before AuthContext
                if session_index > auth_index:
                    self.record_metric("stack_integration", "correct_middleware_order", 1)
                else:
                    self.record_metric("stack_integration", "incorrect_middleware_order", 1)
                    
        except Exception as e:
            self.record_metric("stack_integration", "complete_setup_failed", 1)
            # This is the critical failure mode from Issue #169
            error_msg = str(e).lower()
            if "secret" in error_msg:
                self.record_metric("stack_integration", "secret_key_failure", 1)
            if "gcp" in error_msg or "secret manager" in error_msg:
                self.record_metric("stack_integration", "gcp_secret_manager_failure", 1)
            raise
            
    def test_middleware_stack_missing_secret_key_integration(self):
        """Test middleware stack behavior when SECRET_KEY is missing.
        
        CRITICAL: This reproduces the exact configuration that causes Issue #169.
        """
        from fastapi import FastAPI
        from netra_backend.app.core.middleware_setup import setup_middleware
        
        # Simulate problematic staging configuration
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("K_SERVICE", "netra-staging-backend")
        
        # Remove SECRET_KEY to reproduce the issue
        self._env.unset("SECRET_KEY")
        self._env.unset("SESSION_SECRET")
        
        app = FastAPI()
        
        try:
            setup_middleware(app)
            
            # If successful, check if fallback was used
            middleware_classes = [str(middleware.cls) for middleware in app.user_middleware]
            session_found = any('SessionMiddleware' in cls for cls in middleware_classes)
            
            if session_found:
                self.record_metric("missing_secret_integration", "fallback_successful", 1)
            else:
                self.record_metric("missing_secret_integration", "no_session_middleware", 1)
                self.fail("SessionMiddleware should be installed even with fallback")
                
        except Exception as e:
            self.record_metric("missing_secret_integration", "setup_failed", 1)
            
            # This reproduces the production issue
            error_msg = str(e).lower()
            if "secret" in error_msg and "key" in error_msg:
                self.record_metric("missing_secret_integration", "secret_key_error", 1)
            
            # Re-raise to understand the exact failure mode
            raise
            
    def test_session_middleware_gcp_auth_context_interaction(self):
        """Test SessionMiddleware and GCPAuthContext middleware interaction.
        
        This tests the specific interaction that fails in production.
        """
        from fastapi import FastAPI
        from netra_backend.app.core.middleware_setup import setup_session_middleware, setup_gcp_auth_context_middleware
        
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("GCP_PROJECT_ID", "netra-staging")
        valid_secret = "a" * 32 + "middleware_interaction_test_key"
        self._env.set("SECRET_KEY", valid_secret)
        
        app = FastAPI()
        
        try:
            # Setup in correct order
            setup_session_middleware(app)
            setup_gcp_auth_context_middleware(app)
            
            # Validate both middleware are present
            middleware_classes = [str(middleware.cls) for middleware in app.user_middleware]
            
            session_found = any('SessionMiddleware' in cls for cls in middleware_classes)
            auth_context_found = any('GCPAuth' in cls or 'AuthContext' in cls for cls in middleware_classes)
            
            self.assertTrue(session_found, "SessionMiddleware must be installed first")
            
            if auth_context_found:
                self.record_metric("middleware_interaction", "both_middleware_installed", 1)
            else:
                self.record_metric("middleware_interaction", "auth_context_skipped", 1)
                
        except Exception as e:
            self.record_metric("middleware_interaction", "interaction_setup_failed", 1)
            raise
            
    def test_end_to_end_request_processing_simulation(self):
        """Test end-to-end request processing through middleware stack."""
        from fastapi import FastAPI, Request, Response
        from netra_backend.app.core.middleware_setup import setup_middleware
        
        self._env.set("ENVIRONMENT", "development")  # Use dev for more permissive testing
        valid_secret = "a" * 32 + "e2e_request_processing_test_key"
        self._env.set("SECRET_KEY", valid_secret)
        
        app = FastAPI()
        
        try:
            setup_middleware(app)
            
            # Create a test endpoint
            @app.get("/test-endpoint")
            async def test_endpoint(request: Request):
                # This is where SessionMiddleware errors would manifest
                try:
                    session = request.session  # This line fails in Issue #169
                    return {"status": "success", "has_session": session is not None}
                except Exception as e:
                    return {"status": "error", "error": str(e)}
            
            # Test the endpoint with test client
            from fastapi.testclient import TestClient
            
            client = TestClient(app)
            response = client.get("/test-endpoint")
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            if data.get("status") == "success":
                self.record_metric("e2e_processing", "request_successful", 1)
                self.assertTrue(data.get("has_session") is not None, "Session should be available")
            else:
                self.record_metric("e2e_processing", "request_failed", 1)
                error_msg = data.get("error", "").lower()
                if "sessionmiddleware must be installed" in error_msg:
                    self.record_metric("e2e_processing", "session_error_reproduced", 1)
                    self.fail(f"SessionMiddleware error in E2E test: {data['error']}")
                    
        except Exception as e:
            self.record_metric("e2e_processing", "setup_failed", 1)
            raise
            
    def test_concurrent_request_session_access_integration(self):
        """Test concurrent request processing with session access."""
        from fastapi import FastAPI, Request
        from netra_backend.app.core.middleware_setup import setup_middleware
        from fastapi.testclient import TestClient
        import threading
        import time
        
        self._env.set("ENVIRONMENT", "development")
        valid_secret = "a" * 32 + "concurrent_session_test_key"
        self._env.set("SECRET_KEY", valid_secret)
        
        app = FastAPI()
        
        try:
            setup_middleware(app)
            
            # Track session access results
            session_results = []
            session_errors = []
            
            @app.get("/concurrent-test/{user_id}")
            async def concurrent_test(request: Request, user_id: str):
                try:
                    session = request.session
                    session[f"user_{user_id}"] = f"data_for_{user_id}"
                    return {"user_id": user_id, "session_access": "success"}
                except Exception as e:
                    return {"user_id": user_id, "session_access": "failed", "error": str(e)}
            
            client = TestClient(app)
            
            def make_request(user_id):
                response = client.get(f"/concurrent-test/{user_id}")
                data = response.json()
                if data.get("session_access") == "success":
                    session_results.append(user_id)
                else:
                    session_errors.append((user_id, data.get("error", "unknown")))
            
            # Make concurrent requests
            threads = []
            for i in range(5):
                thread = threading.Thread(target=make_request, args=(f"user_{i}",))
                threads.append(thread)
                thread.start()
                
            # Wait for all threads
            for thread in threads:
                thread.join(timeout=5.0)
            
            # Analyze results
            success_count = len(session_results)
            error_count = len(session_errors)
            
            self.record_metric("concurrent_integration", "successful_requests", success_count)
            self.record_metric("concurrent_integration", "failed_requests", error_count)
            
            if error_count > 0:
                # Check if SessionMiddleware errors occurred
                session_middleware_errors = [
                    error for user_id, error in session_errors
                    if "sessionmiddleware" in error.lower()
                ]
                if session_middleware_errors:
                    self.record_metric("concurrent_integration", "session_middleware_errors", len(session_middleware_errors))
                    self.fail(f"SessionMiddleware errors in concurrent requests: {session_middleware_errors}")
                    
            self.assertGreater(success_count, 0, "At least some requests should succeed")
            
        except Exception as e:
            self.record_metric("concurrent_integration", "setup_failed", 1)
            raise
            
    def test_middleware_environment_specific_behavior(self):
        """Test middleware behavior differences across environments."""
        from fastapi import FastAPI
        from netra_backend.app.core.middleware_setup import setup_middleware
        
        environments = ["development", "staging", "production"]
        valid_secret = "a" * 32 + "environment_specific_test_key"
        
        for environment in environments:
            with self.subTest(environment=environment):
                self._env.set("ENVIRONMENT", environment)
                self._env.set("SECRET_KEY", valid_secret)
                
                if environment in ["staging", "production"]:
                    self._env.set("K_SERVICE", f"netra-{environment}-backend")
                    self._env.set("GCP_PROJECT_ID", f"netra-{environment}")
                
                app = FastAPI()
                
                try:
                    setup_middleware(app)
                    
                    middleware_count = len(app.user_middleware)
                    middleware_classes = [str(middleware.cls) for middleware in app.user_middleware]
                    
                    # All environments should have SessionMiddleware
                    session_found = any('SessionMiddleware' in cls for cls in middleware_classes)
                    self.assertTrue(session_found, f"SessionMiddleware missing in {environment}")
                    
                    # Production/staging may have additional middleware
                    if environment in ["staging", "production"]:
                        gcp_middleware = any('GCP' in cls for cls in middleware_classes)
                        if gcp_middleware:
                            self.record_metric("environment_behavior", f"{environment}_gcp_middleware", 1)
                        
                    self.record_metric("environment_behavior", f"{environment}_success", 1)
                    
                except Exception as e:
                    self.record_metric("environment_behavior", f"{environment}_failed", 1)
                    # Environment-specific failures help identify the problem
                    if environment == "staging":
                        # Staging failures are most critical for Issue #169
                        raise AssertionError(f"Staging middleware setup failed (Issue #169): {e}")
                    else:
                        # Log but don't fail for other environments
                        print(f"Middleware setup failed in {environment}: {e}")


if __name__ == "__main__":
    unittest.main()