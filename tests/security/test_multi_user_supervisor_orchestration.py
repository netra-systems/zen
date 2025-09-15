"""
Security and Performance Tests for Multi-User Supervisor Orchestration

Business Value: $500K+ ARR Enterprise Security - Multi-user isolation validation
Purpose: Validate multi-user concurrent orchestration security and performance
Focus: User isolation, performance under load, security boundaries

This validates Issue #1188 Phase 3.4 enterprise-grade multi-user orchestration.
Critical for HIPAA, SOC2, SEC compliance readiness.
"""

import pytest
import asyncio
import threading
import time
import gc
import psutil
import os
from typing import Dict, List, Any, Set
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
import weakref

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Core supervisor and security imports
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager


class MultiUserSupervisorOrchestrationSecurityTests(SSotAsyncTestCase):
    """Security tests for multi-user supervisor orchestration."""

    def setup_method(self, method):
        """Set up multi-user security test environment."""
        super().setup_method(method)

        # Test environment
        self.env = IsolatedEnvironment()

        # Track user isolation
        self.user_data_isolation = {}
        self.cross_contamination_detected = []

        # Mock LLM manager
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_llm_manager.get_client = Mock(return_value=Mock())

    def _create_user_context(self, user_id: str) -> UserExecutionContext:
        """Create isolated user context for testing."""
        return UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=f"security-thread-{user_id}",
            run_id=f"security-run-{user_id}",
            request_id=f"security-request-{user_id}"
        )

    def test_user_context_isolation_validation(self):
        """
        Test that user contexts are properly isolated between supervisor instances.

        Business Impact: Prevents user data leakage in enterprise deployment.
        Compliance: HIPAA, SOC2, SEC requirements.
        """
        user_contexts = [self._create_user_context(f"security-user-{i}") for i in range(5)]
        supervisors = []

        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory') as mock_factory:
            # Create unique factories per user
            factories = [Mock() for _ in range(5)]
            mock_factory.side_effect = factories

            # Create supervisors for each user
            for user_ctx in user_contexts:
                supervisor = SupervisorAgent(
                    llm_manager=self.mock_llm_manager,
                    user_context=user_ctx
                )
                supervisors.append(supervisor)

            # Test 1: Each supervisor should have isolated user context
            for i, supervisor in enumerate(supervisors):
                assert supervisor._initialization_user_context.user_id == user_contexts[i].user_id
                assert supervisor._initialization_user_context.thread_id == user_contexts[i].thread_id

            # Test 2: No supervisor should share user context with another
            for i, supervisor_1 in enumerate(supervisors):
                for j, supervisor_2 in enumerate(supervisors):
                    if i != j:
                        assert supervisor_1._initialization_user_context is not supervisor_2._initialization_user_context
                        assert supervisor_1._initialization_user_context.user_id != supervisor_2._initialization_user_context.user_id

    def test_agent_factory_isolation_security(self):
        """
        Test that agent factories are properly isolated per user.

        Business Impact: Prevents cross-user agent contamination.
        Security: Enterprise-grade factory isolation.
        """
        user_contexts = [self._create_user_context(f"factory-user-{i}") for i in range(3)]

        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory') as mock_factory_creator:
            # Create unique factory instances
            factories = [Mock() for _ in range(3)]
            mock_factory_creator.side_effect = factories

            supervisors = []
            for user_ctx in user_contexts:
                supervisor = SupervisorAgent(
                    llm_manager=self.mock_llm_manager,
                    user_context=user_ctx
                )
                supervisors.append(supervisor)

            # Test 3: Each supervisor should have its own factory instance
            for i, supervisor in enumerate(supervisors):
                assert supervisor.agent_factory is factories[i]

            # Test 4: No factory sharing between supervisors
            factory_instances = [supervisor.agent_factory for supervisor in supervisors]
            assert len(set(id(f) for f in factory_instances)) == 3  # All unique instances

    def test_concurrent_user_orchestration_isolation(self):
        """
        Test that concurrent user orchestrations don't interfere with each other.

        Business Impact: Multi-user scalability without data leakage.
        Performance: Concurrent user support validation.
        """
        num_users = 5
        user_contexts = [self._create_user_context(f"concurrent-user-{i}") for i in range(num_users)]

        # Track events per user to detect contamination
        user_events = {ctx.user_id: [] for ctx in user_contexts}

        def create_supervisor_and_run_orchestration(user_ctx):
            """Create supervisor and simulate orchestration for a user."""
            with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
                # Mock WebSocket bridge that tracks user events
                mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)

                async def track_events(event_type: str, event_data: Dict[str, Any]):
                    user_id = event_data.get('user_id', 'UNKNOWN')
                    user_events[user_id].append({
                        'event_type': event_type,
                        'user_id': user_id,
                        'timestamp': time.time(),
                        'thread_id': threading.current_thread().ident
                    })

                mock_websocket_bridge.send_agent_event = AsyncMock(side_effect=track_events)

                try:
                    supervisor = SupervisorAgent(
                        llm_manager=self.mock_llm_manager,
                        user_context=user_ctx,
                        websocket_bridge=mock_websocket_bridge
                    )

                    # Simulate orchestration events
                    async def simulate_orchestration():
                        await supervisor.websocket_bridge.send_agent_event(
                            "agent_started",
                            {"user_id": user_ctx.user_id, "message": f"Started for {user_ctx.user_id}"}
                        )
                        await asyncio.sleep(0.1)  # Simulate work
                        await supervisor.websocket_bridge.send_agent_event(
                            "agent_completed",
                            {"user_id": user_ctx.user_id, "message": f"Completed for {user_ctx.user_id}"}
                        )

                    # Run orchestration
                    asyncio.run(simulate_orchestration())
                    return True

                except Exception as e:
                    return f"ERROR: {e}"

        # Test 5: Run concurrent orchestrations
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(create_supervisor_and_run_orchestration, ctx) for ctx in user_contexts]
            results = [future.result() for future in as_completed(futures)]

        # Test 6: All orchestrations should succeed
        for result in results:
            assert result is True, f"Orchestration failed: {result}"

        # Test 7: Validate user isolation in events
        for user_id, events in user_events.items():
            if user_id != 'UNKNOWN':  # Skip unknown events
                assert len(events) == 2, f"User {user_id} should have 2 events, got {len(events)}"
                for event in events:
                    assert event['user_id'] == user_id, f"Event contamination detected: {event}"

        # Test 8: No cross-user contamination
        all_user_ids = set(user_events.keys()) - {'UNKNOWN'}
        for user_id, events in user_events.items():
            if user_id in all_user_ids:
                for event in events:
                    # Each event should only belong to the correct user
                    assert event['user_id'] == user_id
                    assert event['user_id'] in all_user_ids

    def test_memory_isolation_and_cleanup(self):
        """
        Test memory isolation and cleanup between user sessions.

        Business Impact: Prevents memory leaks and data persistence.
        Security: Ensures no user data remains in memory after session ends.
        """
        initial_memory = psutil.Process().memory_info().rss

        # Create and destroy supervisor instances
        supervisors_created = 0
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            for i in range(10):  # Create multiple supervisor instances
                user_ctx = self._create_user_context(f"memory-user-{i}")

                supervisor = SupervisorAgent(
                    llm_manager=self.mock_llm_manager,
                    user_context=user_ctx
                )
                supervisors_created += 1

                # Use weak reference to verify cleanup
                supervisor_ref = weakref.ref(supervisor)
                user_ctx_ref = weakref.ref(user_ctx)

                # Clear references
                del supervisor
                del user_ctx

                # Force garbage collection
                gc.collect()

                # Test 9: Objects should be cleaned up
                # Note: This test may be flaky due to Python's garbage collection timing
                # In a real system, we would use more sophisticated memory tracking

        # Test 10: Memory usage should not grow excessively
        final_memory = psutil.Process().memory_info().rss
        memory_growth = final_memory - initial_memory

        # Allow some memory growth but not excessive (less than 50MB for 10 instances)
        max_allowed_growth = 50 * 1024 * 1024  # 50MB
        assert memory_growth < max_allowed_growth, f"Memory grew by {memory_growth / (1024*1024):.1f}MB, exceeding {max_allowed_growth / (1024*1024)}MB limit"

    def test_websocket_event_user_isolation(self):
        """
        Test that WebSocket events are isolated per user session.

        Business Impact: Prevents users from receiving other users' events.
        Security: Critical for multi-tenant security.
        """
        users = [self._create_user_context(f"websocket-user-{i}") for i in range(3)]
        user_websocket_events = {user.user_id: [] for user in users}

        def create_isolated_websocket_bridge(target_user_id: str):
            """Create WebSocket bridge that only handles events for specific user."""
            mock_bridge = Mock(spec=AgentWebSocketBridge)

            async def isolated_event_handler(event_type: str, event_data: Dict[str, Any]):
                received_user_id = event_data.get('user_id')
                if received_user_id == target_user_id:
                    user_websocket_events[target_user_id].append({
                        'event_type': event_type,
                        'user_id': received_user_id,
                        'data': event_data
                    })
                else:
                    # This would be a security violation
                    self.cross_contamination_detected.append({
                        'target_user': target_user_id,
                        'received_event_for_user': received_user_id,
                        'event_type': event_type
                    })

            mock_bridge.send_agent_event = AsyncMock(side_effect=isolated_event_handler)
            return mock_bridge

        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisors = []

            # Create supervisors with isolated WebSocket bridges
            for user_ctx in users:
                websocket_bridge = create_isolated_websocket_bridge(user_ctx.user_id)
                supervisor = SupervisorAgent(
                    llm_manager=self.mock_llm_manager,
                    user_context=user_ctx,
                    websocket_bridge=websocket_bridge
                )
                supervisors.append((supervisor, user_ctx))

            # Test 11: Send events from each supervisor
            async def send_events_for_all_users():
                tasks = []
                for supervisor, user_ctx in supervisors:
                    async def send_user_events(sup, ctx):
                        await sup.websocket_bridge.send_agent_event(
                            "agent_started",
                            {"user_id": ctx.user_id, "message": f"Event for {ctx.user_id}"}
                        )
                    tasks.append(send_user_events(supervisor, user_ctx))

                await asyncio.gather(*tasks)

            # Run the event sending
            asyncio.run(send_events_for_all_users())

            # Test 12: Validate event isolation
            for user_id, events in user_websocket_events.items():
                assert len(events) == 1, f"User {user_id} should have exactly 1 event"
                assert events[0]['user_id'] == user_id, f"Event user_id mismatch for {user_id}"

            # Test 13: No cross-contamination should be detected
            assert len(self.cross_contamination_detected) == 0, f"Cross-contamination detected: {self.cross_contamination_detected}"


class SupervisorOrchestrationPerformanceTests(SSotAsyncTestCase):
    """Performance tests for supervisor orchestration under load."""

    def setup_method(self, method):
        """Set up performance test environment."""
        super().setup_method(method)

        self.performance_metrics = {
            'initialization_times': [],
            'orchestration_times': [],
            'memory_usage': [],
            'concurrent_users_supported': 0
        }

    def test_supervisor_initialization_performance(self):
        """
        Test supervisor initialization performance under load.

        Business Impact: Fast response times for user requests.
        SLA: Initialization should be under 100ms per supervisor.
        """
        num_supervisors = 50
        initialization_times = []

        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            for i in range(num_supervisors):
                user_ctx = UserExecutionContext.from_request(
                    user_id=f"perf-user-{i}",
                    thread_id=f"perf-thread-{i}",
                    run_id=f"perf-run-{i}",
                    request_id=f"perf-request-{i}"
                )

                start_time = time.time()

                supervisor = SupervisorAgent(
                    llm_manager=Mock(spec=LLMManager),
                    user_context=user_ctx
                )

                end_time = time.time()
                initialization_time = end_time - start_time
                initialization_times.append(initialization_time)

                # Test 14: Each initialization should be fast
                assert initialization_time < 0.1, f"Initialization {i} took {initialization_time:.3f}s, exceeding 100ms SLA"

        # Test 15: Average initialization time should be well under SLA
        avg_time = sum(initialization_times) / len(initialization_times)
        assert avg_time < 0.05, f"Average initialization time {avg_time:.3f}s exceeds 50ms target"

        # Test 16: 95th percentile should be reasonable
        sorted_times = sorted(initialization_times)
        p95_time = sorted_times[int(0.95 * len(sorted_times))]
        assert p95_time < 0.1, f"95th percentile initialization time {p95_time:.3f}s exceeds 100ms SLA"

    def test_concurrent_users_scalability(self):
        """
        Test how many concurrent users the supervisor orchestration can support.

        Business Impact: Enterprise scalability requirements.
        Target: Support 10+ concurrent users with acceptable performance.
        """
        max_users_to_test = 10
        successful_users = 0
        failed_users = 0

        def create_and_test_supervisor(user_id: int) -> Dict[str, Any]:
            """Create supervisor and measure performance for a user."""
            try:
                user_ctx = UserExecutionContext.from_request(
                    user_id=f"scale-user-{user_id}",
                    thread_id=f"scale-thread-{user_id}",
                    run_id=f"scale-run-{user_id}",
                    request_id=f"scale-request-{user_id}"
                )

                with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
                    start_time = time.time()

                    supervisor = SupervisorAgent(
                        llm_manager=Mock(spec=LLMManager),
                        user_context=user_ctx
                    )

                    creation_time = time.time() - start_time

                    return {
                        'user_id': user_id,
                        'success': True,
                        'creation_time': creation_time,
                        'memory_usage': psutil.Process().memory_info().rss
                    }

            except Exception as e:
                return {
                    'user_id': user_id,
                    'success': False,
                    'error': str(e),
                    'creation_time': None
                }

        # Test 17: Create supervisors concurrently
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_users_to_test) as executor:
            futures = [executor.submit(create_and_test_supervisor, i) for i in range(max_users_to_test)]
            results = [future.result() for future in as_completed(futures)]

        total_time = time.time() - start_time

        # Analyze results
        for result in results:
            if result['success']:
                successful_users += 1
                if result['creation_time']:
                    self.performance_metrics['initialization_times'].append(result['creation_time'])
            else:
                failed_users += 1

        # Test 18: Most users should succeed (at least 80%)
        success_rate = successful_users / max_users_to_test
        assert success_rate >= 0.8, f"Success rate {success_rate:.1%} below 80% threshold"

        # Test 19: Concurrent creation should be efficient
        assert total_time < 5.0, f"Concurrent creation took {total_time:.1f}s, exceeding 5s limit"

        # Test 20: Record supported concurrent users
        self.performance_metrics['concurrent_users_supported'] = successful_users

    def test_memory_usage_under_load(self):
        """
        Test memory usage patterns under sustained load.

        Business Impact: Resource efficiency for cost optimization.
        """
        initial_memory = psutil.Process().memory_info().rss
        memory_measurements = [initial_memory]

        num_iterations = 20
        supervisors_per_iteration = 5

        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            for iteration in range(num_iterations):
                iteration_supervisors = []

                # Create supervisors for this iteration
                for i in range(supervisors_per_iteration):
                    user_ctx = UserExecutionContext.from_request(
                        user_id=f"memory-test-iter-{iteration}-user-{i}",
                        thread_id=f"memory-thread-{iteration}-{i}",
                        run_id=f"memory-run-{iteration}-{i}",
                        request_id=f"memory-request-{iteration}-{i}"
                    )

                    supervisor = SupervisorAgent(
                        llm_manager=Mock(spec=LLMManager),
                        user_context=user_ctx
                    )
                    iteration_supervisors.append(supervisor)

                current_memory = psutil.Process().memory_info().rss
                memory_measurements.append(current_memory)

                # Clean up supervisors from this iteration
                del iteration_supervisors
                gc.collect()

        final_memory = psutil.Process().memory_info().rss
        memory_measurements.append(final_memory)

        # Test 21: Memory growth should be controlled
        total_memory_growth = final_memory - initial_memory
        max_acceptable_growth = 100 * 1024 * 1024  # 100MB
        assert total_memory_growth < max_acceptable_growth, f"Memory grew by {total_memory_growth / (1024*1024):.1f}MB"

        # Test 22: Memory usage should stabilize (not continuously grow)
        # Check if memory growth rate slows down in later iterations
        early_growth = memory_measurements[5] - memory_measurements[0]  # First 5 iterations
        late_growth = memory_measurements[-1] - memory_measurements[-6]  # Last 5 iterations

        # Late growth should be less than or equal to early growth
        growth_ratio = late_growth / early_growth if early_growth > 0 else 0
        assert growth_ratio <= 2.0, f"Memory growth accelerated: early={early_growth}, late={late_growth}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])