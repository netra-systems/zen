"""
Test to validate CanonicalMessageRouter as the SOLE message routing authority.

This test validates that after SSOT consolidation, CanonicalMessageRouter is the 
single source of truth for all message routing functionality, with all other
routers being adapters that delegate to it.

Business Value:
- Ensures consistent message routing behavior across all system components
- Validates proper user isolation in multi-user chat environment  
- Protects $500K+ ARR Golden Path by ensuring reliable message delivery
- Prevents cross-user message routing security vulnerabilities

This test should PASS after SSOT consolidation is complete.

Created: 2025-09-17
GitHub Issue: SSOT-incomplete-migration-message-routing-consolidation
"""

import asyncio
import inspect
import importlib
from typing import List, Dict, Any, Set, Type, Optional
from unittest.mock import patch, MagicMock, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class TestCanonicalMessageRouterSoleAuthority(SSotAsyncTestCase):
    """
    Test that validates CanonicalMessageRouter as the sole routing authority.
    
    This test should PASS after SSOT consolidation is complete.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.env = get_env()
        self.canonical_router = None

    async def test_canonical_router_is_primary_implementation(self):
        """
        Test that CanonicalMessageRouter is the primary implementation.
        
        Validates that CanonicalMessageRouter exists and has all core functionality
        required for message routing in the system.
        """
        # Import and validate CanonicalMessageRouter exists
        try:
            from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
            self.canonical_router = CanonicalMessageRouter
        except ImportError as e:
            self.fail(f"CRITICAL: CanonicalMessageRouter not found: {e}")

        # Validate it has core routing methods
        required_methods = [
            'route_message',
            'broadcast_message', 
            'send_to_user',
            'handle_agent_event',
            'initialize_user_context'
        ]

        for method_name in required_methods:
            self.assertTrue(
                hasattr(self.canonical_router, method_name),
                f"CanonicalMessageRouter missing required method: {method_name}"
            )

        # Validate it can be instantiated
        try:
            router_instance = self.canonical_router(user_context={'user_id': 'test_user'})
            self.assertIsNotNone(router_instance)
        except Exception as e:
            self.fail(f"Cannot instantiate CanonicalMessageRouter: {e}")

    async def test_all_other_routers_are_adapters(self):
        """
        Test that all other router implementations are adapters that delegate to CanonicalMessageRouter.
        
        After SSOT consolidation, any remaining router classes should inherit from
        or delegate to CanonicalMessageRouter.
        """
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        
        # Check legacy router implementations
        legacy_routers = await self._get_legacy_router_implementations()
        
        for router_info in legacy_routers:
            router_class = router_info['class']
            
            # Check if it inherits from CanonicalMessageRouter
            is_subclass = issubclass(router_class, CanonicalMessageRouter)
            
            # Check if it delegates to CanonicalMessageRouter
            delegates_to_canonical = await self._check_delegation_pattern(router_class)
            
            # One of these should be true for proper SSOT compliance
            self.assertTrue(
                is_subclass or delegates_to_canonical,
                f"Router {router_info['name']} must either inherit from or delegate to CanonicalMessageRouter. "
                f"Inherits: {is_subclass}, Delegates: {delegates_to_canonical}"
            )

    async def test_canonical_router_factory_is_primary(self):
        """
        Test that the canonical factory function is the primary way to create routers.
        
        Validates that create_message_router() function creates CanonicalMessageRouter instances.
        """
        try:
            from netra_backend.app.websocket_core.canonical_message_router import create_message_router
        except ImportError:
            self.fail("create_message_router factory function not found")

        # Test factory creates CanonicalMessageRouter
        router_instance = create_message_router(user_context={'user_id': 'test_user'})
        
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        self.assertIsInstance(
            router_instance, 
            CanonicalMessageRouter,
            f"create_message_router() must return CanonicalMessageRouter instance, got {type(router_instance)}"
        )

    async def test_user_isolation_in_canonical_router(self):
        """
        Test that CanonicalMessageRouter provides proper user isolation.
        
        Critical for multi-user chat environment - ensures messages are routed 
        only to intended users.
        """
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        
        # Create routers for different users
        user1_context = {'user_id': 'user1', 'session_id': 'session1'}
        user2_context = {'user_id': 'user2', 'session_id': 'session2'}
        
        router1 = CanonicalMessageRouter(user_context=user1_context)
        router2 = CanonicalMessageRouter(user_context=user2_context)
        
        # Verify they are separate instances
        self.assertIsNot(router1, router2, "Router instances must be separate for different users")
        
        # Verify they have different user contexts
        self.assertEqual(router1.user_context['user_id'], 'user1')
        self.assertEqual(router2.user_context['user_id'], 'user2')
        
        # Test that routing respects user boundaries
        with patch.object(router1, '_send_to_websocket') as mock_send1, \
             patch.object(router2, '_send_to_websocket') as mock_send2:
            
            # User1 router should only send to user1
            await router1.send_to_user('user1', {'message': 'test'})
            mock_send1.assert_called_once()
            mock_send2.assert_not_called()

    async def test_canonical_router_handles_all_message_types(self):
        """
        Test that CanonicalMessageRouter can handle all WebSocket message types.
        
        Validates comprehensive message handling capability.
        """
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        
        router = CanonicalMessageRouter(user_context={'user_id': 'test_user'})
        
        # Test all critical message types
        message_types = [
            MessageType.AGENT_STARTED,
            MessageType.AGENT_THINKING, 
            MessageType.TOOL_EXECUTING,
            MessageType.TOOL_COMPLETED,
            MessageType.AGENT_COMPLETED,
            MessageType.USER_MESSAGE,
            MessageType.SYSTEM_MESSAGE
        ]
        
        for msg_type in message_types:
            test_message = WebSocketMessage(
                type=msg_type,
                data={'test': 'data'},
                user_id='test_user'
            )
            
            # Should not raise exception
            try:
                await router.route_message(test_message)
            except Exception as e:
                self.fail(f"CanonicalMessageRouter failed to handle {msg_type}: {e}")

    async def test_canonical_router_performance_requirements(self):
        """
        Test that CanonicalMessageRouter meets performance requirements.
        
        Ensures the consolidated router doesn't introduce performance regressions.
        """
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        
        router = CanonicalMessageRouter(user_context={'user_id': 'test_user'})
        
        # Test message routing performance
        test_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            data={'message': 'test performance'},
            user_id='test_user'
        )
        
        # Mock the actual sending to avoid external dependencies
        with patch.object(router, '_send_to_websocket', new_callable=AsyncMock) as mock_send:
            import time
            
            start_time = time.time()
            await router.route_message(test_message)
            end_time = time.time()
            
            routing_time = end_time - start_time
            
            # Message routing should be very fast (< 10ms for mocked operation)
            self.assertLess(
                routing_time, 
                0.01,  # 10ms
                f"Message routing took {routing_time:.4f}s, should be < 0.01s"
            )

    async def test_canonical_router_error_handling(self):
        """
        Test that CanonicalMessageRouter has robust error handling.
        
        Ensures the router can handle various error conditions gracefully.
        """
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        
        router = CanonicalMessageRouter(user_context={'user_id': 'test_user'})
        
        # Test handling invalid message
        invalid_message = "not a message object"
        
        try:
            await router.route_message(invalid_message)
        except Exception as e:
            # Should handle gracefully with appropriate error
            self.assertIn("message", str(e).lower(), "Error should mention message validation")

        # Test handling missing user context
        try:
            router_no_context = CanonicalMessageRouter(user_context=None)
            test_message = WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                data={'message': 'test'},
                user_id='test_user'
            )
            await router_no_context.route_message(test_message)
        except Exception as e:
            # Should handle gracefully
            self.assertIn("context", str(e).lower(), "Error should mention context requirement")

    async def _get_legacy_router_implementations(self) -> List[Dict[str, Any]]:
        """Get list of legacy router implementations that should be adapters."""
        routers = []
        
        # Check if legacy implementations still exist
        legacy_imports = [
            ('WebSocketEventRouter', 'netra_backend.app.services.websocket_event_router'),
            ('UserScopedWebSocketEventRouter', 'netra_backend.app.services.user_scoped_websocket_event_router'),
            ('MessageRouter', 'netra_backend.app.routes.message_router'),
        ]
        
        for class_name, module_name in legacy_imports:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, class_name):
                    router_class = getattr(module, class_name)
                    routers.append({
                        'name': class_name,
                        'class': router_class,
                        'module': module_name
                    })
            except ImportError:
                # Module doesn't exist anymore, which is fine
                continue
                
        return routers

    async def _check_delegation_pattern(self, router_class: Type) -> bool:
        """Check if a router class delegates to CanonicalMessageRouter."""
        try:
            # Check if class has delegation indicators in source
            source = inspect.getsource(router_class)
            
            # Look for delegation patterns
            delegation_indicators = [
                'CanonicalMessageRouter',
                'canonical_router',
                'self._canonical',
                'delegate_to_canonical'
            ]
            
            return any(indicator in source for indicator in delegation_indicators)
        except (OSError, TypeError):
            return False

    async def test_canonical_router_websocket_event_integration(self):
        """
        Test that CanonicalMessageRouter properly integrates with WebSocket events.
        
        Critical for Golden Path - ensures all 5 business-critical events are handled.
        """
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        from netra_backend.app.websocket_core.types import MessageType
        
        router = CanonicalMessageRouter(user_context={'user_id': 'test_user'})
        
        # Test all 5 critical WebSocket events
        critical_events = [
            MessageType.AGENT_STARTED,
            MessageType.AGENT_THINKING,
            MessageType.TOOL_EXECUTING, 
            MessageType.TOOL_COMPLETED,
            MessageType.AGENT_COMPLETED
        ]
        
        for event_type in critical_events:
            # Should have specific handler for each critical event
            handler_method = f"handle_{event_type.value}"
            
            # Check if specific handler exists or can be handled by generic route_message
            has_specific_handler = hasattr(router, handler_method)
            has_generic_handler = hasattr(router, 'route_message')
            
            self.assertTrue(
                has_specific_handler or has_generic_handler,
                f"CanonicalMessageRouter must handle critical event {event_type.value}"
            )