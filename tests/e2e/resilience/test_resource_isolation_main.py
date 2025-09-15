"""
Main Resource Isolation Test Suite - E2E Implementation

This file serves as the main entry point for resource isolation tests that were
split from test_agent_resource_isolation.py to comply with size limits.

Business Value Justification (BVJ):
- Segment: Enterprise (multi-tenant isolation requirements)
- Business Goal: Ensure secure per-tenant resource isolation
- Value Impact: Prevents performance degradation affecting $500K+ enterprise contracts
- Revenue Impact: Essential for enterprise trust and SLA compliance

The original file was refactored into focused modules:
- test_resource_baseline_monitoring.py - Baseline resource monitoring
- test_resource_quota_enforcement.py - Quota enforcement mechanisms
- Additional modules for leak detection, performance isolation, etc.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.test_helpers.resource_monitoring import (
    MemoryLeakDetector,
    ResourceMonitor,
    resource_monitoring_context,
)

logger = logging.getLogger(__name__)

# Integration test configuration
INTEGRATION_CONFIG = {
    "test_duration": 180,        # 3 minutes
    "tenant_count": 5,
    "cpu_threshold": 25.0,       # % per tenant
    "memory_threshold": 512.0,   # MB per tenant
    "isolation_score_min": 0.8
}

class ResourceIsolationIntegrationTests:
    """Integration tests for complete resource isolation system"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(600)
    async def test_complete_resource_isolation_system(self):
        """Test complete resource isolation system under realistic load"""
        logger.info("Testing complete resource isolation system")
        
        leak_detector = MemoryLeakDetector(threshold_mb=100.0)
        leak_detector.establish_baseline()
        
        async with resource_monitoring_context(interval=2.0) as monitor:
            # Run comprehensive isolation test
            isolation_results = await self._run_comprehensive_isolation_test()
            
            # Check for memory leaks
            leak_result = leak_detector.check_for_leak()
            assert not leak_result["leak_detected"], \
                f"Memory leak detected: {leak_result['growth_mb']:.1f}MB"
            
            # Get final statistics
            stats = monitor.get_statistics()
            
            # Validate overall system performance
            self._validate_isolation_system_performance(isolation_results, stats)
        
        logger.info("Complete resource isolation system validated")
    
    @pytest.mark.asyncio
    async def test_multi_tenant_stress_with_isolation(self):
        """Test resource isolation under multi-tenant stress conditions"""
        logger.info("Testing multi-tenant stress with isolation")
        
        tenant_count = INTEGRATION_CONFIG["tenant_count"]
        
        async with resource_monitoring_context(interval=1.0) as monitor:
            # Create diverse tenant workloads
            tenant_tasks = []
            
            for tenant_id in range(tenant_count):
                workload_type = self._get_workload_type(tenant_id)
                task = asyncio.create_task(
                    self._execute_tenant_workload(tenant_id, workload_type)
                )
                tenant_tasks.append(task)
            
            # Run all tenant workloads concurrently
            tenant_results = await asyncio.gather(*tenant_tasks, return_exceptions=True)
            
            # Analyze results
            successful_tenants = sum(
                1 for r in tenant_results 
                if isinstance(r, dict) and r.get("success", False)
            )
            
            assert successful_tenants >= tenant_count * 0.8, \
                f"Too many tenant failures: {successful_tenants}/{tenant_count}"
            
            # Validate resource isolation
            stats = monitor.get_statistics()
            avg_cpu_per_tenant = stats["cpu"]["avg"] / tenant_count
            avg_memory_per_tenant = stats["memory"]["avg_mb"] / tenant_count
            
            assert avg_cpu_per_tenant <= INTEGRATION_CONFIG["cpu_threshold"], \
                f"CPU per tenant too high: {avg_cpu_per_tenant:.1f}%"
            
            assert avg_memory_per_tenant <= INTEGRATION_CONFIG["memory_threshold"], \
                f"Memory per tenant too high: {avg_memory_per_tenant:.1f}MB"
        
        logger.info("Multi-tenant stress isolation validated")
    
    @pytest.mark.asyncio
    async def test_isolation_system_recovery(self):
        """Test resource isolation system recovery after failures"""
        logger.info("Testing isolation system recovery")
        
        # Create system stress to test recovery
        await self._create_system_stress()
        
        # Monitor recovery
        recovery_start = time.time()
        recovery_successful = False
        
        while time.time() - recovery_start < 60:  # 60s timeout
            from tests.e2e.test_helpers.resource_monitoring import (
                check_resource_limits,
            )
            
            limits_check = check_resource_limits(
                cpu_limit=INTEGRATION_CONFIG["cpu_threshold"] * INTEGRATION_CONFIG["tenant_count"],
                memory_limit_mb=INTEGRATION_CONFIG["memory_threshold"] * INTEGRATION_CONFIG["tenant_count"]
            )
            
            if limits_check["cpu_ok"] and limits_check["memory_ok"]:
                recovery_successful = True
                break
            
            await asyncio.sleep(2.0)
        
        recovery_time = time.time() - recovery_start
        
        assert recovery_successful, "System did not recover within timeout"
        assert recovery_time <= 30, f"Recovery took too long: {recovery_time:.1f}s"
        
        logger.info(f"Isolation system recovered in {recovery_time:.1f}s")
    
    async def _run_comprehensive_isolation_test(self) -> Dict[str, Any]:
        """Run comprehensive resource isolation test"""
        duration = INTEGRATION_CONFIG["test_duration"]
        tenant_count = INTEGRATION_CONFIG["tenant_count"]
        
        # Run mixed workloads for extended period
        start_time = time.time()
        
        # Create different types of tenant workloads
        workload_tasks = []
        for i in range(tenant_count):
            workload_type = ["cpu_intensive", "memory_intensive", "balanced"][i % 3]
            task = asyncio.create_task(
                self._long_running_tenant_workload(i, workload_type, duration // 3)
            )
            workload_tasks.append(task)
        
        # Wait for completion
        results = await asyncio.gather(*workload_tasks, return_exceptions=True)
        
        test_duration = time.time() - start_time
        
        return {
            "test_duration": test_duration,
            "tenant_results": results,
            "tenant_count": tenant_count,
            "success_rate": sum(1 for r in results if isinstance(r, dict) and r.get("success")) / len(results)
        }
    
    def _get_workload_type(self, tenant_id: int) -> str:
        """Determine workload type for tenant"""
        workload_types = ["cpu_intensive", "memory_intensive", "io_intensive", "balanced"]
        return workload_types[tenant_id % len(workload_types)]
    
    async def _execute_tenant_workload(self, tenant_id: int, workload_type: str) -> Dict[str, Any]:
        """Execute workload for specific tenant"""
        start_time = time.time()
        
        try:
            if workload_type == "cpu_intensive":
                await self._cpu_intensive_workload(30)
            elif workload_type == "memory_intensive":
                await self._memory_intensive_workload(30)
            elif workload_type == "balanced":
                await self._balanced_workload(30)
            else:
                await asyncio.sleep(30)  # Default light workload
            
            return {
                "tenant_id": tenant_id,
                "workload_type": workload_type,
                "duration": time.time() - start_time,
                "success": True
            }
            
        except Exception as e:
            return {
                "tenant_id": tenant_id,
                "workload_type": workload_type,
                "duration": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
    
    async def _long_running_tenant_workload(self, tenant_id: int, workload_type: str, duration: int) -> Dict[str, Any]:
        """Execute long-running tenant workload"""
        return await self._execute_tenant_workload(tenant_id, workload_type)
    
    async def _cpu_intensive_workload(self, duration: int):
        """CPU-intensive workload simulation"""
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # CPU-bound work
            for _ in range(10000):
                _ = sum(range(100))
            await asyncio.sleep(0.01)
    
    async def _memory_intensive_workload(self, duration: int):
        """Memory-intensive workload simulation"""
        end_time = time.time() + duration
        memory_blocks = []
        
        try:
            while time.time() < end_time:
                # Allocate memory blocks
                block = bytearray(1024 * 1024)  # 1MB
                memory_blocks.append(block)
                
                # Keep only recent blocks
                if len(memory_blocks) > 50:
                    memory_blocks.pop(0)
                
                await asyncio.sleep(0.5)
        finally:
            del memory_blocks
    
    async def _balanced_workload(self, duration: int):
        """Balanced CPU and memory workload"""
        end_time = time.time() + duration
        memory_blocks = []
        
        try:
            while time.time() < end_time:
                # Some CPU work
                for _ in range(1000):
                    _ = sum(range(50))
                
                # Some memory allocation
                if len(memory_blocks) < 10:
                    memory_blocks.append(bytearray(512 * 1024))  # 512KB
                
                await asyncio.sleep(0.1)
        finally:
            del memory_blocks
    
    async def _create_system_stress(self):
        """Create system stress for recovery testing"""
        from tests.e2e.test_helpers.resource_monitoring import (
            stress_system_resources,
        )
        
        await stress_system_resources(
            duration_seconds=20,
            cpu_intensive=True,
            memory_intensive=True
        )
    
    def _validate_isolation_system_performance(self, isolation_results: Dict[str, Any], 
                                             stats: Dict[str, Any]):
        """Validate overall isolation system performance"""
        # Check success rate
        assert isolation_results["success_rate"] >= 0.8, \
            f"Isolation system success rate too low: {isolation_results['success_rate']:.3f}"
        
        # Check resource efficiency
        max_cpu = stats["cpu"]["max"]
        max_memory = stats["memory"]["max_mb"]
        
        tenant_count = isolation_results["tenant_count"]
        cpu_per_tenant = max_cpu / tenant_count
        memory_per_tenant = max_memory / tenant_count
        
        assert cpu_per_tenant <= INTEGRATION_CONFIG["cpu_threshold"] * 1.2, \
            f"CPU per tenant exceeded threshold: {cpu_per_tenant:.1f}%"
        
        assert memory_per_tenant <= INTEGRATION_CONFIG["memory_threshold"] * 1.2, \
            f"Memory per tenant exceeded threshold: {memory_per_tenant:.1f}MB"
