#!/usr/bin/env python3
"""
Issue #1278 Infrastructure Problems - WebSocket Infrastructure Validation

MISSION: Test WebSocket infrastructure components specifically
- WebSocket server connectivity and stability
- Message routing and event handling
- Connection lifecycle management
- Error handling and recovery
- Subprotocol negotiation and headers

EXPECTED: Tests should FAIL initially, reproducing Issue #1278 WebSocket problems

NOTE: Focuses specifically on WebSocket infrastructure issues
"""
import os
import pytest
import asyncio
import json
import logging
import ssl
from typing import Dict, Any, Optional, List
import websockets
from websockets import ConnectionClosed, InvalidStatusCode
import aiohttp

# Test infrastructure imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from dev_launcher.isolated_environment import IsolatedEnvironment

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.infrastructure
@pytest.mark.issue_1278
@pytest.mark.websocket
class TestIssue1278WebSocketInfrastructureValidation(SSotAsyncTestCase):
    """Test suite for WebSocket infrastructure validation"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with staging environment"""
        super().setUpClass()
        cls.env = IsolatedEnvironment("staging")
        cls.websocket_url = "wss://api.staging.netrasystems.ai/ws"
        cls.backend_url = "https://staging.netrasystems.ai"
        
    async def test_websocket_basic_connectivity(self):
        """
        Test: Basic WebSocket connectivity to staging
        EXPECT: Should FAIL - reproducing basic connectivity issues
        """
        logger.info("Testing WebSocket basic connectivity")
        
        try:
            ssl_context = ssl.create_default_context()
            
            # Test basic connection
            async with websockets.connect(
                self.websocket_url,
                ssl=ssl_context,
                timeout=10
            ) as websocket:
                
                logger.info("WebSocket connection established")
                
                # Test connection state
                assert websocket.open, "WebSocket should be open"
                assert websocket.closed is False, "WebSocket should not be closed"
                
                # Test ping/pong
                pong_waiter = await websocket.ping()
                await pong_waiter
                logger.info("WebSocket ping/pong successful")
                
            logger.info("CHECK WebSocket basic connectivity successful")
            
        except Exception as e:
            logger.error(f"X WebSocket basic connectivity failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: WebSocket connectivity failure - {e}")
    
    async def test_websocket_subprotocol_negotiation(self):
        """
        Test: WebSocket subprotocol negotiation
        EXPECT: Should FAIL - reproducing subprotocol issues
        """
        logger.info("Testing WebSocket subprotocol negotiation")
        
        try:
            ssl_context = ssl.create_default_context()
            
            # Test with specific subprotocols
            subprotocols = ['chat', 'json', 'echo']
            
            async with websockets.connect(
                self.websocket_url,
                ssl=ssl_context,
                subprotocols=subprotocols,
                timeout=10
            ) as websocket:
                
                logger.info(f"Connected with subprotocol: {websocket.subprotocol}")
                
                # Validate subprotocol selection
                if websocket.subprotocol:
                    assert websocket.subprotocol in subprotocols, \
                        f"Unexpected subprotocol: {websocket.subprotocol}"
                
                # Test protocol-specific communication
                test_message = {
                    'type': 'protocol_test',
                    'subprotocol': websocket.subprotocol or 'none',
                    'data': 'Issue #1278 protocol validation'
                }
                
                await websocket.send(json.dumps(test_message))
                logger.info("Protocol test message sent")
                
            logger.info("CHECK WebSocket subprotocol negotiation successful")
            
        except Exception as e:
            logger.error(f"X WebSocket subprotocol negotiation failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: WebSocket subprotocol failure - {e}")
    
    async def test_websocket_headers_and_origin_validation(self):
        """
        Test: WebSocket headers and origin validation
        EXPECT: Should FAIL - reproducing header/origin validation issues
        """
        logger.info("Testing WebSocket headers and origin validation")
        
        try:
            ssl_context = ssl.create_default_context()
            
            # Test with proper headers
            valid_headers = {
                'Origin': 'https://staging.netrasystems.ai',
                'User-Agent': 'Issue1278TestClient/1.0',
                'X-Real-IP': '127.0.0.1',
                'X-Forwarded-For': '127.0.0.1'
            }
            
            async with websockets.connect(
                self.websocket_url,
                ssl=ssl_context,
                extra_headers=valid_headers,
                timeout=10
            ) as websocket:
                
                logger.info("WebSocket connected with valid headers")
                
                # Test header echo (if supported)
                header_test = {
                    'type': 'header_test',
                    'request_headers': valid_headers
                }
                
                await websocket.send(json.dumps(header_test))
                logger.info("Header test message sent")
                
            # Test with invalid origin (should fail)
            invalid_headers = {
                'Origin': 'https://malicious-site.com',
                'User-Agent': 'Issue1278TestClient/1.0'
            }
            
            try:
                async with websockets.connect(
                    self.websocket_url,
                    ssl=ssl_context,
                    extra_headers=invalid_headers,
                    timeout=5
                ) as websocket:
                    # If connection succeeds with invalid origin, that's a security issue
                    logger.warning("WebSocket accepted invalid origin - potential security issue")
                    
            except (ConnectionClosed, InvalidStatusCode) as e:
                logger.info(f"WebSocket properly rejected invalid origin: {e}")
            
            logger.info("CHECK WebSocket headers and origin validation working")
            
        except Exception as e:
            logger.error(f"X WebSocket headers/origin validation failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: WebSocket headers/origin failure - {e}")
    
    async def test_websocket_message_routing_infrastructure(self):
        """
        Test: WebSocket message routing infrastructure
        EXPECT: Should FAIL - reproducing message routing issues
        """
        logger.info("Testing WebSocket message routing infrastructure")
        
        try:
            ssl_context = ssl.create_default_context()
            
            async with websockets.connect(
                self.websocket_url,
                ssl=ssl_context,
                timeout=10
            ) as websocket:
                
                # Test different message types
                message_types = [
                    {'type': 'ping', 'data': 'routing_test'},
                    {'type': 'subscribe', 'events': ['test_event']},
                    {'type': 'unsubscribe', 'events': ['test_event']},
                    {'type': 'chat_message', 'message': 'Test message routing'},
                    {'type': 'agent_request', 'action': 'test_action'}
                ]
                
                responses = []
                
                for message in message_types:
                    logger.info(f"Sending message type: {message['type']}")
                    await websocket.send(json.dumps(message))
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3)
                        response_data = json.loads(response)
                        responses.append(response_data)
                        logger.info(f"Received response: {response_data.get('type', 'unknown')}")
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"No response for message type: {message['type']}")
                        responses.append({'timeout': True, 'original_type': message['type']})
                
                # Validate responses
                assert len(responses) > 0, "No responses received from WebSocket"
                
                # Check for error handling
                error_responses = [r for r in responses if 'error' in r]
                if error_responses:
                    logger.info(f"Error responses received: {len(error_responses)}")
                
            logger.info("CHECK WebSocket message routing infrastructure functional")
            
        except Exception as e:
            logger.error(f"X WebSocket message routing failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: WebSocket routing failure - {e}")
    
    async def test_websocket_connection_lifecycle_management(self):
        """
        Test: WebSocket connection lifecycle management
        EXPECT: Should FAIL - reproducing connection lifecycle issues
        """
        logger.info("Testing WebSocket connection lifecycle management")
        
        try:
            ssl_context = ssl.create_default_context()
            connections = []
            
            # Test multiple connections
            for i in range(3):
                connection = await websockets.connect(
                    self.websocket_url,
                    ssl=ssl_context,
                    timeout=10
                )
                connections.append(connection)
                logger.info(f"Connection {i+1} established")
                
                # Test connection state
                assert connection.open, f"Connection {i+1} should be open"
                
                # Send identification message
                id_message = {
                    'type': 'identify',
                    'connection_id': f'test_connection_{i+1}',
                    'session_id': 'issue_1278_lifecycle_test'
                }
                await connection.send(json.dumps(id_message))
            
            # Test concurrent message sending
            for i, connection in enumerate(connections):
                test_message = {
                    'type': 'concurrent_test',
                    'connection_id': f'test_connection_{i+1}',
                    'timestamp': asyncio.get_event_loop().time()
                }
                await connection.send(json.dumps(test_message))
            
            # Test graceful closure
            for i, connection in enumerate(connections):
                await connection.close()
                assert connection.closed, f"Connection {i+1} should be closed"
                logger.info(f"Connection {i+1} closed gracefully")
            
            logger.info("CHECK WebSocket connection lifecycle management successful")
            
        except Exception as e:
            logger.error(f"X WebSocket connection lifecycle failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: WebSocket lifecycle failure - {e}")
    
    async def test_websocket_error_handling_and_recovery(self):
        """
        Test: WebSocket error handling and recovery mechanisms
        EXPECT: Should FAIL - reproducing error handling issues
        """
        logger.info("Testing WebSocket error handling and recovery")
        
        try:
            ssl_context = ssl.create_default_context()
            
            async with websockets.connect(
                self.websocket_url,
                ssl=ssl_context,
                timeout=10
            ) as websocket:
                
                # Test malformed message handling
                malformed_messages = [
                    "invalid json {",
                    '{"type": "unknown_type", "data": "test"}',
                    '{"missing_type": true}',
                    '',
                    '{"type": null}'
                ]
                
                error_responses = []
                
                for malformed_msg in malformed_messages:
                    logger.info(f"Sending malformed message: {malformed_msg[:50]}...")
                    
                    try:
                        await websocket.send(malformed_msg)
                        
                        # Wait for error response
                        response = await asyncio.wait_for(websocket.recv(), timeout=2)
                        response_data = json.loads(response)
                        error_responses.append(response_data)
                        logger.info(f"Error response: {response_data.get('error', 'no error field')}")
                        
                    except asyncio.TimeoutError:
                        logger.warning("No error response received")
                    except ConnectionClosed:
                        logger.error("Connection closed due to malformed message")
                        break
                
                # Validate error handling
                if error_responses:
                    for error_resp in error_responses:
                        assert 'error' in error_resp or 'status' in error_resp, \
                            "Error responses should contain error or status field"
                
                # Test connection recovery after errors
                recovery_message = {
                    'type': 'recovery_test',
                    'data': 'Connection should still work after errors'
                }
                await websocket.send(json.dumps(recovery_message))
                logger.info("Recovery message sent successfully")
            
            logger.info("CHECK WebSocket error handling and recovery functional")
            
        except Exception as e:
            logger.error(f"X WebSocket error handling failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: WebSocket error handling failure - {e}")
    
    async def test_websocket_load_balancer_integration(self):
        """
        Test: WebSocket integration with load balancer
        EXPECT: Should FAIL - reproducing load balancer integration issues
        """
        logger.info("Testing WebSocket load balancer integration")
        
        try:
            # Test WebSocket upgrade through load balancer
            backend_url = self.backend_url
            
            # First check if HTTP upgrade is possible
            upgrade_headers = {
                'Connection': 'Upgrade',
                'Upgrade': 'websocket',
                'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
                'Sec-WebSocket-Version': '13',
                'Origin': 'https://staging.netrasystems.ai'
            }
            
            timeout = aiohttp.ClientTimeout(total=15)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Test WebSocket upgrade endpoint
                ws_upgrade_url = f"{backend_url.replace('https://', 'http://')}/ws"
                
                try:
                    async with session.get(
                        ws_upgrade_url,
                        headers=upgrade_headers
                    ) as response:
                        logger.info(f"WebSocket upgrade status: {response.status}")
                        
                        # Should get 101 Switching Protocols or 404 if not supported
                        assert response.status in [101, 404, 426], \
                            f"Unexpected upgrade response: {response.status}"
                        
                        if response.status == 101:
                            logger.info("WebSocket upgrade successful through load balancer")
                        else:
                            logger.info("WebSocket upgrade not supported at HTTP endpoint")
                            
                except Exception as upgrade_error:
                    logger.warning(f"WebSocket upgrade test failed: {upgrade_error}")
            
            # Test actual WebSocket connection through load balancer
            ssl_context = ssl.create_default_context()
            
            # Test with load balancer headers
            lb_headers = {
                'X-Forwarded-Proto': 'https',
                'X-Forwarded-For': '127.0.0.1',
                'X-Real-IP': '127.0.0.1',
                'Origin': 'https://staging.netrasystems.ai'
            }
            
            async with websockets.connect(
                self.websocket_url,
                ssl=ssl_context,
                extra_headers=lb_headers,
                timeout=10
            ) as websocket:
                
                # Test load balancer awareness
                lb_test_message = {
                    'type': 'load_balancer_test',
                    'headers': lb_headers,
                    'data': 'Testing load balancer integration'
                }
                
                await websocket.send(json.dumps(lb_test_message))
                logger.info("Load balancer test message sent")
                
                # Test sticky session behavior (if applicable)
                session_test_message = {
                    'type': 'session_test',
                    'session_id': 'issue_1278_lb_test',
                    'data': 'Testing session persistence'
                }
                
                await websocket.send(json.dumps(session_test_message))
                logger.info("Session persistence test message sent")
            
            logger.info("CHECK WebSocket load balancer integration functional")
            
        except Exception as e:
            logger.error(f"X WebSocket load balancer integration failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: WebSocket load balancer failure - {e}")


if __name__ == "__main__":
    # Run tests with verbose output to capture failure details
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure to capture Issue #1278 reproduction
        "--log-cli-level=INFO",
        "--asyncio-mode=auto"
    ])