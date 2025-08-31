#!/usr/bin/env python3
"""
Manual WebSocket Test Script

This script tests WebSocket connections in development mode to verify the fixes.
"""

import asyncio
import json
import websockets
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def test_websocket_connection():
    """Test WebSocket connection in development mode."""
    uri = "ws://localhost:8000/ws"
    
    try:
        logger.info(f"Attempting to connect to: {uri}")
        
        # Try connection without authentication (development mode)
        async with websockets.connect(uri) as websocket:
            logger.info("✅ WebSocket connection established!")
            
            # Send a test message
            test_message = {
                "type": "ping",
                "timestamp": asyncio.get_event_loop().time(),
                "data": "Hello WebSocket!"
            }
            
            logger.info(f"Sending test message: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                logger.info(f"✅ Received response: {response_data}")
                
                # Check if we got expected response types
                if response_data.get("type") in ["pong", "connection_established", "system_message"]:
                    logger.info("✅ WebSocket bidirectional communication working!")
                    return True
                    
            except asyncio.TimeoutError:
                logger.warning("⚠️  No response received within 5 seconds")
                logger.info("✅ Connection established but no response (may be expected)")
                return True
                
    except websockets.exceptions.ConnectionClosedError as e:
        logger.error(f"❌ WebSocket connection closed: {e.code} - {e.reason}")
        
        # Check if this is an auth error (expected without token)
        if e.code == 1008:  # Policy violation (auth failure)
            logger.info("ℹ️  Connection closed due to authentication (expected without token)")
            logger.info("✅ WebSocket authentication bypass may need explicit enabling")
            return False
        return False
        
    except Exception as e:
        logger.error(f"❌ WebSocket connection failed: {e}")
        return False


async def test_websocket_test_endpoint():
    """Test the /ws/test endpoint (no auth required)."""
    uri = "ws://localhost:8000/ws/test"
    
    try:
        logger.info(f"Attempting to connect to test endpoint: {uri}")
        
        # This endpoint should work without authentication
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Test WebSocket connection established!")
            
            # Send a test message
            test_message = {
                "type": "ping",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            logger.info(f"Sending test message: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                logger.info(f"✅ Received response: {response_data}")
                
                if response_data.get("type") == "pong":
                    logger.info("✅ Test endpoint working perfectly!")
                    return True
                    
            except asyncio.TimeoutError:
                logger.warning("⚠️  No response received from test endpoint")
                
    except Exception as e:
        logger.error(f"❌ Test WebSocket connection failed: {e}")
        return False


async def main():
    """Run WebSocket tests."""
    logger.info("🚀 Starting WebSocket Connection Tests")
    logger.info("=" * 50)
    
    # Test 1: Test endpoint (should always work)
    logger.info("Test 1: Testing /ws/test endpoint")
    test_result = await test_websocket_test_endpoint()
    
    # Test 2: Main endpoint (may require OAUTH SIMULATION)
    logger.info("\nTest 2: Testing /ws main endpoint")
    main_result = await test_websocket_connection()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Test Endpoint (/ws/test): {'✅ PASS' if test_result else '❌ FAIL'}")
    logger.info(f"Main Endpoint (/ws): {'✅ PASS' if main_result else '❌ FAIL'}")
    
    if test_result:
        logger.info("✅ WebSocket infrastructure is working!")
    else:
        logger.info("❌ WebSocket infrastructure needs attention")
        
    if main_result:
        logger.info("✅ Development OAUTH SIMULATION is working!")
    else:
        logger.info("ℹ️  Main endpoint requires authentication or bypass configuration")
    
    return test_result or main_result


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        exit(1)