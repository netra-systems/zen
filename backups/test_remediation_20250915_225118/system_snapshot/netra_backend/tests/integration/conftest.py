"""Integration tests conftest - Lightweight services for non-Docker testing.

This conftest provides lightweight service fixtures for integration tests
that don't require Docker or external services. It enables fast integration
testing that validates business logic and component interactions.
"""

import pytest

# Import lightweight service fixtures directly
from test_framework.fixtures.lightweight_services import (
    lightweight_postgres_connection,
    lightweight_test_database,
    lightweight_services_fixture,
    lightweight_auth_context,
    integration_services
)

# Re-export fixtures to make them available to integration tests
__all__ = [
    'lightweight_postgres_connection',
    'lightweight_test_database', 
    'lightweight_services_fixture',
    'lightweight_auth_context',
    'integration_services'
]