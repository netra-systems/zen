"""
Shared pytest configuration and fixtures for services tests.

MODULE PURPOSE:
Provides centralized pytest configuration and fixture imports for all service tests.
Makes fixtures from fixture modules available to all test files in the services directory.

COMPLIANCE:
- Module ≤300 lines
- Single source of truth for test configuration
"""

# Import all fixtures to make them available to pytest
from netra_backend.tests.services.test_agent_service_fixtures import (
    agent_service,
    mock_message_handler,
    mock_supervisor,
    mock_thread_service,
)
