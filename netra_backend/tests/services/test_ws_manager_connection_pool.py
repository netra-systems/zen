"""
WebSocket Manager connection pooling and cleanup tests
Modular test suite split into focused test modules for maintainability
"""

# Import all test classes from modular test files to maintain backward compatibility

from netra_backend.app.websocket_core.manager import WebSocketManager
from pathlib import Path
import sys

from netra_backend.tests.services.test_ws_connection_basic import (

    TestWebSocketManagerConnectionPooling,

)
# Removed WebSocket mock import - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

    MockConnectionPool,

    MockWebSocket,

    WebSocketTestHelpers,

)
from netra_backend.tests.services.test_ws_connection_performance import (

    TestWebSocketManagerPerformanceAndScaling,

)

# Re-export all classes for backward compatibility

__all__ = [

    'MockWebSocket',

    'MockConnectionPool', 

    'WebSocketTestHelpers',

    'TestWebSocketManagerConnectionPooling',

    'TestWebSocketManagerPerformanceAndScaling'

]

# Note: This file now serves as a compatibility layer for the modular test suite.
# The original 650-line test file has been refactored into three focused modules:
# - test_ws_connection_mocks.py: Mock classes and test utilities (~295 lines)
# - test_ws_connection_basic.py: Basic connection and pooling tests (~298 lines)  
# - test_ws_connection_performance.py: Performance and scaling tests (~298 lines)
# 
# All functions have been refactored to ≤8 lines using helper methods while
# preserving complete test functionality and coverage.