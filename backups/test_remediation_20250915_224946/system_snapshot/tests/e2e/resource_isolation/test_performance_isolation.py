"""
Test Performance Isolation Under Load

This test validates that one tenant's high resource usage
does not significantly impact other tenants' performance.
"""

import asyncio
import logging
import statistics
import time
from typing import Any, Dict, List
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
async def test_performance_isolation_under_load(resource_isolation_suite, tenant_agents):
    """
    Test Case 4: Performance Isolation Under Load
    
    Validates that when one tenant is under heavy load, other tenants
    maintain acceptable performance levels with minimal impact.
    
    BVJ: Critical for enterprise multi-tenancy and SLA compliance.
    """
    suite = resource_isolation_suite
    agents = tenant_agents
    
    logger.info("=== Test: Performance Isolation Under Load ===")
    
    # Phase 1: Establish performance baseline
    logger.info("Phase 1: Establishing performance baseline for all tenants")
    
    await asyncio.sleep(10.0)  # System stabilization
    
    # Run baseline workload for all agents
    baseline_tasks = []
    for agent in agents:
        task = asyncio.create_task(
            suite.generate_workload(agent, "normal", duration=30.0)
        )
        baseline_tasks.append(task)
    
    baseline_results = await asyncio.gather(*baseline_tasks)
    
    # Establish performance baseline
    baseline_metrics = await suite.isolation_validator.establish_performance_baseline(
        tenant_ids=[agent.tenant_id for agent in agents],
        duration=15.0
    )
    
    # Record baseline performance
    baseline_performance = {}
    for i, agent in enumerate(agents):
        result = baseline_results[i]
        metrics = baseline_metrics.get(agent.tenant_id)
        
        baseline_performance[agent.tenant_id] = {
            "message_rate": result["message_rate"],
            "messages_sent": result["messages_sent"],
            "responses_received": result["responses_received"],
            "cpu_percent": metrics.cpu_percent if metrics else 0,
            "memory_mb": metrics.memory_mb if metrics else 0
        }
        
        logger.info(f"Baseline for {agent.tenant_id}: "
                   f"{result['message_rate']:.1f} msg/s, "
                   f"CPU={metrics.cpu_percent:.1f}%, "
                   f"Memory={metrics.memory_mb:.1f}MB")
    
    # Phase 2: Test isolation with one stressed tenant
    logger.info("Phase 2: Testing isolation with one tenant under stress")
    
    stressed_agent = agents[0]
    normal_agents = agents[1:]
    
    # Start stressed workload
    stressed_task = asyncio.create_task(
        _sustained_high_load(suite, stressed_agent, duration=120.0)
    )
    
    # Wait for stress to ramp up
    await asyncio.sleep(10.0)
    
    # Start normal workloads for other agents during stress
    normal_tasks = []
    for agent in normal_agents:
        task = asyncio.create_task(
            _sustained_normal_load(suite, agent, duration=90.0)
        )
        normal_tasks.append(task)
    
    # Monitor cross-tenant impact
    impact_monitoring_task = asyncio.create_task(
        _monitor_cross_tenant_impact(suite, normal_agents, stressed_agent, duration=90.0)
    )
    
    # Wait for all workloads
    await stressed_task
    normal_results = await asyncio.gather(*normal_tasks)
    impact_results = await impact_monitoring_task
    
    # Phase 3: Measure performance impact
    logger.info("Phase 3: Measuring performance impact on normal tenants")
    
    # Collect stressed period metrics
    stressed_metrics = {}
    for agent in normal_agents:
        metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=30)
        stressed_metrics[agent.tenant_id] = metrics
    
    # Calculate performance impact
    performance_impact = {}
    for i, agent in enumerate(normal_agents):
        baseline_perf = baseline_performance[agent.tenant_id]
        stressed_result = normal_results[i]
        stressed_metric = stressed_metrics[agent.tenant_id]
        
        # Calculate performance degradation
        message_rate_impact = ((baseline_perf["message_rate"] - stressed_result["message_rate"]) / 
                              baseline_perf["message_rate"] * 100) if baseline_perf["message_rate"] > 0 else 0
        
        cpu_impact = stressed_metric.get('avg_cpu_percent', 0) - baseline_perf["cpu_percent"]
        memory_impact = stressed_metric.get('avg_memory_mb', 0) - baseline_perf["memory_mb"]
        
        performance_impact[agent.tenant_id] = {
            "message_rate_degradation_percent": message_rate_impact,
            "cpu_increase_percent": cpu_impact,
            "memory_increase_mb": memory_impact,
            "overall_impact_percent": max(abs(message_rate_impact), abs(cpu_impact))
        }
        
        logger.info(f"Performance impact for {agent.tenant_id}: "
                   f"Message rate: {message_rate_impact:.1f}%, "
                   f"CPU: {cpu_impact:.1f}%, "
                   f"Memory: {memory_impact:.1f}MB")
    
    # Phase 4: Validate isolation effectiveness
    logger.info("Phase 4: Validating isolation effectiveness")
    
    max_acceptable_impact = RESOURCE_LIMITS["cross_tenant_impact_max"]  # 10%
    
    for agent in normal_agents:
        impact = performance_impact[agent.tenant_id]
        overall_impact = impact["overall_impact_percent"]
        
        assert overall_impact <= max_acceptable_impact, \
            f"Cross-tenant impact too high for {agent.tenant_id}: {overall_impact:.1f}% > {max_acceptable_impact}%"
        
        # Message rate should not degrade significantly
        assert impact["message_rate_degradation_percent"] <= max_acceptable_impact, \
            f"Message rate degraded too much for {agent.tenant_id}: {impact['message_rate_degradation_percent']:.1f}%"
    
    logger.info("[U+2713] Performance isolation validated within acceptable limits")
    
    # Phase 5: Test recovery after stress
    logger.info("Phase 5: Testing performance recovery after stress")
    
    # Allow system to recover
    await asyncio.sleep(20.0)
    
    # Run recovery validation workload
    recovery_tasks = []
    for agent in normal_agents:
        task = asyncio.create_task(
            suite.generate_workload(agent, "normal", duration=30.0)
        )
        recovery_tasks.append(task)
    
    recovery_results = await asyncio.gather(*recovery_tasks)
    
    # Validate recovery
    recovery_performance = {}
    for i, agent in enumerate(normal_agents):
        result = recovery_results[i]
        baseline_perf = baseline_performance[agent.tenant_id]
        
        recovery_rate = result["message_rate"]
        baseline_rate = baseline_perf["message_rate"]
        
        recovery_percentage = (recovery_rate / baseline_rate * 100) if baseline_rate > 0 else 0
        
        recovery_performance[agent.tenant_id] = {
            "recovery_rate": recovery_rate,
            "baseline_rate": baseline_rate,
            "recovery_percentage": recovery_percentage
        }
        
        # Performance should recover to at least 90% of baseline
        assert recovery_percentage >= 90.0, \
            f"Performance did not recover for {agent.tenant_id}: {recovery_percentage:.1f}%"
        
        logger.info(f"Recovery for {agent.tenant_id}: {recovery_percentage:.1f}% of baseline")
    
    # Phase 6: Generate comprehensive isolation report
    logger.info("Phase 6: Generating comprehensive isolation report")
    
    isolation_report = {
        "test_result": "PASSED",
        "baseline_performance": baseline_performance,
        "stressed_tenant": stressed_agent.tenant_id,
        "performance_impact": performance_impact,
        "isolation_effectiveness": {
            "max_impact_observed": max(
                impact["overall_impact_percent"] 
                for impact in performance_impact.values()
            ),
            "max_acceptable_impact": max_acceptable_impact,
            "isolation_maintained": all(
                impact["overall_impact_percent"] <= max_acceptable_impact
                for impact in performance_impact.values()
            )
        },
        "recovery_validation": recovery_performance,
        "cross_tenant_monitoring": impact_results
    }
    
    logger.info("=== Performance Isolation Under Load Test PASSED ===")
    logger.info(f"Max cross-tenant impact: {isolation_report['isolation_effectiveness']['max_impact_observed']:.1f}%")
    logger.info(f"Isolation maintained: {isolation_report['isolation_effectiveness']['isolation_maintained']}")
    logger.info(f"Recovery successful: All tenants recovered to  >= 90% baseline performance")
    
    # Final assertions
    assert isolation_report["isolation_effectiveness"]["isolation_maintained"], \
        "Performance isolation should be maintained under stress"
    
    assert all(perf["recovery_percentage"] >= 90.0 for perf in recovery_performance.values()), \
        "All tenants should recover to at least 90% of baseline performance"


async def _sustained_high_load(suite, agent, duration: float) -> Dict[str, Any]:
    """Generate sustained high load for stress testing."""
    logger.info(f"Starting sustained high load for {agent.tenant_id}")
    
    start_time = time.time()
    total_messages = 0
    load_phases = []
    
    # Phase 1: Ramp up (20% of duration)
    ramp_duration = duration * 0.2
    ramp_result = await suite.generate_workload(agent, "heavy", ramp_duration, "normal")
    load_phases.append(("ramp", ramp_result))
    total_messages += ramp_result["messages_sent"]
    
    # Phase 2: Peak load (60% of duration)
    peak_duration = duration * 0.6
    peak_result = await suite.generate_workload(agent, "heavy", peak_duration, "high")
    load_phases.append(("peak", peak_result))
    total_messages += peak_result["messages_sent"]
    
    # Phase 3: Noisy load (20% of duration)
    noisy_duration = duration * 0.2
    noisy_result = await suite.generate_workload(agent, "noisy", noisy_duration, "extreme")
    load_phases.append(("noisy", noisy_result))
    total_messages += noisy_result["messages_sent"]
    
    return {
        "tenant_id": agent.tenant_id,
        "total_duration": time.time() - start_time,
        "total_messages": total_messages,
        "load_phases": load_phases,
        "average_rate": total_messages / (time.time() - start_time)
    }


async def _sustained_normal_load(suite, agent, duration: float) -> Dict[str, Any]:
    """Generate sustained normal load for comparison."""
    return await suite.generate_workload(agent, "normal", duration)


async def _monitor_cross_tenant_impact(suite, normal_agents, stressed_agent, duration: float) -> Dict[str, Any]:
    """Monitor cross-tenant performance impact during stress test."""
    start_time = time.time()
    impact_samples = []
    
    while time.time() - start_time < duration:
        sample_time = time.time()
        
        # Collect metrics for all agents
        sample = {"timestamp": sample_time}
        
        # Stressed agent metrics
        stressed_metrics = suite.monitor.get_tenant_metrics_summary(stressed_agent.tenant_id, window_seconds=5)
        sample["stressed_agent"] = {
            "tenant_id": stressed_agent.tenant_id,
            "cpu_percent": stressed_metrics.get('avg_cpu_percent', 0),
            "memory_mb": stressed_metrics.get('avg_memory_mb', 0)
        }
        
        # Normal agents metrics
        sample["normal_agents"] = []
        for agent in normal_agents:
            metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=5)
            sample["normal_agents"].append({
                "tenant_id": agent.tenant_id,
                "cpu_percent": metrics.get('avg_cpu_percent', 0),
                "memory_mb": metrics.get('avg_memory_mb', 0)
            })
        
        impact_samples.append(sample)
        await asyncio.sleep(5.0)
    
    # Analyze impact patterns
    stressed_cpu_values = [s["stressed_agent"]["cpu_percent"] for s in impact_samples]
    normal_cpu_values = []
    for agent in normal_agents:
        agent_cpu_values = [
            next((na["cpu_percent"] for na in s["normal_agents"] if na["tenant_id"] == agent.tenant_id), 0)
            for s in impact_samples
        ]
        normal_cpu_values.extend(agent_cpu_values)
    
    return {
        "duration": time.time() - start_time,
        "samples_collected": len(impact_samples),
        "stressed_agent_stats": {
            "avg_cpu": statistics.mean(stressed_cpu_values) if stressed_cpu_values else 0,
            "max_cpu": max(stressed_cpu_values) if stressed_cpu_values else 0,
            "peak_stress_detected": max(stressed_cpu_values) > RESOURCE_LIMITS["per_agent_cpu_max"] if stressed_cpu_values else False
        },
        "normal_agents_stats": {
            "avg_cpu": statistics.mean(normal_cpu_values) if normal_cpu_values else 0,
            "max_cpu": max(normal_cpu_values) if normal_cpu_values else 0,
            "impact_correlation": "low"  # Simplified analysis
        }
    }
