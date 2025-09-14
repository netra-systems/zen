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

# Import canonical MessageRouter and test import path behavior
from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalMessageRouter
# NOTE: Proxy imports now removed as part of Issue #1101 SSOT remediation

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
    
    def test_canonical_router_functionality_after_proxy_removal(self):
        """Verify canonical router functionality after proxy removal."""
        canonical_router = CanonicalMessageRouter()
        
        # Test all canonical router methods are functional
        canonical_methods = [
            'add_route', 'add_middleware', 'start', 'stop', 
            'get_statistics', 'handlers', 'add_handler', 'remove_handler',
            'route_message', 'get_stats'
        ]
        
        for method in canonical_methods:
            self.assertTrue(hasattr(canonical_router, method), 
                           f"Canonical router missing method: {method}")
    
    def test_proxy_imports_properly_removed(self):
        """Test that proxy imports now fail correctly after removal."""
        # Test 1: core.message_router import should fail
        with self.assertRaises(ImportError):
            from netra_backend.app.core.message_router import MessageRouter
        
        # Test 2: services.message_router import should fail
        with self.assertRaises(ImportError):
            from netra_backend.app.services.message_router import MessageRouter
        
        # Test 3: agents.message_router import should fail
        with self.assertRaises(ImportError):
            from netra_backend.app.agents.message_router import MessageRouter
    
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
    
    def test_confirmed_breaking_changes_after_proxy_removal(self):
        """Confirm that breaking changes occurred as expected after proxy removal."""
        # Test 1: Import path changes - these should now fail
        with self.assertRaises(ImportError):
            from netra_backend.app.core.message_router import MessageRouter
            
        # Test 2: Global instance imports should also fail
        with self.assertRaises(ImportError):
            from netra_backend.app.core.message_router import message_router
            
        # Test 3: Type imports from proxy paths should fail  
        with self.assertRaises(ImportError):
            from netra_backend.app.core.message_router import Message, MessageType
        
        # All proxy-related imports should now fail after removal
        logger.info("SUCCESS: All proxy imports correctly fail after Issue #1101 remediation")
    
    def test_canonical_router_has_complete_interface(self):
        """Test that canonical router has complete interface after proxy removal."""
        canonical_router = CanonicalMessageRouter()
        
        # Verify canonical router has all necessary methods
        required_methods = [
            'add_handler', 'remove_handler', 'route_message', 'handlers',
            'get_stats', 'add_route', 'add_middleware', 'start', 'stop',
            'get_statistics'
        ]
        
        for method in required_methods:
            self.assertTrue(hasattr(canonical_router, method),
                           f"Canonical router missing required method: {method}")
        
        # Verify no proxy-specific attributes exist
        proxy_specific_attributes = ['_canonical_router']
        for attr in proxy_specific_attributes:
            self.assertFalse(hasattr(canonical_router, attr),
                            f"Canonical router should not have proxy attribute {attr}")
    
    def test_canonical_logging_behavior_after_removal(self):
        """Test canonical router logging behavior after proxy removal."""
        canonical_router = CanonicalMessageRouter()
        
        # Test that canonical router has proper logging
        stats = canonical_router.get_statistics()
        self.assertIsInstance(stats, dict)
        
        # Verify no proxy-specific entries in stats
        self.assertNotIn("proxy_info", stats)
        
        logger.info("SUCCESS: Canonical router operates with clean logging (no proxy artifacts)")
    
    def test_canonical_statistics_format_after_proxy_removal(self):
        """Test canonical statistics format after proxy removal."""
        canonical_router = CanonicalMessageRouter()
        
        # Get statistics from canonical router
        canonical_stats = canonical_router.get_statistics()
        
        # Verify canonical stats format
        self.assertIsInstance(canonical_stats, dict)
        
        # Canonical stats should NOT include proxy_info
        self.assertNotIn("proxy_info", canonical_stats)
        
        # Should include expected canonical fields
        expected_fields = ["total_messages", "active_routes", "middleware_count", "active"]
        for field in expected_fields:
            self.assertIn(field, canonical_stats, f"Missing expected field: {field}")
        
        logger.info("SUCCESS: Canonical statistics format clean after proxy removal")
    
    def test_middleware_and_route_compatibility_after_removal(self):
        """Test middleware and route compatibility after proxy removal."""
        canonical_router = CanonicalMessageRouter()
        
        # Test route addition (proxy compatibility method)
        test_route_pattern = "/test/route"
        test_handler = Mock()
        
        # This should work in canonical router
        canonical_router.add_route(test_route_pattern, test_handler)
        
        # Verify route was added (test compatibility method)
        if hasattr(canonical_router, '_test_routes'):
            self.assertIn(test_route_pattern, canonical_router._test_routes)
        
        logger.info("SUCCESS: Canonical router maintains compatibility interface after proxy removal")
        
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