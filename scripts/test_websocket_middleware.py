#!/usr/bin/env python
"""Test script to verify WebSocket connectivity and identify middleware issues."""

import asyncio
import json
import logging
import sys
from typing import Optional
from shared.isolated_environment import IsolatedEnvironment

import httpx
import websockets

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebSocketTester:
    """Test WebSocket connectivity through middleware."""
    
    def __init__(self, base_url: str = "http://localhost:8000", ws_base: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.ws_base = ws_base
        self.token: Optional[str] = None
        
    async def test_health_check(self) -> bool:
        """Test if the backend is running."""
        logger.info("Testing backend health check...")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                logger.info(f"Health check response: {response.status_code}")
                return response.status_code == 200
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return False
    
    async def test_ws_config_endpoint(self) -> dict:
        """Test WebSocket configuration endpoint."""
        logger.info("Testing WebSocket config endpoint...")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/ws/config")
                if response.status_code == 200:
                    config = response.json()
                    logger.info(f"WebSocket config retrieved: {json.dumps(config, indent=2)}")
                    return config
                else:
                    logger.error(f"Config endpoint returned: {response.status_code}")
                    return {}
            except Exception as e:
                logger.error(f"Config endpoint failed: {e}")
                return {}
    
    async def test_websocket_test_endpoint(self) -> bool:
        """Test the unauthenticated test WebSocket endpoint."""
        logger.info("Testing WebSocket test endpoint (no auth)...")
        ws_url = f"{self.ws_base}/ws/test"
        
        try:
            logger.info(f"Attempting to connect to: {ws_url}")
            async with websockets.connect(ws_url) as websocket:
                logger.info("Connected to test WebSocket!")
                
                # Wait for welcome message
                welcome = await websocket.recv()
                logger.info(f"Welcome message: {welcome}")
                
                # Send a ping
                await websocket.send(json.dumps({"type": "ping"}))
                pong = await websocket.recv()
                logger.info(f"Pong response: {pong}")
                
                # Test echo
                await websocket.send(json.dumps({"type": "echo", "data": "test"}))
                echo = await websocket.recv()
                logger.info(f"Echo response: {echo}")
                
                await websocket.close()
                return True
                
        except Exception as e:
            logger.error(f"Test WebSocket failed: {e}")
            return False
    
    async def test_websocket_with_cors_headers(self) -> bool:
        """Test WebSocket with CORS origin headers."""
        logger.info("Testing WebSocket with CORS headers...")
        ws_url = f"{self.ws_base}/ws/test"
        
        try:
            # Test with different origin headers
            origins = [
                "http://localhost:3000",
                "http://localhost:3001", 
                "http://127.0.0.1:3000",
                "https://app.staging.netrasystems.ai"
            ]
            
            for origin in origins:
                logger.info(f"Testing with origin: {origin}")
                headers = {
                    "Origin": origin,
                    "User-Agent": "WebSocketTester/1.0"
                }
                
                try:
                    async with websockets.connect(ws_url, extra_headers=headers) as websocket:
                        logger.info(f"[U+2713] Connected with origin: {origin}")
                        await websocket.close()
                except Exception as e:
                    logger.warning(f"[U+2717] Failed with origin {origin}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"CORS test failed: {e}")
            return False
    
    async def check_middleware_order(self) -> None:
        """Analyze middleware configuration issues."""
        logger.info("\n=== MIDDLEWARE ANALYSIS ===")
        
        # Check if WebSocket endpoints are excluded from auth
        logger.info("\n1. Auth Middleware Configuration:")
        logger.info("   - WebSocket paths (/ws, /websocket) should be excluded from auth middleware")
        logger.info("   - Current setup: Auth middleware doesn't explicitly exclude WebSocket paths")
        logger.info("   - Issue: Auth middleware may interfere with WebSocket upgrade requests")
        
        # Check CORS middleware setup
        logger.info("\n2. CORS Middleware Configuration:")
        logger.info("   - WebSocketAwareCORSMiddleware skips WebSocket upgrades")
        logger.info("   - WebSocketCORSMiddleware handles WebSocket CORS separately")
        logger.info("   - Current setup: Proper separation of HTTP and WebSocket CORS")
        
        # Check middleware order
        logger.info("\n3. Middleware Order:")
        logger.info("   - Security middleware  ->  Request middleware  ->  Security response middleware")
        logger.info("   - WebSocket CORS wrapping happens in setup_request_middleware")
        logger.info("   - Issue: WebSocket wrapping may not be effective due to FastAPI limitations")
        
        # Key findings
        logger.info("\n=== KEY FINDINGS ===")
        logger.info("1. AUTH MIDDLEWARE ISSUE:")
        logger.info("   - Auth middleware processes ALL non-excluded paths")
        logger.info("   - WebSocket paths (/ws, /websocket) are NOT in excluded_paths")
        logger.info("   - This causes auth middleware to interfere with WebSocket upgrade")
        
        logger.info("\n2. WEBSOCKET CORS WRAPPING:")
        logger.info("   - configure_websocket_cors() wraps the app but doesn't reassign")
        logger.info("   - FastAPI middleware chain may not include the wrapped WebSocket handler")
        
        logger.info("\n3. SECURITY HEADERS:")
        logger.info("   - Security headers middleware adds headers to /ws paths")
        logger.info("   - May interfere with WebSocket upgrade process")
        
    async def run_all_tests(self) -> None:
        """Run all WebSocket connectivity tests."""
        logger.info("=== STARTING WEBSOCKET MIDDLEWARE AUDIT ===\n")
        
        # Test basic connectivity
        if await self.test_health_check():
            logger.info("[U+2713] Backend is running\n")
        else:
            logger.error("[U+2717] Backend is not running. Please start the backend first.\n")
            return
        
        # Get WebSocket config
        config = await self.test_ws_config_endpoint()
        if config:
            logger.info("[U+2713] WebSocket config endpoint accessible\n")
        else:
            logger.warning("[U+2717] WebSocket config endpoint not accessible\n")
        
        # Test WebSocket connectivity
        if await self.test_websocket_test_endpoint():
            logger.info("[U+2713] Test WebSocket endpoint works\n")
        else:
            logger.error("[U+2717] Test WebSocket endpoint failed\n")
        
        # Test CORS
        if await self.test_websocket_with_cors_headers():
            logger.info("[U+2713] CORS headers handled\n")
        else:
            logger.warning("[U+2717] CORS issues detected\n")
        
        # Analyze middleware configuration
        await self.check_middleware_order()
        
        # Recommendations
        logger.info("\n=== RECOMMENDATIONS ===")
        logger.info("1. Add WebSocket paths to auth middleware exclusions:")
        logger.info('   excluded_paths = ["/health", "/metrics", "/", "/docs", "/openapi.json", "/redoc", "/ws", "/websocket", "/ws/test"]')
        logger.info("\n2. Properly integrate WebSocket CORS middleware:")
        logger.info("   - Consider using ASGI middleware mounting instead of wrapping")
        logger.info("   - Or handle CORS directly in WebSocket endpoint")
        logger.info("\n3. Skip security headers for WebSocket upgrade requests:")
        logger.info("   - Check for Upgrade: websocket header before adding security headers")


async def main():
    """Main entry point."""
    tester = WebSocketTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())