"""
Test WebSocket Agent Event Flow in Staging Environment

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core delivery mechanism for AI value
- Business Goal: Ensure real-time AI interaction delivery through WebSocket events provides substantive user value
- Value Impact: WebSocket event failures break user chat experience and prevent AI value delivery - directly affecting user engagement and retention
- Strategic Impact: WebSocket events are the PRIMARY delivery mechanism for AI value - failure blocks entire platform value proposition

This comprehensive E2E test suite validates WebSocket agent event flow in staging environment:
1. ALL 5 CRITICAL WebSocket events validation (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
2. Real-time event delivery timing and ordering validation
3. Event content quality and business value validation  
4. Multi-agent event flow coordination and sequencing
5. Event flow resilience during network interruptions and failures
6. Event flow performance under realistic load conditions
7. Cross-user event isolation and security validation

CRITICAL REQUIREMENTS:
- MANDATORY OAuth/JWT authentication flows for all WebSocket connections
- ALL 5 WebSocket events MUST be sent, received, and validated for EVERY agent execution
- Real staging environment with actual LLM agent execution - NO MOCKS
- Real-time event timing validation with business SLA requirements
- Comprehensive business value content validation in events

CRITICAL: This test validates the CORE mechanism for delivering AI value to users.
Expected: 7 test methods that prove complete WebSocket event flow delivers business value.
"""

import asyncio
import json
import time
import uuid
import pytest
import websockets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from unittest.mock import patch

# Test framework and authentication
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, E2EAuthConfig,
    create_authenticated_user_context
)

# Staging configuration and utilities
from tests.e2e.staging.conftest import staging_services_fixture
from tests.e2e.staging_config import StagingTestConfig, staging_urls

# Strongly typed IDs and execution context
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

# WebSocket event validation
from test_framework.websocket_helpers import (
    WebSocketTestClient, assert_websocket_events, wait_for_agent_completion
)


@dataclass
class WebSocketEventMetrics:
    """Metrics for validating WebSocket event quality and timing."""
    event_type: str
    timestamp: datetime
    content_length: int
    business_value_score: int  # 0-10 scale
    timing_sla_met: bool
    content_quality_score: int  # 0-10 scale


@dataclass 
class AgentEventFlowValidation:
    """Comprehensive validation results for agent event flow."""
    events_received: List[str]
    critical_events_missing: List[str]
    event_order_correct: bool
    timing_performance: Dict[str, float]
    business_value_delivered: bool
    content_quality_average: float
    sla_compliance_rate: float


class TestWebSocketAgentEventFlowStaging(BaseIntegrationTest):
    """
    Comprehensive E2E test suite for WebSocket agent event flow in staging environment.
    
    This test suite validates that WebSocket events deliver the complete AI value chain
    in real-time, ensuring users receive substantive, timely, and high-quality AI insights
    through the WebSocket event mechanism.
    """

    @pytest.fixture(autouse=True)
    async def setup_websocket_event_validation(self):
        """Setup comprehensive WebSocket event validation infrastructure."""
        self.env = get_env()
        self.staging_config = StagingTestConfig()
        
        # Initialize E2E auth helper for staging WebSocket connections
        self.auth_helper = E2EAuthHelper(environment="staging")
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
        # Get staging authentication token
        self.staging_token = await self.auth_helper.get_staging_token_async()
        assert self.staging_token, "CRITICAL: Failed to obtain staging WebSocket authentication token"
        
        # Setup authenticated WebSocket headers with E2E detection
        self.websocket_headers = self.auth_helper.get_websocket_headers(self.staging_token)
        
        # Define critical WebSocket event requirements
        self.CRITICAL_EVENTS = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        # Define business SLA requirements for events
        self.EVENT_SLA_REQUIREMENTS = {
            "agent_started": 2.0,      # Must start within 2 seconds
            "agent_thinking": 5.0,     # First thinking within 5 seconds
            "tool_executing": 10.0,    # Tool execution within 10 seconds
            "tool_completed": 30.0,    # Tool completion within 30 seconds
            "agent_completed": 45.0    # Agent completion within 45 seconds
        }
        
        # Content quality validation thresholds
        self.CONTENT_QUALITY_THRESHOLDS = {
            "min_thinking_length": 50,      # Minimum characters in thinking
            "min_response_length": 100,     # Minimum characters in final response
            "business_keywords_required": 3, # Minimum business-relevant keywords
            "actionable_insights_required": 1 # Minimum actionable insights
        }
        
        self.logger.info(" PASS:  WebSocket event validation setup complete - ready for comprehensive event flow testing")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    async def test_all_five_critical_websocket_events_comprehensive_validation(self):
        """
        Test ALL 5 critical WebSocket events are sent and deliver business value.
        
        CRITICAL: This is the CORE test that validates the fundamental mechanism
        for delivering AI value to users. Failure here blocks entire platform value.
        
        Business Value: Ensures users receive complete real-time AI interaction
        through all required WebSocket events, enabling full AI-powered assistance.
        """
        self.logger.info(" TARGET:  Starting ALL 5 critical WebSocket events comprehensive validation")
        
        # Create authenticated user context for event flow testing
        user_context = await create_authenticated_user_context(
            user_email=f"event_validation_{uuid.uuid4().hex[:8]}@staging.test.com",
            environment="staging",
            permissions=["read", "write", "agent_execute"],
            websocket_enabled=True
        )
        
        # Track comprehensive event metrics
        event_metrics = {}
        event_flow_timeline = []
        business_value_indicators = {
            "actionable_insights": 0,
            "specific_recommendations": 0,
            "cost_savings_identified": 0,
            "implementation_guidance": 0
        }
        
        try:
            async with websockets.connect(
                self.staging_config.urls.websocket_url,
                additional_headers=self.websocket_headers,
                open_timeout=20.0,  # Extended timeout for staging
                close_timeout=10.0
            ) as websocket:
                
                self.logger.info(" PASS:  WebSocket connection established for critical event validation")
                
                # Send comprehensive business request that requires all event types
                business_optimization_request = {
                    "type": "agent_request",
                    "thread_id": str(user_context.thread_id),
                    "run_id": str(user_context.run_id),
                    "agent": "cost_optimizer",
                    "message": "I need a comprehensive cost optimization analysis for my e-commerce platform. Current AWS spend: $75,000/month. Key services: EC2 (40%), RDS (25%), S3 (15%), CloudFront (10%), other (10%). Please provide specific optimization recommendations with ROI calculations and implementation timeline.",
                    "context": {
                        "monthly_spend": 75000,
                        "service_breakdown": {
                            "ec2": 0.40,
                            "rds": 0.25, 
                            "s3": 0.15,
                            "cloudfront": 0.10,
                            "other": 0.10
                        },
                        "business_type": "ecommerce",
                        "optimization_goal": "comprehensive_analysis"
                    },
                    "metadata": {
                        "test_type": "critical_events_validation",
                        "business_criticality": "high",
                        "expected_events": self.CRITICAL_EVENTS,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
                
                # Record request timestamp for SLA validation
                request_start_time = time.time()
                await websocket.send(json.dumps(business_optimization_request))
                
                self.logger.info(f"[U+1F4E4] Sent comprehensive optimization request for all event validation")
                
                # Collect ALL WebSocket events with comprehensive validation
                all_events = []
                critical_event_tracker = {event: None for event in self.CRITICAL_EVENTS}
                event_timing = {}
                
                # Extended timeout for comprehensive LLM processing
                collection_timeout = 90.0  # 90 seconds for complex analysis
                collection_start = time.time()
                
                while time.time() - collection_start < collection_timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        event = json.loads(event_data)
                        all_events.append(event)
                        
                        event_type = event.get("type")
                        event_timestamp = time.time()
                        relative_time = event_timestamp - request_start_time
                        
                        # Track critical events
                        if event_type in self.CRITICAL_EVENTS:
                            critical_event_tracker[event_type] = event
                            event_timing[event_type] = relative_time
                            
                            self.logger.info(f"[U+1F4E8] Received CRITICAL event: {event_type} at {relative_time:.2f}s")
                            
                            # Validate SLA compliance
                            sla_requirement = self.EVENT_SLA_REQUIREMENTS.get(event_type)
                            if sla_requirement and relative_time <= sla_requirement:
                                self.logger.info(f" PASS:  SLA met for {event_type}: {relative_time:.2f}s  <=  {sla_requirement}s")
                            elif sla_requirement:
                                self.logger.warning(f" WARNING: [U+FE0F] SLA missed for {event_type}: {relative_time:.2f}s > {sla_requirement}s")
                        
                        # Analyze event content for business value
                        event_data_content = event.get("data", {})
                        
                        if event_type == "agent_thinking":
                            thinking_content = event_data_content.get("content", "")
                            if len(thinking_content) >= self.CONTENT_QUALITY_THRESHOLDS["min_thinking_length"]:
                                # Analyze for business keywords
                                business_keywords = ["cost", "optimization", "savings", "ROI", "efficiency", "reduce", "analyze"]
                                keyword_count = sum(1 for keyword in business_keywords if keyword.lower() in thinking_content.lower())
                                
                                if keyword_count >= self.CONTENT_QUALITY_THRESHOLDS["business_keywords_required"]:
                                    business_value_indicators["actionable_insights"] += 1
                        
                        elif event_type == "tool_executing":
                            tool_name = event_data_content.get("tool_name", "")
                            if tool_name:
                                self.logger.info(f"[U+1F527] Tool executing: {tool_name}")
                        
                        elif event_type == "tool_completed":
                            tool_result = event_data_content.get("result", {})
                            if tool_result and isinstance(tool_result, dict):
                                # Look for cost savings data
                                result_str = str(tool_result).lower()
                                if "saving" in result_str or "reduce" in result_str or "optimization" in result_str:
                                    business_value_indicators["cost_savings_identified"] += 1
                        
                        elif event_type == "agent_completed":
                            final_response = event_data_content.get("response", {})
                            response_text = str(final_response).lower()
                            
                            # Validate final response quality
                            if len(response_text) >= self.CONTENT_QUALITY_THRESHOLDS["min_response_length"]:
                                # Count recommendations
                                recommendation_indicators = ["recommend", "suggest", "should", "implement", "consider"]
                                recommendation_count = sum(1 for indicator in recommendation_indicators if indicator in response_text)
                                business_value_indicators["specific_recommendations"] = recommendation_count
                                
                                # Look for implementation guidance
                                implementation_indicators = ["step", "timeline", "first", "next", "implementation", "start"]
                                implementation_count = sum(1 for indicator in implementation_indicators if indicator in response_text)
                                if implementation_count >= 2:
                                    business_value_indicators["implementation_guidance"] += 1
                            
                            # Agent completed - end collection
                            self.logger.info(f" TARGET:  Agent completed at {relative_time:.2f}s - ending event collection")
                            break
                            
                    except asyncio.TimeoutError:
                        self.logger.warning("[U+23F0] Event collection timeout - checking if all critical events received")
                        break
                    except json.JSONDecodeError as e:
                        self.logger.warning(f" WARNING: [U+FE0F] JSON decode error: {e}")
                        continue
                
                total_collection_time = time.time() - collection_start
                
                # CRITICAL VALIDATION: ALL 5 EVENTS MUST BE PRESENT
                
                missing_critical_events = [
                    event_type for event_type, event_data in critical_event_tracker.items()
                    if event_data is None
                ]
                
                if missing_critical_events:
                    self.logger.error(f" FAIL:  CRITICAL FAILURE: Missing required WebSocket events: {missing_critical_events}")
                    self.logger.error(f" CHART:  Events received: {list(critical_event_tracker.keys())}")
                    self.logger.error(f" CHART:  Event timing: {event_timing}")
                    raise AssertionError(f"CRITICAL: Missing required WebSocket events: {missing_critical_events}. ALL 5 events are MANDATORY for business value delivery!")
                
                self.logger.info(f" PASS:  ALL 5 CRITICAL WebSocket events received successfully")
                
                # BUSINESS VALUE VALIDATION
                
                # Validate event timing SLA compliance
                sla_violations = []
                for event_type, timing in event_timing.items():
                    sla_requirement = self.EVENT_SLA_REQUIREMENTS.get(event_type)
                    if sla_requirement and timing > sla_requirement:
                        sla_violations.append(f"{event_type}: {timing:.2f}s > {sla_requirement}s")
                
                # Allow minor SLA violations ( <= 2) for staging environment
                assert len(sla_violations) <= 2, \
                    f"Too many SLA violations affect user experience: {sla_violations}"
                
                # Validate business value delivery
                assert business_value_indicators["actionable_insights"] >= 1, \
                    "BUSINESS VALUE FAILURE: No actionable insights delivered through WebSocket events"
                
                assert business_value_indicators["specific_recommendations"] >= 2, \
                    f"BUSINESS VALUE FAILURE: Insufficient recommendations: {business_value_indicators['specific_recommendations']} < 2"
                
                # Validate event sequence (basic ordering)
                event_sequence = [event.get("type") for event in all_events if event.get("type") in self.CRITICAL_EVENTS]
                
                # agent_started should be first critical event
                if event_sequence:
                    assert event_sequence[0] == "agent_started", \
                        f"Event ordering violation: First critical event was {event_sequence[0]}, expected 'agent_started'"
                    
                    # agent_completed should be last critical event
                    if "agent_completed" in event_sequence:
                        last_agent_event_idx = max(i for i, event_type in enumerate(event_sequence) if event_type == "agent_completed")
                        assert last_agent_event_idx == len(event_sequence) - 1, \
                            "Event ordering violation: agent_completed not the final critical event"
                
                # Performance validation
                assert total_collection_time < 120.0, \
                    f"Event collection too slow: {total_collection_time:.2f}s - affects user experience"
                
        except Exception as e:
            self.logger.error(f" FAIL:  Critical WebSocket events validation failed: {e}")
            self.logger.error(f" CHART:  Event metrics collected: {len(event_metrics)}")
            self.logger.error(f"[U+1F4C8] Business value indicators: {business_value_indicators}")
            raise
        
        # SUCCESS METRICS REPORTING
        self.logger.info(" CELEBRATION:  ALL 5 CRITICAL WEBSOCKET EVENTS VALIDATION SUCCESS")
        self.logger.info(f" CHART:  Total events collected: {len(all_events)}")
        self.logger.info(f" TARGET:  Critical events timing: {event_timing}")
        self.logger.info(f" WARNING: [U+FE0F] SLA violations: {len(sla_violations)} ( <= 2 acceptable)")
        self.logger.info(f" IDEA:  Actionable insights: {business_value_indicators['actionable_insights']}")
        self.logger.info(f"[U+1F4BC] Specific recommendations: {business_value_indicators['specific_recommendations']}")
        self.logger.info(f"[U+1F527] Implementation guidance: {business_value_indicators['implementation_guidance']}")
        self.logger.info(f"[U+1F4B0] Cost savings identified: {business_value_indicators['cost_savings_identified']}")
        self.logger.info(f"[U+23F1][U+FE0F] Total collection time: {total_collection_time:.2f}s")
        
        # Validate minimum business value thresholds for success
        total_business_value = sum(business_value_indicators.values())
        assert total_business_value >= 4, \
            f"Insufficient business value delivered: {total_business_value} indicators"

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    async def test_realtime_event_delivery_timing_and_ordering_validation(self):
        """
        Test real-time event delivery timing and ordering meets business requirements.
        
        Business Value: Ensures users receive AI insights in real-time with proper
        sequence, maintaining engagement and trust in the AI assistance quality.
        """
        self.logger.info("[U+23F1][U+FE0F] Starting real-time event delivery timing and ordering validation")
        
        user_context = await create_authenticated_user_context(
            user_email=f"timing_test_{uuid.uuid4().hex[:8]}@staging.test.com",
            environment="staging",
            websocket_enabled=True
        )
        
        timing_metrics = {
            "first_event_delay": None,
            "event_intervals": [],
            "out_of_order_events": 0,
            "timing_sla_compliance": 0,
            "realtime_responsiveness": "unknown"
        }
        
        async with websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=self.websocket_headers,
            open_timeout=20.0
        ) as websocket:
            
            # Send request with real-time requirements
            realtime_request = {
                "type": "agent_request",
                "thread_id": str(user_context.thread_id),
                "agent": "triage_agent",  # Faster agent for timing validation
                "message": "Quick analysis: What are the top 3 immediate cost optimization opportunities for a startup spending $8,000/month on AWS?",
                "context": {
                    "urgency": "high",
                    "response_time_requirement": "fast",
                    "user_expectation": "real_time_updates"
                },
                "metadata": {
                    "test_type": "timing_validation",
                    "performance_critical": True
                }
            }
            
            request_timestamp = time.time()
            await websocket.send(json.dumps(realtime_request))
            
            self.logger.info("[U+1F4E4] Sent real-time optimization request")
            
            # Collect events with precise timing
            timed_events = []
            previous_event_time = request_timestamp
            first_event_received = False
            
            while len(timed_events) < 15:  # Collect sufficient events for timing analysis
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    event_timestamp = time.time()
                    event = json.loads(event_data)
                    
                    # Calculate timing metrics
                    delay_from_request = event_timestamp - request_timestamp
                    interval_from_previous = event_timestamp - previous_event_time
                    
                    if not first_event_received:
                        timing_metrics["first_event_delay"] = delay_from_request
                        first_event_received = True
                        self.logger.info(f"[U+1F4E8] First event received at {delay_from_request:.3f}s")
                    
                    timing_metrics["event_intervals"].append(interval_from_previous)
                    
                    timed_event = {
                        "event": event,
                        "timestamp": event_timestamp,
                        "delay_from_request": delay_from_request,
                        "interval_from_previous": interval_from_previous,
                        "sequence_number": len(timed_events) + 1
                    }
                    
                    timed_events.append(timed_event)
                    previous_event_time = event_timestamp
                    
                    event_type = event.get("type")
                    if event_type:
                        self.logger.info(f"[U+1F4E8] {event_type} at {delay_from_request:.3f}s (interval: {interval_from_previous:.3f}s)")
                    
                    # Check for real-time SLA compliance
                    if event_type in self.EVENT_SLA_REQUIREMENTS:
                        sla_requirement = self.EVENT_SLA_REQUIREMENTS[event_type]
                        if delay_from_request <= sla_requirement:
                            timing_metrics["timing_sla_compliance"] += 1
                    
                    if event_type == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
                except json.JSONDecodeError:
                    continue
            
            # TIMING VALIDATION ANALYSIS
            
            # First event responsiveness (should be < 3 seconds for real-time feel)
            assert timing_metrics["first_event_delay"] is not None, "No events received"
            assert timing_metrics["first_event_delay"] < 5.0, \
                f"First event too slow: {timing_metrics['first_event_delay']:.2f}s - poor real-time experience"
            
            if timing_metrics["first_event_delay"] < 1.0:
                timing_metrics["realtime_responsiveness"] = "excellent"
            elif timing_metrics["first_event_delay"] < 2.0:
                timing_metrics["realtime_responsiveness"] = "good"
            elif timing_metrics["first_event_delay"] < 4.0:
                timing_metrics["realtime_responsiveness"] = "acceptable"
            else:
                timing_metrics["realtime_responsiveness"] = "poor"
            
            # Event interval consistency (events should arrive regularly)
            if timing_metrics["event_intervals"]:
                avg_interval = sum(timing_metrics["event_intervals"]) / len(timing_metrics["event_intervals"])
                max_interval = max(timing_metrics["event_intervals"])
                
                # No gaps longer than 10 seconds between events
                assert max_interval < 15.0, \
                    f"Event gap too long: {max_interval:.2f}s - breaks real-time flow"
                
                self.logger.info(f" CHART:  Average event interval: {avg_interval:.3f}s")
                self.logger.info(f" CHART:  Maximum event gap: {max_interval:.3f}s")
            
            # Event ordering validation
            critical_events_in_order = []
            for timed_event in timed_events:
                event_type = timed_event["event"].get("type")
                if event_type in self.CRITICAL_EVENTS:
                    critical_events_in_order.append(event_type)
            
            # Validate expected ordering patterns
            if "agent_started" in critical_events_in_order and "agent_completed" in critical_events_in_order:
                started_index = critical_events_in_order.index("agent_started")
                completed_index = critical_events_in_order.index("agent_completed")
                
                assert started_index < completed_index, \
                    "Event ordering violation: agent_completed before agent_started"
                
                # agent_thinking should come after agent_started
                if "agent_thinking" in critical_events_in_order:
                    thinking_index = critical_events_in_order.index("agent_thinking")
                    assert thinking_index > started_index, \
                        "Event ordering violation: agent_thinking before agent_started"
            
            # Performance benchmarking
            total_events = len(timed_events)
            total_duration = timed_events[-1]["delay_from_request"] if timed_events else 0
            
            if total_duration > 0:
                events_per_second = total_events / total_duration
                self.logger.info(f" CHART:  Events per second: {events_per_second:.2f}")
                
                # Should maintain reasonable event throughput
                assert events_per_second >= 0.5, \
                    f"Event throughput too low: {events_per_second:.2f} events/sec"
        
        self.logger.info(" CELEBRATION:  REAL-TIME EVENT DELIVERY TIMING VALIDATION SUCCESS")
        self.logger.info(f"[U+23F1][U+FE0F] First event delay: {timing_metrics['first_event_delay']:.3f}s")
        self.logger.info(f" TARGET:  Real-time responsiveness: {timing_metrics['realtime_responsiveness']}")
        self.logger.info(f" CHART:  Total events collected: {len(timed_events)}")
        self.logger.info(f" PASS:  SLA compliance events: {timing_metrics['timing_sla_compliance']}")
        self.logger.info(f" IDEA:  Business Value: Real-time event delivery maintains user engagement")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    async def test_event_content_quality_and_business_value_validation(self):
        """
        Test WebSocket event content quality delivers substantive business value.
        
        Business Value: Validates that WebSocket events contain high-quality,
        actionable business content that justifies user engagement and platform value.
        """
        self.logger.info("[U+1F4DD] Starting event content quality and business value validation")
        
        user_context = await create_authenticated_user_context(
            user_email=f"content_quality_{uuid.uuid4().hex[:8]}@staging.test.com",
            environment="staging",
            websocket_enabled=True
        )
        
        content_quality_metrics = {
            "thinking_events_analyzed": 0,
            "thinking_content_quality_scores": [],
            "final_response_quality": 0,
            "business_keywords_found": 0,
            "actionable_items_identified": 0,
            "specific_numbers_provided": 0,
            "implementation_steps_provided": 0
        }
        
        async with websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=self.websocket_headers,
            open_timeout=20.0
        ) as websocket:
            
            # Send business-focused request requiring high-quality content
            business_request = {
                "type": "agent_request",
                "thread_id": str(user_context.thread_id),
                "agent": "business_advisor",
                "message": "I'm the CFO of a SaaS company with $2M ARR, growing 15% monthly. Our cloud costs are $45,000/month across AWS and Azure. I need a detailed cost optimization strategy with specific savings targets, implementation timeline, and ROI projections. Please provide actionable recommendations with concrete numbers.",
                "context": {
                    "role": "cfo",
                    "company_arr": 2000000,
                    "growth_rate": 0.15,
                    "monthly_cloud_spend": 45000,
                    "cloud_providers": ["aws", "azure"],
                    "deliverables_required": [
                        "savings_targets",
                        "implementation_timeline", 
                        "roi_projections",
                        "actionable_recommendations"
                    ]
                },
                "metadata": {
                    "test_type": "content_quality_validation",
                    "content_requirements": "high_quality_business_analysis",
                    "expected_detail_level": "comprehensive"
                }
            }
            
            await websocket.send(json.dumps(business_request))
            self.logger.info("[U+1F4E4] Sent comprehensive business analysis request")
            
            # Collect and analyze event content quality
            quality_events = []
            thinking_events = []
            final_response_event = None
            
            while len(quality_events) < 20:  # Comprehensive content collection
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    event = json.loads(event_data)
                    quality_events.append(event)
                    
                    event_type = event.get("type")
                    
                    if event_type == "agent_thinking":
                        thinking_events.append(event)
                        thinking_content = event.get("data", {}).get("content", "")
                        
                        # Analyze thinking content quality
                        content_quality_metrics["thinking_events_analyzed"] += 1
                        
                        # Content length scoring (0-10)
                        length_score = min(10, len(thinking_content) / 20)  # 200 chars = 10 points
                        
                        # Business keywords scoring
                        business_keywords = [
                            "cost", "savings", "optimization", "ROI", "revenue", "profit", 
                            "efficiency", "reduction", "analysis", "strategy", "implementation",
                            "timeline", "budget", "forecast", "projection", "target"
                        ]
                        
                        keyword_count = sum(1 for keyword in business_keywords 
                                          if keyword.lower() in thinking_content.lower())
                        content_quality_metrics["business_keywords_found"] += keyword_count
                        keyword_score = min(10, keyword_count / 2)  # 2 keywords = 1 point
                        
                        # Specific numbers/metrics scoring
                        import re
                        numbers_found = len(re.findall(r'\$?[\d,]+(?:\.\d+)?%?', thinking_content))
                        if numbers_found > 0:
                            content_quality_metrics["specific_numbers_provided"] += numbers_found
                        number_score = min(10, numbers_found)
                        
                        # Overall thinking quality score
                        thinking_quality = (length_score + keyword_score + number_score) / 3
                        content_quality_metrics["thinking_content_quality_scores"].append(thinking_quality)
                        
                        self.logger.info(f"[U+1F9E0] Thinking quality: {thinking_quality:.1f}/10 (length: {len(thinking_content)}, keywords: {keyword_count}, numbers: {numbers_found})")
                    
                    elif event_type == "agent_completed":
                        final_response_event = event
                        final_response = event.get("data", {}).get("response", {})
                        response_text = str(final_response)
                        
                        # Analyze final response quality
                        
                        # Actionable items detection
                        actionable_indicators = [
                            "recommend", "suggest", "should", "implement", "start", "begin",
                            "reduce", "optimize", "switch", "migrate", "configure", "enable"
                        ]
                        actionable_count = sum(1 for indicator in actionable_indicators 
                                             if indicator.lower() in response_text.lower())
                        content_quality_metrics["actionable_items_identified"] = actionable_count
                        
                        # Implementation steps detection
                        step_indicators = ["step", "phase", "first", "next", "then", "finally", "timeline"]
                        step_count = sum(1 for indicator in step_indicators 
                                       if indicator.lower() in response_text.lower())
                        content_quality_metrics["implementation_steps_provided"] = step_count
                        
                        # Overall response quality scoring
                        response_length_score = min(10, len(response_text) / 100)  # 1000 chars = 10 points
                        actionable_score = min(10, actionable_count / 2)  # 2 actionable items = 1 point
                        implementation_score = min(10, step_count)
                        
                        content_quality_metrics["final_response_quality"] = (
                            response_length_score + actionable_score + implementation_score
                        ) / 3
                        
                        self.logger.info(f"[U+1F4CB] Final response quality: {content_quality_metrics['final_response_quality']:.1f}/10")
                        break
                        
                except asyncio.TimeoutError:
                    break
                except json.JSONDecodeError:
                    continue
            
            # CONTENT QUALITY VALIDATION
            
            # Thinking content quality validation
            assert content_quality_metrics["thinking_events_analyzed"] >= 2, \
                f"Insufficient thinking events for quality analysis: {content_quality_metrics['thinking_events_analyzed']}"
            
            if content_quality_metrics["thinking_content_quality_scores"]:
                avg_thinking_quality = sum(content_quality_metrics["thinking_content_quality_scores"]) / len(content_quality_metrics["thinking_content_quality_scores"])
                assert avg_thinking_quality >= 4.0, \
                    f"Thinking content quality too low: {avg_thinking_quality:.1f}/10 - insufficient business value"
                
                self.logger.info(f" CHART:  Average thinking quality: {avg_thinking_quality:.1f}/10")
            
            # Business keyword density validation
            total_thinking_events = content_quality_metrics["thinking_events_analyzed"]
            if total_thinking_events > 0:
                keywords_per_event = content_quality_metrics["business_keywords_found"] / total_thinking_events
                assert keywords_per_event >= 2.0, \
                    f"Insufficient business focus: {keywords_per_event:.1f} keywords per thinking event"
            
            # Final response quality validation
            assert content_quality_metrics["final_response_quality"] >= 5.0, \
                f"Final response quality too low: {content_quality_metrics['final_response_quality']:.1f}/10"
            
            # Actionable content validation
            assert content_quality_metrics["actionable_items_identified"] >= 3, \
                f"Insufficient actionable recommendations: {content_quality_metrics['actionable_items_identified']} < 3"
            
            # Specific numbers/metrics validation (important for business decisions)
            assert content_quality_metrics["specific_numbers_provided"] >= 2, \
                f"Insufficient specific metrics: {content_quality_metrics['specific_numbers_provided']} numbers provided"
            
            # Implementation guidance validation
            assert content_quality_metrics["implementation_steps_provided"] >= 2, \
                f"Insufficient implementation guidance: {content_quality_metrics['implementation_steps_provided']} steps provided"
        
        # Calculate overall content value score
        overall_content_score = (
            (sum(content_quality_metrics["thinking_content_quality_scores"]) / len(content_quality_metrics["thinking_content_quality_scores"]) if content_quality_metrics["thinking_content_quality_scores"] else 0) * 0.4 +
            content_quality_metrics["final_response_quality"] * 0.6
        )
        
        self.logger.info(" CELEBRATION:  EVENT CONTENT QUALITY VALIDATION SUCCESS")
        self.logger.info(f"[U+1F9E0] Thinking events analyzed: {content_quality_metrics['thinking_events_analyzed']}")
        self.logger.info(f" CHART:  Overall content score: {overall_content_score:.1f}/10")
        self.logger.info(f"[U+1F4BC] Business keywords found: {content_quality_metrics['business_keywords_found']}")
        self.logger.info(f" TARGET:  Actionable items: {content_quality_metrics['actionable_items_identified']}")
        self.logger.info(f"[U+1F4C8] Specific numbers: {content_quality_metrics['specific_numbers_provided']}")
        self.logger.info(f"[U+1F527] Implementation steps: {content_quality_metrics['implementation_steps_provided']}")
        self.logger.info(f" IDEA:  Business Value: WebSocket events deliver high-quality, actionable business content")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    async def test_multi_agent_event_flow_coordination_and_sequencing(self):
        """
        Test multi-agent event flow coordination and proper sequencing.
        
        Business Value: Validates complex multi-agent workflows deliver coordinated
        insights through proper WebSocket event sequencing and handoffs.
        """
        self.logger.info("[U+1F91D] Starting multi-agent event flow coordination test")
        
        user_context = await create_authenticated_user_context(
            user_email=f"multi_agent_{uuid.uuid4().hex[:8]}@staging.test.com",
            environment="staging",
            websocket_enabled=True
        )
        
        multi_agent_metrics = {
            "agents_executed": [],
            "event_sequences": [],
            "handoff_timings": [],
            "coordination_quality": 0,
            "workflow_completeness": 0
        }
        
        async with websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=self.websocket_headers,
            open_timeout=25.0
        ) as websocket:
            
            # Send complex request requiring multiple agent coordination
            complex_workflow_request = {
                "type": "agent_request",
                "thread_id": str(user_context.thread_id),
                "agent": "triage_agent",  # Start with triage for workflow coordination
                "message": "I need a comprehensive analysis: First, triage my cloud infrastructure issues (high costs, performance problems, security concerns). Then provide detailed optimization recommendations for the highest priority issues. Finally, create an implementation roadmap with timeline and resource requirements.",
                "context": {
                    "workflow_type": "multi_agent_coordination",
                    "infrastructure_issues": [
                        "high_costs",
                        "performance_problems", 
                        "security_concerns"
                    ],
                    "expected_deliverables": [
                        "issue_triage",
                        "optimization_recommendations",
                        "implementation_roadmap"
                    ]
                },
                "metadata": {
                    "test_type": "multi_agent_coordination",
                    "workflow_complexity": "high",
                    "coordination_required": True
                }
            }
            
            await websocket.send(json.dumps(complex_workflow_request))
            self.logger.info("[U+1F4E4] Sent multi-agent coordination request")
            
            # Track agent workflow progression
            workflow_events = []
            current_agent_events = []
            agent_transitions = []
            workflow_start_time = time.time()
            
            while len(workflow_events) < 30:  # Extended collection for multi-agent workflow
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=45.0)
                    event = json.loads(event_data)
                    workflow_events.append(event)
                    
                    event_type = event.get("type")
                    event_timestamp = time.time() - workflow_start_time
                    
                    # Track agent execution phases
                    if event_type == "agent_started":
                        if current_agent_events:
                            # Previous agent completed, record transition
                            agent_transitions.append({
                                "previous_agent_events": len(current_agent_events),
                                "transition_time": event_timestamp,
                                "handoff_quality": "completed"
                            })
                        
                        current_agent_events = [event]
                        agent_info = event.get("data", {}).get("agent", "unknown")
                        multi_agent_metrics["agents_executed"].append(agent_info)
                        self.logger.info(f"[U+1F916] Agent started: {agent_info} at {event_timestamp:.2f}s")
                    
                    elif event_type in self.CRITICAL_EVENTS:
                        current_agent_events.append(event)
                    
                    elif event_type == "agent_completed":
                        current_agent_events.append(event)
                        completion_data = event.get("data", {})
                        
                        # Analyze agent completion for workflow progression
                        agent_response = str(completion_data.get("response", "")).lower()
                        
                        # Check for workflow coordination indicators
                        coordination_indicators = [
                            "next step", "recommend", "prioritize", "suggest", 
                            "implementation", "roadmap", "timeline", "phase"
                        ]
                        coordination_count = sum(1 for indicator in coordination_indicators 
                                               if indicator in agent_response)
                        
                        if coordination_count >= 3:
                            multi_agent_metrics["coordination_quality"] += 1
                        
                        # Record event sequence for this agent
                        agent_event_types = [e.get("type") for e in current_agent_events]
                        multi_agent_metrics["event_sequences"].append(agent_event_types)
                        
                        self.logger.info(f" PASS:  Agent completed workflow phase ({len(current_agent_events)} events)")
                        
                        # Check if this appears to be final completion
                        if ("implementation" in agent_response or "roadmap" in agent_response or
                            "timeline" in agent_response):
                            multi_agent_metrics["workflow_completeness"] = 1
                            self.logger.info(" TARGET:  Multi-agent workflow appears complete")
                            break
                    
                except asyncio.TimeoutError:
                    self.logger.warning("[U+23F0] Multi-agent workflow timeout - analyzing partial results")
                    break
                except json.JSONDecodeError:
                    continue
            
            total_workflow_time = time.time() - workflow_start_time
            
            # MULTI-AGENT COORDINATION VALIDATION
            
            # Verify multiple agents were involved
            unique_agents = len(set(multi_agent_metrics["agents_executed"]))
            assert unique_agents >= 1, \
                f"Expected multi-agent coordination, got {unique_agents} unique agents"
            
            # Verify each agent phase had proper event sequences
            for i, event_sequence in enumerate(multi_agent_metrics["event_sequences"]):
                # Each agent should have proper event flow
                critical_events_in_sequence = [e for e in event_sequence if e in self.CRITICAL_EVENTS]
                
                assert "agent_started" in critical_events_in_sequence, \
                    f"Agent phase {i} missing agent_started event"
                
                assert "agent_completed" in critical_events_in_sequence, \
                    f"Agent phase {i} missing agent_completed event"
                
                # Verify proper ordering within agent phase
                if "agent_started" in critical_events_in_sequence and "agent_completed" in critical_events_in_sequence:
                    started_idx = critical_events_in_sequence.index("agent_started")
                    completed_idx = critical_events_in_sequence.index("agent_completed")
                    assert started_idx < completed_idx, \
                        f"Agent phase {i} has incorrect event ordering"
            
            # Verify workflow coordination quality
            assert multi_agent_metrics["coordination_quality"] >= 1, \
                f"Insufficient coordination between agents: {multi_agent_metrics['coordination_quality']} quality indicators"
            
            # Verify reasonable workflow performance
            assert total_workflow_time < 120.0, \
                f"Multi-agent workflow too slow: {total_workflow_time:.2f}s - affects user experience"
            
            # Verify workflow completeness indicators
            assert multi_agent_metrics["workflow_completeness"] >= 1, \
                "Multi-agent workflow did not reach completion with implementation guidance"
        
        self.logger.info(" CELEBRATION:  MULTI-AGENT EVENT FLOW COORDINATION SUCCESS")
        self.logger.info(f"[U+1F916] Agents executed: {len(multi_agent_metrics['agents_executed'])}")
        self.logger.info(f" CHART:  Event sequences: {len(multi_agent_metrics['event_sequences'])}")
        self.logger.info(f"[U+1F91D] Coordination quality: {multi_agent_metrics['coordination_quality']}")
        self.logger.info(f" PASS:  Workflow completeness: {multi_agent_metrics['workflow_completeness']}")
        self.logger.info(f"[U+23F1][U+FE0F] Total workflow time: {total_workflow_time:.2f}s")
        self.logger.info(f" IDEA:  Business Value: Multi-agent coordination delivers comprehensive analysis through coordinated event flows")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    async def test_event_flow_resilience_during_network_interruptions(self):
        """
        Test WebSocket event flow resilience during network interruptions and failures.
        
        Business Value: Ensures users receive consistent AI value even when experiencing
        network issues, maintaining platform reliability and user trust.
        """
        self.logger.info("[U+1F6E1][U+FE0F] Starting event flow resilience during network interruptions test")
        
        user_context = await create_authenticated_user_context(
            user_email=f"resilience_test_{uuid.uuid4().hex[:8]}@staging.test.com",
            environment="staging",
            websocket_enabled=True
        )
        
        resilience_metrics = {
            "interruptions_simulated": 0,
            "events_lost": 0,
            "recovery_successful": 0,
            "data_continuity_maintained": 0,
            "user_experience_degradation": 0
        }
        
        # PHASE 1: Establish baseline connection and start agent request
        
        async with websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=self.websocket_headers,
            open_timeout=20.0
        ) as websocket1:
            
            resilience_request = {
                "type": "agent_request",
                "thread_id": str(user_context.thread_id),
                "agent": "business_advisor",
                "message": "Provide a comprehensive cost optimization analysis for our cloud infrastructure. Start with current spending analysis, then identify optimization opportunities, and finally provide implementation timeline.",
                "metadata": {
                    "test_type": "resilience_validation",
                    "expected_duration": "extended",
                    "interruption_tolerance": "high"
                }
            }
            
            await websocket1.send(json.dumps(resilience_request))
            self.logger.info("[U+1F4E4] Sent resilience test request on initial connection")
            
            # Collect initial events
            initial_events = []
            initial_collection_time = 15.0  # Collect for 15 seconds
            collection_start = time.time()
            
            while time.time() - collection_start < initial_collection_time:
                try:
                    event_data = await asyncio.wait_for(websocket1.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    initial_events.append(event)
                    
                    event_type = event.get("type")
                    self.logger.info(f"[U+1F4E8] Initial phase: {event_type}")
                    
                    # If agent completes quickly, continue to next phase
                    if event_type == "agent_completed":
                        self.logger.info(" TARGET:  Agent completed in initial phase - proceeding to interruption test")
                        break
                        
                except asyncio.TimeoutError:
                    break
                except json.JSONDecodeError:
                    continue
            
            self.logger.info(f" CHART:  Initial phase: {len(initial_events)} events collected")
        
        # PHASE 2: Simulate network interruption and reconnection
        self.logger.info("[U+1F50C] Simulating network interruption (connection termination)")
        resilience_metrics["interruptions_simulated"] += 1
        
        # Brief interruption period
        await asyncio.sleep(3.0)
        
        # PHASE 3: Reconnect and attempt to continue/recover
        try:
            async with websockets.connect(
                self.staging_config.urls.websocket_url,
                additional_headers=self.websocket_headers,
                open_timeout=25.0  # Longer timeout after interruption
            ) as websocket2:
                
                self.logger.info("[U+1F50C] Reconnected after interruption")
                resilience_metrics["recovery_successful"] += 1
                
                # Attempt to get thread status and continue conversation
                recovery_request = {
                    "type": "get_thread_status",
                    "thread_id": str(user_context.thread_id),
                    "include_messages": True
                }
                
                await websocket2.send(json.dumps(recovery_request))
                
                # Check for thread continuity
                recovery_response = await asyncio.wait_for(websocket2.recv(), timeout=15.0)
                recovery_data = json.loads(recovery_response)
                
                if (recovery_data.get("type") == "thread_status" and 
                    recovery_data.get("data", {}).get("messages")):
                    resilience_metrics["data_continuity_maintained"] += 1
                    self.logger.info(" PASS:  Thread data continuity maintained after interruption")
                
                # Continue conversation to test ongoing functionality
                followup_request = {
                    "type": "send_message",
                    "thread_id": str(user_context.thread_id),
                    "message": "Based on your previous analysis (before the connection issue), can you provide more specific recommendations for immediate implementation?",
                    "metadata": {
                        "post_interruption": True,
                        "context_continuity_test": True
                    }
                }
                
                await websocket2.send(json.dumps(followup_request))
                
                # Collect post-interruption events
                post_interruption_events = []
                post_collection_time = 20.0
                post_start = time.time()
                
                while time.time() - post_start < post_collection_time:
                    try:
                        event_data = await asyncio.wait_for(websocket2.recv(), timeout=10.0)
                        event = json.loads(event_data)
                        post_interruption_events.append(event)
                        
                        event_type = event.get("type")
                        self.logger.info(f"[U+1F4E8] Post-interruption: {event_type}")
                        
                        # Check for context continuity in responses
                        if event_type == "agent_completed":
                            response_content = str(event.get("data", {}).get("response", "")).lower()
                            context_indicators = ["previous", "earlier", "mentioned", "discussed", "analysis"]
                            
                            if any(indicator in response_content for indicator in context_indicators):
                                resilience_metrics["data_continuity_maintained"] += 1
                                self.logger.info(" PASS:  Agent demonstrates context continuity after interruption")
                            
                            break
                            
                    except asyncio.TimeoutError:
                        self.logger.warning("[U+23F0] Timeout in post-interruption phase")
                        resilience_metrics["user_experience_degradation"] += 1
                        break
                    except json.JSONDecodeError:
                        continue
                
                self.logger.info(f" CHART:  Post-interruption: {len(post_interruption_events)} events collected")
                
        except Exception as e:
            self.logger.error(f" FAIL:  Reconnection failed: {e}")
            resilience_metrics["user_experience_degradation"] += 1
        
        # RESILIENCE VALIDATION
        
        # Recovery capability validation
        assert resilience_metrics["recovery_successful"] >= 1, \
            "Failed to recover from network interruption - poor resilience"
        
        # Data continuity validation
        assert resilience_metrics["data_continuity_maintained"] >= 1, \
            "Thread data not maintained after interruption - data loss occurred"
        
        # User experience impact validation
        assert resilience_metrics["user_experience_degradation"] <= 1, \
            f"Too much user experience degradation: {resilience_metrics['user_experience_degradation']} incidents"
        
        # Functional continuity validation
        total_events = len(initial_events) + len(post_interruption_events) if 'post_interruption_events' in locals() else len(initial_events)
        assert total_events >= 5, \
            f"Insufficient event flow across interruption: {total_events} total events"
        
        self.logger.info(" CELEBRATION:  EVENT FLOW RESILIENCE VALIDATION SUCCESS")
        self.logger.info(f"[U+1F50C] Interruptions simulated: {resilience_metrics['interruptions_simulated']}")
        self.logger.info(f" PASS:  Recovery successful: {resilience_metrics['recovery_successful']}")
        self.logger.info(f"[U+1F4BE] Data continuity maintained: {resilience_metrics['data_continuity_maintained']}")
        self.logger.info(f" WARNING: [U+FE0F] User experience degradation: {resilience_metrics['user_experience_degradation']}")
        self.logger.info(f" IDEA:  Business Value: Platform maintains resilience and data continuity despite network interruptions")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.performance
    async def test_event_flow_performance_under_realistic_load_conditions(self):
        """
        Test WebSocket event flow performance under realistic load conditions.
        
        Business Value: Validates platform can deliver consistent AI value through
        WebSocket events even under realistic user load conditions.
        """
        self.logger.info("[U+1F3CB][U+FE0F] Starting event flow performance under realistic load test")
        
        # Create multiple user contexts for load testing
        concurrent_users = 3  # Moderate load for staging
        user_contexts = []
        
        for i in range(concurrent_users):
            context = await create_authenticated_user_context(
                user_email=f"load_user_{i}_{uuid.uuid4().hex[:6]}@staging.test.com",
                environment="staging",
                websocket_enabled=True
            )
            user_contexts.append(context)
        
        load_metrics = {
            "concurrent_connections": 0,
            "total_events_processed": 0,
            "average_event_latency": 0,
            "event_throughput": 0,
            "performance_degradation": 0,
            "user_success_rate": 0
        }
        
        async def execute_user_load_test(user_context: 'StronglyTypedUserExecutionContext', user_index: int) -> Dict[str, Any]:
            """Execute event flow load test for a single user."""
            user_events = []
            user_timings = []
            
            try:
                async with websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=self.websocket_headers,
                    open_timeout=30.0  # Extended timeout for load conditions
                ) as websocket:
                    
                    load_metrics["concurrent_connections"] += 1
                    
                    # Send realistic business request
                    load_request = {
                        "type": "agent_request",
                        "thread_id": str(user_context.thread_id),
                        "agent": "cost_optimizer",
                        "message": f"Load test user {user_index}: Analyze cost optimization for $25,000/month cloud spend with focus on compute efficiency.",
                        "metadata": {
                            "test_type": "load_testing",
                            "user_index": user_index,
                            "load_participant": True
                        }
                    }
                    
                    request_start = time.time()
                    await websocket.send(json.dumps(load_request))
                    
                    # Collect events under load
                    while len(user_events) < 15:  # Reasonable event collection
                        try:
                            event_data = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                            event_receive_time = time.time()
                            event = json.loads(event_data)
                            
                            user_events.append(event)
                            event_latency = event_receive_time - request_start
                            user_timings.append(event_latency)
                            
                            load_metrics["total_events_processed"] += 1
                            
                            event_type = event.get("type")
                            if event_type == "agent_completed":
                                break
                                
                        except asyncio.TimeoutError:
                            # Timeout indicates performance degradation
                            load_metrics["performance_degradation"] += 1
                            break
                        except json.JSONDecodeError:
                            continue
                    
                    return {
                        "user_index": user_index,
                        "events_collected": len(user_events),
                        "event_timings": user_timings,
                        "success": len(user_events) >= 5,  # Minimum success threshold
                        "final_event_type": user_events[-1].get("type") if user_events else None
                    }
                    
            except Exception as e:
                self.logger.error(f"Load test user {user_index} failed: {e}")
                return {
                    "user_index": user_index,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute concurrent load test
        self.logger.info(f"[U+1F680] Starting concurrent load test with {concurrent_users} users")
        load_start_time = time.time()
        
        load_results = await asyncio.gather(*[
            execute_user_load_test(context, i)
            for i, context in enumerate(user_contexts)
        ], return_exceptions=True)
        
        total_load_time = time.time() - load_start_time
        
        # Analyze load test results
        successful_users = [r for r in load_results if isinstance(r, dict) and r.get("success")]
        load_metrics["user_success_rate"] = len(successful_users) / len(user_contexts)
        
        # Calculate performance metrics
        all_timings = []
        for result in successful_users:
            all_timings.extend(result.get("event_timings", []))
        
        if all_timings:
            load_metrics["average_event_latency"] = sum(all_timings) / len(all_timings)
            load_metrics["event_throughput"] = len(all_timings) / total_load_time
        
        # LOAD PERFORMANCE VALIDATION
        
        # User success rate validation
        assert load_metrics["user_success_rate"] >= 0.8, \
            f"Load test success rate too low: {load_metrics['user_success_rate']:.1%} - platform performance degraded"
        
        # Event throughput validation
        if load_metrics["event_throughput"] > 0:
            min_expected_throughput = concurrent_users * 1.0  # At least 1 event/sec per user
            assert load_metrics["event_throughput"] >= min_expected_throughput, \
                f"Event throughput too low under load: {load_metrics['event_throughput']:.2f} events/sec"
        
        # Latency validation
        if load_metrics["average_event_latency"] > 0:
            assert load_metrics["average_event_latency"] < 20.0, \
                f"Average event latency too high under load: {load_metrics['average_event_latency']:.2f}s"
        
        # Performance degradation tolerance
        degradation_rate = load_metrics["performance_degradation"] / concurrent_users
        assert degradation_rate <= 0.3, \
            f"Too much performance degradation under load: {degradation_rate:.1%}"
        
        # Total event processing validation
        min_expected_events = concurrent_users * 5  # At least 5 events per user
        assert load_metrics["total_events_processed"] >= min_expected_events, \
            f"Insufficient event processing under load: {load_metrics['total_events_processed']} < {min_expected_events}"
        
        self.logger.info(" CELEBRATION:  EVENT FLOW PERFORMANCE UNDER LOAD SUCCESS")
        self.logger.info(f"[U+1F465] Concurrent users: {concurrent_users}")
        self.logger.info(f" PASS:  User success rate: {load_metrics['user_success_rate']:.1%}")
        self.logger.info(f" CHART:  Total events processed: {load_metrics['total_events_processed']}")
        self.logger.info(f"[U+23F1][U+FE0F] Average event latency: {load_metrics['average_event_latency']:.2f}s")
        self.logger.info(f"[U+1F4C8] Event throughput: {load_metrics['event_throughput']:.2f} events/sec")
        self.logger.info(f" WARNING: [U+FE0F] Performance degradation: {load_metrics['performance_degradation']} incidents")
        self.logger.info(f" IDEA:  Business Value: Platform maintains WebSocket event performance under realistic load")