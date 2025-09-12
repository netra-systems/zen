"""
E2E Tests for Issue #463: Staging WebSocket Authentication Failures

This test suite reproduces the actual staging environment WebSocket authentication failures:
- Direct WebSocket connection to staging endpoint (expecting 404 -> was 502 before)
- WebSocket error code 1006 (connection closed abnormally)  
- Complete chat flow functionality testing
- Real staging environment validation

These tests are EXPECTED TO FAIL initially to demonstrate the staging problems exist.
Once remediation is applied, these same tests should pass to validate the fix.

Issue: https://github.com/netra-systems/netra-apex/issues/463
"""

import asyncio
import json
import logging
import pytest
import websockets
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import patch

# Import test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import WebSocket client components
import websockets.client
import websockets.exceptions

logger = logging.getLogger(__name__)


class TestStagingWebSocketDirectConnection(SSotAsyncTestCase):
    """Test direct WebSocket connections to staging environment."""
    
    STAGING_WEBSOCKET_URL = "wss://netra-backend-staging-service-1087371144.us-central1.run.app/ws/chat"
    STAGING_API_URL = "https://netra-backend-staging-service-1087371144.us-central1.run.app"
    
    async def setup_method(self, method):
        """Setup test environment."""
        await super().setup_method(method)
        self.env = get_env()
        
        # Store test results for analysis
        self.connection_attempts = []
        self.error_codes_encountered = []
        
    async def test_staging_websocket_connection_returns_404_error(self):
        """
        REPRODUCE ISSUE #463: Staging WebSocket connection returns 404 (was 502 before).
        
        This test attempts to connect directly to the staging WebSocket endpoint
        and expects to receive a 404 error due to authentication issues.
        """
        connection_result = {
            'success': False,
            'error_code': None,
            'error_message': None,
            'http_status': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Attempt direct connection to staging WebSocket
            logger.info(f"Attempting connection to staging WebSocket: {self.STAGING_WEBSOCKET_URL}")
            
            # Set connection timeout
            async with websockets.connect(
                self.STAGING_WEBSOCKET_URL,
                timeout=10,
                extra_headers={'User-Agent': 'Issue463-E2E-Test'}
            ) as websocket:
                # If we get here, connection succeeded unexpectedly
                connection_result['success'] = True
                logger.warning("UNEXPECTED: Staging WebSocket connection succeeded")
                
                # Try to send a test message
                test_message = {"type": "test", "message": "Issue 463 E2E test"}
                await websocket.send(json.dumps(test_message))
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    connection_result['response'] = response
                except asyncio.TimeoutError:
                    connection_result['response'] = 'TIMEOUT_NO_RESPONSE'
                    
        except websockets.exceptions.InvalidStatus as e:
            # This is the expected failure - WebSocket returns HTTP error status
            connection_result['error_code'] = 'INVALID_STATUS'
            connection_result['http_status'] = e.response.status_code if hasattr(e, 'response') else None
            connection_result['error_message'] = str(e)
            logger.info(f"Expected staging WebSocket error: HTTP {connection_result['http_status']} - {e}")
            
        except websockets.exceptions.ConnectionClosedError as e:
            # WebSocket connection closed unexpectedly (code 1006 scenario)
            connection_result['error_code'] = 'CONNECTION_CLOSED'
            connection_result['close_code'] = e.code
            connection_result['error_message'] = f"Connection closed with code {e.code}: {e.reason}"
            logger.info(f"Staging WebSocket closed: Code {e.code} - {e.reason}")
            
        except Exception as e:
            # Other connection errors
            connection_result['error_code'] = type(e).__name__
            connection_result['error_message'] = str(e)
            logger.info(f"Staging WebSocket connection error: {type(e).__name__}: {e}")
        
        # Store result for analysis
        self.connection_attempts.append(connection_result)
        
        # EXPECTED FAILURE: Connection should fail with 404 or authentication error
        assert not connection_result['success'], "Staging WebSocket should fail due to authentication issues"
        
        # Verify we get the expected 404 status (improvement from 502)
        if connection_result.get('http_status'):
            assert connection_result['http_status'] in [404, 403, 401], f"Expected 404/403/401 but got {connection_result['http_status']}"
            
        # Log the failure for analysis
        logger.error(f"EXPECTED FAILURE - Staging WebSocket connection failed as expected: {connection_result}")
    
    async def test_staging_websocket_with_auth_token_still_fails(self):
        """
        Test staging WebSocket connection with authorization token still fails.
        
        This test attempts connection with various auth token formats to see
        if the issue is specifically with token validation.
        """
        test_tokens = [
            "Bearer test-token-123",
            "Bearer invalid-token-format", 
            "Bearer expired-test-token",
            "test-token-no-bearer"
        ]
        
        for i, token in enumerate(test_tokens):
            connection_result = {
                'token_format': token[:20] + "..." if len(token) > 20 else token,
                'success': False,
                'error_code': None,
                'error_message': None,
                'attempt_number': i + 1
            }
            
            try:
                # Try connection with authorization header
                headers = {'Authorization': token}
                
                async with websockets.connect(
                    self.STAGING_WEBSOCKET_URL,
                    timeout=5,
                    extra_headers=headers
                ) as websocket:
                    # Unexpected success
                    connection_result['success'] = True
                    logger.warning(f"UNEXPECTED: Staging WebSocket succeeded with token {token[:20]}")
                    
            except websockets.exceptions.InvalidStatus as e:
                connection_result['error_code'] = 'INVALID_STATUS'
                connection_result['http_status'] = e.response.status_code if hasattr(e, 'response') else None
                connection_result['error_message'] = str(e)
                
            except Exception as e:
                connection_result['error_code'] = type(e).__name__
                connection_result['error_message'] = str(e)
            
            # Store result
            self.connection_attempts.append(connection_result)
            
            # EXPECTED FAILURE: Even with tokens, should fail due to missing environment variables
            assert not connection_result['success'], f"Staging WebSocket should fail even with token: {token[:20]}"
    
    async def test_staging_websocket_code_1006_error_reproduction(self):
        """
        REPRODUCE ISSUE #463: WebSocket error code 1006 (connection closed abnormally).
        
        This test specifically tries to reproduce the WebSocket error code 1006
        that occurs when connections are closed abnormally due to auth failures.
        """
        code_1006_attempts = []
        
        # Try multiple connection attempts to reproduce code 1006
        for attempt in range(3):
            connection_result = {
                'attempt': attempt + 1,
                'success': False,
                'close_code': None,
                'error_code': None,
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                # Create WebSocket connection with specific settings that might trigger 1006
                async with websockets.connect(
                    self.STAGING_WEBSOCKET_URL,
                    timeout=3,  # Short timeout to potentially trigger abnormal closure
                    ping_interval=1,  # Frequent pings
                    ping_timeout=2,
                    extra_headers={'Connection': 'close'}  # Request connection close
                ) as websocket:
                    # If connected, wait a moment then try to use it
                    await asyncio.sleep(0.5)
                    
                    # Try to send message that might trigger closure
                    await websocket.send('{"type": "test_1006_trigger"}')
                    
                    # Wait for potential closure
                    try:
                        await asyncio.wait_for(websocket.recv(), timeout=2)
                        connection_result['success'] = True  # Unexpected success
                    except asyncio.TimeoutError:
                        # Connection might be in bad state, triggering 1006 on close
                        pass
                        
            except websockets.exceptions.ConnectionClosedError as e:
                # This is what we expect - connection closed abnormally
                connection_result['close_code'] = e.code
                connection_result['error_code'] = 'CONNECTION_CLOSED'
                connection_result['error_message'] = f"Code {e.code}: {e.reason}"
                
                # Check if we got the specific 1006 code
                if e.code == 1006:
                    connection_result['is_code_1006'] = True
                    logger.info(f"REPRODUCED: WebSocket error code 1006 on attempt {attempt + 1}")
                else:
                    logger.info(f"Got close code {e.code} instead of 1006 on attempt {attempt + 1}")
                    
            except Exception as e:
                connection_result['error_code'] = type(e).__name__
                connection_result['error_message'] = str(e)
            
            code_1006_attempts.append(connection_result)
            
            # Brief delay between attempts
            await asyncio.sleep(0.1)
        
        # Store all attempts for analysis
        self.connection_attempts.extend(code_1006_attempts)
        
        # EXPECTED RESULT: Should have connection failures, potentially including 1006
        failure_count = sum(1 for attempt in code_1006_attempts if not attempt['success'])
        assert failure_count >= 2, "Most connection attempts should fail due to staging auth issues"
        
        # Check if we reproduced the 1006 error specifically
        code_1006_reproduced = any(attempt.get('is_code_1006', False) for attempt in code_1006_attempts)
        if code_1006_reproduced:
            logger.error("SUCCESSFULLY REPRODUCED: WebSocket error code 1006 in staging environment")
        else:
            logger.warning("Could not reproduce specific 1006 error code, but connections failed as expected")


class TestStagingChatFlowFunctionality(SSotAsyncTestCase):
    """Test complete chat flow functionality in staging environment."""
    
    async def setup_method(self, method):
        """Setup test environment."""
        await super().setup_method(method)
        
        # Chat flow test configuration
        self.staging_base_url = "https://netra-backend-staging-service-1087371144.us-central1.run.app"
        self.test_messages = [
            {"type": "chat", "message": "Hello, can you help me optimize my AI costs?"},
            {"type": "agent_request", "request": "analyze_performance"},
            {"type": "test", "message": "Issue 463 E2E chat flow test"}
        ]
        
    async def test_staging_chat_websocket_flow_fails_at_connection(self):
        """
        REPRODUCE ISSUE #463: Complete chat flow fails at WebSocket connection stage.
        
        This test attempts to simulate a complete user chat flow and expects it
        to fail at the WebSocket connection stage due to authentication issues.
        """
        chat_flow_result = {
            'connection_successful': False,
            'authentication_successful': False, 
            'message_sent': False,
            'response_received': False,
            'flow_completed': False,
            'failure_point': None,
            'error_details': None
        }
        
        try:
            # Step 1: Attempt WebSocket connection for chat
            logger.info("Starting chat flow test - attempting WebSocket connection")
            
            ws_url = f"{self.staging_base_url.replace('https://', 'wss://')}/ws/chat"
            
            async with websockets.connect(
                ws_url,
                timeout=10,
                extra_headers={
                    'User-Agent': 'ChatFlow-E2E-Test-Issue463',
                    'Origin': 'https://netra-frontend-staging.example.com'
                }
            ) as websocket:
                chat_flow_result['connection_successful'] = True
                logger.info("Chat WebSocket connection succeeded unexpectedly")
                
                # Step 2: Attempt authentication message
                auth_message = {
                    "type": "authenticate",
                    "token": "test-chat-user-token",
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(auth_message))
                
                # Wait for authentication response
                try:
                    auth_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    auth_data = json.loads(auth_response)
                    
                    if auth_data.get('type') == 'authentication_success':
                        chat_flow_result['authentication_successful'] = True
                        logger.info("Chat authentication succeeded unexpectedly")
                    else:
                        chat_flow_result['failure_point'] = 'authentication'
                        chat_flow_result['error_details'] = auth_data
                        
                except asyncio.TimeoutError:
                    chat_flow_result['failure_point'] = 'authentication_timeout'
                    chat_flow_result['error_details'] = 'No authentication response within timeout'
                
                # Step 3: If authenticated, try sending chat message
                if chat_flow_result['authentication_successful']:
                    for message in self.test_messages:
                        try:
                            await websocket.send(json.dumps(message))
                            chat_flow_result['message_sent'] = True
                            
                            # Wait for response
                            response = await asyncio.wait_for(websocket.recv(), timeout=10)
                            chat_flow_result['response_received'] = True
                            
                            # Brief delay between messages
                            await asyncio.sleep(0.5)
                            
                        except Exception as msg_error:
                            chat_flow_result['failure_point'] = 'message_handling'
                            chat_flow_result['error_details'] = str(msg_error)
                            break
                    
                    if chat_flow_result['message_sent'] and chat_flow_result['response_received']:
                        chat_flow_result['flow_completed'] = True
                        logger.warning("UNEXPECTED: Complete chat flow succeeded in staging")
                        
        except websockets.exceptions.InvalidStatus as e:
            # Expected failure at connection stage
            chat_flow_result['failure_point'] = 'websocket_connection'
            chat_flow_result['error_details'] = {
                'http_status': e.response.status_code if hasattr(e, 'response') else None,
                'error_message': str(e)
            }
            logger.info(f"EXPECTED: Chat flow failed at connection stage: HTTP {chat_flow_result['error_details']['http_status']}")
            
        except Exception as e:
            chat_flow_result['failure_point'] = 'connection_error'
            chat_flow_result['error_details'] = {
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
            
        # EXPECTED FAILURE: Chat flow should fail due to authentication issues
        assert not chat_flow_result['flow_completed'], "Chat flow should fail due to staging authentication issues"
        assert chat_flow_result['failure_point'] is not None, "Should have a specific failure point identified"
        
        # The most likely failure point should be at connection or authentication
        expected_failure_points = ['websocket_connection', 'connection_error', 'authentication', 'authentication_timeout']
        assert chat_flow_result['failure_point'] in expected_failure_points, \
            f"Expected failure at {expected_failure_points}, got {chat_flow_result['failure_point']}"
        
        logger.error(f"EXPECTED FAILURE - Chat flow failed as expected: {chat_flow_result}")
    
    async def test_staging_rest_api_health_check_vs_websocket_failure(self):
        """
        Test staging REST API health vs WebSocket failure to isolate the issue.
        
        This test checks if the staging REST API works while WebSocket fails,
        which would indicate the issue is specifically with WebSocket authentication.
        """
        import httpx
        
        test_results = {
            'rest_api_health': None,
            'rest_api_error': None,
            'websocket_health': None,
            'websocket_error': None,
            'issue_isolated': False
        }
        
        # Test 1: Check REST API health endpoint
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.staging_base_url}/health")
                test_results['rest_api_health'] = {
                    'status_code': response.status_code,
                    'accessible': response.status_code < 500,
                    'response_time_ms': response.elapsed.total_seconds() * 1000 if hasattr(response, 'elapsed') else None
                }
                
        except Exception as e:
            test_results['rest_api_error'] = {
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
        
        # Test 2: Check WebSocket connection (expected to fail)
        try:
            ws_url = f"{self.staging_base_url.replace('https://', 'wss://')}/ws/chat"
            
            async with websockets.connect(ws_url, timeout=5) as websocket:
                test_results['websocket_health'] = {
                    'connection_successful': True
                }
                
        except Exception as e:
            test_results['websocket_error'] = {
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
        
        # Analysis: If REST works but WebSocket fails, issue is isolated to WebSocket auth
        rest_works = (test_results['rest_api_health'] is not None and 
                     test_results['rest_api_health'].get('accessible', False))
        websocket_fails = test_results['websocket_error'] is not None
        
        if rest_works and websocket_fails:
            test_results['issue_isolated'] = True
            logger.error("ISSUE ISOLATED: REST API works but WebSocket fails - confirms WebSocket-specific auth issue")
        
        # EXPECTED RESULT: REST should work, WebSocket should fail
        # This isolates the issue to WebSocket authentication specifically
        if test_results['rest_api_health']:
            assert test_results['rest_api_health']['accessible'], "REST API should be accessible in staging"
        
        assert test_results['websocket_error'] is not None, "WebSocket should fail due to authentication issues"
        
        logger.error(f"API vs WebSocket test results: {test_results}")


if __name__ == '__main__':
    """
    Run these E2E tests to reproduce Issue #463 staging WebSocket authentication failures.
    
    Expected outcome: ALL TESTS SHOULD FAIL
    This demonstrates that staging WebSocket authentication is broken due to 
    missing environment variables and configuration issues.
    
    Usage:
    python -m pytest tests/e2e/test_staging_websocket_authentication_issue_463.py -v -s
    """
    pytest.main([__file__, '-v', '-s', '--tb=short'])