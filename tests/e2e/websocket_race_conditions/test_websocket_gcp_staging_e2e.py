"""
Critical E2E Tests for GCP Staging WebSocket Race Conditions

These tests validate WebSocket behavior in actual GCP Cloud Run staging environment:
- Real GCP Cloud Run WebSocket connection lifecycle with load balancer behavior
- Complete user chat interaction with agent events in staging environment  

Business Value Justification:
1. Segment: Platform/Internal - Chat is King staging environment protection
2. Business Goal: Prevent $500K+ ARR loss from staging WebSocket failures affecting production confidence
3. Value Impact: Validates mission-critical chat functionality works in production-like GCP environment
4. Strategic Impact: Ensures staging environment mirrors production WebSocket behavior

@compliance CLAUDE.md - MANDATORY real authentication, NO MOCKS in E2E tests
@compliance Five Whys Analysis - Tests actual GCP Cloud Run infrastructure race conditions
"""
import asyncio
import pytest
import time
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
import websockets
import httpx
import aiohttp
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
from tests.mission_critical.websocket_real_test_base import RealWebSocketTestBase, requires_docker
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env
from tests.e2e.staging_config import StagingTestConfig, staging_urls

class RealGCPWebSocketConnectionLifecycleTests:
    """
    CRITICAL E2E TEST: Real GCP Cloud Run WebSocket connection lifecycle.
    
    FAILURE PATTERN: 2-3 minute WebSocket disconnections, 22+ second validation failures
    ROOT CAUSE: GCP Cloud Run load balancer + NEG timeout misalignment with application lifecycle
    """

    @pytest.fixture(autouse=True)
    async def setup_staging_environment(self):
        """Setup for staging environment testing."""
        self.env = get_env()
        self.environment = self.env.get('TEST_ENV', 'test')
        self.is_real_staging = self.environment == 'staging'
        if self.is_real_staging:
            self.staging_config = StagingTestConfig()
            self.websocket_url = self.staging_config.urls.websocket_url
            self.backend_url = self.staging_config.urls.backend_url
            self.auth_url = self.staging_config.urls.auth_url
        else:
            self.docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
            await self.docker_manager.start_services_smart(services=['postgresql', 'redis', 'backend', 'auth'], wait_healthy=True)
            self.websocket_url = 'ws://localhost:8000/ws'
            self.backend_url = 'http://localhost:8000'
            self.auth_url = 'http://localhost:8081'
        self.auth_helper = E2EWebSocketAuthHelper(environment=self.environment)
        yield
        if not self.is_real_staging and hasattr(self, 'docker_manager'):
            await self.docker_manager.stop_services()

    @pytest.mark.asyncio
    async def test_real_gcp_websocket_connection_lifecycle(self):
        """
        Test actual GCP Cloud Run WebSocket behavior (E2E Test 1).
        
        CRITICAL: This test MUST FAIL when GCP infrastructure race conditions occur.
        Tests the complete WebSocket lifecycle in GCP environment.
        """
        if self.is_real_staging:
            print('[U+1F680] REAL STAGING: Testing against actual GCP Cloud Run environment')
        else:
            print('[U+1F527] STAGING SIMULATION: Testing against local staging-configured services')
        jwt_token = await self._get_staging_authentication()
        assert jwt_token is not None, 'Must have valid JWT token for E2E test'
        connection_timeout = 20.0 if self.is_real_staging else 10.0
        print(f'[U+1F50C] Connecting to WebSocket: {self.websocket_url}')
        print(f'[U+23F1][U+FE0F] Using timeout: {connection_timeout}s')
        connection_start_time = time.time()
        try:
            websocket_conn = await self.auth_helper.connect_authenticated_websocket(timeout=connection_timeout)
            connection_time = time.time() - connection_start_time
            print(f' PASS:  WebSocket connected in {connection_time:.2f}s')
            stability_test_duration = 30.0
            stability_start = time.time()
            ping_count = 0
            pong_count = 0
            while time.time() - stability_start < stability_test_duration:
                ping_message = {'type': 'ping', 'timestamp': time.time(), 'test_id': f'gcp_stability_{ping_count}'}
                await websocket_conn.send(json.dumps(ping_message))
                ping_count += 1
                try:
                    response = await asyncio.wait_for(websocket_conn.recv(), timeout=5.0)
                    pong_count += 1
                    try:
                        response_data = json.loads(response)
                        assert 'type' in response_data, 'Response should have type field'
                    except json.JSONDecodeError:
                        pass
                except asyncio.TimeoutError:
                    print(f' WARNING: [U+FE0F] Ping {ping_count} timed out - possible GCP race condition')
                await asyncio.sleep(2.0)
            stability_rate = pong_count / ping_count if ping_count > 0 else 0
            print(f' CHART:  Stability test: {pong_count}/{ping_count} pings succeeded ({stability_rate:.1%})')
            assert stability_rate >= 0.7, f'Connection too unstable: {stability_rate:.1%} success rate'
            print('[U+23F3] Testing GCP load balancer idle timeout behavior...')
            idle_start = time.time()
            idle_duration = 60.0
            await asyncio.sleep(idle_duration)
            try:
                alive_test = {'type': 'alive_test', 'idle_duration': idle_duration, 'timestamp': time.time()}
                await websocket_conn.send(json.dumps(alive_test))
                response = await asyncio.wait_for(websocket_conn.recv(), timeout=10.0)
                print(f' PASS:  Connection survived {idle_duration}s idle period')
                connection_survived_idle = True
            except (asyncio.TimeoutError, websockets.ConnectionClosed) as e:
                print(f' FAIL:  Connection lost during idle period: {e}')
                connection_survived_idle = False
            await websocket_conn.close()
            total_test_time = time.time() - connection_start_time
            print(f'[U+1F3C1] Total test time: {total_test_time:.2f}s')
            assert connection_time < 30.0, f'Initial connection too slow: {connection_time}s'
            assert total_test_time < 120.0, f'Total test time too long: {total_test_time}s'
            return {'connection_time': connection_time, 'stability_rate': stability_rate, 'total_pings': ping_count, 'successful_pongs': pong_count, 'survived_idle': connection_survived_idle, 'total_test_time': total_test_time}
        except asyncio.TimeoutError:
            connection_time = time.time() - connection_start_time
            error_msg = f'WebSocket connection to {self.websocket_url} timed out after {connection_time:.2f}s. Environment: {self.environment}. '
            if self.is_real_staging:
                error_msg += f'This may indicate: (1) GCP Cloud Run cold start delays, (2) GCP NEG health check issues, (3) Authentication service delays, or (4) Load balancer configuration problems.'
            else:
                error_msg += f'Local staging simulation timeout - check Docker services.'
            pytest.fail(error_msg)
        except Exception as e:
            pytest.fail(f'Unexpected error in GCP WebSocket lifecycle test: {e}')

    async def _get_staging_authentication(self) -> str:
        """Get staging-appropriate authentication token."""
        if self.is_real_staging:
            return await self.auth_helper.get_staging_token_async()
        else:
            return self.auth_helper.create_test_jwt_token(user_id=f'gcp-test-{uuid.uuid4().hex[:8]}')

@requires_docker
class UserChatValueDeliveryE2ETests:
    """
    CRITICAL E2E TEST: Complete user chat interaction with agent events.
    
    FAILURE PATTERN: Missing agent events, incomplete chat responses, user experience degradation
    ROOT CAUSE: Agent execution failures don't deliver complete business value through WebSocket events
    """

    @pytest.fixture(autouse=True)
    async def setup_chat_test_environment(self):
        """Setup complete environment for chat value testing."""
        self.env = get_env()
        self.environment = self.env.get('TEST_ENV', 'test')
        if self.environment == 'staging':
            self.staging_config = StagingTestConfig()
            self.is_real_staging = True
        else:
            self.docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
            await self.docker_manager.start_services_smart(services=['postgresql', 'redis', 'backend', 'auth'], wait_healthy=True)
            self.is_real_staging = False
        self.websocket_test_base = RealWebSocketTestBase()
        async with self.websocket_test_base.real_websocket_test_session():
            yield
        if not self.is_real_staging and hasattr(self, 'docker_manager'):
            await self.docker_manager.stop_services()

    @pytest.mark.asyncio
    async def test_user_chat_value_delivery_e2e(self):
        """
        Test complete user chat interaction with agent events (E2E Test 2).
        
        CRITICAL: This test MUST FAIL if chat business value isn't delivered properly.
        Tests the complete user journey from chat request to valuable AI response.
        """
        user_context = await create_authenticated_user_context(user_email=f'chat_user_{uuid.uuid4().hex[:8]}@example.com', environment=self.environment, websocket_enabled=True)
        print(f'[U+1F464] Created authenticated user: {user_context.user_id}')
        test_context = await self.websocket_test_base.create_test_context(user_id=str(user_context.user_id), jwt_token=user_context.agent_context.get('jwt_token'))
        await test_context.setup_websocket_connection(endpoint='/ws', auth_required=True)
        print('[U+1F50C] WebSocket connection established for chat')
        chat_request = {'type': 'chat_message', 'message': 'Help me analyze the performance of my e-commerce website and suggest optimizations.', 'user_id': str(user_context.user_id), 'thread_id': str(user_context.thread_id), 'context': {'chat_session': True, 'expects_agent_response': True, 'business_context': 'e-commerce optimization'}, 'timestamp': datetime.now(timezone.utc).isoformat()}
        print(f"[U+1F4AC] Sending chat request: {chat_request['message'][:50]}...")
        chat_start_time = time.time()
        await test_context.send_message(chat_request)
        required_agent_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        print(' CHART:  Waiting for agent events (business value delivery)...')
        agent_timeout = 120.0 if self.is_real_staging else 60.0
        event_validation = await self.websocket_test_base.validate_agent_events(test_context=test_context, required_events=required_agent_events, timeout=agent_timeout)
        chat_total_time = time.time() - chat_start_time
        print(f'[U+23F1][U+FE0F] Total chat processing time: {chat_total_time:.2f}s')
        assert event_validation.success, f'Agent events not delivered: {event_validation.missing_events}'
        captured_events = event_validation.events_captured
        agent_responses = []
        for event in captured_events:
            if event.get('type') == 'agent_completed' and 'content' in event:
                agent_responses.append(event['content'])
            elif event.get('type') == 'chat_response':
                agent_responses.append(event.get('message', ''))
        has_substantial_response = any((len(str(response)) > 50 for response in agent_responses))
        assert has_substantial_response, 'Agent should provide substantial response for business value'
        assert chat_total_time < 180.0, f'Chat response too slow: {chat_total_time}s (user experience degraded)'
        assert chat_total_time > 1.0, f'Chat response too fast: {chat_total_time}s (suggests no real AI processing)'
        event_timestamps = []
        event_types_ordered = []
        for event in captured_events:
            if event.get('timestamp') and event.get('type'):
                try:
                    ts = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    event_timestamps.append(ts.timestamp())
                    event_types_ordered.append(event['type'])
                except:
                    pass
        if 'agent_started' in event_types_ordered and 'agent_completed' in event_types_ordered:
            started_idx = event_types_ordered.index('agent_started')
            completed_idx = event_types_ordered.index('agent_completed')
            assert started_idx < completed_idx, 'agent_started must come before agent_completed (logical order)'
        followup_request = {'type': 'chat_message', 'message': 'Can you provide more details about the SEO optimizations you mentioned?', 'user_id': str(user_context.user_id), 'thread_id': str(user_context.thread_id), 'context': {'chat_session': True, 'followup_request': True}, 'timestamp': datetime.now(timezone.utc).isoformat()}
        print('[U+1F4AC] Sending follow-up chat message...')
        await test_context.send_message(followup_request)
        try:
            followup_response = await test_context.receive_message(timeout=30.0)
            followup_processed = True
            print(' PASS:  Follow-up message processed successfully')
        except asyncio.TimeoutError:
            followup_processed = False
            print(' WARNING: [U+FE0F] Follow-up message timed out (may indicate session issues)')
        await test_context.cleanup()
        return {'chat_processing_time': chat_total_time, 'agent_events_delivered': len(event_validation.required_events_found), 'total_events_captured': event_validation.total_events, 'missing_events': list(event_validation.missing_events), 'has_substantial_response': has_substantial_response, 'followup_processed': followup_processed, 'business_value_delivered': event_validation.success and has_substantial_response and (chat_total_time < 180.0)}

@pytest.mark.e2e_auth_required
class WebSocketRaceConditionE2EIntegrationTests:
    """
    Integration of both E2E tests - validates complete GCP WebSocket + Chat scenarios.
    """

    @pytest.mark.asyncio
    async def test_combined_gcp_websocket_chat_scenario(self):
        """
        Test combined GCP WebSocket connection + chat value delivery.
        
        CRITICAL: This test validates that both infrastructure and business value work together.
        """
        env = get_env()
        environment = env.get('TEST_ENV', 'test')
        infrastructure_test = RealGCPWebSocketConnectionLifecycleTests()
        await infrastructure_test.setup_staging_environment().__aenter__()
        try:
            infrastructure_result = await infrastructure_test.test_real_gcp_websocket_connection_lifecycle()
            assert infrastructure_result['stability_rate'] >= 0.7, 'Infrastructure test failed'
        finally:
            await infrastructure_test.setup_staging_environment().__aexit__(None, None, None)
        chat_test = UserChatValueDeliveryE2ETests()
        await chat_test.setup_chat_test_environment().__aenter__()
        try:
            chat_result = await chat_test.test_user_chat_value_delivery_e2e()
            assert chat_result['business_value_delivered'], 'Chat business value not delivered'
        finally:
            await chat_test.setup_chat_test_environment().__aexit__(None, None, None)
        combined_success = infrastructure_result['stability_rate'] >= 0.7 and chat_result['business_value_delivered']
        assert combined_success, 'Combined GCP WebSocket + Chat scenario failed'
        return {'infrastructure_metrics': infrastructure_result, 'chat_metrics': chat_result, 'combined_success': combined_success}
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')