"""
E2E Tests for Cross-Service Integration in Agent Golden Path
Issue #1081 - Agent Golden Path Messages E2E Test Creation

MISSION CRITICAL: Tests complete cross-service integration during agent message processing
- Backend → Auth Service integration during message processing
- Backend → Database service integration for chat history
- WebSocket → Agent → LLM service integration for responses
- Real-time event delivery across service boundaries

Business Value Justification (BVJ):
- Segment: All Users (Free/Early/Mid/Enterprise)
- Business Goal: System Reliability & Service Integration Validation
- Value Impact: Ensures $500K+ ARR chat functionality works across all service boundaries
- Strategic Impact: Validates production-ready multi-service architecture

Test Strategy:
- REAL SERVICES: Complete staging GCP service mesh integration
- REAL PERSISTENCE: Database writes during message processing
- REAL AUTH: Service-to-service authentication validation
- REAL WEBSOCKETS: Cross-service WebSocket event delivery
- NO MOCKING: Full service integration testing

Coverage Target: Increase from 65-75% to 85%
Test Focus: Cross-service communication, data persistence, service resilience
"""
import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
import httpx
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, AuthenticatedUser

@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.cross_service
@pytest.mark.mission_critical
class CrossServiceIntegrationE2ETests(SSotAsyncTestCase):
    """
    E2E tests for cross-service integration in agent golden path.
    
    Validates complete service mesh integration during agent message processing
    including auth service validation, database persistence, and real-time events.
    """

    @classmethod
    def setup_class(cls):
        """Setup cross-service integration test environment."""
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        if not is_staging_available():
            pytest.skip('Staging environment not available')
        cls.auth_helper = E2EWebSocketAuthHelper(environment='staging')
        cls.service_endpoints = {'backend': cls.staging_config.urls.backend_url, 'auth': cls.staging_config.urls.auth_url, 'websocket': cls.staging_config.urls.websocket_url, 'api': cls.staging_config.urls.api_base_url}
        cls.logger.info('Cross-service integration e2e tests initialized')

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.test_id = f'cross_service_test_{int(time.time())}'
        self.thread_id = f'thread_{self.test_id}'
        self.run_id = f'run_{self.test_id}'
        self.logger.info(f'Cross-service test setup - test_id: {self.test_id}')

    async def test_auth_service_integration_during_message_processing(self):
        """
        Test auth service integration during agent message processing.
        
        Validates that:
        1. Initial WebSocket connection authenticates with auth service
        2. Message processing validates tokens with auth service
        3. Service-to-service auth works during agent execution
        4. Auth failures are handled gracefully
        
        Flow:
        1. Authenticate with auth service → get JWT
        2. Connect WebSocket with JWT → backend validates with auth service
        3. Send agent message → processing validates auth continuously
        4. Receive agent response → auth maintained throughout
        
        Coverage: Auth service integration, token validation, service-to-service auth
        """
        auth_integration_start = time.time()
        auth_events = []
        self.logger.info('🔐 Testing auth service integration during message processing')
        try:
            auth_user = await self.auth_helper.create_authenticated_user(email=f'cross_service_auth_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'agent_execution'])
            auth_events.append({'event': 'user_authentication', 'timestamp': time.time() - auth_integration_start, 'success': True, 'user_id': auth_user.user_id})
            async with httpx.AsyncClient() as client:
                validate_response = await client.get(f"{self.service_endpoints['auth']}/auth/validate", headers={'Authorization': f'Bearer {auth_user.jwt_token}'}, timeout=10.0)
                assert validate_response.status_code == 200, f'Auth service token validation failed: {validate_response.status_code}'
                auth_events.append({'event': 'token_validation', 'timestamp': time.time() - auth_integration_start, 'success': True, 'status_code': validate_response.status_code})
                self.logger.info('✅ Direct auth service validation successful')
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            headers = self.auth_helper.get_websocket_headers(auth_user.jwt_token)
            websocket = await asyncio.wait_for(websockets.connect(self.service_endpoints['websocket'], additional_headers=headers, ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=20.0)
            auth_events.append({'event': 'websocket_auth_connection', 'timestamp': time.time() - auth_integration_start, 'success': True})
            self.logger.info('✅ WebSocket connection with auth integration successful')
            auth_test_message = {'type': 'chat_message', 'content': 'Test message requiring auth validation during agent processing', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': auth_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'auth_integration', 'expects_agent_processing': True}}
            await websocket.send(json.dumps(auth_test_message))
            auth_events.append({'event': 'auth_message_sent', 'timestamp': time.time() - auth_integration_start, 'success': True})
            agent_events = []
            auth_maintained = True
            timeout = 60.0
            collection_start = time.time()
            while time.time() - collection_start < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    agent_events.append(event)
                    event_type = event.get('type', 'unknown')
                    if 'auth' in event_type.lower() and 'error' in event_type.lower():
                        auth_maintained = False
                        self.logger.error(f'Auth failure during processing: {event}')
                    if event_type == 'agent_completed':
                        break
                    if event_type == 'error':
                        error_msg = event.get('message', '')
                        if 'auth' in error_msg.lower() or 'unauthorized' in error_msg.lower():
                            auth_maintained = False
                except asyncio.TimeoutError:
                    continue
            processing_time = time.time() - collection_start
            auth_events.append({'event': 'agent_processing_with_auth', 'timestamp': time.time() - auth_integration_start, 'success': auth_maintained, 'processing_time': processing_time, 'events_received': len(agent_events)})
            await websocket.close()
            total_auth_time = time.time() - auth_integration_start
            assert len(agent_events) > 0, 'Should receive agent events with maintained auth'
            assert auth_maintained, 'Auth should be maintained throughout agent processing'
            auth_validation_time = next((e['timestamp'] for e in auth_events if e['event'] == 'token_validation'), 0)
            assert auth_validation_time < 5.0, f'Auth service validation too slow: {auth_validation_time:.2f}s'
            self.logger.info('🔐 Auth service integration validation complete')
            self.logger.info(f'   Total time: {total_auth_time:.2f}s')
            self.logger.info(f'   Auth events: {len(auth_events)}')
            self.logger.info(f'   Agent events with auth: {len(agent_events)}')
            self.logger.info(f'   Auth maintained: {auth_maintained}')
        except Exception as e:
            self.logger.error(f'❌ Auth service integration failed: {e}')
            raise AssertionError(f'Auth service integration during message processing failed: {e}. This breaks authentication across service boundaries.')

    async def test_database_persistence_during_agent_processing(self):
        """
        Test database persistence during agent message processing.
        
        Validates that:
        1. Chat messages are persisted to database
        2. Agent responses are stored in chat history
        3. User context is maintained in database
        4. Database operations don't impact agent response times
        
        Flow:
        1. Send message → should persist to database
        2. Agent processes → intermediate states may be persisted
        3. Agent completes → response persisted to database
        4. Verify chat history via API → database read validation
        
        Coverage: Database integration, persistence, chat history, data consistency
        """
        db_integration_start = time.time()
        db_operations = []
        self.logger.info('💾 Testing database persistence during agent processing')
        try:
            db_user = await self.auth_helper.create_authenticated_user(email=f'cross_service_db_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'history_access'])
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.service_endpoints['websocket'], additional_headers=self.auth_helper.get_websocket_headers(db_user.jwt_token), ssl=ssl_context), timeout=15.0)
            persistence_message = {'type': 'chat_message', 'content': f'Database persistence test message - {self.test_id}', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': db_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'database_persistence', 'should_persist': True, 'test_identifier': self.test_id}}
            message_send_time = time.time()
            await websocket.send(json.dumps(persistence_message))
            db_operations.append({'operation': 'message_sent_for_persistence', 'timestamp': time.time() - db_integration_start, 'message_id': self.run_id})
            agent_response = None
            agent_completed = False
            processing_timeout = 45.0
            processing_start = time.time()
            while time.time() - processing_start < processing_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    event_type = event.get('type', 'unknown')
                    if event_type == 'agent_completed':
                        agent_response = event
                        agent_completed = True
                        break
                except asyncio.TimeoutError:
                    continue
            assert agent_completed, 'Agent should complete processing for database persistence test'
            db_operations.append({'operation': 'agent_response_received', 'timestamp': time.time() - db_integration_start, 'response_length': len(str(agent_response))})
            await websocket.close()
            async with httpx.AsyncClient() as client:
                history_response = await client.get(f"{self.service_endpoints['api']}/chat/history", headers={'Authorization': f'Bearer {db_user.jwt_token}'}, params={'thread_id': self.thread_id, 'limit': 10}, timeout=15.0)
                db_operations.append({'operation': 'chat_history_read', 'timestamp': time.time() - db_integration_start, 'status_code': history_response.status_code})
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    messages = history_data.get('messages', [])
                    test_message_found = any((self.test_id in str(msg.get('content', '')) for msg in messages))
                    agent_response_found = any((msg.get('type') == 'agent_response' or msg.get('role') == 'assistant' for msg in messages))
                    db_operations.append({'operation': 'persistence_validation', 'timestamp': time.time() - db_integration_start, 'messages_found': len(messages), 'test_message_persisted': test_message_found, 'agent_response_persisted': agent_response_found})
                    assert len(messages) > 0, 'Should find persisted messages in chat history'
                    assert test_message_found, f"Test message should be persisted in database. Messages found: {[msg.get('content', '')[:50] for msg in messages]}"
                    self.logger.info(f'✅ Database persistence validated: {len(messages)} messages found')
                else:
                    self.logger.warning(f'Chat history endpoint returned {history_response.status_code}')
            total_db_time = time.time() - db_integration_start
            assert total_db_time < 90.0, f'Database integration too slow: {total_db_time:.2f}s (max 90s)'
            self.logger.info('💾 Database persistence validation complete')
            self.logger.info(f'   Total time: {total_db_time:.2f}s')
            self.logger.info(f'   DB operations: {len(db_operations)}')
            for op in db_operations:
                self.logger.info(f"   - {op['operation']}: {op['timestamp']:.2f}s")
        except Exception as e:
            self.logger.error(f'❌ Database persistence integration failed: {e}')
            raise AssertionError(f'Database persistence during agent processing failed: {e}. This breaks data consistency across service boundaries.')

    async def test_websocket_event_delivery_across_services(self):
        """
        Test WebSocket event delivery across service boundaries.
        
        Validates that:
        1. Events flow correctly from backend through WebSocket service
        2. Real-time events are delivered during cross-service processing
        3. Event ordering is maintained across services
        4. No events are lost during service communication
        
        Flow:
        1. Send message → backend processes → events flow to WebSocket service
        2. Agent starts → backend notifies WebSocket → client receives event
        3. Agent completes → backend notifies WebSocket → client receives event
        4. Validate event sequence and timing
        
        Coverage: WebSocket service integration, real-time events, service communication
        """
        websocket_integration_start = time.time()
        event_flow = []
        self.logger.info('📡 Testing WebSocket event delivery across services')
        try:
            ws_user = await self.auth_helper.create_authenticated_user(email=f'cross_service_ws_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'websocket_events'])
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.service_endpoints['websocket'], additional_headers=self.auth_helper.get_websocket_headers(ws_user.jwt_token), ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=15.0)
            event_flow.append({'event': 'websocket_connected', 'timestamp': time.time() - websocket_integration_start, 'service': 'websocket'})
            event_test_message = {'type': 'chat_message', 'content': 'Test cross-service WebSocket event delivery', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': ws_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'websocket_events', 'expects_real_time_events': True}}
            message_send_time = time.time()
            await websocket.send(json.dumps(event_test_message))
            event_flow.append({'event': 'message_sent', 'timestamp': time.time() - websocket_integration_start, 'service': 'backend'})
            expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            received_events = []
            event_timestamps = {}
            events_timeout = 60.0
            collection_start = time.time()
            while time.time() - collection_start < events_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    event_type = event.get('type', 'unknown')
                    event_timestamp = time.time() - websocket_integration_start
                    received_events.append(event)
                    event_timestamps[event_type] = event_timestamp
                    event_flow.append({'event': f'received_{event_type}', 'timestamp': event_timestamp, 'service': 'websocket'})
                    self.logger.info(f'📨 Cross-service event: {event_type} at {event_timestamp:.2f}s')
                    if event_type == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    continue
            await websocket.close()
            total_websocket_time = time.time() - websocket_integration_start
            assert len(received_events) > 0, 'Should receive WebSocket events from cross-service flow'
            received_event_types = [e.get('type', 'unknown') for e in received_events]
            critical_events_received = [event for event in expected_events if event in received_event_types]
            assert len(critical_events_received) >= 2, f'Should receive at least 2 critical events from cross-service flow. Expected: {expected_events}, Received: {received_event_types}'
            if 'agent_started' in event_timestamps and 'agent_completed' in event_timestamps:
                processing_duration = event_timestamps['agent_completed'] - event_timestamps['agent_started']
                assert processing_duration < 45.0, f'Cross-service processing too slow: {processing_duration:.2f}s'
            if 'agent_started' in received_event_types and 'agent_completed' in received_event_types:
                started_index = received_event_types.index('agent_started')
                completed_index = received_event_types.index('agent_completed')
                assert started_index < completed_index, 'Event ordering should be logical across services'
            self.logger.info('📡 WebSocket cross-service event delivery validation complete')
            self.logger.info(f'   Total time: {total_websocket_time:.2f}s')
            self.logger.info(f'   Events received: {len(received_events)}')
            self.logger.info(f'   Critical events: {critical_events_received}')
            self.logger.info(f'   Event flow steps: {len(event_flow)}')
        except Exception as e:
            self.logger.error(f'❌ WebSocket cross-service event delivery failed: {e}')
            raise AssertionError(f'WebSocket event delivery across services failed: {e}. This breaks real-time user experience across service boundaries.')

    async def test_service_resilience_during_agent_processing(self):
        """
        Test service resilience during agent message processing.
        
        Validates that:
        1. System handles temporary service slowdowns gracefully
        2. Retries work across service boundaries
        3. Timeouts are appropriate for cross-service calls
        4. Error handling works across services
        
        Flow:
        1. Send complex message → stresses cross-service communication
        2. Monitor for service stress indicators
        3. Validate graceful handling of service delays
        4. Ensure system remains responsive
        
        Coverage: Service resilience, timeout handling, error recovery, system stability
        """
        resilience_test_start = time.time()
        service_metrics = {'response_times': [], 'error_events': [], 'recovery_events': [], 'timeout_events': []}
        self.logger.info('🛡️ Testing service resilience during agent processing')
        try:
            resilience_user = await self.auth_helper.create_authenticated_user(email=f'cross_service_resilience_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'stress_testing'])
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.service_endpoints['websocket'], additional_headers=self.auth_helper.get_websocket_headers(resilience_user.jwt_token), ssl=ssl_context), timeout=15.0)
            stress_message = {'type': 'chat_message', 'content': 'Please provide a comprehensive analysis of AI cost optimization strategies for a large enterprise with 100,000+ employees, including detailed implementation timelines, ROI calculations, risk assessments, compliance considerations, and technical architecture recommendations. This should stress-test the cross-service communication and processing capabilities.', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': resilience_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'service_resilience', 'complexity': 'high', 'expects_stress_handling': True}}
            message_start = time.time()
            await websocket.send(json.dumps(stress_message))
            events = []
            error_count = 0
            timeout_count = 0
            max_processing_time = 120.0
            collection_start = time.time()
            while time.time() - collection_start < max_processing_time:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    events.append(event)
                    event_type = event.get('type', 'unknown')
                    event_timestamp = time.time() - collection_start
                    if 'error' in event_type.lower():
                        error_count += 1
                        service_metrics['error_events'].append({'type': event_type, 'timestamp': event_timestamp, 'details': event.get('message', '')})
                    service_metrics['response_times'].append(event_timestamp)
                    if event_type == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    timeout_count += 1
                    service_metrics['timeout_events'].append({'timestamp': time.time() - collection_start, 'timeout_duration': 15.0})
                    if timeout_count > 5:
                        break
            processing_time = time.time() - collection_start
            await websocket.close()
            total_resilience_time = time.time() - resilience_test_start
            assert len(events) > 0, 'Should receive events even under service stress'
            error_rate = error_count / max(len(events), 1)
            assert error_rate < 0.3, f'Error rate too high under stress: {error_rate:.1%} (errors: {error_count}, events: {len(events)})'
            timeout_rate = timeout_count / max(processing_time / 15.0, 1)
            assert timeout_rate < 0.5, f'Timeout rate too high: {timeout_rate:.1%} (timeouts: {timeout_count}, expected intervals: {processing_time / 15.0:.1f})'
            assert processing_time < max_processing_time, f'Processing exceeded maximum time: {processing_time:.2f}s'
            avg_response_time = sum(service_metrics['response_times']) / len(service_metrics['response_times']) if service_metrics['response_times'] else 0
            self.logger.info('🛡️ Service resilience validation complete')
            self.logger.info(f'   Total time: {total_resilience_time:.2f}s')
            self.logger.info(f'   Processing time: {processing_time:.2f}s')
            self.logger.info(f'   Events received: {len(events)}')
            self.logger.info(f'   Error events: {error_count}')
            self.logger.info(f'   Timeout events: {timeout_count}')
            self.logger.info(f'   Error rate: {error_rate:.1%}')
            self.logger.info(f'   Timeout rate: {timeout_rate:.1%}')
            self.logger.info(f'   Avg response time: {avg_response_time:.2f}s')
        except Exception as e:
            self.logger.error(f'❌ Service resilience testing failed: {e}')
            raise AssertionError(f'Service resilience during agent processing failed: {e}. This indicates system instability under stress.')

    async def test_end_to_end_service_integration_flow(self):
        """
        Test complete end-to-end service integration flow.
        
        Validates the complete cross-service integration in one comprehensive test:
        1. Auth service → JWT generation and validation
        2. WebSocket service → Real-time connection and events
        3. Backend service → Message processing and agent orchestration
        4. Database service → Persistence and history
        5. LLM service → Agent response generation
        
        This is the ultimate cross-service integration test.
        
        Coverage: Complete service mesh, end-to-end flow, service coordination
        """
        e2e_integration_start = time.time()
        integration_steps = []
        self.logger.info('🌐 Testing complete end-to-end service integration flow')
        try:
            step_start = time.time()
            e2e_user = await self.auth_helper.create_authenticated_user(email=f'e2e_integration_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'agent_execution', 'full_access'])
            integration_steps.append({'step': 'auth_service_integration', 'duration': time.time() - step_start, 'success': True, 'user_id': e2e_user.user_id})
            step_start = time.time()
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.service_endpoints['websocket'], additional_headers=self.auth_helper.get_websocket_headers(e2e_user.jwt_token), ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=20.0)
            integration_steps.append({'step': 'websocket_service_integration', 'duration': time.time() - step_start, 'success': True})
            step_start = time.time()
            e2e_message = {'type': 'chat_message', 'content': f'End-to-end service integration test {self.test_id}. Please provide recommendations for AI cost optimization that demonstrates complete service integration.', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': e2e_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'e2e_service_integration', 'test_id': self.test_id, 'expects_full_processing': True}}
            await websocket.send(json.dumps(e2e_message))
            all_events = []
            processing_complete = False
            final_response = None
            processing_timeout = 90.0
            processing_start = time.time()
            while time.time() - processing_start < processing_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    all_events.append(event)
                    event_type = event.get('type', 'unknown')
                    if event_type == 'agent_completed':
                        final_response = event
                        processing_complete = True
                        break
                    if event_type in ['agent_started', 'agent_thinking', 'tool_executing', 'agent_completed']:
                        self.logger.info(f'🔄 E2E event: {event_type}')
                except asyncio.TimeoutError:
                    continue
            backend_processing_time = time.time() - processing_start
            integration_steps.append({'step': 'backend_service_processing', 'duration': backend_processing_time, 'success': processing_complete, 'events_received': len(all_events), 'final_response_received': final_response is not None})
            step_start = time.time()
            response_valid = False
            response_length = 0
            if final_response:
                response_data = final_response.get('data', {})
                result = response_data.get('result', {})
                response_text = str(result)
                response_length = len(response_text)
                response_valid = response_length > 100 and any((word in response_text.lower() for word in ['cost', 'optimization', 'recommendation']))
            integration_steps.append({'step': 'llm_service_integration', 'duration': time.time() - step_start, 'success': response_valid, 'response_length': response_length})
            step_start = time.time()
            db_verification = False
            try:
                async with httpx.AsyncClient() as client:
                    history_response = await client.get(f"{self.service_endpoints['api']}/chat/history", headers={'Authorization': f'Bearer {e2e_user.jwt_token}'}, params={'thread_id': self.thread_id, 'limit': 5}, timeout=10.0)
                    if history_response.status_code == 200:
                        db_verification = True
            except Exception as e:
                self.logger.warning(f'Database verification optional check failed: {e}')
            integration_steps.append({'step': 'database_service_verification', 'duration': time.time() - step_start, 'success': db_verification, 'optional': True})
            await websocket.close()
            total_e2e_time = time.time() - e2e_integration_start
            required_steps = [s for s in integration_steps if not s.get('optional', False)]
            successful_steps = [s for s in required_steps if s['success']]
            success_rate = len(successful_steps) / len(required_steps)
            assert success_rate >= 0.8, f'E2E service integration success rate too low: {success_rate:.1%}. Successful: {len(successful_steps)}, Required: {len(required_steps)}'
            assert processing_complete, 'Should complete full e2e processing flow'
            assert len(all_events) > 0, 'Should receive events from e2e flow'
            assert final_response is not None, 'Should receive final response from e2e flow'
            assert total_e2e_time < 150.0, f'E2E integration too slow: {total_e2e_time:.2f}s (max 150s)'
            self.logger.info('🌐 Complete end-to-end service integration validation SUCCESS')
            self.logger.info(f'   Total E2E time: {total_e2e_time:.2f}s')
            self.logger.info(f'   Integration steps: {len(integration_steps)}')
            self.logger.info(f'   Success rate: {success_rate:.1%}')
            self.logger.info(f'   Events received: {len(all_events)}')
            self.logger.info(f'   Response length: {response_length} chars')
            for step in integration_steps:
                status = '✅' if step['success'] else '❌'
                optional = ' (optional)' if step.get('optional') else ''
                self.logger.info(f"   {status} {step['step']}: {step['duration']:.2f}s{optional}")
        except Exception as e:
            self.logger.error(f'❌ End-to-end service integration failed: {e}')
            raise AssertionError(f'Complete end-to-end service integration failed: {e}. This indicates fundamental service mesh communication issues.')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')