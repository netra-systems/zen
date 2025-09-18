"""
Authentication and User Management Integration Tests

This module contains comprehensive integration tests for core authentication
and user management functionality using real services (PostgreSQL, Redis).

Test Coverage:
- User registration and validation (4 tests)
- Authentication flows (JWT, OAuth) (4 tests)
- Session management (4 tests) 
- Authorization and permissions (4 tests)
- User profile and data operations (4 tests)

All tests follow CLAUDE.md requirements:
 PASS:  ZERO MOCKS - Uses real PostgreSQL and Redis
 PASS:  SSOT patterns from test_framework
 PASS:  Business Value Justification (BVJ) for each test
 PASS:  BaseIntegrationTest inheritance
 PASS:  @pytest.mark.integration and @pytest.mark.real_services markers
"""