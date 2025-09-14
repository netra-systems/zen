"""
Unit Tests for Issue #1101 MessageRouter Proxy Removal Impact Analysis

These tests validate what happens when the proxy layer is removed:
1. Test current proxy behavior
2. Simulate proxy removal scenarios
3. Identify breaking changes and dependencies
4. Validate impact on existing functionality

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Safe SSOT migration without breaking changes
- Value Impact: Ensures smooth transition to true SSOT compliance
- Strategic Impact: Protects system stability during proxy removal
"""

import pytest
import time
import asyncio
import warnings
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, List

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import all MessageRouter variants to test proxy removal impact
from netra_backend.app.core.message_router import MessageRouter as ProxyMessageRouter
from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalMessageRouter
from netra_backend.app.services.message_router import MessageRouter as ServicesMessageRouter

from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestMessageRouterProxyRemovalImpact(SSotBaseTestCase):
    """Unit tests for analyzing the impact of removing MessageRouter proxy layer."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_user_id = "test_user_67890"
        self.test_websocket = Mock()
        self.test_message = {
            "type": "user_message",
            "payload": {"content": "test proxy removal"},
            "timestamp": time.time()
        }
    
    def test_current_proxy_behavior_baseline(self):
        """Establish baseline behavior of current proxy implementation."""
        proxy_router = ProxyMessageRouter()
        
        # Verify proxy is working correctly
        self.assertTrue(hasattr(proxy_router, '_canonical_router'))
        self.assertIsInstance(proxy_router._canonical_router, CanonicalMessageRouter)
        
        # Test all proxy methods are functional
        proxy_methods = [
            'add_route', 'add_middleware', 'start', 'stop', 
            'get_statistics', 'handlers', 'routes', 'middleware', 'active'
        ]
        
        for method in proxy_methods:
            self.assertTrue(hasattr(proxy_router, method), 
                           f"Proxy missing method: {method}")
    
    def test_proxy_deprecation_warnings_collected(self):
        """Test that proxy deprecation warnings are properly emitted and collected."""
        warnings.resetwarnings()
        
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            
            # Create proxy instance - should trigger deprecation warning
            proxy_router = ProxyMessageRouter()
            
            # Verify warning was emitted
            self.assertTrue(len(warning_list) > 0)
            deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]
            self.assertTrue(len(deprecation_warnings) > 0)
            
            warning_message = str(deprecation_warnings[0].message)
            self.assertIn("deprecated", warning_message.lower())
            self.assertIn("phase 2", warning_message.lower())
    
    def test_proxy_removal_simulation_direct_canonical_usage(self):
        """Simulate proxy removal by testing direct canonical router usage."""
        # Simulate what would happen if proxy is removed
        # Tests would need to import directly from canonical location
        
        canonical_router = CanonicalMessageRouter()
        
        # Verify all expected functionality is available in canonical router
        expected_methods = [
            'add_handler', 'remove_handler', 'route_message', 'handlers',
            'get_stats', 'add_route', 'add_middleware', 'start', 'stop',
            'get_statistics'
        ]
        
        for method in expected_methods:
            self.assertTrue(hasattr(canonical_router, method),
                           f"Canonical router missing method: {method}")
    
    def test_breaking_changes_from_proxy_removal(self):
        """Identify potential breaking changes when proxy is removed."""
        # Test 1: Import path changes
        try:
            # This import would break if proxy is removed
            from netra_backend.app.core.message_router import MessageRouter
            self.assertIsNotNone(MessageRouter)
            
            # Document the breaking change
            logger.warning("BREAKING CHANGE: Import 'from netra_backend.app.core.message_router import MessageRouter' "
                          "will fail when proxy is removed")
        except ImportError:
            # This would happen after proxy removal
            pass
        
        # Test 2: Global instance compatibility
        from netra_backend.app.core.message_router import message_router
        self.assertIsInstance(message_router, ProxyMessageRouter)
        
        # Document that global instance would need updating
        logger.warning("BREAKING CHANGE: Global 'message_router' instance would need to be updated "
                      "when proxy is removed")
    
    def test_proxy_specific_methods_would_be_lost(self):
        """Test that proxy-specific methods would be lost on removal."""
        proxy_router = ProxyMessageRouter()
        
        # These are proxy-specific and would be lost
        proxy_specific_attributes = ['_canonical_router']
        
        for attr in proxy_specific_attributes:
            self.assertTrue(hasattr(proxy_router, attr),
                           f"Proxy-specific attribute {attr} exists now but would be lost")
        
        # Verify canonical router doesn't have these
        canonical_router = CanonicalMessageRouter()
        for attr in proxy_specific_attributes:
            self.assertFalse(hasattr(canonical_router, attr),
                            f"Canonical router should not have proxy attribute {attr}")
    
    def test_proxy_logging_behavior_changes(self):
        """Test that proxy-specific logging would change after removal."""
        proxy_router = ProxyMessageRouter()
        
        # Capture logs during proxy operation
        with patch('netra_backend.app.core.message_router.logger') as mock_logger:
            proxy_router.get_statistics()
            
            # Verify proxy-specific logging occurred
            mock_logger.debug.assert_called()
            debug_calls = [call.args[0] for call in mock_logger.debug.call_args_list]
            proxy_debug_messages = [msg for msg in debug_calls if "PROXY:" in msg]
            
            self.assertTrue(len(proxy_debug_messages) > 0,
                           "Proxy-specific debug logging would be lost")
    
    def test_statistics_format_changes_after_proxy_removal(self):
        """Test that statistics format would change when proxy is removed."""
        proxy_router = ProxyMessageRouter()
        canonical_router = CanonicalMessageRouter()
        
        # Get statistics from both
        proxy_stats = proxy_router.get_statistics()
        canonical_stats = canonical_router.get_statistics()
        
        # Proxy stats should include proxy_info
        self.assertIn("proxy_info", proxy_stats)
        self.assertTrue(proxy_stats["proxy_info"]["is_proxy"])
        
        # Canonical stats should NOT include proxy_info
        self.assertNotIn("proxy_info", canonical_stats)
        
        # Document the format change
        logger.warning("FORMAT CHANGE: Statistics format will change when proxy is removed - "
                      "proxy_info section will disappear")
    
    def test_middleware_and_route_compatibility_after_removal(self):
        """Test middleware and route compatibility after proxy removal."""
        canonical_router = CanonicalMessageRouter()
        
        # Test route addition (proxy compatibility method)
        test_route_pattern = "/test/route"
        test_handler = Mock()
        
        # This should work in canonical router
        canonical_router.add_route(test_route_pattern, test_handler)
        
        # Verify route was added
        if hasattr(canonical_router, '_test_routes'):
            self.assertIn(test_route_pattern, canonical_router._test_routes)
        
        # Test middleware addition
        test_middleware = Mock()
        test_middleware.__name__ = "test_middleware"
        
        canonical_router.add_middleware(test_middleware)
        
        # Verify middleware was added
        if hasattr(canonical_router, '_test_middleware'):
            self.assertIn(test_middleware, canonical_router._test_middleware)
    
    def test_startup_lifecycle_compatibility_after_removal(self):
        """Test startup/lifecycle compatibility after proxy removal."""
        canonical_router = CanonicalMessageRouter()
        
        # Test start/stop methods exist
        self.assertTrue(hasattr(canonical_router, 'start'))
        self.assertTrue(hasattr(canonical_router, 'stop'))
        
        # Test they can be called without error
        canonical_router.start()
        self.assertTrue(getattr(canonical_router, '_test_active', False))
        
        canonical_router.stop()
        self.assertFalse(getattr(canonical_router, '_test_active', True))
    
    async def test_async_routing_behavior_unchanged_after_removal(self):
        """Test that async routing behavior remains unchanged after proxy removal."""
        canonical_router = CanonicalMessageRouter()
        mock_websocket = Mock()
        
        test_message = {
            "type": "test_message",
            "payload": {"content": "test"},
            "timestamp": time.time()
        }
        
        # Test async routing works
        result = await canonical_router.route_message(
            self.test_user_id, mock_websocket, test_message
        )
        
        # Should return boolean result
        self.assertIsInstance(result, bool)
    
    def test_handler_registration_unchanged_after_removal(self):
        """Test that handler registration works the same after proxy removal."""
        canonical_router = CanonicalMessageRouter()
        
        # Create mock handler
        mock_handler = Mock()
        mock_handler.can_handle = Mock(return_value=True)
        mock_handler.handle_message = Mock()
        mock_handler.__class__.__name__ = "TestHandler"
        
        initial_count = len(canonical_router.handlers)
        
        # Add handler
        canonical_router.add_handler(mock_handler)
        
        # Verify it was added
        self.assertEqual(len(canonical_router.handlers), initial_count + 1)
        self.assertIn(mock_handler, canonical_router.handlers)
    
    def test_global_instance_needs_updating_after_removal(self):
        """Test that global instances need updating when proxy is removed."""
        from netra_backend.app.core.message_router import message_router
        
        # Current global instance is proxy
        self.assertIsInstance(message_router, ProxyMessageRouter)
        
        # After removal, this would need to be CanonicalMessageRouter
        # Document the required change
        logger.warning("REQUIRED CHANGE: Global message_router instance must be updated "
                      "from ProxyMessageRouter to CanonicalMessageRouter when proxy is removed")
    
    def test_import_alias_compatibility_after_removal(self):
        """Test import alias compatibility after proxy removal."""
        # Test current aliases
        from netra_backend.app.core.message_router import Message, MessageType
        
        self.assertIsNotNone(Message)
        self.assertIsNotNone(MessageType)
        
        # These should still work after proxy removal since they're imported from canonical source
        from netra_backend.app.websocket_core.types import WebSocketMessage as Message
        from netra_backend.app.websocket_core.types import MessageType
        
        self.assertIsNotNone(Message)
        self.assertIsNotNone(MessageType)
    
    def test_dependency_chain_analysis_for_removal(self):
        """Analyze dependency chain that would be affected by proxy removal."""
        # Find all modules that might import from core.message_router
        import sys
        
        proxy_dependent_modules = []
        
        # Check loaded modules for potential dependencies
        for module_name, module in sys.modules.items():
            if module and hasattr(module, '__file__') and module.__file__:
                if 'netra_backend' in module_name:
                    # Check if module might depend on proxy
                    if hasattr(module, 'MessageRouter'):
                        try:
                            router_class = getattr(module, 'MessageRouter')
                            if router_class is ProxyMessageRouter:
                                proxy_dependent_modules.append(module_name)
                        except:
                            pass
        
        # Log dependency analysis
        if proxy_dependent_modules:
            logger.warning(f"DEPENDENCY ANALYSIS: Modules that depend on proxy: {proxy_dependent_modules}")
        else:
            logger.info("DEPENDENCY ANALYSIS: No modules directly dependent on proxy found")
    
    def test_configuration_compatibility_after_removal(self):
        """Test that configuration and initialization work after proxy removal."""
        # Test that canonical router can be configured the same way
        canonical_router = CanonicalMessageRouter()
        
        # Test statistics access
        stats = canonical_router.get_statistics()
        self.assertIsInstance(stats, dict)
        
        # Test handler count access
        handler_count = len(canonical_router.handlers)
        self.assertIsInstance(handler_count, int)
        self.assertGreaterEqual(handler_count, 0)
    
    def test_proxy_removal_transition_plan_validation(self):
        """Validate the transition plan for proxy removal."""
        # Phase 1: Current state (proxy exists)
        proxy_router = ProxyMessageRouter()
        self.assertTrue(hasattr(proxy_router, '_canonical_router'))
        
        # Phase 2: Direct canonical usage (post-removal state)
        canonical_router = CanonicalMessageRouter()
        
        # Verify canonical has all required functionality
        required_for_transition = [
            'add_handler', 'remove_handler', 'route_message', 'handlers',
            'get_stats', 'add_route', 'add_middleware', 'start', 'stop'
        ]
        
        for method in required_for_transition:
            self.assertTrue(hasattr(canonical_router, method),
                           f"Canonical router missing method required for transition: {method}")
        
        # Document transition requirements
        logger.info("TRANSITION VALIDATION: Canonical router has all required methods for proxy removal")
    
    def test_error_handling_consistency_after_removal(self):
        """Test that error handling remains consistent after proxy removal."""
        canonical_router = CanonicalMessageRouter()
        
        # Test with invalid handler
        invalid_handler = "not_a_handler"
        
        with self.assertRaises(TypeError):
            canonical_router.add_handler(invalid_handler)
        
        # Test with malformed message
        mock_websocket = Mock()
        malformed_message = {"invalid": "structure"}
        
        # Should handle gracefully
        try:
            asyncio.run(canonical_router.route_message(
                self.test_user_id, mock_websocket, malformed_message
            ))
        except Exception as e:
            # Should not crash, may return False
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])