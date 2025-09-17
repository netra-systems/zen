""""""
E2E Test: WebSocket Event Structure Validation (Staging GCP)

PURPOSE: End-to-end validation of WebSocket event structure in staging environment
REPRODUCES: Issue #1021 - Business fields buried in 'data' wrapper

EXPECTED FAILURE: These tests should FAIL until structural issue is resolved
ENVIRONMENT: Staging GCP deployment only (no Docker)
""""""
import pytest
import asyncio
import json
import websockets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import os
from unittest.mock import patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from auth_service.auth_core.test_utilities.auth_test_harness import AuthAgentFlowHarness

class WebSocketEventStructureE2ETests(SSotAsyncTestCase):
    "E2E validation of WebSocket event structure in staging environment"""

    async def asyncSetUp(self):
        "Set up E2E test environment"
        await super().asyncSetUp()
        if os.environ.get('TEST_ENV') != 'staging':
            pytest.skip('E2E tests require staging environment')
        self.staging_ws_url = 'wss://netra-staging-websocket.run.app/ws'
        self.staging_api_base = 'https://netra-staging-backend.run.app'
        self.harness = AuthAgentFlowHarness()
        await self.harness.setup_auth_client()
        self.test_user = self.harness.test_user
        self.auth_token = None
        self.captured_events = []

    async def setup_staging_websocket_connection(self):
        "Set up authenticated WebSocket connection to staging"
        if not self.auth_token:
            login_response = await self.harness.auth_client.post(f'{self.staging_api_base}/auth/login', json={'email': self.test_user['email'], 'password': self.test_user['password']}
            auth_data = login_response.json()
            self.auth_token = auth_data['access_token']
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        self.websocket = await websockets.connect(f'{self.staging_ws_url}?token={self.auth_token}', extra_headers=headers)
        return self.websocket

    async def start_agent_conversation(self, user_message: str) -> str:
        Start agent conversation and return conversation ID""
        response = await self.harness.auth_client.post(f'{self.staging_api_base}/chat/start', headers={'Authorization': f'Bearer {self.auth_token}'}, json={'message': user_message}
        chat_data = response.json()
        return chat_data['conversation_id']

    async def capture_websocket_events(self, duration_seconds: int=10):
        Capture WebSocket events for specified duration""
        self.captured_events.clear()
        end_time = datetime.now() + timedelta(seconds=duration_seconds)
        try:
            while datetime.now() < end_time:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    event_data = json.loads(message)
                    self.captured_events.append(event_data)
                    if event_data.get('type') == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    continue
        except Exception as e:
            print(f'Error capturing events: {e}')
        return self.captured_events

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_agent_execution_event_structure(self):
""""""
        Test complete agent execution event structure in staging
        EXPECTED FAILURE: Events should have business fields at top level
""""""
        websocket = await self.setup_staging_websocket_connection()
        try:
            conversation_id = await self.start_agent_conversation('Analyze the current market trends for tech stocks')
            events = await self.capture_websocket_events(duration_seconds=15)
            event_types = [event.get('type') for event in events]
            expected_types = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            self.assertIn('agent_started', event_types, 'Should receive agent_started event')
            for event in events:
                event_type = event.get('type')
                if event_type == 'agent_started':
                    self.validate_agent_started_structure(event)
                elif event_type == 'agent_thinking':
                    self.validate_agent_thinking_structure(event)
                elif event_type == 'tool_executing':
                    self.validate_tool_executing_structure(event)
                elif event_type == 'tool_completed':
                    self.validate_tool_completed_structure(event)
                elif event_type == 'agent_completed':
                    self.validate_agent_completed_structure(event)
        finally:
            await websocket.close()

    def validate_agent_started_structure(self, event: Dict[str, Any]:
""""""
        Validate agent_started event structure
        EXPECTED FAILURE: Business fields should be at top level
""""""
        self.assertEqual(event.get('type'), 'agent_started')
        self.assertIn('agent_type', event, 'agent_type should be at top level of agent_started event')
        self.assertIn('run_id', event, 'run_id should be at top level of agent_started event')
        self.assertIn('user_id', event, 'user_id should be at top level of agent_started event')
        if 'data' in event and 'agent_type' in event['data']:
            self.fail("agent_type should not be buried in 'data' wrapper)"

    def validate_agent_thinking_structure(self, event: Dict[str, Any]:
        
        Validate agent_thinking event structure
        EXPECTED FAILURE: Thinking content should be at top level
""
        self.assertEqual(event.get('type'), 'agent_thinking')
        self.assertIn('thinking_content', event, 'thinking_content should be at top level of agent_thinking event')
        if 'data' in event and 'thinking_content' in event['data']:
            self.fail(thinking_content should not be buried in 'data' wrapper)

    def validate_tool_executing_structure(self, event: Dict[str, Any]:
        ""
        Validate tool_executing event structure
        EXPECTED FAILURE: Tool details should be at top level

        self.assertEqual(event.get('type'), 'tool_executing')
        self.assertIn('tool_name', event, 'tool_name should be at top level of tool_executing event')
        self.assertIn('tool_description', event, 'tool_description should be at top level of tool_executing event')
        if 'data' in event and 'tool_name' in event['data']:
            self.fail("tool_name should not be buried in 'data' wrapper)"

    def validate_tool_completed_structure(self, event: Dict[str, Any]:
        
        Validate tool_completed event structure  
        EXPECTED FAILURE: Tool results should be at top level
""
        self.assertEqual(event.get('type'), 'tool_completed')
        self.assertIn('tool_name', event, 'tool_name should be at top level of tool_completed event')
        self.assertIn('result', event, 'result should be at top level of tool_completed event')
        self.assertIn('status', event, 'status should be at top level of tool_completed event')
        if 'data' in event and 'result' in event['data']:
            self.fail(result should not be buried in 'data' wrapper)

    def validate_agent_completed_structure(self, event: Dict[str, Any]:
""""""
        Validate agent_completed event structure
        EXPECTED FAILURE: Response content should be at top level
""""""
        self.assertEqual(event.get('type'), 'agent_completed')
        self.assertIn('response', event, 'response should be at top level of agent_completed event')
        self.assertIn('run_id', event, 'run_id should be at top level of agent_completed event')
        if 'data' in event and 'response' in event['data']:
            self.fail(response should not be buried in 'data' wrapper)""

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_frontend_event_parsing_compatibility(self):
""""""
        Test WebSocket event structure compatibility with frontend parsing
        EXPECTED FAILURE: Current structure may break frontend event handling
""""""
        websocket = await self.setup_staging_websocket_connection()
        try:
            conversation_id = await self.start_agent_conversation("What's the weather like?)"
            events = await self.capture_websocket_events(duration_seconds=8)
            for event in events:
                event_type = event.get('type')
                if event_type == 'agent_started':
                    agent_type = event.get('agent_type')
                    self.assertIsNotNone(agent_type, 'Frontend requires direct access to agent_type')
                    run_id = event.get('run_id')
                    self.assertIsNotNone(run_id, 'Frontend requires direct access to run_id')
                elif event_type == 'agent_thinking':
                    thinking_content = event.get('thinking_content')
                    self.assertIsNotNone(thinking_content, 'Frontend requires direct access to thinking_content')
                elif event_type == 'tool_executing':
                    tool_name = event.get('tool_name')
                    self.assertIsNotNone(tool_name, 'Frontend requires direct access to tool_name')
                elif event_type == 'agent_completed':
                    response = event.get('response')
                    self.assertIsNotNone(response, 'Frontend requires direct access to response')
                if 'data' in event and isinstance(event['data'], dict):
                    for key in event['data']:
                        self.fail(fBusiness field '{key}' should not be buried in 'data' wrapper - frontend cannot access it)
        finally:
            await websocket.close()

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_real_time_event_streaming_structure(self):
    ""
        Test real-time event streaming maintains consistent structure
        EXPECTED FAILURE: Structure inconsistencies may affect real-time UX
        
        websocket = await self.setup_staging_websocket_connection()
        try:
            conversation_id = await self.start_agent_conversation('Give me a detailed analysis of the current cryptocurrency market trends')
            streaming_events = []
            timeout = 20
            start_time = datetime.now()
            while (datetime.now() - start_time).seconds < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event = json.loads(message)
                    streaming_events.append(event)
                    self.validate_streaming_event_structure(event)
                    if event.get('type') == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    continue
            self.assertGreater(len(streaming_events), 0, 'Should have received streaming events')
            for event in streaming_events:
                self.assertIn('type', event, All events should have 'type' field")"
                self.assertIn('timestamp', event, All events should have 'timestamp')
                if 'data' in event and isinstance(event['data'], dict):
                    business_fields = ['agent_type', 'run_id', 'thinking_content', 'tool_name', 'response', 'result']
                    for field in business_fields:
                        if field in event['data']:
                            self.fail(fBusiness field '{field}' buried in data wrapper affects real-time UX)""
        finally:
            await websocket.close()

    def validate_streaming_event_structure(self, event: Dict[str, Any]:
""""""
        Validate individual streaming event structure
        EXPECTED FAILURES: Business fields should be directly accessible
""""""
        event_type = event.get('type')
        if event_type in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
            self.assertIn('timestamp', event, f'{event_type} should have timestamp at top level')
            if 'data' in event:
                self.assertIsInstance(event['data'], (dict, type(None)), 'If data exists, it should be dict or None')
                if isinstance(event['data'], dict) and len(event['data'] > 0:
                    business_fields = list(event['data'].keys())
                    if business_fields:
                        self.fail(fBusiness fields {business_fields} should not be in 'data' wrapper for {event_type}")"
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')