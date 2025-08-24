"""
Unified test fixtures package.
Organizes test fixtures by domain for easy reuse across services.
"""

from test_framework.fixtures.auth_fixtures import *
from test_framework.fixtures.database_fixtures import *  
from test_framework.fixtures.service_fixtures import *
from test_framework.fixtures.health import *
from test_framework.fixtures.real_services import *

__all__ = [
    # Re-export all fixtures from submodules
]