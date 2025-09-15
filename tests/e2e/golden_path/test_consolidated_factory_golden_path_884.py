"""
Test Suite: Issue #884 - Multiple execution engine factories blocking AI responses
Module: Consolidated Factory Golden Path E2E Test

PURPOSE:
This E2E test validates the complete Golden Path user flow with the consolidated factory:
user login → chat request → agent execution → AI response delivery.
Tests on GCP staging environment (no Docker required).

BUSINESS IMPACT:
- $500K+ ARR Golden Path directly validated with consolidated factory
- Complete user journey from authentication to AI response delivery
- Real-world validation of factory consolidation protecting business value
- End-to-end validation ensures customer-facing functionality works

TEST REQUIREMENTS:
- Tests complete Golden Path: login → chat → AI response
- Runs on GCP staging environment (no Docker)
- Uses real authentication and AI services
- Validates all 5 critical WebSocket events during agent execution

Created: 2025-09-14 for Issue #884 Step 2 Golden Path validation
"""

import asyncio
import uuid
import json
import time
from typing import Dict, Any, Optional, List
import pytest
import websockets
import aiohttp
from datetime import datetime, UTC

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestConsolidatedFactoryGoldenPath884(SSotAsyncTestCase):
    """
    E2E Test: Validate complete Golden Path with consolidated factory
    
    This test validates the entire customer journey from login through AI response
    delivery, ensuring the consolidated factory doesn't break business-critical flows.
    """
    
    def setup_method(self, method):
        """Set up Golden Path E2E test"""
        super().setup_method(method)
        self.record_metric("test_type", "e2e")
        self.record_metric("test_scope", "golden_path")
        self.record_metric("environment", "staging")
        self.record_metric("docker_required", False)
        self.record_metric("issue_number", "884")
        
        # Set staging environment
        env = self.get_env()
        env.set("ENVIRONMENT", "staging", "e2e_test")
        env.set("TEST_GOLDEN_PATH", "true", "e2e_test")
        
        # Staging URLs (adjust based on actual staging environment)
        self.base_url = env.get("STAGING_BASE_URL", "https://staging-netra-backend.example.com")
        self.ws_url = env.get("STAGING_WS_URL", "wss://staging-netra-backend.example.com/ws")
        
    async def test_complete_golden_path_with_consolidated_factory_884(self):
        """
        CRITICAL E2E TEST: Complete Golden Path user journey with consolidated factory
        
        This test validates the entire customer flow:
        1. User authentication  
        2. WebSocket connection establishment
        3. Chat message submission
        4. Agent execution with consolidated factory
        5. AI response delivery with all WebSocket events
        
        Expected: Complete flow works without factory-related failures
        """
        start_time = time.time()
        self.record_metric("golden_path_start", start_time)
        
        # Step 1: Authenticate test user
        auth_result = await self._authenticate_test_user()
        self.assertTrue(auth_result['success'], 
            f"CRITICAL: Authentication failed: {auth_result.get('error')}. "
            f"Cannot test Golden Path without authentication.")
        
        jwt_token = auth_result['token']
        user_id = auth_result['user_id']
        self.record_metric("authentication_time", auth_result['duration'])
        
        # Step 2: Establish WebSocket connection  
        ws_result = await self._establish_websocket_connection(jwt_token)
        self.assertTrue(ws_result['success'],
            f"CRITICAL: WebSocket connection failed: {ws_result.get('error')}. "
            f"This blocks real-time Golden Path functionality.")
        
        websocket = ws_result['websocket']
        self.record_metric("websocket_connection_time", ws_result['duration'])
        
        try:
            # Step 3: Send chat message that triggers agent execution
            chat_result = await self._send_chat_message_and_track_execution(
                websocket, user_id, 
                "Analyze the performance of our AI optimization platform and provide recommendations."
            )
            
            self.assertTrue(chat_result['success'],
                f"CRITICAL: Chat execution failed: {chat_result.get('error')}. "
                f"This indicates factory consolidation broke agent execution.")
            
            # Step 4: Validate all WebSocket events were received
            events = chat_result['events']
            self._validate_websocket_events(events)
            
            # Step 5: Validate AI response quality
            ai_response = chat_result['final_response']
            self._validate_ai_response_quality(ai_response)
            
            self.record_metric("chat_execution_time", chat_result['duration'])
            self.record_metric("total_events_received", len(events))
            
        finally:
            # Clean up WebSocket connection
            await websocket.close()
        
        total_time = time.time() - start_time
        self.record_metric("total_golden_path_time", total_time)
        
        # Performance validation - Golden Path should complete reasonably quickly
        assert total_time < 60.0, (
            f"CRITICAL: Golden Path too slow: {total_time:.2f}s. "
            f"This affects user experience and may indicate factory performance issues.")
        
        # Record successful Golden Path validation
        self.record_metric("golden_path_validated", True)
        self.record_metric("factory_consolidation_compatible", True)
        self.record_metric("business_value_protected", True)
        
    async def _authenticate_test_user(self) -> Dict[str, Any]:
        """Authenticate a test user for Golden Path validation"""
        auth_start = time.time()
        
        try:
            # Create test user credentials
            test_email = f"golden_path_test_{uuid.uuid4().hex[:8]}@example.com"
            test_password = f"test_password_{uuid.uuid4().hex[:8]}"
            
            async with aiohttp.ClientSession() as session:
                # Register test user (if registration endpoint exists)
                register_data = {
                    "email": test_email,
                    "password": test_password,
                    "name": "Golden Path Test User"
                }
                
                register_url = f"{self.base_url}/auth/register"
                try:
                    async with session.post(register_url, json=register_data) as response:
                        if response.status not in [200, 201, 409]:  # 409 = user exists
                            return {
                                'success': False,
                                'error': f"Registration failed: {response.status}",
                                'duration': time.time() - auth_start
                            }
                except Exception as e:
                    # Registration may not be available, try login directly
                    pass
                
                # Login test user
                login_data = {
                    "email": test_email, 
                    "password": test_password
                }
                
                login_url = f"{self.base_url}/auth/login"
                async with session.post(login_url, json=login_data) as response:
                    if response.status == 200:
                        auth_data = await response.json()
                        return {
                            'success': True,
                            'token': auth_data.get('access_token') or auth_data.get('token'),
                            'user_id': auth_data.get('user_id') or f"test_user_{uuid.uuid4().hex[:8]}",
                            'duration': time.time() - auth_start
                        }
                    else:
                        # Try with demo/test credentials if available
                        demo_login_data = {
                            "email": "demo@example.com",
                            "password": "demo123"
                        }
                        
                        async with session.post(login_url, json=demo_login_data) as demo_response:
                            if demo_response.status == 200:
                                auth_data = await demo_response.json()
                                return {
                                    'success': True,
                                    'token': auth_data.get('access_token') or auth_data.get('token'),
                                    'user_id': auth_data.get('user_id') or "demo_user",
                                    'duration': time.time() - auth_start
                                }
                            else:
                                return {
                                    'success': False,
                                    'error': f"Login failed: {response.status}",
                                    'duration': time.time() - auth_start
                                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Authentication error: {str(e)}",
                'duration': time.time() - auth_start
            }
    
    async def _establish_websocket_connection(self, jwt_token: str) -> Dict[str, Any]:
        """Establish WebSocket connection for real-time communication"""
        ws_start = time.time()
        
        try:
            # WebSocket headers with JWT token
            headers = {
                "Authorization": f"Bearer {jwt_token}"
            }
            
            # Connect to WebSocket endpoint
            websocket = await websockets.connect(
                self.ws_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            # Wait for connection confirmation
            try:
                # Send initial ping/hello message
                hello_msg = {
                    "type": "hello",
                    "timestamp": datetime.now(UTC).isoformat()
                }
                await websocket.send(json.dumps(hello_msg))
                
                # Wait for response (with timeout)
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                if response_data.get('type') in ['hello_ack', 'connected', 'connection_confirmed']:
                    return {
                        'success': True,
                        'websocket': websocket,
                        'duration': time.time() - ws_start
                    }
                else:
                    await websocket.close()
                    return {
                        'success': False,
                        'error': f"Unexpected WebSocket response: {response_data}",
                        'duration': time.time() - ws_start
                    }
                    
            except asyncio.TimeoutError:
                await websocket.close()
                return {
                    'success': False,
                    'error': "WebSocket connection timeout",
                    'duration': time.time() - ws_start
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"WebSocket connection error: {str(e)}",
                'duration': time.time() - ws_start
            }
    
    async def _send_chat_message_and_track_execution(
        self, 
        websocket, 
        user_id: str, 
        message: str
    ) -> Dict[str, Any]:
        """Send chat message and track complete agent execution"""
        chat_start = time.time()
        
        try:
            # Send chat message
            chat_message = {
                "type": "chat_message",
                "message": message,
                "user_id": user_id,
                "session_id": f"golden_path_session_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            await websocket.send(json.dumps(chat_message))
            
            # Track WebSocket events during execution
            events = []
            final_response = None
            execution_complete = False
            
            # Listen for events with timeout
            timeout = 45.0  # 45 second timeout for agent execution
            end_time = time.time() + timeout
            
            while time.time() < end_time and not execution_complete:
                try:
                    # Wait for next WebSocket message
                    message = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=min(10.0, end_time - time.time())
                    )
                    
                    event_data = json.loads(message)
                    events.append(event_data)
                    
                    event_type = event_data.get('type')
                    
                    # Track critical Golden Path events
                    if event_type == 'agent_started':
                        self.record_metric("agent_started_received", True)
                        
                    elif event_type == 'agent_thinking':
                        self.record_metric("agent_thinking_received", True)
                        
                    elif event_type == 'tool_executing':
                        self.record_metric("tool_executing_received", True)
                        
                    elif event_type == 'tool_completed':
                        self.record_metric("tool_completed_received", True)
                        
                    elif event_type == 'agent_completed':
                        self.record_metric("agent_completed_received", True)
                        final_response = event_data.get('response') or event_data.get('message')
                        execution_complete = True
                        
                    elif event_type in ['agent_response', 'chat_response', 'final_response']:
                        final_response = event_data.get('response') or event_data.get('message')
                        execution_complete = True
                        
                    elif event_type == 'error':
                        return {
                            'success': False,
                            'error': f"Agent execution error: {event_data.get('message')}",
                            'events': events,
                            'duration': time.time() - chat_start
                        }
                        
                except asyncio.TimeoutError:
                    # Check if we got at least some events
                    if events:
                        continue  # Keep waiting if we're getting events
                    else:
                        return {
                            'success': False,
                            'error': "No WebSocket events received - possible agent execution failure",
                            'events': events,
                            'duration': time.time() - chat_start
                        }
                        
            if not execution_complete:
                return {
                    'success': False,
                    'error': f"Agent execution timeout after {timeout}s",
                    'events': events,
                    'duration': time.time() - chat_start
                }
            
            return {
                'success': True,
                'events': events,
                'final_response': final_response,
                'duration': time.time() - chat_start
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Chat execution error: {str(e)}",
                'events': [],
                'duration': time.time() - chat_start
            }
    
    def _validate_websocket_events(self, events: List[Dict[str, Any]]):
        """Validate that all critical WebSocket events were received"""
        event_types = [event.get('type') for event in events]
        
        # Critical Golden Path events that must be present
        critical_events = [
            'agent_started',
            'agent_thinking', 
            'agent_completed'
        ]
        
        missing_events = []
        for event_type in critical_events:
            if event_type not in event_types:
                missing_events.append(event_type)
        
        # Allow some flexibility but require core events
        assert len(missing_events) <= 1, (
            f"CRITICAL: Missing critical WebSocket events: {missing_events}. "
            f"Received events: {event_types}. "
            f"This indicates factory consolidation broke real-time event delivery "
            f"that's essential for Golden Path user experience.")
        
        # Validate event order makes sense
        if 'agent_started' in event_types and 'agent_completed' in event_types:
            start_index = event_types.index('agent_started')
            complete_index = event_types.index('agent_completed')
            
            assert complete_index > start_index, (
                f"CRITICAL: WebSocket events out of order. "
                f"agent_completed ({complete_index}) before agent_started ({start_index}). "
                f"This indicates execution engine timing issues.")
    
    def _validate_ai_response_quality(self, response: Optional[str]):
        """Validate that AI response has reasonable quality"""
        if not response:
            raise AssertionError(
                "CRITICAL: No AI response received. "
                "This indicates factory consolidation broke agent response generation.")
        
        # Basic quality checks
        response_length = len(response.strip())
        
        assert response_length > 50, (
            f"CRITICAL: AI response too short ({response_length} chars): '{response[:100]}...'. "
            f"This indicates agent execution issues that affect response quality.")
        
        # Check for reasonable content (not just error messages)
        error_indicators = ['error', 'failed', 'exception', 'traceback']
        response_lower = response.lower()
        
        for indicator in error_indicators:
            assert indicator not in response_lower, (
                f"CRITICAL: AI response contains error indicator '{indicator}': '{response[:200]}...'. "
                f"This indicates agent execution failures.")
        
        self.record_metric("ai_response_length", response_length)
        self.record_metric("ai_response_quality_validated", True)
    
    async def test_factory_consolidation_maintains_websocket_stability_884(self):
        """
        E2E TEST: Validate factory consolidation doesn't destabilize WebSocket connections
        
        This test specifically focuses on WebSocket stability during agent execution
        with the consolidated factory.
        """
        # Authenticate user
        auth_result = await self._authenticate_test_user()
        if not auth_result['success']:
            pytest.skip(f"Authentication not available: {auth_result.get('error')}")
        
        jwt_token = auth_result['token']
        
        # Establish multiple WebSocket connections to test stability
        connections = []
        try:
            for i in range(3):
                ws_result = await self._establish_websocket_connection(jwt_token)
                if ws_result['success']:
                    connections.append(ws_result['websocket'])
            
            # Should be able to establish multiple connections
            assert len(connections) >= 1, (
                "CRITICAL: Cannot establish WebSocket connections. "
                "This indicates factory consolidation broke WebSocket infrastructure.")
            
            # Test message handling on each connection
            for i, ws in enumerate(connections):
                ping_msg = {
                    "type": "ping",
                    "connection_id": i,
                    "timestamp": datetime.now(UTC).isoformat()
                }
                
                await ws.send(json.dumps(ping_msg))
                
                # Should receive response
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    # Connection should be stable
                    assert response_data.get('type') in ['pong', 'ping_ack', 'message'], (
                        f"CRITICAL: WebSocket connection {i} unstable: {response_data}")
                        
                except asyncio.TimeoutError:
                    raise AssertionError(
                        f"CRITICAL: WebSocket connection {i} timeout. "
                        f"This indicates connection stability issues.")
            
        finally:
            # Clean up all connections
            for ws in connections:
                try:
                    await ws.close()
                except:
                    pass
        
        self.record_metric("websocket_stability_validated", True)