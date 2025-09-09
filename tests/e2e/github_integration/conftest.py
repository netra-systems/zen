"""
Conftest for GitHub Integration E2E Tests

Registers shared fixtures and configuration for GitHub e2e tests.
CRITICAL: All e2e tests MUST use authentication.
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

# Import E2E authentication fixtures
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig

# Import staging configuration
from tests.e2e.staging_config import StagingTestConfig

# GitHub-specific pytest configuration
# NOTE: pytest_plugins moved to root conftest.py per pytest requirement

@pytest.fixture(scope="session")
def e2e_auth_config():
    """E2E authentication configuration for GitHub tests"""
    return E2EAuthConfig.for_staging()

@pytest.fixture(scope="session") 
def e2e_auth_helper(e2e_auth_config):
    """E2E authentication helper for GitHub tests"""
    return E2EAuthHelper(e2e_auth_config)