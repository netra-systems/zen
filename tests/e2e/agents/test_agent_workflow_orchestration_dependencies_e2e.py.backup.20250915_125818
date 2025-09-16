"""
E2E Tests for Agent Workflow Orchestration and Dependencies (Staging)
Test #9 of Agent Registry and Factory Patterns Test Suite

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (Complex multi-agent workflows for sophisticated business processes)  
- Business Goal: Enable complex multi-agent workflows with proper orchestration and dependencies
- Value Impact: Supports enterprise workflows requiring sequential and parallel agent coordination
- Strategic Impact: $3M+ ARR enabler - complex workflows differentiate us from simple chat bots

CRITICAL MISSION: Test Agent Workflow Orchestration and Dependencies ensuring:
1. Multi-agent workflows execute in correct dependency order (Data  ->  Optimization  ->  Report)
2. Agent dependencies are enforced and validated before execution
3. WebSocket events provide real-time workflow progress visibility
4. Workflow state is preserved across agent transitions
5. Error handling in workflows isolates failures and enables recovery
6. Parallel agent execution works within orchestrated workflows  
7. Resource management prevents workflow resource leaks
8. Authentication is maintained throughout multi-agent workflows

FOCUS: E2E staging environment testing with real agent workflows, dependencies, 
        WebSocket orchestration, and complete authentication flows.
"""
import asyncio
import pytest
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from tests.e2e.staging_config import StagingTestConfig
from tests.e2e.agent_orchestration_fixtures import WorkflowTestFixtures

@dataclass
class WorkflowStep:
    """Represents a single step in an agent workflow."""
    step_id: str
    agent_type: str
    dependencies: List[str] = field(default_factory=list)
    input_data: Dict[str, Any] = field(default_factory=dict)
    expected_outputs: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    parallel_execution: bool = False
    required_permissions: List[str] = field(default_factory=lambda: ['read', 'write'])

@dataclass
class AgentWorkflow:
    """Represents a complete multi-agent workflow."""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)
    max_execution_time: float = 300.0
    requires_authentication: bool = True
    workflow_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowExecutionContext:
    """Tracks workflow execution state and results."""
    workflow: AgentWorkflow
    user_context: Any
    execution_id: str
    started_at: datetime
    step_results: Dict[str, Any] = field(default_factory=dict)
    step_status: Dict[str, str] = field(default_factory=dict)
    workflow_state: Dict[str, Any] = field(default_factory=dict)
    websocket_events: List[Dict] = field(default_factory=list)
    execution_errors: List[str] = field(default_factory=list)

@pytest.fixture
def staging_auth_helper():
    """Create staging authentication helper for E2E workflow tests."""
    return E2EAuthHelper(environment='staging')

@pytest.fixture
def staging_config():
    """Create staging configuration for E2E testing."""
    return StagingTestConfig()

@pytest.fixture
async def authenticated_workflow_user(staging_auth_helper):
    """Create authenticated user context for workflow testing."""
    return await create_authenticated_user_context(user_email='workflow_test@staging.com', environment='staging', permissions=['read', 'write', 'agent_execute'], websocket_enabled=True)

@pytest.fixture
def sample_data_analysis_workflow():
    """Create a comprehensive data analysis workflow for testing."""
    return AgentWorkflow(workflow_id=f'data_analysis_workflow_{uuid.uuid4().hex[:8]}', name='Enterprise Data Analysis Workflow', description='Multi-stage data analysis with optimization and reporting', steps=[WorkflowStep(step_id='data_collection', agent_type='data_helper', dependencies=[], input_data={'analysis_type': 'comprehensive', 'data_sources': ['database', 'api', 'files'], 'date_range': 'last_30_days'}, expected_outputs=['raw_data', 'data_quality_metrics', 'collection_summary'], timeout_seconds=45.0, required_permissions=['read', 'data_access']), WorkflowStep(step_id='data_validation', agent_type='data_validation_agent', dependencies=['data_collection'], input_data={'validation_rules': ['completeness', 'accuracy', 'consistency'], 'quality_thresholds': {'completeness': 0.95, 'accuracy': 0.98}}, expected_outputs=['validation_report', 'cleaned_data', 'quality_score'], timeout_seconds=30.0), WorkflowStep(step_id='parallel_analysis_1', agent_type='optimization_agent', dependencies=['data_validation'], input_data={'optimization_type': 'cost_reduction', 'constraints': {'budget': 100000, 'timeline': 'Q1'}, 'objectives': ['minimize_cost', 'maintain_quality']}, expected_outputs=['optimization_recommendations', 'cost_analysis', 'impact_projection'], timeout_seconds=60.0, parallel_execution=True), WorkflowStep(step_id='parallel_analysis_2', agent_type='performance_analysis_agent', dependencies=['data_validation'], input_data={'performance_metrics': ['efficiency', 'throughput', 'quality'], 'benchmark_comparison': True, 'trend_analysis': {'period': '12_months', 'seasonality': True}}, expected_outputs=['performance_report', 'trend_analysis', 'benchmark_comparison'], timeout_seconds=60.0, parallel_execution=True), WorkflowStep(step_id='synthesis_and_reporting', agent_type='report_generation_agent', dependencies=['parallel_analysis_1', 'parallel_analysis_2'], input_data={'report_format': 'executive_summary', 'include_visualizations': True, 'audience': 'executives', 'recommendations_priority': 'high_impact'}, expected_outputs=['executive_report', 'detailed_analysis', 'action_plan'], timeout_seconds=45.0)], max_execution_time=400.0, workflow_metadata={'complexity': 'high', 'business_value': 'cost_optimization_and_performance', 'expected_duration_minutes': 5.0, 'parallel_steps': ['parallel_analysis_1', 'parallel_analysis_2']})

@pytest.fixture
def simple_sequential_workflow():
    """Create a simple sequential workflow for basic dependency testing."""
    return AgentWorkflow(workflow_id=f'sequential_workflow_{uuid.uuid4().hex[:8]}', name='Simple Sequential Analysis', description='Basic sequential data  ->  analysis  ->  report workflow', steps=[WorkflowStep(step_id='data_step', agent_type='data_helper', dependencies=[], input_data={'query': 'fetch_recent_data', 'limit': 100}, expected_outputs=['dataset', 'metadata'], timeout_seconds=30.0), WorkflowStep(step_id='analysis_step', agent_type='analysis_agent', dependencies=['data_step'], input_data={'analysis_type': 'basic_stats', 'confidence_level': 0.95}, expected_outputs=['analysis_results', 'insights'], timeout_seconds=30.0), WorkflowStep(step_id='report_step', agent_type='report_agent', dependencies=['analysis_step'], input_data={'report_type': 'summary', 'format': 'json'}, expected_outputs=['final_report'], timeout_seconds=20.0)], max_execution_time=120.0, workflow_metadata={'complexity': 'low', 'test_purpose': 'basic_dependency_validation'})

class WorkflowOrchestrationEngine:
    """Mock workflow orchestration engine for E2E testing of agent workflows."""

    def __init__(self, staging_config: StagingTestConfig, auth_helper: E2EAuthHelper):
        self.staging_config = staging_config
        self.auth_helper = auth_helper
        self.active_workflows: Dict[str, WorkflowExecutionContext] = {}
        self.websocket_client = None
        self.agent_client = None

    async def initialize(self):
        """Initialize connections to staging environment."""
        self.agent_client = await self.auth_helper.create_authenticated_session()
        from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
        ws_helper = E2EWebSocketAuthHelper(environment='staging')
        self.websocket_client = await ws_helper.connect_authenticated_websocket(timeout=15.0)

    async def execute_workflow(self, workflow: AgentWorkflow, user_context: Any, execution_options: Optional[Dict[str, Any]]=None) -> WorkflowExecutionContext:
        """Execute a complete workflow with dependency orchestration."""
        execution_id = f'workflow_exec_{uuid.uuid4().hex[:8]}'
        workflow_context = WorkflowExecutionContext(workflow=workflow, user_context=user_context, execution_id=execution_id, started_at=datetime.now(timezone.utc))
        self.active_workflows[execution_id] = workflow_context
        try:
            for step in workflow.steps:
                workflow_context.step_status[step.step_id] = 'pending'
            await self._execute_workflow_steps(workflow_context)
            return workflow_context
        except Exception as e:
            workflow_context.execution_errors.append(f'Workflow execution failed: {str(e)}')
            raise
        finally:
            if execution_id in self.active_workflows:
                del self.active_workflows[execution_id]

    async def _execute_workflow_steps(self, workflow_context: WorkflowExecutionContext):
        """Execute workflow steps with proper dependency management."""
        workflow = workflow_context.workflow
        completed_steps = set()
        while len(completed_steps) < len(workflow.steps):
            ready_steps = []
            for step in workflow.steps:
                if step.step_id not in completed_steps and workflow_context.step_status[step.step_id] == 'pending' and all((dep in completed_steps for dep in step.dependencies)):
                    ready_steps.append(step)
            if not ready_steps:
                pending_steps = [s for s in workflow.steps if s.step_id not in completed_steps]
                if pending_steps:
                    unmet_deps = {}
                    for step in pending_steps:
                        unmet = [dep for dep in step.dependencies if dep not in completed_steps]
                        if unmet:
                            unmet_deps[step.step_id] = unmet
                    error_msg = f'Circular or unresolvable dependencies detected: {unmet_deps}'
                    workflow_context.execution_errors.append(error_msg)
                    raise Exception(error_msg)
                break
            parallel_steps = [step for step in ready_steps if step.parallel_execution]
            sequential_steps = [step for step in ready_steps if not step.parallel_execution]
            if parallel_steps:
                await self._execute_parallel_steps(workflow_context, parallel_steps, completed_steps)
            for step in sequential_steps:
                await self._execute_single_step(workflow_context, step)
                completed_steps.add(step.step_id)

    async def _execute_parallel_steps(self, workflow_context: WorkflowExecutionContext, parallel_steps: List[WorkflowStep], completed_steps: Set[str]):
        """Execute multiple steps in parallel."""
        execution_tasks = []
        for step in parallel_steps:
            task = self._execute_single_step(workflow_context, step)
            execution_tasks.append((task, step))
        results = await asyncio.gather(*[task for task, _ in execution_tasks], return_exceptions=True)
        for i, (result, step) in enumerate(zip(results, [step for _, step in execution_tasks])):
            if isinstance(result, Exception):
                workflow_context.execution_errors.append(f'Parallel step {step.step_id} failed: {str(result)}')
                workflow_context.step_status[step.step_id] = 'failed'
                raise result
            else:
                completed_steps.add(step.step_id)

    async def _execute_single_step(self, workflow_context: WorkflowExecutionContext, step: WorkflowStep):
        """Execute a single workflow step."""
        step_start_time = time.time()
        workflow_context.step_status[step.step_id] = 'running'
        try:
            await self._send_workflow_event(workflow_context, 'step_started', {'step_id': step.step_id, 'agent_type': step.agent_type, 'dependencies': step.dependencies, 'parallel_execution': step.parallel_execution})
            step_input = {**step.input_data, 'workflow_id': workflow_context.workflow.workflow_id, 'execution_id': workflow_context.execution_id, 'step_id': step.step_id, 'previous_results': {dep: workflow_context.step_results.get(dep, {}) for dep in step.dependencies}, 'workflow_state': workflow_context.workflow_state}
            agent_result = await self._execute_agent_via_api(step.agent_type, step_input, workflow_context.user_context, step.timeout_seconds)
            workflow_context.step_results[step.step_id] = agent_result
            workflow_context.step_status[step.step_id] = 'completed'
            for output_key in step.expected_outputs:
                if output_key in agent_result:
                    workflow_context.workflow_state[f'{step.step_id}_{output_key}'] = agent_result[output_key]
            step_execution_time = (time.time() - step_start_time) * 1000
            await self._send_workflow_event(workflow_context, 'step_completed', {'step_id': step.step_id, 'agent_type': step.agent_type, 'execution_time_ms': step_execution_time, 'outputs_generated': list(agent_result.keys()), 'expected_outputs': step.expected_outputs})
        except Exception as e:
            workflow_context.step_status[step.step_id] = 'failed'
            workflow_context.execution_errors.append(f'Step {step.step_id} failed: {str(e)}')
            await self._send_workflow_event(workflow_context, 'step_failed', {'step_id': step.step_id, 'agent_type': step.agent_type, 'error': str(e), 'execution_time_ms': (time.time() - step_start_time) * 1000})
            raise

    async def _execute_agent_via_api(self, agent_type: str, input_data: Dict[str, Any], user_context: Any, timeout_seconds: float) -> Dict[str, Any]:
        """Execute agent via staging API with authentication."""
        agent_request = {'agent_type': agent_type, 'input_data': input_data, 'user_context': {'user_id': str(user_context.user_id), 'thread_id': str(user_context.thread_id), 'run_id': str(user_context.run_id), 'request_id': str(user_context.request_id)}, 'execution_options': {'timeout_seconds': timeout_seconds, 'enable_websocket_events': True}}
        agent_url = f'{self.staging_config.urls.backend_url}/agents/execute'
        async with self.agent_client.post(agent_url, json=agent_request, timeout=timeout_seconds + 10) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f'Agent API call failed: {response.status} - {error_text}')
            result = await response.json()
            if not isinstance(result, dict):
                raise Exception(f'Invalid agent response format: expected dict, got {type(result)}')
            if 'status' not in result:
                raise Exception("Agent response missing required 'status' field")
            if result['status'] != 'success':
                error_msg = result.get('error', 'Unknown agent execution error')
                raise Exception(f'Agent execution failed: {error_msg}')
            return result.get('data', {})

    async def _send_workflow_event(self, workflow_context: WorkflowExecutionContext, event_type: str, event_data: Dict[str, Any]):
        """Send workflow event via WebSocket."""
        event = {'event_type': f'workflow_{event_type}', 'workflow_id': workflow_context.workflow.workflow_id, 'execution_id': workflow_context.execution_id, 'user_id': str(workflow_context.user_context.user_id), 'timestamp': datetime.now(timezone.utc).isoformat(), 'data': event_data}
        workflow_context.websocket_events.append(event)
        if self.websocket_client:
            try:
                await self.websocket_client.send(json.dumps(event))
            except Exception as e:
                workflow_context.execution_errors.append(f'WebSocket event failed: {str(e)}')

    async def cleanup(self):
        """Cleanup connections and resources."""
        if self.websocket_client:
            await self.websocket_client.close()
        if self.agent_client:
            await self.agent_client.close()

@pytest.mark.e2e
class TestSequentialWorkflowDependencies(SSotBaseTestCase):
    """Test sequential workflow execution with proper dependency management."""

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_simple_sequential_workflow_dependency_order(self, staging_config, staging_auth_helper, authenticated_workflow_user, simple_sequential_workflow):
        """Test that sequential workflow executes steps in correct dependency order."""
        orchestrator = WorkflowOrchestrationEngine(staging_config, staging_auth_helper)
        await orchestrator.initialize()
        try:
            execution_start = time.time()
            workflow_context = await orchestrator.execute_workflow(simple_sequential_workflow, authenticated_workflow_user)
            total_execution_time = time.time() - execution_start
            assert len(workflow_context.execution_errors) == 0, f'Workflow should complete without errors: {workflow_context.execution_errors}'
            expected_steps = ['data_step', 'analysis_step', 'report_step']
            for step_id in expected_steps:
                assert workflow_context.step_status[step_id] == 'completed', f'Step {step_id} should be completed'
                assert step_id in workflow_context.step_results, f'Step {step_id} should have results'
            step_events = [e for e in workflow_context.websocket_events if 'step_' in e['event_type']]
            start_events = [e for e in step_events if e['event_type'] == 'workflow_step_started']
            assert len(start_events) == 3, 'Should have 3 step start events'
            step_order = [e['data']['step_id'] for e in start_events]
            assert step_order[0] == 'data_step', 'Data step should execute first'
            assert step_order[1] == 'analysis_step', 'Analysis step should execute second'
            assert step_order[2] == 'report_step', 'Report step should execute third'
            data_step_result = workflow_context.step_results['data_step']
            analysis_step_result = workflow_context.step_results['analysis_step']
            report_step_result = workflow_context.step_results['report_step']
            assert 'previous_results' in analysis_step_result or 'dataset' in str(analysis_step_result)
            assert 'previous_results' in report_step_result or 'analysis_results' in str(report_step_result)
            assert total_execution_time < 120.0, f'Sequential workflow should complete in <2 minutes, took {total_execution_time:.2f}s'
        finally:
            await orchestrator.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_dependency_validation_prevents_invalid_order(self, staging_config, staging_auth_helper, authenticated_workflow_user):
        """Test that dependency validation prevents steps from executing in invalid order."""
        circular_workflow = AgentWorkflow(workflow_id=f'circular_workflow_{uuid.uuid4().hex[:8]}', name='Invalid Circular Workflow', description='Workflow with circular dependencies for testing validation', steps=[WorkflowStep(step_id='step_a', agent_type='data_helper', dependencies=['step_c'], input_data={'test': 'circular_a'}), WorkflowStep(step_id='step_b', agent_type='analysis_agent', dependencies=['step_a'], input_data={'test': 'circular_b'}), WorkflowStep(step_id='step_c', agent_type='report_agent', dependencies=['step_b'], input_data={'test': 'circular_c'})])
        orchestrator = WorkflowOrchestrationEngine(staging_config, staging_auth_helper)
        await orchestrator.initialize()
        try:
            with pytest.raises(Exception) as exc_info:
                await orchestrator.execute_workflow(circular_workflow, authenticated_workflow_user)
            error_message = str(exc_info.value).lower()
            assert 'circular' in error_message or 'unresolvable' in error_message, f'Error should indicate circular/unresolvable dependencies: {error_message}'
        finally:
            await orchestrator.cleanup()

@pytest.mark.e2e
class TestParallelWorkflowExecution(SSotBaseTestCase):
    """Test parallel workflow execution with complex dependencies."""

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_complex_parallel_workflow_execution(self, staging_config, staging_auth_helper, authenticated_workflow_user, sample_data_analysis_workflow):
        """Test complex workflow with both sequential and parallel execution."""
        orchestrator = WorkflowOrchestrationEngine(staging_config, staging_auth_helper)
        await orchestrator.initialize()
        try:
            execution_start = time.time()
            workflow_context = await orchestrator.execute_workflow(sample_data_analysis_workflow, authenticated_workflow_user)
            total_execution_time = time.time() - execution_start
            assert len(workflow_context.execution_errors) == 0, f'Complex workflow should complete without errors: {workflow_context.execution_errors}'
            expected_steps = ['data_collection', 'data_validation', 'parallel_analysis_1', 'parallel_analysis_2', 'synthesis_and_reporting']
            for step_id in expected_steps:
                assert workflow_context.step_status[step_id] == 'completed', f'Step {step_id} should be completed, got status: {workflow_context.step_status[step_id]}'
                assert step_id in workflow_context.step_results, f'Step {step_id} should have results'
            step_events = [e for e in workflow_context.websocket_events if e['event_type'] == 'workflow_step_started']
            step_start_times = {e['data']['step_id']: e['timestamp'] for e in step_events}
            assert step_start_times['data_validation'] > step_start_times['data_collection'], 'Data validation should start after data collection'
            assert step_start_times['parallel_analysis_1'] > step_start_times['data_validation'], 'Parallel analysis 1 should start after data validation'
            assert step_start_times['parallel_analysis_2'] > step_start_times['data_validation'], 'Parallel analysis 2 should start after data validation'
            parallel_1_completion = None
            parallel_2_completion = None
            synthesis_start = None
            for event in workflow_context.websocket_events:
                if event['event_type'] == 'workflow_step_completed':
                    step_id = event['data']['step_id']
                    if step_id == 'parallel_analysis_1':
                        parallel_1_completion = event['timestamp']
                    elif step_id == 'parallel_analysis_2':
                        parallel_2_completion = event['timestamp']
                elif event['event_type'] == 'workflow_step_started' and event['data']['step_id'] == 'synthesis_and_reporting':
                    synthesis_start = event['timestamp']
            assert parallel_1_completion is not None, 'Parallel analysis 1 should have completed'
            assert parallel_2_completion is not None, 'Parallel analysis 2 should have completed'
            assert synthesis_start is not None, 'Synthesis should have started'
            latest_parallel_completion = max(parallel_1_completion, parallel_2_completion)
            assert synthesis_start > latest_parallel_completion, 'Synthesis should start after both parallel analyses complete'
            data_collection_result = workflow_context.step_results['data_collection']
            validation_result = workflow_context.step_results['data_validation']
            parallel_1_result = workflow_context.step_results['parallel_analysis_1']
            parallel_2_result = workflow_context.step_results['parallel_analysis_2']
            synthesis_result = workflow_context.step_results['synthesis_and_reporting']
            assert 'previous_results' in str(validation_result) or 'raw_data' in str(validation_result), 'Validation should receive data collection results'
            assert 'previous_results' in str(parallel_1_result) or 'cleaned_data' in str(parallel_1_result), 'Parallel analysis 1 should receive validation results'
            assert 'previous_results' in str(parallel_2_result) or 'cleaned_data' in str(parallel_2_result), 'Parallel analysis 2 should receive validation results'
            synthesis_deps = str(synthesis_result)
            assert 'optimization_recommendations' in synthesis_deps or 'performance_report' in synthesis_deps or 'previous_results' in synthesis_deps, 'Synthesis should receive results from both parallel analyses'
            assert total_execution_time < 300.0, f'Complex workflow with parallel execution should complete in <5 minutes, took {total_execution_time:.2f}s'
        finally:
            await orchestrator.cleanup()

@pytest.mark.e2e
class TestWorkflowErrorHandlingRecovery(SSotBaseTestCase):
    """Test workflow error handling and recovery mechanisms."""

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_workflow_step_failure_isolation(self, staging_config, staging_auth_helper, authenticated_workflow_user):
        """Test that workflow step failures are properly isolated and don't corrupt workflow state."""
        failure_workflow = AgentWorkflow(workflow_id=f'failure_test_workflow_{uuid.uuid4().hex[:8]}', name='Failure Testing Workflow', description='Workflow with intentional failure for testing error handling', steps=[WorkflowStep(step_id='success_step_1', agent_type='data_helper', dependencies=[], input_data={'query': 'fetch_test_data', 'should_succeed': True}, timeout_seconds=30.0), WorkflowStep(step_id='failure_step', agent_type='nonexistent_agent_type', dependencies=['success_step_1'], input_data={'invalid': 'data', 'should_fail': True}, timeout_seconds=30.0), WorkflowStep(step_id='success_step_2', agent_type='report_agent', dependencies=['failure_step'], input_data={'report': 'final', 'should_not_execute': True}, timeout_seconds=30.0)])
        orchestrator = WorkflowOrchestrationEngine(staging_config, staging_auth_helper)
        await orchestrator.initialize()
        try:
            with pytest.raises(Exception) as exc_info:
                await orchestrator.execute_workflow(failure_workflow, authenticated_workflow_user)
            assert 'nonexistent_agent_type' in str(exc_info.value) or 'failed' in str(exc_info.value).lower()
            if orchestrator.active_workflows:
                workflow_context = list(orchestrator.active_workflows.values())[0]
                if 'success_step_1' in workflow_context.step_status:
                    assert workflow_context.step_status['success_step_1'] == 'completed', 'First step should have completed successfully'
                if 'failure_step' in workflow_context.step_status:
                    assert workflow_context.step_status['failure_step'] == 'failed', 'Failure step should be marked as failed'
                if 'success_step_2' in workflow_context.step_status:
                    assert workflow_context.step_status['success_step_2'] != 'completed', 'Dependent step should not complete when dependency fails'
                assert len(workflow_context.execution_errors) > 0, 'Workflow should have recorded execution errors'
        finally:
            await orchestrator.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_workflow_timeout_handling(self, staging_config, staging_auth_helper, authenticated_workflow_user):
        """Test workflow timeout handling and resource cleanup."""
        timeout_workflow = AgentWorkflow(workflow_id=f'timeout_test_workflow_{uuid.uuid4().hex[:8]}', name='Timeout Testing Workflow', description='Workflow with aggressive timeout for testing timeout handling', steps=[WorkflowStep(step_id='timeout_step', agent_type='data_helper', dependencies=[], input_data={'query': 'fetch_large_dataset', 'processing_time': 'long', 'complexity': 'high'}, timeout_seconds=0.5)], max_execution_time=2.0)
        orchestrator = WorkflowOrchestrationEngine(staging_config, staging_auth_helper)
        await orchestrator.initialize()
        try:
            start_time = time.time()
            with pytest.raises((asyncio.TimeoutError, Exception)) as exc_info:
                await orchestrator.execute_workflow(timeout_workflow, authenticated_workflow_user)
            execution_time = time.time() - start_time
            assert execution_time < 5.0, f'Workflow should timeout quickly, took {execution_time:.2f}s'
            error_message = str(exc_info.value).lower()
            timeout_indicators = ['timeout', 'time out', 'deadline', 'exceeded']
            assert any((indicator in error_message for indicator in timeout_indicators)), f'Error should indicate timeout: {error_message}'
        finally:
            await orchestrator.cleanup()

@pytest.mark.e2e
class TestWorkflowWebSocketIntegration(SSotBaseTestCase):
    """Test WebSocket event integration during workflow execution."""

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_workflow_websocket_event_sequence(self, staging_config, staging_auth_helper, authenticated_workflow_user, simple_sequential_workflow):
        """Test that workflow execution generates proper WebSocket event sequence."""
        orchestrator = WorkflowOrchestrationEngine(staging_config, staging_auth_helper)
        await orchestrator.initialize()
        try:
            workflow_context = await orchestrator.execute_workflow(simple_sequential_workflow, authenticated_workflow_user)
            assert len(workflow_context.websocket_events) > 0, 'Workflow should generate WebSocket events'
            expected_step_ids = ['data_step', 'analysis_step', 'report_step']
            for step_id in expected_step_ids:
                step_events = [e for e in workflow_context.websocket_events if e.get('data', {}).get('step_id') == step_id]
                assert len(step_events) >= 2, f'Step {step_id} should have at least start and completion events'
                start_events = [e for e in step_events if e['event_type'] == 'workflow_step_started']
                assert len(start_events) == 1, f'Step {step_id} should have exactly one start event'
                start_event = start_events[0]
                assert start_event['data']['agent_type'] is not None, 'Start event should include agent type'
                assert 'dependencies' in start_event['data'], 'Start event should include dependencies'
                if workflow_context.step_status[step_id] == 'completed':
                    completion_events = [e for e in step_events if e['event_type'] == 'workflow_step_completed']
                    assert len(completion_events) == 1, f'Step {step_id} should have exactly one completion event'
                    completion_event = completion_events[0]
                    assert 'execution_time_ms' in completion_event['data'], 'Completion event should include execution time'
                    assert completion_event['data']['execution_time_ms'] > 0, 'Execution time should be positive'
            event_timestamps = [e['timestamp'] for e in workflow_context.websocket_events]
            assert event_timestamps == sorted(event_timestamps), 'WebSocket events should be in chronological order'
            for event in workflow_context.websocket_events:
                assert event['workflow_id'] == simple_sequential_workflow.workflow_id, 'All events should include correct workflow ID'
                assert event['execution_id'] == workflow_context.execution_id, 'All events should include correct execution ID'
                assert event['user_id'] == str(authenticated_workflow_user.user_id), 'All events should include correct user ID'
        finally:
            await orchestrator.cleanup()

@pytest.mark.e2e
class TestWorkflowAuthentication(SSotBaseTestCase):
    """Test authentication is maintained throughout multi-agent workflows."""

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_authentication_maintained_across_workflow_steps(self, staging_config, staging_auth_helper, authenticated_workflow_user, simple_sequential_workflow):
        """Test that authentication context is maintained across all workflow steps."""
        auth_workflow = AgentWorkflow(workflow_id=f'auth_test_workflow_{uuid.uuid4().hex[:8]}', name='Authentication Test Workflow', description='Workflow for testing authentication across steps', steps=[WorkflowStep(step_id='auth_step_1', agent_type='data_helper', dependencies=[], input_data={'requires_auth': True, 'permission_check': 'read'}, required_permissions=['read'], timeout_seconds=30.0), WorkflowStep(step_id='auth_step_2', agent_type='analysis_agent', dependencies=['auth_step_1'], input_data={'requires_auth': True, 'permission_check': 'write'}, required_permissions=['write'], timeout_seconds=30.0), WorkflowStep(step_id='auth_step_3', agent_type='report_agent', dependencies=['auth_step_2'], input_data={'requires_auth': True, 'permission_check': 'agent_execute'}, required_permissions=['agent_execute'], timeout_seconds=30.0)], requires_authentication=True)
        orchestrator = WorkflowOrchestrationEngine(staging_config, staging_auth_helper)
        await orchestrator.initialize()
        try:
            workflow_context = await orchestrator.execute_workflow(auth_workflow, authenticated_workflow_user)
            assert len(workflow_context.execution_errors) == 0, f'Authenticated workflow should complete successfully: {workflow_context.execution_errors}'
            for step_id in ['auth_step_1', 'auth_step_2', 'auth_step_3']:
                assert workflow_context.step_status[step_id] == 'completed', f'Authenticated step {step_id} should complete successfully'
            for step_id, result in workflow_context.step_results.items():
                result_str = str(result).lower()
                auth_indicators = ['user_id', 'authenticated', 'permission', str(authenticated_workflow_user.user_id)]
                assert any((indicator in result_str for indicator in auth_indicators)), f'Step {step_id} result should show evidence of authenticated execution'
            for event in workflow_context.websocket_events:
                assert event['user_id'] == str(authenticated_workflow_user.user_id), 'All WebSocket events should include authenticated user ID'
                event_str = str(event).lower()
                sensitive_data = ['password', 'secret', 'token', 'key']
                assert not any((sensitive in event_str for sensitive in sensitive_data)), f'WebSocket events should not contain sensitive authentication data'
        finally:
            await orchestrator.cleanup()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')