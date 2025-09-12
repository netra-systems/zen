#!/usr/bin/env python3
"""
WebSocket App Integration Test - Test with FastAPI app like the failing test
Reproduces the integration test behavior to identify the timeout root cause.
"""

import asyncio
import json
import os
import sys
import logging
from datetime import datetime, timezone
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set minimal environment variables for testing
os.environ.setdefault("TEST_ENV", "test")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("E2E_TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-unified-testing-32chars")

# Add path for imports
sys.path.insert(0, '/Users/anthony/Documents/GitHub/netra-apex')

try:
    # Mock WebSocket TestClient first to avoid import issues
    import pytest
    from fastapi.testclient import TestClient
    from unittest.mock import Mock, MagicMock
    
    # Try to import the E2E auth helper
    from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
    logger.info(" PASS:  Successfully imported E2EWebSocketAuthHelper")
    
    # Now try importing the backend app (this may cause import issues)
    logger.info("Attempting to import backend app...")
    
    # Set additional environment variables that might be needed
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
    os.environ.setdefault("CLICKHOUSE_URL", "http://localhost:8123")
    
    try:
        from netra_backend.app.main import app
        logger.info(" PASS:  Successfully imported FastAPI app")
    except Exception as e:
        logger.error(f" FAIL:  Failed to import FastAPI app: {e}")
        logger.info("Creating minimal mock app for WebSocket testing...")
        
        from fastapi import FastAPI, WebSocket
        from fastapi.responses import JSONResponse
        
        # Create minimal mock app
        app = FastAPI()
        
        @app.websocket("/ws")
        async def mock_websocket_endpoint(websocket: WebSocket):
            """Mock WebSocket endpoint that behaves like the real one."""
            logger.info(f"Mock WebSocket connection from {websocket.client}")
            await websocket.accept()
            
            # Send connection established message
            await websocket.send_json({
                "type": "connection_established",
                "connection_id": f"mock-conn-{int(datetime.now().timestamp())}",
                "user_id": "mock-test-user",
                "connection_ready": True,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "config": {"heartbeat_interval": 30}
            })
            
            try:
                while True:
                    # Listen for messages
                    data = await websocket.receive_json()
                    logger.info(f"Mock received: {data}")
                    
                    # Handle ping/pong
                    if data.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    
                    # Handle echo
                    elif data.get("type") == "echo":
                        await websocket.send_json({
                            "type": "echo_response",
                            "original": data
                        })
                        
            except Exception as e:
                logger.info(f"Mock WebSocket connection closed: {e}")
                
        logger.info(" PASS:  Created minimal mock app for WebSocket testing")
    
    
    async def test_websocket_connection_success():
        """Test successful WebSocket connection with proper JWT authentication."""
        logger.info("[U+1F9EA] Testing WebSocket connection success...")
        
        try:
            # Create auth helper
            auth_helper = E2EWebSocketAuthHelper(environment="test")
            
            # Create JWT token
            token = auth_helper.create_test_jwt_token(
                user_id="websocket-test-user", 
                email="websocket-test@example.com",
                permissions=["read", "write"],
                exp_minutes=10
            )
            
            # Get WebSocket headers
            headers = auth_helper.get_websocket_headers(token)
            logger.info(f"WebSocket headers: {headers}")
            
            # Create TestClient and try connection
            client = TestClient(app)
            
            # Use timeout to detect if it hangs
            timeout_duration = 10.0
            logger.info(f"Attempting WebSocket connection with {timeout_duration}s timeout...")
            
            try:
                with client.websocket_connect("/ws", headers=headers) as websocket:
                    logger.info(" PASS:  WebSocket connection successful!")
                    
                    # Should receive connection_established message
                    data = websocket.receive_json()
                    logger.info(f"Received connection data: {data}")
                    
                    # Verify connection established
                    assert data["type"] == "connection_established"
                    assert "connection_id" in data
                    assert "user_id" in data
                    assert data["connection_ready"] is True
                    
                    logger.info(" PASS:  Connection success test passed!")
                    return True
                    
            except Exception as e:
                logger.error(f" FAIL:  WebSocket connection failed: {e}")
                logger.error(f"Error type: {type(e)}")
                import traceback
                traceback.print_exc()
                return False
                
        except Exception as e:
            logger.error(f" FAIL:  Test setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    async def test_websocket_no_auth():
        """Test WebSocket connection fails without authentication token."""
        logger.info("[U+1F9EA] Testing WebSocket connection without auth...")
        
        try:
            client = TestClient(app)
            
            # Try to connect without authentication - should fail
            try:
                with client.websocket_connect("/ws") as websocket:
                    logger.error(" FAIL:  Connection succeeded when it should have failed!")
                    return False
            except Exception as e:
                logger.info(f" PASS:  Connection correctly failed: {e}")
                return True
                
        except Exception as e:
            logger.error(f" FAIL:  Test setup failed: {e}")
            return False
    
    
    async def test_websocket_ping_pong():
        """Test WebSocket ping/pong messaging with authentication."""
        logger.info("[U+1F9EA] Testing WebSocket ping/pong...")
        
        try:
            # Create auth helper
            auth_helper = E2EWebSocketAuthHelper(environment="test")
            token = auth_helper.create_test_jwt_token(
                user_id="websocket-ping-test", 
                email="ping-test@example.com"
            )
            headers = auth_helper.get_websocket_headers(token)
            
            client = TestClient(app)
            
            with client.websocket_connect("/ws", headers=headers) as websocket:
                # Wait for connection established
                connection_data = websocket.receive_json()
                assert connection_data["type"] == "connection_established"
                
                # Send ping message
                ping_message = {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                websocket.send_json(ping_message)
                
                # Should receive pong response
                response = websocket.receive_json()
                assert response["type"] == "pong"
                assert "timestamp" in response
                
                logger.info(" PASS:  Ping/pong test passed!")
                return True
                
        except Exception as e:
            logger.error(f" FAIL:  Ping/pong test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    async def main():
        """Main test execution."""
        logger.info("[U+1F680] Starting WebSocket App Integration Tests...")
        
        tests = [
            ("Connection Success", test_websocket_connection_success),
            ("No Auth Failure", test_websocket_no_auth),
            ("Ping/Pong", test_websocket_ping_pong)
        ]
        
        results = {}
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                # Run each test with timeout
                result = await asyncio.wait_for(test_func(), timeout=15.0)
                results[test_name] = result
                logger.info(f" PASS:  {test_name}: {'PASS' if result else 'FAIL'}")
            except asyncio.TimeoutError:
                logger.error(f" FAIL:  {test_name}: TIMEOUT (15s)")
                results[test_name] = False
            except Exception as e:
                logger.error(f" FAIL:  {test_name}: ERROR - {e}")
                results[test_name] = False
        
        # Print final results
        logger.info(f"\n{'='*50}")
        logger.info("FINAL RESULTS")
        logger.info(f"{'='*50}")
        
        for test_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            logger.info(f"{test_name}: {status}")
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        logger.info(f"\nTotal: {passed_tests}/{total_tests} tests passed")
        
        return all(results.values())
    
    
    if __name__ == "__main__":
        # Run the tests
        try:
            success = asyncio.run(main())
            exit(0 if success else 1)
        except KeyboardInterrupt:
            logger.info("Tests interrupted by user")
            exit(1)
        except Exception as e:
            logger.error(f"Critical error: {e}")
            import traceback
            traceback.print_exc()
            exit(1)

except ImportError as e:
    logger.error(f" FAIL:  Import failed: {e}")
    logger.error("This indicates missing dependencies or import path issues")
    logger.error("The integration tests are likely failing due to similar import issues")
    exit(1)