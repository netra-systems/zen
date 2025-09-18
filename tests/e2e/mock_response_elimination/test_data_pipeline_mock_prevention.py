"""
Data Pipeline Mock Response Prevention Tests

Business Value Justification (BVJ):
- Segment: All segments, especially Enterprise (100K+ ARR)
- Business Goal: Ensure data integrity - no fabricated analytics reach users  
- Value Impact: Prevent business decisions based on fake data
- Strategic Impact: Platform credibility depends on authentic data delivery

CRITICAL: These tests are designed to FAIL initially to prove that the 
UnifiedDataAgent._generate_fallback_data() method can deliver fabricated
metrics to users as if they were real analytics.

Test Status: FAILING (Expected) - Proves fake data can reach users
Fix Required: Replace fallback data with proper error handling
"""
import asyncio
import pytest
import json
import logging
import time
from typing import Dict, List, Any, Optional
import aiohttp
import websockets
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID
logger = logging.getLogger(__name__)

class DataPipelineMockPreventionTests(BaseE2ETest):
    """
    FAILING TESTS: Prove data pipeline can return fabricated data to users.
    
    These tests target the UnifiedDataAgent._generate_fallback_data() method
    that returns mock analytics when real data access fails.
    """

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_data_agent_prevents_mock_data_delivery(self, real_services_fixture):
        """
        FAILING TEST: Proves data agent returns fabricated metrics.
        
        Business Value: Analytics queries for Enterprise customers (100K+ ARR)
        must NEVER return fake data that could impact business decisions.
        
        Expected Failure: Currently calls _generate_fallback_data() 
        which returns fabricated metrics as if they were real.
        
        Required Fix: Clear error or retry, NOT mock analytics data.
        """
        auth_helper = E2EAuthHelper()
        user = await auth_helper.create_authenticated_user(email='data.analyst@enterprise.com', subscription_tier='enterprise', metadata={'role': 'data_analyst', 'arr_value': 150000, 'data_access_level': 'full'})
        backend_url = real_services_fixture['backend_url']
        ws_url = backend_url.replace('http', 'ws') + '/ws'
        async with WebSocketTestClient(url=ws_url, auth_token=user.jwt_token) as websocket_client:
            analytics_query = {'type': 'agent_request', 'agent': 'unified_data_agent', 'message': 'Generate comprehensive analytics report for our cloud infrastructure costs. Need accurate metrics for: monthly spend trends, service utilization rates, cost optimization opportunities, and performance benchmarks.', 'context': {'user_id': str(user.user_id), 'subscription': 'enterprise', 'data_request': True, 'metrics_needed': ['monthly_costs', 'utilization_rates', 'optimization_savings', 'performance_metrics']}, 'request_id': f'analytics_data_test_{int(time.time())}'}
            await websocket_client.send_json(analytics_query)
            events = []
            timeout = 45
            async for event in websocket_client.receive_events(timeout=timeout):
                events.append(event)
                logger.info(f"Data agent event: {event.get('type', 'unknown')}")
                if event.get('type') == 'agent_completed':
                    break
            assert len(events) > 0, 'No response to analytics data request'
            completion_event = None
            for event in reversed(events):
                if event.get('type') == 'agent_completed':
                    completion_event = event
                    break
            assert completion_event is not None, 'Analytics request did not complete'
            response_data = completion_event.get('data', {})
            response_content = response_data.get('response') or response_data.get('content', '')
            analytics_data = response_data.get('analytics_data', {})
            metrics_data = response_data.get('metrics', [])
            if analytics_data or metrics_data or any((indicator in response_content.lower() for indicator in ['$', 'cost', 'savings', 'metrics', 'data'])):
                fallback_data_indicators = ['sample_data', 'fallback_data', 'mock_metrics', 'generated_data', 'placeholder', 'example_value', 'test_data']
                for indicator in fallback_data_indicators:
                    assert indicator not in response_content.lower(), f"MOCK DATA DETECTED: Found '{indicator}' in analytics response. Users should never receive fabricated analytics data. Response excerpt: {response_content[:300]}..."
                if analytics_data:
                    analytics_str = json.dumps(analytics_data).lower()
                    for indicator in fallback_data_indicators:
                        assert indicator not in analytics_str, f"MOCK DATA IN ANALYTICS STRUCTURE: Found '{indicator}' in analytics_data. Structured data appears fabricated. Analytics data: {analytics_data}"
                if metrics_data:
                    metrics_str = json.dumps(metrics_data).lower()
                    for indicator in fallback_data_indicators:
                        assert indicator not in metrics_str, f"MOCK DATA IN METRICS: Found '{indicator}' in metrics data. Metrics appear to be fabricated fallback data. Metrics: {(metrics_data[:3] if isinstance(metrics_data, list) else metrics_data)}"
                if analytics_data:
                    self._validate_data_authenticity(analytics_data, 'analytics_data')
                if isinstance(metrics_data, list):
                    for i, metric in enumerate(metrics_data[:5]):
                        self._validate_data_authenticity(metric, f'metric_{i}')
            else:
                no_data_acceptable_messages = ['no data available', 'data access unavailable', 'service temporarily unavailable', 'please try again later', 'data connection failed']
                has_acceptable_message = any((msg in response_content.lower() for msg in no_data_acceptable_messages))
                assert has_acceptable_message, f'No analytics data provided but no clear explanation given. Users should know why no data is available. Response: {response_content[:200]}...'

    def _validate_data_authenticity(self, data: Any, data_source: str) -> None:
        """
        Helper to validate that data appears authentic, not generated.
        
        Mock data often has suspicious patterns:
        - Round numbers (100, 1000, 50.0)
        - Sequential patterns (1, 2, 3, 4)
        - Too-perfect percentages (exactly 50%, 75%)
        - Repeated values
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    if 'cost' in key.lower() or 'price' in key.lower() or 'spend' in key.lower():
                        if value > 100 and value % 100 == 0:
                            logger.warning(f'Suspicious round cost value: {key}={value}')
                        mock_cost_values = [100, 500, 1000, 5000, 10000, 50000]
                        assert value not in mock_cost_values, f'SUSPICIOUS MOCK COST: {key}={value} appears to be common mock data value in {data_source}'
                    if 'percent' in key.lower() or 'rate' in key.lower():
                        if value in [25.0, 50.0, 75.0, 100.0]:
                            logger.warning(f'Suspicious round percentage: {key}={value}')
        elif isinstance(data, list) and len(data) > 2:
            numeric_values = [item for item in data if isinstance(item, (int, float))]
            if len(numeric_values) >= 3:
                differences = [numeric_values[i + 1] - numeric_values[i] for i in range(len(numeric_values) - 1)]
                if len(set(differences)) == 1 and differences[0] in [1, 10, 100]:
                    assert False, f'SEQUENTIAL MOCK DATA PATTERN: Values in {data_source} appear to be in perfect sequence: {numeric_values[:5]}... This suggests generated mock data.'

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_cost_optimization_authentic_data_only(self, real_services_fixture):
        """
        FAILING TEST: Cost optimization can return fabricated savings data.
        
        Business Value: Users making financial decisions based on cost analysis
        must NEVER receive fabricated data that could mislead business strategy.
        
        Expected Failure: May return mock cost savings that mislead users.
        """
        auth_helper = E2EAuthHelper()
        user = await auth_helper.create_authenticated_user(email='cfo@company.com', subscription_tier='enterprise', metadata={'role': 'cfo', 'financial_authority': True, 'arr_value': 250000})
        backend_url = real_services_fixture['backend_url']
        ws_url = backend_url.replace('http', 'ws') + '/ws'
        async with WebSocketTestClient(url=ws_url, auth_token=user.jwt_token) as websocket_client:
            cost_query = {'type': 'agent_request', 'agent': 'cost_optimizer', 'message': 'Urgent: Analyze potential cost savings for Q4 budget planning. Board needs accurate savings projections for infrastructure optimization. Include specific recommendations with dollar amounts.', 'context': {'user_id': str(user.user_id), 'subscription': 'enterprise', 'urgency': 'high', 'financial_impact': True, 'quarterly_analysis': True}, 'request_id': f'cost_optimization_test_{int(time.time())}'}
            await websocket_client.send_json(cost_query)
            events = []
            async for event in websocket_client.receive_events(timeout=60):
                events.append(event)
                if event.get('type') == 'agent_completed':
                    break
            assert len(events) > 0, 'No response to critical cost optimization query'
            completion_event = None
            for event in reversed(events):
                if event.get('type') == 'agent_completed':
                    completion_event = event
                    break
            assert completion_event is not None, 'Cost optimization did not complete'
            response_data = completion_event.get('data', {})
            response_content = response_data.get('response') or response_data.get('content', '')
            has_cost_data = any((indicator in response_content.lower() for indicator in ['$', 'savings', 'cost', 'budget', 'optimization', 'dollar', 'money', 'financial', 'reduce']))
            if has_cost_data:
                mock_financial_patterns = ['sample savings', 'example cost', 'placeholder amount', 'mock financial', 'generated savings', 'fallback cost', 'default optimization']
                for pattern in mock_financial_patterns:
                    assert pattern not in response_content.lower(), f"MOCK FINANCIAL DATA DETECTED: Found '{pattern}' in cost analysis. CFO/financial decisions cannot be based on fabricated data. Response excerpt: {response_content[:300]}..."
                import re
                dollar_amounts = re.findall('\\$[\\d,]+\\.?\\d*', response_content)
                for amount in dollar_amounts:
                    numeric_amount = amount.replace('$', '').replace(',', '')
                    try:
                        value = float(numeric_amount)
                        mock_amounts = [1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000]
                        if value in mock_amounts:
                            logger.warning(f'Suspicious perfect savings amount: {amount}')
                        if value >= 10000 and value % 10000 == 0:
                            assert False, f'SUSPICIOUS SAVINGS AMOUNT: {amount} appears to be fabricated mock data - real savings rarely end in perfect zeros'
                    except ValueError:
                        continue
                cost_data = response_data.get('cost_analysis', {})
                savings_data = response_data.get('savings', {})
                if cost_data:
                    self._validate_financial_data_authenticity(cost_data, 'cost_analysis')
                if savings_data:
                    self._validate_financial_data_authenticity(savings_data, 'savings')
            else:
                financial_unavailable_explanations = ['cost data unavailable', 'financial analysis not available', 'insufficient data for cost analysis', 'please contact support for financial analysis']
                has_explanation = any((explanation in response_content.lower() for explanation in financial_unavailable_explanations))
                assert has_explanation, f'No cost analysis provided but no explanation given to CFO. Financial stakeholders need clear reason why analysis unavailable. Response: {response_content[:200]}...'

    def _validate_financial_data_authenticity(self, financial_data: Dict, data_type: str) -> None:
        """Validate that financial data appears authentic, not mock-generated."""
        for key, value in financial_data.items():
            if isinstance(value, (int, float)):
                if key.lower() in ['savings', 'cost', 'amount', 'total', 'spend']:
                    if value >= 1000:
                        if value % 1000 == 0:
                            logger.warning(f'Suspicious round financial value: {key}={value}')
                        common_mock_values = [1000, 2500, 5000, 7500, 10000, 15000, 20000, 25000, 50000, 100000, 250000, 500000]
                        assert value not in common_mock_values, f'MOCK FINANCIAL VALUE DETECTED: {key}={value} in {data_type} matches common mock financial data pattern'

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_enterprise_analytics_dashboard_data_integrity(self, real_services_fixture):
        """
        FAILING TEST: Enterprise dashboard analytics may include fabricated data.
        
        Business Value: Enterprise customers (200K+ ARR) rely on dashboard
        analytics for strategic decisions. Fabricated data could cause 
        significant business harm.
        """
        auth_helper = E2EAuthHelper()
        user = await auth_helper.create_authenticated_user(email='analytics.director@enterprise.com', subscription_tier='enterprise', metadata={'role': 'analytics_director', 'dashboard_access': 'full', 'arr_value': 300000, 'strategic_user': True})
        backend_url = real_services_fixture['backend_url']
        ws_url = backend_url.replace('http', 'ws') + '/ws'
        async with WebSocketTestClient(url=ws_url, auth_token=user.jwt_token) as websocket_client:
            dashboard_query = {'type': 'agent_request', 'agent': 'unified_data_agent', 'message': 'Generate executive dashboard with key performance indicators: monthly active users, revenue trends, cost per acquisition, infrastructure costs, optimization opportunities, and growth metrics.', 'context': {'user_id': str(user.user_id), 'subscription': 'enterprise', 'dashboard_request': True, 'executive_level': True, 'kpi_categories': ['user_metrics', 'revenue_metrics', 'cost_metrics', 'growth_metrics']}, 'request_id': f'dashboard_data_test_{int(time.time())}'}
            await websocket_client.send_json(dashboard_query)
            events = []
            async for event in websocket_client.receive_events(timeout=60):
                events.append(event)
                if event.get('type') == 'agent_completed':
                    break
            assert len(events) > 0, 'No dashboard data response'
            completion_event = None
            for event in reversed(events):
                if event.get('type') == 'agent_completed':
                    completion_event = event
                    break
            assert completion_event is not None, 'Dashboard request did not complete'
            response_data = completion_event.get('data', {})
            response_content = response_data.get('response') or response_data.get('content', '')
            dashboard_data = response_data.get('dashboard_data', {})
            kpi_data = response_data.get('kpis', [])
            metrics = response_data.get('metrics', {})
            has_dashboard_data = bool(dashboard_data or kpi_data or metrics or any((indicator in response_content.lower() for indicator in ['users', 'revenue', 'growth', 'kpi', 'metric', 'performance', 'dashboard', 'analytics'])))
            if has_dashboard_data:
                enterprise_forbidden_data_patterns = ['sample_kpi', 'mock_metric', 'example_revenue', 'placeholder_users', 'generated_growth', 'fallback_dashboard', 'default_analytics', 'demo_data']
                for pattern in enterprise_forbidden_data_patterns:
                    assert pattern not in response_content.lower(), f"MOCK DASHBOARD DATA: Found '{pattern}' in enterprise dashboard. $300K ARR customer cannot receive fabricated KPIs. Response excerpt: {response_content[:300]}..."
                if dashboard_data:
                    dashboard_str = json.dumps(dashboard_data).lower()
                    for pattern in enterprise_forbidden_data_patterns:
                        assert pattern not in dashboard_str, f"MOCK DATA IN DASHBOARD STRUCTURE: Found '{pattern}' in dashboard_data for enterprise customer"
                if kpi_data:
                    for i, kpi in enumerate(kpi_data[:5]):
                        if isinstance(kpi, dict):
                            self._validate_kpi_authenticity(kpi, f'kpi_{i}')
                if metrics:
                    self._validate_dashboard_metrics_authenticity(metrics)
            else:
                enterprise_explanations = ['dashboard data unavailable', 'analytics temporarily offline', 'contact enterprise support', 'data aggregation in progress']
                has_enterprise_explanation = any((explanation in response_content.lower() for explanation in enterprise_explanations))
                assert has_enterprise_explanation, f'No dashboard data provided to enterprise customer without explanation. $300K ARR customer needs clear reason for data unavailability. Response: {response_content[:200]}...'

    def _validate_kpi_authenticity(self, kpi: Dict, kpi_id: str) -> None:
        """Validate KPI data appears authentic for enterprise dashboard."""
        kpi_name = kpi.get('name', '').lower()
        kpi_value = kpi.get('value')
        if isinstance(kpi_value, (int, float)):
            if 'users' in kpi_name or 'customers' in kpi_name:
                mock_user_counts = [100, 500, 1000, 5000, 10000, 50000, 100000]
                assert kpi_value not in mock_user_counts, f'MOCK USER KPI: {kpi_name} = {kpi_value} appears to be common mock user count in {kpi_id}'
            if 'revenue' in kpi_name or 'sales' in kpi_name:
                if kpi_value >= 10000 and kpi_value % 10000 == 0:
                    assert False, f'SUSPICIOUS REVENUE KPI: {kpi_name} = {kpi_value} is suspiciously round for real revenue data'
            if 'growth' in kpi_name or 'percent' in kpi_name:
                perfect_percentages = [10.0, 15.0, 20.0, 25.0, 50.0, 75.0, 100.0]
                if kpi_value in perfect_percentages:
                    logger.warning(f'Perfect growth percentage may be mock: {kpi_name} = {kpi_value}%')

    def _validate_dashboard_metrics_authenticity(self, metrics: Dict) -> None:
        """Validate dashboard metrics appear authentic, not generated."""
        for metric_key, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)):
                if 'cost' in metric_key.lower():
                    if metric_value >= 1000 and metric_value % 1000 == 0:
                        logger.warning(f'Round cost metric may be mock: {metric_key} = {metric_value}')
                if 'performance' in metric_key.lower() or 'latency' in metric_key.lower():
                    if metric_value in [100, 200, 500, 1000]:
                        logger.warning(f'Perfect performance metric: {metric_key} = {metric_value}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')