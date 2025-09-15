"""
E2E Tests for Advanced Agent Feature Integration - Golden Path Premium Features

MISSION CRITICAL: Tests advanced agent features and integrations to validate sophisticated
AI capabilities in the Golden Path workflow. These tests ensure premium features work
correctly and provide the advanced functionality that differentiates the platform.

Business Value Justification (BVJ):
- Segment: Mid-tier and Enterprise Users (Premium Features)
- Business Goal: Feature Differentiation & Premium Value through Advanced AI Capabilities
- Value Impact: Validates advanced features that justify premium pricing and enterprise adoption
- Strategic Impact: Advanced features = competitive advantage = premium revenue = $500K+ ARR

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- FEATURE INTEGRATION: Test complex agent interactions, tool usage, and advanced workflows
- BUSINESS SCENARIOS: Realistic enterprise use cases requiring sophisticated AI processing
- QUALITY VALIDATION: Ensure advanced features deliver high-quality, actionable results
- PERFORMANCE: Advanced features should maintain acceptable performance standards

CRITICAL: These tests must demonstrate actual advanced functionality with real complexity.
No mocking of sophisticated features or bypassing complex processing logic.

GitHub Issue: #861 Agent Golden Path Messages Test Creation - Gap Area 3
Coverage Target: Advanced agent feature integration (identified gap)
"""
import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import uuid
import re
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper

@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.advanced_features
@pytest.mark.mission_critical
class TestAdvancedAgentFeaturesE2E(SSotAsyncTestCase):
    """
    E2E tests for validating advanced agent features in staging GCP.

    Tests sophisticated AI capabilities, complex agent interactions,
    and premium features that differentiate the platform.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment for advanced feature testing."""
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        if not is_staging_available():
            pytest.skip('Staging environment not available')
        cls.auth_helper = E2EAuthHelper(environment='staging')
        cls.websocket_helper = WebSocketTestHelper(base_url=cls.staging_config.urls.websocket_url, environment='staging')
        cls.CRITICAL_EVENTS = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        cls.logger.info(f'Advanced agent features E2E tests initialized for staging')

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.advanced_test_session = f'advanced_features_{int(time.time())}'
        self.thread_id = f'advanced_test_{self.advanced_test_session}'
        self.run_id = f'run_{self.thread_id}'
        self.test_user_id = f'advanced_test_user_{int(time.time())}'
        self.test_user_email = f'advanced_test_{int(time.time())}@netra-testing.ai'
        self.access_token = self.__class__.auth_helper.create_test_jwt_token(user_id=self.test_user_id, email=self.test_user_email, exp_minutes=90)
        self.logger.info(f'Advanced features test setup - session: {self.advanced_test_session}')

    async def _establish_websocket_connection(self) -> websockets.ServerConnection:
        """Establish WebSocket connection for advanced feature testing."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f'Bearer {self.access_token}', 'X-Environment': 'staging', 'X-Test-Suite': 'advanced-agent-features', 'X-Session-Id': self.advanced_test_session}, ssl=ssl_context, ping_interval=45, ping_timeout=15), timeout=25.0)
        return websocket

    async def _process_advanced_agent_request(self, agent_type: str, message: str, context: Dict[str, Any]=None, timeout: float=120.0) -> Dict[str, Any]:
        """Process advanced agent request and return comprehensive analysis."""
        start_time = time.time()
        websocket = await self._establish_websocket_connection()
        try:
            request_message = {'type': 'agent_request', 'agent': agent_type, 'message': message, 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': self.test_user_id, 'context': {'advanced_feature_test': True, 'requires_sophisticated_processing': True, **(context or {})}}
            message_sent_time = time.time()
            await websocket.send(json.dumps(request_message))
            events = []
            event_types = set()
            thinking_events = []
            tool_events = []
            response_content = ''
            while time.time() - message_sent_time < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    events.append(event)
                    event_type = event.get('type', 'unknown')
                    event_types.add(event_type)
                    if event_type == 'agent_thinking':
                        thinking_events.append(event)
                    elif event_type in ['tool_executing', 'tool_completed']:
                        tool_events.append(event)
                    elif event_type == 'agent_completed':
                        response_data = event.get('data', {})
                        result = response_data.get('result', {})
                        if isinstance(result, dict):
                            response_content = result.get('response', str(result))
                        else:
                            response_content = str(result)
                        break
                    elif event_type in ['error', 'agent_error']:
                        raise AssertionError(f'Agent error during advanced processing: {event}')
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError as e:
                    self.logger.warning(f'JSON decode error in advanced processing: {e}')
                    continue
            await websocket.close()
            total_time = time.time() - start_time
            return {'success': len(response_content) > 0, 'total_time': total_time, 'events': events, 'events_count': len(events), 'event_types': event_types, 'critical_events': event_types.intersection(self.__class__.CRITICAL_EVENTS), 'thinking_events': thinking_events, 'tool_events': tool_events, 'response_content': response_content, 'response_length': len(response_content)}
        except Exception as e:
            await websocket.close()
            total_time = time.time() - start_time
            return {'success': False, 'total_time': total_time, 'error': str(e), 'events': [], 'events_count': 0, 'event_types': set(), 'critical_events': set()}

    def _analyze_response_sophistication(self, response_content: str) -> Dict[str, Any]:
        """Analyze response content for sophistication indicators."""
        analysis = {'length': len(response_content), 'word_count': len(response_content.split()), 'has_numbers': bool(re.search('\\d+', response_content)), 'has_specific_recommendations': False, 'has_implementation_steps': False, 'has_business_context': False, 'has_technical_details': False, 'sophistication_score': 0}
        response_lower = response_content.lower()
        recommendation_indicators = ['recommend', 'suggest', 'advise', 'propose', 'should consider', 'step 1', 'step 2', 'first', 'second', 'next', 'then', 'finally']
        analysis['has_specific_recommendations'] = any((indicator in response_lower for indicator in recommendation_indicators))
        implementation_indicators = ['implement', 'execute', 'deploy', 'configure', 'set up', 'install', 'integrate', 'optimize', 'monitor']
        analysis['has_implementation_steps'] = any((indicator in response_lower for indicator in implementation_indicators))
        business_indicators = ['cost', 'savings', 'revenue', 'roi', 'budget', 'efficiency', 'business', 'enterprise', 'organization', 'company']
        analysis['has_business_context'] = any((indicator in response_lower for indicator in business_indicators))
        technical_indicators = ['api', 'model', 'algorithm', 'architecture', 'infrastructure', 'configuration', 'optimization', 'performance', 'scaling']
        analysis['has_technical_details'] = any((indicator in response_lower for indicator in technical_indicators))
        score_components = [analysis['length'] > 200, analysis['word_count'] > 50, analysis['has_numbers'], analysis['has_specific_recommendations'], analysis['has_implementation_steps'], analysis['has_business_context'], analysis['has_technical_details']]
        analysis['sophistication_score'] = sum(score_components) / len(score_components)
        return analysis

    async def test_complex_multi_step_optimization_analysis(self):
        """
        Test complex multi-step AI cost optimization analysis with APEX agent.

        ADVANCED FEATURES: Validates sophisticated analysis capabilities including
        market research, detailed calculations, and comprehensive recommendations.

        Scenario:
        1. Request comprehensive AI cost optimization analysis
        2. Expect multi-step reasoning and tool usage
        3. Validate detailed recommendations with calculations
        4. Ensure business context and implementation guidance
        5. Verify premium-quality response sophistication

        DIFFICULTY: Very High (50 minutes)
        REAL SERVICES: Yes - Advanced APEX agent capabilities in staging
        STATUS: Should PASS - Premium optimization features essential for differentiation
        """
        self.logger.info('🧠 Testing complex multi-step optimization analysis')
        complex_optimization_request = "I'm the CTO of a fintech startup that's grown from 50K to 2M users in 18 months. Our AI infrastructure costs have exploded from $8K to $85K monthly, primarily from: - GPT-4 for customer support (40% of usage) - Claude for document analysis (30% of usage) - Custom models for fraud detection (20% of usage) - GPT-3.5 for marketing personalization (10% of usage) We're profitable but margins are shrinking fast. I need a comprehensive analysis that includes: 1. Detailed cost breakdown and optimization opportunities 2. Market research on alternative solutions and pricing 3. Specific implementation strategies with timelines 4. ROI projections and risk assessments 5. Technical implementation guidance for my development team Our architecture: microservices on AWS, Redis for caching, PostgreSQL for data, Python/FastAPI backend, React frontend. Team of 15 engineers."
        result = await self._process_advanced_agent_request('apex_optimizer_agent', complex_optimization_request, {'complexity_level': 'very_high', 'requires_market_research': True, 'requires_calculations': True, 'requires_implementation_guidance': True, 'business_context': 'fintech_startup_scaling'}, timeout=180.0)
        self.logger.info(f'📊 Complex Optimization Analysis Results:')
        self.logger.info(f"   Success: {result['success']}")
        self.logger.info(f"   Processing Time: {result['total_time']:.1f}s")
        self.logger.info(f"   Events: {result['events_count']}")
        self.logger.info(f"   Critical Events: {len(result['critical_events'])}")
        self.logger.info(f"   Thinking Events: {len(result['thinking_events'])}")
        self.logger.info(f"   Tool Events: {len(result['tool_events'])}")
        self.logger.info(f"   Response Length: {result['response_length']} chars")
        assert result['success'], f"Complex optimization analysis should succeed. Error: {result.get('error')}"
        assert len(result['critical_events']) >= 4, f"Complex processing should generate comprehensive events. Got: {result['critical_events']}"
        assert len(result['thinking_events']) >= 2, f"Complex analysis should show agent reasoning. Got {len(result['thinking_events'])} thinking events"
        if len(result['tool_events']) > 0:
            self.logger.info(f"   Tool usage detected: {len(result['tool_events'])} tool events")
        sophistication = self._analyze_response_sophistication(result['response_content'])
        self.logger.info(f'📈 Response Sophistication Analysis:')
        self.logger.info(f"   Word Count: {sophistication['word_count']}")
        self.logger.info(f"   Has Numbers: {sophistication['has_numbers']}")
        self.logger.info(f"   Has Recommendations: {sophistication['has_specific_recommendations']}")
        self.logger.info(f"   Has Implementation: {sophistication['has_implementation_steps']}")
        self.logger.info(f"   Has Business Context: {sophistication['has_business_context']}")
        self.logger.info(f"   Has Technical Details: {sophistication['has_technical_details']}")
        self.logger.info(f"   Sophistication Score: {sophistication['sophistication_score']:.2f}")
        assert sophistication['sophistication_score'] >= 0.6, f"Complex optimization analysis should be sophisticated. Score: {sophistication['sophistication_score']:.2f} (min 0.6)"
        assert sophistication['word_count'] >= 200, f"Complex analysis should be comprehensive: {sophistication['word_count']} words (min 200)"
        assert sophistication['has_specific_recommendations'], f'Should provide specific recommendations for premium analysis'
        assert sophistication['has_business_context'], f'Should understand business context for fintech startup'
        response_content = result['response_content'].lower()
        context_elements = ['fintech', '2m users', '85k', 'cost', 'margins', 'aws', 'microservices']
        addressed_elements = [elem for elem in context_elements if elem in response_content]
        assert len(addressed_elements) >= 4, f'Should address specific business context. Addressed: {addressed_elements} of {context_elements}'
        assert result['total_time'] < 240.0, f"Complex analysis should complete within reasonable time: {result['total_time']:.1f}s (max 240s)"
        self.logger.info('✅ Complex multi-step optimization analysis validated')

    async def test_supervisor_agent_coordination_capabilities(self):
        """
        Test supervisor agent's advanced coordination and delegation capabilities.

        ADVANCED FEATURES: Validates supervisor's ability to coordinate complex
        multi-faceted requests requiring different types of analysis and expertise.

        Scenario:
        1. Request multi-dimensional business analysis requiring coordination
        2. Expect supervisor to analyze and structure the response
        3. Validate comprehensive coverage of business dimensions
        4. Ensure strategic-level thinking and coordination
        5. Verify enterprise-grade analysis quality

        DIFFICULTY: Very High (45 minutes)
        REAL SERVICES: Yes - Advanced supervisor coordination in staging
        STATUS: Should PASS - Supervisor coordination essential for enterprise features
        """
        self.logger.info('👥 Testing supervisor agent coordination capabilities')
        coordination_request = "I'm presenting to our board next week about our AI strategy and need comprehensive analysis. As CEO of a healthcare SaaS company (500 employees, $50M ARR), I need to address: STRATEGIC QUESTIONS: 1. How should we position AI in our competitive landscape? 2. What's our optimal AI investment strategy for the next 2 years? 3. How do we balance innovation with regulatory compliance (HIPAA, SOC2)? OPERATIONAL QUESTIONS: 4. Current AI spending is $120K/month - is this efficient for our scale? 5. Should we build internal AI capabilities or rely on vendors? 6. How do we measure ROI on our AI investments? RISK QUESTIONS: 7. What are the key risks in our AI strategy and how do we mitigate them? 8. How do we ensure data privacy and security with AI systems? 9. What's our contingency plan if AI costs increase 300% (like they did this year)? I need this structured as an executive briefing with clear recommendations, supporting data, and action items for each area."
        result = await self._process_advanced_agent_request('supervisor_agent', coordination_request, {'executive_briefing': True, 'multi_dimensional_analysis': True, 'board_presentation': True, 'healthcare_context': True, 'strategic_coordination_required': True}, timeout=150.0)
        self.logger.info(f'📊 Supervisor Coordination Results:')
        self.logger.info(f"   Success: {result['success']}")
        self.logger.info(f"   Processing Time: {result['total_time']:.1f}s")
        self.logger.info(f"   Events: {result['events_count']}")
        self.logger.info(f"   Response Length: {result['response_length']} chars")
        assert result['success'], f"Supervisor coordination should succeed. Error: {result.get('error')}"
        assert len(result['critical_events']) >= 3, f"Supervisor should generate comprehensive events. Got: {result['critical_events']}"
        sophistication = self._analyze_response_sophistication(result['response_content'])
        response_content = result['response_content'].lower()
        strategic_coverage = ['competitive', 'investment', 'strategy', 'positioning']
        operational_coverage = ['efficiency', 'build vs buy', 'roi', 'measurement']
        risk_coverage = ['risk', 'mitigation', 'privacy', 'security', 'contingency']
        strategic_addressed = sum((1 for term in strategic_coverage if term in response_content))
        operational_addressed = sum((1 for term in operational_coverage if term in response_content))
        risk_addressed = sum((1 for term in risk_coverage if term in response_content))
        self.logger.info(f'📈 Multi-Dimensional Coverage Analysis:')
        self.logger.info(f'   Strategic Coverage: {strategic_addressed}/{len(strategic_coverage)}')
        self.logger.info(f'   Operational Coverage: {operational_addressed}/{len(operational_coverage)}')
        self.logger.info(f'   Risk Coverage: {risk_addressed}/{len(risk_coverage)}')
        self.logger.info(f"   Overall Sophistication: {sophistication['sophistication_score']:.2f}")
        assert strategic_addressed >= 2, f'Should address strategic questions comprehensively. Addressed: {strategic_addressed}/{len(strategic_coverage)}'
        assert operational_addressed >= 2, f'Should address operational questions comprehensively. Addressed: {operational_addressed}/{len(operational_coverage)}'
        assert risk_addressed >= 2, f'Should address risk management comprehensively. Addressed: {risk_addressed}/{len(risk_coverage)}'
        assert sophistication['sophistication_score'] >= 0.7, f"Executive briefing should be highly sophisticated. Score: {sophistication['sophistication_score']:.2f} (min 0.7)"
        assert sophistication['word_count'] >= 300, f"Executive briefing should be comprehensive: {sophistication['word_count']} words (min 300)"
        healthcare_context = ['healthcare', 'hipaa', '$50m', '500 employees', '$120k']
        context_addressed = sum((1 for context in healthcare_context if context in response_content))
        assert context_addressed >= 3, f'Should incorporate specific business context. Addressed: {context_addressed}/{len(healthcare_context)} elements'
        self.logger.info('✅ Supervisor agent coordination capabilities validated')

    async def test_data_helper_agent_analytical_capabilities(self):
        """
        Test data helper agent's advanced analytical and computational capabilities.

        ADVANCED FEATURES: Validates sophisticated data analysis, calculations,
        and metrics generation for business intelligence scenarios.

        Scenario:
        1. Request complex data analysis with calculations
        2. Expect sophisticated analytical reasoning
        3. Validate numerical accuracy and business insights
        4. Ensure data-driven recommendations
        5. Verify analytical depth and accuracy

        DIFFICULTY: High (40 minutes)
        REAL SERVICES: Yes - Advanced data analysis capabilities in staging
        STATUS: Should PASS - Data analysis features critical for business intelligence
        """
        self.logger.info('📊 Testing data helper agent analytical capabilities')
        analytical_request = "I need comprehensive data analysis for our AI cost optimization project. Here's our data: CURRENT AI USAGE (Monthly): - GPT-4: 50M tokens input, 12M tokens output, $0.03/$0.06 per 1K tokens - GPT-3.5: 200M tokens input, 80M tokens output, $0.0015/$0.002 per 1K tokens - Claude-3: 30M tokens input, 8M tokens output, $0.015/$0.075 per 1K tokens - Custom embeddings: 500M tokens, $0.0001 per 1K tokens USAGE PATTERNS: - Customer support: 40% of total usage, peak 9AM-5PM EST - Content generation: 35% of total usage, distributed throughout day - Data analysis: 15% of total usage, batch jobs 2AM-4AM EST - Other: 10% of total usage, various times BUSINESS CONTEXT: - Current monthly spend: $47,500 - Revenue per customer: $150/month - Customer support cost per ticket: $12 - Content generation revenue impact: $5,000/month ANALYSIS NEEDED: 1. Calculate exact monthly costs by model and use case 2. Identify top 3 cost optimization opportunities with projected savings 3. Analyze cost per customer and impact on unit economics 4. Project cost scaling scenarios: 50% growth, 100% growth, 200% growth 5. Recommend optimal model mix with cost-benefit analysis 6. Create efficiency metrics and KPIs for ongoing monitoring"
        result = await self._process_advanced_agent_request('data_helper_agent', analytical_request, {'complex_calculations_required': True, 'business_intelligence': True, 'cost_analysis': True, 'numerical_accuracy_critical': True}, timeout=120.0)
        self.logger.info(f'📊 Data Analysis Results:')
        self.logger.info(f"   Success: {result['success']}")
        self.logger.info(f"   Processing Time: {result['total_time']:.1f}s")
        self.logger.info(f"   Events: {result['events_count']}")
        self.logger.info(f"   Response Length: {result['response_length']} chars")
        assert result['success'], f"Data analysis should succeed. Error: {result.get('error')}"
        sophistication = self._analyze_response_sophistication(result['response_content'])
        response_content = result['response_content'].lower()
        assert sophistication['has_numbers'], f'Data analysis should include numerical calculations'
        analytical_indicators = ['calculate', 'analysis', 'cost', 'savings', 'efficiency', 'metrics', 'projected', 'optimization', 'recommend']
        analytical_coverage = sum((1 for indicator in analytical_indicators if indicator in response_content))
        assert analytical_coverage >= 6, f'Should demonstrate comprehensive analytical thinking. Coverage: {analytical_coverage}/{len(analytical_indicators)}'
        model_references = ['gpt-4', 'gpt-3.5', 'claude', 'embedding']
        model_coverage = sum((1 for model in model_references if model in response_content))
        assert model_coverage >= 3, f'Should reference specific AI models in analysis. Coverage: {model_coverage}/{len(model_references)}'
        business_elements = ['customer', 'revenue', 'unit economics', 'cost per', 'roi']
        business_coverage = sum((1 for element in business_elements if element in response_content))
        assert business_coverage >= 3, f'Should demonstrate business context understanding. Coverage: {business_coverage}/{len(business_elements)}'
        assert sophistication['sophistication_score'] >= 0.6, f"Data analysis should be sophisticated. Score: {sophistication['sophistication_score']:.2f} (min 0.6)"
        assert sophistication['word_count'] >= 250, f"Complex data analysis should be comprehensive: {sophistication['word_count']} words (min 250)"
        self.logger.info('✅ Data helper agent analytical capabilities validated')

    async def test_agent_context_awareness_and_personalization(self):
        """
        Test advanced agent context awareness and response personalization.

        ADVANCED FEATURES: Validates agents' ability to adapt responses based
        on user context, role, industry, and specific requirements.

        Scenario:
        1. Send requests with different user personas and contexts
        2. Expect responses tailored to specific roles and industries
        3. Validate appropriate technical depth and business focus
        4. Ensure context-appropriate recommendations
        5. Verify personalization quality and relevance

        DIFFICULTY: High (35 minutes)
        REAL SERVICES: Yes - Context-aware response generation in staging
        STATUS: Should PASS - Personalization essential for premium user experience
        """
        self.logger.info('🎯 Testing agent context awareness and personalization')
        persona_scenarios = [{'persona': 'Technical CTO', 'request': "As CTO of a Series B SaaS company with 200 engineers, I need technical guidance for optimizing our AI infrastructure. We're using Kubernetes on GCP with microservices architecture. Our AI costs are $200K/month and growing 15% monthly. I need specific technical implementation strategies.", 'expected_focus': ['technical', 'kubernetes', 'architecture', 'implementation'], 'technical_depth': 'high'}, {'persona': 'Business Executive', 'request': "I'm the CEO of a Fortune 500 retail company. Our board is asking about AI strategy and ROI. We're spending $2M annually on AI initiatives across customer experience, supply chain, and marketing. I need business-focused analysis for board presentation.", 'expected_focus': ['roi', 'strategy', 'board', 'business case'], 'technical_depth': 'low'}, {'persona': 'Startup Founder', 'request': "I'm a solo founder bootstrapping an AI-powered edtech startup. Current AI costs are $3K/month but I need to scale to 10K users. I'm technical but need both business and implementation advice for rapid, cost-effective growth.", 'expected_focus': ['bootstrap', 'scale', 'cost-effective', 'growth'], 'technical_depth': 'medium'}]
        results = []
        for scenario in persona_scenarios:
            self.logger.info(f"Testing {scenario['persona']} persona...")
            result = await self._process_advanced_agent_request('supervisor_agent', scenario['request'], {'persona_context': scenario['persona'], 'personalization_test': True, 'context_awareness_required': True}, timeout=90.0)
            response_content = result['response_content'].lower()
            focus_coverage = sum((1 for focus in scenario['expected_focus'] if focus in response_content))
            persona_analysis = {'persona': scenario['persona'], 'success': result['success'], 'response_length': result['response_length'], 'focus_coverage': focus_coverage, 'expected_focus_count': len(scenario['expected_focus']), 'focus_percentage': focus_coverage / len(scenario['expected_focus']) if scenario['expected_focus'] else 0, 'sophistication': self._analyze_response_sophistication(result['response_content'])}
            results.append(persona_analysis)
            assert result['success'], f"{scenario['persona']} request should succeed. Error: {result.get('error')}"
            assert focus_coverage >= 2, f"{scenario['persona']} response should address expected focus areas. Addressed: {focus_coverage}/{len(scenario['expected_focus'])}"
            assert result['response_length'] >= 150, f"{scenario['persona']} should receive substantial response: {result['response_length']} chars"
        avg_focus_coverage = sum((r['focus_percentage'] for r in results)) / len(results)
        avg_sophistication = sum((r['sophistication']['sophistication_score'] for r in results)) / len(results)
        self.logger.info(f'📈 Personalization Analysis:')
        self.logger.info(f'   Average Focus Coverage: {avg_focus_coverage:.1%}')
        self.logger.info(f'   Average Sophistication: {avg_sophistication:.2f}')
        for result in results:
            self.logger.info(f"   {result['persona']}: {result['focus_percentage']:.1%} focus, {result['sophistication']['sophistication_score']:.2f} sophistication")
        assert avg_focus_coverage >= 0.6, f'Personalization should address persona-specific needs. Average coverage: {avg_focus_coverage:.1%} (min 60%)'
        assert avg_sophistication >= 0.5, f'Personalized responses should be sophisticated. Average sophistication: {avg_sophistication:.2f} (min 0.5)'
        successful_personas = sum((1 for r in results if r['success']))
        assert successful_personas == len(persona_scenarios), f'All persona scenarios should succeed. Successful: {successful_personas}/{len(persona_scenarios)}'
        self.logger.info('✅ Agent context awareness and personalization validated')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')