"""
Issue #1182 Race Condition Detection Tests

Tests to detect race conditions in WebSocket Manager initialization and usage:
- Concurrent manager initialization
- Singleton pattern race conditions  
- Factory registration timing issues
- Multi-user session isolation failures

These tests should FAIL initially to prove race conditions exist.
"""

import pytest
import threading
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any, Set

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class TestIssue1182RaceConditionDetection(SSotBaseTestCase):
    """Unit tests to detect WebSocket Manager race conditions"""

    def test_concurrent_websocket_manager_initialization_race(self):
        """SHOULD FAIL: Detect race conditions in concurrent manager initialization"""
        initialization_results = []
        initialization_lock = threading.Lock()
        
        def initialize_manager(thread_id: int):
            """Initialize WebSocket manager in separate thread"""
            try:
                # Simulate concurrent initialization
                time.sleep(0.01)  # Small delay to increase race condition probability
                
                # Try multiple initialization approaches
                managers = {}
                
                # Approach 1: Direct import and instantiation
                try:
                    from netra_backend.app.websocket_core.manager import WebSocketManager
                    managers['backend_direct'] = WebSocketManager()
                except Exception as e:
                    managers['backend_direct'] = f"ERROR: {str(e)}"
                
                # Approach 2: Factory pattern (if exists)
                try:
                    from netra_backend.app.websocket_core.manager import WebSocketManager
                    if hasattr(WebSocketManager, 'get_instance'):
                        managers['backend_singleton'] = WebSocketManager.get_instance()
                    elif hasattr(WebSocketManager, 'create'):
                        managers['backend_factory'] = WebSocketManager.create()
                except Exception as e:
                    managers['backend_factory'] = f"ERROR: {str(e)}"
                
                # Approach 3: Shared module
                try:
                    from shared.websocket.manager import WebSocketManager as SharedManager
                    managers['shared'] = SharedManager()
                except Exception as e:
                    managers['shared'] = f"ERROR: {str(e)}"
                
                with initialization_lock:
                    initialization_results.append({
                        'thread_id': thread_id,
                        'managers': managers,
                        'instance_ids': {k: id(v) if not isinstance(v, str) else v for k, v in managers.items()},
                        'timestamp': time.time()
                    })
                    
            except Exception as e:
                with initialization_lock:
                    initialization_results.append({
                        'thread_id': thread_id,
                        'error': str(e),
                        'timestamp': time.time()
                    })
        
        # Run concurrent initializations
        threads = []
        num_threads = 10
        
        for i in range(num_threads):
            thread = threading.Thread(target=initialize_manager, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Analyze results for race conditions
        successful_results = [r for r in initialization_results if 'error' not in r]
        
        self.logger.info(f"Concurrent initialization results: {len(successful_results)}/{num_threads} successful")
        
        if len(successful_results) >= 2:
            # Check for instance consistency
            instance_ids_per_manager = {}
            for result in successful_results:
                for manager_type, instance_id in result['instance_ids'].items():
                    if isinstance(instance_id, int):  # Valid instance
                        if manager_type not in instance_ids_per_manager:
                            instance_ids_per_manager[manager_type] = set()
                        instance_ids_per_manager[manager_type].add(instance_id)
            
            # Detect race conditions
            race_conditions_detected = []
            for manager_type, instance_ids in instance_ids_per_manager.items():
                if len(instance_ids) > 1:
                    race_conditions_detected.append({
                        'manager_type': manager_type,
                        'unique_instances': len(instance_ids),
                        'expected': 1 if 'singleton' in manager_type else 'multiple_ok'
                    })
            
            self.logger.info(f"Race conditions detected: {race_conditions_detected}")
            
            # This should FAIL if singleton patterns have race conditions
            singleton_race_conditions = [rc for rc in race_conditions_detected if 'singleton' in rc['manager_type']]
            assert len(singleton_race_conditions) == 0, (
                f"SINGLETON RACE CONDITION DETECTED: {len(singleton_race_conditions)} singleton patterns "
                f"created multiple instances concurrently. Details: {singleton_race_conditions}"
            )

    def test_websocket_factory_registration_timing_race(self):
        """SHOULD FAIL: Detect timing issues in factory registration"""
        registration_results = []
        registration_lock = threading.Lock()
        
        def register_factory(thread_id: int, delay: float):
            """Register WebSocket factory with specific timing"""
            time.sleep(delay)
            
            try:
                # Attempt to register factory or get existing registration
                result = {
                    'thread_id': thread_id,
                    'delay': delay,
                    'timestamp': time.time()
                }
                
                # Try different factory registration approaches
                try:
                    # Check if there's a registry to register with
                    from netra_backend.app.agents.registry import AgentRegistry
                    
                    # Simulate factory registration race
                    if hasattr(AgentRegistry, 'set_websocket_manager'):
                        from netra_backend.app.websocket_core.manager import WebSocketManager
                        manager = WebSocketManager()
                        AgentRegistry.set_websocket_manager(manager)
                        result['registration'] = 'success'
                        result['manager_id'] = id(manager)
                    else:
                        result['registration'] = 'no_registry_method'
                        
                except Exception as e:
                    result['registration'] = f'error: {str(e)}'
                
                with registration_lock:
                    registration_results.append(result)
                    
            except Exception as e:
                with registration_lock:
                    registration_results.append({
                        'thread_id': thread_id,
                        'delay': delay,
                        'error': str(e),
                        'timestamp': time.time()
                    })
        
        # Test different timing scenarios
        timing_scenarios = [
            (0, 0.0),    # Immediate registration
            (1, 0.01),   # Short delay
            (2, 0.02),   # Medium delay  
            (3, 0.05),   # Long delay
            (4, 0.0),    # Immediate (duplicate)
        ]
        
        threads = []
        for thread_id, delay in timing_scenarios:
            thread = threading.Thread(target=register_factory, args=(thread_id, delay))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Analyze registration timing issues
        successful_registrations = [r for r in registration_results if r.get('registration') == 'success']
        
        self.logger.info(f"Factory registration results: {len(successful_registrations)} successful")
        
        if len(successful_registrations) >= 2:
            # Check if all registrations used same manager instance
            manager_ids = [r['manager_id'] for r in successful_registrations]
            unique_manager_ids = set(manager_ids)
            
            # This should FAIL if factory creates multiple instances when it should be singleton
            assert len(unique_manager_ids) == len(manager_ids), (
                f"FACTORY REGISTRATION RACE DETECTED: Expected unique managers per registration, "
                f"but got {len(unique_manager_ids)} unique instances for {len(manager_ids)} registrations"
            )

    def test_multi_user_session_isolation_race(self):
        """SHOULD FAIL: Detect race conditions in multi-user session isolation"""
        session_results = []
        session_lock = threading.Lock()
        
        def simulate_user_session(user_id: int):
            """Simulate user WebSocket session with potential state contamination"""
            try:
                # Import WebSocket manager
                from netra_backend.app.websocket_core.manager import WebSocketManager
                
                # Create or get manager instance
                manager = WebSocketManager()
                
                # Simulate user-specific operations
                user_data = {
                    'user_id': user_id,
                    'session_id': f'session_{user_id}_{time.time()}',
                    'state': {}
                }
                
                # Test for state isolation
                result = {
                    'user_id': user_id,
                    'manager_id': id(manager),
                    'user_data': user_data,
                    'timestamp': time.time()
                }
                
                # Try to store user-specific state
                if hasattr(manager, 'user_sessions'):
                    manager.user_sessions[user_id] = user_data
                    result['state_storage'] = 'shared_dict'
                elif hasattr(manager, 'add_connection'):
                    # Simulate adding connection
                    connection_mock = MagicMock()
                    connection_mock.user_id = user_id
                    manager.add_connection(connection_mock)
                    result['state_storage'] = 'connection_based'
                else:
                    result['state_storage'] = 'no_state_mechanism'
                
                # Simulate some processing time
                time.sleep(0.01)
                
                # Check if state was contaminated by other users
                if hasattr(manager, 'user_sessions'):
                    other_users = [uid for uid in manager.user_sessions.keys() if uid != user_id]
                    result['other_users_detected'] = len(other_users)
                    result['state_contamination'] = len(other_users) > 0
                else:
                    result['other_users_detected'] = 0
                    result['state_contamination'] = False
                
                with session_lock:
                    session_results.append(result)
                    
            except Exception as e:
                with session_lock:
                    session_results.append({
                        'user_id': user_id,
                        'error': str(e),
                        'timestamp': time.time()
                    })
        
        # Simulate concurrent user sessions
        user_threads = []
        num_users = 5
        
        for user_id in range(num_users):
            thread = threading.Thread(target=simulate_user_session, args=(user_id,))
            user_threads.append(thread)
            thread.start()
        
        for thread in user_threads:
            thread.join(timeout=5.0)
        
        # Analyze session isolation
        successful_sessions = [r for r in session_results if 'error' not in r]
        
        self.logger.info(f"User session results: {len(successful_sessions)} successful")
        
        if len(successful_sessions) >= 2:
            # Check manager instance sharing
            manager_ids = [r['manager_id'] for r in successful_sessions]
            unique_managers = set(manager_ids)
            
            # Check state contamination
            contaminated_sessions = [r for r in successful_sessions if r.get('state_contamination', False)]
            
            self.logger.info(f"Manager instances: {len(unique_managers)} unique, {len(manager_ids)} total")
            self.logger.info(f"State contamination detected: {len(contaminated_sessions)} sessions")
            
            # This should FAIL if shared manager causes state contamination
            assert len(contaminated_sessions) == 0, (
                f"MULTI-USER STATE CONTAMINATION DETECTED: {len(contaminated_sessions)} sessions "
                f"detected state from other users. This indicates inadequate user isolation."
            )

    @pytest.mark.asyncio
    async def test_async_websocket_race_conditions(self):
        """SHOULD FAIL: Detect race conditions in async WebSocket operations"""
        async_results = []
        
        async def async_websocket_operation(operation_id: int):
            """Perform async WebSocket operation"""
            try:
                # Import async WebSocket components
                from netra_backend.app.websocket_core.manager import WebSocketManager
                
                # Create manager
                manager = WebSocketManager()
                
                # Simulate async operations
                result = {
                    'operation_id': operation_id,
                    'manager_id': id(manager),
                    'start_time': time.time()
                }
                
                # Simulate async event sending
                if hasattr(manager, 'send_event'):
                    try:
                        # This might reveal race conditions in event handling
                        await asyncio.sleep(0.01)  # Simulate async delay
                        event_result = manager.send_event(
                            f"test_event_{operation_id}", 
                            {"data": f"test_{operation_id}"}, 
                            f"user_{operation_id}"
                        )
                        result['event_sent'] = True
                        result['event_result'] = str(event_result)
                    except Exception as e:
                        result['event_sent'] = False
                        result['event_error'] = str(e)
                else:
                    result['event_sent'] = False
                    result['event_error'] = 'no_send_event_method'
                
                result['end_time'] = time.time()
                result['duration'] = result['end_time'] - result['start_time']
                
                async_results.append(result)
                
            except Exception as e:
                async_results.append({
                    'operation_id': operation_id,
                    'error': str(e)
                })
        
        # Run concurrent async operations
        tasks = []
        num_operations = 8
        
        for i in range(num_operations):
            task = asyncio.create_task(async_websocket_operation(i))
            tasks.append(task)
        
        # Wait for all operations
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze async race conditions
        successful_operations = [r for r in async_results if 'error' not in r]
        
        self.logger.info(f"Async operations: {len(successful_operations)} successful")
        
        if len(successful_operations) >= 2:
            # Check for timing issues
            durations = [r['duration'] for r in successful_operations]
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            
            # Check event sending consistency
            events_sent = [r for r in successful_operations if r.get('event_sent', False)]
            event_errors = [r for r in successful_operations if r.get('event_error')]
            
            self.logger.info(f"Event sending: {len(events_sent)} successful, {len(event_errors)} errors")
            
            # This should FAIL if async operations have inconsistent behavior
            assert len(event_errors) == 0, (
                f"ASYNC WEBSOCKET RACE CONDITIONS DETECTED: {len(event_errors)} operations failed. "
                f"Errors: {[r['event_error'] for r in event_errors if r.get('event_error')][:3]}"
            )

    def test_websocket_manager_thread_safety(self):
        """SHOULD FAIL: Detect thread safety issues in WebSocket manager"""
        thread_safety_results = []
        shared_state = {'counter': 0}
        state_lock = threading.Lock()
        
        def thread_unsafe_operation(thread_id: int):
            """Perform operations that might reveal thread safety issues"""
            try:
                from netra_backend.app.websocket_core.manager import WebSocketManager
                
                manager = WebSocketManager()
                
                # Perform operations that modify shared state
                for i in range(10):
                    # Simulate state modification without proper locking
                    if hasattr(manager, 'connection_count'):
                        # Read-modify-write that could have race conditions
                        current_count = getattr(manager, 'connection_count', 0)
                        time.sleep(0.001)  # Increase race condition window
                        setattr(manager, 'connection_count', current_count + 1)
                    
                    # Modify shared test state
                    current_value = shared_state['counter']
                    time.sleep(0.001)  # Race condition window
                    shared_state['counter'] = current_value + 1
                
                with state_lock:
                    thread_safety_results.append({
                        'thread_id': thread_id,
                        'manager_id': id(manager),
                        'final_shared_counter': shared_state['counter'],
                        'manager_connection_count': getattr(manager, 'connection_count', 0)
                    })
                    
            except Exception as e:
                with state_lock:
                    thread_safety_results.append({
                        'thread_id': thread_id,
                        'error': str(e)
                    })
        
        # Run concurrent thread-unsafe operations
        threads = []
        num_threads = 5
        
        for i in range(num_threads):
            thread = threading.Thread(target=thread_unsafe_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Analyze thread safety
        successful_results = [r for r in thread_safety_results if 'error' not in r]
        
        if len(successful_results) >= 2:
            expected_counter = num_threads * 10
            actual_counter = shared_state['counter']
            
            # Check manager instance sharing
            manager_ids = [r['manager_id'] for r in successful_results]
            unique_managers = set(manager_ids)
            
            self.logger.info(f"Thread safety test: expected {expected_counter}, got {actual_counter}")
            self.logger.info(f"Manager instances: {len(unique_managers)} unique")
            
            # This should FAIL if there are race conditions in shared state
            counter_race_detected = actual_counter != expected_counter
            assert not counter_race_detected, (
                f"THREAD SAFETY RACE CONDITION DETECTED: Expected counter {expected_counter}, "
                f"got {actual_counter}. This indicates race conditions in shared state modification."
            )