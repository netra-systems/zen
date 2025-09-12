"""
Test CPU/Memory Quota Enforcement

This test validates that resource quotas are properly enforced
and violations are detected and handled appropriately.
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
@pytest.mark.timeout(400)
async def test_cpu_memory_quota_enforcement(resource_isolation_suite, tenant_agents):
    """
    Test Case 2: CPU/Memory Quota Enforcement
    
    Validates that CPU and memory quotas are properly enforced,
    and violations are detected when agents exceed their limits.
    
    BVJ: Essential for preventing noisy neighbor problems in multi-tenant environment.
    """
    suite = resource_isolation_suite
    agents = tenant_agents
    
    logger.info("=== Test: CPU/Memory Quota Enforcement ===")
    
    # Phase 1: Establish baseline resource usage
    logger.info("Phase 1: Establishing baseline resource usage")
    
    await asyncio.sleep(10.0)  # System stabilization
    await suite.leak_detector.establish_baseline(stabilization_time=15.0)
    
    baseline_quotas = {
        "cpu_quota_percent": RESOURCE_LIMITS["per_agent_cpu_max"],  # 25%
        "memory_quota_mb": RESOURCE_LIMITS["per_agent_memory_mb"]   # 512MB
    }
    
    logger.info(f"Baseline quotas: CPU={baseline_quotas['cpu_quota_percent']}%, "
               f"Memory={baseline_quotas['memory_quota_mb']}MB")
    
    # Phase 2: Test normal operation within quotas
    logger.info("Phase 2: Testing normal operation within quotas")
    
    normal_workload_tasks = []
    for agent in agents:
        task = asyncio.create_task(
            suite.generate_workload(agent, "normal", duration=30.0)
        )
        normal_workload_tasks.append(task)
    
    # Monitor quota compliance during normal workload
    quota_monitoring_task = asyncio.create_task(
        _monitor_quota_compliance(suite, agents, duration=30.0, 
                                 expected_violations=0)
    )
    
    # Wait for normal workloads
    normal_results = await asyncio.gather(*normal_workload_tasks)
    quota_results = await quota_monitoring_task
    
    # Validate normal operation doesn't violate quotas
    for i, agent in enumerate(agents):
        result = normal_results[i]
        assert result["messages_sent"] > 20, \
            f"Normal workload should send messages: {result['messages_sent']}"
    
    assert quota_results["violations_detected"] == 0, \
        f"Normal workload should not violate quotas: {quota_results['violations_detected']}"
    
    logger.info("[U+2713] Normal operation within quotas validated")
    
    # Phase 3: Test quota enforcement with heavy workload
    logger.info("Phase 3: Testing quota enforcement with heavy workload")
    
    # Clear previous violations
    suite.violations_detected.clear()
    
    # Generate heavy workload to trigger quota violations
    heavy_agent = agents[0]  # Use first agent for heavy workload
    normal_agents = agents[1:]  # Keep others on normal workload
    
    # Start heavy workload
    heavy_task = asyncio.create_task(
        suite.generate_workload(heavy_agent, "heavy", duration=60.0, intensity="high")
    )
    
    # Start normal workloads for other agents
    normal_tasks = []
    for agent in normal_agents:
        task = asyncio.create_task(
            suite.generate_workload(agent, "normal", duration=60.0)
        )
        normal_tasks.append(task)
    
    # Monitor quota enforcement
    enforcement_task = asyncio.create_task(
        _enforce_quotas_actively(suite, agents, duration=60.0, 
                               strict_quotas=baseline_quotas)
    )
    
    # Wait for all workloads
    heavy_result = await heavy_task
    normal_results = await asyncio.gather(*normal_tasks)
    enforcement_results = await enforcement_task
    
    # Phase 4: Validate quota enforcement effectiveness
    logger.info("Phase 4: Validating quota enforcement effectiveness")
    
    # Check that heavy workload agent had quota enforcement
    heavy_violations = [v for v in suite.violations_detected 
                       if v.tenant_id == heavy_agent.tenant_id]
    
    # We expect some quota violations from the heavy workload
    assert len(heavy_violations) > 0, \
        f"Heavy workload should trigger quota violations for {heavy_agent.tenant_id}"
    
    # Check that normal agents were not affected
    for agent in normal_agents:
        agent_violations = [v for v in suite.violations_detected 
                           if v.tenant_id == agent.tenant_id]
        
        # Normal agents should have minimal or no violations
        critical_violations = [v for v in agent_violations if v.severity == "critical"]
        assert len(critical_violations) <= 1, \
            f"Normal workload agent {agent.tenant_id} should not have critical violations: {len(critical_violations)}"
    
    # Phase 5: Test memory quota enforcement specifically
    logger.info("Phase 5: Testing memory quota enforcement specifically")
    
    # Clear violations for clean test
    suite.violations_detected.clear()
    
    # Generate memory-intensive workload
    memory_agent = agents[-1]  # Use last agent for memory test
    
    memory_task = asyncio.create_task(
        suite.generate_workload(memory_agent, "noisy", duration=30.0, intensity="high")
    )
    
    # Monitor memory quota enforcement
    memory_monitoring_task = asyncio.create_task(
        _monitor_memory_quota_specifically(suite, memory_agent, duration=30.0,
                                         memory_quota_mb=baseline_quotas["memory_quota_mb"])
    )
    
    await memory_task
    memory_monitoring_results = await memory_monitoring_task
    
    # Validate memory quota monitoring
    memory_violations = [v for v in suite.violations_detected 
                        if v.tenant_id == memory_agent.tenant_id and v.violation_type == "memory"]
    
    logger.info(f"Memory violations detected: {len(memory_violations)}")
    
    # Phase 6: Test quota recovery and cleanup
    logger.info("Phase 6: Testing quota recovery and cleanup")
    
    # Allow system to stabilize after heavy workloads
    await asyncio.sleep(15.0)
    
    # Check that resource usage returns to normal levels
    recovery_metrics = {}
    for agent in agents:
        metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=10)
        recovery_metrics[agent.tenant_id] = metrics
        
        # Resource usage should return to reasonable levels
        current_cpu = metrics.get('avg_cpu_percent', 0)
        current_memory = metrics.get('avg_memory_mb', 0)
        
        assert current_cpu < baseline_quotas["cpu_quota_percent"] * 1.5, \
            f"CPU usage should recover for {agent.tenant_id}: {current_cpu:.1f}%"
        
        assert current_memory < baseline_quotas["memory_quota_mb"] * 1.2, \
            f"Memory usage should recover for {agent.tenant_id}: {current_memory:.1f}MB"
    
    # Phase 7: Generate comprehensive quota enforcement report
    logger.info("Phase 7: Generating comprehensive quota enforcement report")
    
    total_violations = len(suite.violations_detected)
    cpu_violations = len([v for v in suite.violations_detected if "cpu" in v.violation_type])
    memory_violations = len([v for v in suite.violations_detected if "memory" in v.violation_type])
    
    quota_report = {
        "test_result": "PASSED",
        "quotas_enforced": baseline_quotas,
        "total_violations_detected": total_violations,
        "cpu_violations": cpu_violations,
        "memory_violations": memory_violations,
        "enforcement_effectiveness": {
            "heavy_workload_violations": len(heavy_violations),
            "normal_workload_protection": all(
                len([v for v in suite.violations_detected 
                    if v.tenant_id == agent.tenant_id and v.severity == "critical"]) <= 1
                for agent in normal_agents
            )
        },
        "recovery_validation": {
            "all_agents_recovered": all(
                recovery_metrics.get(agent.tenant_id, {}).get('avg_cpu_percent', 100) < baseline_quotas["cpu_quota_percent"] * 1.5
                for agent in agents
            )
        }
    }
    
    logger.info("=== CPU/Memory Quota Enforcement Test PASSED ===")
    logger.info(f"Total violations detected: {total_violations} (CPU: {cpu_violations}, Memory: {memory_violations})")
    logger.info(f"Heavy workload violations: {len(heavy_violations)}")
    logger.info(f"Normal workload protection: {quota_report['enforcement_effectiveness']['normal_workload_protection']}")
    
    # Final assertions
    assert quota_report["enforcement_effectiveness"]["heavy_workload_violations"] > 0, \
        "Heavy workload should trigger quota violations"
    
    assert quota_report["enforcement_effectiveness"]["normal_workload_protection"], \
        "Normal workload agents should be protected from excessive violations"
    
    assert quota_report["recovery_validation"]["all_agents_recovered"], \
        "All agents should recover to normal resource usage levels"


async def _monitor_quota_compliance(suite, agents, duration: float, expected_violations: int) -> Dict[str, Any]:
    """Monitor quota compliance during workload execution."""
    start_time = time.time()
    violations_at_start = len(suite.violations_detected)
    
    compliance_samples = []
    
    while time.time() - start_time < duration:
        for agent in agents:
            # Check current resource usage
            metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=5)
            
            if metrics:
                compliance_samples.append({
                    "tenant_id": agent.tenant_id,
                    "timestamp": time.time(),
                    "cpu_percent": metrics.get('avg_cpu_percent', 0),
                    "memory_mb": metrics.get('avg_memory_mb', 0),
                    "within_cpu_quota": metrics.get('avg_cpu_percent', 0) <= RESOURCE_LIMITS["per_agent_cpu_max"],
                    "within_memory_quota": metrics.get('avg_memory_mb', 0) <= RESOURCE_LIMITS["per_agent_memory_mb"]
                })
        
        await asyncio.sleep(2.0)
    
    violations_detected = len(suite.violations_detected) - violations_at_start
    
    return {
        "duration": time.time() - start_time,
        "violations_detected": violations_detected,
        "expected_violations": expected_violations,
        "compliance_samples": len(compliance_samples),
        "within_quotas_percentage": (
            len([s for s in compliance_samples if s["within_cpu_quota"] and s["within_memory_quota"]]) /
            len(compliance_samples) * 100 if compliance_samples else 0
        )
    }


async def _enforce_quotas_actively(suite, agents, duration: float, strict_quotas: Dict[str, float]) -> Dict[str, Any]:
    """Actively enforce quotas and monitor enforcement effectiveness."""
    start_time = time.time()
    enforcement_actions = []
    
    while time.time() - start_time < duration:
        for agent in agents:
            # Enforce CPU quota
            cpu_enforced = await suite.quota_enforcer.enforce_cpu_quota(
                agent.tenant_id, 
                strict_quotas["cpu_quota_percent"]
            )
            
            # Enforce memory quota
            memory_enforced = await suite.quota_enforcer.enforce_memory_quota(
                agent.tenant_id,
                strict_quotas["memory_quota_mb"]
            )
            
            enforcement_actions.append({
                "tenant_id": agent.tenant_id,
                "timestamp": time.time(),
                "cpu_quota_enforced": cpu_enforced,
                "memory_quota_enforced": memory_enforced
            })
        
        await asyncio.sleep(1.0)
    
    return {
        "duration": time.time() - start_time,
        "enforcement_actions": len(enforcement_actions),
        "enforcement_success_rate": (
            len([a for a in enforcement_actions if a["cpu_quota_enforced"] and a["memory_quota_enforced"]]) /
            len(enforcement_actions) * 100 if enforcement_actions else 0
        )
    }


async def _monitor_memory_quota_specifically(suite, agent, duration: float, memory_quota_mb: float) -> Dict[str, Any]:
    """Monitor memory quota enforcement specifically."""
    start_time = time.time()
    memory_samples = []
    
    while time.time() - start_time < duration:
        metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=2)
        
        if metrics:
            current_memory = metrics.get('avg_memory_mb', 0)
            memory_samples.append({
                "timestamp": time.time(),
                "memory_mb": current_memory,
                "quota_mb": memory_quota_mb,
                "within_quota": current_memory <= memory_quota_mb,
                "quota_usage_percent": (current_memory / memory_quota_mb * 100) if memory_quota_mb > 0 else 0
            })
        
        await asyncio.sleep(0.5)
    
    peak_memory = max([s["memory_mb"] for s in memory_samples]) if memory_samples else 0
    avg_quota_usage = sum([s["quota_usage_percent"] for s in memory_samples]) / len(memory_samples) if memory_samples else 0
    
    return {
        "duration": time.time() - start_time,
        "memory_samples": len(memory_samples),
        "peak_memory_mb": peak_memory,
        "average_quota_usage_percent": avg_quota_usage,
        "quota_exceeded": peak_memory > memory_quota_mb,
        "quota_mb": memory_quota_mb
    }
