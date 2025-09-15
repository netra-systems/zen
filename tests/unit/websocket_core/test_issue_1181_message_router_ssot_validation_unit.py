"""
Unit Tests for Issue #1181 MessageRouter SSOT Validation
=========================================================

Business Value Justification:
- Segment: Platform/Critical Infrastructure
- Business Goal: SSOT Compliance & System Stability
- Value Impact: Prevents SSOT violations that could break $500K+ ARR chat functionality
- Strategic Impact: Ensures MessageRouter consolidation follows SSOT principles

CRITICAL SSOT VALIDATION:
Issue #1181 requires MessageRouter SSOT consolidation to eliminate fragmentation
while maintaining all existing functionality. These tests validate that the 
MessageRouter implementation follows SSOT principles and that any consolidation
preserves the single authoritative implementation.

Tests verify SSOT compliance, import path consolidation, and interface consistency
across all MessageRouter usage patterns.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import inspect
import importlib
import sys
from typing import Dict, Any, List, Type
from pathlib import Path

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.unit
class Issue1181MessageRouterSSOTValidationTests(SSotAsyncTestCase, unittest.TestCase):
    """Test suite to validate MessageRouter SSOT compliance for Issue #1181."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.canonical_import_path = "netra_backend.app.websocket_core.handlers"
        self.canonical_class_name = "MessageRouter"
        self.expected_methods = [
            "route_message",
            "add_handler", 
            "remove_handler",
            "get_stats",
            "_find_handler",
            "_prepare_message"
        ]
        
    def test_canonical_message_router_import_succeeds(self):
        """
        SSOT TEST: Verify that the canonical MessageRouter can be imported successfully.
        
        The main MessageRouter should be importable from its canonical location
        and should be the authoritative implementation.
        """
        logger.info(" TESTING:  Canonical MessageRouter import validation")
        
        try:
            # Import from canonical path
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            # Verify it's a class
            self.assertTrue(inspect.isclass(MessageRouter), "MessageRouter should be a class")
            
            # Verify it can be instantiated
            router = MessageRouter()
            self.assertIsNotNone(router, "MessageRouter should be instantiable")
            
            # Verify it has expected methods
            for method_name in self.expected_methods:
                self.assertTrue(
                    hasattr(router, method_name),
                    f"MessageRouter missing expected method: {method_name}"
                )
                self.assertTrue(
                    callable(getattr(router, method_name)),
                    f"MessageRouter method {method_name} should be callable"
                )
            
            logger.info(" PASS:  Canonical MessageRouter import and instantiation successful")
            
        except ImportError as e:
            self.fail(f"Failed to import canonical MessageRouter: {e}")
        except Exception as e:
            self.fail(f"Error validating canonical MessageRouter: {e}")
    
    def test_message_router_class_identity_consistency(self):
        """
        SSOT TEST: Verify that MessageRouter class identity is consistent across imports.
        
        All import paths should resolve to the same class object to ensure SSOT compliance.
        """
        logger.info(" TESTING:  MessageRouter class identity consistency")
        
        # Import from canonical path
        from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalRouter
        
        # Test potential alternative import paths (these may not exist or may be proxies)
        alternative_paths = [
            "netra_backend.app.core.message_router",
            "netra_backend.app.agents.message_router", 
            "netra_backend.app.services.message_router"
        ]
        
        identical_imports = []
        proxy_imports = []
        broken_imports = []
        
        for alt_path in alternative_paths:
            try:
                # Try to import MessageRouter from alternative path
                module = importlib.import_module(alt_path)
                if hasattr(module, 'MessageRouter'):
                    alt_router = getattr(module, 'MessageRouter')
                    
                    # Check if it's the same class object (SSOT compliant)
                    if alt_router is CanonicalRouter:
                        identical_imports.append(alt_path)
                        logger.info(f" PASS:  {alt_path} imports identical MessageRouter class")
                    else:
                        # Check if it's a proxy/subclass (acceptable during migration)
                        if inspect.isclass(alt_router) and issubclass(alt_router, CanonicalRouter):
                            proxy_imports.append(alt_path)
                            logger.info(f" WARN:  {alt_path} imports MessageRouter proxy/subclass")
                        else:
                            broken_imports.append(alt_path)
                            logger.error(f" FAIL:  {alt_path} imports different MessageRouter class")
                else:
                    logger.info(f" INFO:  {alt_path} does not export MessageRouter")
            
            except ImportError:
                logger.info(f" INFO:  {alt_path} does not exist or cannot be imported")
            except Exception as e:
                broken_imports.append(f"{alt_path}: {str(e)}")
                logger.error(f" FAIL:  Error importing from {alt_path}: {e}")
        
        # Report results
        logger.info(f" SUMMARY:  MessageRouter class identity check:")
        logger.info(f"   - Identical imports: {len(identical_imports)} - {identical_imports}")
        logger.info(f"   - Proxy imports: {len(proxy_imports)} - {proxy_imports}")
        logger.info(f"   - Broken imports: {len(broken_imports)} - {broken_imports}")
        
        # SSOT validation: No broken imports should exist
        self.assertEqual(
            len(broken_imports), 0,
            f"Found broken MessageRouter imports that violate SSOT: {broken_imports}"
        )
        
        logger.info(" PASS:  MessageRouter class identity consistency validated")
    
    def test_message_router_interface_completeness(self):
        """
        SSOT TEST: Verify that MessageRouter has a complete and consistent interface.
        
        The MessageRouter should have all expected methods and properties needed
        for both core functionality and quality integration.
        """
        logger.info(" TESTING:  MessageRouter interface completeness")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        
        # Test core message routing interface
        core_methods = [
            ("route_message", "async"),
            ("add_handler", "sync"),
            ("remove_handler", "sync"),
            ("insert_handler", "sync"),
            ("get_handler_order", "sync"),
            ("_find_handler", "sync"),
            ("_prepare_message", "async"),
            ("get_stats", "sync")
        ]
        
        for method_name, method_type in core_methods:
            self.assertTrue(
                hasattr(router, method_name),
                f"MessageRouter missing core method: {method_name}"
            )
            
            method = getattr(router, method_name)
            self.assertTrue(callable(method), f"Method {method_name} should be callable")
            
            # Check if method is async when expected
            if method_type == "async":
                self.assertTrue(
                    inspect.iscoroutinefunction(method),
                    f"Method {method_name} should be async"
                )
            
            logger.info(f" PASS:  Core method {method_name} ({method_type}) verified")
        
        # Test quality integration interface (Phase 2 compatibility)
        quality_methods = [
            ("handle_quality_message", "async"),
            ("_is_quality_message_type", "sync"),
            ("_initialize_quality_handlers", "async"),
            ("broadcast_quality_update", "async"),
            ("broadcast_quality_alert", "async")
        ]
        
        quality_method_count = 0
        for method_name, method_type in quality_methods:
            if hasattr(router, method_name):
                quality_method_count += 1
                method = getattr(router, method_name)
                self.assertTrue(callable(method), f"Quality method {method_name} should be callable")
                
                if method_type == "async":
                    self.assertTrue(
                        inspect.iscoroutinefunction(method),
                        f"Quality method {method_name} should be async"
                    )
                
                logger.info(f" PASS:  Quality method {method_name} ({method_type}) verified")
            else:
                logger.info(f" INFO:  Quality method {method_name} not yet implemented")
        
        # Test compatibility interface for testing
        compatibility_methods = [
            ("add_route", "sync"),
            ("add_middleware", "sync"), 
            ("start", "sync"),
            ("stop", "sync"),
            ("get_statistics", "sync")
        ]
        
        compatibility_method_count = 0
        for method_name, method_type in compatibility_methods:
            if hasattr(router, method_name):
                compatibility_method_count += 1
                method = getattr(router, method_name)
                self.assertTrue(callable(method), f"Compatibility method {method_name} should be callable")
                logger.info(f" PASS:  Compatibility method {method_name} verified")
            else:
                logger.info(f" INFO:  Compatibility method {method_name} not implemented")
        
        # Validate that core interface is complete (all core methods must be present)
        core_method_names = [name for name, _ in core_methods]
        missing_core_methods = [name for name in core_method_names if not hasattr(router, name)]
        
        self.assertEqual(
            len(missing_core_methods), 0,
            f"MessageRouter missing critical core methods: {missing_core_methods}"
        )
        
        logger.info(f" SUMMARY:  Interface completeness validated:")
        logger.info(f"   - Core methods: {len(core_methods)}/{len(core_methods)} (required)")
        logger.info(f"   - Quality methods: {quality_method_count}/{len(quality_methods)} (optional)")
        logger.info(f"   - Compatibility methods: {compatibility_method_count}/{len(compatibility_methods)} (optional)")
        
        logger.info(" PASS:  MessageRouter interface completeness validated")
    
    def test_message_router_handler_management_ssot(self):
        """
        SSOT TEST: Verify that MessageRouter handler management follows SSOT principles.
        
        Handler registration, removal, and ordering should be consistent and follow
        a single authoritative pattern.
        """
        logger.info(" TESTING:  MessageRouter handler management SSOT compliance")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter, BaseMessageHandler
        from netra_backend.app.websocket_core.types import MessageType
        
        router = MessageRouter()
        
        # Test Case 1: Initial state should have built-in handlers
        initial_handler_count = len(router.handlers)
        initial_builtin_count = len(router.builtin_handlers)
        initial_custom_count = len(router.custom_handlers)
        
        self.assertGreater(initial_builtin_count, 0, "Should have built-in handlers")
        self.assertEqual(initial_custom_count, 0, "Should start with no custom handlers")
        self.assertEqual(
            initial_handler_count, initial_builtin_count + initial_custom_count,
            "Total handlers should equal builtin + custom"
        )
        
        logger.info(f" PASS:  Initial state: {initial_builtin_count} builtin, {initial_custom_count} custom handlers")
        
        # Test Case 2: Add custom handler should work and take precedence
        class HandlerTests(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])
        
        test_handler = HandlerTests()
        router.add_handler(test_handler)
        
        self.assertEqual(len(router.custom_handlers), 1, "Should have one custom handler")
        self.assertEqual(len(router.handlers), initial_handler_count + 1, "Total handlers should increase")
        self.assertIs(router.handlers[0], test_handler, "Custom handler should be first in priority")
        
        logger.info(" PASS:  Custom handler addition and precedence validated")
        
        # Test Case 3: Insert handler at specific position
        class Handler2Tests(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.PING])
        
        test_handler2 = Handler2Tests()
        router.insert_handler(test_handler2, 0)  # Insert at highest precedence
        
        self.assertEqual(len(router.custom_handlers), 2, "Should have two custom handlers")
        self.assertIs(router.handlers[0], test_handler2, "Inserted handler should be first")
        self.assertIs(router.handlers[1], test_handler, "Previous handler should be second")
        
        logger.info(" PASS:  Handler insertion and ordering validated")
        
        # Test Case 4: Remove handler should work
        router.remove_handler(test_handler)
        
        self.assertEqual(len(router.custom_handlers), 1, "Should have one custom handler after removal")
        self.assertIs(router.handlers[0], test_handler2, "Remaining handler should be test_handler2")
        self.assertNotIn(test_handler, router.handlers, "Removed handler should not be in list")
        
        logger.info(" PASS:  Handler removal validated")
        
        # Test Case 5: Get handler order should be deterministic
        handler_order = router.get_handler_order()
        self.assertIsInstance(handler_order, list, "Handler order should be a list")
        self.assertGreater(len(handler_order), 0, "Should have handler names")
        self.assertEqual(handler_order[0], "Handler2Tests", "First handler should be Handler2Tests")
        
        logger.info(f" PASS:  Handler order deterministic: {handler_order[:3]}...")
        
        logger.info(" PASS:  MessageRouter handler management SSOT compliance validated")
    
    def test_message_router_singleton_behavior(self):
        """
        SSOT TEST: Verify that get_message_router() returns the same instance (singleton).
        
        SSOT requires that the global message router instance is consistent
        across all calls to prevent state fragmentation.
        """
        logger.info(" TESTING:  MessageRouter singleton behavior")
        
        from netra_backend.app.websocket_core.handlers import get_message_router
        
        # Test Case 1: Multiple calls should return same instance
        router1 = get_message_router()
        router2 = get_message_router() 
        router3 = get_message_router()
        
        self.assertIs(router1, router2, "get_message_router() should return same instance")
        self.assertIs(router2, router3, "get_message_router() should return same instance")
        self.assertIs(router1, router3, "get_message_router() should return same instance")
        
        logger.info(" PASS:  Singleton behavior validated - same instance returned")
        
        # Test Case 2: Instance should be properly initialized
        self.assertIsNotNone(router1, "Router instance should not be None")
        self.assertGreater(len(router1.handlers), 0, "Router should have handlers")
        
        # Test Case 3: Utility functions should work with singleton
        from netra_backend.app.websocket_core.handlers import get_router_handler_count, list_registered_handlers
        
        handler_count = get_router_handler_count()
        handler_list = list_registered_handlers()
        
        self.assertEqual(handler_count, len(router1.handlers), "Utility function should match instance")
        self.assertEqual(len(handler_list), len(router1.handlers), "Handler list should match instance")
        
        logger.info(f" PASS:  Singleton utilities validated: {handler_count} handlers")
        
        logger.info(" PASS:  MessageRouter singleton behavior validated")
    
    def test_message_router_protocol_validation(self):
        """
        SSOT TEST: Verify that MessageRouter properly validates handler protocols.
        
        SSOT requires consistent interface validation to prevent registration
        of invalid handlers that could break the system.
        """
        logger.info(" TESTING:  MessageRouter protocol validation")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        
        # Test Case 1: Valid handler should pass validation
        class ValidHandler:
            def can_handle(self, message_type):
                return True
            
            async def handle_message(self, user_id, websocket, message):
                return True
        
        valid_handler = ValidHandler()
        validation_result = router._validate_handler_protocol(valid_handler)
        self.assertTrue(validation_result, "Valid handler should pass protocol validation")
        
        # Should be able to add valid handler
        try:
            router.add_handler(valid_handler)
            logger.info(" PASS:  Valid handler registration successful")
        except Exception as e:
            self.fail(f"Valid handler registration failed: {e}")
        
        # Test Case 2: Handler missing can_handle should fail validation
        class MissingCanHandleHandler:
            async def handle_message(self, user_id, websocket, message):
                return True
        
        invalid_handler1 = MissingCanHandleHandler()
        validation_result = router._validate_handler_protocol(invalid_handler1)
        self.assertFalse(validation_result, "Handler missing can_handle should fail validation")
        
        # Should raise TypeError when trying to add
        with self.assertRaises(TypeError) as context:
            router.add_handler(invalid_handler1)
        
        error_message = str(context.exception)
        self.assertIn("can_handle", error_message, "Error should mention missing can_handle method")
        
        logger.info(" PASS:  Missing can_handle handler properly rejected")
        
        # Test Case 3: Handler missing handle_message should fail validation
        class MissingHandleMessageHandler:
            def can_handle(self, message_type):
                return True
        
        invalid_handler2 = MissingHandleMessageHandler()
        validation_result = router._validate_handler_protocol(invalid_handler2)
        self.assertFalse(validation_result, "Handler missing handle_message should fail validation")
        
        # Should raise TypeError when trying to add
        with self.assertRaises(TypeError) as context:
            router.add_handler(invalid_handler2)
        
        error_message = str(context.exception)
        self.assertIn("handle_message", error_message, "Error should mention missing handle_message method")
        
        logger.info(" PASS:  Missing handle_message handler properly rejected")
        
        # Test Case 4: Raw function should fail validation
        def raw_function_handler():
            return True
        
        validation_result = router._validate_handler_protocol(raw_function_handler)
        self.assertFalse(validation_result, "Raw function should fail protocol validation")
        
        # Should raise TypeError when trying to add
        with self.assertRaises(TypeError) as context:
            router.add_handler(raw_function_handler)
        
        error_message = str(context.exception)
        self.assertIn("Raw functions are not supported", error_message, "Error should reject raw functions")
        
        logger.info(" PASS:  Raw function handler properly rejected")
        
        logger.info(" PASS:  MessageRouter protocol validation working correctly")
    
    def test_message_router_statistics_consistency(self):
        """
        SSOT TEST: Verify that MessageRouter statistics are consistent and accurate.
        
        SSOT requires that all statistics and metrics accurately reflect the
        current state without duplication or inconsistency.
        """
        logger.info(" TESTING:  MessageRouter statistics consistency")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        
        # Get initial statistics
        stats = router.get_stats()
        
        # Test Case 1: Statistics structure should be consistent
        required_stat_keys = [
            "messages_routed",
            "unhandled_messages", 
            "handler_errors",
            "message_types",
            "handler_stats",
            "handler_order",
            "handler_count",
            "handler_status"
        ]
        
        for key in required_stat_keys:
            self.assertIn(key, stats, f"Statistics missing required key: {key}")
        
        logger.info(" PASS:  Statistics structure validated")
        
        # Test Case 2: Handler count should match actual handlers
        actual_handler_count = len(router.handlers)
        reported_handler_count = stats["handler_count"]
        
        self.assertEqual(
            actual_handler_count, reported_handler_count,
            f"Handler count mismatch: actual={actual_handler_count}, reported={reported_handler_count}"
        )
        
        logger.info(f" PASS:  Handler count consistent: {actual_handler_count}")
        
        # Test Case 3: Handler order should match actual order
        actual_order = router.get_handler_order()
        reported_order = stats["handler_order"]
        
        self.assertEqual(
            actual_order, reported_order,
            "Handler order in statistics should match get_handler_order()"
        )
        
        logger.info(" PASS:  Handler order consistent")
        
        # Test Case 4: Handler status should include grace period info
        handler_status = stats["handler_status"]
        required_status_keys = ["status", "handler_count", "elapsed_seconds"]
        
        for key in required_status_keys:
            self.assertIn(key, handler_status, f"Handler status missing key: {key}")
        
        self.assertIsInstance(handler_status["elapsed_seconds"], (int, float), "Elapsed seconds should be numeric")
        self.assertGreaterEqual(handler_status["elapsed_seconds"], 0, "Elapsed seconds should be non-negative")
        
        logger.info(f" PASS:  Handler status consistent: {handler_status['status']}")
        
        # Test Case 5: Message type statistics should be valid
        message_types_stats = stats["message_types"]
        self.assertIsInstance(message_types_stats, dict, "Message types should be a dictionary")
        
        for msg_type, count in message_types_stats.items():
            self.assertIsInstance(count, int, f"Message type count should be integer for {msg_type}")
            self.assertGreaterEqual(count, 0, f"Message type count should be non-negative for {msg_type}")
        
        logger.info(f" PASS:  Message type statistics validated: {len(message_types_stats)} types")
        
        logger.info(" PASS:  MessageRouter statistics consistency validated")


if __name__ == '__main__':
    unittest.main()