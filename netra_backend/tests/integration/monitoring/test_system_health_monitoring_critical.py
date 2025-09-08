"""
Test System Health Monitoring Critical - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal, All customer segments  
- Business Goal: System availability and customer satisfaction
- Value Impact: Prevents service outages and maintains customer trust
- Strategic Impact: Foundation for 99.9% uptime SLA and business continuity

CRITICAL REQUIREMENTS:
- Tests real system health monitoring and alerting
- Validates infrastructure monitoring and auto-recovery
- Ensures health check accuracy and response
- No mocks - uses real health monitoring systems
"""

import asyncio
import pytest
import time
import psutil
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
import uuid
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.api.health_checks import HealthCheckManager
from netra_backend.app.db.comprehensive_health_monitor import ComprehensiveHealthMonitor
from netra_backend.app.db.connection_pool_monitor import ConnectionPoolMonitor
from netra_backend.app.monitoring.system_resource_monitor import SystemResourceMonitor


class TestSystemHealthMonitoringCritical(SSotBaseTestCase):
    """
    Critical system health monitoring tests.
    
    Tests essential health monitoring that ensures business continuity:
    - Infrastructure health monitoring and alerting
    - Database connection pool monitoring
    - System resource utilization tracking
    - Auto-recovery mechanisms and failover
    - Health check endpoint reliability
    """
    
    def __init__(self):
        """Initialize system health monitoring test suite."""
        super().__init__()
        self.env = get_env()
        self.db_helper = DatabaseTestHelper()
        self.isolated_helper = IsolatedTestHelper()
        
        # Test configuration
        self.test_prefix = f"health_monitor_{uuid.uuid4().hex[:8]}"
        
    async def setup_health_monitoring_system(self) -> Tuple[HealthCheckManager, ComprehensiveHealthMonitor, SystemResourceMonitor]:
        """Set up health monitoring system with real components."""
        # Initialize health monitoring components
        health_manager = HealthCheckManager()
        comprehensive_monitor = ComprehensiveHealthMonitor()
        resource_monitor = SystemResourceMonitor()
        
        await comprehensive_monitor.initialize()
        await resource_monitor.initialize()
        
        return health_manager, comprehensive_monitor, resource_monitor
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_infrastructure_health_monitoring_and_alerting(self):
        """
        Test infrastructure health monitoring with real-time alerting.
        
        BUSINESS CRITICAL: Infrastructure failures cause complete service outages.
        Must detect and alert on infrastructure issues immediately.
        """
        health_manager, comprehensive_monitor, resource_monitor = await self.setup_health_monitoring_system()
        
        try:
            # Test database health monitoring
            db_health_start = time.time()
            db_health = await health_manager.check_postgresql_health(force_check=True)
            db_health_duration = time.time() - db_health_start
            
            # Database health check should complete quickly
            assert db_health_duration < 5.0, \
                f"Database health check too slow: {db_health_duration:.2f}s (max: 5.0s)"
            
            # Database should be healthy or gracefully degraded
            assert db_health.status in ["healthy", "degraded"], \
                f"Database in critical state: {db_health.status} - {db_health.error}"
            
            if db_health.status == "healthy":
                assert db_health.response_time_ms is not None, "Healthy database missing response time"
                assert db_health.response_time_ms < 2000, \
                    f"Database response time too high: {db_health.response_time_ms}ms"
            
            # Test Redis health monitoring
            redis_health_start = time.time()
            redis_health = await health_manager.check_redis_health(force_check=True)
            redis_health_duration = time.time() - redis_health_start
            
            assert redis_health_duration < 5.0, \
                f"Redis health check too slow: {redis_health_duration:.2f}s"
            
            # Redis should be healthy, degraded, or properly not configured
            valid_redis_states = ["healthy", "degraded", "not_configured"]
            assert redis_health.status in valid_redis_states, \
                f"Redis in invalid state: {redis_health.status} - {redis_health.error}"
            
            # Test ClickHouse health monitoring  
            clickhouse_health_start = time.time()
            clickhouse_health = await health_manager.check_clickhouse_health(force_check=True)
            clickhouse_health_duration = time.time() - clickhouse_health_start
            
            assert clickhouse_health_duration < 10.0, \
                f"ClickHouse health check too slow: {clickhouse_health_duration:.2f}s"
            
            valid_clickhouse_states = ["healthy", "degraded", "not_configured", "failed"]
            assert clickhouse_health.status in valid_clickhouse_states, \
                f"ClickHouse in unexpected state: {clickhouse_health.status}"
            
            # Test overall system health aggregation
            system_health_start = time.time()
            system_health = await health_manager.check_overall_health(force_check=True)
            system_health_duration = time.time() - system_health_start
            
            assert system_health_duration < 15.0, \
                f"System health check too slow: {system_health_duration:.2f}s"
            
            # Overall health should reflect component health
            component_statuses = [
                system_health.services["postgresql"].status,
                system_health.services["redis"].status,
                system_health.services["clickhouse"].status
            ]
            
            # System health logic validation
            if "failed" in component_statuses:
                critical_failed = system_health.services["postgresql"].status == "failed"
                if critical_failed:
                    assert system_health.overall_status == "failed", \
                        "System should be failed when PostgreSQL fails"
                else:
                    assert system_health.overall_status in ["degraded", "failed"], \
                        "System should be degraded when non-critical services fail"
            
            elif "degraded" in component_statuses:
                assert system_health.overall_status in ["degraded", "healthy"], \
                    "System should be degraded when components are degraded"
            
            else:
                healthy_components = [s for s in component_statuses if s in ["healthy", "not_configured"]]
                if len(healthy_components) == len(component_statuses):
                    assert system_health.overall_status == "healthy", \
                        "System should be healthy when all components are healthy"
            
            # Test health monitoring alerting
            if system_health.overall_status in ["degraded", "failed"]:
                # Should trigger monitoring alerts
                alerts = await comprehensive_monitor.check_health_alerts(
                    system_health=system_health,
                    test_prefix=self.test_prefix
                )
                
                assert len(alerts) > 0, \
                    f"No alerts generated for {system_health.overall_status} system health"
                
                # Validate alert content
                for alert in alerts:
                    assert alert.severity in ["MEDIUM", "HIGH", "CRITICAL"], \
                        f"Invalid alert severity: {alert.severity}"
                    assert "health" in alert.title.lower(), \
                        f"Health alert title unclear: {alert.title}"
            
            # Test health check caching behavior
            # Second check should use cache
            cached_start = time.time()
            cached_health = await health_manager.check_overall_health(force_check=False)
            cached_duration = time.time() - cached_start
            
            # Cached check should be much faster
            assert cached_duration < 1.0, \
                f"Cached health check too slow: {cached_duration:.2f}s (should use cache)"
            
            # Results should be consistent
            assert cached_health.overall_status == system_health.overall_status, \
                "Cached health status inconsistent with original"
                
        finally:
            await comprehensive_monitor.cleanup_test_data(test_prefix=self.test_prefix)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_pool_monitoring(self):
        """
        Test database connection pool monitoring and management.
        
        BUSINESS CRITICAL: Connection pool exhaustion blocks all user operations.
        Must monitor and manage connection pools proactively.
        """
        health_manager, comprehensive_monitor, resource_monitor = await self.setup_health_monitoring_system()
        
        try:
            # Initialize connection pool monitor
            pool_monitor = ConnectionPoolMonitor()
            await pool_monitor.initialize()
            
            # Get initial connection pool status
            initial_pool_status = await pool_monitor.get_pool_status()
            
            assert initial_pool_status.total_connections >= 0, \
                "Total connections should be non-negative"
            assert initial_pool_status.active_connections >= 0, \
                "Active connections should be non-negative"
            assert initial_pool_status.idle_connections >= 0, \
                "Idle connections should be non-negative"
            
            # Validate pool configuration
            assert initial_pool_status.max_connections > initial_pool_status.min_connections, \
                f"Invalid pool config: max({initial_pool_status.max_connections}) should > min({initial_pool_status.min_connections})"
            
            # Test connection pool under load
            concurrent_connections = 10
            connection_tasks = []
            connection_results = []
            
            async def simulate_database_load(task_id: int):
                """Simulate realistic database load."""
                try:
                    start_time = time.time()
                    
                    # Simulate typical database operations
                    operations = [
                        {"type": "SELECT", "duration": 0.1},
                        {"type": "INSERT", "duration": 0.2},
                        {"type": "UPDATE", "duration": 0.15},
                        {"type": "SELECT", "duration": 0.05},
                    ]
                    
                    for operation in operations:
                        # Simulate database operation
                        await pool_monitor.execute_monitored_operation(
                            operation_type=operation["type"],
                            estimated_duration=operation["duration"],
                            tags={"test_id": self.test_prefix, "task_id": str(task_id)}
                        )
                        
                        # Realistic delay between operations
                        await asyncio.sleep(operation["duration"])
                    
                    duration = time.time() - start_time
                    return {"task_id": task_id, "success": True, "duration": duration}
                    
                except Exception as e:
                    return {"task_id": task_id, "success": False, "error": str(e)}
            
            # Execute concurrent database load
            load_start = time.time()
            connection_results = await asyncio.gather(*[
                simulate_database_load(i) for i in range(concurrent_connections)
            ], return_exceptions=True)
            load_duration = time.time() - load_start
            
            # Analyze connection pool performance under load
            successful_tasks = [r for r in connection_results if isinstance(r, dict) and r.get("success")]
            failed_tasks = [r for r in connection_results if isinstance(r, dict) and not r.get("success")]
            exceptions = [r for r in connection_results if isinstance(r, Exception)]
            
            # Most tasks should succeed (connection pool should handle load)
            success_rate = len(successful_tasks) / len(connection_results)
            assert success_rate >= 0.8, \
                f"Connection pool performance poor: {success_rate:.1%} success rate under load"
            
            # Get pool status during load
            load_pool_status = await pool_monitor.get_pool_status()
            
            # Pool should be managing connections effectively
            assert load_pool_status.active_connections <= load_pool_status.max_connections, \
                f"Pool exceeded max connections: {load_pool_status.active_connections} > {load_pool_status.max_connections}"
            
            # Check for connection leaks
            await asyncio.sleep(2.0)  # Wait for connections to return to pool
            post_load_pool_status = await pool_monitor.get_pool_status()
            
            # Active connections should decrease after load
            assert post_load_pool_status.active_connections <= load_pool_status.active_connections, \
                f"Potential connection leak: active connections increased from {load_pool_status.active_connections} to {post_load_pool_status.active_connections}"
            
            # Test connection pool alerting
            pool_health = await pool_monitor.evaluate_pool_health()
            
            if pool_health.status == "degraded":
                # Should generate appropriate alerts
                pool_alerts = await pool_monitor.get_pool_alerts(test_prefix=self.test_prefix)
                
                assert len(pool_alerts) > 0, "No alerts for degraded connection pool"
                
                # Validate alert details
                for alert in pool_alerts:
                    assert "connection" in alert.title.lower() or "pool" in alert.title.lower(), \
                        f"Pool alert title unclear: {alert.title}"
                    assert alert.metrics is not None, "Pool alert missing metrics"
            
            # Test connection pool auto-recovery
            if pool_health.status in ["degraded", "failed"]:
                recovery_result = await pool_monitor.attempt_pool_recovery(
                    test_prefix=self.test_prefix
                )
                
                if recovery_result.attempted:
                    # Wait for recovery
                    await asyncio.sleep(3.0)
                    
                    recovered_status = await pool_monitor.get_pool_status()
                    recovered_health = await pool_monitor.evaluate_pool_health()
                    
                    # Recovery should improve pool health
                    assert recovered_health.status in ["healthy", "degraded"], \
                        f"Pool recovery failed: still {recovered_health.status}"
                        
        finally:
            await pool_monitor.cleanup_test_data(test_prefix=self.test_prefix)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_system_resource_utilization_monitoring(self):
        """
        Test system resource utilization monitoring and capacity management.
        
        BUSINESS CRITICAL: Resource exhaustion causes service unavailability.
        Must monitor CPU, memory, disk, and network resources proactively.
        """
        health_manager, comprehensive_monitor, resource_monitor = await self.setup_health_monitoring_system()
        
        try:
            # Test baseline resource monitoring
            baseline_resources = await resource_monitor.get_current_resource_usage()
            
            # Validate baseline measurements
            assert 0 <= baseline_resources.cpu_percent <= 100, \
                f"Invalid CPU usage: {baseline_resources.cpu_percent}%"
            assert baseline_resources.memory_used_mb >= 0, \
                f"Invalid memory usage: {baseline_resources.memory_used_mb}MB"
            assert baseline_resources.memory_total_mb > baseline_resources.memory_used_mb, \
                f"Memory usage exceeds total: {baseline_resources.memory_used_mb}MB > {baseline_resources.memory_total_mb}MB"
            assert 0 <= baseline_resources.memory_percent <= 100, \
                f"Invalid memory percentage: {baseline_resources.memory_percent}%"
            
            # Disk usage validation
            assert baseline_resources.disk_used_gb >= 0, \
                f"Invalid disk usage: {baseline_resources.disk_used_gb}GB"
            assert baseline_resources.disk_total_gb > 0, \
                f"Invalid total disk space: {baseline_resources.disk_total_gb}GB"
            assert 0 <= baseline_resources.disk_percent <= 100, \
                f"Invalid disk percentage: {baseline_resources.disk_percent}%"
            
            # Test resource monitoring under simulated load
            load_scenarios = [
                {
                    "name": "cpu_intensive",
                    "description": "CPU-intensive workload simulation",
                    "duration_seconds": 10,
                    "expected_impact": "cpu_percent"
                },
                {
                    "name": "memory_intensive", 
                    "description": "Memory-intensive workload simulation",
                    "duration_seconds": 8,
                    "expected_impact": "memory_percent"
                },
                {
                    "name": "io_intensive",
                    "description": "I/O-intensive workload simulation", 
                    "duration_seconds": 6,
                    "expected_impact": "disk_io"
                }
            ]
            
            resource_measurements = []
            
            for scenario in load_scenarios:
                print(f"Executing load scenario: {scenario['name']}")
                
                # Start resource monitoring for this scenario
                monitoring_task = asyncio.create_task(
                    resource_monitor.monitor_during_load(
                        scenario_name=scenario["name"],
                        test_prefix=self.test_prefix,
                        duration_seconds=scenario["duration_seconds"]
                    )
                )
                
                # Simulate workload based on scenario
                if scenario["name"] == "cpu_intensive":
                    # CPU-bound task
                    await self._simulate_cpu_load(duration=scenario["duration_seconds"])
                    
                elif scenario["name"] == "memory_intensive":
                    # Memory allocation task
                    await self._simulate_memory_load(duration=scenario["duration_seconds"])
                    
                elif scenario["name"] == "io_intensive":
                    # I/O-bound task
                    await self._simulate_io_load(duration=scenario["duration_seconds"])
                
                # Wait for monitoring to complete
                scenario_measurements = await monitoring_task
                resource_measurements.append({
                    "scenario": scenario,
                    "measurements": scenario_measurements
                })
                
                # Cool down between scenarios
                await asyncio.sleep(2.0)
            
            # Analyze resource utilization patterns
            for measurement in resource_measurements:
                scenario = measurement["scenario"]
                measurements = measurement["measurements"]
                
                assert len(measurements) > 0, \
                    f"No resource measurements captured for {scenario['name']}"
                
                # Calculate resource utilization statistics
                max_cpu = max(m.cpu_percent for m in measurements)
                max_memory = max(m.memory_percent for m in measurements)
                avg_cpu = sum(m.cpu_percent for m in measurements) / len(measurements)
                avg_memory = sum(m.memory_percent for m in measurements) / len(measurements)
                
                # Validate resource monitoring detected load
                expected_impact = scenario["expected_impact"]
                
                if expected_impact == "cpu_percent":
                    # CPU-intensive scenario should show increased CPU usage
                    cpu_increase = max_cpu - baseline_resources.cpu_percent
                    assert cpu_increase > 5, \
                        f"CPU load not detected in {scenario['name']}: increase {cpu_increase}%"
                        
                elif expected_impact == "memory_percent":
                    # Memory-intensive scenario should show memory usage
                    memory_increase = max_memory - baseline_resources.memory_percent
                    assert memory_increase >= 0, \
                        f"Memory monitoring failed in {scenario['name']}: decrease {memory_increase}%"
                
                # Validate resource alerts if thresholds exceeded
                if max_cpu > 80 or max_memory > 85:
                    resource_alerts = await resource_monitor.check_resource_alerts(
                        scenario_name=scenario["name"],
                        test_prefix=self.test_prefix
                    )
                    
                    # Should generate alerts for high resource usage
                    if max_cpu > 90 or max_memory > 95:
                        assert len(resource_alerts) > 0, \
                            f"No critical resource alerts for {scenario['name']} (CPU: {max_cpu}%, Memory: {max_memory}%)"
            
            # Test resource capacity planning
            capacity_analysis = await resource_monitor.analyze_capacity_trends(
                time_range_minutes=30,
                test_prefix=self.test_prefix
            )
            
            # Capacity analysis should provide actionable insights
            assert capacity_analysis.cpu_trend is not None, "Missing CPU trend analysis"
            assert capacity_analysis.memory_trend is not None, "Missing memory trend analysis"
            assert capacity_analysis.disk_trend is not None, "Missing disk trend analysis"
            
            # Should include capacity recommendations
            if capacity_analysis.recommendations:
                for recommendation in capacity_analysis.recommendations:
                    assert recommendation.resource_type in ["cpu", "memory", "disk"], \
                        f"Invalid resource type in recommendation: {recommendation.resource_type}"
                    assert recommendation.recommended_action in ["scale_up", "optimize", "monitor"], \
                        f"Invalid recommended action: {recommendation.recommended_action}"
                        
        finally:
            await resource_monitor.cleanup_test_data(test_prefix=self.test_prefix)
    
    async def _simulate_cpu_load(self, duration: int):
        """Simulate CPU-intensive workload."""
        def cpu_intensive_task():
            start_time = time.time()
            while time.time() - start_time < duration:
                # CPU-bound calculation
                [x**2 for x in range(1000)]
                time.sleep(0.001)  # Small yield
        
        # Run CPU task in thread to avoid blocking event loop
        with ThreadPoolExecutor(max_workers=2) as executor:
            tasks = [executor.submit(cpu_intensive_task) for _ in range(2)]
            await asyncio.gather(*[
                asyncio.get_event_loop().run_in_executor(None, task.result) 
                for task in tasks
            ])
    
    async def _simulate_memory_load(self, duration: int):
        """Simulate memory-intensive workload."""
        memory_chunks = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                # Allocate memory in chunks
                chunk = bytearray(1024 * 1024)  # 1MB chunks
                memory_chunks.append(chunk)
                await asyncio.sleep(0.1)
                
                # Limit total allocation to prevent system issues
                if len(memory_chunks) > 50:  # Max 50MB
                    break
                    
        finally:
            # Clean up memory
            memory_chunks.clear()
    
    async def _simulate_io_load(self, duration: int):
        """Simulate I/O-intensive workload."""
        import tempfile
        import os
        
        start_time = time.time()
        temp_files = []
        
        try:
            while time.time() - start_time < duration:
                # Create temporary files with data
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    # Write some data
                    data = b"test data " * 1000  # 9KB per file
                    temp_file.write(data)
                    temp_files.append(temp_file.name)
                
                await asyncio.sleep(0.1)
                
                # Limit file count
                if len(temp_files) > 20:
                    break
                    
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass  # Ignore cleanup errors


if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "--tb=short"])