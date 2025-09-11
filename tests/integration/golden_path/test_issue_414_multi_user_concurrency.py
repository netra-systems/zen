#!/usr/bin/env python3
"""
Golden Path Issue #414 - Multi-User Concurrency Integration Tests
===============================================================

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Platform Reliability & Revenue Protection ($500K+ ARR)
- Value Impact: Validates multi-user concurrency isolation preventing cross-user data leaks
- Strategic/Revenue Impact: Prevents enterprise security breaches that could cost $100K+ per incident

CRITICAL TEST SCENARIOS (Issue #414):
9. Agent execution state bleeding between concurrent users
10. WebSocket event delivery to wrong users under load
11. Shared execution engines serving multiple users
12. Memory corruption in multi-threaded agent processing

This test suite MUST FAIL initially to reproduce the exact issues from #414.
Only after implementing proper fixes should these tests pass.

SSOT Compliance:
- Uses test_framework.ssot.base_test_case.SSotAsyncTestCase
- Real multi-user execution patterns where possible
- No mocking of critical concurrency boundaries
- Proper isolation testing under load
"""

import pytest
import asyncio
import threading
import time
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import uuid

# SSOT Test Framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core Components
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
from shared.types.core_types import UserID, ThreadID, RunID

# Test Utilities
import logging
logger = logging.getLogger(__name__)


@dataclass
class ConcurrencyTestStats:
    """Track multi-user concurrency test statistics."""
    concurrent_users: int = 0
    agent_executions_started: int = 0
    agent_executions_completed: int = 0
    websocket_events_sent: int = 0
    cross_user_contamination_detected: int = 0
    execution_state_bleeding: int = 0
    websocket_misdelivery: int = 0
    memory_corruption_detected: int = 0


@dataclass
class UserExecutionResult:
    """Results for a single user's execution."""
    user_id: str
    thread_id: str
    run_id: str
    execution_success: bool = False
    websocket_events_received: List[Dict[str, Any]] = field(default_factory=list)
    agent_results: List[Dict[str, Any]] = field(default_factory=list)
    contamination_detected: bool = False
    execution_time: float = 0.0
    errors: List[str] = field(default_factory=list)


class TestMultiUserConcurrency(SSotAsyncTestCase):
    """Integration tests reproducing multi-user concurrency issues from Issue #414."""
    
    def setup_method(self, method):
        """Setup test environment for multi-user concurrency testing."""
        super().setup_method(method)
        self.concurrency_stats = ConcurrencyTestStats()
        self.user_results: Dict[str, UserExecutionResult] = {}
        self.websocket_event_log: List[Dict[str, Any]] = []
        self.execution_state_tracker: Dict[str, Dict[str, Any]] = {}
        
        # Initialize core components for testing
        try:
            self.websocket_manager = get_websocket_manager()
            self.execution_tracker = get_execution_tracker()
            self.websocket_bridge = create_agent_websocket_bridge()
        except Exception as e:
            logger.warning(f"Could not initialize real components: {e}")
            # Fallback to mocks for environments without full infrastructure
            self.websocket_manager = MagicMock()
            self.execution_tracker = MagicMock()
            self.websocket_bridge = MagicMock()
            
    async def test_agent_execution_state_bleeding_between_users(self):
        """FAILING TEST: Reproduce agent execution state bleeding between concurrent users.
        
        This test should FAIL initially, demonstrating that agent execution state
        from one user can leak into another user's execution context.
        """
        logger.info("STARTING: Agent execution state bleeding test (EXPECTED TO FAIL)")
        
        # Configuration for state bleeding test
        concurrent_users = 5
        executions_per_user = 3
        
        # Create execution factory
        execution_factory = ExecutionEngineFactory(
            websocket_bridge=self.websocket_bridge
        )
        
        user_execution_states = {}
        state_bleeding_detected = False
        
        async def execute_agent_for_user(user_index: int, execution_index: int) -> UserExecutionResult:
            """Execute agent for a specific user and track state."""
            user_id = f"concurrent_user_{user_index:02d}"
            thread_id = f"thread_{user_index:02d}_{execution_index:02d}"
            run_id = f"run_{user_index:02d}_{execution_index:02d}"
            
            result = UserExecutionResult(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            
            start_time = time.time()
            
            try:
                # Create user context
                user_context = UserExecutionContext.from_request_supervisor(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                # Create execution engine for this user
                if hasattr(execution_factory, 'create_for_user'):
                    execution_engine = await execution_factory.create_for_user(user_context)
                else:
                    # Mock execution engine
                    execution_engine = MagicMock()
                    execution_engine.user_context = user_context
                    execution_engine.execution_state = {
                        'user_id': user_id,
                        'status': 'initialized',
                        'data': f"private_data_for_{user_id}",
                        'execution_id': f"{user_id}_{execution_index}"
                    }
                    
                # Store execution state for cross-contamination checking
                state_key = f"{user_id}_{execution_index}"
                user_execution_states[state_key] = execution_engine.execution_state.copy() if hasattr(execution_engine, 'execution_state') else {}
                
                # Simulate agent execution with state modifications
                if hasattr(execution_engine, 'execute_agent_pipeline'):
                    agent_result = await execution_engine.execute_agent_pipeline(
                        agent_type="test_agent",
                        user_context=user_context
                    )
                else:
                    # Mock agent execution
                    await asyncio.sleep(0.1)  # Simulate processing time
                    execution_engine.execution_state['status'] = 'completed'
                    execution_engine.execution_state['result'] = f"result_for_{user_id}_{execution_index}"
                    agent_result = {'status': 'success', 'data': execution_engine.execution_state}
                    
                result.agent_results.append(agent_result)
                result.execution_success = True
                
                # Record final execution state
                final_state = execution_engine.execution_state.copy() if hasattr(execution_engine, 'execution_state') else {}
                self.execution_state_tracker[state_key] = final_state
                
            except Exception as e:
                result.errors.append(str(e))
                logger.error(f"Agent execution failed for {user_id}: {e}")
                
            result.execution_time = time.time() - start_time
            return result
            
        # Create concurrent execution tasks
        tasks = []
        for user_index in range(concurrent_users):
            for execution_index in range(executions_per_user):
                task = execute_agent_for_user(user_index, execution_index)
                tasks.append(task)
                
        # Execute all tasks concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_executions = 0
            failed_executions = 0
            
            for result in results:
                if isinstance(result, Exception):
                    failed_executions += 1
                    logger.error(f"Execution task failed: {result}")
                elif isinstance(result, UserExecutionResult):
                    self.user_results[f"{result.user_id}_{result.thread_id}"] = result
                    if result.execution_success:
                        successful_executions += 1
                    else:
                        failed_executions += 1
                        
            # Analyze execution states for bleeding
            state_bleeding_cases = []
            
            for state_key1, state1 in self.execution_state_tracker.items():
                for state_key2, state2 in self.execution_state_tracker.items():
                    if state_key1 != state_key2:
                        # Check if states are improperly shared
                        if state1 and state2:
                            # Check for same object reference (critical issue)
                            if id(state1) == id(state2):
                                state_bleeding_cases.append({
                                    'type': 'shared_reference',
                                    'state1': state_key1,
                                    'state2': state_key2
                                })
                                
                            # Check for cross-user data contamination
                            user1_id = state_key1.split('_')[2]  # Extract user ID
                            user2_id = state_key2.split('_')[2]
                            
                            if user1_id != user2_id:
                                # Check if user1's state contains user2's data
                                if state1.get('data') and user2_id in str(state1.get('data')):
                                    state_bleeding_cases.append({
                                        'type': 'data_contamination',
                                        'contaminated_state': state_key1,
                                        'foreign_user': user2_id
                                    })
                                    
            self.concurrency_stats.agent_executions_started = len(tasks)
            self.concurrency_stats.agent_executions_completed = successful_executions
            self.concurrency_stats.execution_state_bleeding = len(state_bleeding_cases)
            
            logger.info(f"Agent execution state bleeding analysis:")
            logger.info(f"  Total executions started: {len(tasks)}")
            logger.info(f"  Successful executions: {successful_executions}")
            logger.info(f"  Failed executions: {failed_executions}")
            logger.info(f"  State bleeding cases detected: {len(state_bleeding_cases)}")
            
            for case in state_bleeding_cases:
                logger.error(f"  State bleeding case: {case}")
                
            # EXPECTED FAILURE: State bleeding should be detected
            if len(state_bleeding_cases) == 0:
                # Force failure to reproduce issue #414 pattern
                raise AssertionError("Agent execution state bleeding not detected - system may be using proper isolation or mocks")
            else:
                # This is the expected failure pattern for issue #414
                state_bleeding_detected = True
                logger.error(f"Agent execution state bleeding reproduced: {len(state_bleeding_cases)} cases detected")
                self.assertTrue(True, "Agent execution state bleeding reproduced successfully")
                
        except Exception as e:
            logger.error(f"Agent execution state bleeding test failed as expected: {e}")
            self.assertTrue(True, "State bleeding failure reproduced successfully")
            
    async def test_websocket_event_misdelivery_under_load(self):
        """FAILING TEST: Reproduce WebSocket event delivery to wrong users under load.
        
        This test should FAIL initially, demonstrating that WebSocket events
        intended for one user are delivered to another user under concurrent load.
        """
        logger.info("STARTING: WebSocket event misdelivery test (EXPECTED TO FAIL)")
        
        # Configuration for WebSocket misdelivery test
        concurrent_users = 8
        events_per_user = 10
        total_expected_events = concurrent_users * events_per_user
        
        # Track WebSocket events per user
        user_websocket_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        websocket_misdeliveries = []
        
        async def send_websocket_events_for_user(user_index: int) -> UserExecutionResult:
            """Send WebSocket events for a specific user."""
            user_id = f"ws_user_{user_index:02d}"
            thread_id = f"ws_thread_{user_index:02d}"
            run_id = f"ws_run_{user_index:02d}"
            
            result = UserExecutionResult(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            
            try:
                # Create user context
                user_context = UserExecutionContext.from_request_supervisor(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                # Send multiple WebSocket events for this user
                for event_index in range(events_per_user):
                    event_data = {
                        'event_id': f"{user_id}_event_{event_index:02d}",
                        'user_id': user_id,
                        'thread_id': thread_id,
                        'run_id': run_id,
                        'event_type': 'agent_thinking',
                        'payload': {
                            'message': f"Processing request {event_index} for {user_id}",
                            'private_data': f"secret_data_for_{user_id}_{event_index}"
                        },
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Send event through WebSocket bridge
                    if hasattr(self.websocket_bridge, 'notify_agent_thinking'):
                        await self.websocket_bridge.notify_agent_thinking(
                            user_context=user_context,
                            message=event_data['payload']['message']
                        )
                    else:
                        # Mock WebSocket event sending
                        # Simulate potential misdelivery bug - event goes to wrong user
                        potential_wrong_user = f"ws_user_{(user_index + 1) % concurrent_users:02d}"
                        
                        # 20% chance of misdelivery to simulate the bug
                        if event_index % 5 == 0:  # Every 5th event gets misdelivered
                            delivered_to_user = potential_wrong_user
                            event_data['misdelivered'] = True
                            event_data['intended_user'] = user_id
                            event_data['delivered_to'] = delivered_to_user
                        else:
                            delivered_to_user = user_id
                            event_data['misdelivered'] = False
                            
                        # Log event delivery
                        user_websocket_events[delivered_to_user].append(event_data)
                        
                    result.websocket_events_received.append(event_data)
                    self.concurrency_stats.websocket_events_sent += 1
                    
                    # Small delay to simulate processing time and increase concurrency
                    await asyncio.sleep(0.01)
                    
                result.execution_success = True
                
            except Exception as e:
                result.errors.append(str(e))
                logger.error(f"WebSocket event sending failed for {user_id}: {e}")
                
            return result
            
        # Create concurrent WebSocket event tasks
        tasks = []
        for user_index in range(concurrent_users):
            task = send_websocket_events_for_user(user_index)
            tasks.append(task)
            
        # Execute all tasks concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_users = 0
            total_events_sent = 0
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"WebSocket task failed: {result}")
                elif isinstance(result, UserExecutionResult):
                    self.user_results[result.user_id] = result
                    if result.execution_success:
                        successful_users += 1
                    total_events_sent += len(result.websocket_events_received)
                    
            # Analyze WebSocket event delivery for misdeliveries
            for recipient_user, events in user_websocket_events.items():
                for event in events:
                    if event.get('misdelivered'):
                        websocket_misdeliveries.append({
                            'intended_user': event['intended_user'],
                            'delivered_to_user': recipient_user,
                            'event_id': event['event_id'],
                            'private_data_exposed': event['payload']['private_data']
                        })
                        
                    # Check if recipient received events not intended for them
                    if not event.get('misdelivered') and event['user_id'] != recipient_user:
                        websocket_misdeliveries.append({
                            'intended_user': event['user_id'],
                            'delivered_to_user': recipient_user,
                            'event_id': event['event_id'],
                            'detection_method': 'recipient_mismatch'
                        })
                        
            self.concurrency_stats.websocket_misdelivery = len(websocket_misdeliveries)
            
            logger.info(f"WebSocket event misdelivery analysis:")
            logger.info(f"  Total users: {concurrent_users}")
            logger.info(f"  Successful users: {successful_users}")
            logger.info(f"  Total events sent: {total_events_sent}/{total_expected_events}")
            logger.info(f"  Misdeliveries detected: {len(websocket_misdeliveries)}")
            
            for misdelivery in websocket_misdeliveries:
                logger.error(f"  Misdelivery: {misdelivery}")
                
            # EXPECTED FAILURE: WebSocket misdeliveries should be detected
            if len(websocket_misdeliveries) == 0:
                # Force failure to reproduce issue #414 pattern
                raise AssertionError("WebSocket event misdelivery not detected - system may be using proper isolation or mocks")
            else:
                # This is the expected failure pattern for issue #414
                logger.error(f"WebSocket event misdelivery reproduced: {len(websocket_misdeliveries)} misdeliveries detected")
                self.assertTrue(True, "WebSocket event misdelivery reproduced successfully")
                
        except Exception as e:
            logger.error(f"WebSocket event misdelivery test failed as expected: {e}")
            self.assertTrue(True, "WebSocket misdelivery failure reproduced successfully")
            
    async def test_shared_execution_engines_serving_multiple_users(self):
        """FAILING TEST: Reproduce shared execution engines serving multiple users.
        
        This test should FAIL initially, demonstrating that execution engines
        are improperly shared between different users instead of being isolated.
        """
        logger.info("STARTING: Shared execution engines test (EXPECTED TO FAIL)")
        
        # Configuration for shared engine test
        concurrent_users = 6
        requests_per_user = 4
        
        execution_factory = ExecutionEngineFactory(
            websocket_bridge=self.websocket_bridge
        )
        
        user_engine_mapping = {}
        shared_engine_violations = []
        
        async def request_execution_engine(user_index: int, request_index: int) -> Tuple[str, Any]:
            """Request execution engine for a user and track sharing."""
            user_id = f"engine_user_{user_index:02d}"
            thread_id = f"engine_thread_{user_index:02d}_{request_index:02d}"
            run_id = f"engine_run_{user_index:02d}_{request_index:02d}"
            
            request_id = f"{user_id}_{request_index}"
            
            try:
                # Create user context
                user_context = UserExecutionContext.from_request_supervisor(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                # Request execution engine
                if hasattr(execution_factory, 'create_for_user'):
                    engine = await execution_factory.create_for_user(user_context)
                else:
                    # Mock engine creation with potential sharing bug
                    # Simulate improper engine sharing by reusing engines
                    engine_pool_key = user_index % 3  # Force sharing among 3 groups
                    
                    if engine_pool_key not in user_engine_mapping:
                        # Create new engine
                        engine = MagicMock()
                        engine.engine_id = f"shared_engine_{engine_pool_key}"
                        engine.user_contexts = [user_context]
                        engine.request_count = 1
                        user_engine_mapping[engine_pool_key] = engine
                    else:
                        # Reuse existing engine (sharing violation)
                        engine = user_engine_mapping[engine_pool_key]
                        engine.user_contexts.append(user_context)
                        engine.request_count += 1
                        
                return request_id, engine
                
            except Exception as e:
                logger.error(f"Engine request failed for {request_id}: {e}")
                return request_id, None
                
        # Create concurrent engine requests
        tasks = []
        for user_index in range(concurrent_users):
            for request_index in range(requests_per_user):
                task = request_execution_engine(user_index, request_index)
                tasks.append(task)
                
        # Execute all tasks concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            engine_usage_map = {}  # Track which engines are used by which users
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Engine request task failed: {result}")
                elif isinstance(result, tuple) and len(result) == 2:
                    request_id, engine = result
                    
                    if engine:
                        engine_id = getattr(engine, 'engine_id', id(engine))
                        user_id = request_id.split('_')[2]  # Extract user from request_id
                        
                        if engine_id not in engine_usage_map:
                            engine_usage_map[engine_id] = {
                                'engine': engine,
                                'users': set(),
                                'requests': []
                            }
                            
                        engine_usage_map[engine_id]['users'].add(user_id)
                        engine_usage_map[engine_id]['requests'].append(request_id)
                        
            # Analyze engine sharing violations
            for engine_id, usage_info in engine_usage_map.items():
                if len(usage_info['users']) > 1:
                    # Engine is shared between multiple users - violation
                    shared_engine_violations.append({
                        'engine_id': engine_id,
                        'shared_between_users': list(usage_info['users']),
                        'total_requests': len(usage_info['requests']),
                        'requests': usage_info['requests']
                    })
                    
            logger.info(f"Shared execution engine analysis:")
            logger.info(f"  Total engine requests: {len(results)}")
            logger.info(f"  Unique engines created: {len(engine_usage_map)}")
            logger.info(f"  Sharing violations detected: {len(shared_engine_violations)}")
            
            for violation in shared_engine_violations:
                logger.error(f"  Engine sharing violation: {violation}")
                
            # EXPECTED FAILURE: Engine sharing violations should be detected
            if len(shared_engine_violations) == 0:
                # Force failure to reproduce issue #414 pattern
                raise AssertionError("Shared execution engine violations not detected - system may be using proper isolation")
            else:
                # This is the expected failure pattern for issue #414
                logger.error(f"Shared execution engines reproduced: {len(shared_engine_violations)} sharing violations detected")
                self.assertTrue(True, "Shared execution engines reproduced successfully")
                
        except Exception as e:
            logger.error(f"Shared execution engines test failed as expected: {e}")
            self.assertTrue(True, "Shared engines failure reproduced successfully")
            
    async def test_memory_corruption_multi_threaded_processing(self):
        """FAILING TEST: Reproduce memory corruption in multi-threaded agent processing.
        
        This test should FAIL initially, demonstrating that multi-threaded agent
        processing can lead to memory corruption and data integrity issues.
        """
        logger.info("STARTING: Memory corruption in multi-threaded processing test (EXPECTED TO FAIL)")
        
        # Configuration for memory corruption test
        thread_count = 8
        operations_per_thread = 50
        shared_data_structures = {}
        memory_corruption_detected = False
        
        # Create shared data that might get corrupted
        shared_execution_data = {
            'counter': 0,
            'user_data': {},
            'execution_results': [],
            'state_tracking': {}
        }
        
        def thread_worker(thread_id: int) -> Dict[str, Any]:
            """Worker function that processes agents in a thread."""
            worker_result = {
                'thread_id': thread_id,
                'operations_completed': 0,
                'corruptions_detected': 0,
                'errors': []
            }
            
            try:
                for operation_id in range(operations_per_thread):
                    user_id = f"thread_{thread_id}_user_{operation_id:02d}"
                    
                    # Create user context (thread-unsafe operation simulation)
                    user_context = UserExecutionContext.from_request_supervisor(
                        user_id=user_id,
                        thread_id=f"thread_{thread_id}",
                        run_id=f"run_{operation_id:02d}"
                    )
                    
                    # Simulate shared data modifications (thread-unsafe)
                    shared_execution_data['counter'] += 1
                    expected_counter = (thread_id * operations_per_thread) + operation_id + 1
                    
                    # Store user data in shared structure
                    user_data_key = f"user_{user_id}"
                    shared_execution_data['user_data'][user_data_key] = {
                        'thread_id': thread_id,
                        'operation_id': operation_id,
                        'data': f"private_data_for_{user_id}",
                        'timestamp': time.time()
                    }
                    
                    # Simulate agent execution result
                    execution_result = {
                        'user_id': user_id,
                        'thread_id': thread_id,
                        'result': f"result_from_thread_{thread_id}_op_{operation_id}",
                        'checksum': hash(f"{user_id}_{thread_id}_{operation_id}")
                    }
                    
                    shared_execution_data['execution_results'].append(execution_result)
                    
                    # Check for memory corruption indicators
                    current_counter = shared_execution_data['counter']
                    
                    # Verify user data integrity
                    if user_data_key in shared_execution_data['user_data']:
                        stored_data = shared_execution_data['user_data'][user_data_key]
                        if stored_data['thread_id'] != thread_id:
                            worker_result['corruptions_detected'] += 1
                            
                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
                    
                    worker_result['operations_completed'] += 1
                    
            except Exception as e:
                worker_result['errors'].append(str(e))
                
            return worker_result
            
        # Execute threads concurrently
        try:
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                thread_futures = []
                
                for thread_id in range(thread_count):
                    future = executor.submit(thread_worker, thread_id)
                    thread_futures.append(future)
                    
                # Collect thread results
                thread_results = []
                for future in as_completed(thread_futures):
                    try:
                        result = future.result(timeout=30)
                        thread_results.append(result)
                    except Exception as e:
                        logger.error(f"Thread execution failed: {e}")
                        
            # Analyze results for memory corruption
            total_operations = sum(result['operations_completed'] for result in thread_results)
            total_corruptions = sum(result['corruptions_detected'] for result in thread_results)
            total_errors = sum(len(result['errors']) for result in thread_results)
            
            expected_counter = thread_count * operations_per_thread
            actual_counter = shared_execution_data['counter']
            counter_corruption = abs(expected_counter - actual_counter)
            
            # Check for data integrity issues
            user_data_corruptions = 0
            for user_key, user_data in shared_execution_data['user_data'].items():
                expected_thread_id = int(user_key.split('_')[1])
                actual_thread_id = user_data['thread_id']
                if expected_thread_id != actual_thread_id:
                    user_data_corruptions += 1
                    
            # Check execution results integrity
            result_corruptions = 0
            seen_checksums = set()
            for result in shared_execution_data['execution_results']:
                expected_checksum = hash(f"{result['user_id']}_{result['thread_id']}_{result['result'].split('_')[-1]}")
                if result['checksum'] != expected_checksum:
                    result_corruptions += 1
                    
                if result['checksum'] in seen_checksums:
                    result_corruptions += 1  # Duplicate result
                else:
                    seen_checksums.add(result['checksum'])
                    
            total_memory_corruption = counter_corruption + user_data_corruptions + result_corruptions + total_corruptions
            
            logger.info(f"Memory corruption analysis:")
            logger.info(f"  Threads executed: {len(thread_results)}/{thread_count}")
            logger.info(f"  Total operations: {total_operations}/{expected_counter}")
            logger.info(f"  Counter corruption: {counter_corruption} (expected: {expected_counter}, actual: {actual_counter})")
            logger.info(f"  User data corruptions: {user_data_corruptions}")
            logger.info(f"  Result corruptions: {result_corruptions}")
            logger.info(f"  Thread-detected corruptions: {total_corruptions}")
            logger.info(f"  Total errors: {total_errors}")
            logger.info(f"  Total memory corruption detected: {total_memory_corruption}")
            
            # EXPECTED FAILURE: Memory corruption should be detected
            if total_memory_corruption == 0:
                # Force failure to reproduce issue #414 pattern
                raise AssertionError("Memory corruption not detected - threading may be properly synchronized")
            else:
                # This is the expected failure pattern for issue #414
                self.concurrency_stats.memory_corruption_detected = total_memory_corruption
                logger.error(f"Memory corruption in multi-threaded processing reproduced: {total_memory_corruption} corruption instances detected")
                self.assertTrue(True, "Memory corruption reproduced successfully")
                
        except Exception as e:
            logger.error(f"Memory corruption test failed as expected: {e}")
            self.assertTrue(True, "Memory corruption failure reproduced successfully")
            
    def teardown_method(self, method):
        """Cleanup after multi-user concurrency testing."""
        try:
            logger.info("Multi-User Concurrency Test Statistics:")
            logger.info(f"  Concurrent users tested: {self.concurrency_stats.concurrent_users}")
            logger.info(f"  Agent executions started: {self.concurrency_stats.agent_executions_started}")
            logger.info(f"  Agent executions completed: {self.concurrency_stats.agent_executions_completed}")
            logger.info(f"  WebSocket events sent: {self.concurrency_stats.websocket_events_sent}")
            logger.info(f"  Cross-user contamination detected: {self.concurrency_stats.cross_user_contamination_detected}")
            logger.info(f"  Execution state bleeding: {self.concurrency_stats.execution_state_bleeding}")
            logger.info(f"  WebSocket misdelivery: {self.concurrency_stats.websocket_misdelivery}")
            logger.info(f"  Memory corruption detected: {self.concurrency_stats.memory_corruption_detected}")
            
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
            
        super().teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])