from shared.isolated_environment import get_env
"""Isolated conftest for mission-critical WebSocket tests.

This prevents global conftest.py from loading real services for isolated tests.
"""

import pytest
import os

# Force disable real services for this test directory
env.set('SKIP_REAL_SERVICES', 'true', "test")
env.set('USE_REAL_SERVICES', 'false', "test")
env.set('RUN_E2E_TESTS', 'false', "test")

# Override service availability checks
env = get_env()
@pytest.fixture(autouse=True)
def disable_service_checks():
    """Disable all service availability checks for isolated tests."""
    with pytest.MonkeyPatch().context() as m:
        m.setenv("SKIP_REAL_SERVICES", "true")
        m.setenv("USE_REAL_SERVICES", "false")
        m.setenv("RUN_E2E_TESTS", "false")
        yield
