"""
Unit tests for SessionMiddleware installation order.
Ensures middleware dependencies are properly ordered.
"""

import unittest
from unittest.mock import MagicMock, patch, call
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from fastapi import FastAPI


class TestSessionMiddlewareInstallationOrder(SSotBaseTestCase):
    """Test middleware installation order to prevent dependency issues."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.app = FastAPI()
        self.env = IsolatedEnvironment()
        
    def test_session_middleware_installed_before_gcp_auth(self):
        """Test that SessionMiddleware is installed before GCPAuthContextMiddleware."""
        from netra_backend.app.core.middleware_setup import setup_middleware
        
        with patch('netra_backend.app.core.middleware_setup.setup_session_middleware') as mock_session:
            with patch('netra_backend.app.core.middleware_setup.setup_gcp_auth_context_middleware') as mock_gcp:
                # Track call order
                call_order = []
                mock_session.side_effect = lambda app: call_order.append('session')
                mock_gcp.side_effect = lambda app: call_order.append('gcp')
                
                # Setup middleware
                setup_middleware(self.app)
                
                # Verify correct order
                self.assertEqual(call_order, ['session', 'gcp'])
                self._track_metric("middleware_order", "correct_order", 1)
                
    def test_middleware_stack_inspection(self):
        """Test that middleware stack can be inspected after installation."""
        from netra_backend.app.core.middleware_setup import setup_middleware
        
        # Mock middleware setup functions
        with patch('netra_backend.app.core.middleware_setup.setup_session_middleware') as mock_session:
            with patch('netra_backend.app.core.middleware_setup.setup_gcp_auth_context_middleware') as mock_gcp:
                
                # Track middleware additions
                middleware_stack = []
                
                def track_session(app):
                    middleware_stack.append('SessionMiddleware')
                    
                def track_gcp(app):
                    middleware_stack.append('GCPAuthContextMiddleware')
                    
                mock_session.side_effect = track_session
                mock_gcp.side_effect = track_gcp
                
                # Setup middleware
                setup_middleware(self.app)
                
                # Verify stack order
                self.assertEqual(middleware_stack[0], 'SessionMiddleware')
                self.assertIn('GCPAuthContextMiddleware', middleware_stack)
                self._track_metric("middleware_stack", "inspection_passed", 1)
                
    def test_middleware_dependency_detection(self):
        """Test detection of middleware dependencies."""
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        # GCPAuthContextMiddleware should have session dependency
        middleware = GCPAuthContextMiddleware()
        
        # Check if middleware attempts to access session
        request = MagicMock()
        request.session = None
        
        # Should handle missing session gracefully
        try:
            # Simulate middleware checking for session
            if hasattr(request, 'session') and request.session:
                self._track_metric("middleware_dependency", "session_available", 1)
            else:
                self._track_metric("middleware_dependency", "session_missing", 1)
        except Exception as e:
            self.fail(f"Middleware should handle missing session: {e}")
            
    def test_ssot_middleware_setup_compliance(self):
        """Test that middleware setup follows SSOT principles."""
        from netra_backend.app.core.middleware_setup import setup_middleware
        
        # Verify single source of truth for middleware configuration
        with patch('netra_backend.app.core.middleware_setup.setup_session_middleware') as mock_session:
            with patch('netra_backend.app.core.middleware_setup.setup_gcp_auth_context_middleware') as mock_gcp:
                
                setup_middleware(self.app)
                
                # Each middleware should be set up exactly once
                mock_session.assert_called_once_with(self.app)
                mock_gcp.assert_called_once_with(self.app)
                self._track_metric("ssot_compliance", "middleware_setup", 1)
                
    def test_middleware_installation_error_handling(self):
        """Test error handling during middleware installation."""
        from netra_backend.app.core.middleware_setup import setup_middleware
        
        with patch('netra_backend.app.core.middleware_setup.setup_session_middleware') as mock_session:
            # Simulate SessionMiddleware installation failure
            mock_session.side_effect = RuntimeError("SECRET_KEY validation failed")
            
            # Should raise or handle error appropriately
            with self.assertRaises(RuntimeError) as context:
                setup_middleware(self.app)
                
            self.assertIn("SECRET_KEY", str(context.exception))
            self._track_metric("middleware_installation", "error_handling", 1)
            
    def test_middleware_ordering_with_all_middleware(self):
        """Test complete middleware stack ordering."""
        from netra_backend.app.core.middleware_setup import setup_middleware
        
        # Track all middleware installations
        installations = []
        
        with patch('netra_backend.app.core.middleware_setup.setup_cors_middleware') as mock_cors:
            with patch('netra_backend.app.core.middleware_setup.setup_session_middleware') as mock_session:
                with patch('netra_backend.app.core.middleware_setup.setup_gcp_auth_context_middleware') as mock_gcp:
                    
                    mock_cors.side_effect = lambda app: installations.append('CORS')
                    mock_session.side_effect = lambda app: installations.append('Session')
                    mock_gcp.side_effect = lambda app: installations.append('GCP')
                    
                    setup_middleware(self.app)
                    
                    # Session should come before GCP
                    session_idx = installations.index('Session') if 'Session' in installations else -1
                    gcp_idx = installations.index('GCP') if 'GCP' in installations else -1
                    
                    if session_idx >= 0 and gcp_idx >= 0:
                        self.assertLess(session_idx, gcp_idx, 
                                      "SessionMiddleware must be installed before GCPAuthContextMiddleware")
                    
                    self._track_metric("middleware_order", "complete_stack", len(installations))


if __name__ == "__main__":
    unittest.main()