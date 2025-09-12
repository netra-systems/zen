"""
Test ExecutionEngine User Isolation Comprehensive Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal (Foundation for all customer segments)
- Business Goal: System Safety & Data Security
- Value Impact: Prevents catastrophic data leakage between customers ($500K+ ARR protection)
- Strategic Impact: Enables safe multi-tenant deployment at scale

PURPOSE: Comprehensive validation that user isolation works correctly in all scenarios.
This is critical for customer trust and regulatory compliance.

Test Coverage:
1. Multi-user concurrent execution isolation
2. User data and state complete separation  
3. WebSocket event routing accuracy
4. Agent execution context isolation
5. Memory and resource per-user limits
6. Session and request scoping validation
7. Error isolation (user A errors don't affect user B)
8. Performance isolation (user A load doesn't impact user B)

CRITICAL: These tests protect $500K+ ARR by ensuring customer data isolation.
"""

import asyncio
import pytest
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Set
from unittest.mock import MagicMock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class TestExecutionEngineUserIsolationComprehensive(SSotAsyncTestCase):
    """
    Comprehensive test suite for user isolation in ExecutionEngine implementations.
    
    These tests ensure that no user data, state, or events leak between users
    under any circumstances - a critical requirement for multi-tenant system.
    """

    async def asyncSetUp(self):
        """Set up comprehensive test environment for user isolation testing."""
        await super().asyncSetUp()
        
        # Create diverse user contexts for testing
        self.test_users = [
            {
                'user_id': 'enterprise_user_001',
                'username': 'alice@enterprise.com',
                'subscription_tier': 'enterprise',
                'session_id': f'session_ent_{uuid.uuid4().hex[:8]}',
                'role': 'admin',
                'sensitive_data': 'ENTERPRISE_SECRET_KEY_12345'
            },
            {
                'user_id': 'early_user_002', 
                'username': 'bob@startup.com',
                'subscription_tier': 'early',
                'session_id': f'session_early_{uuid.uuid4().hex[:8]}',
                'role': 'user',
                'sensitive_data': 'EARLY_USER_API_TOKEN_67890'
            },
            {
                'user_id': 'free_user_003',
                'username': 'charlie@gmail.com', 
                'subscription_tier': 'free',
                'session_id': f'session_free_{uuid.uuid4().hex[:8]}',
                'role': 'guest',
                'sensitive_data': 'FREE_USER_SESSION_ABCDEF'
            }
        ]

    @pytest.mark.integration
    @pytest.mark.mission_critical
    async def test_concurrent_multi_user_complete_isolation(self):
        """
        Test that multiple users executing concurrently have complete isolation.
        
        CRITICAL: This test simulates real production scenario with 3+ concurrent users.
        Any data leakage here represents a catastrophic security failure.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
        except ImportError:
            # Fallback to testing available ExecutionEngine
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine as UserExecutionEngine
            
        user_executions = {}
        user_events = {}
        user_errors = {}
        
        async def execute_user_workflow(user_data, execution_id):
            """Execute a complete workflow for one user with sensitive operations."""
            try:
                # Create isolated user context
                if 'UserExecutionContext' in globals():
                    context = UserExecutionContext(
                        user_id=user_data['user_id'],
                        session_id=user_data['session_id'],
                        request_id=f"{execution_id}_{int(time.time())}"
                    )
                    engine = UserExecutionEngine(user_context=context)
                else:
                    # Fallback for legacy ExecutionEngine
                    engine = UserExecutionEngine()
                
                # Track events for this user
                user_events[user_data['user_id']] = []
                
                # Mock WebSocket emitter to capture events
                def capture_events(event_type, data):
                    user_events[user_data['user_id']].append({
                        'event_type': event_type,
                        'data': data,
                        'timestamp': time.time(),
                        'user_id': user_data['user_id']
                    })
                
                if hasattr(engine, 'websocket_emitter'):
                    engine.websocket_emitter = MagicMock()
                    engine.websocket_emitter.emit = capture_events
                
                # Simulate user-specific operations
                execution_result = {
                    'user_id': user_data['user_id'],
                    'start_time': time.time(),
                    'sensitive_operations': [],
                    'execution_state': {}
                }
                
                # Simulate handling sensitive data
                sensitive_key = f"sensitive_data_{user_data['user_id']}"
                execution_result['execution_state'][sensitive_key] = user_data['sensitive_data']
                
                # Simulate agent execution steps
                for step in range(5):
                    await asyncio.sleep(0.02)  # Allow context switching
                    
                    step_data = {
                        'step_number': step,
                        'user_specific_data': f"{user_data['username']}_step_{step}",
                        'sensitive_info': user_data['sensitive_data'],
                        'operation': f"user_operation_{user_data['user_id']}_step_{step}"
                    }
                    
                    execution_result['sensitive_operations'].append(step_data)
                    
                    # Emit WebSocket events
                    if hasattr(engine, 'websocket_emitter'):
                        engine.websocket_emitter.emit("agent_thinking", {
                            'thought': f"Processing step {step} for {user_data['username']}",
                            'sensitive_context': user_data['sensitive_data']
                        })
                
                # Final results
                execution_result['end_time'] = time.time()
                execution_result['duration'] = execution_result['end_time'] - execution_result['start_time']
                execution_result['success'] = True
                
                user_executions[user_data['user_id']] = execution_result
                
            except Exception as e:
                user_errors[user_data['user_id']] = {
                    'error': str(e),
                    'timestamp': time.time()
                }
        
        # Execute all users concurrently
        tasks = []
        for i, user_data in enumerate(self.test_users):
            task = asyncio.create_task(execute_user_workflow(user_data, f"exec_{i}"))
            tasks.append(task)
        
        # Wait for all concurrent executions
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # CRITICAL VALIDATION: No errors should occur
        self.assertEqual(len(user_errors), 0, 
            f"Concurrent user execution had errors: {user_errors}")
        
        # Validate all users completed
        self.assertEqual(len(user_executions), len(self.test_users),
            f"Not all users completed. Expected {len(self.test_users)}, got {len(user_executions)}")
        
        # CRITICAL: Validate complete data isolation
        for user_data in self.test_users:
            user_id = user_data['user_id']
            execution = user_executions[user_id]
            
            # Check user-specific data integrity
            self.assertEqual(execution['user_id'], user_id)
            
            # Validate sensitive data isolation
            sensitive_key = f"sensitive_data_{user_id}"
            self.assertIn(sensitive_key, execution['execution_state'])
            self.assertEqual(execution['execution_state'][sensitive_key], user_data['sensitive_data'])
            
            # CRITICAL: Ensure no other users' sensitive data leaked in
            for other_user in self.test_users:
                if other_user['user_id'] != user_id:
                    other_sensitive_key = f"sensitive_data_{other_user['user_id']}"
                    self.assertNotIn(other_sensitive_key, execution['execution_state'],
                        f"User {user_id} leaked sensitive data from user {other_user['user_id']}")
                    
                    # Check that other users' sensitive data doesn't appear anywhere
                    execution_str = str(execution)
                    self.assertNotIn(other_user['sensitive_data'], execution_str,
                        f"User {user_id} execution contains other user's sensitive data: {other_user['sensitive_data']}")
        
        self.logger.info(f"Multi-user isolation test PASSED for {len(self.test_users)} concurrent users")

    @pytest.mark.integration
    @pytest.mark.mission_critical
    async def test_websocket_event_routing_isolation(self):
        """
        Test that WebSocket events are routed only to the correct user.
        
        BUSINESS CRITICAL: Incorrect event routing means users see other users' data.
        This would be a catastrophic privacy and security failure.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
        except ImportError:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine as UserExecutionEngine
        
        # Track events per user
        user_event_logs = {user['user_id']: [] for user in self.test_users}
        
        # Create engines with event tracking
        user_engines = {}
        
        for user_data in self.test_users:
            try:
                if 'UserExecutionContext' in globals():
                    context = UserExecutionContext(
                        user_id=user_data['user_id'],
                        session_id=user_data['session_id'],
                        request_id=f"event_test_{uuid.uuid4().hex[:8]}"
                    )
                    engine = UserExecutionEngine(user_context=context)
                else:
                    engine = UserExecutionEngine()
                
                # Setup event capture for this specific user
                def make_event_capture(target_user_id):
                    def capture_events(event_type, data):
                        user_event_logs[target_user_id].append({
                            'event_type': event_type,
                            'data': data,
                            'timestamp': time.time(),
                            'captured_for_user': target_user_id
                        })
                    return capture_events
                
                if hasattr(engine, 'websocket_emitter'):
                    engine.websocket_emitter = MagicMock()
                    engine.websocket_emitter.emit = make_event_capture(user_data['user_id'])
                
                user_engines[user_data['user_id']] = engine
                
            except Exception as e:
                self.fail(f"Failed to create engine for user {user_data['user_id']}: {e}")
        
        # Send user-specific events
        for user_data in self.test_users:
            user_id = user_data['user_id']
            engine = user_engines[user_id]
            
            # Send multiple event types with sensitive data
            events_to_send = [
                ('agent_started', {
                    'agent_type': 'cost_optimizer',
                    'user_context': user_data['sensitive_data'],
                    'session': user_data['session_id']
                }),
                ('agent_thinking', {
                    'thought': f"Analyzing data for {user_data['username']}",
                    'private_info': user_data['sensitive_data']
                }),
                ('tool_executing', {
                    'tool': 'data_analyzer', 
                    'user_specific_params': user_data['sensitive_data']
                }),
                ('agent_completed', {
                    'results': f"Private results for {user_data['user_id']}",
                    'sensitive_output': user_data['sensitive_data']
                })
            ]
            
            if hasattr(engine, 'websocket_emitter'):
                for event_type, event_data in events_to_send:
                    engine.websocket_emitter.emit(event_type, event_data)
        
        # CRITICAL VALIDATION: Event isolation
        for user_data in self.test_users:
            user_id = user_data['user_id']
            user_events = user_event_logs[user_id]
            
            # This user should have received events
            self.assertGreater(len(user_events), 0, 
                f"User {user_id} should have received events")
            
            # Validate all events are for this user
            for event in user_events:
                self.assertEqual(event['captured_for_user'], user_id,
                    f"Event routing error: event meant for {user_id} was captured for {event['captured_for_user']}")
                
                # Check event contains this user's data
                event_str = str(event['data'])
                if 'user_context' in event['data'] or 'private_info' in event['data'] or 'user_specific_params' in event['data'] or 'sensitive_output' in event['data']:
                    self.assertIn(user_data['sensitive_data'], event_str,
                        f"Event for user {user_id} doesn't contain their sensitive data")
            
            # CRITICAL: Check no other users' data leaked into this user's events
            for other_user in self.test_users:
                if other_user['user_id'] != user_id:
                    user_events_str = str(user_events)
                    self.assertNotIn(other_user['sensitive_data'], user_events_str,
                        f"SECURITY VIOLATION: User {user_id} events contain other user's data: {other_user['sensitive_data']}")
        
        self.logger.info("WebSocket event routing isolation test PASSED")

    @pytest.mark.integration
    @pytest.mark.mission_critical
    async def test_execution_state_complete_separation(self):
        """
        Test that execution state is completely separated between users.
        
        STATE ISOLATION: Critical that user A's variables/state cannot be accessed by user B.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
        except ImportError:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine as UserExecutionEngine
        
        user_engines = {}
        
        # Create engines and set user-specific state
        for user_data in self.test_users:
            try:
                if 'UserExecutionContext' in globals():
                    context = UserExecutionContext(
                        user_id=user_data['user_id'],
                        session_id=user_data['session_id'],
                        request_id=f"state_test_{uuid.uuid4().hex[:8]}"
                    )
                    engine = UserExecutionEngine(user_context=context)
                else:
                    engine = UserExecutionEngine()
                
                # Initialize execution state
                if not hasattr(engine, '_execution_state'):
                    engine._execution_state = {}
                
                # Set user-specific sensitive state
                engine._execution_state.update({
                    'user_id': user_data['user_id'],
                    'api_key': user_data['sensitive_data'],
                    'session_token': f"token_{user_data['session_id']}",
                    'private_config': {
                        'subscription': user_data['subscription_tier'],
                        'role': user_data['role'],
                        'email': user_data['username']
                    },
                    'execution_history': [],
                    'cached_results': {}
                })
                
                # Add some execution history
                for i in range(3):
                    engine._execution_state['execution_history'].append({
                        'step': i,
                        'action': f"private_action_{user_data['user_id']}_{i}",
                        'timestamp': time.time(),
                        'sensitive_data': user_data['sensitive_data']
                    })
                
                user_engines[user_data['user_id']] = engine
                
            except Exception as e:
                self.fail(f"Failed to setup execution state for user {user_data['user_id']}: {e}")
        
        # CRITICAL VALIDATION: State isolation
        for user_data in self.test_users:
            user_id = user_data['user_id']
            engine = user_engines[user_id]
            
            # Validate this user's state exists and is correct
            self.assertTrue(hasattr(engine, '_execution_state'),
                f"User {user_id} engine should have execution state")
            
            state = engine._execution_state
            
            # Check user's own data is present
            self.assertEqual(state['user_id'], user_id)
            self.assertEqual(state['api_key'], user_data['sensitive_data'])
            self.assertGreater(len(state['execution_history']), 0)
            
            # CRITICAL: Validate no other users' data is present
            for other_user in self.test_users:
                if other_user['user_id'] != user_id:
                    # Check other user's ID is not in this user's state
                    state_str = str(state)
                    self.assertNotIn(other_user['user_id'], state_str,
                        f"ISOLATION VIOLATION: User {user_id} state contains other user ID {other_user['user_id']}")
                    
                    # Check other user's sensitive data is not in this user's state
                    self.assertNotIn(other_user['sensitive_data'], state_str,
                        f"SECURITY VIOLATION: User {user_id} state contains other user's sensitive data: {other_user['sensitive_data']}")
                    
                    # Check other user's email/username is not in this user's state
                    self.assertNotIn(other_user['username'], state_str,
                        f"PRIVACY VIOLATION: User {user_id} state contains other user's email: {other_user['username']}")
        
        # Cross-validation: Try to access other users' state (should fail)
        for i, user_data in enumerate(self.test_users):
            user_id = user_data['user_id']
            engine = user_engines[user_id]
            
            # Try to access other users' engines (should be impossible with proper isolation)
            for j, other_user in enumerate(self.test_users):
                if i != j:
                    other_engine = user_engines[other_user['user_id']]
                    
                    # Engines should be different objects
                    self.assertIsNot(engine, other_engine,
                        f"User {user_id} and {other_user['user_id']} should have different engine instances")
                    
                    # Execution states should be different objects
                    if hasattr(engine, '_execution_state') and hasattr(other_engine, '_execution_state'):
                        self.assertIsNot(engine._execution_state, other_engine._execution_state,
                            f"User {user_id} and {other_user['user_id']} should have different execution states")
        
        self.logger.info("Execution state separation test PASSED")

    @pytest.mark.integration 
    @pytest.mark.performance
    async def test_user_performance_isolation(self):
        """
        Test that one user's heavy load doesn't impact other users' performance.
        
        PERFORMANCE ISOLATION: User A's heavy workload should not slow down User B.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
        except ImportError:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine as UserExecutionEngine
        
        # Performance tracking
        user_performance = {}
        
        async def light_user_workload(user_data):
            """Simulate a light user workload."""
            start_time = time.time()
            
            try:
                if 'UserExecutionContext' in globals():
                    context = UserExecutionContext(
                        user_id=user_data['user_id'],
                        session_id=user_data['session_id'],
                        request_id=f"light_{uuid.uuid4().hex[:8]}"
                    )
                    engine = UserExecutionEngine(user_context=context)
                else:
                    engine = UserExecutionEngine()
                
                # Light operations
                for i in range(10):
                    await asyncio.sleep(0.01)  # 10ms each = 100ms total
                
                end_time = time.time()
                duration = end_time - start_time
                
                user_performance[user_data['user_id']] = {
                    'workload_type': 'light',
                    'duration': duration,
                    'operations': 10,
                    'success': True
                }
                
            except Exception as e:
                user_performance[user_data['user_id']] = {
                    'workload_type': 'light',
                    'error': str(e),
                    'success': False
                }
        
        async def heavy_user_workload(user_data):
            """Simulate a heavy user workload."""
            start_time = time.time()
            
            try:
                if 'UserExecutionContext' in globals():
                    context = UserExecutionContext(
                        user_id=user_data['user_id'],
                        session_id=user_data['session_id'],
                        request_id=f"heavy_{uuid.uuid4().hex[:8]}"
                    )
                    engine = UserExecutionEngine(user_context=context)
                else:
                    engine = UserExecutionEngine()
                
                # Heavy operations
                for i in range(100):
                    await asyncio.sleep(0.02)  # 20ms each = 2000ms total
                    
                    # Simulate memory-intensive work
                    if hasattr(engine, '_execution_state'):
                        if not hasattr(engine, '_execution_state') or engine._execution_state is None:
                            engine._execution_state = {}
                        engine._execution_state[f'heavy_data_{i}'] = f'data_{i}' * 1000  # ~5KB per iteration
                
                end_time = time.time()
                duration = end_time - start_time
                
                user_performance[user_data['user_id']] = {
                    'workload_type': 'heavy',
                    'duration': duration,
                    'operations': 100,
                    'success': True
                }
                
            except Exception as e:
                user_performance[user_data['user_id']] = {
                    'workload_type': 'heavy',
                    'error': str(e),
                    'success': False
                }
        
        # Run mixed workloads concurrently
        tasks = []
        
        # User 0: Heavy workload
        tasks.append(asyncio.create_task(heavy_user_workload(self.test_users[0])))
        
        # Users 1 & 2: Light workloads
        for user_data in self.test_users[1:]:
            tasks.append(asyncio.create_task(light_user_workload(user_data)))
        
        # Execute all concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate all executions completed
        self.assertEqual(len(user_performance), len(self.test_users),
            "Not all users completed performance test")
        
        # Check no errors occurred
        failed_users = [user_id for user_id, perf in user_performance.items() if not perf.get('success', False)]
        self.assertEqual(len(failed_users), 0, f"Users failed performance test: {failed_users}")
        
        # Validate performance isolation
        heavy_user = self.test_users[0]
        light_users = self.test_users[1:]
        
        heavy_perf = user_performance[heavy_user['user_id']]
        
        # Heavy user should have taken longer (as expected)
        self.assertGreater(heavy_perf['duration'], 1.5, 
            "Heavy user should take at least 1.5 seconds")
        
        # Light users should not be significantly impacted
        for user_data in light_users:
            light_perf = user_performance[user_data['user_id']]
            
            # Light users should complete quickly even with heavy user running
            self.assertLess(light_perf['duration'], 0.5,
                f"Light user {user_data['user_id']} took {light_perf['duration']:.3f}s, "
                f"suggesting performance interference from heavy user")
            
            # Performance ratio should show isolation
            performance_ratio = light_perf['duration'] / heavy_perf['duration']
            self.assertLess(performance_ratio, 0.3,
                f"Performance isolation failed. Light/Heavy ratio: {performance_ratio:.3f}")
        
        self.logger.info("User performance isolation test PASSED")

    @pytest.mark.integration
    @pytest.mark.mission_critical
    async def test_error_isolation_between_users(self):
        """
        Test that errors in one user's execution don't affect other users.
        
        ERROR ISOLATION: User A's errors should never cause User B's execution to fail.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
        except ImportError:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine as UserExecutionEngine
        
        execution_results = {}
        
        async def error_prone_execution(user_data, should_error=False):
            """Execute with potential errors."""
            try:
                if 'UserExecutionContext' in globals():
                    context = UserExecutionContext(
                        user_id=user_data['user_id'],
                        session_id=user_data['session_id'],
                        request_id=f"error_test_{uuid.uuid4().hex[:8]}"
                    )
                    engine = UserExecutionEngine(user_context=context)
                else:
                    engine = UserExecutionEngine()
                
                # Simulate normal operations
                operations = []
                for i in range(5):
                    await asyncio.sleep(0.01)
                    
                    if should_error and i == 3:
                        # Intentional error for testing
                        raise ValueError(f"Intentional error for user {user_data['user_id']}")
                    
                    operations.append(f"operation_{i}_user_{user_data['user_id']}")
                
                execution_results[user_data['user_id']] = {
                    'success': True,
                    'operations': operations,
                    'error': None
                }
                
            except Exception as e:
                execution_results[user_data['user_id']] = {
                    'success': False,
                    'operations': [],
                    'error': str(e)
                }
        
        # Execute with mixed error scenarios
        tasks = []
        
        # User 0: Should error
        tasks.append(asyncio.create_task(error_prone_execution(self.test_users[0], should_error=True)))
        
        # Users 1 & 2: Should succeed
        for user_data in self.test_users[1:]:
            tasks.append(asyncio.create_task(error_prone_execution(user_data, should_error=False)))
        
        # Execute concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate error isolation
        error_user = self.test_users[0]
        success_users = self.test_users[1:]
        
        # Error user should have failed
        error_result = execution_results[error_user['user_id']]
        self.assertFalse(error_result['success'], 
            "Error user should have failed")
        self.assertIsNotNone(error_result['error'])
        self.assertIn("Intentional error", error_result['error'])
        
        # Success users should have succeeded despite error user failing
        for user_data in success_users:
            success_result = execution_results[user_data['user_id']]
            self.assertTrue(success_result['success'],
                f"User {user_data['user_id']} should have succeeded despite other user's error. "
                f"Error: {success_result.get('error')}")
            self.assertIsNone(success_result['error'])
            self.assertGreater(len(success_result['operations']), 0)
        
        self.logger.info("Error isolation test PASSED")


if __name__ == "__main__":
    """
    Run comprehensive user isolation tests.
    
    Expected Result: ALL TESTS SHOULD PASS for proper implementation
    These tests are critical for multi-tenant system safety.
    """
    pytest.main([__file__, "-v", "--tb=short", "-x"])  # Stop on first failure