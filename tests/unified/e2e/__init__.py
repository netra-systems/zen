"""E2E Test Package for Netra Apex

End-to-end tests for critical system functionality with real service interactions.
Focus on production-like scenarios and integration validation.

Business Value: Ensures production reliability and prevents customer-facing issues.
"""

# Simplified imports to prevent conflicts
try:
    from tests.unified.unified_e2e_harness import UnifiedE2ETestHarness, create_e2e_harness, quick_e2e_test
    from tests.unified.service_orchestrator import E2EServiceOrchestrator
    from tests.unified.user_journey_executor import UserJourneyExecutor, TestUser
    
    __all__ = [
        "UnifiedE2ETestHarness",
        "E2EServiceOrchestrator", 
        "UserJourneyExecutor",
        "TestUser",
        "create_e2e_harness",
        "quick_e2e_test"
    ]
except ImportError:
    # Allow individual test files to run without full harness
    __all__ = []
