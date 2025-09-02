"""
Mission Critical Test Suite: Singleton Removal Phase 2 Validation

CRITICAL: This test suite validates the removal of singleton patterns that prevent 
concurrent user isolation. These tests WILL FAIL until singleton patterns are 
properly replaced with factory patterns.

BUSINESS VALUE JUSTIFICATION:
- Segment: Enterprise/Platform
- Business Goal: Concurrent User Support & Stability
- Value Impact: Enables 10+ concurrent users without data leakage or blocking
- Strategic Impact: Foundation for enterprise scalability and user isolation

ARCHITECTURAL PROBLEMS TESTED:
1. WebSocketManager singleton prevents per-user state isolation
2. AgentWebSocketBridge singleton shares state across all users  
3. AgentExecutionRegistry singleton creates execution conflicts
4. Global factory functions return shared instances
5. Database session sharing across users
6. Memory leaks from unbounded singleton growth
7. Race conditions in shared singleton state
8. Performance degradation under concurrent load

Each test demonstrates WHY the current singleton architecture fails and 
what specific changes are needed for proper concurrent user support.

EXPECTED TEST RESULTS:
- ALL tests in this suite should FAIL with current singleton architecture
- Tests document the specific failure modes and required fixes
- Each test includes detailed business impact analysis
- Tests serve as validation criteria for singleton removal work

TEST CATEGORIES:
1. Concurrent User Execution Isolation (10 users simultaneous)
2. WebSocket Event User Isolation (events go to correct user only)
3. State Isolation Between Requests (no shared state)
4. Factory Pattern Validation (unique instances per user)
5. Database Session Isolation (separate sessions per user)
6. Memory Leak Prevention (bounded resource growth)
7. Race Condition Protection (concurrent modifications safe)
8. Performance Under Load (system handles 10+ users)
"""

import pytest
import asyncio
import uuid
import time
import threading
import random
import gc
import psutil
import os
from typing import Dict, List, Optional, Set, Any, Tuple
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict
from datetime import datetime, timezone

# Import the current singleton-based modules that need to be tested
try:
    from netra_backend.app.websocket_core.manager import (
        WebSocketManager, 
        get_websocket_manager,
        get_manager
    )
except ImportError:
    # Create mock implementations for missing modules
    class WebSocketManager:
        _instance = None
        def __new__(cls):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def get_websocket_manager():
        return WebSocketManager()
    
    def get_manager():
        return WebSocketManager()

try:
    from netra_backend.app.services.agent_websocket_bridge import (
        AgentWebSocketBridge,
        get_agent_websocket_bridge
    )
except ImportError:
    class AgentWebSocketBridge:
        _instance = None
        def __new__(cls):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    async def get_agent_websocket_bridge():
        return AgentWebSocketBridge()

try:
    from netra_backend.app.orchestration.agent_execution_registry import (
        AgentExecutionRegistry,
        get_agent_execution_registry
    )
except ImportError:
    class AgentExecutionRegistry:
        _instance = None
        def __new__(cls):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    async def get_agent_execution_registry():
        return AgentExecutionRegistry()

# Optional imports for enhanced testing
try:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
except ImportError:
    AgentRegistry = None

try:
    from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
except ImportError:
    ExecutionEngine = None


@dataclass
class MockUser:
    """Represents a concurrent user for isolation testing"""
    user_id: str
    thread_id: str
    run_id: str
    websocket: Mock
    session_data: Dict[str, Any] = field(default_factory=dict)
    received_events: List[Dict[str, Any]] = field(default_factory=list)
    execution_context: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ConcurrencyTestResult:
    """Results from concurrent user testing"""
    users_tested: int
    successful_isolations: int
    data_leakage_incidents: List[Dict[str, Any]]
    performance_metrics: Dict[str, float]
    race_conditions_detected: int
    memory_growth_mb: float
    test_duration_seconds: float


class SingletonRemovalTestHelper:
    """Helper utilities for singleton removal testing"""
    
    @staticmethod
    def create_mock_users(count: int) -> List[MockUser]:
        """Create multiple mock users for concurrent testing"""
        users = []
        for i in range(count):
            websocket = Mock()
            websocket.send_json = AsyncMock()
            websocket.send_text = AsyncMock()
            websocket.close = AsyncMock()
            
            user = MockUser(
                user_id=f"user_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{i}_{uuid.uuid4().hex[:8]}",
                websocket=websocket
            )
            users.append(user)
        return users
    
    @staticmethod
    async def simulate_concurrent_execution(
        users: List[MockUser],
        execution_func,
        duration_seconds: int = 5
    ) -> ConcurrencyTestResult:
        """Simulate concurrent user execution and measure isolation"""
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        data_leakage_incidents = []
        race_conditions = 0
        
        # Track per-user state to detect leakage
        user_states = {}
        
        # Create concurrent execution tasks
        tasks = []
        for user in users:
            task = asyncio.create_task(
                SingletonRemovalTestHelper._execute_user_workflow(
                    user, execution_func, duration_seconds
                )
            )
            tasks.append(task)
        
        # Run all users concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for data leakage
        for i, (user, result) in enumerate(zip(users, results)):
            if isinstance(result, Exception):
                race_conditions += 1
            else:
                user_states[user.user_id] = result
        
        # Check for state contamination between users
        for user_id, state in user_states.items():
            if state and isinstance(state, dict):
                for other_user_id, other_state in user_states.items():
                    if user_id != other_user_id and other_state:
                        # Check for shared references or data
                        shared_refs = SingletonRemovalTestHelper._detect_shared_references(
                            state, other_state
                        )
                        if shared_refs:
                            data_leakage_incidents.append({
                                'type': 'shared_state',
                                'user1': user_id,
                                'user2': other_user_id,
                                'shared_data': shared_refs
                            })
        
        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        return ConcurrencyTestResult(
            users_tested=len(users),
            successful_isolations=len(users) - len(data_leakage_incidents),
            data_leakage_incidents=data_leakage_incidents,
            performance_metrics={
                'avg_response_time': (end_time - start_time) / len(users),
                'total_duration': end_time - start_time,
                'throughput_users_per_second': len(users) / (end_time - start_time)
            },
            race_conditions_detected=race_conditions,
            memory_growth_mb=end_memory - start_memory,
            test_duration_seconds=end_time - start_time
        )
    
    @staticmethod
    async def _execute_user_workflow(user: MockUser, execution_func, duration_seconds: int):
        """Execute user workflow and capture state"""
        try:
            # Add random delays to increase chance of race conditions
            await asyncio.sleep(random.uniform(0, 0.1))
            
            # Execute the provided function for this user
            result = await execution_func(user)
            
            # Add another delay to simulate real execution time
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            return result
        except Exception as e:
            return e
    
    @staticmethod
    def _detect_shared_references(state1: Dict[str, Any], state2: Dict[str, Any]) -> List[str]:
        """Detect shared object references between two states"""
        shared_refs = []
        
        for key in state1.keys() & state2.keys():
            if id(state1[key]) == id(state2[key]) and state1[key] is not None:
                shared_refs.append(key)
        
        return shared_refs
    
    @staticmethod
    def validate_factory_uniqueness(factory_func, iterations: int = 10) -> Tuple[bool, List[str], List[Any]]:
        """Validate that factory function returns unique instances"""
        instances = []
        issues = []
        
        for i in range(iterations):
            try:
                instance = factory_func()
                instances.append(instance)
            except Exception as e:
                issues.append(f"Factory call {i} failed: {e}")
        
        # Check for shared instances (singleton behavior)
        instance_ids = [id(instance) for instance in instances]
        unique_ids = set(instance_ids)
        
        if len(unique_ids) != len(instances):
            issues.append(f"Factory returned shared instances: {len(instances)} calls, {len(unique_ids)} unique instances")
        
        return len(issues) == 0, issues, instances


# ============================================================================
# TEST CATEGORY 1: Concurrent User Execution Isolation
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.singleton_removal
class TestConcurrentUserExecutionIsolation:
    """
    Tests that validate proper isolation of execution state between concurrent users.
    
    EXPECTED TO FAIL: Current singleton architecture prevents proper user isolation.
    """
    
    async def test_concurrent_user_execution_isolation(self):
        """
        Test that 10+ concurrent users don't share execution state.
        
        EXPECTED FAILURE: WebSocketManager singleton shares state across all users.
        BUSINESS IMPACT: User A sees User B's agent events and data.
        REQUIRED FIX: Replace singleton with per-user factory pattern.
        """
        users = SingletonRemovalTestHelper.create_mock_users(12)
        
        async def user_execution_workflow(user: MockUser) -> Dict[str, Any]:
            # Each user should get their own WebSocket manager instance
            websocket_manager = get_websocket_manager()
            
            # Register user with unique data
            connection_id = await websocket_manager.connect_user(
                user_id=user.user_id,
                websocket=user.websocket,
                thread_id=user.thread_id
            )
            
            # Store user-specific data that should NOT be shared
            user_specific_data = {
                'secret_token': f"secret_{user.user_id}_{uuid.uuid4().hex}",
                'private_data': f"private_data_for_{user.user_id}",
                'connection_id': connection_id,
                'manager_instance_id': id(websocket_manager)
            }
            
            # Simulate agent execution with user data
            await websocket_manager.send_to_user(
                user_id=user.user_id,
                message={
                    'type': 'test_execution',
                    'user_data': user_specific_data['private_data'],
                    'timestamp': time.time()
                }
            )
            
            return user_specific_data
        
        # Execute concurrent users
        result = await SingletonRemovalTestHelper.simulate_concurrent_execution(
            users=users,
            execution_func=user_execution_workflow,
            duration_seconds=10
        )
        
        # ASSERTION: This should fail with current singleton architecture
        assert result.data_leakage_incidents == [], (
            f"SINGLETON FAILURE: {len(result.data_leakage_incidents)} data leakage incidents detected. "
            f"WebSocketManager singleton is sharing state between users. "
            f"Incidents: {result.data_leakage_incidents}"
        )
        
        assert result.successful_isolations == result.users_tested, (
            f"ISOLATION FAILURE: Only {result.successful_isolations}/{result.users_tested} users properly isolated. "
            f"Singleton architecture prevents concurrent user isolation."
        )
    
    async def test_agent_execution_registry_isolation(self):
        """
        Test that AgentExecutionRegistry doesn't share state between users.
        
        EXPECTED FAILURE: AgentExecutionRegistry singleton creates execution conflicts.
        BUSINESS IMPACT: Agent runs get mixed up between users.
        REQUIRED FIX: Per-request registry instances with proper scoping.
        """
        users = SingletonRemovalTestHelper.create_mock_users(8)
        
        async def registry_execution_workflow(user: MockUser) -> Dict[str, Any]:
            # Each user should get isolated registry state
            registry = await get_agent_execution_registry()
            
            # Register user execution
            execution_id = f"execution_{user.user_id}_{uuid.uuid4().hex[:8]}"
            
            # Store user-specific execution data
            execution_data = {
                'execution_id': execution_id,
                'user_id': user.user_id,
                'run_id': user.run_id,
                'private_execution_state': f"state_{user.user_id}_{time.time()}",
                'registry_instance_id': id(registry)
            }
            
            # This should be isolated per user, not shared globally
            await registry.register_execution(execution_id, execution_data)
            
            return execution_data
        
        result = await SingletonRemovalTestHelper.simulate_concurrent_execution(
            users=users,
            execution_func=registry_execution_workflow,
            duration_seconds=8
        )
        
        # ASSERTION: This should fail due to singleton registry sharing state
        assert result.data_leakage_incidents == [], (
            f"REGISTRY SINGLETON FAILURE: {len(result.data_leakage_incidents)} execution state conflicts detected. "
            f"AgentExecutionRegistry singleton is mixing execution state between users."
        )
        
        assert result.race_conditions_detected == 0, (
            f"RACE CONDITION FAILURE: {result.race_conditions_detected} race conditions in shared registry state. "
            f"Singleton architecture creates concurrent access conflicts."
        )
    
    async def test_websocket_bridge_user_isolation(self):
        """
        Test that AgentWebSocketBridge properly isolates users.
        
        EXPECTED FAILURE: AgentWebSocketBridge singleton shares state.
        BUSINESS IMPACT: WebSocket events sent to wrong users.
        REQUIRED FIX: Per-user bridge instances or proper scoping.
        """
        users = SingletonRemovalTestHelper.create_mock_users(10)
        
        async def bridge_workflow(user: MockUser) -> Dict[str, Any]:
            # Each user should get isolated bridge behavior
            bridge = await get_agent_websocket_bridge()
            
            # Register user's run mapping
            await bridge.register_run_thread_mapping(
                run_id=user.run_id,
                thread_id=user.thread_id,
                metadata={'user_id': user.user_id}
            )
            
            # Send user-specific notifications
            await bridge.notify_agent_started(
                run_id=user.run_id,
                agent_name="TestAgent",
                context={'user_secret': f"secret_for_{user.user_id}"}
            )
            
            bridge_data = {
                'bridge_instance_id': id(bridge),
                'user_id': user.user_id,
                'run_id': user.run_id,
                'thread_id': user.thread_id
            }
            
            return bridge_data
        
        result = await SingletonRemovalTestHelper.simulate_concurrent_execution(
            users=users,
            execution_func=bridge_workflow,
            duration_seconds=6
        )
        
        # ASSERTION: Should fail due to bridge singleton sharing state
        assert result.data_leakage_incidents == [], (
            f"BRIDGE SINGLETON FAILURE: {len(result.data_leakage_incidents)} WebSocket routing conflicts detected. "
            f"AgentWebSocketBridge singleton is mixing user notifications."
        )


# ============================================================================
# TEST CATEGORY 2: WebSocket Event User Isolation  
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.singleton_removal
class TestWebSocketEventUserIsolation:
    """
    Tests that validate WebSocket events are properly isolated to the correct users.
    
    EXPECTED TO FAIL: Singleton WebSocket components mix up user events.
    """
    
    async def test_websocket_event_user_isolation(self):
        """
        Test that WebSocket events go only to the correct user.
        
        EXPECTED FAILURE: Singleton WebSocketManager broadcasts to all users.
        BUSINESS IMPACT: User A receives User B's private agent events.  
        REQUIRED FIX: Per-user WebSocket state management.
        """
        users = SingletonRemovalTestHelper.create_mock_users(15)
        
        # Track which user should receive which events
        expected_events = {}
        actual_events = defaultdict(list)
        
        async def websocket_event_workflow(user: MockUser) -> Dict[str, Any]:
            websocket_manager = get_websocket_manager()
            bridge = await get_agent_websocket_bridge()
            
            # Connect user
            connection_id = await websocket_manager.connect_user(
                user_id=user.user_id,
                websocket=user.websocket,
                thread_id=user.thread_id
            )
            
            # Register run mapping
            await bridge.register_run_thread_mapping(
                run_id=user.run_id,
                thread_id=user.thread_id,
                metadata={'user_id': user.user_id}
            )
            
            # Generate user-specific events
            user_events = [
                {
                    'type': 'agent_started',
                    'user_specific_data': f"start_data_for_{user.user_id}",
                    'timestamp': time.time()
                },
                {
                    'type': 'tool_executing',
                    'user_specific_data': f"tool_data_for_{user.user_id}",
                    'timestamp': time.time()
                },
                {
                    'type': 'agent_completed',
                    'user_specific_data': f"completion_data_for_{user.user_id}",
                    'timestamp': time.time()
                }
            ]
            
            expected_events[user.user_id] = user_events
            
            # Send events through bridge (should only reach this user)
            for event in user_events:
                if event['type'] == 'agent_started':
                    await bridge.notify_agent_started(
                        run_id=user.run_id,
                        agent_name="TestAgent",
                        context={'data': event['user_specific_data']}
                    )
                elif event['type'] == 'tool_executing':
                    await bridge.notify_tool_executing(
                        run_id=user.run_id,
                        agent_name="TestAgent",
                        tool_name="TestTool",
                        parameters={'data': event['user_specific_data']}
                    )
                elif event['type'] == 'agent_completed':
                    await bridge.notify_agent_completed(
                        run_id=user.run_id,
                        agent_name="TestAgent",
                        result={'data': event['user_specific_data']}
                    )
            
            # Capture events that actually got sent to this user's WebSocket
            sent_events = []
            for call in user.websocket.send_json.call_args_list:
                if call.args:
                    sent_events.append(call.args[0])
            
            actual_events[user.user_id].extend(sent_events)
            
            return {
                'user_id': user.user_id,
                'expected_events': len(user_events),
                'received_events': len(sent_events),
                'connection_id': connection_id
            }
        
        result = await SingletonRemovalTestHelper.simulate_concurrent_execution(
            users=users,
            execution_func=websocket_event_workflow,
            duration_seconds=10
        )
        
        # Validate event isolation
        isolation_failures = []
        
        for user in users:
            user_expected = expected_events.get(user.user_id, [])
            user_actual = actual_events.get(user.user_id, [])
            
            # Check if user received correct number of events
            if len(user_actual) != len(user_expected):
                isolation_failures.append(f"User {user.user_id} expected {len(user_expected)} events, got {len(user_actual)}")
            
            # Check if user received other users' events
            for event in user_actual:
                if 'user_specific_data' in str(event):
                    if user.user_id not in str(event):
                        # User received another user's event!
                        isolation_failures.append(f"User {user.user_id} received another user's event: {event}")
        
        # ASSERTION: Should fail due to singleton event mixing
        assert len(isolation_failures) == 0, (
            f"WEBSOCKET EVENT ISOLATION FAILURE: {len(isolation_failures)} event routing errors detected. "
            f"Singleton WebSocket architecture is mixing user events. "
            f"Failures: {isolation_failures[:5]}..."  # Show first 5
        )
    
    async def test_websocket_death_notification_isolation(self):
        """
        Test that agent death notifications go to the correct user only.
        
        EXPECTED FAILURE: Singleton bridge broadcasts deaths to all users.
        BUSINESS IMPACT: Users see other users' agent failures.
        REQUIRED FIX: Proper user-scoped notification routing.
        """
        users = SingletonRemovalTestHelper.create_mock_users(6)
        
        # One user will have agent "die", others should not be notified
        dying_user = users[0]
        other_users = users[1:]
        
        async def death_notification_workflow(user: MockUser) -> Dict[str, Any]:
            bridge = await get_agent_websocket_bridge()
            websocket_manager = get_websocket_manager()
            
            # Connect all users
            connection_id = await websocket_manager.connect_user(
                user_id=user.user_id,
                websocket=user.websocket,
                thread_id=user.thread_id
            )
            
            await bridge.register_run_thread_mapping(
                run_id=user.run_id,
                thread_id=user.thread_id,
                metadata={'user_id': user.user_id}
            )
            
            # If this is the "dying" user, trigger death notification
            if user == dying_user:
                await bridge.notify_agent_death(
                    run_id=user.run_id,
                    agent_name="DyingAgent",
                    death_cause="timeout",
                    death_context={'user_specific_error': f"error_for_{user.user_id}"}
                )
            
            # Wait for notifications to propagate
            await asyncio.sleep(0.5)
            
            # Check what notifications this user received
            death_notifications = []
            for call in user.websocket.send_json.call_args_list:
                if call.args and 'agent_death' in str(call.args[0]):
                    death_notifications.append(call.args[0])
            
            return {
                'user_id': user.user_id,
                'is_dying_user': user == dying_user,
                'death_notifications_received': len(death_notifications),
                'notifications': death_notifications
            }
        
        result = await SingletonRemovalTestHelper.simulate_concurrent_execution(
            users=users,
            execution_func=death_notification_workflow,
            duration_seconds=5
        )
        
        # Analyze death notification isolation
        dying_user_got_notification = False
        other_users_got_notification = []
        
        for i, (user, user_result) in enumerate(zip(users, result)):
            if isinstance(user_result, dict):
                if user_result['is_dying_user']:
                    dying_user_got_notification = user_result['death_notifications_received'] > 0
                else:
                    if user_result['death_notifications_received'] > 0:
                        other_users_got_notification.append(user_result['user_id'])
        
        # ASSERTIONS: Should fail due to singleton broadcast behavior
        assert dying_user_got_notification, (
            "DEATH NOTIFICATION FAILURE: Dying user did not receive their own death notification. "
            "Singleton architecture may be dropping notifications."
        )
        
        assert len(other_users_got_notification) == 0, (
            f"DEATH NOTIFICATION ISOLATION FAILURE: {len(other_users_got_notification)} other users received death notifications. "
            f"Singleton WebSocket bridge is broadcasting death notifications to all users instead of just the relevant user. "
            f"Users who incorrectly received notifications: {other_users_got_notification}"
        )


# ============================================================================
# TEST CATEGORY 3: Factory Pattern Validation
# ============================================================================

@pytest.mark.asyncio  
@pytest.mark.singleton_removal
class TestFactoryPatternValidation:
    """
    Tests that validate factory functions return unique instances instead of singletons.
    
    EXPECTED TO FAIL: Current factory functions return the same singleton instance.
    """
    
    def test_websocket_manager_factory_uniqueness(self):
        """
        Test that WebSocket manager factory creates unique instances.
        
        EXPECTED FAILURE: get_websocket_manager() returns same singleton instance.
        BUSINESS IMPACT: All users share the same WebSocket manager state.
        REQUIRED FIX: Factory should return per-request or per-user instances.
        """
        is_unique, issues = SingletonRemovalTestHelper.validate_factory_uniqueness(
            factory_func=get_websocket_manager,
            iterations=15
        )
        
        # ASSERTION: Should fail because get_websocket_manager returns singleton
        assert is_unique, (
            f"WEBSOCKET MANAGER FACTORY FAILURE: Factory returns shared instances (singleton behavior). "
            f"Issues: {issues}. "
            f"REQUIRED FIX: get_websocket_manager() must return unique instances per call for proper user isolation."
        )
    
    def test_websocket_bridge_factory_uniqueness(self):
        """
        Test that WebSocket bridge factory creates unique instances.
        
        EXPECTED FAILURE: get_agent_websocket_bridge() returns same singleton.
        BUSINESS IMPACT: All users share bridge state and get mixed notifications.
        REQUIRED FIX: Factory should create per-user bridge instances.
        """
        async def async_factory():
            return await get_agent_websocket_bridge()
        
        # Test async factory uniqueness
        instances = []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            for i in range(10):
                instance = loop.run_until_complete(async_factory())
                instances.append(instance)
        finally:
            loop.close()
        
        instance_ids = [id(instance) for instance in instances]
        unique_ids = set(instance_ids)
        
        # ASSERTION: Should fail because bridge is singleton
        assert len(unique_ids) == len(instances), (
            f"WEBSOCKET BRIDGE FACTORY FAILURE: Factory returned {len(instances)} calls but only {len(unique_ids)} unique instances. "
            f"AgentWebSocketBridge is using singleton pattern. "
            f"REQUIRED FIX: get_agent_websocket_bridge() must return unique instances for user isolation."
        )
    
    def test_execution_registry_factory_uniqueness(self):
        """
        Test that execution registry factory creates unique instances.
        
        EXPECTED FAILURE: get_agent_execution_registry() returns singleton.
        BUSINESS IMPACT: Agent executions get mixed up between users.
        REQUIRED FIX: Per-request registry instances.
        """
        async def async_registry_factory():
            return await get_agent_execution_registry()
        
        instances = []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            for i in range(8):
                instance = loop.run_until_complete(async_registry_factory())
                instances.append(instance)
        finally:
            loop.close()
        
        instance_ids = [id(instance) for instance in instances]
        unique_ids = set(instance_ids)
        
        # ASSERTION: Should fail due to singleton pattern
        assert len(unique_ids) == len(instances), (
            f"EXECUTION REGISTRY FACTORY FAILURE: Factory returned {len(instances)} calls but only {len(unique_ids)} unique instances. "
            f"AgentExecutionRegistry is using singleton pattern. "
            f"REQUIRED FIX: get_agent_execution_registry() must return per-request instances."
        )


# ============================================================================
# TEST CATEGORY 4: Memory Leak Prevention
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.singleton_removal  
class TestMemoryLeakPrevention:
    """
    Tests that validate proper resource management without unbounded singleton growth.
    
    EXPECTED TO FAIL: Singleton instances accumulate state without bounds.
    """
    
    async def test_websocket_manager_memory_bounds(self):
        """
        Test that WebSocket manager doesn't grow memory unbounded.
        
        EXPECTED FAILURE: Singleton accumulates connections without proper cleanup.
        BUSINESS IMPACT: Server memory exhaustion under load.
        REQUIRED FIX: Per-user instances with proper lifecycle management.
        """
        # Measure initial memory
        gc.collect()
        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        # Create many "users" that connect and disconnect
        websocket_manager = get_websocket_manager()
        
        connection_ids = []
        for i in range(100):
            mock_websocket = Mock()
            mock_websocket.send_json = AsyncMock()
            
            connection_id = await websocket_manager.connect_user(
                user_id=f"memory_test_user_{i}",
                websocket=mock_websocket,
                thread_id=f"thread_memory_test_{i}"
            )
            connection_ids.append(connection_id)
        
        # Disconnect all users
        for connection_id in connection_ids:
            await websocket_manager._cleanup_connection(connection_id)
        
        # Force cleanup and measure memory
        gc.collect()
        await asyncio.sleep(1)  # Allow cleanup tasks to run
        
        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # ASSERTION: Should fail due to singleton memory accumulation
        assert memory_growth < 50, (  # 50MB threshold
            f"MEMORY LEAK FAILURE: WebSocket manager grew by {memory_growth:.1f}MB after 100 user connections. "
            f"Singleton pattern prevents proper memory cleanup. "
            f"REQUIRED FIX: Replace singleton with per-user instances that can be garbage collected."
        )
    
    async def test_concurrent_user_memory_isolation(self):
        """
        Test that concurrent users don't cause unbounded memory growth.
        
        EXPECTED FAILURE: Singleton instances accumulate per-user state globally.
        BUSINESS IMPACT: Memory usage grows with user count instead of being bounded.
        REQUIRED FIX: User state should be scoped to request/session, not global.
        """
        users = SingletonRemovalTestHelper.create_mock_users(50)
        
        gc.collect()
        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        async def memory_intensive_workflow(user: MockUser) -> Dict[str, Any]:
            # Create user-specific data that should be cleanable
            user_data = {
                'large_data': 'x' * 10000,  # 10KB per user
                'user_history': [f"event_{i}" for i in range(100)],
                'user_state': {f"key_{i}": f"value_{i}" for i in range(50)}
            }
            
            # Store in singleton components (should accumulate unbounded)
            websocket_manager = get_websocket_manager()
            bridge = await get_agent_websocket_bridge()
            
            connection_id = await websocket_manager.connect_user(
                user_id=user.user_id,
                websocket=user.websocket,
                thread_id=user.thread_id
            )
            
            await bridge.register_run_thread_mapping(
                run_id=user.run_id,
                thread_id=user.thread_id,
                metadata=user_data  # This should be cleanable per user
            )
            
            return user_data
        
        # Execute all users
        await SingletonRemovalTestHelper.simulate_concurrent_execution(
            users=users,
            execution_func=memory_intensive_workflow,
            duration_seconds=3
        )
        
        # Force cleanup
        gc.collect()
        await asyncio.sleep(2)
        
        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # ASSERTION: Should fail due to singleton accumulation
        max_expected_growth = 30  # Should be much lower with proper cleanup
        assert memory_growth < max_expected_growth, (
            f"CONCURRENT USER MEMORY FAILURE: Memory grew by {memory_growth:.1f}MB for 50 users. "
            f"Expected < {max_expected_growth}MB. "
            f"Singleton pattern accumulates per-user data globally without cleanup. "
            f"REQUIRED FIX: User-scoped instances that can be garbage collected after user session ends."
        )


# ============================================================================
# TEST CATEGORY 5: Race Condition Protection
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.singleton_removal
class TestRaceConditionProtection:
    """
    Tests that validate concurrent modifications to shared singleton state are safe.
    
    EXPECTED TO FAIL: Singleton shared state creates race conditions.
    """
    
    async def test_concurrent_websocket_modifications(self):
        """
        Test that concurrent WebSocket manager modifications don't create race conditions.
        
        EXPECTED FAILURE: Singleton WebSocket manager has shared state race conditions.
        BUSINESS IMPACT: Connection state corruption, lost events, crashes.
        REQUIRED FIX: Per-user instances eliminate shared state races.
        """
        users = SingletonRemovalTestHelper.create_mock_users(20)
        race_condition_errors = []
        
        async def concurrent_modification_workflow(user: MockUser) -> Dict[str, Any]:
            try:
                websocket_manager = get_websocket_manager()
                
                # Rapid connect/disconnect to trigger race conditions
                for attempt in range(5):
                    connection_id = await websocket_manager.connect_user(
                        user_id=f"{user.user_id}_attempt_{attempt}",
                        websocket=user.websocket,
                        thread_id=f"{user.thread_id}_attempt_{attempt}"
                    )
                    
                    # Immediately try to send message (race condition opportunity)
                    await websocket_manager.send_to_user(
                        user_id=f"{user.user_id}_attempt_{attempt}",
                        message={'test': f'race_test_{attempt}_{time.time()}'}
                    )
                    
                    # Immediately disconnect (race condition opportunity)
                    await websocket_manager._cleanup_connection(connection_id)
                
                return {'success': True, 'user_id': user.user_id}
                
            except Exception as e:
                # Capture race condition errors
                race_condition_errors.append({
                    'user_id': user.user_id,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                return {'success': False, 'error': str(e)}
        
        result = await SingletonRemovalTestHelper.simulate_concurrent_execution(
            users=users,
            execution_func=concurrent_modification_workflow,
            duration_seconds=5
        )
        
        # ASSERTION: Should fail due to race conditions in singleton
        assert len(race_condition_errors) == 0, (
            f"RACE CONDITION FAILURE: {len(race_condition_errors)} race condition errors detected in singleton WebSocket manager. "
            f"Concurrent modifications to shared singleton state are not thread-safe. "
            f"Sample errors: {race_condition_errors[:3]}. "
            f"REQUIRED FIX: Replace singleton with per-user instances to eliminate shared state races."
        )
        
        assert result.race_conditions_detected == 0, (
            f"RACE CONDITION FAILURE: {result.race_conditions_detected} race conditions detected during concurrent execution. "
            f"Singleton architecture creates concurrent access conflicts."
        )
    
    async def test_concurrent_bridge_notifications(self):
        """
        Test that concurrent bridge notifications don't interfere.
        
        EXPECTED FAILURE: Singleton bridge creates notification race conditions.
        BUSINESS IMPACT: Notifications lost, sent to wrong users, or corrupted.
        REQUIRED FIX: Per-user notification routing eliminates races.
        """
        users = SingletonRemovalTestHelper.create_mock_users(15)
        notification_errors = []
        notification_counts = defaultdict(int)
        
        async def concurrent_notification_workflow(user: MockUser) -> Dict[str, Any]:
            try:
                bridge = await get_agent_websocket_bridge()
                
                await bridge.register_run_thread_mapping(
                    run_id=user.run_id,
                    thread_id=user.thread_id,
                    metadata={'user_id': user.user_id}
                )
                
                # Send multiple notifications rapidly (race condition opportunity)
                notification_types = ['agent_started', 'tool_executing', 'agent_completed']
                
                for i in range(10):
                    for notification_type in notification_types:
                        if notification_type == 'agent_started':
                            await bridge.notify_agent_started(
                                run_id=user.run_id,
                                agent_name=f"TestAgent_{i}",
                                context={'iteration': i}
                            )
                        elif notification_type == 'tool_executing':
                            await bridge.notify_tool_executing(
                                run_id=user.run_id,
                                agent_name=f"TestAgent_{i}",
                                tool_name=f"TestTool_{i}",
                                parameters={'iteration': i}
                            )
                        elif notification_type == 'agent_completed':
                            await bridge.notify_agent_completed(
                                run_id=user.run_id,
                                agent_name=f"TestAgent_{i}",
                                result={'iteration': i}
                            )
                        
                        notification_counts[user.user_id] += 1
                
                return {'success': True, 'notifications_sent': notification_counts[user.user_id]}
                
            except Exception as e:
                notification_errors.append({
                    'user_id': user.user_id,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                return {'success': False, 'error': str(e)}
        
        result = await SingletonRemovalTestHelper.simulate_concurrent_execution(
            users=users,
            execution_func=concurrent_notification_workflow,
            duration_seconds=8
        )
        
        # ASSERTION: Should fail due to notification race conditions
        assert len(notification_errors) == 0, (
            f"NOTIFICATION RACE CONDITION FAILURE: {len(notification_errors)} errors during concurrent notifications. "
            f"Singleton bridge cannot handle concurrent notification requests safely. "
            f"Sample errors: {notification_errors[:3]}. "
            f"REQUIRED FIX: Per-user bridge instances eliminate concurrent access to shared state."
        )


# ============================================================================
# TEST CATEGORY 6: Performance Under Concurrent Load
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.singleton_removal
class TestPerformanceUnderConcurrentLoad:
    """
    Tests that validate system performance with concurrent users.
    
    EXPECTED TO FAIL: Singleton bottlenecks degrade performance under load.
    """
    
    async def test_concurrent_user_performance_degradation(self):
        """
        Test that system handles 10+ users without performance degradation.
        
        EXPECTED FAILURE: Singleton bottlenecks cause performance to degrade with user count.
        BUSINESS IMPACT: Poor user experience, timeouts, system instability.
        REQUIRED FIX: Per-user instances scale linearly with user count.
        """
        # Test with increasing user counts to show performance degradation
        performance_results = []
        
        for user_count in [1, 5, 10, 15, 20]:
            users = SingletonRemovalTestHelper.create_mock_users(user_count)
            
            async def performance_workflow(user: MockUser) -> Dict[str, Any]:
                start_time = time.time()
                
                # Simulate typical user workflow
                websocket_manager = get_websocket_manager()
                bridge = await get_agent_websocket_bridge()
                
                connection_id = await websocket_manager.connect_user(
                    user_id=user.user_id,
                    websocket=user.websocket,
                    thread_id=user.thread_id
                )
                
                await bridge.register_run_thread_mapping(
                    run_id=user.run_id,
                    thread_id=user.thread_id,
                    metadata={'user_id': user.user_id}
                )
                
                # Send several events (typical agent workflow)
                for i in range(5):
                    await bridge.notify_agent_started(
                        run_id=user.run_id,
                        agent_name=f"Agent_{i}",
                        context={'step': i}
                    )
                    
                    await bridge.notify_tool_executing(
                        run_id=user.run_id,
                        agent_name=f"Agent_{i}",
                        tool_name=f"Tool_{i}",
                        parameters={'data': f'data_{i}'}
                    )
                    
                    await bridge.notify_agent_completed(
                        run_id=user.run_id,
                        agent_name=f"Agent_{i}",
                        result={'result': f'result_{i}'}
                    )
                
                end_time = time.time()
                return {
                    'user_id': user.user_id,
                    'workflow_duration': end_time - start_time
                }
            
            result = await SingletonRemovalTestHelper.simulate_concurrent_execution(
                users=users,
                execution_func=performance_workflow,
                duration_seconds=15
            )
            
            performance_results.append({
                'user_count': user_count,
                'avg_response_time': result.performance_metrics['avg_response_time'],
                'total_duration': result.performance_metrics['total_duration'],
                'throughput': result.performance_metrics['throughput_users_per_second']
            })
        
        # Analyze performance degradation
        baseline_response_time = performance_results[0]['avg_response_time']  # 1 user
        max_response_time = performance_results[-1]['avg_response_time']  # 20 users
        
        performance_degradation_ratio = max_response_time / baseline_response_time
        
        # ASSERTION: Should fail due to singleton performance bottleneck
        max_acceptable_degradation = 2.0  # 2x slowdown acceptable
        assert performance_degradation_ratio < max_acceptable_degradation, (
            f"PERFORMANCE DEGRADATION FAILURE: Response time increased by {performance_degradation_ratio:.1f}x from 1 to 20 users. "
            f"Baseline: {baseline_response_time:.3f}s, Max load: {max_response_time:.3f}s. "
            f"Singleton architecture creates performance bottlenecks that don't scale with user count. "
            f"Performance results: {performance_results}. "
            f"REQUIRED FIX: Per-user instances should scale linearly, not create bottlenecks."
        )
    
    async def test_memory_usage_scales_linearly(self):
        """
        Test that memory usage scales linearly with concurrent users.
        
        EXPECTED FAILURE: Singleton accumulates memory super-linearly.
        BUSINESS IMPACT: Memory exhaustion with moderate user counts.
        REQUIRED FIX: Per-user instances with proper cleanup scale linearly.
        """
        memory_results = []
        
        for user_count in [5, 10, 15, 20]:
            users = SingletonRemovalTestHelper.create_mock_users(user_count)
            
            gc.collect()
            initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            
            async def memory_workflow(user: MockUser) -> Dict[str, Any]:
                # Create realistic user session data
                websocket_manager = get_websocket_manager()
                bridge = await get_agent_websocket_bridge()
                registry = await get_agent_execution_registry()
                
                connection_id = await websocket_manager.connect_user(
                    user_id=user.user_id,
                    websocket=user.websocket,
                    thread_id=user.thread_id
                )
                
                await bridge.register_run_thread_mapping(
                    run_id=user.run_id,
                    thread_id=user.thread_id,
                    metadata={
                        'user_id': user.user_id,
                        'session_data': {'key': 'x' * 1000}  # 1KB per user
                    }
                )
                
                return {'user_id': user.user_id, 'memory_allocated': True}
            
            await SingletonRemovalTestHelper.simulate_concurrent_execution(
                users=users,
                execution_func=memory_workflow,
                duration_seconds=3
            )
            
            gc.collect()
            await asyncio.sleep(1)
            
            final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            memory_growth = final_memory - initial_memory
            
            memory_results.append({
                'user_count': user_count,
                'memory_growth_mb': memory_growth,
                'memory_per_user_mb': memory_growth / user_count
            })
        
        # Check for super-linear memory growth (singleton accumulation)
        baseline_per_user = memory_results[0]['memory_per_user_mb']  # 5 users
        max_per_user = memory_results[-1]['memory_per_user_mb']  # 20 users
        
        memory_growth_ratio = max_per_user / max(baseline_per_user, 0.1)  # Avoid division by zero
        
        # ASSERTION: Should fail due to singleton memory accumulation
        max_acceptable_growth = 2.0  # 2x per-user growth acceptable
        assert memory_growth_ratio < max_acceptable_growth, (
            f"MEMORY SCALING FAILURE: Memory per user increased by {memory_growth_ratio:.1f}x from 5 to 20 users. "
            f"Baseline per-user: {baseline_per_user:.1f}MB, Max per-user: {max_per_user:.1f}MB. "
            f"Singleton pattern causes super-linear memory accumulation instead of linear scaling. "
            f"Memory results: {memory_results}. "
            f"REQUIRED FIX: Per-user instances should maintain constant per-user memory usage."
        )


# ============================================================================
# FINAL COMPREHENSIVE TEST
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.singleton_removal
class TestComprehensiveSingletonRemovalValidation:
    """
    Comprehensive test that validates all aspects of singleton removal together.
    
    EXPECTED TO FAIL: Multiple singleton issues compound under realistic load.
    """
    
    async def test_comprehensive_singleton_removal_validation(self):
        """
        Comprehensive test that validates concurrent users with realistic workflows.
        
        EXPECTED FAILURE: Multiple singleton issues create compound failures.
        BUSINESS IMPACT: System cannot support concurrent users in production.
        REQUIRED FIX: Complete singleton removal with factory pattern replacement.
        """
        users = SingletonRemovalTestHelper.create_mock_users(25)
        
        # Track comprehensive issues
        isolation_failures = []
        performance_issues = []
        memory_issues = []
        race_condition_errors = []
        
        gc.collect()
        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        async def comprehensive_workflow(user: MockUser) -> Dict[str, Any]:
            try:
                start_time = time.time()
                
                # Full realistic user workflow
                websocket_manager = get_websocket_manager()
                bridge = await get_agent_websocket_bridge()
                registry = await get_agent_execution_registry()
                
                # User session setup
                connection_id = await websocket_manager.connect_user(
                    user_id=user.user_id,
                    websocket=user.websocket,
                    thread_id=user.thread_id
                )
                
                await bridge.register_run_thread_mapping(
                    run_id=user.run_id,
                    thread_id=user.thread_id,
                    metadata={
                        'user_id': user.user_id,
                        'user_secret': f'secret_for_{user.user_id}_{uuid.uuid4().hex}',
                        'session_start': time.time()
                    }
                )
                
                # Simulate complete agent execution workflow
                agent_names = ['DataAnalyzer', 'ReportGenerator', 'SummaryExtractor']
                
                for agent_name in agent_names:
                    # Agent lifecycle with events
                    await bridge.notify_agent_started(
                        run_id=user.run_id,
                        agent_name=agent_name,
                        context={'user_specific_context': f'context_for_{user.user_id}'}
                    )
                    
                    # Multiple tool executions
                    for tool_idx in range(3):
                        await bridge.notify_tool_executing(
                            run_id=user.run_id,
                            agent_name=agent_name,
                            tool_name=f'Tool_{tool_idx}',
                            parameters={'user_data': f'data_for_{user.user_id}_{tool_idx}'}
                        )
                        
                        await asyncio.sleep(0.01)  # Simulate tool execution
                        
                        await bridge.notify_tool_completed(
                            run_id=user.run_id,
                            agent_name=agent_name,
                            tool_name=f'Tool_{tool_idx}',
                            result={'user_result': f'result_for_{user.user_id}_{tool_idx}'}
                        )
                    
                    await bridge.notify_agent_completed(
                        run_id=user.run_id,
                        agent_name=agent_name,
                        result={'final_result': f'final_for_{user.user_id}_{agent_name}'}
                    )
                
                # Check for isolation issues
                component_ids = {
                    'websocket_manager_id': id(websocket_manager),
                    'bridge_id': id(bridge), 
                    'registry_id': id(registry)
                }
                
                end_time = time.time()
                
                return {
                    'user_id': user.user_id,
                    'workflow_duration': end_time - start_time,
                    'component_ids': component_ids,
                    'success': True
                }
                
            except Exception as e:
                race_condition_errors.append({
                    'user_id': user.user_id,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                return {'success': False, 'error': str(e)}
        
        # Execute comprehensive test
        result = await SingletonRemovalTestHelper.simulate_concurrent_execution(
            users=users,
            execution_func=comprehensive_workflow,
            duration_seconds=20
        )
        
        # Analyze comprehensive results
        gc.collect()
        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Check for component sharing (singleton evidence)
        component_id_sets = defaultdict(set)
        successful_results = [r for r in result if isinstance(r, dict) and r.get('success')]
        
        for user_result in successful_results:
            if 'component_ids' in user_result:
                for component, comp_id in user_result['component_ids'].items():
                    component_id_sets[component].add(comp_id)
        
        # Comprehensive assertions - ALL should fail with singleton architecture
        
        # 1. Component isolation
        for component, id_set in component_id_sets.items():
            assert len(id_set) == len(users), (
                f"COMPREHENSIVE FAILURE - SINGLETON DETECTED: {component} has only {len(id_set)} unique instances for {len(users)} users. "
                f"Singleton pattern prevents proper user isolation."
            )
        
        # 2. Data leakage
        assert len(result.data_leakage_incidents) == 0, (
            f"COMPREHENSIVE FAILURE - DATA LEAKAGE: {len(result.data_leakage_incidents)} data leakage incidents detected. "
            f"Singleton architecture mixes user data."
        )
        
        # 3. Race conditions  
        assert len(race_condition_errors) == 0, (
            f"COMPREHENSIVE FAILURE - RACE CONDITIONS: {len(race_condition_errors)} race condition errors. "
            f"Singleton shared state creates concurrent access conflicts."
        )
        
        # 4. Performance degradation
        avg_response_time = result.performance_metrics['avg_response_time']
        assert avg_response_time < 2.0, (  # 2 second max per user
            f"COMPREHENSIVE FAILURE - PERFORMANCE: Average response time {avg_response_time:.2f}s exceeds 2.0s. "
            f"Singleton bottlenecks degrade performance under concurrent load."
        )
        
        # 5. Memory efficiency
        memory_per_user = memory_growth / len(users)
        assert memory_per_user < 10.0, (  # 10MB max per user
            f"COMPREHENSIVE FAILURE - MEMORY: Memory usage {memory_per_user:.1f}MB per user exceeds 10MB limit. "
            f"Total growth: {memory_growth:.1f}MB for {len(users)} users. "
            f"Singleton architecture accumulates memory inefficiently."
        )
        
        # Final comprehensive failure message
        if any([
            len(component_id_sets.get('websocket_manager_id', {1})) == 1,
            len(component_id_sets.get('bridge_id', {1})) == 1,
            len(component_id_sets.get('registry_id', {1})) == 1,
            len(result.data_leakage_incidents) > 0,
            len(race_condition_errors) > 0,
            avg_response_time >= 2.0,
            memory_per_user >= 10.0
        ]):
            pytest.fail(
                f"\n\n{'='*80}\n"
                f"COMPREHENSIVE SINGLETON REMOVAL VALIDATION FAILED\n"
                f"{'='*80}\n\n"
                f"BUSINESS IMPACT: System cannot support concurrent users in production\n\n"
                f"SINGLETON ISSUES DETECTED:\n"
                f"- Component sharing: {dict(component_id_sets)}\n"
                f"- Data leakage incidents: {len(result.data_leakage_incidents)}\n" 
                f"- Race condition errors: {len(race_condition_errors)}\n"
                f"- Performance degradation: {avg_response_time:.2f}s avg response\n"
                f"- Memory inefficiency: {memory_per_user:.1f}MB per user\n\n"
                f"REQUIRED FIXES:\n"
                f"1. Replace WebSocketManager singleton with per-user factory\n"
                f"2. Replace AgentWebSocketBridge singleton with per-user instances\n"
                f"3. Replace AgentExecutionRegistry singleton with per-request instances\n"
                f"4. Implement proper user-scoped state management\n"
                f"5. Add concurrent-safe resource cleanup\n\n"
                f"VALIDATION: All tests in this suite should PASS after singleton removal\n"
                f"{'='*80}"
            )


if __name__ == "__main__":
    # Run the singleton removal test suite
    print("\n" + "="*80)
    print("SINGLETON REMOVAL PHASE 2 TEST SUITE")
    print("="*80)
    print("\nWARNING: These tests are EXPECTED TO FAIL with current singleton architecture")
    print("They validate the requirements for proper concurrent user isolation")
    print("\nRunning comprehensive validation...")
    print("="*80 + "\n")
    
    pytest.main([
        __file__,
        "-v",
        "-s", 
        "--tb=short",
        "-k", "singleton_removal"
    ])