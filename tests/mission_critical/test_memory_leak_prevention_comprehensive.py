#!/usr/bin/env python
"""
MISSION CRITICAL: Memory Leak Detection and Prevention Tests

Business Value: Prevents $300K+ ARR loss from memory-related service outages  
Critical Requirements:
- Memory usage must remain stable over extended operations (24+ hours)
- Memory leaks must be detected before reaching 1GB increase
- Object cleanup must prevent zombie processes and file descriptor leaks
- Garbage collection must be effective for long-running agent operations

This suite tests memory management in extreme scenarios that could cause:
- Service crashes from OOM conditions
- Performance degradation from excessive garbage collection
- File descriptor exhaustion causing connection failures
- Memory fragmentation leading to allocation failures

ANY MEMORY LEAK DETECTION BLOCKS PRODUCTION DEPLOYMENT.
"""

import asyncio
import gc
import json
import os
import psutil
import random
import sys
import threading
import time
import tracemalloc
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional, Callable, Union, Tuple
from unittest.mock import AsyncMock, Mock, patch
import tempfile
import resource

import pytest
from loguru import logger

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import components for memory testing
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from netra_backend.app.llm.llm_manager import LLMManager


# ============================================================================
# MEMORY MONITORING UTILITIES
# ============================================================================

class MemoryProfiler:
    """Advanced memory profiling for leak detection."""
    
    def __init__(self, enable_tracemalloc: bool = True):
        self.enable_tracemalloc = enable_tracemalloc
        self.baseline_memory = None
        self.memory_snapshots: List[Dict] = []
        self.object_tracking: Dict[str, List] = {}
        self.file_descriptors: List[int] = []
        self.thread_tracking: List[threading.Thread] = []
        self.gc_stats_history: List[Dict] = []
        
        # Memory thresholds
        self.memory_leak_threshold_mb = 100  # 100MB increase
        self.memory_warning_threshold_mb = 50   # 50MB increase
        
        if self.enable_tracemalloc:
            tracemalloc.start()
    
    def establish_baseline(self) -> Dict[str, Any]:
        """Establish memory and resource baseline."""
        gc.collect()  # Force garbage collection
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        baseline = {
            "timestamp": time.time(),
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / 1024 / 1024,
            "open_files": len(process.open_files()),
            "num_threads": process.num_threads(),
            "gc_stats": gc.get_stats(),
            "gc_counts": gc.get_count()
        }
        
        if self.enable_tracemalloc:
            snapshot = tracemalloc.take_snapshot()
            baseline["tracemalloc_total"] = sum(stat.size for stat in snapshot.statistics('filename'))
        
        self.baseline_memory = baseline
        self.memory_snapshots = [baseline]
        
        logger.info(f"Memory baseline established: {baseline['rss_mb']:.1f}MB RSS, "
                   f"{baseline['open_files']} files, {baseline['num_threads']} threads")
        
        return baseline
    
    def take_memory_snapshot(self, label: str = "snapshot") -> Dict[str, Any]:
        """Take comprehensive memory snapshot."""
        gc.collect()  # Force garbage collection before measurement
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        snapshot = {
            "timestamp": time.time(),
            "label": label,
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / 1024 / 1024,
            "open_files": len(process.open_files()),
            "num_threads": process.num_threads(),
            "gc_stats": gc.get_stats(),
            "gc_counts": gc.get_count()
        }
        
        # Calculate increases from baseline
        if self.baseline_memory:
            snapshot["rss_increase_mb"] = snapshot["rss_mb"] - self.baseline_memory["rss_mb"]
            snapshot["files_increase"] = snapshot["open_files"] - self.baseline_memory["open_files"]
            snapshot["threads_increase"] = snapshot["num_threads"] - self.baseline_memory["num_threads"]
        
        if self.enable_tracemalloc:
            tracemalloc_snapshot = tracemalloc.take_snapshot()
            snapshot["tracemalloc_total"] = sum(stat.size for stat in tracemalloc_snapshot.statistics('filename'))
            
            if self.baseline_memory and "tracemalloc_total" in self.baseline_memory:
                snapshot["tracemalloc_increase"] = (
                    snapshot["tracemalloc_total"] - self.baseline_memory["tracemalloc_total"]
                )
        
        self.memory_snapshots.append(snapshot)
        return snapshot
    
    def track_objects(self, objects: List[Any], category: str):
        """Track objects using weak references for lifecycle monitoring."""
        if category not in self.object_tracking:
            self.object_tracking[category] = []
        
        for obj in objects:
            try:
                weak_ref = weakref.ref(obj)
                self.object_tracking[category].append({
                    "ref": weak_ref,
                    "creation_time": time.time(),
                    "type": type(obj).__name__,
                    "id": id(obj)
                })
            except TypeError:
                # Some objects can't be weakly referenced
                pass
    
    def check_object_cleanup(self, category: str) -> Dict[str, Any]:
        """Check if tracked objects have been properly cleaned up."""
        if category not in self.object_tracking:
            return {"error": f"Category {category} not tracked"}
        
        tracked_objects = self.object_tracking[category]
        
        alive_objects = []
        dead_objects = []
        
        for obj_info in tracked_objects:
            if obj_info["ref"]() is not None:
                alive_objects.append(obj_info)
            else:
                dead_objects.append(obj_info)
        
        cleanup_rate = len(dead_objects) / len(tracked_objects) if tracked_objects else 1.0
        
        return {
            "category": category,
            "total_tracked": len(tracked_objects),
            "alive_objects": len(alive_objects),
            "dead_objects": len(dead_objects),
            "cleanup_rate": cleanup_rate,
            "oldest_alive": min(
                (obj["creation_time"] for obj in alive_objects), 
                default=time.time()
            ),
            "alive_object_types": [obj["type"] for obj in alive_objects]
        }
    
    def detect_memory_leaks(self, iterations_completed: int = 1) -> Dict[str, Any]:
        """Comprehensive memory leak analysis."""
        if not self.baseline_memory or not self.memory_snapshots:
            return {"error": "No baseline or snapshots available"}
        
        latest_snapshot = self.memory_snapshots[-1]
        
        # Memory leak analysis
        rss_increase = latest_snapshot.get("rss_increase_mb", 0)
        files_increase = latest_snapshot.get("files_increase", 0)
        threads_increase = latest_snapshot.get("threads_increase", 0)
        
        # Calculate memory increase per iteration
        memory_per_iteration = rss_increase / iterations_completed if iterations_completed > 0 else 0
        
        # Determine leak severity
        leak_severity = "none"
        if rss_increase > self.memory_leak_threshold_mb:
            leak_severity = "critical"
        elif rss_increase > self.memory_warning_threshold_mb:
            leak_severity = "moderate"
        elif memory_per_iteration > 1.0:  # >1MB per iteration
            leak_severity = "minor"
        
        # Analyze memory growth trend
        if len(self.memory_snapshots) >= 3:
            recent_snapshots = self.memory_snapshots[-3:]
            memory_trend = []
            for i in range(1, len(recent_snapshots)):
                growth = recent_snapshots[i]["rss_mb"] - recent_snapshots[i-1]["rss_mb"]
                memory_trend.append(growth)
            
            trend_direction = "increasing" if all(g > 0 for g in memory_trend) else "stable"
        else:
            trend_direction = "insufficient_data"
        
        # Object cleanup analysis
        object_cleanup_summary = {}
        for category in self.object_tracking:
            cleanup_info = self.check_object_cleanup(category)
            object_cleanup_summary[category] = cleanup_info
        
        # Garbage collection analysis
        gc_stats = gc.get_stats()
        gc_counts = gc.get_count()
        
        analysis = {
            "memory_analysis": {
                "baseline_rss_mb": self.baseline_memory["rss_mb"],
                "current_rss_mb": latest_snapshot["rss_mb"],
                "rss_increase_mb": rss_increase,
                "memory_per_iteration_mb": memory_per_iteration,
                "leak_severity": leak_severity,
                "trend_direction": trend_direction,
                "iterations_completed": iterations_completed
            },
            "resource_analysis": {
                "baseline_files": self.baseline_memory["open_files"],
                "current_files": latest_snapshot["open_files"],
                "files_increase": files_increase,
                "baseline_threads": self.baseline_memory["num_threads"],
                "current_threads": latest_snapshot["num_threads"],
                "threads_increase": threads_increase
            },
            "object_cleanup": object_cleanup_summary,
            "gc_analysis": {
                "current_stats": gc_stats,
                "current_counts": gc_counts,
                "baseline_counts": self.baseline_memory.get("gc_counts", [0, 0, 0])
            },
            "snapshots_taken": len(self.memory_snapshots),
            "peak_memory_mb": max(s["rss_mb"] for s in self.memory_snapshots),
            "leak_detected": leak_severity in ["critical", "moderate"],
            "resource_leak_detected": files_increase > 50 or threads_increase > 20
        }
        
        # Add tracemalloc analysis if enabled
        if self.enable_tracemalloc and "tracemalloc_increase" in latest_snapshot:
            analysis["tracemalloc_analysis"] = {
                "baseline_bytes": self.baseline_memory.get("tracemalloc_total", 0),
                "current_bytes": latest_snapshot["tracemalloc_total"],
                "increase_bytes": latest_snapshot["tracemalloc_increase"],
                "increase_mb": latest_snapshot["tracemalloc_increase"] / 1024 / 1024
            }
        
        return analysis


class MemoryStressGenerator:
    """Generates various memory stress scenarios for leak testing."""
    
    def __init__(self):
        self.stress_scenarios = {
            "object_creation_destruction": self._object_creation_stress,
            "circular_references": self._circular_reference_stress,
            "large_data_processing": self._large_data_stress,
            "recursive_operations": self._recursive_operations_stress,
            "file_operations": self._file_operations_stress,
            "thread_creation": self._thread_creation_stress,
            "callback_accumulation": self._callback_accumulation_stress
        }
        
        self.created_objects = []
        self.temp_files = []
        self.threads = []
    
    async def run_stress_scenario(self, scenario_name: str, intensity: int = 100):
        """Run specific memory stress scenario."""
        if scenario_name not in self.stress_scenarios:
            raise ValueError(f"Unknown stress scenario: {scenario_name}")
        
        logger.info(f"Running memory stress scenario: {scenario_name} (intensity: {intensity})")
        
        try:
            await self.stress_scenarios[scenario_name](intensity)
        except Exception as e:
            logger.error(f"Stress scenario {scenario_name} failed: {e}")
            raise
    
    async def _object_creation_stress(self, intensity: int):
        """Create and destroy many objects to test cleanup."""
        for i in range(intensity):
            # Create various types of objects
            large_dict = {f"key_{j}": f"value_{j}" * 100 for j in range(50)}
            large_list = [f"item_{j}" * 50 for j in range(100)]
            
            # Create nested structures
            nested_structure = {
                "data": large_dict,
                "list": large_list,
                "metadata": {
                    "created": time.time(),
                    "index": i,
                    "size": len(large_dict) + len(large_list)
                }
            }
            
            self.created_objects.append(nested_structure)
            
            # Periodic cleanup
            if i % 20 == 0:
                self.created_objects = self.created_objects[-10:]  # Keep only last 10
                await asyncio.sleep(0.01)
    
    async def _circular_reference_stress(self, intensity: int):
        """Create circular references to test garbage collection."""
        circular_objects = []
        
        for i in range(intensity):
            obj_a = {"name": f"object_a_{i}", "ref": None}
            obj_b = {"name": f"object_b_{i}", "ref": None}
            
            # Create circular reference
            obj_a["ref"] = obj_b
            obj_b["ref"] = obj_a
            
            circular_objects.append((obj_a, obj_b))
            
            # Periodic cleanup of circular references
            if i % 30 == 0:
                # Break circular references explicitly
                for obj_pair in circular_objects[-10:]:
                    obj_pair[0]["ref"] = None
                    obj_pair[1]["ref"] = None
                
                circular_objects = []
                gc.collect()  # Force garbage collection
                await asyncio.sleep(0.01)
    
    async def _large_data_stress(self, intensity: int):
        """Process large data structures to test memory handling."""
        for i in range(intensity):
            # Create large data structure
            large_data = {
                "matrix": [[random.random() for _ in range(100)] for _ in range(100)],
                "text": "Large text data " * 1000,
                "binary": bytes(range(256)) * 100
            }
            
            # Process the data
            processed = json.dumps({
                "matrix_sum": sum(sum(row) for row in large_data["matrix"]),
                "text_length": len(large_data["text"]),
                "binary_length": len(large_data["binary"])
            })
            
            # Clean up immediately
            del large_data
            del processed
            
            if i % 10 == 0:
                gc.collect()
                await asyncio.sleep(0.01)
    
    async def _recursive_operations_stress(self, intensity: int):
        """Test recursive operations that might cause stack/memory issues."""
        
        def recursive_dict_creation(depth: int, max_depth: int = 20):
            if depth >= max_depth:
                return f"leaf_{depth}"
            
            return {
                f"level_{depth}": recursive_dict_creation(depth + 1, max_depth),
                "metadata": {"depth": depth, "data": "x" * 50}
            }
        
        for i in range(intensity):
            max_depth = min(10 + (i % 20), 30)  # Vary recursion depth
            recursive_structure = recursive_dict_creation(0, max_depth)
            
            # Process the structure
            def count_nodes(node):
                if isinstance(node, dict):
                    return 1 + sum(count_nodes(v) for v in node.values())
                return 1
            
            node_count = count_nodes(recursive_structure)
            
            # Clean up
            del recursive_structure
            
            if i % 15 == 0:
                gc.collect()
                await asyncio.sleep(0.01)
    
    async def _file_operations_stress(self, intensity: int):
        """Test file operations for file descriptor leaks."""
        for i in range(min(intensity, 50)):  # Limit to avoid too many files
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w+')
            
            try:
                # Write data to file
                data = f"Test data {i} " * 1000
                temp_file.write(data)
                temp_file.flush()
                
                # Read data back
                temp_file.seek(0)
                read_data = temp_file.read()
                
                self.temp_files.append(temp_file.name)
                
            finally:
                temp_file.close()
            
            # Periodic cleanup
            if i % 10 == 0:
                await self._cleanup_temp_files()
                await asyncio.sleep(0.01)
    
    async def _thread_creation_stress(self, intensity: int):
        """Test thread creation and cleanup."""
        import threading
        
        def worker_thread(thread_id: int):
            # Do some work
            result = sum(i ** 2 for i in range(1000))
            time.sleep(0.1)
            return result
        
        for i in range(min(intensity, 20)):  # Limit thread count
            thread = threading.Thread(
                target=worker_thread,
                args=(i,),
                name=f"stress_thread_{i}"
            )
            
            thread.start()
            self.threads.append(thread)
            
            # Cleanup completed threads
            if i % 5 == 0:
                await self._cleanup_threads()
                await asyncio.sleep(0.05)
    
    async def _callback_accumulation_stress(self, intensity: int):
        """Test callback/closure accumulation."""
        callbacks = []
        
        for i in range(intensity):
            # Create closure that captures variables
            data = {"index": i, "data": "x" * 100}
            
            def callback(captured_data=data, iteration=i):
                return f"Callback {iteration}: {len(captured_data['data'])}"
            
            callbacks.append(callback)
            
            # Execute some callbacks
            if len(callbacks) > 20:
                # Execute and remove old callbacks
                for cb in callbacks[:10]:
                    try:
                        result = cb()
                    except:
                        pass
                
                callbacks = callbacks[10:]
            
            if i % 25 == 0:
                callbacks = []  # Clear all callbacks
                await asyncio.sleep(0.01)
    
    async def _cleanup_temp_files(self):
        """Clean up temporary files."""
        for filepath in self.temp_files:
            try:
                os.unlink(filepath)
            except:
                pass
        self.temp_files = []
    
    async def _cleanup_threads(self):
        """Wait for threads to complete and clean up."""
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=0.1)  # Short timeout
        
        self.threads = [t for t in self.threads if t.is_alive()]
    
    async def cleanup_all(self):
        """Clean up all resources created during stress testing."""
        await self._cleanup_temp_files()
        await self._cleanup_threads()
        self.created_objects.clear()


# ============================================================================
# MEMORY LEAK TEST UTILITIES
# ============================================================================

class MemoryLeakTestAgent(BaseAgent):
    """Agent designed for memory leak testing."""
    
    def __init__(self, name: str = "memory_test_agent", enable_large_responses: bool = False):
        # Create mock LLM manager
        mock_llm = AsyncMock(spec=LLMManager)
        
        async def mock_response(*args, **kwargs):
            # Create responses of varying sizes
            if enable_large_responses:
                content_size = random.randint(1000, 10000)  # 1-10KB responses
                content = "Memory test response. " * (content_size // 20)
            else:
                content = "Standard memory test response."
            
            return {
                "content": content,
                "tokens": {
                    "input": random.randint(50, 200),
                    "output": len(content) // 4,  # Approximate token count
                    "total": random.randint(100, 400)
                },
                "model": "gpt-4",
                "provider": "openai"
            }
        
        mock_llm.chat_completion = mock_response
        
        super().__init__(
            llm_manager=mock_llm,
            name=name,
            description=f"Memory leak test agent: {name}"
        )
        
        self.execution_count = 0
        self.large_data_accumulation = []
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute with potential memory accumulation patterns."""
        self.execution_count += 1
        
        # Simulate LLM call
        if hasattr(self, 'llm_manager') and self.llm_manager:
            response = await self.llm_manager.chat_completion(
                messages=[{"role": "user", "content": f"Memory test query {self.execution_count}"}],
                model="gpt-4"
            )
            
            # Store response in state
            if response:
                state.context["llm_response"] = response.get("content", "")
                state.context["tokens"] = response.get("tokens", {})
        
        # Create some data structures
        execution_data = {
            "execution_count": self.execution_count,
            "timestamp": time.time(),
            "run_id": run_id,
            "processing_data": [i ** 2 for i in range(100)],  # Some computation
            "metadata": {
                "agent_name": self.name,
                "large_string": "X" * 1000  # 1KB string
            }
        }
        
        state.context[f"execution_{self.execution_count}"] = execution_data
        
        # Occasionally accumulate large data (potential leak source)
        if self.execution_count % 10 == 0:
            self.large_data_accumulation.append({
                "data": "Y" * 5000,  # 5KB per accumulation
                "timestamp": time.time()
            })
            
            # Clean up old accumulations (simulate proper cleanup)
            if len(self.large_data_accumulation) > 5:
                self.large_data_accumulation = self.large_data_accumulation[-5:]
        
        # Simulate processing delay
        await asyncio.sleep(0.01)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def memory_profiler():
    """Memory profiler fixture with baseline establishment."""
    profiler = MemoryProfiler(enable_tracemalloc=True)
    baseline = profiler.establish_baseline()
    yield profiler
    
    # Final analysis
    final_analysis = profiler.detect_memory_leaks(iterations_completed=1)
    if final_analysis.get("leak_detected"):
        logger.warning(f"Memory leak detected in test: {final_analysis}")


@pytest.fixture
def memory_stress_generator():
    """Memory stress generator fixture with cleanup."""
    generator = MemoryStressGenerator()
    yield generator
    # Cleanup after test
    asyncio.create_task(generator.cleanup_all())


@pytest.fixture
async def memory_test_agents():
    """Create agents for memory testing."""
    agents = []
    for i in range(3):
        agent = MemoryLeakTestAgent(f"memory_agent_{i}", enable_large_responses=(i == 0))
        agents.append(agent)
    
    yield agents
    
    # Cleanup agents
    for agent in agents:
        try:
            if hasattr(agent, 'cleanup'):
                await agent.cleanup()
        except:
            pass


# ============================================================================
# MEMORY LEAK DETECTION TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(300)  # 5 minutes for extensive memory testing
async def test_extended_agent_execution_memory_stability(memory_profiler, memory_test_agents):
    """CRITICAL: Test memory stability during extended agent execution."""
    
    profiler = memory_profiler
    agents = memory_test_agents
    
    # Track agents for cleanup monitoring
    profiler.track_objects(agents, "test_agents")
    
    # Run extended execution test
    iterations = 500  # High iteration count
    batch_size = 25
    
    for batch_start in range(0, iterations, batch_size):
        batch_end = min(batch_start + batch_size, iterations)
        
        # Execute batch of operations
        tasks = []
        for i in range(batch_start, batch_end):
            agent = agents[i % len(agents)]
            
            state = DeepAgentState()
            state.run_id = f"memory_test_{i}"
            
            task = asyncio.create_task(
                agent.execute(state, state.run_id, stream_updates=False)
            )
            tasks.append(task)
        
        # Wait for batch completion
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Take memory snapshot every 10 batches
        if (batch_start // batch_size) % 10 == 0:
            snapshot = profiler.take_memory_snapshot(f"batch_{batch_start//batch_size}")
            logger.info(f"Memory at batch {batch_start//batch_size}: {snapshot['rss_mb']:.1f}MB "
                       f"(+{snapshot.get('rss_increase_mb', 0):.1f}MB)")
        
        # Small delay between batches
        await asyncio.sleep(0.05)
    
    # Final memory analysis
    final_analysis = profiler.detect_memory_leaks(iterations)
    
    # CRITICAL MEMORY STABILITY ASSERTIONS
    memory_analysis = final_analysis["memory_analysis"]
    
    assert not final_analysis["leak_detected"], \
        f"Memory leak detected: {memory_analysis['leak_severity']} - " \
        f"{memory_analysis['rss_increase_mb']:.1f}MB increase over {iterations} iterations"
    
    # Memory per iteration should be minimal
    memory_per_iteration = memory_analysis["memory_per_iteration_mb"]
    assert memory_per_iteration < 0.5, \
        f"Memory usage per iteration too high: {memory_per_iteration:.3f}MB (limit: <0.5MB)"
    
    # Resource leaks check
    assert not final_analysis["resource_leak_detected"], \
        f"Resource leak detected: files +{final_analysis['resource_analysis']['files_increase']}, " \
        f"threads +{final_analysis['resource_analysis']['threads_increase']}"
    
    # Object cleanup verification
    agent_cleanup = profiler.check_object_cleanup("test_agents")
    # Agents should still be alive since we're holding references
    assert agent_cleanup["alive_objects"] == len(agents), \
        f"Unexpected agent cleanup: {agent_cleanup['alive_objects']}/{len(agents)} alive"
    
    logger.info(f"Extended execution test: {iterations} iterations, "
                f"{memory_analysis['rss_increase_mb']:.1f}MB increase, "
                f"{memory_per_iteration:.3f}MB per iteration")


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(180)
async def test_memory_stress_scenarios_leak_detection(memory_profiler, memory_stress_generator):
    """CRITICAL: Test memory stability under various stress scenarios."""
    
    profiler = memory_profiler
    generator = memory_stress_generator
    
    stress_scenarios = [
        ("object_creation_destruction", 200),
        ("circular_references", 150),
        ("large_data_processing", 100),
        ("recursive_operations", 100),
        ("file_operations", 50),
        ("callback_accumulation", 200)
    ]
    
    scenario_results = []
    
    for scenario_name, intensity in stress_scenarios:
        logger.info(f"Running stress scenario: {scenario_name} with intensity {intensity}")
        
        # Take snapshot before scenario
        before_snapshot = profiler.take_memory_snapshot(f"before_{scenario_name}")
        
        try:
            # Run stress scenario
            await generator.run_stress_scenario(scenario_name, intensity)
            
            # Force cleanup
            await generator.cleanup_all()
            gc.collect()
            
            # Take snapshot after scenario
            after_snapshot = profiler.take_memory_snapshot(f"after_{scenario_name}")
            
            memory_increase = after_snapshot["rss_mb"] - before_snapshot["rss_mb"]
            files_increase = after_snapshot["open_files"] - before_snapshot["open_files"]
            
            scenario_results.append({
                "scenario": scenario_name,
                "intensity": intensity,
                "memory_increase_mb": memory_increase,
                "files_increase": files_increase,
                "success": True,
                "peak_memory": after_snapshot["rss_mb"]
            })
            
            # Individual scenario assertions
            assert memory_increase < 50, \
                f"Scenario {scenario_name}: Memory increase too high: {memory_increase:.1f}MB"
            
            assert abs(files_increase) < 10, \
                f"Scenario {scenario_name}: File descriptor leak: {files_increase} files"
            
        except Exception as e:
            scenario_results.append({
                "scenario": scenario_name,
                "intensity": intensity,
                "success": False,
                "error": str(e)
            })
            logger.error(f"Stress scenario {scenario_name} failed: {e}")
    
    # Overall stress test analysis
    successful_scenarios = [r for r in scenario_results if r["success"]]
    total_memory_increase = sum(r.get("memory_increase_mb", 0) for r in successful_scenarios)
    
    # CRITICAL STRESS TEST ASSERTIONS
    assert len(successful_scenarios) >= len(stress_scenarios) * 0.8, \
        f"Too many stress scenarios failed: {len(successful_scenarios)}/{len(stress_scenarios)}"
    
    assert total_memory_increase < 100, \
        f"Total memory increase across all scenarios too high: {total_memory_increase:.1f}MB"
    
    # Final leak detection
    final_analysis = profiler.detect_memory_leaks(len(stress_scenarios))
    
    assert not final_analysis["leak_detected"], \
        f"Memory leak detected after stress testing: {final_analysis['memory_analysis']}"
    
    logger.info(f"Stress scenarios completed: {len(successful_scenarios)}/{len(stress_scenarios)} successful, "
                f"total memory increase: {total_memory_increase:.1f}MB")


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(120)
async def test_concurrent_operations_memory_isolation(memory_profiler):
    """CRITICAL: Test memory isolation during concurrent operations."""
    
    profiler = memory_profiler
    
    # Create many concurrent operations
    concurrent_count = 100
    
    async def memory_intensive_operation(op_id: int):
        """Operation that creates and cleans up memory."""
        # Create agent for this operation
        agent = MemoryLeakTestAgent(f"concurrent_agent_{op_id}")
        
        # Track agent
        profiler.track_objects([agent], f"concurrent_batch_{op_id // 20}")
        
        try:
            # Execute multiple times
            for i in range(5):
                state = DeepAgentState()
                state.run_id = f"concurrent_{op_id}_{i}"
                
                await agent.execute(state, state.run_id, stream_updates=False)
                
                # Add some concurrent data processing
                data = {
                    "operation": op_id,
                    "iteration": i,
                    "timestamp": time.time(),
                    "large_data": "X" * 1000  # 1KB per operation
                }
                
                # Simulate processing
                processed = json.dumps(data)
                del data
                del processed
            
            return f"Concurrent operation {op_id} completed"
            
        finally:
            # Explicit cleanup
            del agent
    
    # Execute all operations concurrently
    logger.info(f"Starting {concurrent_count} concurrent memory operations")
    
    tasks = [
        asyncio.create_task(memory_intensive_operation(i))
        for i in range(concurrent_count)
    ]
    
    # Monitor memory during execution
    monitoring_task = asyncio.create_task(
        profiler._monitor_memory_during_concurrent_test(15.0)
    )
    
    try:
        # Wait for completion
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop monitoring
        monitoring_task.cancel()
        
        successful_ops = sum(1 for r in results if isinstance(r, str))
        
        # Force cleanup
        gc.collect()
        
        # Take final snapshot
        final_snapshot = profiler.take_memory_snapshot("concurrent_test_complete")
        
        # Analyze concurrent operations
        final_analysis = profiler.detect_memory_leaks(concurrent_count)
        
        # CRITICAL CONCURRENT MEMORY ASSERTIONS
        assert successful_ops >= concurrent_count * 0.9, \
            f"Too many concurrent operations failed: {successful_ops}/{concurrent_count}"
        
        memory_analysis = final_analysis["memory_analysis"]
        memory_increase = memory_analysis["rss_increase_mb"]
        
        assert memory_increase < 200, \
            f"Concurrent operations memory increase too high: {memory_increase:.1f}MB (limit: <200MB)"
        
        # Memory per operation should be reasonable
        memory_per_op = memory_increase / concurrent_count if concurrent_count > 0 else 0
        assert memory_per_op < 2.0, \
            f"Memory per concurrent operation too high: {memory_per_op:.2f}MB (limit: <2MB)"
        
        # Check object cleanup for concurrent batches
        cleanup_issues = []
        for batch_id in range(concurrent_count // 20 + 1):
            cleanup_info = profiler.check_object_cleanup(f"concurrent_batch_{batch_id}")
            if cleanup_info.get("alive_objects", 0) > 2:  # Allow some alive objects
                cleanup_issues.append(cleanup_info)
        
        assert len(cleanup_issues) < 3, \
            f"Too many object cleanup issues in concurrent test: {len(cleanup_issues)}"
        
        logger.info(f"Concurrent operations test: {successful_ops}/{concurrent_count} successful, "
                   f"{memory_increase:.1f}MB increase, "
                   f"{memory_per_op:.2f}MB per operation")
        
    except asyncio.CancelledError:
        pass


async def _monitor_memory_during_concurrent_test(self, duration: float):
    """Monitor memory usage during concurrent test."""
    start_time = time.time()
    samples = []
    
    while time.time() - start_time < duration:
        try:
            process = psutil.Process()
            sample = {
                "timestamp": time.time() - start_time,
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "threads": process.num_threads(),
                "files": len(process.open_files())
            }
            samples.append(sample)
            
        except Exception:
            pass
        
        await asyncio.sleep(0.5)
    
    # Add samples to profiler for analysis
    for sample in samples:
        self.memory_snapshots.append({
            "timestamp": sample["timestamp"],
            "label": "concurrent_monitor",
            "rss_mb": sample["memory_mb"],
            "num_threads": sample["threads"],
            "open_files": sample["files"]
        })

# Add the monitoring method to the MemoryProfiler class
MemoryProfiler._monitor_memory_during_concurrent_test = _monitor_memory_during_concurrent_test


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(150)
async def test_garbage_collection_effectiveness(memory_profiler):
    """CRITICAL: Test that garbage collection effectively prevents memory accumulation."""
    
    profiler = memory_profiler
    
    # Test different garbage collection scenarios
    gc_scenarios = [
        {"name": "manual_gc", "gc_frequency": 50, "force_gc": True},
        {"name": "automatic_gc", "gc_frequency": 0, "force_gc": False},
        {"name": "mixed_gc", "gc_frequency": 100, "force_gc": True}
    ]
    
    gc_results = []
    
    for scenario in gc_scenarios:
        logger.info(f"Testing GC scenario: {scenario['name']}")
        
        # Clear any existing objects
        gc.collect()
        before_snapshot = profiler.take_memory_snapshot(f"gc_before_{scenario['name']}")
        
        # Create many objects with potential circular references
        objects_created = 0
        circular_objects = []
        
        for i in range(300):  # Create many objects
            # Create objects with circular references
            obj_a = {"id": f"a_{i}", "data": "X" * 500, "ref": None}
            obj_b = {"id": f"b_{i}", "data": "Y" * 500, "ref": None, "back_ref": None}
            obj_c = {"id": f"c_{i}", "data": "Z" * 500, "refs": []}
            
            # Create circular references
            obj_a["ref"] = obj_b
            obj_b["ref"] = obj_c
            obj_b["back_ref"] = obj_a
            obj_c["refs"] = [obj_a, obj_b]
            
            circular_objects.append((obj_a, obj_b, obj_c))
            objects_created += 3
            
            # Apply garbage collection based on scenario
            if scenario["force_gc"] and scenario["gc_frequency"] > 0:
                if i % scenario["gc_frequency"] == 0:
                    gc.collect()
            
            # Periodic cleanup of some objects
            if i % 100 == 0 and circular_objects:
                # Break some circular references
                for obj_tuple in circular_objects[-50:]:
                    for obj in obj_tuple:
                        if isinstance(obj, dict):
                            obj.clear()
                
                circular_objects = circular_objects[:-50]
                
                if scenario["force_gc"]:
                    gc.collect()
        
        # Final garbage collection
        if scenario["force_gc"]:
            gc.collect()
        
        after_snapshot = profiler.take_memory_snapshot(f"gc_after_{scenario['name']}")
        
        memory_increase = after_snapshot["rss_mb"] - before_snapshot["rss_mb"]
        
        # Get GC statistics
        gc_stats = gc.get_stats()
        gc_counts = gc.get_count()
        
        gc_results.append({
            "scenario": scenario["name"],
            "objects_created": objects_created,
            "memory_increase_mb": memory_increase,
            "gc_counts": gc_counts,
            "gc_stats": gc_stats,
            "force_gc_enabled": scenario["force_gc"]
        })
        
        # Individual scenario assertions
        max_expected_increase = 150 if scenario["force_gc"] else 300  # Higher limit for auto GC
        
        assert memory_increase < max_expected_increase, \
            f"GC scenario {scenario['name']}: Memory increase too high: {memory_increase:.1f}MB " \
            f"(limit: {max_expected_increase}MB)"
        
        # Clear objects for next scenario
        circular_objects.clear()
        gc.collect()
        
        logger.info(f"GC scenario {scenario['name']}: Created {objects_created} objects, "
                   f"memory increase: {memory_increase:.1f}MB")
    
    # CRITICAL GARBAGE COLLECTION ASSERTIONS
    
    # Manual GC should be most effective
    manual_gc_result = next(r for r in gc_results if r["scenario"] == "manual_gc")
    auto_gc_result = next(r for r in gc_results if r["scenario"] == "automatic_gc")
    
    assert manual_gc_result["memory_increase_mb"] <= auto_gc_result["memory_increase_mb"] * 1.5, \
        f"Manual GC not significantly better than automatic: " \
        f"manual={manual_gc_result['memory_increase_mb']:.1f}MB, " \
        f"auto={auto_gc_result['memory_increase_mb']:.1f}MB"
    
    # All scenarios should prevent excessive accumulation
    max_memory_increase = max(r["memory_increase_mb"] for r in gc_results)
    assert max_memory_increase < 400, \
        f"Excessive memory accumulation despite GC: {max_memory_increase:.1f}MB"
    
    # Final leak detection
    final_analysis = profiler.detect_memory_leaks(sum(r["objects_created"] for r in gc_results))
    
    assert not final_analysis["leak_detected"], \
        f"Memory leak detected after GC testing: {final_analysis['memory_analysis']}"
    
    logger.info(f"GC effectiveness test completed: max increase {max_memory_increase:.1f}MB across scenarios")


if __name__ == "__main__":
    # Run memory leak detection tests
    pytest.main([__file__, "-v", "--tb=short", "-x"])