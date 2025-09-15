"""
Test Framework Resilience Module for Issue #1278

Provides infrastructure resilience testing capabilities including:
- Pre-test connectivity validation
- Graceful degradation during infrastructure failures
- Enhanced timeout and retry patterns
- Fallback configuration management

Business Value: Platform/Internal - Test Infrastructure Resilience
Enables development to continue during staging infrastructure outages.
"""

from .test_connectivity_validator import (
    TestConnectivityValidator,
    ConnectivityStatus,
    ServiceType,
    ConnectivityResult,
    InfrastructureHealth,
    validate_infrastructure_health,
    validate_critical_services,
    should_skip_test_due_to_infrastructure,
    get_resilient_test_configuration
)

from .enhanced_test_runner import (
    ResilientTestRunner,
    TestExecutionMode,
    TestResult,
    run_tests_with_resilience
)

__all__ = [
    # Core Classes
    "TestConnectivityValidator",
    "ResilientTestRunner",

    # Enums
    "ConnectivityStatus",
    "ServiceType",
    "TestExecutionMode",

    # Data Classes
    "ConnectivityResult",
    "InfrastructureHealth",
    "TestResult",

    # Convenience Functions
    "validate_infrastructure_health",
    "validate_critical_services",
    "should_skip_test_due_to_infrastructure",
    "get_resilient_test_configuration",
    "run_tests_with_resilience"
]