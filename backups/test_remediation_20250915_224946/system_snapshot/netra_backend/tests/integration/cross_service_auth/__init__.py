"""
Cross-Service Authentication & Authorization Integration Tests

This package contains comprehensive integration tests for cross-service authentication
and authorization flows in the Netra platform.

Test Modules:
- test_cross_service_auth_flow_integration.py: Basic cross-service auth flows
- test_jwt_token_lifecycle_integration.py: Complete JWT token lifecycle management
- test_auth_circuit_breaker_integration.py: Circuit breaker resilience patterns
- test_multi_service_auth_consistency_integration.py: Multi-service consistency validation

Business Value:
These tests validate the authentication foundation that enables all user operations
across the platform. Auth failures block user access and business value delivery.

Usage:
Run with unified test runner:
  python tests/unified_test_runner.py --category integration --test-pattern cross_service_auth
  python tests/unified_test_runner.py --real-services --test-file netra_backend/tests/integration/cross_service_auth/

Individual test files:
  pytest netra_backend/tests/integration/cross_service_auth/test_cross_service_auth_flow_integration.py
"""