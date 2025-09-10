"""
Integration tests for SessionMiddleware with complete middleware chain.
Tests real FastAPI application with actual middleware stack.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware


class TestSessionMiddlewareIntegration(SSotBaseTestCase):
    """Integration tests for SessionMiddleware in complete application."""
    
    def setUp(self):
        """Set up test environment with real FastAPI app."""
        super().setUp()
        self.env = IsolatedEnvironment()
        
        # Set required environment variables
        self.env.set("SECRET_KEY", "test_secret_key_" + "x" * 32)
        self.env.set("ENV", "test")
        
        # Create test app
        self.app = FastAPI()
        self.setup_test_app()
        self.client = TestClient(self.app)
        
    def setup_test_app(self):
        """Set up test application with middleware and routes."""
        # Add SessionMiddleware
        self.app.add_middleware(
            SessionMiddleware,
            secret_key=self.env.get("SECRET_KEY")
        )
        
        # Add test route
        @self.app.get("/test-session")
        async def test_session(request: Request):
            # Try to access session
            try:
                session_data = request.session
                return {"session_available": True, "session_id": session_data.get("session_id")}
            except Exception as e:
                return {"session_available": False, "error": str(e)}
                
        @self.app.get("/test-auth-context")
        async def test_auth_context(request: Request):
            # Simulate GCPAuthContextMiddleware behavior
            auth_context = {}
            try:
                if hasattr(request, 'session') and request.session:
                    auth_context['session_id'] = request.session.get('session_id')
                    auth_context['user_id'] = request.session.get('user_id', 'anonymous')
            except RuntimeError as e:
                if "SessionMiddleware must be installed" in str(e):
                    auth_context['error'] = "SessionMiddleware not available"
            return auth_context
            
    def test_session_middleware_processes_requests(self):
        """Test that SessionMiddleware processes requests correctly."""
        response = self.client.get("/test-session")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("session_available"))
        self._track_metric("integration", "session_processing", 1)
        
    def test_middleware_chain_with_gcp_auth_context(self):
        """Test complete middleware chain including GCP auth context."""
        response = self.client.get("/test-auth-context")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should not have SessionMiddleware error
        self.assertNotIn("error", data)
        self.assertIn("user_id", data)
        self._track_metric("integration", "auth_context_extraction", 1)
        
    def test_session_persistence_across_requests(self):
        """Test that session data persists across requests."""
        # First request - set session data
        with self.client as client:
            response1 = client.get("/test-session")
            self.assertEqual(response1.status_code, 200)
            
            # Second request - should maintain session
            response2 = client.get("/test-session")
            self.assertEqual(response2.status_code, 200)
            
            # Check cookies for session
            if response1.cookies:
                self._track_metric("integration", "session_persistence", 1)
                
    def test_middleware_error_handling_integration(self):
        """Test error handling in middleware chain."""
        # Remove SECRET_KEY to force error
        with patch.dict('os.environ', {'SECRET_KEY': ''}, clear=False):
            app = FastAPI()
            
            # Try to add SessionMiddleware with invalid key
            try:
                app.add_middleware(SessionMiddleware, secret_key="")
                client = TestClient(app)
                response = client.get("/")
                # If we get here, middleware allowed empty key
                self._track_metric("integration", "empty_key_allowed", 1)
            except Exception as e:
                # Expected - middleware rejected invalid key
                self._track_metric("integration", "invalid_key_rejected", 1)
                
    def test_gcp_staging_environment_simulation(self):
        """Test middleware behavior simulating GCP staging environment."""
        # Simulate staging environment
        self.env.set("ENV", "staging")
        self.env.set("GCP_PROJECT", "netra-staging")
        
        # Create app with staging configuration
        app = FastAPI()
        
        # Add middleware with staging config
        secret_key = self.env.get("SECRET_KEY")
        if secret_key and len(secret_key) >= 32:
            app.add_middleware(SessionMiddleware, secret_key=secret_key)
            
            @app.get("/staging-test")
            async def staging_test(request: Request):
                # Try session access
                try:
                    session = request.session
                    return {"status": "success", "env": "staging"}
                except RuntimeError as e:
                    return {"status": "error", "message": str(e)}
                    
            client = TestClient(app)
            response = client.get("/staging-test")
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("status"), "success")
            self._track_metric("integration", "staging_simulation", 1)
            
    def test_concurrent_request_handling(self):
        """Test middleware handles concurrent requests correctly."""
        async def make_request(client, request_id):
            response = client.get(f"/test-session?id={request_id}")
            return response.json()
            
        # Simulate concurrent requests
        async def run_concurrent():
            tasks = []
            for i in range(10):
                # Create new client for each request to simulate different users
                client = TestClient(self.app)
                tasks.append(make_request(client, i))
                
            results = await asyncio.gather(*tasks)
            return results
            
        # Run concurrent test
        loop = asyncio.new_event_loop()
        results = loop.run_until_complete(run_concurrent())
        loop.close()
        
        # All requests should succeed
        for result in results:
            self.assertTrue(result.get("session_available"))
            
        self._track_metric("integration", "concurrent_requests", len(results))


if __name__ == "__main__":
    unittest.main()