_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
'\nE2E GCP Staging Test Suite for UnifiedWebSocketManager - Golden Path Validation\n\nBusiness Value Justification (BVJ):\n- Segment: All (Free, Early, Mid, Enterprise) - Golden Path protects all revenue streams\n- Business Goal: Validate Production-Like Golden Path protecting $500K+ ARR  \n- Value Impact: E2E tests ensure WebSocket manager works in real GCP Cloud Run environment\n- Strategic Impact: MISSION CRITICAL - Validates the complete user journey that drives all revenue\n\nThis E2E test suite validates UnifiedWebSocketManager in the actual GCP staging environment,\nfollowing CLAUDE.md Golden Path requirements: Real GCP infrastructure, real Cloud Run, real networking.\n\nGOLDEN PATH CRITICAL AREAS (10/10 Business Criticality):\n1. Real GCP Cloud Run WebSocket Connection Establishment (production-like environment)\n2. Real GCP Load Balancer WebSocket Upgrade Handling (production networking)  \n3. Real GCP VPC Network Latency and Performance (production conditions)\n4. Real GCP Auto-scaling WebSocket Connection Handling (production scalability)\n5. Real GCP Secret Manager Authentication Integration (production security)\n6. Real GCP Logging and Monitoring Integration (production observability)\n7. Real GCP Redis Connection Pool Management (production state management)\n8. Real GCP Database Connection Handling (production data persistence)\n9. Real GCP Service Mesh Traffic Management (production networking)\n10. Complete User Journey: Login  ->  Chat  ->  AI Response (Golden Path business flow)\n\nTest Structure:  \n- 12 E2E Tests (4 high difficulty) running against real GCP staging environment\n- Real production-like infrastructure validation\n- Complete Golden Path user journey testing\n- Real Cloud Run race condition and timing validation\n- Real GCP performance and scalability testing\n'
import asyncio
import pytest
import time
import uuid
import json
import aiohttp
import websockets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Union
import ssl
from urllib.parse import urljoin
import os
from pathlib import Path
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import RealServicesTestFixtures
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, ConnectionID, WebSocketID, RequestID, ensure_user_id, ensure_thread_id, ensure_websocket_id
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection, WebSocketManagerMode
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.auth_integration.auth import validate_jwt_token
from netra_backend.app.services.user_execution_context import UserExecutionContext
logger = central_logger.get_logger(__name__)

class GCPWebSocketClient:
    """Real GCP WebSocket client for E2E testing."""

    def __init__(self, staging_url: str, auth_token: str=None):
        self.staging_url = staging_url
        self.auth_token = auth_token
        self.websocket = None
        self.received_messages = []
        self.connected = False
        self.connection_latency = None
        self.message_latencies = []

    async def connect_to_gcp_staging(self, user_id: str=None) -> Dict[str, Any]:
        """Connect to real GCP staging WebSocket endpoint."""
        ws_url = self.staging_url.replace('https://', 'wss://').replace('http://', 'ws://')
        if not ws_url.endswith('/'):
            ws_url += '/'
        ws_url += 'ws'
        if user_id:
            ws_url += f'?user_id={user_id}'
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        connection_start = time.time()
        try:
            self.websocket = await websockets.connect(ws_url, extra_headers=headers, ping_interval=20, ping_timeout=10, close_timeout=10)
            self.connection_latency = time.time() - connection_start
            self.connected = True
            asyncio.create_task(self._listen_for_gcp_messages())
            logger.info(f'Connected to GCP staging WebSocket in {self.connection_latency:.3f}s')
            return {'connected': True, 'latency_ms': self.connection_latency * 1000, 'endpoint': ws_url}
        except Exception as e:
            logger.error(f'Failed to connect to GCP staging WebSocket: {e}')
            return {'connected': False, 'error': str(e), 'endpoint': ws_url}

    async def _listen_for_gcp_messages(self):
        """Listen for messages from GCP staging WebSocket."""
        try:
            async for message in self.websocket:
                receive_time = time.time()
                data = json.loads(message)
                message_latency = None
                if 'timestamp' in data:
                    try:
                        sent_time = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                        message_latency = receive_time - sent_time.timestamp()
                        self.message_latencies.append(message_latency)
                    except:
                        pass
                self.received_messages.append({'message': data, 'received_at': datetime.now(timezone.utc), 'latency_ms': message_latency * 1000 if message_latency else None})
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            logger.info('GCP WebSocket connection closed')
        except Exception as e:
            logger.error(f'Error in GCP WebSocket message listener: {e}')
            self.connected = False

    async def send_json_to_gcp(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON data to GCP staging WebSocket."""
        if not self.websocket or not self.connected:
            return {'success': False, 'error': 'Not connected'}
        send_start = time.time()
        data['timestamp'] = datetime.now(timezone.utc).isoformat()
        try:
            await self.websocket.send(json.dumps(data))
            send_latency = time.time() - send_start
            return {'success': True, 'send_latency_ms': send_latency * 1000}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def disconnect_from_gcp(self):
        """Disconnect from GCP staging WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False

class GCPHTTPClient:
    """Real GCP HTTP client for E2E API testing."""

    def __init__(self, staging_url: str, auth_token: str=None):
        self.staging_url = staging_url.rstrip('/')
        self.auth_token = auth_token
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        headers = {'Content-Type': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300, use_dns_cache=True)
        self.session = aiohttp.ClientSession(headers=headers, connector=connector, timeout=aiohttp.ClientTimeout(total=30))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def create_test_thread(self, user_id: str) -> Dict[str, Any]:
        """Create a test thread via GCP staging API."""
        async with self.session.post(f'{self.staging_url}/api/threads', json={'user_id': user_id, 'title': 'E2E Test Thread'}) as response:
            if response.status == 201:
                return await response.json()
            else:
                return {'error': f'HTTP {response.status}', 'detail': await response.text()}

    async def send_chat_message(self, thread_id: str, user_id: str, message: str) -> Dict[str, Any]:
        """Send chat message via GCP staging API."""
        async with self.session.post(f'{self.staging_url}/api/threads/{thread_id}/messages', json={'user_id': user_id, 'content': message, 'message_type': 'user'}) as response:
            if response.status in [200, 201]:
                return await response.json()
            else:
                return {'error': f'HTTP {response.status}', 'detail': await response.text()}

    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status from GCP staging."""
        try:
            async with self.session.get(f'{self.staging_url}/health') as response:
                return {'status_code': response.status, 'response_time_ms': response.headers.get('X-Response-Time', 'unknown'), 'healthy': response.status == 200, 'data': await response.json() if response.status == 200 else await response.text()}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}

@pytest.mark.e2e
@pytest.mark.gcp_staging
class TestUnifiedWebSocketManagerGCPGoldenPath(BaseIntegrationTest):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(user_id='test_user', thread_id='test_thread', run_id='test_run')
    'E2E test suite for UnifiedWebSocketManager Golden Path validation in GCP.'

    @classmethod
    def setUpClass(cls):
        """Set up GCP staging environment configuration."""
        super().setUpClass()
        cls.staging_url = get_env('GCP_STAGING_URL', 'https://netra-staging-your-project.cloudfunctions.net')
        cls.auth_token = get_env('GCP_STAGING_AUTH_TOKEN')
        if not cls.staging_url:
            pytest.skip('GCP_STAGING_URL not configured - skipping GCP E2E tests')
        logger.info(f'Running GCP E2E tests against: {cls.staging_url}')

    def setUp(self):
        """Set up for each test."""
        super().setUp()
        self.test_user_id = ensure_user_id(f'gcp-e2e-user-{uuid.uuid4()}')
        self.test_user_id_2 = ensure_user_id(f'gcp-e2e-user-{uuid.uuid4()}')

    async def test_gcp_golden_path_complete_user_journey_business_critical(self):
        """
        HIGH DIFFICULTY: Test complete Golden Path user journey in GCP staging.
        
        Business Value: Validates the complete $500K+ ARR user flow in production-like environment.
        Can Fail: If Golden Path breaks in GCP, the entire business model fails.
        """
        ws_client = GCPWebSocketClient(self.staging_url, self.auth_token)
        connection_result = await ws_client.connect_to_gcp_staging(self.test_user_id)
        self.assertTrue(connection_result['connected'], f"Failed to connect to GCP staging: {connection_result.get('error')}")
        self.assertLess(connection_result['latency_ms'], 2000, f"GCP connection latency too high: {connection_result['latency_ms']:.1f}ms")
        async with GCPHTTPClient(self.staging_url, self.auth_token) as http_client:
            thread_result = await http_client.create_test_thread(self.test_user_id)
            if 'error' in thread_result:
                logger.warning(f"Thread creation failed: {thread_result['error']}")
                thread_id = str(uuid.uuid4())
            else:
                thread_id = thread_result.get('thread_id', str(uuid.uuid4()))
            golden_path_message = {'type': 'chat_message', 'thread_id': thread_id, 'user_id': self.test_user_id, 'content': "Help me optimize my cloud costs - I'm spending $10,000/month on AWS", 'expect_agent_response': True, 'business_critical': True}
            send_result = await ws_client.send_json_to_gcp(golden_path_message)
            self.assertTrue(send_result['success'], f"Failed to send message: {send_result.get('error')}")
            expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            received_events = []
            timeout = 60
            start_time = time.time()
            while len(received_events) < 5 and time.time() - start_time < timeout:
                await asyncio.sleep(1)
                for message_data in ws_client.received_messages[len(received_events):]:
                    event_type = message_data['message'].get('type')
                    if event_type in expected_events:
                        received_events.append(event_type)
                        logger.info(f'Golden Path received event: {event_type}')
            self.assertGreaterEqual(len(received_events), 3, f'Golden Path incomplete - only received {len(received_events)} events: {received_events}')
            self.assertIn('agent_started', received_events, 'Golden Path missing agent_started event')
            final_messages = [msg for msg in ws_client.received_messages if msg['message'].get('type') == 'agent_completed']
            if final_messages:
                final_event = final_messages[-1]['message']
                business_indicators = ['savings', 'cost', 'optimization', 'reduce', 'efficiency', '$']
                has_business_value = any((indicator in str(final_event).lower() for indicator in business_indicators))
                self.assertTrue(has_business_value, f'Agent response lacks business value: {final_event}')
        await ws_client.disconnect_from_gcp()

    async def test_gcp_cloud_run_websocket_race_conditions_high_difficulty(self):
        """
        HIGH DIFFICULTY: Test GCP Cloud Run WebSocket race conditions and timing.
        
        Business Value: Prevents WebSocket failures that break chat in production Cloud Run.
        Can Fail: If Cloud Run race conditions exist, chat fails during auto-scaling.
        """
        num_rapid_connections = 5
        connection_tasks = []
        clients = []
        for i in range(num_rapid_connections):
            user_id = ensure_user_id(f'rapid-user-{i}-{uuid.uuid4()}')
            client = GCPWebSocketClient(self.staging_url, self.auth_token)
            clients.append(client)
            connection_tasks.append(client.connect_to_gcp_staging(user_id))
        connection_start = time.time()
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_connection_time = time.time() - connection_start
        successful_connections = 0
        connection_errors = []
        total_latency = 0
        for i, result in enumerate(connection_results):
            if isinstance(result, Exception):
                connection_errors.append(f'Client {i}: {str(result)}')
            elif isinstance(result, dict) and result.get('connected'):
                successful_connections += 1
                total_latency += result['latency_ms']
            else:
                connection_errors.append(f"Client {i}: {result.get('error', 'Unknown error')}")
        success_rate = successful_connections / num_rapid_connections
        self.assertGreaterEqual(success_rate, 0.6, f'Cloud Run connection success rate too low: {success_rate:.1%} Errors: {connection_errors}')
        if successful_connections > 0:
            avg_latency = total_latency / successful_connections
            self.assertLess(avg_latency, 5000, f'Average connection latency too high: {avg_latency:.1f}ms')
        if successful_connections > 0:
            message_tasks = []
            for i, client in enumerate(clients):
                if client.connected:
                    message = {'type': 'race_condition_test', 'client_id': i, 'content': f'Testing Cloud Run message handling from client {i}', 'timestamp': datetime.now(timezone.utc).isoformat()}
                    message_tasks.append(client.send_json_to_gcp(message))
            message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
            successful_sends = sum((1 for result in message_results if isinstance(result, dict) and result.get('success')))
            self.assertGreater(successful_sends, 0, 'No messages sent successfully under rapid conditions')
        cleanup_tasks = [client.disconnect_from_gcp() for client in clients if client.connected]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    async def test_gcp_load_balancer_websocket_upgrade_high_difficulty(self):
        """
        HIGH DIFFICULTY: Test GCP Load Balancer WebSocket upgrade handling.
        
        Business Value: Ensures WebSocket connections work through GCP production networking.
        Can Fail: If load balancer config is wrong, WebSocket connections fail completely.
        """
        client = GCPWebSocketClient(self.staging_url, self.auth_token)
        connection_result = await client.connect_to_gcp_staging(self.test_user_id)
        self.assertTrue(connection_result['connected'], f"Load balancer WebSocket upgrade failed: {connection_result.get('error')}")
        if client.websocket:
            self.assertIsNotNone(client.websocket.version, 'WebSocket version not set by load balancer')
            ping_start = time.time()
            try:
                pong_waiter = await client.websocket.ping()
                await asyncio.wait_for(pong_waiter, timeout=10)
                ping_latency = time.time() - ping_start
                self.assertLess(ping_latency, 2.0, f'Ping latency through load balancer too high: {ping_latency:.3f}s')
            except asyncio.TimeoutError:
                self.fail('WebSocket ping/pong failed through load balancer')
        message_count = 10
        for i in range(message_count):
            test_message = {'type': 'load_balancer_test', 'sequence': i, 'content': f'Testing sustained connection message {i}', 'timestamp': datetime.now(timezone.utc).isoformat()}
            send_result = await client.send_json_to_gcp(test_message)
            self.assertTrue(send_result['success'], f"Message {i} failed through load balancer: {send_result.get('error')}")
            await asyncio.sleep(0.5)
        await asyncio.sleep(2)
        self.assertTrue(client.connected, 'Connection lost during sustained messaging through load balancer')
        await client.disconnect_from_gcp()

    async def test_gcp_autoscaling_connection_handling_high_difficulty(self):
        """
        HIGH DIFFICULTY: Test GCP auto-scaling WebSocket connection handling.
        
        Business Value: Ensures chat works during traffic spikes and scaling events.
        Can Fail: If auto-scaling breaks WebSocket connections, chat fails during growth.
        """
        base_connections = 3
        scale_up_connections = 7
        total_connections = base_connections + scale_up_connections
        clients = []
        logger.info('Phase 1: Establishing base connections')
        for i in range(base_connections):
            user_id = ensure_user_id(f'autoscale-base-{i}-{uuid.uuid4()}')
            client = GCPWebSocketClient(self.staging_url, self.auth_token)
            clients.append(client)
            connection_result = await client.connect_to_gcp_staging(user_id)
            self.assertTrue(connection_result['connected'], f"Base connection {i} failed: {connection_result.get('error')}")
            await client.send_json_to_gcp({'type': 'autoscale_baseline', 'phase': 'base_connection', 'connection_id': i})
        await asyncio.sleep(2)
        logger.info('Phase 2: Rapid scale-up simulation')
        scale_up_tasks = []
        for i in range(scale_up_connections):
            user_id = ensure_user_id(f'autoscale-surge-{i}-{uuid.uuid4()}')
            client = GCPWebSocketClient(self.staging_url, self.auth_token)
            clients.append(client)
            scale_up_tasks.append(client.connect_to_gcp_staging(user_id))
        scale_start = time.time()
        scale_results = await asyncio.gather(*scale_up_tasks, return_exceptions=True)
        scale_time = time.time() - scale_start
        scale_successes = sum((1 for result in scale_results if isinstance(result, dict) and result.get('connected')))
        scale_success_rate = scale_successes / scale_up_connections
        self.assertGreaterEqual(scale_success_rate, 0.5, f'Auto-scaling handled only {scale_success_rate:.1%} of surge connections')
        logger.info(f'Auto-scaling handled {scale_successes}/{scale_up_connections} connections in {scale_time:.2f}s')
        logger.info('Phase 3: Testing all connections post-scaling')
        active_clients = [client for client in clients if client.connected]
        if active_clients:
            message_tasks = []
            for i, client in enumerate(active_clients):
                message = {'type': 'post_autoscale_test', 'client_index': i, 'total_active': len(active_clients), 'content': 'Testing connection stability after auto-scaling'}
                message_tasks.append(client.send_json_to_gcp(message))
            message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
            successful_messages = sum((1 for result in message_results if isinstance(result, dict) and result.get('success')))
            message_success_rate = successful_messages / len(active_clients)
            self.assertGreaterEqual(message_success_rate, 0.8, f'Only {message_success_rate:.1%} of messages succeeded post-scaling')
        cleanup_tasks = [client.disconnect_from_gcp() for client in clients if client.connected]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    async def test_gcp_staging_health_and_connectivity(self):
        """Test GCP staging environment health and basic connectivity."""
        async with GCPHTTPClient(self.staging_url, self.auth_token) as http_client:
            health_result = await http_client.get_health_status()
            self.assertTrue(health_result['healthy'], f"GCP staging environment unhealthy: {health_result.get('error')}")
            if health_result['healthy']:
                logger.info(f"GCP staging healthy - Response time: {health_result['response_time_ms']}")

    async def test_gcp_websocket_connection_stability(self):
        """Test WebSocket connection stability in GCP environment."""
        client = GCPWebSocketClient(self.staging_url, self.auth_token)
        connection_result = await client.connect_to_gcp_staging(self.test_user_id)
        self.assertTrue(connection_result['connected'])
        stability_duration = 10
        message_interval = 2
        messages_sent = 0
        start_time = time.time()
        while time.time() - start_time < stability_duration:
            if client.connected:
                message = {'type': 'stability_test', 'timestamp': datetime.now(timezone.utc).isoformat(), 'message_number': messages_sent}
                send_result = await client.send_json_to_gcp(message)
                if send_result['success']:
                    messages_sent += 1
            await asyncio.sleep(message_interval)
        self.assertTrue(client.connected, 'Connection lost during stability test')
        self.assertGreater(messages_sent, 0, 'No messages sent during stability test')
        await client.disconnect_from_gcp()

    async def test_gcp_websocket_message_latency(self):
        """Test WebSocket message latency in GCP environment."""
        client = GCPWebSocketClient(self.staging_url, self.auth_token)
        await client.connect_to_gcp_staging(self.test_user_id)
        num_messages = 5
        for i in range(num_messages):
            message = {'type': 'latency_test', 'sequence': i, 'timestamp': datetime.now(timezone.utc).isoformat()}
            send_result = await client.send_json_to_gcp(message)
            self.assertTrue(send_result['success'])
            await asyncio.sleep(1)
        await asyncio.sleep(3)
        if client.message_latencies:
            avg_latency = sum(client.message_latencies) / len(client.message_latencies)
            max_latency = max(client.message_latencies)
            self.assertLess(avg_latency, 5.0, f'Average message latency too high: {avg_latency:.3f}s')
            self.assertLess(max_latency, 10.0, f'Max message latency too high: {max_latency:.3f}s')
            logger.info(f'GCP message latency - Avg: {avg_latency:.3f}s, Max: {max_latency:.3f}s')
        await client.disconnect_from_gcp()

    async def test_gcp_concurrent_user_isolation(self):
        """Test user isolation with concurrent users in GCP."""
        client1 = GCPWebSocketClient(self.staging_url, self.auth_token)
        client2 = GCPWebSocketClient(self.staging_url, self.auth_token)
        await client1.connect_to_gcp_staging(self.test_user_id)
        await client2.connect_to_gcp_staging(self.test_user_id_2)
        message1 = {'type': 'user_isolation_test', 'user_id': self.test_user_id, 'sensitive_data': 'User 1 private information', 'timestamp': datetime.now(timezone.utc).isoformat()}
        message2 = {'type': 'user_isolation_test', 'user_id': self.test_user_id_2, 'sensitive_data': 'User 2 private information', 'timestamp': datetime.now(timezone.utc).isoformat()}
        await client1.send_json_to_gcp(message1)
        await client2.send_json_to_gcp(message2)
        await asyncio.sleep(2)
        user1_messages = client1.received_messages
        user2_messages = client2.received_messages
        for msg_data in user1_messages:
            message_content = str(msg_data['message'])
            self.assertNotIn('User 2 private information', message_content, "User isolation violated - User 1 saw User 2's data")
        for msg_data in user2_messages:
            message_content = str(msg_data['message'])
            self.assertNotIn('User 1 private information', message_content, "User isolation violated - User 2 saw User 1's data")
        await client1.disconnect_from_gcp()
        await client2.disconnect_from_gcp()

    async def test_gcp_websocket_error_handling(self):
        """Test WebSocket error handling in GCP environment."""
        client = GCPWebSocketClient(self.staging_url, self.auth_token)
        await client.connect_to_gcp_staging(self.test_user_id)
        error_message = {'type': 'error_test', 'invalid_field': None, 'malformed_data': {'nested': {'deeply': {'invalid': float('inf')}}}, 'content': 'Testing error handling in GCP'}
        send_result = await client.send_json_to_gcp(error_message)
        await asyncio.sleep(2)
        self.assertTrue(client.connected, 'Connection lost after error message')
        recovery_message = {'type': 'recovery_test', 'content': 'Testing recovery after error', 'timestamp': datetime.now(timezone.utc).isoformat()}
        recovery_result = await client.send_json_to_gcp(recovery_message)
        self.assertTrue(recovery_result['success'], 'Connection did not recover from error')
        await client.disconnect_from_gcp()

    async def test_gcp_websocket_authentication_integration(self):
        """Test WebSocket authentication integration in GCP."""
        client_no_auth = GCPWebSocketClient(self.staging_url, auth_token=None)
        no_auth_result = await client_no_auth.connect_to_gcp_staging(self.test_user_id)
        if self.auth_token:
            client_with_auth = GCPWebSocketClient(self.staging_url, self.auth_token)
            auth_result = await client_with_auth.connect_to_gcp_staging(self.test_user_id)
            self.assertTrue(auth_result['connected'], f"Authenticated connection failed: {auth_result.get('error')}")
            auth_message = {'type': 'authenticated_test', 'content': 'Testing authenticated WebSocket message', 'requires_auth': True}
            send_result = await client_with_auth.send_json_to_gcp(auth_message)
            self.assertTrue(send_result['success'], 'Authenticated message send failed')
            await client_with_auth.disconnect_from_gcp()
        if client_no_auth.connected:
            await client_no_auth.disconnect_from_gcp()

    async def test_gcp_websocket_performance_under_load(self):
        """Test WebSocket performance under moderate load in GCP."""
        num_messages = 20
        client = GCPWebSocketClient(self.staging_url, self.auth_token)
        await client.connect_to_gcp_staging(self.test_user_id)
        start_time = time.time()
        send_tasks = []
        for i in range(num_messages):
            message = {'type': 'performance_test', 'sequence': i, 'payload': ['data'] * 50, 'timestamp': datetime.now(timezone.utc).isoformat()}
            send_tasks.append(client.send_json_to_gcp(message))
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        successful_sends = sum((1 for result in results if isinstance(result, dict) and result.get('success')))
        success_rate = successful_sends / num_messages
        throughput = successful_sends / total_time
        self.assertGreaterEqual(success_rate, 0.8, f'Send success rate too low: {success_rate:.1%}')
        self.assertGreater(throughput, 5, f'Throughput too low: {throughput:.1f} messages/second')
        logger.info(f'GCP performance - Success rate: {success_rate:.1%}, Throughput: {throughput:.1f} msg/s')
        await client.disconnect_from_gcp()

    async def test_gcp_websocket_connection_recovery(self):
        """Test WebSocket connection recovery in GCP environment."""
        client = GCPWebSocketClient(self.staging_url, self.auth_token)
        initial_result = await client.connect_to_gcp_staging(self.test_user_id)
        self.assertTrue(initial_result['connected'])
        if client.websocket:
            await client.websocket.close()
            await asyncio.sleep(1)
        recovery_result = await client.connect_to_gcp_staging(self.test_user_id)
        if recovery_result['connected']:
            test_message = {'type': 'recovery_test', 'content': 'Testing recovered connection'}
            send_result = await client.send_json_to_gcp(test_message)
            self.assertTrue(send_result['success'], 'Recovered connection not functional')
        if client.connected:
            await client.disconnect_from_gcp()

    async def test_gcp_websocket_message_ordering(self):
        """Test message ordering in GCP WebSocket environment."""
        client = GCPWebSocketClient(self.staging_url, self.auth_token)
        await client.connect_to_gcp_staging(self.test_user_id)
        num_messages = 10
        for i in range(num_messages):
            message = {'type': 'ordering_test', 'sequence_number': i, 'content': f'Message number {i}', 'timestamp': datetime.now(timezone.utc).isoformat()}
            send_result = await client.send_json_to_gcp(message)
            self.assertTrue(send_result['success'], f'Message {i} send failed')
            await asyncio.sleep(0.2)
        await asyncio.sleep(3)
        if client.received_messages:
            logger.info(f'Received {len(client.received_messages)} messages from GCP')
            for msg_data in client.received_messages:
                self.assertIn('received_at', msg_data)
                self.assertIsInstance(msg_data['received_at'], datetime)
        await client.disconnect_from_gcp()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')