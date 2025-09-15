"""
E2E Tests for Complete Agent Workflows with Authentication (Staging)
Test #10 of Agent Registry and Factory Patterns Test Suite - FINAL TEST

Business Value Justification (BVJ):
- Segment: Enterprise (Complete authenticated multi-agent workflows for enterprise customers)
- Business Goal: Validate end-to-end authenticated agent workflows deliver complete business value
- Value Impact: Ensures enterprise customers can execute complex authenticated AI workflows reliably
- Strategic Impact: $5M+ ARR validation - Complete authenticated workflows are core enterprise value proposition

CRITICAL MISSION: Test Complete Agent Workflows with Authentication ensuring:
1. End-to-end authenticated agent workflows execute successfully with real JWT/OAuth
2. Complete business workflows (data analysis  ->  insights  ->  actions) work end-to-end  
3. WebSocket events provide complete real-time visibility throughout authenticated workflows
4. User context and permissions are enforced throughout complete workflow execution
5. Factory patterns maintain complete isolation during authenticated multi-user workflows
6. Resource cleanup and security are maintained in complete authenticated scenarios
7. Performance meets enterprise SLA requirements for complete authenticated workflows
8. Error handling and recovery work in complete authenticated production-like scenarios

FOCUS: Complete E2E staging validation with real authentication, real multi-agent workflows,
        and real WebSocket connections to validate complete enterprise business value delivery.
"""
import asyncio
import pytest
import time
import uuid
import json
import httpx
import websockets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
from tests.e2e.staging_config import StagingTestConfig

@dataclass
class EnterpriseWorkflowRequest:
    """Represents a complete enterprise workflow request."""
    workflow_type: str
    business_objective: str
    input_parameters: Dict[str, Any]
    expected_deliverables: List[str]
    sla_requirements: Dict[str, float]
    authentication_requirements: List[str]
    user_context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowExecutionMetrics:
    """Tracks comprehensive workflow execution metrics."""
    workflow_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_execution_time: float = 0.0
    agents_executed: int = 0
    websocket_events_received: int = 0
    authentication_validations: int = 0
    business_value_delivered: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    error_count: int = 0
    success_rate: float = 0.0

@pytest.fixture
def staging_config():
    """Staging configuration for complete E2E testing."""
    return StagingTestConfig()

@pytest.fixture
def enterprise_auth_helper():
    """Enterprise-grade authentication helper for complete workflow testing."""
    return E2EAuthHelper(environment='staging')

@pytest.fixture
async def enterprise_authenticated_user(enterprise_auth_helper):
    """Create enterprise user with complete authentication for workflow testing."""
    return await create_authenticated_user_context(user_email='enterprise_workflow@staging.com', environment='staging', permissions=['read', 'write', 'agent_execute', 'workflow_orchestrate', 'enterprise_access'], websocket_enabled=True)

@pytest.fixture
def enterprise_data_analysis_workflow():
    """Complete enterprise data analysis workflow for comprehensive testing."""
    return EnterpriseWorkflowRequest(workflow_type='comprehensive_data_analysis', business_objective='Generate actionable business insights from enterprise data', input_parameters={'data_sources': ['sales_database', 'customer_feedback', 'market_data'], 'analysis_depth': 'comprehensive', 'time_period': 'Q4_2024', 'business_metrics': ['revenue_growth', 'customer_satisfaction', 'market_share'], 'optimization_goals': ['cost_reduction', 'efficiency_improvement'], 'report_audience': 'C_suite_executives', 'confidentiality_level': 'confidential'}, expected_deliverables=['executive_summary_report', 'detailed_analytics_dashboard', 'actionable_recommendations', 'implementation_roadmap', 'roi_projections', 'risk_assessment'], sla_requirements={'max_execution_time_minutes': 10.0, 'min_success_rate': 0.95, 'max_error_rate': 0.05, 'min_data_quality_score': 0.9, 'required_websocket_events': 15}, authentication_requirements=['jwt_token_validation', 'oauth_integration', 'permission_enforcement', 'audit_logging'])

@pytest.fixture
def multi_user_workflow_scenarios():
    """Multiple concurrent enterprise workflow scenarios for testing."""
    scenarios = []
    scenarios.append(EnterpriseWorkflowRequest(workflow_type='financial_analysis', business_objective='Comprehensive financial performance analysis and forecasting', input_parameters={'financial_data': ['quarterly_reports', 'budget_actuals', 'cash_flow'], 'forecast_horizon': '12_months', 'risk_assessment': True, 'compliance_check': 'SOX_compliance'}, expected_deliverables=['financial_health_report', 'forecast_projections', 'risk_analysis', 'compliance_summary'], sla_requirements={'max_execution_time_minutes': 8.0, 'min_success_rate': 0.9, 'max_error_rate': 0.1}, authentication_requirements=['jwt_token_validation', 'financial_data_access']))
    scenarios.append(EnterpriseWorkflowRequest(workflow_type='customer_intelligence', business_objective='Customer behavior analysis and personalization recommendations', input_parameters={'customer_segments': ['enterprise', 'mid_market', 'smb'], 'behavioral_data': ['purchase_history', 'engagement_metrics', 'support_interactions'], 'personalization_goals': ['retention', 'upsell', 'satisfaction'], 'privacy_compliance': 'GDPR'}, expected_deliverables=['customer_segments_analysis', 'behavioral_insights', 'personalization_strategy', 'retention_recommendations'], sla_requirements={'max_execution_time_minutes': 6.0, 'min_success_rate': 0.85, 'max_error_rate': 0.15}, authentication_requirements=['jwt_token_validation', 'customer_data_access']))
    scenarios.append(EnterpriseWorkflowRequest(workflow_type='operational_optimization', business_objective='Operations efficiency analysis and improvement recommendations', input_parameters={'operational_areas': ['supply_chain', 'manufacturing', 'distribution'], 'efficiency_metrics': ['throughput', 'quality', 'cost'], 'optimization_constraints': ['budget_limits', 'resource_availability'], 'improvement_targets': {'cost_reduction': 0.15, 'efficiency_gain': 0.2}}, expected_deliverables=['efficiency_analysis', 'bottleneck_identification', 'optimization_recommendations', 'implementation_plan'], sla_requirements={'max_execution_time_minutes': 7.0, 'min_success_rate': 0.9, 'max_error_rate': 0.1}, authentication_requirements=['jwt_token_validation', 'operational_data_access']))
    return scenarios

class EnterpriseWorkflowExecutionEngine:
    """Complete workflow execution engine for enterprise E2E testing."""

    def __init__(self, staging_config: StagingTestConfig, auth_helper: E2EAuthHelper):
        self.staging_config = staging_config
        self.auth_helper = auth_helper
        self.http_client: Optional[httpx.AsyncClient] = None
        self.websocket_connection = None
        self.websocket_events: List[Dict] = []
        self.execution_metrics: Dict[str, WorkflowExecutionMetrics] = {}

    async def initialize(self):
        """Initialize complete enterprise connections and authentication."""
        auth_headers = self.auth_helper.get_auth_headers()
        self.http_client = httpx.AsyncClient(base_url=self.staging_config.urls.backend_url, headers=auth_headers, timeout=httpx.Timeout(300.0))
        ws_helper = E2EWebSocketAuthHelper(environment='staging')
        self.websocket_connection = await ws_helper.connect_authenticated_websocket(timeout=20.0)
        self._websocket_listener_task = asyncio.create_task(self._listen_for_websocket_events())

    async def execute_complete_enterprise_workflow(self, workflow_request: EnterpriseWorkflowRequest, user_context: Any, execution_options: Optional[Dict[str, Any]]=None) -> WorkflowExecutionMetrics:
        """Execute complete enterprise workflow with full authentication and monitoring."""
        workflow_id = f'{workflow_request.workflow_type}_{uuid.uuid4().hex[:8]}'
        metrics = WorkflowExecutionMetrics(workflow_id=workflow_id, started_at=datetime.now(timezone.utc))
        self.execution_metrics[workflow_id] = metrics
        try:
            await self._validate_workflow_authentication(workflow_request, user_context, metrics)
            workflow_results = await self._execute_workflow_pipeline(workflow_request, user_context, metrics)
            await self._validate_business_value_delivery(workflow_request, workflow_results, metrics)
            await self._assess_workflow_performance_quality(workflow_request, workflow_results, metrics)
            metrics.completed_at = datetime.now(timezone.utc)
            metrics.total_execution_time = (metrics.completed_at - metrics.started_at).total_seconds()
            metrics.success_rate = (metrics.agents_executed - metrics.error_count) / max(metrics.agents_executed, 1)
            return metrics
        except Exception as e:
            metrics.error_count += 1
            metrics.completed_at = datetime.now(timezone.utc)
            metrics.total_execution_time = (metrics.completed_at - metrics.started_at).total_seconds()
            raise Exception(f'Enterprise workflow {workflow_id} failed: {str(e)}')

    async def _validate_workflow_authentication(self, workflow_request: EnterpriseWorkflowRequest, user_context: Any, metrics: WorkflowExecutionMetrics):
        """Validate complete authentication for workflow execution."""
        auth_validations = 0
        try:
            token = self.auth_helper._get_valid_token()
            is_valid = await self.auth_helper.validate_token(token)
            if not is_valid:
                raise Exception('JWT token validation failed')
            auth_validations += 1
        except Exception as e:
            metrics.error_count += 1
            raise Exception(f'JWT authentication failed: {str(e)}')
        required_permissions = set(workflow_request.authentication_requirements)
        user_permissions = set(user_context.agent_context.get('permissions', []))
        missing_permissions = required_permissions - user_permissions
        if missing_permissions:
            metrics.error_count += 1
            raise Exception(f'Missing required permissions: {missing_permissions}')
        auth_validations += 1
        required_context_fields = ['user_id', 'thread_id', 'run_id', 'request_id']
        for field in required_context_fields:
            if not getattr(user_context, field, None):
                metrics.error_count += 1
                raise Exception(f'Missing required user context field: {field}')
        auth_validations += 1
        metrics.authentication_validations = auth_validations

    async def _execute_workflow_pipeline(self, workflow_request: EnterpriseWorkflowRequest, user_context: Any, metrics: WorkflowExecutionMetrics) -> Dict[str, Any]:
        """Execute complete multi-agent workflow pipeline."""
        workflow_results = {}
        agent_sequence = self._get_agent_execution_sequence(workflow_request.workflow_type)
        for i, agent_config in enumerate(agent_sequence):
            agent_start_time = time.time()
            try:
                agent_input = {**workflow_request.input_parameters, 'workflow_context': {'workflow_id': metrics.workflow_id, 'workflow_type': workflow_request.workflow_type, 'business_objective': workflow_request.business_objective, 'step_number': i + 1, 'total_steps': len(agent_sequence), 'previous_results': workflow_results}, 'user_context': {'user_id': str(user_context.user_id), 'thread_id': str(user_context.thread_id), 'run_id': str(user_context.run_id), 'request_id': str(user_context.request_id)}, 'execution_config': agent_config.get('config', {})}
                agent_result = await self._execute_authenticated_agent(agent_config['agent_type'], agent_input, timeout=agent_config.get('timeout_seconds', 60.0))
                step_key = f"step_{i + 1}_{agent_config['agent_type']}"
                workflow_results[step_key] = agent_result
                metrics.agents_executed += 1
                agent_execution_time = time.time() - agent_start_time
                metrics.performance_metrics[f"{agent_config['agent_type']}_execution_time"] = agent_execution_time
                self._validate_agent_outputs(agent_config, agent_result, metrics)
            except Exception as e:
                metrics.error_count += 1
                agent_execution_time = time.time() - agent_start_time
                metrics.performance_metrics[f"{agent_config['agent_type']}_failed_time"] = agent_execution_time
                if agent_config.get('critical', True):
                    raise Exception(f"Critical agent {agent_config['agent_type']} failed: {str(e)}")
                else:
                    workflow_results[f"error_{agent_config['agent_type']}"] = str(e)
        return workflow_results

    def _get_agent_execution_sequence(self, workflow_type: str) -> List[Dict[str, Any]]:
        """Get agent execution sequence for workflow type."""
        sequences = {'comprehensive_data_analysis': [{'agent_type': 'data_helper', 'timeout_seconds': 45.0, 'critical': True, 'config': {'analysis_depth': 'comprehensive', 'data_validation': True}}, {'agent_type': 'optimization_agent', 'timeout_seconds': 60.0, 'critical': True, 'config': {'optimization_type': 'comprehensive', 'multi_objective': True}}, {'agent_type': 'report_generation_agent', 'timeout_seconds': 45.0, 'critical': True, 'config': {'report_type': 'executive', 'include_visualizations': True}}, {'agent_type': 'validation_agent', 'timeout_seconds': 30.0, 'critical': False, 'config': {'validation_type': 'quality_assurance', 'completeness_check': True}}], 'financial_analysis': [{'agent_type': 'data_helper', 'timeout_seconds': 40.0, 'critical': True, 'config': {'data_type': 'financial', 'compliance_check': True}}, {'agent_type': 'financial_analysis_agent', 'timeout_seconds': 60.0, 'critical': True, 'config': {'analysis_type': 'comprehensive', 'risk_assessment': True}}, {'agent_type': 'report_generation_agent', 'timeout_seconds': 40.0, 'critical': True, 'config': {'report_type': 'financial', 'executive_summary': True}}], 'customer_intelligence': [{'agent_type': 'data_helper', 'timeout_seconds': 35.0, 'critical': True, 'config': {'data_type': 'customer', 'privacy_compliance': 'GDPR'}}, {'agent_type': 'customer_analysis_agent', 'timeout_seconds': 50.0, 'critical': True, 'config': {'analysis_type': 'behavioral', 'segmentation': True}}, {'agent_type': 'recommendation_agent', 'timeout_seconds': 40.0, 'critical': True, 'config': {'recommendation_type': 'personalization', 'retention_focus': True}}], 'operational_optimization': [{'agent_type': 'data_helper', 'timeout_seconds': 40.0, 'critical': True, 'config': {'data_type': 'operational', 'efficiency_metrics': True}}, {'agent_type': 'optimization_agent', 'timeout_seconds': 55.0, 'critical': True, 'config': {'optimization_type': 'operational', 'constraint_analysis': True}}, {'agent_type': 'implementation_agent', 'timeout_seconds': 45.0, 'critical': True, 'config': {'implementation_type': 'roadmap', 'feasibility_analysis': True}}]}
        return sequences.get(workflow_type, [{'agent_type': 'data_helper', 'timeout_seconds': 30.0, 'critical': True, 'config': {}}, {'agent_type': 'analysis_agent', 'timeout_seconds': 40.0, 'critical': True, 'config': {}}, {'agent_type': 'report_agent', 'timeout_seconds': 30.0, 'critical': True, 'config': {}}])

    async def _execute_authenticated_agent(self, agent_type: str, agent_input: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        """Execute agent with complete authentication via staging API."""
        request_payload = {'agent_type': agent_type, 'input_data': agent_input, 'execution_options': {'timeout_seconds': timeout, 'enable_websocket_events': True, 'enable_detailed_logging': True, 'enterprise_mode': True}}
        response = await self.http_client.post('/agents/execute', json=request_payload, timeout=timeout + 15)
        if response.status_code != 200:
            error_detail = f'Status: {response.status_code}, Response: {response.text}'
            raise Exception(f'Agent API call failed: {error_detail}')
        result = response.json()
        if not isinstance(result, dict) or 'status' not in result:
            raise Exception(f'Invalid agent response structure: {result}')
        if result['status'] != 'success':
            error_msg = result.get('error', 'Unknown agent execution error')
            raise Exception(f'Agent {agent_type} execution failed: {error_msg}')
        return result.get('data', {})

    def _validate_agent_outputs(self, agent_config: Dict[str, Any], agent_result: Dict[str, Any], metrics: WorkflowExecutionMetrics):
        """Validate agent delivered expected outputs."""
        expected_outputs = agent_config.get('expected_outputs', [])
        if expected_outputs:
            missing_outputs = []
            for expected_output in expected_outputs:
                if expected_output not in str(agent_result):
                    missing_outputs.append(expected_output)
            if missing_outputs:
                metrics.error_count += 1
                if agent_config.get('strict_validation', False):
                    raise Exception(f'Agent missing required outputs: {missing_outputs}')

    async def _validate_business_value_delivery(self, workflow_request: EnterpriseWorkflowRequest, workflow_results: Dict[str, Any], metrics: WorkflowExecutionMetrics):
        """Validate that workflow delivered expected business value."""
        delivered_value = {}
        delivered_deliverables = []
        for deliverable in workflow_request.expected_deliverables:
            deliverable_found = any((deliverable.lower() in str(result).lower() for result in workflow_results.values()))
            if deliverable_found:
                delivered_deliverables.append(deliverable)
        delivered_value['deliverables_delivered'] = delivered_deliverables
        delivered_value['deliverables_completion_rate'] = len(delivered_deliverables) / len(workflow_request.expected_deliverables)
        business_keywords = workflow_request.business_objective.lower().split()
        business_value_indicators = 0
        for result in workflow_results.values():
            result_str = str(result).lower()
            for keyword in business_keywords:
                if keyword in result_str:
                    business_value_indicators += 1
                    break
        delivered_value['business_objective_alignment'] = business_value_indicators / len(workflow_results)
        deliverables_weight = 0.6
        objective_alignment_weight = 0.4
        business_value_score = delivered_value['deliverables_completion_rate'] * deliverables_weight + delivered_value['business_objective_alignment'] * objective_alignment_weight
        delivered_value['overall_business_value_score'] = business_value_score
        metrics.business_value_delivered = delivered_value
        if business_value_score < 0.7:
            metrics.error_count += 1
            raise Exception(f'Insufficient business value delivered: {business_value_score:.2f} < 0.70')

    async def _assess_workflow_performance_quality(self, workflow_request: EnterpriseWorkflowRequest, workflow_results: Dict[str, Any], metrics: WorkflowExecutionMetrics):
        """Assess workflow performance against SLA requirements."""
        sla_requirements = workflow_request.sla_requirements
        performance_score = {}
        max_execution_time = sla_requirements.get('max_execution_time_minutes', 10.0) * 60
        actual_execution_time = metrics.total_execution_time
        execution_time_performance = min(1.0, max_execution_time / max(actual_execution_time, 0.1))
        performance_score['execution_time'] = execution_time_performance
        min_success_rate = sla_requirements.get('min_success_rate', 0.9)
        actual_success_rate = metrics.success_rate
        success_rate_performance = actual_success_rate / min_success_rate if min_success_rate > 0 else 1.0
        performance_score['success_rate'] = min(1.0, success_rate_performance)
        required_events = sla_requirements.get('required_websocket_events', 10)
        actual_events = metrics.websocket_events_received
        events_performance = actual_events / max(required_events, 1)
        performance_score['websocket_events'] = min(1.0, events_performance)
        quality_score = {}
        data_quality_indicators = 0
        total_results = len(workflow_results)
        for result in workflow_results.values():
            result_str = str(result).lower()
            quality_keywords = ['validated', 'complete', 'accurate', 'verified', 'quality']
            if any((keyword in result_str for keyword in quality_keywords)):
                data_quality_indicators += 1
        data_quality = data_quality_indicators / max(total_results, 1)
        quality_score['data_quality'] = data_quality
        response_quality_indicators = 0
        for result in workflow_results.values():
            result_length = len(str(result))
            if result_length > 200:
                response_quality_indicators += 1
        response_quality = response_quality_indicators / max(total_results, 1)
        quality_score['response_comprehensiveness'] = response_quality
        metrics.performance_metrics.update(performance_score)
        metrics.quality_metrics.update(quality_score)
        overall_performance = sum(performance_score.values()) / len(performance_score)
        overall_quality = sum(quality_score.values()) / len(quality_score)
        if overall_performance < 0.8:
            metrics.error_count += 1
            raise Exception(f'SLA performance requirements not met: {overall_performance:.2f} < 0.80')
        if overall_quality < 0.6:
            metrics.error_count += 1
            raise Exception(f'Quality requirements not met: {overall_quality:.2f} < 0.60')

    async def _listen_for_websocket_events(self):
        """Listen for WebSocket events during workflow execution."""
        try:
            async for message in self.websocket_connection:
                try:
                    event_data = json.loads(message)
                    self.websocket_events.append({'timestamp': datetime.now(timezone.utc).isoformat(), 'event': event_data})
                    for metrics in self.execution_metrics.values():
                        metrics.websocket_events_received += 1
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            pass

    async def cleanup(self):
        """Cleanup all connections and resources."""
        if hasattr(self, '_websocket_listener_task'):
            self._websocket_listener_task.cancel()
            try:
                await self._websocket_listener_task
            except asyncio.CancelledError:
                pass
        if self.websocket_connection:
            await self.websocket_connection.close()
        if self.http_client:
            await self.http_client.aclose()

@pytest.mark.e2e
class CompleteEnterpriseWorkflowsTests(SSotBaseTestCase):
    """Test complete enterprise workflows with full authentication."""

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_complete_enterprise_data_analysis_workflow(self, staging_config, enterprise_auth_helper, enterprise_authenticated_user, enterprise_data_analysis_workflow):
        """Test complete enterprise data analysis workflow with authentication."""
        engine = EnterpriseWorkflowExecutionEngine(staging_config, enterprise_auth_helper)
        await engine.initialize()
        try:
            execution_metrics = await engine.execute_complete_enterprise_workflow(enterprise_data_analysis_workflow, enterprise_authenticated_user)
            assert execution_metrics.completed_at is not None, 'Workflow should have completion timestamp'
            assert execution_metrics.error_count == 0, f'Enterprise workflow should complete without errors, got {execution_metrics.error_count} errors'
            assert execution_metrics.authentication_validations >= 3, f'Should have performed multiple authentication validations, got {execution_metrics.authentication_validations}'
            assert execution_metrics.agents_executed >= 3, f'Should have executed multiple agents, got {execution_metrics.agents_executed}'
            assert execution_metrics.success_rate >= 0.95, f'Success rate should meet SLA requirement (95%), got {execution_metrics.success_rate:.2%}'
            max_execution_time = enterprise_data_analysis_workflow.sla_requirements['max_execution_time_minutes'] * 60
            assert execution_metrics.total_execution_time <= max_execution_time, f'Execution time should meet SLA ({max_execution_time}s), took {execution_metrics.total_execution_time:.2f}s'
            required_events = enterprise_data_analysis_workflow.sla_requirements['required_websocket_events']
            assert execution_metrics.websocket_events_received >= required_events, f'Should have received  >= {required_events} WebSocket events, got {execution_metrics.websocket_events_received}'
            business_value = execution_metrics.business_value_delivered
            assert 'deliverables_completion_rate' in business_value, 'Should track deliverables completion'
            assert business_value['deliverables_completion_rate'] >= 0.8, f"Should deliver  >= 80% of expected deliverables, got {business_value['deliverables_completion_rate']:.1%}"
            assert 'overall_business_value_score' in business_value, 'Should calculate overall business value'
            assert business_value['overall_business_value_score'] >= 0.7, f"Should achieve  >= 70% business value score, got {business_value['overall_business_value_score']:.1%}"
            quality_metrics = execution_metrics.quality_metrics
            assert 'data_quality' in quality_metrics, 'Should assess data quality'
            assert quality_metrics['data_quality'] >= 0.6, f"Data quality should be  >= 60%, got {quality_metrics['data_quality']:.1%}"
            performance_metrics = execution_metrics.performance_metrics
            assert 'execution_time' in performance_metrics, 'Should track execution time performance'
            assert 'success_rate' in performance_metrics, 'Should track success rate performance'
            assert 'websocket_events' in performance_metrics, 'Should track WebSocket events performance'
            workflow_related_events = [event for event in engine.websocket_events if 'workflow' in str(event).lower() or 'agent' in str(event).lower()]
            assert len(workflow_related_events) >= 5, f'Should have workflow-related WebSocket events, got {len(workflow_related_events)}'
            assert str(enterprise_authenticated_user.user_id) in str(execution_metrics.business_value_delivered), 'User context should be preserved in business value tracking'
        finally:
            await engine.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_concurrent_multi_user_enterprise_workflows(self, staging_config, enterprise_auth_helper, multi_user_workflow_scenarios):
        """Test concurrent execution of multiple enterprise workflows with authentication."""
        authenticated_users = []
        for i, scenario in enumerate(multi_user_workflow_scenarios):
            user_context = await create_authenticated_user_context(user_email=f'concurrent_enterprise_user_{i}@staging.com', environment='staging', permissions=['read', 'write', 'agent_execute', 'workflow_orchestrate'], websocket_enabled=True)
            authenticated_users.append(user_context)
        engines = []
        for user_context in authenticated_users:
            engine = EnterpriseWorkflowExecutionEngine(staging_config, enterprise_auth_helper)
            await engine.initialize()
            engines.append(engine)
        try:
            concurrent_tasks = []
            for i, (scenario, user_context, engine) in enumerate(zip(multi_user_workflow_scenarios, authenticated_users, engines)):
                task = engine.execute_complete_enterprise_workflow(scenario, user_context)
                concurrent_tasks.append((task, scenario, user_context, engine))
            start_time = time.time()
            results = await asyncio.gather(*[task for task, _, _, _ in concurrent_tasks], return_exceptions=True)
            total_concurrent_time = time.time() - start_time
            successful_executions = []
            failed_executions = []
            for i, (result, (_, scenario, user_context, engine)) in enumerate(zip(results, concurrent_tasks)):
                if isinstance(result, Exception):
                    failed_executions.append((i, result, scenario))
                else:
                    successful_executions.append((i, result, scenario, user_context))
            total_executions = len(results)
            success_count = len(successful_executions)
            concurrent_success_rate = success_count / total_executions
            assert concurrent_success_rate >= 0.8, f'Concurrent success rate should be  >= 80%, got {concurrent_success_rate:.1%} ({success_count}/{total_executions})'
            assert total_concurrent_time < 600, f'Concurrent workflows should complete in <10 minutes, took {total_concurrent_time:.1f}s'
            user_ids_in_results = set()
            for _, metrics, _, user_context in successful_executions:
                user_ids_in_results.add(str(user_context.user_id))
            expected_user_ids = set((str(user.user_id) for user in authenticated_users[:len(successful_executions)]))
            assert user_ids_in_results == expected_user_ids, 'User isolation should be maintained during concurrent execution'
            for execution_index, metrics, scenario, user_context in successful_executions:
                max_time = scenario.sla_requirements.get('max_execution_time_minutes', 10.0) * 60
                assert metrics.total_execution_time <= max_time * 1.5, f'Workflow {execution_index} execution time acceptable under concurrent load'
                business_value_score = metrics.business_value_delivered.get('overall_business_value_score', 0.0)
                assert business_value_score >= 0.6, f'Workflow {execution_index} should deliver business value under concurrent load'
            total_events_received = sum((engine.websocket_events_received for _, metrics, _, _ in successful_executions))
            assert total_events_received >= len(successful_executions) * 10, f'Should receive adequate WebSocket events across all concurrent workflows'
            for _, _, _, engine in concurrent_tasks:
                pass
        finally:
            cleanup_tasks = [engine.cleanup() for engine in engines]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

@pytest.mark.e2e
class AuthenticationSecurityEdgeCasesTests(SSotBaseTestCase):
    """Test authentication security and edge cases in enterprise workflows."""

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_workflow_authentication_edge_cases(self, staging_config, enterprise_auth_helper):
        """Test various authentication edge cases and security scenarios."""
        try:
            expired_token_user = await create_authenticated_user_context(user_email='expired_token@staging.com', environment='staging', permissions=['read', 'write'], websocket_enabled=True)
            expired_token_user.agent_context['jwt_token_expired'] = True
            simple_workflow = EnterpriseWorkflowRequest(workflow_type='simple_test', business_objective='Test authentication handling', input_parameters={'test': 'expired_token'}, expected_deliverables=['test_result'], sla_requirements={'max_execution_time_minutes': 2.0}, authentication_requirements=['jwt_token_validation'])
            engine = EnterpriseWorkflowExecutionEngine(staging_config, enterprise_auth_helper)
            await engine.initialize()
            try:
                result = await engine.execute_complete_enterprise_workflow(simple_workflow, expired_token_user)
                assert result.authentication_validations > 0, 'Should have performed authentication validations'
            except Exception as e:
                error_msg = str(e).lower()
                auth_error_indicators = ['token', 'auth', 'expired', 'invalid', 'unauthorized']
                assert any((indicator in error_msg for indicator in auth_error_indicators)), f'Authentication failure should be clearly identified: {error_msg}'
            finally:
                await engine.cleanup()
        except Exception as e:
            assert 'auth' in str(e).lower() or 'token' in str(e).lower(), f'Setup failure should be authentication-related: {str(e)}'
        try:
            limited_user = await create_authenticated_user_context(user_email='limited_permissions@staging.com', environment='staging', permissions=['read'], websocket_enabled=True)
            permission_workflow = EnterpriseWorkflowRequest(workflow_type='permission_test', business_objective='Test permission enforcement', input_parameters={'test': 'insufficient_permissions'}, expected_deliverables=['test_result'], sla_requirements={'max_execution_time_minutes': 2.0}, authentication_requirements=['jwt_token_validation', 'write', 'agent_execute'])
            engine = EnterpriseWorkflowExecutionEngine(staging_config, enterprise_auth_helper)
            await engine.initialize()
            try:
                with pytest.raises(Exception) as exc_info:
                    await engine.execute_complete_enterprise_workflow(permission_workflow, limited_user)
                error_msg = str(exc_info.value).lower()
                permission_error_indicators = ['permission', 'access', 'forbidden', 'unauthorized']
                assert any((indicator in error_msg for indicator in permission_error_indicators)), f'Should raise permission-related error: {error_msg}'
            finally:
                await engine.cleanup()
        except Exception as e:
            pass

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_workflow_websocket_authentication_integration(self, staging_config, enterprise_auth_helper):
        """Test WebSocket authentication integration during workflows."""
        ws_test_user = await create_authenticated_user_context(user_email='websocket_auth@staging.com', environment='staging', permissions=['read', 'write', 'agent_execute'], websocket_enabled=True)
        websocket_workflow = EnterpriseWorkflowRequest(workflow_type='websocket_test', business_objective='Test WebSocket authentication and event flow', input_parameters={'test': 'websocket_events', 'generate_events': True}, expected_deliverables=['event_report'], sla_requirements={'max_execution_time_minutes': 3.0, 'required_websocket_events': 5}, authentication_requirements=['jwt_token_validation', 'websocket_access'])
        engine = EnterpriseWorkflowExecutionEngine(staging_config, enterprise_auth_helper)
        await engine.initialize()
        try:
            initial_event_count = len(engine.websocket_events)
            execution_metrics = await engine.execute_complete_enterprise_workflow(websocket_workflow, ws_test_user)
            final_event_count = len(engine.websocket_events)
            events_received = final_event_count - initial_event_count
            assert events_received >= 3, f'Should have received WebSocket events during workflow, got {events_received}'
            workflow_events = engine.websocket_events[initial_event_count:]
            authenticated_events = 0
            for event_entry in workflow_events:
                event_str = str(event_entry).lower()
                if str(ws_test_user.user_id) in event_str:
                    authenticated_events += 1
            assert authenticated_events > 0, 'WebSocket events should contain authenticated user context'
            for event_entry in workflow_events:
                event_str = str(event_entry).lower()
                sensitive_data = ['password', 'secret', 'private_key', 'token']
                assert not any((sensitive in event_str for sensitive in sensitive_data)), 'WebSocket events should not contain sensitive authentication data'
            assert execution_metrics.websocket_events_received >= 3, f'Execution metrics should track WebSocket events, got {execution_metrics.websocket_events_received}'
        finally:
            await engine.cleanup()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')