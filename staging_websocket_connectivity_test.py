#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE 1 WebSocket SSOT Validation - Staging GCP Connectivity Test
Focus: Test basic WebSocket connectivity to staging GCP environment
Business Impact: $60K+ MRR at risk from broken chat functionality
"""
import sys
import io
# Fix Windows console encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')
import asyncio
import json
import time
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
import os
import sys

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

async def test_staging_websocket_basic_connectivity():
    """Test basic WebSocket connectivity to staging GCP"""
    
    # Staging WebSocket URL from .env.staging
    staging_ws_url = "wss://api.staging.netrasystems.ai/ws"
    
    print(f"[PHASE 1] WebSocket SSOT Validation")
    print(f"[TESTING] Connectivity to: {staging_ws_url}")
    print(f"[BUSINESS] Impact: $60K+ MRR Golden Path at risk")
    print("="*60)
    
    start_time = time.time()
    
    try:
        # Test basic WebSocket connection
        print("[CONNECT] Attempting WebSocket connection...")
        
        async with websockets.connect(
            staging_ws_url,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        ) as websocket:
            connection_time = time.time() - start_time
            print(f"[SUCCESS] WebSocket connection successful in {connection_time:.2f}s")
            
            # Test basic ping/pong
            print("[PING] Testing WebSocket ping/pong...")
            pong_waiter = await websocket.ping()
            await asyncio.wait_for(pong_waiter, timeout=5)
            ping_time = time.time() - start_time
            print(f"[SUCCESS] Ping/pong successful in {ping_time:.2f}s")
            
            # Test JSON message serialization (key issue from Phase 1)
            print("[JSON] Testing JSON message serialization...")
            test_message = {
                "type": "test_websocket_json_serialization",
                "data": {
                    "agent_state": "testing",
                    "user_id": "test-user-123",
                    "timestamp": time.time()
                }
            }
            
            # Send test message
            await websocket.send(json.dumps(test_message))
            json_send_time = time.time() - start_time
            print(f"[SUCCESS] JSON message sent in {json_send_time:.2f}s")
            
            # Wait for response or timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                json_response_time = time.time() - start_time
                print(f"[RESPONSE] Received response in {json_response_time:.2f}s: {response[:100]}...")
                
                # Try to parse response as JSON
                try:
                    response_data = json.loads(response)
                    print("[SUCCESS] Response is valid JSON")
                    print(f"[DATA] Response type: {response_data.get('type', 'unknown')}")
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Response is not valid JSON: {e}")
                    print(f"Raw response: {response}")
                    
            except asyncio.TimeoutError:
                print("[TIMEOUT] No response received within timeout (expected for staging)")
            
            total_time = time.time() - start_time
            print(f"[STATS] Total test time: {total_time:.2f}s")
            
            # WebSocket health check
            print("[HEALTH] WebSocket connection still alive:", not websocket.closed)
            
    except ConnectionClosedError as e:
        print(f"[ERROR] WebSocket connection closed unexpectedly: {e}")
        print(f"Close code: {e.code}, Close reason: {e.reason}")
        return False
        
    except ConnectionClosedOK as e:
        print(f"[SUCCESS] WebSocket connection closed gracefully: {e}")
        return True
        
    except OSError as e:
        print(f"[ERROR] Network/OS error: {e}")
        return False
        
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("="*60)
    print("[SUCCESS] PHASE 1 WebSocket connectivity test completed")
    return True

async def test_websocket_1011_error_reproduction():
    """Test for WebSocket 1011 error reproduction (from issue analysis)"""
    
    staging_ws_url = "wss://api.staging.netrasystems.ai/ws"
    
    print(f"[1011] Testing WebSocket 1011 error reproduction...")
    
    try:
        async with websockets.connect(staging_ws_url, timeout=15) as websocket:
            
            # Test problematic agent state serialization scenarios
            problematic_states = [
                {"type": "agent_started", "state": "ENUM_VALUE_TEST"},
                {"type": "agent_thinking", "data": {"complex": {"nested": "object"}}},
                {"type": "tool_executing", "tool_data": None},  # Potential None serialization issue
                {"type": "agent_completed", "result": {"status": "undefined_enum"}},
            ]
            
            for i, state in enumerate(problematic_states):
                print(f"[TEST] Testing problematic state {i+1}: {state['type']}")
                try:
                    await websocket.send(json.dumps(state))
                    await asyncio.sleep(0.5)  # Brief pause
                except Exception as e:
                    print(f"[ERROR] Error sending state {i+1}: {e}")
                    
            # Check if WebSocket is still alive
            if not websocket.closed:
                print("[SUCCESS] WebSocket survived problematic state tests")
            else:
                print(f"[ERROR] WebSocket closed during test: code {websocket.close_code}")
                
    except Exception as e:
        print(f"[ERROR] WebSocket 1011 reproduction test failed: {e}")

async def main():
    """Main test execution"""
    print("[PHASE1] PHASE 1 WebSocket SSOT Validation - Staging GCP")
    print("[TASK] Execute WebSocket connectivity and JSON serialization tests")
    print("[GOAL] Identify fixable issues vs deeper remediation needs")
    print()
    
    # Test 1: Basic connectivity
    basic_result = await test_staging_websocket_basic_connectivity()
    
    print()
    
    # Test 2: 1011 error reproduction
    await test_websocket_1011_error_reproduction()
    
    print()
    print("="*60)
    print("[SUMMARY] PHASE 1 WebSocket SSOT Validation Summary")
    print(f"[RESULT] Basic connectivity: {'PASS' if basic_result else 'FAIL'}")
    print("[NEXT] Next steps: Analyze results for business impact")

if __name__ == "__main__":
    asyncio.run(main())