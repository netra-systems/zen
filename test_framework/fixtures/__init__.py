"""
Unified test fixtures package.
Organizes test fixtures by domain for easy reuse across services.
"""

from test_framework.fixtures.auth_fixtures import *
from test_framework.fixtures.database_fixtures import *  
from test_framework.fixtures.service_fixtures import *
from test_framework.fixtures.health import *
from test_framework.fixtures.real_services import *

# Import additional classes and functions
from test_framework.fixtures.service_fixtures import _ConfigManagerHelper as ConfigManagerHelper, create_test_app

# Import create_test_client from backend route helpers
from netra_backend.tests.helpers.route_test_helpers import create_test_client

# Add stub for missing fixtures
def create_test_deep_state():
    """Stub for create_test_deep_state fixture."""
    return {}

def create_test_thread_message():
    """Stub for create_test_thread_message fixture."""
    return {"id": "test_thread", "content": "test message"}

__all__ = [
    # Re-export all fixtures from submodules
    "ConfigManagerHelper",
    "create_test_app",
    "create_test_client",
    "create_test_deep_state",
    "create_test_thread_message",
]