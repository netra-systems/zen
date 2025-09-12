"""
Stress Testing for Concurrent Agent Execution with Advanced Factory Patterns
Test #8 of Agent Registry and Factory Patterns Test Suite

Business Value Justification (BVJ):
- Segment: Enterprise (Advanced stress testing for production-scale concurrent workloads)
- Business Goal: Ensure platform stability under high-load concurrent agent execution scenarios
- Value Impact: Validates platform can handle enterprise-scale concurrent workloads (50+ users)
- Strategic Impact: $2M+ ARR protection - prevents platform failures under production load

CRITICAL MISSION: Test Advanced Concurrent Agent Execution Stress Scenarios ensuring:
1. Platform handles extreme concurrent loads (20+ simultaneous users)
2. Factory patterns maintain isolation under stress conditions
3. Memory management prevents leaks during sustained concurrent execution
4. WebSocket event delivery remains reliable under high event throughput
5. Error propagation and recovery work correctly under concurrent failures
6. Performance degradation is graceful and within acceptable bounds
7. Resource cleanup prevents resource exhaustion during stress tests
8. Agent state consistency maintained under concurrent modifications

FOCUS: Stress testing with realistic production-like concurrent loads to validate 
        enterprise-grade stability and performance characteristics.
"""

import asyncio
import pytest
import time
import uuid
import json
import gc
import psutil
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from collections import defaultdict, deque
import random
import weakref

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import classes under test
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry,
    UserAgentSession
)

from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    configure_agent_instance_factory
)

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    create_agent_websocket_bridge
)

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher


# ============================================================================
# FIXTURES - Stress Testing Infrastructure
# ============================================================================

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager optimized for stress testing."""
    mock_llm = AsyncMock()
    mock_llm.initialize = AsyncMock()
    mock_llm.chat_completion = AsyncMock(return_value="Stress test response from agent")
    mock_llm.is_healthy = Mock(return_value=True)
    
    # Stress testing metrics
    mock_llm.stress_metrics = {
        "total_requests": 0,
        "concurrent_requests": 0,
        "max_concurrent": 0,
        "error_count": 0,
        "avg_response_time": 0.0
    }
    
    # Track concurrent usage
    async def track_request(*args, **kwargs):
        mock_llm.stress_metrics["total_requests"] += 1
        mock_llm.stress_metrics["concurrent_requests"] += 1
        if mock_llm.stress_metrics["concurrent_requests"] > mock_llm.stress_metrics["max_concurrent"]:
            mock_llm.stress_metrics["max_concurrent"] = mock_llm.stress_metrics["concurrent_requests"]
        
        try:
            # Simulate variable response time under load
            response_time = random.uniform(0.05, 0.2)
            await asyncio.sleep(response_time)
            return "Stress test response from agent"
        finally:
            mock_llm.stress_metrics["concurrent_requests"] -= 1
    
    mock_llm.chat_completion = track_request
    return mock_llm


@pytest.fixture
def stress_websocket_manager():
    """Create WebSocket manager optimized for stress testing."""
    ws_manager = UnifiedWebSocketManager()
    
    # Stress testing infrastructure
    ws_manager._stress_metrics = {
        "total_events": 0,
        "events_per_second": 0,
        "max_events_per_second": 0,
        "failed_events": 0,
        "backpressure_events": 0,
        "last_second_events": deque(maxlen=1000)
    }
    
    ws_manager._event_buffer = deque(maxlen=10000)  # Large buffer for stress testing
    ws_manager._buffer_lock = asyncio.Lock()
    ws_manager._last_metrics_update = time.time()
    
    # High-throughput event handling
    async def stress_send_event(*args, **kwargs):
        current_time = time.time()
        async with ws_manager._buffer_lock:
            # Track events per second
            ws_manager._stress_metrics["last_second_events"].append(current_time)
            ws_manager._stress_metrics["total_events"] += 1
            
            # Update events per second every second
            if current_time - ws_manager._last_metrics_update >= 1.0:
                recent_events = [t for t in ws_manager._stress_metrics["last_second_events"] 
                               if current_time - t <= 1.0]
                ws_manager._stress_metrics["events_per_second"] = len(recent_events)
                
                if ws_manager._stress_metrics["events_per_second"] > ws_manager._stress_metrics["max_events_per_second"]:
                    ws_manager._stress_metrics["max_events_per_second"] = ws_manager._stress_metrics["events_per_second"]
                
                ws_manager._last_metrics_update = current_time
            
            # Add event to buffer
            event_data = args[0] if args else kwargs
            ws_manager._event_buffer.append({
                "timestamp": current_time,
                "event": event_data,
                "thread_id": threading.get_ident()
            })
            
            # Simulate backpressure under extreme load
            if len(ws_manager._event_buffer) > 8000:
                ws_manager._stress_metrics["backpressure_events"] += 1
                # Simulate slight delay under backpressure
                await asyncio.sleep(0.001)
        
        return True
    
    ws_manager.send_event = stress_send_event
    ws_manager.send_to_thread = stress_send_event  # Bridge calls send_to_thread, not send_event
    ws_manager.is_connected = Mock(return_value=True)
    ws_manager.get_connection_count = Mock(return_value=50)  # Simulate many connections
    
    return ws_manager


@pytest.fixture
def stress_test_user_contexts():
    """Create large number of user contexts for stress testing."""
    contexts = []
    user_tiers = ["free", "early", "mid", "enterprise", "premium"]
    
    for i in range(25):  # Stress test with 25 concurrent users
        tier = user_tiers[i % len(user_tiers)]
        context = UserExecutionContext(
            user_id=f"stress_user_{i}_{uuid.uuid4().hex[:6]}",
            request_id=f"stress_req_{i}_{uuid.uuid4().hex[:6]}",
            thread_id=f"stress_thread_{i}_{uuid.uuid4().hex[:6]}",
            run_id=f"stress_run_{i}_{uuid.uuid4().hex[:6]}",
            agent_context={
                "user_tier": tier,
                "stress_test": True,
                "user_index": i,
                "load_factor": random.uniform(0.5, 2.0),
                "simulated_complexity": random.choice(["low", "medium", "high", "extreme"])
            }
        )
        contexts.append(context)
    
    return contexts


@pytest.fixture
def mock_stress_test_agent():
    """Create mock agent that simulates realistic stress under concurrent load."""
    class MockStressTestAgent:
        def __init__(self, llm_manager=None, tool_dispatcher=None):
            self.llm_manager = llm_manager
            self.tool_dispatcher = tool_dispatcher
            self.execution_history = []
            self._websocket_bridge = None
            self._run_id = None
            self._agent_name = None
            self._stress_metrics = {
                "total_executions": 0,
                "failed_executions": 0,
                "avg_execution_time": 0.0,
                "memory_usage": 0,
                "cpu_usage": 0.0
            }
            
        def set_websocket_bridge(self, bridge, run_id, agent_name=None):
            self._websocket_bridge = bridge
            self._run_id = run_id
            self._agent_name = agent_name or "stress_agent"
            
        async def execute(self, state, run_id):
            """Stress test agent execution with realistic computational load."""
            execution_start = time.time()
            try:
                self._stress_metrics["total_executions"] += 1
                
                # Extract complexity from state/context
                complexity = "medium"
                load_factor = 1.0
                if hasattr(state, 'complexity'):
                    complexity = state.complexity
                if hasattr(state, 'load_factor'):
                    load_factor = state.load_factor
                
                # Send enhanced agent started event
                if self._websocket_bridge:
                    await self._websocket_bridge.notify_agent_started(
                        run_id=self._run_id,
                        agent_name=self._agent_name,
                        context={
                            "state": "started",
                            "complexity": complexity,
                            "load_factor": load_factor,
                            "execution_count": self._stress_metrics["total_executions"],
                            "stress_test": True
                        }
                    )
                
                # Simulate variable computational load based on complexity
                complexity_multiplier = {"low": 0.5, "medium": 1.0, "high": 1.5, "extreme": 2.0}[complexity]
                base_processing_time = 0.1 * complexity_multiplier * load_factor
                
                # Simulate multi-step processing with WebSocket updates
                steps = int(3 * complexity_multiplier)
                for step in range(steps):
                    # Send thinking update
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_agent_thinking(
                            run_id=self._run_id,
                            agent_name=self._agent_name,
                            reasoning=f"Processing step {step + 1}/{steps} - Complexity: {complexity}",
                            step_number=step + 1,
                            progress_percentage=(step + 1) / steps * 100
                        )
                    
                    # Simulate actual computational work
                    await asyncio.sleep(base_processing_time / steps)
                    
                    # Simulate memory allocation (testing memory management)
                    temp_data = [i for i in range(1000)]  # Temporary allocation
                    del temp_data  # Cleanup
                
                # Simulate tool executions
                tool_count = min(5, int(2 * complexity_multiplier))
                for i in range(tool_count):
                    tool_name = f"stress_tool_{i}"
                    
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_tool_executing(
                            run_id=self._run_id,
                            agent_name=self._agent_name,
                            tool_name=tool_name,
                            parameters={
                                "input": str(state),
                                "complexity": complexity,
                                "tool_index": i,
                                "load_factor": load_factor
                            }
                        )
                    
                    # Simulate tool processing
                    tool_time = base_processing_time / tool_count
                    await asyncio.sleep(tool_time)
                    
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_tool_completed(
                            run_id=self._run_id,
                            agent_name=self._agent_name,
                            tool_name=tool_name,
                            result={
                                "output": f"processed_by_{tool_name}",
                                "complexity": complexity,
                                "processing_time": tool_time * 1000
                            },
                            execution_time_ms=tool_time * 1000
                        )
                
                # Calculate final execution metrics
                total_execution_time = (time.time() - execution_start) * 1000
                
                # Update stress metrics
                prev_avg = self._stress_metrics["avg_execution_time"]
                count = self._stress_metrics["total_executions"]
                self._stress_metrics["avg_execution_time"] = (prev_avg * (count - 1) + total_execution_time) / count
                
                # Complete execution
                result = {
                    "status": "success",
                    "data": f"Stress processed: {state}",
                    "complexity": complexity,
                    "load_factor": load_factor,
                    "execution_metrics": {
                        "execution_time_ms": total_execution_time,
                        "steps_processed": steps,
                        "tools_used": tool_count,
                        "thread_id": threading.get_ident(),
                        "run_id": run_id
                    },
                    "stress_metrics": self._stress_metrics.copy()
                }
                
                if self._websocket_bridge:
                    await self._websocket_bridge.notify_agent_completed(
                        run_id=self._run_id,
                        agent_name=self._agent_name,
                        result=result,
                        execution_time_ms=total_execution_time
                    )
                
                # Record execution history for analysis
                self.execution_history.append({
                    "execution_id": f"{run_id}_{time.time()}",
                    "state": str(state),
                    "run_id": run_id,
                    "result": result,
                    "execution_time": total_execution_time,
                    "complexity": complexity,
                    "thread_id": threading.get_ident()
                })
                
                return result
                
            except Exception as e:
                self._stress_metrics["failed_executions"] += 1
                
                if self._websocket_bridge:
                    await self._websocket_bridge.notify_agent_error(
                        run_id=self._run_id,
                        agent_name=self._agent_name,
                        error=str(e),
                        context={
                            "complexity": complexity,
                            "load_factor": load_factor,
                            "execution_time": (time.time() - execution_start) * 1000
                        }
                    )
                raise
            
        async def cleanup(self):
            """Enhanced cleanup with stress test metrics preservation."""
            cleanup_start = time.time()
            
            # Preserve metrics before cleanup
            final_metrics = self._stress_metrics.copy()
            
            # Clear execution history to free memory
            self.execution_history.clear()
            
            cleanup_time = (time.time() - cleanup_start) * 1000
            final_metrics["cleanup_time_ms"] = cleanup_time
            
            return final_metrics
        
        def get_stress_metrics(self):
            """Get current stress testing metrics."""
            return self._stress_metrics.copy()
    
    return MockStressTestAgent


# ============================================================================
# TEST: High-Load Concurrent Stress Testing
# ============================================================================

class TestHighLoadConcurrentStress(SSotBaseTestCase):
    """Test system behavior under high concurrent load stress conditions."""
    
    @pytest.mark.asyncio
    async def test_25_concurrent_users_extreme_stress(self, mock_llm_manager, stress_websocket_manager, 
                                                    mock_stress_test_agent, stress_test_user_contexts):
        """Test platform stability with 25 concurrent users under extreme stress load."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(stress_websocket_manager)
        
        # Stress test metrics collection
        stress_metrics = {
            "total_users": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
            "peak_memory_usage": 0,
            "peak_websocket_events": 0,
            "user_performance": {}
        }
        
        # Create all 25 stress test agents
        user_agents = []
        agent_creation_start = time.time()
        
        for i, context in enumerate(stress_test_user_contexts):
            agent = mock_stress_test_agent()
            registry.get_async = AsyncMock(return_value=agent)
            
            created_agent = await registry.create_agent_for_user(
                user_id=context.user_id,
                agent_type=f"stress_agent_{i}",
                user_context=context,
                websocket_manager=stress_websocket_manager
            )
            
            user_agents.append((created_agent, context))
            stress_metrics["total_users"] += 1
        
        agent_creation_time = time.time() - agent_creation_start
        
        # Record initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Execute all agents concurrently with varying complexity
        execution_tasks = []
        stress_test_start = time.time()
        
        for agent, context in user_agents:
            complexity = context.agent_context["simulated_complexity"]
            load_factor = context.agent_context["load_factor"]
            
            # Create stress test input data
            stress_input = type('StressInput', (), {
                'data': f"stress_data_{context.user_id}",
                'complexity': complexity,
                'load_factor': load_factor,
                'user_index': context.agent_context["user_index"]
            })()
            
            execution_task = agent.execute(stress_input, context.run_id)
            execution_tasks.append((execution_task, agent, context))
        
        # Monitor system resources during execution
        async def monitor_resources():
            max_memory = initial_memory
            max_events = 0
            
            for _ in range(10):  # Monitor for ~5 seconds
                await asyncio.sleep(0.5)
                
                current_memory = process.memory_info().rss / 1024 / 1024
                max_memory = max(max_memory, current_memory)
                
                current_events = stress_websocket_manager._stress_metrics["events_per_second"]
                max_events = max(max_events, current_events)
            
            return max_memory, max_events
        
        # Execute stress test with resource monitoring
        monitor_task = asyncio.create_task(monitor_resources())
        task_list = [task for task, _, _ in execution_tasks]
        
        results = await asyncio.gather(*task_list, return_exceptions=True)
        peak_memory, peak_events = await monitor_task
        
        total_stress_execution_time = time.time() - stress_test_start
        
        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception) and r.get("status") == "success"]
        failed_results = [r for r in results if isinstance(r, Exception) or r.get("status") != "success"]
        
        stress_metrics.update({
            "successful_executions": len(successful_results),
            "failed_executions": len(failed_results),
            "total_execution_time": total_stress_execution_time,
            "peak_memory_usage": peak_memory,
            "peak_websocket_events": peak_events,
            "agent_creation_time": agent_creation_time
        })
        
        # Collect per-user performance metrics
        for i, (result, (agent, context)) in enumerate(zip(results, execution_tasks)):
            user_id = context.user_id
            if not isinstance(result, Exception):
                execution_time = result.get("execution_metrics", {}).get("execution_time_ms", 0)
                stress_metrics["user_performance"][user_id] = {
                    "success": True,
                    "execution_time_ms": execution_time,
                    "complexity": context.agent_context["simulated_complexity"],
                    "load_factor": context.agent_context["load_factor"]
                }
            else:
                stress_metrics["user_performance"][user_id] = {
                    "success": False,
                    "error": str(result),
                    "complexity": context.agent_context["simulated_complexity"],
                    "load_factor": context.agent_context["load_factor"]
                }
        
        # Stress test assertions
        assert len(results) == 25, "Should have 25 stress test results"
        
        # Allow for some failures under extreme stress, but most should succeed
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.8, f"Success rate should be  >= 80% under stress, got {success_rate:.1%}"
        
        # Performance under stress
        assert total_stress_execution_time < 10.0, f"25 concurrent stress executions should complete in <10s, took {total_stress_execution_time:.2f}s"
        assert agent_creation_time < 5.0, f"Agent creation for 25 users should take <5s, took {agent_creation_time:.2f}s"
        
        # Memory usage should not grow excessively
        memory_growth = peak_memory - initial_memory
        assert memory_growth < 200, f"Memory growth should be <200MB under stress, grew {memory_growth:.1f}MB"
        
        # WebSocket performance under stress
        total_ws_events = stress_websocket_manager._stress_metrics["total_events"]
        assert total_ws_events >= 100, f"Should have generated  >= 100 WebSocket events under stress, got {total_ws_events}"
        assert peak_events >= 10, f"Peak events per second should be  >= 10 under stress, got {peak_events}"
        
        # LLM manager stress metrics
        llm_metrics = mock_llm_manager.stress_metrics
        assert llm_metrics["max_concurrent"] >= 10, f"Should have handled  >= 10 concurrent LLM requests, max was {llm_metrics['max_concurrent']}"
    
    @pytest.mark.asyncio
    async def test_sustained_concurrent_load_memory_leak_detection(self, mock_llm_manager, stress_websocket_manager, 
                                                                 mock_stress_test_agent, stress_test_user_contexts):
        """Test for memory leaks during sustained concurrent load."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(stress_websocket_manager)
        
        # Memory leak detection metrics
        memory_samples = []
        object_counts = []
        
        def sample_memory():
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_samples.append(memory_mb)
            
            # Count objects for leak detection
            gc.collect()  # Force garbage collection
            object_count = len(gc.get_objects())
            object_counts.append(object_count)
            
            return memory_mb, object_count
        
        # Baseline memory measurement
        initial_memory, initial_objects = sample_memory()
        
        # Run multiple rounds of concurrent execution
        rounds = 3
        users_per_round = 8
        
        for round_num in range(rounds):
            print(f"Starting sustained load round {round_num + 1}/{rounds}")
            
            # Create agents for this round
            round_agents = []
            for i in range(users_per_round):
                context_index = (round_num * users_per_round + i) % len(stress_test_user_contexts)
                context = stress_test_user_contexts[context_index]
                
                agent = mock_stress_test_agent()
                registry.get_async = AsyncMock(return_value=agent)
                
                created_agent = await registry.create_agent_for_user(
                    user_id=f"{context.user_id}_round_{round_num}",
                    agent_type=f"leak_test_agent_{round_num}_{i}",
                    user_context=context,
                    websocket_manager=stress_websocket_manager
                )
                
                round_agents.append((created_agent, context))
            
            # Execute agents for this round
            execution_tasks = []
            for agent, context in round_agents:
                stress_input = f"sustained_load_round_{round_num}_data_{context.user_id}"
                task = agent.execute(stress_input, context.run_id)
                execution_tasks.append(task)
            
            # Wait for completion
            round_results = await asyncio.gather(*execution_tasks)
            
            # Cleanup agents for this round
            cleanup_tasks = []
            for agent, context in round_agents:
                cleanup_task = agent.cleanup()
                cleanup_tasks.append(cleanup_task)
            
            await asyncio.gather(*cleanup_tasks)
            
            # Clear references to help garbage collection
            round_agents.clear()
            round_results = None
            
            # Force garbage collection between rounds
            gc.collect()
            await asyncio.sleep(0.1)  # Allow async cleanup to complete
            
            # Sample memory after this round
            current_memory, current_objects = sample_memory()
            print(f"Round {round_num + 1} completed - Memory: {current_memory:.1f}MB, Objects: {current_objects}")
        
        # Final memory measurement
        final_memory, final_objects = sample_memory()
        
        # Memory leak analysis
        memory_growth = final_memory - initial_memory
        object_growth = final_objects - initial_objects
        
        print(f"Memory leak analysis:")
        print(f"  Initial memory: {initial_memory:.1f}MB")
        print(f"  Final memory: {final_memory:.1f}MB")
        print(f"  Memory growth: {memory_growth:.1f}MB")
        print(f"  Initial objects: {initial_objects}")
        print(f"  Final objects: {final_objects}")
        print(f"  Object growth: {object_growth}")
        
        # Memory leak assertions
        # Allow some memory growth but not excessive
        assert memory_growth < 50, f"Memory growth should be <50MB after sustained load, grew {memory_growth:.1f}MB"
        
        # Object count shouldn't grow significantly
        object_growth_percentage = (object_growth / initial_objects) * 100 if initial_objects > 0 else 0
        assert object_growth_percentage < 20, f"Object count growth should be <20%, grew {object_growth_percentage:.1f}%"
        
        # Memory should not continuously grow across rounds
        if len(memory_samples) >= 3:
            # Check that memory growth is not linear (which would indicate a leak)
            early_avg = sum(memory_samples[:2]) / 2
            late_avg = sum(memory_samples[-2:]) / 2
            growth_rate = (late_avg - early_avg) / len(memory_samples)
            assert growth_rate < 5, f"Memory growth rate should be <5MB per round, was {growth_rate:.2f}MB"
    
    @pytest.mark.asyncio
    async def test_websocket_event_throughput_under_stress(self, mock_llm_manager, stress_websocket_manager, 
                                                         mock_stress_test_agent, stress_test_user_contexts):
        """Test WebSocket event throughput and delivery reliability under stress conditions."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(stress_websocket_manager)
        
        # WebSocket stress metrics
        throughput_metrics = {
            "events_generated": 0,
            "events_processed": 0,
            "max_throughput": 0,
            "backpressure_events": 0,
            "delivery_reliability": 0.0,
            "event_latency_samples": []
        }
        
        # Create agents for WebSocket stress testing
        stress_agents = []
        for i, context in enumerate(stress_test_user_contexts[:15]):  # 15 users for WebSocket stress
            agent = mock_stress_test_agent()
            registry.get_async = AsyncMock(return_value=agent)
            
            created_agent = await registry.create_agent_for_user(
                user_id=context.user_id,
                agent_type=f"websocket_stress_agent_{i}",
                user_context=context,
                websocket_manager=stress_websocket_manager
            )
            
            stress_agents.append((created_agent, context))
        
        # Execute agents to generate high WebSocket event throughput
        execution_tasks = []
        for agent, context in stress_agents:
            # Use high complexity to generate more WebSocket events
            context.agent_context["simulated_complexity"] = "extreme"
            context.agent_context["load_factor"] = 2.0
            
            stress_input = type('WebSocketStressInput', (), {
                'data': f"websocket_stress_{context.user_id}",
                'complexity': "extreme",
                'load_factor': 2.0
            })()
            
            task = agent.execute(stress_input, context.run_id)
            execution_tasks.append(task)
        
        # Monitor WebSocket throughput during execution
        async def monitor_websocket_throughput():
            throughput_samples = []
            
            for _ in range(20):  # Monitor for ~10 seconds
                await asyncio.sleep(0.5)
                
                current_throughput = stress_websocket_manager._stress_metrics["events_per_second"]
                throughput_samples.append(current_throughput)
                
                if current_throughput > throughput_metrics["max_throughput"]:
                    throughput_metrics["max_throughput"] = current_throughput
            
            return throughput_samples
        
        # Execute with throughput monitoring
        throughput_task = asyncio.create_task(monitor_websocket_throughput())
        results = await asyncio.gather(*execution_tasks)
        throughput_samples = await throughput_task
        
        # Analyze WebSocket performance
        total_events = stress_websocket_manager._stress_metrics["total_events"]
        backpressure_events = stress_websocket_manager._stress_metrics["backpressure_events"]
        max_events_per_second = stress_websocket_manager._stress_metrics["max_events_per_second"]
        
        throughput_metrics.update({
            "events_generated": total_events,
            "events_processed": total_events - backpressure_events,
            "backpressure_events": backpressure_events,
            "delivery_reliability": (total_events - backpressure_events) / total_events if total_events > 0 else 0,
            "avg_throughput": sum(throughput_samples) / len(throughput_samples) if throughput_samples else 0
        })
        
        # Verify all executions completed successfully under WebSocket stress
        successful_results = [r for r in results if not isinstance(r, Exception) and r.get("status") == "success"]
        assert len(successful_results) >= 12, f"At least 80% should succeed under WebSocket stress, got {len(successful_results)}/15"
        
        # WebSocket throughput assertions
        assert total_events >= 200, f"Should generate  >= 200 WebSocket events under stress, got {total_events}"
        assert max_events_per_second >= 20, f"Peak throughput should be  >= 20 events/sec, got {max_events_per_second}"
        
        # Delivery reliability should remain high even under stress
        reliability = throughput_metrics["delivery_reliability"]
        assert reliability >= 0.95, f"WebSocket delivery reliability should be  >= 95% under stress, got {reliability:.1%}"
        
        # Backpressure should be reasonable
        backpressure_rate = backpressure_events / total_events if total_events > 0 else 0
        assert backpressure_rate < 0.1, f"Backpressure rate should be <10% under stress, got {backpressure_rate:.1%}"
        
        # Average throughput should be sustained
        avg_throughput = throughput_metrics["avg_throughput"]
        assert avg_throughput >= 10, f"Average throughput should be  >= 10 events/sec, got {avg_throughput:.1f}"


# ============================================================================
# TEST: Error Handling and Recovery Under Stress
# ============================================================================

class TestStressErrorHandlingRecovery(SSotBaseTestCase):
    """Test error handling and recovery mechanisms under stress conditions."""
    
    @pytest.mark.asyncio
    async def test_partial_failure_isolation_under_concurrent_stress(self, mock_llm_manager, stress_websocket_manager, 
                                                                   mock_stress_test_agent, stress_test_user_contexts):
        """Test that partial failures are properly isolated during concurrent stress execution."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(stress_websocket_manager)
        
        # Configure mixed success/failure scenario
        success_agents = []
        failure_agents = []
        
        for i, context in enumerate(stress_test_user_contexts[:20]):  # 20 users for failure isolation test
            agent = mock_stress_test_agent()
            
            if i < 12:  # First 12 agents succeed
                success_agents.append((agent, context))
            else:  # Last 8 agents fail under stress
                # Override agent to simulate stress-induced failure
                original_execute = agent.execute
                
                async def stress_failure_execute(state, run_id):
                    # Simulate partial execution before failure
                    if agent._websocket_bridge:
                        await agent._websocket_bridge.notify_agent_started(
                            run_id=agent._run_id,
                            agent_name=agent._agent_name,
                            context={"state": "started", "will_fail_under_stress": True}
                        )
                        
                        await agent._websocket_bridge.notify_agent_thinking(
                            run_id=agent._run_id,
                            agent_name=agent._agent_name,
                            reasoning="Processing under stress before failure",
                            step_number=1,
                            progress_percentage=25.0
                        )
                    
                    # Simulate stress-induced failure after partial progress
                    await asyncio.sleep(0.1)  # Some processing before failure
                    raise Exception(f"Stress-induced failure for user {context.user_id} after partial execution")
                
                agent.execute = stress_failure_execute
                failure_agents.append((agent, context))
        
        # Register all agents
        all_stress_agents = success_agents + failure_agents
        for agent, context in all_stress_agents:
            registry.get_async = AsyncMock(return_value=agent)
            
            created_agent = await registry.create_agent_for_user(
                user_id=context.user_id,
                agent_type="stress_failure_test_agent",
                user_context=context,
                websocket_manager=stress_websocket_manager
            )
            
            # Update agent reference
            if (agent, context) in success_agents:
                index = success_agents.index((agent, context))
                success_agents[index] = (created_agent, context)
            else:
                index = failure_agents.index((agent, context))
                failure_agents[index] = (created_agent, context)
        
        # Execute all agents concurrently under stress
        execution_tasks = []
        for agent, context in all_stress_agents:
            stress_input = f"stress_failure_test_{context.user_id}"
            task = agent.execute(stress_input, context.run_id)
            execution_tasks.append((task, context))
        
        # Execute with failure isolation
        results = await asyncio.gather(*[task for task, _ in execution_tasks], return_exceptions=True)
        
        # Analyze failure isolation
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            context = execution_tasks[i][1]
            
            if isinstance(result, Exception):
                failed_results.append((result, context))
            elif result.get("status") == "success":
                successful_results.append((result, context))
            else:
                failed_results.append((result, context))
        
        # Verify failure isolation
        assert len(successful_results) == 12, f"Should have exactly 12 successful results, got {len(successful_results)}"
        assert len(failed_results) == 8, f"Should have exactly 8 failed results, got {len(failed_results)}"
        
        # Verify that successful executions were not affected by failures
        for result, context in successful_results:
            assert result["status"] == "success"
            assert "execution_metrics" in result
            assert result["execution_metrics"]["execution_time_ms"] > 0
        
        # Verify that failures contain proper error information
        for result, context in failed_results:
            if isinstance(result, Exception):
                assert "stress-induced failure" in str(result).lower()
                assert context.user_id in str(result)
            else:
                assert result.get("status") != "success"
        
        # Verify WebSocket events show proper failure isolation
        async with stress_websocket_manager._buffer_lock:
            all_events = list(stress_websocket_manager._event_buffer)
        
        # Count events by success/failure groups
        success_user_ids = {context.user_id for _, context in successful_results}
        failure_user_ids = {context.user_id for _, context in failed_results}
        
        success_events = [e for e in all_events if e["event"].get("user_id") in success_user_ids]
        failure_events = [e for e in all_events if e["event"].get("user_id") in failure_user_ids]
        
        # Successful users should have completion events
        completion_events = [e for e in success_events if "completed" in str(e["event"]).lower()]
        assert len(completion_events) > 0, "Successful users should have completion events"
        
        # Failed users should not have completion events (they failed mid-execution)
        failed_completion_events = [e for e in failure_events if "completed" in str(e["event"]).lower() and "success" in str(e["event"]).lower()]
        assert len(failed_completion_events) == 0, "Failed users should not have successful completion events"
    
    @pytest.mark.asyncio
    async def test_stress_recovery_after_transient_failures(self, mock_llm_manager, stress_websocket_manager, 
                                                          mock_stress_test_agent, stress_test_user_contexts):
        """Test system recovery after transient failures under stress conditions."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(stress_websocket_manager)
        
        # Recovery metrics tracking
        recovery_metrics = {
            "initial_failures": 0,
            "recovery_attempts": 0,
            "successful_recoveries": 0,
            "persistent_failures": 0,
            "recovery_time_samples": []
        }
        
        # Create agents with transient failure simulation
        recovery_test_agents = []
        
        for i, context in enumerate(stress_test_user_contexts[:10]):  # 10 users for recovery test
            agent = mock_stress_test_agent()
            
            # Add transient failure logic
            agent._failure_count = 0
            agent._max_failures = 2  # Fail first 2 attempts, then succeed
            
            original_execute = agent.execute
            
            async def transient_failure_execute(state, run_id):
                agent._failure_count += 1
                
                # Simulate transient failures
                if agent._failure_count <= agent._max_failures:
                    recovery_metrics["initial_failures"] += 1
                    
                    if agent._websocket_bridge:
                        await agent._websocket_bridge.notify_agent_started(
                            run_id=agent._run_id,
                            agent_name=agent._agent_name,
                            context={"state": "started", "attempt": agent._failure_count, "will_fail_transiently": True}
                        )
                    
                    # Simulate brief processing before transient failure
                    await asyncio.sleep(0.05)
                    raise Exception(f"Transient failure #{agent._failure_count} for {context.user_id}")
                
                # After max failures, execute successfully
                return await original_execute(state, run_id)
            
            agent.execute = transient_failure_execute
            recovery_test_agents.append((agent, context))
        
        # Register agents
        for agent, context in recovery_test_agents:
            registry.get_async = AsyncMock(return_value=agent)
            
            created_agent = await registry.create_agent_for_user(
                user_id=context.user_id,
                agent_type="recovery_test_agent",
                user_context=context,
                websocket_manager=stress_websocket_manager
            )
            
            # Update reference
            index = recovery_test_agents.index((agent, context))
            recovery_test_agents[index] = (created_agent, context)
        
        # Simulate recovery attempts (retry failed executions)
        final_results = []
        
        for agent, context in recovery_test_agents:
            attempts = 0
            max_attempts = 5
            
            while attempts < max_attempts:
                attempts += 1
                recovery_metrics["recovery_attempts"] += 1
                
                try:
                    recovery_start = time.time()
                    result = await agent.execute(f"recovery_test_data_{context.user_id}", context.run_id)
                    recovery_time = time.time() - recovery_start
                    
                    recovery_metrics["recovery_time_samples"].append(recovery_time)
                    recovery_metrics["successful_recoveries"] += 1
                    final_results.append((result, context, attempts))
                    break
                    
                except Exception as e:
                    if attempts == max_attempts:
                        recovery_metrics["persistent_failures"] += 1
                        final_results.append((e, context, attempts))
                    else:
                        # Wait before retry (simulating backoff)
                        await asyncio.sleep(0.1 * attempts)
        
        # Analyze recovery results
        successful_recoveries = [r for r, c, a in final_results if not isinstance(r, Exception)]
        persistent_failures = [r for r, c, a in final_results if isinstance(r, Exception)]
        
        # Recovery assertions
        assert len(successful_recoveries) == 10, f"All agents should eventually succeed after recovery, got {len(successful_recoveries)}/10"
        assert len(persistent_failures) == 0, f"Should have no persistent failures after recovery, got {len(persistent_failures)}"
        
        # Verify recovery metrics
        assert recovery_metrics["successful_recoveries"] == 10, "Should have 10 successful recoveries"
        assert recovery_metrics["initial_failures"] == 20, "Should have 20 initial failures (2 per agent)"
        assert recovery_metrics["persistent_failures"] == 0, "Should have no persistent failures"
        
        # Recovery time should be reasonable
        if recovery_metrics["recovery_time_samples"]:
            avg_recovery_time = sum(recovery_metrics["recovery_time_samples"]) / len(recovery_metrics["recovery_time_samples"])
            assert avg_recovery_time < 2.0, f"Average recovery time should be <2s, got {avg_recovery_time:.2f}s"
        
        # Verify that all final results show successful execution
        for result, context, attempts in final_results:
            if not isinstance(result, Exception):
                assert result["status"] == "success"
                assert attempts >= 3, f"Should have required at least 3 attempts for recovery, got {attempts}"


if __name__ == "__main__":
    # Run stress tests with extended timeouts and detailed reporting
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=2", "-s", "--timeout=60"])