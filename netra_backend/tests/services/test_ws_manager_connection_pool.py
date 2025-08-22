"""
WebSocket Manager connection pooling and cleanup tests
Modular test suite split into focused test modules for maintainability
"""

# Import all test classes from modular test files to maintain backward compatibility

# Add project root to path

# Add project root to path

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from netra_backend.tests.test_utils import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

from netra_backend.tests.test_ws_connection_basic import (

    TestWebSocketManagerConnectionPooling,

)
from netra_backend.tests.test_ws_connection_mocks import (

    MockConnectionPool,
    # Add project root to path

    MockWebSocket,

    WebSocketTestHelpers,

)
from netra_backend.tests.test_ws_connection_performance import (

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