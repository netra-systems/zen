"""
Network Isolation Tests for Agent Resource Isolation

Tests that validate network isolation between tenant agents to ensure
one tenant's network usage doesn't impact others.

Business Value Justification (BVJ):
- Segment: Enterprise (multi-tenant isolation requirements)
- Business Goal: Ensure network isolation prevents bandwidth monopolization
- Value Impact: Protects against network-based noisy neighbor problems
- Revenue Impact: Critical for $500K+ enterprise contract SLAs
"""

import asyncio
import json
import logging
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
    simulate_workload_burst,
)

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.network_isolation
async def test_network_bandwidth_isolation(resource_isolation_suite, tenant_agents):
    """Test network bandwidth isolation between tenants."""
    suite = resource_isolation_suite
    isolation_base = AgentIsolationBase()
    
    # Establish baseline network usage
    for agent in tenant_agents:
        await isolation_base.establish_baseline_metrics(agent.tenant_id, duration=10.0)
    
    # Select one tenant for high bandwidth usage
    bandwidth_intensive_agent = tenant_agents[0]
    normal_agents = tenant_agents[1:]
    
    # Generate high bandwidth workload (large messages)
    intensive_task = asyncio.create_task(
        _generate_high_bandwidth_workload(bandwidth_intensive_agent, duration=30.0)
    )
    
    # Generate normal workload for other tenants
    normal_tasks = [
        asyncio.create_task(suite.generate_workload(agent, "normal", duration=30.0))
        for agent in normal_agents
    ]
    
    await asyncio.gather(intensive_task, *normal_tasks)
    
    # Check for cross-tenant impact on response times
    normal_tenant_ids = [agent.tenant_id for agent in normal_agents]
    violations = isolation_base.detect_cross_tenant_impact(
        bandwidth_intensive_agent.tenant_id, normal_tenant_ids, threshold_percentage=15.0
    )
    
    # Allow minimal network impact
    assert len(violations) <= 1, f"Network isolation violations: {len(violations)}"
    logger.info("Network bandwidth isolation test passed")

async def _generate_high_bandwidth_workload(agent, duration: float) -> Dict[str, Any]:
    """Generate high bandwidth workload with large messages."""
    start_time = time.time()
    messages_sent = 0
    
    end_time = start_time + duration
    large_payload = "x" * 50000  # 50KB payload
    
    while time.time() < end_time:
        # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
        message = {
            "type": "high_bandwidth_test",
            "tenant_id": agent.tenant_id,
            "message_id": f"{agent.tenant_id}-bandwidth-{messages_sent}",
            "large_payload": large_payload,
            "timestamp": time.time()
        }
        
        await agent.connection.send(json.dumps(message))
        messages_sent += 1
        
        # Send rapidly to consume bandwidth
        await asyncio.sleep(0.05)  # 20 messages per second
    
    return {
        "workload_type": "high_bandwidth",
        "duration": time.time() - start_time,
        "messages_sent": messages_sent,
        "payload_size_kb": 50
    }

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.network_isolation
async def test_connection_burst_isolation(resource_isolation_suite, tenant_agents):
    """Test isolation during connection burst scenarios."""
    suite = resource_isolation_suite
    isolation_base = AgentIsolationBase()
    
    # Generate burst workloads using isolation helper
    burst_results = []
    for agent in tenant_agents:
        if agent.connection:
            result = await isolation_base.simulate_workload_burst(
                agent.connection, agent.tenant_id, burst_size=100, burst_delay=0.01
            )
            burst_results.append(result)
    
    # Analyze burst performance
    success_rates = [r["success_rate"] for r in burst_results]
    avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
    
    # All tenants should maintain reasonable success rates during bursts
    assert avg_success_rate >= 80.0, f"Low burst success rate: {avg_success_rate:.2f}%"
    
    # No tenant should have drastically different performance
    min_success = min(success_rates) if success_rates else 0
    max_success = max(success_rates) if success_rates else 0
    performance_gap = max_success - min_success
    
    assert performance_gap <= 30.0, f"Large performance gap during burst: {performance_gap:.2f}%"
    
    logger.info(f"Connection burst test passed: avg success {avg_success_rate:.2f}%")

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.network_isolation
async def test_message_rate_isolation(resource_isolation_suite, tenant_agents):
    """Test isolation of message rate limits between tenants."""
    suite = resource_isolation_suite
    
    # Generate different message rates for different tenants
    rate_tasks = []
    
    for i, agent in enumerate(tenant_agents):
        # Vary message rates: high, medium, low
        rates = ["extreme", "normal", "low"]
        intensity = rates[i % len(rates)]
        
        task = asyncio.create_task(
            suite.generate_workload(agent, "heavy", duration=25.0, intensity=intensity)
        )
        rate_tasks.append(task)
    
    results = await asyncio.gather(*rate_tasks)
    
    # Analyze message rates
    message_rates = [r.get("message_rate", 0) for r in results]
    
    # Verify each tenant achieved their target rate
    for i, rate in enumerate(message_rates):
        expected_rates = {"extreme": 50, "normal": 10, "low": 2}  # messages per second
        intensity = ["extreme", "normal", "low"][i % 3]
        expected_min = expected_rates[intensity] * 0.5  # Allow 50% tolerance
        
        assert rate >= expected_min, \
            f"Tenant {i} rate too low: {rate:.2f} < {expected_min:.2f} msg/sec"
    
    logger.info(f"Message rate isolation test passed: rates {message_rates}")

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.network_isolation
async def test_websocket_connection_stability(resource_isolation_suite, tenant_agents):
    """Test WebSocket connection stability under network stress."""
    suite = resource_isolation_suite
    
    # Test connection stability with rapid message exchange
    stability_tasks = []
    for agent in tenant_agents:
        task = asyncio.create_task(
            _test_connection_stability(agent, duration=20.0)
        )
        stability_tasks.append(task)
    
    stability_results = await asyncio.gather(*stability_tasks, return_exceptions=True)
    
    # Count connection failures
    failures = []
    for i, result in enumerate(stability_results):
        if isinstance(result, Exception):
            failures.append(f"Agent {i}: {result}")
        elif isinstance(result, dict) and not result.get("stable", True):
            failures.append(f"Agent {i}: Connection unstable")
    
    # Allow minimal connection issues
    max_failures = len(tenant_agents) // 3  # Max 33% can have issues
    assert len(failures) <= max_failures, f"Too many connection failures: {failures}"
    
    logger.info(f"Connection stability test: {len(failures)} failures out of {len(tenant_agents)}")

async def _test_connection_stability(agent, duration: float) -> Dict[str, Any]:
    """Test connection stability for a single agent."""
    start_time = time.time()
    messages_sent = 0
    connection_errors = 0
    
    end_time = start_time + duration
    
    while time.time() < end_time:
        # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
        # Rapid ping-pong messages to test stability
        message = {
            "type": "stability_test",
            "tenant_id": agent.tenant_id,
            "message_id": f"stability-{messages_sent}",
            "timestamp": time.time()
        }
        
        await agent.connection.send(json.dumps(message))
        messages_sent += 1
        
        # Try to receive response
        # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
        # Note: Using timeout for response collection - let timeout raise if needed
        await asyncio.wait_for(agent.connection.recv(), timeout=0.5)
        
        await asyncio.sleep(0.1)
    
    error_rate = connection_errors / messages_sent if messages_sent > 0 else 1.0
    
    return {
        "stable": error_rate < 0.1,  # < 10% error rate is considered stable
        "messages_sent": messages_sent,
        "connection_errors": connection_errors,
        "error_rate": error_rate,
        "duration": time.time() - start_time
    }

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.network_isolation
async def test_concurrent_network_load(resource_isolation_suite, tenant_agents):
    """Test network isolation under concurrent load from all tenants."""
    suite = resource_isolation_suite
    
    # All tenants generate network-intensive workload simultaneously
    concurrent_tasks = [
        asyncio.create_task(
            suite.generate_workload(agent, "noisy", duration=35.0, intensity="normal")
        )
        for agent in tenant_agents
    ]
    
    start_time = time.time()
    results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
    total_duration = time.time() - start_time
    
    # Analyze concurrent performance
    successful_results = [r for r in results if isinstance(r, dict)]
    failed_count = len(results) - len(successful_results)
    
    # Check success rate
    success_rate = len(successful_results) / len(results) * 100
    assert success_rate >= 80.0, f"Low success rate under concurrent load: {success_rate:.2f}%"
    
    # Check message throughput
    total_messages = sum(r.get("messages_sent", 0) for r in successful_results)
    overall_throughput = total_messages / total_duration
    
    # Should maintain reasonable throughput under concurrent load
    min_expected_throughput = len(tenant_agents) * 5  # 5 msg/sec per tenant minimum
    assert overall_throughput >= min_expected_throughput, \
        f"Low throughput: {overall_throughput:.2f} < {min_expected_throughput} msg/sec"
    
    logger.info(f"Concurrent network load test: {success_rate:.2f}% success, "
                f"{overall_throughput:.2f} msg/sec throughput")

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.network_isolation
async def test_network_error_isolation(resource_isolation_suite, tenant_agents):
    """Test that network errors in one tenant don't affect others."""
    suite = resource_isolation_suite
    
    if len(tenant_agents) < 2:
        pytest.skip("Need at least 2 agents for error isolation test")
    
    # Select one agent to simulate network errors
    error_agent = tenant_agents[0]
    normal_agents = tenant_agents[1:]
    
    # Simulate network errors by sending malformed messages
    error_task = asyncio.create_task(
        _simulate_network_errors(error_agent, duration=20.0)
    )
    
    # Normal agents continue with regular workload
    normal_tasks = [
        asyncio.create_task(suite.generate_workload(agent, "normal", duration=20.0))
        for agent in normal_agents
    ]
    
    # Wait for all tasks but don't fail if error agent fails
    await asyncio.gather(error_task, *normal_tasks, return_exceptions=True)
    
    # Check that normal agents were not affected
    final_check_tasks = [
        asyncio.create_task(_quick_connectivity_check(agent))
        for agent in normal_agents
    ]
    
    connectivity_results = await asyncio.gather(*final_check_tasks, return_exceptions=True)
    
    # Count how many normal agents still work
    working_agents = sum(1 for r in connectivity_results 
                        if isinstance(r, dict) and r.get("connected", False))
    
    # Most normal agents should still be working
    min_working = len(normal_agents) * 0.8  # 80% should still work
    assert working_agents >= min_working, \
        f"Network errors affected too many agents: {working_agents}/{len(normal_agents)}"
    
    logger.info(f"Network error isolation test: {working_agents}/{len(normal_agents)} agents working")

async def _simulate_network_errors(agent, duration: float):
    """Simulate network errors for an agent."""
    start_time = time.time()
    end_time = start_time + duration
    
    while time.time() < end_time:
        # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
        # Send malformed/invalid messages
        malformed_messages = [
            "invalid json{",
            json.dumps({"type": "invalid_type", "data": "x" * 100000}),  # Very large
            "",  # Empty message
            json.dumps({"type": None}),  # Invalid type
        ]
        
        for msg in malformed_messages:
            await agent.connection.send(msg)
            await asyncio.sleep(0.1)
        
        await asyncio.sleep(1.0)

async def _quick_connectivity_check(agent) -> Dict[str, Any]:
    """Quick check if agent connection is still working."""
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    test_message = {
        "type": "connectivity_test",
        "tenant_id": agent.tenant_id,
        "timestamp": time.time()
    }
    
    await agent.connection.send(json.dumps(test_message))
    
    # Try to receive any response (or timeout quickly)
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    # Note: Using timeout for response collection - let timeout raise if needed
    await asyncio.wait_for(agent.connection.recv(), timeout=2.0)
    
    return {"connected": True}
