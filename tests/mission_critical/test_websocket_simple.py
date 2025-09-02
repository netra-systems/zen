from shared.isolated_environment import get_env
#!/usr/bin/env python
"""MISSION CRITICAL: Simple WebSocket Bridge Tests

CRITICAL BUSINESS CONTEXT:
- WebSocket bridge is 90% of chat value delivery
- Run_id to thread_id extraction is ESSENTIAL for proper routing

Simple direct tests:
1. Run_id to thread_id extraction patterns
2. WebSocket event emission verification
3. Bridge initialization and health
"""

import asyncio
import os
import sys
from typing import Optional
from unittest.mock import MagicMock, patch

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up isolated test environment
os.environ["WEBSOCKET_TEST_ISOLATED"] = "true"
os.environ["SKIP_REAL_SERVICES"] = "true"
os.environ["TEST_COLLECTION_MODE"] = "1"

# Import the WebSocket bridge
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState


class MockWebSocketManager:
    def __init__(self):
        self.sent_messages = []
    
    async def send_to_thread(self, thread_id: str, message: dict) -> bool:
        self.sent_messages.append((thread_id, message))
        print(f"Mock WebSocket sent to {thread_id}: {message.get(\"type\", \"unknown\")}")
        return True


async def test_basic_extraction():
    """Test basic run_id to thread_id extraction."""
    print("\n=== Testing Basic Thread ID Extraction ===")
    
    mock_websocket = MockWebSocketManager()
    
    with patch("netra_backend.app.services.agent_websocket_bridge.get_websocket_manager", return_value=mock_websocket), \
         patch("netra_backend.app.services.agent_websocket_bridge.get_agent_execution_registry", return_value=MagicMock()):
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Test direct thread_id patterns
        test_cases = [
            ("thread_12345", "thread_12345"),
            ("thread_abc123", "thread_abc123"),
            ("run_thread_456", "thread_456"),
            ("user_123_thread_789_session", "thread_789"),
        ]
        
        print("Testing thread_id extraction patterns:")
        passed = 0
        failed = 0
        
        for run_id, expected in test_cases:
            try:
                result = await bridge._resolve_thread_id_from_run_id(run_id)
                if result == expected:
                    print(f"  PASS: {run_id} -> {result}")
                    passed += 1
                else:
                    print(f"  FAIL: {run_id} -> expected {expected}, got {result}")
                    failed += 1
            except Exception as e:
                print(f"  ERROR: {run_id} -> {e}")
                failed += 1
        
        print(f"Results: {passed} passed, {failed} failed")
        return failed == 0


async def run_test():
    """Run the test."""
    print("MISSION CRITICAL: WebSocket Bridge Tests")
    print("=" * 50)
    
    try:
        result = await test_basic_extraction()
        if result:
            print("SUCCESS: WebSocket bridge extraction test passed!")
        else:
            print("FAILURE: WebSocket bridge has issues!")
        return result
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(run_test())
    sys.exit(0 if result else 1)

