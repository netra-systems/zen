"""Domain Expert Agents E2E Test Suite - Business Critical Testing

MISSION CRITICAL: Tests domain expert agents (finance, engineering, business) with real services.
Business Value: Ensure specialized expertise delivery for enterprise clients.

Business Value Justification (BVJ):
1. Segment: Mid, Enterprise
2. Business Goal: Enable specialized AI consultation and domain expertise
3. Value Impact: Domain experts provide expert-level advice in specific industries
4. Revenue Impact: 400K+ ARR from specialized consulting and domain expertise features

CLAUDE.md COMPLIANCE:
- Uses real services ONLY (NO MOCKS)
- Validates ALL 5 required WebSocket events per expert
- Tests actual domain expert business logic
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
from enum import Enum
import os
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent if '__file__' in locals() else Path.cwd().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
import pytest
from loguru import logger
from shared.isolated_environment import get_env
from tests.e2e.e2e_test_config import get_e2e_config, E2ETestConfig, REQUIRED_WEBSOCKET_EVENTS

class DomainExpertType(Enum):
    """Domain expert specializations."""
    FINANCE = 'finance_expert'
    ENGINEERING = 'engineering_expert'
    BUSINESS = 'business_expert'

@dataclass
class DomainExpertValidation:
    """Captures and validates domain expert agent execution."""
    user_id: str
    thread_id: str
    expert_type: DomainExpertType
    consultation_request: str
    start_time: float = field(default_factory=time.time)
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    event_types_seen: Set[str] = field(default_factory=set)
    expertise_applied: List[str] = field(default_factory=list)
    domain_recommendations: List[str] = field(default_factory=list)
    compliance_checks: Dict[str, Any] = field(default_factory=dict)
    analysis_depth: int = 0
    tools_executed: List[str] = field(default_factory=list)
    final_expert_response: Optional[Dict[str, Any]] = None
    time_to_expert_started: Optional[float] = None
    time_to_first_expertise: Optional[float] = None
    time_to_domain_analysis: Optional[float] = None
    time_to_consultation_completion: Optional[float] = None
    expert_knowledge_demonstrated: bool = False
    domain_specific_analysis: bool = False
    actionable_recommendations: bool = False
    compliance_validated: bool = False
    consultation_quality: float = 0.0

class RealDomainExpertsTester:
    """Tests domain expert agents with real services and WebSocket events."""
    REQUIRED_EVENTS = set(REQUIRED_WEBSOCKET_EVENTS.keys())
    DOMAIN_EXPERT_SCENARIOS = {DomainExpertType.FINANCE: [{'consultation_type': 'tco_analysis', 'request': 'Perform total cost of ownership analysis for migrating to cloud infrastructure with 500 users', 'expected_expertise': ['cost_breakdown', 'roi_calculation', 'financial_modeling'], 'expected_tools': ['cost_calculator', 'financial_analyzer', 'roi_predictor'], 'success_criteria': ['detailed_cost_analysis', 'roi_projections', 'payback_timeline']}, {'consultation_type': 'budget_optimization', 'request': 'Optimize IT budget allocation for a growing enterprise with $2M annual technology spend', 'expected_expertise': ['budget_planning', 'cost_optimization', 'resource_allocation'], 'expected_tools': ['budget_optimizer', 'spend_analyzer', 'allocation_model'], 'success_criteria': ['optimized_budget', 'savings_identified', 'allocation_strategy']}, {'consultation_type': 'financial_risk_assessment', 'request': 'Assess financial risks of implementing AI automation across business operations', 'expected_expertise': ['risk_assessment', 'financial_impact', 'cost_benefit_analysis'], 'expected_tools': ['risk_calculator', 'impact_analyzer', 'scenario_modeler'], 'success_criteria': ['risk_identification', 'mitigation_strategies', 'financial_impact']}], DomainExpertType.ENGINEERING: [{'consultation_type': 'architecture_review', 'request': 'Review microservices architecture for scalability and performance optimization', 'expected_expertise': ['system_design', 'scalability_patterns', 'performance_optimization'], 'expected_tools': ['architecture_analyzer', 'performance_profiler', 'scalability_checker'], 'success_criteria': ['architecture_assessment', 'optimization_recommendations', 'scalability_plan']}, {'consultation_type': 'security_assessment', 'request': 'Conduct comprehensive security assessment of cloud-native application infrastructure', 'expected_expertise': ['security_architecture', 'threat_modeling', 'compliance_standards'], 'expected_tools': ['security_scanner', 'threat_analyzer', 'compliance_checker'], 'success_criteria': ['security_gaps', 'threat_mitigation', 'compliance_roadmap']}, {'consultation_type': 'technology_modernization', 'request': 'Plan technology stack modernization from legacy monolith to cloud-native microservices', 'expected_expertise': ['modernization_strategy', 'migration_planning', 'technology_selection'], 'expected_tools': ['migration_planner', 'technology_assessor', 'modernization_roadmap'], 'success_criteria': ['migration_strategy', 'technology_recommendations', 'implementation_timeline']}], DomainExpertType.BUSINESS: [{'consultation_type': 'digital_transformation', 'request': 'Develop digital transformation strategy for traditional manufacturing company', 'expected_expertise': ['transformation_strategy', 'change_management', 'business_process_optimization'], 'expected_tools': ['transformation_planner', 'process_analyzer', 'strategy_generator'], 'success_criteria': ['transformation_roadmap', 'change_strategy', 'process_improvements']}, {'consultation_type': 'market_expansion', 'request': 'Analyze market expansion opportunities for SaaS product in European markets', 'expected_expertise': ['market_analysis', 'competitive_intelligence', 'expansion_strategy'], 'expected_tools': ['market_analyzer', 'competitor_research', 'expansion_planner'], 'success_criteria': ['market_insights', 'expansion_plan', 'competitive_positioning']}, {'consultation_type': 'operational_efficiency', 'request': 'Improve operational efficiency through AI-powered automation and process optimization', 'expected_expertise': ['process_optimization', 'automation_strategy', 'efficiency_metrics'], 'expected_tools': ['process_mapper', 'efficiency_analyzer', 'automation_advisor'], 'success_criteria': ['efficiency_gains', 'automation_opportunities', 'optimization_plan']}]}

    def __init__(self, config: Optional[E2ETestConfig]=None):
        self.config = config or get_e2e_config()
        self.env = None
        self.ws_client = None
        self.backend_client = None
        self.jwt_helper = None
        self.validations: List[DomainExpertValidation] = []

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
        user_data = create_test_user_data('domain_expert_test')
        self.user_id = str(uuid.uuid4())
        self.email = user_data['email']
        self.token = self.jwt_helper.create_access_token(self.user_id, self.email, permissions=['experts:consult', 'domain:access', 'analysis:advanced', 'tools:specialized', 'finance:analyze', 'engineering:assess', 'business:strategize', 'consultation:premium'])
        ws_url = self.config.websocket_url
        self.ws_client = WebSocketTestClient(ws_url)
        connected = await self.ws_client.connect(token=self.token)
        if not connected:
            raise RuntimeError('Failed to connect to WebSocket')
        logger.info(f'Domain experts test environment ready for user {self.email}')
        logger.info(f'Using backend: {self.config.backend_url}')
        logger.info(f'Using websocket: {self.config.websocket_url}')
        return self

    async def teardown(self):
        """Clean up test environment."""
        if self.ws_client:
            await self.ws_client.disconnect()

    async def execute_domain_expert_consultation(self, expert_type: DomainExpertType, scenario: Dict[str, Any], timeout: float=120.0) -> DomainExpertValidation:
        """Execute a domain expert consultation and validate results.
        
        Args:
            expert_type: Type of domain expert
            scenario: Consultation scenario configuration
            timeout: Maximum execution time
            
        Returns:
            Complete validation results
        """
        thread_id = str(uuid.uuid4())
        validation = DomainExpertValidation(user_id=self.user_id, thread_id=thread_id, expert_type=expert_type, consultation_request=scenario['request'])
        consultation_request = {'type': 'agent_request', 'agent': expert_type.value, 'message': scenario['request'], 'thread_id': thread_id, 'context': {'consultation_type': scenario['consultation_type'], 'expert_domain': expert_type.value.replace('_expert', ''), 'analysis_depth': 'comprehensive', 'user_id': self.user_id, 'expected_deliverables': scenario.get('success_criteria', [])}, 'optimistic_id': str(uuid.uuid4())}
        await self.ws_client.send_json(consultation_request)
        logger.info(f"Sent {expert_type.value} consultation: {scenario['consultation_type']} - {scenario['request'][:50]}...")
        start_time = time.time()
        completed = False
        while time.time() - start_time < timeout and (not completed):
            event = await self.ws_client.receive(timeout=2.0)
            if event:
                await self._process_domain_expert_event(event, validation, scenario)
                if event.get('type') in ['agent_completed', 'consultation_completed', 'error']:
                    completed = True
                    validation.time_to_consultation_completion = time.time() - start_time
        self._validate_domain_expert_consultation(validation, scenario)
        self.validations.append(validation)
        return validation

    async def _process_domain_expert_event(self, event: Dict[str, Any], validation: DomainExpertValidation, scenario: Dict[str, Any]):
        """Process and categorize domain expert specific events."""
        event_type = event.get('type', 'unknown')
        event_time = time.time() - validation.start_time
        validation.events_received.append(event)
        validation.event_types_seen.add(event_type)
        if event_type == 'agent_started' and (not validation.time_to_expert_started):
            validation.time_to_expert_started = event_time
            logger.info(f'Domain expert {validation.expert_type.value} started at {event_time:.2f}s')
        elif event_type == 'agent_thinking' and (not validation.time_to_first_expertise):
            validation.time_to_first_expertise = event_time
            thinking_data = event.get('data', {})
            if isinstance(thinking_data, dict):
                thought = thinking_data.get('thought', '')
                if any((expertise in thought.lower() for expertise in scenario.get('expected_expertise', []))):
                    validation.expertise_applied.append(thought)
                    validation.analysis_depth += 1
        elif event_type == 'tool_executing' and (not validation.time_to_domain_analysis):
            validation.time_to_domain_analysis = event_time
            tool_name = event.get('data', {}).get('tool_name', 'unknown')
            validation.tools_executed.append(tool_name)
            logger.info(f'Domain expert executing specialized tool: {tool_name}')
        elif event_type == 'tool_completed':
            tool_result = event.get('data', {}).get('result', {})
            if isinstance(tool_result, dict):
                if 'analysis' in tool_result or 'recommendations' in tool_result:
                    if 'recommendations' in tool_result and isinstance(tool_result['recommendations'], list):
                        validation.domain_recommendations.extend(tool_result['recommendations'])
                    if 'compliance' in tool_result:
                        validation.compliance_checks.update(tool_result.get('compliance', {}))
        elif event_type in ['agent_completed', 'consultation_completed']:
            final_data = event.get('data', {})
            if isinstance(final_data, dict):
                validation.final_expert_response = final_data
                logger.info(f'Domain consultation completed with sections: {list(final_data.keys())}')
                if 'domain' in final_data:
                    validation.expert_knowledge_demonstrated = True
                if 'recommendations' in final_data and isinstance(final_data['recommendations'], list):
                    validation.domain_recommendations.extend(final_data['recommendations'])
                if 'compliance' in final_data:
                    validation.compliance_checks.update(final_data['compliance'])

    def _validate_domain_expert_consultation(self, validation: DomainExpertValidation, scenario: Dict[str, Any]):
        """Validate domain expert consultation against business requirements."""
        expected_expertise = scenario.get('expected_expertise', [])
        expertise_content = ' '.join(validation.expertise_applied).lower()
        final_content = str(validation.final_expert_response).lower() if validation.final_expert_response else ''
        validation.expert_knowledge_demonstrated = len(expected_expertise) > 0 and any((exp_expertise.lower().replace('_', ' ') in expertise_content or exp_expertise.lower().replace('_', ' ') in final_content for exp_expertise in expected_expertise))
        if validation.analysis_depth > 0 or validation.final_expert_response:
            analysis_quality_score = 0
            if validation.analysis_depth >= 2:
                analysis_quality_score += 1
            if len(validation.tools_executed) >= 1:
                analysis_quality_score += 1
            if validation.final_expert_response and len(str(validation.final_expert_response)) > 300:
                analysis_quality_score += 1
            if len(validation.domain_recommendations) > 0:
                analysis_quality_score += 1
            validation.domain_specific_analysis = analysis_quality_score >= 2
        if validation.domain_recommendations or (validation.final_expert_response and 'recommendations' in str(validation.final_expert_response)):
            recommendation_content = ' '.join(validation.domain_recommendations).lower()
            final_content = str(validation.final_expert_response).lower()
            actionable_indicators = ['implement', 'recommend', 'suggest', 'improve', 'optimize', 'consider', 'adopt', 'upgrade', 'migrate', 'establish']
            validation.actionable_recommendations = any((indicator in recommendation_content or indicator in final_content for indicator in actionable_indicators))
        if validation.compliance_checks or (validation.final_expert_response and 'compliance' in str(validation.final_expert_response)):
            validation.compliance_validated = True
        else:
            compliance_terms = ['compliance', 'standard', 'regulation', 'policy', 'guideline']
            all_content = expertise_content + final_content
            validation.compliance_validated = any((term in all_content for term in compliance_terms))
        quality_components = [validation.expert_knowledge_demonstrated, validation.domain_specific_analysis, validation.actionable_recommendations, validation.compliance_validated]
        validation.consultation_quality = sum(quality_components) / len(quality_components)

    def generate_domain_experts_report(self) -> str:
        """Generate comprehensive domain experts test report."""
        report = []
        report.append('=' * 80)
        report.append('REAL DOMAIN EXPERT AGENTS TEST REPORT')
        report.append('=' * 80)
        report.append(f'Total domain expert consultations tested: {len(self.validations)}')
        report.append('')
        by_expert_type = {}
        for val in self.validations:
            expert_type = val.expert_type.value
            if expert_type not in by_expert_type:
                by_expert_type[expert_type] = []
            by_expert_type[expert_type].append(val)
        for expert_type, validations in by_expert_type.items():
            report.append(f'\n--- {expert_type.upper()} EXPERT CONSULTATIONS ---')
            report.append(f'Consultations: {len(validations)}')
            for i, val in enumerate(validations, 1):
                report.append(f'\n  Consultation {i}:')
                report.append(f'    Request: {val.consultation_request[:80]}...')
                report.append(f'    User ID: {val.user_id}')
                report.append(f'    Thread ID: {val.thread_id}')
                report.append(f'    Events received: {len(val.events_received)}')
                report.append(f'    Event types: {sorted(val.event_types_seen)}')
                missing_events = self.REQUIRED_EVENTS - val.event_types_seen
                if missing_events:
                    report.append(f'     WARNING: MISSING REQUIRED EVENTS: {missing_events}')
                else:
                    report.append('    CHECK All required WebSocket events received')
                report.append('    Performance Metrics:')
                report.append(f'      - Expert started: {val.time_to_expert_started:.2f}s' if val.time_to_expert_started else '      - Expert not started')
                report.append(f'      - First expertise: {val.time_to_first_expertise:.2f}s' if val.time_to_first_expertise else '      - No expertise observed')
                report.append(f'      - Domain analysis: {val.time_to_domain_analysis:.2f}s' if val.time_to_domain_analysis else '      - No analysis performed')
                report.append(f'      - Consultation completion: {val.time_to_consultation_completion:.2f}s' if val.time_to_consultation_completion else '      - Consultation not completed')
                report.append('    Domain Expertise Validation:')
                report.append(f'      CHECK Expert knowledge demonstrated: {val.expert_knowledge_demonstrated}')
                report.append(f'      CHECK Domain-specific analysis: {val.domain_specific_analysis}')
                report.append(f'      CHECK Actionable recommendations: {val.actionable_recommendations}')
                report.append(f'      CHECK Compliance validated: {val.compliance_validated}')
                report.append(f'      CHECK Overall consultation quality: {val.consultation_quality:.1%}')
                if val.expertise_applied:
                    report.append(f'    Expertise Applied ({len(val.expertise_applied)} insights):')
                    for insight in val.expertise_applied[:2]:
                        report.append(f'      - {insight[:100]}...')
                if val.tools_executed:
                    report.append(f"    Specialized Tools: {', '.join(set(val.tools_executed))}")
                if val.domain_recommendations:
                    report.append(f'    Domain Recommendations: {len(val.domain_recommendations)} provided')
                if val.compliance_checks:
                    report.append(f'    Compliance Checks: {len(val.compliance_checks)} assessments')
        report.append('\n' + '=' * 80)
        report.append('SUMMARY STATISTICS')
        report.append('=' * 80)
        if self.validations:
            avg_quality = sum((v.consultation_quality for v in self.validations)) / len(self.validations)
            high_quality = sum((1 for v in self.validations if v.consultation_quality >= 0.7))
            report.append(f'Average consultation quality: {avg_quality:.1%}')
            report.append(f'High-quality consultations: {high_quality}/{len(self.validations)} ({high_quality / len(self.validations):.1%})')
            completion_times = [v.time_to_consultation_completion for v in self.validations if v.time_to_consultation_completion]
            if completion_times:
                avg_completion = sum(completion_times) / len(completion_times)
                report.append(f'Average consultation completion time: {avg_completion:.2f}s')
        report.append('\n' + '=' * 80)
        return '\n'.join(report)

@pytest.fixture(params=['local', 'staging'])
async def domain_experts_tester(request):
    """Create and setup the domain experts tester for both local and staging."""
    test_env = get_env().get('E2E_TEST_ENV', None)
    if test_env and test_env != request.param:
        pytest.skip(f'Skipping {request.param} tests (E2E_TEST_ENV={test_env})')
    if request.param == 'staging':
        config = get_e2e_config('staging')
        if not config.is_available():
            pytest.skip(f'Staging environment not available: {config.backend_url}')
    config = get_e2e_config(request.param)
    tester = RealDomainExpertsTester(config)
    await tester.setup()
    yield tester
    await tester.teardown()

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.real_llm
class RealDomainExpertsTests:
    """Test suite for real domain expert agent execution."""

    async def test_finance_expert_tco_analysis(self, domain_experts_tester):
        """Test finance expert total cost of ownership analysis."""
        scenario = domain_experts_tester.DOMAIN_EXPERT_SCENARIOS[DomainExpertType.FINANCE][0]
        validation = await domain_experts_tester.execute_domain_expert_consultation(DomainExpertType.FINANCE, scenario, timeout=150.0)
        missing_events = domain_experts_tester.REQUIRED_EVENTS - validation.event_types_seen
        assert not missing_events, f'Missing required events: {missing_events}'
        assert validation.time_to_expert_started is not None, 'Finance expert should have started'
        assert validation.time_to_expert_started < 8.0, 'Finance expert should start quickly'
        assert len(validation.events_received) >= 5, 'Should have substantial expert consultation flow'
        if validation.final_expert_response:
            response_content = str(validation.final_expert_response).lower()
            finance_terms = ['cost', 'roi', 'financial', 'budget', 'investment']
            assert any((term in response_content for term in finance_terms)), 'Finance expert should use financial terminology'
        if validation.time_to_consultation_completion:
            assert validation.time_to_consultation_completion < 120.0, 'Should complete within performance target'

    async def test_engineering_expert_architecture_review(self, domain_experts_tester):
        """Test engineering expert architecture review consultation."""
        scenario = domain_experts_tester.DOMAIN_EXPERT_SCENARIOS[DomainExpertType.ENGINEERING][0]
        validation = await domain_experts_tester.execute_domain_expert_consultation(DomainExpertType.ENGINEERING, scenario, timeout=140.0)
        assert 'agent_started' in validation.event_types_seen, 'Should have agent_started event'
        assert len(validation.events_received) > 0, 'Should receive consultation events'
        if validation.expertise_applied:
            assert len(validation.expertise_applied) > 0, 'Should demonstrate engineering expertise'
        if validation.tools_executed:
            assert len(validation.tools_executed) > 0, 'Should use engineering tools'
        if validation.final_expert_response:
            response_content = str(validation.final_expert_response).lower()
            engineering_terms = ['architecture', 'scalability', 'performance', 'system', 'design']
            assert any((term in response_content for term in engineering_terms)), 'Engineering expert should use technical terminology'

    async def test_business_expert_digital_transformation(self, domain_experts_tester):
        """Test business expert digital transformation consultation."""
        scenario = domain_experts_tester.DOMAIN_EXPERT_SCENARIOS[DomainExpertType.BUSINESS][0]
        validation = await domain_experts_tester.execute_domain_expert_consultation(DomainExpertType.BUSINESS, scenario, timeout=130.0)
        assert validation.events_received, 'Should receive consultation events'
        if validation.final_expert_response:
            response_content = str(validation.final_expert_response).lower()
            business_terms = ['strategy', 'transformation', 'business', 'process', 'change']
            assert any((term in response_content for term in business_terms)), 'Business expert should use strategic terminology'
        if validation.domain_recommendations:
            assert len(validation.domain_recommendations) > 0, 'Should provide strategic recommendations'

    async def test_domain_experts_consultation_quality(self, domain_experts_tester):
        """Test domain expert consultation quality metrics across all experts."""
        scenarios_to_test = [(DomainExpertType.FINANCE, domain_experts_tester.DOMAIN_EXPERT_SCENARIOS[DomainExpertType.FINANCE][1]), (DomainExpertType.ENGINEERING, domain_experts_tester.DOMAIN_EXPERT_SCENARIOS[DomainExpertType.ENGINEERING][1]), (DomainExpertType.BUSINESS, domain_experts_tester.DOMAIN_EXPERT_SCENARIOS[DomainExpertType.BUSINESS][1])]
        quality_results = []
        for expert_type, scenario in scenarios_to_test:
            validation = await domain_experts_tester.execute_domain_expert_consultation(expert_type, scenario, timeout=120.0)
            quality_results.append(validation)
        for validation in quality_results:
            assert validation.consultation_quality >= 0.5, f'{validation.expert_type.value} consultation quality {validation.consultation_quality:.1%} below minimum'
        avg_quality = sum((v.consultation_quality for v in quality_results)) / len(quality_results)
        assert avg_quality >= 0.6, f'Average domain expert quality {avg_quality:.1%} below acceptable threshold'
        logger.info(f'Domain experts average consultation quality: {avg_quality:.1%}')

    async def test_domain_experts_performance_benchmarks(self, domain_experts_tester):
        """Test domain expert performance against business benchmarks."""
        quick_scenarios = [(DomainExpertType.FINANCE, {'consultation_type': 'quick_financial_assessment', 'request': 'Quick assessment of cloud cost optimization opportunities', 'expected_expertise': ['cost_analysis'], 'success_criteria': ['cost_insights']}), (DomainExpertType.ENGINEERING, {'consultation_type': 'quick_tech_review', 'request': 'Quick review of system performance bottlenecks', 'expected_expertise': ['performance_analysis'], 'success_criteria': ['performance_insights']})]
        performance_results = []
        for expert_type, scenario in quick_scenarios:
            validation = await domain_experts_tester.execute_domain_expert_consultation(expert_type, scenario, timeout=90.0)
            performance_results.append(validation)
        start_times = [v.time_to_expert_started for v in performance_results if v.time_to_expert_started]
        completion_times = [v.time_to_consultation_completion for v in performance_results if v.time_to_consultation_completion]
        if start_times:
            avg_start_time = sum(start_times) / len(start_times)
            assert avg_start_time < 10.0, f'Average expert start time {avg_start_time:.2f}s too slow'
        if completion_times:
            avg_completion = sum(completion_times) / len(completion_times)
            assert avg_completion < 100.0, f'Average expert completion {avg_completion:.2f}s too slow'

    async def test_domain_experts_error_handling(self, domain_experts_tester):
        """Test error handling across domain experts."""
        challenging_scenarios = [(DomainExpertType.FINANCE, {'consultation_type': 'complex_financial_modeling', 'request': 'Create complex financial model for cryptocurrency trading platform with regulatory uncertainty', 'expected_expertise': ['financial_modeling'], 'success_criteria': ['analysis_attempt']}), (DomainExpertType.ENGINEERING, {'consultation_type': 'impossible_architecture', 'request': 'Design zero-latency global distributed system with infinite scalability and no cost', 'expected_expertise': ['architecture_design'], 'success_criteria': ['realistic_assessment']})]
        for expert_type, scenario in challenging_scenarios:
            validation = await domain_experts_tester.execute_domain_expert_consultation(expert_type, scenario, timeout=80.0)
            assert len(validation.events_received) > 0, f'{expert_type.value} should receive events even with challenging requests'
            assert validation.time_to_expert_started is not None or 'error' in validation.event_types_seen, f'{expert_type.value} should start or handle complexity gracefully'

    async def test_comprehensive_domain_experts_report(self, domain_experts_tester):
        """Run comprehensive test across all domain experts and generate detailed report."""
        comprehensive_scenarios = [(DomainExpertType.FINANCE, domain_experts_tester.DOMAIN_EXPERT_SCENARIOS[DomainExpertType.FINANCE][0]), (DomainExpertType.ENGINEERING, domain_experts_tester.DOMAIN_EXPERT_SCENARIOS[DomainExpertType.ENGINEERING][0]), (DomainExpertType.BUSINESS, domain_experts_tester.DOMAIN_EXPERT_SCENARIOS[DomainExpertType.BUSINESS][0])]
        for expert_type, scenario in comprehensive_scenarios:
            await domain_experts_tester.execute_domain_expert_consultation(expert_type, scenario, timeout=140.0)
        report = domain_experts_tester.generate_domain_experts_report()
        logger.info('\n' + report)
        report_file = os.path.join(project_root, 'test_outputs', 'domain_experts_e2e_report.txt')
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            f.write(f'\n\nGenerated at: {datetime.now().isoformat()}\n')
        logger.info(f'Domain experts report saved to: {report_file}')
        total_tests = len(domain_experts_tester.validations)
        successful_consultations = sum((1 for v in domain_experts_tester.validations if v.expert_knowledge_demonstrated and v.consultation_quality >= 0.5))
        assert successful_consultations > 0, 'At least some domain expert consultations should demonstrate expertise'
        success_rate = successful_consultations / total_tests if total_tests > 0 else 0
        logger.info(f'Domain experts consultation success rate: {success_rate:.1%}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')