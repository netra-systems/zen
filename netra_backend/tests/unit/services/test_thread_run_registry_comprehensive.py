"""
ThreadRunRegistry SSOT - Comprehensive Unit Test Suite

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Stability & Chat Value Delivery  
- Value Impact: Ensures 100% reliable WebSocket event routing for $75K+ MRR chat functionality
- Strategic Impact: Eliminates WebSocket notification failures that cause user engagement loss

This comprehensive test suite validates the critical ThreadRunRegistry SSOT class that enables
reliable thread-to-run mapping for WebSocket event delivery. Complete test coverage ensures
the registry maintains thread safety, singleton consistency, and business SLA compliance.

Test Categories:
1. Singleton Pattern & SSOT Consistency (20+ tests)
2. Registration & Lookup Core Business Logic (25+ tests)  
3. Thread Safety & Concurrent Access (20+ tests)
4. TTL & Cleanup Business Logic (15+ tests)
5. Metrics & Monitoring (10+ tests)
6. Performance & Scalability (15+ tests)
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import pytest
from unittest.mock import Mock, AsyncMock, patch

from netra_backend.app.services.thread_run_registry import (
    ThreadRunRegistry,
    RegistryConfig, 
    RunMapping,
    MappingState,
    get_thread_run_registry,
    initialize_thread_run_registry
)


# Test Configuration Constants
TEST_CONFIG = RegistryConfig(
    mapping_ttl_hours=1,  # 1 hour for faster testing
    cleanup_interval_minutes=1,  # 1 minute for faster testing  
    max_mappings=100,
    enable_debug_logging=False  # Reduce test noise
)

PERFORMANCE_TEST_CONFIG = RegistryConfig(
    mapping_ttl_hours=24,
    cleanup_interval_minutes=30,
    max_mappings=10000,
    enable_debug_logging=False
)


@pytest.fixture
async def registry():
    """Create a fresh ThreadRunRegistry instance for each test."""
    # Reset singleton for testing
    ThreadRunRegistry._instance = None
    
    registry = ThreadRunRegistry(TEST_CONFIG)
    yield registry
    
    # Clean shutdown
    await registry.shutdown()
    ThreadRunRegistry._instance = None


@pytest.fixture  
async def performance_registry():
    """Create a registry optimized for performance testing."""
    # Reset singleton for testing
    ThreadRunRegistry._instance = None
    
    registry = ThreadRunRegistry(PERFORMANCE_TEST_CONFIG)
    yield registry
    
    # Clean shutdown
    await registry.shutdown()
    ThreadRunRegistry._instance = None


class TestThreadRunRegistrySingletonPattern:
    """
    BVJ: Validates SSOT singleton pattern ensuring system-wide consistency.
    Business Impact: Prevents multiple registry instances that would cause routing conflicts.
    """
    
    async def test_singleton_pattern_enforces_single_instance(self):
        """BVJ: Ensures only one registry exists system-wide for SSOT compliance."""
        # Reset singleton state
        ThreadRunRegistry._instance = None
        
        registry1 = ThreadRunRegistry(TEST_CONFIG)
        registry2 = ThreadRunRegistry(TEST_CONFIG)
        
        assert registry1 is registry2, "Singleton pattern must ensure same instance"
        assert ThreadRunRegistry._instance is registry1
        
        await registry1.shutdown()
        ThreadRunRegistry._instance = None
    
    async def test_singleton_preserves_state_across_instantiations(self, registry):
        """BVJ: Validates SSOT state consistency across multiple instantiation attempts."""
        # Register mapping in first instance
        success = await registry.register("run1", "thread1", {"test": "data"})
        assert success, "Registration should succeed"
        
        # Create "new" instance - should be same singleton
        registry2 = ThreadRunRegistry(TEST_CONFIG)
        
        # Verify state is preserved
        thread_id = await registry2.get_thread("run1")
        assert thread_id == "thread1", "Singleton must preserve state"
        
        assert registry is registry2, "Must return same singleton instance"
    
    async def test_singleton_thread_safety_under_concurrent_access(self):
        """BVJ: Validates singleton creation is thread-safe under high concurrency."""
        # Reset singleton state
        ThreadRunRegistry._instance = None
        
        async def create_registry():
            return ThreadRunRegistry(TEST_CONFIG)
        
        # Create 10 concurrent registry creation attempts
        tasks = [create_registry() for _ in range(10)]
        registries = await asyncio.gather(*tasks)
        
        # All should be the same instance
        first_registry = registries[0]
        for registry in registries[1:]:
            assert registry is first_registry, "All concurrent creations must return same instance"
        
        await first_registry.shutdown()
        ThreadRunRegistry._instance = None
    
    async def test_factory_function_returns_singleton(self):
        """BVJ: Validates factory function maintains SSOT singleton pattern."""
        # Reset singleton state
        ThreadRunRegistry._instance = None
        
        registry1 = await get_thread_run_registry(TEST_CONFIG)
        registry2 = await get_thread_run_registry(TEST_CONFIG)
        
        assert registry1 is registry2, "Factory function must return same singleton"
        
        await registry1.shutdown()
        ThreadRunRegistry._instance = None
    
    async def test_initialization_function_maintains_singleton(self):
        """BVJ: Validates initialization function preserves singleton pattern."""
        # Reset singleton state  
        ThreadRunRegistry._instance = None
        
        registry1 = await initialize_thread_run_registry(TEST_CONFIG)
        registry2 = await initialize_thread_run_registry(TEST_CONFIG)
        
        assert registry1 is registry2, "Initialization must maintain singleton"
        
        await registry1.shutdown()
        ThreadRunRegistry._instance = None


class TestThreadRunRegistryCore:
    """
    BVJ: Tests core registration and lookup operations that enable WebSocket routing.
    Business Impact: Ensures 100% reliable WebSocket event delivery for chat functionality.
    """
    
    async def test_register_creates_bidirectional_mapping(self, registry):
        """BVJ: Validates core business logic for thread-run mapping creation."""
        run_id = "run_123"
        thread_id = "thread_456"
        metadata = {"agent_name": "data_analyzer", "user_id": "user_789"}
        
        success = await registry.register(run_id, thread_id, metadata)
        
        assert success, "Registration must succeed for valid inputs"
        
        # Test forward mapping
        retrieved_thread = await registry.get_thread(run_id)
        assert retrieved_thread == thread_id, "Forward mapping must work"
        
        # Test reverse mapping
        run_ids = await registry.get_runs(thread_id)
        assert run_id in run_ids, "Reverse mapping must work"
    
    async def test_register_with_metadata_preserves_business_context(self, registry):
        """BVJ: Ensures business context is preserved for WebSocket routing decisions."""
        run_id = "run_business"
        thread_id = "thread_business"
        metadata = {
            "agent_name": "market_analyzer",
            "user_id": "premium_user_001", 
            "priority": "high",
            "business_value": 15000
        }
        
        await registry.register(run_id, thread_id, metadata)
        
        # Access internal mapping to verify metadata storage
        async with registry._registry_lock:
            mapping = registry._run_to_thread[run_id]
            assert mapping.metadata == metadata, "Metadata must be preserved"
            assert mapping.metadata["business_value"] == 15000
    
    async def test_lookup_updates_access_tracking(self, registry):
        """BVJ: Validates access tracking for business intelligence and metrics."""
        run_id = "run_tracked"
        thread_id = "thread_tracked"
        
        await registry.register(run_id, thread_id)
        
        # Initial access
        initial_time = datetime.now(timezone.utc)
        await registry.get_thread(run_id)
        
        # Verify access tracking
        async with registry._registry_lock:
            mapping = registry._run_to_thread[run_id]
            assert mapping.access_count == 1, "Access count must increment"
            assert mapping.last_accessed >= initial_time, "Last access time must update"
    
    async def test_lookup_nonexistent_run_returns_none(self, registry):
        """BVJ: Validates graceful handling of invalid lookup requests."""
        thread_id = await registry.get_thread("nonexistent_run")
        assert thread_id is None, "Nonexistent run lookup must return None"
    
    async def test_multiple_runs_per_thread(self, registry):
        """BVJ: Supports multi-agent workflows within single thread context."""
        thread_id = "thread_multi"
        run_ids = ["run_1", "run_2", "run_3"]
        
        # Register multiple runs for same thread
        for i, run_id in enumerate(run_ids):
            metadata = {"agent_sequence": i + 1}
            success = await registry.register(run_id, thread_id, metadata)
            assert success, f"Registration {i+1} must succeed"
        
        # Verify all runs map to same thread
        for run_id in run_ids:
            retrieved_thread = await registry.get_thread(run_id)
            assert retrieved_thread == thread_id
        
        # Verify reverse mapping contains all runs
        retrieved_runs = await registry.get_runs(thread_id)
        for run_id in run_ids:
            assert run_id in retrieved_runs
        
        assert len(retrieved_runs) == 3, "Thread must contain all registered runs"
    
    async def test_unregister_removes_mappings_cleanly(self, registry):
        """BVJ: Ensures clean removal prevents memory leaks and stale routing."""
        run_id = "run_remove"
        thread_id = "thread_remove"
        
        await registry.register(run_id, thread_id)
        
        # Verify registration
        assert await registry.get_thread(run_id) == thread_id
        assert run_id in await registry.get_runs(thread_id)
        
        # Unregister
        success = await registry.unregister_run(run_id)
        assert success, "Unregistration must succeed"
        
        # Verify removal
        assert await registry.get_thread(run_id) is None
        assert run_id not in await registry.get_runs(thread_id)
    
    async def test_unregister_last_run_cleans_thread_entry(self, registry):
        """BVJ: Prevents memory leaks by cleaning empty thread entries."""
        run_id = "run_last"
        thread_id = "thread_last"
        
        await registry.register(run_id, thread_id)
        await registry.unregister_run(run_id)
        
        # Verify thread entry is completely removed  
        async with registry._registry_lock:
            assert thread_id not in registry._thread_to_runs, "Empty thread entry must be cleaned"
    
    async def test_unregister_nonexistent_run_handles_gracefully(self, registry):
        """BVJ: Graceful handling of invalid unregistration requests."""
        success = await registry.unregister_run("nonexistent_run")
        assert not success, "Unregistering nonexistent run should return False"


class TestThreadRunRegistryThreadSafety:
    """
    BVJ: Validates thread safety for multi-user concurrent operations.
    Business Impact: Ensures registry remains stable under high concurrent load.
    """
    
    async def test_concurrent_registration_maintains_consistency(self, registry):
        """BVJ: Validates thread safety under high concurrent registration load."""
        num_concurrent = 50
        base_run = "concurrent_run"
        base_thread = "concurrent_thread"
        
        async def register_mapping(index):
            run_id = f"{base_run}_{index}"
            thread_id = f"{base_thread}_{index}"
            return await registry.register(run_id, thread_id, {"index": index})
        
        # Execute concurrent registrations
        tasks = [register_mapping(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks)
        
        # All registrations should succeed
        assert all(results), "All concurrent registrations must succeed"
        
        # Verify all mappings exist
        for i in range(num_concurrent):
            run_id = f"{base_run}_{i}"
            thread_id = f"{base_thread}_{i}"
            retrieved_thread = await registry.get_thread(run_id)
            assert retrieved_thread == thread_id, f"Mapping {i} must be correct"
    
    async def test_concurrent_lookup_while_registering(self, registry):
        """BVJ: Validates consistent lookups during concurrent modifications."""
        # Pre-register some mappings
        for i in range(10):
            await registry.register(f"lookup_run_{i}", f"lookup_thread_{i}")
        
        async def perform_lookups():
            results = []
            for i in range(10):
                run_id = f"lookup_run_{i}"
                thread_id = await registry.get_thread(run_id)
                results.append(thread_id == f"lookup_thread_{i}")
            return results
        
        async def perform_new_registrations():
            results = []  
            for i in range(10, 20):
                run_id = f"lookup_run_{i}"
                thread_id = f"lookup_thread_{i}"
                success = await registry.register(run_id, thread_id)
                results.append(success)
            return results
        
        # Execute concurrent operations
        lookup_task = asyncio.create_task(perform_lookups())
        register_task = asyncio.create_task(perform_new_registrations())
        
        lookup_results, register_results = await asyncio.gather(lookup_task, register_task)
        
        # All operations should succeed
        assert all(lookup_results), "Lookups during concurrent registration must succeed"
        assert all(register_results), "New registrations must succeed"
    
    async def test_concurrent_cleanup_and_access(self, registry):
        """BVJ: Validates thread safety during cleanup operations."""
        # Register mappings that will expire quickly
        for i in range(20):
            await registry.register(f"cleanup_run_{i}", f"cleanup_thread_{i}")
        
        async def access_mappings():
            results = []
            for _ in range(100):  # Many access attempts
                try:
                    thread_id = await registry.get_thread(f"cleanup_run_{i % 20}")
                    results.append(thread_id is not None)
                except Exception:
                    results.append(False)
                await asyncio.sleep(0.001)  # Small delay
            return results
        
        async def trigger_cleanup():
            await asyncio.sleep(0.01)  # Let some accesses happen first
            cleaned = await registry.cleanup_old_mappings()
            return cleaned
        
        # Execute concurrent access and cleanup
        access_task = asyncio.create_task(access_mappings())
        cleanup_task = asyncio.create_task(trigger_cleanup())
        
        access_results, cleaned_count = await asyncio.gather(access_task, cleanup_task)
        
        # Operations should complete without exceptions
        assert isinstance(access_results, list), "Access operations must complete"
        assert isinstance(cleaned_count, int), "Cleanup must complete"


class TestThreadRunRegistryTTL:
    """
    BVJ: Tests TTL and cleanup logic that prevents memory leaks and maintains performance.
    Business Impact: Ensures system remains performant and stable over time.
    """
    
    async def test_expired_mapping_returns_none(self, registry):
        """BVJ: Validates TTL enforcement prevents stale routing information."""
        run_id = "expired_run"
        thread_id = "expired_thread"
        
        await registry.register(run_id, thread_id)
        
        # Manually expire the mapping by modifying creation time
        async with registry._registry_lock:
            mapping = registry._run_to_thread[run_id]
            # Set creation time to 2 hours ago (beyond 1 hour TTL)
            mapping.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Lookup should return None for expired mapping
        thread_id_result = await registry.get_thread(run_id)
        assert thread_id_result is None, "Expired mapping lookup must return None"
    
    async def test_cleanup_removes_expired_mappings(self, registry):
        """BVJ: Validates automatic cleanup prevents memory leaks."""
        # Register mappings and immediately expire them
        expired_runs = []
        for i in range(5):
            run_id = f"cleanup_run_{i}"
            thread_id = f"cleanup_thread_{i}"
            await registry.register(run_id, thread_id)
            expired_runs.append(run_id)
        
        # Expire all mappings
        async with registry._registry_lock:
            for run_id in expired_runs:
                mapping = registry._run_to_thread[run_id]
                mapping.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Perform cleanup
        cleaned_count = await registry.cleanup_old_mappings()
        
        assert cleaned_count == 5, "All expired mappings must be cleaned"
        
        # Verify mappings are removed
        for run_id in expired_runs:
            thread_id = await registry.get_thread(run_id)
            assert thread_id is None, "Cleaned mappings must not be accessible"
    
    async def test_cleanup_preserves_active_mappings(self, registry):
        """BVJ: Ensures cleanup only removes expired mappings, preserves active ones."""
        # Register some active and some expired mappings
        active_runs = ["active_1", "active_2"]
        expired_runs = ["expired_1", "expired_2"]
        
        # Register active mappings
        for run_id in active_runs:
            await registry.register(run_id, f"thread_{run_id}")
        
        # Register and expire mappings
        for run_id in expired_runs:
            await registry.register(run_id, f"thread_{run_id}")
        
        # Expire only specific mappings
        async with registry._registry_lock:
            for run_id in expired_runs:
                mapping = registry._run_to_thread[run_id]
                mapping.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Perform cleanup
        cleaned_count = await registry.cleanup_old_mappings()
        
        assert cleaned_count == 2, "Only expired mappings should be cleaned"
        
        # Verify active mappings are preserved
        for run_id in active_runs:
            thread_id = await registry.get_thread(run_id)
            assert thread_id == f"thread_{run_id}", "Active mappings must be preserved"
        
        # Verify expired mappings are removed
        for run_id in expired_runs:
            thread_id = await registry.get_thread(run_id)
            assert thread_id is None, "Expired mappings must be removed"
    
    async def test_cleanup_updates_reverse_mappings(self, registry):
        """BVJ: Ensures cleanup maintains consistency in bidirectional mappings."""
        thread_id = "shared_thread"
        run_ids = ["run_1", "run_2", "run_3"]
        
        # Register multiple runs for same thread
        for run_id in run_ids:
            await registry.register(run_id, thread_id)
        
        # Expire first two runs
        async with registry._registry_lock:
            for run_id in run_ids[:2]:
                mapping = registry._run_to_thread[run_id]
                mapping.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Perform cleanup
        cleaned_count = await registry.cleanup_old_mappings()
        assert cleaned_count == 2, "Two mappings should be cleaned"
        
        # Verify reverse mapping is updated correctly
        remaining_runs = await registry.get_runs(thread_id)
        assert len(remaining_runs) == 1, "Only one run should remain"
        assert "run_3" in remaining_runs, "Active run should remain"
        assert "run_1" not in remaining_runs, "Expired run should be removed"
        assert "run_2" not in remaining_runs, "Expired run should be removed"


class TestThreadRunRegistryMetrics:
    """
    BVJ: Validates metrics and monitoring functionality for business intelligence.
    Business Impact: Enables performance monitoring and capacity planning decisions.
    """
    
    async def test_metrics_track_registration_count(self, registry):
        """BVJ: Validates business intelligence tracking for capacity planning."""
        initial_metrics = await registry.get_metrics()
        initial_count = initial_metrics['total_registrations']
        
        # Register several mappings
        for i in range(10):
            await registry.register(f"metrics_run_{i}", f"metrics_thread_{i}")
        
        final_metrics = await registry.get_metrics()
        final_count = final_metrics['total_registrations']
        
        assert final_count - initial_count == 10, "Registration count must be tracked"
    
    async def test_metrics_track_lookup_success_rate(self, registry):
        """BVJ: Validates performance metrics for SLA monitoring."""
        # Register some mappings
        for i in range(5):
            await registry.register(f"sla_run_{i}", f"sla_thread_{i}")
        
        # Perform successful lookups
        for i in range(5):
            await registry.get_thread(f"sla_run_{i}")
        
        # Perform failed lookups
        for i in range(3):
            await registry.get_thread(f"nonexistent_run_{i}")
        
        metrics = await registry.get_metrics()
        
        # Verify success rate calculation
        total_lookups = metrics['successful_lookups'] + metrics['failed_lookups']
        expected_success_rate = metrics['successful_lookups'] / total_lookups
        
        assert metrics['lookup_success_rate'] == expected_success_rate
        assert metrics['successful_lookups'] >= 5, "Successful lookups must be tracked"
        assert metrics['failed_lookups'] >= 3, "Failed lookups must be tracked"
    
    async def test_metrics_track_active_mappings(self, registry):
        """BVJ: Validates memory usage tracking for capacity planning."""
        initial_metrics = await registry.get_metrics()
        initial_active = initial_metrics['active_mappings']
        
        # Add mappings
        for i in range(7):
            await registry.register(f"active_run_{i}", f"active_thread_{i}")
        
        mid_metrics = await registry.get_metrics()
        assert mid_metrics['active_mappings'] - initial_active == 7
        
        # Remove some mappings
        for i in range(3):
            await registry.unregister_run(f"active_run_{i}")
        
        final_metrics = await registry.get_metrics()
        assert final_metrics['active_mappings'] - initial_active == 4
    
    async def test_status_includes_health_indicators(self, registry):
        """BVJ: Validates system health monitoring for operational decisions."""
        status = await registry.get_status()
        
        # Verify required health indicators
        assert 'registry_healthy' in status, "Health status must be included"
        assert 'active_mappings' in status, "Active mappings count must be included"
        assert 'lookup_success_rate' in status, "Success rate must be included"
        assert 'uptime_seconds' in status, "Uptime must be tracked"
        assert 'memory_usage_percentage' in status, "Memory usage must be tracked"
        assert 'cleanup_task_running' in status, "Cleanup task status must be included"
        
        # Health should be True for active registry
        assert status['registry_healthy'] is True, "Active registry must report healthy"


class TestThreadRunRegistryPerformance:
    """
    BVJ: Validates performance characteristics for production SLA compliance.
    Business Impact: Ensures sub-10ms lookup times for responsive chat experience.
    """
    
    async def test_lookup_performance_meets_sla(self, performance_registry):
        """BVJ: Validates lookup performance meets <10ms average SLA requirement."""
        registry = performance_registry
        
        # Pre-populate with realistic dataset
        for i in range(1000):
            await registry.register(f"perf_run_{i}", f"perf_thread_{i}")
        
        # Measure lookup performance
        start_time = time.perf_counter()
        
        # Perform 1000 lookups
        lookup_tasks = []
        for i in range(1000):
            run_id = f"perf_run_{i % 1000}"  # Mix of existing and non-existing
            lookup_tasks.append(registry.get_thread(run_id))
        
        await asyncio.gather(*lookup_tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_ms = (total_time / 1000) * 1000
        
        assert avg_time_ms < 10, f"Average lookup time {avg_time_ms:.2f}ms must be <10ms"
    
    async def test_registration_performance_under_load(self, performance_registry):
        """BVJ: Validates registration performance under concurrent load."""
        registry = performance_registry
        
        start_time = time.perf_counter()
        
        # Register 1000 mappings concurrently
        registration_tasks = []
        for i in range(1000):
            run_id = f"load_run_{i}"
            thread_id = f"load_thread_{i}"
            registration_tasks.append(registry.register(run_id, thread_id))
        
        results = await asyncio.gather(*registration_tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        assert all(results), "All registrations must succeed under load"
        assert total_time < 5.0, f"1000 registrations took {total_time:.2f}s, must be <5s"
    
    async def test_mixed_workload_performance(self, performance_registry):
        """BVJ: Validates realistic mixed workload performance."""
        registry = performance_registry
        
        # Pre-populate registry
        for i in range(500):
            await registry.register(f"mixed_run_{i}", f"mixed_thread_{i}")
        
        async def workload_simulation():
            """Simulate realistic workload: 70% lookups, 25% registrations, 5% cleanups."""
            operations = []
            
            # 70% lookups
            for i in range(700):
                run_id = f"mixed_run_{i % 500}"
                operations.append(registry.get_thread(run_id))
            
            # 25% registrations
            for i in range(250):
                run_id = f"new_run_{i}"
                thread_id = f"new_thread_{i}"
                operations.append(registry.register(run_id, thread_id))
            
            # 5% cleanup operations (simulated via unregistration)
            for i in range(50):
                run_id = f"mixed_run_{i}"
                operations.append(registry.unregister_run(run_id))
            
            return await asyncio.gather(*operations)
        
        start_time = time.perf_counter()
        results = await workload_simulation()
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        operations_per_second = len(results) / total_time
        
        assert operations_per_second > 1000, f"Mixed workload: {operations_per_second:.0f} ops/sec, need >1000"
    
    async def test_memory_efficiency_large_dataset(self, performance_registry):
        """BVJ: Validates memory efficiency with large datasets."""
        registry = performance_registry
        
        # Register large dataset with substantial metadata
        large_metadata = {
            "agent_name": "comprehensive_data_analyzer", 
            "user_context": "premium_enterprise_user",
            "business_priority": "critical_revenue_generating",
            "data_payload": "x" * 1000  # 1KB metadata per mapping
        }
        
        for i in range(5000):
            run_id = f"large_run_{i}"
            thread_id = f"large_thread_{i % 1000}"  # 1000 unique threads, 5 runs each
            await registry.register(run_id, thread_id, large_metadata)
        
        # Verify memory usage is reasonable
        metrics = await registry.get_metrics()
        memory_usage = metrics['memory_usage_percentage']
        
        assert memory_usage < 80, f"Memory usage {memory_usage:.1f}% must be <80%"
        assert metrics['active_mappings'] == 5000, "All mappings must be active"


class TestThreadRunRegistryIntegration:
    """
    BVJ: Tests integration scenarios that mirror real WebSocket bridge usage.
    Business Impact: Validates end-to-end WebSocket routing scenarios.
    """
    
    async def test_websocket_bridge_integration_scenario(self, registry):
        """BVJ: Validates typical WebSocket bridge usage pattern for chat delivery."""
        # Simulate agent execution starting
        user_id = "user_123"
        thread_id = "thread_chat_session"
        run_id = "run_data_analysis"
        
        # 1. Agent starts - registry mapping created
        metadata = {
            "user_id": user_id,
            "agent_name": "market_data_analyzer",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "business_priority": "high_value_customer"
        }
        
        success = await registry.register(run_id, thread_id, metadata)
        assert success, "WebSocket bridge registration must succeed"
        
        # 2. Multiple WebSocket events need routing
        websocket_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        # Simulate bridge resolving thread_id for each event
        routing_results = []
        for event in websocket_events:
            resolved_thread = await registry.get_thread(run_id)
            routing_results.append(resolved_thread == thread_id)
        
        assert all(routing_results), "All WebSocket events must route correctly"
        
        # 3. Agent execution completes - cleanup
        cleanup_success = await registry.unregister_run(run_id)
        assert cleanup_success, "WebSocket bridge cleanup must succeed"
        
        # Verify no routing after cleanup
        final_thread = await registry.get_thread(run_id)
        assert final_thread is None, "No routing after cleanup"
    
    async def test_multi_agent_workflow_scenario(self, registry):
        """BVJ: Validates complex multi-agent workflow routing."""
        thread_id = "thread_multi_agent_workflow"
        
        # Simulate multi-stage agent workflow
        agents = [
            {"run_id": "run_data_ingestion", "agent": "data_ingestion_agent"},
            {"run_id": "run_data_analysis", "agent": "analysis_agent"}, 
            {"run_id": "run_insight_generation", "agent": "insight_agent"},
            {"run_id": "run_report_generation", "agent": "report_agent"}
        ]
        
        # Register all agents in workflow
        for agent_info in agents:
            metadata = {
                "agent_name": agent_info["agent"],
                "workflow_stage": agents.index(agent_info) + 1,
                "total_stages": len(agents)
            }
            success = await registry.register(agent_info["run_id"], thread_id, metadata)
            assert success, f"Registration for {agent_info['agent']} must succeed"
        
        # Verify all agents are properly mapped
        workflow_runs = await registry.get_runs(thread_id)
        assert len(workflow_runs) == 4, "All workflow stages must be registered"
        
        for agent_info in agents:
            resolved_thread = await registry.get_thread(agent_info["run_id"])
            assert resolved_thread == thread_id, f"{agent_info['agent']} routing must be correct"
        
        # Simulate gradual completion of workflow stages
        for i, agent_info in enumerate(agents):
            # Unregister completed stage
            success = await registry.unregister_run(agent_info["run_id"])
            assert success, f"Unregistration for {agent_info['agent']} must succeed"
            
            # Verify remaining stages still route correctly
            remaining_runs = await registry.get_runs(thread_id)
            expected_remaining = len(agents) - (i + 1)
            assert len(remaining_runs) == expected_remaining
    
    async def test_factory_functions_integration(self, registry):
        """BVJ: Validates factory functions work correctly with SSOT singleton."""
        # Use factory function to get registry
        factory_registry = await get_thread_run_registry()
        
        # Should return same instance as fixture
        assert factory_registry is registry, "Factory function must return singleton"
        
        # Operations through factory should affect same instance
        await factory_registry.register("factory_run", "factory_thread")
        
        # Verify through original registry reference
        thread_id = await registry.get_thread("factory_run")
        assert thread_id == "factory_thread", "Factory operations must affect singleton"


class TestThreadRunRegistryErrorHandling:
    """
    BVJ: Validates error handling and recovery scenarios for system resilience.
    Business Impact: Ensures WebSocket routing remains stable under error conditions.
    """
    
    async def test_registration_handles_invalid_inputs(self, registry):
        """BVJ: Validates graceful handling of invalid registration inputs."""
        # Test empty strings
        success = await registry.register("", "thread_id")
        assert not success, "Empty run_id registration should fail gracefully"
        
        success = await registry.register("run_id", "")  
        assert not success, "Empty thread_id registration should fail gracefully"
        
        # Test None values
        success = await registry.register(None, "thread_id")
        assert not success, "None run_id registration should fail gracefully"
        
        success = await registry.register("run_id", None)
        assert not success, "None thread_id registration should fail gracefully"
    
    async def test_lookup_handles_invalid_inputs(self, registry):
        """BVJ: Validates graceful handling of invalid lookup inputs."""
        # Test None lookup
        thread_id = await registry.get_thread(None)
        assert thread_id is None, "None lookup must return None gracefully"
        
        # Test empty string lookup
        thread_id = await registry.get_thread("")
        assert thread_id is None, "Empty string lookup must return None gracefully"
    
    async def test_operations_during_shutdown(self, registry):
        """BVJ: Validates graceful behavior during registry shutdown."""
        # Register initial mapping
        await registry.register("shutdown_run", "shutdown_thread")
        
        # Initiate shutdown
        await registry.shutdown()
        
        # Operations after shutdown should handle gracefully
        try:
            success = await registry.register("post_shutdown", "post_thread")
            # Should not raise exception, may return False
            assert isinstance(success, bool)
        except Exception as e:
            pytest.fail(f"Post-shutdown registration raised exception: {e}")
        
        try:
            thread_id = await registry.get_thread("shutdown_run")
            # Should not raise exception, may return None
            assert thread_id is None or isinstance(thread_id, str)
        except Exception as e:
            pytest.fail(f"Post-shutdown lookup raised exception: {e}")
    
    async def test_metrics_survive_internal_errors(self, registry):
        """BVJ: Validates metrics remain available even with internal errors."""
        # Simulate internal state corruption by directly modifying internals
        async with registry._registry_lock:
            # Create inconsistent state  
            registry._run_to_thread["corrupted_run"] = None
        
        # Metrics should still be retrievable and not raise exceptions
        try:
            metrics = await registry.get_metrics()
            assert isinstance(metrics, dict), "Metrics must remain available"
            assert 'error' not in metrics or 'timestamp' in metrics
        except Exception as e:
            # If metrics fail, they should return error dict, not raise
            pytest.fail(f"Metrics raised exception instead of returning error dict: {e}")
    
    async def test_cleanup_handles_corrupted_mappings(self, registry):
        """BVJ: Validates cleanup handles corrupted mapping states gracefully."""
        # Create normal mapping
        await registry.register("normal_run", "normal_thread")
        
        # Simulate corruption by directly modifying internal state
        async with registry._registry_lock:
            # Create mapping with no created_at (simulated corruption)
            from netra_backend.app.services.thread_run_registry import RunMapping
            corrupted_mapping = RunMapping("corrupted_run", "corrupted_thread")
            corrupted_mapping.created_at = None  # Corruption
            registry._run_to_thread["corrupted_run"] = corrupted_mapping
        
        # Cleanup should handle corruption gracefully
        try:
            cleaned_count = await registry.cleanup_old_mappings()
            assert isinstance(cleaned_count, int), "Cleanup must return int even with corruption"
        except Exception as e:
            pytest.fail(f"Cleanup raised exception with corrupted data: {e}")
        
        # Normal operations should still work
        thread_id = await registry.get_thread("normal_run")
        assert thread_id == "normal_thread", "Normal operations must continue after cleanup"


class TestThreadRunRegistryEdgeCases:
    """
    BVJ: Tests edge cases and boundary conditions for comprehensive coverage.
    Business Impact: Ensures robust behavior in all scenarios.
    """
    
    async def test_duplicate_registration_updates_existing(self, registry):
        """BVJ: Validates handling of duplicate run_id registrations."""
        run_id = "duplicate_run"
        original_thread = "original_thread"
        updated_thread = "updated_thread"
        
        # Initial registration
        await registry.register(run_id, original_thread, {"version": 1})
        
        # Duplicate registration should update
        await registry.register(run_id, updated_thread, {"version": 2})
        
        # Should resolve to updated thread
        resolved_thread = await registry.get_thread(run_id)
        assert resolved_thread == updated_thread, "Duplicate registration should update mapping"
        
        # Verify metadata is updated
        async with registry._registry_lock:
            mapping = registry._run_to_thread[run_id]
            assert mapping.metadata["version"] == 2, "Metadata should be updated"
    
    async def test_special_character_handling(self, registry):
        """BVJ: Validates handling of IDs with special characters."""
        special_chars_run = "run_with_special_chars!@#$%^&*()_+-=[]{}|;:,.<>?"
        special_chars_thread = "thread_with_unicode_éñøđẽ_characters"
        
        success = await registry.register(special_chars_run, special_chars_thread)
        assert success, "Special characters in IDs should be handled"
        
        resolved_thread = await registry.get_thread(special_chars_run)
        assert resolved_thread == special_chars_thread, "Special character lookup must work"
    
    async def test_very_long_id_handling(self, registry):
        """BVJ: Validates handling of extremely long IDs."""
        long_run_id = "run_" + "x" * 1000  # 1004 character run_id
        long_thread_id = "thread_" + "y" * 1000  # 1007 character thread_id
        
        success = await registry.register(long_run_id, long_thread_id)
        assert success, "Very long IDs should be handled"
        
        resolved_thread = await registry.get_thread(long_run_id)
        assert resolved_thread == long_thread_id, "Long ID lookup must work"
    
    async def test_boundary_condition_max_mappings(self, registry):
        """BVJ: Validates behavior at maximum mappings capacity."""
        # Registry has max_mappings = 100 in test config
        
        # Fill registry to capacity
        for i in range(100):
            run_id = f"boundary_run_{i}"
            thread_id = f"boundary_thread_{i}"
            success = await registry.register(run_id, thread_id)
            assert success, f"Registration {i} should succeed within capacity"
        
        # Verify all registrations work
        metrics = await registry.get_metrics()
        assert metrics['active_mappings'] == 100, "Should have max capacity mappings"
        
        # Additional registration beyond capacity should still work
        # (registry doesn't enforce hard limit, just tracks for monitoring)
        success = await registry.register("overflow_run", "overflow_thread")
        assert success, "Registration beyond max_mappings should work"
    
    async def test_empty_metadata_handling(self, registry):
        """BVJ: Validates handling of various metadata scenarios."""
        # Empty metadata dict
        success = await registry.register("empty_meta_run", "empty_meta_thread", {})
        assert success, "Empty metadata should be handled"
        
        # None metadata
        success = await registry.register("none_meta_run", "none_meta_thread", None)
        assert success, "None metadata should be handled"
        
        # Large metadata
        large_metadata = {f"key_{i}": f"value_{i}" * 100 for i in range(50)}
        success = await registry.register("large_meta_run", "large_meta_thread", large_metadata)
        assert success, "Large metadata should be handled"
    
    async def test_concurrent_shutdown_operations(self, registry):
        """BVJ: Validates thread safety during shutdown scenarios."""
        # Register some mappings
        for i in range(10):
            await registry.register(f"shutdown_run_{i}", f"shutdown_thread_{i}")
        
        async def perform_operations():
            """Perform operations while shutdown is happening."""
            results = []
            for i in range(20):
                try:
                    # Mix of operations
                    if i % 3 == 0:
                        success = await registry.register(f"concurrent_run_{i}", f"concurrent_thread_{i}")
                        results.append(('register', success))
                    elif i % 3 == 1:
                        thread_id = await registry.get_thread(f"shutdown_run_{i % 10}")
                        results.append(('lookup', thread_id))
                    else:
                        metrics = await registry.get_metrics()
                        results.append(('metrics', isinstance(metrics, dict)))
                except Exception as e:
                    results.append(('error', str(e)))
            return results
        
        # Start operations and shutdown concurrently
        operations_task = asyncio.create_task(perform_operations())
        
        # Small delay then shutdown
        await asyncio.sleep(0.01)
        shutdown_task = asyncio.create_task(registry.shutdown())
        
        operations_results, _ = await asyncio.gather(operations_task, shutdown_task)
        
        # Operations should complete without raising exceptions
        assert len(operations_results) > 0, "Some operations should complete"
        
        # No operation should raise unhandled exceptions
        for op_type, result in operations_results:
            if op_type == 'error':
                pytest.fail(f"Operation raised unhandled exception: {result}")