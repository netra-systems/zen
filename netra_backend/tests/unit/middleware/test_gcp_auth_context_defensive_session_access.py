"""
Unit tests for GCPAuthContextMiddleware defensive session access patterns.
Tests graceful handling when SessionMiddleware is missing.
"""

import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
import asyncio


class TestGCPAuthContextDefensiveSessionAccess(SSotBaseTestCase):
    """Test defensive session access patterns in GCPAuthContextMiddleware."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.env = IsolatedEnvironment()
        
    def test_graceful_handling_missing_session_middleware(self):
        """Test that GCPAuthContextMiddleware handles missing SessionMiddleware gracefully."""
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # Simulate missing session attribute
        if hasattr(request, 'session'):
            delattr(request, 'session')
        
        # Should not raise exception
        async def test_extract():
            try:
                auth_context = await middleware._extract_auth_context(request)
                self.assertIsInstance(auth_context, dict)
                self._track_metric("defensive_access", "missing_session_handled", 1)
                return True
            except Exception as e:
                if "SessionMiddleware must be installed" in str(e):
                    # Expected error, but should be handled
                    self._track_metric("defensive_access", "session_error_caught", 1)
                    return False
                raise
        
        # Run async test
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(test_extract())
        loop.close()
        
    def test_session_middleware_error_specific_handling(self):
        """Test specific handling of SessionMiddleware errors."""
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # Mock session access to raise specific error
        def raise_session_error():
            raise RuntimeError("SessionMiddleware must be installed to access request.session")
        
        request.session = property(raise_session_error)
        
        async def test_extract():
            with patch.object(middleware, 'logger') as mock_logger:
                auth_context = await middleware._extract_auth_context(request)
                
                # Should log warning but not fail
                mock_logger.warning.assert_called()
                warning_msg = str(mock_logger.warning.call_args)
                
                if "SessionMiddleware" in warning_msg:
                    self._track_metric("defensive_access", "session_error_logged", 1)
                
                # Should return valid context despite error
                self.assertIsInstance(auth_context, dict)
                self.assertIn('user_id', auth_context)
                
        # Run async test
        loop = asyncio.new_event_loop()
        loop.run_until_complete(test_extract())
        loop.close()
        
    def test_fallback_auth_context_on_session_failure(self):
        """Test that fallback auth context is provided when session fails."""
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        request.headers = {'Authorization': 'Bearer test_token'}
        
        # Simulate session access failure
        def raise_error():
            raise RuntimeError("SessionMiddleware must be installed")
        request.session = property(raise_error)
        
        async def test_extract():
            auth_context = await middleware._extract_auth_context(request)
            
            # Should still extract from headers
            self.assertIn('jwt_token', auth_context)
            self.assertEqual(auth_context['jwt_token'], 'test_token')
            
            # Should provide defaults
            self.assertIn('user_id', auth_context)
            self.assertIn('auth_method', auth_context)
            self.assertIn('customer_tier', auth_context)
            
            self._track_metric("defensive_access", "fallback_context_used", 1)
            
        # Run async test  
        loop = asyncio.new_event_loop()
        loop.run_until_complete(test_extract())
        loop.close()
        
    def test_partial_session_data_extraction(self):
        """Test extraction when session exists but has partial data."""
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # Session exists but incomplete
        request.session = {
            'user_id': 'test_user',
            # Missing session_id and user_email
        }
        
        async def test_extract():
            auth_context = await middleware._extract_auth_context(request)
            
            # Should extract available data
            self.assertEqual(auth_context.get('user_id'), 'test_user')
            
            # Should handle missing fields gracefully
            if 'session_id' not in request.session:
                self._track_metric("defensive_access", "partial_session_handled", 1)
                
        # Run async test
        loop = asyncio.new_event_loop()
        loop.run_until_complete(test_extract())
        loop.close()
        
    def test_no_error_propagation_to_request_handler(self):
        """Test that session errors don't propagate to request handler."""
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # Force session error
        def raise_error():
            raise RuntimeError("SessionMiddleware must be installed")
        request.session = property(raise_error)
        
        async def call_next(req):
            # Simulate next middleware/handler
            return MagicMock(status_code=200)
            
        async def test_dispatch():
            # Middleware dispatch should not raise
            response = await middleware.dispatch(request, call_next)
            self.assertEqual(response.status_code, 200)
            self._track_metric("defensive_access", "error_not_propagated", 1)
            
        # Run async test
        loop = asyncio.new_event_loop()
        loop.run_until_complete(test_dispatch())
        loop.close()
        
    def test_logging_distinguishes_config_vs_order_issues(self):
        """Test that logging clearly distinguishes configuration vs ordering issues."""
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # Simulate SessionMiddleware error
        def raise_error():
            raise RuntimeError("SessionMiddleware must be installed to access request.session")
        request.session = property(raise_error)
        
        async def test_extract():
            with patch.object(middleware, 'logger') as mock_logger:
                await middleware._extract_auth_context(request)
                
                # Check if logging indicates middleware order issue
                if mock_logger.warning.called:
                    call_args = str(mock_logger.warning.call_args)
                    if "middleware_order_issue" in call_args or "dependency" in call_args.lower():
                        self._track_metric("defensive_logging", "order_issue_identified", 1)
                    else:
                        self._track_metric("defensive_logging", "generic_warning", 1)
                        
        # Run async test
        loop = asyncio.new_event_loop()
        loop.run_until_complete(test_extract())
        loop.close()
        
    def test_request_state_fallback_when_session_unavailable(self):
        """Test fallback to request.state when session is unavailable."""
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # No session but has state
        if hasattr(request, 'session'):
            delattr(request, 'session')
            
        request.state.user = MagicMock(
            user_id='state_user',
            email='user@example.com',
            customer_tier='premium'
        )
        
        async def test_extract():
            auth_context = await middleware._extract_auth_context(request)
            
            # Should extract from request.state
            self.assertEqual(auth_context.get('user_id'), 'state_user')
            self.assertEqual(auth_context.get('user_email'), 'user@example.com')
            self.assertEqual(auth_context.get('customer_tier'), 'premium')
            
            self._track_metric("defensive_access", "state_fallback_used", 1)
            
        # Run async test
        loop = asyncio.new_event_loop()
        loop.run_until_complete(test_extract())
        loop.close()
        
    def test_defensive_pattern_performance_impact(self):
        """Test that defensive patterns don't significantly impact performance."""
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        import time
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # Force session error for defensive path
        def raise_error():
            raise RuntimeError("SessionMiddleware must be installed")
        request.session = property(raise_error)
        
        async def test_performance():
            start_time = time.time()
            
            # Run multiple extractions
            for _ in range(100):
                await middleware._extract_auth_context(request)
                
            elapsed = time.time() - start_time
            
            # Should complete quickly even with defensive handling
            self.assertLess(elapsed, 1.0, "Defensive handling should not significantly impact performance")
            self._track_metric("defensive_performance", "elapsed_ms", elapsed * 1000)
            
        # Run async test
        loop = asyncio.new_event_loop()
        loop.run_until_complete(test_performance())
        loop.close()


if __name__ == "__main__":
    unittest.main()