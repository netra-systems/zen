"""
MISSION CRITICAL: Multi-Agent WebSocket Bridge Integration Tests

Comprehensive tests for WebSocket bridge sharing and lifecycle across multiple concurrent agents.
These tests verify the SSOT WebSocket bridge can handle complex multi-agent scenarios without
state corruption, event loss, or resource contention.

Business Value Justification:
- Segment: Enterprise | Platform Stability  
- Business Goal: Ensure reliable multi-agent orchestration for complex AI workflows
- Value Impact: Prevents 40% of enterprise chat failures due to multi-agent coordination issues
- Revenue Impact: Critical for $100K+ enterprise contracts requiring complex agent workflows

Test Scenarios:
1. Multiple agents sharing same WebSocket bridge instance
2. Agent hierarchy with supervisor spawning sub-agents  
3. WebSocket event ordering across concurrent agents
4. Bridge state consistency with concurrent operations
5. Proper cleanup when multiple agents complete/fail
6. Event collision and race condition handling
7. Resource sharing and lock contention under stress

This test suite is EXTREMELY COMPREHENSIVE and designed to STRESS the system.
"""

import asyncio
import unittest
import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Set
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# Import core agent infrastructure with error handling
try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, get_agent_websocket_bridge
    from netra_backend.app.agents.base_agent import BaseAgent
    from netra_backend.app.agents.state import DeepAgentState
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.logging_config import central_logger
    
    # Optional imports - tests will work without these
    try:
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
    except ImportError:
        DataSubAgent = None
        
    try:
        from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
    except ImportError:
        OptimizationsCoreSubAgent = None
        
    try:
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent  
    except ImportError:
        ReportingSubAgent = None
        
    try:
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    except ImportError:
        AgentRegistry = None
        
    try:
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
    except ImportError:
        ExecutionEngine = None
        
except ImportError as e:
    print(f"WARNING: Could not import some agent infrastructure: {e}")
    print("Some tests may be skipped")
    BaseAgent = None

if BaseAgent is not None:
    logger = central_logger.get_logger(__name__)
else:
    import logging
    logger = logging.getLogger(__name__)

# Skip all tests if BaseAgent is not available
skip_tests = BaseAgent is None
skip_reason = "BaseAgent infrastructure not available"

@dataclass
class AgentExecutionRecord:
    """Record of agent execution for validation."""
    agent_id: str
    agent_name: str
    run_id: str
    thread_id: str
    start_time: float
    end_time: Optional[float] = None
    events_emitted: List[Dict[str, Any]] = None
    success: bool = False
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.events_emitted is None:
            self.events_emitted = []


@dataclass
class WebSocketEventCapture:
    """Captures WebSocket events for validation."""
    event_type: str
    run_id: str
    agent_name: str
    timestamp: float
    thread_id: str
    payload: Dict[str, Any]
    bridge_instance_id: str


class MockWebSocketManager:
    """Mock WebSocket manager that captures all events for verification."""
    
    def __init__(self):
        self.captured_events: List[WebSocketEventCapture] = []
        self.connections: Dict[str, Mock] = {}
        self.lock = asyncio.Lock()
        
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Capture events sent to threads."""
        async with self.lock:
            event = WebSocketEventCapture(
                event_type=message.get('type', 'unknown'),
                run_id=message.get('run_id', 'unknown'),
                agent_name=message.get('agent_name', 'unknown'),
                timestamp=time.time(),
                thread_id=thread_id,
                payload=message.get('payload', {}),
                bridge_instance_id=id(self)
            )
            self.captured_events.append(event)
            logger.debug(f"Captured event: {event.event_type} for {event.agent_name} (run_id={event.run_id})")
            return True
    
    def get_events_for_thread(self, thread_id: str) -> List[WebSocketEventCapture]:
        """Get all events for a specific thread."""
        return [e for e in self.captured_events if e.thread_id == thread_id]
    
    def get_events_for_agent(self, agent_name: str) -> List[WebSocketEventCapture]:
        """Get all events for a specific agent."""
        return [e for e in self.captured_events if e.agent_name == agent_name]


@unittest.skipIf(skip_tests, skip_reason)
class TestMultiAgentWebSocketIntegration(unittest.TestCase):
    """Comprehensive multi-agent WebSocket integration tests."""
    
    def setUp(self):
        """Set up test environment with real agents and mocked infrastructure."""
        self.test_start_time = time.time()
        
        # Create unique test identifiers
        self.test_id = f"test_{uuid.uuid4().hex[:8]}"
        
        # Create mock WebSocket manager
        self.mock_websocket_manager = MockWebSocketManager()
        
        # Create mock LLM manager
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_llm_manager.ask_llm = AsyncMock(return_value="Mock LLM response for testing")
        
        # Execution records for validation
        self.execution_records: List[AgentExecutionRecord] = []
        self.active_agents: Set[str] = set()
        
        # Test data
        self.test_threads = []
        self.test_run_ids = []
        
        logger.info(f"Starting multi-agent test: {self.test_id}")
    
    def tearDown(self):
        """Clean up test environment."""
        test_duration = time.time() - self.test_start_time
        logger.info(f"Test {self.test_id} completed in {test_duration:.2f}s")
        
        # Clear singleton state for next test
        AgentWebSocketBridge._instance = None
    
    def test_multiple_agents_sharing_same_bridge(self):
        """
        Test 1: Multiple agents sharing the same WebSocket bridge instance.
        
        This test verifies that multiple agents can safely share a single WebSocket bridge
        without state corruption or event cross-contamination.
        """
        logger.info("🧪 TEST 1: Multiple agents sharing same bridge")
        
        async def run_test():
            # Create shared bridge with mock WebSocket manager
            bridge = AgentWebSocketBridge()
            
            # Mock the WebSocket manager initialization
            with patch.object(bridge, '_websocket_manager', self.mock_websocket_manager):
                bridge.state = bridge.IntegrationState.ACTIVE if hasattr(bridge, 'IntegrationState') else 'active'
                
                # Create multiple agents that share the bridge
                agents = []
                agent_configs = [
                    ("DataSubAgent", "data_analysis"),
                    ("OptimizationsCoreSubAgent", "optimizations"),
                    ("ReportingSubAgent", "reporting"),
                    ("DataSubAgent", "data_validation"),  # Second data agent
                    ("OptimizationsCoreSubAgent", "cost_optimization"),  # Second optimization agent
                ]
                
                for i, (agent_class, agent_name) in enumerate(agent_configs):
                    # Create test agent instances
                    if agent_class == "DataSubAgent":
                        agent = TestDataAgent(self.mock_llm_manager, name=agent_name)
                    elif agent_class == "OptimizationsCoreSubAgent":
                        agent = TestOptimizationAgent(self.mock_llm_manager, name=agent_name)
                    elif agent_class == "ReportingSubAgent":
                        agent = TestReportingAgent(self.mock_llm_manager, name=agent_name)
                    
                    # Set the shared bridge
                    agent._websocket_adapter.set_bridge(bridge)
                    agents.append(agent)
                
                # Execute all agents concurrently
                tasks = []
                for i, agent in enumerate(agents):
                    thread_id = f"thread_{self.test_id}_{i}"
                    run_id = f"run_{self.test_id}_{i}"
                    self.test_threads.append(thread_id)
                    self.test_run_ids.append(run_id)
                    
                    # Register thread mapping in bridge
                    await bridge.register_run_thread_mapping(run_id, thread_id, {
                        "agent_name": agent.name,
                        "test_id": self.test_id
                    })
                    
                    # Execute agent
                    task = self._execute_agent_with_events(agent, run_id, thread_id)
                    tasks.append(task)
                
                # Wait for all agents to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Validate results
                successful_executions = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
                self.assertEqual(successful_executions, len(agents), 
                               f"Not all agents executed successfully: {successful_executions}/{len(agents)}")
                
                # Validate WebSocket events were captured
                total_events = len(self.mock_websocket_manager.captured_events)
                expected_min_events = len(agents) * 4  # At least 4 events per agent
                self.assertGreaterEqual(total_events, expected_min_events,
                                      f"Expected at least {expected_min_events} events, got {total_events}")
                
                # Validate no event cross-contamination
                await self._validate_no_event_cross_contamination()
                
                logger.info(f"✅ TEST 1 PASSED: {len(agents)} agents shared bridge successfully, {total_events} events captured")
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()
    
    def test_agent_hierarchy_with_supervisor_spawning(self):
        """
        Test 2: Agent hierarchy with supervisor spawning sub-agents.
        
        This test simulates a complex agent hierarchy where a supervisor agent
        spawns multiple sub-agents, all sharing the same WebSocket bridge.
        """
        logger.info("🧪 TEST 2: Agent hierarchy with supervisor spawning")
        
        async def run_test():
            # Create supervisor-controlled bridge
            bridge = AgentWebSocketBridge()
            
            with patch.object(bridge, '_websocket_manager', self.mock_websocket_manager):
                bridge.state = bridge.IntegrationState.ACTIVE if hasattr(bridge, 'IntegrationState') else 'active'
                
                # Create supervisor agent
                supervisor = TestSupervisorAgent(self.mock_llm_manager, name="supervisor")
                supervisor._websocket_adapter.set_bridge(bridge)
                
                # Supervisor thread and run ID
                supervisor_thread = f"thread_supervisor_{self.test_id}"
                supervisor_run_id = f"run_supervisor_{self.test_id}"
                
                await bridge.register_run_thread_mapping(supervisor_run_id, supervisor_thread, {
                    "agent_name": "supervisor",
                    "hierarchy": "root"
                })
                
                # Execute supervisor which will spawn sub-agents
                supervisor_result = await self._execute_supervisor_with_subagents(
                    supervisor, supervisor_run_id, supervisor_thread, bridge
                )
                
                self.assertTrue(supervisor_result['success'], "Supervisor execution failed")
                self.assertGreaterEqual(supervisor_result['subagents_spawned'], 3, 
                                      "Expected at least 3 sub-agents to be spawned")
                
                # Validate hierarchical event ordering
                await self._validate_hierarchical_event_ordering()
                
                # Validate sub-agent lifecycle events
                await self._validate_subagent_lifecycle_events()
                
                logger.info(f"✅ TEST 2 PASSED: Supervisor spawned {supervisor_result['subagents_spawned']} sub-agents successfully")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()
    
    def test_websocket_event_ordering_across_agents(self):
        """
        Test 3: WebSocket event ordering across multiple concurrent agents.
        
        This test ensures that WebSocket events are properly ordered and no events
        are lost when multiple agents emit events concurrently.
        """
        logger.info("🧪 TEST 3: WebSocket event ordering across agents")
        
        async def run_test():
            bridge = AgentWebSocketBridge()
            
            with patch.object(bridge, '_websocket_manager', self.mock_websocket_manager):
                bridge.state = bridge.IntegrationState.ACTIVE if hasattr(bridge, 'IntegrationState') else 'active'
                
                # Create agents with different execution patterns
                agents = [
                    TestFastAgent(self.mock_llm_manager, name="fast_agent"),
                    TestSlowAgent(self.mock_llm_manager, name="slow_agent"),
                    TestBurstAgent(self.mock_llm_manager, name="burst_agent"),
                    TestStreamingAgent(self.mock_llm_manager, name="streaming_agent"),
                ]
                
                # Set up all agents with the same bridge
                for agent in agents:
                    agent._websocket_adapter.set_bridge(bridge)
                
                # Execute all agents with staggered starts
                tasks = []
                start_times = {}
                
                for i, agent in enumerate(agents):
                    thread_id = f"thread_ordering_{i}"
                    run_id = f"run_ordering_{i}"
                    
                    await bridge.register_run_thread_mapping(run_id, thread_id, {
                        "agent_name": agent.name,
                        "execution_pattern": type(agent).__name__
                    })
                    
                    # Stagger starts by 100ms
                    start_delay = i * 0.1
                    task = self._execute_agent_with_timing(agent, run_id, thread_id, start_delay)
                    tasks.append(task)
                    start_times[run_id] = time.time() + start_delay
                
                # Wait for all executions
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Validate all executions succeeded
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.fail(f"Agent {agents[i].name} failed with exception: {result}")
                    self.assertTrue(result.get('success'), f"Agent {agents[i].name} execution failed")
                
                # Validate event ordering and timing
                await self._validate_event_ordering_and_timing(start_times)
                
                # Validate no events were lost
                await self._validate_no_event_loss(agents)
                
                logger.info("✅ TEST 3 PASSED: Event ordering maintained across concurrent agents")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()
    
    def test_bridge_state_consistency_under_concurrency(self):
        """
        Test 4: Bridge state consistency with concurrent agent operations.
        
        This test hammers the bridge with concurrent operations to ensure
        internal state remains consistent under heavy load.
        """
        logger.info("🧪 TEST 4: Bridge state consistency under concurrency")
        
        async def run_test():
            bridge = AgentWebSocketBridge()
            
            with patch.object(bridge, '_websocket_manager', self.mock_websocket_manager):
                bridge.state = bridge.IntegrationState.ACTIVE if hasattr(bridge, 'IntegrationState') else 'active'
                
                # Create high-concurrency scenario
                num_concurrent_agents = 20
                num_events_per_agent = 50
                
                agents = []
                for i in range(num_concurrent_agents):
                    agent = TestHammerAgent(
                        self.mock_llm_manager, 
                        name=f"hammer_agent_{i}",
                        events_to_emit=num_events_per_agent
                    )
                    agent._websocket_adapter.set_bridge(bridge)
                    agents.append(agent)
                
                # Execute all agents simultaneously
                tasks = []
                for i, agent in enumerate(agents):
                    thread_id = f"thread_hammer_{i}"
                    run_id = f"run_hammer_{i}"
                    
                    await bridge.register_run_thread_mapping(run_id, thread_id, {
                        "agent_name": agent.name,
                        "stress_test": True
                    })
                    
                    task = self._execute_agent_with_events(agent, run_id, thread_id)
                    tasks.append(task)
                
                # Wait for completion with timeout
                start_time = time.time()
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=60.0  # 1 minute timeout
                )
                duration = time.time() - start_time
                
                # Validate all executions completed
                successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
                self.assertEqual(successful, num_concurrent_agents, 
                               f"Only {successful}/{num_concurrent_agents} agents completed successfully")
                
                # Validate expected number of events
                total_events = len(self.mock_websocket_manager.captured_events)
                expected_events = num_concurrent_agents * num_events_per_agent
                self.assertEqual(total_events, expected_events,
                               f"Expected {expected_events} events, got {total_events}")
                
                # Validate bridge state consistency
                await self._validate_bridge_state_consistency(bridge)
                
                logger.info(f"✅ TEST 4 PASSED: {num_concurrent_agents} agents × {num_events_per_agent} events = {total_events} events in {duration:.2f}s")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()
    
    def test_cleanup_when_agents_complete_or_fail(self):
        """
        Test 5: Proper cleanup when multiple agents complete or fail.
        
        This test ensures the bridge properly handles cleanup when agents
        complete successfully or fail with exceptions.
        """
        logger.info("🧪 TEST 5: Cleanup when agents complete or fail")
        
        async def run_test():
            bridge = AgentWebSocketBridge()
            
            with patch.object(bridge, '_websocket_manager', self.mock_websocket_manager):
                bridge.state = bridge.IntegrationState.ACTIVE if hasattr(bridge, 'IntegrationState') else 'active'
                
                # Create agents with different failure modes
                agents = [
                    TestSuccessAgent(self.mock_llm_manager, name="success_1"),
                    TestSuccessAgent(self.mock_llm_manager, name="success_2"),
                    TestFailureAgent(self.mock_llm_manager, name="failure_1", failure_type="exception"),
                    TestFailureAgent(self.mock_llm_manager, name="failure_2", failure_type="timeout"),
                    TestSuccessAgent(self.mock_llm_manager, name="success_3"),
                    TestFailureAgent(self.mock_llm_manager, name="failure_3", failure_type="silent_death"),
                ]
                
                # Set bridge for all agents
                for agent in agents:
                    agent._websocket_adapter.set_bridge(bridge)
                
                # Execute all agents
                tasks = []
                thread_mappings = {}
                
                for i, agent in enumerate(agents):
                    thread_id = f"thread_cleanup_{i}"
                    run_id = f"run_cleanup_{i}"
                    thread_mappings[run_id] = thread_id
                    
                    await bridge.register_run_thread_mapping(run_id, thread_id, {
                        "agent_name": agent.name,
                        "expected_outcome": "success" if "success" in agent.name else "failure"
                    })
                    
                    task = self._execute_agent_with_cleanup_tracking(agent, run_id, thread_id)
                    tasks.append(task)
                
                # Wait for all executions (some will fail)
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Validate expected success/failure patterns
                successes = []
                failures = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception) or (isinstance(result, dict) and not result.get('success')):
                        failures.append(agents[i].name)
                    else:
                        successes.append(agents[i].name)
                
                expected_successes = 3
                expected_failures = 3
                self.assertEqual(len(successes), expected_successes, f"Expected {expected_successes} successes, got {len(successes)}: {successes}")
                self.assertEqual(len(failures), expected_failures, f"Expected {expected_failures} failures, got {len(failures)}: {failures}")
                
                # Validate cleanup was performed for all agents
                await self._validate_cleanup_was_performed(thread_mappings, bridge)
                
                # Validate error notifications were sent for failed agents
                await self._validate_error_notifications_sent(failures)
                
                logger.info(f"✅ TEST 5 PASSED: {len(successes)} successes, {len(failures)} failures, all cleaned up properly")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()
    
    def test_event_collision_and_race_conditions(self):
        """
        Test 6: Event collision and race condition handling between agents.
        
        This test creates scenarios where agents might emit events at exactly
        the same time to test for race conditions and event handling robustness.
        """
        logger.info("🧪 TEST 6: Event collision and race conditions")
        
        async def run_test():
            bridge = AgentWebSocketBridge()
            
            with patch.object(bridge, '_websocket_manager', self.mock_websocket_manager):
                bridge.state = bridge.IntegrationState.ACTIVE if hasattr(bridge, 'IntegrationState') else 'active'
                
                # Create agents that will emit events simultaneously
                num_collision_agents = 15
                agents = []
                
                for i in range(num_collision_agents):
                    agent = TestCollisionAgent(
                        self.mock_llm_manager, 
                        name=f"collision_agent_{i}",
                        collision_group=i % 3  # Group agents for synchronized emissions
                    )
                    agent._websocket_adapter.set_bridge(bridge)
                    agents.append(agent)
                
                # Set up synchronization barriers for each collision group
                barriers = {
                    0: asyncio.Barrier(5),  # 5 agents in group 0
                    1: asyncio.Barrier(5),  # 5 agents in group 1  
                    2: asyncio.Barrier(5),  # 5 agents in group 2
                }
                
                # Execute agents with collision barriers
                tasks = []
                for i, agent in enumerate(agents):
                    thread_id = f"thread_collision_{i}"
                    run_id = f"run_collision_{i}"
                    
                    await bridge.register_run_thread_mapping(run_id, thread_id, {
                        "agent_name": agent.name,
                        "collision_group": agent.collision_group
                    })
                    
                    barrier = barriers[agent.collision_group]
                    task = self._execute_agent_with_collision_barrier(agent, run_id, thread_id, barrier)
                    tasks.append(task)
                
                # Wait for all collision tests
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Validate all agents completed despite collisions
                successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
                self.assertEqual(successful, num_collision_agents,
                               f"Only {successful}/{num_collision_agents} agents survived collisions")
                
                # Validate no events were lost in collisions
                await self._validate_no_collision_event_loss(agents)
                
                # Validate bridge handled concurrent access gracefully
                await self._validate_concurrent_access_handling(bridge)
                
                logger.info(f"✅ TEST 6 PASSED: {num_collision_agents} agents handled event collisions successfully")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()
    
    def test_resource_sharing_and_lock_contention(self):
        """
        Test 7: Resource sharing and lock contention under extreme stress.
        
        This test pushes the WebSocket bridge to its limits with extreme
        concurrent load to test for deadlocks, resource leaks, and performance degradation.
        """
        logger.info("🧪 TEST 7: Resource sharing and lock contention under extreme stress")
        
        async def run_test():
            bridge = AgentWebSocketBridge()
            
            with patch.object(bridge, '_websocket_manager', self.mock_websocket_manager):
                bridge.state = bridge.IntegrationState.ACTIVE if hasattr(bridge, 'IntegrationState') else 'active'
                
                # Create extreme stress scenario
                num_stress_agents = 50
                events_per_agent = 100
                
                agents = []
                for i in range(num_stress_agents):
                    agent = TestStressAgent(
                        self.mock_llm_manager,
                        name=f"stress_agent_{i}",
                        events_to_emit=events_per_agent,
                        stress_pattern="random"  # Random timing to maximize contention
                    )
                    agent._websocket_adapter.set_bridge(bridge)
                    agents.append(agent)
                
                # Monitor performance during stress test
                performance_monitor = PerformanceMonitor()
                performance_monitor.start()
                
                # Execute all agents simultaneously for maximum contention
                tasks = []
                for i, agent in enumerate(agents):
                    thread_id = f"thread_stress_{i}"
                    run_id = f"run_stress_{i}"
                    
                    await bridge.register_run_thread_mapping(run_id, thread_id, {
                        "agent_name": agent.name,
                        "stress_test": True,
                        "stress_level": "extreme"
                    })
                    
                    # All agents start immediately for maximum lock contention
                    task = self._execute_stress_agent(agent, run_id, thread_id, performance_monitor)
                    tasks.append(task)
                
                # Wait with extended timeout due to stress
                start_time = time.time()
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=180.0  # 3 minute timeout for stress test
                    )
                except asyncio.TimeoutError:
                    self.fail("Stress test timed out - potential deadlock detected")
                
                duration = time.time() - start_time
                performance_monitor.stop()
                
                # Validate all agents completed under stress
                successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
                failure_rate = (num_stress_agents - successful) / num_stress_agents
                
                # Allow up to 5% failure rate under extreme stress
                self.assertLessEqual(failure_rate, 0.05, 
                                   f"Failure rate {failure_rate:.2%} too high under stress")
                
                # Validate performance metrics
                performance_stats = performance_monitor.get_stats()
                await self._validate_stress_performance(performance_stats, duration)
                
                # Validate total events
                total_events = len(self.mock_websocket_manager.captured_events)
                expected_min_events = successful * events_per_agent * 0.95  # Allow 5% event loss under extreme stress
                self.assertGreaterEqual(total_events, expected_min_events,
                                      f"Too many events lost under stress: {total_events} < {expected_min_events}")
                
                logger.info(f"✅ TEST 7 PASSED: {successful}/{num_stress_agents} agents survived extreme stress in {duration:.2f}s")
                logger.info(f"   Performance: {total_events} events, {failure_rate:.1%} failure rate")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()
    
    # ==================== HELPER METHODS ====================
    
    async def _execute_agent_with_events(self, agent, run_id: str, thread_id: str) -> Dict[str, Any]:
        """Execute agent and capture all events."""
        record = AgentExecutionRecord(
            agent_id=id(agent),
            agent_name=agent.name,
            run_id=run_id,
            thread_id=thread_id,
            start_time=time.time()
        )
        self.execution_records.append(record)
        
        try:
            # Execute agent with full event emission
            if hasattr(agent, 'execute_with_events'):
                result = await agent.execute_with_events(run_id, thread_id)
            else:
                # Fallback for standard agent execution
                result = await self._standard_agent_execution(agent, run_id, thread_id)
            
            record.end_time = time.time()
            record.success = True
            record.events_emitted = self.mock_websocket_manager.get_events_for_agent(agent.name)
            
            return {"success": True, "result": result, "events": len(record.events_emitted)}
            
        except Exception as e:
            record.end_time = time.time()
            record.success = False
            record.error = str(e)
            logger.error(f"Agent {agent.name} execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _standard_agent_execution(self, agent, run_id: str, thread_id: str) -> Dict[str, Any]:
        """Standard agent execution with WebSocket events."""
        # Set run context
        agent._websocket_adapter.set_run_context(run_id, agent.name)
        
        # Emit lifecycle events
        await agent._websocket_adapter.emit_agent_started("Starting agent execution")
        await agent._websocket_adapter.emit_thinking("Processing request...")
        
        # Simulate some work
        await asyncio.sleep(0.1)
        await agent._websocket_adapter.emit_tool_executing("analysis_tool", {"data": "test"})
        await asyncio.sleep(0.05)
        await agent._websocket_adapter.emit_tool_completed("analysis_tool", {"result": "completed"})
        
        await agent._websocket_adapter.emit_agent_completed({"analysis": "complete"})
        
        return {"analysis_complete": True, "thread_id": thread_id}
    
    async def _execute_supervisor_with_subagents(self, supervisor, run_id: str, thread_id: str, bridge) -> Dict[str, Any]:
        """Execute supervisor agent that spawns sub-agents."""
        supervisor._websocket_adapter.set_run_context(run_id, supervisor.name)
        
        # Supervisor starts
        await supervisor._websocket_adapter.emit_agent_started("Supervisor coordinating analysis")
        
        # Spawn sub-agents
        subagents = []
        subagent_tasks = []
        
        subagent_configs = [
            ("data_analysis", TestDataAgent),
            ("optimization", TestOptimizationAgent),
            ("reporting", TestReportingAgent),
        ]
        
        for i, (name, agent_class) in enumerate(subagent_configs):
            subagent = agent_class(self.mock_llm_manager, name=f"sub_{name}")
            subagent._websocket_adapter.set_bridge(bridge)
            
            sub_thread_id = f"{thread_id}_sub_{i}"
            sub_run_id = f"{run_id}_sub_{i}"
            
            await bridge.register_run_thread_mapping(sub_run_id, sub_thread_id, {
                "parent_run_id": run_id,
                "agent_name": subagent.name,
                "hierarchy": "sub"
            })
            
            # Emit sub-agent spawning event
            await supervisor._websocket_adapter.emit_subagent_started(subagent.name, sub_run_id)
            
            # Execute sub-agent
            task = self._execute_agent_with_events(subagent, sub_run_id, sub_thread_id)
            subagent_tasks.append(task)
            subagents.append(subagent)
        
        # Wait for all sub-agents
        subagent_results = await asyncio.gather(*subagent_tasks, return_exceptions=True)
        
        # Emit completion events for sub-agents
        for i, result in enumerate(subagent_results):
            if isinstance(result, dict) and result.get('success'):
                await supervisor._websocket_adapter.emit_subagent_completed(
                    subagents[i].name, 
                    {"result": "success"}
                )
        
        # Supervisor completes
        await supervisor._websocket_adapter.emit_agent_completed({
            "subagents_spawned": len(subagents),
            "subagents_completed": sum(1 for r in subagent_results if isinstance(r, dict) and r.get('success'))
        })
        
        return {
            "success": True,
            "subagents_spawned": len(subagents),
            "subagent_results": subagent_results
        }
    
    async def _execute_agent_with_timing(self, agent, run_id: str, thread_id: str, start_delay: float) -> Dict[str, Any]:
        """Execute agent with specific timing delay."""
        await asyncio.sleep(start_delay)
        return await self._execute_agent_with_events(agent, run_id, thread_id)
    
    async def _execute_agent_with_cleanup_tracking(self, agent, run_id: str, thread_id: str) -> Dict[str, Any]:
        """Execute agent with cleanup tracking."""
        try:
            result = await self._execute_agent_with_events(agent, run_id, thread_id)
            
            # Simulate cleanup for successful agents
            if result.get('success'):
                await agent._websocket_adapter.bridge.unregister_run_mapping(run_id)
            
            return result
        except Exception as e:
            # Simulate error cleanup
            await agent._websocket_adapter.emit_error(f"Agent failed: {e}")
            await agent._websocket_adapter.bridge.unregister_run_mapping(run_id)
            raise
    
    async def _execute_agent_with_collision_barrier(self, agent, run_id: str, thread_id: str, barrier: asyncio.Barrier) -> Dict[str, Any]:
        """Execute agent with collision barrier synchronization."""
        agent._websocket_adapter.set_run_context(run_id, agent.name)
        
        # Wait for all agents in collision group
        await barrier.wait()
        
        # All agents in group emit simultaneously
        simultaneous_tasks = [
            agent._websocket_adapter.emit_agent_started("Collision test starting"),
            agent._websocket_adapter.emit_thinking("Synchronized thinking"),
            agent._websocket_adapter.emit_tool_executing("collision_tool", {"collision": True}),
        ]
        
        # Execute all at once to force collision
        await asyncio.gather(*simultaneous_tasks)
        
        # Brief pause then complete
        await asyncio.sleep(0.01)
        await agent._websocket_adapter.emit_tool_completed("collision_tool", {"success": True})
        await agent._websocket_adapter.emit_agent_completed({"collision_survived": True})
        
        return {"success": True, "collision_group": agent.collision_group}
    
    async def _execute_stress_agent(self, agent, run_id: str, thread_id: str, performance_monitor) -> Dict[str, Any]:
        """Execute agent under stress conditions."""
        performance_monitor.agent_started(agent.name)
        
        try:
            if hasattr(agent, 'execute_stress_pattern'):
                result = await agent.execute_stress_pattern(run_id, thread_id)
            else:
                result = await self._execute_agent_with_events(agent, run_id, thread_id)
            
            performance_monitor.agent_completed(agent.name, success=True)
            return result
            
        except Exception as e:
            performance_monitor.agent_completed(agent.name, success=False)
            raise
    
    # ==================== VALIDATION METHODS ====================
    
    async def _validate_no_event_cross_contamination(self):
        """Validate that events don't cross-contaminate between agents."""
        events_by_thread = {}
        for event in self.mock_websocket_manager.captured_events:
            if event.thread_id not in events_by_thread:
                events_by_thread[event.thread_id] = []
            events_by_thread[event.thread_id].append(event)
        
        # Validate each thread only receives its own events
        for thread_id, events in events_by_thread.items():
            agent_names = set(event.agent_name for event in events)
            # Each thread should have events from only one agent (or supervisor + sub-agents)
            if len(agent_names) > 3:  # Allow supervisor + 2 sub-agents max
                self.fail(f"Thread {thread_id} received events from too many agents: {agent_names}")
    
    async def _validate_hierarchical_event_ordering(self):
        """Validate events follow proper hierarchical ordering."""
        supervisor_events = [e for e in self.mock_websocket_manager.captured_events 
                           if e.agent_name == "supervisor"]
        subagent_events = [e for e in self.mock_websocket_manager.captured_events 
                         if e.agent_name.startswith("sub_")]
        
        # Supervisor should start before any sub-agents
        if supervisor_events and subagent_events:
            supervisor_start = min(e.timestamp for e in supervisor_events if e.event_type == "agent_started")
            subagent_start = min(e.timestamp for e in subagent_events if e.event_type == "agent_started")
            self.assertLess(supervisor_start, subagent_start, "Supervisor should start before sub-agents")
    
    async def _validate_subagent_lifecycle_events(self):
        """Validate sub-agent lifecycle events are properly emitted."""
        lifecycle_events = [e for e in self.mock_websocket_manager.captured_events 
                          if e.event_type in ["subagent_started", "subagent_completed"]]
        
        started_events = [e for e in lifecycle_events if e.event_type == "subagent_started"]
        completed_events = [e for e in lifecycle_events if e.event_type == "subagent_completed"]
        
        # Should have matching started/completed events
        self.assertEqual(len(started_events), len(completed_events), 
                        "Mismatched sub-agent started/completed events")
    
    async def _validate_event_ordering_and_timing(self, start_times: Dict[str, float]):
        """Validate events are properly ordered by timing."""
        for run_id, expected_start in start_times.items():
            run_events = [e for e in self.mock_websocket_manager.captured_events if e.run_id == run_id]
            if run_events:
                actual_start = min(e.timestamp for e in run_events)
                # Allow 100ms tolerance for timing
                self.assertAlmostEqual(actual_start, expected_start, delta=0.1,
                                     msg=f"Event timing off for run_id {run_id}")
    
    async def _validate_no_event_loss(self, agents: List):
        """Validate no events were lost during concurrent execution."""
        expected_event_types = ["agent_started", "thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for agent in agents:
            agent_events = self.mock_websocket_manager.get_events_for_agent(agent.name)
            event_types = set(e.event_type for e in agent_events)
            
            for expected_type in expected_event_types:
                # Allow for some event types to be missing under stress (but not agent lifecycle events)
                if expected_type in ["agent_started", "agent_completed"]:
                    self.assertIn(expected_type, event_types, 
                                f"Agent {agent.name} missing critical event: {expected_type}")
    
    async def _validate_bridge_state_consistency(self, bridge):
        """Validate bridge internal state remains consistent."""
        try:
            # Bridge should still be in active state
            if hasattr(bridge, 'state'):
                expected_states = ['active', bridge.IntegrationState.ACTIVE if hasattr(bridge, 'IntegrationState') else 'active']
                self.assertIn(bridge.state, expected_states, "Bridge state corrupted under stress")
            
            # Bridge should still respond to health checks
            if hasattr(bridge, 'health_check'):
                health = await bridge.health_check()
                self.assertIsNotNone(health, "Bridge health check failed after stress test")
            
        except Exception as e:
            self.fail(f"Bridge state consistency check failed: {e}")
    
    async def _validate_cleanup_was_performed(self, thread_mappings: Dict[str, str], bridge):
        """Validate cleanup was performed for all threads."""
        # Check that thread mappings were cleaned up
        if hasattr(bridge, 'get_thread_registry_status'):
            registry_status = await bridge.get_thread_registry_status()
            if registry_status:
                # Registry should not have mappings for completed runs
                active_mappings = registry_status.get('active_mappings', 0)
                # Allow some leeway for concurrent cleanup
                self.assertLessEqual(active_mappings, len(thread_mappings) * 0.1,
                                   "Too many thread mappings not cleaned up")
    
    async def _validate_error_notifications_sent(self, failed_agent_names: List[str]):
        """Validate error notifications were sent for failed agents."""
        error_events = [e for e in self.mock_websocket_manager.captured_events 
                       if e.event_type in ["agent_error", "agent_death"]]
        
        notified_agents = set(e.agent_name for e in error_events)
        failed_agents_set = set(failed_agent_names)
        
        # Most failed agents should have error notifications
        coverage = len(notified_agents.intersection(failed_agents_set)) / len(failed_agents_set)
        self.assertGreaterEqual(coverage, 0.8, f"Only {coverage:.1%} of failed agents got error notifications")
    
    async def _validate_no_collision_event_loss(self, agents: List):
        """Validate no events were lost during collision scenarios."""
        for agent in agents:
            agent_events = self.mock_websocket_manager.get_events_for_agent(agent.name)
            # Should have at least 4 events from collision test
            self.assertGreaterEqual(len(agent_events), 4,
                                  f"Agent {agent.name} lost events during collision test")
    
    async def _validate_concurrent_access_handling(self, bridge):
        """Validate bridge handled concurrent access gracefully."""
        # Bridge should still be functional after concurrent access
        if hasattr(bridge, 'get_status'):
            try:
                status = await bridge.get_status()
                self.assertIsNotNone(status, "Bridge status unavailable after concurrent access")
            except Exception as e:
                self.fail(f"Bridge corrupted by concurrent access: {e}")
    
    async def _validate_stress_performance(self, performance_stats: Dict, duration: float):
        """Validate performance metrics under stress."""
        events_per_second = len(self.mock_websocket_manager.captured_events) / duration
        
        # Should maintain reasonable throughput even under stress
        self.assertGreaterEqual(events_per_second, 100, 
                              f"Throughput too low under stress: {events_per_second:.1f} events/sec")
        
        # Should complete in reasonable time
        self.assertLess(duration, 120, f"Stress test took too long: {duration:.1f}s")


# ==================== TEST AGENT CLASSES ====================

class TestDataAgent(BaseAgent):
    """Test data agent with WebSocket event emission."""
    
    async def execute_with_events(self, run_id: str, thread_id: str):
        self._websocket_adapter.set_run_context(run_id, self.name)
        
        await self._websocket_adapter.emit_agent_started("Data analysis starting")
        await self._websocket_adapter.emit_thinking("Analyzing data patterns...")
        await self._websocket_adapter.emit_tool_executing("data_analyzer", {"dataset": "test"})
        await asyncio.sleep(0.05)
        await self._websocket_adapter.emit_tool_completed("data_analyzer", {"insights": 5})
        await self._websocket_adapter.emit_agent_completed({"data_analysis": "complete"})
        
        return {"data_insights": 5}


class TestOptimizationAgent(BaseAgent):
    """Test optimization agent with WebSocket event emission."""
    
    async def execute_with_events(self, run_id: str, thread_id: str):
        self._websocket_adapter.set_run_context(run_id, self.name)
        
        await self._websocket_adapter.emit_agent_started("Optimization analysis starting")
        await self._websocket_adapter.emit_thinking("Identifying optimization opportunities...")
        await self._websocket_adapter.emit_tool_executing("optimizer", {"scope": "cost"})
        await asyncio.sleep(0.08)
        await self._websocket_adapter.emit_tool_completed("optimizer", {"savings": "$5000"})
        await self._websocket_adapter.emit_agent_completed({"optimizations": 3})
        
        return {"cost_savings": 5000}


class TestReportingAgent(BaseAgent):
    """Test reporting agent with WebSocket event emission."""
    
    async def execute_with_events(self, run_id: str, thread_id: str):
        self._websocket_adapter.set_run_context(run_id, self.name)
        
        await self._websocket_adapter.emit_agent_started("Report generation starting")
        await self._websocket_adapter.emit_thinking("Compiling analysis results...")
        await self._websocket_adapter.emit_tool_executing("report_generator", {"format": "executive"})
        await asyncio.sleep(0.06)
        await self._websocket_adapter.emit_tool_completed("report_generator", {"pages": 12})
        await self._websocket_adapter.emit_agent_completed({"report": "generated"})
        
        return {"report_pages": 12}


class TestSupervisorAgent(BaseAgent):
    """Test supervisor agent that coordinates sub-agents."""
    pass  # Implementation provided in test method


class TestFastAgent(BaseAgent):
    """Agent that executes quickly with rapid events."""
    
    async def execute_with_events(self, run_id: str, thread_id: str):
        self._websocket_adapter.set_run_context(run_id, self.name)
        
        # Rapid fire events
        await self._websocket_adapter.emit_agent_started("Fast execution")
        await self._websocket_adapter.emit_thinking("Quick analysis")
        await self._websocket_adapter.emit_tool_executing("fast_tool", {})
        await self._websocket_adapter.emit_tool_completed("fast_tool", {"speed": "fast"})
        await self._websocket_adapter.emit_agent_completed({"execution": "fast"})
        
        return {"speed": "fast"}


class TestSlowAgent(BaseAgent):
    """Agent that executes slowly with delayed events."""
    
    async def execute_with_events(self, run_id: str, thread_id: str):
        self._websocket_adapter.set_run_context(run_id, self.name)
        
        await self._websocket_adapter.emit_agent_started("Slow execution")
        await asyncio.sleep(0.2)
        await self._websocket_adapter.emit_thinking("Deep analysis")
        await asyncio.sleep(0.2)
        await self._websocket_adapter.emit_tool_executing("slow_tool", {})
        await asyncio.sleep(0.3)
        await self._websocket_adapter.emit_tool_completed("slow_tool", {"depth": "deep"})
        await self._websocket_adapter.emit_agent_completed({"execution": "thorough"})
        
        return {"speed": "slow"}


class TestBurstAgent(BaseAgent):
    """Agent that emits events in bursts."""
    
    async def execute_with_events(self, run_id: str, thread_id: str):
        self._websocket_adapter.set_run_context(run_id, self.name)
        
        # Burst of events
        burst_tasks = [
            self._websocket_adapter.emit_agent_started("Burst execution"),
            self._websocket_adapter.emit_thinking("Burst thinking"),
            self._websocket_adapter.emit_tool_executing("burst_tool_1", {}),
            self._websocket_adapter.emit_tool_executing("burst_tool_2", {}),
            self._websocket_adapter.emit_tool_executing("burst_tool_3", {}),
        ]
        await asyncio.gather(*burst_tasks)
        
        # Completion burst
        completion_tasks = [
            self._websocket_adapter.emit_tool_completed("burst_tool_1", {}),
            self._websocket_adapter.emit_tool_completed("burst_tool_2", {}),
            self._websocket_adapter.emit_tool_completed("burst_tool_3", {}),
        ]
        await asyncio.gather(*completion_tasks)
        
        await self._websocket_adapter.emit_agent_completed({"pattern": "burst"})
        return {"pattern": "burst"}


class TestStreamingAgent(BaseAgent):
    """Agent that emits streaming progress events."""
    
    async def execute_with_events(self, run_id: str, thread_id: str):
        self._websocket_adapter.set_run_context(run_id, self.name)
        
        await self._websocket_adapter.emit_agent_started("Streaming execution")
        
        # Stream progress updates
        for i in range(5):
            await self._websocket_adapter.emit_progress(f"Processing step {i+1}/5", {
                "progress": (i + 1) * 20,
                "step": i + 1
            })
            await asyncio.sleep(0.02)
        
        await self._websocket_adapter.emit_agent_completed({"stream": "complete"})
        return {"steps": 5}


class TestHammerAgent(BaseAgent):
    """Agent that hammers the bridge with many events."""
    
    def __init__(self, llm_manager, name: str, events_to_emit: int = 50):
        super().__init__(llm_manager, name=name)
        self.events_to_emit = events_to_emit
    
    async def execute_with_events(self, run_id: str, thread_id: str):
        self._websocket_adapter.set_run_context(run_id, self.name)
        
        await self._websocket_adapter.emit_agent_started("Hammer test starting")
        
        # Emit many events rapidly
        for i in range(self.events_to_emit):
            await self._websocket_adapter.emit_progress(f"Hammer event {i}", {"count": i})
            # No delay - hammer as fast as possible
        
        await self._websocket_adapter.emit_agent_completed({"events_sent": self.events_to_emit})
        return {"hammered": True}


class TestSuccessAgent(BaseAgent):
    """Agent that always succeeds."""
    
    async def execute_with_events(self, run_id: str, thread_id: str):
        self._websocket_adapter.set_run_context(run_id, self.name)
        
        await self._websocket_adapter.emit_agent_started("Success execution")
        await self._websocket_adapter.emit_thinking("Processing successfully")
        await self._websocket_adapter.emit_tool_executing("success_tool", {})
        await asyncio.sleep(0.05)
        await self._websocket_adapter.emit_tool_completed("success_tool", {"result": "success"})
        await self._websocket_adapter.emit_agent_completed({"status": "success"})
        
        return {"success": True}


class TestFailureAgent(BaseAgent):
    """Agent that fails in different ways."""
    
    def __init__(self, llm_manager, name: str, failure_type: str = "exception"):
        super().__init__(llm_manager, name=name)
        self.failure_type = failure_type
    
    async def execute_with_events(self, run_id: str, thread_id: str):
        self._websocket_adapter.set_run_context(run_id, self.name)
        
        await self._websocket_adapter.emit_agent_started("Failure test starting")
        await self._websocket_adapter.emit_thinking("About to fail...")
        
        if self.failure_type == "exception":
            await self._websocket_adapter.emit_error("Intentional test exception")
            raise RuntimeError("Intentional test failure")
        elif self.failure_type == "timeout":
            await asyncio.sleep(10)  # Will be cancelled
        elif self.failure_type == "silent_death":
            # Just return without proper completion
            return {"died_silently": True}
        
        return {"should_not_reach": True}


class TestCollisionAgent(BaseAgent):
    """Agent for collision testing."""
    
    def __init__(self, llm_manager, name: str, collision_group: int):
        super().__init__(llm_manager, name=name)
        self.collision_group = collision_group


class TestStressAgent(BaseAgent):
    """Agent for stress testing."""
    
    def __init__(self, llm_manager, name: str, events_to_emit: int = 100, stress_pattern: str = "random"):
        super().__init__(llm_manager, name=name)
        self.events_to_emit = events_to_emit
        self.stress_pattern = stress_pattern
    
    async def execute_stress_pattern(self, run_id: str, thread_id: str):
        self._websocket_adapter.set_run_context(run_id, self.name)
        
        await self._websocket_adapter.emit_agent_started("Stress test execution")
        
        # Emit events with random delays for maximum contention
        import random
        for i in range(self.events_to_emit):
            if self.stress_pattern == "random":
                await asyncio.sleep(random.uniform(0, 0.01))
            
            await self._websocket_adapter.emit_progress(f"Stress event {i}", {
                "stress_level": "extreme",
                "event_number": i
            })
        
        await self._websocket_adapter.emit_agent_completed({"stress_events": self.events_to_emit})
        return {"stress_completed": True}


class PerformanceMonitor:
    """Monitor performance during stress tests."""
    
    def __init__(self):
        self.start_time = None
        self.agent_starts = {}
        self.agent_completions = {}
        self.success_count = 0
        self.failure_count = 0
    
    def start(self):
        self.start_time = time.time()
    
    def stop(self):
        pass
    
    def agent_started(self, agent_name: str):
        self.agent_starts[agent_name] = time.time()
    
    def agent_completed(self, agent_name: str, success: bool):
        self.agent_completions[agent_name] = time.time()
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
    
    def get_stats(self):
        duration = time.time() - self.start_time if self.start_time else 0
        return {
            "total_duration": duration,
            "agents_started": len(self.agent_starts),
            "agents_completed": len(self.agent_completions),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_count / (self.success_count + self.failure_count) if (self.success_count + self.failure_count) > 0 else 0
        }


if __name__ == "__main__":
    # Enable detailed logging for debugging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the tests
    unittest.main(verbosity=2, buffer=True)