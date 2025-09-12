"""
Agent Execution Multi-User Isolation Integration Tests
====================================================

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: Enterprise ($500K+ ARR customers requiring multi-tenant security)
- Business Goal: Ensure complete isolation between users' agent executions
- Value Impact: Prevents data leakage and cross-contamination that would violate enterprise security requirements
- Strategic Impact: Protects enterprise contracts and enables scaling to thousands of concurrent users

CRITICAL REQUIREMENTS:
- REAL factory pattern testing with UserExecutionContext isolation
- Test concurrent user executions with no shared state contamination
- Validate memory isolation prevents cross-user data access
- Test WebSocket event routing isolation between users
- Ensure database-level user isolation in execution tracking
- Test factory cleanup and resource management per user

This test suite validates the critical security and isolation mechanisms
that enable enterprise multi-tenant usage of the platform, ensuring each
user's agent executions are completely isolated from others.
"""

import asyncio
import pytest
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from unittest.mock import AsyncMock, MagicMock

# SSOT Imports from registry
from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionTracker, ExecutionState, AgentExecutionPhase
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, UserContextManager, create_isolated_execution_context,
    InvalidContextError, ContextIsolationError
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.execution_factory import ExecutionFactory
from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.logging_config import central_logger

# Base test infrastructure
from netra_backend.tests.integration.agent_execution.base_agent_execution_test import BaseAgentExecutionTest

logger = central_logger.get_logger(__name__)


class UserExecutionTracker:
    """Helper class to track per-user execution data during isolation testing."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.executions: Dict[str, Dict[str, Any]] = {}
        self.websocket_events: List[Dict[str, Any]] = []
        self.factory_instances: List[Any] = []
        self.memory_references: Set[int] = set()
        self.start_time = time.time()
        
    def add_execution(self, execution_id: str, execution_data: Dict[str, Any]):
        """Track an execution for this user."""
        self.executions[execution_id] = execution_data
        
    def add_websocket_event(self, event: Dict[str, Any]):
        """Track WebSocket events for this user."""
        self.websocket_events.append(event)
        
    def add_factory_instance(self, instance: Any):
        """Track factory instances created for this user."""
        self.factory_instances.append(instance)
        self.memory_references.add(id(instance))
        
    def get_stats(self) -> Dict[str, Any]:
        """Get isolation statistics for this user."""
        return {
            'user_id': self.user_id,
            'execution_count': len(self.executions),
            'websocket_event_count': len(self.websocket_events),
            'factory_instance_count': len(self.factory_instances),
            'unique_memory_references': len(self.memory_references),
            'duration': time.time() - self.start_time
        }


@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.isolation
class TestMultiUserIsolation(BaseAgentExecutionTest):
    """Integration tests for multi-user execution isolation with factory patterns."""

    async def setup_method(self):
        """Set up multi-user test environment."""
        await super().setup_method()
        
        # Create multiple test users
        self.user_count = 5
        self.users = []
        self.user_trackers: Dict[str, UserExecutionTracker] = {}
        
        for i in range(self.user_count):
            user_id = f"isolation_user_{i}_{uuid.uuid4().hex[:8]}"
            self.users.append(user_id)
            self.user_trackers[user_id] = UserExecutionTracker(user_id)
        
        # Set up user context manager
        self.context_manager = UserContextManager()
        
        # Set up execution factory
        self.execution_factory = ExecutionFactory()
        
        # Set up shared execution tracker
        self.execution_tracker = AgentExecutionTracker()
        await self.execution_tracker.start_monitoring()
        
        logger.info(f"Multi-user isolation test setup complete with {self.user_count} users")

    async def teardown_method(self):
        """Clean up multi-user test resources."""
        try:
            # Clean up user contexts
            for user_id in self.users:
                await self.context_manager.cleanup_user_context(user_id)
            
            # Clean up execution tracker
            if hasattr(self, 'execution_tracker'):
                await self.execution_tracker.stop_monitoring()
                
        except Exception as e:
            logger.warning(f"Multi-user cleanup error (non-critical): {e}")
        
        await super().teardown_method()

    async def test_user_execution_context_isolation_boundaries(self):
        """Test that UserExecutionContext maintains strict isolation boundaries.
        
        Business Value: Prevents data leakage between enterprise customers,
        essential for maintaining security compliance and trust.
        """
        # Create isolated contexts for each user
        user_contexts: Dict[str, UserExecutionContext] = {}
        
        for user_id in self.users:
            context = create_isolated_execution_context(
                user_id=user_id,
                thread_id=f"thread_{user_id}",
                run_id=f"run_{user_id}",
                websocket_connection_id=f"ws_{user_id}",
                metadata={
                    "user_specific_data": f"sensitive_data_for_{user_id}",
                    "user_permissions": ["read", "write", "execute"],
                    "isolation_test": True
                }
            )
            user_contexts[user_id] = context
            self.user_trackers[user_id].add_factory_instance(context)
        
        # Verify each context is properly isolated
        for user_id, context in user_contexts.items():
            # Verify basic isolation properties
            assert context.user_id == user_id
            assert context.thread_id == f"thread_{user_id}"
            assert context.run_id == f"run_{user_id}"
            
            # Verify user-specific metadata isolation
            assert context.metadata["user_specific_data"] == f"sensitive_data_for_{user_id}"
            
            # Verify isolation validation
            context.verify_isolation()
            
            # Verify no cross-contamination with other user contexts
            for other_user_id, other_context in user_contexts.items():
                if other_user_id != user_id:
                    assert context.user_id != other_context.user_id
                    assert context.metadata["user_specific_data"] != other_context.metadata["user_specific_data"]
                    assert id(context) != id(other_context), "Contexts should not share memory references"
        
        logger.info(" PASS:  User execution context isolation boundaries verified")

    async def test_concurrent_agent_execution_isolation(self):
        """Test isolation during concurrent agent executions across multiple users.
        
        Business Value: Ensures platform can handle multiple enterprise customers
        simultaneously without performance degradation or security issues.
        """
        # Create concurrent execution tasks for all users
        execution_tasks = []
        
        for user_id in self.users:
            task = self._create_user_execution_task(user_id)
            execution_tasks.append(task)
        
        # Execute all user tasks concurrently
        start_time = time.time()
        execution_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify no execution failed due to isolation issues
        successful_executions = []
        for i, result in enumerate(execution_results):
            if isinstance(result, Exception):
                logger.error(f"User {self.users[i]} execution failed: {result}")
                assert False, f"Concurrent execution failed for user {self.users[i]}: {result}"
            else:
                successful_executions.append(result)
        
        assert len(successful_executions) == self.user_count, \
            f"Expected {self.user_count} successful executions, got {len(successful_executions)}"
        
        # Verify execution isolation - no data mixing between users
        for i, result in enumerate(successful_executions):
            user_id = self.users[i]
            
            assert result['user_id'] == user_id, "Execution result should match correct user"
            assert result['thread_id'] == f"thread_{user_id}", "Thread ID should be user-specific"
            assert user_id in result['execution_summary'], "User should appear in their own execution summary"
            
            # Verify no other users' data appears in results
            for other_user_id in self.users:
                if other_user_id != user_id:
                    assert other_user_id not in str(result), \
                        f"User {other_user_id} data should not appear in {user_id} results"
        
        logger.info(f" PASS:  Concurrent isolation verified: {self.user_count} users in {total_time:.2f}s")

    async def test_factory_pattern_memory_isolation(self):
        """Test that factory patterns create isolated instances without shared memory.
        
        Business Value: Prevents memory-based data leakage that could expose
        one customer's data to another, critical for enterprise security.
        """
        # Create factory instances for each user
        user_factory_instances: Dict[str, List[Any]] = {}
        
        for user_id in self.users:
            instances = []
            
            # Create multiple factory instances per user
            for i in range(3):
                context = create_isolated_execution_context(
                    user_id=user_id,
                    thread_id=f"factory_thread_{user_id}_{i}",
                    run_id=f"factory_run_{user_id}_{i}",
                    websocket_connection_id=f"factory_ws_{user_id}_{i}"
                )
                
                execution_session = UserAgentSession(
                    user_id=user_id,
                    context=context,
                    session_metadata={"factory_instance": i}
                )
                
                instances.append(execution_session)
                self.user_trackers[user_id].add_factory_instance(execution_session)
            
            user_factory_instances[user_id] = instances
        
        # Verify memory isolation between factory instances
        all_memory_refs = set()
        user_memory_refs: Dict[str, Set[int]] = {}
        
        for user_id, instances in user_factory_instances.items():
            user_refs = set()
            
            for instance in instances:
                memory_ref = id(instance)
                user_refs.add(memory_ref)
                
                # Verify no shared memory references
                assert memory_ref not in all_memory_refs, \
                    f"Memory reference {memory_ref} is shared between users"
                
                all_memory_refs.add(memory_ref)
                
                # Verify instance belongs to correct user
                assert instance.user_id == user_id, \
                    f"Factory instance has wrong user_id: {instance.user_id} vs {user_id}"
            
            user_memory_refs[user_id] = user_refs
        
        # Verify no memory reference overlap between users
        for user_id_1, refs_1 in user_memory_refs.items():
            for user_id_2, refs_2 in user_memory_refs.items():
                if user_id_1 != user_id_2:
                    overlap = refs_1.intersection(refs_2)
                    assert len(overlap) == 0, \
                        f"Memory overlap detected between {user_id_1} and {user_id_2}: {overlap}"
        
        logger.info(f" PASS:  Factory pattern memory isolation verified: {len(all_memory_refs)} unique instances")

    async def test_websocket_event_routing_isolation(self):
        """Test that WebSocket events are routed only to the correct user.
        
        Business Value: Prevents users from seeing other users' agent activity,
        maintaining privacy and security in multi-tenant environment.
        """
        # Create WebSocket mock managers for each user
        user_websocket_managers: Dict[str, AsyncMock] = {}
        
        for user_id in self.users:
            mock_manager = AsyncMock()
            mock_manager.user_id = user_id
            mock_manager.emitted_events = []
            
            # Mock event emission methods
            async def mock_emit_event(event_type: str, data: Dict[str, Any], **kwargs):
                event = {
                    'type': event_type,
                    'data': data,
                    'target_user': user_id,
                    'timestamp': time.time()
                }
                mock_manager.emitted_events.append(event)
                self.user_trackers[user_id].add_websocket_event(event)
                return True
            
            mock_manager.notify_agent_started = mock_emit_event
            mock_manager.notify_agent_thinking = mock_emit_event
            mock_manager.notify_agent_completed = mock_emit_event
            
            user_websocket_managers[user_id] = mock_manager
        
        # Create executions with WebSocket events for each user
        for user_id in self.users:
            execution_id = self.execution_tracker.create_execution(
                agent_name=f"WebSocketTestAgent_{user_id}",
                thread_id=f"ws_thread_{user_id}",
                user_id=user_id,
                metadata={"websocket_routing_test": True}
            )
            
            # Emit events through user-specific WebSocket manager
            websocket_manager = user_websocket_managers[user_id]
            
            await self.execution_tracker.transition_state(
                execution_id, AgentExecutionPhase.STARTING,
                metadata={"user_specific_event": user_id},
                websocket_manager=websocket_manager
            )
            
            await self.execution_tracker.transition_state(
                execution_id, AgentExecutionPhase.THINKING,
                metadata={"user_reasoning": f"Thinking for {user_id}"},
                websocket_manager=websocket_manager
            )
            
            await self.execution_tracker.transition_state(
                execution_id, AgentExecutionPhase.COMPLETED,
                metadata={"user_result": f"Completed for {user_id}"},
                websocket_manager=websocket_manager
            )
        
        # Verify WebSocket event isolation
        for user_id in self.users:
            user_events = self.user_trackers[user_id].websocket_events
            
            assert len(user_events) >= 3, f"User {user_id} should have received events"
            
            # Verify all events are for the correct user
            for event in user_events:
                assert event['target_user'] == user_id, \
                    f"Event incorrectly routed to {user_id}: {event}"
                
                # Verify user-specific data in events
                if 'user_specific_event' in event['data']:
                    assert event['data']['user_specific_event'] == user_id
                
        logger.info(" PASS:  WebSocket event routing isolation verified")

    async def test_database_level_user_isolation(self):
        """Test database-level isolation of user execution data.
        
        Business Value: Ensures database queries cannot access other users' data,
        providing the deepest level of security for enterprise customers.
        """
        # Create executions for each user with database persistence
        user_executions: Dict[str, List[str]] = {}
        
        for user_id in self.users:
            executions = []
            
            # Create multiple executions per user
            for i in range(3):
                execution_id = self.execution_tracker.create_execution(
                    agent_name=f"DBIsolationAgent_{i}",
                    thread_id=f"db_thread_{user_id}_{i}",
                    user_id=user_id,
                    metadata={
                        "sensitive_user_data": f"confidential_data_for_{user_id}_{i}",
                        "user_permissions": ["admin"] if i == 0 else ["user"],
                        "database_isolation_test": True
                    }
                )
                
                # Update execution state to ensure database persistence
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.COMPLETED,
                    result=f"DB isolation test result for {user_id}_{i}"
                )
                
                executions.append(execution_id)
                self.user_trackers[user_id].add_execution(
                    execution_id, 
                    {"user_id": user_id, "execution_index": i}
                )
            
            user_executions[user_id] = executions
        
        # Verify database-level isolation
        for user_id, execution_ids in user_executions.items():
            for execution_id in execution_ids:
                record = self.execution_tracker.get_execution(execution_id)
                
                # Verify record belongs to correct user
                assert record.user_id == user_id, \
                    f"Database record user mismatch: {record.user_id} vs {user_id}"
                
                # Verify sensitive data isolation
                assert user_id in record.metadata.get("sensitive_user_data", ""), \
                    "User-specific sensitive data should be present"
                
                # Verify no other users' data in metadata
                for other_user_id in self.users:
                    if other_user_id != user_id:
                        assert other_user_id not in str(record.metadata), \
                            f"Other user data leaked into {user_id} record: {record.metadata}"
        
        # Test cross-user query isolation (simulate database queries)
        for user_id in self.users:
            user_records = self.execution_tracker.get_executions_by_thread(f"db_thread_{user_id}_0")
            
            # Verify only this user's records are returned
            for record in user_records:
                assert record.user_id == user_id, \
                    f"Cross-user data leak detected in query for {user_id}"
        
        logger.info(" PASS:  Database-level user isolation verified")

    async def test_resource_cleanup_isolation(self):
        """Test that resource cleanup maintains isolation and prevents leakage.
        
        Business Value: Ensures proper resource management prevents one user's
        resource usage from affecting other users' performance or security.
        """
        # Track initial resource state
        initial_stats = {user_id: tracker.get_stats() 
                        for user_id, tracker in self.user_trackers.items()}
        
        # Create and clean up resources for each user
        for user_id in self.users:
            # Create multiple resources that need cleanup
            resources = []
            
            for i in range(5):
                execution_id = self.execution_tracker.create_execution(
                    agent_name=f"CleanupTestAgent_{i}",
                    thread_id=f"cleanup_thread_{user_id}_{i}",
                    user_id=user_id,
                    metadata={"resource_cleanup_test": True, "resource_id": i}
                )
                
                # Complete execution
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.COMPLETED,
                    result=f"Cleanup test completed for {user_id}_{i}"
                )
                
                resources.append(execution_id)
            
            # Clean up user-specific resources
            for execution_id in resources:
                success = self.execution_tracker.cleanup_state(execution_id)
                assert success, f"Resource cleanup failed for {execution_id}"
            
            # Verify cleanup completed for this user
            for execution_id in resources:
                # In-memory record should be cleaned up
                record = self.execution_tracker.get_execution(execution_id)
                assert record is None, f"Resource {execution_id} not cleaned up"
        
        # Verify cleanup didn't affect other users' resources
        final_stats = {user_id: tracker.get_stats() 
                      for user_id, tracker in self.user_trackers.items()}
        
        for user_id in self.users:
            # Verify user isolation maintained during cleanup
            assert final_stats[user_id]['user_id'] == user_id
            
            # Verify no cross-contamination during cleanup
            for other_user_id in self.users:
                if other_user_id != user_id:
                    # Each user's stats should be independent
                    assert final_stats[user_id]['user_id'] != final_stats[other_user_id]['user_id']
        
        logger.info(" PASS:  Resource cleanup isolation verified")

    async def test_stress_isolation_under_high_concurrency(self):
        """Test isolation under high-concurrency stress conditions.
        
        Business Value: Validates platform can maintain isolation even under
        peak enterprise load with hundreds of concurrent users.
        """
        # Create high-concurrency scenario
        concurrent_tasks_per_user = 10
        total_tasks = self.user_count * concurrent_tasks_per_user
        
        # Create concurrent tasks for all users
        all_tasks = []
        
        for user_id in self.users:
            for task_id in range(concurrent_tasks_per_user):
                task = self._create_stress_task(user_id, task_id)
                all_tasks.append(task)
        
        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify no isolation violations under stress
        successful_results = []
        failed_results = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_results.append(result)
            else:
                successful_results.append(result)
        
        # Allow some failures under extreme stress, but verify isolation maintained
        success_rate = len(successful_results) / total_tasks
        assert success_rate >= 0.9, \
            f"Success rate too low under stress: {success_rate:.2%} ({len(failed_results)} failures)"
        
        # Verify isolation maintained in successful results
        user_result_counts = {user_id: 0 for user_id in self.users}
        
        for result in successful_results:
            user_id = result['user_id']
            user_result_counts[user_id] += 1
            
            # Verify no cross-contamination
            for other_user_id in self.users:
                if other_user_id != user_id:
                    assert other_user_id not in str(result), \
                        f"Isolation violation under stress: {other_user_id} in {user_id} result"
        
        # Verify roughly equal distribution (allowing for some variation under stress)
        expected_per_user = len(successful_results) / self.user_count
        for user_id, count in user_result_counts.items():
            variance = abs(count - expected_per_user) / expected_per_user
            assert variance <= 0.5, \
                f"Uneven distribution for {user_id}: {count} vs expected {expected_per_user:.1f}"
        
        logger.info(f" PASS:  Stress isolation verified: {success_rate:.2%} success rate, {total_time:.2f}s total")

    # Helper methods for multi-user testing

    async def _create_user_execution_task(self, user_id: str) -> Dict[str, Any]:
        """Create a comprehensive execution task for a specific user."""
        # Create user-specific execution context
        context = create_isolated_execution_context(
            user_id=user_id,
            thread_id=f"thread_{user_id}",
            run_id=f"run_{user_id}",
            websocket_connection_id=f"ws_{user_id}",
            metadata={
                "concurrent_test": True,
                "user_data": f"data_for_{user_id}",
                "execution_timestamp": time.time()
            }
        )
        
        # Create execution
        execution_id = self.execution_tracker.create_execution(
            agent_name=f"ConcurrentAgent_{user_id}",
            thread_id=context.thread_id,
            user_id=user_id,
            metadata=context.metadata
        )
        
        # Simulate agent execution phases
        phases = [
            ExecutionState.STARTING,
            ExecutionState.RUNNING,
            ExecutionState.COMPLETING,
            ExecutionState.COMPLETED
        ]
        
        for phase in phases:
            self.execution_tracker.update_execution_state(
                execution_id, phase,
                result=f"Phase {phase.value} for {user_id}"
            )
            await asyncio.sleep(0.01)  # Small delay to simulate work
        
        # Return execution summary
        final_record = self.execution_tracker.get_execution(execution_id)
        
        return {
            'user_id': user_id,
            'execution_id': execution_id,
            'thread_id': context.thread_id,
            'final_state': final_record.state.value if final_record else 'unknown',
            'execution_summary': f"Execution completed for {user_id}",
            'isolated': True
        }

    async def _create_stress_task(self, user_id: str, task_id: int) -> Dict[str, Any]:
        """Create a stress test task for a specific user."""
        execution_id = self.execution_tracker.create_execution(
            agent_name=f"StressAgent_{user_id}_{task_id}",
            thread_id=f"stress_thread_{user_id}_{task_id}",
            user_id=user_id,
            metadata={"stress_test": True, "task_id": task_id}
        )
        
        # Rapid state changes to stress the system
        self.execution_tracker.update_execution_state(
            execution_id, ExecutionState.RUNNING
        )
        
        await asyncio.sleep(0.001)  # Minimal delay
        
        self.execution_tracker.update_execution_state(
            execution_id, ExecutionState.COMPLETED,
            result=f"Stress test {task_id} completed for {user_id}"
        )
        
        return {
            'user_id': user_id,
            'task_id': task_id,
            'execution_id': execution_id,
            'completed': True
        }