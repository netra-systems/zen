"""
Conftest for GitHub Integration Integration Tests

Registers shared fixtures and configuration for GitHub integration tests.
"""

import pytest
import sys
import os

# Add test_framework to Python path for fixture imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

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

# Import base integration test configuration
from test_framework.ssot.base_integration_test import BaseIntegrationTest

# GitHub-specific pytest configuration
pytest_plugins = [
    "test_framework.fixtures.github_integration_fixtures"
]