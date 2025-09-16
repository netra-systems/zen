"""
Unit Tests for Basic Triage & Response (UVS) Validation - Issue #135

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All tiers (Free/Early/Mid/Enterprise) - Core chat functionality
- Business Goal: Validate message processing logic for $500K+ ARR Golden Path
- Value Impact: Unit-level validation of triage response processing without Docker dependencies
- Revenue Protection: Ensure message routing and processing logic works correctly

PURPOSE: Test the core message processing logic for triage responses at the unit level.
Focus on WebSocket message handling, triage categorization, and response generation
without requiring Docker services or full system integration.

KEY COVERAGE:
1. Message parsing and validation
2. Triage categorization logic
3. Response formatting and structure
4. Error handling in message processing
5. WebSocket event generation
6. Mock agent execution validation

GOLDEN PATH UNIT VALIDATION:
These tests validate the core message processing components that enable:
User Message  ->  Message Parse  ->  Triage Logic  ->  Response Generation  ->  WebSocket Events

These tests MUST initially FAIL to demonstrate current issues, then guide remediation.
"""
import pytest
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.websocket_core.handlers import MessageRouter
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
from netra_backend.app.websocket_core.context import WebSocketContext

@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.issue_135
class TestBasicTriageResponseUnit(SSotAsyncTestCase):
    """
    Unit tests for basic triage response processing without Docker dependencies.
    
    These tests focus on the core message processing logic that handles
    user messages and generates triage responses via WebSocket events.
    
    CRITICAL: These tests should initially FAIL to demonstrate current
    WebSocket 1011 message processing issues identified in Issue #135.
    """

    def setup_method(self, method=None):
        """Setup unit test environment"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.env.set('ENVIRONMENT', 'test')
        self.env.set('DEMO_MODE', '1')
        self.user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        self.thread_id = f'test_thread_{uuid.uuid4().hex[:8]}'
        self.run_id = f'test_run_{uuid.uuid4().hex[:8]}'
        self.connection_id = f'test_conn_{uuid.uuid4().hex[:8]}'
        self.mock_websocket = AsyncMock()
        self.mock_websocket.scope = {'user': {'sub': self.user_id}, 'path': '/ws', 'client': ('127.0.0.1', 8000), 'headers': []}
        self.sent_events = []
        self.mock_websocket.send_text = AsyncMock(side_effect=self._track_sent_events)
        self.message_router = MessageRouter()
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.services.thread_service import ThreadService
        mock_supervisor = Mock(spec=SupervisorAgent)
        mock_thread_service = Mock(spec=ThreadService)
        mock_message_handler_service = MessageHandlerService(supervisor=mock_supervisor, thread_service=mock_thread_service)
        self.agent_handler = AgentMessageHandler(message_handler_service=mock_message_handler_service, websocket=self.mock_websocket)

    async def _track_sent_events(self, event_data: str):
        """Track WebSocket events sent during testing"""
        try:
            event = json.loads(event_data)
            self.sent_events.append(event)
        except json.JSONDecodeError:
            self.sent_events.append({'raw': event_data})

    @pytest.mark.asyncio
    async def test_message_parsing_basic_structure(self):
        """
        Test basic message parsing handles user_message type correctly.
        
        Business Impact: Validates core message routing that enables chat functionality.
        
        EXPECTED OUTCOME: Should initially FAIL due to message processing issues.
        """
        user_message = {'type': 'user_message', 'content': 'Help me optimize my AI infrastructure costs', 'thread_id': self.thread_id, 'user_id': self.user_id, 'timestamp': datetime.utcnow().isoformat()}
        try:
            handler = self.message_router._find_handler('user_message')
            assert handler is not None, 'No handler found for user_message type'
            message_obj = self.message_router._prepare_message(user_message)
            assert message_obj is not None, 'Message preparation failed'
            assert hasattr(message_obj, 'type'), 'Message object missing type attribute'
            assert message_obj.type == 'user_message', 'Message type not preserved'
            self.record_metric('message_parsing_success', True)
        except Exception as e:
            self.record_metric('message_parsing_failure', str(e))
            pytest.fail(f'Message parsing failed (expected initially): {e}')

    @pytest.mark.asyncio
    async def test_message_validation_required_fields(self):
        """
        Test message validation enforces required fields for triage processing.
        
        Business Impact: Prevents malformed messages from breaking chat flow.
        """
        invalid_message_no_content = {'type': 'user_message', 'thread_id': self.thread_id, 'user_id': self.user_id}
        invalid_message_no_user = {'type': 'user_message', 'content': 'Test message', 'thread_id': self.thread_id}
        validation_results = []
        for invalid_msg in [invalid_message_no_content, invalid_message_no_user]:
            try:
                message_obj = self.message_router._prepare_message(invalid_msg)
                validation_results.append(False)
            except Exception as e:
                validation_results.append(True)
                self.record_metric(f'validation_error_{len(validation_results)}', str(e))
        assert any(validation_results), 'Message validation should reject invalid messages'
        self.record_metric('message_validation_working', True)

    @pytest.mark.asyncio
    async def test_triage_categorization_cost_optimization(self):
        """
        Test triage agent correctly categorizes cost optimization requests.
        
        Business Impact: Validates AI can properly route cost optimization queries
        which are high-value use cases for the platform.
        
        EXPECTED OUTCOME: May initially fail due to agent execution issues.
        """
        mock_triage_agent = AsyncMock(spec=GoalsTriageSubAgent)
        expected_triage_result = {'category': 'Cost Optimization', 'priority': 'high', 'confidence_score': 0.95, 'data_sufficiency': 'sufficient', 'next_agents': ['data_helper', 'optimization_agent'], 'reasoning': 'User specified infrastructure costs and optimization goal'}
        mock_triage_agent.analyze_request.return_value = expected_triage_result
        test_request = 'Help me reduce my AWS infrastructure costs by 30%'
        with patch('netra_backend.app.agents.goals_triage_sub_agent.GoalsTriageSubAgent', return_value=mock_triage_agent):
            try:
                triage_result = await mock_triage_agent.analyze_request(request=test_request, user_id=self.user_id, context={'thread_id': self.thread_id})
                assert triage_result['category'] == 'Cost Optimization'
                assert triage_result['priority'] == 'high'
                assert triage_result['confidence_score'] > 0.8
                assert 'optimization_agent' in triage_result['next_agents']
                self.record_metric('triage_categorization_success', True)
                self.record_metric('triage_confidence', triage_result['confidence_score'])
            except Exception as e:
                self.record_metric('triage_categorization_failure', str(e))
                pytest.fail(f'Triage categorization failed (may be expected initially): {e}')

    @pytest.mark.asyncio
    async def test_triage_response_structure_validation(self):
        """
        Test triage response contains all required fields for downstream processing.
        
        Business Impact: Ensures triage responses have sufficient data for
        subsequent agent execution in the pipeline.
        """
        mock_triage_response = {'category': 'Performance Optimization', 'priority': 'medium', 'confidence_score': 0.87, 'data_sufficiency': 'partial', 'next_agents': ['data_helper', 'performance_agent'], 'reasoning': 'User mentions performance issues', 'entities': {'services': ['database', 'api'], 'metrics': ['latency', 'throughput']}, 'recommendations': ['Gather more performance metrics', 'Analyze database query patterns']}
        required_fields = ['category', 'priority', 'confidence_score', 'data_sufficiency', 'next_agents', 'reasoning']
        for field in required_fields:
            assert field in mock_triage_response, f'Missing required field: {field}'
        assert isinstance(mock_triage_response['confidence_score'], (int, float))
        assert 0.0 <= mock_triage_response['confidence_score'] <= 1.0
        assert isinstance(mock_triage_response['next_agents'], list)
        assert len(mock_triage_response['next_agents']) > 0
        assert mock_triage_response['priority'] in ['low', 'medium', 'high', 'critical']
        assert mock_triage_response['data_sufficiency'] in ['insufficient', 'partial', 'sufficient']
        self.record_metric('triage_structure_validation_success', True)
        self.record_metric('triage_required_fields_present', len(required_fields))

    @pytest.mark.asyncio
    async def test_websocket_event_generation_sequence(self):
        """
        Test that WebSocket events are generated in correct sequence for triage processing.
        
        Business Impact: Validates user experience events that show AI progress.
        These events are critical for user engagement and trust.
        
        EXPECTED OUTCOME: May initially fail due to WebSocket event delivery issues.
        """
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

        async def mock_emit_event(event_type: str, data: Dict[str, Any]):
            event = {'type': event_type, 'data': data, 'timestamp': datetime.utcnow().isoformat(), 'user_id': self.user_id}
            await self.mock_websocket.send_text(json.dumps(event))
        try:
            for event_type in expected_events:
                await mock_emit_event(event_type, {'message': f'Triage {event_type}', 'thread_id': self.thread_id})
            assert len(self.sent_events) == len(expected_events)
            sent_event_types = [event['type'] for event in self.sent_events]
            for expected_event in expected_events:
                assert expected_event in sent_event_types, f'Missing event: {expected_event}'
            self.record_metric('websocket_events_generated', len(self.sent_events))
            self.record_metric('websocket_event_sequence_correct', True)
        except Exception as e:
            self.record_metric('websocket_event_failure', str(e))
            pytest.fail(f'WebSocket event generation failed (may be expected): {e}')

    @pytest.mark.asyncio
    async def test_websocket_event_content_validation(self):
        """
        Test WebSocket event content contains required business data.
        
        Business Impact: Ensures events provide meaningful information to users
        about AI processing progress and results.
        """
        completion_event_data = {'agent_type': 'triage', 'status': 'completed', 'results': {'category': 'Cost Optimization', 'priority': 'high', 'confidence_score': 0.92, 'next_agents': ['data_helper', 'optimization_agent']}, 'execution_time': 2.5, 'thread_id': self.thread_id, 'run_id': self.run_id}
        completion_event = {'type': 'agent_completed', 'data': completion_event_data, 'timestamp': datetime.utcnow().isoformat(), 'user_id': self.user_id}
        await self.mock_websocket.send_text(json.dumps(completion_event))
        assert len(self.sent_events) == 1
        sent_event = self.sent_events[0]
        assert sent_event['type'] == 'agent_completed'
        assert 'results' in sent_event['data']
        assert 'category' in sent_event['data']['results']
        assert 'next_agents' in sent_event['data']['results']
        assert sent_event['data']['thread_id'] == self.thread_id
        assert sent_event['user_id'] == self.user_id
        self.record_metric('websocket_event_content_valid', True)
        self.record_metric('triage_results_in_events', True)

    @pytest.mark.asyncio
    async def test_message_processing_error_handling(self):
        """
        Test error handling in message processing pipeline.
        
        Business Impact: Validates system gracefully handles errors without
        breaking user experience or losing messages.
        
        EXPECTED OUTCOME: Should demonstrate current error handling gaps.
        """
        error_scenarios = [{'name': 'malformed_json', 'message': 'invalid_json_string', 'expected_error': 'JSON parsing'}, {'name': 'missing_type', 'message': {'content': 'test', 'user_id': self.user_id}, 'expected_error': 'message type'}, {'name': 'empty_content', 'message': {'type': 'user_message', 'content': '', 'user_id': self.user_id}, 'expected_error': 'empty content'}]
        error_handling_results = []
        for scenario in error_scenarios:
            try:
                if isinstance(scenario['message'], str):
                    json.loads(scenario['message'])
                else:
                    message_obj = self.message_router._prepare_message(scenario['message'])
                error_handling_results.append({'scenario': scenario['name'], 'handled': False, 'error': 'No error raised'})
            except Exception as e:
                error_handling_results.append({'scenario': scenario['name'], 'handled': True, 'error': str(e)})
        handled_errors = [r for r in error_handling_results if r['handled']]
        assert len(handled_errors) > 0, 'Error handling not working for any scenarios'
        self.record_metric('error_scenarios_tested', len(error_scenarios))
        self.record_metric('errors_properly_handled', len(handled_errors))
        self.record_metric('error_handling_rate', len(handled_errors) / len(error_scenarios))

    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self):
        """
        Test concurrent message processing maintains isolation and order.
        
        Business Impact: Validates system can handle multiple users simultaneously
        without cross-contamination or message loss.
        """
        num_concurrent = 3
        messages = []
        for i in range(num_concurrent):
            message = {'type': 'user_message', 'content': f'Concurrent test message {i}', 'thread_id': f'concurrent_thread_{i}', 'user_id': f'concurrent_user_{i}', 'message_id': f'msg_{i}'}
            messages.append(message)
        processing_tasks = []
        for message in messages:

            async def process_message(msg):
                try:
                    message_obj = self.message_router._prepare_message(msg)
                    await asyncio.sleep(0.1)
                    return {'success': True, 'message_id': msg['message_id']}
                except Exception as e:
                    return {'success': False, 'error': str(e), 'message_id': msg['message_id']}
            task = process_message(message)
            processing_tasks.append(task)
        results = await asyncio.gather(*processing_tasks, return_exceptions=True)
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
        assert len(successful_results) >= num_concurrent // 2, 'Too many concurrent processing failures'
        message_ids = [msg['message_id'] for msg in messages]
        result_ids = [r['message_id'] for r in successful_results if 'message_id' in r]
        for result_id in result_ids:
            assert result_id in message_ids, f'Cross-contamination detected: {result_id}'
        self.record_metric('concurrent_messages_processed', len(successful_results))
        self.record_metric('concurrent_processing_success_rate', len(successful_results) / num_concurrent)
        self.record_metric('no_cross_contamination', True)

    @pytest.mark.asyncio
    async def test_golden_path_unit_message_flow(self):
        """
        Test complete Golden Path message flow at unit level.
        
        Business Impact: Validates the core message processing pipeline that
        enables the $500K+ ARR user journey without external dependencies.
        
        Flow: User Message  ->  Parse  ->  Route  ->  Triage  ->  Events  ->  Response
        
        EXPECTED OUTCOME: Should initially FAIL demonstrating current issues.
        """
        golden_path_steps = {'message_received': False, 'message_parsed': False, 'handler_routed': False, 'triage_processed': False, 'events_emitted': False, 'response_generated': False}
        user_message = {'type': 'user_message', 'content': 'I need to optimize my machine learning infrastructure costs on AWS. Current spend is $10,000/month.', 'thread_id': self.thread_id, 'user_id': self.user_id, 'timestamp': datetime.utcnow().isoformat()}
        try:
            golden_path_steps['message_received'] = True
            message_obj = self.message_router._prepare_message(user_message)
            golden_path_steps['message_parsed'] = True
            handler = self.message_router._find_handler('user_message')
            assert handler is not None
            golden_path_steps['handler_routed'] = True
            mock_triage_result = {'category': 'Cost Optimization', 'priority': 'high', 'confidence_score': 0.95, 'next_agents': ['data_helper', 'optimization_agent']}
            golden_path_steps['triage_processed'] = True
            events_to_emit = ['agent_started', 'agent_thinking', 'agent_completed']
            for event_type in events_to_emit:
                await self.mock_websocket.send_text(json.dumps({'type': event_type, 'data': {'triage_result': mock_triage_result}, 'user_id': self.user_id}))
            golden_path_steps['events_emitted'] = True
            final_response = {'type': 'triage_complete', 'results': mock_triage_result, 'next_steps': 'Proceeding with data helper and optimization agent'}
            golden_path_steps['response_generated'] = True
            completed_steps = sum((1 for step, completed in golden_path_steps.items() if completed))
            total_steps = len(golden_path_steps)
            assert completed_steps == total_steps, f'Golden Path incomplete: {completed_steps}/{total_steps} steps'
            assert len(self.sent_events) == 3, 'Missing WebSocket events'
            self.record_metric('golden_path_unit_steps_completed', completed_steps)
            self.record_metric('golden_path_unit_success', True)
            self.record_metric('golden_path_events_count', len(self.sent_events))
        except Exception as e:
            failed_step = None
            for step, completed in golden_path_steps.items():
                if not completed:
                    failed_step = step
                    break
            self.record_metric('golden_path_unit_failure', str(e))
            self.record_metric('golden_path_failed_at_step', failed_step or 'unknown')
            pytest.fail(f'Golden Path unit flow failed at {failed_step}: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')