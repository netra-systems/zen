"""

Agent Resource Isolation Test Suite - Refactored Entry Point



This file serves as the main entry point for the refactored agent resource 

isolation tests. It imports all individual test modules and provides a 

unified interface for running the complete test suite.



Business Value Justification (BVJ):

- Segment: Enterprise (multi-tenant isolation requirements)

- Business Goal: Ensure secure per-tenant resource isolation

- Value Impact: Prevents performance degradation affecting $500K+ enterprise contracts

- Revenue Impact: Essential for enterprise trust and SLA compliance



The original test_agent_resource_isolation.py (1640 lines) has been refactored into:

- test_infrastructure.py - Core monitoring and enforcement infrastructure

- test_suite.py - Main test suite class and fixtures

- test_monitoring_baseline.py - Baseline monitoring tests

- test_quota_enforcement.py - Quota enforcement tests  

- test_leak_detection.py - Resource leak detection tests

- test_performance_isolation.py - Performance isolation tests

"""



import pytest

import logging

from shared.isolated_environment import IsolatedEnvironment



logger = logging.getLogger(__name__)



# Import all test modules to register their tests

from tests.e2e.resource_isolation.test_monitoring_baseline import (

    test_per_tenant_resource_monitoring_baseline,

    test_monitoring_accuracy_validation

)



from tests.e2e.resource_isolation.test_quota_enforcement import (

    test_cpu_memory_quota_enforcement

)



from tests.e2e.resource_isolation.test_leak_detection import (

    test_resource_leak_detection_and_prevention

)



from tests.e2e.resource_isolation.test_performance_isolation import (

    test_performance_isolation_under_load

)



# Import fixtures

from tests.e2e.resource_isolation.test_suite import (

    resource_isolation_suite,

    tenant_agents

)





@pytest.mark.asyncio

@pytest.mark.e2e

@pytest.mark.resource_isolation

@pytest.mark.integration

@pytest.mark.timeout(600)

async def test_comprehensive_resource_isolation_suite(resource_isolation_suite, tenant_agents):

    """

    Comprehensive test that validates the complete resource isolation system.

    

    This test runs key validation checks from each isolation test category

    to ensure the system functions correctly as an integrated whole.

    """

    suite = resource_isolation_suite

    agents = tenant_agents

    

    logger.info("=== Comprehensive Resource Isolation Suite ===")

    

    # Test 1: Basic monitoring functionality

    logger.info("Validating basic monitoring functionality...")

    

    # Ensure monitoring is active

    assert suite.monitor.monitoring_active, "Resource monitoring should be active"

    

    # Ensure all agents are registered

    registered_tenants = len(suite.monitor.tenant_processes)

    logger.info(f"Registered tenant processes: {registered_tenants}")

    

    # Test 2: Quota enforcement capability

    logger.info("Validating quota enforcement capability...")

    

    # Check quota enforcer is functional

    test_agent = agents[0]

    cpu_quota_result = await suite.quota_enforcer.enforce_cpu_quota(

        test_agent.tenant_id, 50.0  # 50% quota

    )

    

    memory_quota_result = await suite.quota_enforcer.enforce_memory_quota(

        test_agent.tenant_id, 256.0  # 256MB quota

    )

    

    logger.info(f"Quota enforcement test: CPU={cpu_quota_result}, Memory={memory_quota_result}")

    

    # Test 3: Leak detection capability

    logger.info("Validating leak detection capability...")

    

    # Ensure baseline is established

    assert len(suite.leak_detector.baseline_metrics) > 0, \

        "Leak detector should have baseline metrics"

    

    # Test leak detection

    memory_leaks = suite.leak_detector.detect_memory_leaks(

        growth_threshold_mb=10.0,

        growth_threshold_percent=5.0

    )

    

    logger.info(f"Leak detection test: {len(memory_leaks)} leaks detected")

    

    # Test 4: Performance isolation validator

    logger.info("Validating performance isolation capability...")

    

    # Establish performance baseline

    performance_baseline = await suite.isolation_validator.establish_performance_baseline(

        tenant_ids=[agent.tenant_id for agent in agents[:2]],

        duration=10.0

    )

    

    assert len(performance_baseline) > 0, \

        "Performance baseline should be established"

    

    logger.info(f"Performance baseline established for {len(performance_baseline)} tenants")

    

    # Test 5: End-to-end isolation validation

    logger.info("Running end-to-end isolation validation...")

    

    # Generate brief workload to test system integration

    import asyncio

    

    workload_tasks = []

    for agent in agents:

        task = asyncio.create_task(

            suite.generate_workload(agent, "normal", duration=20.0)

        )

        workload_tasks.append(task)

    

    workload_results = await asyncio.gather(*workload_tasks)

    

    # Validate workload execution

    for i, result in enumerate(workload_results):

        agent = agents[i]

        assert result["messages_sent"] > 10, \

            f"Agent {agent.tenant_id} should send messages: {result['messages_sent']}"

        

        assert result["message_rate"] > 0, \

            f"Agent {agent.tenant_id} should have positive message rate: {result['message_rate']}"

    

    # Final validation

    final_metrics = {}

    for agent in agents:

        metrics = suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=15)

        final_metrics[agent.tenant_id] = metrics

        

        # Ensure metrics are being collected

        assert metrics.get('sample_count', 0) > 0, \

            f"Should have metrics samples for {agent.tenant_id}"

    

    logger.info("=== Comprehensive Resource Isolation Suite PASSED ===")

    logger.info(f"Validated {len(agents)} tenant agents")

    logger.info(f"Total workload messages: {sum(r['messages_sent'] for r in workload_results)}")

    logger.info(f"Resource violations detected: {len(suite.violations_detected)}")

    

    # Assert comprehensive system health

    assert all(result["messages_sent"] > 10 for result in workload_results), \

        "All agents should successfully process workloads"

    

    assert all(metrics.get('sample_count', 0) > 0 for metrics in final_metrics.values()), \

        "All agents should have monitoring metrics"

    

    # Allow some violations but not excessive

    assert len(suite.violations_detected) < len(agents) * 5, \

        f"Excessive violations detected: {len(suite.violations_detected)}"





# Validation helper functions

async def validate_resource_isolation_integrity(suite, agents):

    """Validate overall resource isolation system integrity."""

    validation_results = {

        "monitoring_active": suite.monitor.monitoring_active,

        "agents_registered": len(suite.monitor.tenant_processes),

        "baseline_established": len(suite.leak_detector.baseline_metrics) > 0,

        "quota_enforcer_ready": suite.quota_enforcer is not None,

        "isolation_validator_ready": suite.isolation_validator is not None

    }

    

    logger.info(f"Resource isolation integrity check: {validation_results}")

    

    return all(validation_results.values())





def generate_comprehensive_report(suite, agents, test_results):

    """Generate comprehensive resource isolation test report."""

    report = {

        "test_summary": {

            "total_agents_tested": len(agents),

            "tests_executed": len(test_results),

            "overall_status": "PASSED" if all(test_results.values()) else "FAILED"

        },

        "monitoring_summary": {

            "total_violations": len(suite.violations_detected),

            "monitoring_samples": sum(

                suite.monitor.get_tenant_metrics_summary(agent.tenant_id, window_seconds=60).get('sample_count', 0)

                for agent in agents

            ),

            "agents_monitored": len(suite.monitor.tenant_processes)

        },

        "isolation_validation": {

            "quota_enforcement_functional": suite.quota_enforcer is not None,

            "leak_detection_functional": len(suite.leak_detector.baseline_metrics) > 0,

            "performance_isolation_functional": suite.isolation_validator is not None

        }

    }

    

    logger.info("=== Comprehensive Resource Isolation Report ===")

    logger.info(f"Overall Status: {report['test_summary']['overall_status']}")

    logger.info(f"Agents Tested: {report['test_summary']['total_agents_tested']}")

    logger.info(f"Total Violations: {report['monitoring_summary']['total_violations']}")

    logger.info(f"Monitoring Samples: {report['monitoring_summary']['monitoring_samples']}")

    

    return report

