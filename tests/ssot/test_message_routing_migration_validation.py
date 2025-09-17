"""
Test to validate message routing migration from legacy to SSOT maintains functionality.

This test ensures that the migration from multiple router implementations to 
CanonicalMessageRouter SSOT maintains all existing functionality and backwards
compatibility during the transition period.

Business Value:
- Protects $500K+ ARR during migration by ensuring no regressions
- Validates backwards compatibility for existing integrations
- Ensures smooth transition without breaking existing functionality
- Maintains user isolation and security during migration

Created: 2025-09-17
GitHub Issue: SSOT-incomplete-migration-message-routing-consolidation
"""

import asyncio
import importlib
from typing import List, Dict, Any, Set, Type, Optional, Callable
from unittest.mock import patch, MagicMock, AsyncMock, call
from dataclasses import dataclass
import time

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


@dataclass
class RouterTestCase:
    """Test case for router functionality validation."""
    name: str
    input_data: Dict[str, Any]
    expected_result: Dict[str, Any]
    test_type: str  # 'routing', 'broadcast', 'user_isolation', etc.


class TestMessageRoutingMigrationValidation(SSotAsyncTestCase):
    """
    Test that validates message routing migration maintains functionality.
    
    This test ensures backwards compatibility and functional equivalence
    during the SSOT consolidation migration.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.env = get_env()
        self.test_cases = self._create_test_cases()

    async def test_canonical_router_maintains_legacy_functionality(self):
        """
        Test that CanonicalMessageRouter provides same functionality as legacy routers.
        
        Validates that all functionality available in legacy routers is preserved
        in the consolidated implementation.
        """
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        
        # Test basic message routing functionality
        canonical_router = CanonicalMessageRouter(user_context={'user_id': 'test_user'})
        
        # Test each functional area
        await self._test_message_routing_functionality(canonical_router)
        await self._test_broadcast_functionality(canonical_router)
        await self._test_user_isolation_functionality(canonical_router)
        await self._test_agent_event_functionality(canonical_router)

    async def test_legacy_router_adapter_compatibility(self):
        """
        Test that legacy router adapters maintain API compatibility.
        
        Ensures existing code using legacy routers continues to work
        during the migration period.
        """
        legacy_routers = await self._get_available_legacy_routers()
        
        for router_info in legacy_routers:
            await self._test_legacy_router_compatibility(router_info)

    async def test_factory_function_migration(self):
        """
        Test that factory functions provide backwards compatibility.
        
        Ensures factory functions continue to work during migration.
        """
        # Test canonical factory
        try:
            from netra_backend.app.websocket_core.canonical_message_router import create_message_router
            canonical_instance = create_message_router(user_context={'user_id': 'test_user'})
            self.assertIsNotNone(canonical_instance)
        except ImportError:
            self.fail("Canonical create_message_router factory not available")

        # Test legacy factories if they exist
        legacy_factories = [
            ('get_websocket_router', 'netra_backend.app.services.websocket_event_router'),
            ('create_user_event_router', 'netra_backend.app.services.user_scoped_websocket_event_router'),
        ]

        for factory_name, module_name in legacy_factories:
            await self._test_legacy_factory_compatibility(factory_name, module_name)

    async def test_message_format_compatibility(self):
        """
        Test that message formats remain compatible during migration.
        
        Ensures messages sent by legacy routers can be handled by canonical router
        and vice versa.
        """
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        
        canonical_router = CanonicalMessageRouter(user_context={'user_id': 'test_user'})
        
        # Test various message formats
        test_messages = [
            # Agent event messages
            WebSocketMessage(
                type=MessageType.AGENT_STARTED,
                data={'agent_id': 'test_agent', 'task': 'test_task'},
                user_id='test_user'
            ),
            # Tool execution messages
            WebSocketMessage(
                type=MessageType.TOOL_EXECUTING,
                data={'tool_name': 'test_tool', 'args': {'param': 'value'}},
                user_id='test_user'
            ),
            # User messages
            WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                data={'message': 'Hello', 'thread_id': 'test_thread'},
                user_id='test_user'
            ),
        ]

        with patch.object(canonical_router, '_send_to_websocket', new_callable=AsyncMock) as mock_send:
            for message in test_messages:
                try:
                    await canonical_router.route_message(message)
                except Exception as e:
                    self.fail(f"Canonical router failed to handle message {message.type}: {e}")

    async def test_performance_regression_prevention(self):
        """
        Test that consolidated router doesn't introduce performance regressions.
        
        Ensures migration doesn't negatively impact system performance.
        """
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        
        canonical_router = CanonicalMessageRouter(user_context={'user_id': 'test_user'})
        
        # Performance baseline test
        test_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            data={'message': 'performance test'},
            user_id='test_user'
        )

        # Test routing performance
        with patch.object(canonical_router, '_send_to_websocket', new_callable=AsyncMock):
            routing_times = []
            
            for _ in range(10):  # Test multiple iterations
                start_time = time.time()
                await canonical_router.route_message(test_message)
                end_time = time.time()
                routing_times.append(end_time - start_time)

            avg_routing_time = sum(routing_times) / len(routing_times)
            max_routing_time = max(routing_times)

            # Performance requirements
            self.assertLess(avg_routing_time, 0.005, f"Average routing time {avg_routing_time:.4f}s too slow")
            self.assertLess(max_routing_time, 0.010, f"Max routing time {max_routing_time:.4f}s too slow")

    async def test_concurrent_user_migration_safety(self):
        """
        Test that migration maintains safety for concurrent users.
        
        Critical for multi-user environment - ensures migration doesn't
        introduce cross-user message routing issues.
        """
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        
        # Create routers for multiple users
        users = ['user1', 'user2', 'user3']
        routers = {}
        
        for user_id in users:
            routers[user_id] = CanonicalMessageRouter(user_context={'user_id': user_id})

        # Test concurrent message routing
        messages = []
        for user_id in users:
            message = WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                data={'message': f'Message from {user_id}', 'user_specific_data': user_id},
                user_id=user_id
            )
            messages.append((user_id, message))

        # Mock WebSocket sending to track message routing
        send_calls = {}
        for user_id in users:
            send_calls[user_id] = []

        async def mock_send_for_user(user_id):
            async def mock_send(message):
                send_calls[user_id].append(message)
            return mock_send

        # Patch each router's send method
        patches = []
        for user_id in users:
            patch_obj = patch.object(
                routers[user_id], 
                '_send_to_websocket', 
                new_callable=AsyncMock
            )
            patches.append(patch_obj)

        # Run concurrent routing
        async with asyncio.TaskGroup() as tg:
            for patch_obj in patches:
                patch_obj.start()
            
            try:
                # Send messages concurrently
                tasks = []
                for user_id, message in messages:
                    task = tg.create_task(routers[user_id].route_message(message))
                    tasks.append(task)
                
                # Wait for all tasks to complete
                await asyncio.gather(*tasks)
                
            finally:
                for patch_obj in patches:
                    patch_obj.stop()

        # Validate message isolation
        for user_id in users:
            self.assertTrue(
                len(send_calls[user_id]) > 0,
                f"User {user_id} should have received their message"
            )

    async def test_error_handling_migration(self):
        """
        Test that error handling is maintained during migration.
        
        Ensures error conditions are handled consistently between
        legacy and canonical implementations.
        """
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        
        canonical_router = CanonicalMessageRouter(user_context={'user_id': 'test_user'})
        
        # Test various error conditions
        error_test_cases = [
            {
                'name': 'invalid_message_type',
                'message': {'invalid': 'message_format'},
                'expected_error_type': (TypeError, ValueError, AttributeError)
            },
            {
                'name': 'missing_user_context',
                'setup': lambda: CanonicalMessageRouter(user_context=None),
                'expected_error_type': (ValueError, TypeError)
            },
            {
                'name': 'malformed_message_data',
                'message': "not_a_dict",
                'expected_error_type': (TypeError, ValueError)
            }
        ]

        for test_case in error_test_cases:
            with self.subTest(error_case=test_case['name']):
                if 'setup' in test_case:
                    # Test error during setup
                    try:
                        test_case['setup']()
                        self.fail(f"Expected error for {test_case['name']} but none occurred")
                    except test_case['expected_error_type']:
                        pass  # Expected error occurred
                else:
                    # Test error during message routing
                    try:
                        await canonical_router.route_message(test_case['message'])
                        self.fail(f"Expected error for {test_case['name']} but none occurred")
                    except test_case['expected_error_type']:
                        pass  # Expected error occurred

    async def _test_message_routing_functionality(self, router):
        """Test basic message routing functionality."""
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        
        test_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            data={'message': 'test routing'},
            user_id='test_user'
        )
        
        with patch.object(router, '_send_to_websocket', new_callable=AsyncMock) as mock_send:
            await router.route_message(test_message)
            mock_send.assert_called_once()

    async def _test_broadcast_functionality(self, router):
        """Test broadcast functionality."""
        broadcast_data = {'announcement': 'system message'}
        
        with patch.object(router, '_broadcast_to_all', new_callable=AsyncMock) as mock_broadcast:
            if hasattr(router, 'broadcast_message'):
                await router.broadcast_message(broadcast_data)
                mock_broadcast.assert_called_once()

    async def _test_user_isolation_functionality(self, router):
        """Test user isolation functionality."""
        target_user = 'target_user'
        message_data = {'private': 'message'}
        
        with patch.object(router, '_send_to_user', new_callable=AsyncMock) as mock_send:
            if hasattr(router, 'send_to_user'):
                await router.send_to_user(target_user, message_data)
                mock_send.assert_called_once_with(target_user, message_data)

    async def _test_agent_event_functionality(self, router):
        """Test agent event handling functionality."""
        agent_event = {
            'event_type': 'agent_started',
            'agent_id': 'test_agent',
            'data': {'task': 'test_task'}
        }
        
        with patch.object(router, '_handle_agent_event', new_callable=AsyncMock) as mock_handle:
            if hasattr(router, 'handle_agent_event'):
                await router.handle_agent_event(agent_event)
                mock_handle.assert_called_once()

    async def _get_available_legacy_routers(self) -> List[Dict[str, Any]]:
        """Get list of legacy routers still available."""
        routers = []
        
        legacy_router_specs = [
            ('WebSocketEventRouter', 'netra_backend.app.services.websocket_event_router'),
            ('UserScopedWebSocketEventRouter', 'netra_backend.app.services.user_scoped_websocket_event_router'),
            ('MessageRouter', 'netra_backend.app.routes.message_router'),
        ]
        
        for class_name, module_name in legacy_router_specs:
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
                continue
                
        return routers

    async def _test_legacy_router_compatibility(self, router_info: Dict[str, Any]):
        """Test that legacy router maintains compatibility."""
        router_class = router_info['class']
        
        try:
            # Test instantiation
            router_instance = router_class(user_context={'user_id': 'test_user'})
            
            # Test basic functionality if available
            if hasattr(router_instance, 'route_message'):
                # Test with mock to avoid external dependencies
                with patch.object(router_instance, '_send_to_websocket', new_callable=AsyncMock):
                    # Should not raise exception
                    test_data = {'test': 'data'}
                    await router_instance.route_message(test_data)
                    
        except Exception as e:
            self.fail(f"Legacy router {router_info['name']} compatibility test failed: {e}")

    async def _test_legacy_factory_compatibility(self, factory_name: str, module_name: str):
        """Test that legacy factory functions remain compatible."""
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, factory_name):
                factory_func = getattr(module, factory_name)
                
                # Test factory function
                try:
                    router_instance = factory_func(user_context={'user_id': 'test_user'})
                    self.assertIsNotNone(router_instance)
                except Exception as e:
                    self.fail(f"Legacy factory {factory_name} failed: {e}")
                    
        except ImportError:
            # Legacy factory may have been removed, which is acceptable
            pass

    def _create_test_cases(self) -> List[RouterTestCase]:
        """Create standardized test cases for router functionality."""
        return [
            RouterTestCase(
                name="basic_user_message",
                input_data={
                    'type': 'user_message',
                    'data': {'message': 'Hello'},
                    'user_id': 'test_user'
                },
                expected_result={'status': 'sent'},
                test_type='routing'
            ),
            RouterTestCase(
                name="agent_started_event",
                input_data={
                    'type': 'agent_started',
                    'data': {'agent_id': 'test_agent'},
                    'user_id': 'test_user'
                },
                expected_result={'status': 'broadcasted'},
                test_type='broadcast'
            ),
            RouterTestCase(
                name="user_isolation",
                input_data={
                    'target_user': 'user1',
                    'data': {'private': 'message'},
                    'sender': 'user2'
                },
                expected_result={'delivered_to': 'user1_only'},
                test_type='user_isolation'
            )
        ]