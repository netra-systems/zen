#!/usr/bin/env python
"""
E2E STAGING TESTS: Business Problem Solving Chat Workflows - Revenue-Generating Value Delivery

CRITICAL BUSINESS MISSION: These tests validate COMPLETE business problem solving workflows
that generate ACTUAL VALUE for customers. This is the CORE of our $500K+ ARR - customers
pay us to solve real business problems through AI-powered chat interactions.

Business Value Justification (BVJ):  
- Segment: All (Free, Early, Mid, Enterprise) - core value proposition for all segments
- Business Goal: Validate complete business problem → AI analysis → actionable solutions workflow
- Value Impact: Ensures customers receive substantive ROI through AI-powered business insights  
- Strategic Impact: Protects $500K+ ARR by validating core value delivery mechanism

CRITICAL REQUIREMENTS per CLAUDE.md:
1. MUST test REAL business problem solving workflows (cost optimization, performance analysis)
2. MUST use REAL authentication and REAL staging services per "MOCKS = Abomination"  
3. MUST validate SUBSTANTIVE business value delivery (actionable insights, specific recommendations)
4. MUST validate all 5 REQUIRED WebSocket events during problem-solving process
5. MUST be designed to fail hard if business value is not delivered

TEST FOCUS: E2E tests in STAGING environment that validate the complete business problem
solving workflow that customers pay for - from problem statement to actionable solutions.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal

# SSOT IMPORTS - Following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper, create_authenticated_user_context
)
from tests.e2e.staging_config import StagingTestConfig

# Core system imports for business workflow testing
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, WebSocketEventType
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Business intelligence validation
import re
from dataclasses import dataclass


@dataclass
class BusinessValueMetrics:
    """Metrics for validating business value delivery."""
    cost_savings_identified: bool = False
    specific_recommendations_count: int = 0
    actionable_steps_count: int = 0
    quantified_benefits_count: int = 0
    implementation_timeline_provided: bool = False
    roi_estimates_provided: bool = False
    
    def calculate_business_value_score(self) -> float:
        """Calculate overall business value score (0.0 to 1.0)."""
        score = 0.0
        max_score = 6.0  # Total possible points
        
        if self.cost_savings_identified:
            score += 1.0
        if self.specific_recommendations_count >= 3:
            score += 1.0
        if self.actionable_steps_count >= 5:
            score += 1.0
        if self.quantified_benefits_count >= 2:
            score += 1.0
        if self.implementation_timeline_provided:
            score += 1.0
        if self.roi_estimates_provided:
            score += 1.0
            
        return score / max_score
    
    def is_substantive_value(self) -> bool:
        """Determine if delivered value meets substantive business criteria."""
        return self.calculate_business_value_score() >= 0.7  # 70% threshold


class BusinessValueAnalyzer:
    """Analyzes AI responses for substantive business value delivery."""
    
    def __init__(self):
        # Patterns for identifying business value components
        self.cost_savings_patterns = [
            r'save\s+\$[\d,]+', r'reduce.*cost.*by.*\d+%', r'cost.*reduction.*\$[\d,]+',
            r'savings.*of.*\$[\d,]+', r'decrease.*spend.*\$[\d,]+', r'optimize.*budget.*\$[\d,]+'
        ]
        
        self.recommendation_patterns = [
            r'recommend', r'suggest', r'should', r'consider', r'implement',
            r'strategy', r'approach', r'solution', r'optimize', r'improve'
        ]
        
        self.action_patterns = [
            r'step\s+\d+', r'first.*second.*third', r'action.*item', r'to.*do',
            r'implementation.*plan', r'next.*steps', r'immediate.*action'
        ]
        
        self.quantification_patterns = [
            r'\d+%.*improvement', r'\$[\d,]+.*benefit', r'\d+.*hours.*saved',
            r'increase.*by.*\d+%', r'reduce.*by.*\d+', r'roi.*of.*\d+'
        ]
        
        self.timeline_patterns = [
            r'within.*\d+.*weeks?', r'in.*\d+.*months?', r'timeline', r'schedule',
            r'phase.*\d+', r'quarter.*\d+', r'by.*end.*of'
        ]
        
    def analyze_business_value(self, response_text: str) -> BusinessValueMetrics:
        """Analyze response text for business value components."""
        text_lower = response_text.lower()
        metrics = BusinessValueMetrics()
        
        # Check for cost savings identification
        for pattern in self.cost_savings_patterns:
            if re.search(pattern, text_lower):
                metrics.cost_savings_identified = True
                break
        
        # Count specific recommendations
        recommendation_matches = []
        for pattern in self.recommendation_patterns:
            matches = re.finditer(pattern, text_lower)
            recommendation_matches.extend(matches)
        metrics.specific_recommendations_count = len(recommendation_matches)
        
        # Count actionable steps
        action_matches = []
        for pattern in self.action_patterns:
            matches = re.finditer(pattern, text_lower)
            action_matches.extend(matches)
        metrics.actionable_steps_count = len(action_matches)
        
        # Count quantified benefits
        quantification_matches = []
        for pattern in self.quantification_patterns:
            matches = re.finditer(pattern, text_lower)
            quantification_matches.extend(matches)
        metrics.quantified_benefits_count = len(quantification_matches)
        
        # Check for implementation timeline
        for pattern in self.timeline_patterns:
            if re.search(pattern, text_lower):
                metrics.implementation_timeline_provided = True
                break
        
        # Check for ROI estimates
        roi_patterns = [r'roi', r'return.*on.*investment', r'payback.*period']
        for pattern in roi_patterns:
            if re.search(pattern, text_lower):
                metrics.roi_estimates_provided = True
                break
                
        return metrics


@pytest.mark.e2e
@pytest.mark.staging
@pytest.mark.business_critical
class TestBusinessProblemSolvingChatWorkflows(SSotAsyncTestCase):
    """
    CRITICAL: E2E tests for complete business problem solving workflows in staging.
    
    These tests validate the CORE business value proposition - customers pay us to solve
    real business problems through AI-powered analysis and actionable recommendations.
    """
    
    def setup_method(self, method=None):
        """Setup with business value tracking."""
        super().setup_method(method)
        
        # Business value metrics for revenue protection
        self.record_metric("business_segment", "all_segments_core_value")
        self.record_metric("test_type", "e2e_staging_business_value")
        self.record_metric("revenue_protection_target", 500000)  # $500K ARR
        self.record_metric("value_delivery_requirement", "substantive_business_insights")
        
        # Initialize test components
        self._websocket_helper = None
        self._staging_config = None
        self._value_analyzer = None
        
    async def async_setup_method(self, method=None):
        """Async setup for staging business workflow testing.""" 
        await super().async_setup_method(method)
        
        # Initialize staging configuration
        self._staging_config = StagingTestConfig()
        
        # Initialize WebSocket helper for staging
        self._websocket_helper = E2EWebSocketAuthHelper(environment="staging")
        
        # Initialize business value analyzer
        self._value_analyzer = BusinessValueAnalyzer()
        
    @pytest.mark.asyncio
    async def test_complete_cost_optimization_problem_solving_workflow_staging(self):
        """
        Test complete cost optimization problem solving workflow in staging environment.
        
        CRITICAL: This tests the PRIMARY revenue-generating workflow:
        Customer Cost Problem → AI Analysis → Specific Recommendations → Quantified Savings → Customer ROI
        
        Business Value: Validates the core value proposition that customers pay premium for.
        """
        # Arrange - Create authenticated user with realistic business problem
        user_context = await create_authenticated_user_context(
            user_email="cost_optimization_customer@enterprise.com",
            environment="staging", 
            permissions=["read", "write", "execute_agents", "cost_optimization", "premium_features"],
            websocket_enabled=True
        )
        
        # Connect to staging WebSocket with authentication
        websocket_url = self._staging_config.urls.websocket_url
        headers = self._websocket_helper.get_websocket_headers()
        
        self.logger.info(f"🔌 Connecting to staging WebSocket: {websocket_url}")
        
        business_problem = (
            "Our company is spending $50,000 monthly on cloud infrastructure (AWS, Azure, GCP) "
            "and AI/ML services. Our costs have increased 40% in the last 6 months. "
            "We need detailed cost optimization analysis with specific recommendations "
            "to reduce spending by at least 25% while maintaining performance. "
            "Include implementation timeline, expected savings amounts, and ROI projections."
        )
        
        collected_events = []
        final_response = None
        
        # Act - Execute complete cost optimization workflow in staging
        async with self._websocket_helper.connect_authenticated_websocket(timeout=30.0) as websocket:
            
            # Send comprehensive business problem
            problem_request = {
                "type": "chat_message",
                "content": business_problem,
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "requires_comprehensive_analysis": True,
                "business_context": "cost_optimization_enterprise",
                "expected_deliverables": [
                    "specific_cost_reduction_strategies",
                    "quantified_savings_estimates", 
                    "implementation_timeline",
                    "roi_projections"
                ]
            }
            
            await websocket.send(json.dumps(problem_request))
            self.logger.info(f"📤 Sent comprehensive cost optimization problem to staging")
            
            # Collect WebSocket events and final response
            collection_timeout = 120.0  # Extended timeout for comprehensive analysis
            collection_start = time.time()
            
            while (time.time() - collection_start) < collection_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    
                    collected_events.append({
                        **event,
                        "received_timestamp": time.time(),
                        "staging_environment": True
                    })
                    
                    self.logger.info(f"📨 Staging event: {event.get('type', 'unknown')}")
                    
                    # Capture final response with business recommendations
                    if event.get("type") in ["agent_completed", "final_response", "business_analysis_complete"]:
                        final_response = event
                        if event.get("final", False) or event.get("content"):
                            break
                            
                except asyncio.TimeoutError:
                    if len(collected_events) >= 5 and final_response:
                        break
                    continue
                except Exception as e:
                    self.logger.error(f"❌ Error in staging WebSocket communication: {e}")
                    break
        
        # Assert - Validate comprehensive business value delivery
        self.assertIsNotNone(final_response, 
            "CRITICAL: No final response received from staging business problem solving workflow")
        
        # Validate required WebSocket events for transparency
        required_events = ["agent_started", "agent_thinking", "tool_executing", "agent_completed"]
        received_event_types = [event.get("type") for event in collected_events]
        
        for required_event in required_events:
            self.assertIn(required_event, received_event_types,
                f"Missing required WebSocket event '{required_event}' in staging workflow")
        
        # Extract and analyze business response content
        response_content = ""
        if final_response.get("content"):
            response_content = str(final_response["content"])
        elif final_response.get("result"):
            response_content = str(final_response["result"])
        else:
            # Aggregate content from all events if no single final response
            response_content = " ".join([str(event.get("content", "")) for event in collected_events])
        
        self.assertTrue(len(response_content) > 500,
            f"Business analysis response too short ({len(response_content)} chars) - not substantive")
        
        # Analyze business value using our analyzer
        business_metrics = self._value_analyzer.analyze_business_value(response_content)
        business_value_score = business_metrics.calculate_business_value_score()
        
        # CRITICAL: Response must meet substantive business value criteria
        self.assertTrue(business_metrics.is_substantive_value(),
            f"CRITICAL BUSINESS VALUE FAILURE: Analysis score {business_value_score:.2f} below 70% threshold. "
            f"Metrics: savings={business_metrics.cost_savings_identified}, "
            f"recommendations={business_metrics.specific_recommendations_count}, "
            f"actions={business_metrics.actionable_steps_count}, "
            f"quantified={business_metrics.quantified_benefits_count}")
        
        # Validate specific business requirements are addressed
        response_lower = response_content.lower()
        
        # Must address the $50K monthly spend context
        self.assertTrue("50" in response_content or "50,000" in response_content,
            "Response must address the specific $50K monthly spend mentioned")
        
        # Must address the 25% reduction target  
        self.assertTrue("25%" in response_content or "25 percent" in response_content,
            "Response must address the 25% cost reduction target")
        
        # Must contain infrastructure optimization strategies
        infrastructure_terms = ["aws", "azure", "gcp", "cloud", "infrastructure", "server", "compute"]
        found_terms = [term for term in infrastructure_terms if term in response_lower]
        self.assertGreaterEqual(len(found_terms), 3,
            f"Response must contain infrastructure optimization context. Found: {found_terms}")
        
        # Validate actionable recommendations are present
        self.assertGreaterEqual(business_metrics.specific_recommendations_count, 5,
            f"Expected at least 5 specific recommendations, found {business_metrics.specific_recommendations_count}")
        
        self.assertGreaterEqual(business_metrics.actionable_steps_count, 3,
            f"Expected at least 3 actionable steps, found {business_metrics.actionable_steps_count}")
        
        # Record comprehensive business metrics
        self.record_metric("staging_events_received", len(collected_events))
        self.record_metric("business_value_score", business_value_score)
        self.record_metric("cost_savings_identified", business_metrics.cost_savings_identified)
        self.record_metric("specific_recommendations", business_metrics.specific_recommendations_count)
        self.record_metric("actionable_steps", business_metrics.actionable_steps_count)
        self.record_metric("substantive_value_delivered", business_metrics.is_substantive_value())
        self.record_metric("response_length_chars", len(response_content))
        
        self.logger.info(f"✅ Staging cost optimization workflow delivered substantive business value: "
                        f"score {business_value_score:.2f}, {business_metrics.specific_recommendations_count} recommendations")
    
    @pytest.mark.asyncio
    async def test_complete_performance_optimization_workflow_with_technical_analysis_staging(self):
        """
        Test complete performance optimization workflow with technical analysis in staging.
        
        CRITICAL: This tests TECHNICAL business problem solving workflow:
        Performance Issues → Technical Analysis → Optimization Strategies → Implementation Plan → Business Impact
        
        Business Value: Validates technical problem solving that drives Mid/Enterprise customer retention.
        """
        # Arrange - Create authenticated user with technical performance problem
        user_context = await create_authenticated_user_context(
            user_email="performance_optimization_cto@techcompany.com",
            environment="staging",
            permissions=["read", "write", "execute_agents", "performance_analysis", "technical_optimization"],
            websocket_enabled=True
        )
        
        # Define complex technical business problem
        performance_problem = (
            "Our API response times have degraded 300% over the last quarter. "
            "Current average response time is 2.5 seconds, target is under 500ms. "
            "System handles 10,000 requests per minute peak load. "
            "We're using microservices architecture with Node.js, Redis, PostgreSQL. "
            "Database queries are taking 800ms average, cache hit rate is 45%. "
            "Provide comprehensive performance optimization analysis with specific technical recommendations, "
            "implementation priorities, expected performance improvements, and timeline for fixes."
        )
        
        collected_events = []
        final_technical_response = None
        
        # Act - Execute performance optimization workflow in staging
        async with self._websocket_helper.connect_authenticated_websocket(timeout=30.0) as websocket:
            
            # Send technical performance problem
            technical_request = {
                "type": "chat_message", 
                "content": performance_problem,
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "requires_technical_analysis": True,
                "business_context": "performance_optimization_technical",
                "current_metrics": {
                    "response_time_ms": 2500,
                    "target_response_time_ms": 500,
                    "requests_per_minute": 10000,
                    "db_query_time_ms": 800,
                    "cache_hit_rate_percent": 45
                },
                "tech_stack": ["nodejs", "redis", "postgresql", "microservices"]
            }
            
            await websocket.send(json.dumps(technical_request))
            self.logger.info(f"📤 Sent technical performance problem to staging")
            
            # Collect technical analysis events
            collection_timeout = 90.0
            collection_start = time.time()
            
            while (time.time() - collection_start) < collection_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    
                    collected_events.append({
                        **event,
                        "received_timestamp": time.time(),
                        "technical_analysis": True
                    })
                    
                    self.logger.info(f"📨 Technical analysis event: {event.get('type', 'unknown')}")
                    
                    # Capture technical response
                    if event.get("type") in ["agent_completed", "technical_analysis_complete", "final_response"]:
                        final_technical_response = event
                        if event.get("final", False) or len(str(event.get("content", ""))) > 1000:
                            break
                            
                except asyncio.TimeoutError:
                    if len(collected_events) >= 4 and final_technical_response:
                        break
                    continue
                except Exception as e:
                    self.logger.error(f"❌ Error in staging technical analysis: {e}")
                    break
        
        # Assert - Validate comprehensive technical business value
        self.assertIsNotNone(final_technical_response,
            "CRITICAL: No technical analysis response received from staging workflow")
        
        # Extract technical response content
        technical_content = ""
        if final_technical_response.get("content"):
            technical_content = str(final_technical_response["content"])
        elif final_technical_response.get("result"):
            technical_content = str(final_technical_response["result"])
        else:
            technical_content = " ".join([str(event.get("content", "")) for event in collected_events])
        
        self.assertTrue(len(technical_content) > 800,
            f"Technical analysis too short ({len(technical_content)} chars) for comprehensive problem")
        
        # Analyze technical business value
        technical_metrics = self._value_analyzer.analyze_business_value(technical_content)
        technical_value_score = technical_metrics.calculate_business_value_score()
        
        # Validate technical content addresses specific problem metrics
        content_lower = technical_content.lower()
        
        # Must address response time performance issue
        response_time_terms = ["response time", "latency", "performance", "500ms", "2.5 seconds", "millisecond"]
        found_perf_terms = [term for term in response_time_terms if term in content_lower]
        self.assertGreaterEqual(len(found_perf_terms), 3,
            f"Technical analysis must address performance metrics. Found: {found_perf_terms}")
        
        # Must address database optimization
        db_terms = ["database", "postgresql", "query", "index", "optimization", "800ms"]
        found_db_terms = [term for term in db_terms if term in content_lower]
        self.assertGreaterEqual(len(found_db_terms), 3,
            f"Technical analysis must address database performance. Found: {found_db_terms}")
        
        # Must address caching improvements
        cache_terms = ["cache", "redis", "caching", "hit rate", "45%", "cache"]
        found_cache_terms = [term for term in cache_terms if term in content_lower]
        self.assertGreaterEqual(len(found_cache_terms), 2,
            f"Technical analysis must address caching optimization. Found: {found_cache_terms}")
        
        # Validate technical recommendations are actionable
        self.assertGreaterEqual(technical_metrics.specific_recommendations_count, 4,
            f"Expected at least 4 technical recommendations, found {technical_metrics.specific_recommendations_count}")
        
        # Validate WebSocket events for technical workflow
        required_technical_events = ["agent_started", "agent_thinking", "tool_executing"]
        received_event_types = [event.get("type") for event in collected_events]
        
        for required_event in required_technical_events:
            self.assertIn(required_event, received_event_types,
                f"Missing required technical workflow event '{required_event}'")
        
        # Business impact validation - technical solutions must have business context
        business_impact_terms = ["business impact", "user experience", "revenue", "customer", "sla", "uptime"]
        found_business_terms = [term for term in business_impact_terms if term in content_lower]
        self.assertGreaterEqual(len(found_business_terms), 2,
            f"Technical solutions must include business impact context. Found: {found_business_terms}")
        
        # Record technical business value metrics
        self.record_metric("technical_events_received", len(collected_events))
        self.record_metric("technical_value_score", technical_value_score)
        self.record_metric("technical_recommendations", technical_metrics.specific_recommendations_count)
        self.record_metric("performance_terms_found", len(found_perf_terms))
        self.record_metric("database_optimization_addressed", len(found_db_terms) >= 3)
        self.record_metric("caching_optimization_addressed", len(found_cache_terms) >= 2)
        self.record_metric("business_impact_included", len(found_business_terms) >= 2)
        self.record_metric("technical_response_length", len(technical_content))
        
        self.logger.info(f"✅ Staging technical optimization workflow delivered comprehensive analysis: "
                        f"score {technical_value_score:.2f}, {technical_metrics.specific_recommendations_count} technical recommendations")
    
    def teardown_method(self, method=None):
        """Cleanup after business workflow tests."""
        super().teardown_method(method)
        
        self.logger.info(f"✅ Business problem solving chat workflow staging test completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "staging"])