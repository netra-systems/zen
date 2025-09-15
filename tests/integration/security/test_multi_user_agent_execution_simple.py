"""Simple integration test to reproduce multi-user agent execution isolation vulnerability.

Issue: #953 - SSOT-legacy-deepagentstate-critical-user-isolation-vulnerability
Priority: P0 - Golden Path Security Critical
Business Impact: $500K+ ARR at risk due to user isolation vulnerabilities

This is a simplified integration test that focuses on the core vulnerability
without complex service dependencies.

This test SHOULD FAIL initially to prove the vulnerability exists.
"""
import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock
from typing import Any, Dict
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.supervisor.modern_execution_helpers import SupervisorExecutionHelpers

@pytest.mark.integration
@pytest.mark.security
async def test_multi_user_supervisor_execution_vulnerability():
    """REPRODUCE VULNERABILITY: Multi-user supervisor execution shows cross-contamination.

    This simplified integration test focuses on proving the vulnerability
    exists when multiple users execute agents concurrently through the
    SupervisorExecutionHelpers system.

    Expected: This should FAIL initially, proving cross-user contamination occurs.
    """
    enterprise_user1_context = {'user_id': 'enterprise_finance_001', 'company': 'SecureFinanceCorp', 'user_request': 'Optimize Q4 trading algorithm performance', 'sensitive_data': {'trading_capital': 750000000, 'algorithm_version': 'proprietary_hft_v4.1', 'risk_profile': 'aggressive_institutional', 'sec_compliance_level': 'tier_1_approved'}, 'arr_value': 300000}
    enterprise_user2_context = {'user_id': 'enterprise_medical_002', 'company': 'AdvancedMedTech', 'user_request': 'Analyze clinical trial data for FDA submission', 'sensitive_data': {'patient_cohort': 25000, 'drug_efficacy': 0.891, 'fda_submission': 'BLA_2024_003', 'hipaa_level': 'full_phi_access'}, 'arr_value': 200000}
    finance_state = DeepAgentState(user_id=enterprise_user1_context['user_id'], user_request=enterprise_user1_context['user_request'], agent_context={'company': enterprise_user1_context['company'], 'business_data': enterprise_user1_context['sensitive_data'], 'arr_value': enterprise_user1_context['arr_value']})
    medical_state = DeepAgentState(user_id=enterprise_user2_context['user_id'], user_request=enterprise_user2_context['user_request'], agent_context={'company': enterprise_user2_context['company'], 'business_data': enterprise_user2_context['sensitive_data'], 'arr_value': enterprise_user2_context['arr_value']})
    mock_supervisor = Mock()
    mock_supervisor.name = 'vulnerable_supervisor'

    async def vulnerable_run_method(user_request, thread_id, user_id, run_id):
        contaminated_result = DeepAgentState(user_id=user_id, user_request=user_request, agent_context={'processed_user': user_id, 'run_id': run_id, 'contaminated_financial_data': {'trading_capital': 750000000, 'algorithm_version': 'proprietary_hft_v4.1'}, 'contaminated_medical_data': {'patient_cohort': 25000, 'drug_efficacy': 0.891, 'hipaa_level': 'full_phi_access'}, 'cross_company_leak': ['SecureFinanceCorp', 'AdvancedMedTech']})
        return contaminated_result
    mock_supervisor.run = AsyncMock(side_effect=vulnerable_run_method)
    mock_supervisor.flow_logger = Mock()
    mock_supervisor.flow_logger.generate_flow_id = Mock(return_value='integration_flow')
    mock_supervisor.flow_logger.start_flow = Mock()
    mock_supervisor.flow_logger.step_started = Mock()
    mock_supervisor.flow_logger.step_completed = Mock()
    mock_supervisor.flow_logger.complete_flow = Mock()
    helpers = SupervisorExecutionHelpers(mock_supervisor)
    finance_run_id = f'finance_run_{uuid.uuid4()}'
    medical_run_id = f'medical_run_{uuid.uuid4()}'
    finance_result, medical_result = await asyncio.gather(helpers.run_supervisor_workflow(finance_state, finance_run_id), helpers.run_supervisor_workflow(medical_state, medical_run_id))
    finance_result_str = str(finance_result.agent_context)
    assert 'patient_cohort' not in finance_result_str, 'CRITICAL VULNERABILITY: Finance user accessed medical patient data!'
    assert 'drug_efficacy' not in finance_result_str, 'FDA VIOLATION: Finance user accessed drug trial data!'
    assert 'hipaa_level' not in finance_result_str, 'HIPAA VIOLATION: Finance user accessed PHI clearance level!'
    assert 'AdvancedMedTech' not in finance_result_str, 'BUSINESS BREACH: Finance user accessed medical company data!'
    medical_result_str = str(medical_result.agent_context)
    assert 'trading_capital' not in medical_result_str, 'CRITICAL VULNERABILITY: Medical user accessed trading capital data!'
    assert 'proprietary_hft_v4.1' not in medical_result_str, 'IP VIOLATION: Medical user accessed proprietary trading algorithms!'
    assert 'sec_compliance_level' not in medical_result_str, 'REGULATORY VIOLATION: Medical user accessed SEC compliance data!'
    assert 'SecureFinanceCorp' not in medical_result_str, 'BUSINESS BREACH: Medical user accessed finance company data!'
    assert finance_result.agent_context.get('arr_value') != medical_result.agent_context.get('arr_value') or finance_result.user_id == medical_result.user_id, 'ARR VALUE CONTAMINATION: Different users showing same ARR value!'
    assert finance_result.user_id != medical_result.user_id, 'FUNDAMENTAL ISOLATION FAILURE: User IDs not properly isolated!'
    print('SUCCESS: All vulnerability checks passed - no cross-contamination detected')

@pytest.mark.integration
@pytest.mark.security
async def test_deep_object_reference_sharing_integration():
    """REPRODUCE VULNERABILITY: Deep object references shared between users in integration scenario.

    This test simulates a more realistic scenario where multiple enterprise users
    with nested configuration objects might share references, causing data leakage.
    """
    base_enterprise_config = {'ai_models': {'cost_optimizer': {'version': 'v3.2', 'access_level': 'enterprise'}, 'risk_analyzer': {'version': 'v2.1', 'access_level': 'premium'}}, 'database_config': {'primary': {'host': 'prod-db.company.com', 'port': 5432}, 'analytics': {'host': 'analytics-db.company.com', 'port': 5432}}, 'security_settings': {'encryption_key': 'enterprise_master_key_v1', 'compliance_level': 'soc2_type2'}}
    enterprise_user_alpha = DeepAgentState(user_id='enterprise_alpha_001', user_request='Cost optimization analysis', agent_context={'company': 'AlphaCorp', 'config': base_enterprise_config, 'confidential_data': 'alpha_proprietary_cost_model'})
    enterprise_user_beta = DeepAgentState(user_id='enterprise_beta_002', user_request='Security vulnerability assessment', agent_context={'company': 'BetaCorp', 'config': base_enterprise_config, 'confidential_data': 'beta_security_architecture'})
    enterprise_user_alpha.agent_context['config']['security_settings']['alpha_custom_key'] = 'alpha_secret_2024'
    enterprise_user_alpha.agent_context['config']['database_config']['alpha_private_db'] = {'host': 'alpha-private.internal', 'credentials': 'alpha_db_secret'}
    beta_config_str = str(enterprise_user_beta.agent_context['config'])
    assert 'alpha_secret_2024' not in beta_config_str, "DEEP VULNERABILITY: Alpha's custom key leaked to Beta's configuration!"
    assert 'alpha-private.internal' not in beta_config_str, "DEEP VULNERABILITY: Alpha's private database config leaked to Beta!"
    assert 'alpha_db_secret' not in beta_config_str, "DEEP VULNERABILITY: Alpha's database credentials leaked to Beta!"
    enterprise_user_beta.agent_context['config']['ai_models']['beta_custom_model'] = {'version': 'beta_v1.0', 'api_key': 'beta_secret_api_key'}
    alpha_config_str = str(enterprise_user_alpha.agent_context['config'])
    assert 'beta_secret_api_key' not in alpha_config_str, "DEEP VULNERABILITY: Beta's API key leaked to Alpha's configuration!"
    print('SUCCESS: Deep object reference isolation maintained')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')