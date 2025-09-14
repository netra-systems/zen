"""
WebSocket Test Utility - Compatibility Layer for SSOT Integration Tests

This module provides a compatibility layer for SSOT integration tests that expect
a WebSocketTestUtility class. It re-exports functionality from existing modules.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Re-exports from existing websocket test modules
- DO NOT add new functionality here

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

# Re-export from existing websocket test modules
from test_framework.ssot.websocket_bridge_test_helper import (
    WebSocketBridgeTestHelper,
)
from test_framework.ssot.websocket_auth_helper import (
    WebSocketAuthHelper,
)

# Create WebSocketTestUtility as an alias that combines functionality
class WebSocketTestUtility(WebSocketBridgeTestHelper):
    """
    Unified WebSocket test utility combining functionality from multiple helpers.

    This class provides a unified interface for WebSocket testing operations
    by inheriting from WebSocketBridgeTestHelper and adding auth capabilities.
    """

    def __init__(self, *args, **kwargs):
        """Initialize WebSocket test utility."""
        super().__init__(*args, **kwargs)
        self.auth_helper = WebSocketAuthHelper()

    def setup_auth_for_testing(self, *args, **kwargs):
        """Setup authentication for testing."""
        return self.auth_helper.setup_auth_for_testing(*args, **kwargs)

    async def create_authenticated_connection(self, *args, **kwargs):
        """Create authenticated WebSocket connection."""
        return await self.auth_helper.create_authenticated_connection(*args, **kwargs)

    async def get_staging_websocket_url(self):
        """
        REMEDIATION FIX: Get staging WebSocket URL - missing method for Issue #861.

        This method was missing and causing integration test failures.
        It provides the staging WebSocket URL for E2E testing.

        Returns:
            str: Staging WebSocket URL
        """
        # Use staging config to get proper URL
        from tests.e2e.staging_config import StagingTestConfig
        staging_config = StagingTestConfig()
        return staging_config.urls.websocket_url

# Create alias for compatibility with existing test files
WebSocketTestHelper = WebSocketTestUtility

__all__ = [
    "WebSocketTestUtility",
    "WebSocketTestHelper",  # Compatibility alias
    "WebSocketBridgeTestHelper",
    "WebSocketAuthHelper",
]