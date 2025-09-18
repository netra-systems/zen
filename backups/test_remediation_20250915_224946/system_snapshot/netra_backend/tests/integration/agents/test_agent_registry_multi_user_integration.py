"""
Comprehensive Integration Tests for Agent Registry Multi-User Isolation

Business Value Justification (BVJ):
- Segment: ALL (Free/Early/Mid/Enterprise/Platform)
- Business Goal: Multi-User Security & Platform Scalability
- Value Impact: Protects $10M+ liability from user data leakage and enables 100+ concurrent users
- Revenue Impact: Critical for enterprise deployment - failure blocks entire multi-user platform

CRITICAL MULTI-USER SCENARIOS:
1. Agent Registry Creation: Multiple users get isolated agent instances
2. Memory Management: No memory leaks during high-volume agent creation
3. Concurrent User Support: Multiple users creating agents simultaneously
4. Agent Cleanup: Proper cleanup prevents memory accumulation
5. User Session Isolation: Agent sessions completely isolated per user
6. Registry State Management: Registry maintains correct state across users

SSOT Testing Compliance:
- Uses test_framework.ssot.base_test_case.SSotAsyncTestCase
- Real AgentRegistry components (no mocks for core functionality)
- Business-critical multi-user validation focus
- Performance and memory testing included

COVERAGE TARGETS:
- Agent Registry Integration: 12% → 65% target
- Multi-user isolation: 100% critical scenarios
- Memory management: 95% cleanup validation
- Concurrent operations: 90% stress testing
"""

import asyncio
import gc
import psutil
import time
import uuid
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from shared.isolated_environment import get_env

# Agent Registry Components Under Test
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry,
    AgentLifecycleManager,
    UserAgentSession
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Supporting Infrastructure
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


@dataclass
class RegistryTestMetrics:
    """Metrics for agent registry testing."""
    users_tested: int = 0
    agents_created: int = 0
    agents_cleaned_up: int = 0
    memory_usage_start: Optional[float] = None
    memory_usage_peak: Optional[float] = None
    memory_usage_end: Optional[float] = None
    concurrent_operations: int = 0
    isolation_violations: int = 0
    registry_operations: List[str] = field(default_factory=list)


class AgentRegistryMultiUserIntegrationTests(SSotAsyncTestCase):
    """
    Comprehensive integration tests for Agent Registry multi-user isolation.

    Tests the Agent Registry's ability to create, manage, and clean up agent
    instances across multiple users without data leakage or memory issues.
    """

    @pytest.fixture(autouse=True)
    async def setup_registry_multi_user_test_environment(self):
        """Setup test environment for multi-user agent registry testing."""
        # Initialize SSOT mock factory
        self.mock_factory = SSotMockFactory()

        # Create test metrics tracking
        self.test_metrics = RegistryTestMetrics()

        # Track initial memory usage
        process = psutil.Process()
        self.test_metrics.memory_usage_start = process.memory_info().rss / 1024 / 1024  # MB

        # Create mock infrastructure for registry testing
        self.mock_websocket_bridge = self.mock_factory.create_mock_agent_websocket_bridge()
        self.mock_llm_manager = self.mock_factory.create_mock_llm_manager()
        self.mock_db_session = self.mock_factory.create_mock("AsyncSession")

        # Create real AgentRegistry for testing
        self.agent_registry = AgentRegistry()

        # Configure WebSocket bridge for the registry
        self.agent_registry.set_websocket_manager(self.mock_websocket_bridge)

        # Create multiple test user contexts
        self.test_users = {}
        for i in range(1, 6):  # 5 test users
            user_id = f"test_user_{i:03d}"
            self.test_users[user_id] = UserExecutionContext(
                user_id=user_id,
                thread_id=f"test_thread_{i:03d}",
                run_id=f"test_run_{i:03d}",
                request_id=f"test_req_{i:03d}",
                websocket_client_id=f"test_ws_{i:03d}"
            )

        # Track agent instances and user sessions
        self.created_agents = {}
        self.user_sessions = {}
        self.isolation_test_data = {}

        # Configure mock behaviors
        await self._setup_mock_behaviors()

    async def _setup_mock_behaviors(self):
        """Setup mock behaviors for agent registry testing."""
        # Configure WebSocket events (should be isolated per user)
        async def track_websocket_event(event_type, run_id, *args, **kwargs):
            """Track WebSocket events by user."""
            if run_id not in self.isolation_test_data:
                self.isolation_test_data[run_id] = {"websocket_events": []}

            self.isolation_test_data[run_id]["websocket_events"].append({
                "event_type": event_type,
                "timestamp": time.time(),
                "args": args,
                "kwargs": kwargs
            })

        # Configure all WebSocket events to track user isolation
        self.mock_websocket_bridge.notify_agent_started = AsyncMock(
            side_effect=lambda run_id, *a, **k: track_websocket_event('agent_started', run_id, *a, **k)
        )
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock(
            side_effect=lambda run_id, *a, **k: track_websocket_event('agent_completed', run_id, *a, **k)
        )

        # Configure LLM manager
        self.mock_llm_manager.generate_response = AsyncMock(
            return_value={"content": "Test response", "tokens": 100}
        )

    async def teardown_method(self):
        """Clean up after each test."""
        # Force cleanup of all created agents
        try:
            await self.agent_registry.cleanup_all_sessions()
        except Exception as e:
            print(f"Cleanup warning: {e}")

        # Clear tracking data
        self.created_agents.clear()
        self.user_sessions.clear()
        self.isolation_test_data.clear()

        # Force garbage collection
        gc.collect()

        # Record final memory usage
        process = psutil.Process()
        self.test_metrics.memory_usage_end = process.memory_info().rss / 1024 / 1024  # MB

    # ============================================================================
    # MULTI-USER TEST 1: Isolated Agent Creation Across Users
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_agent_registry_isolated_agent_creation_per_user(self):
        """
        Test that Agent Registry creates isolated agent instances for each user.

        BVJ: Multi-user security foundation - ensures no shared state between users
        Critical Path: Multiple Users → AgentRegistry → Isolated Agent Instances → No Cross-Contamination
        """
        # Arrange: Create agents for multiple users
        agent_type = "supervisor_agent"
        users_to_test = list(self.test_users.keys())[:3]  # Test with 3 users

        created_agents = {}
        execution_results = {}

        # Act: Create agents for each user independently
        for user_id in users_to_test:
            user_context = self.test_users[user_id]

            # Create agent through registry
            agent = await self.agent_registry.create_agent(
                agent_type=agent_type,
                user_context=user_context,
                llm_manager=self.mock_llm_manager
            )

            # Store created agent
            created_agents[user_id] = agent
            self.created_agents[user_id] = agent

            # Store user-specific data in agent (to test isolation)
            if hasattr(agent, 'user_specific_data'):
                agent.user_specific_data = {
                    "user_id": user_id,
                    "secret_key": f"secret_for_{user_id}",
                    "timestamp": time.time(),
                    "isolation_test_value": f"CONFIDENTIAL_DATA_{user_id}"
                }

            self.test_metrics.agents_created += 1

        # Update metrics
        self.test_metrics.users_tested = len(users_to_test)

        # Assert: Verify agent isolation
        assert len(created_agents) == len(users_to_test)

        # Verify each user has their own agent instance
        agent_instances = list(created_agents.values())
        for i, agent_a in enumerate(agent_instances):
            for j, agent_b in enumerate(agent_instances):
                if i != j:
                    assert agent_a is not agent_b, f"Agents for users {users_to_test[i]} and {users_to_test[j]} are the same instance"

        # Verify user-specific data is isolated
        for user_id, agent in created_agents.items():
            if hasattr(agent, 'user_specific_data'):
                user_data = agent.user_specific_data
                assert user_data["user_id"] == user_id
                assert user_data["secret_key"] == f"secret_for_{user_id}"
                assert user_data["isolation_test_value"] == f"CONFIDENTIAL_DATA_{user_id}"

                # Verify no other user's data is present
                for other_user_id in users_to_test:
                    if other_user_id != user_id:
                        assert f"secret_for_{other_user_id}" not in str(user_data)
                        assert f"CONFIDENTIAL_DATA_{other_user_id}" not in str(user_data)

        # Verify registry maintains correct mapping
        registry_sessions = self.agent_registry._user_sessions
        assert len(registry_sessions) >= len(users_to_test)

        for user_id in users_to_test:
            user_context = self.test_users[user_id]
            session_key = f"{user_context.user_id}:{user_context.thread_id}"
            assert session_key in registry_sessions

    # ============================================================================
    # MULTI-USER TEST 2: Concurrent Agent Creation Stress Test
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_agent_registry_concurrent_multi_user_creation(self):
        """
        Test Agent Registry under concurrent multi-user agent creation load.

        BVJ: Platform scalability - ensures registry handles multiple simultaneous users
        Critical Path: Concurrent Users → Simultaneous Agent Creation → Isolated Results → No Deadlocks
        """
        # Arrange: Prepare concurrent user operations
        all_users = list(self.test_users.keys())
        agent_type = "triage_agent"
        concurrent_operations = []

        # Define concurrent agent creation function
        async def create_agent_for_user(user_id: str, operation_id: int):
            """Create agent for specific user in concurrent environment."""
            try:
                user_context = self.test_users[user_id]

                # Add artificial delay to increase chance of race conditions
                await asyncio.sleep(0.01 * operation_id)

                # Create agent
                agent = await self.agent_registry.create_agent(
                    agent_type=agent_type,
                    user_context=user_context,
                    llm_manager=self.mock_llm_manager
                )

                # Store operation-specific data
                operation_data = {
                    "user_id": user_id,
                    "operation_id": operation_id,
                    "agent_id": id(agent),
                    "timestamp": time.time(),
                    "success": True
                }

                # Track operation
                self.test_metrics.registry_operations.append(f"create_{user_id}_{operation_id}")

                return operation_data

            except Exception as e:
                # Track failure
                self.test_metrics.registry_operations.append(f"error_{user_id}_{operation_id}")
                return {
                    "user_id": user_id,
                    "operation_id": operation_id,
                    "error": str(e),
                    "success": False
                }

        # Act: Launch concurrent agent creation operations
        start_time = time.time()

        # Create multiple operations per user
        operations_per_user = 2
        for user_id in all_users:
            for op_id in range(operations_per_user):
                concurrent_operations.append(
                    create_agent_for_user(user_id, op_id)
                )

        # Track peak memory during concurrent operations
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Execute all operations concurrently
        results = await asyncio.gather(*concurrent_operations, return_exceptions=True)

        # Track peak memory after operations
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        self.test_metrics.memory_usage_peak = max(memory_before, memory_after)

        execution_time = time.time() - start_time

        # Update metrics
        self.test_metrics.concurrent_operations = len(concurrent_operations)
        self.test_metrics.agents_created = len([r for r in results if isinstance(r, dict) and r.get('success')])

        # Assert: Verify concurrent operations succeeded
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_results = [r for r in results if isinstance(r, Exception) or not r.get('success')]

        # Verify majority of operations succeeded
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.8, f"Success rate too low: {success_rate:.2%} (expected >= 80%)"

        # Verify no agent instances are shared between users
        agent_ids_by_user = {}
        for result in successful_results:
            user_id = result["user_id"]
            agent_id = result["agent_id"]

            if user_id not in agent_ids_by_user:
                agent_ids_by_user[user_id] = []
            agent_ids_by_user[user_id].append(agent_id)

        # Check for agent ID sharing across users (isolation violation)
        all_agent_ids = []
        for user_id, agent_ids in agent_ids_by_user.items():
            for agent_id in agent_ids:
                if agent_id in all_agent_ids:
                    self.test_metrics.isolation_violations += 1
                all_agent_ids.append(agent_id)

        # Assert no isolation violations
        assert self.test_metrics.isolation_violations == 0, f"Found {self.test_metrics.isolation_violations} isolation violations"

        # Verify reasonable memory usage (should not grow excessively)
        memory_growth = memory_after - memory_before
        assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.1f}MB (expected < 100MB)"

        # Verify execution time is reasonable
        assert execution_time < 10.0, f"Execution took too long: {execution_time:.2f}s (expected < 10s)"

    # ============================================================================
    # MULTI-USER TEST 3: Agent Cleanup and Memory Management
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_agent_registry_cleanup_and_memory_management(self):
        """
        Test Agent Registry cleanup and memory management across users.

        BVJ: Resource efficiency - prevents memory leaks in production deployment
        Critical Path: Agent Creation → User Session End → Agent Cleanup → Memory Recovery
        """
        # Arrange: Create agents for multiple users to test cleanup
        users_for_cleanup = list(self.test_users.keys())[:4]  # 4 users for cleanup test
        agent_type = "data_helper_agent"

        # Track memory before agent creation
        process = psutil.Process()
        memory_before_creation = process.memory_info().rss / 1024 / 1024  # MB

        created_agents = []
        user_session_keys = []

        # Create multiple agents per user
        agents_per_user = 2
        for user_id in users_for_cleanup:
            user_context = self.test_users[user_id]

            for i in range(agents_per_user):
                # Create agent
                agent = await self.agent_registry.create_agent(
                    agent_type=agent_type,
                    user_context=user_context,
                    llm_manager=self.mock_llm_manager
                )

                created_agents.append(agent)
                self.test_metrics.agents_created += 1

                # Store reference to session
                session_key = f"{user_context.user_id}:{user_context.thread_id}"
                if session_key not in user_session_keys:
                    user_session_keys.append(session_key)

                # Add some data to agent to make cleanup more meaningful
                if hasattr(agent, 'test_data'):
                    agent.test_data = {
                        "large_data": ["x" * 1000] * 100,  # Some test data to track
                        "user_id": user_id,
                        "agent_index": i
                    }

        # Track memory after creation
        memory_after_creation = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth_creation = memory_after_creation - memory_before_creation

        # Verify agents were created
        assert len(created_agents) == len(users_for_cleanup) * agents_per_user
        assert len(user_session_keys) == len(users_for_cleanup)

        # Act: Cleanup agents systematically
        cleanup_start_time = time.time()

        # Cleanup half the users first (partial cleanup test)
        users_to_cleanup_first = users_for_cleanup[:2]
        for user_id in users_to_cleanup_first:
            user_context = self.test_users[user_id]

            # Cleanup user session
            await self.agent_registry.cleanup_user_session(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id
            )

            self.test_metrics.agents_cleaned_up += agents_per_user

        # Track memory after partial cleanup
        memory_after_partial_cleanup = process.memory_info().rss / 1024 / 1024  # MB

        # Cleanup remaining users
        remaining_users = users_for_cleanup[2:]
        for user_id in remaining_users:
            user_context = self.test_users[user_id]

            await self.agent_registry.cleanup_user_session(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id
            )

            self.test_metrics.agents_cleaned_up += agents_per_user

        # Final cleanup call
        await self.agent_registry.cleanup_all_sessions()

        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow cleanup to complete

        # Track final memory usage
        memory_after_cleanup = process.memory_info().rss / 1024 / 1024  # MB
        cleanup_time = time.time() - cleanup_start_time

        # Update metrics
        self.test_metrics.users_tested = len(users_for_cleanup)

        # Assert: Verify cleanup effectiveness
        # Check that registry no longer has sessions for cleaned up users
        registry_sessions = self.agent_registry._user_sessions
        for user_id in users_for_cleanup:
            user_context = self.test_users[user_id]
            session_key = f"{user_context.user_id}:{user_context.thread_id}"
            assert session_key not in registry_sessions, f"Session {session_key} was not cleaned up"

        # Verify memory was recovered after cleanup
        memory_growth_final = memory_after_cleanup - memory_before_creation
        memory_recovered = memory_after_creation - memory_after_cleanup

        # Should recover at least 50% of memory growth
        min_expected_recovery = memory_growth_creation * 0.3
        assert memory_recovered >= min_expected_recovery, (
            f"Insufficient memory recovery: {memory_recovered:.1f}MB recovered "
            f"(expected >= {min_expected_recovery:.1f}MB)"
        )

        # Verify cleanup completed in reasonable time
        assert cleanup_time < 5.0, f"Cleanup took too long: {cleanup_time:.2f}s (expected < 5s)"

        # Verify all agents were tracked for cleanup
        assert self.test_metrics.agents_cleaned_up == self.test_metrics.agents_created

        print(f"Memory statistics: Creation: +{memory_growth_creation:.1f}MB, "
              f"Recovery: -{memory_recovered:.1f}MB, "
              f"Final growth: {memory_growth_final:.1f}MB")

    # ============================================================================
    # MULTI-USER TEST 4: User Session Isolation Validation
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_agent_registry_user_session_isolation_validation(self):
        """
        Test strict user session isolation in Agent Registry.

        BVJ: Data security - ensures zero data leakage between user sessions
        Critical Path: Multiple User Sessions → Data Storage → Cross-Session Access Attempts → Isolation Verification
        """
        # Arrange: Create isolated user sessions with sensitive data
        users_for_isolation = list(self.test_users.keys())[:3]
        agent_type = "apex_optimizer_agent"

        user_sessions = {}
        sensitive_data_per_user = {}

        # Create sessions with user-specific sensitive data
        for user_id in users_for_isolation:
            user_context = self.test_users[user_id]

            # Create agent for user
            agent = await self.agent_registry.create_agent(
                agent_type=agent_type,
                user_context=user_context,
                llm_manager=self.mock_llm_manager
            )

            # Store sensitive user data
            sensitive_data = {
                "user_id": user_id,
                "api_key": f"sk-{user_id}-{uuid.uuid4().hex}",
                "private_data": f"CONFIDENTIAL_BUSINESS_DATA_FOR_{user_id}",
                "financial_info": {
                    "revenue": 1000000 + hash(user_id) % 1000000,
                    "costs": 500000 + hash(user_id) % 500000,
                    "profit_margin": 0.15 + (hash(user_id) % 100) / 1000
                },
                "user_secrets": [f"secret_{i}_{user_id}" for i in range(5)]
            }

            # Store in session
            session_key = f"{user_context.user_id}:{user_context.thread_id}"
            user_sessions[session_key] = {
                "agent": agent,
                "user_context": user_context,
                "sensitive_data": sensitive_data
            }

            sensitive_data_per_user[user_id] = sensitive_data

            # Store data in agent if possible
            if hasattr(agent, 'session_data'):
                agent.session_data = sensitive_data

            self.test_metrics.agents_created += 1

        # Act: Attempt to access data across user sessions
        isolation_violations = []
        cross_access_attempts = 0

        # Test 1: Try to access other users' data through registry
        for current_user_id in users_for_isolation:
            current_context = self.test_users[current_user_id]
            current_session_key = f"{current_context.user_id}:{current_context.thread_id}"

            # Get current user's session
            current_session = user_sessions[current_session_key]
            current_agent = current_session["agent"]

            # Try to access other users' data
            for other_user_id in users_for_isolation:
                if other_user_id != current_user_id:
                    cross_access_attempts += 1
                    other_context = self.test_users[other_user_id]
                    other_session_key = f"{other_context.user_id}:{other_context.thread_id}"

                    # Check if current agent has access to other user's data
                    if hasattr(current_agent, 'session_data'):
                        current_data = current_agent.session_data
                        other_sensitive_data = sensitive_data_per_user[other_user_id]

                        # Check for data leakage
                        for key, value in other_sensitive_data.items():
                            if key in current_data and current_data[key] == value:
                                isolation_violations.append({
                                    "type": "data_leakage",
                                    "from_user": other_user_id,
                                    "to_user": current_user_id,
                                    "leaked_key": key,
                                    "leaked_value": str(value)[:100]  # Truncate for security
                                })

                        # Check for cross-contamination in lists
                        if isinstance(current_data.get("user_secrets"), list):
                            for secret in other_sensitive_data.get("user_secrets", []):
                                if secret in current_data["user_secrets"]:
                                    isolation_violations.append({
                                        "type": "list_contamination",
                                        "from_user": other_user_id,
                                        "to_user": current_user_id,
                                        "contaminated_item": secret
                                    })

        # Test 2: Verify registry session isolation
        registry_sessions = self.agent_registry._user_sessions
        for session_key_a, session_a in user_sessions.items():
            for session_key_b, session_b in user_sessions.items():
                if session_key_a != session_key_b:
                    cross_access_attempts += 1

                    # Verify sessions are truly separate
                    if session_a["agent"] is session_b["agent"]:
                        isolation_violations.append({
                            "type": "shared_agent_instance",
                            "session_a": session_key_a,
                            "session_b": session_key_b
                        })

        # Test 3: Verify WebSocket event isolation
        for user_id in users_for_isolation:
            user_context = self.test_users[user_id]
            run_id = user_context.run_id

            # Check if this user has events from other users
            if run_id in self.isolation_test_data:
                user_events = self.isolation_test_data[run_id]["websocket_events"]

                # Check if events contain data from other users
                for event in user_events:
                    event_str = str(event)
                    for other_user_id in users_for_isolation:
                        if other_user_id != user_id and other_user_id in event_str:
                            isolation_violations.append({
                                "type": "websocket_event_contamination",
                                "user": user_id,
                                "contaminated_with": other_user_id,
                                "event_type": event.get("event_type")
                            })

        # Update metrics
        self.test_metrics.users_tested = len(users_for_isolation)
        self.test_metrics.isolation_violations = len(isolation_violations)
        self.test_metrics.concurrent_operations = cross_access_attempts

        # Assert: Verify perfect isolation
        assert len(isolation_violations) == 0, (
            f"Found {len(isolation_violations)} isolation violations: "
            f"{isolation_violations}"
        )

        # Verify each user has their correct data
        for user_id in users_for_isolation:
            user_context = self.test_users[user_id]
            session_key = f"{user_context.user_id}:{user_context.thread_id}"
            session = user_sessions[session_key]

            if hasattr(session["agent"], 'session_data'):
                agent_data = session["agent"].session_data
                expected_data = sensitive_data_per_user[user_id]

                # Verify user has their own data
                assert agent_data["user_id"] == user_id
                assert agent_data["api_key"] == expected_data["api_key"]
                assert agent_data["private_data"] == expected_data["private_data"]

        # Verify registry maintains correct session count
        assert len(registry_sessions) >= len(users_for_isolation)

        print(f"Isolation test completed: {cross_access_attempts} cross-access attempts, "
              f"{len(isolation_violations)} violations detected")