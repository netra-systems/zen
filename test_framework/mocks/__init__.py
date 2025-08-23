"""
Unified mock objects package.
Consolidates mock implementations from across the project.
"""

from test_framework.mocks.websocket_mocks import *
from test_framework.mocks.service_mocks import *
from test_framework.mocks.database_mocks import *

__all__ = [
    # Re-export all mocks from submodules
]