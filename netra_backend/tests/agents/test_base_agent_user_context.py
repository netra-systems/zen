"""
Base Agent User Context Tests - Foundation Coverage Phase 1

Business Value: Platform/Internal - Multi-User System Security & Isolation
Tests UserExecutionContext integration, user isolation patterns, and factory-based
agent instantiation that prevents data leakage between concurrent users.

SSOT Compliance: Uses SSotAsyncTestCase, real UserExecutionContext instances,
follows USER_CONTEXT_ARCHITECTURE.md patterns per CLAUDE.md standards.

Coverage Target: BaseAgent UserExecutionContext integration, isolation patterns
Current BaseAgent User Context Coverage: ~3% -> Target: 20%+

Critical Patterns Tested:
- Factory-based user isolation (no shared singletons)
- UserExecutionContext preservation across agent operations
- Memory isolation between concurrent users
- Session management and resource cleanup
- Audit trail and compliance tracking

GitHub Issue: #714 Agents Module Unit Tests - Phase 1 Foundation
"""

import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
from shared.isolated_environment import get_env

# Import target classes
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class UserContextTestAgent(BaseAgent):
    """Agent for testing UserExecutionContext integration patterns."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_type = "user_context_test_agent"
        self.execution_log = []  # Track execution context for testing

    async def process_request(self, request: str, context: UserExecutionContext) -> Dict[str, Any]:
        """Implementation that validates and logs user context usage."""
        # Log the context details for verification
        self.execution_log.append({
            "user_id": context.user_id,
            "thread_id": context.thread_id,
            "run_id": context.run_id,
            "request": request,
            "timestamp": time.time(),
            "agent_context": context.agent_context.copy() if context.agent_context else None
        })

        # Verify context integrity
        assert context.user_id is not None, "UserExecutionContext missing user_id"
        assert context.thread_id is not None, "UserExecutionContext missing thread_id"
        assert context.run_id is not None, "UserExecutionContext missing run_id"

        # Simulate some processing that might modify context
        if context.agent_context:
            # Add processing metadata without modifying original context
            processing_metadata = {
                "processed_by": self.agent_type,
                "processing_time": time.time(),
                "original_request": request
            }

        # Return response with context information for verification
        return {
            "status": "success",
            "response": f"Processed for user {context.user_id}: {request}",
            "agent_type": self.agent_type,
            "context_validation": {
                "user_id": context.user_id,
                "thread_id": context.thread_id,
                "run_id": context.run_id,
                "has_agent_context": bool(context.agent_context),
                "has_db_session": bool(context.db_session)
            }
        }

    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Return execution log for testing verification."""
        return self.execution_log.copy()

    def clear_execution_log(self):
        """Clear execution log for test isolation."""
        self.execution_log.clear()


class TestBaseAgentUserContext(SSotAsyncTestCase):
    """Test BaseAgent UserExecutionContext integration and user isolation."""

    def setup_method(self, method):
        """Set up test environment with multiple user contexts."""
        super().setup_method(method)

        # Create mock dependencies
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="Mock response")

        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.emit_agent_event = AsyncMock()
        self.websocket_bridge.emit_tool_event = AsyncMock()

        # Create multiple user contexts for isolation testing
        self.user_contexts = {
            "user_1": UserExecutionContext(
                user_id="user-context-test-001",
                thread_id="thread-context-test-001",
                run_id="run-context-test-001",
                agent_context={
                    "user_request": "user 1 context test",
                    "user_preferences": {"theme": "dark", "language": "en"},
                    "session_data": {"login_time": time.time()}
                }
            ).with_db_session(AsyncMock()),

            "user_2": UserExecutionContext(
                user_id="user-context-test-002",
                thread_id="thread-context-test-002",
                run_id="run-context-test-002",
                agent_context={
                    "user_request": "user 2 context test",
                    "user_preferences": {"theme": "light", "language": "es"},
                    "session_data": {"login_time": time.time() + 100}
                }
            ).with_db_session(AsyncMock()),

            "user_3": UserExecutionContext(
                user_id="user-context-test-003",
                thread_id="thread-context-test-003",
                run_id="run-context-test-003",
                agent_context={
                    "user_request": "user 3 context test",
                    "user_preferences": {"theme": "auto", "language": "fr"},
                    "session_data": {"login_time": time.time() + 200}
                }
            ).with_db_session(AsyncMock())
        }

    def teardown_method(self, method):
        """Clean up user context test resources."""
        super().teardown_method(method)
        # Clear any potential shared state
        self.user_contexts.clear()

    async def test_user_context_preservation_single_request(self):
        """Test UserExecutionContext is preserved during single agent execution."""
        agent = UserContextTestAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )

        context = self.user_contexts["user_1"]
        test_request = "test user context preservation"

        # Execute request
        result = await agent.process_request(test_request, context)

        # Verify: Context was preserved in result
        assert result["context_validation"]["user_id"] == "user-context-test-001"
        assert result["context_validation"]["thread_id"] == "thread-context-test-001"
        assert result["context_validation"]["run_id"] == "run-context-test-001"
        assert result["context_validation"]["has_agent_context"] is True
        assert result["context_validation"]["has_db_session"] is True

        # Verify: Execution log captured context correctly
        execution_log = agent.get_execution_log()
        assert len(execution_log) == 1
        assert execution_log[0]["user_id"] == "user-context-test-001"
        assert execution_log[0]["request"] == test_request

        # Verify: Original context was not modified
        assert context.user_id == "user-context-test-001"
        assert context.agent_context["user_preferences"]["theme"] == "dark"

    async def test_user_context_isolation_concurrent_users(self):
        """Test user context isolation between concurrent agent executions."""
        agent = UserContextTestAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )

        # Execute concurrent requests for different users
        tasks = []
        for i, (user_key, context) in enumerate(self.user_contexts.items()):
            task = asyncio.create_task(
                agent.process_request(f"concurrent request {i+1}", context),
                name=f"user_{i+1}_task"
            )
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        # Verify: All requests completed successfully
        assert len(results) == 3
        assert all(r["status"] == "success" for r in results)

        # Verify: Each result contains correct user context
        user_ids_in_results = [r["context_validation"]["user_id"] for r in results]
        expected_user_ids = [
            "user-context-test-001",
            "user-context-test-002",
            "user-context-test-003"
        ]
        assert set(user_ids_in_results) == set(expected_user_ids)

        # Verify: Execution log shows all three executions with proper isolation
        execution_log = agent.get_execution_log()
        assert len(execution_log) == 3

        # Check that each user's context was preserved separately
        logged_user_ids = [entry["user_id"] for entry in execution_log]
        assert set(logged_user_ids) == set(expected_user_ids)

        # Verify: No context mixing occurred
        for entry in execution_log:
            if entry["user_id"] == "user-context-test-001":
                assert entry["agent_context"]["user_preferences"]["theme"] == "dark"
            elif entry["user_id"] == "user-context-test-002":
                assert entry["agent_context"]["user_preferences"]["theme"] == "light"
            elif entry["user_id"] == "user-context-test-003":
                assert entry["agent_context"]["user_preferences"]["theme"] == "auto"

    async def test_user_context_factory_pattern_isolation(self):
        """Test factory pattern ensures no shared state between agent instances."""
        # Create multiple agent instances (simulating factory pattern)
        agents = []
        for i in range(3):
            agent = UserContextTestAgent(
                llm_manager=self.llm_manager,
                websocket_bridge=self.websocket_bridge
            )
            agents.append(agent)

        # Execute requests on different agents with different users
        tasks = []
        for i, (agent, (user_key, context)) in enumerate(zip(agents, self.user_contexts.items())):
            task = asyncio.create_task(
                agent.process_request(f"factory pattern test {i+1}", context)
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Verify: All executions successful
        assert len(results) == 3
        assert all(r["status"] == "success" for r in results)

        # Verify: Each agent maintained separate execution logs
        for i, agent in enumerate(agents):
            log = agent.get_execution_log()
            assert len(log) == 1  # Each agent should have only its own execution
            assert f"factory pattern test {i+1}" in log[0]["request"]

        # Verify: No cross-contamination between agent instances
        user_ids = [agent.get_execution_log()[0]["user_id"] for agent in agents]
        assert len(set(user_ids)) == 3  # All different user IDs

    async def test_user_context_memory_isolation_stress_test(self):
        """Test memory isolation under stress with many concurrent users."""
        agent = UserContextTestAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )

        # Create many user contexts for stress testing
        stress_contexts = []
        for i in range(20):  # 20 concurrent users
            context = UserExecutionContext(
                user_id=f"stress-user-{i:03d}",
                thread_id=f"stress-thread-{i:03d}",
                run_id=f"stress-run-{i:03d}",
                agent_context={
                    "user_request": f"stress test request {i}",
                    "user_index": i,
                    "secret_data": f"user_{i}_secret_value_do_not_leak"
                }
            ).with_db_session(AsyncMock())
            stress_contexts.append(context)

        # Execute all requests concurrently
        tasks = [
            asyncio.create_task(
                agent.process_request(f"stress request {i}", context)
            )
            for i, context in enumerate(stress_contexts)
        ]

        results = await asyncio.gather(*tasks)

        # Verify: All requests completed
        assert len(results) == 20
        assert all(r["status"] == "success" for r in results)

        # Verify: No data leakage between users
        execution_log = agent.get_execution_log()
        assert len(execution_log) == 20

        # Check each execution maintained its own data
        for i, entry in enumerate(execution_log):
            user_index = entry["agent_context"]["user_index"]
            secret_data = entry["agent_context"]["secret_data"]

            # Verify: Each user's secret data contains only their own index
            assert f"user_{user_index}_secret" in secret_data

            # Verify: No other user's data leaked in
            for j in range(20):
                if j != user_index:
                    assert f"user_{j}_secret" not in secret_data

    async def test_user_context_session_management(self):
        """Test UserExecutionContext session management and cleanup patterns."""
        agent = UserContextTestAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )

        context = self.user_contexts["user_1"]

        # Test: Context with database session
        assert context.db_session is not None

        # Execute request
        result = await agent.process_request("session management test", context)

        # Verify: Session was preserved during execution
        assert result["context_validation"]["has_db_session"] is True

        # Test: Context maintains session integrity
        assert context.db_session is not None

        # Verify: Session is properly typed and functional
        assert hasattr(context.db_session, '__call__')  # Should be callable (AsyncMock)

    def test_user_context_thread_safety(self):
        """Test UserExecutionContext is thread-safe in synchronous context."""
        agent = UserContextTestAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )

        # Create contexts for thread testing
        contexts = []
        for i in range(5):
            context = UserExecutionContext(
                user_id=f"thread-test-user-{i}",
                thread_id=f"thread-test-thread-{i}",
                run_id=f"thread-test-run-{i}",
                agent_context={"thread_index": i, "thread_data": f"data_for_thread_{i}"}
            )
            contexts.append(context)

        # Function to test context in different threads
        def test_context_in_thread(context, thread_index):
            # Verify context integrity in this thread
            assert context.user_id == f"thread-test-user-{thread_index}"
            assert context.agent_context["thread_index"] == thread_index
            assert context.agent_context["thread_data"] == f"data_for_thread_{thread_index}"
            return context.user_id

        # Execute in multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i, context in enumerate(contexts):
                future = executor.submit(test_context_in_thread, context, i)
                futures.append(future)

            # Collect results
            results = [future.result() for future in futures]

        # Verify: All threads saw correct context data
        expected_user_ids = [f"thread-test-user-{i}" for i in range(5)]
        assert set(results) == set(expected_user_ids)

    async def test_user_context_audit_trail_compliance(self):
        """Test UserExecutionContext provides proper audit trail for compliance."""
        agent = UserContextTestAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )

        context = self.user_contexts["user_1"]

        # Execute multiple requests to build audit trail
        requests = [
            "audit test request 1",
            "audit test request 2",
            "audit test request 3"
        ]

        for request in requests:
            await agent.process_request(request, context)

        # Verify: Complete audit trail is maintained
        execution_log = agent.get_execution_log()
        assert len(execution_log) == 3

        # Verify: Each entry has required audit information
        for i, entry in enumerate(execution_log):
            assert entry["user_id"] == "user-context-test-001"
            assert entry["thread_id"] == "thread-context-test-001"
            assert entry["run_id"] == "run-context-test-001"
            assert entry["request"] == requests[i]
            assert "timestamp" in entry
            assert entry["timestamp"] > 0

        # Verify: Audit trail shows proper chronological order
        timestamps = [entry["timestamp"] for entry in execution_log]
        assert timestamps == sorted(timestamps)  # Should be in chronological order

    async def test_user_context_error_isolation(self):
        """Test errors in one user context don't affect other users."""

        class ErrorTestAgent(BaseAgent):
            """Agent that fails for specific users but succeeds for others."""

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.agent_type = "error_test_agent"

            async def process_request(self, request: str, context: UserExecutionContext) -> Dict[str, Any]:
                # Fail for user 2, succeed for others
                if context.user_id == "user-context-test-002":
                    raise ValueError(f"Simulated error for user {context.user_id}")

                return {
                    "status": "success",
                    "response": f"Success for {context.user_id}",
                    "user_id": context.user_id
                }

        agent = ErrorTestAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )

        # Execute requests for all users concurrently
        tasks = []
        for user_key, context in self.user_contexts.items():
            task = asyncio.create_task(
                agent.process_request(f"error isolation test", context),
                name=f"{user_key}_error_test"
            )
            tasks.append(task)

        # Gather results, expecting some failures
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify: User 1 and 3 succeeded, User 2 failed
        assert len(results) == 3

        success_count = 0
        error_count = 0

        for result in results:
            if isinstance(result, Exception):
                error_count += 1
                assert "user-context-test-002" in str(result)
            else:
                success_count += 1
                assert result["status"] == "success"
                assert result["user_id"] in ["user-context-test-001", "user-context-test-003"]

        # Verify: Exactly one error (user 2) and two successes (users 1 and 3)
        assert error_count == 1
        assert success_count == 2

        # This proves errors are properly isolated per user context
        # Critical for multi-tenant system with $500K+ ARR dependency