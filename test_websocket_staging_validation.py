#!/usr/bin/env python3
"""
Test WebSocket Staging Validation (Issue #680)

Quick test to validate that the WebSocket staging fallback is working correctly.
"""

import asyncio
import os
from test_framework.websocket_helpers import WebSocketTestHelpers
from shared.isolated_environment import get_env

async def test_staging_websocket_fallback():
    """Test that staging WebSocket fallback works when Docker is unavailable."""

    # Set up staging environment
    os.environ["USE_STAGING_SERVICES"] = "true"
    os.environ["STAGING_WEBSOCKET_URL"] = "wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws"
    os.environ["TEST_WEBSOCKET_URL"] = "wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws"

    print("🧪 Testing WebSocket staging fallback (Issue #680)")
    print(f"   📡 Staging WebSocket URL: {os.environ['STAGING_WEBSOCKET_URL']}")
    print(f"   🔧 Use Staging Services: {os.environ['USE_STAGING_SERVICES']}")

    # Check Docker availability
    from test_framework.websocket_helpers import is_docker_available_for_websocket
    docker_available = is_docker_available_for_websocket()
    print(f"   🐳 Docker Available: {docker_available}")

    try:
        # This should trigger staging fallback since Docker is not available
        connection = await WebSocketTestHelpers.create_test_websocket_connection(
            url="ws://localhost:8000/ws/test",  # This will fail and trigger staging fallback
            timeout=10.0,
            max_retries=2
        )

        print(f"✅ WebSocket connection successful: {type(connection)}")

        # Test basic operations
        await connection.ping()
        print("✅ WebSocket ping successful")

        # Clean up
        await connection.close()
        print("✅ WebSocket connection closed successfully")

        return True

    except Exception as e:
        print(f"❌ WebSocket staging fallback test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_staging_websocket_fallback())
    if result:
        print("\n🎉 Issue #680 WebSocket staging fallback validation: SUCCESS")
    else:
        print("\n💥 Issue #680 WebSocket staging fallback validation: FAILED")