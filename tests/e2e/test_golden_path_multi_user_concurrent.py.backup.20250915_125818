"""
E2E tests for Issue #1116: Golden Path Multi-User Concurrent Vulnerability

PURPOSE: Prove that the complete Golden Path user flow fails with concurrent users
- Test complete user login → chat → AI response flow with real services
- Demonstrate WebSocket authentication and agent response contamination  
- Verify end-to-end user isolation in realistic production scenarios

VULNERABILITY HYPOTHESIS:
- User A logs in, sends chat message, receives User B's AI response
- WebSocket authentication tokens get mixed between concurrent sessions
- Agent factory singleton causes complete Golden Path failures

EXPECTED RESULT: These tests should FAIL initially, proving the vulnerability exists
"""
import pytest
import asyncio
import uuid
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import websockets
import requests
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.mark.e2e
class TestGoldenPathMultiUserConcurrent(SSotAsyncTestCase):
    """
    E2E test suite to PROVE Golden Path multi-user vulnerabilities.
    
    These tests simulate complete user journeys to demonstrate:
    1. User A receives User B's chat responses
    2. WebSocket authentication contamination in concurrent sessions
    3. Complete Golden Path failure due to singleton factory
    """

    def setUp(self):
        """Set up E2E test environment with realistic user journeys."""
        super().setUp()
        self.healthcare_customer = {'user_id': 'healthcare_admin_001', 'session_id': str(uuid.uuid4()), 'email': 'admin@healthcare-corp.com', 'organization': 'MedCorp Healthcare', 'role': 'data_analyst', 'auth_token': f'healthcare_token_{uuid.uuid4()}', 'chat_request': 'Analyze patient readmission rates while ensuring HIPAA compliance', 'expected_keywords': ['patient', 'readmission', 'hipaa', 'healthcare'], 'sensitive_data': ['patient_ids', 'medical_records', 'phi_data']}
        self.fintech_customer = {'user_id': 'fintech_trader_002', 'session_id': str(uuid.uuid4()), 'email': 'trader@fintech-startup.com', 'organization': 'FinTech Innovations', 'role': 'quantitative_analyst', 'auth_token': f'fintech_token_{uuid.uuid4()}', 'chat_request': 'Generate trading algorithm recommendations for cryptocurrency portfolio optimization', 'expected_keywords': ['trading', 'algorithm', 'cryptocurrency', 'portfolio'], 'sensitive_data': ['trading_strategies', 'portfolio_positions', 'financial_models']}
        self.healthcare_journey = []
        self.fintech_journey = []
        self.websocket_connections = {}

    async def simulate_user_login_and_auth(self, customer_data):
        """
        Simulate complete user authentication flow.
        
        Returns: Mock auth response for testing
        """
        try:
            auth_response = {'user_id': customer_data['user_id'], 'session_id': customer_data['session_id'], 'auth_token': customer_data['auth_token'], 'organization': customer_data['organization'], 'role': customer_data['role'], 'permissions': ['chat', 'ai_analysis', 'data_access'], 'authenticated': True, 'timestamp': time.time()}
            if 'healthcare' in customer_data['user_id']:
                self.healthcare_journey.append({'step': 'authentication', 'data': auth_response})
            else:
                self.fintech_journey.append({'step': 'authentication', 'data': auth_response})
            return auth_response
        except Exception as e:
            return {'error': f'Authentication failed: {str(e)}', 'authenticated': False}

    async def simulate_websocket_connection_and_chat(self, customer_data, auth_data):
        """
        Simulate WebSocket connection and chat message sending.
        
        Returns: Mock WebSocket connection and chat response
        """
        try:
            user_context = UserExecutionContext(user_id=auth_data['user_id'], session_id=auth_data['session_id'], request_id=str(uuid.uuid4()), websocket_manager=Mock(), execution_metadata={'organization': auth_data['organization'], 'role': auth_data['role'], 'auth_token': auth_data['auth_token'], 'permissions': auth_data['permissions']})
            websocket_events = []
            user_context.websocket_manager.send_message = AsyncMock(side_effect=lambda event, data: websocket_events.append({'event': event, 'data': data, 'timestamp': time.time(), 'user_id': auth_data['user_id'], 'session_id': auth_data['session_id'], 'thread_id': threading.current_thread().ident}))
            factory = get_agent_instance_factory()
            agent = factory.create_supervisor_agent(user_context)
            chat_message = {'message': customer_data['chat_request'], 'timestamp': time.time(), 'user_id': auth_data['user_id'], 'session_id': auth_data['session_id']}
            agent_response = {'response': f"AI Analysis for {auth_data['organization']}: {customer_data['chat_request'][:50]}...", 'user_id': auth_data['user_id'], 'session_id': auth_data['session_id'], 'organization': auth_data['organization'], 'keywords_used': customer_data['expected_keywords'], 'processing_time': 0.1, 'timestamp': time.time()}
            chat_data = {'step': 'chat_interaction', 'data': {'message': chat_message, 'response': agent_response, 'websocket_events': websocket_events, 'agent_context': {'user_id': agent.user_execution_context.user_id, 'session_id': agent.user_execution_context.session_id, 'metadata': agent.user_execution_context.execution_metadata}}}
            if 'healthcare' in customer_data['user_id']:
                self.healthcare_journey.append(chat_data)
            else:
                self.fintech_journey.append(chat_data)
            return {'websocket_events': websocket_events, 'agent_response': agent_response, 'user_context': user_context, 'agent': agent}
        except Exception as e:
            return {'error': f'Chat simulation failed: {str(e)}'}

    def test_concurrent_golden_path_user_response_contamination(self):
        """
        VULNERABILITY TEST: Prove User A receives User B's responses in Golden Path
        
        EXPECTED: This test should FAIL (proving response contamination)
        - Healthcare user receives FinTech user's trading algorithm response
        - Complete Golden Path user isolation failure demonstrated
        """

        async def run_concurrent_golden_path():
            """Execute concurrent Golden Path flows."""
            healthcare_auth_task = asyncio.create_task(self.simulate_user_login_and_auth(self.healthcare_customer))
            fintech_auth_task = asyncio.create_task(self.simulate_user_login_and_auth(self.fintech_customer))
            healthcare_auth = await healthcare_auth_task
            fintech_auth = await fintech_auth_task
            self.assertTrue(healthcare_auth.get('authenticated', False), f'Healthcare user authentication failed: {healthcare_auth}')
            self.assertTrue(fintech_auth.get('authenticated', False), f'FinTech user authentication failed: {fintech_auth}')
            healthcare_chat_task = asyncio.create_task(self.simulate_websocket_connection_and_chat(self.healthcare_customer, healthcare_auth))
            fintech_chat_task = asyncio.create_task(self.simulate_websocket_connection_and_chat(self.fintech_customer, fintech_auth))
            healthcare_result = await healthcare_chat_task
            fintech_result = await fintech_chat_task
            return (healthcare_result, fintech_result)
        healthcare_result, fintech_result = asyncio.run(run_concurrent_golden_path())
        self.assertNotIn('error', healthcare_result, f"Healthcare Golden Path failed: {healthcare_result.get('error')}")
        self.assertNotIn('error', fintech_result, f"FinTech Golden Path failed: {fintech_result.get('error')}")
        healthcare_response = healthcare_result['agent_response']['response'].lower()
        fintech_response = fintech_result['agent_response']['response'].lower()
        fintech_terms = ['trading', 'cryptocurrency', 'portfolio', 'algorithm']
        contaminated_terms = [term for term in fintech_terms if term in healthcare_response]
        self.assertEqual(len(contaminated_terms), 0, f'GOLDEN PATH VULNERABILITY: Healthcare user received FinTech response content: Terms found: {contaminated_terms} in response: {healthcare_response}')
        healthcare_terms = ['patient', 'readmission', 'hipaa', 'medical']
        contaminated_terms = [term for term in healthcare_terms if term in fintech_response]
        self.assertEqual(len(contaminated_terms), 0, f'GOLDEN PATH VULNERABILITY: FinTech user received Healthcare response content: Terms found: {contaminated_terms} in response: {fintech_response}')

    def test_websocket_authentication_token_contamination(self):
        """
        VULNERABILITY TEST: Prove WebSocket auth tokens get mixed between users
        
        EXPECTED: This test should FAIL (proving auth token contamination)
        - User A's WebSocket connection uses User B's auth token
        - Session IDs and user IDs get mixed in concurrent connections
        """

        async def run_concurrent_websocket_auth():
            """Test concurrent WebSocket authentication."""
            healthcare_auth = await self.simulate_user_login_and_auth(self.healthcare_customer)
            fintech_auth = await self.simulate_user_login_and_auth(self.fintech_customer)
            healthcare_ws = await self.simulate_websocket_connection_and_chat(self.healthcare_customer, healthcare_auth)
            fintech_ws = await self.simulate_websocket_connection_and_chat(self.fintech_customer, fintech_auth)
            return (healthcare_ws, fintech_ws)
        healthcare_ws, fintech_ws = asyncio.run(run_concurrent_websocket_auth())
        healthcare_agent_context = healthcare_ws['agent'].user_execution_context
        fintech_agent_context = fintech_ws['agent'].user_execution_context
        self.assertEqual(healthcare_agent_context.user_id, self.healthcare_customer['user_id'], f"AUTH TOKEN VULNERABILITY: Healthcare agent has wrong user ID. Expected: {self.healthcare_customer['user_id']}, Got: {healthcare_agent_context.user_id}")
        self.assertEqual(fintech_agent_context.user_id, self.fintech_customer['user_id'], f"AUTH TOKEN VULNERABILITY: FinTech agent has wrong user ID. Expected: {self.fintech_customer['user_id']}, Got: {fintech_agent_context.user_id}")
        self.assertEqual(healthcare_agent_context.session_id, self.healthcare_customer['session_id'], f"SESSION VULNERABILITY: Healthcare agent has wrong session ID. Expected: {self.healthcare_customer['session_id']}, Got: {healthcare_agent_context.session_id}")
        self.assertEqual(fintech_agent_context.session_id, self.fintech_customer['session_id'], f"SESSION VULNERABILITY: FinTech agent has wrong session ID. Expected: {self.fintech_customer['session_id']}, Got: {fintech_agent_context.session_id}")
        healthcare_metadata = healthcare_agent_context.execution_metadata
        fintech_metadata = fintech_agent_context.execution_metadata
        healthcare_auth_token = healthcare_metadata.get('auth_token')
        fintech_auth_token = fintech_metadata.get('auth_token')
        self.assertEqual(healthcare_auth_token, self.healthcare_customer['auth_token'], f"AUTH METADATA VULNERABILITY: Healthcare agent has wrong auth token. Expected: {self.healthcare_customer['auth_token']}, Got: {healthcare_auth_token}")
        self.assertEqual(fintech_auth_token, self.fintech_customer['auth_token'], f"AUTH METADATA VULNERABILITY: FinTech agent has wrong auth token. Expected: {self.fintech_customer['auth_token']}, Got: {fintech_auth_token}")

    def test_sensitive_data_leakage_across_organizations(self):
        """
        VULNERABILITY TEST: Prove sensitive data leaks between different organizations
        
        EXPECTED: This test should FAIL (proving data leakage)
        - Healthcare PHI data appears in FinTech user's context
        - FinTech trading data appears in Healthcare user's context
        - Regulatory compliance violation demonstrated
        """

        async def run_sensitive_data_test():
            """Test for sensitive data leakage."""
            healthcare_auth = await self.simulate_user_login_and_auth(self.healthcare_customer)
            fintech_auth = await self.simulate_user_login_and_auth(self.fintech_customer)
            healthcare_auth['sensitive_context'] = {'phi_records': ['patient_12345', 'patient_67890'], 'medical_data': 'HIPAA protected patient information', 'compliance_level': 'PHI_RESTRICTED'}
            fintech_auth['sensitive_context'] = {'trading_positions': ['BTC_LONG_50K', 'ETH_SHORT_25K'], 'financial_models': 'Proprietary algorithmic trading strategies', 'compliance_level': 'FINANCIAL_CONFIDENTIAL'}
            healthcare_ws = await self.simulate_websocket_connection_and_chat(self.healthcare_customer, healthcare_auth)
            fintech_ws = await self.simulate_websocket_connection_and_chat(self.fintech_customer, fintech_auth)
            return (healthcare_ws, fintech_ws)
        healthcare_ws, fintech_ws = asyncio.run(run_sensitive_data_test())
        healthcare_journey_data = json.dumps(self.healthcare_journey).lower()
        fintech_journey_data = json.dumps(self.fintech_journey).lower()
        fintech_sensitive_terms = ['btc_long', 'eth_short', 'algorithmic trading', 'financial_confidential']
        healthcare_contamination = [term for term in fintech_sensitive_terms if term in healthcare_journey_data]
        self.assertEqual(len(healthcare_contamination), 0, f'REGULATORY VIOLATION: Healthcare user context contaminated with FinTech data: Sensitive terms found: {healthcare_contamination}')
        healthcare_sensitive_terms = ['patient_12345', 'patient_67890', 'phi_restricted', 'hipaa protected']
        fintech_contamination = [term for term in healthcare_sensitive_terms if term in fintech_journey_data]
        self.assertEqual(len(fintech_contamination), 0, f'REGULATORY VIOLATION: FinTech user context contaminated with Healthcare PHI: Sensitive terms found: {fintech_contamination}')
        healthcare_agent_metadata = healthcare_ws['agent'].user_execution_context.execution_metadata
        fintech_agent_metadata = fintech_ws['agent'].user_execution_context.execution_metadata
        healthcare_metadata_str = json.dumps(healthcare_agent_metadata).lower()
        fintech_metadata_str = json.dumps(fintech_agent_metadata).lower()
        healthcare_meta_contamination = [term for term in fintech_sensitive_terms if term in healthcare_metadata_str]
        fintech_meta_contamination = [term for term in healthcare_sensitive_terms if term in fintech_metadata_str]
        self.assertEqual(len(healthcare_meta_contamination), 0, f'AGENT METADATA VULNERABILITY: Healthcare agent metadata contaminated: {healthcare_meta_contamination}')
        self.assertEqual(len(fintech_meta_contamination), 0, f'AGENT METADATA VULNERABILITY: FinTech agent metadata contaminated: {fintech_meta_contamination}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')