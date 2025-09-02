from shared.isolated_environment import get_env
#!/usr/bin/env python
"""MISSION CRITICAL: WebSocket Bridge Edge Cases and Failure Scenarios 20250902

CRITICAL BUSINESS CONTEXT:
- These tests target the MOST DIFFICULT WebSocket bridge failure scenarios
- Edge cases that could cause silent failures destroying user trust
- Race conditions that could break real-time chat value delivery
- Memory leaks that could crash production systems
- Any failure here means users lose connection to AI processing

COMPREHENSIVE EDGE CASE TESTING SCOPE:
1. Race conditions in WebSocket bridge initialization during concurrent access
2. Multiple concurrent agent executions sharing a bridge with resource contention
3. Bridge cleanup and resource management after agent failures/exceptions
4. Memory leaks in long-running agent sessions with continuous WebSocket events
5. WebSocket reconnection scenarios with state corruption and recovery
6. Invalid/null bridge handling with graceful degradation
7. Bridge state corruption scenarios under high load and interruption
8. Timeout and resource exhaustion cases with proper error boundaries
9. Thread safety violations in bridge singleton pattern
10. Event ordering corruption under concurrent load
11. Bridge persistence across agent restarts and crashes
12. Network partition scenarios affecting WebSocket delivery
13. Malicious input handling and security edge cases
14. Bridge lifecycle during Docker container restart scenarios

THESE TESTS MUST BE EXTREMELY DIFFICULT AND UNFORGIVING.
No mercy for edge cases that could destroy user experience.
"""

import asyncio
import gc
import json
import os
import sys
import time
import uuid
import threading
import websockets
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple, Union, Callable
from unittest.mock import AsyncMock, MagicMock, patch, Mock, call
from dataclasses import dataclass, field
import random
import signal
import psutil
# import memory_profiler  # Optional - not available in all environments

# CRITICAL: Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

# Set up test environment
os.environ['TEST_ENV'] = 'true'
os.environ['WEBSOCKET_BRIDGE_EDGE_CASE_TEST'] = 'true'

# Import core components
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState
from netra_backend.app.core.agent_heartbeat import AgentHeartbeat
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.llm.llm_manager import LLMManager


@dataclass
class StressTestMetrics:
    """Metrics for stress testing WebSocket bridge."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    concurrent_peak: int = 0
    memory_usage_start_mb: float = 0.0
    memory_usage_peak_mb: float = 0.0
    memory_usage_end_mb: float = 0.0
    average_response_time_ms: float = 0.0
    error_types: Dict[str, int] = field(default_factory=dict)
    race_condition_detections: int = 0
    resource_leak_detections: int = 0
    corruption_detections: int = 0


@dataclass
class ConcurrencyTestResult:
    """Result of concurrency stress test."""
    success: bool
    metrics: StressTestMetrics
    failures: List[str]
    race_conditions: List[str]
    resource_issues: List[str]


class MaliciousAgent(BaseAgent):
    """Agent designed to cause problems for testing edge cases."""
    
    def __init__(self, attack_type: str = "memory_bomb", name: str = "MaliciousAgent"):
        super().__init__(name=name, description=f"Malicious agent: {attack_type}")
        self.attack_type = attack_type
        self.websocket_bridge_set = False
        self.websocket_bridge_instance = None
        self.run_id_received = None
        self.execution_calls = []
        
    def set_websocket_bridge(self, bridge, run_id: str) -> None:
        """Override to track bridge setting."""
        super().set_websocket_bridge(bridge, run_id)
        self.websocket_bridge_set = True
        self.websocket_bridge_instance = bridge
        self.run_id_received = run_id
        
    async def execute(self, state: DeepAgentState, run_id: str, stream: bool = False) -> Dict[str, Any]:
        """Execute malicious behavior based on attack type."""
        execution_start = time.time()
        
        self.execution_calls.append({
            'state': state,
            'run_id': run_id,
            'stream': stream,
            'timestamp': datetime.now()
        })
        
        if not self.websocket_bridge_set:
            raise RuntimeError(f"CRITICAL: WebSocket bridge not set on agent {self.name}")
        
        if self.attack_type == "memory_bomb":
            await self._memory_bomb_attack()
        elif self.attack_type == "event_spam":
            await self._event_spam_attack()
        elif self.attack_type == "bridge_corruption":
            await self._bridge_corruption_attack()
        elif self.attack_type == "infinite_loop":
            await self._infinite_loop_attack()
        elif self.attack_type == "race_condition":
            await self._race_condition_attack()
        elif self.attack_type == "resource_exhaustion":
            await self._resource_exhaustion_attack()
        elif self.attack_type == "state_corruption":
            await self._state_corruption_attack()
        elif self.attack_type == "deadlock":
            await self._deadlock_attack()
        
        execution_time = time.time() - execution_start
        return {
            "success": True,
            "agent_name": self.name,
            "attack_type": self.attack_type,
            "execution_time": execution_time,
            "run_id": run_id
        }
    
    async def _memory_bomb_attack(self):
        """Create massive memory allocations to test memory leak detection."""
        await self.emit_thinking("Starting memory bomb attack")
        
        # Allocate large amounts of memory
        memory_bombs = []
        for i in range(10):
            # Create 10MB chunks
            bomb = b'A' * (10 * 1024 * 1024)
            memory_bombs.append(bomb)
            
            # Emit events to stress the bridge
            await self.emit_tool_executing(f"memory_alloc_{i}", {"size": "10MB"})
            await asyncio.sleep(0.01)
        
        await self.emit_thinking("Memory bomb attack complete")
        # Don't clean up memory - let garbage collection handle it
    
    async def _event_spam_attack(self):
        """Spam WebSocket events to test rate limiting and buffer management."""
        await self.emit_thinking("Starting event spam attack")
        
        # Send 1000 events rapidly
        for i in range(1000):
            await self.emit_thinking(f"Spam event {i}")
            await self.emit_tool_executing(f"spam_tool_{i}", {"iteration": i})
            await self.emit_tool_completed(f"spam_tool_{i}", {"result": f"spam_{i}"})
            
            # No delay - send as fast as possible
            if i % 100 == 0:
                await asyncio.sleep(0.001)  # Minimal yield
        
        await self.emit_thinking("Event spam attack complete")
    
    async def _bridge_corruption_attack(self):
        """Attempt to corrupt bridge state."""
        await self.emit_thinking("Starting bridge corruption attack")
        
        try:
            # Try to manipulate bridge internals
            if hasattr(self, '_websocket_adapter') and self._websocket_adapter._bridge:
                bridge = self._websocket_adapter._bridge
                
                # Try to corrupt bridge state
                original_state = bridge.state
                bridge.state = None  # Corrupt state
                
                await self.emit_tool_executing("corruption_test", {"target": "bridge_state"})
                
                # Try to trigger errors with corrupted state
                await bridge.health_check()
                
                # Restore state
                bridge.state = original_state
                
        except Exception as e:
            await self.emit_error(f"Bridge corruption attempt failed: {e}")
        
        await self.emit_thinking("Bridge corruption attack complete")
    
    async def _infinite_loop_attack(self):
        """Create near-infinite loop to test timeout handling."""
        await self.emit_thinking("Starting infinite loop attack")
        
        start_time = time.time()
        iteration = 0
        
        # Loop for a very long time (but not truly infinite)
        while time.time() - start_time < 60:  # 60 second limit
            iteration += 1
            if iteration % 1000 == 0:
                await self.emit_thinking(f"Loop iteration {iteration}")
                await asyncio.sleep(0.001)  # Minimal yield
        
        await self.emit_thinking("Infinite loop attack complete")
    
    async def _race_condition_attack(self):
        """Create race conditions in bridge access."""
        await self.emit_thinking("Starting race condition attack")
        
        # Create multiple concurrent tasks accessing bridge
        tasks = []
        for i in range(50):
            task = asyncio.create_task(self._concurrent_bridge_access(i))
            tasks.append(task)
        
        # Wait for all tasks with timeout
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=5.0)
        except asyncio.TimeoutError:
            await self.emit_error("Race condition attack timed out")
        
        await self.emit_thinking("Race condition attack complete")
    
    async def _concurrent_bridge_access(self, task_id: int):
        """Concurrent bridge access for race condition testing."""
        for i in range(10):
            await self.emit_thinking(f"Concurrent access {task_id}-{i}")
            await self.emit_tool_executing(f"race_tool_{task_id}_{i}", {"task_id": task_id})
            await self.emit_tool_completed(f"race_tool_{task_id}_{i}", {"result": i})
    
    async def _resource_exhaustion_attack(self):
        """Exhaust system resources."""
        await self.emit_thinking("Starting resource exhaustion attack")
        
        # Create many file descriptors
        files = []
        try:
            for i in range(100):
                import tempfile
                f = tempfile.NamedTemporaryFile()
                files.append(f)
                await self.emit_tool_executing(f"resource_fd_{i}", {"fd_count": len(files)})
        except Exception as e:
            await self.emit_error(f"Resource exhaustion: {e}")
        finally:
            # Clean up
            for f in files:
                try:
                    f.close()
                except:
                    pass
        
        await self.emit_thinking("Resource exhaustion attack complete")
    
    async def _state_corruption_attack(self):
        """Corrupt agent state."""
        await self.emit_thinking("Starting state corruption attack")
        
        # Corrupt our own state
        original_state = self.state
        self.state = "CORRUPTED_STATE"
        
        await self.emit_tool_executing("state_corruption", {"original": str(original_state)})
        
        # Try to continue with corrupted state
        try:
            self.set_state(SubAgentLifecycle.RUNNING)
        except Exception as e:
            await self.emit_error(f"State corruption detected: {e}")
        
        # Restore state
        self.state = original_state
        
        await self.emit_thinking("State corruption attack complete")
    
    async def _deadlock_attack(self):
        """Create potential deadlock scenarios."""
        await self.emit_thinking("Starting deadlock attack")
        
        # Create multiple locks and acquire them in different orders
        lock_a = asyncio.Lock()
        lock_b = asyncio.Lock()
        
        async def task_a():
            async with lock_a:
                await asyncio.sleep(0.1)
                async with lock_b:
                    await self.emit_tool_executing("deadlock_a", {"task": "a"})
        
        async def task_b():
            async with lock_b:
                await asyncio.sleep(0.1)
                async with lock_a:
                    await self.emit_tool_executing("deadlock_b", {"task": "b"})
        
        # Run tasks concurrently with timeout to prevent actual deadlock
        try:
            await asyncio.wait_for(
                asyncio.gather(task_a(), task_b()),
                timeout=1.0
            )
        except asyncio.TimeoutError:
            await self.emit_error("Deadlock detected and prevented")
        
        await self.emit_thinking("Deadlock attack complete")


class UnstableAgent(BaseAgent):
    """Agent that randomly fails or behaves unpredictably."""
    
    def __init__(self, failure_rate: float = 0.3, name: str = "UnstableAgent"):
        super().__init__(name=name, description=f"Unstable agent: {failure_rate} failure rate")
        self.failure_rate = failure_rate
        self.websocket_bridge_set = False
        
    def set_websocket_bridge(self, bridge, run_id: str) -> None:
        """Override to track bridge setting."""
        super().set_websocket_bridge(bridge, run_id)
        self.websocket_bridge_set = True
        
    async def execute(self, state: DeepAgentState, run_id: str, stream: bool = False) -> Dict[str, Any]:
        """Execute with random failures."""
        
        if not self.websocket_bridge_set:
            raise RuntimeError(f"CRITICAL: WebSocket bridge not set on agent {self.name}")
        
        await self.emit_thinking("Starting unstable execution")
        
        # Random failure
        if random.random() < self.failure_rate:
            error_type = random.choice([
                "network_error",
                "timeout_error", 
                "memory_error",
                "permission_error",
                "corruption_error"
            ])
            await self.emit_error(f"Random failure: {error_type}")
            raise RuntimeError(f"Unstable agent failure: {error_type}")
        
        # Random delays
        delay = random.uniform(0.01, 0.5)
        await asyncio.sleep(delay)
        
        # Random number of events
        num_events = random.randint(1, 10)
        for i in range(num_events):
            await self.emit_thinking(f"Unstable step {i}")
            await self.emit_tool_executing(f"unstable_tool_{i}", {"step": i})
            await self.emit_tool_completed(f"unstable_tool_{i}", {"result": i})
        
        return {
            "success": True,
            "agent_name": self.name,
            "events_emitted": num_events,
            "execution_delay": delay,
            "run_id": run_id
        }


class WebSocketBridgeStressTester:
    """Comprehensive stress tester for WebSocket bridge edge cases."""
    
    def __init__(self):
        self.metrics = StressTestMetrics()
        self.active_bridges: Set[AgentWebSocketBridge] = set()
        self.active_agents: List[BaseAgent] = []
        self.memory_tracker: List[float] = []
        self.error_log: List[str] = []
        
    def track_memory_usage(self):
        """Track current memory usage."""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.memory_tracker.append(memory_mb)
        return memory_mb
    
    async def stress_test_concurrent_bridge_creation(self, num_concurrent: int = 50) -> ConcurrencyTestResult:
        """Test concurrent bridge creation for race conditions."""
        
        self.metrics.memory_usage_start_mb = self.track_memory_usage()
        failures = []
        race_conditions = []
        
        async def create_bridge(bridge_id: int):
            try:
                # Force new bridge creation
                bridge = AgentWebSocketBridge()
                self.active_bridges.add(bridge)
                
                # Try to initialize concurrently
                result = await bridge.ensure_integration(force_reinit=True)
                
                if not result.success:
                    failures.append(f"Bridge {bridge_id} initialization failed: {result.error}")
                    return False
                
                # Test bridge operations
                status = await bridge.get_status()
                if status["state"] != IntegrationState.ACTIVE.value:
                    race_conditions.append(f"Bridge {bridge_id} in wrong state: {status['state']}")
                
                return True
                
            except Exception as e:
                failures.append(f"Bridge {bridge_id} creation failed: {e}")
                return False
        
        # Create bridges concurrently
        start_time = time.time()
        tasks = [create_bridge(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Calculate metrics
        successful = sum(1 for r in results if r is True)
        failed = num_concurrent - successful
        
        self.metrics.total_operations += num_concurrent
        self.metrics.successful_operations += successful
        self.metrics.failed_operations += failed
        self.metrics.concurrent_peak = max(self.metrics.concurrent_peak, num_concurrent)
        self.metrics.average_response_time_ms = ((end_time - start_time) * 1000) / num_concurrent
        self.metrics.memory_usage_peak_mb = max(self.memory_tracker[-10:]) if self.memory_tracker else 0
        
        return ConcurrencyTestResult(
            success=(failed / num_concurrent) < 0.1,  # Allow 10% failure rate
            metrics=self.metrics,
            failures=failures,
            race_conditions=race_conditions,
            resource_issues=[]
        )
    
    async def stress_test_agent_execution_swarm(self, num_agents: int = 100, execution_time: float = 5.0) -> ConcurrencyTestResult:
        """Test swarm of agents executing concurrently."""
        
        failures = []
        race_conditions = []
        resource_issues = []
        
        # Create single bridge for all agents
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration(force_reinit=True)
        
        # Create agent registry
        registry = AgentRegistry()
        
        # Create agents with different behaviors
        agents = []
        for i in range(num_agents):
            if i % 10 == 0:
                # 10% malicious agents
                attack_type = random.choice([
                    "memory_bomb", "event_spam", "bridge_corruption", 
                    "race_condition", "resource_exhaustion"
                ])
                agent = MaliciousAgent(attack_type=attack_type, name=f"Malicious_{i}")
            elif i % 5 == 0:
                # 20% unstable agents
                agent = UnstableAgent(failure_rate=0.2, name=f"Unstable_{i}")
            else:
                # 70% normal agents
                from tests.mission_critical.test_websocket_bridge_lifecycle_audit_20250902 import TestAgent
                agent = TestAgent(f"Normal_{i}", execution_time=random.uniform(0.1, 0.5))
            
            agents.append(agent)
            registry.register(agent.name, agent)
            self.active_agents.append(agent)
        
        # Create execution engine
        execution_engine = ExecutionEngine(registry, bridge)
        
        async def execute_agent_with_monitoring(agent: BaseAgent, agent_id: int):
            try:
                context = AgentExecutionContext(
                    agent_name=agent.name,
                    run_id=f"stress_test_{agent_id}_{uuid.uuid4()}"
                )
                state = DeepAgentState(user_id=f"stress_user_{agent_id % 10}")
                
                start_time = time.time()
                result = await execution_engine.agent_core.execute_agent(context, state, timeout=execution_time)
                execution_duration = time.time() - start_time
                
                if not result.success:
                    failures.append(f"Agent {agent.name} failed: {result.error}")
                    return False
                
                # Check for race conditions
                if execution_duration > execution_time + 1.0:
                    race_conditions.append(f"Agent {agent.name} exceeded timeout significantly")
                
                return True
                
            except Exception as e:
                failures.append(f"Agent {agent.name} execution failed: {e}")
                return False
        
        # Execute all agents concurrently with memory monitoring
        self.metrics.memory_usage_start_mb = self.track_memory_usage()
        
        start_time = time.time()
        tasks = [execute_agent_with_monitoring(agent, i) for i, agent in enumerate(agents)]
        
        # Monitor memory during execution
        memory_monitor_task = asyncio.create_task(self._monitor_memory_during_execution())
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            memory_monitor_task.cancel()
            try:
                await memory_monitor_task
            except asyncio.CancelledError:
                pass
        
        end_time = time.time()
        
        # Calculate metrics
        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful
        
        self.metrics.total_operations += num_agents
        self.metrics.successful_operations += successful
        self.metrics.failed_operations += failed
        self.metrics.concurrent_peak = max(self.metrics.concurrent_peak, num_agents)
        self.metrics.average_response_time_ms = ((end_time - start_time) * 1000) / num_agents
        self.metrics.memory_usage_end_mb = self.track_memory_usage()
        
        # Check for memory leaks
        if self.metrics.memory_usage_end_mb > self.metrics.memory_usage_start_mb * 2:
            resource_issues.append(f"Potential memory leak detected: {self.metrics.memory_usage_start_mb}MB -> {self.metrics.memory_usage_end_mb}MB")
        
        return ConcurrencyTestResult(
            success=(failed / num_agents) < 0.2,  # Allow 20% failure rate for stress test
            metrics=self.metrics,
            failures=failures,
            race_conditions=race_conditions,
            resource_issues=resource_issues
        )
    
    async def _monitor_memory_during_execution(self):
        """Monitor memory usage during test execution."""
        while True:
            try:
                memory_mb = self.track_memory_usage()
                self.metrics.memory_usage_peak_mb = max(self.metrics.memory_usage_peak_mb, memory_mb)
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception:
                continue
    
    async def cleanup_resources(self):
        """Clean up test resources."""
        # Close all bridges
        for bridge in self.active_bridges:
            try:
                await bridge.shutdown()
            except Exception:
                pass
        
        self.active_bridges.clear()
        self.active_agents.clear()
        
        # Force garbage collection
        gc.collect()


@pytest.fixture
async def stress_tester():
    """Fixture providing WebSocket bridge stress tester."""
    tester = WebSocketBridgeStressTester()
    yield tester
    await tester.cleanup_resources()


@pytest.fixture
async def bridge_singleton_manager():
    """Fixture to manage bridge singleton state."""
    # Clear singleton state before test
    AgentWebSocketBridge._instance = None
    yield
    # Clear singleton state after test
    AgentWebSocketBridge._instance = None


class TestWebSocketBridgeRaceConditions:
    """Test race conditions in WebSocket bridge lifecycle."""
    
    @pytest.mark.asyncio
    async def test_concurrent_bridge_initialization_race_conditions(self, bridge_singleton_manager, stress_tester):
        """Test race conditions in concurrent bridge initialization."""
        
        # Test with increasing levels of concurrency
        concurrency_levels = [10, 25, 50, 100]
        
        for level in concurrency_levels:
            # Clear singleton between tests
            AgentWebSocketBridge._instance = None
            
            result = await stress_tester.stress_test_concurrent_bridge_creation(level)
            
            # Must handle race conditions gracefully
            assert result.success, f"Race condition handling failed at level {level}: {result.failures}"
            
            # Should not have excessive race condition detections
            assert len(result.race_conditions) < level * 0.1, \
                f"Too many race conditions at level {level}: {result.race_conditions}"
            
            # Memory usage should be reasonable
            assert result.metrics.memory_usage_peak_mb < 1000, \
                f"Excessive memory usage: {result.metrics.memory_usage_peak_mb}MB"
    
    @pytest.mark.asyncio
    async def test_bridge_singleton_thread_safety(self, bridge_singleton_manager):
        """Test thread safety of bridge singleton pattern."""
        
        bridges_created = []
        exceptions = []
        
        def create_bridge_sync():
            try:
                # Create bridge from different thread
                bridge = AgentWebSocketBridge()
                bridges_created.append(id(bridge))
            except Exception as e:
                exceptions.append(str(e))
        
        # Create bridges from multiple threads simultaneously
        threads = []
        for i in range(20):
            thread = threading.Thread(target=create_bridge_sync)
            threads.append(thread)
        
        # Start all threads at once
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Validate thread safety
        assert len(exceptions) == 0, f"Thread safety violations: {exceptions}"
        
        # All bridges should be the same instance (singleton)
        unique_bridges = set(bridges_created)
        assert len(unique_bridges) == 1, \
            f"Singleton pattern violated - multiple instances created: {unique_bridges}"
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution_with_shared_bridge(self, stress_tester):
        """Test multiple agents executing concurrently with shared bridge."""
        
        result = await stress_tester.stress_test_agent_execution_swarm(num_agents=50, execution_time=2.0)
        
        # Must handle concurrent execution
        assert result.success, f"Concurrent execution failed: {result.failures[:10]}"  # Show first 10 failures
        
        # Should handle race conditions gracefully
        assert len(result.race_conditions) < 5, \
            f"Too many race conditions: {result.race_conditions}"
        
        # Resource usage should be reasonable
        assert len(result.resource_issues) == 0, \
            f"Resource issues detected: {result.resource_issues}"


class TestWebSocketBridgeMemoryLeaks:
    """Test memory leaks in WebSocket bridge lifecycle."""
    
    @pytest.mark.asyncio
    async def test_memory_leak_in_long_running_sessions(self, bridge_singleton_manager):
        """Test for memory leaks in long-running agent sessions."""
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        registry = AgentRegistry()
        
        # Track memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run many short agent sessions
        for session in range(100):
            agent = MaliciousAgent(attack_type="memory_bomb", name=f"MemoryAgent_{session}")
            registry.register(agent.name, agent)
            
            execution_core = AgentExecutionCore(registry, bridge)
            
            context = AgentExecutionContext(
                agent_name=agent.name,
                run_id=f"memory_test_{session}"
            )
            state = DeepAgentState(user_id=f"user_{session % 10}")
            
            try:
                # Execute with short timeout to prevent hanging
                result = await asyncio.wait_for(
                    execution_core.execute_agent(context, state, timeout=0.5),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                # Expected for memory bomb attacks
                pass
            except Exception:
                # Expected for malicious agents
                pass
            
            # Clean up agent
            registry._agents.pop(agent.name, None)
            
            # Force garbage collection every 10 sessions
            if session % 10 == 0:
                gc.collect()
        
        # Final garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Let cleanup complete
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 500MB for 100 sessions)
        assert memory_growth < 500, \
            f"Potential memory leak detected: {initial_memory}MB -> {final_memory}MB (growth: {memory_growth}MB)"
        
        # Clean up
        await bridge.shutdown()
    
    @pytest.mark.asyncio
    async def test_event_buffer_memory_management(self, bridge_singleton_manager):
        """Test memory management of WebSocket event buffers."""
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Create agent that spams events
        agent = MaliciousAgent(attack_type="event_spam", name="EventSpammer")
        registry = AgentRegistry()
        registry.register(agent.name, agent)
        
        execution_core = AgentExecutionCore(registry, bridge)
        
        # Track memory before
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        context = AgentExecutionContext(
            agent_name=agent.name,
            run_id="event_spam_test"
        )
        state = DeepAgentState(user_id="spam_user")
        
        # Execute event spam attack
        try:
            await asyncio.wait_for(
                execution_core.execute_agent(context, state, timeout=5.0),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            pass  # Expected
        
        # Force cleanup
        gc.collect()
        await asyncio.sleep(0.1)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be bounded despite event spam
        assert memory_growth < 100, \
            f"Event buffer memory leak: {initial_memory}MB -> {final_memory}MB (growth: {memory_growth}MB)"
        
        await bridge.shutdown()


class TestWebSocketBridgeReconnectionScenarios:
    """Test WebSocket reconnection and recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_bridge_recovery_after_websocket_failure(self, bridge_singleton_manager):
        """Test bridge recovery after WebSocket manager failure."""
        
        bridge = AgentWebSocketBridge()
        
        # Mock WebSocket manager that fails
        failing_websocket_manager = AsyncMock()
        failing_websocket_manager.send_to_thread = AsyncMock(side_effect=Exception("WebSocket disconnected"))
        failing_websocket_manager.connections = {}
        
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager') as mock_get_ws:
            mock_get_ws.return_value = failing_websocket_manager
            
            # Initialize with failing WebSocket manager
            result = await bridge.ensure_integration()
            assert result.success, "Bridge initialization should succeed even with failing WebSocket manager"
            
            # Test notification with failing WebSocket
            success = await bridge.notify_agent_started("test_run", "TestAgent")
            assert not success, "Notification should fail with broken WebSocket manager"
            
            # Verify bridge detects failure
            health = await bridge.health_check()
            assert not health.websocket_manager_healthy, "Should detect WebSocket manager failure"
        
        # Now test recovery with working WebSocket manager
        working_websocket_manager = AsyncMock()
        working_websocket_manager.send_to_thread = AsyncMock(return_value=True)
        working_websocket_manager.connections = {}
        
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager') as mock_get_ws:
            mock_get_ws.return_value = working_websocket_manager
            
            # Force recovery
            recovery_result = await bridge.recover_integration()
            assert recovery_result.success, f"Recovery should succeed: {recovery_result.error}"
            
            # Test notification with recovered WebSocket
            success = await bridge.notify_agent_started("test_run_2", "TestAgent2")
            assert success, "Notification should succeed after recovery"
            
            # Verify bridge health is restored
            health = await bridge.health_check()
            assert health.websocket_manager_healthy, "WebSocket manager should be healthy after recovery"
        
        await bridge.shutdown()
    
    @pytest.mark.asyncio
    async def test_bridge_state_corruption_recovery(self, bridge_singleton_manager):
        """Test recovery from bridge state corruption."""
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Corrupt bridge state
        original_state = bridge.state
        bridge.state = None  # Corrupt state
        
        # Verify corruption is detected
        try:
            await bridge.health_check()
        except Exception:
            pass  # Expected with corrupted state
        
        # Test recovery
        bridge.state = original_state
        recovery_result = await bridge.recover_integration()
        assert recovery_result.success, "Should recover from state corruption"
        
        # Verify recovery
        health = await bridge.health_check()
        assert health.state == IntegrationState.ACTIVE, "Should be active after recovery"
        
        await bridge.shutdown()


class TestWebSocketBridgeInvalidInputHandling:
    """Test handling of invalid and malicious inputs."""
    
    @pytest.mark.asyncio
    async def test_invalid_run_id_handling(self, bridge_singleton_manager):
        """Test handling of invalid run_ids."""
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Test with various invalid run_ids
        invalid_run_ids = [
            None,
            "",
            "a" * 10000,  # Extremely long
            "invalid\x00\x01\x02",  # With null bytes
            "../../etc/passwd",  # Path traversal attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "' OR 1=1 --",  # SQL injection attempt
            "🚀🔥💀👹🤖",  # Unicode emojis
        ]
        
        for invalid_run_id in invalid_run_ids:
            try:
                success = await bridge.notify_agent_started(invalid_run_id, "TestAgent")
                # Should either succeed gracefully or fail safely
                assert isinstance(success, bool), f"Should return boolean for run_id: {invalid_run_id}"
            except Exception as e:
                # Exceptions should be handled gracefully
                assert "Critical" not in str(e), f"Should not have critical errors for run_id: {invalid_run_id}"
        
        await bridge.shutdown()
    
    @pytest.mark.asyncio
    async def test_malicious_agent_name_handling(self, bridge_singleton_manager):
        """Test handling of malicious agent names."""
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        malicious_names = [
            None,
            "",
            "A" * 100000,  # Extremely long name
            "Agent\x00NULL",  # With null bytes
            "../../../evil",  # Path traversal
            "<script>document.location='http://evil.com'</script>",  # XSS
            "'; DROP TABLE agents; --",  # SQL injection
            "Agent\r\n\r\nHTTP/1.1 200 OK\r\n\r\n<html><body>Injected</body></html>",  # HTTP header injection
        ]
        
        for malicious_name in malicious_names:
            try:
                success = await bridge.notify_agent_started("test_run", malicious_name)
                assert isinstance(success, bool), f"Should handle malicious name safely: {malicious_name}"
            except Exception as e:
                # Should not crash with unhandled exceptions
                assert "CRITICAL" not in str(e).upper(), f"Should not have critical errors: {malicious_name}"
        
        await bridge.shutdown()
    
    @pytest.mark.asyncio
    async def test_massive_payload_handling(self, bridge_singleton_manager):
        """Test handling of massive payloads."""
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Create massive payloads
        massive_string = "A" * (10 * 1024 * 1024)  # 10MB string
        massive_dict = {f"key_{i}": f"value_{i}" * 1000 for i in range(10000)}  # Large dict
        
        # Test various notification methods with massive payloads
        test_cases = [
            ("notify_agent_thinking", ["test_run", "TestAgent", massive_string]),
            ("notify_tool_executing", ["test_run", "TestAgent", "test_tool", massive_dict]),
            ("notify_tool_completed", ["test_run", "TestAgent", "test_tool", massive_dict]),
            ("notify_custom", ["test_run", "TestAgent", "custom_type", massive_dict]),
        ]
        
        for method_name, args in test_cases:
            try:
                method = getattr(bridge, method_name)
                success = await method(*args)
                
                # Should either handle gracefully or fail safely
                assert isinstance(success, bool), f"Should return boolean for {method_name} with massive payload"
                
            except Exception as e:
                # Should not cause system crashes
                assert "OutOfMemoryError" not in str(e), f"Should handle memory gracefully: {method_name}"
                assert "SystemExit" not in str(e), f"Should not exit system: {method_name}"
        
        await bridge.shutdown()


class TestWebSocketBridgeTimeoutScenarios:
    """Test timeout and resource exhaustion scenarios."""
    
    @pytest.mark.asyncio
    async def test_bridge_initialization_timeout(self, bridge_singleton_manager):
        """Test bridge initialization timeout handling."""
        
        # Mock slow WebSocket manager
        slow_websocket_manager = AsyncMock()
        
        async def slow_init():
            await asyncio.sleep(100)  # Very slow
            return slow_websocket_manager
        
        slow_websocket_manager.send_to_thread = AsyncMock(return_value=True)
        slow_websocket_manager.connections = {}
        
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager') as mock_get_ws:
            mock_get_ws.side_effect = slow_init
            
            bridge = AgentWebSocketBridge()
            
            # Test initialization with timeout
            start_time = time.time()
            result = await asyncio.wait_for(
                bridge.ensure_integration(),
                timeout=2.0
            )
            end_time = time.time()
            
            # Should timeout gracefully
            assert end_time - start_time < 3.0, "Should timeout within reasonable time"
            assert not result.success, "Should fail due to timeout"
            assert "timeout" in result.error.lower() or "failed" in result.error.lower(), \
                f"Should indicate timeout/failure: {result.error}"
    
    @pytest.mark.asyncio
    async def test_agent_execution_timeout_with_bridge_cleanup(self, bridge_singleton_manager):
        """Test agent execution timeout with proper bridge cleanup."""
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Create agent that hangs
        hanging_agent = MaliciousAgent(attack_type="infinite_loop", name="HangingAgent")
        registry = AgentRegistry()
        registry.register(hanging_agent.name, hanging_agent)
        
        execution_core = AgentExecutionCore(registry, bridge)
        
        context = AgentExecutionContext(
            agent_name=hanging_agent.name,
            run_id="timeout_test"
        )
        state = DeepAgentState(user_id="timeout_user")
        
        # Execute with timeout
        start_time = time.time()
        result = await execution_core.execute_agent(context, state, timeout=1.0)
        end_time = time.time()
        
        # Should timeout properly
        assert end_time - start_time < 5.0, "Should timeout within reasonable time"
        assert not result.success, "Should fail due to timeout"
        
        # Bridge should still be functional
        health = await bridge.health_check()
        assert health.websocket_manager_healthy, "Bridge should remain functional after agent timeout"
        
        await bridge.shutdown()
    
    @pytest.mark.asyncio
    async def test_websocket_notification_timeout_handling(self, bridge_singleton_manager):
        """Test WebSocket notification timeout handling."""
        
        bridge = AgentWebSocketBridge()
        
        # Mock WebSocket manager that hangs on send
        hanging_websocket_manager = AsyncMock()
        
        async def hanging_send(*args, **kwargs):
            await asyncio.sleep(100)  # Hang indefinitely
            return True
        
        hanging_websocket_manager.send_to_thread = hanging_send
        hanging_websocket_manager.connections = {}
        
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager') as mock_get_ws:
            mock_get_ws.return_value = hanging_websocket_manager
            
            await bridge.ensure_integration()
            
            # Test notification with hanging WebSocket
            start_time = time.time()
            try:
                success = await asyncio.wait_for(
                    bridge.notify_agent_started("test_run", "TestAgent"),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                success = False
            end_time = time.time()
            
            # Should timeout within reasonable time
            assert end_time - start_time < 2.0, "Should timeout quickly"
            assert not success, "Should fail due to WebSocket timeout"
        
        await bridge.shutdown()


class TestWebSocketBridgeDockerScenarios:
    """Test bridge behavior during Docker container scenarios."""
    
    @pytest.mark.asyncio
    async def test_bridge_persistence_across_service_restart(self, bridge_singleton_manager):
        """Test bridge persistence across service restarts."""
        
        # Create and initialize bridge
        bridge = AgentWebSocketBridge()
        result = await bridge.ensure_integration()
        assert result.success, "Initial bridge setup should succeed"
        
        # Get initial metrics
        initial_metrics = await bridge.get_metrics()
        
        # Simulate service restart by forcing re-initialization
        restart_result = await bridge.ensure_integration(force_reinit=True)
        assert restart_result.success, "Bridge should handle restart gracefully"
        
        # Verify metrics are preserved/handled correctly
        post_restart_metrics = await bridge.get_metrics()
        assert post_restart_metrics["total_initializations"] > initial_metrics["total_initializations"], \
            "Should track restart as new initialization"
        
        # Verify bridge is functional after restart
        success = await bridge.notify_agent_started("post_restart_test", "TestAgent")
        assert success, "Bridge should be functional after restart"
        
        await bridge.shutdown()
    
    @pytest.mark.asyncio
    async def test_bridge_graceful_shutdown_handling(self, bridge_singleton_manager):
        """Test bridge graceful shutdown handling."""
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Start some background operations
        background_tasks = []
        for i in range(10):
            task = asyncio.create_task(
                bridge.notify_agent_thinking(f"run_{i}", "TestAgent", f"Background operation {i}")
            )
            background_tasks.append(task)
        
        # Initiate graceful shutdown
        shutdown_start = time.time()
        await bridge.shutdown()
        shutdown_end = time.time()
        
        # Shutdown should be reasonably fast
        assert shutdown_end - shutdown_start < 5.0, "Shutdown should complete within 5 seconds"
        
        # Background tasks should be handled gracefully
        for task in background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Bridge should be in shutdown state
        assert bridge.state == IntegrationState.UNINITIALIZED, "Bridge should be uninitialized after shutdown"


class TestWebSocketBridgeExtremeConcurrency:
    """Test extreme concurrency scenarios."""
    
    @pytest.mark.asyncio
    async def test_extreme_concurrent_agent_swarm(self, stress_tester):
        """Test extreme concurrency with large agent swarm."""
        
        # Test with 500 concurrent agents (extreme stress)
        result = await stress_tester.stress_test_agent_execution_swarm(
            num_agents=500, 
            execution_time=1.0
        )
        
        # Even under extreme stress, should maintain reasonable success rate
        success_rate = result.metrics.successful_operations / max(1, result.metrics.total_operations)
        assert success_rate > 0.7, f"Success rate too low under extreme load: {success_rate}"
        
        # Memory usage should be bounded
        memory_growth = result.metrics.memory_usage_end_mb - result.metrics.memory_usage_start_mb
        assert memory_growth < 2000, f"Excessive memory growth under load: {memory_growth}MB"
        
        # Should handle resource issues gracefully
        assert len(result.resource_issues) < 5, f"Too many resource issues: {result.resource_issues}"
    
    @pytest.mark.asyncio
    async def test_bridge_under_sustained_load(self, bridge_singleton_manager):
        """Test bridge behavior under sustained high load."""
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Create sustained load for 10 seconds
        load_duration = 10.0
        start_time = time.time()
        
        successful_notifications = 0
        failed_notifications = 0
        
        async def generate_load():
            nonlocal successful_notifications, failed_notifications
            
            while time.time() - start_time < load_duration:
                try:
                    # Send various types of notifications rapidly
                    tasks = [
                        bridge.notify_agent_started(f"load_test_{int(time.time() * 1000000)}", "LoadAgent"),
                        bridge.notify_agent_thinking(f"load_test_{int(time.time() * 1000000)}", "LoadAgent", "Processing..."),
                        bridge.notify_tool_executing(f"load_test_{int(time.time() * 1000000)}", "LoadAgent", "LoadTool"),
                        bridge.notify_tool_completed(f"load_test_{int(time.time() * 1000000)}", "LoadAgent", "LoadTool"),
                        bridge.notify_agent_completed(f"load_test_{int(time.time() * 1000000)}", "LoadAgent"),
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, bool) and result:
                            successful_notifications += 1
                        else:
                            failed_notifications += 1
                    
                    await asyncio.sleep(0.001)  # Brief pause
                    
                except Exception:
                    failed_notifications += 5  # Count all as failed
        
        # Generate load from multiple concurrent sources
        load_tasks = [generate_load() for _ in range(20)]
        await asyncio.gather(*load_tasks)
        
        total_notifications = successful_notifications + failed_notifications
        success_rate = successful_notifications / max(1, total_notifications)
        
        # Should maintain reasonable success rate under sustained load
        assert success_rate > 0.8, f"Success rate too low under sustained load: {success_rate}"
        assert total_notifications > 1000, f"Should process significant volume: {total_notifications}"
        
        # Bridge should remain healthy
        health = await bridge.health_check()
        assert health.websocket_manager_healthy, "Bridge should remain healthy under sustained load"
        
        await bridge.shutdown()


if __name__ == "__main__":
    # Run the tests with maximum verbosity
    pytest.main([__file__, "-v", "-s", "--tb=short", "--maxfail=5"])
