#!/usr/bin/env python3
"""
Debug WebSocket 1011 Analysis - P0 Golden Path Investigation
Mission: Analyze exact WebSocket message processing errors on staging.
"""

import asyncio
import json
import os
import time
import sys
from typing import Dict, Optional

# Add project root to path for imports
sys.path.insert(0, '/Users/anthony/Desktop/netra-apex')

from tests.e2e.staging_test_config import get_staging_config, StagingConfig
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig

try:
    import websockets
except ImportError:
    print("[ERROR] websockets library not available")
    sys.exit(1)


class WebSocket1011Analyzer:
    """Analyzes WebSocket 1011 errors on staging environment"""
    
    def __init__(self):
        self.config = get_staging_config()
        self.auth_token = None
        self.websocket_headers = {}
        
    def setup_authentication(self):
        """Set up proper staging authentication"""
        try:
            print("[INFO] Setting up staging authentication...")
            
            # Set up environment for staging
            env = IsolatedEnvironment()
            env.set('ENVIRONMENT', 'staging')
            
            # Load staging JWT secret
            config_path = '/Users/anthony/Desktop/netra-apex/config/staging.env'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            if key == 'JWT_SECRET_STAGING':
                                env.set('JWT_SECRET_KEY', value)
                                print(f"[SUCCESS] Loaded JWT_SECRET_STAGING from staging config")
                                break
            
            # Create E2E auth helper for staging
            staging_config = E2EAuthConfig.for_staging()
            auth_helper = E2EAuthHelper(config=staging_config, environment="staging")
            
            # Use existing staging test user
            test_user = {
                "user_id": "staging-e2e-user-001",
                "email": "staging_debug@test.netrasystems.ai"
            }
            
            print(f"[AUTH] Creating JWT for user: {test_user['user_id']}")
            
            # Create JWT token
            self.auth_token = auth_helper.create_test_jwt_token(
                user_id=test_user["user_id"],
                email=test_user["email"],
                permissions=["read", "write", "execute"],
                exp_minutes=60
            )
            
            if self.auth_token:
                print(f"[SUCCESS] Created staging JWT token")
                print(f"[TOKEN_PREVIEW] {self.auth_token[:20]}...")
                
                # Set up WebSocket headers with authentication
                self.websocket_headers = {
                    'Authorization': f'Bearer {self.auth_token}',
                    'X-Test-Type': 'E2E',
                    'X-Test-Environment': 'staging',
                    'X-Test-Priority': 'P0-Golden-Path',
                    'User-Agent': 'WebSocket-1011-Analyzer/1.0'
                }
                
                # Also add as subprotocol (staging WebSocket expects this)
                self.websocket_subprotocols = [f'jwt.{self.auth_token}']
                
                return True
            else:
                print("[ERROR] Failed to create JWT token")
                return False
                
        except Exception as e:
            print(f"[ERROR] Authentication setup failed: {e}")
            return False
    
    async def test_websocket_message_processing(self):
        """Test WebSocket message processing layer for 1011 errors"""
        
        if not self.auth_token:
            print("[ERROR] No authentication token available")
            return
            
        print(f"[INFO] Testing WebSocket message processing on: {self.config.websocket_url}")
        
        try:
            # Connect with proper authentication
            async with websockets.connect(
                self.config.websocket_url,
                additional_headers=self.websocket_headers,
                subprotocols=self.websocket_subprotocols
            ) as websocket:
                print("[SUCCESS] WebSocket connected with authentication")
                
                # Test different message types that could trigger 1011 errors
                test_messages = [
                    # Basic user message
                    {
                        "type": "user_message",
                        "content": "Hello, test message for 1011 analysis",
                        "thread_id": "test-thread-001"
                    },
                    
                    # Agent execution request
                    {
                        "type": "start_agent",
                        "agent_type": "supervisor",
                        "message": "Analyze system performance",
                        "user_id": "staging-e2e-user-001"
                    },
                    
                    # Tool execution message
                    {
                        "type": "tool_execute",
                        "tool": "system_info",
                        "parameters": {"query": "status"}
                    },
                    
                    # Chat completion request
                    {
                        "type": "chat_completion",
                        "messages": [{"role": "user", "content": "Test completion"}],
                        "stream": False
                    }
                ]
                
                for i, test_message in enumerate(test_messages, 1):
                    print(f"\n[TEST {i}] Sending message type: {test_message['type']}")
                    print(f"[MESSAGE] {json.dumps(test_message, indent=2)}")
                    
                    try:
                        # Send the message
                        await websocket.send(json.dumps(test_message))
                        print(f"[SENT] Message sent successfully")
                        
                        # Wait for response and analyze
                        response_count = 0
                        start_time = time.time()
                        
                        while response_count < 5 and (time.time() - start_time) < 10:
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                                response_count += 1
                                
                                print(f"[RESPONSE {response_count}] Received ({len(response)} bytes)")
                                
                                try:
                                    data = json.loads(response)
                                    print(f"[JSON] {json.dumps(data, indent=2)}")
                                    
                                    # Analyze for 1011 errors
                                    self.analyze_response_for_1011(data, test_message['type'])
                                    
                                except json.JSONDecodeError:
                                    print(f"[RAW] {response}")
                                    
                            except asyncio.TimeoutError:
                                print(f"[TIMEOUT] No more responses for message {i}")
                                break
                            except websockets.exceptions.ConnectionClosedError as e:
                                print(f"[CONNECTION_CLOSED] Code: {e.code}, Reason: {e.reason}")
                                if e.code == 1011:
                                    print("[CRITICAL] Found 1011 WebSocket connection closure!")
                                    self.analyze_1011_error(e, test_message)
                                return
                                
                        print(f"[COMPLETE] Test {i} completed with {response_count} responses")
                        
                        # Brief pause between tests
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        print(f"[ERROR] Message {i} failed: {e}")
                        if "1011" in str(e):
                            print("[CRITICAL] 1011 error detected in exception!")
                            self.analyze_1011_error(e, test_message)
                
                print("\n[COMPLETE] All message processing tests completed")
                
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"[CONNECTION_CLOSED] Code: {e.code}, Reason: {e.reason}")
            if e.code == 1011:
                print("[CRITICAL] Found 1011 WebSocket connection closure during initial connection!")
                self.analyze_1011_error(e, None)
        except Exception as e:
            print(f"[ERROR] WebSocket connection failed: {e}")
            if "1011" in str(e):
                print("[CRITICAL] 1011 error detected in connection!")
    
    def analyze_response_for_1011(self, data: Dict, message_type: str):
        """Analyze response data for 1011 error patterns"""
        
        # Check for direct 1011 error codes
        if isinstance(data, dict):
            if data.get('error_code') == 1011:
                print("[CRITICAL] Found 1011 error code in response!")
                print(f"[ERROR_DETAILS] {json.dumps(data, indent=2)}")
                
            if 'error' in data and isinstance(data['error'], dict):
                if data['error'].get('code') == 1011:
                    print("[CRITICAL] Found 1011 error in error object!")
                    print(f"[ERROR_DETAILS] {json.dumps(data['error'], indent=2)}")
                    
            # Check for 1011 in any string values
            if '1011' in json.dumps(data):
                print("[WARNING] Found '1011' in response JSON")
                
            # Check for internal server error patterns
            error_msg = data.get('error_message', '')
            if 'internal server error' in error_msg.lower():
                print("[WARNING] Found 'internal server error' in response")
                
            # Check for database connectivity issues (root cause)
            if 'database connectivity failure' in error_msg.lower():
                print("[DATABASE] Database connectivity failure detected - likely root cause")
                
    def analyze_1011_error(self, error, test_message: Optional[Dict]):
        """Detailed analysis of 1011 errors"""
        print("\n" + "="*60)
        print("CRITICAL: 1011 INTERNAL SERVER ERROR ANALYSIS")
        print("="*60)
        
        print(f"Error Type: {type(error)}")
        print(f"Error Details: {error}")
        
        if hasattr(error, 'code'):
            print(f"WebSocket Close Code: {error.code}")
        if hasattr(error, 'reason'):
            print(f"WebSocket Close Reason: {error.reason}")
            
        if test_message:
            print(f"Message Type that triggered error: {test_message.get('type', 'unknown')}")
            print(f"Message Content: {json.dumps(test_message, indent=2)}")
        else:
            print("Error occurred during connection establishment")
            
        # Analysis recommendations
        print("\nANALYSIS RECOMMENDATIONS:")
        print("1. Check server-side logs for internal server errors")
        print("2. Verify database connectivity on staging environment")
        print("3. Check message routing handlers for specific message types")
        print("4. Validate authentication and user permissions")
        print("5. Review WebSocket connection pooling and resource limits")
        
        print("="*60)


async def main():
    """Main analysis function"""
    print("WebSocket 1011 Error Analysis - P0 Golden Path Investigation")
    print("=" * 60)
    
    analyzer = WebSocket1011Analyzer()
    
    # Set up authentication
    if not analyzer.setup_authentication():
        print("[ERROR] Authentication setup failed - cannot proceed")
        return
        
    # Test message processing layer
    await analyzer.test_websocket_message_processing()
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())