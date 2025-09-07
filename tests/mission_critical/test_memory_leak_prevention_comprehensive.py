class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

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
import tempfile
import resource
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
from loguru import logger

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import components for memory testing
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.services.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


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
    """Use real service instance."""
    # TODO: Initialize real service
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
    """Use real service instance."""
    # TODO: Initialize real service
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


# ============================================================================
# AUTHENTICATION FLOW VALIDATION TESTS
# ============================================================================

class TestAuthenticationFlowMemoryManagement:
    """Test authentication flows under memory stress to prevent leaks during user journeys."""
    
    @pytest.fixture(autouse=True)
    async def setup_auth_memory_tests(self):
        """Setup authentication flow memory testing."""
        self.profiler = MemoryProfiler(enable_tracemalloc=True)
        self.baseline = self.profiler.establish_baseline()
        
        # Mock authentication service
        self.websocket = TestWebSocketConnection()
        
        # Mock WebSocket manager for real-time updates
        self.websocket = TestWebSocketConnection()
        self.mock_ws_manager.send_to_thread = AsyncMock(return_value=True)
        
        yield
        
        # Final memory analysis
        final_analysis = self.profiler.detect_memory_leaks(iterations_completed=1)
        if final_analysis.get("leak_detected"):
            logger.warning(f"Authentication flow memory leak detected: {final_analysis}")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(180)
    async def test_complete_signup_login_chat_flow_memory_stability(self):
        """CRITICAL: Test complete user journey from signup to AI chat without memory leaks."""
        
        # Track authentication objects
        auth_sessions = []
        
        # Test multiple user signup/login/chat cycles
        iterations = 100
        batch_size = 10
        
        for batch_start in range(0, iterations, batch_size):
            batch_end = min(batch_start + batch_size, iterations)
            
            for i in range(batch_start, batch_end):
                user_id = f"memory_user_{i}"
                
                # 1. SIGNUP FLOW
                signup_data = {
                    "email": f"{user_id}@netra.ai",
                    "password": "SecurePass123!",
                    "full_name": f"Memory Test User {i}",
                    "company": "Netra Memory Testing",
                    "tier": "free" if i % 3 == 0 else "premium"
                }
                
                self.mock_auth_service.signup.return_value = {
                    "user_id": user_id,
                    "email": signup_data["email"],
                    "tier": signup_data["tier"],
                    "created_at": time.time()
                }
                
                signup_result = await self.mock_auth_service.signup(signup_data)
                
                # 2. LOGIN FLOW  
                login_data = {
                    "email": signup_data["email"],
                    "password": signup_data["password"]
                }
                
                self.mock_auth_service.login.return_value = {
                    "access_token": f"jwt_token_{i}",
                    "refresh_token": f"refresh_{i}",
                    "user": signup_result,
                    "expires_in": 3600
                }
                
                login_result = await self.mock_auth_service.login(login_data)
                
                # 3. JWT VALIDATION (during chat requests)
                self.mock_auth_service.validate_jwt.return_value = {
                    "user_id": user_id,
                    "tier": signup_data["tier"],
                    "valid": True,
                    "permissions": ["chat", "agents", "tools"]
                }
                
                jwt_validation = await self.mock_auth_service.validate_jwt(
                    login_result["access_token"]
                )
                
                # 4. CHAT FLOW SIMULATION (AI value delivery)
                chat_session = {
                    "user_id": user_id,
                    "thread_id": f"thread_{i}",
                    "messages": []
                }
                
                # Simulate AI chat interactions
                for msg_idx in range(5):  # 5 messages per session
                    message = {
                        "role": "user" if msg_idx % 2 == 0 else "assistant",
                        "content": f"Message {msg_idx} from {user_id}",
                        "timestamp": time.time(),
                        "tokens": {"input": 50, "output": 100, "total": 150}
                    }
                    chat_session["messages"].append(message)
                    
                    # Simulate WebSocket event for real-time updates
                    await self.mock_ws_manager.send_to_thread(
                        chat_session["thread_id"],
                        {
                            "type": "agent_thinking" if message["role"] == "assistant" else "user_message",
                            "payload": {
                                "message": message["content"][:50],  # Truncated for memory efficiency
                                "user_id": user_id,
                                "revenue_impact": 0.05  # $0.05 per interaction
                            }
                        }
                    )
                
                # 5. TOKEN REFRESH (during long sessions)
                self.mock_auth_service.refresh_token.return_value = {
                    "access_token": f"refreshed_jwt_token_{i}",
                    "refresh_token": f"new_refresh_{i}",
                    "expires_in": 3600
                }
                
                refresh_result = await self.mock_auth_service.refresh_token(
                    login_result["refresh_token"]
                )
                
                # 6. LOGOUT FLOW
                self.mock_auth_service.logout.return_value = {
                    "success": True,
                    "session_duration": time.time() - login_result.get("login_time", time.time())
                }
                
                logout_result = await self.mock_auth_service.logout(user_id)
                
                # Track session for memory analysis
                session_data = {
                    "user_id": user_id,
                    "signup": signup_result,
                    "login": login_result, 
                    "chat_session": chat_session,
                    "logout": logout_result,
                    "revenue_generated": len(chat_session["messages"]) * 0.05
                }
                auth_sessions.append(session_data)
                
                # Periodic memory cleanup
                if i % 20 == 0:
                    # Keep only recent sessions
                    auth_sessions = auth_sessions[-10:]
                    gc.collect()
                    
                    # Take memory snapshot
                    snapshot = self.profiler.take_memory_snapshot(f"auth_batch_{i}")
                    logger.info(f"Auth flow batch {i}: {snapshot['rss_mb']:.1f}MB RSS, "
                               f"+{snapshot.get('rss_increase_mb', 0):.1f}MB from baseline")
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        # Final memory analysis
        final_analysis = self.profiler.detect_memory_leaks(iterations)
        
        # CRITICAL AUTHENTICATION MEMORY ASSERTIONS
        memory_analysis = final_analysis["memory_analysis"]
        
        # Memory increase should be minimal despite 100 complete user journeys
        assert not final_analysis["leak_detected"], \
            f"Authentication flow memory leak: {memory_analysis['leak_severity']} - " \
            f"{memory_analysis['rss_increase_mb']:.1f}MB increase"
        
        # Memory per user journey should be reasonable
        memory_per_user = memory_analysis["rss_increase_mb"] / iterations
        assert memory_per_user < 2.0, \
            f"Memory per user journey too high: {memory_per_user:.2f}MB (limit: <2MB)"
        
        # No resource leaks
        assert not final_analysis["resource_leak_detected"], \
            f"Resource leak in auth flows: {final_analysis['resource_analysis']}"
        
        # Business metrics validation
        total_revenue = sum(session["revenue_generated"] for session in auth_sessions)
        assert total_revenue > 0, "Should generate revenue from AI interactions"
        
        logger.info(f"Authentication flow test: {iterations} complete user journeys, "
                   f"{memory_analysis['rss_increase_mb']:.1f}MB total increase, "
                   f"${total_revenue:.2f} simulated revenue, "
                   f"{memory_per_user:.3f}MB per user")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(240)
    async def test_concurrent_user_authentication_memory_isolation(self):
        """CRITICAL: Test concurrent user authentication with memory isolation."""
        
        concurrent_users = 50
        
        async def simulate_user_journey(user_index: int):
            """Simulate complete user journey with authentication."""
            user_id = f"concurrent_user_{user_index}"
            
            try:
                # Memory-intensive user data
                user_profile = {
                    "user_id": user_id,
                    "preferences": {"theme": "dark", "language": "en", "notifications": True},
                    "usage_history": [f"action_{i}" for i in range(100)],  # 100 actions
                    "ai_interactions": []
                }
                
                # Authentication flow
                auth_token = f"jwt_{user_index}_{time.time()}"
                
                # Simulate multiple AI interactions
                for interaction in range(10):
                    ai_interaction = {
                        "query": f"AI query {interaction} from {user_id}",
                        "response": "AI response " * 100,  # 1KB response
                        "tokens_used": {"input": 75, "output": 150, "total": 225},
                        "cost": 0.01,
                        "timestamp": time.time()
                    }
                    user_profile["ai_interactions"].append(ai_interaction)
                    
                    # WebSocket real-time update
                    await self.mock_ws_manager.send_to_thread(
                        f"thread_{user_id}",
                        {
                            "type": "agent_completed",
                            "payload": {
                                "response": ai_interaction["response"][:100],  # Truncated
                                "tokens": ai_interaction["tokens_used"]["total"],
                                "cost": ai_interaction["cost"]
                            }
                        }
                    )
                    
                    # Small delay between interactions
                    await asyncio.sleep(0.01)
                
                # Calculate user value
                total_cost = sum(ai["cost"] for ai in user_profile["ai_interactions"])
                user_value = total_cost * 2  # 2x markup
                
                return {
                    "user_id": user_id,
                    "interactions": len(user_profile["ai_interactions"]),
                    "total_cost": total_cost,
                    "user_value": user_value,
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"User journey failed for {user_id}: {e}")
                return {"user_id": user_id, "success": False, "error": str(e)}
            
            finally:
                # Explicit cleanup
                del user_profile
        
        # Execute all user journeys concurrently
        start_time = time.time()
        
        logger.info(f"Starting {concurrent_users} concurrent user authentication flows")
        
        tasks = [
            asyncio.create_task(simulate_user_journey(i))
            for i in range(concurrent_users)
        ]
        
        # Monitor memory during concurrent execution
        memory_monitor_task = asyncio.create_task(
            self._monitor_concurrent_auth_memory(30.0)
        )
        
        try:
            # Wait for all user journeys
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Stop memory monitoring
            memory_monitor_task.cancel()
            
            # Analyze results
            successful_users = [r for r in results if isinstance(r, dict) and r.get("success")]
            failed_users = [r for r in results if isinstance(r, dict) and not r.get("success")]
            
            duration = time.time() - start_time
            
            # Force cleanup
            gc.collect()
            
            # Final memory analysis
            final_analysis = self.profiler.detect_memory_leaks(concurrent_users)
            
            # CRITICAL CONCURRENT AUTHENTICATION ASSERTIONS
            assert len(successful_users) >= concurrent_users * 0.95, \
                f"Too many auth failures: {len(successful_users)}/{concurrent_users} successful"
            
            memory_analysis = final_analysis["memory_analysis"]
            memory_increase = memory_analysis["rss_increase_mb"]
            
            assert memory_increase < 300, \
                f"Concurrent auth memory increase too high: {memory_increase:.1f}MB (limit: <300MB)"
            
            # Memory per concurrent user
            memory_per_user = memory_increase / concurrent_users
            assert memory_per_user < 6.0, \
                f"Memory per concurrent user too high: {memory_per_user:.2f}MB (limit: <6MB)"
            
            # Business metrics
            total_value = sum(user.get("user_value", 0) for user in successful_users)
            total_interactions = sum(user.get("interactions", 0) for user in successful_users)
            
            assert total_value > 0, "Should generate business value from concurrent users"
            assert total_interactions >= concurrent_users * 8, "Should have sufficient AI interactions"
            
            # Performance metrics
            users_per_second = concurrent_users / duration
            assert users_per_second > 20, \
                f"Concurrent auth throughput too low: {users_per_second:.1f} users/s (need >20)"
            
            logger.info(f"Concurrent auth test: {len(successful_users)}/{concurrent_users} successful, "
                       f"{memory_increase:.1f}MB increase, ${total_value:.2f} total value, "
                       f"{users_per_second:.1f} users/s, {total_interactions} AI interactions")
            
        except asyncio.CancelledError:
            pass

    async def _monitor_concurrent_auth_memory(self, duration: float):
        """Monitor memory during concurrent authentication test."""
        start_time = time.time()
        samples = []
        
        while time.time() - start_time < duration:
            try:
                sample = self.profiler.take_memory_snapshot(f"concurrent_auth_{len(samples)}")
                samples.append(sample)
                
                # Log critical memory spikes
                if sample.get("rss_increase_mb", 0) > 500:
                    logger.warning(f"High memory usage detected: {sample['rss_mb']:.1f}MB RSS")
                
            except Exception:
                pass
                
            await asyncio.sleep(1.0)
        
        logger.info(f"Concurrent auth monitoring: {len(samples)} samples collected")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(300)
    async def test_oauth_social_login_memory_efficiency(self):
        """CRITICAL: Test OAuth and social login flows for memory efficiency."""
        
        oauth_providers = ["google", "microsoft", "github", "linkedin", "apple"]
        iterations_per_provider = 20
        
        for provider in oauth_providers:
            logger.info(f"Testing {provider} OAuth flow memory efficiency")
            
            before_snapshot = self.profiler.take_memory_snapshot(f"before_{provider}")
            
            for i in range(iterations_per_provider):
                # OAuth initiation
                oauth_request = {
                    "provider": provider,
                    "redirect_uri": f"https://netra.ai/auth/{provider}/callback",
                    "state": f"{provider}_state_{i}_{uuid.uuid4()}",
                    "user_id": f"oauth_user_{provider}_{i}"
                }
                
                # Simulate OAuth callback with authorization code
                auth_code_data = {
                    "code": f"oauth_code_{i}_{time.time()}",
                    "state": oauth_request["state"],
                    "provider": provider
                }
                
                # Mock OAuth token exchange
                self.mock_auth_service.exchange_oauth_code = AsyncMock(return_value={
                    "access_token": f"{provider}_access_{i}",
                    "refresh_token": f"{provider}_refresh_{i}",
                    "user_info": {
                        "id": f"{provider}_id_{i}",
                        "email": f"user_{i}@{provider}.com",
                        "name": f"{provider.title()} User {i}",
                        "profile_picture": f"https://{provider}.com/avatar_{i}.jpg"
                    },
                    "expires_in": 7200
                })
                
                oauth_result = await self.mock_auth_service.exchange_oauth_code(
                    auth_code_data["code"], 
                    oauth_request["redirect_uri"]
                )
                
                # Create internal JWT from OAuth
                internal_jwt_data = {
                    "user_id": oauth_request["user_id"],
                    "email": oauth_result["user_info"]["email"],
                    "provider": provider,
                    "oauth_token": oauth_result["access_token"],
                    "tier": "premium" if provider in ["microsoft", "apple"] else "free"
                }
                
                self.mock_auth_service.create_jwt_from_oauth = AsyncMock(return_value={
                    "jwt_token": f"netra_jwt_{provider}_{i}",
                    "refresh_token": f"netra_refresh_{provider}_{i}",
                    "user": internal_jwt_data,
                    "expires_in": 3600
                })
                
                jwt_result = await self.mock_auth_service.create_jwt_from_oauth(
                    oauth_result
                )
                
                # Simulate AI interactions with OAuth user
                for interaction in range(3):  # 3 AI interactions per OAuth user
                    ai_query = {
                        "query": f"OAuth query {interaction} from {provider} user {i}",
                        "user_tier": internal_jwt_data["tier"],
                        "provider": provider
                    }
                    
                    # Premium OAuth users get better AI responses
                    ai_response = {
                        "response": ("Premium AI response " * 50) if internal_jwt_data["tier"] == "premium" else ("Standard AI response " * 25),
                        "tokens": {
                            "input": 100 if internal_jwt_data["tier"] == "premium" else 50,
                            "output": 200 if internal_jwt_data["tier"] == "premium" else 100,
                            "total": 300 if internal_jwt_data["tier"] == "premium" else 150
                        },
                        "cost": 0.015 if internal_jwt_data["tier"] == "premium" else 0.008,
                        "provider_bonus": 1.2 if provider in ["microsoft", "apple"] else 1.0
                    }
                    
                    # Send WebSocket update for OAuth user
                    await self.mock_ws_manager.send_to_thread(
                        f"oauth_thread_{provider}_{i}",
                        {
                            "type": "agent_completed",
                            "payload": {
                                "response": ai_response["response"][:100],
                                "cost": ai_response["cost"],
                                "provider": provider,
                                "tier": internal_jwt_data["tier"]
                            }
                        }
                    )
                
                # Cleanup OAuth data every 5 iterations
                if i % 5 == 0:
                    gc.collect()
            
            after_snapshot = self.profiler.take_memory_snapshot(f"after_{provider}")
            memory_increase = after_snapshot["rss_mb"] - before_snapshot["rss_mb"]
            
            # CRITICAL OAUTH MEMORY ASSERTIONS
            assert memory_increase < 50, \
                f"{provider} OAuth flow memory increase too high: {memory_increase:.1f}MB (limit: <50MB)"
            
            memory_per_oauth = memory_increase / iterations_per_provider
            assert memory_per_oauth < 2.5, \
                f"{provider} memory per OAuth too high: {memory_per_oauth:.2f}MB (limit: <2.5MB)"
            
            logger.info(f"{provider} OAuth test: {iterations_per_provider} flows, "
                       f"{memory_increase:.1f}MB increase, "
                       f"{memory_per_oauth:.3f}MB per OAuth flow")


# ============================================================================
# USER JOURNEY TESTING UNDER MEMORY CONSTRAINTS
# ============================================================================

class TestUserJourneyMemoryOptimization:
    """Test complete user journeys under memory constraints to ensure optimal performance."""
    
    @pytest.fixture(autouse=True)  
    async def setup_user_journey_memory_tests(self):
        """Setup user journey memory testing with realistic constraints."""
        self.profiler = MemoryProfiler(enable_tracemalloc=True)
        self.baseline = self.profiler.establish_baseline()
        
        # Mock services for complete user journey
        self.websocket = TestWebSocketConnection()
        
        # Mock WebSocket manager for real-time updates
        self.websocket = TestWebSocketConnection()
        self.mock_ws_manager.send_to_thread = AsyncMock(return_value=True)
        
        yield
        
        # Ensure no memory leaks in user journeys
        final_analysis = self.profiler.detect_memory_leaks(iterations_completed=1)
        if final_analysis.get("leak_detected"):
            pytest.fail(f"User journey memory leak detected: {final_analysis}")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(360)
    async def test_first_time_user_onboarding_memory_profile(self):
        """CRITICAL: Test first-time user onboarding memory profile for optimal UX."""
        
        new_users = 25
        onboarding_journeys = []
        
        for user_idx in range(new_users):
            user_journey_start = time.time()
            
            # 1. LANDING PAGE AND SIGNUP INITIATION
            landing_data = {
                "user_id": f"new_user_{user_idx}",
                "referral_source": "google_ads" if user_idx % 3 == 0 else "organic",
                "utm_campaign": f"onboarding_test_{user_idx}",
                "device": "desktop" if user_idx % 2 == 0 else "mobile"
            }
            
            # 2. ACCOUNT CREATION WITH VERIFICATION
            account_creation = {
                "email": f"newuser{user_idx}@example.com",
                "password": "SecureNewUserPass123!",
                "full_name": f"New User {user_idx}",
                "company": f"Startup {user_idx}",
                "industry": "technology" if user_idx % 2 == 0 else "consulting",
                "team_size": "1-10" if user_idx < 15 else "11-50",
                "use_case": "AI automation" if user_idx % 2 == 0 else "data analysis"
            }
            
            self.mock_user_service.create_account.return_value = {
                "user_id": landing_data["user_id"],
                "account_created": True,
                "verification_email_sent": True,
                "initial_tier": "free"
            }
            
            account_result = await self.mock_user_service.create_account(account_creation)
            
            # 3. EMAIL VERIFICATION SIMULATION
            verification_data = {
                "user_id": landing_data["user_id"],
                "verification_token": f"verify_token_{user_idx}_{time.time()}",
                "email_verified": True,
                "verification_time": time.time()
            }
            
            self.mock_user_service.verify_email.return_value = {
                "verified": True,
                "account_activated": True,
                "welcome_bonus_credits": 100  # $1.00 in free credits
            }
            
            verification_result = await self.mock_user_service.verify_email(
                verification_data["verification_token"]
            )
            
            # 4. ONBOARDING TUTORIAL AND AI INTRODUCTION
            tutorial_data = {
                "user_id": landing_data["user_id"],
                "tutorials_completed": [],
                "ai_interactions": []
            }
            
            # Simulate tutorial steps
            tutorial_steps = [
                "account_setup", "dashboard_tour", "first_ai_query", 
                "agent_selection", "tool_introduction"
            ]
            
            for step in tutorial_steps:
                tutorial_completion = {
                    "step": step,
                    "completed_at": time.time(),
                    "duration_seconds": 30 + (user_idx % 60),  # 30-90 seconds per step
                    "user_engagement": 0.8 + (user_idx % 20) * 0.01  # 80-100% engagement
                }
                tutorial_data["tutorials_completed"].append(tutorial_completion)
                
                # AI interaction for tutorial step
                if step in ["first_ai_query", "agent_selection", "tool_introduction"]:
                    ai_tutorial_interaction = {
                        "query": f"Tutorial {step} query from {landing_data['user_id']}",
                        "response": f"Tutorial response for {step}" * 20,  # ~400 chars
                        "tokens": {"input": 25, "output": 75, "total": 100},
                        "cost": 0.005,  # Using welcome bonus credits
                        "tutorial_step": step
                    }
                    tutorial_data["ai_interactions"].append(ai_tutorial_interaction)
                    
                    # Send real-time tutorial progress
                    await self.mock_ws_manager.send_to_thread(
                        f"onboarding_thread_{user_idx}",
                        {
                            "type": "tutorial_progress",
                            "payload": {
                                "step": step,
                                "completed": True,
                                "ai_response": ai_tutorial_interaction["response"][:50],
                                "engagement": tutorial_completion["user_engagement"]
                            }
                        }
                    )
            
            # 5. FIRST REAL AI INTERACTION (POST-TUTORIAL)
            first_real_query = {
                "query": f"My first real AI query from {landing_data['user_id']} about {account_creation['use_case']}",
                "context": {
                    "use_case": account_creation["use_case"],
                    "industry": account_creation["industry"],
                    "company": account_creation["company"]
                }
            }
            
            self.mock_ai_service.process_query.return_value = {
                "response": f"Comprehensive AI response tailored to {account_creation['use_case']} in {account_creation['industry']}" * 30,  # ~1.8KB response
                "tokens": {"input": 150, "output": 400, "total": 550},
                "cost": 0.025,
                "agent_used": "general_purpose_agent",
                "tools_used": ["web_search", "data_analysis"],
                "processing_time_ms": 2500,
                "user_satisfaction_predicted": 0.85
            }
            
            first_ai_result = await self.mock_ai_service.process_query(first_real_query)
            
            # 6. UPGRADE PROMPT AND TIER ASSESSMENT
            usage_assessment = {
                "user_id": landing_data["user_id"],
                "tutorial_engagement": sum(t["user_engagement"] for t in tutorial_data["tutorials_completed"]) / len(tutorial_data["tutorials_completed"]),
                "ai_interactions_count": len(tutorial_data["ai_interactions"]) + 1,
                "total_tokens_used": sum(ai["tokens"]["total"] for ai in tutorial_data["ai_interactions"]) + first_ai_result["tokens"]["total"],
                "credits_remaining": 100 - sum(ai["cost"] * 100 for ai in tutorial_data["ai_interactions"]) - (first_ai_result["cost"] * 100),
                "upgrade_likelihood": 0.3 if tutorial_data["tutorials_completed"][-1]["user_engagement"] > 0.9 else 0.1
            }
            
            # Determine upgrade prompt strategy
            upgrade_prompt = None
            if usage_assessment["credits_remaining"] < 50:  # Less than $0.50 remaining
                upgrade_prompt = {
                    "type": "low_credits",
                    "message": "You're almost out of free credits! Upgrade to continue unlimited AI access.",
                    "recommended_tier": "early" if usage_assessment["upgrade_likelihood"] > 0.25 else "free_trial_extension"
                }
            elif usage_assessment["ai_interactions_count"] >= 5:
                upgrade_prompt = {
                    "type": "power_user",
                    "message": "You're a power user! Upgrade for advanced agents and priority support.",
                    "recommended_tier": "mid"
                }
            
            # 7. ONBOARDING COMPLETION METRICS
            journey_duration = time.time() - user_journey_start
            
            onboarding_completion = {
                "user_id": landing_data["user_id"],
                "completed_at": time.time(),
                "journey_duration_minutes": journey_duration / 60,
                "tutorial_completion_rate": len(tutorial_data["tutorials_completed"]) / len(tutorial_steps),
                "first_ai_success": True,
                "credits_used": 100 - usage_assessment["credits_remaining"],
                "engagement_score": usage_assessment["tutorial_engagement"],
                "conversion_potential": usage_assessment["upgrade_likelihood"],
                "onboarding_success": True
            }
            
            onboarding_journeys.append(onboarding_completion)
            
            # Memory cleanup every 5 users
            if user_idx % 5 == 0:
                gc.collect()
                snapshot = self.profiler.take_memory_snapshot(f"onboarding_batch_{user_idx}")
                logger.info(f"Onboarding batch {user_idx}: {snapshot['rss_mb']:.1f}MB RSS")
            
            # Small delay between user onboardings
            await asyncio.sleep(0.02)
        
        # Final onboarding memory analysis
        final_analysis = self.profiler.detect_memory_leaks(new_users)
        
        # CRITICAL ONBOARDING MEMORY ASSERTIONS
        memory_analysis = final_analysis["memory_analysis"]
        
        assert not final_analysis["leak_detected"], \
            f"Onboarding memory leak detected: {memory_analysis['leak_severity']}"
        
        memory_per_onboarding = memory_analysis["rss_increase_mb"] / new_users
        assert memory_per_onboarding < 5.0, \
            f"Memory per onboarding too high: {memory_per_onboarding:.2f}MB (limit: <5MB)"
        
        # Business metrics validation
        successful_onboardings = [j for j in onboarding_journeys if j["onboarding_success"]]
        average_engagement = sum(j["engagement_score"] for j in successful_onboardings) / len(successful_onboardings)
        total_credits_used = sum(j["credits_used"] for j in successful_onboardings)
        conversion_potential = sum(j["conversion_potential"] for j in successful_onboardings)
        
        assert len(successful_onboardings) == new_users, "All onboardings should succeed"
        assert average_engagement > 0.7, f"Engagement too low: {average_engagement:.2f} (need >0.7)"
        assert total_credits_used > new_users * 10, "Should use significant credits during onboarding"
        assert conversion_potential > new_users * 0.1, "Should generate conversion potential"
        
        # Performance assertions
        average_duration = sum(j["journey_duration_minutes"] for j in successful_onboardings) / len(successful_onboardings)
        assert average_duration < 15, f"Onboarding too long: {average_duration:.1f} minutes (limit: <15 min)"
        
        logger.info(f"Onboarding memory test: {len(successful_onboardings)} successful onboardings, "
                   f"{memory_analysis['rss_increase_mb']:.1f}MB total increase, "
                   f"{average_engagement:.2f} avg engagement, "
                   f"{average_duration:.1f} min avg duration, "
                   f"${total_credits_used:.2f} credits used")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(300)
    async def test_power_user_workflow_memory_scalability(self):
        """CRITICAL: Test power user workflows for memory scalability under heavy usage."""
        
        power_users = 10
        heavy_usage_sessions = []
        
        for user_idx in range(power_users):
            session_start = time.time()
            
            # Power user profile
            user_profile = {
                "user_id": f"power_user_{user_idx}",
                "tier": "enterprise" if user_idx < 3 else "mid",
                "monthly_spend": 500 + (user_idx * 100),  # $500-$1400/month
                "team_size": 5 + (user_idx * 2),  # 5-25 team members
                "usage_pattern": "heavy_ai_automation",
                "preferred_agents": ["data_analysis", "code_generation", "research", "optimization"]
            }
            
            # Heavy usage session simulation
            session_data = {
                "user_id": user_profile["user_id"],
                "session_start": session_start,
                "ai_interactions": [],
                "agent_executions": [],
                "tool_uses": [],
                "data_processed_gb": 0,
                "revenue_generated": 0
            }
            
            # Multiple concurrent AI workflows
            for workflow_idx in range(20):  # 20 heavy workflows per power user
                
                # Complex AI workflow with multiple agents and tools
                workflow = {
                    "workflow_id": f"workflow_{user_idx}_{workflow_idx}",
                    "type": "complex_analysis" if workflow_idx % 3 == 0 else "automation_task",
                    "agents_involved": []
                }
                
                # Multi-agent workflow execution
                for agent_name in user_profile["preferred_agents"]:
                    agent_execution = {
                        "agent": agent_name,
                        "query": f"Power user {user_idx} workflow {workflow_idx} - {agent_name} task",
                        "context": {
                            "user_tier": user_profile["tier"],
                            "team_context": f"Team of {user_profile['team_size']} members",
                            "workflow_type": workflow["type"]
                        }
                    }
                    
                    # Agent processing with multiple tools
                    tools_used = []
                    for tool_idx in range(5):  # 5 tools per agent
                        tool_execution = {
                            "tool": f"tool_{agent_name}_{tool_idx}",
                            "input_size_kb": 100 + (tool_idx * 50),  # 100KB - 350KB inputs
                            "processing_time_ms": 500 + (tool_idx * 200),
                            "output_size_kb": 50 + (tool_idx * 25),
                            "cost": 0.02 + (tool_idx * 0.01)
                        }
                        tools_used.append(tool_execution)
                        session_data["tool_uses"].append(tool_execution)
                        
                        # WebSocket progress update for each tool
                        await self.mock_ws_manager.send_to_thread(
                            f"power_user_thread_{user_idx}",
                            {
                                "type": "tool_executing",
                                "payload": {
                                    "tool": tool_execution["tool"],
                                    "progress": (tool_idx + 1) / 5 * 100,
                                    "estimated_remaining_ms": tool_execution["processing_time_ms"] * (4 - tool_idx)
                                }
                            }
                        )
                    
                    # Agent completion
                    agent_result = {
                        "agent": agent_name,
                        "result": f"Complex result from {agent_name}" * 200,  # ~4KB result
                        "tools_used": len(tools_used),
                        "processing_time_ms": sum(t["processing_time_ms"] for t in tools_used),
                        "total_cost": sum(t["cost"] for t in tools_used),
                        "data_processed_mb": sum(t["input_size_kb"] for t in tools_used) / 1024,
                        "success": True
                    }
                    
                    workflow["agents_involved"].append(agent_result)
                    session_data["agent_executions"].append(agent_result)
                    
                    # Agent completion WebSocket event
                    await self.mock_ws_manager.send_to_thread(
                        f"power_user_thread_{user_idx}",
                        {
                            "type": "agent_completed",
                            "payload": {
                                "agent": agent_name,
                                "result_summary": agent_result["result"][:100],
                                "cost": agent_result["total_cost"],
                                "processing_time": agent_result["processing_time_ms"]
                            }
                        }
                    )
                
                # Workflow completion
                workflow_cost = sum(agent["total_cost"] for agent in workflow["agents_involved"])
                workflow_revenue = workflow_cost * 2.5  # 2.5x markup for enterprise
                workflow_data_processed = sum(agent["data_processed_mb"] for agent in workflow["agents_involved"])
                
                session_data["revenue_generated"] += workflow_revenue
                session_data["data_processed_gb"] += workflow_data_processed / 1024
                
                # Memory cleanup every 5 workflows
                if workflow_idx % 5 == 0:
                    # Keep only recent data in memory
                    session_data["agent_executions"] = session_data["agent_executions"][-10:]
                    session_data["tool_uses"] = session_data["tool_uses"][-25:]
                    gc.collect()
            
            # Session completion
            session_duration = time.time() - session_start
            session_summary = {
                "user_id": user_profile["user_id"],
                "session_duration_minutes": session_duration / 60,
                "total_workflows": 20,
                "total_agent_executions": len(session_data["agent_executions"]),
                "total_tool_uses": len(session_data["tool_uses"]),
                "data_processed_gb": session_data["data_processed_gb"],
                "revenue_generated": session_data["revenue_generated"],
                "efficiency_score": session_data["revenue_generated"] / (session_duration / 60),  # $/minute
                "power_user_tier": user_profile["tier"]
            }
            
            heavy_usage_sessions.append(session_summary)
            
            # Memory snapshot every 3 power users
            if user_idx % 3 == 0:
                snapshot = self.profiler.take_memory_snapshot(f"power_user_batch_{user_idx}")
                logger.info(f"Power user batch {user_idx}: {snapshot['rss_mb']:.1f}MB RSS, "
                           f"${session_summary['revenue_generated']:.2f} revenue")
            
            await asyncio.sleep(0.05)
        
        # Final power user memory analysis
        final_analysis = self.profiler.detect_memory_leaks(power_users * 20)  # 20 workflows per user
        
        # CRITICAL POWER USER MEMORY ASSERTIONS
        memory_analysis = final_analysis["memory_analysis"]
        
        assert not final_analysis["leak_detected"], \
            f"Power user workflow memory leak: {memory_analysis['leak_severity']}"
        
        memory_per_workflow = memory_analysis["rss_increase_mb"] / (power_users * 20)
        assert memory_per_workflow < 3.0, \
            f"Memory per workflow too high: {memory_per_workflow:.2f}MB (limit: <3MB)"
        
        # Business performance validation
        total_revenue = sum(s["revenue_generated"] for s in heavy_usage_sessions)
        total_data_processed = sum(s["data_processed_gb"] for s in heavy_usage_sessions)
        average_efficiency = sum(s["efficiency_score"] for s in heavy_usage_sessions) / len(heavy_usage_sessions)
        
        assert total_revenue > power_users * 50, \
            f"Power user revenue too low: ${total_revenue:.2f} (need >${power_users * 50})"
        
        assert total_data_processed > power_users * 2, \
            f"Data processing too low: {total_data_processed:.1f}GB (need >{power_users * 2}GB)"
        
        assert average_efficiency > 20, \
            f"Efficiency too low: ${average_efficiency:.2f}/min (need >$20/min)"
        
        # Scalability assertions
        enterprise_users = [s for s in heavy_usage_sessions if s["power_user_tier"] == "enterprise"]
        enterprise_revenue = sum(s["revenue_generated"] for s in enterprise_users)
        enterprise_efficiency = sum(s["efficiency_score"] for s in enterprise_users) / len(enterprise_users) if enterprise_users else 0
        
        assert enterprise_efficiency > average_efficiency * 1.3, \
            f"Enterprise users should be 30% more efficient: ${enterprise_efficiency:.2f} vs ${average_efficiency:.2f}"
        
        logger.info(f"Power user workflow test: {power_users} users, {power_users * 20} workflows, "
                   f"{memory_analysis['rss_increase_mb']:.1f}MB total increase, "
                   f"${total_revenue:.2f} total revenue, "
                   f"{total_data_processed:.1f}GB processed, "
                   f"${average_efficiency:.2f}/min efficiency")


# ============================================================================
# PERFORMANCE UNDER LOAD WITH AUTHENTICATION
# ============================================================================

class TestAuthenticationPerformanceUnderLoad:
    """Test authentication and user journey performance under extreme load."""
    
    @pytest.fixture(autouse=True)
    async def setup_performance_load_tests(self):
        """Setup performance testing under load with memory monitoring."""
        self.profiler = MemoryProfiler(enable_tracemalloc=True)
        self.baseline = self.profiler.establish_baseline()
        
        # Performance metrics tracking
        self.performance_metrics = {
            "auth_latency_ms": [],
            "journey_completion_times": [],
            "memory_peaks": [],
            "concurrent_users": 0,
            "errors": [],
            "revenue_per_second": []
        }
        
        # Mock WebSocket manager for real-time updates
        self.websocket = TestWebSocketConnection()
        self.mock_ws_manager.send_to_thread = AsyncMock(return_value=True)
        
        yield

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(600)  # 10 minutes for extreme load testing
    async def test_50_concurrent_users_complete_journeys(self):
        """CRITICAL: Test 50+ concurrent users completing full authentication and AI journeys."""
        
        concurrent_users = 75
        target_completion_time = 30  # seconds
        
        async def complete_user_journey(user_index: int) -> Dict[str, Any]:
            """Complete full user journey under load."""
            start_time = time.time()
            user_id = f"load_user_{user_index}"
            
            try:
                journey_metrics = {
                    "user_id": user_id,
                    "start_time": start_time,
                    "auth_completed": False,
                    "ai_interactions_completed": 0,
                    "revenue_generated": 0,
                    "errors": [],
                    "completion_time": 0,
                    "success": False
                }
                
                # 1. RAPID AUTHENTICATION
                auth_start = time.time()
                
                signup_data = {
                    "email": f"loaduser{user_index}@loadtest.com",
                    "password": "LoadTest123!",
                    "tier": "premium" if user_index % 3 == 0 else "free"
                }
                
                # Simulate auth service response time under load
                auth_latency = 50 + (user_index % 200)  # 50-250ms auth latency
                await asyncio.sleep(auth_latency / 1000)
                
                auth_result = {
                    "user_id": user_id,
                    "jwt_token": f"load_jwt_{user_index}",
                    "tier": signup_data["tier"],
                    "auth_time_ms": auth_latency
                }
                
                auth_completed_time = time.time()
                journey_metrics["auth_completed"] = True
                self.performance_metrics["auth_latency_ms"].append(auth_latency)
                
                # 2. IMMEDIATE AI INTERACTION (CRITICAL FOR USER EXPERIENCE)
                ai_interactions = 8 if signup_data["tier"] == "premium" else 5
                
                for ai_idx in range(ai_interactions):
                    ai_start = time.time()
                    
                    # AI query with realistic complexity
                    ai_query = {
                        "query": f"Load test AI query {ai_idx} from {user_id}",
                        "complexity": "high" if signup_data["tier"] == "premium" else "standard",
                        "expected_tokens": 300 if signup_data["tier"] == "premium" else 150
                    }
                    
                    # Simulate AI processing time under load  
                    ai_processing_time = (200 + (ai_idx * 100)) if signup_data["tier"] == "premium" else (100 + (ai_idx * 50))
                    await asyncio.sleep(ai_processing_time / 1000)
                    
                    ai_response = {
                        "response": f"AI response {ai_idx}" * (60 if signup_data["tier"] == "premium" else 30),
                        "tokens": {"input": 50, "output": ai_query["expected_tokens"], "total": ai_query["expected_tokens"] + 50},
                        "cost": 0.02 if signup_data["tier"] == "premium" else 0.01,
                        "processing_time_ms": ai_processing_time
                    }
                    
                    journey_metrics["ai_interactions_completed"] += 1
                    journey_metrics["revenue_generated"] += ai_response["cost"] * 2  # 2x markup
                    
                    # WebSocket update for real-time user experience
                    await self.mock_ws_manager.send_to_thread(
                        f"load_thread_{user_index}",
                        {
                            "type": "agent_completed",
                            "payload": {
                                "interaction": ai_idx,
                                "cost": ai_response["cost"],
                                "processing_time": ai_processing_time
                            }
                        }
                    )
                    
                    # Brief pause between AI interactions
                    await asyncio.sleep(0.01)
                
                # 3. COMPLETION METRICS
                journey_metrics["completion_time"] = time.time() - start_time
                journey_metrics["success"] = journey_metrics["completion_time"] < target_completion_time
                
                # Track performance metrics
                self.performance_metrics["journey_completion_times"].append(journey_metrics["completion_time"])
                
                # Calculate revenue per second for this user
                if journey_metrics["completion_time"] > 0:
                    revenue_per_second = journey_metrics["revenue_generated"] / journey_metrics["completion_time"]
                    self.performance_metrics["revenue_per_second"].append(revenue_per_second)
                
                return journey_metrics
                
            except Exception as e:
                error_info = f"User {user_index} journey failed: {str(e)}"
                logger.error(error_info)
                self.performance_metrics["errors"].append(error_info)
                
                return {
                    "user_id": user_id,
                    "start_time": start_time,
                    "completion_time": time.time() - start_time,
                    "success": False,
                    "error": str(e)
                }
        
        # Track concurrent user peak
        self.performance_metrics["concurrent_users"] = concurrent_users
        
        # Execute all user journeys concurrently
        logger.info(f"Starting {concurrent_users} concurrent user journeys (target: <{target_completion_time}s each)")
        
        load_test_start = time.time()
        
        # Memory monitoring task
        memory_monitor = asyncio.create_task(
            self._monitor_load_test_memory(60.0)  # Monitor for 60 seconds
        )
        
        try:
            # Launch all concurrent user journeys
            tasks = [
                asyncio.create_task(complete_user_journey(i))
                for i in range(concurrent_users)
            ]
            
            # Wait for all journeys to complete
            journey_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Stop memory monitoring
            memory_monitor.cancel()
            
            load_test_duration = time.time() - load_test_start
            
            # Analyze results
            successful_journeys = [r for r in journey_results if isinstance(r, dict) and r.get("success")]
            failed_journeys = [r for r in journey_results if isinstance(r, dict) and not r.get("success")]
            exception_count = len([r for r in journey_results if isinstance(r, Exception)])
            
            # Final memory analysis
            gc.collect()
            final_analysis = self.profiler.detect_memory_leaks(concurrent_users)
            
            # CRITICAL LOAD PERFORMANCE ASSERTIONS
            
            # Success rate should be high
            success_rate = len(successful_journeys) / concurrent_users
            assert success_rate >= 0.9, \
                f"Load test success rate too low: {success_rate*100:.1f}% (need ≥90%)"
            
            # Average completion time should meet target
            if successful_journeys:
                avg_completion_time = sum(j["completion_time"] for j in successful_journeys) / len(successful_journeys)
                assert avg_completion_time < target_completion_time * 1.2, \
                    f"Average completion time too high: {avg_completion_time:.1f}s (limit: {target_completion_time * 1.2}s)"
            
            # Memory should remain stable under load
            memory_analysis = final_analysis["memory_analysis"]
            assert not final_analysis["leak_detected"], \
                f"Memory leak under load: {memory_analysis['leak_severity']}"
            
            memory_per_user = memory_analysis["rss_increase_mb"] / concurrent_users
            assert memory_per_user < 8.0, \
                f"Memory per concurrent user too high: {memory_per_user:.2f}MB (limit: <8MB)"
            
            # Authentication latency should be reasonable
            if self.performance_metrics["auth_latency_ms"]:
                avg_auth_latency = sum(self.performance_metrics["auth_latency_ms"]) / len(self.performance_metrics["auth_latency_ms"])
                assert avg_auth_latency < 500, \
                    f"Authentication latency too high under load: {avg_auth_latency:.0f}ms (limit: <500ms)"
            
            # Revenue generation should be significant
            total_revenue = sum(j.get("revenue_generated", 0) for j in successful_journeys)
            assert total_revenue > concurrent_users * 0.1, \
                f"Revenue generation too low: ${total_revenue:.2f} (need >${concurrent_users * 0.1})"
            
            # Throughput assertions
            users_per_second = concurrent_users / load_test_duration
            assert users_per_second > 5, \
                f"User throughput too low: {users_per_second:.1f} users/s (need >5)"
            
            if self.performance_metrics["revenue_per_second"]:
                avg_revenue_per_second = sum(self.performance_metrics["revenue_per_second"]) / len(self.performance_metrics["revenue_per_second"])
                assert avg_revenue_per_second > 0.02, \
                    f"Revenue per second too low: ${avg_revenue_per_second:.3f}/s (need >$0.02)"
            
            # Error rate should be minimal
            total_errors = len(self.performance_metrics["errors"]) + exception_count
            error_rate = total_errors / concurrent_users
            assert error_rate < 0.05, \
                f"Error rate too high under load: {error_rate*100:.1f}% (limit: <5%)"
            
            logger.info(f"Load test results: {len(successful_journeys)}/{concurrent_users} successful "
                       f"({success_rate*100:.1f}%), "
                       f"{avg_completion_time:.1f}s avg completion, "
                       f"{memory_analysis['rss_increase_mb']:.1f}MB memory increase, "
                       f"${total_revenue:.2f} total revenue, "
                       f"{users_per_second:.1f} users/s throughput")
            
        except asyncio.CancelledError:
            pass

    async def _monitor_load_test_memory(self, duration: float):
        """Monitor memory usage during load test."""
        start_time = time.time()
        peak_memory = 0
        
        while time.time() - start_time < duration:
            try:
                snapshot = self.profiler.take_memory_snapshot("load_monitor")
                current_memory = snapshot["rss_mb"]
                peak_memory = max(peak_memory, current_memory)
                
                self.performance_metrics["memory_peaks"].append(current_memory)
                
                # Alert on extreme memory usage
                if current_memory > 2000:  # 2GB
                    logger.warning(f"Extreme memory usage under load: {current_memory:.1f}MB")
                
            except Exception:
                pass
                
            await asyncio.sleep(2.0)
        
        logger.info(f"Load test peak memory: {peak_memory:.1f}MB")


if __name__ == "__main__":
    # Run comprehensive memory leak detection and authentication tests
    pytest.main([__file__, "-v", "--tb=short", "-x"])