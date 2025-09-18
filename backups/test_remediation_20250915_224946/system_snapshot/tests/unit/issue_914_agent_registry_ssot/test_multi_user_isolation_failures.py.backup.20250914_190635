"""
Multi-User Isolation Failure Tests for Issue #914 AgentRegistry SSOT Consolidation

CRITICAL P0 TESTS: These tests are DESIGNED TO FAIL initially to prove multi-user
isolation failures that cause user context contamination and memory leaks.

Business Value: $500K+ ARR Golden Path protection - ensures user isolation
prevents data leaks, memory issues, and cross-user contamination.

Test Focus:
- User context contamination between registries
- Memory leaks from shared state violations
- WebSocket event delivery to wrong users
- Concurrent execution isolation failures

Created: 2025-01-14 - Issue #914 Test Creation Plan
Priority: CRITICAL P0 - Must prove isolation failures blocking Golden Path
"""

import pytest
import asyncio
import time
import uuid
import threading
from typing import Dict, Any, List, Optional, Set
from unittest.mock import Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor

# SSOT Base Test Case - Required for all tests
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Environment access through SSOT pattern only
from shared.isolated_environment import IsolatedEnvironment

# Test imports - both registries to validate isolation
from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry


class TestAgentRegistryMultiUserIsolationFailures(SSotAsyncTestCase):
    """
    CRITICAL P0 Tests: Prove multi-user isolation failures block Golden Path
    
    These tests are DESIGNED TO FAIL initially to demonstrate isolation failures
    that cause user context contamination and security issues.
    """
    
    async def async_setup_method(self, method=None):
        """Set up test environment with SSOT patterns"""
        await super().async_setup_method(method)
        self.env = IsolatedEnvironment()
        
        # Initialize registries for isolation testing
        self.basic_registry = BasicRegistry()
        self.advanced_registry = AdvancedRegistry()
        
        # Mock WebSocket managers for event delivery testing
        self.user_websocket_managers = {}
        self.websocket_event_log = []
        self.websocket_event_lock = threading.Lock()
        
        # Test users for isolation validation
        self.test_users = [
            {"user_id": "user-1-isolation-test", "session_id": "session-1-test"},
            {"user_id": "user-2-isolation-test", "session_id": "session-2-test"},
            {"user_id": "user-3-isolation-test", "session_id": "session-3-test"}
        ]
        
        # Memory tracking for leak detection
        self.memory_snapshots = {}
        self.registry_instance_tracking = {}

    async def test_user_context_contamination_between_registries(self):
        """
        CRITICAL P0 TEST: Prove user context contamination
        
        DESIGNED TO FAIL: User contexts leak between registry instances causing
        data contamination where User A sees User B's data or agent state.
        
        Business Impact: Golden Path breaks user privacy when agent responses
        contain data from other users, causing security breaches and lost trust.
        """
        user_context_isolation_results = {}
        contamination_evidence = []
        
        # Create user sessions in both registries
        registry_user_sessions = {
            'basic': {},
            'advanced': {}
        }
        
        # Test user session creation and isolation
        for user_info in self.test_users:
            user_id = user_info['user_id']
            session_id = user_info['session_id']
            
            user_context_isolation_results[user_id] = {
                'basic_registry': {'success': False, 'context': None, 'error': None},
                'advanced_registry': {'success': False, 'context': None, 'error': None},
                'unique_data': f"PRIVATE_DATA_FOR_{user_id}_{uuid.uuid4().hex[:8]}"
            }
            
            # Try creating user session in basic registry
            try:
                if hasattr(self.basic_registry, 'create_user_session'):
                    basic_context = await self.basic_registry.create_user_session(user_id, session_id)
                    registry_user_sessions['basic'][user_id] = basic_context
                    
                    # Store unique data in context if possible
                    if hasattr(basic_context, 'set_user_data') and basic_context:
                        await basic_context.set_user_data('private_data', 
                                                        user_context_isolation_results[user_id]['unique_data'])
                    
                    user_context_isolation_results[user_id]['basic_registry'] = {
                        'success': True,
                        'context': basic_context,
                        'context_id': id(basic_context) if basic_context else None
                    }
                    
                    self.logger.info(f"Basic registry user session created for {user_id}")
                else:
                    user_context_isolation_results[user_id]['basic_registry'] = {
                        'success': False,
                        'error': 'create_user_session method not available'
                    }
                    
            except Exception as e:
                user_context_isolation_results[user_id]['basic_registry'] = {
                    'success': False,
                    'error': str(e)
                }
                self.logger.error(f"Basic registry user session failed for {user_id}: {e}")
            
            # Try creating user session in advanced registry
            try:
                if hasattr(self.advanced_registry, 'create_user_session'):
                    advanced_context = await self.advanced_registry.create_user_session(user_id, session_id)
                    registry_user_sessions['advanced'][user_id] = advanced_context
                    
                    # Store unique data in context if possible
                    if hasattr(advanced_context, 'set_user_data') and advanced_context:
                        await advanced_context.set_user_data('private_data', 
                                                           user_context_isolation_results[user_id]['unique_data'])
                    
                    user_context_isolation_results[user_id]['advanced_registry'] = {
                        'success': True,
                        'context': advanced_context,
                        'context_id': id(advanced_context) if advanced_context else None
                    }
                    
                    self.logger.info(f"Advanced registry user session created for {user_id}")
                else:
                    user_context_isolation_results[user_id]['advanced_registry'] = {
                        'success': False,
                        'error': 'create_user_session method not available'
                    }
                    
            except Exception as e:
                user_context_isolation_results[user_id]['advanced_registry'] = {
                    'success': False,
                    'error': str(e)
                }
                self.logger.error(f"Advanced registry user session failed for {user_id}: {e}")
        
        # Test for cross-user data contamination
        for user_info in self.test_users:
            user_id = user_info['user_id']
            
            # Check each registry type
            for registry_type in ['basic', 'advanced']:
                if user_context_isolation_results[user_id][f'{registry_type}_registry']['success']:
                    context = user_context_isolation_results[user_id][f'{registry_type}_registry']['context']
                    
                    if context and hasattr(context, 'get_user_data'):
                        try:
                            # Try to retrieve this user's data
                            user_data = await context.get_user_data('private_data')
                            expected_data = user_context_isolation_results[user_id]['unique_data']
                            
                            # Check if data matches expected value
                            if user_data != expected_data:
                                contamination_evidence.append({
                                    'contamination_type': 'data_mismatch',
                                    'registry': registry_type,
                                    'user_id': user_id,
                                    'expected_data': expected_data,
                                    'actual_data': user_data,
                                    'description': f"User {user_id} got wrong data from {registry_type} registry"
                                })
                            
                            # Try to access other users' data (should fail)
                            for other_user in self.test_users:
                                if other_user['user_id'] != user_id:
                                    try:
                                        other_user_data = await context.get_user_data(
                                            f"private_data_for_{other_user['user_id']}"
                                        )
                                        if other_user_data is not None:
                                            contamination_evidence.append({
                                                'contamination_type': 'cross_user_access',
                                                'registry': registry_type,
                                                'user_id': user_id,
                                                'accessed_other_user': other_user['user_id'],
                                                'leaked_data': other_user_data,
                                                'description': f"User {user_id} accessed data from {other_user['user_id']}"
                                            })
                                    except:
                                        # This is expected - cross-user access should fail
                                        pass
                                        
                        except Exception as e:
                            self.logger.warning(f"Could not test user data for {user_id} in {registry_type}: {e}")
        
        # Test for shared state contamination at registry level
        registry_state_contamination = []
        
        # Check if registries share state between users
        successful_basic_sessions = [info['basic_registry']['context'] for info in user_context_isolation_results.values() 
                                   if info['basic_registry']['success'] and info['basic_registry']['context']]
        successful_advanced_sessions = [info['advanced_registry']['context'] for info in user_context_isolation_results.values() 
                                      if info['advanced_registry']['success'] and info['advanced_registry']['context']]
        
        # Check basic registry for shared state
        if len(successful_basic_sessions) > 1:
            for i, context_a in enumerate(successful_basic_sessions):
                for j, context_b in enumerate(successful_basic_sessions):
                    if i != j and id(context_a) == id(context_b):
                        registry_state_contamination.append({
                            'contamination_type': 'shared_context_instance',
                            'registry': 'basic',
                            'context_id': id(context_a),
                            'description': f"Multiple users share same context instance in basic registry"
                        })
        
        # Check advanced registry for shared state  
        if len(successful_advanced_sessions) > 1:
            for i, context_a in enumerate(successful_advanced_sessions):
                for j, context_b in enumerate(successful_advanced_sessions):
                    if i != j and id(context_a) == id(context_b):
                        registry_state_contamination.append({
                            'contamination_type': 'shared_context_instance',
                            'registry': 'advanced',
                            'context_id': id(context_a),
                            'description': f"Multiple users share same context instance in advanced registry"
                        })
        
        # DESIGNED TO FAIL: User context contamination detected
        failure_reasons = []
        
        if contamination_evidence:
            for evidence in contamination_evidence:
                failure_reasons.append(
                    f"{evidence['contamination_type']} in {evidence['registry']} registry: {evidence['description']}"
                )
        
        if registry_state_contamination:
            for contamination in registry_state_contamination:
                failure_reasons.append(
                    f"{contamination['contamination_type']}: {contamination['description']}"
                )
        
        # Check for missing isolation features
        isolation_feature_missing = []
        for user_info in self.test_users:
            user_id = user_info['user_id']
            for registry_type in ['basic', 'advanced']:
                if not user_context_isolation_results[user_id][f'{registry_type}_registry']['success']:
                    error = user_context_isolation_results[user_id][f'{registry_type}_registry']['error']
                    if 'not available' in str(error):
                        isolation_feature_missing.append(f"{registry_type} registry missing user session support")
        
        if isolation_feature_missing:
            failure_reasons.extend(isolation_feature_missing)
        
        if failure_reasons:
            pytest.fail(
                f"CRITICAL USER CONTEXT CONTAMINATION: Multi-user isolation failures detected. "
                f"This causes privacy breaches and data leaks blocking Golden Path security. "
                f"Contamination evidence: {'; '.join(failure_reasons)}. "
                f"IMPACT: Users see other users' private data and agent responses."
            )
        
        # If no contamination detected, isolation is working properly
        self.logger.info("User context isolation is properly implemented across all registries")

    async def test_memory_leaks_from_shared_state_violations(self):
        """
        CRITICAL P0 TEST: Prove memory leaks from shared state
        
        DESIGNED TO FAIL: Shared state between registry instances causes memory
        to accumulate over time, leading to memory leaks and service degradation.
        
        Business Impact: Golden Path degrades over time as memory leaks cause
        service slowdowns and eventual crashes affecting all users.
        """
        memory_leak_evidence = []
        registry_instance_growth = {}
        shared_state_violations = []
        
        # Track initial memory state
        import gc
        import sys
        
        initial_object_counts = {}
        for obj_type in [BasicRegistry, AdvancedRegistry]:
            initial_object_counts[obj_type.__name__] = len([obj for obj in gc.get_objects() 
                                                          if type(obj) == obj_type])
        
        self.logger.info(f"Initial object counts: {initial_object_counts}")
        
        # Simulate multiple user sessions to detect memory accumulation
        session_cycles = 5
        users_per_cycle = 3
        
        for cycle in range(session_cycles):
            cycle_registries = {
                'basic': [],
                'advanced': []
            }
            
            # Create multiple registry instances and user sessions per cycle
            for user_num in range(users_per_cycle):
                user_id = f"memory-test-user-{cycle}-{user_num}"
                session_id = f"memory-test-session-{cycle}-{user_num}"
                
                # Create new registry instances
                try:
                    basic_registry = BasicRegistry()
                    cycle_registries['basic'].append(basic_registry)
                    
                    # Try to create user session if supported
                    if hasattr(basic_registry, 'create_user_session'):
                        user_context = await basic_registry.create_user_session(user_id, session_id)
                        
                        # Add some data to the context to simulate usage
                        if hasattr(user_context, 'set_user_data') and user_context:
                            test_data = f"test_data_{cycle}_{user_num}_{uuid.uuid4().hex}"
                            await user_context.set_user_data('test_data', test_data)
                    
                    self.logger.debug(f"Created basic registry instance for {user_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to create basic registry for {user_id}: {e}")
                
                try:
                    advanced_registry = AdvancedRegistry()
                    cycle_registries['advanced'].append(advanced_registry)
                    
                    # Try to create user session if supported
                    if hasattr(advanced_registry, 'create_user_session'):
                        user_context = await advanced_registry.create_user_session(user_id, session_id)
                        
                        # Add some data to the context to simulate usage
                        if hasattr(user_context, 'set_user_data') and user_context:
                            test_data = f"test_data_{cycle}_{user_num}_{uuid.uuid4().hex}"
                            await user_context.set_user_data('test_data', test_data)
                    
                    self.logger.debug(f"Created advanced registry instance for {user_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to create advanced registry for {user_id}: {e}")
            
            # Track object counts after each cycle
            current_object_counts = {}
            for obj_type in [BasicRegistry, AdvancedRegistry]:
                current_object_counts[obj_type.__name__] = len([obj for obj in gc.get_objects() 
                                                              if type(obj) == obj_type])
            
            registry_instance_growth[cycle] = {
                'cycle': cycle,
                'basic_instances': len(cycle_registries['basic']),
                'advanced_instances': len(cycle_registries['advanced']),
                'total_basic_objects': current_object_counts['BasicRegistry'],
                'total_advanced_objects': current_object_counts['AdvancedRegistry']
            }
            
            self.logger.info(f"Cycle {cycle} - Basic: {current_object_counts['BasicRegistry']}, "
                           f"Advanced: {current_object_counts['AdvancedRegistry']}")
            
            # Test for shared state violations
            for registry_type, registries in cycle_registries.items():
                if len(registries) > 1:
                    # Check if registries share internal state
                    for i, registry_a in enumerate(registries):
                        for j, registry_b in enumerate(registries):
                            if i != j:
                                # Check for shared attributes that indicate state sharing
                                shared_attributes = []
                                
                                for attr_name in ['_agents', '_user_sessions', '_websocket_manager', 'agent_registry']:
                                    if hasattr(registry_a, attr_name) and hasattr(registry_b, attr_name):
                                        attr_a = getattr(registry_a, attr_name)
                                        attr_b = getattr(registry_b, attr_name)
                                        
                                        if attr_a is attr_b and attr_a is not None:
                                            shared_attributes.append(attr_name)
                                
                                if shared_attributes:
                                    shared_state_violations.append({
                                        'cycle': cycle,
                                        'registry_type': registry_type,
                                        'registry_a_id': id(registry_a),
                                        'registry_b_id': id(registry_b),
                                        'shared_attributes': shared_attributes,
                                        'description': f"Registries share state attributes: {shared_attributes}"
                                    })
            
            # Small delay to allow garbage collection
            await asyncio.sleep(0.1)
            
            # Force garbage collection
            gc.collect()
        
        # Analyze memory growth patterns
        final_object_counts = {}
        for obj_type in [BasicRegistry, AdvancedRegistry]:
            final_object_counts[obj_type.__name__] = len([obj for obj in gc.get_objects() 
                                                        if type(obj) == obj_type])
        
        # Calculate memory growth
        memory_growth_analysis = {}
        for obj_type_name in initial_object_counts.keys():
            initial_count = initial_object_counts[obj_type_name]
            final_count = final_object_counts[obj_type_name]
            expected_count = initial_count  # Should return to initial after GC
            
            memory_growth_analysis[obj_type_name] = {
                'initial_count': initial_count,
                'final_count': final_count,
                'expected_count': expected_count,
                'growth': final_count - initial_count,
                'potential_leak': final_count > expected_count + 1  # Allow some tolerance
            }
        
        # Check for memory leaks over time
        for cycle_data in registry_instance_growth.values():
            cycle_num = cycle_data['cycle']
            
            # Compare object counts to expected values
            expected_basic = initial_object_counts['BasicRegistry'] + cycle_data['basic_instances']
            expected_advanced = initial_object_counts['AdvancedRegistry'] + cycle_data['advanced_instances']
            
            if cycle_data['total_basic_objects'] > expected_basic * 1.5:  # 50% tolerance
                memory_leak_evidence.append({
                    'cycle': cycle_num,
                    'registry_type': 'basic',
                    'expected_objects': expected_basic,
                    'actual_objects': cycle_data['total_basic_objects'],
                    'excess_objects': cycle_data['total_basic_objects'] - expected_basic,
                    'description': f"BasicRegistry object count exceeds expected by {cycle_data['total_basic_objects'] - expected_basic}"
                })
            
            if cycle_data['total_advanced_objects'] > expected_advanced * 1.5:  # 50% tolerance
                memory_leak_evidence.append({
                    'cycle': cycle_num,
                    'registry_type': 'advanced',
                    'expected_objects': expected_advanced,
                    'actual_objects': cycle_data['total_advanced_objects'],
                    'excess_objects': cycle_data['total_advanced_objects'] - expected_advanced,
                    'description': f"AdvancedRegistry object count exceeds expected by {cycle_data['total_advanced_objects'] - expected_advanced}"
                })
        
        # DESIGNED TO FAIL: Memory leaks or shared state violations detected
        failure_reasons = []
        
        if memory_leak_evidence:
            for evidence in memory_leak_evidence:
                failure_reasons.append(
                    f"Memory leak in {evidence['registry_type']} registry cycle {evidence['cycle']}: "
                    f"{evidence['excess_objects']} excess objects ({evidence['description']})"
                )
        
        if shared_state_violations:
            for violation in shared_state_violations:
                failure_reasons.append(
                    f"Shared state violation in {violation['registry_type']} registry cycle {violation['cycle']}: "
                    f"{violation['description']}"
                )
        
        # Check for persistent memory growth
        persistent_growth = []
        for obj_type_name, analysis in memory_growth_analysis.items():
            if analysis['potential_leak']:
                persistent_growth.append(
                    f"{obj_type_name}: {analysis['growth']} objects not cleaned up "
                    f"({analysis['final_count']} final vs {analysis['expected_count']} expected)"
                )
        
        if persistent_growth:
            failure_reasons.extend(persistent_growth)
        
        if failure_reasons:
            pytest.fail(
                f"CRITICAL MEMORY LEAKS FROM SHARED STATE: Memory leaks and state sharing violations detected. "
                f"This causes service degradation and crashes blocking Golden Path reliability. "
                f"Memory issues: {'; '.join(failure_reasons)}. "
                f"IMPACT: Service performance degrades over time, affecting all users."
            )
        
        # If no memory leaks or shared state issues, isolation is properly implemented
        self.logger.info(f"No memory leaks detected - proper isolation maintained. "
                        f"Final object counts: {final_object_counts}")

    async def test_websocket_event_delivery_to_wrong_users(self):
        """
        CRITICAL P0 TEST: Prove WebSocket events delivered to wrong users
        
        DESIGNED TO FAIL: Registry SSOT violations cause WebSocket events to be
        delivered to wrong users, leaking private agent progress and responses.
        
        Business Impact: Golden Path privacy breach when users see other users'
        agent activities, causing security issues and user confusion.
        """
        websocket_event_contamination = []
        user_event_isolation_results = {}
        
        # Create mock WebSocket managers for each test user
        for user_info in self.test_users:
            user_id = user_info['user_id']
            
            # Create user-specific WebSocket manager mock
            websocket_manager = AsyncMock()
            websocket_manager.emit_agent_event = AsyncMock()
            self.user_websocket_managers[user_id] = websocket_manager
            
            user_event_isolation_results[user_id] = {
                'websocket_manager': websocket_manager,
                'events_received': [],
                'events_expected': [],
                'basic_registry_setup': False,
                'advanced_registry_setup': False
            }
        
        # Set up WebSocket managers in both registry types
        for user_info in self.test_users:
            user_id = user_info['user_id']
            session_id = user_info['session_id']
            websocket_manager = self.user_websocket_managers[user_id]
            
            # Set up WebSocket manager in basic registry
            try:
                if hasattr(self.basic_registry, 'set_websocket_manager'):
                    if asyncio.iscoroutinefunction(self.basic_registry.set_websocket_manager):
                        await self.basic_registry.set_websocket_manager(websocket_manager)
                    else:
                        self.basic_registry.set_websocket_manager(websocket_manager)
                    
                    user_event_isolation_results[user_id]['basic_registry_setup'] = True
                    self.logger.info(f"Basic registry WebSocket setup for {user_id}")
                    
            except Exception as e:
                self.logger.warning(f"Failed to set WebSocket manager in basic registry for {user_id}: {e}")
            
            # Set up WebSocket manager in advanced registry  
            try:
                if hasattr(self.advanced_registry, 'set_websocket_manager'):
                    if asyncio.iscoroutinefunction(self.advanced_registry.set_websocket_manager):
                        await self.advanced_registry.set_websocket_manager(websocket_manager)
                    else:
                        self.advanced_registry.set_websocket_manager(websocket_manager)
                    
                    user_event_isolation_results[user_id]['advanced_registry_setup'] = True
                    self.logger.info(f"Advanced registry WebSocket setup for {user_id}")
                    
            except Exception as e:
                self.logger.warning(f"Failed to set WebSocket manager in advanced registry for {user_id}: {e}")
        
        # Simulate agent events for each user
        agent_events = [
            {'event': 'agent_started', 'data': {'agent_id': 'test-agent', 'status': 'started'}},
            {'event': 'agent_thinking', 'data': {'agent_id': 'test-agent', 'message': 'Processing request'}},
            {'event': 'agent_completed', 'data': {'agent_id': 'test-agent', 'result': 'Task completed'}}
        ]
        
        # Send events through each registry for each user
        for user_info in self.test_users:
            user_id = user_info['user_id']
            session_id = user_info['session_id']
            
            for event in agent_events:
                # Create user-specific event data
                user_specific_event = {
                    'event': event['event'],
                    'data': {
                        **event['data'],
                        'user_id': user_id,
                        'session_id': session_id,
                        'private_data': f"PRIVATE_EVENT_DATA_FOR_{user_id}_{uuid.uuid4().hex[:8]}"
                    }
                }
                
                user_event_isolation_results[user_id]['events_expected'].append(user_specific_event)
                
                # Try sending through basic registry
                if user_event_isolation_results[user_id]['basic_registry_setup']:
                    try:
                        if hasattr(self.basic_registry, '_notify_agent_event'):
                            await self.basic_registry._notify_agent_event(
                                user_specific_event['event'],
                                user_specific_event['data']
                            )
                        elif hasattr(self.basic_registry, 'emit_agent_event'):
                            await self.basic_registry.emit_agent_event(
                                user_specific_event['event'],
                                user_specific_event['data']
                            )
                        
                        self.logger.debug(f"Sent event {event['event']} through basic registry for {user_id}")
                    except Exception as e:
                        self.logger.warning(f"Failed to send event through basic registry for {user_id}: {e}")
                
                # Try sending through advanced registry
                if user_event_isolation_results[user_id]['advanced_registry_setup']:
                    try:
                        if hasattr(self.advanced_registry, '_notify_agent_event'):
                            await self.advanced_registry._notify_agent_event(
                                user_specific_event['event'],
                                user_specific_event['data']
                            )
                        elif hasattr(self.advanced_registry, 'emit_agent_event'):
                            await self.advanced_registry.emit_agent_event(
                                user_specific_event['event'], 
                                user_specific_event['data']
                            )
                        
                        self.logger.debug(f"Sent event {event['event']} through advanced registry for {user_id}")
                    except Exception as e:
                        self.logger.warning(f"Failed to send event through advanced registry for {user_id}: {e}")
        
        # Allow time for event processing
        await asyncio.sleep(0.5)
        
        # Analyze WebSocket manager calls to detect cross-user contamination
        for user_id, results in user_event_isolation_results.items():
            websocket_manager = results['websocket_manager']
            
            # Check all calls made to this user's WebSocket manager
            if websocket_manager.emit_agent_event.called:
                for call in websocket_manager.emit_agent_event.call_args_list:
                    args, kwargs = call
                    
                    # Extract event data
                    if len(args) >= 2:
                        event_type = args[0]
                        event_data = args[1]
                    elif 'event' in kwargs and 'data' in kwargs:
                        event_type = kwargs['event']
                        event_data = kwargs['data']
                    else:
                        continue
                    
                    results['events_received'].append({
                        'event': event_type,
                        'data': event_data
                    })
                    
                    # Check if this event contains data for other users
                    if isinstance(event_data, dict):
                        event_user_id = event_data.get('user_id')
                        private_data = event_data.get('private_data', '')
                        
                        # If event contains another user's data, it's contamination
                        if event_user_id and event_user_id != user_id:
                            websocket_event_contamination.append({
                                'contamination_type': 'wrong_user_event',
                                'receiving_user': user_id,
                                'event_from_user': event_user_id,
                                'event_type': event_type,
                                'private_data_leaked': private_data,
                                'description': f"User {user_id} received event for user {event_user_id}"
                            })
                        
                        # Check for private data from other users
                        if private_data and f'FOR_{user_id}_' not in private_data:
                            # This private data doesn't belong to receiving user
                            for other_user in self.test_users:
                                if f"FOR_{other_user['user_id']}_" in private_data:
                                    websocket_event_contamination.append({
                                        'contamination_type': 'private_data_leak',
                                        'receiving_user': user_id,
                                        'data_from_user': other_user['user_id'],
                                        'event_type': event_type,
                                        'leaked_private_data': private_data,
                                        'description': f"User {user_id} received private data from {other_user['user_id']}"
                                    })
                                    break
        
        # Check for missing events (events sent but not received by correct user)
        missing_events = []
        for user_id, results in user_event_isolation_results.items():
            expected_events = results['events_expected']
            received_events = results['events_received']
            
            for expected_event in expected_events:
                # Check if this expected event was received
                event_received = False
                for received_event in received_events:
                    if (received_event['event'] == expected_event['event'] and
                        received_event['data'].get('user_id') == user_id):
                        event_received = True
                        break
                
                if not event_received:
                    missing_events.append({
                        'user_id': user_id,
                        'missing_event': expected_event['event'],
                        'event_data': expected_event['data'],
                        'description': f"User {user_id} did not receive expected {expected_event['event']} event"
                    })
        
        # DESIGNED TO FAIL: WebSocket event contamination or isolation failures
        failure_reasons = []
        
        if websocket_event_contamination:
            for contamination in websocket_event_contamination:
                failure_reasons.append(
                    f"{contamination['contamination_type']}: {contamination['description']}"
                )
        
        if missing_events:
            for missing in missing_events:
                failure_reasons.append(f"Missing event: {missing['description']}")
        
        # Check for WebSocket setup failures
        setup_failures = []
        for user_id, results in user_event_isolation_results.items():
            if not results['basic_registry_setup'] and not results['advanced_registry_setup']:
                setup_failures.append(f"User {user_id} failed WebSocket setup in both registries")
        
        if setup_failures:
            failure_reasons.extend(setup_failures)
        
        if failure_reasons:
            pytest.fail(
                f"CRITICAL WEBSOCKET EVENT CONTAMINATION: WebSocket events delivered to wrong users. "
                f"This causes privacy breaches and user confusion blocking Golden Path security. "
                f"Event contamination: {'; '.join(failure_reasons)}. "
                f"IMPACT: Users see other users' private agent activities and responses."
            )
        
        # If no contamination detected, WebSocket event isolation is working
        self.logger.info("WebSocket event isolation is properly implemented across all users")

    async def test_concurrent_execution_isolation_failures(self):
        """
        CRITICAL P0 TEST: Prove concurrent execution isolation failures
        
        DESIGNED TO FAIL: Multiple users executing agents concurrently causes
        execution context leaks and race conditions between user sessions.
        
        Business Impact: Golden Path fails for concurrent users when execution
        contexts interfere, causing incorrect responses and system instability.
        """
        concurrent_execution_failures = []
        execution_isolation_results = {}
        
        # Create concurrent execution test scenarios
        concurrent_users = [
            {"user_id": f"concurrent-user-{i}", "session_id": f"concurrent-session-{i}"} 
            for i in range(5)  # Test with 5 concurrent users
        ]
        
        # Initialize execution tracking for each user
        for user_info in concurrent_users:
            user_id = user_info['user_id']
            execution_isolation_results[user_id] = {
                'execution_started': False,
                'execution_completed': False,
                'execution_results': [],
                'execution_errors': [],
                'context_contamination': [],
                'basic_registry_results': None,
                'advanced_registry_results': None
            }
        
        # Define concurrent execution tasks
        async def execute_user_task(user_info, registry, registry_type):
            user_id = user_info['user_id']
            session_id = user_info['session_id']
            
            try:
                execution_isolation_results[user_id]['execution_started'] = True
                
                # Create unique execution data for this user
                unique_data = f"EXECUTION_DATA_FOR_{user_id}_{uuid.uuid4().hex[:8]}"
                execution_start_time = time.time()
                
                # Try to create user session if supported
                user_context = None
                if hasattr(registry, 'create_user_session'):
                    user_context = await registry.create_user_session(user_id, session_id)
                    
                    # Store unique execution data
                    if hasattr(user_context, 'set_user_data') and user_context:
                        await user_context.set_user_data('execution_data', unique_data)
                        await user_context.set_user_data('execution_start_time', execution_start_time)
                
                # Simulate agent execution
                await asyncio.sleep(0.1)  # Simulate processing time
                
                # Try to get available agents
                agents = None
                if hasattr(registry, 'list_available_agents'):
                    list_agents_method = getattr(registry, 'list_available_agents')
                    if asyncio.iscoroutinefunction(list_agents_method):
                        agents = await list_agents_method()
                    else:
                        agents = list_agents_method()
                
                # Verify execution data integrity
                execution_data_intact = True
                if user_context and hasattr(user_context, 'get_user_data'):
                    retrieved_data = await user_context.get_user_data('execution_data')
                    retrieved_start_time = await user_context.get_user_data('execution_start_time')
                    
                    if retrieved_data != unique_data:
                        execution_isolation_results[user_id]['context_contamination'].append({
                            'contamination_type': 'execution_data_mismatch',
                            'expected': unique_data,
                            'actual': retrieved_data,
                            'registry_type': registry_type
                        })
                        execution_data_intact = False
                    
                    if retrieved_start_time != execution_start_time:
                        execution_isolation_results[user_id]['context_contamination'].append({
                            'contamination_type': 'execution_time_mismatch',
                            'expected': execution_start_time,
                            'actual': retrieved_start_time,
                            'registry_type': registry_type
                        })
                        execution_data_intact = False
                
                # Record execution results
                execution_result = {
                    'registry_type': registry_type,
                    'user_id': user_id,
                    'session_id': session_id,
                    'execution_time': time.time() - execution_start_time,
                    'agents_retrieved': agents is not None,
                    'agents_count': len(agents) if isinstance(agents, list) else None,
                    'user_context_created': user_context is not None,
                    'execution_data_intact': execution_data_intact,
                    'unique_data': unique_data
                }
                
                execution_isolation_results[user_id]['execution_results'].append(execution_result)
                execution_isolation_results[user_id][f'{registry_type}_registry_results'] = execution_result
                execution_isolation_results[user_id]['execution_completed'] = True
                
                self.logger.debug(f"Concurrent execution completed for {user_id} in {registry_type} registry")
                
                return execution_result
                
            except Exception as e:
                execution_isolation_results[user_id]['execution_errors'].append({
                    'registry_type': registry_type,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                self.logger.error(f"Concurrent execution failed for {user_id} in {registry_type} registry: {e}")
                return None
        
        # Execute concurrent tasks for basic registry
        basic_registry_tasks = [
            execute_user_task(user_info, self.basic_registry, 'basic')
            for user_info in concurrent_users
        ]
        
        # Execute concurrent tasks for advanced registry
        advanced_registry_tasks = [
            execute_user_task(user_info, self.advanced_registry, 'advanced')
            for user_info in concurrent_users
        ]
        
        # Run concurrent executions
        self.logger.info("Starting concurrent execution tests...")
        
        basic_results = await asyncio.gather(*basic_registry_tasks, return_exceptions=True)
        await asyncio.sleep(0.2)  # Brief pause between registry tests
        advanced_results = await asyncio.gather(*advanced_registry_tasks, return_exceptions=True)
        
        # Analyze concurrent execution results for isolation failures
        for user_id, results in execution_isolation_results.items():
            # Check for context contamination
            if results['context_contamination']:
                for contamination in results['context_contamination']:
                    concurrent_execution_failures.append({
                        'failure_type': 'context_contamination',
                        'user_id': user_id,
                        'registry_type': contamination['registry_type'],
                        'contamination_type': contamination['contamination_type'],
                        'description': f"User {user_id} execution context contaminated in {contamination['registry_type']} registry"
                    })
            
            # Check for execution errors
            if results['execution_errors']:
                for error in results['execution_errors']:
                    concurrent_execution_failures.append({
                        'failure_type': 'execution_error',
                        'user_id': user_id,
                        'registry_type': error['registry_type'],
                        'error': error['error'],
                        'description': f"User {user_id} execution failed in {error['registry_type']} registry: {error['error']}"
                    })
        
        # Check for cross-user execution contamination
        for user_a_id, results_a in execution_isolation_results.items():
            for user_b_id, results_b in execution_isolation_results.items():
                if user_a_id != user_b_id:
                    # Compare execution results for contamination
                    for result_a in results_a['execution_results']:
                        for result_b in results_b['execution_results']:
                            if (result_a['registry_type'] == result_b['registry_type'] and
                                result_a['unique_data'] == result_b['unique_data']):
                                # Same unique data across different users indicates contamination
                                concurrent_execution_failures.append({
                                    'failure_type': 'cross_user_contamination',
                                    'user_a': user_a_id,
                                    'user_b': user_b_id,
                                    'registry_type': result_a['registry_type'],
                                    'contaminated_data': result_a['unique_data'],
                                    'description': f"Users {user_a_id} and {user_b_id} share execution data in {result_a['registry_type']} registry"
                                })
        
        # Check for inconsistent execution results that indicate isolation failures
        registry_execution_consistency = {}
        for registry_type in ['basic', 'advanced']:
            registry_execution_consistency[registry_type] = {
                'successful_executions': 0,
                'failed_executions': 0,
                'execution_times': [],
                'agents_counts': []
            }
            
            for user_id, results in execution_isolation_results.items():
                registry_result = results.get(f'{registry_type}_registry_results')
                if registry_result:
                    registry_execution_consistency[registry_type]['successful_executions'] += 1
                    registry_execution_consistency[registry_type]['execution_times'].append(registry_result['execution_time'])
                    
                    if registry_result['agents_count'] is not None:
                        registry_execution_consistency[registry_type]['agents_counts'].append(registry_result['agents_count'])
                else:
                    registry_execution_consistency[registry_type]['failed_executions'] += 1
        
        # Check for suspiciously inconsistent results
        for registry_type, consistency in registry_execution_consistency.items():
            # Check for high failure rate
            total_attempts = consistency['successful_executions'] + consistency['failed_executions']
            if total_attempts > 0:
                failure_rate = consistency['failed_executions'] / total_attempts
                if failure_rate > 0.2:  # More than 20% failure rate indicates problems
                    concurrent_execution_failures.append({
                        'failure_type': 'high_failure_rate',
                        'registry_type': registry_type,
                        'failure_rate': failure_rate * 100,
                        'description': f"{registry_type} registry has {failure_rate*100:.1f}% execution failure rate"
                    })
            
            # Check for highly variable execution times (indicates contention/blocking)
            if len(consistency['execution_times']) > 1:
                min_time = min(consistency['execution_times'])
                max_time = max(consistency['execution_times'])
                if max_time > min_time * 3:  # More than 3x variation indicates blocking
                    concurrent_execution_failures.append({
                        'failure_type': 'execution_time_variance',
                        'registry_type': registry_type,
                        'min_time': min_time,
                        'max_time': max_time,
                        'variance_ratio': max_time / min_time,
                        'description': f"{registry_type} registry shows high execution time variance ({max_time/min_time:.1f}x)"
                    })
        
        # DESIGNED TO FAIL: Concurrent execution isolation failures detected
        failure_reasons = []
        
        if concurrent_execution_failures:
            for failure in concurrent_execution_failures:
                failure_reasons.append(f"{failure['failure_type']}: {failure['description']}")
        
        if failure_reasons:
            pytest.fail(
                f"CRITICAL CONCURRENT EXECUTION ISOLATION FAILURES: Multiple users interfere during concurrent execution. "
                f"This causes incorrect responses and system instability blocking Golden Path reliability. "
                f"Isolation failures: {'; '.join(failure_reasons)}. "
                f"IMPACT: Concurrent users experience incorrect agent responses and execution errors."
            )
        
        # If no isolation failures detected, concurrent execution is properly isolated
        self.logger.info("Concurrent execution isolation is properly implemented across all users")

    async def async_teardown_method(self, method=None):
        """Clean up test resources and memory"""
        # Clear tracking data
        self.memory_snapshots.clear()
        self.registry_instance_tracking.clear()
        self.user_websocket_managers.clear()
        self.websocket_event_log.clear()
        
        await super().async_teardown_method(method)


if __name__ == "__main__":
    # Run with pytest for proper async support
    pytest.main([__file__, "-v", "--tb=short", "-s"])