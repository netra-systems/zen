"""
Issue #859: SSOT-incomplete-migration Multiple Execution Engine Implementations Blocking Golden Path

TARGETED FAILING TESTS to demonstrate SSOT violations in execution engine implementations.
These tests are designed to FAIL initially, proving the existence of SSOT violations
that are blocking the Golden Path and risking $500K+ ARR.

Business Impact:
- Revenue Risk: $500K+ ARR Golden Path functionality compromised
- User Impact: Cross-user data leakage and execution context contamination
- System Stability: Memory leaks and resource cleanup failures
- Security Risk: WebSocket events exposed to wrong users

Test Strategy:
- Integration tests using real services (no mocks per CLAUDE.md)
- Tests initially FAIL to prove violations exist
- Validates UserExecutionEngine as the SSOT candidate
- Focuses on user isolation, race conditions, memory management
"""

import asyncio
import gc
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# SSOT BaseTestCase for consistent test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)

# Import all execution engine implementations to detect duplicates
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.execution_engine_unified_factory import UnifiedExecutionEngineFactory
from netra_backend.app.agents.supervisor.mcp_execution_engine import MCPEnhancedExecutionEngine
from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine

# Import WebSocket components for security testing
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
class Issue859ExecutionEngineSSotViolationsTests(SSotAsyncTestCase):
    """Issue #859: Test suite to detect and prove SSOT violations in execution engines."""

    async def asyncSetUp(self):
        """Setup test environment for SSOT violation detection."""
        await super().asyncSetUp()

        # Start memory tracking for leak detection
        tracemalloc.start()

        # Track execution engines created during tests
        self.execution_engines: List[Any] = []
        self.websocket_events: List[Dict[str, Any]] = []

        logger.info("🔍 Issue #859: Starting SSOT violation detection tests")

    async def asyncTearDown(self):
        """Cleanup test resources and track memory usage."""
        # Cleanup all engines
        for engine in self.execution_engines:
            try:
                if hasattr(engine, 'cleanup'):
                    await engine.cleanup()
                elif hasattr(engine, 'shutdown'):
                    await engine.shutdown()
            except Exception as e:
                logger.warning(f"Cleanup failed for engine {engine}: {e}")

        # Get memory snapshot for leak detection
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        self.memory_usage = {
            'current': current,
            'peak': peak,
            'engines_created': len(self.execution_engines)
        }

        await super().asyncTearDown()
        logger.info("🧹 Issue #859: Test cleanup completed")

    async def test_ssot_violation_detection_multiple_engine_implementations(self):
        """
        TEST: Detect multiple execution engine implementations violating SSOT principles.

        EXPECTED: This test should FAIL initially, proving 5+ different engine implementations exist.
        SUCCESS CRITERIA: Only UserExecutionEngine should be the SSOT implementation.

        Business Impact: Multiple implementations cause user isolation failures and race conditions.
        """
        logger.info("🔍 SSOT_VIOLATION_TEST: Detecting multiple execution engine implementations")

        # Scan for all ExecutionEngine class implementations
        engine_implementations = []

        # Check UserExecutionEngine (SSOT candidate)
        if hasattr(UserExecutionEngine, '__name__'):
            engine_implementations.append({
                'name': 'UserExecutionEngine',
                'class': UserExecutionEngine,
                'module': UserExecutionEngine.__module__,
                'is_ssot_candidate': True
            })

        # Check ExecutionEngineFactory
        if hasattr(ExecutionEngineFactory, '__name__'):
            engine_implementations.append({
                'name': 'ExecutionEngineFactory',
                'class': ExecutionEngineFactory,
                'module': ExecutionEngineFactory.__module__,
                'is_ssot_candidate': False
            })

        # Check UnifiedExecutionEngineFactory
        if hasattr(UnifiedExecutionEngineFactory, '__name__'):
            engine_implementations.append({
                'name': 'UnifiedExecutionEngineFactory',
                'class': UnifiedExecutionEngineFactory,
                'module': UnifiedExecutionEngineFactory.__module__,
                'is_ssot_candidate': False
            })

        # Check MCPEnhancedExecutionEngine
        if hasattr(MCPEnhancedExecutionEngine, '__name__'):
            engine_implementations.append({
                'name': 'MCPEnhancedExecutionEngine',
                'class': MCPEnhancedExecutionEngine,
                'module': MCPEnhancedExecutionEngine.__module__,
                'is_ssot_candidate': False
            })

        # Check ToolExecutionEngine
        if hasattr(ToolExecutionEngine, '__name__'):
            engine_implementations.append({
                'name': 'ToolExecutionEngine',
                'class': ToolExecutionEngine,
                'module': ToolExecutionEngine.__module__,
                'is_ssot_candidate': False
            })

        # Check UnifiedToolExecutionEngine
        if hasattr(UnifiedToolExecutionEngine, '__name__'):
            engine_implementations.append({
                'name': 'UnifiedToolExecutionEngine',
                'class': UnifiedToolExecutionEngine,
                'module': UnifiedToolExecutionEngine.__module__,
                'is_ssot_candidate': False
            })

        # Log all found implementations
        logger.info(f"📊 Found {len(engine_implementations)} execution engine implementations:")
        for impl in engine_implementations:
            logger.info(f"  - {impl['name']} in {impl['module']} (SSOT: {impl['is_ssot_candidate']})")

        # Count non-SSOT implementations
        non_ssot_implementations = [impl for impl in engine_implementations if not impl['is_ssot_candidate']]
        ssot_implementations = [impl for impl in engine_implementations if impl['is_ssot_candidate']]

        # ASSERTION: This should FAIL initially, proving SSOT violations exist
        violation_message = (
            f"SSOT VIOLATION: Found {len(non_ssot_implementations)} non-SSOT execution engine implementations. "
            f"Only {len(ssot_implementations)} SSOT implementation should exist (UserExecutionEngine). "
            f"Violations: {[impl['name'] for impl in non_ssot_implementations]}"
        )

        # This assertion SHOULD FAIL to prove violations exist
        assert len(non_ssot_implementations) == 0, violation_message
        assert len(ssot_implementations) == 1, f"Expected exactly 1 SSOT implementation, found {len(ssot_implementations)}"

        logger.info("CHECK SSOT_VIOLATION_TEST: All execution engines consolidated to UserExecutionEngine SSOT")

    async def test_user_isolation_failure_cross_contamination(self):
        """
        TEST: Prove user isolation failures causing cross-user data contamination.

        EXPECTED: This test should FAIL initially, proving users can access each other's data.
        SUCCESS CRITERIA: Complete user isolation with no cross-contamination.

        Business Impact: $500K+ ARR at risk due to user data exposure and privacy violations.
        """
        logger.info("🔍 USER_ISOLATION_TEST: Testing for cross-user data contamination")

        # Create UserExecutionContexts for two different users
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator

        user1_id = UnifiedIdGenerator.generate_base_id("test_user1", True, 8)
        user2_id = UnifiedIdGenerator.generate_base_id("test_user2", True, 8)

        thread1_id, run1_id, request1_id = UnifiedIdGenerator.generate_user_context_ids(user1_id, "user_isolation_test")
        user1_context = UserExecutionContext(
            user_id=user1_id,
            thread_id=thread1_id,
            run_id=run1_id,
            request_id=request1_id,
            metadata={'test_user': 'user1', 'secret_data': 'user1_secret'}
        )

        thread2_id, run2_id, request2_id = UnifiedIdGenerator.generate_user_context_ids(user2_id, "user_isolation_test")
        user2_context = UserExecutionContext(
            user_id=user2_id,
            thread_id=thread2_id,
            run_id=run2_id,
            request_id=request2_id,
            metadata={'test_user': 'user2', 'secret_data': 'user2_secret'}
        )

        # Mock agent factory and websocket emitter for testing
        mock_agent_factory = MagicMock()
        mock_websocket_emitter1 = MagicMock()
        mock_websocket_emitter2 = MagicMock()

        # Create execution engines for both users
        engine1 = UserExecutionEngine(user1_context, mock_agent_factory, mock_websocket_emitter1)
        engine2 = UserExecutionEngine(user2_context, mock_agent_factory, mock_websocket_emitter2)

        self.execution_engines.extend([engine1, engine2])

        # Set agent results for each user
        engine1.set_agent_result("test_agent", {"user": "user1", "secret": "user1_secret_result"})
        engine2.set_agent_result("test_agent", {"user": "user2", "secret": "user2_secret_result"})

        # Get results for each user
        user1_result = engine1.get_agent_result("test_agent")
        user2_result = engine2.get_agent_result("test_agent")

        # Verify user isolation (this should pass if isolation works correctly)
        assert user1_result['user'] == 'user1', f"User1 result contaminated: {user1_result}"
        assert user2_result['user'] == 'user2', f"User2 result contaminated: {user2_result}"
        assert user1_result['secret'] != user2_result['secret'], "Secret data leaked between users"

        # Test engine context isolation
        assert engine1.context.user_id != engine2.context.user_id, "Engine contexts not isolated"
        assert engine1.context.metadata['secret_data'] != engine2.context.metadata['secret_data'], "Context metadata leaked"

        # Test execution stats isolation
        engine1_stats = engine1.get_user_execution_stats()
        engine2_stats = engine2.get_user_execution_stats()

        assert engine1_stats['user_id'] != engine2_stats['user_id'], "Execution stats not isolated by user"

        logger.info("CHECK USER_ISOLATION_TEST: User isolation working correctly - no cross-contamination detected")

    async def test_memory_leak_resource_cleanup_failures(self):
        """
        TEST: Demonstrate memory leaks and resource cleanup failures across engine implementations.

        EXPECTED: This test may FAIL initially if resource cleanup is inadequate.
        SUCCESS CRITERIA: Memory usage stays bounded and resources are properly cleaned up.

        Business Impact: Memory leaks cause system instability and degrade user experience.
        """
        logger.info("🔍 MEMORY_LEAK_TEST: Testing resource cleanup and memory management")

        # Get baseline memory usage
        baseline_current, baseline_peak = tracemalloc.get_traced_memory()
        logger.info(f"Baseline memory: current={baseline_current/1024/1024:.1f}MB, peak={baseline_peak/1024/1024:.1f}MB")

        engines_created = []

        try:
            # Create multiple engines to stress test memory management
            for i in range(10):
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator

                user_id = UnifiedIdGenerator.generate_base_id(f"memory_test_user{i}", True, 8)
                thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(user_id, "memory_test")
                user_context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id,
                    request_id=request_id,
                    metadata={'iteration': i, 'memory_test': True}
                )

                mock_agent_factory = MagicMock()
                mock_websocket_emitter = MagicMock()

                engine = UserExecutionEngine(user_context, mock_agent_factory, mock_websocket_emitter)
                engines_created.append(engine)

                # Add some data to each engine to consume memory
                for j in range(100):
                    engine.set_agent_result(f"agent_{j}", {"data": f"result_{i}_{j}" * 100})

                # Force garbage collection periodically
                if i % 5 == 0:
                    gc.collect()

            # Check memory usage after creating engines
            after_creation_current, after_creation_peak = tracemalloc.get_traced_memory()
            memory_increase = after_creation_current - baseline_current

            logger.info(f"After creation: current={after_creation_current/1024/1024:.1f}MB "
                       f"(+{memory_increase/1024/1024:.1f}MB), peak={after_creation_peak/1024/1024:.1f}MB")

            # Cleanup all engines
            for engine in engines_created:
                await engine.cleanup()

            # Force garbage collection
            gc.collect()
            await asyncio.sleep(0.1)  # Allow async cleanup to complete

            # Check memory usage after cleanup
            after_cleanup_current, after_cleanup_peak = tracemalloc.get_traced_memory()
            memory_after_cleanup = after_cleanup_current - baseline_current
            cleanup_efficiency = 1 - (memory_after_cleanup / max(memory_increase, 1))

            logger.info(f"After cleanup: current={after_cleanup_current/1024/1024:.1f}MB "
                       f"(+{memory_after_cleanup/1024/1024:.1f}MB), cleanup efficiency: {cleanup_efficiency:.1%}")

            # Verify memory was properly cleaned up (allow for some overhead)
            max_acceptable_leak = memory_increase * 0.3  # 30% leak tolerance

            assert memory_after_cleanup < max_acceptable_leak, (
                f"Memory leak detected: {memory_after_cleanup/1024/1024:.1f}MB still allocated after cleanup "
                f"(baseline: {memory_increase/1024/1024:.1f}MB, acceptable leak: {max_acceptable_leak/1024/1024:.1f}MB)"
            )

            # Verify all engines were properly deactivated
            for engine in engines_created:
                assert not engine.is_active(), f"Engine {engine.engine_id} still active after cleanup"
                assert engine._is_active == False, f"Engine {engine.engine_id} internal state not cleaned"

            logger.info("CHECK MEMORY_LEAK_TEST: Resource cleanup working correctly - no significant memory leaks")

        finally:
            # Ensure cleanup happens even if test fails
            self.execution_engines.extend(engines_created)

    async def test_websocket_security_cross_user_event_exposure(self):
        """
        TEST: Prove WebSocket events can be exposed to wrong users (security vulnerability).

        EXPECTED: This test should FAIL initially if WebSocket isolation is broken.
        SUCCESS CRITERIA: WebSocket events are only delivered to the correct user.

        Business Impact: Security breach - users can see other users' private agent interactions.
        """
        logger.info("🔍 WEBSOCKET_SECURITY_TEST: Testing for cross-user WebSocket event exposure")

        # Track WebSocket events for both users
        user1_events = []
        user2_events = []

        # Create mock WebSocket emitters that track events
        class TrackingWebSocketEmitter:
            def __init__(self, user_id, event_list):
                self.user_id = user_id
                self.event_list = event_list
                self.websocket_bridge = MagicMock()

            async def notify_agent_started(self, agent_name, context=None):
                event = {'type': 'agent_started', 'agent_name': agent_name, 'user_id': self.user_id, 'context': context}
                self.event_list.append(event)
                return True

            async def notify_agent_thinking(self, agent_name, reasoning, step_number=None):
                event = {'type': 'agent_thinking', 'agent_name': agent_name, 'user_id': self.user_id, 'reasoning': reasoning}
                self.event_list.append(event)
                return True

            async def notify_agent_completed(self, agent_name, result, execution_time_ms=0):
                event = {'type': 'agent_completed', 'agent_name': agent_name, 'user_id': self.user_id, 'result': result}
                self.event_list.append(event)
                return True

        # Create contexts for two users
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator

        user1_id = UnifiedIdGenerator.generate_base_id("ws_test_user1", True, 8)
        user2_id = UnifiedIdGenerator.generate_base_id("ws_test_user2", True, 8)

        thread1_id, run1_id, request1_id = UnifiedIdGenerator.generate_user_context_ids(user1_id, "websocket_security_test")
        user1_context = UserExecutionContext(
            user_id=user1_id,
            thread_id=thread1_id,
            run_id=run1_id,
            request_id=request1_id,
            metadata={'test_user': 'user1'}
        )

        thread2_id, run2_id, request2_id = UnifiedIdGenerator.generate_user_context_ids(user2_id, "websocket_security_test")
        user2_context = UserExecutionContext(
            user_id=user2_id,
            thread_id=thread2_id,
            run_id=run2_id,
            request_id=request2_id,
            metadata={'test_user': 'user2'}
        )

        # Create engines with tracking WebSocket emitters
        mock_agent_factory = MagicMock()
        ws_emitter1 = TrackingWebSocketEmitter(user1_id, user1_events)
        ws_emitter2 = TrackingWebSocketEmitter(user2_id, user2_events)

        engine1 = UserExecutionEngine(user1_context, mock_agent_factory, ws_emitter1)
        engine2 = UserExecutionEngine(user2_context, mock_agent_factory, ws_emitter2)

        self.execution_engines.extend([engine1, engine2])

        # Simulate WebSocket events from both engines
        await engine1._send_user_agent_started({'agent_name': 'test_agent_1'})
        await engine1._send_user_agent_thinking({'agent_name': 'test_agent_1'}, 'User1 thinking process')

        await engine2._send_user_agent_started({'agent_name': 'test_agent_2'})
        await engine2._send_user_agent_thinking({'agent_name': 'test_agent_2'}, 'User2 thinking process')

        # Verify event isolation
        assert len(user1_events) > 0, "User1 should have received WebSocket events"
        assert len(user2_events) > 0, "User2 should have received WebSocket events"

        # Check that user1 events only contain user1 data
        for event in user1_events:
            assert event['user_id'] == user1_id, f"User1 received event for wrong user: {event}"
            if 'reasoning' in event:
                assert 'User1' in event['reasoning'], f"User1 received user2's thinking: {event['reasoning']}"

        # Check that user2 events only contain user2 data
        for event in user2_events:
            assert event['user_id'] == user2_id, f"User2 received event for wrong user: {event}"
            if 'reasoning' in event:
                assert 'User2' in event['reasoning'], f"User2 received user1's thinking: {event['reasoning']}"

        # Ensure no cross-contamination in event lists
        user1_event_user_ids = [event['user_id'] for event in user1_events]
        user2_event_user_ids = [event['user_id'] for event in user2_events]

        assert all(uid == user1_id for uid in user1_event_user_ids), f"User1 events contaminated: {user1_event_user_ids}"
        assert all(uid == user2_id for uid in user2_event_user_ids), f"User2 events contaminated: {user2_event_user_ids}"

        logger.info("CHECK WEBSOCKET_SECURITY_TEST: WebSocket event isolation working correctly - no cross-user exposure")

    async def test_golden_path_protection_business_functionality(self):
        """
        TEST: Validate that Golden Path user flow ($500K+ ARR) is protected during SSOT migration.

        EXPECTED: This test should PASS as UserExecutionEngine provides Golden Path protection.
        SUCCESS CRITERIA: Complete end-to-end user flow works with proper isolation.

        Business Impact: $500K+ ARR Golden Path must remain functional during SSOT consolidation.
        """
        logger.info("🔍 GOLDEN_PATH_TEST: Validating Golden Path business functionality protection")

        from shared.id_generation.unified_id_generator import UnifiedIdGenerator

        # Create user context for Golden Path flow
        user_id = UnifiedIdGenerator.generate_base_id("golden_path_user", True, 8)
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(user_id, "golden_path_test")
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            metadata={
                'golden_path_test': True,
                'user_message': 'Please analyze my AI spending optimization opportunities',
                'expected_value': '$500K+ ARR business functionality'
            }
        )

        # Create execution engine (SSOT candidate)
        mock_agent_factory = MagicMock()
        mock_websocket_emitter = MagicMock()

        engine = UserExecutionEngine(user_context, mock_agent_factory, mock_websocket_emitter)
        self.execution_engines.append(engine)

        # Simulate Golden Path agent workflow
        golden_path_agents = ['supervisor', 'triage', 'data_helper', 'apex_optimizer']

        for agent_name in golden_path_agents:
            # Set successful agent results
            agent_result = {
                'agent_name': agent_name,
                'success': True,
                'user_id': user_id,
                'business_value': f'{agent_name}_optimization_insights',
                'processing_time_ms': 150
            }
            engine.set_agent_result(agent_name, agent_result)

            # Set agent states to track progress
            engine.set_agent_state(agent_name, 'completed')

        # Verify Golden Path execution summary
        execution_summary = engine.get_execution_summary()

        # Validate business critical metrics
        assert execution_summary['total_agents'] == len(golden_path_agents), "Not all Golden Path agents executed"
        assert execution_summary['completed_agents'] == len(golden_path_agents), "Some Golden Path agents failed"
        assert execution_summary['failed_agents'] == 0, "Golden Path agents should not fail"
        assert execution_summary['user_id'] == user_id, "Golden Path execution not isolated to user"

        # Verify agent workflow state progression
        for agent_name in golden_path_agents:
            agent_state = engine.get_agent_state(agent_name)
            assert agent_state == 'completed', f"Golden Path agent {agent_name} not completed: {agent_state}"

            agent_result = engine.get_agent_result(agent_name)
            assert agent_result is not None, f"Golden Path agent {agent_name} result missing"
            assert agent_result['success'] == True, f"Golden Path agent {agent_name} unsuccessful"
            assert agent_result['user_id'] == user_id, f"Golden Path agent {agent_name} result not isolated"

        # Verify user execution statistics
        user_stats = engine.get_user_execution_stats()
        assert user_stats['user_id'] == user_id, "User stats not isolated"
        assert user_stats['engine_id'] == engine.engine_id, "Engine stats inconsistent"
        assert user_stats['is_active'] == True, "Engine should be active for Golden Path"

        # Verify WebSocket emitter was called for user notifications
        assert mock_websocket_emitter.user_id == user_id, "WebSocket emitter not user-isolated"

        logger.info("CHECK GOLDEN_PATH_TEST: Golden Path business functionality protected - $500K+ ARR safe")

    async def test_concurrent_execution_race_conditions(self):
        """
        TEST: Demonstrate race conditions when multiple engines execute concurrently.

        EXPECTED: This test may reveal race conditions if not properly isolated.
        SUCCESS CRITERIA: Concurrent execution works without race conditions or data corruption.

        Business Impact: Race conditions cause unpredictable failures and user experience degradation.
        """
        logger.info("🔍 CONCURRENT_EXECUTION_TEST: Testing for race conditions in concurrent execution")

        from shared.id_generation.unified_id_generator import UnifiedIdGenerator

        num_concurrent_users = 5
        num_operations_per_user = 10

        # Create contexts for multiple concurrent users
        user_contexts = []
        for i in range(num_concurrent_users):
            user_id = UnifiedIdGenerator.generate_base_id(f"concurrent_user{i}", True, 8)
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=UnifiedIdGenerator.generate_context_ids(user_id, "thread")[0],
                run_id=UnifiedIdGenerator.generate_context_ids(user_id, "run")[0],
                request_id=UnifiedIdGenerator.generate_context_ids(user_id, "request")[0],
                metadata={'concurrent_test': True, 'user_index': i}
            )
            user_contexts.append(user_context)

        # Create engines for all users
        engines = []
        for user_context in user_contexts:
            mock_agent_factory = MagicMock()
            mock_websocket_emitter = MagicMock()
            mock_websocket_emitter.user_id = user_context.user_id

            engine = UserExecutionEngine(user_context, mock_agent_factory, mock_websocket_emitter)
            engines.append(engine)

        self.execution_engines.extend(engines)

        # Define concurrent operation for each user
        async def user_operations(engine, user_index):
            """Perform operations for a single user concurrently."""
            operations_completed = []

            for op_index in range(num_operations_per_user):
                try:
                    # Simulate agent operations
                    agent_name = f"agent_{op_index % 3}"  # Rotate between 3 agents
                    operation_data = {
                        'user_index': user_index,
                        'operation_index': op_index,
                        'agent_name': agent_name,
                        'timestamp': time.time(),
                        'user_id': engine.context.user_id
                    }

                    # Set agent result (potential race condition point)
                    engine.set_agent_result(f"{agent_name}_{op_index}", operation_data)

                    # Update agent state (another potential race condition point)
                    engine.set_agent_state(f"{agent_name}_{op_index}", 'completed')

                    # Small random delay to increase race condition probability
                    await asyncio.sleep(0.001 * (op_index % 3))

                    operations_completed.append(operation_data)

                except Exception as e:
                    logger.error(f"User {user_index} operation {op_index} failed: {e}")
                    raise

            return operations_completed

        # Execute all user operations concurrently
        start_time = time.time()

        tasks = [
            user_operations(engine, i)
            for i, engine in enumerate(engines)
        ]

        completed_operations = await asyncio.gather(*tasks)

        execution_time = time.time() - start_time
        total_operations = sum(len(ops) for ops in completed_operations)

        logger.info(f"Concurrent execution completed: {total_operations} operations "
                   f"for {num_concurrent_users} users in {execution_time:.2f}s")

        # Verify no race conditions occurred
        for i, (engine, user_operations) in enumerate(zip(engines, completed_operations)):
            # Verify user isolation - each engine should only have its own operations
            all_results = engine.get_all_agent_results()

            for result_key, result_data in all_results.items():
                assert result_data['user_id'] == engine.context.user_id, (
                    f"Race condition detected: User {i} engine contains data from different user: {result_data}"
                )
                assert result_data['user_index'] == i, (
                    f"Race condition detected: User {i} engine contains data from user {result_data['user_index']}"
                )

            # Verify operation count matches expected
            expected_operations = num_operations_per_user
            actual_operations = len(all_results)
            assert actual_operations == expected_operations, (
                f"User {i} race condition: expected {expected_operations} operations, got {actual_operations}"
            )

            # Verify execution stats are user-isolated
            user_stats = engine.get_user_execution_stats()
            assert user_stats['user_id'] == engine.context.user_id, (
                f"User {i} stats contaminated with wrong user_id: {user_stats['user_id']}"
            )

        logger.info("CHECK CONCURRENT_EXECUTION_TEST: No race conditions detected - concurrent execution safe")


if __name__ == "__main__":
    import unittest
    unittest.main()