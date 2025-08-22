#!/usr/bin/env python3
"""
Simple WebSocket Test Script for Netra Platform
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Optional, Any

import httpx
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

# Service URLs from running services
BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8083"
WEBSOCKET_URL = "ws://localhost:8000/ws"

async def get_auth_token():
    """Get authentication token."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/auth/dev/login",
                json={}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
        except Exception:
            pass
        return None

async def test_websocket_connection():
    """Test WebSocket connection."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests_passed": 0,
        "tests_failed": 0,
        "websocket_connections": [],
        "messages_sent": [],
        "messages_received": [],
        "errors": []
    }
    
    print("Starting WebSocket Tests")
    
    # Get authentication token
    auth_token = await get_auth_token()
    if auth_token:
        print(f"PASS: Got auth token: {auth_token[:20]}...")
        results["tests_passed"] += 1
    else:
        print("FAIL: Could not get auth token")
        results["tests_failed"] += 1
        return results
    
    # Test WebSocket Info Endpoint
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{BACKEND_URL}/ws")
            if response.status_code == 200:
                print("PASS: WebSocket Info Endpoint")
                results["tests_passed"] += 1
            else:
                print(f"FAIL: WebSocket Info Endpoint - Status {response.status_code}")
                results["tests_failed"] += 1
        except Exception as e:
            print(f"FAIL: WebSocket Info Endpoint - {str(e)}")
            results["tests_failed"] += 1
    
    # Test WebSocket Connection (multiple methods)
    websocket_endpoints = [
        (WEBSOCKET_URL, "Standard WebSocket"),
        ("ws://localhost:8000/ws/secure", "Secure WebSocket"),
    ]
    
    for ws_url, test_name in websocket_endpoints:
        print(f"\nTesting {test_name} at {ws_url}")
        
        websocket = None
        connection_method = "unknown"
        
        # Method 1: With Authorization header and subprotocols
        if auth_token:
            try:
                headers = {"Authorization": f"Bearer {auth_token}"}
                subprotocols = ["jwt-auth", f"Bearer.{auth_token}"]
                
                websocket = await websockets.connect(
                    ws_url,
                    extra_headers=headers,
                    subprotocols=subprotocols,
                    timeout=10
                )
                connection_method = "headers_and_subprotocols"
                print(f"PASS: {test_name} Connection - Connected via {connection_method}")
                results["tests_passed"] += 1
                
            except Exception as e:
                print(f"FAIL: {test_name} Connection (Method 1) - {str(e)}")
                results["tests_failed"] += 1
                
                # Method 2: Headers only
                try:
                    websocket = await websockets.connect(
                        ws_url,
                        extra_headers=headers,
                        timeout=10
                    )
                    connection_method = "headers_only"
                    print(f"PASS: {test_name} Connection - Connected via {connection_method}")
                    results["tests_passed"] += 1
                    
                except Exception as e2:
                    print(f"FAIL: {test_name} Connection (Method 2) - {str(e2)}")
                    results["tests_failed"] += 1
                    
                    # Method 3: No auth (fallback)
                    try:
                        websocket = await websockets.connect(ws_url, timeout=10)
                        connection_method = "no_auth"
                        print(f"PASS: {test_name} Connection - Connected via {connection_method}")
                        results["tests_passed"] += 1
                        
                    except Exception as e3:
                        print(f"FAIL: {test_name} Connection (All Methods) - Last error: {str(e3)}")
                        results["tests_failed"] += 1
        
        if websocket:
            try:
                results["websocket_connections"].append({
                    "url": ws_url,
                    "method": connection_method,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Test Ping/Pong
                try:
                    pong_waiter = await websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=5.0)
                    print(f"PASS: {test_name} Ping/Pong")
                    results["tests_passed"] += 1
                except asyncio.TimeoutError:
                    print(f"FAIL: {test_name} Ping/Pong - Timeout")
                    results["tests_failed"] += 1
                except Exception as e:
                    print(f"FAIL: {test_name} Ping/Pong - {str(e)}")
                    results["tests_failed"] += 1
                
                # Test Message Exchange
                try:
                    test_message = {
                        "type": "message",
                        "data": {
                            "message": "Hello WebSocket! This is a test.",
                            "timestamp": datetime.now().isoformat()
                        },
                        "id": "test-message-001"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    results["messages_sent"].append({
                        "message": test_message,
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"PASS: {test_name} Message Send")
                    results["tests_passed"] += 1
                    
                    # Try to receive response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        if response:
                            try:
                                response_data = json.loads(response)
                                results["messages_received"].append({
                                    "message": response_data,
                                    "timestamp": datetime.now().isoformat()
                                })
                                print(f"PASS: {test_name} Message Receive - Got response")
                                results["tests_passed"] += 1
                            except json.JSONDecodeError:
                                print(f"PASS: {test_name} Message Receive - Got raw response: {response[:100]}...")
                                results["tests_passed"] += 1
                        else:
                            print(f"FAIL: {test_name} Message Receive - Empty response")
                            results["tests_failed"] += 1
                    except asyncio.TimeoutError:
                        print(f"FAIL: {test_name} Message Receive - Timeout (this may be expected)")
                        results["tests_failed"] += 1
                        
                except Exception as e:
                    print(f"FAIL: {test_name} Message Exchange - {str(e)}")
                    results["tests_failed"] += 1
                
            finally:
                await websocket.close()
    
    return results

async def main():
    """Main test execution."""
    results = await test_websocket_connection()
    
    print(f"\nWebSocket Test Results:")
    print(f"   Passed: {results['tests_passed']}")
    print(f"   Failed: {results['tests_failed']}")
    print(f"   WebSocket Connections: {len(results['websocket_connections'])}")
    print(f"   Messages Sent: {len(results['messages_sent'])}")
    print(f"   Messages Received: {len(results['messages_received'])}")
    
    # Save results to file
    with open("websocket_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to websocket_test_results.json")
    
    # Return success if all tests passed
    success = results["tests_failed"] == 0 and results["tests_passed"] > 0
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)