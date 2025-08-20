"""
Performance Testing Fixtures

Shared fixtures for all performance tests.
"""

import pytest
import asyncio
import os
from tests.e2e.test_helpers.performance_base import HighVolumeWebSocketServer, HighVolumeThroughputClient
from tests.e2e.fixtures.high_volume_data import test_user_token

# Environment configuration
E2E_TEST_CONFIG = {
    "websocket_url": os.getenv("E2E_WEBSOCKET_URL", "ws://localhost:8765"),
    "backend_url": os.getenv("E2E_BACKEND_URL", "http://localhost:8000"),
    "auth_service_url": os.getenv("E2E_AUTH_SERVICE_URL", "http://localhost:8001"),
    "skip_real_services": os.getenv("SKIP_REAL_SERVICES", "true").lower() == "true",
    "test_mode": os.getenv("HIGH_VOLUME_TEST_MODE", "mock")
}


@pytest.fixture
async def high_volume_server():
    """High-volume WebSocket server fixture."""
    if E2E_TEST_CONFIG["test_mode"] != "mock":
        yield None
        return
        
    server = HighVolumeWebSocketServer()
    await server.start()
    
    # Allow server startup time
    await asyncio.sleep(1.0)
    
    yield server
    await server.stop()


@pytest.fixture
async def throughput_client(test_user_token, high_volume_server):
    """High-volume throughput client fixture."""
    websocket_uri = E2E_TEST_CONFIG["websocket_url"]
    client = HighVolumeThroughputClient(websocket_uri, test_user_token["token"], "primary-client")
    
    # Establish connection with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await client.connect()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                pytest.skip(f"WebSocket connection failed after {max_retries} attempts: {e}")
            await asyncio.sleep(1.0)
    
    yield client
    
    # Cleanup
    try:
        await client.disconnect()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Client cleanup error: {e}")