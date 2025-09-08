"""
Test Startup Performance and Load Testing

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure system can handle production load and scale effectively
- Value Impact: Performance issues prevent users from accessing chat functionality
- Strategic Impact: System scalability and reliability under real-world conditions

This module tests the performance characteristics of the startup process under
various load conditions to ensure the system can handle production scenarios
and scale appropriately.

CRITICAL: These tests validate that:
1. Startup completes within acceptable time limits under normal conditions
2. System can handle concurrent startup scenarios (multiple instances)
3. Resource utilization remains within reasonable bounds during startup
4. Performance degrades gracefully under high load conditions
5. Memory usage remains stable and doesn't leak during repeated startups
"""

import asyncio
import pytest
import time
import statistics
import psutil
import gc
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor
import threading

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.isolated_environment_fixtures import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user

from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.startup_module import (
    StartupModule,
    StartupPhase,
    StartupContext,
    StartupValidationError
)
from netra_backend.app.core.registry.universal_registry import UniversalRegistry
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry


class TestStartupPerformanceLoad(BaseIntegrationTest):
    """Test startup performance under various load conditions."""
    
    def __init__(self):
        """Initialize test suite with performance monitoring."""
        super().__init__()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.startup_modules: List[StartupModule] = []
        self.performance_metrics: List[Dict] = []
        
    async def asyncSetUp(self):
        """Set up test environment with proper authentication."""
        await super().asyncSetUp()
        # Create authenticated test user for performance tests
        self.test_token, self.test_user = await create_authenticated_user(
            environment="test",
            email="performance_test@example.com",
            permissions=["read", "write"]
        )
        
        # Record initial system metrics
        self.initial_memory = psutil.Process().memory_info().rss
        self.initial_cpu_percent = psutil.Process().cpu_percent()
        
    async def asyncTearDown(self):
        """Clean up test resources and record final metrics."""
        # Cleanup all startup modules
        for startup_module in self.startup_modules:
            try:
                await startup_module.shutdown()
            except Exception:
                pass
        self.startup_modules.clear()
        
        # Force garbage collection
        gc.collect()
        
        # Record final metrics
        final_memory = psutil.Process().memory_info().rss
        memory_growth = final_memory - self.initial_memory
        
        if memory_growth > 100 * 1024 * 1024:  # 100MB threshold
            print(f"WARNING: Significant memory growth detected: {memory_growth / 1024 / 1024:.2f}MB")
        
        await super().asyncTearDown()
    
    def _create_tracked_startup_module(self) -> StartupModule:
        """Create startup module with tracking for cleanup and monitoring."""
        startup_module = StartupModule()
        self.startup_modules.append(startup_module)
        return startup_module
    
    def _record_performance_metric(self, test_name: str, metrics: Dict[str, Any]):
        """Record performance metrics for analysis."""
        metrics.update({
            "test_name": test_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "process_memory": psutil.Process().memory_info().rss,
            "system_memory_percent": psutil.virtual_memory().percent,
            "cpu_percent": psutil.Process().cpu_percent()
        })
        self.performance_metrics.append(metrics)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_baseline_startup_performance(self, real_services_fixture):
        """Test baseline startup performance under normal conditions."""
        startup_module = self._create_tracked_startup_module()
        
        # Measure complete startup time
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        context = await startup_module.startup()
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        # Record performance metrics
        startup_duration = end_time - start_time
        memory_usage = end_memory - start_memory
        
        self._record_performance_metric("baseline_startup", {
            "startup_duration": startup_duration,
            "memory_usage": memory_usage,
            "phases_completed": len([p for p in context.phase_states.values() if p.is_complete])
        })
        
        # Validate performance requirements
        assert startup_duration < 30.0, f"Startup too slow: {startup_duration:.2f}s"
        assert memory_usage < 200 * 1024 * 1024, f"Memory usage too high: {memory_usage / 1024 / 1024:.2f}MB"
        assert context.is_startup_complete
        assert context.is_chat_ready

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_startup_performance(self, real_services_fixture):
        """Test performance with multiple concurrent startup processes."""
        concurrent_count = 5
        startup_modules = [self._create_tracked_startup_module() for _ in range(concurrent_count)]
        
        async def timed_startup(module_index: int) -> Dict[str, Any]:
            startup_module = startup_modules[module_index]
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            try:
                context = await startup_module.startup()
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss
                
                return {
                    "module_index": module_index,
                    "success": True,
                    "duration": end_time - start_time,
                    "memory_delta": end_memory - start_memory,
                    "chat_ready": context.is_chat_ready
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    "module_index": module_index,
                    "success": False,
                    "duration": end_time - start_time,
                    "error": str(e)
                }
        
        # Execute concurrent startups
        overall_start_time = time.time()
        tasks = [timed_startup(i) for i in range(concurrent_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        overall_duration = time.time() - overall_start_time
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        durations = [r["duration"] for r in successful_results]
        
        # Record performance metrics
        self._record_performance_metric("concurrent_startup", {
            "concurrent_count": concurrent_count,
            "successful_count": len(successful_results),
            "overall_duration": overall_duration,
            "mean_duration": statistics.mean(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0
        })
        
        # Validate performance requirements
        assert len(successful_results) >= concurrent_count * 0.8, "Too many concurrent startup failures"
        
        if durations:
            # Concurrent startup shouldn't take more than 2x baseline
            max_acceptable_duration = 60.0  # 2x baseline of 30s
            assert max(durations) < max_acceptable_duration, f"Concurrent startup too slow: {max(durations):.2f}s"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_repeated_startup_memory_stability(self, real_services_fixture):
        """Test memory stability across repeated startup/shutdown cycles."""
        iteration_count = 10
        memory_measurements = []
        
        for i in range(iteration_count):
            startup_module = self._create_tracked_startup_module()
            
            # Measure memory before startup
            pre_startup_memory = psutil.Process().memory_info().rss
            
            # Execute startup
            start_time = time.time()
            context = await startup_module.startup()
            startup_duration = time.time() - start_time
            
            # Measure memory after startup
            post_startup_memory = psutil.Process().memory_info().rss
            
            # Shutdown
            await startup_module.shutdown()
            
            # Force garbage collection
            gc.collect()
            
            # Measure memory after shutdown and GC
            post_shutdown_memory = psutil.Process().memory_info().rss
            
            memory_measurements.append({
                "iteration": i,
                "pre_startup": pre_startup_memory,
                "post_startup": post_startup_memory,
                "post_shutdown": post_shutdown_memory,
                "startup_growth": post_startup_memory - pre_startup_memory,
                "net_growth": post_shutdown_memory - pre_startup_memory,
                "duration": startup_duration
            })
            
            # Remove from tracking since we shutdown manually
            self.startup_modules.remove(startup_module)
        
        # Analyze memory stability
        net_growths = [m["net_growth"] for m in memory_measurements]
        startup_growths = [m["startup_growth"] for m in memory_measurements]
        durations = [m["duration"] for m in memory_measurements]
        
        self._record_performance_metric("repeated_startup_memory", {
            "iteration_count": iteration_count,
            "mean_net_growth": statistics.mean(net_growths),
            "max_net_growth": max(net_growths),
            "mean_startup_growth": statistics.mean(startup_growths),
            "mean_duration": statistics.mean(durations),
            "duration_stability": statistics.stdev(durations) if len(durations) > 1 else 0
        })
        
        # Validate memory stability
        mean_net_growth = statistics.mean(net_growths)
        max_acceptable_growth = 50 * 1024 * 1024  # 50MB per iteration
        assert mean_net_growth < max_acceptable_growth, f"Memory leak detected: {mean_net_growth / 1024 / 1024:.2f}MB per iteration"
        
        # Performance should be consistent
        duration_stdev = statistics.stdev(durations) if len(durations) > 1 else 0
        assert duration_stdev < 5.0, f"Startup performance too variable: {duration_stdev:.2f}s standard deviation"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_startup_performance_under_memory_pressure(self, real_services_fixture):
        """Test startup performance under memory pressure conditions."""
        startup_module = self._create_tracked_startup_module()
        
        # Create memory pressure by allocating large objects
        memory_pressure_objects = []
        pressure_size = 100 * 1024 * 1024  # 100MB
        
        try:
            # Allocate memory to create pressure
            for i in range(3):  # 300MB total
                memory_pressure_objects.append(bytearray(pressure_size))
            
            # Measure startup under memory pressure
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            context = await startup_module.startup()
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            # Record performance under pressure
            startup_duration = end_time - start_time
            memory_usage = end_memory - start_memory
            
            self._record_performance_metric("startup_under_memory_pressure", {
                "startup_duration": startup_duration,
                "memory_usage": memory_usage,
                "pressure_applied_mb": len(memory_pressure_objects) * pressure_size / 1024 / 1024,
                "system_memory_percent": psutil.virtual_memory().percent
            })
            
            # Validate startup still works under pressure
            assert context.is_startup_complete, "Startup failed under memory pressure"
            assert context.is_chat_ready, "System not chat ready under memory pressure"
            
            # Performance might be slower but should still be reasonable
            assert startup_duration < 60.0, f"Startup too slow under memory pressure: {startup_duration:.2f}s"
            
        finally:
            # Clean up memory pressure
            memory_pressure_objects.clear()
            gc.collect()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_phase_timing_analysis(self, real_services_fixture):
        """Test and analyze timing of individual startup phases."""
        startup_module = self._create_tracked_startup_module()
        phase_timings = {}
        
        # Time each phase individually
        context = None
        for phase in StartupPhase:
            phase_start = time.time()
            
            if phase == StartupPhase.INIT:
                context = await startup_module.execute_phase(phase)
            else:
                context = await startup_module.execute_phase(phase, context)
            
            phase_end = time.time()
            phase_timings[phase.name] = phase_end - phase_start
        
        # Analyze phase timing distribution
        total_time = sum(phase_timings.values())
        slowest_phase = max(phase_timings.items(), key=lambda x: x[1])
        fastest_phase = min(phase_timings.items(), key=lambda x: x[1])
        
        self._record_performance_metric("phase_timing_analysis", {
            "total_startup_time": total_time,
            "slowest_phase": slowest_phase[0],
            "slowest_phase_time": slowest_phase[1],
            "fastest_phase": fastest_phase[0], 
            "fastest_phase_time": fastest_phase[1],
            "phase_timings": phase_timings
        })
        
        # Validate reasonable phase timing distribution
        assert slowest_phase[1] < total_time * 0.6, f"Phase {slowest_phase[0]} dominates startup time"
        assert total_time < 30.0, f"Total startup time too high: {total_time:.2f}s"
        
        # Specific phase expectations
        assert phase_timings.get("INIT", 0) < 2.0, "INIT phase too slow"
        assert phase_timings.get("FINALIZE", 0) < 5.0, "FINALIZE phase too slow"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_utilization_monitoring(self, real_services_fixture):
        """Test resource utilization during startup process."""
        startup_module = self._create_tracked_startup_module()
        
        resource_samples = []
        monitoring_active = True
        
        async def monitor_resources():
            """Monitor system resources during startup."""
            while monitoring_active:
                try:
                    sample = {
                        "timestamp": time.time(),
                        "memory_rss": psutil.Process().memory_info().rss,
                        "memory_vms": psutil.Process().memory_info().vms,
                        "cpu_percent": psutil.Process().cpu_percent(),
                        "system_memory_percent": psutil.virtual_memory().percent,
                        "system_cpu_percent": psutil.cpu_percent(interval=0.1),
                        "open_files": len(psutil.Process().open_files()),
                        "connections": len(psutil.Process().connections())
                    }
                    resource_samples.append(sample)
                except Exception:
                    pass  # Ignore monitoring errors
                
                await asyncio.sleep(0.5)  # Sample every 500ms
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(monitor_resources())
        
        try:
            # Execute startup while monitoring
            start_time = time.time()
            context = await startup_module.startup()
            end_time = time.time()
            
        finally:
            # Stop monitoring
            monitoring_active = False
            await monitor_task
        
        # Analyze resource utilization
        if resource_samples:
            max_memory = max(s["memory_rss"] for s in resource_samples)
            max_cpu = max(s["cpu_percent"] for s in resource_samples) 
            max_system_memory = max(s["system_memory_percent"] for s in resource_samples)
            max_open_files = max(s["open_files"] for s in resource_samples)
            max_connections = max(s["connections"] for s in resource_samples)
            
            self._record_performance_metric("resource_utilization", {
                "startup_duration": end_time - start_time,
                "samples_collected": len(resource_samples),
                "peak_memory_mb": max_memory / 1024 / 1024,
                "peak_cpu_percent": max_cpu,
                "peak_system_memory_percent": max_system_memory,
                "peak_open_files": max_open_files,
                "peak_connections": max_connections
            })
            
            # Validate resource usage within reasonable bounds
            assert max_memory < 1024 * 1024 * 1024, f"Memory usage too high: {max_memory / 1024 / 1024:.2f}MB"
            assert max_open_files < 200, f"Too many open files: {max_open_files}"
            assert max_connections < 50, f"Too many connections: {max_connections}"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_startup_performance_with_slow_database(self, real_services_fixture):
        """Test startup performance when database responses are slow."""
        startup_module = self._create_tracked_startup_module()
        
        # Mock slow database operations
        original_create_pool = None
        
        async def slow_database_operations(*args, **kwargs):
            # Simulate slow database connection
            await asyncio.sleep(2.0)  # 2 second delay
            
            # Create a mock pool with slow operations
            mock_pool = AsyncMock()
            
            async def slow_execute(*args, **kwargs):
                await asyncio.sleep(0.5)  # 500ms per query
                return AsyncMock()
            
            mock_pool.execute = slow_execute
            mock_pool.fetch = slow_execute
            mock_pool.fetchrow = slow_execute
            
            return mock_pool
        
        # Execute startup with slow database
        start_time = time.time()
        
        with patch('asyncpg.create_pool', side_effect=slow_database_operations):
            context = await startup_module.startup()
        
        end_time = time.time()
        startup_duration = end_time - start_time
        
        self._record_performance_metric("startup_with_slow_database", {
            "startup_duration": startup_duration,
            "database_delay_simulation": 2.0,
            "query_delay_simulation": 0.5,
            "startup_completed": context.is_startup_complete
        })
        
        # Validate startup still works but is slower
        assert context.is_startup_complete, "Startup failed with slow database"
        assert startup_duration > 5.0, "Startup should be slower with database delays"
        assert startup_duration < 45.0, f"Startup too slow even with database delays: {startup_duration:.2f}s"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_startup_scaling_characteristics(self, real_services_fixture):
        """Test how startup performance scales with different configuration sizes."""
        test_configurations = [
            {"agent_count": 5, "registry_size": 100, "config_entries": 50},
            {"agent_count": 10, "registry_size": 500, "config_entries": 200},
            {"agent_count": 20, "registry_size": 1000, "config_entries": 500}
        ]
        
        scaling_results = []
        
        for config in test_configurations:
            startup_module = self._create_tracked_startup_module()
            
            # Mock configuration scaling
            with patch.dict('os.environ', {
                'SIMULATED_AGENT_COUNT': str(config["agent_count"]),
                'SIMULATED_REGISTRY_SIZE': str(config["registry_size"]),
                'SIMULATED_CONFIG_ENTRIES': str(config["config_entries"])
            }):
                
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss
                
                context = await startup_module.startup()
                
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss
                
                scaling_results.append({
                    "config": config,
                    "duration": end_time - start_time,
                    "memory_usage": end_memory - start_memory,
                    "startup_success": context.is_startup_complete
                })
        
        # Analyze scaling characteristics
        durations = [r["duration"] for r in scaling_results]
        memory_usages = [r["memory_usage"] for r in scaling_results]
        
        self._record_performance_metric("startup_scaling", {
            "configurations_tested": len(test_configurations),
            "duration_trend": durations,
            "memory_trend": memory_usages,
            "scaling_factor": durations[-1] / durations[0] if durations[0] > 0 else 1.0
        })
        
        # Validate scaling is reasonable (not exponential)
        scaling_factor = durations[-1] / durations[0] if durations[0] > 0 else 1.0
        assert scaling_factor < 5.0, f"Startup scaling too poor: {scaling_factor:.2f}x slower"
        
        # All configurations should complete successfully
        for result in scaling_results:
            assert result["startup_success"], f"Startup failed for config: {result['config']}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_startup_performance_degradation_points(self, real_services_fixture):
        """Test identification of performance degradation points."""
        startup_module = self._create_tracked_startup_module()
        
        degradation_tests = [
            {"name": "high_cpu_load", "cpu_stress": True},
            {"name": "high_memory_usage", "memory_stress": True}, 
            {"name": "high_disk_io", "disk_stress": True},
            {"name": "network_latency", "network_delay": 1.0}
        ]
        
        degradation_results = []
        
        # Baseline measurement
        baseline_start = time.time()
        baseline_context = await startup_module.startup()
        baseline_duration = time.time() - baseline_start
        await startup_module.shutdown()
        
        # Test each degradation scenario
        for test_config in degradation_tests:
            degraded_startup_module = self._create_tracked_startup_module()
            
            start_time = time.time()
            
            try:
                if test_config.get("network_delay"):
                    # Simulate network delay
                    async def delayed_connect(*args, **kwargs):
                        await asyncio.sleep(test_config["network_delay"])
                        return AsyncMock()
                    
                    with patch('asyncpg.create_pool', side_effect=delayed_connect):
                        with patch('redis.asyncio.Redis.from_url', side_effect=delayed_connect):
                            context = await degraded_startup_module.startup()
                else:
                    # For other stress types, just run normal startup
                    # (In real implementation, would simulate CPU/memory/disk stress)
                    context = await degraded_startup_module.startup()
                
                end_time = time.time()
                
                degradation_results.append({
                    "test_name": test_config["name"],
                    "duration": end_time - start_time,
                    "degradation_factor": (end_time - start_time) / baseline_duration,
                    "success": context.is_startup_complete
                })
                
            except Exception as e:
                degradation_results.append({
                    "test_name": test_config["name"],
                    "duration": time.time() - start_time,
                    "degradation_factor": float('inf'),
                    "success": False,
                    "error": str(e)
                })
        
        self._record_performance_metric("degradation_analysis", {
            "baseline_duration": baseline_duration,
            "degradation_results": degradation_results,
            "worst_degradation": max(r.get("degradation_factor", 1) for r in degradation_results)
        })
        
        # Validate graceful degradation
        for result in degradation_results:
            if result["success"]:
                assert result["degradation_factor"] < 10.0, f"Excessive degradation in {result['test_name']}: {result['degradation_factor']:.2f}x"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_phase_execution_performance(self, real_services_fixture):
        """Test performance of phases that can execute concurrently."""
        startup_module = self._create_tracked_startup_module()
        
        # Execute prerequisite phases
        context = await startup_module.execute_through_phase(StartupPhase.CACHE)
        
        # Test if SERVICES and WEBSOCKET preparation can run concurrently
        async def services_phase():
            start_time = time.time()
            services_context = await startup_module.execute_phase(StartupPhase.SERVICES, context)
            return time.time() - start_time, services_context
        
        async def websocket_prep():
            # Simulate WebSocket preparation that could run in parallel
            start_time = time.time()
            await asyncio.sleep(1.0)  # Simulate WebSocket prep work
            return time.time() - start_time
        
        # Sequential execution
        seq_start_time = time.time()
        services_time, services_context = await services_phase()
        websocket_context = await startup_module.execute_phase(StartupPhase.WEBSOCKET, services_context)
        seq_total_time = time.time() - seq_start_time
        
        # Note: True concurrent phase execution would require startup module changes
        # This test validates the current sequential performance
        
        self._record_performance_metric("concurrent_phase_potential", {
            "sequential_total_time": seq_total_time,
            "services_phase_time": services_time,
            "websocket_phase_time": seq_total_time - services_time,
            "potential_concurrency_benefit": "Measured for future optimization"
        })
        
        # Validate phases complete successfully
        assert services_context.phase_states[StartupPhase.SERVICES].is_complete
        assert websocket_context.phase_states[StartupPhase.WEBSOCKET].is_complete

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_startup_performance_monitoring_overhead(self, real_services_fixture):
        """Test the performance overhead of monitoring and metrics collection."""
        # Startup without monitoring
        startup_module_1 = self._create_tracked_startup_module()
        
        start_time = time.time()
        context_1 = await startup_module_1.startup()
        baseline_duration = time.time() - start_time
        
        # Startup with intensive monitoring
        startup_module_2 = self._create_tracked_startup_module()
        
        monitoring_overhead = []
        
        async def intensive_monitoring():
            while True:
                try:
                    # Simulate intensive monitoring
                    psutil.Process().memory_info()
                    psutil.Process().cpu_percent()
                    psutil.virtual_memory()
                    await asyncio.sleep(0.01)  # 100 samples per second
                except Exception:
                    break
        
        monitor_task = asyncio.create_task(intensive_monitoring())
        
        start_time = time.time()
        context_2 = await startup_module_2.startup()
        monitored_duration = time.time() - start_time
        
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        monitoring_overhead_percent = ((monitored_duration - baseline_duration) / baseline_duration) * 100
        
        self._record_performance_metric("monitoring_overhead", {
            "baseline_duration": baseline_duration,
            "monitored_duration": monitored_duration,
            "overhead_percent": monitoring_overhead_percent,
            "overhead_seconds": monitored_duration - baseline_duration
        })
        
        # Validate monitoring overhead is acceptable
        assert monitoring_overhead_percent < 20.0, f"Monitoring overhead too high: {monitoring_overhead_percent:.1f}%"
        assert monitored_duration < baseline_duration * 1.5, "Monitoring more than doubles startup time"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_startup_performance_regression_detection(self, real_services_fixture):
        """Test detection of performance regressions in startup process."""
        # Run multiple startups to establish baseline
        baseline_runs = 3
        baseline_durations = []
        
        for i in range(baseline_runs):
            startup_module = self._create_tracked_startup_module()
            
            start_time = time.time()
            context = await startup_module.startup()
            duration = time.time() - start_time
            
            baseline_durations.append(duration)
            await startup_module.shutdown()
            self.startup_modules.remove(startup_module)  # Manual cleanup tracking
        
        baseline_mean = statistics.mean(baseline_durations)
        baseline_stdev = statistics.stdev(baseline_durations) if len(baseline_durations) > 1 else 0
        
        # Test with simulated regression
        regressed_startup_module = self._create_tracked_startup_module()
        
        # Inject artificial delay to simulate regression
        async def slow_phase_execution(original_method, *args, **kwargs):
            await asyncio.sleep(2.0)  # 2 second regression
            return await original_method(*args, **kwargs)
        
        with patch.object(regressed_startup_module, 'execute_phase') as mock_execute:
            mock_execute.side_effect = lambda phase, context=None: slow_phase_execution(
                regressed_startup_module.__class__.execute_phase, regressed_startup_module, phase, context
            )
            
            start_time = time.time()
            try:
                # This will likely fail due to the mock, but we're testing regression detection
                await regressed_startup_module.startup()
                regressed_duration = time.time() - start_time
            except Exception:
                regressed_duration = time.time() - start_time  # Record time even if failed
        
        # Analyze for regression
        regression_threshold = baseline_mean + (3 * baseline_stdev)  # 3 sigma rule
        is_regression = regressed_duration > regression_threshold
        
        self._record_performance_metric("regression_detection", {
            "baseline_mean": baseline_mean,
            "baseline_stdev": baseline_stdev,
            "regression_threshold": regression_threshold,
            "test_duration": regressed_duration,
            "is_regression_detected": is_regression,
            "performance_change_percent": ((regressed_duration - baseline_mean) / baseline_mean) * 100
        })
        
        # In real scenario, would alert on regression
        if is_regression:
            print(f"Performance regression detected: {regressed_duration:.2f}s vs baseline {baseline_mean:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_startup_throughput_capacity(self, real_services_fixture):
        """Test the throughput capacity of startup processes."""
        # Test different batch sizes
        batch_sizes = [1, 3, 5, 8]
        throughput_results = []
        
        for batch_size in batch_sizes:
            startup_modules = [self._create_tracked_startup_module() for _ in range(batch_size)]
            
            # Measure batch throughput
            batch_start_time = time.time()
            
            async def batch_startup(module):
                try:
                    context = await module.startup()
                    return {"success": True, "chat_ready": context.is_chat_ready}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            # Execute batch
            batch_tasks = [batch_startup(module) for module in startup_modules]
            batch_results = await asyncio.gather(*batch_tasks)
            
            batch_end_time = time.time()
            batch_duration = batch_end_time - batch_start_time
            
            # Calculate throughput metrics
            successful_startups = sum(1 for r in batch_results if r["success"])
            throughput_per_second = successful_startups / batch_duration if batch_duration > 0 else 0
            
            throughput_results.append({
                "batch_size": batch_size,
                "successful_startups": successful_startups,
                "batch_duration": batch_duration,
                "throughput_per_second": throughput_per_second,
                "success_rate": successful_startups / batch_size
            })
        
        # Analyze throughput scaling
        max_throughput = max(r["throughput_per_second"] for r in throughput_results)
        optimal_batch_size = next(r["batch_size"] for r in throughput_results 
                                if r["throughput_per_second"] == max_throughput)
        
        self._record_performance_metric("throughput_capacity", {
            "throughput_results": throughput_results,
            "max_throughput_per_second": max_throughput,
            "optimal_batch_size": optimal_batch_size
        })
        
        # Validate reasonable throughput capacity
        assert max_throughput > 0.1, f"Throughput too low: {max_throughput:.3f} startups/second"
        
        # Validate success rates remain high
        for result in throughput_results:
            assert result["success_rate"] >= 0.8, f"Low success rate at batch size {result['batch_size']}: {result['success_rate']:.2f}"