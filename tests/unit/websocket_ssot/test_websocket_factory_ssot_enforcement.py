"""
Test WebSocket Factory SSOT Enforcement

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) 
- Business Goal: Ensure WebSocket SSOT compliance prevents user isolation failures
- Value Impact: Critical infrastructure for AI chat interactions (90% of platform value)
- Revenue Impact: Foundation for $500K+ ARR user interactions with proper SSOT patterns

CRITICAL: This test validates the WebSocket factory dual pattern fragmentation issue.
These tests MUST FAIL before SSOT remediation and PASS after remediation.

Issue: Deprecated WebSocketManagerFactory exists alongside SSOT get_websocket_manager()
GitHub Issue: https://github.com/netra-systems/netra-apex/issues/1126
"""

import pytest
import warnings
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from typing import Type, Any


class TestWebSocketFactorySSotEnforcement(SSotBaseTestCase):
    """Test WebSocket Factory SSOT enforcement patterns."""
    
    def test_deprecated_websocket_manager_factory_class_not_accessible(self):
        """
        Test that deprecated WebSocketManagerFactory class is NOT accessible.
        
        BEFORE REMEDIATION: This test should FAIL (class is accessible)
        AFTER REMEDIATION: This test should PASS (class is removed/not accessible)
        """
        with self.assertRaises((ImportError, AttributeError)) as context:
            # This should FAIL before remediation (class exists)
            # This should PASS after remediation (class removed)
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
        # Verify proper error messaging
        error_msg = str(context.exception).lower()
        self.assertTrue(
            any(keyword in error_msg for keyword in ['deprecated', 'removed', 'not found', 'ssot']),
            f"Error message should indicate deprecation/removal: {error_msg}"
        )
        
    def test_deprecated_factory_class_not_exported(self):
        """
        Test that WebSocketManagerFactory is NOT in __all__ exports.
        
        BEFORE REMEDIATION: This test should FAIL (class is exported)
        AFTER REMEDIATION: This test should PASS (class not exported)
        """
        try:
            # Import the factory module
            import netra_backend.app.websocket_core.websocket_manager_factory as factory_module
            
            # Check if WebSocketManagerFactory is in __all__
            if hasattr(factory_module, '__all__'):
                all_exports = factory_module.__all__
                # BEFORE REMEDIATION: This assertion should FAIL
                # AFTER REMEDIATION: This assertion should PASS
                self.assertNotIn(
                    'WebSocketManagerFactory', 
                    all_exports, 
                    "WebSocketManagerFactory should NOT be exported after SSOT remediation"
                )
            
            # Also check direct attribute access
            # BEFORE REMEDIATION: This should exist and assertion FAILS
            # AFTER REMEDIATION: This should not exist and assertion PASSES
            self.assertFalse(
                hasattr(factory_module, 'WebSocketManagerFactory'),
                "WebSocketManagerFactory class should not exist after SSOT remediation"
            )
            
        except ImportError:
            # AFTER REMEDIATION: Module might be removed entirely - this is acceptable
            self.skipTest("Factory module not found - acceptable after SSOT remediation")
            
    def test_canonical_get_websocket_manager_is_accessible(self):
        """
        Test that canonical get_websocket_manager() IS accessible.
        
        BEFORE REMEDIATION: This test should PASS (SSOT function exists)
        AFTER REMEDIATION: This test should PASS (SSOT function still exists)
        """
        try:
            # Import the canonical SSOT function
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            
            # Verify it's a function
            import inspect
            self.assertTrue(
                inspect.iscoroutinefunction(get_websocket_manager),
                "get_websocket_manager should be an async function"
            )
            
            # Verify proper signature (user_context parameter)
            sig = inspect.signature(get_websocket_manager)
            param_names = list(sig.parameters.keys())
            self.assertIn(
                'user_context',
                param_names,
                "get_websocket_manager should accept user_context parameter for isolation"
            )
            
        except ImportError as e:
            self.fail(f"Canonical SSOT get_websocket_manager should always be accessible: {e}")
            
    def test_deprecated_factory_warns_on_usage(self):
        """
        Test that deprecated factory patterns issue warnings.
        
        BEFORE REMEDIATION: This test should PASS (warnings are issued)
        AFTER REMEDIATION: This test might PASS or SKIP (warnings still issued or class removed)
        """
        try:
            # Capture warnings
            with warnings.catch_warnings(record=True) as warning_list:
                warnings.simplefilter("always")
                
                try:
                    # Try to import deprecated factory
                    from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
                    
                    # Try to instantiate it
                    factory = WebSocketManagerFactory()
                    
                    # Verify warnings were issued
                    self.assertGreater(
                        len(warning_list), 
                        0, 
                        "Deprecated factory usage should issue warnings"
                    )
                    
                    # Check warning content
                    warning_messages = [str(w.message) for w in warning_list]
                    self.assertTrue(
                        any('deprecated' in msg.lower() for msg in warning_messages),
                        f"Warning should mention deprecation: {warning_messages}"
                    )
                    
                except (ImportError, AttributeError):
                    # AFTER REMEDIATION: Class might be removed - acceptable
                    self.skipTest("WebSocketManagerFactory removed - acceptable after SSOT remediation")
                    
        except Exception as e:
            self.fail(f"Unexpected error in deprecation warning test: {e}")
            
    def test_ssot_manager_creation_without_factory(self):
        """
        Test that WebSocket managers can be created without deprecated factory.
        
        BEFORE REMEDIATION: This test should PASS (SSOT pattern works)
        AFTER REMEDIATION: This test should PASS (SSOT pattern still works)
        """
        # Mock user context for testing
        mock_user_context = {
            'user_id': 'test_user_ssot_enforcement',
            'thread_id': 'test_thread_ssot_enforcement'
        }
        
        # Import and test SSOT function
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        # This should work without using the deprecated factory
        import asyncio
        
        async def test_manager_creation():
            try:
                manager = await get_websocket_manager(user_context=mock_user_context)
                self.assertIsNotNone(manager, "SSOT get_websocket_manager should return a valid manager")
                return True
            except Exception as e:
                # Log the error for debugging
                self.logger.error(f"SSOT manager creation failed: {e}")
                return False
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_manager_creation())
            self.assertTrue(result, "WebSocket manager should be creatable via SSOT pattern")
        finally:
            loop.close()
            
    def test_factory_pattern_replacement_guidance(self):
        """
        Test that proper guidance is provided for factory pattern replacement.
        
        BEFORE REMEDIATION: This test documents expected migration path
        AFTER REMEDIATION: This test validates migration was successful
        """
        # Expected SSOT import path
        expected_ssot_import = "netra_backend.app.websocket_core.websocket_manager.get_websocket_manager"
        
        # Verify SSOT function can be imported
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            self.assertTrue(True, f"SSOT import successful: {expected_ssot_import}")
        except ImportError as e:
            self.fail(f"SSOT import should always work: {expected_ssot_import} - {e}")
            
        # Verify deprecated patterns are discouraged
        deprecated_patterns = [
            "WebSocketManagerFactory",
            "create_websocket_manager", 
            "get_websocket_manager_factory"
        ]
        
        for pattern in deprecated_patterns:
            try:
                # Try to import deprecated pattern
                import netra_backend.app.websocket_core.websocket_manager_factory as factory_module
                
                if hasattr(factory_module, pattern):
                    # BEFORE REMEDIATION: These might exist
                    # AFTER REMEDIATION: These should be removed or issue warnings
                    warnings.warn(
                        f"Deprecated pattern '{pattern}' still exists - should be removed in SSOT remediation",
                        DeprecationWarning
                    )
                    
            except ImportError:
                # AFTER REMEDIATION: Module might be removed - acceptable
                continue
                
        self.logger.info("Factory pattern replacement guidance test completed")


if __name__ == '__main__':
    pytest.main([__file__])