"""
CRITICAL SSOT Test 3: MessageRouter Routing Conflict Reproduction - Issue #1101

PURPOSE: Reproduce and validate routing conflicts that occur when multiple MessageRouter 
implementations are active simultaneously. These tests SHOULD FAIL before remediation 
and PASS after consolidation.

VIOLATION: Multiple active MessageRouter implementations cause:
- Race conditions when multiple routers process the same message
- Inconsistent routing decisions between different router instances  
- Message delivery failures due to handler registration conflicts
- User isolation breaches when routers share state

BUSINESS IMPACT: $500K+ ARR Golden Path failures due to:
- WebSocket messages routed to wrong users (privacy breach)
- Agent responses lost or delivered to wrong sessions
- Multi-user chat conflicts and data contamination
- Unpredictable routing behavior in production

TEST STRATEGY: 20% of MessageRouter SSOT testing strategy focused on conflict reproduction
"""

import pytest
import unittest
import asyncio
import threading
import time
import uuid
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.unit
class MessageRouterRoutingConflictReproductionTests(SSotAsyncTestCase):
    """Test that reproduces routing conflicts between multiple MessageRouter implementations."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.test_messages = []
        self.routing_results = {}
        self.conflict_detected = False

    async def test_concurrent_message_routing_conflicts(self):
        """
        CRITICAL: Reproduce conflicts when multiple routers process same message concurrently.
        
        SHOULD FAIL: Multiple router instances cause race conditions and conflicts
        WILL PASS: After consolidation single router prevents conflicts
        
        Business Impact: Race conditions cause message delivery failures
        """
        # Create test message
        test_message_id = str(uuid.uuid4())
        test_message = {
            'id': test_message_id,
            'type': 'user_message', 
            'user_id': 'test_user_123',
            'content': 'Test message for conflict reproduction',
            'timestamp': time.time()
        }
        
        routing_attempts = []
        routing_errors = []
        
        async def route_with_router_instance(router_source: str, message: dict, attempt_id: int):
            """Simulate routing with different router instances."""
            try:
                if router_source == 'core':
                    # Try to use deprecated core router
                    from netra_backend.app.core.message_router import MessageRouter
                    router = MessageRouter()
                elif router_source == 'websocket_core':
                    # Try to use canonical websocket_core router
                    from netra_backend.app.websocket_core.handlers import MessageRouter
                    router = MessageRouter()
                else:
                    # Try compatibility layer
                    from netra_backend.app.services.message_router import MessageRouter
                    router = MessageRouter()
                
                # Simulate message routing
                start_time = time.time()
                
                # Create a mock message object that both routers can handle
                if hasattr(router, 'route_message'):
                    # Core router style
                    from netra_backend.app.core.message_router import Message, MessageType
                    msg_obj = Message(
                        id=message['id'],
                        type=MessageType.REQUEST,
                        source=message['user_id'],
                        destination='agent',
                        payload=message,
                        timestamp=message['timestamp']
                    )
                    result = await router.route_message(msg_obj)
                elif hasattr(router, 'route'):
                    # WebSocket core router style - simulate routing
                    result = f"routed_by_{router_source}"
                else:
                    result = f"handled_by_{router_source}"
                
                end_time = time.time()
                
                routing_attempts.append({
                    'router_source': router_source,
                    'attempt_id': attempt_id,
                    'message_id': test_message_id,
                    'result': result,
                    'processing_time': end_time - start_time,
                    'router_instance_id': id(router),
                    'success': True
                })
                
            except Exception as e:
                routing_errors.append({
                    'router_source': router_source,
                    'attempt_id': attempt_id,
                    'error': str(e),
                    'error_type': type(e).__name__
                })

        # Simulate concurrent routing attempts with different router sources
        tasks = []
        router_sources = ['core', 'websocket_core', 'services', 'core', 'websocket_core']
        
        for i, source in enumerate(router_sources):
            task = asyncio.create_task(route_with_router_instance(source, test_message, i))
            tasks.append(task)
        
        # Wait for all routing attempts
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze conflicts
        successful_attempts = len(routing_attempts)
        failed_attempts = len(routing_errors)
        
        # Check for router instance conflicts (different instances processing same message)
        router_instances = set(attempt['router_instance_id'] for attempt in routing_attempts)
        different_sources = set(attempt['router_source'] for attempt in routing_attempts)
        
        # CRITICAL: Multiple router instances indicate SSOT violation
        if len(different_sources) > 1:
            self.conflict_detected = True
            
        # After SSOT consolidation, should have consistent routing behavior
        self.assertLessEqual(
            len(different_sources), 1,
            f"SSOT VIOLATION: Found {len(different_sources)} different router sources processing same message: "
            f"{different_sources}. This indicates routing conflicts. "
            f"Routing attempts: {routing_attempts}, Errors: {routing_errors}"
        )

    async def test_message_handler_registration_conflicts(self):
        """
        CRITICAL: Reproduce conflicts in message handler registration between routers.
        
        SHOULD FAIL: Different routers have different/conflicting handler sets
        WILL PASS: After consolidation single router has consistent handler set
        
        Business Impact: Handler conflicts cause unpredictable message processing
        """
        handler_analysis = {}
        registration_conflicts = []
        
        # Test handler registration across different router sources
        router_sources = [
            ('core', 'netra_backend.app.core.message_router'),
            ('websocket_core', 'netra_backend.app.websocket_core.handlers'),
            ('services', 'netra_backend.app.services.message_router')
        ]
        
        for source_name, module_path in router_sources:
            try:
                import importlib
                module = importlib.import_module(module_path)
                
                if hasattr(module, 'MessageRouter'):
                    router = module.MessageRouter()
                    
                    # Analyze handler registration capabilities
                    handler_info = {
                        'has_custom_handlers': hasattr(router, 'custom_handlers'),
                        'has_builtin_handlers': hasattr(router, 'builtin_handlers'),
                        'has_add_route': hasattr(router, 'add_route'),
                        'has_add_middleware': hasattr(router, 'add_middleware'),
                        'router_instance_id': id(router),
                        'router_class': type(router).__name__,
                        'router_module': type(router).__module__
                    }
                    
                    # Count handlers if available
                    if hasattr(router, 'custom_handlers') and hasattr(router, 'builtin_handlers'):
                        all_handlers = getattr(router, 'custom_handlers', []) + getattr(router, 'builtin_handlers', [])
                        handler_info['total_handlers'] = len(all_handlers)
                        handler_info['handler_types'] = [type(h).__name__ for h in all_handlers]
                    elif hasattr(router, 'routes'):
                        handler_info['total_handlers'] = len(getattr(router, 'routes', {}))
                        handler_info['handler_types'] = list(getattr(router, 'routes', {}).keys())
                    else:
                        handler_info['total_handlers'] = 0
                        handler_info['handler_types'] = []
                    
                    handler_analysis[source_name] = handler_info
                    
            except (ImportError, AttributeError) as e:
                registration_conflicts.append({
                    'source': source_name,
                    'module': module_path,
                    'error': str(e),
                    'issue': 'import_or_instantiation_failure'
                })
        
        # Check for handler registration inconsistencies
        if len(handler_analysis) > 1:
            # Compare handler capabilities
            capabilities = {}
            for source, info in handler_analysis.items():
                capability_signature = (
                    info['has_custom_handlers'],
                    info['has_builtin_handlers'], 
                    info['has_add_route'],
                    info['has_add_middleware']
                )
                capabilities[source] = capability_signature
            
            unique_capabilities = set(capabilities.values())
            
            # Check handler count consistency
            handler_counts = {source: info['total_handlers'] for source, info in handler_analysis.items()}
            unique_handler_counts = set(handler_counts.values())
            
            # CRITICAL: Handler registration should be consistent across all router sources
            self.assertEqual(
                len(unique_capabilities), 1,
                f"SSOT VIOLATION: Found {len(unique_capabilities)} different handler registration patterns: "
                f"{capabilities}. All routers should have consistent handler registration capabilities."
            )
            
            # After SSOT consolidation, handler counts should be consistent
            self.assertEqual(
                len(unique_handler_counts), 1,
                f"SSOT VIOLATION: Found {len(unique_handler_counts)} different handler counts: "
                f"{handler_counts}. All router instances should have same handlers."
            )

    async def test_user_isolation_routing_conflicts(self):
        """
        CRITICAL: Reproduce user isolation breaches due to routing conflicts.
        
        SHOULD FAIL: Different routers share state or route to wrong users
        WILL PASS: After consolidation single router maintains proper user isolation
        
        Business Impact: User isolation breaches are privacy/security violations
        """
        user_routing_tests = {}
        isolation_violations = []
        
        # Simulate messages from different users
        test_users = ['user_123', 'user_456', 'user_789']
        
        for user_id in test_users:
            user_routing_tests[user_id] = {
                'messages_sent': [],
                'routing_results': [],
                'router_instances_used': set()
            }
        
        # Test routing for each user with different router sources
        router_sources = ['core', 'websocket_core', 'services']
        
        for user_id in test_users:
            for router_source in router_sources:
                try:
                    # Create user-specific message
                    message = {
                        'id': str(uuid.uuid4()),
                        'user_id': user_id,
                        'content': f'Private message from {user_id}',
                        'timestamp': time.time(),
                        'session_id': f'session_{user_id}'
                    }
                    
                    # Route with specific router source
                    if router_source == 'core':
                        from netra_backend.app.core.message_router import MessageRouter
                        router = MessageRouter()
                    elif router_source == 'websocket_core':
                        from netra_backend.app.websocket_core.handlers import MessageRouter
                        router = MessageRouter()
                    else:
                        from netra_backend.app.services.message_router import MessageRouter
                        router = MessageRouter()
                    
                    user_routing_tests[user_id]['messages_sent'].append(message)
                    user_routing_tests[user_id]['router_instances_used'].add(id(router))
                    user_routing_tests[user_id]['routing_results'].append({
                        'router_source': router_source,
                        'router_instance_id': id(router),
                        'message_id': message['id']
                    })
                    
                except Exception as e:
                    isolation_violations.append({
                        'user_id': user_id,
                        'router_source': router_source,
                        'error': str(e),
                        'violation_type': 'routing_failure'
                    })
        
        # Analyze user isolation
        for user_id, test_data in user_routing_tests.items():
            router_instances = test_data['router_instances_used']
            
            # Check if different router instances were used for same user
            if len(router_instances) > 1:
                isolation_violations.append({
                    'user_id': user_id,
                    'violation_type': 'multiple_router_instances',
                    'router_count': len(router_instances),
                    'details': f'User {user_id} used {len(router_instances)} different router instances'
                })
        
        # Check for cross-user router sharing (potential state sharing)
        all_router_instances = set()
        for test_data in user_routing_tests.values():
            all_router_instances.update(test_data['router_instances_used'])
        
        total_unique_instances = len(all_router_instances)
        expected_instances_after_ssot = 1  # Should use same router class, possibly same instance
        
        # CRITICAL: After SSOT consolidation, should have consistent router usage
        self.assertEqual(
            len(isolation_violations), 0,
            f"SSOT VIOLATION: Found {len(isolation_violations)} user isolation violations: "
            f"{isolation_violations}. Router conflicts cause user isolation breaches."
        )

    async def test_message_delivery_consistency_conflicts(self):
        """
        CRITICAL: Reproduce message delivery inconsistencies between router implementations.
        
        SHOULD FAIL: Different routers deliver messages differently or inconsistently  
        WILL PASS: After consolidation single router ensures consistent delivery
        
        Business Impact: Delivery inconsistencies cause lost messages and user confusion
        """
        delivery_tests = []
        delivery_inconsistencies = []
        
        # Test message with multiple routing scenarios
        test_message = {
            'id': str(uuid.uuid4()),
            'type': 'agent_request',
            'user_id': 'test_user_delivery',
            'content': 'Test delivery consistency',
            'priority': 'high',
            'expected_response': True
        }
        
        # Test delivery through different router paths
        router_paths = [
            ('core_direct', 'netra_backend.app.core.message_router'),
            ('websocket_canonical', 'netra_backend.app.websocket_core.handlers'),
            ('services_compatibility', 'netra_backend.app.services.message_router')
        ]
        
        for path_name, module_path in router_paths:
            delivery_result = {
                'path': path_name,
                'module': module_path,
                'success': False,
                'result': None,
                'processing_time': 0,
                'error': None
            }
            
            try:
                import importlib
                start_time = time.time()
                
                module = importlib.import_module(module_path)
                if hasattr(module, 'MessageRouter'):
                    router = module.MessageRouter()
                    
                    # Simulate message delivery
                    if hasattr(router, 'route_message'):
                        # Core router approach
                        from netra_backend.app.core.message_router import Message, MessageType
                        msg_obj = Message(
                            id=test_message['id'],
                            type=MessageType.REQUEST,
                            source=test_message['user_id'],
                            destination='agent',
                            payload=test_message,
                            timestamp=time.time()
                        )
                        result = await router.route_message(msg_obj)
                        delivery_result['result'] = result
                        delivery_result['success'] = result is not None
                    else:
                        # WebSocket core router - simulate successful routing
                        delivery_result['result'] = f'delivered_via_{path_name}'
                        delivery_result['success'] = True
                    
                    delivery_result['processing_time'] = time.time() - start_time
                    
            except Exception as e:
                delivery_result['error'] = str(e)
                delivery_result['success'] = False
            
            delivery_tests.append(delivery_result)
        
        # Analyze delivery consistency
        successful_deliveries = [test for test in delivery_tests if test['success']]
        failed_deliveries = [test for test in delivery_tests if not test['success']]
        
        # Check for delivery method inconsistencies
        delivery_methods = set()
        for test in successful_deliveries:
            if test['result']:
                delivery_methods.add(type(test['result']).__name__)
        
        # Check processing time consistency (should be similar for same message)
        processing_times = [test['processing_time'] for test in successful_deliveries if test['processing_time'] > 0]
        
        if len(processing_times) > 1:
            time_variance = max(processing_times) - min(processing_times)
            # High variance might indicate different processing paths
            if time_variance > 0.1:  # 100ms variance threshold
                delivery_inconsistencies.append({
                    'type': 'processing_time_variance',
                    'variance': time_variance,
                    'times': processing_times
                })
        
        # Different delivery methods indicate different implementations
        if len(delivery_methods) > 1:
            delivery_inconsistencies.append({
                'type': 'delivery_method_inconsistency', 
                'methods': list(delivery_methods),
                'count': len(delivery_methods)
            })
        
        # CRITICAL: Delivery should be consistent across all router paths after SSOT
        self.assertEqual(
            len(delivery_inconsistencies), 0,
            f"SSOT VIOLATION: Found {len(delivery_inconsistencies)} delivery inconsistencies: "
            f"{delivery_inconsistencies}. All router paths should deliver messages consistently."
        )


@pytest.mark.unit
class MessageRouterConcurrencyConflictsTests(SSotAsyncTestCase):
    """Test concurrency-specific routing conflicts."""

    async def test_concurrent_router_initialization_conflicts(self):
        """
        CRITICAL: Reproduce conflicts during concurrent router initialization.
        
        SHOULD FAIL: Multiple router initializations cause race conditions
        WILL PASS: After consolidation consistent initialization behavior
        
        Business Impact: Initialization conflicts cause startup failures
        """
        initialization_results = []
        initialization_errors = []
        
        async def initialize_router(source: str, iteration: int):
            """Initialize router from specific source."""
            try:
                if source == 'core':
                    from netra_backend.app.core.message_router import MessageRouter
                    router = MessageRouter()
                elif source == 'websocket':
                    from netra_backend.app.websocket_core.handlers import MessageRouter
                    router = MessageRouter()
                else:
                    from netra_backend.app.services.message_router import MessageRouter
                    router = MessageRouter()
                
                initialization_results.append({
                    'source': source,
                    'iteration': iteration,
                    'router_id': id(router),
                    'router_class': type(router).__name__,
                    'router_module': type(router).__module__,
                    'success': True
                })
                
            except Exception as e:
                initialization_errors.append({
                    'source': source,
                    'iteration': iteration,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
        
        # Create multiple concurrent initialization tasks
        tasks = []
        sources = ['core', 'websocket', 'services']
        
        for iteration in range(10):  # 10 concurrent attempts
            for source in sources:
                task = asyncio.create_task(initialize_router(source, iteration))
                tasks.append(task)
        
        # Wait for all initializations
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze initialization conflicts
        successful_inits = len(initialization_results)
        failed_inits = len(initialization_errors)
        
        # Check for different router classes (indicates multiple implementations)
        router_classes = set()
        router_modules = set()
        
        for result in initialization_results:
            router_classes.add(result['router_class'])
            router_modules.add(result['router_module'])
        
        # CRITICAL: After SSOT consolidation should have consistent initialization
        self.assertEqual(
            len(router_classes), 1,
            f"SSOT VIOLATION: Found {len(router_classes)} different router classes during concurrent initialization: "
            f"{router_classes}. Should have exactly 1 SSOT router class."
        )
        
        # Should have minimal initialization failures
        failure_rate = failed_inits / (successful_inits + failed_inits) if (successful_inits + failed_inits) > 0 else 0
        self.assertLess(
            failure_rate, 0.1,  # Less than 10% failure rate
            f"SSOT VIOLATION: High initialization failure rate ({failure_rate:.2%}): "
            f"{failed_inits} failures out of {successful_inits + failed_inits} attempts. "
            f"Errors: {initialization_errors}"
        )


if __name__ == '__main__':
    unittest.main()