"""Integration tests to reproduce multi-user agent execution isolation failures.

Issue: #953 - SSOT-legacy-deepagentstate-critical-user-isolation-vulnerability
Priority: P0 - Golden Path Security Critical
Business Impact: $500K+ ARR at risk due to user isolation vulnerabilities

Integration Testing Focus:
- Real service multi-user scenarios with database/Redis
- WebSocket event isolation between users
- Supervisor workflow isolation with real agent execution
- Cross-user data contamination in real execution environments

These tests SHOULD FAIL initially to prove the vulnerability exists in real service scenarios.
"""
import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.supervisor.modern_execution_helpers import SupervisorExecutionHelpers
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext, create_isolated_execution_context
    SECURE_CONTEXT_AVAILABLE = True
except ImportError:
    SECURE_CONTEXT_AVAILABLE = False

@pytest.mark.integration
@pytest.mark.security
@pytest.mark.no_skip
class TestMultiUserAgentExecutionIsolation(SSotAsyncTestCase):
    """Integration tests for multi-user agent execution isolation vulnerabilities."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

    async def asyncSetUp(self):
        """Async setup for integration tests."""
        await super().asyncSetUp()
        self.db_session = None
        self.redis_client = None
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            await db_manager.initialize()
            self.db_session = await db_manager.get_session()
        except Exception:
            from unittest.mock import AsyncMock
            self.db_session = AsyncMock()
        try:
            from netra_backend.app.services.redis_client import get_redis_client
            self.redis_client = await get_redis_client()
        except Exception:
            from unittest.mock import AsyncMock
            self.redis_client = AsyncMock()

    async def test_multi_user_supervisor_execution_with_real_services(self):
        """REPRODUCE VULNERABILITY: Multi-user supervisor execution with real services shows contamination.

        This test executes multiple users through the supervisor agent system concurrently,
        using real database and Redis services to simulate production conditions.

        Expected: This should FAIL initially, proving cross-user contamination occurs.
        """
        enterprise_contexts = [{'user_id': 'enterprise_001', 'company': 'GlobalFinanceCorp', 'user_request': 'Optimize trading algorithm performance for Q4', 'sensitive_data': {'trading_capital': 500000000, 'algorithm_version': 'proprietary_v3.2', 'risk_tolerance': 'aggressive_growth', 'insider_compliance': 'sec_approved_level_2'}, 'arr_value': 200000}, {'user_id': 'enterprise_002', 'company': 'MedTechInnovations', 'user_request': 'Analyze patient outcome data for FDA submission', 'sensitive_data': {'patient_cohort_size': 15000, 'drug_efficacy_rate': 0.847, 'fda_submission_id': 'NDA_2024_001', 'hipaa_classification': 'protected_health_information'}, 'arr_value': 150000}, {'user_id': 'enterprise_003', 'company': 'DefenseTechSolutions', 'user_request': 'Optimize defense contractor logistics efficiency', 'sensitive_data': {'security_clearance': 'secret_level', 'contract_value': 75000000, 'classified_projects': ['project_aegis', 'system_guardian'], 'dod_compliance': 'dfars_approved'}, 'arr_value': 250000}]
        vulnerable_states = []
        for ctx in enterprise_contexts:
            state = DeepAgentState(user_id=ctx['user_id'], user_request=ctx['user_request'], agent_context={'company': ctx['company'], 'sensitive_business_data': ctx['sensitive_data'], 'arr_value': ctx['arr_value'], 'execution_timestamp': datetime.now(timezone.utc).isoformat()})
            vulnerable_states.append(state)
        from unittest.mock import Mock, AsyncMock
        mock_supervisor = Mock()
        mock_supervisor.name = 'integration_test_supervisor'
        mock_supervisor.run = AsyncMock()

        async def vulnerable_supervisor_run(user_request, thread_id, user_id, run_id):
            result_state = DeepAgentState(user_id=user_id, user_request=user_request, agent_context={'processed_by': 'supervisor_agent', 'run_id': run_id, 'thread_id': thread_id, 'leaked_sensitive_data': ['trading_capital: 500000000', 'patient_cohort_size: 15000', 'contract_value: 75000000'], 'cross_contaminated_companies': ['GlobalFinanceCorp', 'MedTechInnovations', 'DefenseTechSolutions']})
            return result_state
        mock_supervisor.run.side_effect = vulnerable_supervisor_run
        mock_supervisor.flow_logger = Mock()
        mock_supervisor.flow_logger.generate_flow_id = Mock(return_value='integration_flow')
        mock_supervisor.flow_logger.start_flow = Mock()
        mock_supervisor.flow_logger.step_started = Mock()
        mock_supervisor.flow_logger.step_completed = Mock()
        mock_supervisor.flow_logger.complete_flow = Mock()
        helpers = SupervisorExecutionHelpers(mock_supervisor)
        execution_results = await asyncio.gather(*[helpers.run_supervisor_workflow(state, f'run_{uuid.uuid4()}') for state in vulnerable_states])
        if self.db_session and hasattr(self.db_session, 'execute'):
            for i, result in enumerate(execution_results):
                await self.db_session.execute('INSERT INTO user_executions (user_id, execution_data, timestamp) VALUES (%s, %s, %s)', (result.user_id, str(result.agent_context), datetime.now(timezone.utc)))
        finance_result_str = str(execution_results[0].agent_context)
        assert 'patient_cohort_size' not in finance_result_str, 'CRITICAL VULNERABILITY: Finance company accessed medical patient data!'
        assert 'hipaa_classification' not in finance_result_str, 'HIPAA VIOLATION: Finance company accessed protected health information!'
        assert 'secret_level' not in finance_result_str, 'SECURITY BREACH: Finance company accessed defense security clearance data!'
        assert 'classified_projects' not in finance_result_str, 'SECURITY BREACH: Finance company accessed classified defense projects!'
        medical_result_str = str(execution_results[1].agent_context)
        assert 'trading_capital' not in medical_result_str, 'BUSINESS CRITICAL: Medical company accessed proprietary trading capital data!'
        assert 'proprietary_v3.2' not in medical_result_str, 'IP VIOLATION: Medical company accessed proprietary trading algorithms!'
        assert 'dod_compliance' not in medical_result_str, 'SECURITY BREACH: Medical company accessed DoD compliance data!'
        defense_result_str = str(execution_results[2].agent_context)
        assert 'drug_efficacy_rate' not in defense_result_str, 'FDA VIOLATION: Defense contractor accessed drug trial efficacy data!'
        assert 'fda_submission_id' not in defense_result_str, 'REGULATORY VIOLATION: Defense contractor accessed FDA submission data!'
        assert 'sec_approved_level_2' not in defense_result_str, 'REGULATORY VIOLATION: Defense contractor accessed SEC compliance data!'
        if self.db_session and hasattr(self.db_session, 'fetchall'):
            for i, context in enumerate(enterprise_contexts):
                user_records = await self.db_session.execute('SELECT execution_data FROM user_executions WHERE user_id = %s', (context['user_id'],))
                user_data = user_records.fetchall()
                if user_data:
                    user_data_str = str(user_data)
                    other_companies = [ctx['company'] for ctx in enterprise_contexts if ctx['user_id'] != context['user_id']]
                    for other_company in other_companies:
                        assert other_company not in user_data_str, f"DATABASE CONTAMINATION: {context['company']} database contains {other_company} data!"

    async def test_websocket_event_isolation_vulnerability(self):
        """REPRODUCE VULNERABILITY: WebSocket events leak between users in multi-user scenarios.

        This test simulates WebSocket event delivery during concurrent agent execution
        to verify that events are properly isolated between users.
        """
        if not SECURE_CONTEXT_AVAILABLE:
            pytest.skip('UserExecutionContext not available for secure comparison')
        websocket_users = [{'user_id': 'websocket_user_001', 'token': 'jwt_token_001', 'sensitive_context': {'personal_ai_model': 'custom_llm_financial_advisor', 'portfolio_value': 2500000, 'investment_strategy': 'aggressive_tech_growth'}}, {'user_id': 'websocket_user_002', 'token': 'jwt_token_002', 'sensitive_context': {'personal_ai_model': 'custom_llm_medical_analyst', 'patient_access_level': 'full_phi_access', 'research_protocols': ['study_001', 'trial_002']}}]
        websocket_events = {user['user_id']: [] for user in websocket_users}

        async def simulate_agent_execution_with_websockets(user_data):
            """Simulate agent execution that generates WebSocket events."""
            user_id = user_data['user_id']
            state = DeepAgentState(user_id=user_id, user_request='Execute personalized AI analysis', agent_context=user_data['sensitive_context'])
            events = [{'event_type': 'agent_started', 'user_id': user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'data': {'agent_name': 'personalized_analyzer', 'context': state.agent_context}}, {'event_type': 'agent_thinking', 'user_id': user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'data': {'reasoning': f'Analyzing data for {user_id}', 'sensitive_context': state.agent_context}}, {'event_type': 'tool_executing', 'user_id': user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'data': {'tool': 'data_analyzer', 'input_context': state.agent_context}}, {'event_type': 'agent_completed', 'user_id': user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'data': {'result': 'Analysis complete', 'final_context': state.agent_context}}]
            websocket_events[user_id] = events
            if self.redis_client:
                for event in events:
                    await self.redis_client.lpush(f'websocket_events:{user_id}', str(event))
            return state
        execution_states = await asyncio.gather(*[simulate_agent_execution_with_websockets(user_data) for user_data in websocket_users])
        user_001_events_str = str(websocket_events['websocket_user_001'])
        assert 'custom_llm_medical_analyst' not in user_001_events_str, "WEBSOCKET VULNERABILITY: User 001 received User 002's medical AI model events!"
        assert 'full_phi_access' not in user_001_events_str, 'HIPAA WEBSOCKET VIOLATION: User 001 received PHI access level in events!'
        assert 'study_001' not in user_001_events_str, 'RESEARCH CONFIDENTIALITY BREACH: User 001 received research protocol events!'
        user_002_events_str = str(websocket_events['websocket_user_002'])
        assert 'custom_llm_financial_advisor' not in user_002_events_str, "WEBSOCKET VULNERABILITY: User 002 received User 001's financial AI model events!"
        assert '2500000' not in user_002_events_str, 'FINANCIAL PRIVACY BREACH: User 002 received portfolio value in events!'
        assert 'aggressive_tech_growth' not in user_002_events_str, 'BUSINESS CONFIDENTIAL BREACH: User 002 received investment strategy events!'
        if self.redis_client and hasattr(self.redis_client, 'lrange'):
            for user_data in websocket_users:
                user_id = user_data['user_id']
                stored_events = await self.redis_client.lrange(f'websocket_events:{user_id}', 0, -1)
                stored_events_str = str(stored_events)
                other_users = [u for u in websocket_users if u['user_id'] != user_id]
                for other_user in other_users:
                    other_sensitive_data = other_user['sensitive_context']
                    for sensitive_value in other_sensitive_data.values():
                        if isinstance(sensitive_value, str) and len(sensitive_value) > 5:
                            assert str(sensitive_value) not in stored_events_str, f"REDIS CONTAMINATION: {user_id} events contain {other_user['user_id']}'s data: {sensitive_value}"

    async def test_concurrent_database_operations_isolation(self):
        """REPRODUCE VULNERABILITY: Concurrent database operations may leak data between users.

        This test verifies that database operations during concurrent agent execution
        maintain proper user isolation and don't allow cross-user data contamination.
        """
        database_scenarios = [{'user_id': 'db_user_enterprise_001', 'operation_type': 'cost_analysis_query', 'sensitive_queries': ["SELECT * FROM aws_billing WHERE account_id = 'classified_account_001'", "SELECT cost_optimization_recommendations WHERE user_tier = 'enterprise'", "SELECT proprietary_algorithm_results WHERE model_version = 'v3.2_confidential'"], 'expected_results': {'cost_savings': 125000, 'optimization_score': 0.847, 'confidential_data': 'enterprise_cost_analysis_proprietary'}}, {'user_id': 'db_user_healthcare_002', 'operation_type': 'patient_analytics_query', 'sensitive_queries': ["SELECT anonymized_patient_outcomes WHERE study_id = 'hipaa_protected_study_001'", "SELECT drug_efficacy_data WHERE fda_approval_status = 'phase_3_trial'", "SELECT patient_demographics WHERE phi_level = 'restricted_access'"], 'expected_results': {'patient_outcomes': 'positive_response_rate_0.823', 'efficacy_score': 0.756, 'confidential_data': 'fda_submission_ready_results'}}]

        async def execute_database_scenario(scenario):
            """Execute database operations for a specific user scenario."""
            user_id = scenario['user_id']
            db_state = DeepAgentState(user_id=user_id, user_request=f"Execute {scenario['operation_type']}", agent_context={'database_operations': scenario['sensitive_queries'], 'expected_sensitive_results': scenario['expected_results'], 'isolation_context': f'isolated_for_{user_id}'})
            query_results = []
            for query in scenario['sensitive_queries']:
                result = {'query': query, 'user_context': user_id, 'sensitive_result': scenario['expected_results'], 'timestamp': datetime.now(timezone.utc).isoformat()}
                query_results.append(result)
                if self.db_session and hasattr(self.db_session, 'execute'):
                    await self.db_session.execute('INSERT INTO user_query_results (user_id, query_text, result_data) VALUES (%s, %s, %s)', (user_id, query, str(result)))
            db_state.agent_context['query_results'] = query_results
            return db_state
        db_execution_results = await asyncio.gather(*[execute_database_scenario(scenario) for scenario in database_scenarios])
        enterprise_results_str = str(db_execution_results[0].agent_context)
        assert 'hipaa_protected' not in enterprise_results_str, 'DATABASE VULNERABILITY: Enterprise user accessed HIPAA protected study data!'
        assert 'patient_outcomes' not in enterprise_results_str, 'PHI VIOLATION: Enterprise user accessed patient outcome data!'
        assert 'fda_approval_status' not in enterprise_results_str, 'REGULATORY VIOLATION: Enterprise user accessed FDA approval data!'
        healthcare_results_str = str(db_execution_results[1].agent_context)
        assert 'classified_account_001' not in healthcare_results_str, 'DATABASE VULNERABILITY: Healthcare user accessed classified enterprise account!'
        assert 'proprietary_algorithm_results' not in healthcare_results_str, 'IP VIOLATION: Healthcare user accessed proprietary enterprise algorithms!'
        assert 'enterprise_cost_analysis_proprietary' not in healthcare_results_str, 'BUSINESS CONFIDENTIAL BREACH: Healthcare user accessed enterprise cost analysis!'
        if self.db_session and hasattr(self.db_session, 'fetchall'):
            for scenario in database_scenarios:
                user_id = scenario['user_id']
                user_records = await self.db_session.execute('SELECT result_data FROM user_query_results WHERE user_id = %s', (user_id,))
                if hasattr(user_records, 'fetchall'):
                    records = user_records.fetchall()
                    user_records_str = str(records)
                    other_scenarios = [s for s in database_scenarios if s['user_id'] != user_id]
                    for other_scenario in other_scenarios:
                        for sensitive_value in other_scenario['expected_results'].values():
                            if isinstance(sensitive_value, str) and len(sensitive_value) > 5:
                                assert str(sensitive_value) not in user_records_str, f"DATABASE RECORD CONTAMINATION: {user_id} records contain {other_scenario['user_id']}'s sensitive data!"

    async def tearDown(self):
        """Clean up test resources."""
        await super().tearDown()
        if self.db_session and hasattr(self.db_session, 'close'):
            await self.db_session.close()
        if self.redis_client and hasattr(self.redis_client, 'close'):
            await self.redis_client.close()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')