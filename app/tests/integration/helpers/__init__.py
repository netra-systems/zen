"""
Integration test helpers module
BVJ: Supporting infrastructure for critical integration tests
"""

from .critical_integration_helpers import (
    RevenueTestHelpers,
    AuthenticationTestHelpers, 
    WebSocketTestHelpers,
    AgentTestHelpers,
    DatabaseTestHelpers,
    MonitoringTestHelpers,
    MiscTestHelpers
)

# Check if the new user flow helpers exist before importing
try:
    from ..test_helpers.user_flow_base import UserFlowTestBase, UserFlowAssertions
    USER_FLOW_HELPERS_AVAILABLE = True
except ImportError:
    USER_FLOW_HELPERS_AVAILABLE = False

__all__ = [
    'RevenueTestHelpers',
    'AuthenticationTestHelpers',
    'WebSocketTestHelpers', 
    'AgentTestHelpers',
    'DatabaseTestHelpers',
    'MonitoringTestHelpers',
    'MiscTestHelpers'
]

if USER_FLOW_HELPERS_AVAILABLE:
    __all__.extend(['UserFlowTestBase', 'UserFlowAssertions'])