"""Test helpers for E2E tests."""

from typing import Any, Dict, List
import asyncio
from unittest.mock import MagicMock

def create_mock_response(status: int = 200, json_data: Dict = None):
    """Create a mock HTTP response."""
    response = MagicMock()
    response.status_code = status
    response.json.return_value = json_data or {}
    return response

async def wait_for_condition(condition, timeout: float = 5.0):
    """Wait for a condition to become true."""
    start = asyncio.get_event_loop().time()
    while not condition():
        if asyncio.get_event_loop().time() - start > timeout:
            raise TimeoutError("Condition not met within timeout")
        await asyncio.sleep(0.1)
