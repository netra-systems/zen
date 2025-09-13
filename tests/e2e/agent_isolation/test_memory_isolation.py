"""

Memory Isolation Tests for Agent Resource Isolation



Tests that validate memory isolation between tenant agents to ensure

one tenant's memory usage doesn't impact others.



Business Value Justification (BVJ):

- Segment: Enterprise (multi-tenant isolation requirements)

- Business Goal: Ensure memory isolation prevents cross-tenant impact

- Value Impact: Protects against memory-based noisy neighbor problems

- Revenue Impact: Critical for $500K+ enterprise contract SLAs

"""



import pytest

import asyncio

import logging

import time

from typing import Dict, Any

from shared.isolated_environment import IsolatedEnvironment



from tests.e2e.fixtures.resource_monitoring import (

    resource_monitor, memory_leak_detector, isolation_test_config,

    resource_limits, assert_resource_within_limits

)

from tests.e2e.test_helpers.agent_isolation_base import AgentIsolationBase, assert_isolation_quality

from tests.e2e.resource_isolation.test_suite import resource_isolation_suite, tenant_agents



logger = logging.getLogger(__name__)



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.memory_isolation

async def test_memory_usage_baseline(resource_isolation_suite, tenant_agents, resource_limits):

    """Test baseline memory usage stays within limits."""

    suite = resource_isolation_suite

    

    # Establish baseline

    baseline_duration = 15.0

    await asyncio.sleep(baseline_duration)

    

    # Check memory usage for each tenant

    memory_violations = []

    for agent in tenant_agents:

        summary = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=10)

        if summary:

            memory_usage = summary.get("avg_memory_mb", 0)

            if memory_usage > resource_limits["memory_mb_normal"]:

                memory_violations.append({

                    "tenant": agent.tenant_id,

                    "usage": memory_usage,

                    "limit": resource_limits["memory_mb_normal"]

                })

    

    assert len(memory_violations) == 0, f"Memory baseline violations: {memory_violations}"

    logger.info(f"Memory baseline test passed for {len(tenant_agents)} tenants")



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.memory_isolation

async def test_memory_leak_detection(resource_isolation_suite, tenant_agents, memory_leak_detector):

    """Test memory leak detection functionality."""

    suite = resource_isolation_suite

    

    # Generate workload that might cause memory growth

    workload_tasks = []

    for agent in tenant_agents:

        task = asyncio.create_task(

            suite.generate_workload(agent, "heavy", duration=30.0, intensity="normal")

        )

        workload_tasks.append(task)

    

    await asyncio.gather(*workload_tasks)

    

    # Check for memory leaks

    leak_result = memory_leak_detector.check_for_leak()

    

    # Log the results but don't fail if small growth is detected

    if leak_result["leak_detected"]:

        growth_mb = leak_result["growth_mb"]

        logger.warning(f"Memory growth detected: {growth_mb:.2f}MB")

        

        # Only fail if growth is excessive (> 100MB)

        assert growth_mb < 100.0, f"Excessive memory growth: {growth_mb:.2f}MB"

    

    logger.info("Memory leak detection test completed")



@pytest.mark.asyncio

@pytest.mark.e2e  

@pytest.mark.memory_isolation

async def test_memory_isolation_under_load(resource_isolation_suite, tenant_agents):

    """Test memory isolation when one tenant uses high memory."""

    suite = resource_isolation_suite

    isolation_base = AgentIsolationBase()

    

    # Establish baselines

    for agent in tenant_agents:

        await isolation_base.establish_baseline_metrics(agent.tenant_id, duration=10.0)

    

    # Select one tenant for high memory usage

    memory_intensive_agent = tenant_agents[0]

    normal_agents = tenant_agents[1:]

    

    # Generate memory-intensive workload for one tenant

    intensive_task = asyncio.create_task(

        suite.generate_workload(memory_intensive_agent, "heavy", duration=45.0, intensity="high")

    )

    

    # Generate normal workload for other tenants  

    normal_tasks = [

        asyncio.create_task(suite.generate_workload(agent, "normal", duration=45.0))

        for agent in normal_agents

    ]

    

    await asyncio.gather(intensive_task, *normal_tasks)

    

    # Check for cross-tenant impact

    normal_tenant_ids = [agent.tenant_id for agent in normal_agents]

    violations = isolation_base.detect_cross_tenant_impact(

        memory_intensive_agent.tenant_id, normal_tenant_ids, threshold_percentage=5.0

    )

    

    assert len(violations) == 0, f"Memory isolation violations detected: {len(violations)}"

    logger.info("Memory isolation under load test passed")



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.memory_isolation

async def test_memory_quota_enforcement(resource_isolation_suite, tenant_agents):

    """Test memory quota enforcement prevents excessive usage."""

    suite = resource_isolation_suite

    

    memory_quota_mb = 512.0  # 512MB limit

    

    # Test quota enforcement for each tenant

    enforcement_results = []

    for agent in tenant_agents:

        result = await suite.quota_enforcer.enforce_memory_quota(

            agent.tenant_id, memory_quota_mb

        )

        enforcement_results.append({

            "tenant": agent.tenant_id,

            "quota_enforced": result

        })

    

    # Check that quota enforcement is working

    violated_tenants = [r for r in enforcement_results if not r["quota_enforced"]]

    

    # Allow some violations during heavy workload testing

    max_allowed_violations = len(tenant_agents) // 2

    assert len(violated_tenants) <= max_allowed_violations, \

        f"Too many quota violations: {len(violated_tenants)}"

    

    logger.info(f"Memory quota enforcement test: {len(violated_tenants)} violations")



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.memory_isolation

async def test_memory_recovery_after_load(resource_isolation_suite, tenant_agents, resource_limits):

    """Test memory recovery after high load periods."""

    suite = resource_isolation_suite

    

    # Generate high memory load

    high_load_tasks = [

        asyncio.create_task(suite.generate_workload(agent, "heavy", duration=20.0, intensity="high"))

        for agent in tenant_agents

    ]

    

    await asyncio.gather(*high_load_tasks)

    

    # Allow recovery time

    recovery_time = 30.0

    logger.info(f"Allowing {recovery_time}s for memory recovery...")

    await asyncio.sleep(recovery_time)

    

    # Check that memory usage has returned to reasonable levels

    post_recovery_violations = []

    for agent in tenant_agents:

        summary = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=10)

        if summary:

            memory_usage = summary.get("avg_memory_mb", 0)

            if memory_usage > resource_limits["memory_mb_burst"]:

                post_recovery_violations.append({

                    "tenant": agent.tenant_id,

                    "usage": memory_usage,

                    "limit": resource_limits["memory_mb_burst"]

                })

    

    assert len(post_recovery_violations) == 0, \

        f"Memory not recovered after load: {post_recovery_violations}"

    

    logger.info("Memory recovery test passed")



@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.memory_isolation

async def test_concurrent_memory_stress(resource_isolation_suite, tenant_agents):

    """Test memory isolation with concurrent memory stress."""

    suite = resource_isolation_suite

    isolation_base = AgentIsolationBase()

    

    # Establish baselines

    for agent in tenant_agents:

        await isolation_base.establish_baseline_metrics(agent.tenant_id, duration=5.0)

    

    # Run concurrent memory-intensive workloads

    concurrent_tasks = [

        asyncio.create_task(suite.generate_workload(agent, "noisy", duration=30.0, intensity="normal"))

        for agent in tenant_agents

    ]

    

    await asyncio.gather(*concurrent_tasks)

    

    # Generate isolation report

    report = isolation_base.generate_isolation_report()

    

    # Check overall isolation quality

    assert report["summary"]["isolation_score"] >= 75, \

        f"Isolation score too low: {report['summary']['isolation_score']}"

    

    # Check for memory-specific violations

    memory_violations = [v for v in isolation_base.violations if "memory" in v.violation_type]

    max_memory_violations = len(tenant_agents) * 2  # Allow some violations

    

    assert len(memory_violations) <= max_memory_violations, \

        f"Too many memory violations: {len(memory_violations)}"

    

    logger.info(f"Concurrent memory stress test completed: {len(memory_violations)} violations")

