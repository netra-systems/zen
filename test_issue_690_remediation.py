#!/usr/bin/env python3
"""
Test Issue #690 Remediation Effectiveness

Validates that the environment-aware health configuration successfully resolves
staging backend health validation failures by allowing graceful degradation
of LLM services and other optional components.
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netra_backend.app.core.health.environment_health_config import (
    get_environment_health_config,
    ServiceCriticality,
    HealthFailureMode,
    is_service_enabled,
    get_service_timeout
)

from netra_backend.app.llm.staging_resilient_factory import (
    get_resilient_llm_factory,
    create_resilient_llm_manager,
    LLMFactoryMode
)


async def test_staging_environment_configuration():
    """Test that staging environment has correct service criticality configuration."""
    print("Testing staging environment health configuration...")

    # Get staging configuration
    staging_config = get_environment_health_config("staging")

    # Test LLM service configuration in staging
    llm_config = staging_config.get_service_config("llm", "staging")
    assert llm_config is not None, "LLM service configuration should exist"
    assert llm_config.criticality == ServiceCriticality.OPTIONAL, f"LLM should be optional in staging, got {llm_config.criticality}"
    assert llm_config.failure_mode == HealthFailureMode.GRACEFUL_DEGRADE, f"LLM should gracefully degrade in staging, got {llm_config.failure_mode}"

    print("✅ LLM service correctly configured as optional with graceful degradation in staging")

    # Test staging allows partial startup
    assert staging_config.allow_partial_startup == True, "Staging should allow partial startup"
    print("✅ Staging environment allows partial startup")

    # Test timeout configuration
    llm_timeout = get_service_timeout("llm", "staging")
    assert llm_timeout <= 15.0, f"LLM timeout should be reduced in staging, got {llm_timeout}s"
    print(f"✅ LLM timeout appropriately reduced to {llm_timeout}s in staging")

    return True


async def test_resilient_llm_factory():
    """Test that the resilient LLM factory handles staging constraints properly."""
    print("\n🧪 Testing resilient LLM factory for staging...")

    # Get staging factory
    factory = get_resilient_llm_factory("staging")
    assert factory.environment == "staging", "Factory should be configured for staging"

    # Test factory health check
    health = await factory.health_check()
    print(f"📊 Factory health status: {health}")

    # Factory should be available (even if degraded)
    assert health["status"] in ["healthy", "degraded"], f"Factory should be available, got {health['status']}"
    print("✅ Resilient LLM factory operational in staging")

    # Test creating a manager with timeout protection
    try:
        manager = await create_resilient_llm_manager(None, "staging")
        if manager is None:
            print("ℹ️ LLM manager returned None (graceful unavailability) - this is expected behavior in staging")
        else:
            print("✅ LLM manager created successfully with resilience protection")
    except Exception as e:
        print(f"⚠️ LLM manager creation failed (expected in staging): {e}")

    return True


async def test_failure_tolerance():
    """Test that the health configuration properly handles service failures."""
    print("\n🧪 Testing failure tolerance in staging environment...")

    staging_config = get_environment_health_config("staging")

    # Simulate failed services
    failed_services = {
        "llm": "LLM service unavailable due to Cloud Run constraints",
        "clickhouse": "ClickHouse not available in staging infrastructure"
    }

    # Test failure determination
    should_fail, reason = staging_config.should_fail_health_check(failed_services, "staging")

    print(f"📊 Failure analysis: should_fail={should_fail}, reason={reason}")

    # In staging with optional services failing, should not fail health check
    assert not should_fail, f"Health check should not fail for optional service failures in staging: {reason}"
    print("✅ Health check correctly tolerates optional service failures in staging")

    # Test with critical service failure
    critical_failed_services = {
        "postgres": "Database connection failed"
    }

    should_fail_critical, reason_critical = staging_config.should_fail_health_check(critical_failed_services, "staging")
    assert should_fail_critical, f"Health check should fail for critical service failures: {reason_critical}"
    print("✅ Health check correctly fails for critical service failures")

    return True


async def test_production_comparison():
    """Test that production environment has stricter requirements than staging."""
    print("\n🧪 Testing production vs staging configuration differences...")

    staging_config = get_environment_health_config("staging")
    production_config = get_environment_health_config("production")

    # LLM should be more critical in production
    staging_llm = staging_config.get_service_config("llm", "staging")
    production_llm = production_config.get_service_config("llm", "production")

    assert staging_llm.criticality == ServiceCriticality.OPTIONAL, "LLM should be optional in staging"
    assert production_llm.criticality in [ServiceCriticality.IMPORTANT, ServiceCriticality.CRITICAL], "LLM should be important/critical in production"

    # Production should not allow partial startup
    assert not production_config.allow_partial_startup, "Production should not allow partial startup"
    assert staging_config.allow_partial_startup, "Staging should allow partial startup"

    print("✅ Production environment has appropriately stricter requirements than staging")

    return True


async def main():
    """Run all remediation validation tests."""
    print("🚀 Issue #690 Remediation Validation Test Suite")
    print("=" * 60)

    tests = [
        test_staging_environment_configuration,
        test_resilient_llm_factory,
        test_failure_tolerance,
        test_production_comparison
    ]

    results = []

    for test in tests:
        try:
            result = await test()
            results.append(("✅", test.__name__, "PASSED"))
        except Exception as e:
            results.append(("❌", test.__name__, f"FAILED: {e}"))
            print(f"❌ {test.__name__} failed: {e}")

    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)

    for status, test_name, result in results:
        print(f"{status} {test_name}: {result}")

    passed = sum(1 for r in results if r[0] == "✅")
    total = len(results)

    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 Issue #690 remediation validation SUCCESSFUL!")
        print("✅ Staging environment health validation should now work correctly")
        return 0
    else:
        print("💥 Issue #690 remediation validation FAILED!")
        print("❌ Additional fixes may be required")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)