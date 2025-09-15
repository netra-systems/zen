"""
E2E Tests for Agent Response Quality Validation - Golden Path Business Value

MISSION CRITICAL: Validates that agents return substantive, problem-solving responses
that deliver real business value to users. This tests the core chat functionality
representing 90% of platform business value ($500K+ ARR).

Business Value Justification (BVJ):
- Segment: All Users (Free/Early/Mid/Enterprise)
- Business Goal: Customer Satisfaction & Platform Revenue Protection
- Value Impact: Validates AI responses provide actionable insights and real solutions
- Strategic Impact: $500K+ ARR depends on quality AI chat interactions

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- REAL AUTH: JWT tokens via staging auth service
- REAL WEBSOCKETS: wss:// connections to staging backend
- REAL AGENTS: All agent types with complete LLM integration
- REAL LLMS: Actual LLM calls for authentic response quality validation
- BUSINESS FOCUS: Test substance and value of responses, not just technical delivery

CRITICAL: These tests must fail properly when response quality degrades.
No mocking, bypassing, or accepting low-quality responses allowed.

GitHub Issue: #861 Agent Golden Path Messages Test Creation - STEP 1
Coverage Target: 0.9% → 25% improvement (Priority Scenario #1)
"""
import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import httpx
import re
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper

@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.mission_critical
class TestAgentResponseQualityE2E(SSotAsyncTestCase):
    """
    E2E tests for validating agent response quality and business value delivery.

    Tests the core business value: AI agents must provide substantive,
    problem-solving responses that deliver real value to users.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment configuration and dependencies."""
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        if not is_staging_available():
            pytest.skip('Staging environment not available')
        cls.auth_helper = E2EAuthHelper(environment='staging')
        cls.websocket_helper = WebSocketTestHelper()
        cls.test_user_id = f'quality_test_user_{int(time.time())}'
        cls.test_user_email = f'quality_test_{int(time.time())}@netra-testing.ai'
        cls.logger.info(f'Agent response quality E2E tests initialized for staging')

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.thread_id = f'quality_test_{int(time.time())}'
        self.run_id = f'run_{self.thread_id}'
        self.access_token = self.__class__.auth_helper.create_test_jwt_token(user_id=self.__class__.test_user_id, email=self.__class__.test_user_email, exp_minutes=60)
        self.logger.info(f'Quality test setup complete - thread_id: {self.thread_id}')

    async def _establish_websocket_connection(self) -> websockets.ServerConnection:
        """Establish WebSocket connection to staging with proper auth headers."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f'Bearer {self.access_token}', 'X-Environment': 'staging', 'X-Test-Suite': 'agent-quality-e2e'}, ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=20.0)
        return websocket

    async def _send_agent_request(self, websocket, agent_type: str, message: str, context: Dict=None) -> List[Dict]:
        """Send agent request and collect all events until completion."""
        request_message = {'type': 'agent_request', 'agent': agent_type, 'message': message, 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': self.__class__.test_user_id, 'context': context or {}}
        await websocket.send(json.dumps(request_message))
        events = []
        response_timeout = 90.0
        collection_start = time.time()
        while time.time() - collection_start < response_timeout:
            try:
                event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                event = json.loads(event_data)
                events.append(event)
                event_type = event.get('type', 'unknown')
                if event_type == 'agent_completed':
                    break
                elif event_type in ['error', 'agent_error']:
                    raise AssertionError(f'Agent processing error: {event}')
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError as e:
                self.logger.warning(f'Failed to parse WebSocket message: {e}')
                continue
        return events

    def _analyze_response_quality(self, events: List[Dict]) -> Tuple[bool, Dict[str, Any]]:
        """Analyze response quality and extract quality metrics."""
        final_response = None
        for event in reversed(events):
            if event.get('type') == 'agent_completed':
                final_response = event
                break
        if not final_response:
            return (False, {'error': 'No agent_completed event found'})
        response_data = final_response.get('data', {})
        result = response_data.get('result', {})
        if isinstance(result, dict):
            response_text = result.get('response', str(result))
        else:
            response_text = str(result)
        metrics = {'response_length': len(response_text), 'word_count': len(response_text.split()), 'has_actionable_content': False, 'has_specific_recommendations': False, 'has_numerical_insights': False, 'addresses_user_question': False, 'response_text_sample': response_text[:300] + '...' if len(response_text) > 300 else response_text}
        response_lower = response_text.lower()
        actionable_indicators = ['recommend', 'suggest', 'should', 'can', 'try', 'implement', 'reduce', 'optimize', 'improve', 'increase', 'decrease']
        metrics['has_actionable_content'] = any((indicator in response_lower for indicator in actionable_indicators))
        metrics['has_specific_recommendations'] = bool(re.search('\\d+[.)]\\s', response_text) or re.search('•\\s|[-*]\\s', response_text) or 'step ' in response_lower or ('first' in response_lower) or ('second' in response_lower))
        metrics['has_numerical_insights'] = bool(re.search('\\$[\\d,]+|\\d+%|\\d+\\.\\d+|\\d+x|by \\d+', response_text))
        quality_score = 0
        if metrics['response_length'] >= 100:
            quality_score += 1
        if metrics['has_actionable_content']:
            quality_score += 1
        if metrics['has_specific_recommendations']:
            quality_score += 1
        if metrics['has_numerical_insights']:
            quality_score += 1
        metrics['quality_score'] = quality_score
        metrics['quality_grade'] = 'A' if quality_score >= 3 else 'B' if quality_score >= 2 else 'C' if quality_score >= 1 else 'F'
        is_high_quality = quality_score >= 2
        return (is_high_quality, metrics)

    async def test_supervisor_agent_quality_comprehensive(self):
        """
        Test supervisor agent response quality for comprehensive business questions.

        BUSINESS VALIDATION: Supervisor agents must orchestrate high-quality responses
        that demonstrate understanding and provide actionable business insights.

        Quality Requirements:
        1. Response length > 200 characters (substantive)
        2. Contains actionable recommendations
        3. Addresses specific user questions
        4. Provides structured, helpful guidance
        5. Shows understanding of business context

        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes - Complete staging GCP stack with real LLM
        STATUS: Should PASS - Core supervisor functionality
        """
        self.logger.info('🎯 Testing supervisor agent comprehensive response quality')
        websocket = await self._establish_websocket_connection()
        try:
            business_question = "I'm the CEO of a 500-person company spending $50,000/month on AI tools including OpenAI, Claude, and internal ML infrastructure. Our engineering team reports 40% of costs are from redundant API calls and poor prompt optimization. We need to reduce costs by 35% while maintaining AI capabilities for our product. Provide a comprehensive optimization strategy with specific, actionable steps."
            events = await self._send_agent_request(websocket, 'supervisor_agent', business_question, {'test_scenario': 'comprehensive_business_optimization', 'expected_quality': 'high', 'business_context': 'enterprise_ceo_inquiry'})
            is_quality, metrics = self._analyze_response_quality(events)
            self.logger.info(f'📊 Supervisor Agent Quality Metrics:')
            self.logger.info(f"   Response Length: {metrics['response_length']} chars")
            self.logger.info(f"   Word Count: {metrics['word_count']} words")
            self.logger.info(f"   Quality Score: {metrics['quality_score']}/4")
            self.logger.info(f"   Quality Grade: {metrics['quality_grade']}")
            self.logger.info(f"   Has Actionable Content: {metrics['has_actionable_content']}")
            self.logger.info(f"   Has Specific Recommendations: {metrics['has_specific_recommendations']}")
            self.logger.info(f"   Has Numerical Insights: {metrics['has_numerical_insights']}")
            assert is_quality, f"Supervisor agent response quality insufficient. Got grade {metrics['quality_grade']} (need B+ minimum). Metrics: {metrics}"
            assert metrics['response_length'] >= 200, f"Response too short for comprehensive question: {metrics['response_length']} chars (minimum 200 for business-level inquiries)"
            assert metrics['has_actionable_content'], f"Response lacks actionable recommendations. Business users need specific guidance. Sample: {metrics['response_text_sample']}"
            response_text = metrics['response_text_sample']
            key_elements = ['cost', 'reduce', '35%', 'optimization', 'strategy']
            addressed_elements = [elem for elem in key_elements if elem in response_text.lower()]
            assert len(addressed_elements) >= 3, f'Response should address key question elements. Found: {addressed_elements} of {key_elements}'
            self.logger.info('✅ Supervisor agent comprehensive quality validation passed')
        finally:
            await websocket.close()

    async def test_triage_agent_quality_specialization(self):
        """
        Test triage agent response quality for specialized routing and analysis.

        BUSINESS VALIDATION: Triage agents must demonstrate intelligent analysis
        and appropriate specialization recommendations.

        Quality Requirements:
        1. Correctly identifies problem type and complexity
        2. Recommends appropriate specialist agents
        3. Provides initial analysis and context
        4. Shows understanding of user needs
        5. Offers immediate helpful insights

        DIFFICULTY: Medium (20 minutes)
        REAL SERVICES: Yes - Staging triage agent with real LLM analysis
        STATUS: Should PASS - Triage specialization is critical for UX
        """
        self.logger.info('🎯 Testing triage agent specialization quality')
        websocket = await self._establish_websocket_connection()
        try:
            technical_question = "Our machine learning pipeline is consuming 80% more GPU resources than expected. We're running PyTorch models on A100 GPUs in production, processing 1M requests/day. Training costs have increased 3x in the last quarter due to model complexity growth. We need optimization recommendations for both inference and training workflows."
            events = await self._send_agent_request(websocket, 'triage_agent', technical_question, {'test_scenario': 'technical_ml_optimization', 'expected_specialization': 'apex_optimizer_agent', 'domain': 'machine_learning_infrastructure'})
            is_quality, metrics = self._analyze_response_quality(events)
            self.logger.info(f'📊 Triage Agent Quality Metrics:')
            self.logger.info(f"   Response Length: {metrics['response_length']} chars")
            self.logger.info(f"   Quality Score: {metrics['quality_score']}/4")
            self.logger.info(f"   Quality Grade: {metrics['quality_grade']}")
            response_text = metrics['response_text_sample'].lower()
            technical_elements = ['gpu', 'pytorch', 'training', 'inference', 'optimization', 'model']
            identified_elements = [elem for elem in technical_elements if elem in response_text]
            assert len(identified_elements) >= 3, f'Triage agent should identify key technical elements. Found: {identified_elements} of {technical_elements}'
            analysis_indicators = ['analyze', 'recommend', 'suggest', 'identify', 'optimize', 'improve']
            has_analysis = any((indicator in response_text for indicator in analysis_indicators))
            assert has_analysis, f"Triage response should include analysis language. Sample: {metrics['response_text_sample']}"
            assert metrics['response_length'] >= 150, f"Triage response too brief for technical question: {metrics['response_length']} chars"
            assert is_quality, f"Triage agent response quality insufficient for specialization. Got grade {metrics['quality_grade']} - need quality analysis for routing decisions."
            self.logger.info('✅ Triage agent specialization quality validation passed')
        finally:
            await websocket.close()

    async def test_apex_optimizer_quality_depth(self):
        """
        Test APEX Optimizer agent response quality for deep optimization analysis.

        BUSINESS VALIDATION: APEX agents must provide expert-level optimization
        recommendations with specific, implementable solutions.

        Quality Requirements:
        1. Deep technical analysis and understanding
        2. Specific, measurable optimization recommendations
        3. Cost-benefit analysis and projections
        4. Implementation guidance and priorities
        5. Risk assessment and mitigation strategies

        DIFFICULTY: Very High (40 minutes)
        REAL SERVICES: Yes - Full APEX agent with comprehensive LLM analysis
        STATUS: Should PASS - APEX optimization is core product value
        """
        self.logger.info('🎯 Testing APEX Optimizer deep analysis quality')
        websocket = await self._establish_websocket_connection()
        try:
            optimization_scenario = 'Enterprise client analysis: Fortune 500 company with $2M annual AI spend across 15 different departments. Current setup: 75% GPT-4, 20% GPT-3.5, 5% Claude. Average response time: 4.2s, user satisfaction: 78%, cost growth: 15% monthly. Peak usage: 50K concurrent requests. Geographic distribution: 40% US, 35% EU, 25% Asia. Requirements: Reduce costs 40%, improve response time to <2s, maintain quality, support 100K concurrent by Q4. Provide comprehensive optimization strategy with specific implementation timeline and ROI projections.'
            events = await self._send_agent_request(websocket, 'apex_optimizer_agent', optimization_scenario, {'test_scenario': 'enterprise_optimization_analysis', 'expected_depth': 'expert_level', 'complexity': 'very_high', 'client_tier': 'fortune_500'})
            is_quality, metrics = self._analyze_response_quality(events)
            self.logger.info(f'📊 APEX Optimizer Quality Metrics:')
            self.logger.info(f"   Response Length: {metrics['response_length']} chars")
            self.logger.info(f"   Word Count: {metrics['word_count']} words")
            self.logger.info(f"   Quality Score: {metrics['quality_score']}/4")
            self.logger.info(f"   Quality Grade: {metrics['quality_grade']}")
            assert metrics['response_length'] >= 400, f"APEX response too short for enterprise analysis: {metrics['response_length']} chars (enterprise clients expect comprehensive analysis ≥400 chars)"
            assert metrics['quality_score'] >= 3, f"APEX quality insufficient for enterprise client. Got score {metrics['quality_score']}/4, grade {metrics['quality_grade']} (enterprise tier requires A-grade analysis)"
            response_text = metrics['response_text_sample'].lower()
            enterprise_elements = ['cost', '40%', 'response time', 'concurrent', 'timeline', 'roi']
            addressed_enterprise = [elem for elem in enterprise_elements if elem in response_text]
            assert len(addressed_enterprise) >= 4, f'APEX should address enterprise requirements comprehensively. Found: {addressed_enterprise} of {enterprise_elements}'
            assert metrics['has_numerical_insights'], f"APEX analysis must include numerical insights for enterprise ROI. Sample: {metrics['response_text_sample']}"
            assert metrics['has_specific_recommendations'], f"APEX must provide specific, implementable recommendations. Sample: {metrics['response_text_sample']}"
            self.logger.info('✅ APEX Optimizer expert-level quality validation passed')
        finally:
            await websocket.close()

    async def test_data_helper_quality_insights(self):
        """
        Test Data Helper agent response quality for data analysis and insights.

        BUSINESS VALIDATION: Data Helper agents must provide meaningful data insights
        and analysis that support decision-making.

        Quality Requirements:
        1. Accurate data interpretation and analysis
        2. Clear insights and patterns identification
        3. Actionable recommendations based on data
        4. Proper context and limitations acknowledgment
        5. Business-relevant conclusions

        DIFFICULTY: High (25 minutes)
        REAL SERVICES: Yes - Data Helper with real analysis capabilities
        STATUS: Should PASS - Data insights are critical for business decisions
        """
        self.logger.info('🎯 Testing Data Helper insights quality')
        websocket = await self._establish_websocket_connection()
        try:
            data_question = 'Analyze our AI usage patterns: Month 1: 100K API calls, $8,000 cost, avg response 2.1s. Month 2: 150K calls, $13,500 cost, avg response 2.8s. Month 3: 200K calls, $19,200 cost, avg response 3.2s. User satisfaction dropped from 92% to 84%. Peak usage hours: 9-11am, 2-4pm EST. Top use cases: customer support (40%), content generation (35%), data analysis (25%). What patterns do you see and what optimizations would you recommend?'
            events = await self._send_agent_request(websocket, 'data_helper_agent', data_question, {'test_scenario': 'usage_pattern_analysis', 'data_type': 'api_usage_metrics', 'analysis_depth': 'comprehensive'})
            is_quality, metrics = self._analyze_response_quality(events)
            self.logger.info(f'📊 Data Helper Quality Metrics:')
            self.logger.info(f"   Response Length: {metrics['response_length']} chars")
            self.logger.info(f"   Quality Score: {metrics['quality_score']}/4")
            self.logger.info(f"   Quality Grade: {metrics['quality_grade']}")
            response_text = metrics['response_text_sample'].lower()
            data_patterns = ['increase', 'trend', 'pattern', 'growth', 'correlation', 'decrease']
            identified_patterns = [pattern for pattern in data_patterns if pattern in response_text]
            assert len(identified_patterns) >= 2, f'Data Helper should identify patterns in the data. Found: {identified_patterns} of {data_patterns}'
            numeric_references = ['100k', '150k', '200k', '8,000', '13,500', '19,200', '92%', '84%']
            referenced_numbers = [num for num in numeric_references if num.replace(',', '').replace('k', '') in response_text]
            assert len(referenced_numbers) >= 2, f'Data Helper should reference specific data points. Found references: {referenced_numbers}'
            assert metrics['has_actionable_content'], f"Data Helper must provide actionable insights based on data analysis. Sample: {metrics['response_text_sample']}"
            assert is_quality, f"Data Helper response quality insufficient for business insights. Got grade {metrics['quality_grade']} - data analysis requires quality insights."
            self.logger.info('✅ Data Helper insights quality validation passed')
        finally:
            await websocket.close()

    async def test_response_quality_consistency_across_agents(self):
        """
        Test response quality consistency across different agent types.

        BUSINESS VALIDATION: All agents should maintain consistent quality standards
        regardless of specialization, ensuring reliable user experience.

        Quality Requirements:
        1. All agents meet minimum quality thresholds
        2. Response appropriateness for agent specialization
        3. Consistent professional tone and helpfulness
        4. No degradation in quality based on agent type
        5. Appropriate response length for question complexity

        DIFFICULTY: Very High (45 minutes)
        REAL SERVICES: Yes - All agent types in staging
        STATUS: Should PASS - Quality consistency is critical for platform reliability
        """
        self.logger.info('🎯 Testing response quality consistency across all agents')
        websocket = await self._establish_websocket_connection()
        try:
            common_question = "Our startup has grown to 50 employees and our AI costs have reached $5,000/month. We're using primarily GPT-4 for customer support automation and internal tools. Usage is growing 20% monthly but our efficiency improvements aren't keeping pace. What specific steps should we take to optimize our AI spending and scale efficiently?"
            agent_types = ['supervisor_agent', 'triage_agent', 'apex_optimizer_agent', 'data_helper_agent']
            agent_results = {}
            for agent_type in agent_types:
                self.logger.info(f'Testing {agent_type} response quality')
                events = await self._send_agent_request(websocket, agent_type, common_question, {'test_scenario': 'quality_consistency_test', 'agent_type': agent_type, 'question_complexity': 'medium'})
                is_quality, metrics = self._analyze_response_quality(events)
                agent_results[agent_type] = {'is_quality': is_quality, 'metrics': metrics, 'events_count': len(events)}
                self.logger.info(f"   {agent_type}: Grade {metrics['quality_grade']}, Length {metrics['response_length']}, Score {metrics['quality_score']}/4")
                assert is_quality, f"{agent_type} failed quality standards. Grade: {metrics['quality_grade']}, Score: {metrics['quality_score']}/4. All agents must maintain consistent quality."
                assert metrics['response_length'] >= 100, f"{agent_type} response too short: {metrics['response_length']} chars. Business questions require substantive responses."
            quality_scores = [result['metrics']['quality_score'] for result in agent_results.values()]
            response_lengths = [result['metrics']['response_length'] for result in agent_results.values()]
            avg_quality = sum(quality_scores) / len(quality_scores)
            avg_length = sum(response_lengths) / len(response_lengths)
            quality_variance = max(quality_scores) - min(quality_scores)
            self.logger.info(f'📊 Cross-Agent Quality Analysis:')
            self.logger.info(f'   Average Quality Score: {avg_quality:.1f}/4')
            self.logger.info(f'   Average Response Length: {avg_length:.0f} chars')
            self.logger.info(f'   Quality Score Variance: {quality_variance}')
            assert avg_quality >= 2.0, f'Average quality across agents too low: {avg_quality:.1f}/4. Platform requires consistent quality across all agents.'
            assert quality_variance <= 2, f'Quality variance too high across agents: {quality_variance}. Users expect consistent experience regardless of agent type.'
            actionable_agents = sum((1 for result in agent_results.values() if result['metrics']['has_actionable_content']))
            assert actionable_agents >= len(agent_types) * 0.75, f'Too many agents lack actionable content: {actionable_agents}/{len(agent_types)}. Business users need actionable guidance from all agents.'
            self.logger.info('✅ Cross-agent quality consistency validation passed')
        finally:
            await websocket.close()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')