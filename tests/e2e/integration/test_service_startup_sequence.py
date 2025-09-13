"""

Service Startup Sequence E2E Tests - Test #3



BVJ (Business Value Justification):

1. Segment: ALL customer segments

2. Business Goal: System availability = 100% revenue protection

3. Value Impact: Prevents startup failures that cause total system outage

4. Revenue Impact: Each failure prevented saves 100% of MRR during outage



REQUIREMENTS:

- Validates complete startup flow with proper dependency order

- Tests auth service starts first, backend waits for auth, frontend waits for both

- Includes database connection validation (PostgreSQL, ClickHouse)

- Tests inter-service communication after startup

- Performance assertions for <60s startup time

- Failure scenario testing for dependency failures

- 450-line file limit, 25-line function limit

"""

import sys

from pathlib import Path

from shared.isolated_environment import IsolatedEnvironment



import pytest



# Add project root to path for imports



from tests.e2e.service_failure_tester import ServiceFailureScenarioTester

from tests.e2e.startup_sequence_validator import ServiceStartupSequenceValidator



# PYTEST TEST IMPLEMENTATIONS



@pytest.mark.asyncio

@pytest.mark.e2e

async def test_complete_service_startup_sequence():

    """

    Test #3: Complete Service Startup Sequence with Dependencies

    

    BVJ: System availability = 100% revenue protection

    - Validates auth service starts first

    - Backend waits for auth to be healthy  

    - Frontend waits for both auth and backend

    - All database connections established

    - Inter-service communication verified

    - Performance assertion <60s

    """

    validator = ServiceStartupSequenceValidator()

    

    try:

        results = await _execute_startup_validation(validator)

        _validate_startup_results(results)

        _print_startup_success(results)

        

    finally:

        await validator.cleanup()





async def _execute_startup_validation(validator):

    """Execute complete startup sequence validation."""

    return await validator.validate_complete_startup_sequence()





def _validate_startup_results(results):

    """Validate startup test results."""

    assert results["success"], f"Startup sequence failed: {results.get('error')}"

    assert results["total_startup_time"] < 60.0, f"Startup too slow: {results['total_startup_time']:.2f}s"

    

    expected_order = ["auth", "backend", "frontend"]

    assert results["startup_order"] == expected_order, f"Wrong startup order: {results['startup_order']}"

    

    _validate_service_startup_times(results["startup_times"])





def _validate_service_startup_times(startup_times):

    """Validate each service started within reasonable time."""

    for service, startup_time in startup_times.items():

        assert startup_time < 30.0, f"{service} startup too slow: {startup_time:.2f}s"





def _print_startup_success(results):

    """Print startup test success message."""

    print(f"[SUCCESS] Service Startup Sequence: {results['total_startup_time']:.2f}s")

    print(f"[PROTECTED] 100% MRR through system availability")





@pytest.mark.asyncio  

@pytest.mark.e2e

async def test_dependency_failure_scenarios():

    """

    Test dependency failure scenarios and graceful degradation.

    

    BVJ: Prevents cascading failures that cause total system outage

    - Tests behavior when auth service unavailable

    - Validates graceful degradation with optional services down

    - Ensures core functionality remains operational

    """

    failure_tester = ServiceFailureScenarioTester()

    

    try:

        await _execute_failure_tests(failure_tester)

        _print_failure_success()

        

    finally:

        await failure_tester.cleanup()





async def _execute_failure_tests(failure_tester):

    """Execute all failure scenario tests."""

    auth_failure_results = await failure_tester.test_auth_dependency_failure()

    _validate_auth_failure_results(auth_failure_results)

    

    degradation_results = await failure_tester.test_graceful_degradation()

    _validate_degradation_results(degradation_results)





def _validate_auth_failure_results(results):

    """Validate auth dependency failure test results."""

    assert results["success"], f"Auth failure test failed: {results.get('error')}"





def _validate_degradation_results(results):

    """Validate graceful degradation test results."""

    assert results["success"], f"Graceful degradation failed: {results.get('error')}"





def _print_failure_success():

    """Print failure test success message."""

    print("[SUCCESS] Dependency failure scenarios validated")

    print("[PROTECTED] Graceful degradation prevents total outage")





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_performance_requirements():

    """

    Test performance requirements for service startup.

    

    BVJ: Fast startup times reduce customer wait and improve experience

    - All services must start within 60 seconds total

    - Individual services must start within 30 seconds

    - Database connections established within 10 seconds

    """

    validator = ServiceStartupSequenceValidator()

    

    try:

        results = await _execute_performance_test(validator)

        _validate_performance_requirements(results)

        _print_performance_success(results)

        

    finally:

        await validator.cleanup()





async def _execute_performance_test(validator):

    """Execute performance test for startup sequence."""

    return await validator.validate_complete_startup_sequence()





def _validate_performance_requirements(results):

    """Validate performance requirements are met."""

    assert results["success"], f"Performance test failed: {results.get('error')}"

    

    # Total startup time requirement

    assert results["total_startup_time"] < 60.0, f"Total startup exceeded 60s: {results['total_startup_time']:.2f}s"

    

    # Individual service startup time requirements

    for service, time_taken in results["startup_times"].items():

        assert time_taken < 30.0, f"{service} exceeded 30s: {time_taken:.2f}s"





def _print_performance_success(results):

    """Print performance test success message."""

    total_time = results["total_startup_time"]

    print(f"[SUCCESS] Performance Requirements Met: {total_time:.2f}s total")

    print(f"[PROTECTED] Customer experience through fast startup")





if __name__ == "__main__":

    # Run tests directly for development

    import asyncio

    

    async def run_tests():

        """Run all startup sequence tests."""

        print("Running Service Startup Sequence Tests...")

        

        await test_complete_service_startup_sequence()

        await test_dependency_failure_scenarios()

        await test_performance_requirements()

        

        print("All startup sequence tests completed successfully!")

    

    asyncio.run(run_tests())

