"""
Test AgentRegistry Multi-User Isolation Failures (Issue #914)

This test module demonstrates critical multi-user isolation failures between
the two AgentRegistry implementations that cause user context contamination
and memory leaks in concurrent scenarios.

Business Value: Protects $500K+ ARR by identifying isolation violations that
cause users to see other users' agent responses, WebSocket events delivered
to wrong users, and memory leaks from shared state accumulation.

Test Category: Unit (no Docker required) 
Purpose: Failing tests to demonstrate multi-user contamination problems
"""

import asyncio
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Set
from unittest.mock import Mock, AsyncMock, MagicMock
import pytest
import gc
import weakref

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestAgentRegistryMultiUserIsolationFailures(SSotAsyncTestCase):
    """
    Test multi-user isolation failures in AgentRegistry implementations.
    
    These tests are DESIGNED TO FAIL initially to demonstrate how registry
    implementations allow user context contamination and create memory leaks
    in multi-user scenarios, blocking safe Golden Path operation.
    """

    def setup_method(self, method):
        """Setup test environment for isolation testing."""
        self.basic_registry_module = "netra_backend.app.agents.registry"
        self.advanced_registry_module = "netra_backend.app.agents.supervisor.agent_registry"
        
        # Create test user contexts for isolation testing
        self.test_users = [
            {'user_id': f'user_{i}', 'session_id': f'session_{uuid.uuid4()}', 'tenant_id': f'tenant_{i}'}
            for i in range(5)  # 5 concurrent users
        ]
        
        # Track memory references for leak detection
        self.memory_refs = []

    def test_shared_global_instance_contamination(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate user context contamination via shared instances.
        
        This test shows how global registry instances allow one user's context
        to contaminate another user's session, causing privacy violations.
        """
        import importlib
        
        contamination_detected = []
        
        try:
            # Import both registry modules
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            
            # Check for global instances that could be shared
            global_instances = {}
            
            if hasattr(basic_module, 'agent_registry'):
                global_instances['basic'] = getattr(basic_module, 'agent_registry')
                logger.info("Found global agent_registry instance in basic module")
            
            if hasattr(advanced_module, 'agent_registry'):
                global_instances['advanced'] = getattr(advanced_module, 'agent_registry')
                logger.info("Found global agent_registry instance in advanced module")
            
            # Test contamination with global instances
            for registry_name, global_instance in global_instances.items():
                # Simulate user 1 setting context
                user1_context = self.test_users[0]
                user1_websocket = Mock()
                user1_websocket.user_id = user1_context['user_id']
                
                # Try to set user-specific state
                if hasattr(global_instance, 'set_websocket_manager'):
                    try:
                        method = getattr(global_instance, 'set_websocket_manager')
                        if asyncio.iscoroutinefunction(method):
                            # Advanced registry might need user context
                            try:
                                asyncio.get_event_loop().run_until_complete(
                                    method(user1_websocket, Mock(user_id=user1_context['user_id']))
                                )
                            except:
                                asyncio.get_event_loop().run_until_complete(method(user1_websocket))
                        else:
                            method(user1_websocket)
                            
                        logger.info(f"User 1 WebSocket set on {registry_name} global instance")
                        
                    except Exception as e:
                        logger.warning(f"Could not set WebSocket for user 1 on {registry_name}: {e}")
                        continue
                
                # Simulate user 2 setting context (should not contaminate user 1)
                user2_context = self.test_users[1]
                user2_websocket = Mock()
                user2_websocket.user_id = user2_context['user_id']
                
                if hasattr(global_instance, 'set_websocket_manager'):
                    try:
                        method = getattr(global_instance, 'set_websocket_manager')
                        if asyncio.iscoroutinefunction(method):
                            try:
                                asyncio.get_event_loop().run_until_complete(
                                    method(user2_websocket, Mock(user_id=user2_context['user_id']))
                                )
                            except:
                                asyncio.get_event_loop().run_until_complete(method(user2_websocket))
                        else:
                            method(user2_websocket)
                            
                        logger.info(f"User 2 WebSocket set on {registry_name} global instance")
                        
                    except Exception as e:
                        logger.warning(f"Could not set WebSocket for user 2 on {registry_name}: {e}")
                        continue
                
                # Check if user 1's context is still intact (should not be contaminated)
                if hasattr(global_instance, '_websocket_manager') or hasattr(global_instance, 'websocket_manager'):
                    # Get the current websocket manager
                    current_websocket = None
                    if hasattr(global_instance, '_websocket_manager'):
                        current_websocket = global_instance._websocket_manager
                    elif hasattr(global_instance, 'websocket_manager'):
                        current_websocket = global_instance.websocket_manager
                    
                    if current_websocket:
                        current_user_id = getattr(current_websocket, 'user_id', None)
                        
                        # CONTAMINATION DETECTED: Global instance shows user 2's context
                        # when user 1 should still be active (or properly isolated)
                        if current_user_id == user2_context['user_id']:
                            contamination_detected.append({
                                'registry': registry_name,
                                'contamination_type': 'websocket_override',
                                'original_user': user1_context['user_id'],
                                'contaminating_user': user2_context['user_id'],
                                'detail': 'User 2 overwrote User 1 WebSocket in global instance'
                            })
            
            # FAILURE CONDITION: Global instances allow user context contamination
            if contamination_detected:
                contamination_summary = "; ".join([
                    f"{c['registry']}: {c['detail']}" for c in contamination_detected
                ])
                
                self.fail(
                    f"CRITICAL USER PRIVACY VIOLATION: {len(contamination_detected)} contamination scenarios detected. "
                    f"Global registry instances allow user contexts to contaminate each other, causing users to "
                    f"potentially see other users' agent responses and WebSocket events. This violates data privacy "
                    f"and blocks safe multi-user Golden Path operation. Contaminations: {contamination_summary}"
                )
            
        except Exception as e:
            logger.error(f"Unexpected error during contamination testing: {e}")
            # If we can't test contamination due to other issues, that's also a problem
            self.fail(f"CONTAMINATION TEST FAILURE: Unable to test user isolation due to: {e}")
            
        # If no contamination detected, that's the goal state
        logger.info("No user context contamination detected - proper isolation maintained")

    def test_concurrent_user_memory_leak_accumulation(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate memory leaks from shared registry state.
        
        This test shows how registries accumulate user state without proper cleanup,
        causing memory leaks in long-running multi-user scenarios.
        """
        import importlib
        import gc
        
        initial_memory_refs = len(gc.get_objects())
        memory_growth = []
        
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            
            # Test both registry types for memory leaks
            for registry_name, registry_class in [('basic', basic_registry_class), ('advanced', advanced_registry_class)]:
                initial_objects = len(gc.get_objects())
                user_instances = []
                
                # Simulate 20 users creating registry instances with contexts
                for i in range(20):
                    try:
                        registry_instance = registry_class()
                        user_context = self.test_users[i % len(self.test_users)]
                        
                        # Set up WebSocket for this user
                        user_websocket = Mock()
                        user_websocket.user_id = user_context['user_id']
                        user_websocket.session_id = user_context['session_id']
                        
                        if hasattr(registry_instance, 'set_websocket_manager'):
                            method = getattr(registry_instance, 'set_websocket_manager')
                            try:
                                if asyncio.iscoroutinefunction(method):
                                    asyncio.get_event_loop().run_until_complete(
                                        method(user_websocket, Mock(user_id=user_context['user_id']))
                                    )
                                else:
                                    method(user_websocket)
                            except:
                                # Try without user context parameter
                                if asyncio.iscoroutinefunction(method):
                                    asyncio.get_event_loop().run_until_complete(method(user_websocket))
                                else:
                                    method(user_websocket)
                        
                        # Store weak reference to detect proper cleanup
                        weak_ref = weakref.ref(registry_instance)
                        user_instances.append({
                            'instance': registry_instance,
                            'weak_ref': weak_ref,
                            'user_id': user_context['user_id']
                        })
                        
                    except Exception as e:
                        logger.warning(f"Could not create registry instance {i} for {registry_name}: {e}")
                
                # Simulate users disconnecting (should trigger cleanup)
                for user_data in user_instances:
                    del user_data['instance']  # Remove strong reference
                
                # Force garbage collection
                gc.collect()
                time.sleep(0.1)  # Allow time for async cleanup
                gc.collect()
                
                # Check if objects were properly cleaned up
                final_objects = len(gc.get_objects())
                object_growth = final_objects - initial_objects
                
                # Count how many registry instances are still alive (memory leak indicator)
                alive_instances = sum(1 for user_data in user_instances if user_data['weak_ref']() is not None)
                
                memory_growth.append({
                    'registry': registry_name,
                    'initial_objects': initial_objects,
                    'final_objects': final_objects,
                    'object_growth': object_growth,
                    'users_created': len(user_instances),
                    'instances_still_alive': alive_instances,
                    'leak_percentage': (alive_instances / len(user_instances) * 100) if user_instances else 0
                })
                
                logger.error(f"{registry_name} registry memory analysis:")
                logger.error(f"  Objects before: {initial_objects}")
                logger.error(f"  Objects after: {final_objects}")
                logger.error(f"  Growth: {object_growth}")
                logger.error(f"  Users created: {len(user_instances)}")
                logger.error(f"  Instances still alive: {alive_instances}")
                logger.error(f"  Leak percentage: {memory_growth[-1]['leak_percentage']:.1f}%")
            
            # FAILURE CONDITION: Significant memory growth or alive instances indicate leaks
            memory_leaks_detected = []
            for growth_data in memory_growth:
                # Consider it a leak if more than 10% of instances are still alive
                # or if there's significant object growth
                if (growth_data['leak_percentage'] > 10.0 or 
                    growth_data['object_growth'] > growth_data['users_created'] * 5):  # Conservative threshold
                    memory_leaks_detected.append(growth_data)
            
            if memory_leaks_detected:
                leak_summary = "; ".join([
                    f"{leak['registry']}: {leak['instances_still_alive']}/{leak['users_created']} instances alive ({leak['leak_percentage']:.1f}%), {leak['object_growth']} objects growth"
                    for leak in memory_leaks_detected
                ])
                
                self.fail(
                    f"CRITICAL MEMORY LEAK: {len(memory_leaks_detected)} registry types show memory leaks. "
                    f"Registry instances are not being properly cleaned up when users disconnect, "
                    f"causing memory accumulation that will crash the system under load. This blocks "
                    f"production Golden Path deployment with multiple users. Memory leaks: {leak_summary}"
                )
            
        except Exception as e:
            self.fail(f"Unexpected error during memory leak testing: {e}")
            
        # If no significant memory growth, that's the goal state
        logger.info("No significant memory leaks detected - proper cleanup implemented")

    def test_concurrent_websocket_event_delivery_contamination(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate WebSocket event delivery to wrong users.
        
        This test shows how registry implementations can deliver WebSocket events
        to the wrong user sessions, causing privacy violations and confusing UX.
        """
        import importlib
        from concurrent.futures import ThreadPoolExecutor
        
        event_delivery_failures = []
        
        def simulate_user_agent_execution(registry_class, user_context, event_collector):
            """Simulate a user triggering agent execution with WebSocket events."""
            try:
                # Create registry instance for this user
                registry_instance = registry_class()
                
                # Create mock WebSocket for this user
                user_websocket = Mock()
                user_websocket.user_id = user_context['user_id']
                user_websocket.session_id = user_context['session_id']
                
                # Mock WebSocket send method to collect events
                sent_events = []
                def mock_send(event_data):
                    sent_events.append({
                        'user_id': user_context['user_id'],
                        'session_id': user_context['session_id'],
                        'event': event_data,
                        'timestamp': time.time()
                    })
                
                user_websocket.send = mock_send
                user_websocket.send_json = mock_send
                
                # Set up WebSocket on registry
                if hasattr(registry_instance, 'set_websocket_manager'):
                    method = getattr(registry_instance, 'set_websocket_manager')
                    try:
                        if asyncio.iscoroutinefunction(method):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(
                                method(user_websocket, Mock(user_id=user_context['user_id']))
                            )
                        else:
                            method(user_websocket)
                    except:
                        # Try without user context
                        if asyncio.iscoroutinefunction(method):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(method(user_websocket))
                        else:
                            method(user_websocket)
                
                # Simulate agent events
                if hasattr(registry_instance, '_notify_agent_event'):
                    # Send events that should only go to this user
                    test_events = [
                        {'type': 'agent_started', 'user_id': user_context['user_id']},
                        {'type': 'agent_thinking', 'user_id': user_context['user_id']},
                        {'type': 'agent_completed', 'result': f"Result for {user_context['user_id']}"}
                    ]
                    
                    for event in test_events:
                        registry_instance._notify_agent_event(event)
                
                # Collect events sent for this user
                event_collector.extend(sent_events)
                
                return {
                    'user_id': user_context['user_id'],
                    'events_sent': len(sent_events),
                    'success': True
                }
                
            except Exception as e:
                return {
                    'user_id': user_context['user_id'],
                    'events_sent': 0,
                    'success': False,
                    'error': str(e)
                }
        
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            
            # Test both registry types for event contamination
            for registry_name, registry_class in [('basic', basic_registry_class), ('advanced', advanced_registry_class)]:
                event_collector = []  # Shared collector to detect cross-contamination
                
                # Run concurrent user sessions
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = []
                    for user_context in self.test_users:
                        future = executor.submit(
                            simulate_user_agent_execution,
                            registry_class,
                            user_context,
                            event_collector
                        )
                        futures.append(future)
                    
                    # Wait for all users to complete
                    results = []
                    for future in as_completed(futures, timeout=30):
                        try:
                            result = future.result()
                            results.append(result)
                        except Exception as e:
                            results.append({'success': False, 'error': str(e)})
                
                # Analyze event delivery for contamination
                events_by_user = {}
                for event in event_collector:
                    user_id = event['user_id']
                    if user_id not in events_by_user:
                        events_by_user[user_id] = []
                    events_by_user[user_id].append(event)
                
                # Check for cross-contamination in events
                contamination_found = False
                for event in event_collector:
                    # Check if event content mentions a different user than the sender
                    if 'event' in event and isinstance(event['event'], dict):
                        event_content = event['event']
                        sender_user = event['user_id']
                        
                        # Look for user IDs in event content
                        for key, value in event_content.items():
                            if isinstance(value, str) and 'user_' in value:
                                mentioned_user = value
                                if mentioned_user != sender_user:
                                    event_delivery_failures.append({
                                        'registry': registry_name,
                                        'sender_user': sender_user,
                                        'mentioned_user': mentioned_user,
                                        'event_type': event_content.get('type', 'unknown'),
                                        'contamination_type': 'content_mismatch'
                                    })
                                    contamination_found = True
                
                logger.info(f"{registry_name} registry event analysis:")
                logger.info(f"  Total events collected: {len(event_collector)}")
                logger.info(f"  Users with events: {len(events_by_user)}")
                logger.info(f"  Contamination detected: {contamination_found}")
            
            # FAILURE CONDITION: Event contamination between users
            if event_delivery_failures:
                contamination_summary = "; ".join([
                    f"{f['registry']}: {f['event_type']} from {f['sender_user']} mentioned {f['mentioned_user']}"
                    for f in event_delivery_failures
                ])
                
                self.fail(
                    f"CRITICAL WEBSOCKET EVENT CONTAMINATION: {len(event_delivery_failures)} event delivery failures detected. "
                    f"WebSocket events intended for one user contain data from other users, causing privacy violations "
                    f"and confusing user experience. This blocks secure multi-user Golden Path operation. "
                    f"Contaminations: {contamination_summary}"
                )
                
        except Exception as e:
            self.fail(f"Unexpected error during WebSocket event contamination testing: {e}")
            
        # If no event contamination, that's the goal state
        logger.info("No WebSocket event contamination detected - proper user isolation maintained")

    def test_factory_pattern_user_isolation_validation(self):
        """
        TEST DESIGNED TO FAIL: Validate proper factory pattern implementation for user isolation.
        
        This test checks if registries properly implement factory patterns that create
        isolated instances per user, preventing shared state contamination.
        """
        import importlib
        
        isolation_violations = []
        
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            
            # Test factory pattern implementation
            for registry_name, registry_class in [('basic', basic_registry_class), ('advanced', advanced_registry_class)]:
                
                # Create multiple instances for different users
                user_instances = {}
                for user_context in self.test_users:
                    try:
                        instance = registry_class()
                        user_instances[user_context['user_id']] = {
                            'instance': instance,
                            'instance_id': id(instance),
                            'user_context': user_context
                        }
                    except Exception as e:
                        logger.warning(f"Could not create {registry_name} instance for {user_context['user_id']}: {e}")
                
                # Check if instances are actually different (not shared)
                instance_ids = [data['instance_id'] for data in user_instances.values()]
                unique_instance_ids = set(instance_ids)
                
                if len(unique_instance_ids) != len(instance_ids):
                    # Some instances are shared (same ID)
                    shared_instances = len(instance_ids) - len(unique_instance_ids)
                    isolation_violations.append({
                        'registry': registry_name,
                        'violation_type': 'shared_instances',
                        'total_instances': len(instance_ids),
                        'unique_instances': len(unique_instance_ids),
                        'shared_count': shared_instances
                    })
                
                # Check for shared internal state
                for user_id, instance_data in user_instances.items():
                    instance = instance_data['instance']
                    
                    # Look for attributes that might be shared across instances
                    shared_attributes = []
                    for attr_name in dir(instance):
                        if not attr_name.startswith('_') or attr_name in ['_websocket_manager', '_agents', '_state']:
                            try:
                                attr_value = getattr(instance, attr_name)
                                
                                # Check if this attribute is the same object across different instances
                                for other_user_id, other_instance_data in user_instances.items():
                                    if other_user_id != user_id:
                                        other_instance = other_instance_data['instance']
                                        if hasattr(other_instance, attr_name):
                                            other_attr_value = getattr(other_instance, attr_name)
                                            
                                            # If the attribute is the same object (not just equal value)
                                            if attr_value is other_attr_value and attr_value is not None:
                                                shared_attributes.append(attr_name)
                                                break
                                                
                            except Exception:
                                continue  # Skip attributes that can't be compared
                    
                    if shared_attributes:
                        isolation_violations.append({
                            'registry': registry_name,
                            'violation_type': 'shared_attributes',
                            'user_id': user_id,
                            'shared_attributes': shared_attributes
                        })
            
            # FAILURE CONDITION: Factory pattern not properly isolating users
            if isolation_violations:
                violation_summary = []
                for violation in isolation_violations:
                    if violation['violation_type'] == 'shared_instances':
                        detail = f"{violation['registry']}: {violation['shared_count']} instances shared among {violation['total_instances']} users"
                    elif violation['violation_type'] == 'shared_attributes':
                        detail = f"{violation['registry']}: user {violation['user_id']} shares attributes {violation['shared_attributes']}"
                    else:
                        detail = f"{violation['registry']}: {violation['violation_type']}"
                    violation_summary.append(detail)
                
                self.fail(
                    f"CRITICAL FACTORY PATTERN VIOLATION: {len(isolation_violations)} user isolation failures detected. "
                    f"Registry implementations are not properly isolating user contexts, allowing shared state "
                    f"contamination that causes privacy violations and unpredictable behavior. This blocks "
                    f"safe multi-user Golden Path operation. Violations: {'; '.join(violation_summary)}"
                )
                
        except Exception as e:
            self.fail(f"Unexpected error during factory pattern validation: {e}")
            
        # If proper isolation detected, that's the goal state
        logger.info("Proper factory pattern user isolation detected - SSOT compliance achieved")


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    pytest.main([__file__, "-v", "-s"])