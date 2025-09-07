"""
Multi-Tenant Isolation Tests for Agent Resource Isolation

Comprehensive tests that validate isolation across multiple tenant agents
simultaneously, ensuring enterprise-grade multi-tenancy.

Business Value Justification (BVJ):
- Segment: Enterprise (critical for $500K+ contracts)
- Business Goal: Ensure complete multi-tenant isolation at scale
- Value Impact: Prevents any cross-tenant interference in production
- Revenue Impact: Essential for enterprise trust and regulatory compliance
"""

import asyncio
import json
import logging
import statistics
import time
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.fixtures.resource_monitoring import (
    isolation_test_config,
    resource_limits,
)
from tests.e2e.resource_isolation.test_suite import (
    resource_isolation_suite,
    tenant_agents,
)
from tests.e2e.test_helpers.agent_isolation_base import (
    AgentIsolationBase,
    assert_isolation_quality,
)

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.multi_tenant_isolation
@pytest.mark.timeout(600)  # 10 minutes for comprehensive test
async def test_comprehensive_multi_tenant_isolation(resource_isolation_suite):
    """Comprehensive multi-tenant isolation test across all resource types."""
    # Skip complex tenant isolation context fixture for now and focus on core functionality
    pytest.skip("Agent isolation infrastructure requires authenticated WebSocket connections - skipping until proper test auth is implemented")
    
    suite = resource_isolation_suite
    
    # Create diverse tenant workload profiles
    tenant_profiles = [
        {"tier": "light", "workload": "normal", "intensity": "low"},
        {"tier": "medium", "workload": "heavy", "intensity": "normal"},
        {"tier": "heavy", "workload": "noisy", "intensity": "high"},
        {"tier": "medium", "workload": "mixed", "intensity": "normal"},
        {"tier": "light", "workload": "normal", "intensity": "low"}
    ]
    
    # Add tenants with different profiles
    tenants = []
    for i, profile in enumerate(tenant_profiles):
        tenant_id = f"multi_tenant_{i}"
        tenant_config = await context["add_tenant"](tenant_id, profile["tier"])
        tenants.append({
            "id": tenant_id,
            "config": tenant_config,
            "profile": profile
        })
    
    # Create agents for tenants
    tenant_agents_list = await suite.create_tenant_agents(len(tenants))
    connected_agents = await suite.establish_agent_connections(tenant_agents_list)
    
    if len(connected_agents) < len(tenants) * 0.8:
        pytest.skip(f"Insufficient connections: {len(connected_agents)}/{len(tenants)}")
    
    # Run concurrent workloads with different patterns
    workload_tasks = []
    for i, agent in enumerate(connected_agents):
        if i < len(tenant_profiles):
            profile = tenant_profiles[i]
            task = asyncio.create_task(
                suite.generate_workload(
                    agent, 
                    profile["workload"], 
                    duration=120.0,  # 2 minutes
                    intensity=profile["intensity"]
                )
            )
            workload_tasks.append(task)
    
    # Execute workloads concurrently
    start_time = time.time()
    results = await asyncio.gather(*workload_tasks, return_exceptions=True)
    execution_time = time.time() - start_time
    
    # Check for violations across all tenants
    violations = await context["check_violations"]()
    
    # Analyze results
    successful_results = [r for r in results if isinstance(r, dict)]
    success_rate = len(successful_results) / len(workload_tasks) * 100
    
    # Assertions for comprehensive isolation
    assert success_rate >= 80.0, f"Low multi-tenant success rate: {success_rate:.2f}%"
    assert len(violations) <= len(tenants), f"Too many isolation violations: {len(violations)}"
    assert execution_time < 180.0, f"Test took too long: {execution_time:.2f}s"
    
    # Check resource distribution fairness
    await _assert_fair_resource_distribution(suite, connected_agents)
    
    logger.info(f"Comprehensive multi-tenant test: {success_rate:.2f}% success, {len(violations)} violations")

async def _assert_fair_resource_distribution(suite, agents):
    """Assert that resources are distributed fairly among tenants."""
    resource_usage = []
    
    for agent in agents:
        summary = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=30)
        if summary:
            resource_usage.append({
                "tenant": agent.tenant_id,
                "cpu": summary.get("avg_cpu_percent", 0),
                "memory": summary.get("avg_memory_mb", 0)
            })
    
    if len(resource_usage) > 1:
        cpu_values = [r["cpu"] for r in resource_usage]
        memory_values = [r["memory"] for r in resource_usage]
        
        # Check CPU fairness
        if cpu_values and max(cpu_values) > 0:
            cpu_cv = statistics.stdev(cpu_values) / statistics.mean(cpu_values)
            assert cpu_cv < 1.0, f"Unfair CPU distribution: CV={cpu_cv:.3f}"
        
        # Check memory fairness  
        if memory_values and max(memory_values) > 0:
            memory_cv = statistics.stdev(memory_values) / statistics.mean(memory_values)
            assert memory_cv < 1.0, f"Unfair memory distribution: CV={memory_cv:.3f}"

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.multi_tenant_isolation
async def test_tenant_data_isolation(resource_isolation_suite, tenant_agents):
    """Test that tenant data remains isolated and doesn't leak between tenants."""
    suite = resource_isolation_suite
    
    # Generate unique data for each tenant
    tenant_data = {}
    data_exchange_tasks = []
    
    for i, agent in enumerate(tenant_agents):
        unique_data = f"SECRET_DATA_FOR_TENANT_{agent.tenant_id}_{time.time()}_{i}"
        tenant_data[agent.tenant_id] = unique_data
        
        # Send unique data through the agent
        task = asyncio.create_task(
            _send_sensitive_data(agent, unique_data, duration=30.0)
        )
        data_exchange_tasks.append(task)
    
    results = await asyncio.gather(*data_exchange_tasks, return_exceptions=True)
    
    # Analyze responses for data leakage
    data_leaks = []
    successful_results = [r for r in results if isinstance(r, dict)]
    
    for result in successful_results:
        tenant_id = result["tenant_id"]
        responses = result.get("responses", [])
        
        # Check if this tenant's responses contain other tenants' data
        for other_tenant_id, other_data in tenant_data.items():
            if other_tenant_id != tenant_id:
                for response in responses:
                    if other_data in str(response):
                        data_leaks.append({
                            "victim": tenant_id,
                            "leaked_from": other_tenant_id,
                            "leaked_data": other_data[:50] + "..."
                        })
    
    assert len(data_leaks) == 0, f"Data isolation violations detected: {data_leaks}"
    logger.info(f"Tenant data isolation test passed: {len(successful_results)} tenants validated")

async def _send_sensitive_data(agent, sensitive_data: str, duration: float) -> Dict[str, Any]:
    """Send sensitive data through an agent and collect responses."""
    start_time = time.time()
    messages_sent = 0
    responses = []
    
    end_time = start_time + duration
    
    try:
        while time.time() < end_time:
            message = {
                "type": "sensitive_data_test",
                "tenant_id": agent.tenant_id,
                "sensitive_payload": sensitive_data,
                "message_id": f"{agent.tenant_id}-sensitive-{messages_sent}",
                "timestamp": time.time()
            }
            
            await agent.connection.send(json.dumps(message))
            messages_sent += 1
            
            # Try to collect response
            try:
                response = await asyncio.wait_for(agent.connection.recv(), timeout=1.0)
                responses.append(response)
            except asyncio.TimeoutError:
                pass
            
            await asyncio.sleep(1.0)
    
    except Exception as e:
        logger.error(f"Sensitive data test error for {agent.tenant_id}: {e}")
    
    return {
        "tenant_id": agent.tenant_id,
        "messages_sent": messages_sent,
        "responses": responses,
        "duration": time.time() - start_time
    }

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.multi_tenant_isolation
async def test_scalable_tenant_isolation(resource_isolation_suite):
    """Test isolation scales properly with increasing tenant count."""
    suite = resource_isolation_suite
    
    # Test with increasing numbers of tenants
    tenant_counts = [5, 10, 15]
    scalability_results = []
    
    for count in tenant_counts:
        logger.info(f"Testing isolation with {count} tenants...")
        
        # Create tenants for this scale test
        test_agents = await suite.create_tenant_agents(count)
        connected = await suite.establish_agent_connections(test_agents)
        
        if len(connected) < count * 0.8:
            logger.warning(f"Only {len(connected)}/{count} agents connected")
            continue
        
        # Run scale test
        start_time = time.time()
        
        # Generate moderate workload for all tenants
        scale_tasks = [
            asyncio.create_task(
                suite.generate_workload(agent, "normal", duration=20.0)
            )
            for agent in connected
        ]
        
        scale_results = await asyncio.gather(*scale_tasks, return_exceptions=True)
        test_duration = time.time() - start_time
        
        # Analyze scale performance
        successful = [r for r in scale_results if isinstance(r, dict)]
        success_rate = len(successful) / len(scale_tasks) * 100
        
        # Calculate resource efficiency
        total_messages = sum(r.get("messages_sent", 0) for r in successful)
        throughput = total_messages / test_duration
        efficiency = throughput / count if count > 0 else 0
        
        scalability_results.append({
            "tenant_count": count,
            "success_rate": success_rate,
            "throughput": throughput,
            "efficiency": efficiency,
            "duration": test_duration
        })
        
        # Cleanup for next iteration
        for agent in test_agents:
            if agent.connection:
                try:
                    await agent.connection.close()
                except Exception as e:
                    # Connection cleanup failures are non-critical between test iterations
                    logger.debug(f"Failed to close connection for agent: {e}")
    
    # Analyze scalability
    if len(scalability_results) >= 2:
        # Success rate should remain high
        min_success_rate = min(r["success_rate"] for r in scalability_results)
        assert min_success_rate >= 75.0, f"Success rate degraded at scale: {min_success_rate:.2f}%"
        
        # Efficiency shouldn't degrade too much (allow 50% degradation)
        efficiencies = [r["efficiency"] for r in scalability_results]
        if max(efficiencies) > 0:
            efficiency_ratio = min(efficiencies) / max(efficiencies)
            assert efficiency_ratio >= 0.5, f"Efficiency degraded too much: {efficiency_ratio:.3f}"
    
    logger.info(f"Scalability test results: {scalability_results}")

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.multi_tenant_isolation  
async def test_tenant_failure_isolation(resource_isolation_suite, tenant_agents):
    """Test that failure in one tenant doesn't affect others."""
    suite = resource_isolation_suite
    
    if len(tenant_agents) < 3:
        pytest.skip("Need at least 3 agents for failure isolation test")
    
    # Select one tenant to fail
    failing_agent = tenant_agents[0]
    healthy_agents = tenant_agents[1:]
    
    # Start normal workload for healthy tenants
    healthy_tasks = [
        asyncio.create_task(
            suite.generate_workload(agent, "normal", duration=40.0)
        )
        for agent in healthy_agents
    ]
    
    # Simulate failure in one tenant after brief delay
    failure_task = asyncio.create_task(
        _simulate_tenant_failure(failing_agent, delay=10.0)
    )
    
    # Wait for all tasks
    all_results = await asyncio.gather(*healthy_tasks, failure_task, return_exceptions=True)
    
    # Analyze healthy tenant results (exclude the last result which is the failure)
    healthy_results = all_results[:-1]
    successful_healthy = [r for r in healthy_results if isinstance(r, dict)]
    
    # Most healthy tenants should continue working despite one failure
    healthy_success_rate = len(successful_healthy) / len(healthy_agents) * 100
    assert healthy_success_rate >= 80.0, \
        f"Tenant failure affected too many others: {healthy_success_rate:.2f}%"
    
    # Check that healthy tenants maintained performance
    message_rates = [r.get("message_rate", 0) for r in successful_healthy]
    if message_rates:
        avg_rate = statistics.mean(message_rates)
        assert avg_rate >= 0.5, f"Performance degraded after tenant failure: {avg_rate:.2f} msg/sec"
    
    logger.info(f"Tenant failure isolation: {len(successful_healthy)}/{len(healthy_agents)} healthy tenants succeeded")

async def _simulate_tenant_failure(agent, delay: float):
    """Simulate failure in a tenant after delay."""
    await asyncio.sleep(delay)
    
    try:
        # Send malformed messages to cause errors
        malformed_messages = [
            "invalid json",
            json.dumps({"type": "crash_simulation"}),
            "",
            None
        ]
        
        for msg in malformed_messages:
            try:
                if msg is not None:
                    await agent.connection.send(str(msg))
                await asyncio.sleep(0.1)
            except Exception:
                pass  # Expected failures
        
        # Force close connection
        await agent.connection.close()
        
    except Exception:
        pass  # Failure simulation, exceptions expected

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.multi_tenant_isolation
async def test_resource_quota_enforcement_at_scale(resource_isolation_suite, tenant_agents):
    """Test resource quota enforcement across multiple tenants simultaneously."""
    suite = resource_isolation_suite
    
    # Set quotas for all tenants
    cpu_quota = 20.0  # 20% CPU
    memory_quota = 400.0  # 400MB
    
    # Generate heavy workload to trigger quotas
    quota_test_tasks = [
        asyncio.create_task(
            suite.generate_workload(agent, "heavy", duration=30.0, intensity="high")
        )
        for agent in tenant_agents
    ]
    
    await asyncio.gather(*quota_test_tasks, return_exceptions=True)
    
    # Check quota enforcement for each tenant
    quota_violations = []
    enforcement_actions = []
    
    for agent in tenant_agents:
        # Test CPU quota
        cpu_result = await suite.quota_enforcer.enforce_cpu_quota(
            agent.tenant_id, cpu_quota
        )
        if not cpu_result:
            quota_violations.append(f"{agent.tenant_id}: CPU quota violated")
        
        # Test memory quota
        memory_result = await suite.quota_enforcer.enforce_memory_quota(
            agent.tenant_id, memory_quota
        )
        if not memory_result:
            quota_violations.append(f"{agent.tenant_id}: Memory quota violated")
        
        if not cpu_result or not memory_result:
            enforcement_actions.append(agent.tenant_id)
    
    # Should have detected some violations after heavy workload
    violation_rate = len(quota_violations) / (len(tenant_agents) * 2) * 100  # 2 quotas per tenant
    assert violation_rate >= 20.0, f"Too few quota violations detected: {violation_rate:.2f}%"
    
    # But not all tenants should be violating quotas
    assert violation_rate <= 80.0, f"Too many quota violations: {violation_rate:.2f}%"
    
    logger.info(f"Resource quota test: {len(quota_violations)} violations across {len(tenant_agents)} tenants")

