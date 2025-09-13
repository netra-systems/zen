"""
Test Per-Tenant Resource Monitoring Baseline

This test validates that resource monitoring can establish accurate baselines
and track resource usage per tenant agent.
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
@pytest.mark.timeout(300)
async def test_per_tenant_resource_monitoring_baseline(resource_isolation_suite, tenant_agents):
    """
    Test Case 1: Per-Tenant Resource Monitoring Baseline
    
    Validates that resource monitoring can establish accurate baselines
    and track per-tenant resource usage without violations.
    
    BVJ: Critical for enterprise SLA compliance and billing accuracy.
    """
    suite = resource_isolation_suite
    agents = tenant_agents
    
    logger.info("=== Test: Per-Tenant Resource Monitoring Baseline ===")
    
    # Phase 1: Establish baseline with idle agents
    logger.info("Phase 1: Establishing baseline with idle agents")
    
    # Wait for system stabilization
    await asyncio.sleep(10.0)
    
    # Establish monitoring baseline
    await suite.leak_detector.establish_baseline(stabilization_time=20.0)
    
    # Collect baseline metrics
    baseline_metrics = {}
    for agent in agents:
        metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=15)
        baseline_metrics[agent.tenant_id] = metrics
        
        logger.info(f"Baseline for {agent.tenant_id}: CPU={metrics.get('avg_cpu_percent', 0):.1f}%, "
                   f"Memory={metrics.get('avg_memory_mb', 0):.1f}MB")
    
    # Phase 2: Generate normal workload and monitor
    logger.info("Phase 2: Generating normal workload and monitoring")
    
    workload_tasks = []
    for agent in agents:
        task = asyncio.create_task(
            suite.generate_workload(agent, "normal", duration=60.0)
        )
        workload_tasks.append(task)
    
    # Wait for workloads to complete
    workload_results = await asyncio.gather(*workload_tasks)
    
    # Phase 3: Validate resource usage patterns
    logger.info("Phase 3: Validating resource usage patterns")
    
    # Collect post-workload metrics
    post_workload_metrics = {}
    for agent in agents:
        metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=30)
        post_workload_metrics[agent.tenant_id] = metrics
        
        logger.info(f"Post-workload for {agent.tenant_id}: CPU={metrics.get('avg_cpu_percent', 0):.1f}%, "
                   f"Memory={metrics.get('avg_memory_mb', 0):.1f}MB")
    
    # Phase 4: Validate monitoring accuracy and isolation
    logger.info("Phase 4: Validating monitoring accuracy and resource isolation")
    
    for i, agent in enumerate(agents):
        tenant_id = agent.tenant_id
        baseline = baseline_metrics.get(tenant_id, {})
        post_workload = post_workload_metrics.get(tenant_id, {})
        workload_result = workload_results[i]
        
        # Validate baseline was established
        assert baseline, f"No baseline metrics for {tenant_id}"
        assert baseline.get('sample_count', 0) > 5, f"Insufficient baseline samples for {tenant_id}"
        
        # Validate resource limits are respected
        max_cpu = post_workload.get('max_cpu_percent', 0)
        max_memory = post_workload.get('max_memory_mb', 0)
        
        assert max_cpu <= RESOURCE_LIMITS["per_agent_cpu_max"], \
            f"CPU limit exceeded for {tenant_id}: {max_cpu:.1f}% > {RESOURCE_LIMITS['per_agent_cpu_max']}%"
        
        assert max_memory <= RESOURCE_LIMITS["per_agent_memory_mb"], \
            f"Memory limit exceeded for {tenant_id}: {max_memory:.1f}MB > {RESOURCE_LIMITS['per_agent_memory_mb']}MB"
        
        # Validate workload was actually processed
        assert workload_result["messages_sent"] > 50, \
            f"Insufficient messages sent by {tenant_id}: {workload_result['messages_sent']}"
        
        # Validate resource usage increased appropriately with workload
        cpu_increase = post_workload.get('avg_cpu_percent', 0) - baseline.get('avg_cpu_percent', 0)
        assert cpu_increase >= 0, f"CPU usage should increase with workload for {tenant_id}"
        
        logger.info(f"[U+2713] Resource monitoring validated for {tenant_id}")
    
    # Phase 5: Validate no resource violations occurred
    logger.info("Phase 5: Validating no resource violations occurred")
    
    # Check for any violations
    critical_violations = [v for v in suite.violations_detected if v.severity == "critical"]
    
    assert len(critical_violations) == 0, \
        f"Critical resource violations detected: {[(v.tenant_id, v.violation_type, v.measured_value) for v in critical_violations]}"
    
    # Phase 6: Validate isolation between tenants
    logger.info("Phase 6: Validating resource isolation between tenants")
    
    # Check that each tenant's metrics are independently tracked
    tenant_ids = [agent.tenant_id for agent in agents]
    
    for tenant_id in tenant_ids:
        tenant_metrics = suite.monitor.get_tenant_metrics_summary(tenant_id, window_seconds=60)
        
        # Validate metrics exist and are reasonable
        assert tenant_metrics.get('sample_count', 0) > 10, \
            f"Insufficient metric samples for {tenant_id}"
        
        assert 0 <= tenant_metrics.get('avg_cpu_percent', -1) <= 100, \
            f"Invalid CPU percentage for {tenant_id}: {tenant_metrics.get('avg_cpu_percent')}"
        
        assert tenant_metrics.get('avg_memory_mb', 0) > 0, \
            f"Invalid memory usage for {tenant_id}: {tenant_metrics.get('avg_memory_mb')}"
    
    # Phase 7: Generate comprehensive monitoring report
    logger.info("Phase 7: Generating comprehensive monitoring report")
    
    final_report = {
        "test_result": "PASSED",
        "baseline_metrics": baseline_metrics,
        "post_workload_metrics": post_workload_metrics,
        "workload_results": workload_results,
        "violations_detected": len(suite.violations_detected),
        "monitoring_samples_total": sum(
            suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=300).get('sample_count', 0)
            for agent in agents
        ),
        "resource_isolation_validated": True,
        "performance_requirements_met": {
            "cpu_limits_respected": all(
                post_workload_metrics.get(agent.tenant_id, {}).get('max_cpu_percent', 0) <= RESOURCE_LIMITS["per_agent_cpu_max"]
                for agent in agents
            ),
            "memory_limits_respected": all(
                post_workload_metrics.get(agent.tenant_id, {}).get('max_memory_mb', 0) <= RESOURCE_LIMITS["per_agent_memory_mb"]
                for agent in agents
            ),
            "isolation_violations": RESOURCE_LIMITS["isolation_violations"]  # Should be 0
        }
    }
    
    logger.info("=== Resource Monitoring Baseline Test PASSED ===")
    logger.info(f"Monitored {len(agents)} tenant agents with {final_report['monitoring_samples_total']} total samples")
    logger.info(f"Resource limits respected: CPU={final_report['performance_requirements_met']['cpu_limits_respected']}, "
               f"Memory={final_report['performance_requirements_met']['memory_limits_respected']}")
    
    # Ensure all performance requirements are met
    assert final_report["performance_requirements_met"]["cpu_limits_respected"], \
        "CPU limits were not respected across all tenants"
    
    assert final_report["performance_requirements_met"]["memory_limits_respected"], \
        "Memory limits were not respected across all tenants"
    
    assert final_report["violations_detected"] == 0, \
        f"Resource violations detected: {final_report['violations_detected']}"


@pytest.mark.asyncio
@pytest.mark.e2e  
@pytest.mark.resource_isolation
@pytest.mark.timeout(180)
async def test_monitoring_accuracy_validation(resource_isolation_suite, tenant_agents):
    """
    Validate monitoring accuracy and metrics collection reliability.
    
    Tests that resource monitoring produces consistent and accurate
    measurements across different load patterns.
    """
    suite = resource_isolation_suite
    agents = tenant_agents[:2]  # Use first 2 agents
    
    logger.info("=== Test: Monitoring Accuracy Validation ===")
    
    # Phase 1: Collect metrics during idle period
    logger.info("Phase 1: Collecting baseline metrics during idle period")
    
    await asyncio.sleep(10.0)  # Let system settle
    
    idle_metrics = {}
    for agent in agents:
        metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=10)
        idle_metrics[agent.tenant_id] = metrics
    
    # Phase 2: Generate controlled workload
    logger.info("Phase 2: Generating controlled workload")
    
    # Generate light workload for precise measurement
    workload_task = asyncio.create_task(
        suite.generate_workload(agents[0], "normal", duration=30.0)
    )
    
    # Keep second agent idle for comparison
    await workload_task
    
    # Phase 3: Collect post-workload metrics
    logger.info("Phase 3: Collecting post-workload metrics")
    
    post_workload_metrics = {}
    for agent in agents:
        metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=15)
        post_workload_metrics[agent.tenant_id] = metrics
    
    # Phase 4: Validate monitoring accuracy
    logger.info("Phase 4: Validating monitoring accuracy")
    
    active_agent = agents[0]
    idle_agent = agents[1]
    
    active_idle = idle_metrics[active_agent.tenant_id]
    active_post = post_workload_metrics[active_agent.tenant_id]
    idle_idle = idle_metrics[idle_agent.tenant_id]
    idle_post = post_workload_metrics[idle_agent.tenant_id]
    
    # Validate active agent shows increased resource usage
    cpu_increase = active_post.get('avg_cpu_percent', 0) - active_idle.get('avg_cpu_percent', 0)
    assert cpu_increase > 0, f"Active agent should show CPU increase: {cpu_increase}"
    
    # Validate idle agent shows minimal change
    idle_cpu_change = abs(idle_post.get('avg_cpu_percent', 0) - idle_idle.get('avg_cpu_percent', 0))
    assert idle_cpu_change < 5.0, f"Idle agent should show minimal CPU change: {idle_cpu_change}"
    
    # Validate metric consistency
    for agent in agents:
        metrics = post_workload_metrics[agent.tenant_id]
        
        # Ensure metrics are within reasonable bounds
        assert 0 <= metrics.get('avg_cpu_percent', -1) <= 100, \
            f"Invalid CPU percentage: {metrics.get('avg_cpu_percent')}"
        
        assert metrics.get('avg_memory_mb', 0) > 0, \
            f"Memory usage should be positive: {metrics.get('avg_memory_mb')}"
        
        assert metrics.get('sample_count', 0) > 5, \
            f"Insufficient samples: {metrics.get('sample_count')}"
    
    logger.info("=== Monitoring Accuracy Validation Test PASSED ===")
    logger.info(f"Active agent CPU increase: {cpu_increase:.1f}%")
    logger.info(f"Idle agent CPU change: {idle_cpu_change:.1f}%")
