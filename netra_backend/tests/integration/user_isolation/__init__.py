"""
User Isolation Integration Tests

This package contains comprehensive integration tests for User Isolation Patterns
in the Netra platform, focusing on multi-tenant security and data isolation.

Test Categories:
- Data Access Factory Isolation (test_data_access_factory_isolation.py)
- User Execution Context Lifecycle (test_user_execution_context_lifecycle.py)  
- Cross-User Data Isolation (test_cross_user_data_isolation.py)
- Concurrent User Operations (test_concurrent_user_operations.py)

Business Value:
These tests are critical for Enterprise revenue as they ensure complete data
isolation between users, preventing security breaches that could lose major accounts.

Usage:
    # Run all user isolation tests
    python tests/unified_test_runner.py --category integration --pattern "*user_isolation*"
    
    # Run with real services
    python tests/unified_test_runner.py --real-services --pattern "*user_isolation*"
    
    # Run specific test file
    python tests/unified_test_runner.py --test-file netra_backend/tests/integration/user_isolation/test_data_access_factory_isolation.py
"""