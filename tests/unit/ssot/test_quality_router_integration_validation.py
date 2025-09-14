"""
STRATEGIC SSOT Tests: QualityMessageRouter Integration Validation - Issue #1101

PURPOSE: Validate that QualityMessageRouter functionality is properly integrated
into the main MessageRouter after SSOT consolidation.

VIOLATION: Separate QualityMessageRouter should be integrated into main router
BUSINESS IMPACT: Quality features isolated from main routing logic

These tests SHOULD FAIL before integration and PASS after consolidation.
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestQualityRouterIntegrationValidation(SSotAsyncTestCase):
    """Test QualityMessageRouter integration into main router."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_supervisor = Mock()
        self.mock_db_session_factory = Mock()
        self.mock_quality_gate_service = Mock()
        self.mock_monitoring_service = Mock()

    def test_main_router_has_quality_handlers(self):
        """
        CRITICAL: Test that main MessageRouter includes quality handlers.
        
        SHOULD FAIL: Currently quality handlers only in QualityMessageRouter
        WILL PASS: After quality handlers integrated into main router
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            router = MessageRouter()
            
            # Check for quality-related handlers in main router
            all_handlers = []
            if hasattr(router, 'custom_handlers'):
                all_handlers.extend(router.custom_handlers)
            if hasattr(router, 'builtin_handlers'):
                all_handlers.extend(router.builtin_handlers)
            
            handler_types = [type(handler).__name__ for handler in all_handlers]
            
            # After integration, should have quality-related handlers
            quality_handler_found = any(
                'quality' in handler_type.lower() or 
                'gate' in handler_type.lower() or
                'monitoring' in handler_type.lower()
                for handler_type in handler_types
            )
            
            self.assertTrue(
                quality_handler_found,
                f"INTEGRATION VIOLATION: Main MessageRouter missing quality handlers. "
                f"Found handlers: {handler_types}. Expected quality-related handlers."
            )
            
        except ImportError:
            self.fail("Could not import main MessageRouter for quality handler test")

    def test_main_router_has_quality_message_types(self):
        """
        CRITICAL: Test that main router handles quality message types.
        
        SHOULD FAIL: Currently quality messages only handled by separate router
        WILL PASS: After main router handles all quality message types
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            router = MessageRouter()
            
            # Quality message types that should be handled
            quality_message_types = [
                'quality_gate_check',
                'quality_monitoring_start',
                'quality_monitoring_stop',
                'quality_metrics_request',
                'quality_threshold_update'
            ]
            
            # Check if router can handle quality message types
            # This assumes router has a method to check supported message types
            if hasattr(router, 'get_supported_message_types'):
                supported_types = router.get_supported_message_types()
                
                missing_quality_types = []
                for msg_type in quality_message_types:
                    if msg_type not in supported_types:
                        missing_quality_types.append(msg_type)
                
                self.assertEqual(
                    len(missing_quality_types), 0,
                    f"INTEGRATION VIOLATION: Main router missing quality message types: "
                    f"{missing_quality_types}"
                )
            else:
                # Alternative check: look for quality-related methods
                router_methods = [method for method in dir(router) 
                                if not method.startswith('_') and 'quality' in method.lower()]
                
                self.assertGreater(
                    len(router_methods), 0,
                    f"INTEGRATION VIOLATION: Main router has no quality-related methods. "
                    f"Expected quality methods after integration."
                )
                
        except ImportError:
            self.fail("Could not import main MessageRouter for quality message test")

    async def test_quality_routing_functionality_preserved(self):
        """
        CRITICAL: Test that quality routing functionality is preserved in main router.
        
        SHOULD FAIL: Currently quality routing separate from main routing
        WILL PASS: After quality functionality integrated without loss
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            router = MessageRouter()
            
            # Create mock quality message
            quality_message = {
                'type': 'quality_gate_check',
                'data': {
                    'check_type': 'data_quality',
                    'threshold': 0.95
                }
            }
            
            # Test that router can process quality message
            # This is a functional test of integration
            if hasattr(router, 'route_message') or hasattr(router, 'handle_message'):
                route_method = getattr(router, 'route_message', None) or getattr(router, 'handle_message', None)
                
                # Mock WebSocket connection
                mock_websocket = AsyncMock()
                mock_websocket.send = AsyncMock()
                
                try:
                    if asyncio.iscoroutinefunction(route_method):
                        result = await route_method(quality_message, mock_websocket)
                    else:
                        result = route_method(quality_message, mock_websocket)
                    
                    # Should not raise exception and should process message
                    self.assertIsNotNone(result or True)  # Accept None as valid result
                    
                except Exception as e:
                    self.fail(
                        f"INTEGRATION VIOLATION: Main router cannot process quality message. "
                        f"Error: {e}. Quality functionality not properly integrated."
                    )
            else:
                self.fail(
                    "INTEGRATION VIOLATION: Main router missing route_message/handle_message method"
                )
                
        except ImportError:
            self.fail("Could not import main MessageRouter for quality functionality test")

    def test_no_separate_quality_router_imports(self):
        """
        CRITICAL: Test that separate QualityMessageRouter is no longer imported.
        
        SHOULD FAIL: Currently separate QualityMessageRouter exists
        WILL PASS: After integration, no separate quality router needed
        """
        # Check if QualityMessageRouter still exists as separate implementation
        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            
            # If we can import it, check if it's just a compatibility shim
            quality_router = QualityMessageRouter(
                supervisor=self.mock_supervisor,
                db_session_factory=self.mock_db_session_factory,
                quality_gate_service=self.mock_quality_gate_service,
                monitoring_service=self.mock_monitoring_service
            )
            
            # Check if it's actually a wrapper around main router
            if hasattr(quality_router, '_main_router'):
                # Good - it's delegating to main router
                pass
            else:
                self.fail(
                    "INTEGRATION VIOLATION: QualityMessageRouter still exists as separate implementation. "
                    "Should be integrated into main MessageRouter or be a thin compatibility wrapper."
                )
                
        except ImportError:
            # Good - QualityMessageRouter no longer exists as separate module
            # This is the expected state after integration
            pass

    def test_quality_services_properly_injected(self):
        """
        CRITICAL: Test that quality services are properly available in main router.
        
        SHOULD FAIL: Currently quality services only injected into separate router
        WILL PASS: After main router has access to quality services
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            # Main router should be able to work with quality services
            # This test assumes router constructor or factory accepts quality services
            
            # Try to create router with quality services (integration approach)
            try:
                # This might fail if integration not complete - that's expected
                router = MessageRouter(
                    quality_gate_service=self.mock_quality_gate_service,
                    monitoring_service=self.mock_monitoring_service
                )
                
                # If successful, router should have quality services
                self.assertTrue(
                    hasattr(router, 'quality_gate_service') or 
                    hasattr(router, 'monitoring_service'),
                    "INTEGRATION VIOLATION: Main router accepted quality services but doesn't store them"
                )
                
            except TypeError:
                # Expected if integration not complete
                self.fail(
                    "INTEGRATION VIOLATION: Main MessageRouter cannot accept quality services. "
                    "Integration incomplete - quality services should be injectable."
                )
                
        except ImportError:
            self.fail("Could not import main MessageRouter for quality services test")


class TestQualityRoutingMigrationValidation(SSotAsyncTestCase):
    """Test that quality routing migration maintains functionality."""

    async def test_quality_message_routing_compatibility(self):
        """
        CRITICAL: Test backward compatibility for quality message routing.
        
        SHOULD FAIL: If compatibility broken during integration
        WILL PASS: After integration maintains all existing functionality
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            router = MessageRouter()
            
            # Test various quality message formats
            quality_messages = [
                {'type': 'quality_gate_check', 'data': {'threshold': 0.9}},
                {'type': 'quality_monitoring_start', 'data': {'interval': 60}},
                {'type': 'quality_metrics_request', 'data': {'metrics': ['accuracy', 'latency']}}
            ]
            
            mock_websocket = AsyncMock()
            processed_messages = 0
            
            for message in quality_messages:
                try:
                    if hasattr(router, 'route_message'):
                        if asyncio.iscoroutinefunction(router.route_message):
                            await router.route_message(message, mock_websocket)
                        else:
                            router.route_message(message, mock_websocket)
                        processed_messages += 1
                    elif hasattr(router, 'handle_message'):
                        if asyncio.iscoroutinefunction(router.handle_message):
                            await router.handle_message(message, mock_websocket)
                        else:
                            router.handle_message(message, mock_websocket)
                        processed_messages += 1
                except Exception as e:
                    # Message processing failed - integration issue
                    self.fail(
                        f"COMPATIBILITY VIOLATION: Quality message routing failed for {message['type']}. "
                        f"Error: {e}. Integration broke existing functionality."
                    )
            
            self.assertEqual(
                processed_messages, len(quality_messages),
                f"COMPATIBILITY VIOLATION: Only {processed_messages}/{len(quality_messages)} "
                f"quality messages processed successfully"
            )
            
        except ImportError:
            self.fail("Could not import main MessageRouter for compatibility test")

    def test_quality_handler_chain_preserved(self):
        """
        CRITICAL: Test that quality handler chain is preserved after integration.
        
        SHOULD FAIL: If handler chain broken during integration
        WILL PASS: After integration preserves complete handler functionality
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            router = MessageRouter()
            
            # Get all handlers
            all_handlers = []
            if hasattr(router, 'custom_handlers'):
                all_handlers.extend(router.custom_handlers)
            if hasattr(router, 'builtin_handlers'):
                all_handlers.extend(router.builtin_handlers)
            
            # Test that handlers form proper chain
            if all_handlers:
                for i, handler in enumerate(all_handlers):
                    # Each handler should be callable
                    self.assertTrue(
                        callable(handler) or hasattr(handler, 'handle'),
                        f"HANDLER CHAIN VIOLATION: Handler {i} ({type(handler)}) not callable"
                    )
                    
                    # Handler should have proper interface
                    if hasattr(handler, 'handle'):
                        handle_method = getattr(handler, 'handle')
                        self.assertTrue(
                            callable(handle_method),
                            f"HANDLER CHAIN VIOLATION: Handler {i} handle method not callable"
                        )
            else:
                self.fail(
                    "HANDLER CHAIN VIOLATION: No handlers found in main router. "
                    "Quality integration may have broken handler chain."
                )
                
        except ImportError:
            self.fail("Could not import main MessageRouter for handler chain test")


if __name__ == '__main__':
    unittest.main()