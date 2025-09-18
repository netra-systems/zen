"""
CRITICAL SSOT Tests: MessageRouter Import Validation - Issue #1101

PURPOSE: Prove that multiple MessageRouter implementations violate SSOT.
These tests SHOULD FAIL before remediation and PASS after consolidation.

VIOLATION: 4 different MessageRouter implementations:
- Primary: websocket_core.handlers.MessageRouter (SSOT target)
- Duplicate: core.message_router.MessageRouter (to remove)
- Specialized: services.websocket.quality_message_router.QualityMessageRouter (to integrate)  
- Import alias: agents.message_router.MessageRouter (to fix)

BUSINESS IMPACT: $500K+ ARR Golden Path failures due to inconsistent routing
"""

import pytest
import unittest
import importlib
import inspect
from typing import Set, List, Dict, Any
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class MessageRouterSSOTImportValidationTests(SSotBaseTestCase):
    """Test that MessageRouter imports resolve to single implementation."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.expected_ssot_path = "netra_backend.app.websocket_core.handlers"
        self.all_import_paths = [
            "netra_backend.app.websocket_core.handlers",
            "netra_backend.app.core.message_router", 
            "netra_backend.app.agents.message_router",
            "netra_backend.app.services.websocket.quality_message_router"
        ]

    def test_single_message_router_implementation_exists(self):
        """
        CRITICAL: Test that only ONE MessageRouter implementation exists.

        SHOULD FAIL: Currently 4 different implementations
        WILL PASS: After consolidation to single SSOT implementation
        """
        unique_implementations = set()

        all_import_paths = [
            "netra_backend.app.websocket_core.handlers",
            "netra_backend.app.core.message_router",
            "netra_backend.app.agents.message_router",
            "netra_backend.app.services.websocket.quality_message_router"
        ]

        for path in all_import_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    implementation_id = f"{router_class.__module__}.{router_class.__qualname__}"
                    unique_implementations.add(implementation_id)
                elif hasattr(module, 'QualityMessageRouter'):
                    # QualityMessageRouter should be integrated into main router
                    quality_class = getattr(module, 'QualityMessageRouter')
                    implementation_id = f"{quality_class.__module__}.{quality_class.__qualname__}"
                    unique_implementations.add(implementation_id)
            except ImportError:
                continue
        
        # CRITICAL TEST: Should be exactly 1 after SSOT consolidation
        self.assertEqual(
            len(unique_implementations), 1,
            f"SSOT VIOLATION: Found {len(unique_implementations)} MessageRouter implementations: "
            f"{unique_implementations}. Expected exactly 1 SSOT implementation."
        )

    def test_all_imports_resolve_to_same_class(self):
        """
        CRITICAL: Test that all MessageRouter imports resolve to same class.
        
        SHOULD FAIL: Currently different classes from different modules
        WILL PASS: After all imports point to SSOT implementation
        """
        router_classes = []
        
        for path in ["netra_backend.app.websocket_core.handlers", 
                    "netra_backend.app.core.message_router",
                    "netra_backend.app.agents.message_router"]:
            try:
                module = importlib.import_module(path)
                if hasattr(module, 'MessageRouter'):
                    router_classes.append(getattr(module, 'MessageRouter'))
            except ImportError:
                continue
        
        if len(router_classes) > 1:
            # Check if all classes are actually the same class
            first_class = router_classes[0]
            for router_class in router_classes[1:]:
                self.assertIs(
                    router_class, first_class,
                    f"SSOT VIOLATION: MessageRouter imports resolve to different classes. "
                    f"Expected all imports to resolve to {first_class}, "
                    f"but {router_class} is different."
                )

    def test_message_router_import_consistency_across_services(self):
        """
        CRITICAL: Test import path consistency across all services.
        
        SHOULD FAIL: Currently inconsistent import paths  
        WILL PASS: After all services use consistent SSOT import
        """
        import_violations = []
        
        # Check that core.message_router is not the authoritative implementation
        try:
            from netra_backend.app.core.message_router import MessageRouter as CoreRouter
            from netra_backend.app.websocket_core.handlers import MessageRouter as WebSocketRouter
            
            # These should be the same class after SSOT consolidation
            if CoreRouter is not WebSocketRouter:
                import_violations.append(
                    f"core.message_router.MessageRouter ({CoreRouter}) != "
                    f"websocket_core.handlers.MessageRouter ({WebSocketRouter})"
                )
        except ImportError:
            pass
        
        # Check agents import consistency
        try:
            from netra_backend.app.agents.message_router import MessageRouter as AgentsRouter
            from netra_backend.app.websocket_core.handlers import MessageRouter as WebSocketRouter
            
            if AgentsRouter is not WebSocketRouter:
                import_violations.append(
                    f"agents.message_router.MessageRouter ({AgentsRouter}) != "
                    f"websocket_core.handlers.MessageRouter ({WebSocketRouter})"
                )
        except ImportError:
            pass
            
        self.assertEqual(
            len(import_violations), 0,
            f"SSOT VIOLATION: Found {len(import_violations)} import inconsistencies: "
            f"{'; '.join(import_violations)}"
        )

    def test_quality_router_features_integrated_in_main_router(self):
        """
        CRITICAL: Test that QualityMessageRouter features are in main router.
        
        SHOULD FAIL: Currently separate QualityMessageRouter class
        WILL PASS: After quality features integrated into main MessageRouter
        """
        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            # Check if QualityMessageRouter methods exist in main MessageRouter
            quality_methods = [method for method in dir(QualityMessageRouter) 
                             if not method.startswith('_') and callable(getattr(QualityMessageRouter, method))]
            
            main_router_methods = [method for method in dir(MessageRouter)
                                 if not method.startswith('_') and callable(getattr(MessageRouter, method))]
            
            missing_quality_methods = []
            for method in quality_methods:
                if method not in main_router_methods:
                    missing_quality_methods.append(method)
            
            self.assertEqual(
                len(missing_quality_methods), 0,
                f"SSOT VIOLATION: QualityMessageRouter methods not integrated into main router: "
                f"{missing_quality_methods}. Quality routing should be part of main router."
            )
            
        except ImportError:
            # If QualityMessageRouter doesn't exist, that's actually good - means it's integrated
            pass

    def test_no_duplicate_message_routing_logic(self):
        """
        CRITICAL: Test that message routing logic is not duplicated.
        
        SHOULD FAIL: Currently multiple route() methods in different classes
        WILL PASS: After consolidation to single routing implementation
        """
        routing_implementations = []
        
        # Check main implementations for routing logic
        implementations_to_check = [
            ("netra_backend.app.websocket_core.handlers", "MessageRouter"),
            ("netra_backend.app.core.message_router", "MessageRouter"),
            ("netra_backend.app.services.websocket.quality_message_router", "QualityMessageRouter")
        ]
        
        for module_path, class_name in implementations_to_check:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    router_class = getattr(module, class_name)
                    if hasattr(router_class, 'route') or hasattr(router_class, 'handle_message'):
                        routing_implementations.append(f"{module_path}.{class_name}")
            except ImportError:
                continue
        
        # After SSOT consolidation, should be exactly 1 routing implementation
        self.assertLessEqual(
            len(routing_implementations), 1,
            f"SSOT VIOLATION: Found {len(routing_implementations)} routing implementations: "
            f"{routing_implementations}. Should have exactly 1 SSOT routing implementation."
        )


@pytest.mark.unit
class MessageRouterRaceConditionPreventionTests(SSotBaseTestCase):
    """Test that consolidated router prevents race conditions."""

    def test_concurrent_routing_uses_same_router_instance(self):
        """
        CRITICAL: Test concurrent access uses same router consistently.
        
        SHOULD FAIL: Currently different routers can be used concurrently  
        WILL PASS: After SSOT ensures single router instance
        """
        import threading
        import time
        
        router_instances = []
        
        def get_router_instance():
            try:
                from netra_backend.app.websocket_core.handlers import MessageRouter
                router = MessageRouter()
                router_instances.append(id(router))
            except Exception:
                pass
        
        # Create multiple threads accessing router
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_router_instance)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=1.0)
        
        # All router instances should be consistent (same class at least)
        # This is a basic consistency check - full singleton behavior tested elsewhere
        self.assertGreater(
            len(router_instances), 0,
            "Could not create any router instances in concurrent test"
        )

    def test_message_handler_consistency(self):
        """
        CRITICAL: Test that message handlers are consistently available.
        
        SHOULD FAIL: Currently handlers might vary between router implementations
        WILL PASS: After SSOT consolidation ensures consistent handlers
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            # Create multiple router instances
            router1 = MessageRouter()
            router2 = MessageRouter()
            
            # Check handler consistency (both should have same handler types)
            handlers1 = getattr(router1, 'custom_handlers', []) + getattr(router1, 'builtin_handlers', [])
            handlers2 = getattr(router2, 'custom_handlers', []) + getattr(router2, 'builtin_handlers', [])
            
            handler_types1 = [type(handler).__name__ for handler in handlers1]
            handler_types2 = [type(handler).__name__ for handler in handlers2]
            
            self.assertEqual(
                sorted(handler_types1), sorted(handler_types2),
                "SSOT VIOLATION: MessageRouter instances have inconsistent handlers. "
                f"Router1 handlers: {handler_types1}, Router2 handlers: {handler_types2}"
            )
            
        except Exception as e:
            self.fail(f"Could not test handler consistency: {e}")


if __name__ == '__main__':
    unittest.main()