"""
Service Independence Validation Test Suite

BVJ: Enterprise | SOC2 Compliance | Microservice Independence | Critical for scalability
SPEC: SPEC/independent_services.xml
BUSINESS IMPACT: SOC2 compliance and enterprise scalability requirements

This test validates that all microservices (Main Backend, Auth Service, Frontend) 
maintain complete independence and can operate without direct code dependencies.

Requirements:
1. Verify Auth service has ZERO imports from main app
2. Test that Backend communicates with Auth only via HTTP/gRPC
3. Verify Frontend communicates only via APIs  
4. Test services can start independently
5. Test graceful handling when other services fail

Critical for: Enterprise compliance, independent scaling, deployment flexibility

REFACTORED: This module now imports from the new service_independence package
for better modularity and maintainability.
"""

import sys
from pathlib import Path

# Add project root to path for imports

# Import everything from the new modular structure
from tests.e2e.helpers.core.service_independence import *
from tests.e2e.helpers.core.service_independence.pytest_interface import (
    test_service_independence,
    test_zero_import_violations,
    test_api_only_communication,
    test_independent_startup_capability,
    test_graceful_failure_handling,
    run_direct_tests
)

# Backward compatibility alias
ServiceIndependenceHelper = ServiceIndependenceValidator

# For backward compatibility and direct execution
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_direct_tests())
