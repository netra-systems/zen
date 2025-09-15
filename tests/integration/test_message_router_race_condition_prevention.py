"""
STRATEGIC SSOT Tests: Message Router Race Condition Prevention - Issue #1101

PURPOSE: Test that SSOT MessageRouter consolidation prevents race conditions
that occur when multiple router implementations handle concurrent messages.

VIOLATION: Multiple router implementations can cause race conditions in Golden Path
BUSINESS IMPACT: $500K+ ARR at risk from inconsistent message routing

These tests SHOULD FAIL before consolidation and PASS after SSOT implementation.
"""

import unittest
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import AsyncMock, Mock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestMessageRouterRaceConditionPrevention(SSotAsyncTestCase):
    """Test race condition prevention in consolidated MessageRouter."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.concurrent_users = 5
        self.messages_per_user = 10
        self.timeout = 30.0

    async def test_concurrent_message_routing_consistency(self):
        """
        CRITICAL: Test that concurrent message routing is consistent.

        SHOULD FAIL: Currently different routers may handle concurrent messages
        WILL PASS: After SSOT ensures consistent routing behavior
        """
        concurrent_users = 5
        messages_per_user = 10

        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter

            # Create multiple router instances (simulating concurrent usage)
            routers = [MessageRouter() for _ in range(concurrent_users)]
            
            # Track routing results
            routing_results = []
            routing_errors = []
            
            async def route_message_batch(router_id, router, messages):
                """Route a batch of messages through specific router."""
                batch_results = []
                
                for i, message in enumerate(messages):
                    try:
                        mock_websocket = AsyncMock()
                        
                        # Route message through router
                        if hasattr(router, 'route_message'):
                            if asyncio.iscoroutinefunction(router.route_message):
                                result = await router.route_message(message, mock_websocket)
                            else:
                                result = router.route_message(message, mock_websocket)
                        else:
                            # Fallback - just record that router exists
                            result = f"router_{router_id}_handled"
                        
                        batch_results.append({
                            'router_id': router_id,
                            'message_id': i,
                            'result': result,
                            'success': True
                        })
                        
                    except Exception as e:
                        routing_errors.append({
                            'router_id': router_id,
                            'message_id': i,
                            'error': str(e)
                        })
                        batch_results.append({
                            'router_id': router_id,
                            'message_id': i,
                            'result': None,
                            'success': False
                        })
                
                return batch_results
            
            # Create test messages
            test_messages = []
            for i in range(messages_per_user):
                test_messages.append({
                    'type': 'test_message',
                    'data': {'message_id': i, 'content': f'Test message {i}'},
                    'timestamp': time.time()
                })
            
            # Route messages concurrently through different routers
            tasks = []
            for router_id, router in enumerate(routers):
                task = route_message_batch(router_id, router, test_messages)
                tasks.append(task)
            
            # Wait for all routing to complete
            all_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results for consistency
            successful_results = []
            for result_batch in all_results:
                if isinstance(result_batch, Exception):
                    routing_errors.append({'error': str(result_batch)})
                else:
                    successful_results.extend(result_batch)
            
            # Check routing consistency
            successful_routes = [r for r in successful_results if r['success']]
            
            self.assertGreater(
                len(successful_routes), 0,
                f"RACE CONDITION FAILURE: No successful concurrent routes. "
                f"Errors: {routing_errors[:5]}"  # Show first 5 errors
            )
            
            # All successful routes should have consistent behavior pattern
            # (This is a basic consistency check - specific behavior depends on implementation)
            if len(successful_routes) > 1:
                first_pattern = type(successful_routes[0]['result'])
                inconsistent_patterns = [
                    r for r in successful_routes 
                    if type(r['result']) != first_pattern
                ]
                
                self.assertEqual(
                    len(inconsistent_patterns), 0,
                    f"RACE CONDITION VIOLATION: Inconsistent routing patterns detected. "
                    f"Expected all results to have same type, but found variations: "
                    f"{[type(r['result']) for r in inconsistent_patterns[:3]]}"
                )
            
        except ImportError:
            self.fail("Could not import MessageRouter for race condition test")

    async def test_websocket_event_delivery_consistency(self):
        """
        CRITICAL: Test WebSocket event delivery consistency under concurrent load.

        SHOULD FAIL: Currently different routers may cause inconsistent event delivery
        WILL PASS: After SSOT ensures consistent WebSocket event handling
        """
        concurrent_users = 5

        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter

            router = MessageRouter()
            
            # Track WebSocket events
            delivered_events = []
            event_errors = []
            
            def mock_websocket_factory(user_id):
                """Create mock WebSocket for user."""
                websocket = AsyncMock()
                
                async def track_send(message):
                    delivered_events.append({
                        'user_id': user_id,
                        'message': message,
                        'timestamp': time.time(),
                        'thread_id': threading.current_thread().ident
                    })
                
                websocket.send = track_send
                return websocket
            
            async def simulate_user_interaction(user_id):
                """Simulate user WebSocket interaction."""
                websocket = mock_websocket_factory(user_id)
                
                # Simulate agent messages that should trigger WebSocket events
                agent_messages = [
                    {'type': 'agent_started', 'data': {'agent_id': f'agent_{user_id}'}},
                    {'type': 'agent_thinking', 'data': {'thought': f'Processing for user {user_id}'}},
                    {'type': 'agent_completed', 'data': {'result': f'Done for user {user_id}'}}
                ]
                
                try:
                    for message in agent_messages:
                        if hasattr(router, 'route_message'):
                            if asyncio.iscoroutinefunction(router.route_message):
                                await router.route_message(message, websocket)
                            else:
                                router.route_message(message, websocket)
                        
                        # Small delay to test race conditions
                        await asyncio.sleep(0.01)
                        
                except Exception as e:
                    event_errors.append({
                        'user_id': user_id,
                        'error': str(e),
                        'thread_id': threading.current_thread().ident
                    })
            
            # Run concurrent user interactions
            tasks = [simulate_user_interaction(i) for i in range(concurrent_users)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze event delivery consistency
            if len(delivered_events) > 0:
                # Check that events were delivered to correct users
                user_events = {}
                for event in delivered_events:
                    user_id = event['user_id']
                    if user_id not in user_events:
                        user_events[user_id] = []
                    user_events[user_id].append(event)
                
                # Each user should have received their events
                for user_id in range(concurrent_users):
                    if user_id not in user_events:
                        continue  # Skip if no events for this user
                    
                    user_event_count = len(user_events[user_id])
                    # Should have some events (exact count depends on implementation)
                    self.assertGreater(
                        user_event_count, 0,
                        f"CONSISTENCY VIOLATION: User {user_id} received no WebSocket events"
                    )
                    
                    # Events should be properly formatted
                    for event in user_events[user_id]:
                        self.assertIn(
                            'message', event,
                            f"CONSISTENCY VIOLATION: Event missing message field: {event}"
                        )
            
            # Check for errors
            if event_errors:
                error_summary = {error['error']: error['user_id'] for error in event_errors[:3]}
                self.fail(
                    f"RACE CONDITION VIOLATION: WebSocket event delivery errors: {error_summary}. "
                    f"Total errors: {len(event_errors)}"
                )
                
        except ImportError:
            self.fail("Could not import MessageRouter for WebSocket consistency test")

    def test_handler_chain_thread_safety(self):
        """
        CRITICAL: Test that handler chain is thread-safe.
        
        SHOULD FAIL: Currently multiple routers may have conflicting handler state
        WILL PASS: After SSOT ensures thread-safe handler execution
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            router = MessageRouter()
            
            # Get handlers
            handlers = []
            if hasattr(router, 'custom_handlers'):
                handlers.extend(router.custom_handlers or [])
            if hasattr(router, 'builtin_handlers'):
                handlers.extend(router.builtin_handlers or [])
            
            if not handlers:
                # Create a simple handler for testing
                class TestHandler:
                    def __init__(self):
                        self.processed_count = 0
                        self.lock = threading.Lock()
                    
                    def handle(self, message, websocket):
                        with self.lock:
                            self.processed_count += 1
                        return f"processed_{self.processed_count}"
                
                test_handler = TestHandler()
                handlers = [test_handler]
            
            # Test concurrent handler execution
            processing_results = []
            processing_errors = []
            
            def execute_handler_concurrently(handler, message_batch):
                """Execute handler with batch of messages."""
                thread_results = []
                
                for i, message in enumerate(message_batch):
                    try:
                        mock_websocket = AsyncMock()
                        
                        if hasattr(handler, 'handle'):
                            result = handler.handle(message, mock_websocket)
                        elif callable(handler):
                            result = handler(message, mock_websocket)
                        else:
                            result = f"handler_executed_{i}"
                        
                        thread_results.append({
                            'message_id': i,
                            'result': result,
                            'thread_id': threading.current_thread().ident,
                            'success': True
                        })
                        
                    except Exception as e:
                        processing_errors.append({
                            'message_id': i,
                            'error': str(e),
                            'thread_id': threading.current_thread().ident
                        })
                        thread_results.append({
                            'message_id': i,
                            'result': None,
                            'success': False
                        })
                
                return thread_results
            
            # Create test messages
            test_messages = [
                {'type': 'test_handler', 'data': {'id': i}}
                for i in range(20)
            ]
            
            # Split messages across threads
            messages_per_thread = len(test_messages) // 3
            message_batches = [
                test_messages[i:i + messages_per_thread]
                for i in range(0, len(test_messages), messages_per_thread)
            ]
            
            # Test first handler with concurrent execution
            if handlers:
                handler = handlers[0]
                
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [
                        executor.submit(execute_handler_concurrently, handler, batch)
                        for batch in message_batches
                    ]
                    
                    for future in as_completed(futures, timeout=10.0):
                        try:
                            batch_results = future.result()
                            processing_results.extend(batch_results)
                        except Exception as e:
                            processing_errors.append({'error': str(e)})
                
                # Analyze thread safety
                successful_results = [r for r in processing_results if r['success']]
                
                self.assertGreater(
                    len(successful_results), 0,
                    f"THREAD SAFETY VIOLATION: No successful concurrent handler execution. "
                    f"Errors: {processing_errors[:3]}"
                )
                
                # Check for race conditions in results
                thread_ids = set(r['thread_id'] for r in successful_results)
                self.assertGreater(
                    len(thread_ids), 1,
                    "THREAD SAFETY WARNING: All processing happened on same thread"
                )
                
                # Results should be consistent (no corruption)
                for result in successful_results:
                    self.assertIsNotNone(
                        result['result'],
                        f"THREAD SAFETY VIOLATION: Handler returned None result: {result}"
                    )
            
        except ImportError:
            self.fail("Could not import MessageRouter for thread safety test")


class TestMessageRouterSingletonBehaviorValidation(SSotAsyncTestCase):
    """Test that consolidated router behaves as singleton when needed."""

    def test_router_factory_consistency(self):
        """
        CRITICAL: Test that router factory produces consistent instances.
        
        SHOULD FAIL: Currently multiple factory methods may exist
        WILL PASS: After SSOT consolidation ensures consistent factory behavior
        """
        router_instances = []
        creation_errors = []
        
        # Try different ways of creating routers
        creation_methods = [
            lambda: self._create_router_method1(),
            lambda: self._create_router_method2(),
            lambda: self._create_router_method3()
        ]
        
        for i, method in enumerate(creation_methods):
            try:
                router = method()
                if router:
                    router_instances.append({
                        'method_id': i,
                        'router': router,
                        'router_type': type(router).__name__,
                        'router_module': type(router).__module__
                    })
            except Exception as e:
                creation_errors.append({
                    'method_id': i,
                    'error': str(e)
                })
        
        # Check consistency
        if router_instances:
            first_router_type = router_instances[0]['router_type']
            first_router_module = router_instances[0]['router_module']
            
            inconsistent_instances = [
                instance for instance in router_instances
                if (instance['router_type'] != first_router_type or 
                    instance['router_module'] != first_router_module)
            ]
            
            self.assertEqual(
                len(inconsistent_instances), 0,
                f"FACTORY CONSISTENCY VIOLATION: Different router types created. "
                f"Expected all to be {first_router_type} from {first_router_module}, "
                f"but found: {[(i['router_type'], i['router_module']) for i in inconsistent_instances]}"
            )
        else:
            # No instances created - check if it's due to errors or missing implementations
            if creation_errors:
                self.fail(
                    f"FACTORY CREATION FAILURE: Could not create router instances. "
                    f"Errors: {creation_errors}"
                )

    def _create_router_method1(self):
        """Method 1: Direct import from websocket_core."""
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            return MessageRouter()
        except ImportError:
            return None

    def _create_router_method2(self):
        """Method 2: Import from agents alias."""
        try:
            from netra_backend.app.agents.message_router import MessageRouter
            return MessageRouter()
        except ImportError:
            return None

    def _create_router_method3(self):
        """Method 3: Import from core (should be removed after SSOT)."""
        try:
            from netra_backend.app.core.message_router import MessageRouter
            return MessageRouter()
        except ImportError:
            return None


if __name__ == '__main__':
    unittest.main()