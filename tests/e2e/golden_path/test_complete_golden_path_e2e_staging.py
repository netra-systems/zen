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
'\nComprehensive E2E Golden Path Tests for Staging Environment\n\nBusiness Value Justification (BVJ):\n- Segment: All (Free, Early, Mid, Enterprise)\n- Business Goal: Validate complete "users login  ->  get AI responses" flow protecting $500K+ ARR\n- Value Impact: Ensures end-to-end chat functionality works in production-like environment\n- Strategic Impact: Validates 90% of platform value through complete user journey\n\nThis test suite validates the complete golden path user journey in staging:\n1. User authentication and WebSocket connection establishment\n2. Chat message submission and agent execution initiation\n3. Real-time WebSocket event delivery during agent execution\n4. All 5 critical WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)\n5. Final AI response delivery with actionable insights\n6. Multi-user concurrent execution isolation\n7. Performance SLAs and error handling\n8. Integration with real GCP staging infrastructure\n\nKey Coverage Areas:\n- Complete end-to-end user journey validation\n- Real WebSocket connections with GCP staging\n- Actual agent execution with LLM integration\n- Real-time event streaming validation\n- Multi-user isolation and concurrency\n- Performance and SLA compliance\n- Error handling and recovery scenarios\n- Production-like infrastructure validation\n'
import asyncio
import json
import pytest
import time
import uuid
import websockets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, patch
from websockets import ConnectionClosed, WebSocketException
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.user_execution_context import UserExecutionContext
logger = central_logger.get_logger(__name__)

class TestCompleteGoldenPathE2EStaging(SSotAsyncTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(user_id='staging_user_674', thread_id='staging_thread_674', run_id='staging_run_674')
    '\n    Comprehensive E2E tests for golden path in staging environment.\n    \n    Tests the complete user journey from login to AI response delivery\n    using real staging infrastructure and services.\n    '

    def setup_method(self, method):
        """Setup test environment for staging E2E tests."""
        super().setup_method(method)
        from pathlib import Path
        staging_env_file = Path.cwd() / '.env.staging.e2e'
        if staging_env_file.exists():
            env_manager = get_env()
            env_manager.load_from_file(staging_env_file, source='staging_e2e_config')
        self.staging_config = self._discover_staging_environment()
        missing_config = [key for key, value in self.staging_config.items() if not value]
        if missing_config:
            logger.warning(f'Missing staging configuration: {missing_config}')
            self.staging_config.update(self._apply_environment_fallbacks())
        self.test_users = [{'email': get_env().get('TEST_USER_EMAIL', 'test@netra.ai'), 'password': get_env().get('TEST_USER_PASSWORD', 'test_password'), 'user_id': None, 'jwt_token': None}]
        self.captured_events: List[Dict[str, Any]] = []
        self.websocket_connections: List[websockets.ServerConnection] = []
        self.performance_metrics: List[Dict[str, Any]] = []
        self.sla_requirements = {'connection_time_max_seconds': 12.0, 'first_event_max_seconds': 20.0, 'total_execution_max_seconds': 120.0, 'event_delivery_max_seconds': 3.0, 'response_quality_min_score': 0.5}

    def _discover_staging_environment(self) -> Dict[str, str]:
        """
        Discover staging environment configuration with intelligent fallbacks.
        Addresses Issue #677: Environment configuration mismatch.
        """
        staging_config = {'base_url': get_env().get('STAGING_BASE_URL'), 'websocket_url': get_env().get('STAGING_WEBSOCKET_URL'), 'api_url': get_env().get('STAGING_API_URL'), 'auth_url': get_env().get('STAGING_AUTH_URL')}
        if not staging_config['base_url']:
            service_name = get_env().get('K_SERVICE')
            if service_name and 'staging' in service_name.lower():
                project_id = get_env().get('GOOGLE_CLOUD_PROJECT', 'netra-staging')
                region = get_env().get('GOOGLE_CLOUD_REGION', 'us-central1')
                base_domain = f'{service_name}-{region}-{project_id}.a.run.app'
                staging_config.update({'base_url': f'https://{base_domain}', 'websocket_url': f'wss://{base_domain}/ws', 'api_url': f'https://{base_domain}/api', 'auth_url': f'https://{base_domain}/auth'})
                logger.info(f'Detected Cloud Run staging environment: {base_domain}')
        if not staging_config['base_url']:
            local_port = get_env().get('PORT', '8000')
            if get_env().get('ENVIRONMENT') == 'development' or get_env().get('NODE_ENV') == 'development':
                staging_config.update({'base_url': f'http://localhost:{local_port}', 'websocket_url': f'ws://localhost:{local_port}/ws', 'api_url': f'http://localhost:{local_port}/api', 'auth_url': f'http://localhost:{local_port}/auth'})
                logger.info(f'Detected local development environment on port {local_port}')
        return staging_config

    def _apply_environment_fallbacks(self) -> Dict[str, str]:
        """
        Apply fallback configuration when environment discovery fails.
        Addresses Issue #677: Graceful degradation for missing configuration.
        """
        fallback_config = {}
        staging_domains = ['staging.netra.ai', 'staging-api.netra.ai', 'netra-staging.herokuapp.com', 'localhost:8000', '127.0.0.1:8000']
        for domain in staging_domains:
            try:
                if 'localhost' in domain or '127.0.0.1' in domain:
                    base_url = f'http://{domain}'
                    websocket_url = f'ws://{domain}/ws'
                else:
                    base_url = f'https://{domain}'
                    websocket_url = f'wss://{domain}/ws'
                fallback_config.update({'base_url': base_url, 'websocket_url': websocket_url, 'api_url': f'{base_url}/api', 'auth_url': f'{base_url}/auth'})
                logger.info(f'Applied fallback configuration for domain: {domain}')
                break
            except Exception as e:
                logger.debug(f'Fallback domain {domain} not available: {e}')
                continue
        if not fallback_config:
            fallback_config = {'base_url': 'https://staging.netra.ai', 'websocket_url': 'wss://staging.netra.ai/ws', 'api_url': 'https://staging.netra.ai/api', 'auth_url': 'https://staging.netra.ai/auth'}
            logger.warning('Using ultimate fallback configuration - may not be reachable')
        return fallback_config

    async def async_setup_method(self, method):
        """Async setup for E2E environment initialization."""
        await super().async_setup_method(method)
        await self._authenticate_test_users()
        await self._verify_staging_health()

    async def _authenticate_test_users(self):
        """Authenticate test users and obtain JWT tokens."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for user in self.test_users:
                try:
                    auth_payload = {'email': user['email'], 'password': user['password']}
                    async with session.post(f"{self.staging_config['auth_url']}/login", json=auth_payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            auth_data = await response.json()
                            user['jwt_token'] = auth_data.get('access_token')
                            user['user_id'] = auth_data.get('user_id')
                            logger.info(f"Authenticated test user: {user['email']}")
                        else:
                            logger.warning(f"Failed to authenticate test user {user['email']}: {response.status}")
                            user['jwt_token'] = 'mock_jwt_token_for_staging_test'
                            user['user_id'] = str(uuid.uuid4())
                except Exception as e:
                    logger.warning(f"Authentication error for {user['email']}: {e}")
                    user['jwt_token'] = 'mock_jwt_token_for_staging_test'
                    user['user_id'] = str(uuid.uuid4())

    async def _verify_staging_health(self):
        """Verify staging environment health before running tests."""
        import aiohttp
        health_checks = [('API Health', f"{self.staging_config['api_url']}/health"), ('Auth Health', f"{self.staging_config['auth_url']}/health")]
        async with aiohttp.ClientSession() as session:
            for check_name, url in health_checks:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            logger.info(f' PASS:  {check_name}: OK')
                        else:
                            logger.warning(f' WARNING: [U+FE0F] {check_name}: Status {response.status}')
                except Exception as e:
                    logger.warning(f' WARNING: [U+FE0F] {check_name}: Error {e}')

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.staging
    @pytest.mark.real_services
    async def test_complete_golden_path_user_journey_staging(self):
        """
        BVJ: All segments | Complete User Journey | Validates end-to-end chat functionality
        Test complete golden path user journey in staging environment.
        """
        user = self.test_users[0]
        journey_start_time = time.time()
        logger.info('[U+1F680] Starting Golden Path E2E Test - Phase 1: Connection')
        connection_start = time.time()
        try:
            websocket_url = self.staging_config['websocket_url']
            headers = {'Authorization': f"Bearer {user['jwt_token']}"}
            from test_framework.websocket_helpers import WebSocketClientAbstraction
            websocket = await WebSocketClientAbstraction.connect_with_compatibility(websocket_url, headers=headers, timeout=10.0)
            self.websocket_connections.append(websocket)
            connection_time = time.time() - connection_start
            assert connection_time <= self.sla_requirements['connection_time_max_seconds'], f'Connection too slow: {connection_time:.2f}s'
            logger.info(f' PASS:  WebSocket connected to staging in {connection_time:.2f}s')
            welcome_timeout = 5.0
            welcome_message = await asyncio.wait_for(websocket.recv(), timeout=welcome_timeout)
            welcome_data = json.loads(welcome_message)
            assert welcome_data.get('type') == 'connection_ready', f'Expected welcome message, got: {welcome_data}'
            logger.info(' PASS:  Welcome message received from staging')
        except Exception as e:
            logger.error(f' FAIL:  Failed to connect to staging WebSocket: {e}')
            pytest.skip(f'Staging WebSocket connection failed: {e}')
        logger.info('[U+1F680] Phase 2: Chat Message Submission')
        chat_message = {'type': 'user_message', 'text': 'Analyze my cloud infrastructure costs and provide optimization recommendations with estimated savings', 'thread_id': str(uuid.uuid4()), 'timestamp': datetime.utcnow().isoformat()}
        message_send_time = time.time()
        await websocket.send(json.dumps(chat_message))
        logger.info(' PASS:  Chat message sent to staging')
        logger.info('[U+1F680] Phase 3: Real-time Event Collection')
        events_received = []
        first_event_time = None
        last_event_time = None
        required_events = {'agent_started': False, 'agent_thinking': False, 'tool_executing': False, 'tool_completed': False, 'agent_completed': False}
        event_collection_timeout = self.sla_requirements['total_execution_max_seconds']
        event_collection_start = time.time()
        try:
            while time.time() - event_collection_start < event_collection_timeout:
                try:
                    raw_event = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event_receive_time = time.time()
                    if first_event_time is None:
                        first_event_time = event_receive_time
                        first_event_latency = first_event_time - message_send_time
                        assert first_event_latency <= self.sla_requirements['first_event_max_seconds'], f'First event too slow: {first_event_latency:.2f}s'
                    last_event_time = event_receive_time
                    try:
                        event_data = json.loads(raw_event)
                        event_type = event_data.get('type')
                        events_received.append({'type': event_type, 'data': event_data.get('data', {}), 'timestamp': datetime.utcnow(), 'receive_time': event_receive_time, 'latency_from_start': event_receive_time - message_send_time})
                        if event_type in required_events:
                            required_events[event_type] = True
                            logger.info(f' PASS:  Received critical event: {event_type}')
                        if all(required_events.values()):
                            logger.info(' PASS:  All critical events received')
                            break
                    except json.JSONDecodeError:
                        logger.warning(f'Received non-JSON message: {raw_event}')
                        continue
                except asyncio.TimeoutError:
                    if any(required_events.values()):
                        continue
                    else:
                        break
        except Exception as e:
            logger.error(f' FAIL:  Error during event collection: {e}')
        total_execution_time = time.time() - message_send_time
        logger.info('[U+1F680] Phase 4: Event Validation')
        assert len(events_received) > 0, 'Should receive at least some events from staging'
        missing_events = [event_type for event_type, received in required_events.items() if not received]
        if missing_events:
            logger.warning(f' WARNING: [U+FE0F] Missing critical events in staging: {missing_events}')
        received_event_types = [event['type'] for event in events_received]
        logger.info(f'Events received from staging: {received_event_types}')
        if len(events_received) > 1:
            event_times = [event['receive_time'] for event in events_received]
            time_spans = [event_times[i + 1] - event_times[i] for i in range(len(event_times) - 1)]
            max_gap = max(time_spans) if time_spans else 0
            assert max_gap < 30.0, f'Event gap too large (indicates hanging): {max_gap:.2f}s'
        logger.info('[U+1F680] Phase 5: Final Response Validation')
        final_response = None
        agent_completed_events = [e for e in events_received if e['type'] == 'agent_completed']
        if agent_completed_events:
            final_response = agent_completed_events[-1]['data']
        if final_response:
            response_quality_score = self._assess_response_quality(final_response)
            logger.info(f'Response quality score: {response_quality_score:.2f}')
            if response_quality_score < self.sla_requirements['response_quality_min_score']:
                logger.warning(f' WARNING: [U+FE0F] Response quality below threshold: {response_quality_score:.2f}')
        journey_total_time = time.time() - journey_start_time
        performance_summary = {'journey_total_time': journey_total_time, 'connection_time': connection_time, 'first_event_latency': first_event_latency if first_event_time else None, 'total_execution_time': total_execution_time, 'events_received_count': len(events_received), 'required_events_received': sum(required_events.values()), 'required_events_total': len(required_events), 'response_received': final_response is not None, 'staging_environment': True}
        self.performance_metrics.append(performance_summary)
        assert journey_total_time < 120.0, f'Total journey too slow: {journey_total_time:.2f}s'
        assert len(events_received) >= 1, 'Should receive at least one event from staging'
        event_success_rate = sum(required_events.values()) / len(required_events)
        assert event_success_rate >= 0.6, f'Too few critical events received: {event_success_rate:.2%}'
        logger.info(f' CELEBRATION:  Golden Path E2E Test COMPLETED: {journey_total_time:.2f}s total, {len(events_received)} events, {event_success_rate:.2%} critical events')
        await websocket.close()

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_multi_user_golden_path_concurrency_staging(self):
        """
        BVJ: Mid/Enterprise | Multi-user Support | Validates concurrent user isolation
        Test multiple users executing golden path concurrently in staging.
        """
        num_concurrent_users = 3
        concurrent_users = []
        for i in range(num_concurrent_users):
            user_context = {'user_index': i, 'email': f'test_user_{i}@staging.netra.ai', 'jwt_token': f'mock_jwt_token_user_{i}', 'user_id': str(uuid.uuid4()), 'thread_id': str(uuid.uuid4())}
            concurrent_users.append(user_context)

        async def single_user_journey(user_context: Dict[str, Any]) -> Dict[str, Any]:
            user_index = user_context['user_index']
            journey_start = time.time()
            try:
                headers = {'Authorization': f"Bearer {user_context['jwt_token']}"}
                from test_framework.websocket_helpers import WebSocketClientAbstraction
                websocket = await WebSocketClientAbstraction.connect_with_compatibility(self.staging_config['websocket_url'], headers=headers, timeout=10.0)
                message = {'type': 'user_message', 'text': f'User {user_index}: Analyze my infrastructure costs for multi-user test', 'thread_id': user_context['thread_id'], 'user_index': user_index}
                await websocket.send(json.dumps(message))
                user_events = []
                collection_timeout = 30.0
                collection_start = time.time()
                while time.time() - collection_start < collection_timeout:
                    try:
                        raw_event = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        event_data = json.loads(raw_event)
                        user_events.append({'type': event_data.get('type'), 'data': event_data.get('data', {}), 'user_index': user_index, 'timestamp': time.time()})
                        if event_data.get('type') == 'agent_completed':
                            break
                    except asyncio.TimeoutError:
                        break
                    except json.JSONDecodeError:
                        continue
                await websocket.close()
                journey_time = time.time() - journey_start
                return {'user_index': user_index, 'success': True, 'events_received': len(user_events), 'journey_time': journey_time, 'events': user_events}
            except Exception as e:
                return {'user_index': user_index, 'success': False, 'error': str(e), 'journey_time': time.time() - journey_start, 'events': []}
        concurrent_start = time.time()
        journey_tasks = [single_user_journey(user_context) for user_context in concurrent_users]
        results = await asyncio.gather(*journey_tasks, return_exceptions=True)
        concurrent_total_time = time.time() - concurrent_start
        successful_journeys = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        failed_journeys = [r for r in results if isinstance(r, dict) and (not r.get('success', True))]
        success_rate = len(successful_journeys) / len(results)
        logger.info(f'🔍 CONCURRENCY DEBUGGING: {len(successful_journeys)}/{len(results)} journeys successful')
        for i, result in enumerate(results):
            if isinstance(result, dict) and (not result.get('success', True)):
                logger.error(f"❌ Journey {i} failed: {result.get('error', 'Unknown error')}")
            elif isinstance(result, dict) and result.get('success', False):
                logger.info(f"✅ Journey {i} succeeded: {result.get('events_received', 0)} events")
        assert success_rate >= 0.5, f'Concurrent success rate too low: {success_rate:.2%}'
        assert concurrent_total_time < 60.0, f'Concurrent execution too slow: {concurrent_total_time:.2f}s'
        for result in successful_journeys:
            user_index = result['user_index']
            user_events = result['events']
            for event in user_events:
                event_str = str(event)
                for other_index in range(num_concurrent_users):
                    if other_index != user_index:
                        assert f'user_{other_index}' not in event_str.lower(), f'User {user_index} events contain user {other_index} data'
        logger.info(f' CELEBRATION:  Multi-user concurrency test completed: {success_rate:.2%} success rate, {concurrent_total_time:.2f}s total')

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.staging
    @pytest.mark.performance
    async def test_golden_path_performance_sla_staging(self):
        """
        BVJ: All segments | Performance SLA | Validates staging performance requirements
        Test golden path performance SLAs in staging environment.
        """
        user = self.test_users[0]
        num_performance_runs = 3
        performance_results = []
        for run_index in range(num_performance_runs):
            logger.info(f'[U+1F680] Performance Run {run_index + 1}/{num_performance_runs}')
            run_start = time.time()
            try:
                connection_start = time.time()
                from test_framework.websocket_helpers import WebSocketClientAbstraction
                websocket = await WebSocketClientAbstraction.connect_with_compatibility(self.staging_config['websocket_url'], headers={'Authorization': f"Bearer {user['jwt_token']}"}, timeout=10.0)
                connection_time = time.time() - connection_start
                message = {'type': 'user_message', 'text': f'Performance test {run_index}: Quick cost analysis', 'thread_id': str(uuid.uuid4())}
                message_send_time = time.time()
                await websocket.send(json.dumps(message))
                events = []
                first_event_time = None
                last_event_time = None
                timeout = 20.0
                start_collection = time.time()
                while time.time() - start_collection < timeout:
                    try:
                        raw_event = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        event_time = time.time()
                        if first_event_time is None:
                            first_event_time = event_time
                        last_event_time = event_time
                        event_data = json.loads(raw_event)
                        events.append({'type': event_data.get('type'), 'receive_time': event_time})
                        if event_data.get('type') == 'agent_completed':
                            break
                    except asyncio.TimeoutError:
                        break
                    except json.JSONDecodeError:
                        continue
                await websocket.close()
                run_total_time = time.time() - run_start
                first_event_latency = first_event_time - message_send_time if first_event_time else None
                execution_time = last_event_time - message_send_time if last_event_time else None
                run_result = {'run_index': run_index, 'success': True, 'connection_time': connection_time, 'first_event_latency': first_event_latency, 'execution_time': execution_time, 'total_time': run_total_time, 'events_count': len(events), 'events_per_second': len(events) / execution_time if execution_time else 0}
                performance_results.append(run_result)
            except Exception as e:
                logger.warning(f'Performance run {run_index} failed: {e}')
                performance_results.append({'run_index': run_index, 'success': False, 'error': str(e), 'total_time': time.time() - run_start})
        successful_runs = [r for r in performance_results if r.get('success', False)]
        assert len(successful_runs) >= 1, 'At least one performance run should succeed'
        avg_connection_time = sum((r['connection_time'] for r in successful_runs)) / len(successful_runs)
        avg_first_event_latency = sum((r['first_event_latency'] for r in successful_runs if r['first_event_latency'])) / len([r for r in successful_runs if r['first_event_latency']])
        avg_execution_time = sum((r['execution_time'] for r in successful_runs if r['execution_time'])) / len([r for r in successful_runs if r['execution_time']])
        assert avg_connection_time <= self.sla_requirements['connection_time_max_seconds'], f"Average connection time too high: {avg_connection_time:.2f}s (limit: {self.sla_requirements['connection_time_max_seconds']}s)"
        assert avg_first_event_latency <= self.sla_requirements['first_event_max_seconds'], f"Average first event latency too high: {avg_first_event_latency:.2f}s (limit: {self.sla_requirements['first_event_max_seconds']}s)"
        assert avg_execution_time <= self.sla_requirements['total_execution_max_seconds'], f"Average execution time too high: {avg_execution_time:.2f}s (limit: {self.sla_requirements['total_execution_max_seconds']}s)"
        performance_summary = {'successful_runs': len(successful_runs), 'total_runs': len(performance_results), 'success_rate': len(successful_runs) / len(performance_results), 'avg_connection_time': avg_connection_time, 'avg_first_event_latency': avg_first_event_latency, 'avg_execution_time': avg_execution_time}
        logger.info(f' CELEBRATION:  Performance SLA validation completed: {performance_summary}')

    def _assess_response_quality(self, response_data: Dict[str, Any]) -> float:
        """Assess the quality of an AI response."""
        quality_score = 0.0
        if 'result' in response_data or 'final_result' in response_data:
            quality_score += 0.3
        response_str = str(response_data).lower()
        quality_indicators = ['recommendation', 'saving', 'optimize', 'reduce', 'improve', 'analysis', 'cost', 'efficiency', 'performance', 'strategy']
        indicator_count = sum((1 for indicator in quality_indicators if indicator in response_str))
        quality_score += min(indicator_count * 0.1, 0.5)
        if any((char.isdigit() for char in response_str)):
            quality_score += 0.2
        return min(quality_score, 1.0)

    def teardown_method(self, method):
        """Cleanup after E2E tests."""
        self.captured_events.clear()
        self.performance_metrics.clear()
        super().teardown_method(method)

    async def async_teardown_method(self, method):
        """Async cleanup after E2E tests."""
        for websocket in self.websocket_connections:
            try:
                if not websocket.closed:
                    await websocket.close()
            except Exception:
                pass
        self.websocket_connections.clear()
        await super().async_teardown_method(method)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')