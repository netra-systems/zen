"""
UVS (User-specific Validation System) Integration Tests

This package contains comprehensive integration tests for the User-specific Validation System,
focusing on user isolation, validation flows, and factory-based patterns.

Business Value Justification:
- Ensures complete user isolation preventing data leakage
- Validates factory patterns that enable multi-user concurrent operations  
- Tests context hierarchy management for complex agent workflows
- Verifies proper resource management and cleanup patterns

Test Categories:
- UserExecutionContext creation and validation
- ExecutionEngineFactory lifecycle management
- User isolation between concurrent requests
- Factory-based resource management
- Context hierarchy and child context creation
"""