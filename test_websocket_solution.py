#!/usr/bin/env python3
"""
Standalone WebSocket Solution Test

This script demonstrates and validates the WebSocket testing solution
without requiring Docker or external services.

Run: python test_websocket_solution.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.embedded_websocket_server import embedded_websocket_server
from test_framework.websocket_test_integration import (
    WebSocketTestClient,
    validate_websocket_events_for_chat
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_websocket_solution():
    """Test the complete WebSocket solution."""
    logger.info("🚀 Starting WebSocket solution validation...")
    
    try:
        # Start embedded WebSocket server
        async with embedded_websocket_server() as websocket_url:
            logger.info(f"✅ Embedded WebSocket server started: {websocket_url}")
            
            # Test 1: Basic connection
            logger.info("🧪 Test 1: Basic WebSocket connection")
            client = WebSocketTestClient(websocket_url)
            connected = await client.connect()
            
            if connected:
                logger.info("✅ WebSocket connection established")
                
                # Test ping/pong
                success = await client.send_message({"type": "ping"})
                if success:
                    response = await client.receive_message(timeout=3.0)
                    if response and response.get("type") == "pong":
                        logger.info("✅ Ping/pong test passed")
                    else:
                        logger.error("❌ Ping/pong test failed")
                        return False
                else:
                    logger.error("❌ Failed to send ping message")
                    return False
                
                await client.disconnect()
            else:
                logger.error("❌ Failed to establish WebSocket connection")
                return False
            
            # Test 2: Critical events for chat business value
            logger.info("🧪 Test 2: Critical WebSocket events validation")
            chat_events_valid = await validate_websocket_events_for_chat(websocket_url)
            
            if chat_events_valid:
                logger.info("✅ All critical WebSocket events validated")
            else:
                logger.error("❌ Critical WebSocket events validation failed")
                return False
            
            # Test 3: Chat message flow
            logger.info("🧪 Test 3: Chat message flow")
            client = WebSocketTestClient(websocket_url)
            connected = await client.connect()
            
            if connected:
                received_events = await client.send_chat_message(
                    "Hello, this is a test chat message!",
                    expect_events=True
                )
                
                expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
                all_received = all(received_events.get(event, False) for event in expected_events)
                
                if all_received:
                    logger.info("✅ Chat message flow test passed")
                    logger.info(f"   Received events: {list(received_events.keys())}")
                else:
                    missing = [e for e in expected_events if not received_events.get(e, False)]
                    logger.error(f"❌ Chat message flow test failed - missing: {missing}")
                    return False
                
                await client.disconnect()
            else:
                logger.error("❌ Failed to connect for chat message test")
                return False
            
            logger.info("🎉 ALL WEBSOCKET TESTS PASSED!")
            return True
    
    except Exception as e:
        logger.error(f"❌ WebSocket solution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    logger.info("🔍 WebSocket Integration Testing Solution")
    logger.info("=" * 50)
    
    success = await test_websocket_solution()
    
    if success:
        logger.info("=" * 50)
        logger.info("✅ SOLUTION VALIDATION SUCCESSFUL")
        logger.info("✅ WebSocket testing works without Docker dependencies")
        logger.info("✅ All 5 critical WebSocket events are emitted correctly")
        logger.info("✅ Chat business value is preserved and validated")
        return 0
    else:
        logger.error("=" * 50)
        logger.error("❌ SOLUTION VALIDATION FAILED")
        logger.error("❌ WebSocket testing needs additional fixes")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)