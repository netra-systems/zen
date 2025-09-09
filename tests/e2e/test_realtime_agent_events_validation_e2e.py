"""
E2E Test: Real-time Agent Events Validation - MISSION CRITICAL Event Quality Assurance

BUSINESS IMPACT: Tests real-time agent event quality and business value delivery.
This validates that agent events provide meaningful, actionable information to users in real-time.

Business Value Justification (BVJ):
- Segment: Platform/All Users - Real-time Event Quality  
- Business Goal: User Experience - Meaningful real-time updates drive engagement
- Value Impact: Validates event content quality that differentiates from generic progress bars
- Strategic Impact: Tests event intelligence that justifies premium AI platform positioning

CRITICAL SUCCESS METRICS:
✅ Agent events contain substantive business-relevant content
✅ Events provide meaningful progress updates and context
✅ Real-time event delivery maintains user engagement
✅ Event content demonstrates AI thinking and problem-solving
✅ Events build user confidence in AI capabilities

EVENT QUALITY VALIDATION:
• agent_started - Clear explanation of what AI will do
• agent_thinking - Visible reasoning and problem analysis
• tool_executing - Specific tool usage with expected outcomes
• tool_completed - Concrete results and insights delivered
• agent_completed - Comprehensive summary with actionable value

COMPLIANCE:
@compliance CLAUDE.md - WebSocket events enable substantive chat (Section 6)
@compliance CLAUDE.md - E2E AUTH MANDATORY (Section 7.3)
@compliance CLAUDE.md - Real-time business value delivery
@compliance SPEC/core.xml - Agent event content standards
"""

import asyncio
import json
import pytest
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# SSOT Imports - Authentication and Events
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.ssot.agent_event_validators import (
    AgentEventValidator,
    CriticalAgentEventType,
    WebSocketEventMessage,
    validate_agent_events
)
from test_framework.ssot.websocket_golden_path_helpers import (
    WebSocketGoldenPathHelper,
    GoldenPathTestConfig
)

# SSOT Imports - Types
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Test Framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.e2e
@pytest.mark.staging_compatible
class TestRealtimeAgentEventsValidationE2E(SSotBaseTestCase):
    """
    MISSION CRITICAL E2E Tests for Real-time Agent Event Quality Validation.
    
    These tests validate that agent events deliver meaningful, business-relevant
    content in real-time to maintain user engagement and confidence.
    
    BUSINESS IMPACT: If event quality is poor, users lose confidence in AI capabilities.
    """
    
    def setup_method(self):
        """Set up real-time agent events validation test environment."""
        super().setup_method()
        
        # Initialize SSOT helpers
        self.environment = self.get_test_environment()
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.golden_path_helper = WebSocketGoldenPathHelper(environment=self.environment)
        
        # Event quality focused configuration
        self.config = GoldenPathTestConfig.for_environment(self.environment)
        self.config.validate_business_value = True
        self.config.validate_event_timing = True
        
        # Event quality tracking
        self.test_start_time = time.time()
        self.quality_events_received = 0
        self.content_richness_score = 0.0
        self.business_relevance_score = 0.0
        self.user_engagement_score = 0.0
        
        print(f"\n🎯 REAL-TIME AGENT EVENTS VALIDATION E2E - Environment: {self.environment}")
        print(f"📊 Target: High-quality agent events with business value")
        print(f"💡 Business Impact: Event quality drives user confidence and engagement")
    
    def teardown_method(self):
        """Clean up and report event quality metrics."""
        test_duration = time.time() - self.test_start_time
        
        print(f"\n📊 Agent Event Quality Summary:")
        print(f"⏱️ Duration: {test_duration:.2f}s")
        print(f"🎯 Quality Events: {self.quality_events_received}")
        print(f"📝 Content Richness: {self.content_richness_score:.1f}%")
        print(f"💼 Business Relevance: {self.business_relevance_score:.1f}%")
        print(f"👥 User Engagement: {self.user_engagement_score:.1f}%")
        
        overall_quality = (self.content_richness_score + self.business_relevance_score + self.user_engagement_score) / 3
        
        if overall_quality >= 80.0:
            print(f"✅ EXCELLENT EVENT QUALITY - Users highly engaged")
        elif overall_quality >= 65.0:
            print(f"✅ GOOD EVENT QUALITY - Users moderately engaged")
        else:
            print(f"❌ POOR EVENT QUALITY - Risk of user disengagement")
        
        super().teardown_method()
    
    def _analyze_event_content_quality(self, event: WebSocketEventMessage) -> Dict[str, float]:
        """
        Analyze the content quality of an agent event.
        
        Args:
            event: WebSocket event message to analyze
            
        Returns:
            Dictionary with quality scores
        """
        content = ""
        if hasattr(event, 'data'):
            content = (
                event.data.get("message", "") + " " +
                event.data.get("response", "") + " " +
                event.data.get("description", "") + " " +
                str(event.data.get("details", ""))
            ).strip()
        
        quality_scores = {
            "content_length": 0.0,
            "business_keywords": 0.0,
            "specificity": 0.0,
            "actionability": 0.0,
            "technical_depth": 0.0
        }
        
        if not content:
            return quality_scores
        
        content_lower = content.lower()
        
        # Content length scoring (substantial content expected)
        if len(content) > 100:
            quality_scores["content_length"] = 100.0
        elif len(content) > 50:
            quality_scores["content_length"] = 75.0
        elif len(content) > 20:
            quality_scores["content_length"] = 50.0
        else:
            quality_scores["content_length"] = 25.0
        
        # Business keywords scoring
        business_terms = [
            "analyze", "insights", "recommend", "strategy", "optimize",
            "business", "customer", "revenue", "growth", "efficiency",
            "data", "trends", "patterns", "metrics", "performance"
        ]
        found_business_terms = sum(1 for term in business_terms if term in content_lower)
        quality_scores["business_keywords"] = min(100.0, found_business_terms * 15)
        
        # Specificity scoring (specific details and numbers)
        specificity_indicators = [
            "%", "$", "million", "thousand", "increase", "decrease",
            "step", "process", "method", "approach", "technique"
        ]
        found_specificity = sum(1 for indicator in specificity_indicators if indicator in content_lower)
        quality_scores["specificity"] = min(100.0, found_specificity * 20)
        
        # Actionability scoring
        action_words = [
            "should", "recommend", "suggest", "implement", "improve",
            "focus", "prioritize", "consider", "develop", "create"
        ]
        found_actions = sum(1 for word in action_words if word in content_lower)
        quality_scores["actionability"] = min(100.0, found_actions * 25)
        
        # Technical depth scoring
        technical_terms = [
            "algorithm", "model", "analysis", "calculation", "processing",
            "evaluation", "assessment", "comparison", "correlation", "prediction"
        ]
        found_technical = sum(1 for term in technical_terms if term in content_lower)
        quality_scores["technical_depth"] = min(100.0, found_technical * 20)
        
        return quality_scores
    
    def _calculate_user_engagement_score(self, events: List[WebSocketEventMessage]) -> float:
        """Calculate user engagement score based on event characteristics."""
        if not events:
            return 0.0
        
        engagement_factors = []
        
        # Event frequency and consistency
        if len(events) >= 4:
            engagement_factors.append(25.0)  # Good event coverage
        elif len(events) >= 2:
            engagement_factors.append(15.0)
        
        # Event variety (different types)
        event_types = set(event.event_type for event in events)
        variety_score = min(25.0, len(event_types) * 6)
        engagement_factors.append(variety_score)
        
        # Progressive disclosure (events build on each other)
        has_progression = any(
            event.event_type in ["agent_thinking", "tool_executing", "tool_completed"] 
            for event in events
        )
        if has_progression:
            engagement_factors.append(20.0)
        
        # Completion satisfaction (ends with meaningful result)
        completion_events = [e for e in events if e.event_type == "agent_completed"]
        if completion_events:
            engagement_factors.append(15.0)
        
        # Real-time responsiveness (events come at reasonable intervals)
        # This would need timing data, so we'll give a base score
        engagement_factors.append(10.0)
        
        return sum(engagement_factors)
    
    @pytest.mark.asyncio
    async def test_agent_thinking_event_quality_realtime(self):
        """
        CRITICAL: Agent thinking event quality validation in real-time.
        
        Tests that agent_thinking events contain meaningful reasoning
        and problem analysis that demonstrates AI intelligence.
        
        BUSINESS IMPACT: Validates AI transparency that builds user confidence.
        """
        print("\n🧪 CRITICAL: Testing agent thinking event quality...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"thinking_quality_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "agent_reasoning", "websocket"],
            websocket_enabled=True
        )
        
        print(f"👤 User authenticated for thinking quality test: {user_context.user_id}")
        
        # STEP 2: Send complex request that requires visible reasoning
        reasoning_request = (
            "I need to make a strategic decision about expanding our software company "
            "into the European market. We currently have $2M ARR in the US, 50 employees, "
            "and our main competitors are already established in Europe. Please analyze "
            "the key factors I should consider, evaluate the risks and opportunities, "
            "and help me think through this decision systematically."
        )
        
        # STEP 3: Execute request and monitor thinking events
        async with self.golden_path_helper.authenticated_websocket_connection(user_context):
            result = await self.golden_path_helper.execute_golden_path_flow(
                user_message=reasoning_request,
                user_context=user_context,
                timeout=90.0
            )
            
            # STEP 4: Extract and analyze thinking events
            thinking_events = [
                event for event in result.events_received 
                if event.event_type == "agent_thinking"
            ]
            
            assert len(thinking_events) > 0, "No agent_thinking events received"
            
            thinking_quality_scores = []
            high_quality_thinking_events = 0
            
            for event in thinking_events:
                quality_scores = self._analyze_event_content_quality(event)
                
                # Calculate overall thinking quality
                thinking_quality = (
                    quality_scores["content_length"] * 0.3 +
                    quality_scores["business_keywords"] * 0.25 +
                    quality_scores["specificity"] * 0.2 +
                    quality_scores["technical_depth"] * 0.25
                )
                
                thinking_quality_scores.append(thinking_quality)
                
                if thinking_quality >= 70.0:
                    high_quality_thinking_events += 1
                
                # Log thinking event analysis
                if hasattr(event, 'data'):
                    thinking_content = event.data.get("message", "")[:100]
                    print(f"💭 Thinking event quality: {thinking_quality:.1f}% - {thinking_content}...")
            
            # STEP 5: Validate thinking quality
            avg_thinking_quality = sum(thinking_quality_scores) / len(thinking_quality_scores)
            self.content_richness_score = avg_thinking_quality
            self.quality_events_received = high_quality_thinking_events
            
            # Critical thinking quality assertions
            assert avg_thinking_quality >= 50.0, f"Thinking events lack quality: {avg_thinking_quality:.1f}%"
            assert high_quality_thinking_events >= 1, f"No high-quality thinking events: {high_quality_thinking_events}"
            
            # STEP 6: Validate reasoning content
            all_thinking_content = ""
            for event in thinking_events:
                if hasattr(event, 'data'):
                    all_thinking_content += event.data.get("message", "") + " "
            
            reasoning_indicators = [
                "consider", "analyze", "evaluate", "factor", "risk",
                "opportunity", "decision", "strategy", "approach"
            ]
            found_reasoning = sum(1 for indicator in reasoning_indicators if indicator in all_thinking_content.lower())
            
            assert found_reasoning >= 3, f"Insufficient reasoning indicators: {found_reasoning}"
            
            print(f"✅ Agent thinking quality validated")
            print(f"💭 Average thinking quality: {avg_thinking_quality:.1f}%")
            print(f"🎯 High-quality events: {high_quality_thinking_events}/{len(thinking_events)}")
            print(f"🧠 Reasoning indicators: {found_reasoning}")
    
    @pytest.mark.asyncio
    async def test_tool_execution_transparency_realtime(self):
        """
        CRITICAL: Tool execution transparency and result quality.
        
        Tests that tool_executing and tool_completed events provide
        clear information about what tools are doing and their results.
        
        BUSINESS IMPACT: Validates AI action transparency that builds trust.
        """
        print("\n🧪 CRITICAL: Testing tool execution transparency...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"tool_transparency_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "tool_execution", "transparency"],
            websocket_enabled=True
        )
        
        # STEP 2: Send request that requires tool usage
        tool_request = (
            "Please analyze the following business scenario using data analysis tools: "
            "Calculate the customer lifetime value (CLV) for a SaaS business with "
            "average monthly revenue per user of $50, monthly churn rate of 3%, "
            "and customer acquisition cost of $200. Also provide recommendations "
            "for improving these metrics and their potential impact."
        )
        
        # STEP 3: Execute and monitor tool events
        async with self.golden_path_helper.authenticated_websocket_connection(user_context):
            result = await self.golden_path_helper.execute_golden_path_flow(
                user_message=tool_request,
                user_context=user_context,
                timeout=120.0
            )
            
            # STEP 4: Extract tool execution events
            tool_executing_events = [
                event for event in result.events_received 
                if event.event_type == "tool_executing"
            ]
            
            tool_completed_events = [
                event for event in result.events_received 
                if event.event_type == "tool_completed"
            ]
            
            # STEP 5: Analyze tool transparency
            tool_transparency_scores = []
            
            for event in tool_executing_events:
                if hasattr(event, 'data'):
                    tool_name = event.data.get("tool_name", "")
                    tool_description = event.data.get("message", "") + " " + event.data.get("description", "")
                    
                    transparency_score = 0.0
                    
                    # Tool identification clarity
                    if tool_name and len(tool_name) > 3:
                        transparency_score += 25.0
                    
                    # Purpose explanation
                    if len(tool_description) > 20:
                        transparency_score += 25.0
                    
                    # Expected outcome mentioned
                    outcome_keywords = ["calculate", "analyze", "process", "generate", "evaluate"]
                    if any(keyword in tool_description.lower() for keyword in outcome_keywords):
                        transparency_score += 25.0
                    
                    # Business context relevance
                    business_context = ["clv", "revenue", "churn", "customer", "business", "metric"]
                    if any(context in tool_description.lower() for context in business_context):
                        transparency_score += 25.0
                    
                    tool_transparency_scores.append(transparency_score)
                    print(f"🔧 Tool executing transparency: {transparency_score:.1f}% - {tool_name}")
            
            # STEP 6: Analyze tool completion quality
            completion_quality_scores = []
            
            for event in tool_completed_events:
                quality_scores = self._analyze_event_content_quality(event)
                
                completion_quality = (
                    quality_scores["content_length"] * 0.25 +
                    quality_scores["business_keywords"] * 0.25 +
                    quality_scores["specificity"] * 0.3 +
                    quality_scores["actionability"] * 0.2
                )
                
                completion_quality_scores.append(completion_quality)
                
                if hasattr(event, 'data'):
                    result_content = event.data.get("message", "")[:100]
                    print(f"✅ Tool completion quality: {completion_quality:.1f}% - {result_content}...")
            
            # STEP 7: Validate tool transparency
            if tool_transparency_scores:
                avg_transparency = sum(tool_transparency_scores) / len(tool_transparency_scores)
                self.business_relevance_score = avg_transparency
            
            if completion_quality_scores:
                avg_completion_quality = sum(completion_quality_scores) / len(completion_quality_scores)
                self.content_richness_score = max(self.content_richness_score, avg_completion_quality)
            
            # Critical assertions
            assert len(tool_executing_events) > 0 or len(tool_completed_events) > 0, "No tool execution events received"
            
            if tool_transparency_scores:
                assert avg_transparency >= 40.0, f"Tool transparency too low: {avg_transparency:.1f}%"
            
            if completion_quality_scores:
                assert avg_completion_quality >= 45.0, f"Tool completion quality too low: {avg_completion_quality:.1f}%"
            
            print(f"✅ Tool execution transparency validated")
            print(f"🔧 Tool events: {len(tool_executing_events)} executing, {len(tool_completed_events)} completed")
            
            if tool_transparency_scores:
                print(f"🔍 Average transparency: {avg_transparency:.1f}%")
            if completion_quality_scores:
                print(f"📊 Average completion quality: {avg_completion_quality:.1f}%")
    
    @pytest.mark.asyncio
    async def test_comprehensive_event_quality_journey(self):
        """
        CRITICAL: Comprehensive event quality throughout user journey.
        
        Tests the complete event quality experience from start to finish
        to validate overall user engagement and value delivery.
        
        BUSINESS IMPACT: Validates end-to-end event experience quality.
        """
        print("\n🧪 CRITICAL: Testing comprehensive event quality journey...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"comprehensive_quality_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "comprehensive_analysis", "quality_validation"],
            websocket_enabled=True
        )
        
        # STEP 2: Send comprehensive business request
        comprehensive_request = (
            "I'm the CEO of a growing B2B SaaS company and need comprehensive strategic analysis. "
            "We have $3M ARR, 150 customers, 8% monthly churn, and want to scale to $10M ARR. "
            "Please provide: 1) Current business health assessment, "
            "2) Growth strategy analysis with specific tactics, "
            "3) Risk assessment and mitigation plans, "
            "4) Implementation roadmap with timelines and KPIs. "
            "Show your analytical thinking process and provide actionable recommendations."
        )
        
        # STEP 3: Execute comprehensive analysis
        async with self.golden_path_helper.authenticated_websocket_connection(user_context):
            result = await self.golden_path_helper.execute_golden_path_flow(
                user_message=comprehensive_request,
                user_context=user_context,
                timeout=150.0
            )
            
            # STEP 4: Comprehensive event quality analysis
            all_events = result.events_received
            assert len(all_events) >= 3, f"Insufficient events for quality journey: {len(all_events)}"
            
            # Analyze content quality across all events
            event_quality_scores = []
            business_value_events = 0
            
            for event in all_events:
                quality_scores = self._analyze_event_content_quality(event)
                
                overall_quality = (
                    quality_scores["content_length"] * 0.2 +
                    quality_scores["business_keywords"] * 0.3 +
                    quality_scores["specificity"] * 0.2 +
                    quality_scores["actionability"] * 0.2 +
                    quality_scores["technical_depth"] * 0.1
                )
                
                event_quality_scores.append(overall_quality)
                
                if overall_quality >= 60.0:
                    business_value_events += 1
                
                print(f"📊 {event.event_type} quality: {overall_quality:.1f}%")
            
            # STEP 5: Calculate comprehensive metrics
            avg_event_quality = sum(event_quality_scores) / len(event_quality_scores)
            user_engagement_score = self._calculate_user_engagement_score(all_events)
            
            self.content_richness_score = avg_event_quality
            self.user_engagement_score = user_engagement_score
            self.quality_events_received = business_value_events
            
            # STEP 6: Validate journey quality
            assert avg_event_quality >= 45.0, f"Event journey quality too low: {avg_event_quality:.1f}%"
            assert user_engagement_score >= 50.0, f"User engagement score too low: {user_engagement_score:.1f}%"
            assert business_value_events >= 2, f"Insufficient business value events: {business_value_events}"
            
            # STEP 7: Validate business content coverage
            all_content = ""
            for event in all_events:
                if hasattr(event, 'data'):
                    all_content += event.data.get("message", "") + " " + event.data.get("response", "") + " "
            
            business_coverage_terms = [
                "strategy", "growth", "revenue", "customers", "churn",
                "assessment", "analysis", "recommendations", "implementation", "kpi"
            ]
            
            found_coverage = sum(1 for term in business_coverage_terms if term in all_content.lower())
            coverage_score = (found_coverage / len(business_coverage_terms)) * 100
            
            self.business_relevance_score = coverage_score
            
            assert coverage_score >= 60.0, f"Business content coverage too low: {coverage_score:.1f}%"
            
            print(f"🎉 Comprehensive event quality journey validated")
            print(f"📊 Average event quality: {avg_event_quality:.1f}%")
            print(f"👥 User engagement score: {user_engagement_score:.1f}%")
            print(f"💼 Business coverage: {coverage_score:.1f}%")
            print(f"🎯 Business value events: {business_value_events}/{len(all_events)}")
    
    @pytest.mark.asyncio
    async def test_event_quality_under_different_scenarios(self):
        """
        CRITICAL: Event quality consistency across different scenarios.
        
        Tests that event quality remains high across different types
        of business requests and complexity levels.
        
        BUSINESS IMPACT: Ensures consistent quality regardless of request type.
        """
        print("\n🧪 CRITICAL: Testing event quality across scenarios...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"quality_scenarios_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "scenario_testing"],
            websocket_enabled=True
        )
        
        # STEP 2: Define quality test scenarios
        quality_scenarios = [
            {
                "name": "strategic_planning",
                "request": (
                    "Help me develop a 12-month strategic plan for expanding "
                    "our AI consultancy from 5 to 25 employees while maintaining "
                    "quality and profitability."
                ),
                "expected_quality_threshold": 60.0
            },
            {
                "name": "financial_analysis",
                "request": (
                    "Analyze the financial health of a business with $500K revenue, "
                    "$350K expenses, and project growth scenarios for next 3 years."
                ),
                "expected_quality_threshold": 55.0
            },
            {
                "name": "operational_optimization",
                "request": (
                    "Our customer support team handles 200 tickets/day with 24h response time. "
                    "How can we optimize to 4h response while scaling volume?"
                ),
                "expected_quality_threshold": 50.0
            }
        ]
        
        # STEP 3: Test quality across scenarios
        scenario_quality_scores = []
        
        async with self.golden_path_helper.authenticated_websocket_connection(user_context):
            for i, scenario in enumerate(quality_scenarios):
                print(f"🔄 Testing scenario {i+1}: {scenario['name']}")
                
                try:
                    result = await self.golden_path_helper.execute_golden_path_flow(
                        user_message=scenario["request"],
                        user_context=user_context,
                        timeout=90.0
                    )
                    
                    if result.success and result.events_received:
                        # Analyze event quality for this scenario
                        event_qualities = []
                        for event in result.events_received:
                            quality_scores = self._analyze_event_content_quality(event)
                            overall_quality = sum(quality_scores.values()) / len(quality_scores)
                            event_qualities.append(overall_quality)
                        
                        scenario_avg_quality = sum(event_qualities) / len(event_qualities)
                        scenario_quality_scores.append(scenario_avg_quality)
                        
                        print(f"   📊 Quality: {scenario_avg_quality:.1f}% (threshold: {scenario['expected_quality_threshold']:.1f}%)")
                        
                        # Validate scenario quality
                        assert scenario_avg_quality >= scenario["expected_quality_threshold"], (
                            f"{scenario['name']} quality below threshold: {scenario_avg_quality:.1f}%"
                        )
                    
                    else:
                        print(f"   ❌ Scenario execution failed")
                        scenario_quality_scores.append(0.0)
                
                except Exception as e:
                    print(f"   ❌ Scenario exception: {str(e)[:100]}")
                    scenario_quality_scores.append(0.0)
                
                # Brief delay between scenarios
                await asyncio.sleep(2.0)
        
        # STEP 4: Validate overall quality consistency
        successful_scenarios = [score for score in scenario_quality_scores if score > 0]
        assert len(successful_scenarios) >= 2, f"Too few successful quality scenarios: {len(successful_scenarios)}/3"
        
        avg_quality_across_scenarios = sum(successful_scenarios) / len(successful_scenarios)
        quality_consistency = 100.0 - (max(successful_scenarios) - min(successful_scenarios))
        
        self.content_richness_score = avg_quality_across_scenarios
        self.business_relevance_score = quality_consistency
        
        assert avg_quality_across_scenarios >= 45.0, f"Average quality across scenarios too low: {avg_quality_across_scenarios:.1f}%"
        assert quality_consistency >= 60.0, f"Quality consistency too low: {quality_consistency:.1f}%"
        
        print(f"🎉 Event quality consistency validation complete")
        print(f"📊 Average quality across scenarios: {avg_quality_across_scenarios:.1f}%")
        print(f"🎯 Quality consistency: {quality_consistency:.1f}%")
        print(f"✅ Successful scenarios: {len(successful_scenarios)}/3")


if __name__ == "__main__":
    """
    Run E2E tests for real-time agent events validation.
    
    Usage:
        python -m pytest tests/e2e/test_realtime_agent_events_validation_e2e.py -v
        python -m pytest tests/e2e/test_realtime_agent_events_validation_e2e.py::TestRealtimeAgentEventsValidationE2E::test_agent_thinking_event_quality_realtime -v -s
    """
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))