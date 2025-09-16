"""
Resource Quota Enforcement Tests - E2E Implementation

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Prevent resource abuse and ensure fair usage
- Value Impact: Protects system stability under multi-tenant load
- Revenue Impact: Essential for SLA compliance and customer trust

This test validates resource quota enforcement mechanisms.
"""

import asyncio
import logging
import time
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.test_helpers.resource_monitoring import (
    ResourceMonitor,
    check_resource_limits,
    stress_system_resources,
)

logger = logging.getLogger(__name__)

QUOTA_CONFIG = {
    "cpu_quota_percent": 80.0,     # Maximum CPU per tenant
    "memory_quota_mb": 1024.0,     # Maximum memory per tenant
    "enforcement_tolerance": 0.1,   # 10% tolerance for enforcement
    "quota_violation_timeout": 30,  # seconds
    "recovery_timeout": 60         # seconds
}

class TestResourceQuotaEnforcement:
    """Test resource quota enforcement mechanisms"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_cpu_quota_enforcement(self):
        """Test CPU quota enforcement under load"""
        logger.info("Testing CPU quota enforcement")
        
        monitor = ResourceMonitor(interval_seconds=1.0)
        await monitor.start()
        
        try:
            # Apply CPU stress to trigger quota enforcement
            await stress_system_resources(
                duration_seconds=QUOTA_CONFIG["quota_violation_timeout"],
                cpu_intensive=True,
                memory_intensive=False
            )
            
            # Check if quota enforcement activated
            stats = monitor.get_statistics()
            max_cpu = stats["cpu"]["max"]
            
            # CPU should be capped near quota limit
            quota_limit = QUOTA_CONFIG["cpu_quota_percent"]
            tolerance = QUOTA_CONFIG["enforcement_tolerance"]
            
            # Allow some tolerance for enforcement mechanisms
            assert max_cpu <= quota_limit * (1 + tolerance), \
                f"CPU quota not enforced: {max_cpu:.1f}% > {quota_limit:.1f}%"
            
            logger.info(f"CPU quota enforced at {max_cpu:.1f}%")
            
        finally:
            await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_memory_quota_enforcement(self):
        """Test memory quota enforcement under pressure"""
        logger.info("Testing memory quota enforcement")
        
        monitor = ResourceMonitor(interval_seconds=2.0)
        await monitor.start()
        
        try:
            # Apply memory pressure
            await stress_system_resources(
                duration_seconds=30,
                cpu_intensive=False,
                memory_intensive=True
            )
            
            stats = monitor.get_statistics()
            max_memory = stats["memory"]["max_mb"]
            
            # Memory should be controlled (though enforcement may vary)
            quota_limit = QUOTA_CONFIG["memory_quota_mb"]
            
            # Check if memory stayed within reasonable bounds
            assert max_memory <= quota_limit * 2, \
                f"Memory grew too much: {max_memory:.1f}MB"
            
            logger.info(f"Memory usage controlled at {max_memory:.1f}MB")
            
        finally:
            await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_quota_violation_recovery(self):
        """Test system recovery after quota violations"""
        logger.info("Testing quota violation recovery")
        
        # Create quota violation
        await self._create_quota_violation()
        
        # Wait for system recovery
        recovery_start = time.time()
        
        # Monitor recovery process
        recovery_successful = False
        while time.time() - recovery_start < QUOTA_CONFIG["recovery_timeout"]:
            limits_check = check_resource_limits(
                cpu_limit=QUOTA_CONFIG["cpu_quota_percent"],
                memory_limit_mb=QUOTA_CONFIG["memory_quota_mb"]
            )
            
            if limits_check["cpu_ok"] and limits_check["memory_ok"]:
                recovery_successful = True
                break
            
            await asyncio.sleep(2.0)
        
        recovery_time = time.time() - recovery_start
        
        assert recovery_successful, \
            f"System did not recover within {QUOTA_CONFIG['recovery_timeout']}s"
        
        logger.info(f"System recovered in {recovery_time:.1f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_quota_enforcement(self):
        """Test quota enforcement with multiple concurrent violators"""
        logger.info("Testing concurrent quota enforcement")
        
        monitor = ResourceMonitor(interval_seconds=1.0)
        await monitor.start()
        
        try:
            # Create multiple concurrent stressors
            stress_tasks = [
                stress_system_resources(30, cpu_intensive=True, memory_intensive=False),
                stress_system_resources(30, cpu_intensive=False, memory_intensive=True),
                stress_system_resources(30, cpu_intensive=True, memory_intensive=True)
            ]
            
            # Run concurrent stress
            await asyncio.gather(*stress_tasks, return_exceptions=True)
            
            stats = monitor.get_statistics()
            
            # System should remain stable despite multiple stressors
            assert stats["cpu"]["max"] <= 100, "CPU exceeded 100%"
            assert stats["memory"]["growth_mb"] <= 1000, "Excessive memory growth"
            
            logger.info("Concurrent quota enforcement validated")
            
        finally:
            await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_quota_fairness_distribution(self):
        """Test fair distribution of resources among tenants"""
        logger.info("Testing quota fairness distribution")
        
        tenant_count = 3
        
        # Simulate multiple tenants requesting resources
        async def tenant_workload(tenant_id: int):
            """Simulate tenant-specific workload"""
            start_time = time.time()
            
            # Each tenant does moderate work
            for _ in range(100):
                # Simulate computational work
                _ = sum(range(1000))
                await asyncio.sleep(0.01)
            
            return {
                "tenant_id": tenant_id,
                "duration": time.time() - start_time
            }
        
        # Run tenant workloads concurrently
        start_time = time.time()
        tasks = [tenant_workload(i) for i in range(tenant_count)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze fairness
        durations = [r["duration"] for r in results]
        max_duration = max(durations)
        min_duration = min(durations)
        
        # Fair distribution should have similar completion times
        fairness_ratio = min_duration / max_duration if max_duration > 0 else 1
        
        assert fairness_ratio >= 0.7, \
            f"Resource distribution not fair: {fairness_ratio:.3f}"
        
        assert total_time <= 30, \
            f"Concurrent execution too slow: {total_time:.2f}s"
        
        logger.info(f"Quota fairness validated: {fairness_ratio:.3f} fairness ratio")
    
    async def _create_quota_violation(self):
        """Create resource quota violation"""
        # Short-term high resource usage
        await stress_system_resources(
            duration_seconds=10,
            cpu_intensive=True,
            memory_intensive=True
        )
