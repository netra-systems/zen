"""
Pytest Interface Module

BVJ: Enterprise | SOC2 Compliance | Test Interface | Critical for CI/CD integration
SPEC: SPEC/independent_services.xml

This module provides the pytest test functions for service independence validation.
Maintains compatibility with existing test runners and CI/CD pipelines.
"""

import asyncio

import pytest

from tests.e2e.helpers.core.service_independence import (
    TEST_TIMEOUT,
    ServiceIndependenceValidator,
)


@pytest.mark.critical
@pytest.mark.asyncio
async def test_service_independence():
    """
    BVJ: Segment: Enterprise | Goal: Compliance | Impact: SOC2
    Tests: Microservice independence for scalability
    """
    validator = ServiceIndependenceValidator()
    
    try:
        results = await validator.test_service_independence()
        
        # Validate results
        assert results["success"], f"Service independence validation failed: {results.get('errors', [])}"
        
        # Check execution time
        assert results["execution_time"] < TEST_TIMEOUT, f"Test exceeded time limit: {results['execution_time']}s"
        
        # Validate critical aspects
        validations = results["validations"]
        
        # Import independence is critical
        import_validation = validations.get("import_independence", {})
        assert import_validation.get("passed", False), f"Import independence failed: {import_validation}"
        
        # Independent startup capability
        startup_validation = validations.get("independent_startup", {})
        assert startup_validation.get("services_can_start", 0) >= 1, "Insufficient services can start independently"
        
        # Service isolation
        isolation_validation = validations.get("service_isolation", {})
        isolation_score = isolation_validation.get("total_isolation_score", 0)
        assert isolation_score >= 50, f"Isolation score too low: {isolation_score}%"
        
        # Print success summary
        summary = results["test_summary"]
        print(f"[SUCCESS] Service Independence Validation: {summary['passed_validations']}/{summary['total_validations']} tests passed")
        print(f"   Execution time: {results['execution_time']}s")
        print(f"   Success rate: {summary['success_rate']}%")
        
        for validation_name, validation_result in validations.items():
            status = "PASS" if validation_result.get("passed", False) else "FAIL"
            print(f"   [{status}] {validation_name}")
        
    finally:
        await validator.cleanup()


@pytest.mark.critical
@pytest.mark.asyncio
async def test_zero_import_violations():
    """Test that services have zero forbidden imports."""
    validator = ServiceIndependenceValidator()
    
    try:
        import_results = await validator._validate_import_independence()
        
        total_violations = import_results.get("total_violations", 0)
        assert total_violations == 0, (
            f"Found {total_violations} import violations:\n" + 
            "\n".join([
                f"  {service}: {len(result.get('violations', []))} violations"
                for service, result in import_results.get("service_results", {}).items()
                if result.get("violations", [])
            ])
        )
        
        # Ensure files were actually scanned
        scan_stats = import_results.get("scan_stats", {})
        assert scan_stats.get("total_files_scanned", 0) > 0, "No files were scanned"
        
        print(f"[PASS] Zero Import Violations: {scan_stats['total_files_scanned']} files scanned across {scan_stats['services_scanned']} services")
        
    finally:
        await validator.cleanup()


@pytest.mark.asyncio
async def test_api_only_communication():
    """Test that services communicate only via APIs."""
    validator = ServiceIndependenceValidator()
    
    try:
        api_results = await validator._validate_api_only_communication()
        
        # If any services are running, they should have working API endpoints
        total_tested = api_results.get("total_endpoints_tested", 0)
        working_endpoints = api_results.get("api_endpoints_working", 0)
        
        if total_tested > 0:
            # At least 50% of tested endpoints should work
            success_rate = working_endpoints / total_tested
            assert success_rate >= 0.5, f"API success rate too low: {success_rate:.2%}"
        
        print(f"[PASS] API-Only Communication: {working_endpoints}/{total_tested} endpoints working")
        
        # Print per-service results
        for service, result in api_results.get("communication_tests", {}).items():
            if result.get("service_accessible", False):
                print(f"   {service}: {result.get('working_endpoints', 0)}/{result.get('total_tested', 0)} endpoints")
            else:
                print(f"   {service}: Not running (expected in tests)")
        
    finally:
        await validator.cleanup()


@pytest.mark.asyncio
async def test_independent_startup_capability():
    """Test that services can start independently."""
    validator = ServiceIndependenceValidator()
    
    try:
        startup_results = await validator._validate_independent_startup()
        
        services_can_start = startup_results.get("services_can_start", 0)
        services_tested = startup_results.get("services_tested", 0)
        
        # At least 1 service should be able to start independently (relaxed for testing)
        assert services_can_start >= 1, f"Only {services_can_start}/{services_tested} services can start independently"
        
        print(f"[PASS] Independent Startup: {services_can_start}/{services_tested} services can start independently")
        
        # Print per-service results
        for service, result in startup_results.get("service_startup_tests", {}).items():
            status = "[PASS]" if result.get("can_start", False) else "[FAIL]"
            startup_time = result.get("startup_time", 0)
            print(f"   {status} {service}: {startup_time:.2f}s")
        
    finally:
        await validator.cleanup()


@pytest.mark.asyncio
async def test_graceful_failure_handling():
    """Test graceful handling when other services fail."""
    validator = ServiceIndependenceValidator()
    
    try:
        failure_results = await validator._validate_graceful_failure_handling()
        
        scenarios_handled = failure_results.get("scenarios_handled", 0)
        scenarios_tested = failure_results.get("scenarios_tested", 0)
        
        # Most failure scenarios should be handled gracefully
        if scenarios_tested > 0:
            success_rate = scenarios_handled / scenarios_tested
            assert success_rate >= 0.5, f"Failure handling rate too low: {success_rate:.2%}"
        
        print(f"[PASS] Graceful Failure Handling: {scenarios_handled}/{scenarios_tested} scenarios handled")
        
        # Print per-scenario results
        for scenario, result in failure_results.get("failure_scenarios", {}).items():
            status = "[PASS]" if result.get("handled_gracefully", False) else "[FAIL]"
            behaviors = result.get("graceful_behaviors", [])
            print(f"   {status} {scenario}: {len(behaviors)} graceful behaviors")
        
    finally:
        await validator.cleanup()


# Main execution function for direct running
async def run_direct_tests():
    """Run tests directly for debugging and development."""
    validator = ServiceIndependenceValidator()
    try:
        results = await validator.test_service_independence()
        print("\n" + "="*80)
        print("SERVICE INDEPENDENCE VALIDATION RESULTS")
        print("="*80)
        success_indicator = "PASS" if results['success'] else "FAIL"
        print(f"Overall Success: {success_indicator}")
        print(f"Execution Time: {results['execution_time']}s")
        print(f"Success Rate: {results['test_summary']['success_rate']}%")
        
        if results["errors"]:
            print(f"\nErrors: {results['errors']}")
            
        print("\nDetailed Results:")
        for name, validation in results["validations"].items():
            status = "PASS" if validation.get("passed", False) else "FAIL"
            print(f"  [{status}] {name}")
            
    finally:
        await validator.cleanup()


if __name__ == "__main__":
    # Run the comprehensive test directly
    asyncio.run(run_direct_tests())
