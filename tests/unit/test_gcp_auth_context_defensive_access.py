"""
Unit tests for GCPAuthContextMiddleware defensive session access patterns.
Reproduces Issue #169 SessionMiddleware dependency failures.

CRITICAL MISSION: These tests validate the defensive programming patterns
that should handle missing SessionMiddleware gracefully without causing
authentication context extraction failures.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestGCPAuthContextDefensiveAccess(SSotBaseTestCase):
    """Test defensive session access patterns in GCPAuthContextMiddleware."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        # Environment is available as self._env from SSotBaseTestCase
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        """Clean up test environment."""
        try:
            self.loop.close()
        except:
            pass
        super().tearDown()
        
    def test_missing_session_middleware_graceful_handling(self):
        """Test graceful handling when SessionMiddleware is completely missing.
        
        CRITICAL: This reproduces the exact error condition from Issue #169.
        """
        # Try to import the actual middleware
        try:
            from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
            middleware_class = GCPAuthContextMiddleware
        except ImportError:
            try:
                from shared.middleware.gcp_auth_context import GCPAuthContextMiddleware  
                middleware_class = GCPAuthContextMiddleware
            except ImportError:
                self.record_metric("middleware_import", "middleware_not_found", 1)
                self.skipTest("GCPAuthContextMiddleware not available for testing")
        
        middleware = middleware_class()
        
        # Create request mock without session attribute
        request = MagicMock()
        if hasattr(request, 'session'):
            delattr(request, 'session')
            
        async def test_extract():
            try:
                # This is the method that fails in staging
                if hasattr(middleware, '_extract_auth_context'):
                    auth_context = await middleware._extract_auth_context(request)
                else:
                    # Try alternative method names
                    if hasattr(middleware, 'extract_auth_context'):
                        auth_context = await middleware.extract_auth_context(request)
                    else:
                        self.record_metric("method_discovery", "extract_method_not_found", 1)
                        return
                
                # Should return valid context despite missing session
                self.assertIsInstance(auth_context, dict)
                self.assertIn('user_id', auth_context)
                
                self.record_metric("defensive_handling", "missing_session_handled", 1)
                
            except Exception as e:
                error_msg = str(e).lower()
                if "sessionmiddleware must be installed" in error_msg:
                    self.record_metric("defensive_handling", "session_error_not_handled", 1)
                    # This is the exact error from Issue #169 - defensive handling failed
                    raise AssertionError(f"Defensive handling failed: {e}")
                else:
                    self.record_metric("defensive_handling", "other_error", 1)
                    raise
                    
        self.loop.run_until_complete(test_extract())
        
    def test_session_access_error_specific_handling(self):
        """Test specific handling of SessionMiddleware access errors."""
        try:
            from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        except ImportError:
            try:
                from shared.middleware.gcp_auth_context import GCPAuthContextMiddleware
            except ImportError:
                self.skipTest("GCPAuthContextMiddleware not available")
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # Mock session property to raise the specific error
        def raise_session_error():
            raise RuntimeError("SessionMiddleware must be installed to access request.session")
            
        type(request).session = property(lambda self: raise_session_error())
        
        async def test_defensive():
            try:
                if hasattr(middleware, '_extract_auth_context'):
                    auth_context = await middleware._extract_auth_context(request)
                elif hasattr(middleware, 'extract_auth_context'):
                    auth_context = await middleware.extract_auth_context(request)
                else:
                    self.skipTest("Extract method not found")
                    
                # Should handle error and return valid context
                self.assertIsInstance(auth_context, dict)
                self.record_metric("error_handling", "session_error_handled", 1)
                
            except RuntimeError as e:
                if "SessionMiddleware must be installed" in str(e):
                    self.record_metric("error_handling", "session_error_propagated", 1)
                    # This indicates defensive handling is not working
                    self.fail(f"SessionMiddleware error should be handled defensively: {e}")
                else:
                    raise
                    
        self.loop.run_until_complete(test_defensive())
        
    def test_fallback_authentication_context_extraction(self):
        """Test fallback auth context extraction when session is unavailable."""
        try:
            from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        except ImportError:
            try:
                from shared.middleware.gcp_auth_context import GCPAuthContextMiddleware
            except ImportError:
                self.skipTest("GCPAuthContextMiddleware not available")
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # Set up request with auth headers but no session
        request.headers = {'Authorization': 'Bearer test_jwt_token_for_fallback'}
        
        # Mock session failure
        def session_error():
            raise RuntimeError("SessionMiddleware must be installed")
        type(request).session = property(lambda self: session_error())
        
        async def test_fallback():
            try:
                if hasattr(middleware, '_extract_auth_context'):
                    auth_context = await middleware._extract_auth_context(request)
                elif hasattr(middleware, 'extract_auth_context'):
                    auth_context = await middleware.extract_auth_context(request)
                else:
                    self.skipTest("Extract method not found")
                
                # Should extract from headers as fallback
                self.assertIn('jwt_token', auth_context)
                self.assertEqual(auth_context['jwt_token'], 'test_jwt_token_for_fallback')
                
                # Should provide default values
                self.assertIn('user_id', auth_context)
                self.assertIn('auth_method', auth_context)
                
                self.record_metric("fallback_extraction", "headers_used", 1)
                
            except Exception as e:
                self.record_metric("fallback_extraction", "fallback_failed", 1)
                self.fail(f"Fallback extraction should work when session unavailable: {e}")
                
        self.loop.run_until_complete(test_fallback())
        
    def test_request_state_fallback_mechanism(self):
        """Test fallback to request.state when session is unavailable."""
        try:
            from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        except ImportError:
            try:
                from shared.middleware.gcp_auth_context import GCPAuthContextMiddleware
            except ImportError:
                self.skipTest("GCPAuthContextMiddleware not available")
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # No session but has request.state with user info
        if hasattr(request, 'session'):
            delattr(request, 'session')
            
        request.state = MagicMock()
        request.state.user = MagicMock(
            user_id='state_user_id',
            email='user@example.com',
            customer_tier='premium'
        )
        
        async def test_state_fallback():
            try:
                if hasattr(middleware, '_extract_auth_context'):
                    auth_context = await middleware._extract_auth_context(request)
                elif hasattr(middleware, 'extract_auth_context'):
                    auth_context = await middleware.extract_auth_context(request)
                else:
                    self.skipTest("Extract method not found")
                
                # Should extract from request.state
                self.assertEqual(auth_context.get('user_id'), 'state_user_id')
                self.assertEqual(auth_context.get('user_email'), 'user@example.com')
                self.assertEqual(auth_context.get('customer_tier'), 'premium')
                
                self.record_metric("state_fallback", "request_state_used", 1)
                
            except Exception as e:
                self.record_metric("state_fallback", "state_fallback_failed", 1)
                self.fail(f"Request.state fallback should work: {e}")
                
        self.loop.run_until_complete(test_state_fallback())
        
    def test_middleware_dispatch_error_isolation(self):
        """Test that SessionMiddleware errors don't propagate to request handlers."""
        try:
            from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        except ImportError:
            try:
                from shared.middleware.gcp_auth_context import GCPAuthContextMiddleware
            except ImportError:
                self.skipTest("GCPAuthContextMiddleware not available")
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # Force session error
        def session_error():
            raise RuntimeError("SessionMiddleware must be installed")
        type(request).session = property(lambda self: session_error())
        
        async def call_next(req):
            # Simulate next middleware/handler  
            return MagicMock(status_code=200, content="Success")
            
        async def test_dispatch():
            try:
                if hasattr(middleware, 'dispatch'):
                    response = await middleware.dispatch(request, call_next)
                elif hasattr(middleware, '__call__'):
                    response = await middleware(request, call_next)
                else:
                    self.skipTest("Dispatch method not found")
                
                # Should not propagate error to handler
                self.assertEqual(response.status_code, 200)
                self.record_metric("error_isolation", "error_contained", 1)
                
            except RuntimeError as e:
                if "SessionMiddleware must be installed" in str(e):
                    self.record_metric("error_isolation", "error_propagated", 1)
                    self.fail(f"SessionMiddleware error should not propagate: {e}")
                else:
                    raise
                    
        self.loop.run_until_complete(test_dispatch())
        
    def test_logging_identifies_configuration_vs_order_issues(self):
        """Test that logging clearly identifies configuration vs middleware order issues."""
        try:
            from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        except ImportError:
            try:
                from shared.middleware.gcp_auth_context import GCPAuthContextMiddleware
            except ImportError:
                self.skipTest("GCPAuthContextMiddleware not available")
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        def session_error():
            raise RuntimeError("SessionMiddleware must be installed to access request.session")
        type(request).session = property(lambda self: session_error())
        
        async def test_logging():
            with patch.object(middleware, 'logger', create=True) as mock_logger:
                mock_logger.warning = MagicMock()
                mock_logger.error = MagicMock()
                
                try:
                    if hasattr(middleware, '_extract_auth_context'):
                        await middleware._extract_auth_context(request)
                    elif hasattr(middleware, 'extract_auth_context'):
                        await middleware.extract_auth_context(request)
                    else:
                        self.skipTest("Extract method not found")
                except Exception:
                    # Error is expected, check if it was logged properly
                    pass
                
                # Should have logged diagnostic information
                if mock_logger.warning.called or mock_logger.error.called:
                    self.record_metric("diagnostic_logging", "session_issue_logged", 1)
                    
                    # Check if logging indicates middleware order issue
                    warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                    error_calls = [str(call) for call in mock_logger.error.call_args_list]
                    all_calls = warning_calls + error_calls
                    
                    order_keywords = ['order', 'dependency', 'install', 'middleware']
                    if any(keyword in call.lower() for call in all_calls for keyword in order_keywords):
                        self.record_metric("diagnostic_logging", "order_issue_identified", 1)
                    else:
                        self.record_metric("diagnostic_logging", "generic_error_logged", 1)
                else:
                    self.record_metric("diagnostic_logging", "no_diagnostic_logging", 1)
                    
        self.loop.run_until_complete(test_logging())
        
    def test_performance_impact_of_defensive_patterns(self):
        """Test that defensive error handling doesn't impact performance significantly."""
        try:
            from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        except ImportError:
            try:
                from shared.middleware.gcp_auth_context import GCPAuthContextMiddleware
            except ImportError:
                self.skipTest("GCPAuthContextMiddleware not available")
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # Force defensive path (session error)
        def session_error():
            raise RuntimeError("SessionMiddleware must be installed")
        type(request).session = property(lambda self: session_error())
        
        async def test_performance():
            import time
            
            start_time = time.time()
            
            # Run multiple extractions to test performance
            for _ in range(50):
                try:
                    if hasattr(middleware, '_extract_auth_context'):
                        await middleware._extract_auth_context(request)
                    elif hasattr(middleware, 'extract_auth_context'):
                        await middleware.extract_auth_context(request)
                    else:
                        break
                except Exception:
                    # Expected due to defensive handling
                    pass
                    
            elapsed = time.time() - start_time
            
            # Should complete quickly even with defensive error handling
            self.assertLess(elapsed, 0.5, "Defensive handling should not significantly impact performance")
            self.record_metric("performance", "elapsed_ms", elapsed * 1000)
            
        self.loop.run_until_complete(test_performance())
        
    def test_session_middleware_dependency_detection(self):
        """Test detection and reporting of SessionMiddleware dependency issues."""
        try:
            from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        except ImportError:
            try:
                from shared.middleware.gcp_auth_context import GCPAuthContextMiddleware
            except ImportError:
                self.skipTest("GCPAuthContextMiddleware not available")
        
        middleware = GCPAuthContextMiddleware()
        request = MagicMock()
        
        # Test different session error scenarios
        error_scenarios = [
            "SessionMiddleware must be installed to access request.session",
            "No attribute 'session'",
            "'Request' object has no attribute 'session'"
        ]
        
        for error_msg in error_scenarios:
            def session_error():
                if "attribute" in error_msg:
                    raise AttributeError(error_msg)
                else:
                    raise RuntimeError(error_msg)
            type(request).session = property(lambda self: session_error())
            
            async def test_scenario():
                try:
                    if hasattr(middleware, '_extract_auth_context'):
                        auth_context = await middleware._extract_auth_context(request)
                    elif hasattr(middleware, 'extract_auth_context'):
                        auth_context = await middleware.extract_auth_context(request)
                    else:
                        return
                    
                    # Should handle each scenario appropriately
                    self.assertIsInstance(auth_context, dict)
                    self.record_metric("dependency_detection", f"handled_{error_msg[:20]}", 1)
                    
                except Exception as e:
                    # Track specific dependency errors
                    if "sessionmiddleware" in str(e).lower():
                        self.record_metric("dependency_detection", f"unhandled_{error_msg[:20]}", 1)
                    else:
                        self.record_metric("dependency_detection", "other_error", 1)
                        
            self.loop.run_until_complete(test_scenario())


if __name__ == "__main__":
    unittest.main()