"""

CPU Isolation Tests for Agent Resource Isolation



Tests that validate CPU isolation between tenant agents to ensure

one tenant's CPU usage doesn't impact others.



Business Value Justification (BVJ):

- Segment: Enterprise (multi-tenant isolation requirements)

- Business Goal: Ensure CPU isolation prevents cross-tenant performance impact

- Value Impact: Protects against CPU-based noisy neighbor problems

- Revenue Impact: Critical for $500K+ enterprise contract SLAs

"""



import pytest

import asyncio

import logging

import time

from typing import List

from shared.isolated_environment import IsolatedEnvironment



from tests.e2e.fixtures.resource_monitoring import (

    resource_monitor, isolation_test_config, resource_limits

)

from tests.e2e.test_helpers.agent_isolation_base import AgentIsolationBase, assert_isolation_quality

from tests.e2e.resource_isolation.test_suite import resource_isolation_suite, tenant_agents



logger = logging.getLogger(__name__)



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.cpu_isolation

async def test_cpu_usage_baseline(resource_isolation_suite, tenant_agents, resource_limits):

    """Test baseline CPU usage stays within limits."""

    suite = resource_isolation_suite

    

    # Establish baseline period

    baseline_duration = 20.0

    await asyncio.sleep(baseline_duration)

    

    # Check CPU usage for each tenant

    cpu_violations = []

    for agent in tenant_agents:

        summary = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=15)

        if summary:

            cpu_usage = summary.get("avg_cpu_percent", 0)

            if cpu_usage > resource_limits["cpu_percent_normal"]:

                cpu_violations.append({

                    "tenant": agent.tenant_id,

                    "usage": cpu_usage,

                    "limit": resource_limits["cpu_percent_normal"]

                })

    

    assert len(cpu_violations) == 0, f"CPU baseline violations: {cpu_violations}"

    logger.info(f"CPU baseline test passed for {len(tenant_agents)} tenants")



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.cpu_isolation

async def test_cpu_isolation_under_load(resource_isolation_suite, tenant_agents):

    """Test CPU isolation when one tenant uses high CPU."""

    suite = resource_isolation_suite

    isolation_base = AgentIsolationBase()

    

    # Establish baselines

    for agent in tenant_agents:

        await isolation_base.establish_baseline_metrics(agent.tenant_id, duration=10.0)

    

    # Select one tenant for high CPU usage

    cpu_intensive_agent = tenant_agents[0]

    normal_agents = tenant_agents[1:]

    

    # Generate CPU-intensive workload for one tenant

    intensive_task = asyncio.create_task(

        suite.generate_workload(cpu_intensive_agent, "heavy", duration=40.0, intensity="extreme")

    )

    

    # Generate normal workload for other tenants

    normal_tasks = [

        asyncio.create_task(suite.generate_workload(agent, "normal", duration=40.0))

        for agent in normal_agents

    ]

    

    await asyncio.gather(intensive_task, *normal_tasks)

    

    # Check for cross-tenant impact

    normal_tenant_ids = [agent.tenant_id for agent in normal_agents]

    violations = isolation_base.detect_cross_tenant_impact(

        cpu_intensive_agent.tenant_id, normal_tenant_ids, threshold_percentage=8.0

    )

    

    assert len(violations) <= 1, f"CPU isolation violations: {len(violations)} (max 1 allowed)"

    logger.info("CPU isolation under load test passed")



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.cpu_isolation

async def test_cpu_quota_enforcement(resource_isolation_suite, tenant_agents):

    """Test CPU quota enforcement prevents excessive usage."""

    suite = resource_isolation_suite

    

    cpu_quota_percent = 25.0  # 25% CPU limit

    

    # Generate heavy workload to trigger quota enforcement

    workload_tasks = [

        asyncio.create_task(suite.generate_workload(agent, "heavy", duration=25.0, intensity="high"))

        for agent in tenant_agents

    ]

    

    await asyncio.gather(*workload_tasks)

    

    # Test quota enforcement

    enforcement_results = []

    for agent in tenant_agents:

        result = await suite.quota_enforcer.enforce_cpu_quota(

            agent.tenant_id, cpu_quota_percent

        )

        enforcement_results.append({

            "tenant": agent.tenant_id,

            "quota_enforced": result

        })

    

    # Check violations were detected

    violated_tenants = [r for r in enforcement_results if not r["quota_enforced"]]

    

    # Should have some violations after heavy workload

    assert len(violated_tenants) >= 1, "Expected some CPU quota violations after heavy workload"

    

    logger.info(f"CPU quota enforcement test: {len(violated_tenants)} violations detected")



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.cpu_isolation

async def test_cpu_burst_handling(resource_isolation_suite, tenant_agents, resource_limits):

    """Test handling of CPU burst scenarios."""

    suite = resource_isolation_suite

    

    # Generate burst workloads

    burst_tasks = []

    for agent in tenant_agents:

        # Stagger the burst timing to avoid simultaneous peaks

        delay = tenant_agents.index(agent) * 5.0

        task = asyncio.create_task(_delayed_burst_workload(suite, agent, delay))

        burst_tasks.append(task)

    

    await asyncio.gather(*burst_tasks)

    

    # Check that burst usage didn't exceed critical limits

    critical_violations = []

    for agent in tenant_agents:

        summary = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=20)

        if summary:

            max_cpu = summary.get("max_cpu_percent", 0)

            if max_cpu > resource_limits["cpu_percent_critical"]:

                critical_violations.append({

                    "tenant": agent.tenant_id,

                    "max_usage": max_cpu,

                    "critical_limit": resource_limits["cpu_percent_critical"]

                })

    

    assert len(critical_violations) == 0, f"Critical CPU violations: {critical_violations}"

    logger.info("CPU burst handling test passed")



async def _delayed_burst_workload(suite, agent, delay_seconds):

    """Generate a delayed burst workload."""

    await asyncio.sleep(delay_seconds)

    return await suite.generate_workload(agent, "noisy", duration=15.0, intensity="high")



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.cpu_isolation

async def test_sustained_cpu_load_isolation(resource_isolation_suite, tenant_agents):

    """Test isolation during sustained CPU load."""

    suite = resource_isolation_suite

    isolation_base = AgentIsolationBase()

    

    # Establish baselines

    for agent in tenant_agents:

        await isolation_base.establish_baseline_metrics(agent.tenant_id, duration=5.0)

    

    # Run sustained workload for extended period

    sustained_duration = 60.0  # 1 minute sustained load

    sustained_tasks = [

        asyncio.create_task(

            suite.generate_workload(agent, "heavy", duration=sustained_duration, intensity="normal")

        )

        for agent in tenant_agents

    ]

    

    await asyncio.gather(*sustained_tasks)

    

    # Check isolation quality after sustained load

    report = isolation_base.generate_isolation_report()

    

    # Verify isolation maintained under sustained load

    assert report["summary"]["isolation_score"] >= 80, \

        f"Isolation degraded under sustained load: {report['summary']['isolation_score']}"

    

    # Check CPU-specific violations

    cpu_violations = [v for v in isolation_base.violations if "cpu" in v.violation_type]

    max_cpu_violations = len(tenant_agents) * 3  # Allow some violations during sustained load

    

    assert len(cpu_violations) <= max_cpu_violations, \

        f"Too many CPU violations during sustained load: {len(cpu_violations)}"

    

    logger.info(f"Sustained CPU load test completed: {len(cpu_violations)} violations")



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.cpu_isolation

async def test_cpu_recovery_after_load(resource_isolation_suite, tenant_agents, resource_limits):

    """Test CPU usage recovery after high load periods."""

    suite = resource_isolation_suite

    

    # Generate high CPU load

    high_load_tasks = [

        asyncio.create_task(

            suite.generate_workload(agent, "heavy", duration=25.0, intensity="extreme")

        )

        for agent in tenant_agents

    ]

    

    await asyncio.gather(*high_load_tasks)

    

    # Allow recovery time

    recovery_time = 20.0

    logger.info(f"Allowing {recovery_time}s for CPU recovery...")

    await asyncio.sleep(recovery_time)

    

    # Check CPU usage has returned to normal levels

    post_recovery_violations = []

    for agent in tenant_agents:

        summary = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=10)

        if summary:

            cpu_usage = summary.get("avg_cpu_percent", 0)

            if cpu_usage > resource_limits["cpu_percent_burst"]:

                post_recovery_violations.append({

                    "tenant": agent.tenant_id,

                    "usage": cpu_usage,

                    "limit": resource_limits["cpu_percent_burst"]

                })

    

    assert len(post_recovery_violations) == 0, \

        f"CPU not recovered after load: {post_recovery_violations}"

    

    logger.info("CPU recovery test passed")



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.cpu_isolation

async def test_cpu_fairness_distribution(resource_isolation_suite, tenant_agents):

    """Test fair CPU distribution among tenants."""

    suite = resource_isolation_suite

    

    # Generate equal workload for all tenants

    equal_workload_tasks = [

        asyncio.create_task(

            suite.generate_workload(agent, "heavy", duration=30.0, intensity="normal")

        )

        for agent in tenant_agents

    ]

    

    await asyncio.gather(*equal_workload_tasks)

    

    # Analyze CPU usage distribution

    cpu_usages = []

    for agent in tenant_agents:

        summary = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=20)

        if summary:

            cpu_usages.append(summary.get("avg_cpu_percent", 0))

    

    if len(cpu_usages) > 1:

        # Calculate coefficient of variation for fairness assessment

        import statistics

        mean_cpu = statistics.mean(cpu_usages)

        if mean_cpu > 0:

            std_dev = statistics.stdev(cpu_usages)

            coefficient_of_variation = std_dev / mean_cpu

            

            # Fair distribution should have low variation (< 0.5)

            assert coefficient_of_variation < 0.5, \

                f"Unfair CPU distribution: CV={coefficient_of_variation:.3f}"

        

        # No tenant should use more than 2x the average

        max_cpu = max(cpu_usages)

        if mean_cpu > 0:

            max_ratio = max_cpu / mean_cpu

            assert max_ratio < 2.0, f"CPU monopolization detected: {max_ratio:.2f}x average"

    

    logger.info(f"CPU fairness test passed: {cpu_usages}")

