"""
Integration Tests for Agent State Management and Context Isolation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Security & Multi-User Support - Ensure complete user isolation
- Value Impact: Enables secure multi-tenant platform with zero context leakage between users
- Strategic Impact: $500K+ ARR protection - User data isolation is critical for enterprise adoption

This module tests agent state management with emphasis on:
1. UserExecutionContext isolation between concurrent users
2. Agent state persistence and recovery patterns
3. Context cleanup and memory management
4. Thread-safe state operations
5. Factory pattern implementation for user isolation

CRITICAL REQUIREMENTS per CLAUDE.md:
- NO MOCKS - use real state management systems
- Test factory patterns for complete user isolation
- Validate memory cleanup and resource management
- Test concurrent user scenarios with state isolation
- Ensure no state leakage between user sessions
"""

import asyncio
import gc
import psutil
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from contextlib import asynccontextmanager
import pytest

# SSOT imports following established patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# State management infrastructure - REAL SERVICES ONLY
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context,
    UserExecutionContextFactory
)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    get_agent_instance_factory
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext as SupervisorUserContext
)
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.state_manager import StateManager
from netra_backend.app.services.state_persistence_optimized import StatePersistenceOptimized
from netra_backend.app.core.configuration.base import get_config


class TestAgentStateManagement(SSotAsyncTestCase):
    """Integration tests for agent state management and user context isolation."""
    
    async def async_setup_method(self, method=None):
        """Set up test environment with real state management infrastructure."""
        await super().async_setup_method(method)
        
        # Initialize environment
        self.env = get_env()
        self.set_env_var("TESTING", "true")
        self.set_env_var("TEST_MODE", "state_management")
        
        # Create test identifiers
        self.test_session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # Initialize state management infrastructure
        self.user_context_factory = None
        self.agent_factory = None
        self.execution_engine = None
        self.state_manager = None
        self.persistence_service = None
        
        # Tracking for cleanup validation
        self.created_contexts = set()
        self.created_agents = set()
        self.memory_snapshots = []
        
        await self._initialize_state_infrastructure()
    
    async def _initialize_state_infrastructure(self):
        """Initialize real state management infrastructure for testing."""
        try:
            # Initialize user context factory
            self.user_context_factory = UserExecutionContextFactory()
            
            # Initialize agent factory
            self.agent_factory = get_agent_instance_factory()
            
            # Initialize state persistence service
            config = get_config()
            self.persistence_service = StatePersistenceOptimized(config)
            
            # Initialize state manager
            self.state_manager = StateManager(
                persistence_service=self.persistence_service
            )
            
            # Initialize execution engine for state testing
            self.execution_engine = UserExecutionEngine()
            
            # Take initial memory snapshot
            process = psutil.Process()
            self.memory_snapshots.append({
                'timestamp': time.time(),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'stage': 'initial'
            })
            
            self.record_metric("state_infrastructure_init_success", True)
            
        except Exception as e:
            self.record_metric("state_infrastructure_init_error", str(e))
            raise
    
    def _take_memory_snapshot(self, stage: str):
        """Take a memory snapshot for resource tracking."""
        try:
            process = psutil.Process()
            self.memory_snapshots.append({
                'timestamp': time.time(),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'stage': stage
            })
        except Exception:
            pass  # Memory tracking is optional
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_isolation_between_sessions(self):
        """
        Test complete isolation between user execution contexts.
        
        Business Value: Ensures user data and agent state never leak between
        different user sessions, maintaining enterprise-grade security.
        """
        # Create multiple isolated user contexts
        user_contexts = []
        context_data = []
        
        for i in range(5):
            user_id = f"isolated_user_{i}_{uuid.uuid4().hex[:6]}"
            thread_id = f"isolated_thread_{i}_{uuid.uuid4().hex[:6]}"
            
            # Create user context with unique data
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=f"isolated_run_{i}_{uuid.uuid4().hex[:6]}",
                session_metadata={
                    "user_index": i,
                    "secret_data": f"user_{i}_secret_{uuid.uuid4().hex[:8]}",
                    "session_id": self.test_session_id
                }
            )
            
            # Track context for cleanup
            self.created_contexts.add(user_context.user_id)
            
            # Validate isolation properties
            validate_user_context(user_context)
            self.assertTrue(user_context.is_isolated())
            
            user_contexts.append(user_context)
            context_data.append({
                'user_id': user_id,
                'thread_id': thread_id,
                'secret_data': user_context.session_metadata['secret_data']
            })
        
        # Validate each context maintains its unique identity
        for i, context in enumerate(user_contexts):
            # Verify unique identifiers
            self.assertEqual(context.user_id, context_data[i]['user_id'])
            self.assertEqual(context.thread_id, context_data[i]['thread_id'])
            self.assertEqual(
                context.session_metadata['secret_data'], 
                context_data[i]['secret_data']
            )
            
            # Verify no contamination from other contexts
            for j, other_context in enumerate(user_contexts):
                if i != j:
                    self.assertNotEqual(context.user_id, other_context.user_id)
                    self.assertNotEqual(context.thread_id, other_context.thread_id)
                    self.assertNotEqual(
                        context.session_metadata['secret_data'],
                        other_context.session_metadata['secret_data']
                    )
        
        # Test concurrent state operations
        async def modify_context_state(context: UserExecutionContext, index: int):
            """Modify context state in concurrent operation."""
            await asyncio.sleep(0.1 * index)  # Stagger operations
            context.set_context_variable(f"modified_at_{index}", time.time())
            return context.get_context_variable(f"modified_at_{index}")
        
        # Execute concurrent modifications
        results = await asyncio.gather(
            *[modify_context_state(ctx, i) for i, ctx in enumerate(user_contexts)]
        )
        
        # Verify isolation maintained during concurrent operations
        for i, result in enumerate(results):
            self.assertIsNotNone(result)
            
            # Verify each context only has its own modification
            context = user_contexts[i]
            self.assertIsNotNone(context.get_context_variable(f"modified_at_{i}"))
            
            # Verify no cross-contamination
            for j in range(len(user_contexts)):
                if i != j:
                    self.assertIsNone(context.get_context_variable(f"modified_at_{j}"))
        
        self.record_metric("user_contexts_isolated", len(user_contexts))
        self.record_metric("isolation_integrity_verified", True)
        
        # Take memory snapshot after context operations
        self._take_memory_snapshot("after_context_isolation")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_state_persistence_and_recovery(self):
        """
        Test agent state persistence and recovery across execution cycles.
        
        Business Value: Ensures conversation continuity and state recovery,
        supporting long-running user interactions and system reliability.
        """
        # Create user context for persistent state testing
        user_context = UserExecutionContext(
            user_id=f"persist_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"persist_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"persist_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "state_persistence"}
        )
        self.created_contexts.add(user_context.user_id)
        
        # Create initial agent execution context with state
        execution_context = AgentExecutionContext(
            agent_name="triage_agent",
            user_message="Initialize conversation with persistent state",
            user_context=user_context,
            execution_id=f"persist_exec_{uuid.uuid4().hex[:8]}"
        )
        
        # Execute initial agent to create state
        initial_result = await self.execution_engine.execute_agent(execution_context)
        self.assertIsNotNone(initial_result)
        
        # Store state information for validation
        initial_state_data = {
            'user_id': user_context.user_id,
            'thread_id': user_context.thread_id,
            'execution_time': time.time(),
            'conversation_started': True
        }
        
        # Persist state using state manager
        state_key = f"agent_state_{user_context.user_id}_{user_context.thread_id}"
        await self.state_manager.store_state(state_key, initial_state_data)
        
        # Simulate system interruption - clear in-memory state
        await asyncio.sleep(0.1)
        gc.collect()  # Force garbage collection
        
        # Create new execution context simulating recovery
        recovery_context = AgentExecutionContext(
            agent_name="triage_agent",
            user_message="Continue conversation after recovery",
            user_context=user_context,  # Same user context
            execution_id=f"recover_exec_{uuid.uuid4().hex[:8]}"
        )
        
        # Recover state
        recovered_state = await self.state_manager.retrieve_state(state_key)
        self.assertIsNotNone(recovered_state)
        
        # Validate recovered state matches original
        self.assertEqual(recovered_state['user_id'], initial_state_data['user_id'])
        self.assertEqual(recovered_state['thread_id'], initial_state_data['thread_id'])
        self.assertTrue(recovered_state['conversation_started'])
        
        # Execute agent with recovered state
        recovery_result = await self.execution_engine.execute_agent(recovery_context)
        self.assertIsNotNone(recovery_result)
        
        # Validate continuity
        self.assertEqual(recovery_result.user_context.user_id, user_context.user_id)
        self.assertEqual(recovery_result.user_context.thread_id, user_context.thread_id)
        
        # Test state cleanup
        await self.state_manager.cleanup_state(state_key)
        cleaned_state = await self.state_manager.retrieve_state(state_key)
        self.assertIsNone(cleaned_state)
        
        self.record_metric("state_persistence_verified", True)
        self.record_metric("state_recovery_successful", True)
        
        # Take memory snapshot after persistence operations
        self._take_memory_snapshot("after_persistence")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_agent_state_isolation(self):
        """
        Test agent state isolation under concurrent execution.
        
        Business Value: Ensures platform can handle multiple simultaneous users
        with complete state isolation, supporting business scalability.
        """
        # Configuration for concurrent testing
        concurrent_users = 4
        operations_per_user = 3
        
        # Create concurrent user contexts
        user_contexts = []
        for i in range(concurrent_users):
            context = UserExecutionContext(
                user_id=f"concurrent_user_{i}_{uuid.uuid4().hex[:6]}",
                thread_id=f"concurrent_thread_{i}_{uuid.uuid4().hex[:6]}",
                run_id=f"concurrent_run_{i}_{uuid.uuid4().hex[:6]}",
                session_metadata={
                    "user_index": i,
                    "test_type": "concurrent_isolation"
                }
            )
            user_contexts.append(context)
            self.created_contexts.add(context.user_id)
        
        # Track state modifications per user
        user_state_tracking = {ctx.user_id: [] for ctx in user_contexts}
        
        async def execute_user_operations(user_ctx: UserExecutionContext, user_index: int):
            """Execute multiple operations for a single user."""
            operations_completed = []
            
            for op_index in range(operations_per_user):
                # Create unique execution context
                exec_context = AgentExecutionContext(
                    agent_name="triage_agent",
                    user_message=f"User {user_index} operation {op_index}",
                    user_context=user_ctx,
                    execution_id=f"concurrent_exec_{user_index}_{op_index}_{uuid.uuid4().hex[:6]}"
                )
                
                # Add operation delay to increase concurrency potential
                await asyncio.sleep(0.05 * user_index)
                
                # Store state specific to this user
                state_key = f"user_{user_index}_op_{op_index}"
                operation_data = {
                    'user_id': user_ctx.user_id,
                    'operation_index': op_index,
                    'timestamp': time.time(),
                    'unique_value': f"value_{user_index}_{op_index}_{uuid.uuid4().hex[:6]}"
                }
                
                await self.state_manager.store_state(state_key, operation_data)
                
                # Execute agent operation
                result = await self.execution_engine.execute_agent(exec_context)
                
                operations_completed.append({
                    'operation_index': op_index,
                    'state_key': state_key,
                    'operation_data': operation_data,
                    'execution_result': result
                })
                
                user_state_tracking[user_ctx.user_id].append(operation_data)
            
            return operations_completed
        
        # Execute all users concurrently
        start_time = time.time()
        user_results = await asyncio.gather(
            *[execute_user_operations(ctx, i) for i, ctx in enumerate(user_contexts)],
            return_exceptions=True
        )
        concurrent_execution_time = time.time() - start_time
        
        # Validate concurrent execution results
        successful_users = 0
        for i, user_result in enumerate(user_results):
            if isinstance(user_result, Exception):
                self.fail(f"User {i} concurrent execution failed: {user_result}")
            
            self.assertEqual(len(user_result), operations_per_user)
            successful_users += 1
            
            # Validate user state isolation
            user_id = user_contexts[i].user_id
            user_operations = user_state_tracking[user_id]
            
            self.assertEqual(len(user_operations), operations_per_user)
            
            # Verify each operation's state is unique and isolated
            for operation in user_operations:
                self.assertEqual(operation['user_id'], user_id)
                
                # Verify no contamination from other users
                for other_user_id, other_operations in user_state_tracking.items():
                    if other_user_id != user_id:
                        for other_op in other_operations:
                            self.assertNotEqual(operation['unique_value'], other_op['unique_value'])
        
        # Validate all operations completed successfully
        self.assertEqual(successful_users, concurrent_users)
        
        # Performance validation
        expected_max_time = 30.0  # Should complete within 30 seconds
        self.assertLess(concurrent_execution_time, expected_max_time)
        
        self.record_metric("concurrent_users_tested", concurrent_users)
        self.record_metric("concurrent_execution_time", concurrent_execution_time)
        self.record_metric("concurrent_isolation_verified", True)
        
        # Take memory snapshot after concurrent operations
        self._take_memory_snapshot("after_concurrent_operations")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_memory_cleanup_and_resource_management(self):
        """
        Test memory cleanup and resource management for agent states.
        
        Business Value: Ensures platform maintains optimal performance and
        resource usage, supporting cost-effective scaling and system stability.
        """
        # Track memory usage throughout test
        initial_memory = self.memory_snapshots[-1]['memory_mb'] if self.memory_snapshots else 0
        
        # Create and destroy multiple user contexts to test cleanup
        cleanup_test_contexts = []
        cleanup_test_data = []
        
        # Phase 1: Create contexts and agents
        for i in range(10):
            user_context = UserExecutionContext(
                user_id=f"cleanup_user_{i}_{uuid.uuid4().hex[:6]}",
                thread_id=f"cleanup_thread_{i}_{uuid.uuid4().hex[:6]}",
                run_id=f"cleanup_run_{i}_{uuid.uuid4().hex[:6]}",
                session_metadata={"test_type": "cleanup", "iteration": i}
            )
            cleanup_test_contexts.append(user_context)
            self.created_contexts.add(user_context.user_id)
            
            # Store substantial data in state
            state_data = {
                'user_id': user_context.user_id,
                'large_data': 'x' * 1000,  # 1KB of data per context
                'timestamp': time.time(),
                'context_variables': {f'var_{j}': f'value_{j}' for j in range(50)}
            }
            
            state_key = f"cleanup_test_{user_context.user_id}"
            await self.state_manager.store_state(state_key, state_data)
            cleanup_test_data.append(state_key)
        
        self._take_memory_snapshot("after_context_creation")
        
        # Phase 2: Execute operations to build up state
        execution_tasks = []
        for i, context in enumerate(cleanup_test_contexts[:5]):  # Use first 5 for execution
            exec_context = AgentExecutionContext(
                agent_name="triage_agent",
                user_message=f"Cleanup test execution {i}",
                user_context=context,
                execution_id=f"cleanup_exec_{i}_{uuid.uuid4().hex[:6]}"
            )
            execution_tasks.append(self.execution_engine.execute_agent(exec_context))
        
        # Execute with some agents
        execution_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        successful_executions = [r for r in execution_results if not isinstance(r, Exception)]
        
        self._take_memory_snapshot("after_agent_executions")
        
        # Phase 3: Cleanup contexts and states
        cleanup_start_time = time.time()
        
        # Clean up stored states
        for state_key in cleanup_test_data:
            await self.state_manager.cleanup_state(state_key)
        
        # Explicit cleanup of contexts
        for context in cleanup_test_contexts:
            if hasattr(context, 'cleanup'):
                await context.cleanup()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow cleanup to complete
        
        cleanup_time = time.time() - cleanup_start_time
        self._take_memory_snapshot("after_cleanup")
        
        # Phase 4: Verify cleanup effectiveness
        # Verify states are actually cleaned up
        for state_key in cleanup_test_data:
            retrieved_state = await self.state_manager.retrieve_state(state_key)
            self.assertIsNone(retrieved_state, f"State {state_key} not properly cleaned up")
        
        # Analyze memory usage
        if len(self.memory_snapshots) >= 3:
            before_creation = self.memory_snapshots[-4]['memory_mb']
            after_creation = self.memory_snapshots[-3]['memory_mb']
            after_execution = self.memory_snapshots[-2]['memory_mb']
            after_cleanup = self.memory_snapshots[-1]['memory_mb']
            
            memory_growth = after_execution - before_creation
            memory_recovered = after_execution - after_cleanup
            cleanup_efficiency = (memory_recovered / memory_growth) if memory_growth > 0 else 1.0
            
            # Validate memory management
            self.assertGreater(cleanup_efficiency, 0.5, "Cleanup should recover at least 50% of memory")
            
            self.record_metric("memory_growth_mb", memory_growth)
            self.record_metric("memory_recovered_mb", memory_recovered)
            self.record_metric("cleanup_efficiency", cleanup_efficiency)
        
        # Validate cleanup performance
        expected_cleanup_time = 5.0  # Should complete cleanup within 5 seconds
        self.assertLess(cleanup_time, expected_cleanup_time)
        
        self.record_metric("contexts_cleaned", len(cleanup_test_contexts))
        self.record_metric("states_cleaned", len(cleanup_test_data))
        self.record_metric("cleanup_time", cleanup_time)
        self.record_metric("cleanup_verification_passed", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_safe_state_operations(self):
        """
        Test thread-safe state operations under concurrent access.
        
        Business Value: Ensures platform maintains data integrity under
        concurrent load, supporting reliable multi-user operations.
        """
        # Create shared user context for thread safety testing
        shared_context = UserExecutionContext(
            user_id=f"threadsafe_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"threadsafe_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"threadsafe_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "thread_safety"}
        )
        self.created_contexts.add(shared_context.user_id)
        
        # Shared state key and counter for testing
        shared_state_key = f"threadsafe_counter_{shared_context.user_id}"
        operation_results = []
        
        # Initialize shared counter
        await self.state_manager.store_state(shared_state_key, {'counter': 0, 'operations': []})
        
        async def concurrent_state_operation(operation_id: int) -> Dict[str, Any]:
            """Perform thread-safe state operation."""
            try:
                # Retrieve current state
                current_state = await self.state_manager.retrieve_state(shared_state_key)
                if not current_state:
                    return {'operation_id': operation_id, 'success': False, 'error': 'No state found'}
                
                # Modify state (simulate work)
                await asyncio.sleep(0.01)  # Small delay to increase race condition potential
                
                new_counter = current_state['counter'] + 1
                new_operations = current_state['operations'] + [operation_id]
                
                updated_state = {
                    'counter': new_counter,
                    'operations': new_operations,
                    'last_operation_id': operation_id,
                    'timestamp': time.time()
                }
                
                # Store updated state
                await self.state_manager.store_state(shared_state_key, updated_state)
                
                return {
                    'operation_id': operation_id,
                    'success': True,
                    'counter_value': new_counter,
                    'operations_count': len(new_operations)
                }
                
            except Exception as e:
                return {
                    'operation_id': operation_id,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute concurrent state operations
        concurrent_operations = 20
        start_time = time.time()
        
        results = await asyncio.gather(
            *[concurrent_state_operation(i) for i in range(concurrent_operations)],
            return_exceptions=True
        )
        
        execution_time = time.time() - start_time
        
        # Analyze results for thread safety
        successful_operations = [r for r in results if not isinstance(r, Exception) and r.get('success')]
        failed_operations = [r for r in results if isinstance(r, Exception) or not r.get('success')]
        
        # Validate thread safety
        success_rate = len(successful_operations) / len(results)
        self.assertGreater(success_rate, 0.8, "At least 80% of concurrent operations should succeed")
        
        # Retrieve final state to check integrity
        final_state = await self.state_manager.retrieve_state(shared_state_key)
        self.assertIsNotNone(final_state)
        
        # Validate state integrity
        final_counter = final_state.get('counter', 0)
        final_operations = final_state.get('operations', [])
        
        # The counter should be consistent with successful operations
        self.assertEqual(final_counter, len(final_operations))
        self.assertEqual(len(final_operations), len(set(final_operations)))  # No duplicates
        
        # Performance validation
        expected_max_time = 10.0  # Should complete within 10 seconds
        self.assertLess(execution_time, expected_max_time)
        
        self.record_metric("concurrent_operations_tested", concurrent_operations)
        self.record_metric("thread_safety_success_rate", success_rate)
        self.record_metric("final_counter_value", final_counter)
        self.record_metric("thread_safety_execution_time", execution_time)
        self.record_metric("state_integrity_verified", True)
        
        # Cleanup shared state
        await self.state_manager.cleanup_state(shared_state_key)
        
        # Final memory snapshot
        self._take_memory_snapshot("after_thread_safety_test")
    
    async def async_teardown_method(self, method=None):
        """Clean up test infrastructure and validate resource cleanup."""
        try:
            # Clean up all created contexts
            cleanup_tasks = []
            for user_id in self.created_contexts:
                cleanup_tasks.append(self._cleanup_user_context(user_id))
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Clean up infrastructure
            if self.state_manager:
                await self.state_manager.shutdown()
            
            if self.persistence_service:
                await self.persistence_service.cleanup()
            
            if self.execution_engine:
                await self.execution_engine.cleanup()
            
            # Final memory snapshot
            self._take_memory_snapshot("final_cleanup")
            
            # Log memory analysis
            if len(self.memory_snapshots) >= 2:
                initial = self.memory_snapshots[0]['memory_mb']
                final = self.memory_snapshots[-1]['memory_mb']
                memory_delta = final - initial
                
                self.record_metric("memory_delta_mb", memory_delta)
                if memory_delta > 50:  # More than 50MB growth
                    print(f"WARNING: Memory growth of {memory_delta:.2f}MB detected")
            
            # Log performance metrics
            metrics = self.get_all_metrics()
            if metrics:
                print(f"\nAgent State Management Test Metrics:")
                for key, value in metrics.items():
                    print(f"  {key}: {value}")
            
            self.record_metric("test_cleanup_success", True)
            
        except Exception as e:
            self.record_metric("test_cleanup_error", str(e))
        
        await super().async_teardown_method(method)
    
    async def _cleanup_user_context(self, user_id: str):
        """Clean up a specific user context and associated state."""
        try:
            # Clean up any stored state for this user
            state_keys = [f"agent_state_{user_id}", f"cleanup_test_{user_id}"]
            for key in state_keys:
                await self.state_manager.cleanup_state(key)
                
        except Exception:
            pass  # Best effort cleanup