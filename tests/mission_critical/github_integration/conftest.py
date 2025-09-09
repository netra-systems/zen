"""
Conftest for GitHub Integration Mission Critical Tests

Registers shared fixtures and configuration for GitHub mission critical tests.
"""

import pytest
import sys
import os

# Add test_framework to Python path for fixture imports  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'test_framework'))

# Import GitHub test fixtures
from test_framework.fixtures.github_integration_fixtures import (
    github_test_config,
    github_error_context_factory,
    mock_github_issue_factory,
    mock_github_client,
    github_api_responses,
    github_webhook_payload,
    github_error_scenarios,
    github_test_cleanup
)

# Import mission critical test helpers
from tests.mission_critical.helpers.test_helpers import MissionCriticalTestHelper

# GitHub-specific pytest configuration
pytest_plugins = [
    "test_framework.fixtures.github_integration_fixtures",
    "tests.mission_critical.helpers"
]