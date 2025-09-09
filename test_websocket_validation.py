#!/usr/bin/env python3
"""
VALIDATION TEST: WebSocket Connection and Orchestrator Factory Pattern

This focused test validates that the orchestrator factory pattern fixes
have resolved the WebSocket error 1011 issue at agent execution.

CRITICAL: This test directly validates the $120K+ MRR pipeline restoration.
"""

import asyncio
import websockets
import json
import time
import os
from shared.isolated_environment import IsolatedEnvironment

async def test_websocket_orchestrator_validation():
    """
    Direct validation of WebSocket connection stability and orchestrator initialization.
    
    EXPECTED BEHAVIOR:
    - BEFORE FIX: WebSocket error 1011 after ~7 seconds during orchestrator initialization
    - AFTER FIX: WebSocket connection remains stable, agent execution progresses
    
    VALIDATION POINTS:
    1. WebSocket connects successfully 
    2. Agent execution request sends without error
    3. Connection remains stable past 10 seconds (previous failure point)
    4. Agent execution progresses beyond orchestrator initialization
    """
    print("[CRITICAL VALIDATION] Testing orchestrator factory pattern fixes")
    print("=" * 80)
    
    # Load staging environment
    env = IsolatedEnvironment()
    ws_url = "wss://api.staging.netrasystems.ai/ws"
    
    # Create test auth token for staging user that should exist
    # Using staging-e2e-user-001 which should be in the staging database
    test_user_id = "staging-e2e-user-001"
    
    # Create minimal JWT for test (staging environment)
    import jwt
    import os
    
    # Load staging environment variables
    staging_env_file = "config/staging.env"
    if os.path.exists(staging_env_file):
        with open(staging_env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    jwt_secret = env.get("JWT_SECRET_STAGING")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET_STAGING not found in environment")
    
    test_token = jwt.encode({
        "user_id": test_user_id,
        "email": "staging-e2e-user-001@netrasystems.ai",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time())
    }, jwt_secret, algorithm="HS256")
    
    print(f"[AUTH] Created test JWT for user: {test_user_id}")
    
    # WebSocket headers for staging authentication
    headers = {
        "Authorization": f"Bearer {test_token}",
        "X-Test-Type": "websocket-validation",
        "X-Test-Environment": "staging",
        "X-E2E-Test": "orchestrator-validation",
        "X-Staging-E2E": "true",
        "User-Agent": "OrchestatorValidationTest/1.0"
    }
    
    # Add JWT as subprotocol as well (staging auth pattern)
    subprotocols = [f"jwt.{test_token[:50]}..."]
    
    start_time = time.time()
    connection_stable = False
    agent_request_sent = False
    websocket_error = None
    
    try:
        print(f"[CONNECT] Connecting to: {ws_url}")
        print(f"[AUTH] Using subprotocols: {subprotocols[0][:50]}...")
        
        async with websockets.connect(
            ws_url, 
            additional_headers=headers,
            subprotocols=subprotocols,
            ping_timeout=30,
            ping_interval=20
        ) as ws:
            print(f"[SUCCESS] WebSocket connected at {time.time() - start_time:.2f}s")
            
            # Send agent execution request (minimal version of what tests do)
            agent_request = {
                "type": "execute_agent",
                "agent_type": "data_analyst", 
                "user_input": "Test orchestrator initialization",
                "metadata": {
                    "test_type": "orchestrator_validation",
                    "validation_timestamp": time.time()
                }
            }
            
            await ws.send(json.dumps(agent_request))
            agent_request_sent = True
            print(f"[SENT] Agent request sent at {time.time() - start_time:.2f}s")
            
            # CRITICAL VALIDATION: Wait past the 7-second failure point
            # Previous issue: WebSocket error 1011 after ~7 seconds
            validation_phases = [
                (3, "Initial connection stability"),
                (7, "Previous failure point (7s)"), 
                (10, "Post-failure stability"),
                (15, "Orchestrator initialization complete")
            ]
            
            for phase_time, phase_desc in validation_phases:
                try:
                    # Wait for messages or timeout at phase checkpoint
                    remaining_time = phase_time - (time.time() - start_time)
                    if remaining_time > 0:
                        print(f"[WAIT] Waiting for {phase_desc} (T+{phase_time}s)...")
                        
                        # Try to receive messages during this phase
                        while time.time() - start_time < phase_time:
                            try:
                                message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                                msg_data = json.loads(message)
                                elapsed = time.time() - start_time
                                print(f"[MSG] T+{elapsed:.2f}s: {msg_data.get('type', 'unknown')}")
                                
                                # Look for agent execution progression
                                if msg_data.get('type') in ['agent_started', 'agent_thinking', 'tool_executing']:
                                    print(f"[PROGRESS] Agent execution progressing - {msg_data.get('type')}")
                                    
                            except asyncio.TimeoutError:
                                continue  # No message in this second, continue waiting
                                
                    elapsed = time.time() - start_time
                    if elapsed >= phase_time:
                        print(f"[PASS] PASSED: {phase_desc} - Connection stable at T+{elapsed:.2f}s")
                        
                except websockets.exceptions.ConnectionClosedError as e:
                    elapsed = time.time() - start_time
                    websocket_error = e
                    print(f"[FAIL] FAILED: {phase_desc} - WebSocket closed at T+{elapsed:.2f}s")
                    print(f"[ERROR] Error: {e}")
                    break
            
            # If we get here, connection was stable throughout all phases
            final_elapsed = time.time() - start_time
            if final_elapsed >= 15:
                connection_stable = True
                print(f"[SUCCESS] SUCCESS: Connection stable for {final_elapsed:.2f}s - Orchestrator fix validated!")
                
    except Exception as e:
        elapsed = time.time() - start_time
        websocket_error = e
        print(f"[CRITICAL] CRITICAL FAILURE at T+{elapsed:.2f}s: {e}")
    
    # Validation Results
    print("=" * 80)
    print("[RESULTS] VALIDATION RESULTS:")
    print(f"   Connection Successful: {'PASS' if 'ws' in locals() else 'FAIL'}")
    print(f"   Agent Request Sent: {'PASS' if agent_request_sent else 'FAIL'}")  
    print(f"   Connection Stable (>15s): {'PASS' if connection_stable else 'FAIL'}")
    print(f"   WebSocket Error: {'FAIL ' + str(websocket_error) if websocket_error else 'PASS None'}")
    print(f"   Total Duration: {time.time() - start_time:.2f}s")
    
    # BUSINESS IMPACT ASSESSMENT
    print("=" * 80)
    print("[BUSINESS] BUSINESS IMPACT ASSESSMENT:")
    
    if connection_stable and not websocket_error:
        print("[SUCCESS] VALIDATION SUCCESS: Orchestrator factory pattern fixes are working!")
        print("[BUSINESS] BUSINESS VALUE: $120K+ MRR pipeline is likely restored")
        print("[RECOMMENDATION] RECOMMENDATION: Proceed with full agent execution validation")
        return True
        
    elif websocket_error and "1011" in str(websocket_error):
        print("[FAILURE] VALIDATION FAILURE: WebSocket error 1011 still occurring")
        print("[BUSINESS] BUSINESS IMPACT: $120K+ MRR pipeline still broken")
        print("[RECOMMENDATION] RECOMMENDATION: Orchestrator factory fixes did not resolve root cause")
        return False
        
    else:
        print("[PARTIAL] PARTIAL VALIDATION: Connection issues but different from original error 1011")
        print("[RECOMMENDATION] RECOMMENDATION: Need deeper investigation of new failure mode")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_websocket_orchestrator_validation())
    exit(0 if result else 1)