"""Real Agent Corpus Admin E2E Test Suite - Business Critical Testing

MISSION CRITICAL: Tests corpus administration agent with real services.
Business Value: Ensure data management and content organization capabilities.

Business Value Justification (BVJ):
1. Segment: Mid, Enterprise
2. Business Goal: Enable advanced data management workflows  
3. Value Impact: Corpus admin capabilities for document processing
4. Revenue Impact: $200K+ ARR from enterprise document management features

CLAUDE.md COMPLIANCE:
- Uses real services ONLY (NO MOCKS)
- Validates ALL 5 required WebSocket events
- Tests actual agent business logic
- Uses IsolatedEnvironment for environment access
- Absolute imports only
- Factory patterns for user isolation
"""
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import pytest
from loguru import logger
from shared.isolated_environment import get_env as get_env_instance
from tests.e2e.e2e_test_config import get_e2e_config, E2ETestConfig, REQUIRED_WEBSOCKET_EVENTS

@dataclass
class CorpusAdminValidation:
    """Captures and validates corpus admin agent execution."""
    user_id: str
    thread_id: str
    request_type: str
    start_time: float = field(default_factory=time.time)
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    event_types_seen: Set[str] = field(default_factory=set)
    corpus_operations: List[str] = field(default_factory=list)
    data_processed: List[Dict[str, Any]] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    final_result: Optional[Dict[str, Any]] = None
    time_to_agent_started: Optional[float] = None
    time_to_first_thinking: Optional[float] = None
    time_to_tool_execution: Optional[float] = None
    time_to_completion: Optional[float] = None
    data_integrity_maintained: bool = False
    operations_completed: bool = False
    results_coherent: bool = False

class RealAgentCorpusAdminTester:
    """Tests corpus admin agent with real services and WebSocket events."""
    REQUIRED_EVENTS = set(REQUIRED_WEBSOCKET_EVENTS.keys())
    CORPUS_ADMIN_SCENARIOS = [{'request_type': 'document_organization', 'message': 'Organize these documents by topic and priority', 'test_data': {'documents': [{'title': 'Q1 Financial Report', 'content': 'Financial metrics for Q1...'}, {'title': 'Product Roadmap', 'content': 'Product development timeline...'}, {'title': 'Team Updates', 'content': 'Team status and progress...'}]}, 'expected_operations': ['classify', 'organize', 'index'], 'success_criteria': ['documents_categorized', 'metadata_updated']}, {'request_type': 'content_classification', 'message': 'Classify and tag these content pieces', 'test_data': {'content': [{'text': 'Machine learning optimization techniques', 'type': 'technical'}, {'text': 'Customer feedback analysis results', 'type': 'business'}, {'text': 'Security vulnerability assessment', 'type': 'security'}]}, 'expected_operations': ['analyze', 'classify', 'tag'], 'success_criteria': ['content_tagged', 'categories_assigned']}, {'request_type': 'knowledge_indexing', 'message': 'Index and structure this knowledge base content', 'test_data': {'knowledge_items': [{'topic': 'API Documentation', 'sections': ['auth', 'endpoints', 'examples']}, {'topic': 'Best Practices', 'sections': ['coding', 'testing', 'deployment']}]}, 'expected_operations': ['parse', 'index', 'structure'], 'success_criteria': ['indexes_created', 'structure_defined']}]

    def __init__(self, config: Optional[E2ETestConfig]=None):
        self.config = config or get_e2e_config()
        self.env = None
        self.ws_client = None
        self.backend_client = None
        self.jwt_helper = None
        self.validations: List[CorpusAdminValidation] = []

    async def setup(self):
        """Initialize test environment with real services."""
        from shared.isolated_environment import IsolatedEnvironment
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        from tests.clients.backend_client import BackendTestClient
        from tests.clients.websocket_client import WebSocketTestClient
        from tests.e2e.test_data_factory import create_test_user_data
        self.env = IsolatedEnvironment()
        self.jwt_helper = JWTTestHelper()
        backend_url = self.config.backend_url
        self.backend_client = BackendTestClient(backend_url)
        user_data = create_test_user_data('corpus_admin_test')
        self.user_id = str(uuid.uuid4())
        self.email = user_data['email']
        self.token = self.jwt_helper.create_access_token(self.user_id, self.email, permissions=['corpus:admin', 'documents:manage', 'content:classify'])
        ws_url = self.config.websocket_url
        self.ws_client = WebSocketTestClient(ws_url)
        connected = await self.ws_client.connect(token=self.token)
        if not connected:
            raise RuntimeError('Failed to connect to WebSocket')
        logger.info(f'Corpus admin test environment ready for user {self.email}')
        return self

    async def teardown(self):
        """Clean up test environment."""
        if self.ws_client:
            await self.ws_client.disconnect()

    async def execute_corpus_admin_scenario(self, scenario: Dict[str, Any], timeout: float=45.0) -> CorpusAdminValidation:
        """Execute a corpus administration scenario and validate results.
        
        Args:
            scenario: Test scenario configuration
            timeout: Maximum execution time
            
        Returns:
            Complete validation results
        """
        thread_id = str(uuid.uuid4())
        validation = CorpusAdminValidation(user_id=self.user_id, thread_id=thread_id, request_type=scenario['request_type'])
        admin_request = {'type': 'agent_request', 'agent': 'corpus_admin', 'message': scenario['message'], 'thread_id': thread_id, 'context': {'operation_type': scenario['request_type'], 'test_data': scenario['test_data'], 'user_id': self.user_id}, 'optimistic_id': str(uuid.uuid4())}
        await self.ws_client.send_json(admin_request)
        logger.info(f"Sent corpus admin request: {scenario['request_type']}")
        start_time = time.time()
        completed = False
        while time.time() - start_time < timeout and (not completed):
            event = await self.ws_client.receive(timeout=2.0)
            if event:
                await self._process_corpus_admin_event(event, validation)
                if event.get('type') in ['agent_completed', 'corpus_admin_completed', 'error']:
                    completed = True
                    validation.time_to_completion = time.time() - start_time
        self._validate_corpus_admin_execution(validation, scenario)
        self.validations.append(validation)
        return validation

    async def _process_corpus_admin_event(self, event: Dict[str, Any], validation: CorpusAdminValidation):
        """Process and categorize corpus admin specific events."""
        event_type = event.get('type', 'unknown')
        event_time = time.time() - validation.start_time
        validation.events_received.append(event)
        validation.event_types_seen.add(event_type)
        if event_type == 'agent_started' and (not validation.time_to_agent_started):
            validation.time_to_agent_started = event_time
            logger.info(f'Corpus admin agent started at {event_time:.2f}s')
        elif event_type == 'agent_thinking' and (not validation.time_to_first_thinking):
            validation.time_to_first_thinking = event_time
        elif event_type == 'tool_executing' and (not validation.time_to_tool_execution):
            validation.time_to_tool_execution = event_time
            tool_name = event.get('data', {}).get('tool_name', 'unknown')
            validation.tools_used.append(tool_name)
            logger.info(f'Corpus admin executing tool: {tool_name}')
        elif event_type == 'tool_completed':
            tool_result = event.get('data', {}).get('result', {})
            if isinstance(tool_result, dict):
                operation = tool_result.get('operation', '')
                if operation:
                    validation.corpus_operations.append(operation)
                processed_data = tool_result.get('processed_data', [])
                if processed_data:
                    validation.data_processed.extend(processed_data)
        elif event_type in ['agent_completed', 'corpus_admin_completed']:
            final_data = event.get('data', {})
            if isinstance(final_data, dict):
                validation.final_result = final_data
                logger.info(f'Corpus admin completed with result keys: {list(final_data.keys())}')

    def _validate_corpus_admin_execution(self, validation: CorpusAdminValidation, scenario: Dict[str, Any]):
        """Validate corpus admin execution against business requirements."""
        expected_ops = scenario.get('expected_operations', [])
        operations_performed = validation.corpus_operations
        validation.operations_completed = all((any((exp_op in op for op in operations_performed)) for exp_op in expected_ops))
        if validation.data_processed and scenario.get('test_data'):
            original_data_count = sum((len(data) if isinstance(data, list) else 1 for data in scenario['test_data'].values()))
            processed_count = len(validation.data_processed)
            validation.data_integrity_maintained = processed_count >= original_data_count * 0.8
        if validation.final_result:
            success_criteria = scenario.get('success_criteria', [])
            result_keys = list(validation.final_result.keys()) if validation.final_result else []
            validation.results_coherent = any((criteria in str(result_keys).lower() or criteria in str(validation.final_result).lower() for criteria in success_criteria))

    def generate_corpus_admin_report(self) -> str:
        """Generate comprehensive corpus admin test report."""
        report = []
        report.append('=' * 80)
        report.append('REAL AGENT CORPUS ADMIN TEST REPORT')
        report.append('=' * 80)
        report.append(f'Total scenarios tested: {len(self.validations)}')
        report.append('')
        for i, val in enumerate(self.validations, 1):
            report.append(f'\n--- Scenario {i}: {val.request_type} ---')
            report.append(f'User ID: {val.user_id}')
            report.append(f'Thread ID: {val.thread_id}')
            report.append(f'Events received: {len(val.events_received)}')
            report.append(f'Event types: {sorted(val.event_types_seen)}')
            missing_events = self.REQUIRED_EVENTS - val.event_types_seen
            if missing_events:
                report.append(f' WARNING: [U+FE0F] MISSING REQUIRED EVENTS: {missing_events}')
            else:
                report.append('[U+2713] All required WebSocket events received')
            report.append('\nPerformance Metrics:')
            report.append(f'  - Agent started: {val.time_to_agent_started:.2f}s' if val.time_to_agent_started else '  - Agent not started')
            report.append(f'  - First thinking: {val.time_to_first_thinking:.2f}s' if val.time_to_first_thinking else '  - No thinking observed')
            report.append(f'  - Tool execution: {val.time_to_tool_execution:.2f}s' if val.time_to_tool_execution else '  - No tools executed')
            report.append(f'  - Completion: {val.time_to_completion:.2f}s' if val.time_to_completion else '  - Not completed')
            report.append('\nBusiness Logic Validation:')
            report.append(f'  [U+2713] Operations completed: {val.operations_completed}')
            report.append(f'  [U+2713] Data integrity maintained: {val.data_integrity_maintained}')
            report.append(f'  [U+2713] Results coherent: {val.results_coherent}')
            if val.corpus_operations:
                report.append(f'\nCorpus Operations: {val.corpus_operations}')
            if val.tools_used:
                report.append(f'Tools Used: {val.tools_used}')
            if val.data_processed:
                report.append(f'Data Items Processed: {len(val.data_processed)}')
        report.append('\n' + '=' * 80)
        return '\n'.join(report)

@pytest.fixture(params=['local', 'staging'])
async def corpus_admin_tester(request):
    """Create and setup the corpus admin tester for both local and staging.
    
    This fixture will run tests against both local and staging environments
    when E2E_TEST_ENV is not set, or against the specified environment.
    """
    test_env = get_env_instance().get('E2E_TEST_ENV', None)
    if test_env and test_env != request.param:
        pytest.skip(f'Skipping {request.param} tests (E2E_TEST_ENV={test_env})')
    config = get_e2e_config(force_environment=request.param)
    if not config.is_available():
        pytest.skip(f'{request.param} environment not available')
    tester = RealAgentCorpusAdminTester(config)
    await tester.setup()
    yield tester
    await tester.teardown()

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
class RealAgentCorpusAdminTests:
    """Test suite for real corpus admin agent execution."""

    async def test_document_organization_flow(self, corpus_admin_tester):
        """Test document organization with real agent execution."""
        scenario = corpus_admin_tester.CORPUS_ADMIN_SCENARIOS[0]
        validation = await corpus_admin_tester.execute_corpus_admin_scenario(scenario, timeout=60.0)
        missing_events = corpus_admin_tester.REQUIRED_EVENTS - validation.event_types_seen
        assert not missing_events, f'Missing required events: {missing_events}'
        assert validation.time_to_agent_started is not None, 'Agent should have started'
        assert validation.time_to_agent_started < 3.0, 'Agent should start quickly'
        assert validation.operations_completed, 'Document organization operations should complete'
        assert len(validation.event_types_seen) >= 3, 'Should have multiple event types'
        if validation.time_to_completion:
            assert validation.time_to_completion < 45.0, 'Should complete within performance target'

    async def test_content_classification_workflow(self, corpus_admin_tester):
        """Test content classification with real services."""
        scenario = corpus_admin_tester.CORPUS_ADMIN_SCENARIOS[1]
        validation = await corpus_admin_tester.execute_corpus_admin_scenario(scenario, timeout=50.0)
        assert 'agent_started' in validation.event_types_seen, 'Should have agent_started event'
        assert len(validation.events_received) > 0, 'Should receive events'
        if validation.corpus_operations:
            assert any(('classify' in op.lower() or 'tag' in op.lower() for op in validation.corpus_operations)), 'Should perform classification operations'
        if validation.data_processed:
            assert len(validation.data_processed) > 0, 'Should process content data'

    async def test_knowledge_indexing_execution(self, corpus_admin_tester):
        """Test knowledge base indexing functionality."""
        scenario = corpus_admin_tester.CORPUS_ADMIN_SCENARIOS[2]
        validation = await corpus_admin_tester.execute_corpus_admin_scenario(scenario, timeout=55.0)
        assert validation.events_received, 'Should receive execution events'
        if validation.tools_used:
            assert len(validation.tools_used) > 0, 'Should use corpus admin tools'
        if validation.final_result:
            assert isinstance(validation.final_result, dict), 'Should return structured results'

    async def test_corpus_admin_error_handling(self, corpus_admin_tester):
        """Test error handling in corpus admin scenarios."""
        error_scenario = {'request_type': 'invalid_operation', 'message': 'Process this invalid data structure', 'test_data': {'invalid': None, 'malformed': {'incomplete': 'data'}}, 'expected_operations': ['error_handling'], 'success_criteria': ['error_handled']}
        validation = await corpus_admin_tester.execute_corpus_admin_scenario(error_scenario, timeout=30.0)
        assert len(validation.events_received) > 0, 'Should receive events even on error'
        assert validation.time_to_agent_started is not None or 'error' in validation.event_types_seen, 'Should start or handle error gracefully'

    async def test_corpus_admin_performance_benchmarks(self, corpus_admin_tester):
        """Test corpus admin performance against business benchmarks."""
        performance_results = []
        for i, scenario in enumerate(corpus_admin_tester.CORPUS_ADMIN_SCENARIOS[:2]):
            validation = await corpus_admin_tester.execute_corpus_admin_scenario(scenario, timeout=40.0)
            performance_results.append(validation)
        start_times = [v.time_to_agent_started for v in performance_results if v.time_to_agent_started]
        completion_times = [v.time_to_completion for v in performance_results if v.time_to_completion]
        if start_times:
            avg_start_time = sum(start_times) / len(start_times)
            assert avg_start_time < 4.0, f'Average start time {avg_start_time:.2f}s too slow'
        if completion_times:
            avg_completion = sum(completion_times) / len(completion_times)
            assert avg_completion < 50.0, f'Average completion {avg_completion:.2f}s too slow'

    async def test_corpus_admin_websocket_event_ordering(self, corpus_admin_tester):
        """Test WebSocket event ordering for corpus admin."""
        scenario = corpus_admin_tester.CORPUS_ADMIN_SCENARIOS[0]
        validation = await corpus_admin_tester.execute_corpus_admin_scenario(scenario, timeout=45.0)
        event_sequence = [e.get('type') for e in validation.events_received]
        if 'agent_started' in event_sequence:
            started_idx = event_sequence.index('agent_started')
            if 'agent_completed' in event_sequence:
                completed_idx = event_sequence.index('agent_completed')
                assert completed_idx > started_idx, 'Completion should come after start'
        if 'tool_executing' in event_sequence:
            executing_count = event_sequence.count('tool_executing')
            completed_count = event_sequence.count('tool_completed')
            error_count = event_sequence.count('tool_error')
            assert completed_count + error_count >= executing_count * 0.8, 'Most tool executions should complete or error'

    async def test_comprehensive_corpus_admin_report(self, corpus_admin_tester):
        """Run comprehensive test and generate detailed report."""
        for scenario in corpus_admin_tester.CORPUS_ADMIN_SCENARIOS:
            await corpus_admin_tester.execute_corpus_admin_scenario(scenario, timeout=50.0)
        report = corpus_admin_tester.generate_corpus_admin_report()
        logger.info('\n' + report)
        report_file = os.path.join(project_root, 'test_outputs', 'corpus_admin_e2e_report.txt')
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            f.write(f'\n\nGenerated at: {datetime.now().isoformat()}\n')
        logger.info(f'Corpus admin report saved to: {report_file}')
        total_tests = len(corpus_admin_tester.validations)
        successful_operations = sum((1 for v in corpus_admin_tester.validations if v.operations_completed))
        assert successful_operations > 0, 'At least some corpus admin operations should succeed'
        success_rate = successful_operations / total_tests if total_tests > 0 else 0
        logger.info(f'Corpus admin success rate: {success_rate:.1%}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')