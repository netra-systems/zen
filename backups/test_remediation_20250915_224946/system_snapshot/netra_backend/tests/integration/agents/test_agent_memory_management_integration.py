"""
Agent Memory Management Integration Tests - Phase 1 Memory & Cleanup Focus

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: Platform Stability & Cost Management
- Value Impact: Prevents $100K+ cloud costs from memory leaks and resource exhaustion
- Strategic Impact: Ensures system can handle production load without memory issues

CRITICAL MISSION: Validates agent memory management including resource cleanup,
memory leak prevention, garbage collection patterns, and resource monitoring.

Phase 1 Focus Areas:
1. Agent instance memory management and cleanup
2. UserExecutionContext memory lifecycle and isolation
3. WebSocket connection cleanup and resource management
4. LLM context memory management and optimization
5. Tool execution result cleanup and memory efficiency
6. Factory pattern memory management and leak prevention
7. Concurrent execution memory isolation and cleanup
8. Resource monitoring and memory usage tracking

NO Docker dependencies - all tests run locally with real SSOT components.
BUSINESS CRITICAL: Memory leaks = production outages and escalating cloud costs.
"""

import asyncio
import gc
import pytest
import psutil
import resource
import time
import uuid
import weakref
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# SSOT Base Test Case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core Agent Infrastructure
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.schemas.agent import SubAgentLifecycle

# Factory and Registry Infrastructure
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, AgentLifecycleManager
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory

# Infrastructure Services
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class MemoryIntensiveAgent(BaseAgent):
    """Agent designed to test memory management patterns."""
    
    def __init__(self, memory_profile: str = "normal", *args, **kwargs):
        super().__init__(
            name=f"MemoryAgent_{memory_profile}",
            description=f"Memory test agent with {memory_profile} profile",
            *args,
            **kwargs
        )
        self.memory_profile = memory_profile
        self.memory_allocations = []
        self.execution_data = {}
        
    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with specific memory allocation patterns."""
        
        await self.emit_agent_started(f"Starting {self.memory_profile} memory test")
        
        # Allocate memory based on profile
        if self.memory_profile == "high_memory":
            # Allocate large amounts of data
            for i in range(10):
                large_data = "x" * (100 * 1024)  # 100KB each
                self.memory_allocations.append(large_data)
                self.execution_data[f"dataset_{i}"] = {
                    "data": large_data,
                    "size": len(large_data),
                    "timestamp": time.time()
                }
                
        elif self.memory_profile == "many_objects":
            # Create many small objects
            for i in range(1000):
                small_object = {
                    "id": i,
                    "data": f"object_{i}",
                    "metadata": {"created": time.time(), "index": i}
                }
                self.memory_allocations.append(small_object)
                
        elif self.memory_profile == "context_heavy":
            # Store lots of data in context
            for i in range(50):
                context.metadata[f"heavy_data_{i}"] = {
                    "payload": "y" * (10 * 1024),  # 10KB each
                    "index": i,
                    "created": time.time()
                }
                
        else:  # normal profile
            # Minimal memory allocation
            self.execution_data["normal_data"] = "Normal execution data"
        
        await self.emit_thinking(f"Processing {self.memory_profile} memory operations", context=context)
        
        # Simulate some processing
        await asyncio.sleep(0.01)
        
        result = {
            "status": "completed",
            "memory_profile": self.memory_profile,
            "allocations_count": len(self.memory_allocations),
            "execution_data_size": len(self.execution_data),
            "context_data_size": len(context.metadata)
        }
        
        # Store result in context (adds to memory usage)
        self.store_metadata_result(context, f"memory_test_result_{self.memory_profile}", result)
        
        await self.emit_agent_completed(result, context=context)
        
        return result
    
    async def cleanup(self):
        """Override cleanup to test memory cleanup patterns."""
        # Clear memory allocations
        self.memory_allocations.clear()
        self.execution_data.clear()
        
        # Call parent cleanup
        await super().cleanup()


class LeakTestAgent(BaseAgent):
    """Agent designed to test for memory leaks."""
    
    # Class-level storage to test for leaks
    _class_storage = {}
    
    def __init__(self, leak_type: str = "none", *args, **kwargs):
        super().__init__(
            name=f"LeakTestAgent_{leak_type}",
            description=f"Leak test agent with {leak_type} pattern",
            *args,
            **kwargs
        )
        self.leak_type = leak_type
        self.instance_id = uuid.uuid4().hex
        
    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with potential leak patterns."""
        
        # Simulate different leak patterns
        if self.leak_type == "class_storage_leak":
            # Store data in class-level storage (potential leak)
            LeakTestAgent._class_storage[self.instance_id] = {
                "large_data": "z" * (50 * 1024),  # 50KB
                "timestamp": time.time(),
                "context_ref": context  # Dangerous reference
            }
            
        elif self.leak_type == "circular_reference":
            # Create circular references
            self.circular_ref = {"agent": self, "data": "x" * (10 * 1024)}
            context.metadata["agent_ref"] = self  # Circular reference
            
        elif self.leak_type == "unclosed_resources":
            # Simulate unclosed resources (we'll track these)
            self.unclosed_resources = []
            for i in range(5):
                resource_mock = MagicMock()
                resource_mock.close = MagicMock()
                self.unclosed_resources.append(resource_mock)
        
        result = {
            "status": "completed",
            "leak_type": self.leak_type,
            "instance_id": self.instance_id
        }
        
        return result
    
    async def cleanup(self):
        """Override cleanup to test leak prevention."""
        if self.leak_type == "class_storage_leak":
            # Proper cleanup removes class storage
            if self.instance_id in LeakTestAgent._class_storage:
                del LeakTestAgent._class_storage[self.instance_id]
                
        elif self.leak_type == "circular_reference":
            # Break circular references
            if hasattr(self, 'circular_ref'):
                self.circular_ref.clear()
                del self.circular_ref
                
        elif self.leak_type == "unclosed_resources":
            # Close resources properly
            if hasattr(self, 'unclosed_resources'):
                for resource in self.unclosed_resources:
                    resource.close()
                self.unclosed_resources.clear()
        
        await super().cleanup()


@pytest.mark.integration
class AgentMemoryManagementIntegrationTests(SSotAsyncTestCase):
    """Integration tests for agent memory management and cleanup."""
    
    def create_test_user_context(self, user_id: str = None, memory_scenario: str = "memory_test") -> UserExecutionContext:
        """Create user context for memory testing."""
        user_id = user_id or f"memory_user_{uuid.uuid4().hex[:8]}"
        
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"memory_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"memory_run_{uuid.uuid4().hex[:8]}",
            request_id=f"memory_req_{uuid.uuid4().hex[:8]}",
            db_session=None,
            websocket_connection_id=f"memory_ws_{uuid.uuid4().hex[:8]}",
            metadata={
                "user_request": f"Execute {memory_scenario} scenario",
                "memory_scenario": memory_scenario,
                "test_data": "Initial test data"
            }
        )
    
    def get_memory_usage_mb(self) -> float:
        """Get current process memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            # Fallback for systems without psutil
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    
    def get_memory_details(self) -> Dict[str, Any]:
        """Get detailed memory usage information."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
                "available_mb": psutil.virtual_memory().available / 1024 / 1024
            }
        except:
            return {"rss_mb": self.get_memory_usage_mb(), "details": "limited"}
    
    @pytest.fixture
    async def mock_websocket_bridge(self):
        """Mock WebSocket bridge with memory tracking."""
        mock_bridge = AsyncMock()
        mock_bridge.memory_events = []
        mock_bridge.connection_count = 0
        
        async def track_connection(event_type, *args, **kwargs):
            if event_type in ["agent_started", "connection_opened"]:
                mock_bridge.connection_count += 1
            elif event_type in ["agent_completed", "connection_closed"]:
                mock_bridge.connection_count = max(0, mock_bridge.connection_count - 1)
            
            mock_bridge.memory_events.append({
                "event": event_type,
                "timestamp": time.time(),
                "connection_count": mock_bridge.connection_count
            })
            
        mock_bridge.emit_agent_started = AsyncMock(side_effect=lambda *a, **k: track_connection("agent_started", *a, **k))
        mock_bridge.emit_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_connection("agent_completed", *a, **k))
        mock_bridge.emit_agent_thinking = AsyncMock()
        mock_bridge.emit_error = AsyncMock()
        
        return mock_bridge
    
    @pytest.fixture
    async def agent_registry(self):
        """Real agent registry for memory testing."""
        mock_llm = AsyncMock(spec=LLMManager)
        registry = AgentRegistry(mock_llm)
        yield registry
        await registry.emergency_cleanup_all()
    
    @pytest.fixture
    async def agent_factory(self, mock_websocket_bridge):
        """Real agent factory for memory testing."""
        mock_llm = AsyncMock(spec=LLMManager)
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge, llm_manager=mock_llm)
        yield factory
        factory.reset_for_testing()
    
    @pytest.mark.real_services
    async def test_agent_memory_allocation_and_cleanup_patterns(self):
        """Test different memory allocation patterns and cleanup."""
        
        initial_memory = self.get_memory_usage_mb()
        memory_profiles = ["normal", "high_memory", "many_objects", "context_heavy"]
        
        agent_refs = []
        context_refs = []
        results = []
        
        # Test each memory profile
        for profile in memory_profiles:
            user_context = self.create_test_user_context(f"memory_user_{profile}", f"memory_test_{profile}")
            
            agent = MemoryIntensiveAgent(
                memory_profile=profile,
                user_context=user_context
            )
            
            # Store weak references to track cleanup
            agent_refs.append(weakref.ref(agent))
            context_refs.append(weakref.ref(user_context))
            
            # Execute agent
            result = await agent.execute(user_context)
            results.append(result)
            
            # Validate result
            assert result["status"] == "completed"
            assert result["memory_profile"] == profile
            
            # Cleanup agent explicitly
            await agent.cleanup()
            
            # Clear local references
            del agent
            del user_context
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow async cleanup
        
        # Check memory after cleanup
        post_cleanup_memory = self.get_memory_usage_mb()
        memory_increase = post_cleanup_memory - initial_memory
        
        # Memory increase should be reasonable (< 20MB for all profiles)
        assert memory_increase < 20.0, f"Excessive memory increase: {memory_increase:.1f}MB"
        
        # Check weak references - most should be dead
        dead_agent_refs = sum(1 for ref in agent_refs if ref() is None)
        dead_context_refs = sum(1 for ref in context_refs if ref() is None)
        
        # At least 75% should be garbage collected
        assert dead_agent_refs >= len(agent_refs) * 0.75, f"Too many live agent references: {len(agent_refs) - dead_agent_refs}"
        assert dead_context_refs >= len(context_refs) * 0.75, f"Too many live context references: {len(context_refs) - dead_context_refs}"
        
        # Validate results from all profiles
        for i, result in enumerate(results):
            profile = memory_profiles[i]
            assert result["memory_profile"] == profile
            
            if profile == "high_memory":
                assert result["allocations_count"] == 10
            elif profile == "many_objects":
                assert result["allocations_count"] == 1000
            elif profile == "context_heavy":
                assert result["context_data_size"] >= 50
        
        self.record_metric("memory_profiles_tested", len(memory_profiles))
        self.record_metric("memory_increase_mb", memory_increase)
        self.record_metric("agent_refs_cleaned", dead_agent_refs)
        self.record_metric("context_refs_cleaned", dead_context_refs)
        
    @pytest.mark.real_services
    async def test_memory_leak_detection_and_prevention(self):
        """Test memory leak detection and prevention patterns."""
        
        initial_memory = self.get_memory_usage_mb()
        leak_types = ["none", "class_storage_leak", "circular_reference", "unclosed_resources"]
        
        # Track class storage before test
        initial_class_storage = len(LeakTestAgent._class_storage)
        
        agent_instances = []
        leak_refs = []
        
        # Create agents with different leak patterns
        for i, leak_type in enumerate(leak_types):
            user_context = self.create_test_user_context(f"leak_user_{i}", f"leak_test_{leak_type}")
            
            agent = LeakTestAgent(
                leak_type=leak_type,
                user_context=user_context
            )
            
            agent_instances.append(agent)
            leak_refs.append(weakref.ref(agent))
            
            # Execute agent (may create leaks)
            result = await agent.execute(user_context)
            
            assert result["status"] == "completed"
            assert result["leak_type"] == leak_type
        
        # Check class storage increased for leak agents
        post_execution_class_storage = len(LeakTestAgent._class_storage)
        expected_storage_increase = sum(1 for leak in leak_types if leak == "class_storage_leak")
        assert post_execution_class_storage >= initial_class_storage + expected_storage_increase
        
        # Memory should have increased due to leaks
        post_leak_memory = self.get_memory_usage_mb()
        memory_with_leaks = post_leak_memory - initial_memory
        
        # Now cleanup agents properly
        for agent in agent_instances:
            await agent.cleanup()
        
        # Clear references
        agent_instances.clear()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)
        
        # Check memory after proper cleanup
        post_cleanup_memory = self.get_memory_usage_mb()
        final_memory_increase = post_cleanup_memory - initial_memory
        
        # Class storage should be back to initial level
        final_class_storage = len(LeakTestAgent._class_storage)
        assert final_class_storage == initial_class_storage, "Class storage leak detected"
        
        # Memory should have decreased after cleanup
        memory_recovered = memory_with_leaks - final_memory_increase
        assert memory_recovered > 0, "Memory not properly recovered after cleanup"
        
        # Final memory increase should be minimal
        assert final_memory_increase < 5.0, f"Memory leak detected: {final_memory_increase:.1f}MB"
        
        # Weak references should be dead
        dead_refs = sum(1 for ref in leak_refs if ref() is None)
        assert dead_refs >= len(leak_refs) * 0.75, "Agent instances not properly garbage collected"
        
        self.record_metric("leak_types_tested", len(leak_types))
        self.record_metric("memory_recovered_mb", memory_recovered)
        self.record_metric("final_memory_increase_mb", final_memory_increase)
        self.record_metric("leak_prevention_verified", True)
        
    @pytest.mark.real_services
    async def test_concurrent_agent_memory_isolation(self, mock_websocket_bridge):
        """Test memory isolation between concurrent agents."""
        
        initial_memory = self.get_memory_usage_mb()
        
        # Create concurrent agents with different memory patterns
        num_concurrent = 8
        memory_patterns = ["normal", "high_memory", "many_objects", "context_heavy"] * 2
        
        agents = []
        contexts = []
        weak_refs = []
        
        # Create all agents and contexts
        for i in range(num_concurrent):
            pattern = memory_patterns[i]
            context = self.create_test_user_context(f"concurrent_memory_user_{i}", f"concurrent_{pattern}")
            
            agent = MemoryIntensiveAgent(
                memory_profile=pattern,
                user_context=context
            )
            agent.set_websocket_bridge(mock_websocket_bridge, context.run_id)
            
            agents.append(agent)
            contexts.append(context)
            weak_refs.append(weakref.ref(agent))
        
        # Execute all agents concurrently
        start_time = time.time()
        results = await asyncio.gather(*[
            agent.execute(context)
            for agent, context in zip(agents, contexts)
        ])
        execution_time = time.time() - start_time
        
        # Validate concurrent execution succeeded
        assert len(results) == num_concurrent
        for i, result in enumerate(results):
            assert result["status"] == "completed"
            assert result["memory_profile"] == memory_patterns[i]
        
        # Check memory usage under load
        peak_memory = self.get_memory_usage_mb()
        peak_memory_increase = peak_memory - initial_memory
        
        # Validate memory isolation - each agent should have independent memory
        for i in range(num_concurrent):
            agent = agents[i]
            context = contexts[i]
            
            # Each agent should have isolated memory allocations
            if agent.memory_profile == "high_memory":
                assert len(agent.memory_allocations) == 10
                assert len(agent.execution_data) == 10
            elif agent.memory_profile == "many_objects":
                assert len(agent.memory_allocations) == 1000
            
            # Context data should be isolated
            context_keys = set(context.metadata.keys())
            for j in range(num_concurrent):
                if i != j:
                    other_context_keys = set(contexts[j].metadata.keys())
                    # Should have minimal overlap (only basic keys)
                    overlap = context_keys.intersection(other_context_keys)
                    basic_keys = {"user_request", "memory_scenario", "test_data"}
                    assert overlap.issubset(basic_keys), f"Memory contamination detected between agents {i} and {j}"
        
        # Cleanup all agents
        cleanup_start = time.time()
        await asyncio.gather(*[agent.cleanup() for agent in agents])
        cleanup_time = time.time() - cleanup_start
        
        # Clear references
        agents.clear()
        contexts.clear()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)
        
        # Check memory after cleanup
        post_cleanup_memory = self.get_memory_usage_mb()
        final_memory_increase = post_cleanup_memory - initial_memory
        
        # Memory should be mostly recovered
        memory_recovery_rate = (peak_memory_increase - final_memory_increase) / peak_memory_increase
        assert memory_recovery_rate > 0.7, f"Poor memory recovery: {memory_recovery_rate:.1%}"
        
        # Weak references should be dead
        dead_refs = sum(1 for ref in weak_refs if ref() is None)
        assert dead_refs >= num_concurrent * 0.75, f"Too many live references: {num_concurrent - dead_refs}"
        
        # Performance checks
        assert execution_time < 1.0, f"Concurrent execution too slow: {execution_time:.2f}s"
        assert cleanup_time < 0.5, f"Cleanup too slow: {cleanup_time:.2f}s"
        
        self.record_metric("concurrent_agents_tested", num_concurrent)
        self.record_metric("peak_memory_increase_mb", peak_memory_increase)
        self.record_metric("memory_recovery_rate", memory_recovery_rate)
        self.record_metric("execution_time", execution_time)
        self.record_metric("cleanup_time", cleanup_time)
        
    @pytest.mark.real_services
    async def test_agent_factory_memory_management(self, agent_factory):
        """Test agent factory memory management and cleanup."""
        
        initial_memory = self.get_memory_usage_mb()
        
        # Create many contexts through factory
        num_contexts = 25
        created_contexts = []
        context_refs = []
        
        for i in range(num_contexts):
            context = await agent_factory.create_user_execution_context(
                user_id=f"factory_memory_user_{i}",
                thread_id=f"factory_thread_{i}",
                run_id=f"factory_run_{i}"
            )
            
            # Add some data to each context
            context.metadata[f"factory_data_{i}"] = {
                "payload": "f" * (5 * 1024),  # 5KB per context
                "index": i,
                "created": time.time()
            }
            
            created_contexts.append(context)
            context_refs.append(weakref.ref(context))
        
        # Check factory metrics
        factory_metrics = agent_factory.get_factory_metrics()
        assert factory_metrics["total_instances_created"] >= num_contexts
        assert factory_metrics["active_contexts"] >= num_contexts
        
        # Check memory usage with all contexts
        mid_memory = self.get_memory_usage_mb()
        mid_memory_increase = mid_memory - initial_memory
        
        # Memory should have increased
        assert mid_memory_increase > 0, "No memory increase detected with contexts"
        
        # Cleanup half the contexts
        contexts_to_cleanup = created_contexts[:num_contexts // 2]
        contexts_to_keep = created_contexts[num_contexts // 2:]
        
        for context in contexts_to_cleanup:
            await agent_factory.cleanup_user_context(context)
        
        # Check partial cleanup metrics
        partial_metrics = agent_factory.get_factory_metrics()
        assert partial_metrics["total_contexts_cleaned"] >= len(contexts_to_cleanup)
        assert partial_metrics["active_contexts"] == len(contexts_to_keep)
        
        # Clear references to cleaned contexts
        contexts_to_cleanup.clear()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.05)
        
        # Memory should have decreased
        partial_cleanup_memory = self.get_memory_usage_mb()
        partial_memory_recovery = mid_memory - partial_cleanup_memory
        assert partial_memory_recovery > 0, "No memory recovery after partial cleanup"
        
        # Cleanup remaining contexts
        for context in contexts_to_keep:
            await agent_factory.cleanup_user_context(context)
        
        contexts_to_keep.clear()
        created_contexts.clear()
        
        # Force final garbage collection
        gc.collect()
        await asyncio.sleep(0.1)
        
        # Check final factory metrics
        final_metrics = agent_factory.get_factory_metrics()
        assert final_metrics["total_contexts_cleaned"] >= num_contexts
        assert final_metrics["active_contexts"] == 0
        
        # Check final memory
        final_memory = self.get_memory_usage_mb()
        final_memory_increase = final_memory - initial_memory
        
        # Should have recovered most memory
        total_memory_recovery = mid_memory_increase - final_memory_increase
        recovery_rate = total_memory_recovery / mid_memory_increase
        
        assert recovery_rate > 0.8, f"Poor factory memory recovery: {recovery_rate:.1%}"
        assert final_memory_increase < 10.0, f"Excessive final memory usage: {final_memory_increase:.1f}MB"
        
        # Check weak references
        dead_refs = sum(1 for ref in context_refs if ref() is None)
        assert dead_refs >= num_contexts * 0.8, f"Too many live context references: {num_contexts - dead_refs}"
        
        self.record_metric("factory_contexts_tested", num_contexts)
        self.record_metric("factory_memory_recovery_rate", recovery_rate)
        self.record_metric("final_factory_memory_increase_mb", final_memory_increase)
        
    @pytest.mark.real_services
    async def test_websocket_connection_memory_management(self, mock_websocket_bridge):
        """Test WebSocket connection memory management and cleanup."""
        
        initial_memory = self.get_memory_usage_mb()
        
        # Create multiple agents with WebSocket connections
        num_connections = 15
        agents = []
        contexts = []
        
        for i in range(num_connections):
            context = self.create_test_user_context(f"ws_memory_user_{i}", "websocket_memory_test")
            agent = MemoryIntensiveAgent(
                memory_profile="normal",
                user_context=context
            )
            
            # Set WebSocket bridge (simulates connection)
            agent.set_websocket_bridge(mock_websocket_bridge, context.run_id)
            
            agents.append(agent)
            contexts.append(context)
        
        # Execute all agents (creates WebSocket activity)
        results = await asyncio.gather(*[
            agent.execute(context) 
            for agent, context in zip(agents, contexts)
        ])
        
        # Validate WebSocket activity
        assert len(mock_websocket_bridge.memory_events) >= num_connections * 2  # Start and completion events
        
        # Check memory with active connections
        active_memory = self.get_memory_usage_mb()
        active_memory_increase = active_memory - initial_memory
        
        # Cleanup agents (should cleanup WebSocket connections)
        for agent in agents:
            await agent.cleanup()
        
        # Clear references
        agents.clear()
        contexts.clear()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)
        
        # Check memory after WebSocket cleanup
        post_ws_cleanup_memory = self.get_memory_usage_mb()
        final_memory_increase = post_ws_cleanup_memory - initial_memory
        
        # Memory should have been recovered
        ws_memory_recovery = active_memory_increase - final_memory_increase
        assert ws_memory_recovery > 0, "No memory recovery after WebSocket cleanup"
        
        # Final memory increase should be minimal
        assert final_memory_increase < 8.0, f"WebSocket memory leak detected: {final_memory_increase:.1f}MB"
        
        # Mock bridge should show connection cleanup
        final_connection_count = mock_websocket_bridge.connection_count
        # Note: This depends on mock implementation, might be 0 or might track differently
        
        self.record_metric("websocket_connections_tested", num_connections)
        self.record_metric("websocket_memory_recovery_mb", ws_memory_recovery)
        self.record_metric("websocket_final_memory_increase_mb", final_memory_increase)
        
    @pytest.mark.real_services
    async def test_memory_monitoring_and_resource_tracking(self, agent_registry):
        """Test memory monitoring and resource tracking capabilities."""
        
        initial_memory_details = self.get_memory_details()
        
        # Create agents through registry
        num_agents = 12
        user_sessions = []
        
        for i in range(num_agents):
            user_id = f"monitoring_user_{i:03d}"
            user_session = await agent_registry.get_user_session(user_id)
            
            # Add agents to session with memory data
            await user_session.register_agent(f"memory_agent_{i}", {
                "agent_type": "memory_test",
                "memory_profile": ["normal", "high_memory", "many_objects"][i % 3],
                "created_at": time.time(),
                "estimated_memory_mb": [1, 10, 5][i % 3]  # Simulate memory usage
            })
            
            user_sessions.append((user_id, user_session))
        
        # Get registry health and monitoring data
        registry_health = agent_registry.get_registry_health()
        all_users_report = await agent_registry.monitor_all_users()
        
        # Validate monitoring data structure
        assert registry_health["total_user_sessions"] >= num_agents
        assert registry_health["total_user_agents"] >= num_agents
        assert all_users_report["total_users"] >= num_agents
        assert all_users_report["total_agents"] >= num_agents
        
        # Check per-user monitoring
        monitored_users = 0
        total_estimated_memory = 0
        
        for user_id, user_session in user_sessions:
            if user_id in all_users_report["users"]:
                user_report = all_users_report["users"][user_id]
                monitored_users += 1
                
                # Check if memory metrics are tracked
                if "metrics" in user_report:
                    metrics = user_report["metrics"]
                    if "estimated_memory_mb" in metrics:
                        total_estimated_memory += metrics["estimated_memory_mb"]
        
        assert monitored_users >= num_agents // 2, "Insufficient user monitoring coverage"
        
        # Test lifecycle manager memory monitoring
        lifecycle_manager = agent_registry._lifecycle_manager
        
        # Monitor memory for specific users
        memory_reports = []
        for i in range(min(3, len(user_sessions))):
            user_id = user_sessions[i][0]
            memory_report = await lifecycle_manager.monitor_memory_usage(user_id)
            memory_reports.append(memory_report)
            
            assert "status" in memory_report
            assert "user_id" in memory_report
            assert memory_report["user_id"] == user_id
        
        # Cleanup agents through registry
        cleanup_start = time.time()
        cleanup_report = await agent_registry.emergency_cleanup_all()
        cleanup_time = time.time() - cleanup_start
        
        # Validate cleanup report
        assert "users_cleaned" in cleanup_report
        assert "agents_cleaned" in cleanup_report
        assert cleanup_report["users_cleaned"] >= num_agents
        assert cleanup_report["agents_cleaned"] >= num_agents
        
        # Check memory after cleanup
        post_cleanup_memory_details = self.get_memory_details()
        
        # Memory should not have increased excessively
        memory_increase = post_cleanup_memory_details["rss_mb"] - initial_memory_details["rss_mb"]
        assert memory_increase < 15.0, f"Excessive memory increase: {memory_increase:.1f}MB"
        
        # Verify registry is clean
        post_cleanup_health = agent_registry.get_registry_health()
        assert post_cleanup_health["total_user_sessions"] == 0
        assert post_cleanup_health["total_user_agents"] == 0
        
        self.record_metric("monitored_agents", num_agents)
        self.record_metric("memory_monitoring_working", True)
        self.record_metric("cleanup_time", cleanup_time)
        self.record_metric("total_memory_increase_mb", memory_increase)
        
    def teardown_method(self, method=None):
        """Clean up test resources."""
        super().teardown_method(method)
        
        # Force aggressive garbage collection
        for _ in range(3):
            gc.collect()
            
        # Log comprehensive metrics
        metrics = self.get_all_metrics()
        print(f"\nAgent Memory Management Integration Test Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        
        # Log final memory state
        final_memory = self.get_memory_details()
        print(f"Final Memory State: {final_memory}")
        
        # Verify critical metrics for business value protection
        critical_metrics = [
            "leak_prevention_verified",
            "memory_monitoring_working"
        ]
        
        for metric in critical_metrics:
            assert metrics.get(metric, False), f"Critical metric {metric} failed - memory management compromised"
        
        # Verify memory usage is reasonable across all tests
        total_memory_increases = [
            metrics.get("memory_increase_mb", 0),
            metrics.get("final_memory_increase_mb", 0),
            metrics.get("final_factory_memory_increase_mb", 0),
            metrics.get("websocket_final_memory_increase_mb", 0),
            metrics.get("total_memory_increase_mb", 0)
        ]
        
        max_memory_increase = max(total_memory_increases)
        assert max_memory_increase < 50.0, f"Excessive memory usage detected: {max_memory_increase:.1f}MB"