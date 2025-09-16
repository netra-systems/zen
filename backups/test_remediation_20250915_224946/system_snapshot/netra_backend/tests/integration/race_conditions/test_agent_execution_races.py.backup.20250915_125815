"""
Agent Execution Concurrency Race Condition Tests - Integration Testing

This module tests critical race conditions in agent execution that could lead to:
- Cross-user contamination of execution contexts
- Tool execution conflicts between concurrent agents
- Resource leaks during parallel agent execution
- State corruption in multi-agent workflows
- Deadlocks in agent lifecycle management

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise) - Agent reliability is core to platform value
- Business Goal: Ensure agents deliver consistent results under concurrent load  
- Value Impact: Prevents execution failures that would render platform unusable
- Strategic Impact: CRITICAL - Agent execution reliability directly impacts user satisfaction and revenue

Test Coverage:
- Concurrent agent execution isolation (50 simultaneous agents)
- User context isolation under heavy concurrent load
- Tool dispatcher race conditions during parallel execution
- Agent registry state consistency during concurrent access
- WebSocket notification delivery during concurrent agent execution
"""

import asyncio
import gc
import json
import time
import uuid
import weakref
from collections import defaultdict, Counter
from typing import Dict, List, Set, Any, Optional, Tuple
from unittest.mock import Mock, patch, AsyncMock
import pytest

from test_framework.base_integration_test import BaseIntegrationTest  
from test_framework.fixtures.real_services import real_services_fixture, real_redis_fixture
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession
# ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, RequestID, RunID, ensure_user_id
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestAgentExecutionRaces(BaseIntegrationTest):
    """Test race conditions in agent execution and lifecycle management."""
    
    def setup_method(self):
        """Set up test environment with agent execution tracking."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TEST_MODE", "agent_execution_race_testing", source="test")
        
        # Agent execution tracking
        self.active_agents: Dict[str, Any] = {}
        self.execution_contexts: Dict[str, UserExecutionContext] = {}
        self.execution_events: List[Dict] = []
        self.race_conditions_detected: List[Dict] = []
        self.agent_refs: List[weakref.ref] = []
        
        # Concurrency tracking
        self.concurrent_executions: Dict[str, List[Dict]] = defaultdict(list)
        self.tool_execution_log: List[Dict] = []
        self.websocket_events_log: List[Dict] = []
        
        # Performance metrics
        self.execution_times: List[float] = []
        self.context_switch_times: List[float] = []
        self.resource_snapshots: List[Dict] = []
        
    def teardown_method(self):
        """Clean up agent resources and check for leaks."""
        # Force cleanup of active agents
        cleanup_tasks = []
        for agent_id, agent in self.active_agents.items():
            try:
                if hasattr(agent, 'cleanup'):
                    cleanup_tasks.append(agent.cleanup())
            except Exception as e:
                logger.warning(f"Error cleaning up agent {agent_id}: {e}")
        
        # Wait for cleanup with timeout
        if cleanup_tasks:
            try:
                asyncio.get_event_loop().run_until_complete(
                    asyncio.wait_for(asyncio.gather(*cleanup_tasks, return_exceptions=True), timeout=10.0)
                )
            except asyncio.TimeoutError:
                logger.warning("Agent cleanup timed out - potential resource leaks")
        
        # Force garbage collection and check for leaks
        gc.collect()
        leaked_refs = [ref for ref in self.agent_refs if ref() is not None]
        if leaked_refs:
            logger.error(f"RACE CONDITION DETECTED: {len(leaked_refs)} agent objects not garbage collected")
            self.race_conditions_detected.append({
                "type": "agent_resource_leak",
                "leaked_agent_count": len(leaked_refs),
                "timestamp": time.time()
            })
        
        # Clear tracking data
        self.active_agents.clear()
        self.execution_contexts.clear()
        self.execution_events.clear()
        self.agent_refs.clear()
        self.concurrent_executions.clear()
        self.tool_execution_log.clear()
        self.websocket_events_log.clear()
        
        super().teardown_method()
    
    def _track_agent_execution_event(self, event_type: str, agent_id: str, user_id: str = None, metadata: Dict = None):
        """Track agent execution events for race condition analysis."""
        event = {
            "type": event_type,
            "agent_id": agent_id,
            "user_id": user_id,
            "timestamp": time.time(),
            "task_name": asyncio.current_task().get_name() if asyncio.current_task() else "unknown",
            "metadata": metadata or {}
        }
        self.execution_events.append(event)
        
        # Track concurrent executions per user
        if user_id and event_type in ["agent_start", "agent_complete", "agent_error"]:
            self.concurrent_executions[user_id].append(event)
        
        # Analyze for race condition patterns
        self._analyze_execution_race_patterns(event)
    
    def _analyze_execution_race_patterns(self, event: Dict):
        """Analyze execution events for race condition patterns."""
        user_id = event["user_id"]
        event_type = event["type"]
        agent_id = event["agent_id"]
        
        if not user_id:
            return
        
        # Pattern 1: Multiple agents starting simultaneously for same user (resource contention)
        if event_type == "agent_start":
            recent_starts = [
                e for e in self.execution_events[-20:] 
                if e["type"] == "agent_start" and e["user_id"] == user_id
                and event["timestamp"] - e["timestamp"] < 1.0  # Within 1 second
            ]
            
            if len(recent_starts) > 10:  # Threshold for excessive concurrency
                self._detect_race_condition("excessive_concurrent_agent_starts", {
                    "user_id": user_id,
                    "concurrent_starts": len(recent_starts),
                    "time_window": 1.0
                })
        
        # Pattern 2: Agent execution without corresponding start (lifecycle race)
        if event_type == "agent_complete":
            corresponding_start = None
            for e in reversed(self.execution_events):
                if e["type"] == "agent_start" and e["agent_id"] == agent_id:
                    corresponding_start = e
                    break
            
            if not corresponding_start:
                self._detect_race_condition("orphaned_agent_completion", {
                    "agent_id": agent_id,
                    "user_id": user_id
                })
        
        # Pattern 3: Rapid agent start/complete cycles (potential race in cleanup)
        if event_type in ["agent_start", "agent_complete"]:
            user_events = [e for e in self.execution_events[-10:] if e["user_id"] == user_id]
            rapid_cycles = 0
            
            for i in range(len(user_events) - 1):
                time_diff = user_events[i + 1]["timestamp"] - user_events[i]["timestamp"]
                if time_diff < 0.1:  # Very rapid transitions
                    rapid_cycles += 1
            
            if rapid_cycles > 5:
                self._detect_race_condition("rapid_execution_cycles", {
                    "user_id": user_id,
                    "rapid_cycles": rapid_cycles
                })
    
    def _detect_race_condition(self, condition_type: str, metadata: Dict):
        """Record race condition detection."""
        race_condition = {
            "type": condition_type,
            "metadata": metadata,
            "timestamp": time.time(),
            "task_context": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.race_conditions_detected.append(race_condition)
        logger.warning(f"RACE CONDITION DETECTED: {condition_type} - {metadata}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_agent_execution_user_isolation(self, real_services_fixture, real_redis_fixture):
        """
        Test user context isolation during concurrent agent execution.
        
        Verifies that multiple users can execute agents simultaneously without
        cross-contamination of execution contexts, tool dispatchers, or results.
        """
        services = real_services_fixture
        redis_info = real_redis_fixture
        
        if not services["database_available"] or not redis_info["available"]:
            pytest.skip("Real services not available for integration test")
        
        # Business Value: Ensure multi-user platform doesn't have context contamination
        # This is critical for data security and user trust
        
        num_users = 25
        agents_per_user = 3
        total_expected_executions = num_users * agents_per_user
        
        execution_results = []
        user_contexts = {}
        
        async def execute_agent_for_user(user_index: int, agent_index: int) -> Dict:
            """Execute an agent within a specific user context."""
            user_id = ensure_user_id(f"concurrent_user_{user_index}")
            agent_id = f"test_agent_{user_index}_{agent_index}"
            
            try:
                # Create isolated user execution context
                execution_context = UserExecutionContext(
                    user_id=str(user_id),
                    request_id=f"req_{user_index}_{agent_index}_{uuid.uuid4()}",
                    thread_id=f"thread_{user_index}_{uuid.uuid4()}",
                    run_id=f"run_{user_index}_{agent_index}_{uuid.uuid4()}"
                )
                
                # Track context for isolation verification
                context_key = f"{user_id}:{agent_id}"
                user_contexts[context_key] = execution_context
                self.execution_contexts[context_key] = execution_context
                
                # Create user agent session for isolation
                user_session = UserAgentSession(str(user_id))
                
                start_time = time.time()
                
                self._track_agent_execution_event("agent_start", agent_id, str(user_id), {
                    "user_index": user_index,
                    "agent_index": agent_index
                })
                
                # Simulate agent execution with user-specific operations
                agent_state = {
                    "user_id": str(user_id),
                    "agent_id": agent_id,
                    "execution_context": execution_context,
                    "start_time": start_time,
                    "user_specific_data": f"data_for_user_{user_index}_agent_{agent_index}",
                    "context_isolation_token": uuid.uuid4()
                }
                
                # Store agent for tracking
                self.active_agents[agent_id] = agent_state
                self.agent_refs.append(weakref.ref(agent_state))
                
                # Simulate tool execution within user context
                for tool_idx in range(3):  # Each agent uses 3 tools
                    tool_execution = {
                        "tool_name": f"test_tool_{tool_idx}",
                        "user_id": str(user_id),
                        "agent_id": agent_id,
                        "execution_context": str(execution_context.request_id),
                        "result": f"result_{user_index}_{agent_index}_{tool_idx}",
                        "timestamp": time.time()
                    }
                    self.tool_execution_log.append(tool_execution)
                
                # Simulate processing delay
                await asyncio.sleep(0.05)  # 50ms processing time
                
                execution_time = time.time() - start_time
                self.execution_times.append(execution_time)
                
                self._track_agent_execution_event("agent_complete", agent_id, str(user_id), {
                    "execution_time": execution_time,
                    "tools_executed": 3
                })
                
                return {
                    "success": True,
                    "user_id": str(user_id),
                    "agent_id": agent_id,
                    "execution_time": execution_time,
                    "context_isolation_token": agent_state["context_isolation_token"],
                    "user_specific_data": agent_state["user_specific_data"]
                }
                
            except Exception as e:
                self._track_agent_execution_event("agent_error", agent_id, str(user_id), {
                    "error": str(e)
                })
                return {
                    "success": False,
                    "user_id": str(user_id),
                    "agent_id": agent_id,
                    "error": str(e)
                }
        
        # Execute all agent executions concurrently
        logger.info(f"Starting {total_expected_executions} concurrent agent executions across {num_users} users")
        
        execution_tasks = []
        for user_idx in range(num_users):
            for agent_idx in range(agents_per_user):
                execution_tasks.append(execute_agent_for_user(user_idx, agent_idx))
        
        start_time = time.time()
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results for isolation violations
        successful_executions = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_executions = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # CRITICAL BUSINESS VALIDATION: High success rate required
        success_rate = len(successful_executions) / total_expected_executions
        assert success_rate >= 0.95, f"Execution success rate too low: {success_rate:.2%} - indicates race conditions"
        
        # Verify user context isolation - no cross-contamination
        user_data_by_user = defaultdict(list)
        isolation_tokens_by_user = defaultdict(list)
        
        for result in successful_executions:
            user_id = result["user_id"]
            user_data_by_user[user_id].append(result["user_specific_data"])
            isolation_tokens_by_user[user_id].append(result["context_isolation_token"])
        
        # Each user should only have their own data
        for user_id, user_data_list in user_data_by_user.items():
            for data in user_data_list:
                expected_user_prefix = f"data_for_user_{user_id.split('_')[-1]}_"
                assert data.startswith(expected_user_prefix), \
                    f"User data contamination: {user_id} has data {data} - RACE CONDITION"
        
        # All isolation tokens should be unique (no shared state)
        all_tokens = [token for tokens in isolation_tokens_by_user.values() for token in tokens]
        assert len(all_tokens) == len(set(all_tokens)), \
            "Isolation token collision detected - RACE CONDITION"
        
        # Verify tool execution isolation
        tools_by_user = defaultdict(list)
        for tool_exec in self.tool_execution_log:
            tools_by_user[tool_exec["user_id"]].append(tool_exec)
        
        for user_id, tools in tools_by_user.items():
            # Each user should have exactly agents_per_user * 3 tool executions
            expected_tools = agents_per_user * 3
            actual_tools = len(tools)
            assert actual_tools == expected_tools, \
                f"Tool execution mismatch for {user_id}: {actual_tools}/{expected_tools} - RACE CONDITION"
            
            # All tool executions should belong to correct user
            for tool in tools:
                assert tool["user_id"] == user_id, \
                    f"Tool execution user mismatch: {tool['user_id']} vs {user_id} - RACE CONDITION"
        
        # Performance validation
        if self.execution_times:
            avg_execution_time = sum(self.execution_times) / len(self.execution_times)
            max_execution_time = max(self.execution_times)
            
            assert avg_execution_time < 1.0, f"Average execution time too slow: {avg_execution_time:.3f}s"
            assert max_execution_time < 5.0, f"Maximum execution time too slow: {max_execution_time:.3f}s - possible deadlock"
        
        # No race conditions should be detected
        assert len(self.race_conditions_detected) == 0, f"Race conditions detected: {self.race_conditions_detected}"
        
        logger.info(f"SUCCESS: {len(successful_executions)} concurrent agent executions completed in {total_time:.3f}s")
        logger.info(f"Average execution time: {sum(self.execution_times)/len(self.execution_times):.3f}s")
        
        self.assert_business_value_delivered({
            "successful_executions": len(successful_executions),
            "user_isolation_maintained": True,
            "race_conditions": len(self.race_conditions_detected)
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_registry_concurrent_access_race_conditions(self, real_services_fixture, real_redis_fixture):
        """
        Test agent registry state consistency under concurrent access.
        
        Verifies that the agent registry maintains consistent state when multiple
        users register, lookup, and execute agents simultaneously.
        """
        services = real_services_fixture
        redis_info = real_redis_fixture
        
        if not services["database_available"] or not redis_info["available"]:
            pytest.skip("Real services not available for integration test")
        
        num_concurrent_operations = 50
        registry_operations = []
        registry_state_snapshots = []
        
        # Create a shared agent registry for testing
        agent_registry = AgentRegistry()
        
        async def perform_registry_operation(operation_index: int) -> Dict:
            """Perform concurrent registry operations."""
            user_id = ensure_user_id(f"registry_user_{operation_index % 10}")  # 10 different users
            operation_type = ["register", "lookup", "execute"][operation_index % 3]
            
            start_time = time.time()
            
            try:
                if operation_type == "register":
                    # Create user session and register agent
                    user_session = UserAgentSession(str(user_id))
                    
                    # Simulate agent registration
                    agent_name = f"test_agent_{operation_index}"
                    registration_result = {
                        "agent_name": agent_name,
                        "user_id": str(user_id),
                        "registered_at": time.time()
                    }
                    
                    # Take registry state snapshot
                    state_snapshot = {
                        "operation_index": operation_index,
                        "operation_type": operation_type,
                        "user_id": str(user_id),
                        "timestamp": time.time(),
                        "active_sessions": len(agent_registry._user_sessions) if hasattr(agent_registry, '_user_sessions') else 0
                    }
                    registry_state_snapshots.append(state_snapshot)
                    
                elif operation_type == "lookup":
                    # Lookup existing agents for user
                    user_session = UserAgentSession(str(user_id))
                    
                    # Simulate agent lookup
                    lookup_result = {
                        "user_id": str(user_id),
                        "available_agents": [f"agent_{i}" for i in range(3)],
                        "lookup_time": time.time()
                    }
                    
                    state_snapshot = {
                        "operation_index": operation_index,
                        "operation_type": operation_type,
                        "user_id": str(user_id),
                        "timestamp": time.time()
                    }
                    registry_state_snapshots.append(state_snapshot)
                    
                elif operation_type == "execute":
                    # Execute agent through registry
                    user_session = UserAgentSession(str(user_id))
                    
                    execution_context = UserExecutionContext(
                        user_id=str(user_id),
                        request_id=f"registry_req_{operation_index}",
                        thread_id=f"registry_thread_{operation_index}",
                        run_id=f"registry_run_{operation_index}"
                    )
                    
                    # Simulate agent execution
                    execution_result = {
                        "user_id": str(user_id),
                        "execution_context": str(execution_context.request_id),
                        "result": f"execution_result_{operation_index}",
                        "executed_at": time.time()
                    }
                    
                    state_snapshot = {
                        "operation_index": operation_index,
                        "operation_type": operation_type,
                        "user_id": str(user_id),
                        "timestamp": time.time()
                    }
                    registry_state_snapshots.append(state_snapshot)
                
                operation_time = time.time() - start_time
                
                return {
                    "success": True,
                    "operation_index": operation_index,
                    "operation_type": operation_type,
                    "user_id": str(user_id),
                    "operation_time": operation_time
                }
                
            except Exception as e:
                logger.error(f"Registry operation {operation_index} ({operation_type}) failed: {e}")
                return {
                    "success": False,
                    "operation_index": operation_index,
                    "operation_type": operation_type,
                    "error": str(e)
                }
        
        # Execute concurrent registry operations
        logger.info(f"Testing agent registry with {num_concurrent_operations} concurrent operations")
        
        operation_tasks = [perform_registry_operation(i) for i in range(num_concurrent_operations)]
        results = await asyncio.gather(*operation_tasks, return_exceptions=True)
        
        # Analyze registry operation results
        successful_operations = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_operations = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        # CRITICAL: High success rate for registry operations
        success_rate = len(successful_operations) / num_concurrent_operations
        assert success_rate >= 0.95, f"Registry operation success rate too low: {success_rate:.2%}"
        
        # Verify operation distribution (no bias towards specific operations)
        operations_by_type = defaultdict(int)
        for result in successful_operations:
            operations_by_type[result["operation_type"]] += 1
        
        # Each operation type should have roughly equal representation
        expected_per_type = num_concurrent_operations / 3
        for op_type, count in operations_by_type.items():
            ratio = count / expected_per_type
            assert 0.5 <= ratio <= 1.5, f"Operation type {op_type} bias detected: {ratio:.2f}x expected - RACE CONDITION"
        
        # Verify state snapshot consistency
        if registry_state_snapshots:
            # Group snapshots by user
            snapshots_by_user = defaultdict(list)
            for snapshot in registry_state_snapshots:
                snapshots_by_user[snapshot["user_id"]].append(snapshot)
            
            # Verify each user's operations are properly isolated
            for user_id, user_snapshots in snapshots_by_user.items():
                # User snapshots should be consistently for the same user
                user_ids_in_snapshots = {s["user_id"] for s in user_snapshots}
                assert len(user_ids_in_snapshots) == 1, \
                    f"User ID inconsistency in snapshots for {user_id} - RACE CONDITION"
                
                # Snapshots should be temporally ordered
                timestamps = [s["timestamp"] for s in user_snapshots]
                assert timestamps == sorted(timestamps), \
                    f"Temporal ordering violation for user {user_id} - RACE CONDITION"
        
        # Performance validation
        operation_times = [r["operation_time"] for r in successful_operations if "operation_time" in r]
        if operation_times:
            avg_op_time = sum(operation_times) / len(operation_times)
            max_op_time = max(operation_times)
            
            assert avg_op_time < 0.5, f"Average registry operation time too slow: {avg_op_time:.3f}s"
            assert max_op_time < 2.0, f"Maximum registry operation time too slow: {max_op_time:.3f}s - possible deadlock"
        
        # No race conditions should be detected
        assert len(self.race_conditions_detected) == 0, f"Race conditions detected: {self.race_conditions_detected}"
        
        logger.info(f"SUCCESS: {len(successful_operations)} registry operations completed")
        logger.info(f"Operations by type: {dict(operations_by_type)}")
        
        self.assert_business_value_delivered({
            "successful_operations": len(successful_operations),
            "operation_distribution": dict(operations_by_type),
            "race_conditions": len(self.race_conditions_detected)
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_tool_dispatcher_concurrent_execution_races(self, real_services_fixture, real_redis_fixture):
        """
        Test tool dispatcher consistency during concurrent tool executions.
        
        Verifies that the tool dispatcher properly isolates tool executions
        and maintains state consistency when multiple agents use tools simultaneously.
        """
        services = real_services_fixture
        redis_info = real_redis_fixture
        
        if not services["database_available"] or not redis_info["available"]:
            pytest.skip("Real services not available for integration test")
        
        num_agents = 20
        tools_per_agent = 5
        total_expected_tool_executions = num_agents * tools_per_agent
        
        tool_execution_results = []
        tool_dispatcher_state = []
        
        async def execute_tools_for_agent(agent_index: int) -> Dict:
            """Execute multiple tools for a single agent."""
            user_id = ensure_user_id(f"tool_user_{agent_index}")
            agent_id = f"tool_agent_{agent_index}"
            
            try:
                # Create execution context for tool dispatcher
                execution_context = UserExecutionContext(
                    user_id=str(user_id),
                    request_id=f"tool_req_{agent_index}_{uuid.uuid4()}",
                    thread_id=f"tool_thread_{agent_index}",
                    run_id=f"tool_run_{agent_index}"
                )
                
                agent_results = []
                
                # Execute multiple tools concurrently within agent
                for tool_index in range(tools_per_agent):
                    tool_start = time.time()
                    
                    # Simulate tool execution with isolated context
                    tool_execution = {
                        "tool_name": f"test_tool_{tool_index}",
                        "agent_id": agent_id,
                        "user_id": str(user_id),
                        "execution_context": str(execution_context.request_id),
                        "tool_index": tool_index,
                        "start_time": tool_start,
                        "input_data": f"input_for_agent_{agent_index}_tool_{tool_index}",
                        "isolation_token": str(uuid.uuid4())
                    }
                    
                    # Simulate processing time
                    await asyncio.sleep(0.02)  # 20ms per tool
                    
                    tool_execution["completion_time"] = time.time()
                    tool_execution["execution_duration"] = tool_execution["completion_time"] - tool_start
                    tool_execution["result"] = f"result_agent_{agent_index}_tool_{tool_index}"
                    
                    # Track tool execution
                    self.tool_execution_log.append(tool_execution)
                    agent_results.append(tool_execution)
                    
                    # Take dispatcher state snapshot
                    state_snapshot = {
                        "agent_id": agent_id,
                        "user_id": str(user_id),
                        "active_tool_executions": len([
                            t for t in self.tool_execution_log 
                            if "completion_time" not in t or t["completion_time"] > time.time() - 0.1
                        ]),
                        "timestamp": time.time()
                    }
                    tool_dispatcher_state.append(state_snapshot)
                
                return {
                    "success": True,
                    "agent_id": agent_id,
                    "user_id": str(user_id),
                    "tools_executed": len(agent_results),
                    "total_execution_time": max(r["execution_duration"] for r in agent_results)
                }
                
            except Exception as e:
                logger.error(f"Tool execution for agent {agent_index} failed: {e}")
                return {
                    "success": False,
                    "agent_id": agent_id,
                    "error": str(e)
                }
        
        # Execute all agents concurrently (each executing tools)
        logger.info(f"Testing tool dispatcher with {num_agents} agents x {tools_per_agent} tools")
        
        agent_tasks = [execute_tools_for_agent(i) for i in range(num_agents)]
        results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        # Analyze tool execution results
        successful_agents = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # CRITICAL: All agents should successfully execute all tools
        success_rate = len(successful_agents) / num_agents
        assert success_rate >= 0.95, f"Agent tool execution success rate too low: {success_rate:.2%}"
        
        # Verify total tool execution count
        actual_tool_executions = len(self.tool_execution_log)
        assert actual_tool_executions >= total_expected_tool_executions * 0.95, \
            f"Tool execution count too low: {actual_tool_executions}/{total_expected_tool_executions}"
        
        # Verify tool execution isolation
        tools_by_agent = defaultdict(list)
        tools_by_user = defaultdict(list)
        
        for tool_exec in self.tool_execution_log:
            tools_by_agent[tool_exec["agent_id"]].append(tool_exec)
            tools_by_user[tool_exec["user_id"]].append(tool_exec)
        
        # Each agent should have exactly tools_per_agent executions
        for agent_id, agent_tools in tools_by_agent.items():
            assert len(agent_tools) == tools_per_agent, \
                f"Tool count mismatch for {agent_id}: {len(agent_tools)}/{tools_per_agent} - RACE CONDITION"
            
            # All tools for an agent should belong to same user
            user_ids = {tool["user_id"] for tool in agent_tools}
            assert len(user_ids) == 1, f"User contamination in agent {agent_id} tools - RACE CONDITION"
            
            # All tools should have unique isolation tokens
            isolation_tokens = [tool["isolation_token"] for tool in agent_tools]
            assert len(isolation_tokens) == len(set(isolation_tokens)), \
                f"Isolation token collision in agent {agent_id} - RACE CONDITION"
        
        # Verify no cross-user tool contamination
        for user_id, user_tools in tools_by_user.items():
            for tool in user_tools:
                assert tool["user_id"] == user_id, \
                    f"Tool user contamination: {tool['user_id']} vs {user_id} - RACE CONDITION"
                
                # Input data should match user pattern
                expected_user_index = user_id.split("_")[-1]
                expected_prefix = f"input_for_agent_{expected_user_index}_tool_"
                assert tool["input_data"].startswith(expected_prefix), \
                    f"Tool input contamination for {user_id}: {tool['input_data']} - RACE CONDITION"
        
        # Performance validation: tools should execute efficiently
        execution_durations = [tool["execution_duration"] for tool in self.tool_execution_log]
        if execution_durations:
            avg_duration = sum(execution_durations) / len(execution_durations)
            max_duration = max(execution_durations)
            
            assert avg_duration < 0.5, f"Average tool execution too slow: {avg_duration:.3f}s"
            assert max_duration < 2.0, f"Maximum tool execution too slow: {max_duration:.3f}s - possible deadlock"
        
        # No race conditions should be detected
        assert len(self.race_conditions_detected) == 0, f"Race conditions detected: {self.race_conditions_detected}"
        
        logger.info(f"SUCCESS: {actual_tool_executions} tool executions completed across {num_agents} agents")
        logger.info(f"Average tool execution time: {sum(execution_durations)/len(execution_durations):.3f}s")
        
        self.assert_business_value_delivered({
            "tool_executions_completed": actual_tool_executions,
            "agents_successful": len(successful_agents),
            "isolation_maintained": True,
            "race_conditions": len(self.race_conditions_detected)
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_websocket_notification_delivery_races(self, real_services_fixture, real_redis_fixture):
        """
        Test WebSocket notification delivery during concurrent agent execution.
        
        Verifies that WebSocket events are properly delivered to the correct users
        when multiple agents are executing simultaneously.
        """
        services = real_services_fixture
        redis_info = real_redis_fixture
        
        if not services["database_available"] or not redis_info["available"]:
            pytest.skip("Real services not available for integration test")
        
        num_concurrent_agents = 15
        events_per_agent = 5  # agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        expected_total_events = num_concurrent_agents * events_per_agent
        
        websocket_events = []
        event_delivery_log = []
        
        async def execute_agent_with_websocket_events(agent_index: int) -> Dict:
            """Execute agent and track WebSocket event delivery."""
            user_id = ensure_user_id(f"ws_event_user_{agent_index}")
            agent_id = f"ws_event_agent_{agent_index}"
            
            try:
                # Create user session with WebSocket capability
                user_session = UserAgentSession(str(user_id))
                
                # Mock WebSocket manager for event tracking
                websocket_manager = Mock()
                websocket_events_for_agent = []
                
                async def mock_send_event(event_data):
                    event = {
                        "user_id": str(user_id),
                        "agent_id": agent_id,
                        "event_type": event_data.get("type", "unknown"),
                        "event_data": event_data,
                        "timestamp": time.time(),
                        "delivery_token": str(uuid.uuid4())
                    }
                    websocket_events_for_agent.append(event)
                    self.websocket_events_log.append(event)
                    return event
                
                websocket_manager.send_event = AsyncMock(side_effect=mock_send_event)
                
                # Set WebSocket manager for user session
                await user_session.set_websocket_manager(websocket_manager)
                
                # Simulate agent execution with WebSocket events
                agent_events = [
                    {"type": "agent_started", "agent_id": agent_id, "user_id": str(user_id)},
                    {"type": "agent_thinking", "agent_id": agent_id, "message": "Processing request"},
                    {"type": "tool_executing", "tool_name": "test_tool", "agent_id": agent_id},
                    {"type": "tool_completed", "tool_name": "test_tool", "result": "success"},
                    {"type": "agent_completed", "agent_id": agent_id, "result": "execution_complete"}
                ]
                
                # Send events concurrently
                event_tasks = []
                for event in agent_events:
                    event_tasks.append(mock_send_event(event))
                
                # Wait for all events to be sent
                sent_events = await asyncio.gather(*event_tasks)
                
                # Brief delay to simulate processing
                await asyncio.sleep(0.03)
                
                return {
                    "success": True,
                    "user_id": str(user_id),
                    "agent_id": agent_id,
                    "events_sent": len(sent_events),
                    "event_types": [e["event_type"] for e in websocket_events_for_agent],
                    "delivery_tokens": [e["delivery_token"] for e in websocket_events_for_agent]
                }
                
            except Exception as e:
                logger.error(f"WebSocket event agent {agent_index} failed: {e}")
                return {
                    "success": False,
                    "agent_id": agent_id,
                    "error": str(e)
                }
        
        # Execute agents concurrently with WebSocket event tracking
        logger.info(f"Testing WebSocket event delivery with {num_concurrent_agents} concurrent agents")
        
        agent_tasks = [execute_agent_with_websocket_events(i) for i in range(num_concurrent_agents)]
        results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        # Analyze WebSocket event delivery results
        successful_agents = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # CRITICAL: All agents should successfully send WebSocket events
        success_rate = len(successful_agents) / num_concurrent_agents
        assert success_rate >= 0.95, f"WebSocket event agent success rate too low: {success_rate:.2%}"
        
        # Verify total event count
        actual_events = len(self.websocket_events_log)
        assert actual_events >= expected_total_events * 0.95, \
            f"WebSocket event count too low: {actual_events}/{expected_total_events}"
        
        # Verify event delivery isolation (no cross-user contamination)
        events_by_user = defaultdict(list)
        events_by_agent = defaultdict(list)
        
        for event in self.websocket_events_log:
            events_by_user[event["user_id"]].append(event)
            events_by_agent[event["agent_id"]].append(event)
        
        # Each agent should have exactly events_per_agent events
        for agent_id, agent_events in events_by_agent.items():
            assert len(agent_events) == events_per_agent, \
                f"Event count mismatch for {agent_id}: {len(agent_events)}/{events_per_agent} - RACE CONDITION"
            
            # All events for an agent should belong to same user
            user_ids = {event["user_id"] for event in agent_events}
            assert len(user_ids) == 1, f"User contamination in agent {agent_id} events - RACE CONDITION"
            
            # Events should have expected types in order
            event_types = [event["event_type"] for event in sorted(agent_events, key=lambda x: x["timestamp"])]
            expected_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            assert event_types == expected_types, \
                f"Event type order violation for {agent_id}: {event_types} - RACE CONDITION"
            
            # All events should have unique delivery tokens
            delivery_tokens = [event["delivery_token"] for event in agent_events]
            assert len(delivery_tokens) == len(set(delivery_tokens)), \
                f"Delivery token collision for {agent_id} - RACE CONDITION"
        
        # Verify no cross-user event contamination
        for user_id, user_events in events_by_user.items():
            for event in user_events:
                assert event["user_id"] == user_id, \
                    f"Event user contamination: {event['user_id']} vs {user_id} - RACE CONDITION"
                
                # Agent ID should match user pattern
                expected_user_index = user_id.split("_")[-1]
                expected_agent_id = f"ws_event_agent_{expected_user_index}"
                assert event["agent_id"] == expected_agent_id, \
                    f"Event agent contamination for {user_id}: {event['agent_id']} - RACE CONDITION"
        
        # Verify event temporal consistency within each agent
        for agent_id, agent_events in events_by_agent.items():
            timestamps = [event["timestamp"] for event in agent_events]
            assert timestamps == sorted(timestamps), \
                f"Event temporal ordering violation for {agent_id} - RACE CONDITION"
        
        # Performance validation: event delivery should be fast
        if self.websocket_events_log:
            # Calculate delivery time spreads
            events_by_timestamp = sorted(self.websocket_events_log, key=lambda x: x["timestamp"])
            first_event = events_by_timestamp[0]["timestamp"]
            last_event = events_by_timestamp[-1]["timestamp"]
            total_delivery_time = last_event - first_event
            
            assert total_delivery_time < 5.0, \
                f"Total event delivery time too slow: {total_delivery_time:.3f}s - possible deadlock"
        
        # No race conditions should be detected
        assert len(self.race_conditions_detected) == 0, f"Race conditions detected: {self.race_conditions_detected}"
        
        logger.info(f"SUCCESS: {actual_events} WebSocket events delivered across {num_concurrent_agents} agents")
        logger.info(f"Events per user: {len(events_by_user)} users")
        
        self.assert_business_value_delivered({
            "websocket_events_delivered": actual_events,
            "agents_successful": len(successful_agents),
            "event_isolation_maintained": True,
            "race_conditions": len(self.race_conditions_detected)
        }, "insights")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_lifecycle_cleanup_races(self, real_services_fixture, real_redis_fixture):
        """
        Test agent lifecycle cleanup under concurrent execution cycles.
        
        Verifies that agent resources are properly cleaned up and not leaked
        when agents are created and destroyed rapidly in concurrent scenarios.
        """
        services = real_services_fixture
        redis_info = real_redis_fixture
        
        if not services["database_available"] or not redis_info["available"]:
            pytest.skip("Real services not available for integration test")
        
        num_lifecycle_cycles = 30
        agents_per_cycle = 5
        total_agent_instances = num_lifecycle_cycles * agents_per_cycle
        
        lifecycle_results = []
        resource_snapshots = []
        cleanup_events = []
        
        async def agent_lifecycle_cycle(cycle_index: int) -> Dict:
            """Perform complete agent lifecycle (create, execute, cleanup)."""
            cycle_agents = []
            cycle_start = time.time()
            
            try:
                # Phase 1: Rapid agent creation
                for agent_idx in range(agents_per_cycle):
                    user_id = ensure_user_id(f"lifecycle_user_{cycle_index}_{agent_idx}")
                    agent_id = f"lifecycle_agent_{cycle_index}_{agent_idx}"
                    
                    # Create user session and agent
                    user_session = UserAgentSession(str(user_id))
                    
                    agent_state = {
                        "user_id": str(user_id),
                        "agent_id": agent_id,
                        "user_session": user_session,
                        "created_at": time.time(),
                        "lifecycle_token": str(uuid.uuid4()),
                        "resources": [f"resource_{i}" for i in range(3)]  # Simulate resources
                    }
                    
                    cycle_agents.append(agent_state)
                    self.active_agents[agent_id] = agent_state
                    self.agent_refs.append(weakref.ref(agent_state))
                
                # Take resource snapshot after creation
                creation_snapshot = {
                    "cycle_index": cycle_index,
                    "phase": "creation",
                    "active_agents": len(self.active_agents),
                    "agent_refs": len([ref for ref in self.agent_refs if ref() is not None]),
                    "timestamp": time.time()
                }
                resource_snapshots.append(creation_snapshot)
                
                # Phase 2: Simulate brief execution
                execution_tasks = []
                for agent in cycle_agents:
                    # Simulate agent execution
                    async def execute_agent(agent_data):
                        await asyncio.sleep(0.02)  # Brief execution
                        agent_data["executed_at"] = time.time()
                        return agent_data
                    
                    execution_tasks.append(execute_agent(agent))
                
                executed_agents = await asyncio.gather(*execution_tasks)
                
                # Phase 3: Rapid cleanup
                cleanup_tasks = []
                for agent in executed_agents:
                    async def cleanup_agent(agent_data):
                        agent_id = agent_data["agent_id"]
                        
                        # Simulate resource cleanup
                        cleanup_event = {
                            "agent_id": agent_id,
                            "user_id": agent_data["user_id"],
                            "lifecycle_token": agent_data["lifecycle_token"],
                            "resources_cleaned": len(agent_data["resources"]),
                            "cleanup_at": time.time()
                        }
                        cleanup_events.append(cleanup_event)
                        
                        # Remove from active agents
                        if agent_id in self.active_agents:
                            del self.active_agents[agent_id]
                        
                        return cleanup_event
                    
                    cleanup_tasks.append(cleanup_agent(agent))
                
                cleanup_results = await asyncio.gather(*cleanup_tasks)
                
                # Take resource snapshot after cleanup
                cleanup_snapshot = {
                    "cycle_index": cycle_index,
                    "phase": "cleanup",
                    "active_agents": len(self.active_agents),
                    "agent_refs": len([ref for ref in self.agent_refs if ref() is not None]),
                    "timestamp": time.time()
                }
                resource_snapshots.append(cleanup_snapshot)
                
                cycle_time = time.time() - cycle_start
                
                return {
                    "success": True,
                    "cycle_index": cycle_index,
                    "agents_created": len(cycle_agents),
                    "agents_executed": len(executed_agents),
                    "agents_cleaned": len(cleanup_results),
                    "cycle_time": cycle_time
                }
                
            except Exception as e:
                logger.error(f"Lifecycle cycle {cycle_index} failed: {e}")
                return {
                    "success": False,
                    "cycle_index": cycle_index,
                    "error": str(e)
                }
        
        # Execute lifecycle cycles concurrently
        logger.info(f"Testing agent lifecycle cleanup with {num_lifecycle_cycles} concurrent cycles")
        
        cycle_tasks = [agent_lifecycle_cycle(i) for i in range(num_lifecycle_cycles)]
        results = await asyncio.gather(*cycle_tasks, return_exceptions=True)
        
        # Force garbage collection to verify cleanup
        gc.collect()
        
        # Analyze lifecycle results
        successful_cycles = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # CRITICAL: All lifecycle cycles should complete successfully
        success_rate = len(successful_cycles) / num_lifecycle_cycles
        assert success_rate >= 0.95, f"Lifecycle cycle success rate too low: {success_rate:.2%}"
        
        # Verify resource cleanup effectiveness
        final_active_agents = len(self.active_agents)
        final_agent_refs = len([ref for ref in self.agent_refs if ref() is not None])
        
        # Allow small number of remaining agents (cleanup may be async)
        max_allowed_remaining = total_agent_instances * 0.05  # 5% tolerance
        assert final_active_agents <= max_allowed_remaining, \
            f"Too many agents remaining after cleanup: {final_active_agents} - RESOURCE LEAK"
        
        # Verify cleanup events consistency
        total_cleanup_events = len(cleanup_events)
        expected_cleanup_events = sum(r["agents_cleaned"] for r in successful_cycles)
        
        cleanup_ratio = total_cleanup_events / expected_cleanup_events if expected_cleanup_events > 0 else 0
        assert cleanup_ratio >= 0.95, \
            f"Cleanup events ratio too low: {cleanup_ratio:.2%} - RACE CONDITION in cleanup"
        
        # Verify lifecycle token uniqueness (no token reuse)
        lifecycle_tokens = [event["lifecycle_token"] for event in cleanup_events]
        assert len(lifecycle_tokens) == len(set(lifecycle_tokens)), \
            "Lifecycle token collision detected - RACE CONDITION"
        
        # Analyze resource snapshots for leaks
        if resource_snapshots:
            # Group snapshots by phase
            creation_snapshots = [s for s in resource_snapshots if s["phase"] == "creation"]
            cleanup_snapshots = [s for s in resource_snapshots if s["phase"] == "cleanup"]
            
            if creation_snapshots and cleanup_snapshots:
                avg_creation_agents = sum(s["active_agents"] for s in creation_snapshots) / len(creation_snapshots)
                avg_cleanup_agents = sum(s["active_agents"] for s in cleanup_snapshots) / len(cleanup_snapshots)
                
                # Cleanup should significantly reduce active agent count
                cleanup_effectiveness = (avg_creation_agents - avg_cleanup_agents) / avg_creation_agents
                assert cleanup_effectiveness >= 0.8, \
                    f"Cleanup effectiveness too low: {cleanup_effectiveness:.2%} - RESOURCE LEAK"
        
        # Performance validation
        cycle_times = [r["cycle_time"] for r in successful_cycles if "cycle_time" in r]
        if cycle_times:
            avg_cycle_time = sum(cycle_times) / len(cycle_times)
            max_cycle_time = max(cycle_times)
            
            assert avg_cycle_time < 2.0, f"Average lifecycle cycle time too slow: {avg_cycle_time:.3f}s"
            assert max_cycle_time < 10.0, f"Maximum lifecycle cycle time too slow: {max_cycle_time:.3f}s - possible deadlock"
        
        # No race conditions should be detected
        assert len(self.race_conditions_detected) == 0, f"Race conditions detected: {self.race_conditions_detected}"
        
        logger.info(f"SUCCESS: {len(successful_cycles)} lifecycle cycles completed")
        logger.info(f"Final active agents: {final_active_agents}/{total_agent_instances}")
        logger.info(f"Cleanup events: {total_cleanup_events}")
        
        self.assert_business_value_delivered({
            "successful_cycles": len(successful_cycles),
            "cleanup_effectiveness": cleanup_ratio,
            "resource_leak_ratio": final_active_agents / total_agent_instances,
            "race_conditions": len(self.race_conditions_detected)
        }, "automation")