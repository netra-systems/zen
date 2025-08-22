"""
Integration test helpers module
BVJ: Supporting infrastructure for critical integration tests
"""

# Import helpers that exist
try:
    from netra_backend.tests.integration.helpers.critical_integration_helpers import (
        AgentTestHelpers,
        AuthenticationTestHelpers,
        DatabaseTestHelpers,
        MiscTestHelpers,
        MonitoringTestHelpers,
        RevenueTestHelpers,
        WebSocketTestHelpers,
    )
    CRITICAL_HELPERS_AVAILABLE = True
except ImportError:
    CRITICAL_HELPERS_AVAILABLE = False

# Check if the new user flow helpers exist before importing
try:
    from netra_backend.tests.integration.test_helpers.user_flow_base import UserFlowAssertions, UserFlowTestBase
    USER_FLOW_HELPERS_AVAILABLE = True
except ImportError:
    USER_FLOW_HELPERS_AVAILABLE = False

__all__ = []

if CRITICAL_HELPERS_AVAILABLE:
    __all__.extend([
        'RevenueTestHelpers',
        'AuthenticationTestHelpers',
        'WebSocketTestHelpers', 
        'AgentTestHelpers',
        'DatabaseTestHelpers',
        'MonitoringTestHelpers',
        'MiscTestHelpers'
    ])

if USER_FLOW_HELPERS_AVAILABLE:
    __all__.extend(['UserFlowTestBase', 'UserFlowAssertions'])