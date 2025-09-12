#!/usr/bin/env python3
"""
Test WebSocket connection to diagnose rapid disconnect issue.

This script tests the WebSocket connection to understand why it's immediately
disconnecting after successful authentication.
"""

import asyncio
import json
import websockets
import logging
from datetime import datetime
from shared.isolated_environment import IsolatedEnvironment

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    """Test WebSocket connection with various configurations."""
    
    # Test configurations
    test_configs = [
        {
            "name": "No authentication (dev mode)",
            "url": "ws://localhost:8000/ws",
            "headers": {},
            "subprotocols": []
        },
        {
            "name": "With CORS origin header only",
            "url": "ws://localhost:8000/ws",
            "headers": {
                "Origin": "http://localhost:3000"
            },
            "subprotocols": []
        },
        {
            "name": "With dev token in subprotocol",
            "url": "ws://localhost:8000/ws",
            "headers": {
                "Origin": "http://localhost:3000"
            },
            "subprotocols": ["jwt-auth"]
        }
    ]
    
    for config in test_configs:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {config['name']}")
        logger.info(f"URL: {config['url']}")
        logger.info(f"Headers: {config['headers']}")
        logger.info(f"Subprotocols: {config['subprotocols']}")
        logger.info(f"{'='*60}")
        
        try:
            # Connect to WebSocket
            connect_params = {
                'uri': config['url']
            }
            if config['headers']:
                connect_params['additional_headers'] = config['headers']
            if config['subprotocols']:
                connect_params['subprotocols'] = config['subprotocols']
                
            async with websockets.connect(**connect_params) as websocket:
                logger.info(f" PASS:  Connected successfully!")
                logger.info(f"Connection state: {websocket.state}")
                logger.info(f"Subprotocol: {websocket.subprotocol}")
                
                # Send a test message
                test_message = {
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send(json.dumps(test_message))
                logger.info(f"[U+1F4E4] Sent ping message: {test_message}")
                
                # Try to receive messages for 5 seconds
                try:
                    message_count = 0
                    async for message in asyncio.wait_for(websocket.__aiter__(), timeout=5):
                        message_count += 1
                        logger.info(f"[U+1F4E5] Received message {message_count}: {message[:200]}...")
                        
                        # Parse and log message type
                        try:
                            data = json.loads(message)
                            logger.info(f"   Message type: {data.get('type', 'unknown')}")
                            
                            # If it's a ping, send pong
                            if data.get('type') == 'ping':
                                pong_message = {
                                    "type": "pong",
                                    "timestamp": datetime.now().isoformat(),
                                    "original_timestamp": data.get("timestamp")
                                }
                                await websocket.send(json.dumps(pong_message))
                                logger.info(f"[U+1F4E4] Sent pong response")
                                
                        except json.JSONDecodeError:
                            logger.warning(f"   Could not parse message as JSON")
                            
                        if message_count >= 3:
                            break
                            
                except asyncio.TimeoutError:
                    logger.info("[U+23F1][U+FE0F] No more messages received (timeout)")
                    
                # Check final connection state
                logger.info(f"Final connection state: {websocket.state}")
                
        except websockets.exceptions.WebSocketException as e:
            logger.error(f" FAIL:  WebSocket error: {e}")
        except Exception as e:
            logger.error(f" FAIL:  Unexpected error: {e}", exc_info=True)
            
        await asyncio.sleep(1)  # Brief pause between tests

async def monitor_connection_lifecycle():
    """Monitor WebSocket connection lifecycle in detail."""
    
    logger.info("\n" + "="*60)
    logger.info("DETAILED CONNECTION LIFECYCLE MONITORING")
    logger.info("="*60)
    
    url = "ws://localhost:8000/ws"
    headers = {"Origin": "http://localhost:3000"}
    
    try:
        logger.info(f"[U+1F50C] Initiating connection to {url}")
        websocket = await websockets.connect(
            url,
            additional_headers=headers
        )
        
        logger.info(f" PASS:  Connection established")
        logger.info(f"   State: {websocket.state}")
        logger.info(f"   Local address: {websocket.local_address}")
        logger.info(f"   Remote address: {websocket.remote_address}")
        
        # Monitor for 10 seconds
        start_time = asyncio.get_event_loop().time()
        message_count = 0
        
        while asyncio.get_event_loop().time() - start_time < 10:
            try:
                # Wait for message with short timeout
                message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                message_count += 1
                timestamp = asyncio.get_event_loop().time() - start_time
                logger.info(f"[{timestamp:.2f}s] Message #{message_count}: {message[:100]}...")
                
            except asyncio.TimeoutError:
                # Check if still connected
                if websocket.state.value != 1:  # 1 = OPEN
                    logger.warning(f" WARNING: [U+FE0F] Connection state changed: {websocket.state}")
                    break
                    
            except websockets.exceptions.ConnectionClosed as e:
                logger.error(f" FAIL:  Connection closed: code={e.code}, reason={e.reason}")
                break
                
        # Clean close
        if websocket.state.value == 1:
            await websocket.close()
            logger.info("[U+1F50C] Connection closed cleanly")
            
    except Exception as e:
        logger.error(f" FAIL:  Error during lifecycle monitoring: {e}", exc_info=True)

async def main():
    """Run all WebSocket tests."""
    
    logger.info("Starting WebSocket connection tests...")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Test basic connections
    await test_websocket_connection()
    
    # Monitor detailed lifecycle
    await monitor_connection_lifecycle()
    
    logger.info("\n" + "="*60)
    logger.info("All tests completed")
    logger.info("="*60)

if __name__ == "__main__":
    asyncio.run(main())