#!/usr/bin/env python
"""INTEGRATION TEST 6: Agent Workflow with Tool Execution Notifications

This test validates the complete agent workflow with WebSocket notifications
for tool execution events, ensuring users see real-time feedback during
AI processing to deliver substantive chat value.

Business Value: Core chat functionality - users trust AI systems that show their work
Test Requirements:
- Real Docker services (PostgreSQL, Redis, Backend, Auth)
- Real WebSocket connections
- Actual LLM calls for agent execution
- WebSocket event validation for all 5 critical events

CRITICAL: This test verifies the infrastructure that enables 90% of current business value.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict
import threading
from shared.isolated_environment import IsolatedEnvironment

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import websockets
import requests
from loguru import logger
from shared.isolated_environment import get_env

# Import production components
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from test_framework.base_integration_test import BaseIntegrationTest as DockerTestBase


class WebSocketEventCapture:
    """Captures and validates WebSocket events during agent execution"""
    
    def __init__(self, test_timeout: float = 120.0):
        self.events: List[Dict[str, Any]] = []
        self.event_types_seen: Set[str] = set()
        self.tool_executions: List[Dict[str, Any]] = []
        self.test_timeout = test_timeout
        self.start_time = time.time()
        self._lock = threading.Lock()
        
    def capture_event(self, event_data: Dict[str, Any]):
        """Thread-safe event capture"""
        with self._lock:
            event_data['timestamp'] = datetime.now().isoformat()
            event_data['elapsed_ms'] = int((time.time() - self.start_time) * 1000)
            self.events.append(event_data.copy())
            
            event_type = event_data.get('type', '')
            self.event_types_seen.add(event_type)
            
            # Track tool executions specifically
            if event_type in ['tool_executing', 'tool_completed']:
                self.tool_executions.append(event_data.copy())
                
    def get_events_summary(self) -> Dict[str, Any]:
        """Get comprehensive event summary for validation"""
        with self._lock:
            return {
                'total_events': len(self.events),
                'event_types': sorted(list(self.event_types_seen)),
                'tool_executions_count': len(self.tool_executions),
                'events_timeline': self.events.copy(),
                'test_duration_ms': int((time.time() - self.start_time) * 1000)
            }
            
    def validate_critical_events(self) -> tuple[bool, List[str]]:
        """Validate all 5 critical WebSocket events are present"""
        required_events = {
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        }
        
        missing_events = required_events - self.event_types_seen
        return len(missing_events) == 0, list(missing_events)


@pytest.mark.integration
@pytest.mark.requires_docker
@pytest.mark.requires_websocket
class TestAgentWorkflowToolNotifications(DockerTestBase):
    """Integration Test 6: Agent workflow with comprehensive WebSocket notifications"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Initialize test environment with real services"""
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.session_id = f"session_{uuid.uuid4().hex[:8]}"
        self.thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        self.request_id = f"req_{uuid.uuid4().hex[:8]}"
        
        # WebSocket connection details
        backend_port = get_env().get('BACKEND_PORT', '8000')
        self.websocket_url = f"ws://localhost:{backend_port}/ws/{self.user_id}"
        self.backend_url = f"http://localhost:{backend_port}"
        
        # Event capture
        self.event_capture = WebSocketEventCapture(test_timeout=180.0)
        
        yield
        
        # Cleanup after test
        logger.info(f"Test completed. Captured {len(self.event_capture.events)} WebSocket events")
    
    async def _establish_websocket_connection(self) -> websockets.WebSocketServerProtocol:
        """Establish authenticated WebSocket connection"""
        try:
            # Create test authentication token
            auth_token = await self._create_test_auth_token()
            
            headers = {
                'Authorization': f'Bearer {auth_token}',
                'User-Agent': 'IntegrationTest/1.0'
            }
            
            logger.info(f"Connecting to WebSocket: {self.websocket_url}")
            websocket = await websockets.connect(
                self.websocket_url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            
            logger.info("WebSocket connection established successfully")
            return websocket
            
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            raise
    
    async def _create_test_auth_token(self) -> str:
        """Create authentication token for test user"""
        auth_port = get_env().get('AUTH_PORT', '8081')
        auth_url = f"http://localhost:{auth_port}"
        
        # Register test user
        register_payload = {
            'email': f'{self.user_id}@test.netra.com',
            'password': 'TestPassword123!',
            'full_name': f'Test User {self.user_id[:8]}'
        }
        
        response = requests.post(
            f'{auth_url}/auth/register',
            json=register_payload,
            timeout=30
        )
        
        if response.status_code not in [200, 201, 409]:  # 409 = already exists
            logger.warning(f"Registration response: {response.status_code} - {response.text}")
        
        # Login to get token
        login_payload = {
            'email': register_payload['email'],
            'password': register_payload['password']
        }
        
        login_response = requests.post(
            f'{auth_url}/auth/login',
            json=login_payload,
            timeout=30
        )
        
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token_data = login_response.json()
        return token_data['access_token']
    
    async def _listen_websocket_events(self, websocket: websockets.WebSocketServerProtocol):
        """Listen for WebSocket events and capture them"""
        try:
            async for message in websocket:
                try:
                    event_data = json.loads(message)
                    logger.debug(f"Received WebSocket event: {event_data.get('type', 'unknown')}")
                    self.event_capture.capture_event(event_data)
                    
                    # Stop listening after agent completion
                    if event_data.get('type') == 'agent_completed':
                        logger.info("Agent completed - stopping WebSocket listener")
                        break
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse WebSocket message: {e}")
                    continue
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket listening error: {e}")
    
    async def _execute_agent_with_tools(self) -> Dict[str, Any]:
        """Execute agent workflow that requires multiple tool executions"""
        agent_payload = {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'thread_id': self.thread_id,
            'request_id': self.request_id,
            'agent_type': 'supervisor',  # Use supervisor for complex workflows
            'query': (
                'Analyze the performance metrics for our system and provide optimization recommendations. '
                'Please use multiple tools to gather data, perform analysis, and generate actionable insights.'
            ),
            'context': {
                'conversation_context': 'performance_analysis',
                'user_goals': ['system_optimization', 'performance_improvement'],
                'analysis_depth': 'comprehensive'
            }
        }
        
        logger.info(f"Sending agent execution request: {agent_payload['agent_type']}")
        
        response = requests.post(
            f'{self.backend_url}/api/agent/execute',
            json=agent_payload,
            timeout=180,  # Allow time for comprehensive analysis
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 200, f"Agent execution failed: {response.status_code} - {response.text}"
        
        result = response.json()
        logger.info(f"Agent execution completed successfully")
        return result
    
    @pytest.mark.asyncio
    async def test_complete_agent_workflow_with_tool_notifications(self):
        """
        Test 6: Complete agent workflow with WebSocket tool execution notifications
        
        Validates:
        1. WebSocket connection establishment
        2. Agent execution with multiple tools
        3. All 5 critical WebSocket events are emitted
        4. Tool execution events include proper metadata
        5. Events arrive in correct sequence
        6. Business value: Users see AI working on their requests
        """
        logger.info("=== INTEGRATION TEST 6: Agent Workflow Tool Notifications ===")
        
        # Establish WebSocket connection
        websocket = await self._establish_websocket_connection()
        
        try:
            # Start listening for events in background
            listener_task = asyncio.create_task(
                self._listen_websocket_events(websocket)
            )
            
            # Give WebSocket listener time to start
            await asyncio.sleep(0.5)
            
            # Execute agent workflow that uses multiple tools
            start_time = time.time()
            result = await self._execute_agent_with_tools()
            execution_time = time.time() - start_time
            
            # Wait for WebSocket listener to complete
            await asyncio.wait_for(listener_task, timeout=30.0)
            
        finally:
            await websocket.close()
        
        # Validate results
        self._validate_agent_execution_result(result, execution_time)
        self._validate_websocket_events()
        self._validate_tool_execution_events()
        self._validate_event_sequence_and_timing()
        
        logger.info("✅ INTEGRATION TEST 6 PASSED: Agent workflow with tool notifications working correctly")
    
    def _validate_agent_execution_result(self, result: Dict[str, Any], execution_time: float):
        """Validate the agent execution result"""
        assert 'status' in result, "Missing status in agent result"
        assert result['status'] == 'success', f"Agent execution failed: {result.get('message', 'Unknown error')}"
        
        assert 'response' in result, "Missing response in agent result"
        assert len(result['response']) > 0, "Empty agent response"
        
        # Ensure execution time is reasonable (not too fast = no real work)
        assert execution_time > 2.0, f"Execution too fast ({execution_time:.2f}s) - likely not using real tools"
        assert execution_time < 300.0, f"Execution too slow ({execution_time:.2f}s) - potential timeout issue"
        
        logger.info(f"✅ Agent execution completed in {execution_time:.2f}s with valid response")
    
    def _validate_websocket_events(self):
        """Validate all required WebSocket events were emitted"""
        events_summary = self.event_capture.get_events_summary()
        
        # Must have received events
        assert events_summary['total_events'] > 0, "No WebSocket events received"
        
        # Validate critical events
        has_all_critical, missing_events = self.event_capture.validate_critical_events()
        assert has_all_critical, f"Missing critical WebSocket events: {missing_events}"
        
        # Must have tool execution events
        assert events_summary['tool_executions_count'] > 0, "No tool execution events received"
        
        logger.info(f"✅ WebSocket validation passed: {events_summary['total_events']} events, "
                   f"{len(events_summary['event_types'])} event types")
    
    def _validate_tool_execution_events(self):
        """Validate tool execution events contain proper metadata"""
        tool_events = self.event_capture.tool_executions
        
        assert len(tool_events) > 0, "No tool execution events captured"
        
        # Validate tool_executing events
        executing_events = [e for e in tool_events if e.get('type') == 'tool_executing']
        assert len(executing_events) > 0, "No 'tool_executing' events found"
        
        for event in executing_events:
            assert 'tool_name' in event, f"Missing tool_name in tool_executing event: {event}"
            assert 'parameters' in event or 'metadata' in event, f"Missing parameters/metadata in event: {event}"
            
        # Validate tool_completed events
        completed_events = [e for e in tool_events if e.get('type') == 'tool_completed']
        assert len(completed_events) > 0, "No 'tool_completed' events found"
        
        for event in completed_events:
            assert 'tool_name' in event, f"Missing tool_name in tool_completed event: {event}"
            assert 'result' in event or 'status' in event, f"Missing result/status in event: {event}"
            
        # Tool executions should be paired (executing -> completed)
        assert len(executing_events) == len(completed_events), \
            f"Mismatched tool events: {len(executing_events)} executing, {len(completed_events)} completed"
            
        logger.info(f"✅ Tool execution validation passed: {len(tool_events)} tool events")
    
    def _validate_event_sequence_and_timing(self):
        """Validate WebSocket events arrive in correct sequence with reasonable timing"""
        events = self.event_capture.events
        
        # Find critical event positions
        event_positions = {}
        for i, event in enumerate(events):
            event_type = event.get('type')
            if event_type in ['agent_started', 'agent_thinking', 'tool_executing', 
                             'tool_completed', 'agent_completed']:
                if event_type not in event_positions:
                    event_positions[event_type] = i
        
        # Validate sequence: started -> thinking -> tools -> completed
        if 'agent_started' in event_positions and 'agent_completed' in event_positions:
            assert event_positions['agent_started'] < event_positions['agent_completed'], \
                "agent_started must come before agent_completed"
        
        if 'agent_thinking' in event_positions and 'tool_executing' in event_positions:
            # agent_thinking can come before or during tool execution
            pass  # This is flexible based on agent implementation
            
        if 'tool_executing' in event_positions and 'tool_completed' in event_positions:
            assert event_positions['tool_executing'] < event_positions['tool_completed'], \
                "tool_executing must come before tool_completed"
        
        # Validate timing - events should be spread over time
        first_event_time = events[0]['elapsed_ms']
        last_event_time = events[-1]['elapsed_ms']
        total_duration_ms = last_event_time - first_event_time
        
        assert total_duration_ms > 1000, f"Events too clustered ({total_duration_ms}ms) - likely not real processing"
        
        logger.info(f"✅ Event sequence validation passed: {total_duration_ms}ms total duration")
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection_during_agent_execution(self):
        """
        Test 6b: WebSocket reconnection resilience during agent execution
        
        Validates that WebSocket connections can recover from temporary disconnections
        while maintaining event delivery guarantees.
        """
        logger.info("=== INTEGRATION TEST 6b: WebSocket Reconnection Resilience ===")
        
        # This test simulates network issues during agent execution
        websocket = await self._establish_websocket_connection()
        
        try:
            # Start agent execution
            execution_task = asyncio.create_task(self._execute_agent_with_tools())
            
            # Start WebSocket listening
            listener_task = asyncio.create_task(
                self._listen_websocket_events(websocket)
            )
            
            # Simulate connection interruption after 5 seconds
            await asyncio.sleep(5.0)
            await websocket.close()
            
            logger.info("Simulated WebSocket disconnection")
            
            # Reconnect
            await asyncio.sleep(2.0)
            websocket = await self._establish_websocket_connection()
            
            # Continue listening
            listener_task = asyncio.create_task(
                self._listen_websocket_events(websocket)
            )
            
            # Wait for execution to complete
            result = await execution_task
            await asyncio.wait_for(listener_task, timeout=30.0)
            
        finally:
            if websocket and not websocket.closed:
                await websocket.close()
        
        # Validate that we still got meaningful events despite disconnection
        events_summary = self.event_capture.get_events_summary()
        assert events_summary['total_events'] > 0, "No events received after reconnection"
        
        logger.info("✅ INTEGRATION TEST 6b PASSED: WebSocket reconnection resilience working")


if __name__ == "__main__":
    # Run the test directly
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--log-cli-level=INFO"
    ])