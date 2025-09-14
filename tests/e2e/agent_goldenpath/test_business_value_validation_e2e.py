"""
E2E Tests for Agent Business Value Validation - Golden Path Core Quality

MISSION CRITICAL: Tests that agents deliver substantive business value through
quality AI responses that justify $500K+ ARR platform usage. These tests validate
the QUALITY and SUBSTANCE of agent responses, not just technical delivery.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid/Early (All paying segments)
- Business Goal: Customer Retention & Platform Value Demonstration
- Value Impact: Validates AI responses provide real business value, not just chat
- Strategic Impact: $500K+ ARR depends on agents delivering actionable insights

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- REAL AUTH: JWT tokens via staging auth service
- REAL WEBSOCKETS: wss:// connections to staging backend
- REAL AGENTS: Complete supervisor → triage → specialist agent orchestration
- REAL LLMS: Actual LLM calls with substance validation
- BUSINESS FOCUS: Response quality, actionability, and user value validation

CRITICAL: These tests must validate SUBSTANCE, not just technical success.
Response quality and business value are the primary success metrics.

GitHub Issue: #1059 Agent Golden Path Messages E2E Test Creation
Phase: Phase 1 - Business Value Validation Enhancement
"""

import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
import re
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
import httpx

# SSOT imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available

# Auth and WebSocket utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper


@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.business_value
@pytest.mark.mission_critical
class TestAgentBusinessValueValidationE2E(SSotAsyncTestCase):
    """
    E2E tests validating that agents deliver substantive business value through
    quality AI responses that justify platform usage and customer retention.

    Tests the core value proposition: Agent responses must be SUBSTANTIVE,
    ACTIONABLE, and provide REAL BUSINESS VALUE to justify platform costs.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment configuration and business validation utilities."""
        # Initialize staging configuration
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)

        # Skip if staging not available
        if not is_staging_available():
            pytest.skip("Staging environment not available for business value validation")

        # Initialize auth helper for JWT management
        cls.auth_helper = E2EAuthHelper(environment="staging")

        # Initialize WebSocket test utilities
        cls.websocket_helper = WebSocketTestHelper()

        # Test user configuration for business scenarios
        cls.test_user_id = f"business_value_user_{int(time.time())}"
        cls.test_user_email = f"business_value_test_{int(time.time())}@netra-testing.ai"

        # Business value validation criteria
        cls.business_keywords = {
            "cost_optimization": ["cost", "savings", "reduce", "optimization", "efficiency", "budget"],
            "technical_accuracy": ["specific", "implement", "configure", "setup", "deploy"],
            "actionability": ["step", "recommend", "suggest", "should", "consider", "strategy"],
            "quantification": ["percent", "%", "dollar", "$", "reduction", "improvement", "roi"]
        }

        cls.logger.info(f"Business value validation tests initialized for staging")

    def setup_method(self, method):
        """Setup for each business value test method."""
        super().setup_method(method)

        # Generate test-specific business context
        self.thread_id = f"business_value_test_{int(time.time())}"
        self.run_id = f"run_{self.thread_id}"

        # Create JWT token for this test
        self.access_token = self.__class__.auth_helper.create_test_jwt_token(
            user_id=self.__class__.test_user_id,
            email=self.__class__.test_user_email,
            exp_minutes=60
        )

        self.logger.info(f"Business value test setup complete - thread_id: {self.thread_id}")

    def _validate_business_response_quality(self, response_text: str, scenario_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that agent response meets business quality standards.

        Args:
            response_text: The agent's response text to validate
            scenario_context: Context about the business scenario being tested

        Returns:
            Dict with validation results and quality metrics
        """
        validation_results = {
            "length_adequate": len(response_text) >= 200,  # Substantive responses
            "keyword_relevance": {},
            "actionability_score": 0,
            "technical_specificity": 0,
            "business_value_indicators": [],
            "quality_score": 0.0,
            "meets_standards": False
        }

        response_lower = response_text.lower()

        # Check for business keyword relevance
        for category, keywords in self.__class__.business_keywords.items():
            found_keywords = [kw for kw in keywords if kw in response_lower]
            validation_results["keyword_relevance"][category] = {
                "found": found_keywords,
                "count": len(found_keywords),
                "score": min(len(found_keywords) / len(keywords), 1.0)
            }

        # Validate actionability (concrete steps, recommendations)
        actionable_patterns = [
            r'\d+\.\s+[A-Z]',  # Numbered lists
            r'recommend\w*\s+\w+',  # Recommendations
            r'should\s+\w+',  # Should statements
            r'step\s+\d+',  # Step references
            r'implement\s+\w+',  # Implementation guidance
        ]

        actionability_matches = sum(len(re.findall(pattern, response_text, re.IGNORECASE))
                                   for pattern in actionable_patterns)
        validation_results["actionability_score"] = min(actionability_matches / 5, 1.0)

        # Validate technical specificity
        technical_indicators = [
            r'\$\d+', r'\d+%', r'\d+\s*seconds?', r'\d+\s*minutes?',  # Quantifications
            r'config\w*', r'setup', r'deploy', r'implement',  # Technical terms
            r'API\s+\w+', r'endpoint', r'database', r'cache'  # System components
        ]

        technical_matches = sum(len(re.findall(pattern, response_text, re.IGNORECASE))
                               for pattern in technical_indicators)
        validation_results["technical_specificity"] = min(technical_matches / 8, 1.0)

        # Identify business value indicators
        if scenario_context.get("expected_business_value"):
            expected_indicators = scenario_context["expected_business_value"]
            for indicator in expected_indicators:
                if indicator.lower() in response_lower:
                    validation_results["business_value_indicators"].append(indicator)

        # Calculate overall quality score
        quality_components = [
            validation_results["keyword_relevance"]["cost_optimization"]["score"] * 0.3,
            validation_results["keyword_relevance"]["actionability"]["score"] * 0.3,
            validation_results["actionability_score"] * 0.2,
            validation_results["technical_specificity"] * 0.2
        ]
        validation_results["quality_score"] = sum(quality_components)

        # Meets standards if quality score >= 0.6 and length adequate
        validation_results["meets_standards"] = (
            validation_results["quality_score"] >= 0.6 and
            validation_results["length_adequate"]
        )

        return validation_results

    async def test_agent_delivers_quantified_cost_savings_recommendations(self):
        """
        Test agent provides specific, quantified cost optimization recommendations.

        BUSINESS VALUE CORE: This validates agents can deliver concrete, measurable
        business value through specific cost optimization guidance with quantified
        savings estimates.

        Success criteria:
        1. Response contains specific dollar amounts or percentages
        2. Actionable recommendations with implementation steps
        3. ROI estimates or timeframe for savings realization
        4. Technical accuracy in recommendations

        DIFFICULTY: Very High (60+ minutes)
        REAL SERVICES: Yes - Complete staging GCP stack with real LLM analysis
        STATUS: Should PASS - Core business value delivery validation
        """
        business_start_time = time.time()
        business_metrics = []

        self.logger.info("💰 Testing agent delivers quantified cost savings recommendations")

        try:
            # Step 1: Establish WebSocket connection to staging
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False  # Staging environment
            ssl_context.verify_mode = ssl.CERT_NONE

            connection_start = time.time()
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.__class__.staging_config.urls.websocket_url,
                    additional_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Test-Suite": "business-value-e2e",
                        "X-Business-Scenario": "cost-optimization"
                    },
                    ssl=ssl_context,
                    ping_interval=30,
                    ping_timeout=10
                ),
                timeout=20.0
            )

            connection_time = time.time() - connection_start
            business_metrics.append({
                "metric": "websocket_connection_time",
                "value": connection_time,
                "timestamp": time.time(),
                "success": True
            })

            self.logger.info(f"✅ WebSocket connected in {connection_time:.2f}s")

            # Step 2: Send realistic enterprise cost optimization request
            business_scenario = {
                "company_profile": "Enterprise SaaS with 50,000 users",
                "current_spend": "$25,000/month on AI APIs",
                "growth_rate": "40% month-over-month user growth",
                "pain_points": [
                    "Cost scaling faster than revenue",
                    "No intelligent model selection",
                    "Limited caching strategy",
                    "Unpredictable monthly costs"
                ],
                "target_savings": "30-40% cost reduction",
                "constraints": "Cannot sacrifice response quality"
            }

            user_message = {
                "type": "agent_request",
                "agent": "apex_optimizer_agent",
                "message": (
                    f"I'm the CTO of an enterprise SaaS company with {business_scenario['company_profile']}. "
                    f"We're currently spending {business_scenario['current_spend']} with "
                    f"{business_scenario['growth_rate']}. Our main challenges are: "
                    f"{', '.join(business_scenario['pain_points'])}. "
                    f"I need a comprehensive optimization strategy to achieve {business_scenario['target_savings']} "
                    f"while maintaining quality. Please provide specific, quantified recommendations with "
                    f"implementation steps, expected savings amounts, and ROI estimates."
                ),
                "thread_id": self.thread_id,
                "run_id": self.run_id,
                "user_id": self.__class__.test_user_id,
                "context": {
                    "business_scenario": "enterprise_cost_optimization",
                    "expected_business_value": [
                        "dollar amounts", "percentage savings", "ROI estimates",
                        "implementation timeline", "specific recommendations"
                    ],
                    "validation_criteria": "quantified_cost_optimization"
                }
            }

            message_send_start = time.time()
            await websocket.send(json.dumps(user_message))
            message_send_time = time.time() - message_send_start

            business_metrics.append({
                "metric": "message_send_time",
                "value": message_send_time,
                "message_length": len(user_message["message"]),
                "timestamp": time.time(),
                "success": True
            })

            self.logger.info(f"📤 Business scenario message sent ({len(user_message['message'])} chars)")

            # Step 3: Collect agent processing events with business value focus
            agent_events = []
            response_timeout = 120.0  # Extended timeout for complex business analysis
            event_collection_start = time.time()

            # Expected high-value events
            expected_events = [
                "agent_started",
                "agent_thinking",
                "tool_executing",
                "tool_completed",
                "agent_completed"
            ]
            received_events = set()
            final_response = None

            while time.time() - event_collection_start < response_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    agent_events.append(event)

                    event_type = event.get("type", "unknown")
                    received_events.add(event_type)

                    self.logger.info(f"📨 Received business event: {event_type}")

                    # Check for agent completion with business analysis
                    if event_type == "agent_completed":
                        final_response = event
                        self.logger.info("💼 Business analysis completed by agent")
                        break

                    # Check for business-impacting errors
                    if event_type == "error" or event_type == "agent_error":
                        raise AssertionError(f"Business analysis failed: {event}")

                except asyncio.TimeoutError:
                    # Continue waiting for business analysis completion
                    continue
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse business event: {e}")
                    continue

            event_collection_time = time.time() - event_collection_start
            business_metrics.append({
                "metric": "business_analysis_time",
                "value": event_collection_time,
                "event_count": len(agent_events),
                "received_events": list(received_events),
                "timestamp": time.time(),
                "success": len(agent_events) > 0
            })

            # Step 4: Validate business value delivery

            # Must receive complete business analysis
            assert len(agent_events) > 0, "Should receive business analysis events"
            assert "agent_started" in received_events, f"Missing business analysis start. Got: {received_events}"
            assert "agent_completed" in received_events, f"Missing business analysis completion. Got: {received_events}"

            # Validate final business response
            assert final_response is not None, "Should receive final business analysis"

            response_data = final_response.get("data", {})
            result = response_data.get("result", {})

            # Extract business response content
            if isinstance(result, dict):
                response_text = result.get("response", str(result))
            else:
                response_text = str(result)

            # CRITICAL: Validate business value delivery
            assert len(response_text) > 400, (
                f"Business analysis too brief for enterprise scenario: {len(response_text)} chars "
                f"(expected >400 for comprehensive cost optimization analysis)"
            )

            # Validate business response quality
            business_validation = self._validate_business_response_quality(
                response_text,
                user_message["context"]
            )

            # Business value assertions
            assert business_validation["meets_standards"], (
                f"Response fails business value standards. Quality score: {business_validation['quality_score']:.2f} "
                f"(required ≥0.6). Validation details: {business_validation}"
            )

            assert business_validation["length_adequate"], (
                f"Response not substantive enough for enterprise cost optimization: {len(response_text)} chars"
            )

            # Validate specific business requirements
            assert business_validation["keyword_relevance"]["cost_optimization"]["score"] >= 0.4, (
                f"Insufficient cost optimization focus: {business_validation['keyword_relevance']['cost_optimization']}"
            )

            assert business_validation["actionability_score"] >= 0.3, (
                f"Response lacks actionable recommendations: {business_validation['actionability_score']:.2f}"
            )

            # Look for quantified business value
            quantified_indicators = [
                "$", "%", "percent", "dollar", "savings", "reduction", "roi", "return on investment"
            ]
            found_quantification = any(indicator in response_text.lower() for indicator in quantified_indicators)
            assert found_quantification, (
                f"Response lacks quantified business value indicators. Expected one of: {quantified_indicators}. "
                f"Response: {response_text[:300]}..."
            )

            await websocket.close()

            # Final business value reporting
            total_business_time = time.time() - business_start_time

            business_metrics.append({
                "metric": "total_business_analysis_time",
                "value": total_business_time,
                "quality_score": business_validation["quality_score"],
                "business_value_delivered": True,
                "timestamp": time.time(),
                "success": True
            })

            # Log comprehensive business results
            self.logger.info("🎯 BUSINESS VALUE DELIVERY SUCCESS")
            self.logger.info(f"💰 Business Analysis Metrics:")
            self.logger.info(f"   Total Analysis Time: {total_business_time:.1f}s")
            self.logger.info(f"   Response Length: {len(response_text)} characters")
            self.logger.info(f"   Quality Score: {business_validation['quality_score']:.2f}/1.0")
            self.logger.info(f"   Actionability Score: {business_validation['actionability_score']:.2f}/1.0")
            self.logger.info(f"   Business Value Indicators: {business_validation['business_value_indicators']}")
            self.logger.info(f"   Technical Specificity: {business_validation['technical_specificity']:.2f}/1.0")

            # Business success assertions
            assert total_business_time < 180.0, f"Business analysis too slow: {total_business_time:.1f}s (max 180s)"
            assert business_validation["quality_score"] >= 0.6, (
                f"Business value quality insufficient: {business_validation['quality_score']:.2f}"
            )

        except Exception as e:
            total_time = time.time() - business_start_time

            self.logger.error(f"❌ BUSINESS VALUE DELIVERY FAILED")
            self.logger.error(f"   Error: {str(e)}")
            self.logger.error(f"   Duration: {total_time:.1f}s")
            self.logger.error(f"   Business metrics collected: {len(business_metrics)}")

            # Fail with business impact context
            raise AssertionError(
                f"Business value delivery failed after {total_time:.1f}s: {e}. "
                f"This breaks core platform value proposition and threatens $500K+ ARR. "
                f"Business metrics: {business_metrics}"
            )

    async def test_agent_response_quality_meets_enterprise_standards(self):
        """
        Test agent responses meet enterprise-grade quality standards.

        ENTERPRISE VALUE: Validates agents can deliver responses that meet the
        quality expectations of enterprise customers paying premium prices.

        Quality standards:
        1. Comprehensive analysis (>500 chars for complex queries)
        2. Technical accuracy and specificity
        3. Implementation guidance with clear steps
        4. Risk assessment and mitigation strategies
        5. Scalability and compliance considerations

        DIFFICULTY: High (45 minutes)
        REAL SERVICES: Yes - Staging GCP with enterprise scenario analysis
        STATUS: Should PASS - Quality standards critical for enterprise retention
        """
        quality_start_time = time.time()
        quality_metrics = []

        self.logger.info("🏢 Testing agent response quality meets enterprise standards")

        try:
            # Step 1: Establish WebSocket connection
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.__class__.staging_config.urls.websocket_url,
                    additional_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Test-Suite": "enterprise-quality-e2e",
                        "X-Business-Tier": "enterprise"
                    },
                    ssl=ssl_context
                ),
                timeout=20.0
            )

            # Step 2: Test enterprise-complexity scenarios
            enterprise_scenarios = [
                {
                    "name": "healthcare_compliance_optimization",
                    "message": (
                        "We're a healthcare AI platform processing 100,000 patient records daily. "
                        "Current AI costs are $40,000/month with HIPAA compliance requirements. "
                        "We need a comprehensive optimization strategy that maintains SOC2 and HIPAA "
                        "compliance while reducing costs by 25%. Please provide a detailed analysis "
                        "covering data privacy, model selection, caching strategies, and audit trails."
                    ),
                    "expected_quality_indicators": [
                        "hipaa", "compliance", "audit", "privacy", "security",
                        "model selection", "caching", "cost reduction", "data protection"
                    ],
                    "minimum_response_length": 600,
                    "quality_threshold": 0.7
                },
                {
                    "name": "financial_services_optimization",
                    "message": (
                        "As CTO of a fintech startup, we process $50M in transactions monthly using "
                        "AI for fraud detection and risk assessment. Current OpenAI spend is $15,000/month "
                        "with 99.9% uptime requirements. We need optimization recommendations that "
                        "maintain regulatory compliance (PCI DSS, SOX) and real-time performance. "
                        "Include specific model architectures, failover strategies, and cost projections."
                    ),
                    "expected_quality_indicators": [
                        "fraud detection", "risk assessment", "compliance", "pci dss",
                        "real-time", "failover", "model architecture", "cost projections"
                    ],
                    "minimum_response_length": 650,
                    "quality_threshold": 0.75
                }
            ]

            for scenario in enterprise_scenarios:
                scenario_start = time.time()
                self.logger.info(f"🎯 Testing enterprise scenario: {scenario['name']}")

                # Send enterprise-complexity message
                message = {
                    "type": "agent_request",
                    "agent": "supervisor_agent",  # Use supervisor for complex routing
                    "message": scenario["message"],
                    "thread_id": f"enterprise_{scenario['name']}_{int(time.time())}",
                    "run_id": f"run_enterprise_{scenario['name']}",
                    "user_id": self.__class__.test_user_id,
                    "context": {
                        "business_tier": "enterprise",
                        "scenario_type": scenario["name"],
                        "quality_requirements": "enterprise_grade",
                        "expected_business_value": scenario["expected_quality_indicators"]
                    }
                }

                await websocket.send(json.dumps(message))

                # Collect enterprise response
                final_response = None
                response_timeout = 90.0
                collection_start = time.time()

                while time.time() - collection_start < response_timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        event = json.loads(event_data)

                        if event.get("type") == "agent_completed":
                            final_response = event
                            break

                        if "error" in event.get("type", "").lower():
                            raise AssertionError(f"Enterprise analysis failed: {event}")

                    except asyncio.TimeoutError:
                        continue

                scenario_duration = time.time() - scenario_start

                # Validate enterprise response quality
                assert final_response is not None, (
                    f"Should receive enterprise analysis for {scenario['name']}"
                )

                response_data = final_response.get("data", {})
                result = response_data.get("result", {})
                response_text = result.get("response", str(result)) if isinstance(result, dict) else str(result)

                # Enterprise quality validation
                quality_validation = self._validate_business_response_quality(
                    response_text,
                    message["context"]
                )

                # Enterprise quality assertions
                assert len(response_text) >= scenario["minimum_response_length"], (
                    f"Enterprise response too brief for {scenario['name']}: "
                    f"{len(response_text)} chars (required ≥{scenario['minimum_response_length']})"
                )

                assert quality_validation["quality_score"] >= scenario["quality_threshold"], (
                    f"Enterprise quality insufficient for {scenario['name']}: "
                    f"{quality_validation['quality_score']:.2f} (required ≥{scenario['quality_threshold']})"
                )

                # Check for enterprise-specific indicators
                found_indicators = [
                    indicator for indicator in scenario["expected_quality_indicators"]
                    if indicator.lower() in response_text.lower()
                ]
                indicator_coverage = len(found_indicators) / len(scenario["expected_quality_indicators"])

                assert indicator_coverage >= 0.6, (
                    f"Insufficient enterprise topic coverage for {scenario['name']}: "
                    f"{indicator_coverage:.1%} (found: {found_indicators})"
                )

                quality_metrics.append({
                    "scenario": scenario["name"],
                    "duration": scenario_duration,
                    "response_length": len(response_text),
                    "quality_score": quality_validation["quality_score"],
                    "indicator_coverage": indicator_coverage,
                    "meets_enterprise_standards": quality_validation["meets_standards"]
                })

                self.logger.info(f"✅ {scenario['name']}: Quality {quality_validation['quality_score']:.2f}, "
                               f"Coverage {indicator_coverage:.1%}, Duration {scenario_duration:.1f}s")

            await websocket.close()

            # Final enterprise quality validation
            total_quality_time = time.time() - quality_start_time
            avg_quality_score = sum(m["quality_score"] for m in quality_metrics) / len(quality_metrics)
            avg_indicator_coverage = sum(m["indicator_coverage"] for m in quality_metrics) / len(quality_metrics)

            self.logger.info("🏢 ENTERPRISE QUALITY STANDARDS SUCCESS")
            self.logger.info(f"📊 Enterprise Quality Metrics:")
            self.logger.info(f"   Total Quality Assessment Time: {total_quality_time:.1f}s")
            self.logger.info(f"   Average Quality Score: {avg_quality_score:.2f}/1.0")
            self.logger.info(f"   Average Topic Coverage: {avg_indicator_coverage:.1%}")
            self.logger.info(f"   Scenarios Tested: {len(quality_metrics)}")

            # Enterprise success assertions
            assert avg_quality_score >= 0.65, (
                f"Average enterprise quality insufficient: {avg_quality_score:.2f} (required ≥0.65)"
            )
            assert avg_indicator_coverage >= 0.55, (
                f"Average enterprise topic coverage insufficient: {avg_indicator_coverage:.1%} (required ≥55%)"
            )

        except Exception as e:
            total_time = time.time() - quality_start_time

            self.logger.error(f"❌ ENTERPRISE QUALITY STANDARDS FAILED")
            self.logger.error(f"   Error: {str(e)}")
            self.logger.error(f"   Duration: {total_time:.1f}s")

            raise AssertionError(
                f"Enterprise quality validation failed after {total_time:.1f}s: {e}. "
                f"This threatens enterprise customer retention and premium pricing model."
            )

    async def test_agent_tool_integration_enhances_response_value(self):
        """
        Test that agent tool usage significantly enhances response quality and value.

        TOOL VALUE VALIDATION: Validates that when agents use tools during processing,
        the resulting responses are more accurate, specific, and valuable than
        responses generated without tool assistance.

        Tool integration scenarios:
        1. Data analysis requests requiring calculation tools
        2. Configuration optimization requiring system analysis tools
        3. Market research requiring data retrieval tools
        4. Technical validation requiring verification tools

        DIFFICULTY: Very High (50 minutes)
        REAL SERVICES: Yes - Complete staging with real tool orchestration
        STATUS: Should PASS - Tool integration is core platform differentiator
        """
        tool_integration_start = time.time()
        tool_metrics = []

        self.logger.info("🛠️ Testing agent tool integration enhances response value")

        try:
            # Step 1: Establish WebSocket connection
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.__class__.staging_config.urls.websocket_url,
                    additional_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Test-Suite": "tool-integration-e2e",
                        "X-Tool-Validation": "enabled"
                    },
                    ssl=ssl_context
                ),
                timeout=20.0
            )

            # Step 2: Test tool-enhanced scenarios
            tool_scenarios = [
                {
                    "name": "cost_calculation_analysis",
                    "message": (
                        "I'm spending $8,500/month on GPT-4 API calls with 2.3M tokens monthly. "
                        "Usage is growing 15% each month. Calculate my projected costs for the next "
                        "6 months and compare savings from switching 60% of calls to GPT-3.5 "
                        "($0.002/1k vs $0.03/1k tokens). Show exact dollar amounts and ROI timeline."
                    ),
                    "expected_tools": ["calculator", "cost_analysis", "projection"],
                    "tool_indicators": ["calculated", "computed", "analysis shows", "data indicates"],
                    "value_enhancement": "quantified_projections",
                    "minimum_specificity": 0.7
                },
                {
                    "name": "performance_optimization_analysis",
                    "message": (
                        "Our AI API has 3.2s average response time with 12,000 daily requests. "
                        "We're using GPT-4 for everything. Analyze response time impact of "
                        "implementing intelligent routing: 40% GPT-3.5 (0.8s avg), 60% GPT-4 (3.2s avg). "
                        "Include caching hit rates and provide specific performance improvements."
                    ),
                    "expected_tools": ["performance_analyzer", "caching_calculator", "routing_optimizer"],
                    "tool_indicators": ["analyzed", "optimized", "calculations show", "performance data"],
                    "value_enhancement": "performance_metrics",
                    "minimum_specificity": 0.6
                }
            ]

            for scenario in tool_scenarios:
                scenario_start = time.time()
                self.logger.info(f"🔧 Testing tool scenario: {scenario['name']}")

                # Send tool-requiring message
                message = {
                    "type": "agent_request",
                    "agent": "apex_optimizer_agent",
                    "message": scenario["message"],
                    "thread_id": f"tool_test_{scenario['name']}_{int(time.time())}",
                    "run_id": f"run_tool_{scenario['name']}",
                    "user_id": self.__class__.test_user_id,
                    "context": {
                        "tool_scenario": scenario["name"],
                        "expects_tool_usage": True,
                        "expected_tools": scenario["expected_tools"],
                        "value_enhancement_type": scenario["value_enhancement"]
                    }
                }

                await websocket.send(json.dumps(message))

                # Monitor for tool events specifically
                tool_events = []
                final_response = None
                response_timeout = 75.0
                collection_start = time.time()

                tool_executing_seen = False
                tool_completed_seen = False

                while time.time() - collection_start < response_timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=12.0)
                        event = json.loads(event_data)

                        event_type = event.get("type", "unknown")

                        # Track tool usage events
                        if event_type == "tool_executing":
                            tool_executing_seen = True
                            tool_events.append(event)
                            self.logger.info(f"🔧 Tool executing: {event.get('data', {}).get('tool_name', 'unknown')}")

                        elif event_type == "tool_completed":
                            tool_completed_seen = True
                            tool_events.append(event)
                            self.logger.info(f"✅ Tool completed: {event.get('data', {}).get('tool_name', 'unknown')}")

                        elif event_type == "agent_completed":
                            final_response = event
                            break

                        elif "error" in event_type.lower():
                            raise AssertionError(f"Tool integration error: {event}")

                    except asyncio.TimeoutError:
                        continue

                scenario_duration = time.time() - scenario_start

                # Validate tool integration occurred
                assert tool_executing_seen and tool_completed_seen, (
                    f"Tool integration not detected for {scenario['name']}. "
                    f"Tool executing: {tool_executing_seen}, Tool completed: {tool_completed_seen}. "
                    f"This scenario requires tool usage for accurate analysis."
                )

                assert len(tool_events) >= 2, (
                    f"Insufficient tool events for {scenario['name']}: {len(tool_events)} "
                    f"(expected ≥2 for tool execution + completion)"
                )

                # Validate enhanced response
                assert final_response is not None, (
                    f"Should receive tool-enhanced response for {scenario['name']}"
                )

                response_data = final_response.get("data", {})
                result = response_data.get("result", {})
                response_text = result.get("response", str(result)) if isinstance(result, dict) else str(result)

                # Validate tool enhancement indicators
                tool_indicators_found = [
                    indicator for indicator in scenario["tool_indicators"]
                    if indicator.lower() in response_text.lower()
                ]

                indicator_ratio = len(tool_indicators_found) / len(scenario["tool_indicators"])

                assert indicator_ratio >= 0.5, (
                    f"Insufficient tool enhancement indicators for {scenario['name']}: "
                    f"{indicator_ratio:.1%} (found: {tool_indicators_found})"
                )

                # Validate response specificity and value
                quality_validation = self._validate_business_response_quality(
                    response_text,
                    message["context"]
                )

                assert quality_validation["technical_specificity"] >= scenario["minimum_specificity"], (
                    f"Tool-enhanced response lacks specificity for {scenario['name']}: "
                    f"{quality_validation['technical_specificity']:.2f} "
                    f"(required ≥{scenario['minimum_specificity']})"
                )

                tool_metrics.append({
                    "scenario": scenario["name"],
                    "duration": scenario_duration,
                    "tool_events_count": len(tool_events),
                    "tool_indicators_found": len(tool_indicators_found),
                    "indicator_ratio": indicator_ratio,
                    "technical_specificity": quality_validation["technical_specificity"],
                    "overall_quality": quality_validation["quality_score"],
                    "tool_enhancement_validated": True
                })

                self.logger.info(f"🛠️ {scenario['name']}: Tools {len(tool_events)}, "
                               f"Specificity {quality_validation['technical_specificity']:.2f}, "
                               f"Duration {scenario_duration:.1f}s")

            await websocket.close()

            # Final tool integration validation
            total_tool_time = time.time() - tool_integration_start
            avg_specificity = sum(m["technical_specificity"] for m in tool_metrics) / len(tool_metrics)
            total_tool_events = sum(m["tool_events_count"] for m in tool_metrics)

            self.logger.info("🛠️ AGENT TOOL INTEGRATION SUCCESS")
            self.logger.info(f"🔧 Tool Integration Metrics:")
            self.logger.info(f"   Total Integration Test Time: {total_tool_time:.1f}s")
            self.logger.info(f"   Total Tool Events: {total_tool_events}")
            self.logger.info(f"   Average Technical Specificity: {avg_specificity:.2f}/1.0")
            self.logger.info(f"   Tool Scenarios Validated: {len(tool_metrics)}")

            # Tool integration success assertions
            assert total_tool_events >= 4, (
                f"Insufficient tool usage across scenarios: {total_tool_events} events "
                f"(expected ≥4 for {len(tool_scenarios)} scenarios)"
            )
            assert avg_specificity >= 0.55, (
                f"Tool enhancement insufficient: {avg_specificity:.2f} avg specificity "
                f"(required ≥0.55 for value demonstration)"
            )

        except Exception as e:
            total_time = time.time() - tool_integration_start

            self.logger.error(f"❌ AGENT TOOL INTEGRATION FAILED")
            self.logger.error(f"   Error: {str(e)}")
            self.logger.error(f"   Duration: {total_time:.1f}s")

            raise AssertionError(
                f"Tool integration validation failed after {total_time:.1f}s: {e}. "
                f"Tool integration is a core platform differentiator for $500K+ ARR. "
                f"Tool metrics: {tool_metrics}"
            )


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "-s",
        "--gcp-staging",
        "--agent-goldenpath",
        "--business-value"
    ])