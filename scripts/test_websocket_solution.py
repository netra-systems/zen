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
    logger.info("[U+1F680] Starting WebSocket solution validation...")
    
    try:
        # Start embedded WebSocket server
        async with embedded_websocket_server() as websocket_url:
            logger.info(f" PASS:  Embedded WebSocket server started: {websocket_url}")
            
            # Test 1: Basic connection
            logger.info("[U+1F9EA] Test 1: Basic WebSocket connection")
            client = WebSocketTestClient(websocket_url)
            connected = await client.connect()
            
            if connected:
                logger.info(" PASS:  WebSocket connection established")
                
                # Test ping/pong
                success = await client.send_message({"type": "ping"})
                if success:
                    response = await client.receive_message(timeout=3.0)
                    if response and response.get("type") == "pong":
                        logger.info(" PASS:  Ping/pong test passed")
                    else:
                        logger.error(" FAIL:  Ping/pong test failed")
                        return False
                else:
                    logger.error(" FAIL:  Failed to send ping message")
                    return False
                
                await client.disconnect()
            else:
                logger.error(" FAIL:  Failed to establish WebSocket connection")
                return False
            
            # Test 2: Critical events for chat business value
            logger.info("[U+1F9EA] Test 2: Critical WebSocket events validation")
            chat_events_valid = await validate_websocket_events_for_chat(websocket_url)
            
            if chat_events_valid:
                logger.info(" PASS:  All critical WebSocket events validated")
            else:
                logger.error(" FAIL:  Critical WebSocket events validation failed")
                return False
            
            # Test 3: Chat message flow
            logger.info("[U+1F9EA] Test 3: Chat message flow")
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
                    logger.info(" PASS:  Chat message flow test passed")
                    logger.info(f"   Received events: {list(received_events.keys())}")
                else:
                    missing = [e for e in expected_events if not received_events.get(e, False)]
                    logger.error(f" FAIL:  Chat message flow test failed - missing: {missing}")
                    return False
                
                await client.disconnect()
            else:
                logger.error(" FAIL:  Failed to connect for chat message test")
                return False
            
            logger.info(" CELEBRATION:  ALL WEBSOCKET TESTS PASSED!")
            return True
    
    except Exception as e:
        logger.error(f" FAIL:  WebSocket solution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    logger.info(" SEARCH:  WebSocket Integration Testing Solution")
    logger.info("=" * 50)
    
    success = await test_websocket_solution()
    
    if success:
        logger.info("=" * 50)
        logger.info(" PASS:  SOLUTION VALIDATION SUCCESSFUL")
        logger.info(" PASS:  WebSocket testing works without Docker dependencies")
        logger.info(" PASS:  All 5 critical WebSocket events are emitted correctly")
        logger.info(" PASS:  Chat business value is preserved and validated")
        return 0
    else:
        logger.error("=" * 50)
        logger.error(" FAIL:  SOLUTION VALIDATION FAILED")
        logger.error(" FAIL:  WebSocket testing needs additional fixes")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)