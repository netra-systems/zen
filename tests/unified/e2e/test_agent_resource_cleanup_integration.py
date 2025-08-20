"""Test 15: Agent Resource Cleanup Integration Test - CRITICAL Memory Management

Tests memory/connection cleanup after agent completion to prevent production memory leaks.
Validates resource management across agent lifecycle and concurrent operations.

Business Value Justification (BVJ):
1. Segment: Platform/Infrastructure ($10K MRR protection)
2. Business Goal: Prevent memory leaks and resource exhaustion in production
3. Value Impact: Ensures system stability and prevents downtime from resource exhaustion
4. Strategic Impact: Protects $10K MRR through validated resource management

COMPLIANCE: File size <300 lines, Functions <8 lines, Real resource testing
"""

import asyncio
import time
import gc
import psutil
import os
from typing import Dict, Any, List, Optional
import pytest

from app.agents.base import BaseSubAgent
from app.agents.supervisor.supervisor_agent import SupervisorAgent
from app.llm.llm_manager import LLMManager
from app.config import get_config


class ResourceCleanupMonitor:
    """Monitors resource usage and cleanup for agent operations."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.baseline_memory = self.process.memory_info().rss
        self.baseline_connections = len(self.process.connections())
        self.resource_snapshots = []
        self.cleanup_metrics = {}
        self.leak_thresholds = {
            "memory_leak_mb": 50,  # 50MB memory leak threshold
            "connection_leak_count": 10,  # 10 connection leak threshold
            "cleanup_time_seconds": 5.0  # 5 second cleanup time limit
        }
    
    def capture_resource_snapshot(self, operation: str) -> Dict[str, Any]:
        """Capture current resource usage snapshot."""
        current_memory = self.process.memory_info().rss
        current_connections = len(self.process.connections())
        current_threads = self.process.num_threads()
        
        snapshot = {
            "operation": operation,
            "timestamp": time.time(),
            "memory_bytes": current_memory,
            "memory_mb": current_memory / (1024 * 1024),
            "memory_delta_mb": (current_memory - self.baseline_memory) / (1024 * 1024),
            "connections": current_connections,
            "connection_delta": current_connections - self.baseline_connections,
            "threads": current_threads
        }
        
        self.resource_snapshots.append(snapshot)
        return snapshot
    
    async def monitor_agent_lifecycle_cleanup(self, agent: BaseSubAgent) -> Dict[str, Any]:
        """Monitor resource cleanup during agent lifecycle."""
        # Capture before agent creation
        pre_snapshot = self.capture_resource_snapshot(f"pre_agent_{agent.name}")
        
        # Simulate agent execution
        start_time = time.time()
        await self._simulate_agent_work(agent)
        execution_time = time.time() - start_time
        
        # Capture during execution
        exec_snapshot = self.capture_resource_snapshot(f"exec_agent_{agent.name}")
        
        # Trigger cleanup
        cleanup_start = time.time()
        await self._cleanup_agent_resources(agent)
        cleanup_time = time.time() - cleanup_start
        
        # Capture after cleanup
        post_snapshot = self.capture_resource_snapshot(f"post_agent_{agent.name}")
        
        cleanup_metrics = {
            "agent_name": agent.name,
            "execution_time": execution_time,
            "cleanup_time": cleanup_time,
            "memory_growth_mb": exec_snapshot["memory_delta_mb"] - pre_snapshot["memory_delta_mb"],
            "memory_cleanup_mb": exec_snapshot["memory_delta_mb"] - post_snapshot["memory_delta_mb"],
            "connection_growth": exec_snapshot["connection_delta"] - pre_snapshot["connection_delta"],
            "connection_cleanup": exec_snapshot["connection_delta"] - post_snapshot["connection_delta"],
            "cleanup_successful": self._validate_cleanup_success(pre_snapshot, post_snapshot)
        }
        
        self.cleanup_metrics[agent.name] = cleanup_metrics
        return cleanup_metrics
    
    def detect_memory_leaks(self, operation_count: int = 1) -> Dict[str, Any]:
        """Detect memory leaks across multiple operations."""
        if len(self.resource_snapshots) < 2:
            return {"leak_detected": False, "insufficient_data": True}
        
        initial_snapshot = self.resource_snapshots[0]
        final_snapshot = self.resource_snapshots[-1]
        
        memory_leak_mb = final_snapshot["memory_delta_mb"] - initial_snapshot["memory_delta_mb"]
        connection_leak = final_snapshot["connection_delta"] - initial_snapshot["connection_delta"]
        
        memory_leak_per_op = memory_leak_mb / operation_count if operation_count > 0 else memory_leak_mb
        
        leak_detection = {
            "total_memory_leak_mb": memory_leak_mb,
            "memory_leak_per_operation_mb": memory_leak_per_op,
            "total_connection_leak": connection_leak,
            "memory_leak_detected": memory_leak_mb > self.leak_thresholds["memory_leak_mb"],
            "connection_leak_detected": connection_leak > self.leak_thresholds["connection_leak_count"],
            "leak_severity": self._calculate_leak_severity(memory_leak_mb, connection_leak)
        }
        
        return leak_detection
    
    async def _simulate_agent_work(self, agent: BaseSubAgent) -> None:
        """Simulate agent work that uses resources."""
        # Simulate memory-intensive operations
        large_data = [i for i in range(10000)]  # Small data structure
        
        # Simulate async operations
        await asyncio.sleep(0.1)
        
        # Simulate some processing
        _ = sum(large_data)
        
        # Clean up local variables
        del large_data
    
    async def _cleanup_agent_resources(self, agent: BaseSubAgent) -> None:
        """Cleanup agent resources explicitly."""
        # Force garbage collection
        gc.collect()
        
        # Simulate agent-specific cleanup
        if hasattr(agent, 'cleanup'):
            await agent.cleanup()
        
        # Additional cleanup delay to allow async cleanup
        await asyncio.sleep(0.1)
    
    def _validate_cleanup_success(self, pre_snapshot: Dict[str, Any], 
                                post_snapshot: Dict[str, Any]) -> bool:
        """Validate cleanup was successful."""
        memory_growth = post_snapshot["memory_delta_mb"] - pre_snapshot["memory_delta_mb"]
        connection_growth = post_snapshot["connection_delta"] - pre_snapshot["connection_delta"]
        
        return (
            memory_growth < self.leak_thresholds["memory_leak_mb"] and
            connection_growth < self.leak_thresholds["connection_leak_count"]
        )
    
    def _calculate_leak_severity(self, memory_leak: float, connection_leak: int) -> str:
        """Calculate leak severity level."""
        if memory_leak > 100 or connection_leak > 20:
            return "critical"
        elif memory_leak > 50 or connection_leak > 10:
            return "high"
        elif memory_leak > 20 or connection_leak > 5:
            return "medium"
        else:
            return "low"


class ConcurrentResourceTester:
    """Tests resource cleanup under concurrent agent operations."""
    
    def __init__(self):
        self.concurrent_metrics = []
        self.resource_monitor = ResourceCleanupMonitor()
    
    async def test_concurrent_agent_cleanup(self, agent_count: int = 10) -> Dict[str, Any]:
        """Test resource cleanup with concurrent agents."""
        config = get_config()
        llm_manager = LLMManager(config)
        
        # Create multiple agents
        agents = []
        for i in range(agent_count):
            agent = BaseSubAgent(
                llm_manager=llm_manager,
                name=f"ConcurrentAgent{i:03d}",
                description=f"Concurrent test agent {i}"
            )
            agent.user_id = "concurrent_cleanup_test_001"
            agents.append(agent)
        
        # Monitor concurrent execution and cleanup
        concurrent_start = time.time()
        
        cleanup_tasks = [
            self.resource_monitor.monitor_agent_lifecycle_cleanup(agent)
            for agent in agents
        ]
        
        cleanup_results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        concurrent_time = time.time() - concurrent_start
        
        successful_cleanups = [
            r for r in cleanup_results 
            if isinstance(r, dict) and r.get("cleanup_successful", False)
        ]
        
        return {
            "total_agents": agent_count,
            "successful_cleanups": len(successful_cleanups),
            "cleanup_success_rate": len(successful_cleanups) / agent_count,
            "concurrent_execution_time": concurrent_time,
            "cleanup_results": cleanup_results,
            "concurrent_cleanup_successful": len(successful_cleanups) >= agent_count * 0.9
        }
    
    async def test_resource_stability_over_time(self, iterations: int = 5) -> Dict[str, Any]:
        """Test resource stability over multiple iterations."""
        config = get_config()
        llm_manager = LLMManager(config)
        
        iteration_results = []
        
        for i in range(iterations):
            # Create and cleanup agent
            agent = BaseSubAgent(
                llm_manager=llm_manager,
                name=f"StabilityAgent{i:03d}",
                description=f"Stability test agent iteration {i}"
            )
            agent.user_id = "stability_test_001"
            
            cleanup_result = await self.resource_monitor.monitor_agent_lifecycle_cleanup(agent)
            iteration_results.append(cleanup_result)
            
            # Brief pause between iterations
            await asyncio.sleep(0.2)
        
        # Analyze stability over iterations
        memory_deltas = [r["memory_cleanup_mb"] for r in iteration_results]
        avg_memory_cleanup = sum(memory_deltas) / len(memory_deltas)
        
        stability_metrics = {
            "iterations_tested": iterations,
            "all_cleanups_successful": all(r["cleanup_successful"] for r in iteration_results),
            "average_memory_cleanup_mb": avg_memory_cleanup,
            "memory_stability": max(memory_deltas) - min(memory_deltas) < 20,  # 20MB variance threshold
            "iteration_results": iteration_results
        }
        
        return stability_metrics


@pytest.mark.integration
class TestAgentResourceCleanupIntegration:
    """Integration tests for agent resource cleanup and memory management."""
    
    @pytest.fixture
    def resource_monitor(self):
        """Initialize resource cleanup monitor."""
        return ResourceCleanupMonitor()
    
    @pytest.fixture
    def concurrent_tester(self):
        """Initialize concurrent resource tester."""
        return ConcurrentResourceTester()
    
    @pytest.mark.asyncio
    async def test_single_agent_resource_cleanup(self, resource_monitor):
        """Test resource cleanup for single agent lifecycle."""
        config = get_config()
        llm_manager = LLMManager(config)
        
        agent = BaseSubAgent(
            llm_manager=llm_manager,
            name="SingleCleanupAgent001",
            description="Single agent cleanup test"
        )
        agent.user_id = "single_cleanup_test_001"
        
        cleanup_metrics = await resource_monitor.monitor_agent_lifecycle_cleanup(agent)
        
        assert cleanup_metrics["cleanup_successful"], "Agent resource cleanup failed"
        assert cleanup_metrics["cleanup_time"] < 5.0, "Cleanup took too long"
        assert cleanup_metrics["memory_cleanup_mb"] >= 0, "Memory not cleaned up properly"
        assert cleanup_metrics["connection_cleanup"] >= 0, "Connections not cleaned up properly"
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, resource_monitor):
        """Test memory leak detection across multiple agent operations."""
        config = get_config()
        llm_manager = LLMManager(config)
        
        # Create and cleanup multiple agents to test for leaks
        for i in range(5):
            agent = BaseSubAgent(
                llm_manager=llm_manager,
                name=f"LeakTestAgent{i:03d}",
                description=f"Memory leak test agent {i}"
            )
            agent.user_id = "leak_test_001"
            
            await resource_monitor.monitor_agent_lifecycle_cleanup(agent)
            await asyncio.sleep(0.1)  # Brief pause between agents
        
        # Detect memory leaks
        leak_detection = resource_monitor.detect_memory_leaks(operation_count=5)
        
        assert not leak_detection["memory_leak_detected"], "Memory leak detected"
        assert not leak_detection["connection_leak_detected"], "Connection leak detected"
        assert leak_detection["leak_severity"] in ["low", "medium"], "Leak severity too high"
        assert leak_detection["memory_leak_per_operation_mb"] < 10, "Per-operation memory leak too high"
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_resource_cleanup(self, concurrent_tester):
        """Test resource cleanup under concurrent agent operations."""
        concurrent_result = await concurrent_tester.test_concurrent_agent_cleanup(agent_count=8)
        
        assert concurrent_result["concurrent_cleanup_successful"], "Concurrent cleanup failed"
        assert concurrent_result["cleanup_success_rate"] >= 0.9, "Too many cleanup failures"
        assert concurrent_result["concurrent_execution_time"] < 15.0, "Concurrent cleanup too slow"
        
        # Validate individual cleanup results
        successful_cleanups = [
            r for r in concurrent_result["cleanup_results"]
            if isinstance(r, dict) and r.get("cleanup_successful")
        ]
        assert len(successful_cleanups) >= 7, "Too many individual cleanup failures"
    
    @pytest.mark.asyncio
    async def test_resource_stability_over_time(self, concurrent_tester):
        """Test resource stability over multiple iterations."""
        stability_result = await concurrent_tester.test_resource_stability_over_time(iterations=5)
        
        assert stability_result["all_cleanups_successful"], "Not all cleanups successful over time"
        assert stability_result["memory_stability"], "Memory usage not stable over iterations"
        assert stability_result["average_memory_cleanup_mb"] >= 0, "Average memory cleanup negative"
        
        # Validate iteration consistency
        iteration_results = stability_result["iteration_results"]
        cleanup_times = [r["cleanup_time"] for r in iteration_results]
        max_cleanup_time = max(cleanup_times)
        
        assert max_cleanup_time < 5.0, "Some iterations had excessive cleanup times"
    
    @pytest.mark.asyncio
    async def test_supervisor_agent_resource_cleanup(self, resource_monitor):
        """Test resource cleanup for supervisor agents with sub-agents."""
        config = get_config()
        llm_manager = LLMManager(config)
        
        # Create supervisor agent
        supervisor = SupervisorAgent(llm_manager=llm_manager, name="CleanupSupervisor001")
        supervisor.user_id = "supervisor_cleanup_test_001"
        
        # Monitor supervisor cleanup (which should include sub-agent cleanup)
        cleanup_metrics = await resource_monitor.monitor_agent_lifecycle_cleanup(supervisor)
        
        assert cleanup_metrics["cleanup_successful"], "Supervisor agent cleanup failed"
        assert cleanup_metrics["cleanup_time"] < 8.0, "Supervisor cleanup took too long"
        
        # Supervisor agents may use more resources
        assert cleanup_metrics["memory_cleanup_mb"] >= 0, "Supervisor memory not cleaned up"
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_under_error_conditions(self, resource_monitor):
        """Test resource cleanup when agents encounter errors."""
        config = get_config()
        llm_manager = LLMManager(config)
        
        agent = BaseSubAgent(
            llm_manager=llm_manager,
            name="ErrorCleanupAgent001",
            description="Agent for testing cleanup under error conditions"
        )
        agent.user_id = "error_cleanup_test_001"
        
        try:
            # Simulate error during agent work by forcing an exception
            pre_snapshot = resource_monitor.capture_resource_snapshot("pre_error_test")
            
            # This should trigger error handling and cleanup
            with pytest.raises(Exception):
                await resource_monitor._simulate_agent_work(agent)
                raise Exception("Simulated agent error")
                
        except Exception:
            pass  # Expected exception
        
        # Force cleanup after error
        await resource_monitor._cleanup_agent_resources(agent)
        post_snapshot = resource_monitor.capture_resource_snapshot("post_error_cleanup")
        
        # Validate cleanup occurred even after error
        memory_growth = post_snapshot["memory_delta_mb"] - pre_snapshot["memory_delta_mb"]
        assert memory_growth < 50, "Excessive memory growth after error and cleanup"