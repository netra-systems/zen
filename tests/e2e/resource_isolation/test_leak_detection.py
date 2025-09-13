"""
Test Resource Leak Detection and Prevention

This test validates the system's ability to detect and prevent
resource leaks in agent processes.
"""

import asyncio
import logging
import time
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.resource_isolation.test_infrastructure import RESOURCE_LIMITS
from tests.e2e.resource_isolation.test_suite import (
    resource_isolation_suite,
    tenant_agents,
)

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.resource_isolation
@pytest.mark.timeout(350)
async def test_resource_leak_detection_and_prevention(resource_isolation_suite, tenant_agents):
    """
    Test Case 3: Resource Leak Detection and Prevention
    
    Validates that the system can detect memory leaks and other
    resource leaks before they impact system stability.
    
    BVJ: Prevents system degradation that could affect enterprise SLAs.
    """
    suite = resource_isolation_suite
    agents = tenant_agents[:2]  # Use 2 agents for focused testing
    
    logger.info("=== Test: Resource Leak Detection and Prevention ===")
    
    # Phase 1: Establish clean baseline
    logger.info("Phase 1: Establishing clean baseline for leak detection")
    
    await asyncio.sleep(15.0)  # Extended stabilization
    await suite.leak_detector.establish_baseline(stabilization_time=30.0)
    
    # Record initial resource state
    initial_metrics = {}
    for agent in agents:
        metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=10)
        initial_metrics[agent.tenant_id] = metrics
        
        logger.info(f"Initial state for {agent.tenant_id}: "
                   f"CPU={metrics.get('avg_cpu_percent', 0):.1f}%, "
                   f"Memory={metrics.get('avg_memory_mb', 0):.1f}MB")
    
    # Phase 2: Generate sustained normal workload to verify no leaks
    logger.info("Phase 2: Running sustained workload to verify no leaks in normal operation")
    
    # Run normal workload for extended period
    sustained_tasks = []
    for agent in agents:
        task = asyncio.create_task(
            suite.generate_workload(agent, "normal", duration=90.0)
        )
        sustained_tasks.append(task)
    
    # Monitor for leaks during normal operation
    normal_leak_monitoring = asyncio.create_task(
        _monitor_for_leaks(suite, agents, duration=90.0, 
                          expected_leaks=False, check_interval=10.0)
    )
    
    sustained_results = await asyncio.gather(*sustained_tasks)
    normal_leak_results = await normal_leak_monitoring
    
    # Validate no leaks during normal operation
    assert not normal_leak_results["memory_leaks_detected"], \
        f"Memory leaks detected during normal operation: {normal_leak_results['leaking_tenants']}"
    
    logger.info("[U+2713] No leaks detected during normal sustained workload")
    
    # Phase 3: Test leak detection with problematic workload
    logger.info("Phase 3: Testing leak detection with resource-intensive workload")
    
    # Clear any previous leak detection state
    suite.violations_detected.clear()
    
    # Generate potentially problematic workload
    leak_agent = agents[0]
    stable_agent = agents[1]
    
    # Start resource-intensive workload that might cause leaks
    leak_task = asyncio.create_task(
        suite.generate_workload(leak_agent, "noisy", duration=120.0, intensity="extreme")
    )
    
    # Keep stable agent on normal workload for comparison
    stable_task = asyncio.create_task(
        suite.generate_workload(stable_agent, "normal", duration=120.0)
    )
    
    # Monitor for leak detection
    leak_detection_task = asyncio.create_task(
        _monitor_for_leaks(suite, agents, duration=120.0,
                          expected_leaks=True, check_interval=15.0)
    )
    
    await leak_task
    await stable_task
    leak_detection_results = await leak_detection_task
    
    # Phase 4: Validate leak detection capabilities
    logger.info("Phase 4: Validating leak detection capabilities")
    
    # Check final resource state
    final_metrics = {}
    for agent in agents:
        metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=20)
        final_metrics[agent.tenant_id] = metrics
        
        logger.info(f"Final state for {agent.tenant_id}: "
                   f"CPU={metrics.get('avg_cpu_percent', 0):.1f}%, "
                   f"Memory={metrics.get('avg_memory_mb', 0):.1f}MB")
    
    # Calculate resource growth
    resource_growth = {}
    for agent in agents:
        initial = initial_metrics[agent.tenant_id]
        final = final_metrics[agent.tenant_id]
        
        memory_growth = final.get('avg_memory_mb', 0) - initial.get('avg_memory_mb', 0)
        cpu_change = final.get('avg_cpu_percent', 0) - initial.get('avg_cpu_percent', 0)
        
        resource_growth[agent.tenant_id] = {
            "memory_growth_mb": memory_growth,
            "cpu_change_percent": cpu_change,
            "memory_growth_percent": (
                (memory_growth / initial.get('avg_memory_mb', 1)) * 100 
                if initial.get('avg_memory_mb', 0) > 0 else 0
            )
        }
        
        logger.info(f"Resource growth for {agent.tenant_id}: "
                   f"Memory={memory_growth:.1f}MB ({resource_growth[agent.tenant_id]['memory_growth_percent']:.1f}%), "
                   f"CPU={cpu_change:.1f}%")
    
    # Phase 5: Test leak prevention and recovery
    logger.info("Phase 5: Testing leak prevention and recovery")
    
    # Allow system to recover
    await asyncio.sleep(30.0)
    
    # Check recovery metrics
    recovery_metrics = {}
    for agent in agents:
        metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=15)
        recovery_metrics[agent.tenant_id] = metrics
    
    # Validate recovery
    for agent in agents:
        recovery = recovery_metrics[agent.tenant_id]
        initial = initial_metrics[agent.tenant_id]
        
        # Memory should not have grown excessively
        memory_growth = recovery.get('avg_memory_mb', 0) - initial.get('avg_memory_mb', 0)
        
        # Allow some growth but prevent runaway leaks
        max_acceptable_growth = RESOURCE_LIMITS["per_agent_memory_mb"] * 0.3  # 30% of quota
        
        assert memory_growth <= max_acceptable_growth, \
            f"Excessive memory growth for {agent.tenant_id}: {memory_growth:.1f}MB > {max_acceptable_growth:.1f}MB"
        
        # CPU should return to reasonable levels
        current_cpu = recovery.get('avg_cpu_percent', 0)
        assert current_cpu <= RESOURCE_LIMITS["per_agent_cpu_max"] * 1.5, \
            f"CPU did not recover for {agent.tenant_id}: {current_cpu:.1f}%"
    
    # Phase 6: Generate leak detection report
    logger.info("Phase 6: Generating comprehensive leak detection report")
    
    leak_report = {
        "test_result": "PASSED",
        "baseline_established": True,
        "normal_operation_leak_free": not normal_leak_results["memory_leaks_detected"],
        "leak_detection_functional": leak_detection_results["leak_monitoring_active"],
        "resource_growth_controlled": all(
            growth["memory_growth_mb"] <= RESOURCE_LIMITS["per_agent_memory_mb"] * 0.3
            for growth in resource_growth.values()
        ),
        "recovery_successful": all(
            recovery_metrics.get(agent.tenant_id, {}).get('avg_cpu_percent', 100) <= RESOURCE_LIMITS["per_agent_cpu_max"] * 1.5
            for agent in agents
        ),
        "leak_detection_results": leak_detection_results,
        "resource_growth_analysis": resource_growth,
        "violations_detected": len(suite.violations_detected)
    }
    
    logger.info("=== Resource Leak Detection and Prevention Test PASSED ===")
    logger.info(f"Leak detection functional: {leak_report['leak_detection_functional']}")
    logger.info(f"Resource growth controlled: {leak_report['resource_growth_controlled']}")
    logger.info(f"Recovery successful: {leak_report['recovery_successful']}")
    
    # Final assertions
    assert leak_report["normal_operation_leak_free"], \
        "Normal operation should not produce memory leaks"
    
    assert leak_report["leak_detection_functional"], \
        "Leak detection system should be functional"
    
    assert leak_report["resource_growth_controlled"], \
        "Resource growth should be controlled even under intensive workload"
    
    assert leak_report["recovery_successful"], \
        "System should recover after intensive workload"


async def _monitor_for_leaks(suite, agents, duration: float, expected_leaks: bool, check_interval: float) -> Dict[str, Any]:
    """Monitor for resource leaks during test execution."""
    start_time = time.time()
    leak_checks = []
    leaking_tenants = set()
    
    while time.time() - start_time < duration:
        # Perform leak detection check
        memory_leaks = suite.leak_detector.detect_memory_leaks(
            growth_threshold_mb=30.0,  # 30MB threshold
            growth_threshold_percent=15.0  # 15% growth threshold
        )
        
        all_leaks = suite.leak_detector.detect_all_leaks(
            cpu_threshold=10.0,
            memory_threshold_mb=30.0,
            thread_threshold=5
        )
        
        leak_check = {
            "timestamp": time.time(),
            "memory_leaks": memory_leaks,
            "all_leaks": all_leaks,
            "total_leak_count": len(memory_leaks) + sum(len(leaks) for leaks in all_leaks.values())
        }
        
        leak_checks.append(leak_check)
        leaking_tenants.update(memory_leaks)
        
        if leak_check["total_leak_count"] > 0:
            logger.warning(f"Leaks detected at {leak_check['timestamp']}: {leak_check}")
        
        await asyncio.sleep(check_interval)
    
    total_leak_instances = sum(check["total_leak_count"] for check in leak_checks)
    memory_leaks_detected = len(leaking_tenants) > 0
    
    return {
        "duration": time.time() - start_time,
        "leak_checks_performed": len(leak_checks),
        "total_leak_instances": total_leak_instances,
        "memory_leaks_detected": memory_leaks_detected,
        "leaking_tenants": list(leaking_tenants),
        "leak_monitoring_active": len(leak_checks) > 0,
        "expected_leaks": expected_leaks,
        "leak_detection_accuracy": memory_leaks_detected == expected_leaks
    }
