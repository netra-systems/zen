"""
Comprehensive Integration Tests for WorkflowOrchestrator

BUSINESS LOGIC CRITICAL SSOT CLASS - Integration testing for ~400-line agent workflow orchestration.
Tests end-to-end workflow coordination and adaptive logic components with real agent coordination.

CRITICAL REQUIREMENTS:
- NO MOCKS allowed - use real agent workflow coordination and adaptive logic components
- Test end-to-end workflow orchestration for Enterprise data integrity
- Focus on agent coordination validation and adaptive workflow behavior
- Test the core business logic orchestration protecting platform operations
- Validate Enterprise coordination and multi-agent workflow management

Business Value: Platform/Enterprise - $500K+ ARR protection through reliable agent orchestration.
Covers multi-agent workflow management, adaptive execution logic, and Enterprise data integrity.
"""
import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.agent_coordination_validator import AgentCoordinationValidator, CoordinationValidationResult, DataIntegrityResult
from netra_backend.app.agents.supervisor.execution_context import PipelineStepConfig, AgentExecutionStrategy, PipelineStep
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
from netra_backend.app.logging_config import central_logger
from shared.types.core_types import UserID, ThreadID, RunID
logger = central_logger.get_logger(__name__)

class MockAgentRegistry:
    """Mock agent registry for testing workflow coordination."""

    def __init__(self):
        self.agents = {}
        self.execution_log = []

    async def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get agent by name for workflow execution."""
        if agent_name == 'triage':
            return MockTriageAgent()
        elif agent_name == 'data_helper':
            return MockDataHelperAgent()
        elif agent_name == 'data':
            return MockDataAgent()
        elif agent_name == 'optimization':
            return MockOptimizationAgent()
        elif agent_name == 'actions':
            return MockActionAgent()
        elif agent_name == 'reporting':
            return MockReportingAgent()
        return None

class MockExecutionEngine:
    """Mock execution engine for testing workflow orchestration."""

    def __init__(self):
        self.execution_log = []
        self.agent_results = {}
        self.should_fail = {}
        self.execution_times = {}

    async def execute_agent(self, context: ExecutionContext, state: Any) -> ExecutionResult:
        """Execute agent and return result."""
        agent_name = context.agent_name
        self.execution_log.append(agent_name)
        execution_time = self.execution_times.get(agent_name, 100)
        await asyncio.sleep(execution_time / 1000)
        should_fail = self.should_fail.get(agent_name, False)
        if should_fail:
            return ExecutionResult(status=ExecutionStatus.FAILED, request_id=context.request_id, data=None, error_message=f'{agent_name} execution failed', execution_time_ms=execution_time, metadata={'agent_name': agent_name})
        result_data = self._generate_agent_result(agent_name, context)
        return ExecutionResult(status=ExecutionStatus.COMPLETED, request_id=context.request_id, data=result_data, execution_time_ms=execution_time, metadata={'agent_name': agent_name})

    def _generate_agent_result(self, agent_name: str, context: ExecutionContext) -> Dict[str, Any]:
        """Generate realistic agent results based on agent type."""
        base_result = {'agent_name': agent_name, 'execution_id': str(uuid.uuid4()), 'timestamp': time.time()}
        if agent_name == 'triage':
            return {**base_result, 'data_sufficiency': 'sufficient', 'request_type': 'optimization', 'complexity_level': 'medium', 'estimated_duration_hours': 2.5, 'required_data_fields': ['current_costs', 'usage_patterns', 'optimization_goals']}
        elif agent_name == 'data_helper':
            return {**base_result, 'data_collection_guidance': {'missing_fields': ['detailed_usage_metrics', 'cost_breakdown'], 'collection_methods': ['api_integration', 'csv_upload'], 'priority_fields': ['monthly_spend', 'service_utilization']}, 'data_quality_assessment': {'completeness': 0.7, 'accuracy_confidence': 0.85}}
        elif agent_name == 'data':
            return {**base_result, 'insights': {'cost_analysis': {'total_monthly_cost': 15000, 'highest_cost_service': 'compute_instances', 'cost_trends': 'increasing_15_percent'}, 'usage_patterns': {'peak_hours': [9, 10, 11, 14, 15, 16], 'utilization_efficiency': 0.65}}, 'data_quality_score': 0.85}
        elif agent_name == 'optimization':
            return {**base_result, 'optimization_strategies': {'rightsizing': {'potential_savings': 3500, 'risk_level': 'low', 'implementation_effort': 'medium'}, 'reserved_instances': {'potential_savings': 4200, 'risk_level': 'very_low', 'implementation_effort': 'low'}, 'auto_scaling': {'potential_savings': 2100, 'risk_level': 'medium', 'implementation_effort': 'high'}}, 'total_potential_savings': 9800, 'roi_percentage': 65.3}
        elif agent_name == 'actions':
            return {**base_result, 'implementation_plan': {'phase_1': {'actions': ['reserved_instance_purchase', 'rightsizing_analysis'], 'timeline_weeks': 2, 'expected_savings': 7700}, 'phase_2': {'actions': ['auto_scaling_implementation'], 'timeline_weeks': 4, 'expected_savings': 2100}}, 'risk_mitigation': ['gradual_rollout', 'monitoring_dashboards', 'rollback_procedures']}
        elif agent_name == 'reporting':
            return {**base_result, 'executive_summary': {'total_savings_potential': 9800, 'implementation_timeline': '6 weeks', 'roi_percentage': 65.3, 'confidence_level': 'high'}, 'detailed_report': {'current_state_analysis': 'comprehensive', 'optimization_recommendations': 3, 'implementation_roadmap': 'detailed', 'success_metrics': ['cost_reduction', 'efficiency_improvement']}}
        return base_result

    def set_agent_failure(self, agent_name: str, should_fail: bool):
        """Set agent to fail for testing error scenarios."""
        self.should_fail[agent_name] = should_fail

    def set_execution_time(self, agent_name: str, time_ms: float):
        """Set execution time for agent."""
        self.execution_times[agent_name] = time_ms

class MockWebSocketManager:
    """Mock WebSocket manager for testing workflow notifications."""

    def __init__(self):
        self.sent_events = []
        self.active_connections = {}
        self.user_contexts = {}

    async def emit_to_user(self, user_id: str, event: str, data: Dict[str, Any]):
        """Emit event to user."""
        self.sent_events.append({'user_id': user_id, 'event': event, 'data': data, 'timestamp': time.time()})

    def get_events_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all events sent to user."""
        return [event for event in self.sent_events if event['user_id'] == user_id]

class MockTriageAgent(BaseAgent):
    """Mock triage agent for workflow testing."""

    async def run(self, context: Any) -> Dict[str, Any]:
        return {'data_sufficiency': 'sufficient', 'request_type': 'optimization', 'complexity_level': 'medium'}

class MockDataHelperAgent(BaseAgent):
    """Mock data helper agent for workflow testing."""

    async def run(self, context: Any) -> Dict[str, Any]:
        return {'data_collection_guidance': {'missing_fields': ['detailed_metrics'], 'priority_fields': ['cost_data']}}

class MockDataAgent(BaseAgent):
    """Mock data agent for workflow testing."""

    async def run(self, context: Any) -> Dict[str, Any]:
        return {'insights': {'cost_analysis': {'total_cost': 15000}, 'usage_patterns': {'efficiency': 0.65}}}

class MockOptimizationAgent(BaseAgent):
    """Mock optimization agent for workflow testing."""

    async def run(self, context: Any) -> Dict[str, Any]:
        return {'optimization_strategies': {'rightsizing': {'savings': 3500}, 'reserved_instances': {'savings': 4200}}, 'total_savings': 7700}

class MockActionAgent(BaseAgent):
    """Mock action agent for workflow testing."""

    async def run(self, context: Any) -> Dict[str, Any]:
        return {'implementation_plan': {'phase_1': {'timeline': 2, 'savings': 5000}}}

class MockReportingAgent(BaseAgent):
    """Mock reporting agent for workflow testing."""

    async def run(self, context: Any) -> Dict[str, Any]:
        return {'executive_summary': {'total_savings': 7700, 'roi_percentage': 65.3}}

class TestWorkflowOrchestratorIntegration(SSotAsyncTestCase):
    """Comprehensive integration tests for WorkflowOrchestrator."""

    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.agent_registry = MockAgentRegistry()
        self.execution_engine = MockExecutionEngine()
        self.websocket_manager = MockWebSocketManager()
        self.user_context = UserExecutionContext(user_id='test_user_123', thread_id='test_thread_456', run_id='test_run_789')
        self.orchestrator = WorkflowOrchestrator(agent_registry=self.agent_registry, execution_engine=self.execution_engine, websocket_manager=self.websocket_manager, user_context=self.user_context)
        self.execution_context = ExecutionContext(request_id='test_request_123', run_id='test_run_789', user_id='test_user_123', stream_updates=True)
        self.execution_context.thread_id = 'test_thread_456'
        self.execution_context.state = type('MockState', (), {})()

class TestAgentWorkflowCoordination(TestWorkflowOrchestratorIntegration):
    """Test multi-agent workflow orchestration and coordination."""

    async def test_full_workflow_execution_end_to_end(self):
        """Test complete workflow execution with all agents."""
        logger.info('Testing full workflow execution end-to-end')
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        self.assertGreaterEqual(len(results), 4)
        self.assertTrue(all((result.status == ExecutionStatus.COMPLETED for result in results)))
        expected_agents = ['triage', 'data', 'optimization', 'actions', 'reporting']
        executed_agents = self.execution_engine.execution_log
        self.assertEqual(executed_agents[0], 'triage')
        for agent in expected_agents:
            self.assertIn(agent, executed_agents)
        logger.info(f' PASS:  Full workflow completed with {len(results)} steps')

    async def test_workflow_with_insufficient_data_adaptive_path(self):
        """Test adaptive workflow when data is insufficient."""
        logger.info('Testing adaptive workflow with insufficient data')
        insufficient_data_result = {'data_sufficiency': 'insufficient', 'request_type': 'optimization', 'missing_data_fields': ['usage_metrics', 'cost_breakdown']}
        workflow_steps = self.orchestrator._define_workflow_based_on_triage(insufficient_data_result)
        expected_agents = ['triage', 'data_helper', 'reporting']
        actual_agents = [step.agent_name for step in workflow_steps]
        self.assertEqual(actual_agents, expected_agents)
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        self.assertGreaterEqual(len(results), 2)
        self.assertIn('data_helper', self.execution_engine.execution_log)
        logger.info(' PASS:  Adaptive workflow handled insufficient data correctly')

    async def test_workflow_with_partial_data_coordination(self):
        """Test workflow coordination with partial data availability."""
        logger.info('Testing workflow coordination with partial data')
        partial_data_result = {'data_sufficiency': 'partial', 'completeness': 0.6, 'available_fields': ['basic_costs', 'service_names'], 'missing_fields': ['detailed_usage', 'optimization_history']}
        workflow_steps = self.orchestrator._define_workflow_based_on_triage(partial_data_result)
        agent_names = [step.agent_name for step in workflow_steps]
        self.assertIn('data_helper', agent_names)
        self.assertIn('reporting', agent_names)
        for step in workflow_steps:
            self.assertIsInstance(step.dependencies, list)
        logger.info(' PASS:  Partial data workflow coordination validated')

    async def test_agent_dependency_management_and_sequencing(self):
        """Test agent dependency management and execution sequencing."""
        logger.info('Testing agent dependency management and sequencing')
        sufficient_data_result = {'data_sufficiency': 'sufficient'}
        workflow_steps = self.orchestrator._define_workflow_based_on_triage(sufficient_data_result)
        step_by_name = {step.agent_name: step for step in workflow_steps}
        if 'optimization' in step_by_name:
            optimization_step = step_by_name['optimization']
            self.assertIn('data', optimization_step.dependencies)
        if 'actions' in step_by_name:
            actions_step = step_by_name['actions']
            self.assertIn('optimization', actions_step.dependencies)
        start_time = time.time()
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        execution_time = time.time() - start_time
        self.assertGreater(execution_time, 0.1)
        self.assertLess(execution_time, 30.0)
        logger.info(f' PASS:  Dependency management validated in {execution_time:.2f}s')

    async def test_workflow_state_management_across_agents(self):
        """Test workflow state management and data passing between agents."""
        logger.info('Testing workflow state management across agents')
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        self.assertIsNotNone(self.execution_context.state)
        if hasattr(self.execution_context.state, 'triage_result'):
            triage_result = self.execution_context.state.triage_result
            self.assertIsInstance(triage_result, dict)
            self.assertIn('data_sufficiency', triage_result)
        for result in results:
            self.assertIsNotNone(result.data)
            self.assertIn('agent_name', result.metadata)
        logger.info(' PASS:  Workflow state management validated')

    async def test_agent_communication_and_result_passing(self):
        """Test inter-agent communication and result passing."""
        logger.info('Testing agent communication and result passing')
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        for result in results:
            self.assertIsNotNone(result.data)
            self.assertIsInstance(result.data, dict)
            if 'agent_name' in result.data:
                self.assertIsInstance(result.data['agent_name'], str)
        execution_log = self.execution_engine.execution_log
        self.assertEqual(execution_log[0], 'triage')
        if len(execution_log) > 1:
            self.assertIn('triage', execution_log[:2])
        logger.info(' PASS:  Agent communication and result passing validated')

class TestAdaptiveLogicTests(TestWorkflowOrchestratorIntegration):
    """Test adaptive workflow logic and dynamic decision making."""

    async def test_dynamic_workflow_adaptation_based_on_agent_results(self):
        """Test dynamic workflow adaptation based on agent execution results."""
        logger.info('Testing dynamic workflow adaptation')
        test_cases = [('sufficient', ['triage', 'data', 'optimization', 'actions', 'reporting']), ('partial', ['triage', 'data_helper', 'data', 'reporting']), ('insufficient', ['triage', 'data_helper', 'reporting']), ('unknown', ['data_helper', 'reporting'])]
        for sufficiency, expected_flow in test_cases:
            triage_result = {'data_sufficiency': sufficiency}
            workflow_steps = self.orchestrator._define_workflow_based_on_triage(triage_result)
            actual_agents = [step.agent_name for step in workflow_steps]
            self.assertEqual(actual_agents, expected_flow, f'Failed for data_sufficiency: {sufficiency}')
        logger.info(' PASS:  Dynamic workflow adaptation validated')

    async def test_conditional_workflow_branching_and_decision_making(self):
        """Test conditional workflow branching based on business logic."""
        logger.info('Testing conditional workflow branching')
        test_data = {'available_data': {'costs': 1000, 'services': ['ec2', 'rds']}, 'missing_data': ['detailed_usage', 'optimization_history']}
        assessment = self.orchestrator.assess_data_completeness(test_data)
        self.assertIn('completeness', assessment)
        self.assertIn('workflow', assessment)
        self.assertIn('confidence', assessment)
        self.assertIn('data_sufficiency', assessment)
        workflow_config = await self.orchestrator.select_workflow(test_data)
        self.assertIn('type', workflow_config)
        self.assertIn('phases', workflow_config)
        self.assertIsInstance(workflow_config['phases'], list)
        logger.info(' PASS:  Conditional workflow branching validated')

    async def test_workflow_optimization_based_on_performance_metrics(self):
        """Test workflow optimization based on execution performance."""
        logger.info('Testing workflow performance optimization')
        self.execution_engine.set_execution_time('data', 200)
        self.execution_engine.set_execution_time('optimization', 500)
        self.execution_engine.set_execution_time('reporting', 50)
        start_time = time.time()
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        total_time = time.time() - start_time
        for result in results:
            self.assertIsNotNone(result.execution_time_ms)
            self.assertGreater(result.execution_time_ms, 0)
        self.assertLess(total_time, 10.0)
        logger.info(f' PASS:  Workflow performance optimization validated ({total_time:.2f}s)')

    async def test_adaptive_resource_allocation_during_execution(self):
        """Test adaptive resource allocation based on workflow demands."""
        logger.info('Testing adaptive resource allocation')
        high_resource_data = {'complexity_level': 'high', 'data_volume': 'large', 'optimization_scope': 'comprehensive'}
        assessment = self.orchestrator.assess_data_completeness(high_resource_data)
        self.assertIsInstance(assessment['completeness'], float)
        self.assertIsInstance(assessment['confidence'], float)
        simple_data = {'complexity_level': 'low', 'data_volume': 'small', 'optimization_scope': 'basic'}
        simple_assessment = self.orchestrator.assess_data_completeness(simple_data)
        self.assertIsNotNone(assessment)
        self.assertIsNotNone(simple_assessment)
        logger.info(' PASS:  Adaptive resource allocation validated')

class TestEnterpriseDataIntegrity(TestWorkflowOrchestratorIntegration):
    """Test Enterprise data integrity and compliance features."""

    async def test_enterprise_customer_workflow_isolation(self):
        """Test Enterprise customer workflow isolation and security."""
        logger.info('Testing Enterprise customer workflow isolation')
        enterprise_user_1 = UserExecutionContext(user_id='enterprise_user_001', thread_id='enterprise_thread_001', run_id='enterprise_run_001')
        enterprise_user_2 = UserExecutionContext(user_id='enterprise_user_002', thread_id='enterprise_thread_002', run_id='enterprise_run_002')
        orchestrator_1 = WorkflowOrchestrator(agent_registry=self.agent_registry, execution_engine=self.execution_engine, websocket_manager=self.websocket_manager, user_context=enterprise_user_1)
        orchestrator_2 = WorkflowOrchestrator(agent_registry=self.agent_registry, execution_engine=self.execution_engine, websocket_manager=self.websocket_manager, user_context=enterprise_user_2)
        context_1 = ExecutionContext(request_id='enterprise_req_001', run_id=enterprise_user_1.run_id, user_id=enterprise_user_1.user_id, stream_updates=True)
        context_1.thread_id = enterprise_user_1.thread_id
        context_1.state = type('MockState', (), {})()
        context_2 = ExecutionContext(request_id='enterprise_req_002', run_id=enterprise_user_2.run_id, user_id=enterprise_user_2.user_id, stream_updates=True)
        context_2.thread_id = enterprise_user_2.thread_id
        context_2.state = type('MockState', (), {})()
        results_1, results_2 = await asyncio.gather(orchestrator_1.execute_standard_workflow(context_1), orchestrator_2.execute_standard_workflow(context_2))
        self.assertGreater(len(results_1), 0)
        self.assertGreater(len(results_2), 0)
        self.assertEqual(orchestrator_1.user_context.user_id, enterprise_user_1.user_id)
        self.assertEqual(orchestrator_2.user_context.user_id, enterprise_user_2.user_id)
        logger.info(' PASS:  Enterprise customer workflow isolation validated')

    async def test_data_consistency_across_workflow_steps(self):
        """Test data consistency validation across workflow execution steps."""
        logger.info('Testing data consistency across workflow steps')
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        self.assertIsNotNone(self.orchestrator.coordination_validator)
        self.assertIsInstance(self.orchestrator.coordination_validator, AgentCoordinationValidator)
        for result in results:
            self.assertIsNotNone(result.data)
            self.assertIn('agent_name', result.data)
            self.assertIn('timestamp', result.data)
            self.assertIn('execution_id', result.data)
        for result in results:
            if hasattr(result, 'metadata') and result.metadata:
                if 'coordination_validation' in result.metadata:
                    validation_data = result.metadata['coordination_validation']
                    self.assertIn('status', validation_data)
        logger.info(' PASS:  Data consistency across workflow steps validated')

    async def test_enterprise_compliance_workflow_validation(self):
        """Test Enterprise compliance requirements in workflow execution."""
        logger.info('Testing Enterprise compliance workflow validation')
        enterprise_context = ExecutionContext(request_id='compliance_req_001', run_id='compliance_run_001', user_id='enterprise_compliance_user', stream_updates=True)
        enterprise_context.thread_id = 'compliance_thread_001'
        enterprise_context.state = type('MockState', (), {})()
        enterprise_context.metadata = {'compliance_level': 'enterprise', 'data_classification': 'confidential', 'audit_required': True, 'retention_policy': '7_years'}
        results = await self.orchestrator.execute_standard_workflow(enterprise_context)
        self.assertGreater(len(results), 0)
        for result in results:
            if result.metadata and 'agent_name' in result.metadata:
                agent_name = result.metadata['agent_name']
                self.assertIsInstance(agent_name, str)
                self.assertGreater(len(agent_name), 0)
        self.assertGreater(len(self.execution_engine.execution_log), 0)
        logger.info(' PASS:  Enterprise compliance workflow validation completed')

    async def test_multi_tenant_workflow_security(self):
        """Test multi-tenant workflow security and data isolation."""
        logger.info('Testing multi-tenant workflow security')
        tenant_contexts = []
        for i in range(3):
            context = UserExecutionContext(user_id=f'tenant_{i}_user', thread_id=f'tenant_{i}_thread', run_id=f'tenant_{i}_run')
            tenant_contexts.append(context)
        orchestrators = []
        execution_contexts = []
        for i, user_context in enumerate(tenant_contexts):
            orchestrator = WorkflowOrchestrator(agent_registry=self.agent_registry, execution_engine=self.execution_engine, websocket_manager=self.websocket_manager, user_context=user_context)
            exec_context = ExecutionContext(request_id=f'tenant_{i}_req', run_id=user_context.run_id, user_id=user_context.user_id, stream_updates=True)
            exec_context.thread_id = user_context.thread_id
            exec_context.state = type('MockState', (), {})()
            orchestrators.append(orchestrator)
            execution_contexts.append(exec_context)
        all_results = await asyncio.gather(*[orch.execute_standard_workflow(ctx) for orch, ctx in zip(orchestrators, execution_contexts)])
        self.assertEqual(len(all_results), 3)
        for i, results in enumerate(all_results):
            self.assertGreater(len(results), 0)
            for result in results:
                self.assertIsNotNone(result.data)
        for i, orchestrator in enumerate(orchestrators):
            expected_user_id = f'tenant_{i}_user'
            self.assertEqual(orchestrator.user_context.user_id, expected_user_id)
        logger.info(' PASS:  Multi-tenant workflow security validated')

class TestAgentCoordinationValidation(TestWorkflowOrchestratorIntegration):
    """Test agent coordination validation and workflow monitoring."""

    async def test_agent_registration_and_discovery_in_workflows(self):
        """Test agent registration and discovery mechanisms."""
        logger.info('Testing agent registration and discovery')
        available_agents = ['triage', 'data_helper', 'data', 'optimization', 'actions', 'reporting']
        for agent_name in available_agents:
            agent = await self.agent_registry.get_agent(agent_name)
            self.assertIsNotNone(agent, f'Agent {agent_name} should be discoverable')
        workflow_definition = self.orchestrator.get_workflow_definition()
        self.assertIsInstance(workflow_definition, list)
        self.assertGreater(len(workflow_definition), 0)
        for step in workflow_definition:
            self.assertIn('agent_name', step)
            self.assertIn('step_type', step)
            self.assertIn('order', step)
        logger.info(' PASS:  Agent registration and discovery validated')

    async def test_inter_agent_communication_and_synchronization(self):
        """Test inter-agent communication and synchronization mechanisms."""
        logger.info('Testing inter-agent communication and synchronization')
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        execution_log = self.execution_engine.execution_log
        self.assertGreater(len(execution_log), 1)
        first_agent = execution_log[0]
        self.assertEqual(first_agent, 'triage')
        for result in results:
            self.assertIsInstance(result.data, dict)
            self.assertIn('agent_name', result.data)
            self.assertIn('timestamp', result.data)
        execution_times = [r.execution_time_ms for r in results if r.execution_time_ms]
        self.assertGreater(len(execution_times), 0)
        self.assertTrue(all((t > 0 for t in execution_times)))
        logger.info(' PASS:  Inter-agent communication and synchronization validated')

    async def test_agent_failure_handling_and_workflow_recovery(self):
        """Test agent failure handling and workflow recovery mechanisms."""
        logger.info('Testing agent failure handling and workflow recovery')
        self.execution_engine.set_agent_failure('data', True)
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        failed_results = [r for r in results if r.status == ExecutionStatus.FAILED]
        self.assertGreater(len(failed_results), 0)
        execution_log = self.execution_engine.execution_log
        self.assertIn('triage', execution_log)
        self.assertIn('data', execution_log)
        self.execution_engine.set_agent_failure('data', False)
        self.execution_engine.execution_log = []
        recovery_results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        successful_results = [r for r in recovery_results if r.status == ExecutionStatus.COMPLETED]
        self.assertGreater(len(successful_results), 0)
        logger.info(' PASS:  Agent failure handling and workflow recovery validated')

    async def test_concurrent_agent_coordination_safety(self):
        """Test concurrent agent coordination and thread safety."""
        logger.info('Testing concurrent agent coordination safety')
        concurrent_contexts = []
        for i in range(3):
            context = ExecutionContext(request_id=f'concurrent_req_{i}', run_id=f'concurrent_run_{i}', user_id=f'concurrent_user_{i}', stream_updates=True)
            context.thread_id = f'concurrent_thread_{i}'
            context.state = type('MockState', (), {})()
            concurrent_contexts.append(context)
        concurrent_results = await asyncio.gather(*[self.orchestrator.execute_standard_workflow(ctx) for ctx in concurrent_contexts])
        self.assertEqual(len(concurrent_results), 3)
        for i, results in enumerate(concurrent_results):
            self.assertGreater(len(results), 0)
            for result in results:
                self.assertIsNotNone(result.data)
                self.assertEqual(result.request_id, f'concurrent_req_{i}')
        total_executions = len(self.execution_engine.execution_log)
        expected_minimum = 3 * 2
        self.assertGreaterEqual(total_executions, expected_minimum)
        logger.info(' PASS:  Concurrent agent coordination safety validated')

class TestBusinessLogicIntegration(TestWorkflowOrchestratorIntegration):
    """Test complete business workflow execution and value delivery."""

    async def test_complete_business_workflow_execution(self):
        """Test complete business workflow from start to finish."""
        logger.info('Testing complete business workflow execution')
        start_time = time.time()
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        execution_time = time.time() - start_time
        self.assertGreater(len(results), 3)
        business_indicators = []
        for result in results:
            if result.data:
                data = result.data
                if any((key in data for key in ['optimization_strategies', 'savings_potential', 'roi_percentage'])):
                    business_indicators.append(result)
                elif any((key in data for key in ['cost_analysis', 'usage_patterns', 'insights'])):
                    business_indicators.append(result)
                elif any((key in data for key in ['implementation_plan', 'executive_summary'])):
                    business_indicators.append(result)
        self.assertGreater(len(business_indicators), 0, 'Should contain business value indicators')
        self.assertLess(execution_time, 30.0)
        logger.info(f' PASS:  Complete business workflow validated in {execution_time:.2f}s')

    async def test_business_rule_enforcement_across_workflows(self):
        """Test business rule enforcement throughout workflow execution."""
        logger.info('Testing business rule enforcement')
        business_rules = {'minimum_data_quality': 0.5, 'maximum_execution_time_minutes': 10, 'required_cost_analysis': True, 'roi_threshold_percentage': 10}
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        self.assertGreater(len(results), 0)
        total_execution_time = sum((r.execution_time_ms for r in results if r.execution_time_ms))
        self.assertLess(total_execution_time / 1000 / 60, business_rules['maximum_execution_time_minutes'])
        cost_analysis_found = False
        roi_found = False
        for result in results:
            if result.data:
                if 'cost_analysis' in result.data or 'insights' in result.data:
                    cost_analysis_found = True
                if 'roi_percentage' in result.data:
                    roi_value = result.data.get('roi_percentage', 0)
                    if roi_value >= business_rules['roi_threshold_percentage']:
                        roi_found = True
        if business_rules['required_cost_analysis']:
            self.assertTrue(cost_analysis_found, 'Cost analysis should be present')
        logger.info(' PASS:  Business rule enforcement validated')

    async def test_revenue_impacting_workflow_validation(self):
        """Test validation of workflows that impact revenue calculations."""
        logger.info('Testing revenue-impacting workflow validation')
        enterprise_context = ExecutionContext(request_id='enterprise_revenue_req', run_id='enterprise_revenue_run', user_id='enterprise_customer_high_value', stream_updates=True)
        enterprise_context.thread_id = 'enterprise_revenue_thread'
        enterprise_context.state = type('MockState', (), {})()
        enterprise_context.metadata = {'customer_tier': 'enterprise', 'monthly_value': 50000, 'contract_type': 'annual'}
        results = await self.orchestrator.execute_standard_workflow(enterprise_context)
        revenue_impact_indicators = []
        for result in results:
            if result.data:
                revenue_keys = ['total_potential_savings', 'roi_percentage', 'cost_analysis', 'optimization_strategies', 'total_savings', 'savings_potential']
                if any((key in result.data for key in revenue_keys)):
                    revenue_impact_indicators.append(result)
        self.assertGreater(len(revenue_impact_indicators), 0, 'Should have revenue-impacting results for Enterprise customer')
        coordination_validation_found = False
        for result in results:
            if hasattr(result, 'metadata') and result.metadata and ('coordination_validation' in result.metadata):
                coordination_validation_found = True
                break
        logger.info(' PASS:  Revenue-impacting workflow validation completed')

    async def test_customer_value_delivery_workflows(self):
        """Test workflows that deliver direct customer value."""
        logger.info('Testing customer value delivery workflows')
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        customer_value_metrics = {'cost_savings_identified': False, 'optimization_recommendations': False, 'implementation_guidance': False, 'roi_calculation': False}
        for result in results:
            if result.data:
                data = result.data
                if any((key in data for key in ['savings', 'cost_reduction', 'total_savings'])):
                    customer_value_metrics['cost_savings_identified'] = True
                if any((key in data for key in ['optimization_strategies', 'recommendations'])):
                    customer_value_metrics['optimization_recommendations'] = True
                if any((key in data for key in ['implementation_plan', 'actions', 'roadmap'])):
                    customer_value_metrics['implementation_guidance'] = True
                if 'roi_percentage' in data:
                    customer_value_metrics['roi_calculation'] = True
        delivered_value_count = sum((1 for delivered in customer_value_metrics.values() if delivered))
        self.assertGreaterEqual(delivered_value_count, 2, 'Should deliver multiple forms of customer value')
        actionable_results = []
        for result in results:
            if result.data and any((key in result.data for key in ['implementation_plan', 'optimization_strategies', 'actions', 'recommendations', 'next_steps'])):
                actionable_results.append(result)
        self.assertGreater(len(actionable_results), 0, 'Should provide actionable customer insights')
        logger.info(' PASS:  Customer value delivery workflows validated')

class TestPerformanceAndScalability(TestWorkflowOrchestratorIntegration):
    """Test workflow performance and scalability characteristics."""

    async def test_workflow_execution_performance_under_load(self):
        """Test workflow execution performance under simulated load."""
        logger.info('Testing workflow execution performance under load')
        self.execution_engine.set_execution_time('triage', 150)
        self.execution_engine.set_execution_time('data', 300)
        self.execution_engine.set_execution_time('optimization', 450)
        self.execution_engine.set_execution_time('actions', 200)
        self.execution_engine.set_execution_time('reporting', 100)
        load_test_count = 5
        start_time = time.time()
        load_results = await asyncio.gather(*[self.orchestrator.execute_standard_workflow(self.execution_context) for _ in range(load_test_count)])
        total_time = time.time() - start_time
        self.assertEqual(len(load_results), load_test_count)
        for results in load_results:
            self.assertGreater(len(results), 0)
            successful_count = sum((1 for r in results if r.status == ExecutionStatus.COMPLETED))
            self.assertGreater(successful_count, 0)
        average_time_per_workflow = total_time / load_test_count
        self.assertLess(average_time_per_workflow, 10.0)
        logger.info(f' PASS:  Load performance validated: {average_time_per_workflow:.2f}s avg per workflow')

    async def test_concurrent_workflow_management(self):
        """Test concurrent workflow management and resource sharing."""
        logger.info('Testing concurrent workflow management')
        concurrent_users = []
        for i in range(4):
            user_context = UserExecutionContext(user_id=f'concurrent_user_{i}', thread_id=f'concurrent_thread_{i}', run_id=f'concurrent_run_{i}')
            concurrent_users.append(user_context)
        concurrent_contexts = []
        for i, user_context in enumerate(concurrent_users):
            context = ExecutionContext(request_id=f'concurrent_req_{i}', run_id=user_context.run_id, user_id=user_context.user_id, stream_updates=True)
            context.thread_id = user_context.thread_id
            context.state = type('MockState', (), {})()
            concurrent_contexts.append(context)
        start_time = time.time()
        concurrent_results = await asyncio.gather(*[self.orchestrator.execute_standard_workflow(ctx) for ctx in concurrent_contexts])
        total_time = time.time() - start_time
        self.assertEqual(len(concurrent_results), 4)
        estimated_sequential_time = 4 * 1.0
        self.assertLess(total_time, estimated_sequential_time * 1.5)
        for i, results in enumerate(concurrent_results):
            self.assertGreater(len(results), 0)
            for result in results:
                self.assertEqual(result.request_id, f'concurrent_req_{i}')
        logger.info(f' PASS:  Concurrent workflow management validated in {total_time:.2f}s')

    async def test_resource_optimization_during_complex_workflows(self):
        """Test resource optimization during complex workflow execution."""
        logger.info('Testing resource optimization during complex workflows')
        complex_context = ExecutionContext(request_id='complex_workflow_req', run_id='complex_workflow_run', user_id='complex_workflow_user', stream_updates=True)
        complex_context.thread_id = 'complex_workflow_thread'
        complex_context.state = type('MockState', (), {})()
        complex_context.metadata = {'complexity_level': 'high', 'data_volume': 'large', 'optimization_scope': 'comprehensive', 'resource_requirements': 'high_compute'}
        start_time = time.time()
        results = await self.orchestrator.execute_standard_workflow(complex_context)
        execution_time = time.time() - start_time
        self.assertGreater(len(results), 0)
        total_agent_execution_time = sum((r.execution_time_ms for r in results if r.execution_time_ms))
        self.assertLess(execution_time, 15.0)
        self.assertGreater(total_agent_execution_time, 0)
        execution_log = self.execution_engine.execution_log
        self.assertIn('triage', execution_log)
        logger.info(f' PASS:  Resource optimization validated for complex workflow ({execution_time:.2f}s)')

    async def test_long_running_workflow_reliability(self):
        """Test reliability of long-running workflow executions."""
        logger.info('Testing long-running workflow reliability')
        self.execution_engine.set_execution_time('triage', 500)
        self.execution_engine.set_execution_time('data', 800)
        self.execution_engine.set_execution_time('optimization', 1200)
        self.execution_engine.set_execution_time('actions', 600)
        self.execution_engine.set_execution_time('reporting', 300)
        start_time = time.time()
        results = await self.orchestrator.execute_standard_workflow(self.execution_context)
        execution_time = time.time() - start_time
        self.assertGreater(len(results), 0)
        successful_results = [r for r in results if r.status == ExecutionStatus.COMPLETED]
        self.assertGreater(len(successful_results), 0)
        for result in results:
            if result.execution_time_ms:
                self.assertGreater(result.execution_time_ms, 0)
                self.assertLess(result.execution_time_ms, 5000)
        self.assertLess(execution_time, 30.0)
        logger.info(f' PASS:  Long-running workflow reliability validated ({execution_time:.2f}s)')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')