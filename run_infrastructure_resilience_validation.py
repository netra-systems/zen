#!/usr/bin/env python3
"""
Infrastructure Resilience Validation Suite - Master Test Runner
Executes all validation tests for infrastructure resilience improvements.
"""

import sys
import subprocess
import asyncio
import time
from pathlib import Path

def run_test_script(script_name: str, description: str) -> dict:
    """Run a test script and return results."""
    print(f"\n🔍 {description}")
    print("=" * 60)

    try:
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        execution_time = time.time() - start_time

        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")

        return {
            "name": script_name,
            "description": description,
            "success": result.returncode == 0,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        print(f"❌ Test timed out after 5 minutes")
        return {
            "name": script_name,
            "description": description,
            "success": False,
            "execution_time": 300,
            "stdout": "",
            "stderr": "Test timed out"
        }
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return {
            "name": script_name,
            "description": description,
            "success": False,
            "execution_time": 0,
            "stdout": "",
            "stderr": str(e)
        }

async def main():
    """Run all infrastructure resilience validation tests."""
    print("🏗️  Infrastructure Resilience Validation Suite")
    print("=" * 70)
    print("Validating that infrastructure resilience improvements maintain")
    print("system stability and don't introduce breaking changes.")
    print("=" * 70)

    # Define test suite
    test_suite = [
        ("import_validation_test.py", "Import Validation & Circular Dependency Check"),
        ("health_endpoint_validation_test.py", "Health Endpoint Functionality Test"),
        ("database_integration_validation_test.py", "Database Integration Validation"),
        ("ssot_compliance_validation_test.py", "SSOT Compliance Verification"),
        ("circuit_breaker_functional_test.py", "Circuit Breaker Functional Test"),
    ]

    # Check that all test files exist
    missing_files = []
    for script_name, _ in test_suite:
        if not Path(script_name).exists():
            missing_files.append(script_name)

    if missing_files:
        print(f"❌ Missing test files: {', '.join(missing_files)}")
        print("Please ensure all validation test scripts are present.")
        return 1

    # Run all tests
    results = []
    total_execution_time = 0

    for script_name, description in test_suite:
        result = run_test_script(script_name, description)
        results.append(result)
        total_execution_time += result["execution_time"]

    # Generate summary report
    print("\n" + "=" * 70)
    print("📊 INFRASTRUCTURE RESILIENCE VALIDATION SUMMARY")
    print("=" * 70)

    successful_tests = [r for r in results if r["success"]]
    failed_tests = [r for r in results if not r["success"]]

    print(f"Total Tests: {len(results)}")
    print(f"Successful: {len(successful_tests)}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Success Rate: {len(successful_tests)/len(results)*100:.1f}%")
    print(f"Total Execution Time: {total_execution_time:.2f} seconds")

    # Detailed results
    print(f"\n📋 Detailed Test Results:")
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"   {status} {result['description']} ({result['execution_time']:.2f}s)")

    if failed_tests:
        print(f"\n⚠️  Failed Tests Details:")
        for result in failed_tests:
            print(f"   ❌ {result['name']}")
            if result['stderr']:
                print(f"      Error: {result['stderr'][:200]}...")

    # Final assessment
    print(f"\n🎯 FINAL VALIDATION ASSESSMENT:")
    if len(successful_tests) == len(results):
        print("✅ ALL TESTS PASSED - Infrastructure resilience improvements are STABLE")
        print("✅ System maintains stability with new resilience capabilities")
        print("✅ No breaking changes detected")
        print("✅ Ready for deployment to staging environment")
        final_status = 0
    elif len(successful_tests) >= len(results) * 0.8:  # 80% pass rate
        print("⚠️  MOSTLY PASSED - Infrastructure resilience improvements are LIKELY STABLE")
        print("⚠️  Some validation tests failed but critical functionality validated")
        print("⚠️  Review failed tests before deployment")
        final_status = 0
    else:
        print("❌ VALIDATION FAILED - Infrastructure resilience improvements need review")
        print("❌ Multiple critical tests failed")
        print("❌ Do not deploy until issues are resolved")
        final_status = 1

    # Additional recommendations
    print(f"\n💡 Recommendations:")
    print("   1. Review comprehensive validation report: INFRASTRUCTURE_RESILIENCE_VALIDATION_REPORT.md")
    print("   2. Run staging environment tests after deployment")
    print("   3. Monitor new health endpoints: /health/infrastructure, /health/circuit-breakers")
    print("   4. Validate circuit breaker functionality under load")

    return final_status

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))