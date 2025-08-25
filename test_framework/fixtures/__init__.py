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

__all__ = [
    # Re-export all fixtures from submodules
    "ConfigManagerHelper",
    "create_test_app",
]