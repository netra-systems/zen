"""
E2E Staging Tests for Issue #1181 Golden Path Message Routing
============================================================

Business Value Justification:
- Segment: Platform/Golden Path Protection
- Business Goal: $500K+ ARR Chat Functionality Validation
- Value Impact: Ensures MessageRouter consolidation maintains Golden Path user flow
- Strategic Impact: Validates end-to-end message routing in staging environment

CRITICAL GOLDEN PATH VALIDATION:
Issue #1181 MessageRouter consolidation must not break the Golden Path user flow
that generates 90% of platform business value. These E2E tests validate that
message routing works correctly in the staging environment with real services.

Tests verify complete user journey: login → agent request → WebSocket events → AI response,
ensuring the consolidated MessageRouter maintains the $500K+ ARR chat functionality.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List
import pytest
import websockets
import requests
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class Issue1181GoldenPathMessageRoutingStagingE2ETests(SSotAsyncTestCase):
    """E2E staging tests for Golden Path message routing validation."""
    
    @classmethod
    def setUpClass(cls):
        """Set up E2E staging test environment."""
        super().setUpClass()
        
        # Staging environment configuration
        cls.staging_base_url = "https://backend.staging.netrasystems.ai"
        cls.staging_ws_url = "wss://backend.staging.netrasystems.ai/ws"
        cls.staging_auth_url = "https://auth.staging.netrasystems.ai"
        
        # Test user credentials for staging
        cls.test_user_email = "e2e.test.user@netrasystems.ai"
        cls.test_user_password = "E2ETestPassword123!"
        
        # Golden Path validation parameters
        cls.golden_path_timeout = 30.0  # 30 seconds for full Golden Path
        cls.websocket_event_timeout = 10.0  # 10 seconds for each WebSocket event
        cls.auth_timeout = 5.0  # 5 seconds for authentication
        
        # Critical WebSocket events that must be received for Golden Path success
        cls.critical_websocket_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        logger.info(" SETUP:  E2E staging environment configured")
        logger.info(f"   - Staging URL: {cls.staging_base_url}")
        logger.info(f"   - WebSocket URL: {cls.staging_ws_url}")
        logger.info(f"   - Critical events: {cls.critical_websocket_events}")
    
    def setUp(self):
        """Set up individual test."""
        super().setUp()
        
        # Generate unique test session ID
        self.test_session_id = f"e2e_test_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Track received events for validation
        self.received_events = []
        self.websocket_messages = []
        self.auth_token = None
        self.user_id = None
        
        logger.info(f" SETUP:  Test session {self.test_session_id} initialized")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_golden_path_complete_user_flow_staging(self):
        """
        GOLDEN PATH E2E TEST: Complete user flow in staging environment.
        
        Tests the complete Golden Path: authentication → WebSocket connection → 
        agent request → WebSocket events → AI response. This validates that 
        MessageRouter consolidation preserves the core $500K+ ARR functionality.
        """
        logger.info(" TESTING:  Golden Path complete user flow in staging")
        
        golden_path_start_time = time.time()
        
        try:
            # Step 1: Authenticate with staging auth service
            auth_success = await self._authenticate_staging_user()
            self.assertTrue(auth_success, "Golden Path blocked: Authentication failed")
            logger.info(f" PASS:  Step 1 - Authentication successful (user_id: {self.user_id})")
            
            # Step 2: Establish WebSocket connection  
            websocket_connected = await self._connect_staging_websocket()
            self.assertTrue(websocket_connected, "Golden Path blocked: WebSocket connection failed")
            logger.info(" PASS:  Step 2 - WebSocket connection established")
            
            # Step 3: Send agent request message through MessageRouter
            agent_request_sent = await self._send_agent_request_message()
            self.assertTrue(agent_request_sent, "Golden Path blocked: Agent request failed")
            logger.info(" PASS:  Step 3 - Agent request sent through MessageRouter")
            
            # Step 4: Validate critical WebSocket events are received
            events_received = await self._validate_critical_websocket_events()
            self.assertTrue(events_received, "Golden Path blocked: Critical WebSocket events missing")
            logger.info(f" PASS:  Step 4 - All {len(self.critical_websocket_events)} critical events received")
            
            # Step 5: Validate AI response is received
            ai_response_received = await self._validate_ai_response()
            self.assertTrue(ai_response_received, "Golden Path blocked: AI response not received")
            logger.info(" PASS:  Step 5 - AI response received")
            
            # Calculate Golden Path timing
            golden_path_duration = time.time() - golden_path_start_time
            
            # Validate Golden Path performance
            self.assertLess(
                golden_path_duration, self.golden_path_timeout,
                f"Golden Path too slow: {golden_path_duration:.2f}s > {self.golden_path_timeout}s"
            )
            
            logger.info(f" SUCCESS:  Golden Path completed in {golden_path_duration:.2f}s")
            logger.info(f"   - Authentication: ✅")
            logger.info(f"   - WebSocket: ✅") 
            logger.info(f"   - Message Routing: ✅")
            logger.info(f"   - WebSocket Events: ✅ ({len(self.received_events)} events)")
            logger.info(f"   - AI Response: ✅")
            logger.info(f"   - Performance: ✅ ({golden_path_duration:.2f}s < {self.golden_path_timeout}s)")
            
        except Exception as e:
            self.fail(f"Golden Path FAILED: {e}")
        
        finally:
            # Clean up WebSocket connection
            await self._cleanup_websocket_connection()
    
    @pytest.mark.e2e  
    @pytest.mark.staging
    async def test_message_router_consolidation_staging_compatibility(self):
        """
        E2E TEST: MessageRouter consolidation compatibility in staging.
        
        Tests that the consolidated MessageRouter works correctly in the staging 
        environment with real services and infrastructure.
        """
        logger.info(" TESTING:  MessageRouter consolidation staging compatibility")
        
        try:
            # Authenticate first
            auth_success = await self._authenticate_staging_user()
            self.assertTrue(auth_success, "Authentication required for MessageRouter testing")
            
            # Connect WebSocket
            websocket_connected = await self._connect_staging_websocket()
            self.assertTrue(websocket_connected, "WebSocket required for MessageRouter testing")
            
            # Test different message types through consolidated MessageRouter
            message_routing_tests = [
                {
                    "test_name": "core_ping_message",
                    "message": {
                        "type": "ping",
                        "payload": {"timestamp": time.time()},
                        "session_id": self.test_session_id
                    },
                    "expected_response": "pong"
                },
                {
                    "test_name": "user_message_routing",
                    "message": {
                        "type": "user_message", 
                        "payload": {
                            "content": "Test message routing consolidation",
                            "thread_id": self.test_thread_id
                        },
                        "session_id": self.test_session_id
                    },
                    "expected_response": "message_received"
                },
                {
                    "test_name": "agent_request_routing",
                    "message": {
                        "type": "agent_request",
                        "payload": {
                            "agent": "triage_agent",
                            "message": "Test agent routing in staging",
                            "thread_id": self.test_thread_id,
                            "run_id": self.test_run_id
                        },
                        "session_id": self.test_session_id
                    },
                    "expected_response": "agent_started"
                }
            ]
            
            routing_results = []
            
            for test in message_routing_tests:
                try:
                    # Send message through WebSocket (goes through MessageRouter)
                    await self.websocket.send(json.dumps(test["message"]))
                    
                    # Wait for response
                    response_received = await self._wait_for_response(
                        expected_type=test["expected_response"],
                        timeout=5.0
                    )
                    
                    routing_results.append({
                        "test_name": test["test_name"],
                        "success": response_received,
                        "message_type": test["message"]["type"]
                    })
                    
                    if response_received:
                        logger.info(f" PASS:  {test['test_name']} - MessageRouter handled correctly")
                    else:
                        logger.warning(f" WARN:  {test['test_name']} - No expected response")
                        
                except Exception as e:
                    routing_results.append({
                        "test_name": test["test_name"],
                        "success": False,
                        "error": str(e)
                    })
                    logger.error(f" FAIL:  {test['test_name']} - {e}")
            
            # Validate MessageRouter consolidation results
            successful_routes = [r for r in routing_results if r["success"]]
            success_rate = len(successful_routes) / len(routing_results)
            
            self.assertGreaterEqual(
                success_rate, 0.67,  # At least 2/3 should work
                f"MessageRouter consolidation success rate too low: {success_rate:.2%}"
            )
            
            logger.info(f" SUMMARY:  MessageRouter consolidation staging compatibility:")
            logger.info(f"   - Tests run: {len(routing_results)}")
            logger.info(f"   - Successful: {len(successful_routes)}")
            logger.info(f"   - Success rate: {success_rate:.2%}")
            
            for result in routing_results:
                status = "✅" if result["success"] else "❌"
                logger.info(f"   {status} {result['test_name']}")
            
        except Exception as e:
            self.fail(f"MessageRouter consolidation staging test failed: {e}")
        
        finally:
            await self._cleanup_websocket_connection()
    
    @pytest.mark.e2e
    @pytest.mark.staging  
    async def test_quality_message_routing_staging_fallback(self):
        """
        E2E TEST: Quality message routing fallback in staging.
        
        Tests that quality message routing fails gracefully in staging when
        QualityMessageRouter dependencies are missing, without breaking core functionality.
        """
        logger.info(" TESTING:  Quality message routing staging fallback")
        
        try:
            # Authenticate and connect
            auth_success = await self._authenticate_staging_user()
            websocket_connected = await self._connect_staging_websocket()
            
            self.assertTrue(auth_success and websocket_connected, "Prerequisites failed")
            
            # Test quality messages that may fail due to missing dependencies
            quality_messages = [
                {
                    "type": "get_quality_metrics",
                    "payload": {"metric_type": "response_time"},
                    "session_id": self.test_session_id
                },
                {
                    "type": "subscribe_quality_alerts", 
                    "payload": {"alert_types": ["error", "performance"]},
                    "session_id": self.test_session_id
                },
                {
                    "type": "validate_content",
                    "payload": {"content": "Test content validation"},
                    "session_id": self.test_session_id
                }
            ]
            
            quality_routing_results = []
            
            for message in quality_messages:
                try:
                    # Send quality message
                    await self.websocket.send(json.dumps(message))
                    
                    # Wait for response or graceful failure
                    response_received = await self._wait_for_response(
                        expected_type=["quality_response", "error", "unknown_message_type"],
                        timeout=3.0
                    )
                    
                    quality_routing_results.append({
                        "message_type": message["type"],
                        "graceful_handling": True,  # Didn't crash
                        "response_received": response_received
                    })
                    
                    logger.info(f" PASS:  {message['type']} handled gracefully")
                    
                except Exception as e:
                    quality_routing_results.append({
                        "message_type": message["type"],
                        "graceful_handling": False,  # Crashed
                        "error": str(e)
                    })
                    logger.error(f" FAIL:  {message['type']} caused error: {e}")
            
            # Validate graceful handling of quality messages
            graceful_count = sum(1 for r in quality_routing_results if r["graceful_handling"])
            graceful_rate = graceful_count / len(quality_routing_results)
            
            # All quality messages should be handled gracefully (even if they fail)
            self.assertEqual(
                graceful_rate, 1.0,
                f"Quality message handling not graceful: {graceful_rate:.2%}"
            )
            
            # Test that core functionality still works after quality message attempts
            core_test_message = {
                "type": "ping",
                "payload": {"test": "after_quality_messages"},
                "session_id": self.test_session_id
            }
            
            await self.websocket.send(json.dumps(core_test_message))
            core_response = await self._wait_for_response("pong", timeout=3.0)
            
            self.assertTrue(
                core_response,
                "Core functionality broken after quality message routing attempts"
            )
            
            logger.info(f" SUMMARY:  Quality message routing staging fallback:")
            logger.info(f"   - Quality messages tested: {len(quality_routing_results)}")
            logger.info(f"   - Gracefully handled: {graceful_count}")
            logger.info(f"   - Core functionality: {'✅' if core_response else '❌'}")
            
        except Exception as e:
            self.fail(f"Quality message routing staging test failed: {e}")
        
        finally:
            await self._cleanup_websocket_connection()
    
    async def _authenticate_staging_user(self) -> bool:
        """Authenticate with staging auth service."""
        try:
            auth_url = f"{self.staging_auth_url}/auth/login"
            
            auth_payload = {
                "email": self.test_user_email,
                "password": self.test_user_password
            }
            
            # Make authentication request
            response = requests.post(
                auth_url, 
                json=auth_payload,
                timeout=self.auth_timeout
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                self.auth_token = auth_data.get("access_token")
                self.user_id = auth_data.get("user_id")
                
                return self.auth_token is not None and self.user_id is not None
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def _connect_staging_websocket(self) -> bool:
        """Connect to staging WebSocket with authentication."""
        try:
            # WebSocket connection with auth headers
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "User-ID": self.user_id
            }
            
            self.websocket = await websockets.connect(
                self.staging_ws_url,
                extra_headers=headers,
                timeout=10.0
            )
            
            # Send initial connection message
            connect_message = {
                "type": "connect",
                "payload": {
                    "user_id": self.user_id,
                    "session_id": self.test_session_id
                }
            }
            
            await self.websocket.send(json.dumps(connect_message))
            
            # Wait for connection confirmation
            connection_confirmed = await self._wait_for_response("connected", timeout=5.0)
            
            return connection_confirmed
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            return False
    
    async def _send_agent_request_message(self) -> bool:
        """Send agent request through MessageRouter."""
        try:
            agent_message = {
                "type": "agent_request",
                "payload": {
                    "agent": "triage_agent",
                    "message": "Analyze cost optimization opportunities for cloud infrastructure",
                    "thread_id": self.test_thread_id,
                    "run_id": self.test_run_id,
                    "user_id": self.user_id
                },
                "session_id": self.test_session_id
            }
            
            await self.websocket.send(json.dumps(agent_message))
            
            # Wait for agent_started event
            agent_started = await self._wait_for_response("agent_started", timeout=10.0)
            
            return agent_started
            
        except Exception as e:
            logger.error(f"Agent request error: {e}")
            return False
    
    async def _validate_critical_websocket_events(self) -> bool:
        """Validate that all critical WebSocket events are received."""
        try:
            events_received = set()
            
            # Wait for critical events with timeout
            timeout_time = time.time() + self.websocket_event_timeout
            
            while len(events_received) < len(self.critical_websocket_events) and time.time() < timeout_time:
                try:
                    # Wait for WebSocket message
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=2.0
                    )
                    
                    message_data = json.loads(message)
                    event_type = message_data.get("type")
                    
                    # Track received messages
                    self.websocket_messages.append(message_data)
                    
                    # Check if it's a critical event
                    if event_type in self.critical_websocket_events:
                        events_received.add(event_type)
                        self.received_events.append(event_type)
                        logger.info(f" EVENT:  Received critical event: {event_type}")
                
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"Event parsing error: {e}")
                    continue
            
            # Check if all critical events were received
            missing_events = set(self.critical_websocket_events) - events_received
            
            if missing_events:
                logger.warning(f"Missing critical events: {missing_events}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Event validation error: {e}")
            return False
    
    async def _validate_ai_response(self) -> bool:
        """Validate that AI response is received."""
        try:
            # Wait for agent_completed and final response
            timeout_time = time.time() + 15.0  # 15 seconds for AI response
            
            while time.time() < timeout_time:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=3.0
                    )
                    
                    message_data = json.loads(message)
                    event_type = message_data.get("type")
                    
                    self.websocket_messages.append(message_data)
                    
                    # Check for AI response indicators
                    if event_type in ["agent_completed", "response", "message_response"]:
                        payload = message_data.get("payload", {})
                        
                        # Validate response has content
                        if any(key in payload for key in ["content", "response", "result", "message"]):
                            logger.info(f" RESPONSE:  AI response received: {event_type}")
                            return True
                
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"Response parsing error: {e}")
                    continue
            
            logger.warning("AI response not received within timeout")
            return False
            
        except Exception as e:
            logger.error(f"AI response validation error: {e}")
            return False
    
    async def _wait_for_response(self, expected_type, timeout: float = 5.0) -> bool:
        """Wait for specific response type."""
        try:
            if isinstance(expected_type, str):
                expected_types = [expected_type]
            else:
                expected_types = expected_type
            
            timeout_time = time.time() + timeout
            
            while time.time() < timeout_time:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=1.0
                    )
                    
                    message_data = json.loads(message)
                    event_type = message_data.get("type")
                    
                    self.websocket_messages.append(message_data)
                    
                    if event_type in expected_types:
                        return True
                
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"Response wait error: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Wait for response error: {e}")
            return False
    
    async def _cleanup_websocket_connection(self):
        """Clean up WebSocket connection."""
        try:
            if hasattr(self, 'websocket') and self.websocket:
                await self.websocket.close()
                logger.info(" CLEANUP:  WebSocket connection closed")
        except Exception as e:
            logger.warning(f"WebSocket cleanup error: {e}")


if __name__ == '__main__':
    # Run with pytest: python -m pytest tests/e2e/test_issue_1181_golden_path_message_routing_staging.py -v -s --tb=short
    import unittest
    unittest.main()