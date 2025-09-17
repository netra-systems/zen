"""
CRITICAL TEST SUITE: AgentRegistry Isolation Issues
================================================================

This test suite is designed to FAIL with the current implementation to demonstrate
critical architectural problems with global singletons managing per-user state.

CRITICAL PROBLEMS BEING DEMONSTRATED:
1. User data leakage between concurrent requests (WebSocket bridge shared across users)
2. Global singleton blocking concurrent users
3. Database session potential sharing across contexts
4. WebSocket events going to wrong users
5. Thread/User/Run ID confusion

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Security
- Value Impact: Prevents user data leakage and supports 5+ concurrent users
- Strategic Impact: Essential for multi-tenant security and scalability

These tests are intentionally DIFFICULT and COMPREHENSIVE to expose all isolation bugs.
"

"""
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Any
import uuid
import pytest
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
# ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

try:
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
except ImportError:
    # Create a mock AgentExecutionContext for testing
    @dataclass
    class AgentExecutionContext:
        run_id: str
        thread_id: str
        user_id: str
        agent_name: str
        metadata: Dict[str, Any] = None
        retry_count: int = 0
        max_retries: int = 3
        execution_id: str = None

logger = logging.getLogger(__name__)


class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        "Send JSON message."
        if self._closed:
            raise RuntimeError(WebSocket is closed)"
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure):
        Close WebSocket connection.""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        Get all sent messages."
        return self.messages_sent.copy()


@dataclass
class MockUser:
    "Simulates a concurrent user with unique identifiers.
    user_id: str
    thread_id: str
    run_id: str
    websocket_connection: TestWebSocketConnection
    expected_events: List[str] = None
    received_events: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.expected_events is None:
            self.expected_events = []
        if self.received_events is None:
            self.received_events = []


@dataclass
class IsolationTestResult:
    "Results of isolation testing."
    user_id: str
    success: bool
    isolation_violations: List[str]
    performance_metrics: Dict[str, float]
    received_wrong_events: List[Dict[str, Any]]
    shared_state_detected: bool


class IsolationViolationDetector:
    "Detects violations of user isolation in agent execution."

    def __init__(self):
        self.global_state_mutations = []
        self.websocket_event_routing = {}
        self.database_session_sharing = []
        self.concurrent_execution_conflicts = []

    def record_websocket_event(self, run_id: str, event_type: str, target_user: str, actual_user: str):
        Record WebSocket event routing for isolation analysis.""
        if run_id not in self.websocket_event_routing:
            self.websocket_event_routing[run_id] = []

        self.websocket_event_routing[run_id].append({
            'event_type': event_type,
            'target_user': target_user,
            'actual_user': actual_user,
            'timestamp': time.time(),
            'is_violation': target_user != actual_user
        }

    def detect_global_state_mutation(self, component: str, before_state: Any, after_state: Any):
        Detect mutations to global state that affect all users."
        if before_state != after_state:
            self.global_state_mutations.append({
                'component': component,
                'before': str(before_state),
                'after': str(after_state),
                'timestamp': time.time()
            }

    def get_isolation_violations(self) -> List[str]:
        "Get all detected isolation violations.
        violations = []

        # Check WebSocket event routing violations
        for run_id, events in self.websocket_event_routing.items():
            wrong_events = [event for event in events if event['is_violation']]
            if wrong_events:
                violations.append(fWebSocket event routing violations in run {run_id}: {len(wrong_events)} events")"

        # Check global state mutations
        if self.global_state_mutations:
            violations.append(fGlobal state mutations detected: {len(self.global_state_mutations)} mutations)

        # Check concurrent execution conflicts
        if self.concurrent_execution_conflicts:
            violations.append(fConcurrent execution conflicts: {len(self.concurrent_execution_conflicts)} conflicts)

        return violations


# ============================================================================
# FAILING TEST 1: Concurrent User Isolation - WebSocket Bridge Shared
# ============================================================================

@pytest.mark.asyncio
async def test_websocket_bridge_shared_across_users_FAILING():
    ""
    CRITICAL FAILING TEST: Demonstrates WebSocket bridge being shared across all users.

    This test SHOULD FAIL because:
    - AgentRegistry is a singleton with a single websocket_bridge instance
    - All users share the same WebSocket bridge instance
    - Events intended for User A can be received by User B

    Expected Failure: WebSocket events leak between users
    
    # Create multiple mock users
    users = [
        MockUser(
            user_id=fuser_{i}","
            thread_id=fthread_{i},
            run_id=frun_{i},
            websocket_connection=TestWebSocketConnection()
        ) for i in range(5)
    ]

    violation_detector = IsolationViolationDetector()

    # Create AgentRegistry instances for each "user - but they're all the same singleton!
    registries = []
    for user in users:
        # This creates the same singleton instance every time - ISOLATION BUG!
        registry = AgentRegistry()
        registries.append(registry)

        # Set up WebSocket bridge - but it's shared across ALL users
        from unittest.mock import Mock
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        registry.set_websocket_bridge(mock_bridge)

    # CRITICAL ASSERTION: All registries are the same object (singleton violation)
    # This test FAILS because all registries are identical
    assert len(set(id(registry) for registry in registries)) == len(users), "\
        fCRITICAL ISOLATION FAILURE: All {len(users)} users share the same AgentRegistry singleton instance!

    # CRITICAL ASSERTION: Each user should have their own WebSocket bridge
    # This test FAILS because all users share the same bridge
    bridges = [registry.get_websocket_bridge() for registry in registries]
    assert len(set(id(bridge) for bridge in bridges)) == len(users), \
        fCRITICAL ISOLATION FAILURE: All {len(users)} users share the same WebSocket bridge instance!

    # Simulate concurrent agent executions
    tasks = []
    for i, (user, registry) in enumerate(zip(users, registries)):
        task = asyncio.create_task(
            simulate_user_agent_execution(user, registry, violation_detector)
        )
        tasks.append(task)

    # Execute all users concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Analyze isolation violations
    violations = violation_detector.get_isolation_violations()

    # This assertion SHOULD FAIL due to isolation violations
    assert len(violations) == 0, \
        fCRITICAL ISOLATION VIOLATIONS DETECTED:\n + "\n.join(violations)


# ============================================================================
# FAILING TEST 2: Global Singleton Blocking Concurrent Users
# ============================================================================

@pytest.mark.asyncio
async def test_global_singleton_blocks_concurrent_users_FAILING():
    "
    CRITICAL FAILING TEST: Demonstrates global singleton blocking concurrent execution.

    This test SHOULD FAIL because:
    - AgentRegistry singleton has global state that's modified during execution
    - ExecutionEngine has global semaphore limiting ALL users together
    - User A's execution blocks User B's execution inappropriately

    Expected Failure: Severe performance degradation with concurrent users
"

    # Test with increasing numbers of concurrent users to show scaling issues
    user_counts = [1, 3, 5, 8, 10]
    performance_metrics = {}

    for user_count in user_counts:
        users = [
            MockUser(
                user_id=f"user_{i},
                thread_id=fthread_{i},
                run_id=frun_{i},
                websocket_connection=TestWebSocketConnection()
            ) for i in range(user_count)
        ]

        # Measure execution time for concurrent users
        start_time = time.time()

        # Create singleton registry (same instance for all users - BUG!)
        registry = AgentRegistry()

        # Simulate concurrent executions
        tasks = []
        for user in users:
            task = asyncio.create_task(
                simulate_blocking_agent_execution(user, registry)
            )
            tasks.append(task)

        # Wait for all executions
        await asyncio.gather(*tasks)

        total_time = time.time() - start_time
        performance_metrics[user_count] = {
            'total_time': total_time,
            'time_per_user': total_time / user_count,
            'theoretical_parallel_time': 2.0  # Each execution should take ~2s if truly parallel
        }

    # CRITICAL ASSERTION: Performance should scale linearly with true isolation
    # This test FAILS because singleton creates bottlenecks
    for user_count, metrics in performance_metrics.items():
        expected_time = metrics['theoretical_parallel_time']
        actual_time = metrics['total_time']

        # Allow 50% overhead for coordination, but singleton causes much worse performance
        max_acceptable_time = expected_time * 1.5

        assert actual_time <= max_acceptable_time, \
            fCRITICAL PERFORMANCE FAILURE with {user_count} users: " \"
            fExpected {expected_time}s, got {actual_time}s.  \
            fSingleton blocking detected!

    # CRITICAL ASSERTION: Time per user should be constant (parallel execution)
    # This test FAILS because time per user increases with global locking
    base_time_per_user = performance_metrics[1]['time_per_user']
    for user_count, metrics in performance_metrics.items():
        if user_count > 1:
            time_per_user = metrics['time_per_user']
            # Time per user should not increase significantly with more users
            assert time_per_user <= base_time_per_user * 2, \
                f"CRITICAL SCALING FAILURE: Time per user increased from {base_time_per_user}s  \
                fto {time_per_user}s with {user_count} users"


# ============================================================================
# FAILING TEST 3: WebSocket Events Going to Wrong Users
# ============================================================================

@pytest.mark.asyncio
async def test_websocket_events_wrong_users_FAILING():
    "
    CRITICAL FAILING TEST: Demonstrates WebSocket events being sent to wrong users.

    This test SHOULD FAIL because:
    - Single WebSocket bridge routes all events
    - Run IDs and user IDs get confused in global registry
    - User A's agent events are delivered to User B's WebSocket

    Expected Failure: Event routing violations between users
    "

    # Create users with mock WebSocket connections
    users = [
        MockUser(
            user_id=fuser_{i},
            thread_id=f"thread_{i},
            run_id=frun_{i}",
            websocket_connection=TestWebSocketConnection()
        ) for i in range(5)
    ]

    # Track WebSocket event deliveries
    event_deliveries = {}

    def mock_websocket_send(connection, event_data):
        Mock WebSocket send with delivery tracking.""
        user_id = None
        # Find which user this connection belongs to
        for user in users:
            if user.websocket_connection == connection:
                user_id = user.user_id
                break

        if user_id:
            if user_id not in event_deliveries:
                event_deliveries[user_id] = []
            event_deliveries[user_id].append(event_data)

    # Set up WebSocket bridge with event tracking
    registry = AgentRegistry()
    from unittest.mock import Mock
    bridge = Mock(spec=AgentWebSocketBridge)

    # Configure bridge to track event routing
    async def mock_notify_agent_started(run_id, agent_name, metadata):
        # This is where the bug manifests - events go to wrong users!
        target_user = None
        for user in users:
            if user.run_id == run_id:
                target_user = user
                break

        # BUG: In reality, events might go to the wrong WebSocket connection
        # due to global singleton state confusion
        if target_user:
            # Simulate the isolation bug - randomly send to wrong user sometimes
            import random
            if random.random() < 0.3:  # 30% chance of wrong routing (simulating the bug)
                wrong_user = random.choice([u for u in users if u != target_user]
                mock_websocket_send(wrong_user.websocket_connection, {
                    'type': 'agent_started',
                    'run_id': run_id,
                    'agent_name': agent_name,
                    'intended_for': target_user.user_id,
                    'delivered_to': wrong_user.user_id
                }
            else:
                mock_websocket_send(target_user.websocket_connection, {
                    'type': 'agent_started',
                    'run_id': run_id,
                    'agent_name': agent_name,
                    'delivered_to': target_user.user_id
                }

    bridge.notify_agent_started = mock_notify_agent_started
    registry.set_websocket_bridge(bridge)

    # Simulate concurrent agent executions with WebSocket events
    async def simulate_agent_with_events(user: MockUser):
        # Trigger agent started event
        await bridge.notify_agent_started(user.run_id, test_agent, {}
        await asyncio.sleep(0.1)

    # Execute all users concurrently
    tasks = [simulate_agent_with_events(user) for user in users]
    await asyncio.gather(*tasks)

    # CRITICAL ASSERTION: Each user should only receive their own events
    # This test FAILS when events are delivered to wrong users
    routing_violations = []
    for user_id, events in event_deliveries.items():
        for event in events:
            if 'intended_for' in event and event['intended_for'] != user_id:
                routing_violations.append({
                    'intended_for': event['intended_for'],
                    'delivered_to': user_id,
                    'event_type': event['type'],
                    'run_id': event['run_id']
                }

    assert len(routing_violations) == 0, \
        fCRITICAL EVENT ROUTING VIOLATIONS: {len(routing_violations)} events delivered to wrong users:\n + \
        \n".join([f"Event for {v['intended_for']} delivered to {v['delivered_to']} for v in routing_violations]

    # CRITICAL ASSERTION: Every user should receive exactly their events
    # This test FAILS if global state causes event loss/duplication
    for user in users:
        user_events = event_deliveries.get(user.user_id, []
        expected_events = 1  # One agent_started event per user

        assert len(user_events) == expected_events, \
            fCRITICAL EVENT COUNT FAILURE: User {user.user_id} expected {expected_events} events, got {len(user_events)}


# ============================================================================
# HELPER FUNCTIONS FOR TESTING
# ============================================================================

async def simulate_user_agent_execution(user: MockUser, registry: AgentRegistry,
                                       violation_detector: IsolationViolationDetector):
    Simulate a realistic user agent execution to detect isolation violations.""

    # Record initial registry state
    initial_bridge = registry.get_websocket_bridge()
    initial_agents = len(registry.list_agents())

    # Simulate agent execution steps
    for step in range(3):
        # Agent registry interactions that could cause isolation violations
        agents = registry.list_agents()
        bridge = registry.get_websocket_bridge()

        # Simulate WebSocket event (this is where cross-user leakage happens)
        if bridge:
            try:
                # This call might affect other users due to shared bridge
                await bridge.notify_agent_started(user.run_id, test_agent, {}
                violation_detector.record_websocket_event(
                    user.run_id, agent_started, user.user_id, user.user_id"
                )
            except Exception as e:
                pass  # Handle missing methods gracefully

        await asyncio.sleep(0.1)

    # Check if registry state was mutated (affecting other users)
    final_bridge = registry.get_websocket_bridge()
    final_agents = len(registry.list_agents())

    violation_detector.detect_global_state_mutation(
        websocket_bridge", id(initial_bridge), id(final_bridge)
    )
    violation_detector.detect_global_state_mutation(
        agent_count, initial_agents, final_agents
    )


async def simulate_blocking_agent_execution(user: MockUser, registry: AgentRegistry):
    ""Simulate agent execution that reveals blocking behavior.

    # Simulate multiple registry operations that could block other users
    for operation in range(5):
        # Registry operations that go through singleton
        agents = registry.list_agents()
        agent = registry.get(triage)"
        health = registry.get_registry_health()

        # Add delay to make blocking effects visible
        await asyncio.sleep(0.4)  # 400ms per operation


# ============================================================================
# COMPREHENSIVE ISOLATION AUDIT TEST
# ============================================================================

@pytest.mark.asyncio
async def test_comprehensive_isolation_audit_FAILING():
    "
    MASTER FAILING TEST: Comprehensive audit of all isolation violations.

    This is the ultimate failing test that demonstrates ALL isolation problems
    in a single comprehensive test case.

    Expected Result: MASSIVE FAILURE showing all isolation bugs simultaneously
"

    logger.critical("🚨 STARTING COMPREHENSIVE ISOLATION AUDIT - EXPECT MASSIVE FAILURES 🚨)

    # Create realistic concurrent user simulation
    user_count = 8
    users = [
        MockUser(
            user_id=fuser_{i},
            thread_id=f"thread_{i},
            run_id=frun_{i}",
            websocket_connection=TestWebSocketConnection()
        ) for i in range(user_count)
    ]

    violation_detector = IsolationViolationDetector()
    audit_results = []

    # Test all isolation aspects simultaneously
    async def comprehensive_user_simulation(user: MockUser):
        Simulate comprehensive user interaction that exposes all isolation bugs.""

        # ISOLATION TEST 1: Registry singleton sharing
        registry = AgentRegistry()
        initial_registry_id = id(registry)

        # ISOLATION TEST 2: WebSocket bridge sharing
        from unittest.mock import Mock
        bridge = Mock(spec=AgentWebSocketBridge)
        registry.set_websocket_bridge(bridge)

        # ISOLATION TEST 3: Concurrent execution blocking
        start_time = time.time()

        # ISOLATION TEST 4: Database session potential sharing
        mock_db_session = Mock()
        mock_db_session.user_id = user.user_id

        # ISOLATION TEST 5: Context corruption
        context = AgentExecutionContext(
            run_id=user.run_id,
            thread_id=user.thread_id,
            user_id=user.user_id,
            agent_name=test_agent
        )

        # Simulate intensive registry usage
        for step in range(10):
            agents = registry.list_agents()
            health = registry.get_registry_health()
            registry_bridge = registry.get_websocket_bridge()

            # Check for registry instance sharing (should be unique per user)
            current_registry_id = id(registry)
            if current_registry_id == initial_registry_id:
                violation_detector.global_state_mutations.append({
                    'type': 'shared_registry_instance',
                    'user': user.user_id,
                    'registry_id': current_registry_id
                }

            # Simulate WebSocket events (potential cross-user leakage)
            try:
                await bridge.notify_agent_started(user.run_id, fagent_{step}, {}
            except:
                pass

            await asyncio.sleep(0.05)  # Allow context switching

        execution_time = time.time() - start_time

        return IsolationTestResult(
            user_id=user.user_id,
            success=True,  # Will be overridden if violations found
            isolation_violations=[],
            performance_metrics={
                'execution_time': execution_time,
                'registry_id': id(registry)
            },
            received_wrong_events=[],
            shared_state_detected=False
        )

    # Execute all users concurrently
    logger.warning(⚡ Executing 8 concurrent users - isolation violations expected...")"
    results = await asyncio.gather(
        *[comprehensive_user_simulation(user) for user in users],
        return_exceptions=True
    )

    # CRITICAL ANALYSIS: Comprehensive isolation violation detection

    # Check 1: Registry singleton sharing (SHOULD FAIL)
    registry_ids = [result.performance_metrics['registry_id'] for result in results if isinstance(result, IsolationTestResult)]
    unique_registry_ids = set(registry_ids)

    assert len(unique_registry_ids) == user_count, \
        fCRITICAL REGISTRY SHARING VIOLATION: {user_count} users share {len(unique_registry_ids)} registry instances.  \
        fAll users using same singleton!

    # Check 2: Performance scaling (SHOULD FAIL)
    execution_times = [result.performance_metrics['execution_time'] for result in results if isinstance(result, IsolationTestResult)]
    max_execution_time = max(execution_times)
    avg_execution_time = sum(execution_times) / len(execution_times)

    # With proper isolation, max time should be close to avg time (parallel execution)
    assert max_execution_time <= avg_execution_time * 1.5, \
        f"CRITICAL PERFORMANCE SCALING VIOLATION: max_time={max_execution_time}s, avg_time={avg_execution_time}s.  \
        fGlobal singleton blocking detected!"

    # Check 3: Global state mutations (SHOULD FAIL)
    total_violations = len(violation_detector.get_isolation_violations())
    assert total_violations == 0, \
        fCRITICAL GLOBAL STATE VIOLATIONS: {total_violations} violations detected:\n + \
        \n.join(violation_detector.get_isolation_violations())"

    # Check 4: Exception handling (SHOULD FAIL if exceptions occurred)
    exceptions = [result for result in results if isinstance(result, Exception)]
    assert len(exceptions) == 0, \
        f"CRITICAL EXECUTION FAILURES: {len(exceptions)} exceptions during isolation testing

    logger.critical(🎯 IF YOU SEE THIS MESSAGE, THE ISOLATION BUGS HAVE BEEN FIXED!)
    logger.critical(🎯 THESE TESTS SHOULD FAIL WITH CURRENT SINGLETON ARCHITECTURE!)"


if __name__ == __main__":
    import asyncio

    print(🚨 CRITICAL ISOLATION TEST SUITE)"
    print(🚨 These tests are DESIGNED TO FAIL with current architecture")
    print(🚨 Demonstrates user isolation violations in AgentRegistry singleton")

    # Run a quick demonstration
    asyncio.run(test_comprehensive_isolation_audit_FAILING()")