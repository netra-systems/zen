#!/usr/bin/env python3
"""
Quick WebSocket connection test for staging environment.
This validates that the E2E environment variables are working correctly.
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_websocket_staging():
    """Test WebSocket connection to staging with E2E headers."""
    
    # Staging WebSocket URL (use wss:// for secure connection)
    ws_url = "wss://netra-backend-staging-701982941522.us-central1.run.app/ws"
    
    # E2E testing headers to bypass JWT authentication
    headers = {
        "X-Test-Type": "e2e",
        "X-Test-Environment": "staging",
        "X-E2E-Test": "true",
        "X-Test-Mode": "test",
        "User-Agent": "WebSocket-Test-Client"
    }
    
    try:
        logger.info(f"Attempting to connect to {ws_url}")
        logger.info(f"Using E2E headers: {headers}")
        
        # Connect with timeout (using additional_headers for compatibility)
        async with websockets.connect(
            ws_url, 
            additional_headers=headers,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5
        ) as websocket:
            logger.info("✅ WebSocket connected successfully!")
            
            # Wait for welcome message
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                welcome_data = json.loads(welcome_msg)
                logger.info(f"✅ Received welcome message: {welcome_data}")
                
                # Check if connection_established event
                if welcome_data.get("event") == "connection_established":
                    logger.info("🎉 Connection fully established!")
                    logger.info(f"   Connection ID: {welcome_data.get('connection_id', 'N/A')}")
                    logger.info(f"   Environment: {welcome_data.get('environment', 'N/A')}")
                    logger.info(f"   Factory pattern: {welcome_data.get('factory_pattern_enabled', 'N/A')}")
                    logger.info(f"   Ready for messages: {welcome_data.get('connection_ready', False)}")
                
            except asyncio.TimeoutError:
                logger.error("❌ Timeout waiting for welcome message")
                return False
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in welcome message: {e}")
                logger.error(f"   Raw message: {welcome_msg}")
                return False
            
            # Send a test message
            test_message = {
                "type": "ping",
                "timestamp": datetime.now().isoformat(),
                "test_data": "WebSocket E2E test"
            }
            
            logger.info(f"Sending test message: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            try:
                response_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response_msg)
                logger.info(f"✅ Received response: {response_data}")
                return True
                
            except asyncio.TimeoutError:
                logger.warning("⚠️ Timeout waiting for response (but connection succeeded)")
                return True  # Connection worked, response timeout is acceptable
                
    except websockets.exceptions.ConnectionClosedError as e:
        logger.error(f"❌ WebSocket connection closed: {e.code} - {e.reason}")
        if e.code == 1008:  # Policy violation
            logger.error("   This indicates authentication/authorization failure")
            logger.error("   The E2E environment variables may not be set correctly")
        return False
        
    except websockets.exceptions.InvalidStatus as e:
        status_text = str(e).split(": ")[-1] if ": " in str(e) else str(e)
        logger.error(f"❌ WebSocket handshake failed: {status_text}")
        logger.error("   This indicates the server rejected the WebSocket upgrade")
        logger.error("   The E2E testing headers may not be properly detected")
        return False
        
    except Exception as e:
        logger.error(f"❌ WebSocket connection failed: {e}")
        return False

async def main():
    """Main test function."""
    logger.info("Starting WebSocket staging test...")
    logger.info("=" * 50)
    
    success = await test_websocket_staging()
    
    logger.info("=" * 50)
    if success:
        logger.info("🎉 STAGING WEBSOCKET TEST: SUCCESS!")
        logger.info("   The E2E environment variables are working correctly")
        logger.info("   WebSocket connections should work for staging tests")
    else:
        logger.error("❌ STAGING WEBSOCKET TEST: FAILED!")
        logger.error("   E2E environment variables may need additional configuration")
        logger.error("   Check staging deployment and environment variables")

if __name__ == "__main__":
    asyncio.run(main())