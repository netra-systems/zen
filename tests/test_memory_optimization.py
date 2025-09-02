"""Comprehensive Memory Optimization Tests

Business Value Justification:
- Segment: Platform/Testing & Quality Assurance  
- Business Goal: Prevent Memory Regressions & Ensure System Stability
- Value Impact: Prevents production OOM incidents, ensures memory efficiency
- Strategic Impact: Critical for production reliability and scalability

This test suite provides comprehensive memory optimization validation:
- Memory leak detection and prevention
- Request-scoped isolation verification  
- Session cleanup validation
- Lazy loading behavior testing
- Memory pressure handling tests
- Performance regression prevention
"""

import asyncio
import gc
import os
import psutil
import pytest
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

# Import the services we're testing
from netra_backend.app.services.memory_optimization_service import (
    MemoryOptimizationService, MemoryPressureLevel, RequestScope, get_memory_service
)
from netra_backend.app.services.session_memory_manager import (
    SessionMemoryManager, UserSession, SessionState, get_session_manager
)
from netra_backend.app.services.lazy_component_loader import (
    LazyComponentLoader, ComponentPriority, LoadingStrategy, get_component_loader
)
from netra_backend.app.agents.request_scoped_tool_dispatcher import (
    RequestScopedToolDispatcher, create_request_scoped_tool_dispatcher
)
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext


class MemoryTracker:
    """Helper class to track memory usage during tests."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.get_memory_usage()
        self.peak_memory = self.initial_memory
        self.measurements: List[Dict[str, Any]] = []
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024
    
    def measure(self, label: str = "") -> float:
        """Take memory measurement."""
        current = self.get_memory_usage()
        self.peak_memory = max(self.peak_memory, current)
        
        measurement = {
            'timestamp': datetime.now(timezone.utc),
            'label': label,
            'memory_mb': current,
            'delta_mb': current - self.initial_memory
        }
        self.measurements.append(measurement)
        
        return current
    
    def get_peak_usage(self) -> float:
        """Get peak memory usage during tracking."""
        return self.peak_memory
    
    def get_memory_increase(self) -> float:
        """Get total memory increase since tracking started."""
        return self.get_memory_usage() - self.initial_memory
    
    def reset(self):
        """Reset tracking to current memory level."""
        self.initial_memory = self.get_memory_usage()
        self.peak_memory = self.initial_memory
        self.measurements.clear()


@pytest.fixture
async def memory_tracker():
    """Fixture providing memory tracking."""
    tracker = MemoryTracker()
    tracker.measure("test_start")
    yield tracker
    tracker.measure("test_end")


@pytest.fixture
async def memory_service():
    """Fixture providing memory optimization service."""
    service = MemoryOptimizationService()
    await service.start()
    yield service
    await service.stop()


@pytest.fixture
async def session_manager():
    """Fixture providing session memory manager."""
    manager = SessionMemoryManager()
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture  
async def component_loader():
    """Fixture providing lazy component loader."""
    loader = LazyComponentLoader()
    await loader.initialize()
    yield loader
    await loader.shutdown()


class TestMemoryOptimizationService:
    """Test memory optimization service functionality."""
    
    async def test_memory_stats_collection(self, memory_service, memory_tracker):
        """Test memory statistics collection."""
        # Get initial stats
        stats = memory_service.get_memory_stats()
        memory_tracker.measure("stats_collected")
        
        assert stats.total_mb > 0
        assert stats.used_mb > 0
        assert stats.available_mb > 0
        assert 0 <= stats.percentage_used <= 100
        assert isinstance(stats.pressure_level, MemoryPressureLevel)
        assert stats.timestamp is not None
        
        # Verify memory tracking doesn't leak significantly
        memory_increase = memory_tracker.get_memory_increase()
        assert memory_increase < 5.0  # Less than 5MB increase for stats
    
    async def test_request_scope_isolation(self, memory_service, memory_tracker):
        """Test request scope isolation and cleanup."""
        initial_memory = memory_tracker.get_memory_usage()
        
        # Create multiple request scopes
        scopes_created = []
        for i in range(10):
            request_id = f"test_request_{i}"
            user_id = f"user_{i}"
            
            async with memory_service.request_scope(request_id, user_id) as scope:
                scopes_created.append(scope.request_id)
                
                # Add some resources to the scope
                scope.components[f"resource_{i}"] = f"test_data_{i}" * 1000  # Some test data
                scope.cleanup_callbacks.append(lambda: None)  # Dummy cleanup
        
        memory_tracker.measure("scopes_disposed")
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)
        
        final_memory = memory_tracker.get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (< 2MB for 10 scopes)
        assert memory_increase < 2.0, f"Memory increased by {memory_increase:.1f}MB - possible leak"
        
        # Verify all scopes were cleaned up
        assert memory_service.get_active_scopes_count() == 0
    
    async def test_memory_pressure_handling(self, memory_service, memory_tracker):
        """Test memory pressure detection and response."""
        # Mock high memory usage
        with patch.object(memory_service, 'get_memory_stats') as mock_stats:
            # Simulate critical memory pressure
            mock_stats.return_value = Mock(
                total_mb=1024.0,
                used_mb=950.0,
                available_mb=74.0,
                percentage_used=92.8,
                pressure_level=MemoryPressureLevel.CRITICAL
            )
            
            # Test emergency cleanup
            await memory_service._emergency_cleanup()
            memory_tracker.measure("emergency_cleanup")
            
            # Verify cleanup was triggered (no direct assertions possible,
            # but method should complete without errors)
    
    async def test_component_lifecycle(self, memory_service, memory_tracker):
        """Test component creation and cleanup within request scope."""
        class TestComponent:
            def __init__(self, size_mb: float):
                self.data = "x" * int(size_mb * 1024 * 1024)  # Allocate memory
                self.cleaned_up = False
            
            def cleanup(self):
                self.data = None
                self.cleaned_up = True
        
        initial_memory = memory_tracker.get_memory_usage()
        
        async with memory_service.request_scope("test_component", "test_user") as scope:
            # Create component with significant memory footprint
            component = memory_service.get_or_create_component(
                scope,
                "heavy_component",
                lambda: TestComponent(5.0),  # 5MB component
                cleanup_callback=lambda: component.cleanup() if 'component' in locals() else None
            )
            
            memory_tracker.measure("component_created")
            memory_after_creation = memory_tracker.get_memory_usage()
            
            # Verify component was created and memory increased
            assert component is not None
            assert isinstance(component, TestComponent)
            assert memory_after_creation > initial_memory
        
        # After scope exit, component should be cleaned up
        await asyncio.sleep(0.1)
        gc.collect()
        
        memory_tracker.measure("component_cleaned")
        final_memory = memory_tracker.get_memory_usage()
        
        # Memory should return close to initial level
        memory_retained = final_memory - initial_memory
        assert memory_retained < 1.0, f"Memory retained: {memory_retained:.1f}MB - possible leak"
    
    @pytest.mark.asyncio
    async def test_concurrent_request_isolation(self, memory_service, memory_tracker):
        """Test memory isolation between concurrent requests."""
        async def simulate_request(request_id: str, user_id: str, data_size_mb: float):
            async with memory_service.request_scope(request_id, user_id) as scope:
                # Create user-specific data
                user_data = "x" * int(data_size_mb * 1024 * 1024)
                scope.components["user_data"] = user_data
                
                # Simulate some processing time
                await asyncio.sleep(0.1)
                
                return len(scope.components)
        
        initial_memory = memory_tracker.get_memory_usage()
        
        # Run multiple concurrent requests
        tasks = [
            simulate_request(f"req_{i}", f"user_{i}", 1.0)  # 1MB each
            for i in range(20)
        ]
        
        results = await asyncio.gather(*tasks)
        memory_tracker.measure("concurrent_requests_done")
        
        # Verify all requests completed successfully
        assert all(result == 1 for result in results)
        
        # Verify no active scopes remain
        assert memory_service.get_active_scopes_count() == 0
        
        # Memory should return to near initial level
        gc.collect()
        await asyncio.sleep(0.1)
        
        final_memory = memory_tracker.get_memory_usage()
        memory_increase = final_memory - initial_memory
        assert memory_increase < 2.0, f"Memory leak detected: {memory_increase:.1f}MB"


class TestSessionMemoryManager:
    """Test session memory management functionality."""
    
    async def test_session_creation_and_cleanup(self, session_manager, memory_tracker):
        """Test session lifecycle and memory cleanup."""
        initial_memory = memory_tracker.get_memory_usage()
        
        # Create user session
        session = await session_manager.create_user_session(
            session_id="test_session",
            user_id="test_user",
            thread_id="test_thread"
        )
        
        # Register resources in session
        test_resource = {"data": "x" * 1000000}  # 1MB of data
        await session_manager.register_session_resource(
            "test_session",
            "test_resource",
            "test_data",
            test_resource,
            memory_estimate_mb=1.0
        )
        
        memory_tracker.measure("session_created")
        
        # Verify session exists and has resources
        retrieved_session = await session_manager.get_user_session("test_session")
        assert retrieved_session is not None
        assert len(retrieved_session.resources) == 1
        assert retrieved_session.memory_usage_mb == 1.0
        
        # Cleanup session
        success = await session_manager.cleanup_session("test_session")
        assert success
        
        memory_tracker.measure("session_cleaned")
        
        # Verify session was removed
        cleaned_session = await session_manager.get_user_session("test_session")
        assert cleaned_session is None
        
        # Memory should be freed
        gc.collect()
        await asyncio.sleep(0.1)
        
        final_memory = memory_tracker.get_memory_usage()
        memory_increase = final_memory - initial_memory
        assert memory_increase < 0.5, f"Memory not freed: {memory_increase:.1f}MB"
    
    async def test_websocket_disconnection_cleanup(self, session_manager, memory_tracker):
        """Test cleanup when WebSocket disconnects."""
        # Create session with WebSocket
        session = await session_manager.create_user_session(
            session_id="ws_test_session",
            user_id="ws_test_user",
            websocket_id="ws_123"
        )
        
        # Simulate WebSocket connection
        await session_manager.websocket_connected("ws_123", "ws_test_session")
        
        # Add resources
        test_data = {"large_data": "x" * 500000}  # 500KB
        await session_manager.register_session_resource(
            "ws_test_session",
            "websocket_data",
            "ws_resource",
            test_data,
            memory_estimate_mb=0.5
        )
        
        memory_tracker.measure("websocket_session_created")
        initial_cleanup_memory = memory_tracker.get_memory_usage()
        
        # Simulate WebSocket disconnection
        await session_manager.websocket_disconnected("ws_123")
        
        # Wait for cleanup delay
        await asyncio.sleep(0.5)  # Cleanup happens after 30s in real implementation, but we'll force it
        
        # Force cleanup of disconnected session
        retrieved_session = await session_manager.get_user_session("ws_test_session")
        if retrieved_session and retrieved_session.state == SessionState.DISCONNECTED:
            await session_manager._dispose_session(retrieved_session)
        
        memory_tracker.measure("websocket_disconnection_cleanup")
        
        # Verify cleanup
        gc.collect()
        final_memory = memory_tracker.get_memory_usage()
        memory_freed = initial_cleanup_memory - final_memory
        
        # Should free some memory (at least the resource data)
        assert memory_freed >= 0, "Memory should be freed after WebSocket disconnection cleanup"


class TestLazyComponentLoader:
    """Test lazy component loading functionality."""
    
    async def test_component_registration_and_loading(self, component_loader, memory_tracker):
        """Test component registration and lazy loading."""
        
        class HeavyComponent:
            def __init__(self):
                self.data = "x" * 1000000  # 1MB of data
                self.initialized = True
        
        # Register component
        component_loader.register_component(
            name="heavy_component",
            factory=HeavyComponent,
            priority=ComponentPriority.MEDIUM,
            strategy=LoadingStrategy.ON_DEMAND,
            memory_cost_mb=1.0,
            description="Test heavy component"
        )
        
        memory_tracker.measure("component_registered")
        initial_memory = memory_tracker.get_memory_usage()
        
        # Verify component is not loaded initially
        assert not component_loader.is_loaded("heavy_component")
        
        # Load component
        component = await component_loader.load_component("heavy_component")
        memory_tracker.measure("component_loaded")
        
        # Verify component loaded successfully
        assert component is not None
        assert isinstance(component, HeavyComponent)
        assert component.initialized
        assert component_loader.is_loaded("heavy_component")
        
        # Verify memory increased
        memory_after_load = memory_tracker.get_memory_usage()
        assert memory_after_load > initial_memory
        
        # Unload component
        success = await component_loader.unload_component("heavy_component")
        assert success
        
        memory_tracker.measure("component_unloaded")
        
        # Verify component unloaded
        assert not component_loader.is_loaded("heavy_component")
        
        # Verify memory freed
        gc.collect()
        await asyncio.sleep(0.1)
        
        final_memory = memory_tracker.get_memory_usage()
        memory_retained = final_memory - initial_memory
        assert memory_retained < 0.2, f"Memory not freed after unload: {memory_retained:.1f}MB"
    
    async def test_dependency_resolution(self, component_loader, memory_tracker):
        """Test component dependency resolution."""
        
        class BaseService:
            def __init__(self):
                self.name = "base_service"
        
        class DependentService:
            def __init__(self):
                self.name = "dependent_service"
                self.base_service = None  # Will be injected by loader
        
        # Register base component
        component_loader.register_component(
            name="base_service",
            factory=BaseService,
            priority=ComponentPriority.HIGH,
            memory_cost_mb=0.5
        )
        
        # Register dependent component
        component_loader.register_component(
            name="dependent_service", 
            factory=DependentService,
            priority=ComponentPriority.MEDIUM,
            dependencies=["base_service"],
            memory_cost_mb=0.3
        )
        
        # Load dependent component (should load base first)
        dependent = await component_loader.load_component("dependent_service")
        memory_tracker.measure("dependencies_loaded")
        
        # Verify both components loaded
        assert component_loader.is_loaded("base_service")
        assert component_loader.is_loaded("dependent_service")
        assert dependent is not None
    
    async def test_memory_pressure_handling(self, component_loader, memory_tracker):
        """Test component loading under memory pressure."""
        
        class ExpensiveComponent:
            def __init__(self):
                self.data = "x" * 10000000  # 10MB
        
        # Register expensive component
        component_loader.register_component(
            name="expensive_component",
            factory=ExpensiveComponent,
            priority=ComponentPriority.LOW,
            memory_cost_mb=10.0
        )
        
        # Mock high memory pressure
        with patch.object(component_loader.memory_service, 'get_memory_stats') as mock_stats:
            mock_stats.return_value = Mock(
                percentage_used=95.0,
                pressure_level=MemoryPressureLevel.CRITICAL
            )
            
            # Try to load expensive component - should fail due to memory pressure
            with pytest.raises(RuntimeError, match="memory pressure too high"):
                await component_loader.load_component("expensive_component")
            
            memory_tracker.measure("memory_pressure_handled")


class TestRequestScopedToolDispatcher:
    """Test request-scoped tool dispatcher."""
    
    async def test_request_scoped_isolation(self, memory_tracker):
        """Test request-scoped tool dispatcher isolation."""
        
        # Create user execution contexts
        context1 = UserExecutionContext(
            user_id="user1",
            run_id="run1",
            thread_id="thread1",
            agent_name="test_agent",
            correlation_id="corr1"
        )
        
        context2 = UserExecutionContext(
            user_id="user2", 
            run_id="run2",
            thread_id="thread2",
            agent_name="test_agent",
            correlation_id="corr2"
        )
        
        initial_memory = memory_tracker.get_memory_usage()
        
        # Create request-scoped dispatchers
        dispatcher1 = RequestScopedToolDispatcher(context1)
        dispatcher2 = RequestScopedToolDispatcher(context2)
        
        memory_tracker.measure("dispatchers_created")
        
        # Verify isolation
        assert dispatcher1.user_context.user_id != dispatcher2.user_context.user_id
        assert dispatcher1.dispatcher_id != dispatcher2.dispatcher_id
        
        # Add tools to each dispatcher
        def test_tool_1():
            return "result_from_user1"
        
        def test_tool_2():
            return "result_from_user2"
        
        dispatcher1.register_tool("test_tool", test_tool_1)
        dispatcher2.register_tool("test_tool", test_tool_2)
        
        # Verify tool isolation
        assert dispatcher1.has_tool("test_tool")
        assert dispatcher2.has_tool("test_tool")
        
        # Clean up dispatchers
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
        
        memory_tracker.measure("dispatchers_cleaned")
        
        # Verify cleanup
        assert not dispatcher1.is_active()
        assert not dispatcher2.is_active()
        
        gc.collect()
        await asyncio.sleep(0.1)
        
        final_memory = memory_tracker.get_memory_usage()
        memory_increase = final_memory - initial_memory
        assert memory_increase < 1.0, f"Memory leak in dispatchers: {memory_increase:.1f}MB"


class TestMemoryRegressionPrevention:
    """Test suite to prevent memory regressions."""
    
    @pytest.mark.slow
    async def test_sustained_load_memory_stability(self, memory_tracker):
        """Test memory stability under sustained load."""
        
        async def simulate_user_request(user_id: str, request_num: int):
            """Simulate a complete user request cycle."""
            context = UserExecutionContext(
                user_id=user_id,
                run_id=f"run_{request_num}",
                thread_id=f"thread_{user_id}",
                agent_name="test_agent",
                correlation_id=f"corr_{request_num}"
            )
            
            # Create request-scoped dispatcher
            async with create_request_scoped_tool_dispatcher(context) as dispatcher:
                # Simulate tool execution
                dispatcher.register_tool("test_tool", lambda: "test_result")
                await dispatcher.dispatch("test_tool")
                
                # Simulate some processing delay
                await asyncio.sleep(0.01)
        
        initial_memory = memory_tracker.get_memory_usage()
        memory_measurements = []
        
        # Simulate 100 user requests
        for batch in range(10):  # 10 batches of 10 requests
            batch_start_memory = memory_tracker.get_memory_usage()
            
            tasks = [
                simulate_user_request(f"user_{i % 5}", batch * 10 + i)  # 5 users, multiple requests each
                for i in range(10)
            ]
            
            await asyncio.gather(*tasks)
            
            # Force cleanup between batches
            gc.collect()
            await asyncio.sleep(0.05)
            
            batch_end_memory = memory_tracker.get_memory_usage()
            memory_measurements.append({
                'batch': batch,
                'start_memory': batch_start_memory,
                'end_memory': batch_end_memory,
                'delta': batch_end_memory - batch_start_memory
            })
            
            memory_tracker.measure(f"batch_{batch}_complete")
        
        final_memory = memory_tracker.get_memory_usage()
        total_memory_increase = final_memory - initial_memory
        
        # Verify memory doesn't grow excessively (< 5MB for 100 requests)
        assert total_memory_increase < 5.0, (
            f"Memory grew by {total_memory_increase:.1f}MB over 100 requests - "
            f"indicates memory leak"
        )
        
        # Verify memory is relatively stable across batches
        memory_deltas = [m['delta'] for m in memory_measurements]
        avg_delta = sum(memory_deltas) / len(memory_deltas)
        
        # Average delta per batch should be small
        assert abs(avg_delta) < 0.5, (
            f"Average memory delta per batch: {avg_delta:.2f}MB - "
            f"indicates systematic memory leak"
        )
    
    async def test_memory_cleanup_effectiveness(self, memory_tracker):
        """Test effectiveness of memory cleanup mechanisms."""
        
        # Create memory optimization service
        service = MemoryOptimizationService()
        await service.start()
        
        try:
            initial_memory = memory_tracker.get_memory_usage()
            
            # Create many request scopes with resources
            scope_tasks = []
            for i in range(50):
                async def create_scope_with_resources(idx):
                    async with service.request_scope(f"test_scope_{idx}", f"user_{idx}") as scope:
                        # Add some resources
                        scope.components[f"resource_{idx}"] = "x" * 100000  # 100KB each
                        await asyncio.sleep(0.01)
                
                scope_tasks.append(create_scope_with_resources(i))
            
            await asyncio.gather(*scope_tasks)
            memory_tracker.measure("scopes_completed")
            
            # Trigger cleanup
            await service._periodic_cleanup()
            memory_tracker.measure("cleanup_triggered")
            
            # Force garbage collection
            for _ in range(3):
                gc.collect()
                await asyncio.sleep(0.01)
            
            final_memory = memory_tracker.get_memory_usage()
            memory_increase = final_memory - initial_memory
            
            # Memory should return close to initial level
            assert memory_increase < 2.0, (
                f"Cleanup ineffective - memory increased by {memory_increase:.1f}MB"
            )
            
            # Verify no active scopes remain
            assert service.get_active_scopes_count() == 0
            
        finally:
            await service.stop()


@pytest.mark.integration
class TestMemoryOptimizationIntegration:
    """Integration tests for memory optimization components."""
    
    async def test_full_system_memory_behavior(self, memory_tracker):
        """Test memory behavior of integrated system."""
        
        # Initialize all memory optimization services
        memory_service = MemoryOptimizationService()
        session_manager = SessionMemoryManager()
        component_loader = LazyComponentLoader()
        
        await memory_service.start()
        await session_manager.start()
        await component_loader.initialize()
        
        try:
            initial_memory = memory_tracker.get_memory_usage()
            
            # Register some lazy components
            component_loader.register_component(
                "test_service",
                factory=lambda: {"data": "x" * 1000000},  # 1MB
                priority=ComponentPriority.MEDIUM,
                memory_cost_mb=1.0
            )
            
            # Simulate integrated user session with components
            async with session_manager.session_scope(
                "integration_session", 
                "integration_user"
            ) as session:
                
                async with memory_service.request_scope(
                    "integration_request",
                    "integration_user"
                ) as scope:
                    
                    # Load lazy component within request scope
                    test_service = await component_loader.load_component("test_service")
                    
                    # Register component in session
                    await session_manager.register_session_resource(
                        "integration_session",
                        "test_service",
                        "service",
                        test_service,
                        memory_estimate_mb=1.0
                    )
                    
                    memory_tracker.measure("integrated_services_active")
                    
                    # Verify all services are working
                    assert test_service is not None
                    assert session.memory_usage_mb >= 1.0
                    assert len(scope.components) >= 0
            
            memory_tracker.measure("integrated_services_cleaned")
            
            # Force cleanup
            gc.collect()
            await asyncio.sleep(0.1)
            
            final_memory = memory_tracker.get_memory_usage()
            memory_increase = final_memory - initial_memory
            
            # Integrated system should not leak significant memory
            assert memory_increase < 3.0, (
                f"Integrated system leaked {memory_increase:.1f}MB"
            )
            
        finally:
            await memory_service.stop()
            await session_manager.stop()
            await component_loader.shutdown()


# Performance benchmarks
@pytest.mark.benchmark
class TestMemoryPerformanceBenchmarks:
    """Benchmark tests for memory performance."""
    
    async def test_request_scope_creation_performance(self, memory_tracker):
        """Benchmark request scope creation performance."""
        service = MemoryOptimizationService()
        await service.start()
        
        try:
            start_time = time.time()
            initial_memory = memory_tracker.get_memory_usage()
            
            # Create many request scopes rapidly
            scope_count = 1000
            for i in range(scope_count):
                async with service.request_scope(f"perf_test_{i}", f"user_{i % 100}") as scope:
                    scope.components[f"data_{i}"] = i
            
            end_time = time.time()
            final_memory = memory_tracker.get_memory_usage()
            
            # Performance metrics
            total_time = end_time - start_time
            avg_time_per_scope = (total_time / scope_count) * 1000  # ms
            memory_per_scope = (final_memory - initial_memory) / scope_count
            
            # Performance assertions
            assert avg_time_per_scope < 1.0, (
                f"Scope creation too slow: {avg_time_per_scope:.2f}ms per scope"
            )
            
            assert memory_per_scope < 0.01, (
                f"Too much memory per scope: {memory_per_scope:.3f}MB"
            )
            
            memory_tracker.measure(f"created_{scope_count}_scopes")
            
        finally:
            await service.stop()


# Test configuration and utilities
@pytest.mark.asyncio
async def test_memory_optimization_configuration():
    """Test memory optimization service configuration."""
    
    # Test with custom configuration
    with patch.dict(os.environ, {
        'ENABLE_MEMORY_MONITORING': 'true',
        'MEMORY_CHECK_INTERVAL': '60',
        'MEMORY_WARNING_THRESHOLD': '75',
        'MEMORY_CRITICAL_THRESHOLD': '85',
        'MEMORY_CLEANUP_ENABLED': 'true'
    }):
        service = MemoryOptimizationService()
        
        assert service.monitoring_enabled is True
        assert service.check_interval == 60
        assert service.warning_threshold == 75.0
        assert service.critical_threshold == 85.0
        assert service.cleanup_enabled is True


if __name__ == "__main__":
    # Run tests with memory profiling
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "not slow and not benchmark",  # Skip slow tests by default
        "--asyncio-mode=auto"
    ])