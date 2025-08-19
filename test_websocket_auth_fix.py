"""Test WebSocket authentication after fix."""
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_auth():
    """Test WebSocket authentication with auth service fix."""
    # First get a dev token
    import httpx
    
    async with httpx.AsyncClient() as client:
        # Get dev token
        try:
            login_response = await client.post(
                'http://127.0.0.1:8081/auth/dev/login',
                json={}
            )
            logger.info(f"Dev login response: {login_response.status_code}")
            if login_response.status_code == 200:
                login_data = login_response.json()
                token = login_data.get('access_token')
                logger.info(f"Got token: {token[:20]}...")
                
                # Now test WebSocket with token
                ws_url = f"ws://localhost:56307/ws?token={token}"
                logger.info(f"Connecting to WebSocket: {ws_url}")
                
                async with websockets.connect(ws_url) as websocket:
                    logger.info("WebSocket connected successfully!")
                    
                    # Send a test message
                    test_message = {
                        "type": "ping",
                        "timestamp": 123456789
                    }
                    await websocket.send(json.dumps(test_message))
                    logger.info(f"Sent message: {test_message}")
                    
                    # Wait for response
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    logger.info(f"Received response: {response}")
                    
                    await websocket.close()
                    logger.info("WebSocket test completed successfully!")
            else:
                logger.error(f"Dev login failed: {login_response.text}")
        except Exception as e:
            logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_auth())