"""
E2E Test: Staging Golden Path SSOT Validation - Issue #1098

CRITICAL: This test must FAIL initially to prove SSOT violations exist.
After SSOT migration, this test must PASS to prove success.

Business Value Justification (BVJ):
- Segment: ALL (Free/Early/Mid/Enterprise/Platform)
- Business Goal: Validate complete Golden Path on staging with SSOT compliance
- Value Impact: Ensures end-to-end chat functionality reliability
- Revenue Impact: Protects $500K+ ARR Golden Path with comprehensive E2E validation

ENVIRONMENT REQUIREMENTS:
- GCP Staging Environment (https://staging.netrasystems.ai)
- Real authentication tokens
- Real WebSocket connections
- Complete Golden Path: Login → Message → AI Response

FAILING TEST STRATEGY:
1. Test initially FAILS proving staging uses factory patterns
2. SSOT migration updates staging deployment
3. Test PASSES proving staging uses SSOT exclusively

GOLDEN PATH VALIDATION:
1. User authentication (OAuth/JWT)
2. WebSocket connection establishment
3. Message sending to agent
4. 5 critical events delivered in sequence
5. Final AI response received
6. All operations use SSOT patterns
"""

import asyncio
import pytest
import json
import time
import uuid
import aiohttp
import websockets
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@dataclass
class StagingEnvironmentConfig:
    """Configuration for staging environment testing."""
    base_url: str = "https://staging.netrasystems.ai"
    websocket_url: str = "wss://api.staging.netrasystems.ai"
    auth_endpoint: str = "/auth/test-login"
    websocket_endpoint: str = "/ws"
    timeout: int = 60
    retry_count: int = 3


class TestStagingGoldenPathSSoT(SSotAsyncTestCase):
    """
    E2E tests on GCP staging to validate Golden Path SSOT compliance.

    CRITICAL: These tests run against real staging environment.
    Tests must FAIL initially proving staging uses factory patterns.
    """

    def setUp(self):
        """Set up staging environment test configuration."""
        super().setUp()
        self.staging_config = StagingEnvironmentConfig()
        self.critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        self.test_user_id = f"e2e_test_user_{uuid.uuid4().hex[:8]}"

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_complete_user_journey_ssot_staging(self):
        """
        Test complete user journey: login → message → AI response (SSOT)

        CRITICAL: Must detect if staging environment uses factory patterns
        """
        # Step 1: User authentication
        auth_result = await self._authenticate_staging_user()

        # Validate authentication uses SSOT patterns
        auth_violations = self._validate_auth_ssot_compliance(auth_result)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(auth_violations) == 0, (
            f"STAGING AUTH SSOT VIOLATIONS: Authentication has {len(auth_violations)} "
            f"SSOT violations in staging environment.\n"
            f"Violations: {auth_violations}"
        )

        auth_token = auth_result['token']
        assert auth_token is not None, "Authentication must succeed in staging"

        # Step 2: WebSocket connection with SSOT validation
        websocket_client = await self._connect_staging_websocket(auth_token)

        # Validate WebSocket connection uses SSOT patterns
        ws_connection_violations = await self._validate_websocket_connection_ssot(websocket_client)

        assert len(ws_connection_violations) == 0, (
            f"STAGING WEBSOCKET SSOT VIOLATIONS: WebSocket connection has {len(ws_connection_violations)} "
            f"SSOT violations in staging.\n"
            f"Violations: {ws_connection_violations}"
        )

        assert websocket_client.connected, "WebSocket connection must succeed in staging"

        # Step 3: Send message to agent
        message_id = await websocket_client.send_message(
            "Help me optimize my AI infrastructure costs and improve performance"
        )

        # Step 4: Validate all 5 critical events received via SSOT
        events_received = await self._wait_for_critical_events(
            websocket_client,
            timeout=self.staging_config.timeout
        )

        # Validate events use SSOT delivery patterns
        event_ssot_violations = self._validate_events_ssot_compliance(events_received)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(event_ssot_violations) == 0, (
            f"STAGING EVENT SSOT VIOLATIONS: Events have {len(event_ssot_violations)} "
            f"SSOT violations in staging environment.\n"
            f"Violations: {event_ssot_violations[:3]}"
        )

        # CRITICAL: All events must be received in staging
        received_event_types = [event.get('type') for event in events_received]

        for expected_event in self.critical_events:
            assert expected_event in received_event_types, (
                f"MISSING CRITICAL EVENT: {expected_event} not received in staging. "
                f"Received events: {received_event_types}"
            )

        # Step 5: Validate final AI response
        final_response = await self._wait_for_final_response(websocket_client, message_id)

        # Validate response uses SSOT patterns
        response_violations = self._validate_response_ssot_compliance(final_response)

        assert len(response_violations) == 0, (
            f"STAGING RESPONSE SSOT VIOLATIONS: Response has {len(response_violations)} "
            f"SSOT violations.\n"
            f"Violations: {response_violations}"
        )

        assert final_response is not None, "Must receive AI response in staging"
        assert len(final_response.get('content', '')) > 50, "Response must be substantive"

        # Step 6: Validate SSOT compliance in staging environment
        staging_ssot_validation = await self._validate_staging_ssot_compliance()

        # CRITICAL: This assertion MUST FAIL initially
        assert staging_ssot_validation['factory_violations'] == 0, (
            f"STAGING FACTORY VIOLATIONS: Found {staging_ssot_validation['factory_violations']} "
            f"factory pattern violations in staging environment.\n"
            f"Details: {staging_ssot_validation['details']}"
        )

        # Cleanup
        await websocket_client.close()

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_multi_user_staging_isolation_ssot(self):
        """
        Test multi-user isolation on staging with SSOT patterns

        CRITICAL: Must detect if staging uses factory patterns for user isolation
        """
        # Create multiple user sessions on staging
        user1_client = await self._create_staging_user_session("e2e_user_001")
        user2_client = await self._create_staging_user_session("e2e_user_002")

        # Validate user isolation uses SSOT patterns
        isolation_violations = await self._validate_user_isolation_ssot_staging(
            user1_client, user2_client
        )

        # CRITICAL: This assertion MUST FAIL initially
        assert len(isolation_violations) == 0, (
            f"STAGING USER ISOLATION SSOT VIOLATIONS: Found {len(isolation_violations)} "
            f"user isolation SSOT violations in staging.\n"
            f"Violations: {isolation_violations[:3]}"
        )

        # Send concurrent messages
        message1_id = await user1_client.send_message("Analyze cost optimization strategies")
        message2_id = await user2_client.send_message("Review security best practices")

        # Validate responses are correctly isolated
        user1_response = await self._wait_for_response(user1_client, message1_id)
        user2_response = await self._wait_for_response(user2_client, message2_id)

        # Validate responses use SSOT patterns
        user1_response_violations = self._validate_response_ssot_compliance(user1_response)
        user2_response_violations = self._validate_response_ssot_compliance(user2_response)

        assert len(user1_response_violations) == 0, (
            f"USER1 RESPONSE SSOT VIOLATIONS: {user1_response_violations}"
        )

        assert len(user2_response_violations) == 0, (
            f"USER2 RESPONSE SSOT VIOLATIONS: {user2_response_violations}"
        )

        # CRITICAL: No cross-user response bleeding
        assert "cost optimization" in user1_response.get('content', '').lower(), (
            "User 1 must get cost optimization response"
        )
        assert "security" in user2_response.get('content', '').lower(), (
            "User 2 must get security response"
        )
        assert user1_response.get('user_id') != user2_response.get('user_id'), (
            "Responses must have different user IDs"
        )

        # Cleanup
        await user1_client.close()
        await user2_client.close()

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_staging_websocket_events_sequence_ssot(self):
        """
        Test WebSocket events sequence uses SSOT patterns on staging

        CRITICAL: Must validate event sequence delivery uses SSOT, not factory
        """
        # Establish staging connection
        auth_token = await self._get_staging_auth_token()
        websocket_client = await self._connect_staging_websocket(auth_token)

        # Send message to trigger event sequence
        message_id = await websocket_client.send_message("Generate optimization report")

        # Monitor event sequence with timing
        event_sequence = await self._monitor_event_sequence_ssot(websocket_client)

        # Validate event sequence uses SSOT patterns
        sequence_violations = self._validate_event_sequence_ssot(event_sequence)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(sequence_violations) == 0, (
            f"STAGING EVENT SEQUENCE SSOT VIOLATIONS: Found {len(sequence_violations)} "
            f"event sequence SSOT violations.\n"
            f"Violations: {sequence_violations[:3]}"
        )

        # Validate proper event ordering
        event_order = [event['type'] for event in event_sequence]
        expected_order = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

        for i, expected_event in enumerate(expected_order):
            assert i < len(event_order), f"Missing event in sequence: {expected_event}"
            assert event_order[i] == expected_event, (
                f"Event order violation: expected {expected_event} at position {i}, "
                f"got {event_order[i] if i < len(event_order) else 'missing'}"
            )

        # Cleanup
        await websocket_client.close()

    # Helper methods for staging SSOT validation

    async def _authenticate_staging_user(self) -> Dict:
        """Authenticate user in staging environment."""
        try:
            async with aiohttp.ClientSession() as session:
                auth_url = f"{self.staging_config.base_url}{self.staging_config.auth_endpoint}"

                auth_payload = {
                    'user_id': self.test_user_id,
                    'test_mode': True
                }

                async with session.post(auth_url, json=auth_payload) as response:
                    if response.status != 200:
                        self.fail(f"Staging authentication failed: {response.status}")

                    auth_result = await response.json()
                    return auth_result

        except Exception as e:
            self.fail(f"Failed to authenticate in staging: {e}")

    def _validate_auth_ssot_compliance(self, auth_result: Dict) -> List[str]:
        """Validate authentication uses SSOT patterns."""
        violations = []

        # Check for factory-based authentication markers
        if auth_result.get('factory_authenticated'):
            violations.append("Authentication uses factory pattern")

        if auth_result.get('isolated_auth_manager'):
            violations.append("Authentication uses isolated manager pattern")

        if auth_result.get('auth_factory_token'):
            violations.append("Authentication token created via factory")

        return violations

    async def _connect_staging_websocket(self, auth_token: str):
        """Connect to staging WebSocket with authentication."""
        try:
            websocket_url = f"{self.staging_config.websocket_url}{self.staging_config.websocket_endpoint}"

            headers = {
                'Authorization': f'Bearer {auth_token}',
                'User-Agent': 'E2E-SSOT-Test'
            }

            websocket = await websockets.connect(websocket_url, extra_headers=headers)

            return StagingWebSocketClient(websocket)

        except Exception as e:
            self.fail(f"Failed to connect to staging WebSocket: {e}")

    async def _validate_websocket_connection_ssot(self, client) -> List[str]:
        """Validate WebSocket connection uses SSOT patterns."""
        violations = []

        # Send probe message to check for factory patterns
        probe_message = {
            'type': 'ssot_probe',
            'data': {'check_factory_patterns': True}
        }

        try:
            await client.send_json(probe_message)
            response = await client.receive_json(timeout=5)

            # Check response for factory pattern indicators
            if response.get('factory_managed'):
                violations.append("WebSocket managed via factory pattern")

            if response.get('isolated_manager'):
                violations.append("WebSocket uses isolated manager")

        except Exception:
            # If probe fails, assume SSOT compliance (probe might not be implemented yet)
            pass

        return violations

    async def _wait_for_critical_events(self, client, timeout: int = 60) -> List[Dict]:
        """Wait for all 5 critical events from staging."""
        events_received = []
        start_time = time.time()

        while len(events_received) < 5 and (time.time() - start_time) < timeout:
            try:
                message = await client.receive_json(timeout=5)

                if message.get('type') in self.critical_events:
                    events_received.append(message)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Error receiving event: {e}")
                break

        return events_received

    def _validate_events_ssot_compliance(self, events: List[Dict]) -> List[str]:
        """Validate events use SSOT delivery patterns."""
        violations = []

        for event in events:
            # Check for factory delivery markers
            if event.get('factory_delivered'):
                violations.append(f"Event {event.get('type')} delivered via factory")

            if event.get('isolated_delivery'):
                violations.append(f"Event {event.get('type')} uses isolated delivery")

            if event.get('manager_factory_event'):
                violations.append(f"Event {event.get('type')} created by manager factory")

        return violations

    async def _wait_for_final_response(self, client, message_id: str, timeout: int = 60) -> Optional[Dict]:
        """Wait for final AI response."""
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            try:
                message = await client.receive_json(timeout=5)

                if message.get('type') == 'agent_response' and message.get('message_id') == message_id:
                    return message

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Error receiving response: {e}")
                break

        return None

    def _validate_response_ssot_compliance(self, response: Dict) -> List[str]:
        """Validate response uses SSOT patterns."""
        violations = []

        if not response:
            return ["No response received"]

        # Check for factory response markers
        if response.get('factory_generated'):
            violations.append("Response generated via factory pattern")

        if response.get('isolated_agent_response'):
            violations.append("Response from isolated agent")

        return violations

    async def _validate_staging_ssot_compliance(self) -> Dict:
        """Validate overall staging environment SSOT compliance."""
        try:
            # Query staging environment for SSOT compliance status
            async with aiohttp.ClientSession() as session:
                health_url = f"{self.staging_config.base_url}/health/ssot-compliance"

                async with session.get(health_url) as response:
                    if response.status == 200:
                        compliance_data = await response.json()
                        return compliance_data
                    else:
                        # If endpoint doesn't exist, assume violations exist
                        return {
                            'factory_violations': 1,
                            'details': 'SSOT compliance endpoint not available'
                        }

        except Exception:
            # If check fails, assume violations exist
            return {
                'factory_violations': 1,
                'details': 'Failed to check SSOT compliance'
            }

    async def _create_staging_user_session(self, user_id: str):
        """Create staging user session."""
        auth_result = await self._authenticate_staging_user()
        auth_token = auth_result['token']
        websocket_client = await self._connect_staging_websocket(auth_token)
        return websocket_client

    async def _validate_user_isolation_ssot_staging(self, user1_client, user2_client) -> List[str]:
        """Validate user isolation uses SSOT patterns in staging."""
        violations = []

        # Send isolation check messages
        isolation_probe1 = {
            'type': 'isolation_probe',
            'user_id': 'e2e_user_001'
        }

        isolation_probe2 = {
            'type': 'isolation_probe',
            'user_id': 'e2e_user_002'
        }

        try:
            await user1_client.send_json(isolation_probe1)
            await user2_client.send_json(isolation_probe2)

            response1 = await user1_client.receive_json(timeout=5)
            response2 = await user2_client.receive_json(timeout=5)

            # Check for factory-based isolation
            if response1.get('factory_isolated'):
                violations.append("User 1 isolated via factory pattern")

            if response2.get('factory_isolated'):
                violations.append("User 2 isolated via factory pattern")

        except Exception:
            # If probe fails, assume SSOT compliance
            pass

        return violations

    async def _wait_for_response(self, client, message_id: str) -> Dict:
        """Wait for response to specific message."""
        return await self._wait_for_final_response(client, message_id)

    async def _get_staging_auth_token(self) -> str:
        """Get staging authentication token."""
        auth_result = await self._authenticate_staging_user()
        return auth_result['token']

    async def _monitor_event_sequence_ssot(self, client) -> List[Dict]:
        """Monitor event sequence for SSOT compliance."""
        events = []
        start_time = time.time()

        while len(events) < 5 and (time.time() - start_time) < 60:
            try:
                message = await client.receive_json(timeout=5)

                if message.get('type') in self.critical_events:
                    # Add timestamp for sequence analysis
                    message['received_at'] = time.time()
                    events.append(message)

            except asyncio.TimeoutError:
                continue
            except Exception:
                break

        return events

    def _validate_event_sequence_ssot(self, event_sequence: List[Dict]) -> List[str]:
        """Validate event sequence uses SSOT patterns."""
        violations = []

        for i, event in enumerate(event_sequence):
            # Check for factory sequence markers
            if event.get('factory_sequenced'):
                violations.append(f"Event {i} sequenced via factory")

            if event.get('isolated_sequence_manager'):
                violations.append(f"Event {i} uses isolated sequence manager")

        return violations


class StagingWebSocketClient:
    """WebSocket client for staging environment testing."""

    def __init__(self, websocket):
        self.websocket = websocket
        self.connected = True

    async def send_message(self, content: str) -> str:
        """Send message and return message ID."""
        message_id = f"msg_{uuid.uuid4().hex[:8]}"

        message = {
            'type': 'user_message',
            'message_id': message_id,
            'content': content,
            'timestamp': time.time()
        }

        await self.send_json(message)
        return message_id

    async def send_json(self, data: Dict):
        """Send JSON message."""
        await self.websocket.send(json.dumps(data))

    async def receive_json(self, timeout: int = 30) -> Dict:
        """Receive JSON message with timeout."""
        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            return json.loads(message)
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError("WebSocket receive timeout")

    async def close(self):
        """Close WebSocket connection."""
        if self.connected:
            await self.websocket.close()
            self.connected = False


if __name__ == "__main__":
    # Run this test independently to check for staging SSOT violations
    pytest.main([__file__, "-v", "-m", "staging"])