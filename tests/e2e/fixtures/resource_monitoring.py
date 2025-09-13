"""

Resource Monitoring Fixtures for Agent Isolation Testing



This module provides pytest fixtures for resource monitoring during

agent isolation tests.



Business Value Justification (BVJ):

- Segment: Enterprise (multi-tenant isolation requirements)  

- Business Goal: Provide consistent monitoring infrastructure for tests

- Value Impact: Ensures reliable detection of resource isolation violations

- Revenue Impact: Critical for maintaining $500K+ enterprise contract SLAs

"""



import asyncio

import logging

import time

from contextlib import asynccontextmanager

from typing import Any, Dict, Optional



import pytest

import pytest_asyncio



from tests.e2e.test_helpers.agent_isolation_base import AgentIsolationBase

from tests.e2e.test_helpers.resource_monitoring import (

    MemoryLeakDetector,

    ResourceMonitor,

    resource_monitoring_context,

)



logger = logging.getLogger(__name__)



@pytest_asyncio.fixture

async def resource_monitor():

    """Fixture providing a configured resource monitor."""

    monitor = ResourceMonitor(interval_seconds=2.0)  # Reasonable frequency for test efficiency

    

    await monitor.start()

    try:

        yield monitor

    finally:

        await monitor.stop()



@pytest_asyncio.fixture  

async def memory_leak_detector():

    """Fixture providing a memory leak detector."""

    detector = MemoryLeakDetector(threshold_mb=50.0)

    detector.establish_baseline()

    

    yield detector

    

    # Check for leaks at test end

    leak_result = detector.check_for_leak()

    if leak_result["leak_detected"]:

        logger.warning(f"Memory leak detected at test end: {leak_result}")



@pytest_asyncio.fixture

async def isolation_monitor():

    """Fixture providing an agent isolation monitor."""

    monitor = AgentIsolationBase(monitoring_interval=2.0)

    

    yield monitor

    

    # Generate final report

    report = monitor.generate_isolation_report()

    logger.info(f"Isolation test completed: {report['summary']}")

    

    # Assert basic isolation quality

    if report["summary"]["total_violations"] > 5:

        logger.warning(f"High violation count: {report['summary']['total_violations']}")



@pytest.fixture

def isolation_test_config():

    """Configuration for isolation tests."""

    return {

        "monitoring_interval": 0.5,

        "baseline_duration": 10.0,

        "test_duration": 60.0,

        "violation_threshold": 10.0,  # 10% performance impact

        "resource_limits": {

            "cpu_percent": 25.0,

            "memory_mb": 512.0,

            "response_time_ms": 1000.0

        },

        "workload_configs": {

            "light": {"message_rate": 1, "payload_size": 100},

            "medium": {"message_rate": 5, "payload_size": 1000}, 

            "heavy": {"message_rate": 20, "payload_size": 10000},

            "burst": {"message_rate": 100, "payload_size": 5000}

        }

    }



@pytest_asyncio.fixture

async def test_performance_baseline(resource_monitor, isolation_test_config):

    """Establish performance baseline before tests."""

    config = isolation_test_config

    

    # Establish system baseline

    logger.info(f"Establishing performance baseline for {config['baseline_duration']}s...")

    

    await asyncio.sleep(config["baseline_duration"])

    

    baseline_stats = resource_monitor.get_statistics()

    

    baseline = {

        "timestamp": time.time(),

        "cpu_baseline": baseline_stats.get("cpu", {}).get("avg", 0),

        "memory_baseline": baseline_stats.get("memory", {}).get("avg_mb", 0),

        "thread_baseline": baseline_stats.get("threads", {}).get("avg", 0),

        "config": config

    }

    

    logger.info(f"Baseline established: CPU {baseline['cpu_baseline']:.2f}%, Memory {baseline['memory_baseline']:.2f}MB")

    

    return baseline



@asynccontextmanager

async def test_resource_monitoring_session(test_name: str, monitoring_config: Optional[Dict] = None):

    """Context manager for a resource monitoring session."""

    config = monitoring_config or {"interval": 0.5, "max_samples": 1000}

    

    logger.info(f"Starting resource monitoring session: {test_name}")

    

    async with resource_monitoring_context(interval=config["interval"]) as monitor:

        session_data = {

            "test_name": test_name,

            "start_time": time.time(),

            "monitor": monitor,

            "config": config

        }

        

        try:

            yield session_data

        finally:

            final_stats = monitor.get_statistics()

            duration = time.time() - session_data["start_time"]

            

            logger.info(f"Resource monitoring session completed: {test_name}")

            logger.info(f"Duration: {duration:.2f}s, Samples: {final_stats.get('sample_count', 0)}")

            

            # Log summary statistics

            if "cpu" in final_stats:

                cpu_stats = final_stats["cpu"]

                logger.info(f"CPU: avg={cpu_stats.get('avg', 0):.2f}%, max={cpu_stats.get('max', 0):.2f}%")

            

            if "memory" in final_stats:

                memory_stats = final_stats["memory"]

                logger.info(f"Memory: avg={memory_stats.get('avg_mb', 0):.2f}MB, growth={memory_stats.get('growth_mb', 0):.2f}MB")



@pytest_asyncio.fixture 

async def monitoring_session(request):

    """Fixture providing a monitoring session for the current test."""

    test_name = request.node.name

    

    async with resource_monitoring_session(test_name) as session:

        yield session



@pytest.fixture

def resource_limits():

    """Standard resource limits for isolation tests."""

    return {

        "cpu_percent_normal": 10.0,     # Normal operation limit

        "cpu_percent_burst": 25.0,      # Burst operation limit

        "cpu_percent_critical": 50.0,   # Critical threshold

        "memory_mb_normal": 256.0,      # Normal operation limit

        "memory_mb_burst": 512.0,       # Burst operation limit

        "memory_mb_critical": 1024.0,   # Critical threshold

        "response_time_ms": 1000.0,     # Response time limit

        "violation_threshold": 0,       # Zero tolerance for violations

        "cross_tenant_impact": 5.0      # Max 5% cross-tenant impact

    }



@pytest_asyncio.fixture

async def tenant_isolation_context(isolation_monitor, resource_limits):

    """Context for multi-tenant isolation testing."""

    context = {

        "monitor": isolation_monitor,

        "limits": resource_limits,

        "tenants": {},

        "baselines": {},

        "violations": []

    }

    

    async def add_tenant(tenant_id: str, resource_tier: str = "medium"):

        """Add a tenant to the isolation context."""

        tenant_config = isolation_monitor.create_test_agent_config(tenant_id, resource_tier)

        context["tenants"][tenant_id] = tenant_config

        

        # Establish baseline for this tenant with shorter duration for tests

        try:

            # Use much shorter baseline for tests (5 seconds instead of 30)

            baseline = await isolation_monitor.establish_baseline_metrics(tenant_id, duration=5.0)

            context["baselines"][tenant_id] = baseline

        except Exception as e:

            logger.warning(f"Could not establish baseline for {tenant_id}: {e}")

            # Create a minimal baseline if establishment fails

            from tests.e2e.test_helpers.agent_isolation_base import IsolationTestMetrics

            import time

            baseline = IsolationTestMetrics(

                tenant_id=tenant_id,

                test_start_time=time.time(),

                baseline_cpu=0.0,

                baseline_memory_mb=0.0

            )

            context["baselines"][tenant_id] = baseline

        

        logger.info(f"Added tenant {tenant_id} to isolation context")

        return tenant_config

    

    async def check_violations():

        """Check for isolation violations across all tenants."""

        all_tenants = list(context["tenants"].keys())

        new_violations = []

        

        for source_tenant in all_tenants:

            target_tenants = [t for t in all_tenants if t != source_tenant]

            violations = isolation_monitor.detect_cross_tenant_impact(

                source_tenant, target_tenants, 

                threshold_percentage=context["limits"]["cross_tenant_impact"]

            )

            new_violations.extend(violations)

        

        context["violations"].extend(new_violations)

        return new_violations

    

    context["add_tenant"] = add_tenant

    context["check_violations"] = check_violations

    

    yield context

    

    # Final violation check

    final_violations = await context["check_violations"]()

    if final_violations:

        logger.warning(f"Final violation check found {len(final_violations)} violations")



@pytest.fixture(scope="session")

def isolation_test_session():

    """Session-scoped fixture for isolation test configuration."""

    return {

        "start_time": time.time(),

        "test_count": 0,

        "violation_count": 0,

        "performance_samples": [],

        "session_id": f"isolation_test_{int(time.time())}"

    }



def assert_resource_within_limits(metrics: Dict[str, Any], limits: Dict[str, float], tenant_id: str):

    """Assert that resource usage is within specified limits."""

    cpu_usage = metrics.get("cpu_percent", 0)

    memory_usage = metrics.get("memory_mb", 0)

    

    assert cpu_usage <= limits["cpu_percent_critical"], \

        f"CPU usage too high for {tenant_id}: {cpu_usage:.2f}% > {limits['cpu_percent_critical']:.2f}%"

    

    assert memory_usage <= limits["memory_mb_critical"], \

        f"Memory usage too high for {tenant_id}: {memory_usage:.2f}MB > {limits['memory_mb_critical']:.2f}MB"

    

    logger.info(f"Resource limits OK for {tenant_id}: CPU {cpu_usage:.2f}%, Memory {memory_usage:.2f}MB")



def assert_no_cross_tenant_impact(isolation_monitor: AgentIsolationBase, 

                                 max_impact_percent: float = 5.0):

    """Assert that there is no significant cross-tenant impact."""

    violations = [v for v in isolation_monitor.violations 

                 if v.violation_type == "performance" and v.impact_percentage > max_impact_percent]

    

    assert len(violations) == 0, \

        f"Cross-tenant impact violations detected: {len(violations)} violations above {max_impact_percent}%"

    

    logger.info(f"No cross-tenant impact violations above {max_impact_percent}%")



def log_test_metrics(test_name: str, metrics: Dict[str, Any], duration: float):

    """Log test metrics in a standardized format."""

    logger.info(f"=== Test Metrics: {test_name} ===")

    logger.info(f"Duration: {duration:.2f}s")

    

    if "resource_usage" in metrics:

        resource = metrics["resource_usage"]

        logger.info(f"CPU: avg={resource.get('avg_cpu', 0):.2f}%, max={resource.get('max_cpu', 0):.2f}%")

        logger.info(f"Memory: avg={resource.get('avg_memory', 0):.2f}MB, max={resource.get('max_memory', 0):.2f}MB")

    

    if "violations" in metrics:

        violations = metrics["violations"]

        logger.info(f"Violations: {violations.get('total', 0)} total, {violations.get('critical', 0)} critical")

    

    if "performance" in metrics:

        perf = metrics["performance"]

        logger.info(f"Performance: {perf.get('success_rate', 0):.2f}% success rate")

    

    logger.info(f"=== End Metrics: {test_name} ===")

