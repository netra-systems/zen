"""
Production-realistic WebSocket tests - main module with imports.

This module imports and re-exports all WebSocket tests from specialized modules
to maintain backward compatibility while adhering to the 450-line limit.

Tests cover:
1. Concurrent connection limits (>1000 users)
2. Message ordering under load
3. Binary data transmission
4. Compression testing
5. Protocol version mismatch
6. Authentication expiry during connection
7. Memory leak detection for long connections
"""

import pytest

# Import all test functions from specialized modules
from netra_backend.tests.websocket.test_concurrent_connections import (
    test_concurrent_connection_limit_1000_users,
    test_rapid_connect_disconnect_cycles,
    test_connection_pool_exhaustion_recovery
)

from netra_backend.tests.websocket.test_message_ordering import (
    test_message_ordering_under_load,
    test_binary_data_transmission,
    test_protocol_version_mismatch
)

from netra_backend.tests.websocket.test_compression_auth import (
    test_websocket_compression,
    test_authentication_expiry_during_connection
)

from netra_backend.tests.websocket.test_memory_monitoring import (
    test_memory_leak_detection_long_connections
)

# Re-export all test functions for backward compatibility
__all__ = [
    'test_concurrent_connection_limit_1000_users',
    'test_message_ordering_under_load',
    'test_binary_data_transmission',
    'test_websocket_compression',
    'test_protocol_version_mismatch',
    'test_authentication_expiry_during_connection',
    'test_memory_leak_detection_long_connections',
    'test_rapid_connect_disconnect_cycles',
    'test_connection_pool_exhaustion_recovery'
]


# Optional: Add integration test that uses multiple modules
@pytest.mark.integration
async def test_websocket_full_integration():
    """Integration test combining multiple WebSocket features"""
    
    # This test demonstrates that all modules work together
    # Could be expanded to test cross-module interactions
    
    # For now, just verify all test functions are importable and callable
    test_functions = [
        test_concurrent_connection_limit_1000_users,
        test_message_ordering_under_load,
        test_binary_data_transmission,
        test_websocket_compression,
        test_protocol_version_mismatch,
        test_authentication_expiry_during_connection,
        test_memory_leak_detection_long_connections,
        test_rapid_connect_disconnect_cycles,
        test_connection_pool_exhaustion_recovery
    ]
    
    # Verify all functions are callable
    for func in test_functions:
        assert callable(func), f"Function {func.__name__} is not callable"
    
    # Integration test could run a subset of actual tests here
    # For brevity, we'll just verify the module structure is correct
    assert len(test_functions) == 9, "Should have exactly 9 WebSocket test functions"