#!/usr/bin/env python
"""
E2E Staging Tests for WebSocket Business Value Validation

MISSION CRITICAL: Business value validation through WebSocket chat experiences.
Tests substantive AI value delivery through complete chat workflows in staging.

Business Value: $500K+ ARR - Validation of AI value delivery mechanisms
- Tests complete business value chains through WebSocket chat
- Validates revenue-generating AI interactions and outcomes
- Ensures chat delivers actionable insights and measurable business results
"""

import asyncio
import json
import pytest
import re
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

# SSOT imports following CLAUDE.md guidelines
from shared.types.core_types import WebSocketEventType, UserID, ThreadID, RequestID
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType as TestEventType
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

# Import production components - NO MOCKS per CLAUDE.md
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.fixture
async def business_value_websocket_utility():
    """Create WebSocket utility for business value testing."""
    staging_ws_url = "wss://staging.netra-apex.com/ws"
    
    async with WebSocketTestUtility(base_url=staging_ws_url) as ws_util:
        yield ws_util


@pytest.fixture
def business_value_auth_helper():
    """Create authentication helper for business value testing."""
    return E2EAuthHelper(environment="staging")


class BusinessValueValidator:
    """Validates business value indicators in AI responses."""
    
    @staticmethod
    def extract_cost_savings(text: str) -> List[Dict[str, Any]]:
        """Extract cost savings mentions from text."""
        savings_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:per\s+month|monthly|/month)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*%\s*(?:savings?|reduction)',
            r'save\s+\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'reduce\s+costs?\s+by\s+\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        ]
        
        savings = []
        for pattern in savings_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                savings.append({
                    "value": match.group(1),
                    "context": match.group(0),
                    "type": "cost_savings"
                })
        
        return savings
    
    @staticmethod
    def extract_actionable_recommendations(text: str) -> List[str]:
        """Extract actionable recommendations from text."""
        recommendation_patterns = [
            r'(?:recommend|suggest|should|consider)\s+([^.!?]*[.!?])',
            r'(?:action\s+item|next\s+step|to\s+do):\s*([^.!?]*[.!?])',
            r'(?:implement|execute|perform)\s+([^.!?]*[.!?])'
        ]
        
        recommendations = []
        for pattern in recommendation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                recommendation = match.group(1).strip()
                if len(recommendation) > 10:  # Filter out short matches
                    recommendations.append(recommendation)
        
        return recommendations
    
    @staticmethod
    def assess_business_value_score(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess business value score of AI response."""
        score = 0
        indicators = []
        response_text = json.dumps(response_data).lower()
        
        # Cost optimization indicators (high value)
        cost_keywords = ['cost', 'saving', 'reduce', 'optimize', 'efficiency', 'budget']
        cost_score = sum(5 for keyword in cost_keywords if keyword in response_text)
        score += min(cost_score, 25)  # Cap at 25 points
        
        if cost_score > 0:
            indicators.append("cost_optimization")
        
        # Actionable insights (high value)
        action_keywords = ['recommend', 'implement', 'action', 'step', 'improve', 'strategy']
        action_score = sum(4 for keyword in action_keywords if keyword in response_text)
        score += min(action_score, 20)  # Cap at 20 points
        
        if action_score > 0:
            indicators.append("actionable_insights")
        
        # Quantified results (medium value)
        number_patterns = [r'\d+%', r'\$\d+', r'\d+\s*hours?', r'\d+\s*days?']
        quantified_score = 0
        for pattern in number_patterns:
            if re.search(pattern, response_text):
                quantified_score += 3
        score += min(quantified_score, 15)  # Cap at 15 points
        
        if quantified_score > 0:
            indicators.append("quantified_results")
        
        # Technical depth (medium value)
        technical_keywords = ['infrastructure', 'architecture', 'database', 'performance', 'scalability']
        technical_score = sum(2 for keyword in technical_keywords if keyword in response_text)
        score += min(technical_score, 10)  # Cap at 10 points
        
        if technical_score > 0:
            indicators.append("technical_depth")
        
        # Timeliness (low value but important)
        time_keywords = ['immediate', 'quick', 'urgent', 'priority', 'timeline']
        time_score = sum(1 for keyword in time_keywords if keyword in response_text)
        score += min(time_score, 5)  # Cap at 5 points
        
        if time_score > 0:
            indicators.append("timeliness")
        
        return {
            "score": score,
            "max_score": 75,
            "percentage": (score / 75) * 100,
            "indicators": indicators,
            "business_value": "high" if score >= 50 else "medium" if score >= 25 else "low"
        }


@pytest.mark.e2e
@pytest.mark.staging
class TestStagingWebSocketBusinessValue:
    """E2E tests for business value delivery through WebSocket chat."""
    
    @pytest.mark.asyncio
    async def test_cost_optimization_business_value_delivery(self, business_value_websocket_utility, business_value_auth_helper):
        """
        Test complete cost optimization business value delivery through chat.
        
        CRITICAL: This validates the core revenue-generating capability.
        Users must receive actionable cost optimization insights worth their subscription fee.
        """
        # Arrange - Create enterprise user focused on cost optimization
        auth_result = await business_value_auth_helper.create_authenticated_user(
            user_id=f"enterprise_cost_optimizer_{uuid.uuid4().hex[:8]}",
            permissions=["chat_access", "enterprise_features", "cost_optimization"],
            subscription_tier="enterprise",
            use_case="cost_optimization"
        )
        
        user_context = UserExecutionContext(
            user_id=UserID(auth_result["user_id"]),
            thread_id=ThreadID(f"cost_opt_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"cost_opt_request_{uuid.uuid4().hex[:8]}"),
            session_id=auth_result["session_id"]
        )
        
        auth_headers = {
            "Authorization": f"Bearer {auth_result['access_token']}",
            "X-User-ID": auth_result["user_id"],
            "X-Subscription-Tier": "enterprise"
        }
        
        async with business_value_websocket_utility.connected_client(user_context.user_id) as client:
            client.headers = auth_headers
            await client.connect(timeout=60.0)
            
            # Act - Request high-value cost optimization analysis
            cost_optimization_request = {
                "content": """I'm spending $50,000/month on cloud infrastructure and need to optimize costs. 
                            Our main expenses are:
                            - Compute: $30,000/month (lots of idle instances)
                            - Storage: $15,000/month (mixed data types)
                            - Network: $5,000/month (data transfer costs)
                            
                            Please analyze this and provide specific recommendations with estimated savings.""",
                "business_context": {
                    "monthly_spend": 50000,
                    "urgency": "high",
                    "optimization_goals": ["reduce_costs", "maintain_performance", "improve_efficiency"]
                },
                "expected_value": "cost_reduction_recommendations",
                "timestamp": datetime.now().isoformat()
            }
            
            await client.send_message(
                TestEventType.MESSAGE_CREATED,
                cost_optimization_request,
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id)
            )
            
            # Wait for complete business value delivery workflow
            business_value_events = []
            optimization_results = None
            
            # Monitor for business value delivery
            monitoring_timeout = 180.0  # 3 minutes for thorough analysis
            start_time = time.time()
            
            while time.time() - start_time < monitoring_timeout:
                try:
                    event = await client.wait_for_message(timeout=30.0)
                    if event:
                        business_value_events.append(event)
                        
                        # Look for final optimization results
                        if event.event_type == TestEventType.AGENT_COMPLETED:
                            optimization_results = event.data.get("result")
                            break
                        
                        # Also check tool_completed for optimization analysis
                        if (event.event_type == TestEventType.TOOL_COMPLETED and 
                            event.data.get("tool") and 
                            "optimization" in event.data.get("tool", "").lower()):
                            
                            tool_result = event.data.get("result")
                            if tool_result and not optimization_results:
                                optimization_results = tool_result
                
                except asyncio.TimeoutError:
                    print(f"Waiting for optimization results... {time.time() - start_time:.0f}s elapsed")
                    continue
            
            # Assert business value delivery
            assert len(business_value_events) >= 3, f"Must receive substantial business value workflow, got {len(business_value_events)} events"
            assert optimization_results is not None, "Must receive concrete optimization results"
            
            # Validate business value content
            validator = BusinessValueValidator()
            
            # Extract cost savings
            results_text = json.dumps(optimization_results)
            cost_savings = validator.extract_cost_savings(results_text)
            assert len(cost_savings) > 0, "Must identify specific cost savings opportunities"
            
            # Extract actionable recommendations
            recommendations = validator.extract_actionable_recommendations(results_text)
            assert len(recommendations) >= 2, f"Must provide actionable recommendations, got {len(recommendations)}"
            
            # Assess overall business value score
            business_value_assessment = validator.assess_business_value_score(optimization_results)
            assert business_value_assessment["percentage"] >= 60, f"Business value score must be >= 60%, got {business_value_assessment['percentage']:.1f}%"
            
            # Verify enterprise-level insights
            enterprise_indicators = [
                "roi", "return on investment", "business impact", "strategic", 
                "scalability", "enterprise", "implementation plan"
            ]
            
            enterprise_score = sum(1 for indicator in enterprise_indicators 
                                 if indicator in results_text.lower())
            assert enterprise_score >= 2, f"Must provide enterprise-level insights, got {enterprise_score} indicators"
            
            # Verify actionable timeline
            timeline_indicators = ["immediate", "short-term", "long-term", "weeks", "months", "priority"]
            timeline_score = sum(1 for indicator in timeline_indicators 
                                if indicator in results_text.lower())
            assert timeline_score >= 1, "Must provide implementation timeline guidance"
            
            print(f"✅ Cost optimization business value validated")
            print(f"   Events received: {len(business_value_events)}")
            print(f"   Cost savings identified: {len(cost_savings)}")
            print(f"   Recommendations provided: {len(recommendations)}")
            print(f"   Business value score: {business_value_assessment['percentage']:.1f}%")
            print(f"   Enterprise indicators: {enterprise_score}")
    
    @pytest.mark.asyncio
    async def test_data_optimization_roi_validation(self, business_value_websocket_utility, business_value_auth_helper):
        """
        Test data optimization ROI validation through WebSocket chat.
        
        CRITICAL: Data optimization must demonstrate clear ROI for business justification.
        Users need quantified benefits to justify AI platform subscription costs.
        """
        # Arrange - Create data-focused enterprise user
        auth_result = await business_value_auth_helper.create_authenticated_user(
            user_id=f"data_optimization_user_{uuid.uuid4().hex[:8]}",
            permissions=["chat_access", "data_optimization", "roi_analysis"],
            subscription_tier="enterprise",
            use_case="data_optimization"
        )
        
        user_context = UserExecutionContext(
            user_id=UserID(auth_result["user_id"]),
            thread_id=ThreadID(f"data_opt_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"data_opt_request_{uuid.uuid4().hex[:8]}"),
            session_id=auth_result["session_id"]
        )
        
        auth_headers = {
            "Authorization": f"Bearer {auth_result['access_token']}",
            "X-User-ID": auth_result["user_id"],
            "X-Use-Case": "data_optimization"
        }
        
        async with business_value_websocket_utility.connected_client(user_context.user_id) as client:
            client.headers = auth_headers
            await client.connect(timeout=60.0)
            
            # Act - Request data optimization with ROI focus
            data_optimization_request = {
                "content": """Our data pipeline is inefficient and expensive:
                            - Processing 10TB daily with 4-hour latency
                            - Running costs: $25,000/month
                            - Data quality issues causing 20% rework
                            - Storage costs growing 15% monthly
                            
                            I need specific optimization recommendations with ROI calculations. 
                            What improvements would give us the best return on investment?""",
                "business_metrics": {
                    "daily_data_volume": "10TB",
                    "current_latency": "4 hours",
                    "monthly_costs": 25000,
                    "rework_percentage": 20,
                    "cost_growth_rate": 15
                },
                "roi_requirements": {
                    "payback_period": "12 months",
                    "minimum_roi": "25%",
                    "cost_reduction_target": "30%"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await client.send_message(
                TestEventType.MESSAGE_CREATED,
                data_optimization_request,
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id)
            )
            
            # Wait for ROI-focused analysis
            roi_analysis_events = []
            roi_results = None
            
            analysis_timeout = 180.0  # 3 minutes for thorough ROI analysis
            start_time = time.time()
            
            while time.time() - start_time < analysis_timeout:
                try:
                    event = await client.wait_for_message(timeout=30.0)
                    if event:
                        roi_analysis_events.append(event)
                        
                        # Look for ROI analysis completion
                        if event.event_type == TestEventType.AGENT_COMPLETED:
                            roi_results = event.data.get("result")
                            break
                        
                        # Check for data optimization tool results
                        if (event.event_type == TestEventType.TOOL_COMPLETED and 
                            event.data.get("tool") and 
                            any(keyword in event.data.get("tool", "").lower() 
                                for keyword in ["data", "optimization", "analysis", "roi"])):
                            
                            tool_result = event.data.get("result")
                            if tool_result and not roi_results:
                                roi_results = tool_result
                
                except asyncio.TimeoutError:
                    print(f"Waiting for ROI analysis... {time.time() - start_time:.0f}s elapsed")
                    continue
            
            # Assert ROI validation
            assert len(roi_analysis_events) >= 3, f"Must receive comprehensive ROI analysis workflow"
            assert roi_results is not None, "Must receive concrete ROI analysis results"
            
            # Validate ROI content
            validator = BusinessValueValidator()
            results_text = json.dumps(roi_results).lower()
            
            # Check for ROI calculations
            roi_indicators = [
                r'roi\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%',
                r'return\s+on\s+investment[:\-]?\s*(\d+(?:\.\d+)?)\s*%',
                r'payback\s+period[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:months?|years?)',
                r'cost\s+reduction[:\-]?\s*(\d+(?:\.\d+)?)\s*%'
            ]
            
            roi_calculations = []
            for pattern in roi_indicators:
                matches = re.finditer(pattern, results_text)
                roi_calculations.extend([match.group(0) for match in matches])
            
            assert len(roi_calculations) > 0, f"Must provide quantified ROI calculations, found: {roi_calculations}"
            
            # Check for data optimization specifics
            data_optimization_indicators = [
                "latency", "throughput", "efficiency", "pipeline", "processing", 
                "storage", "compression", "caching", "indexing", "partitioning"
            ]
            
            data_optimization_score = sum(1 for indicator in data_optimization_indicators 
                                        if indicator in results_text)
            assert data_optimization_score >= 4, f"Must provide data-specific optimizations, got {data_optimization_score} indicators"
            
            # Validate business impact quantification
            business_impact_patterns = [
                r'\$\d{1,3}(?:,\d{3})*\s*(?:savings?|reduction)',
                r'\d+(?:\.\d+)?%\s*(?:improvement|reduction|increase)',
                r'\d+(?:\.\d+)?\s*(?:hours?|minutes?)\s*(?:faster|reduction|improvement)'
            ]
            
            quantified_impacts = []
            for pattern in business_impact_patterns:
                matches = re.finditer(pattern, results_text)
                quantified_impacts.extend([match.group(0) for match in matches])
            
            assert len(quantified_impacts) >= 2, f"Must quantify business impact, found: {quantified_impacts}"
            
            # Assess comprehensive business value
            business_value_assessment = validator.assess_business_value_score(roi_results)
            assert business_value_assessment["percentage"] >= 65, f"ROI analysis must score >= 65%, got {business_value_assessment['percentage']:.1f}%"
            
            print(f"✅ Data optimization ROI validation completed")
            print(f"   Analysis events: {len(roi_analysis_events)}")
            print(f"   ROI calculations found: {len(roi_calculations)}")
            print(f"   Data optimization indicators: {data_optimization_score}")
            print(f"   Quantified impacts: {len(quantified_impacts)}")
            print(f"   Business value score: {business_value_assessment['percentage']:.1f}%")
    
    @pytest.mark.asyncio
    async def test_enterprise_strategic_planning_value_delivery(self, business_value_websocket_utility, business_value_auth_helper):
        """
        Test enterprise strategic planning value delivery through WebSocket chat.
        
        CRITICAL: Strategic planning features justify enterprise subscription tiers.
        Must deliver comprehensive strategic insights worth premium pricing.
        """
        # Arrange - Create enterprise strategic planning user
        auth_result = await business_value_auth_helper.create_authenticated_user(
            user_id=f"enterprise_strategy_user_{uuid.uuid4().hex[:8]}",
            permissions=["chat_access", "enterprise_features", "strategic_planning", "executive_insights"],
            subscription_tier="enterprise_plus",
            use_case="strategic_planning"
        )
        
        user_context = UserExecutionContext(
            user_id=UserID(auth_result["user_id"]),
            thread_id=ThreadID(f"strategy_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"strategy_request_{uuid.uuid4().hex[:8]}"),
            session_id=auth_result["session_id"]
        )
        
        auth_headers = {
            "Authorization": f"Bearer {auth_result['access_token']}",
            "X-User-ID": auth_result["user_id"],
            "X-Subscription-Tier": "enterprise_plus",
            "X-Executive-Access": "true"
        }
        
        async with business_value_websocket_utility.connected_client(user_context.user_id) as client:
            client.headers = auth_headers
            await client.connect(timeout=60.0)
            
            # Act - Request strategic planning analysis
            strategic_planning_request = {
                "content": """I need comprehensive strategic planning for our AI infrastructure optimization:
                            
                            Current State:
                            - $2M annual cloud spend across 5 business units
                            - 40% cost increase year-over-year
                            - Inconsistent optimization practices
                            - No centralized cost management
                            
                            Strategic Goals:
                            - Reduce costs by 25% in 18 months
                            - Standardize infrastructure across units
                            - Implement FinOps practices
                            - Prepare for 100% growth scaling
                            
                            Please provide a comprehensive strategic plan with:
                            1. Multi-year optimization roadmap
                            2. Risk analysis and mitigation strategies
                            3. Investment requirements and ROI projections
                            4. Implementation timeline with milestones
                            5. Success metrics and KPIs""",
                "strategic_context": {
                    "annual_spend": 2000000,
                    "growth_rate": 40,
                    "cost_reduction_target": 25,
                    "timeline": "18 months",
                    "business_units": 5,
                    "scaling_requirement": "100% growth"
                },
                "deliverable_requirements": [
                    "multi_year_roadmap",
                    "risk_analysis", 
                    "roi_projections",
                    "implementation_timeline",
                    "success_metrics"
                ],
                "timestamp": datetime.now().isoformat()
            }
            
            await client.send_message(
                TestEventType.MESSAGE_CREATED,
                strategic_planning_request,
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id)
            )
            
            # Wait for comprehensive strategic analysis
            strategic_events = []
            strategic_plan = None
            
            planning_timeout = 240.0  # 4 minutes for comprehensive strategic planning
            start_time = time.time()
            
            while time.time() - start_time < planning_timeout:
                try:
                    event = await client.wait_for_message(timeout=45.0)
                    if event:
                        strategic_events.append(event)
                        
                        # Look for strategic planning completion
                        if event.event_type == TestEventType.AGENT_COMPLETED:
                            strategic_plan = event.data.get("result")
                            break
                        
                        # Check for strategic analysis tools
                        if (event.event_type == TestEventType.TOOL_COMPLETED and 
                            event.data.get("tool") and 
                            any(keyword in event.data.get("tool", "").lower() 
                                for keyword in ["strategic", "planning", "roadmap", "analysis"])):
                            
                            tool_result = event.data.get("result")
                            if tool_result and not strategic_plan:
                                strategic_plan = tool_result
                
                except asyncio.TimeoutError:
                    print(f"Waiting for strategic planning... {time.time() - start_time:.0f}s elapsed")
                    continue
            
            # Assert strategic value delivery
            assert len(strategic_events) >= 5, f"Must receive comprehensive strategic planning workflow"
            assert strategic_plan is not None, "Must receive detailed strategic plan"
            
            # Validate strategic planning content
            validator = BusinessValueValidator()
            plan_text = json.dumps(strategic_plan).lower()
            
            # Check for required strategic components
            required_components = [
                "roadmap", "timeline", "milestone", "risk", "mitigation",
                "roi", "investment", "kpi", "metric", "success"
            ]
            
            component_score = sum(1 for component in required_components if component in plan_text)
            assert component_score >= 7, f"Must include strategic planning components, got {component_score}/10"
            
            # Validate executive-level insights
            executive_indicators = [
                "strategic", "competitive", "market", "business", "executive",
                "leadership", "governance", "transformation", "innovation"
            ]
            
            executive_score = sum(1 for indicator in executive_indicators if indicator in plan_text)
            assert executive_score >= 4, f"Must provide executive-level insights, got {executive_score} indicators"
            
            # Check for multi-year planning
            timeline_indicators = [
                r'(\d+)\s*(?:year|month)', r'q[1-4]', r'quarter', r'phase\s+\d+',
                r'milestone', r'deadline', r'timeline'
            ]
            
            timeline_mentions = []
            for pattern in timeline_indicators:
                matches = re.finditer(pattern, plan_text)
                timeline_mentions.extend([match.group(0) for match in matches])
            
            assert len(timeline_mentions) >= 3, f"Must include detailed timeline planning, found: {len(timeline_mentions)}"
            
            # Validate financial projections
            financial_patterns = [
                r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?[mk]?',  # Dollar amounts
                r'\d+(?:\.\d+)?%\s*(?:savings?|reduction|roi|return)',  # Percentages
                r'payback\s+period',
                r'break[\-\s]?even'
            ]
            
            financial_projections = []
            for pattern in financial_patterns:
                matches = re.finditer(pattern, plan_text)
                financial_projections.extend([match.group(0) for match in matches])
            
            assert len(financial_projections) >= 3, f"Must include financial projections, found: {len(financial_projections)}"
            
            # Assess overall strategic value
            business_value_assessment = validator.assess_business_value_score(strategic_plan)
            assert business_value_assessment["percentage"] >= 70, f"Strategic plan must score >= 70%, got {business_value_assessment['percentage']:.1f}%"
            
            # Validate premium value indicators (enterprise plus features)
            premium_indicators = [
                "enterprise", "scale", "governance", "compliance", "integration",
                "automation", "orchestration", "optimization", "transformation"
            ]
            
            premium_score = sum(1 for indicator in premium_indicators if indicator in plan_text)
            assert premium_score >= 5, f"Must justify premium pricing with enterprise features, got {premium_score}"
            
            print(f"✅ Enterprise strategic planning value validated")
            print(f"   Strategic events: {len(strategic_events)}")
            print(f"   Strategic components: {component_score}/10")
            print(f"   Executive insights: {executive_score}")
            print(f"   Timeline planning: {len(timeline_mentions)}")
            print(f"   Financial projections: {len(financial_projections)}")
            print(f"   Business value score: {business_value_assessment['percentage']:.1f}%")
            print(f"   Premium value indicators: {premium_score}")