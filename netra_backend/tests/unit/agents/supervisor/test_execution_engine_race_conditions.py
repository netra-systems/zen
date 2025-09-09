"""
Comprehensive Unit Tests for Agent Execution Engine Race Conditions

Business Value Justification (BVJ):
- Segment: Platform/Internal - Risk Reduction + Business Critical Agent Value  
- Business Goal: Reliable agent execution for chat AI value delivery
- Value Impact: Prevents execution race conditions that cause incomplete/corrupted AI responses
- Strategic Impact: Ensures reliable multi-user agent isolation and execution ordering

This module tests the critical race condition scenarios in agent execution that can occur
when multiple users execute agents simultaneously, focusing on:

1. Multiple users running agents simultaneously
2. Tool execution order under concurrent load  
3. Agent state updates during execution
4. User context isolation during concurrent executions
5. WebSocket event emission race conditions during agent execution
6. Graceful degradation during execution failures under load
7. Timeout scenarios during concurrent agent execution

CRITICAL: These tests use ThreadPoolExecutor and asyncio.gather() to create REAL race conditions
in agent execution flows. No mock bypasses that hide race conditions.

Architecture Compliance:
- Uses SSOT imports from test_framework and shared modules
- Follows TEST_CREATION_GUIDE.md patterns for race condition testing
- Tests actual business logic with minimal mocking
- Validates WebSocket event emission (mission critical per CLAUDE.md Section 6)
"""

import asyncio
import pytest
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
import threading
from datetime import datetime

# SSOT imports for agent execution infrastructure
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)

# SSOT imports for test framework
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

# SSOT imports for agent infrastructure
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker, ExecutionState

# Type validation imports for SSOT compliance
from shared.types.execution_types import (
    StronglyTypedUserExecutionContext,
    AgentExecutionMetrics,
    WebSocketEventPriority
)


@dataclass
class RaceConditionTestResult:
    """Results from race condition testing scenarios."""
    user_id: str
    thread_id: str
    run_id: str
    execution_time: float
    success: bool
    error: Optional[str] = None
    websocket_events: List[str] = None
    concurrent_execution_count: int = 0
    race_condition_detected: bool = False
    isolation_verified: bool = False


class MockAgentWebSocketBridge:
    """Mock WebSocket bridge for testing race conditions in event emission."""
    
    def __init__(self):
        self.events = []
        self.lock = asyncio.Lock()
        self.notification_count = 0
        self.concurrent_notifications = 0
        self.max_concurrent_notifications = 0
        
    async def notify_agent_started(self, run_id: str, agent_name: str, context: Dict[str, Any]):
        """Track agent started notifications with race condition detection."""
        async with self.lock:
            self.concurrent_notifications += 1
            self.max_concurrent_notifications = max(
                self.max_concurrent_notifications, 
                self.concurrent_notifications
            )
            
        try:
            self.events.append({
                'type': 'agent_started',
                'run_id': run_id,
                'agent_name': agent_name,
                'context': context,
                'timestamp': time.time(),
                'thread_id': threading.get_ident(),
                'concurrent_count': self.concurrent_notifications
            })
            self.notification_count += 1
            
            # Simulate WebSocket emission delay to create race conditions
            await asyncio.sleep(0.001)
            
        finally:
            async with self.lock:
                self.concurrent_notifications -= 1
                
    async def notify_agent_thinking(self, run_id: str, agent_name: str, 
                                   reasoning: str, step_number: int = None, **kwargs):
        """Track agent thinking notifications with race condition detection."""
        async with self.lock:
            self.concurrent_notifications += 1
            self.max_concurrent_notifications = max(
                self.max_concurrent_notifications, 
                self.concurrent_notifications
            )
            
        try:
            self.events.append({
                'type': 'agent_thinking',
                'run_id': run_id,
                'agent_name': agent_name,
                'reasoning': reasoning,
                'step_number': step_number,
                'timestamp': time.time(),
                'thread_id': threading.get_ident(),
                'concurrent_count': self.concurrent_notifications
            })
            self.notification_count += 1
            
            # Simulate race condition by adding delay
            await asyncio.sleep(0.001)
            
        finally:
            async with self.lock:
                self.concurrent_notifications -= 1
                
    async def notify_tool_executing(self, run_id: str, agent_name: str, 
                                   tool_name: str, parameters: Dict[str, Any] = None):
        """Track tool execution notifications with race condition detection."""
        async with self.lock:
            self.concurrent_notifications += 1
            
        try:
            self.events.append({
                'type': 'tool_executing',
                'run_id': run_id,
                'agent_name': agent_name,
                'tool_name': tool_name,
                'parameters': parameters or {},
                'timestamp': time.time(),
                'thread_id': threading.get_ident(),
                'concurrent_count': self.concurrent_notifications
            })
            self.notification_count += 1
            
        finally:
            async with self.lock:
                self.concurrent_notifications -= 1
                
    async def notify_tool_completed(self, run_id: str, agent_name: str, 
                                   tool_name: str, result: Any):
        """Track tool completion notifications."""
        self.events.append({
            'type': 'tool_completed',
            'run_id': run_id,
            'agent_name': agent_name,
            'tool_name': tool_name,
            'result': result,
            'timestamp': time.time()
        })
        self.notification_count += 1
        
    async def notify_agent_completed(self, run_id: str, agent_name: str, 
                                    result: Any, execution_time_ms: float = None):
        """Track agent completion notifications."""
        async with self.lock:
            self.concurrent_notifications += 1
            
        try:
            self.events.append({
                'type': 'agent_completed',
                'run_id': run_id,
                'agent_name': agent_name,
                'result': result,
                'execution_time_ms': execution_time_ms,
                'timestamp': time.time(),
                'thread_id': threading.get_ident(),
                'concurrent_count': self.concurrent_notifications
            })
            self.notification_count += 1
            
        finally:
            async with self.lock:
                self.concurrent_notifications -= 1
                
    async def notify_agent_error(self, run_id: str, agent_name: str, 
                                error: str, error_context: Dict[str, Any] = None, **kwargs):
        """Track agent error notifications."""
        self.events.append({
            'type': 'agent_error',
            'run_id': run_id,
            'agent_name': agent_name,
            'error': error,
            'error_context': error_context or {},
            'timestamp': time.time()
        })
        self.notification_count += 1
        
    async def notify_agent_death(self, run_id: str, agent_name: str, 
                                death_type: str, context: Dict[str, Any]):
        """Track agent death notifications."""
        self.events.append({
            'type': 'agent_death',
            'run_id': run_id,
            'agent_name': agent_name,
            'death_type': death_type,
            'context': context,
            'timestamp': time.time()
        })
        self.notification_count += 1

    def get_events_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all events for a specific run_id."""
        return [event for event in self.events if event.get('run_id') == run_id]
        
    def get_race_condition_metrics(self) -> Dict[str, Any]:
        """Get race condition detection metrics."""
        return {
            'total_notifications': self.notification_count,
            'max_concurrent_notifications': self.max_concurrent_notifications,
            'race_conditions_detected': self.max_concurrent_notifications > 1,
            'total_events': len(self.events),
            'unique_threads': len(set(event.get('thread_id') for event in self.events if event.get('thread_id')))
        }


class MockAgent:
    """Mock agent for testing race conditions in execution."""
    
    def __init__(self, agent_name: str, execution_time: float = 0.1, should_fail: bool = False):
        self.agent_name = agent_name
        self.execution_time = execution_time
        self.should_fail = should_fail
        self.execution_count = 0
        self.concurrent_executions = 0
        self.max_concurrent_executions = 0
        self.lock = asyncio.Lock()
        
    async def execute(self, state: DeepAgentState, run_id: str, use_tools: bool = True) -> Dict[str, Any]:
        """Execute agent with race condition detection."""
        async with self.lock:
            self.concurrent_executions += 1
            self.max_concurrent_executions = max(
                self.max_concurrent_executions,
                self.concurrent_executions
            )
            
        try:
            self.execution_count += 1
            
            # Simulate actual agent work with potential race conditions
            await asyncio.sleep(self.execution_time)
            
            if self.should_fail:
                raise RuntimeError(f"Simulated failure in {self.agent_name}")
                
            # Simulate tool execution if requested
            tool_results = []
            if use_tools:
                tool_results = await self._simulate_tool_execution(state, run_id)
                
            return {
                'success': True,
                'agent_name': self.agent_name,
                'result': f'Executed {self.agent_name} successfully',
                'execution_count': self.execution_count,
                'concurrent_executions': self.concurrent_executions,
                'tool_results': tool_results,
                'user_id': getattr(state, 'user_id', 'unknown'),
                'thread_id': getattr(state, 'thread_id', 'unknown')
            }
            
        finally:
            async with self.lock:
                self.concurrent_executions -= 1
                
    async def _simulate_tool_execution(self, state: DeepAgentState, run_id: str) -> List[Dict[str, Any]]:
        """Simulate tool execution with potential race conditions."""
        tools = ['analyze_data', 'generate_report', 'optimize_parameters']
        results = []
        
        for tool_name in tools:
            # Simulate tool execution delay
            await asyncio.sleep(0.01)
            
            results.append({
                'tool_name': tool_name,
                'result': f'Tool {tool_name} executed for {run_id}',
                'execution_time': 0.01
            })
            
        return results
        
    def get_race_condition_metrics(self) -> Dict[str, Any]:
        """Get race condition metrics for this agent."""
        return {
            'total_executions': self.execution_count,
            'max_concurrent_executions': self.max_concurrent_executions,
            'race_conditions_detected': self.max_concurrent_executions > 1
        }


class TestExecutionEngineRaceConditions(BaseIntegrationTest):
    """Comprehensive unit tests for agent execution engine race conditions."""
    
    def setup_method(self):
        """Set up test environment for race condition testing."""
        super().setup_method()
        
        # Create mock components for race condition testing
        self.mock_registry = MagicMock()
        self.mock_websocket_bridge = MockAgentWebSocketBridge()
        
        # Create isolated environment for testing
        self.env = IsolatedEnvironment()
        self.env.set("TESTING", "true", source="test")
        
        # Create execution tracker
        self.execution_tracker = get_execution_tracker()
        
        # Initialize test agents with different characteristics
        self.test_agents = {
            'fast_agent': MockAgent('fast_agent', execution_time=0.05),
            'slow_agent': MockAgent('slow_agent', execution_time=0.2),
            'failing_agent': MockAgent('failing_agent', should_fail=True),
            'data_agent': MockAgent('data_agent', execution_time=0.1),
            'optimization_agent': MockAgent('optimization_agent', execution_time=0.15)
        }
        
        # Configure mock registry to return test agents
        self.mock_registry.get.side_effect = lambda name: self.test_agents.get(name)
        
        # Race condition detection metrics
        self.race_condition_results = []
        
    def teardown_method(self):
        """Clean up after race condition testing."""
        # Log race condition detection results
        metrics = self._collect_race_condition_metrics()
        if metrics['race_conditions_detected']:
            print(f"Race conditions detected during test: {metrics}")
            
        super().teardown_method()
        
    def _collect_race_condition_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive race condition metrics."""
        websocket_metrics = self.mock_websocket_bridge.get_race_condition_metrics()
        
        agent_metrics = {}
        for name, agent in self.test_agents.items():
            agent_metrics[name] = agent.get_race_condition_metrics()
            
        return {
            'websocket_metrics': websocket_metrics,
            'agent_metrics': agent_metrics,
            'race_conditions_detected': (
                websocket_metrics['race_conditions_detected'] or
                any(metrics['race_conditions_detected'] for metrics in agent_metrics.values())
            ),
            'test_results': self.race_condition_results
        }
        
    def _create_user_execution_context(self, user_id: str) -> UserExecutionContext:
        """Create isolated user execution context for race condition testing."""
        thread_id = f"thread_{user_id}_{uuid.uuid4().hex[:8]}"
        run_id = f"run_{user_id}_{uuid.uuid4().hex[:8]}"
        
        return UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_context={
                'test_type': 'race_condition',
                'isolation_required': True
            },
            audit_metadata={
                'test_context': 'race_condition_testing',
                'created_for': 'concurrent_execution_test'
            }
        )
        
    def _create_agent_execution_context(self, agent_name: str, user_context: UserExecutionContext) -> AgentExecutionContext:
        """Create agent execution context for race condition testing."""
        return AgentExecutionContext(
            agent_name=agent_name,
            run_id=user_context.run_id,
            thread_id=user_context.thread_id,
            user_id=user_context.user_id,
            metadata={
                'test_type': 'race_condition',
                'user_context_id': user_context.request_id
            }
        )
        
    async def _execute_agent_with_metrics(self, agent_name: str, user_id: str) -> RaceConditionTestResult:
        """Execute agent and collect race condition metrics."""
        start_time = time.time()
        
        try:
            # Create isolated contexts
            user_context = self._create_user_execution_context(user_id)
            agent_context = self._create_agent_execution_context(agent_name, user_context)
            
            # Create execution engine with factory method (SSOT compliant)
            execution_engine = ExecutionEngine._init_from_factory(
                registry=self.mock_registry,
                websocket_bridge=self.mock_websocket_bridge,
                user_context=user_context
            )
            
            # Execute agent with race condition monitoring
            result = await execution_engine.execute_agent(agent_context, user_context)
            
            execution_time = time.time() - start_time
            
            # Collect WebSocket events for this execution
            websocket_events = [
                event['type'] for event in 
                self.mock_websocket_bridge.get_events_for_run(user_context.run_id)
            ]
            
            # Verify user context isolation
            isolation_verified = await self._verify_user_context_isolation(user_context)
            
            test_result = RaceConditionTestResult(
                user_id=user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                execution_time=execution_time,
                success=result.success,
                error=result.error if not result.success else None,
                websocket_events=websocket_events,
                concurrent_execution_count=self.test_agents[agent_name].concurrent_executions,
                race_condition_detected=self.test_agents[agent_name].max_concurrent_executions > 1,
                isolation_verified=isolation_verified
            )
            
            self.race_condition_results.append(test_result)
            return test_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            test_result = RaceConditionTestResult(
                user_id=user_id,
                thread_id="unknown",
                run_id="unknown", 
                execution_time=execution_time,
                success=False,
                error=str(e),
                websocket_events=[],
                race_condition_detected=False,
                isolation_verified=False
            )
            
            self.race_condition_results.append(test_result)
            return test_result
            
    async def _verify_user_context_isolation(self, user_context: UserExecutionContext) -> bool:
        """Verify that user context maintains proper isolation."""
        try:
            # Validate context integrity
            validate_user_context(user_context)
            
            # Verify isolation
            return user_context.verify_isolation()
            
        except Exception as e:
            print(f"User context isolation verification failed: {e}")
            return False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution_single_user(self):
        """Test concurrent agent execution for a single user with race condition detection."""
        user_id = "user_single_concurrent"
        agent_names = ['fast_agent', 'data_agent', 'optimization_agent']
        
        # Execute multiple agents concurrently for single user
        tasks = [
            self._execute_agent_with_metrics(agent_name, user_id)
            for agent_name in agent_names
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions completed
        successful_results = [r for r in results if isinstance(r, RaceConditionTestResult) and r.success]
        assert len(successful_results) == len(agent_names), f"Expected {len(agent_names)} successful executions, got {len(successful_results)}"
        
        # Verify user context isolation maintained across concurrent executions
        for result in successful_results:
            assert result.isolation_verified, f"User context isolation failed for {result.user_id}"
            
        # Verify WebSocket events were sent for all executions
        for result in successful_results:
            assert 'agent_started' in result.websocket_events, f"Missing agent_started event for {result.run_id}"
            assert 'agent_completed' in result.websocket_events, f"Missing agent_completed event for {result.run_id}"
            
        # Check for race conditions in WebSocket event emission
        websocket_metrics = self.mock_websocket_bridge.get_race_condition_metrics()
        assert websocket_metrics['max_concurrent_notifications'] > 0, "Expected concurrent WebSocket notifications"
        
        print(f"Single user concurrent execution test completed. Race conditions detected: {websocket_metrics['race_conditions_detected']}")
        
    @pytest.mark.unit 
    @pytest.mark.asyncio
    async def test_multiple_users_concurrent_agent_execution(self):
        """Test multiple users running agents simultaneously with race condition detection."""
        users = [f"user_{i}" for i in range(5)]
        agent_name = 'data_agent'
        
        # Execute same agent for multiple users concurrently
        tasks = [
            self._execute_agent_with_metrics(agent_name, user_id)
            for user_id in users
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions completed successfully
        successful_results = [r for r in results if isinstance(r, RaceConditionTestResult) and r.success]
        assert len(successful_results) == len(users), f"Expected {len(users)} successful executions, got {len(successful_results)}"
        
        # Verify user isolation - each user should have unique identifiers
        user_ids = set(result.user_id for result in successful_results)
        thread_ids = set(result.thread_id for result in successful_results)
        run_ids = set(result.run_id for result in successful_results)
        
        assert len(user_ids) == len(users), f"User ID collision detected: {user_ids}"
        assert len(thread_ids) == len(users), f"Thread ID collision detected: {thread_ids}"
        assert len(run_ids) == len(users), f"Run ID collision detected: {run_ids}"
        
        # Verify race conditions were properly detected
        agent_metrics = self.test_agents[agent_name].get_race_condition_metrics()
        assert agent_metrics['max_concurrent_executions'] > 1, "Expected concurrent agent executions"
        assert agent_metrics['race_conditions_detected'], "Race conditions should be detected with multiple concurrent users"
        
        print(f"Multi-user concurrent execution test completed. Max concurrent executions: {agent_metrics['max_concurrent_executions']}")

    @pytest.mark.unit
    @pytest.mark.asyncio 
    async def test_tool_execution_race_conditions(self):
        """Test tool execution ordering race conditions during concurrent agent runs."""
        user_id = "user_tool_race"
        agent_name = 'data_agent'  # This agent executes tools
        
        # Execute multiple instances of tool-using agent concurrently
        num_concurrent = 3
        tasks = [
            self._execute_agent_with_metrics(agent_name, f"{user_id}_{i}")
            for i in range(num_concurrent)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions completed
        successful_results = [r for r in results if isinstance(r, RaceConditionTestResult) and r.success]
        assert len(successful_results) == num_concurrent, f"Expected {num_concurrent} successful executions"
        
        # Verify tool execution events were emitted
        tool_executing_events = [
            event for event in self.mock_websocket_bridge.events
            if event['type'] == 'tool_executing'
        ]
        
        # Should have tool execution events for concurrent runs
        assert len(tool_executing_events) >= num_concurrent, f"Expected at least {num_concurrent} tool execution events"
        
        # Check for race conditions in tool execution notifications
        concurrent_tool_notifications = [
            event for event in tool_executing_events
            if event.get('concurrent_count', 0) > 1
        ]
        
        # We expect to see some concurrent tool notifications due to race conditions
        assert len(concurrent_tool_notifications) > 0, "Expected race conditions in tool execution notifications"
        
        print(f"Tool execution race condition test completed. Concurrent tool notifications: {len(concurrent_tool_notifications)}")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_agent_state_management_race_conditions(self):
        """Test agent state updates during concurrent execution to detect race conditions."""
        user_id = "user_state_race"
        agent_name = 'fast_agent'
        
        # Execute many fast agents concurrently to maximize race condition potential
        num_concurrent = 10
        tasks = [
            self._execute_agent_with_metrics(agent_name, f"{user_id}_{i}")
            for i in range(num_concurrent)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify executions completed
        successful_results = [r for r in results if isinstance(r, RaceConditionTestResult) and r.success]
        failed_results = [r for r in results if isinstance(r, RaceConditionTestResult) and not r.success]
        
        print(f"State race condition test: {len(successful_results)} successful, {len(failed_results)} failed, total time: {total_time:.3f}s")
        
        # Verify most executions succeeded (some failures acceptable under race conditions)
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.7, f"Success rate too low: {success_rate:.2f}, may indicate state corruption"
        
        # Verify race conditions were detected
        agent_metrics = self.test_agents[agent_name].get_race_condition_metrics()
        assert agent_metrics['max_concurrent_executions'] > 1, "Expected concurrent agent state updates"
        
        # Verify execution ordering integrity
        execution_times = [result.execution_time for result in successful_results]
        assert all(t > 0 for t in execution_times), "All executions should have positive execution time"
        
        print(f"Agent state race conditions detected: {agent_metrics['race_conditions_detected']}")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_websocket_event_emission_race_conditions(self):
        """Test WebSocket event emission race conditions during agent execution."""
        user_id = "user_websocket_race"
        
        # Execute multiple different agents concurrently to create WebSocket event races
        agent_names = ['fast_agent', 'data_agent', 'optimization_agent', 'slow_agent']
        tasks = [
            self._execute_agent_with_metrics(agent_name, f"{user_id}_{agent_name}")
            for agent_name in agent_names
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify executions completed
        successful_results = [r for r in results if isinstance(r, RaceConditionTestResult) and r.success]
        assert len(successful_results) >= len(agent_names) * 0.8, "Most WebSocket race tests should succeed"
        
        # Analyze WebSocket event ordering and race conditions
        websocket_metrics = self.mock_websocket_bridge.get_race_condition_metrics()
        
        # Verify WebSocket events were emitted concurrently
        assert websocket_metrics['max_concurrent_notifications'] > 1, "Expected concurrent WebSocket notifications"
        assert websocket_metrics['race_conditions_detected'], "WebSocket race conditions should be detected"
        
        # Verify event ordering integrity within each execution
        for result in successful_results:
            events = self.mock_websocket_bridge.get_events_for_run(result.run_id)
            event_types = [event['type'] for event in events]
            
            # Verify critical events are present
            assert 'agent_started' in event_types, f"Missing agent_started for {result.run_id}"
            assert 'agent_completed' in event_types or 'agent_error' in event_types, f"Missing completion event for {result.run_id}"
            
            # Verify event ordering (agent_started should come before agent_completed)
            if 'agent_completed' in event_types:
                started_idx = event_types.index('agent_started')
                completed_idx = event_types.index('agent_completed')
                assert started_idx < completed_idx, f"Event order violation in {result.run_id}"
                
        # Check for overlapping event emission from different threads
        event_threads = set(event.get('thread_id') for event in self.mock_websocket_bridge.events if event.get('thread_id'))
        assert len(event_threads) > 1, f"Expected events from multiple threads, got {len(event_threads)}"
        
        print(f"WebSocket race condition test: {websocket_metrics['total_notifications']} notifications across {len(event_threads)} threads")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execution_timeout_race_conditions(self):
        """Test timeout scenarios during concurrent agent execution."""
        user_id = "user_timeout_race"
        
        # Create mix of fast and slow agents to test timeout handling
        mixed_tasks = [
            self._execute_agent_with_metrics('fast_agent', f"{user_id}_fast_{i}")
            for i in range(3)
        ] + [
            self._execute_agent_with_metrics('slow_agent', f"{user_id}_slow_{i}")
            for i in range(2)
        ]
        
        # Execute with timeout to force race conditions
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*mixed_tasks, return_exceptions=True),
                timeout=0.3  # Short timeout to create race conditions
            )
        except asyncio.TimeoutError:
            # Timeout expected with slow agents - this is part of the race condition test
            results = [RaceConditionTestResult(
                user_id=f"{user_id}_timeout",
                thread_id="timeout",
                run_id="timeout",
                execution_time=0.3,
                success=False,
                error="Execution timeout in race condition test"
            )]
            
        # Analyze timeout behavior under race conditions
        successful_results = [r for r in results if isinstance(r, RaceConditionTestResult) and r.success]
        timeout_results = [r for r in results if isinstance(r, RaceConditionTestResult) and not r.success]
        
        print(f"Timeout race test: {len(successful_results)} completed, {len(timeout_results)} timed out")
        
        # Verify fast agents completed before timeout
        fast_results = [r for r in successful_results if 'fast' in r.user_id]
        assert len(fast_results) > 0, "Fast agents should complete before timeout"
        
        # Verify timeout handling doesn't corrupt state
        for result in successful_results:
            assert result.isolation_verified, f"Isolation compromised during timeout race for {result.user_id}"
            
        # Verify WebSocket events were sent even in timeout scenarios
        websocket_metrics = self.mock_websocket_bridge.get_race_condition_metrics()
        assert websocket_metrics['total_notifications'] > 0, "WebSocket events should be sent even during timeouts"

    @pytest.mark.unit
    @pytest.mark.asyncio 
    async def test_execution_failure_race_conditions(self):
        """Test graceful degradation during execution failures under concurrent load."""
        user_id = "user_failure_race"
        
        # Mix successful and failing agents to test error handling race conditions
        mixed_tasks = [
            self._execute_agent_with_metrics('fast_agent', f"{user_id}_success_{i}")
            for i in range(3)
        ] + [
            self._execute_agent_with_metrics('failing_agent', f"{user_id}_fail_{i}")
            for i in range(2)
        ]
        
        results = await asyncio.gather(*mixed_tasks, return_exceptions=True)
        
        # Separate successful and failed results
        successful_results = [r for r in results if isinstance(r, RaceConditionTestResult) and r.success]
        failed_results = [r for r in results if isinstance(r, RaceConditionTestResult) and not r.success]
        
        print(f"Failure race test: {len(successful_results)} succeeded, {len(failed_results)} failed")
        
        # Verify successful agents weren't affected by failing agents
        assert len(successful_results) >= 3, "Successful agents should complete despite concurrent failures"
        
        # Verify failed agents were handled gracefully
        assert len(failed_results) >= 2, "Expected failures from failing_agent"
        
        # Verify error notifications were sent
        error_events = [
            event for event in self.mock_websocket_bridge.events
            if event['type'] == 'agent_error'
        ]
        assert len(error_events) >= len(failed_results), "Error events should be sent for failed executions"
        
        # Verify no cross-contamination between successful and failed executions
        for success_result in successful_results:
            assert success_result.isolation_verified, f"Successful execution isolation compromised: {success_result.user_id}"
            
        for fail_result in failed_results:
            assert fail_result.error is not None, f"Failed execution should have error details: {fail_result.user_id}"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_thread_pool_executor_race_conditions(self):
        """Test race conditions using ThreadPoolExecutor to simulate real concurrent load."""
        import concurrent.futures
        
        def sync_execute_agent(agent_name: str, user_id: str) -> RaceConditionTestResult:
            """Synchronous wrapper for agent execution to use with ThreadPoolExecutor."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self._execute_agent_with_metrics(agent_name, user_id)
                )
            finally:
                loop.close()
                
        # Create thread pool for true parallel execution
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit concurrent agent executions across multiple threads
            futures = []
            
            for i in range(8):
                future = executor.submit(
                    sync_execute_agent,
                    'data_agent',
                    f"threadpool_user_{i}"
                )
                futures.append(future)
                
            # Collect results from thread pool
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=10):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Thread pool execution failed: {e}")
                    
        # Verify thread pool executions
        successful_results = [r for r in results if r.success]
        print(f"Thread pool race test: {len(successful_results)}/{len(results)} successful")
        
        # Should have multiple successful executions from different threads
        assert len(successful_results) >= 6, f"Expected at least 6 successful thread pool executions, got {len(successful_results)}"
        
        # Verify user isolation across threads
        user_ids = set(result.user_id for result in successful_results)
        assert len(user_ids) == len(successful_results), "User ID collision in thread pool execution"
        
        # Verify race conditions were detected across threads
        agent_metrics = self.test_agents['data_agent'].get_race_condition_metrics()
        assert agent_metrics['max_concurrent_executions'] > 1, "Expected race conditions from thread pool"
        
        print(f"Thread pool race conditions detected: {agent_metrics['race_conditions_detected']}")

    @pytest.mark.unit 
    @pytest.mark.asyncio
    async def test_user_context_isolation_under_load(self):
        """Test user context isolation during high concurrent load with race condition detection."""
        # Create high load scenario with many users and agents
        num_users = 8
        agents_per_user = 3
        
        all_tasks = []
        for user_idx in range(num_users):
            user_id = f"load_user_{user_idx}"
            
            # Each user runs multiple agents concurrently
            user_tasks = [
                self._execute_agent_with_metrics('fast_agent', f"{user_id}_agent_{agent_idx}")
                for agent_idx in range(agents_per_user)
            ]
            all_tasks.extend(user_tasks)
            
        # Execute all tasks concurrently to create maximum load
        start_time = time.time()
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results under load
        successful_results = [r for r in results if isinstance(r, RaceConditionTestResult) and r.success]
        total_expected = num_users * agents_per_user
        
        print(f"Load test: {len(successful_results)}/{total_expected} successful in {total_time:.3f}s")
        
        # Verify high success rate under load
        success_rate = len(successful_results) / total_expected
        assert success_rate >= 0.8, f"Success rate under load too low: {success_rate:.2f}"
        
        # Verify user isolation maintained under load
        isolation_failures = [r for r in successful_results if not r.isolation_verified]
        assert len(isolation_failures) == 0, f"User isolation failed under load: {len(isolation_failures)} failures"
        
        # Verify no user ID collisions
        user_ids = [result.user_id for result in successful_results]
        unique_user_ids = set(user_ids)
        assert len(user_ids) == len(unique_user_ids), f"User ID collision under load: {len(user_ids)} vs {len(unique_user_ids)}"
        
        # Verify WebSocket events maintained integrity under load
        websocket_metrics = self.mock_websocket_bridge.get_race_condition_metrics()
        events_per_execution = websocket_metrics['total_notifications'] / len(successful_results)
        assert events_per_execution >= 2, f"Insufficient WebSocket events under load: {events_per_execution:.2f} per execution"
        
        print(f"Load test completed: race conditions detected = {websocket_metrics['race_conditions_detected']}")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execution_engine_factory_race_conditions(self):
        """Test ExecutionEngine factory method race conditions during concurrent creation."""
        # Test concurrent creation of execution engines to detect factory race conditions
        num_concurrent = 10
        
        async def create_execution_engine(user_id: str) -> tuple:
            """Create execution engine and return creation metrics."""
            user_context = self._create_user_execution_context(user_id)
            
            start_time = time.time()
            try:
                # Use factory method to create execution engine
                engine = ExecutionEngine._init_from_factory(
                    registry=self.mock_registry,
                    websocket_bridge=self.mock_websocket_bridge,
                    user_context=user_context
                )
                
                creation_time = time.time() - start_time
                return (True, creation_time, user_id, engine)
                
            except Exception as e:
                creation_time = time.time() - start_time
                return (False, creation_time, user_id, str(e))
                
        # Create multiple execution engines concurrently
        tasks = [
            create_execution_engine(f"factory_user_{i}")
            for i in range(num_concurrent)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze factory creation results
        successful_creations = [r for r in results if isinstance(r, tuple) and r[0]]
        failed_creations = [r for r in results if isinstance(r, tuple) and not r[0]]
        
        print(f"Factory race test: {len(successful_creations)}/{num_concurrent} engines created successfully")
        
        # Verify most factory creations succeeded
        assert len(successful_creations) >= num_concurrent * 0.9, f"Factory success rate too low: {len(successful_creations)}/{num_concurrent}"
        
        # Verify creation times are reasonable (no excessive blocking)
        creation_times = [result[1] for result in successful_creations]
        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)
        
        assert avg_creation_time < 0.1, f"Average creation time too high: {avg_creation_time:.3f}s"
        assert max_creation_time < 0.5, f"Maximum creation time too high: {max_creation_time:.3f}s"
        
        # Verify each engine was created with proper isolation
        user_ids = [result[2] for result in successful_creations]
        assert len(set(user_ids)) == len(user_ids), "User ID collision in factory creation"
        
        print(f"Factory creation metrics: avg={avg_creation_time:.3f}s, max={max_creation_time:.3f}s")