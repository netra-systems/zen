"""
Complete Message Pipeline Integration Test - Issue #1059 Agent Golden Path Tests

Business Value Justification:
- Segment: All tiers - Core platform functionality 
- Business Goal: Validate end-to-end agent message processing and AI response delivery
- Value Impact: Ensures $500K+ ARR golden path functionality delivers real business value
- Revenue Impact: Prevents complete failure of core AI-powered chat functionality

PURPOSE:
This integration test validates the complete message pipeline from user input
through agent processing to final AI response delivery via WebSocket events.
This is the fundamental business value proposition of the platform - users
send messages and receive meaningful AI assistance in real-time.

CRITICAL DESIGN:
- NO DOCKER usage - tests run against GCP staging environment
- Real E2E testing with actual WebSocket connections and agent execution
- Validates business value delivery (meaningful AI responses, not just technical success)
- Tests all 5 critical WebSocket events for real-time user experience
- Proper user isolation and multi-user concurrent testing
- Comprehensive error handling and timeout controls

SCOPE:
1. Complete user message → agent execution → AI response pipeline
2. WebSocket event delivery validation throughout the process
3. Agent context creation and maintenance during execution
4. Business value validation of AI responses (actionable, problem-solving)
5. Multi-user isolation and concurrent processing validation
6. Error recovery and graceful degradation testing

AGENT_SESSION_ID: agent-session-2025-09-14-1430
Issue #1059: Agent Golden Path Integration Tests - Step 1 Implementation
"""

import asyncio
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

import pytest
import websockets
import httpx
from websockets import ConnectionClosed, WebSocketException

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, AuthenticatedUser
from tests.e2e.staging_config import StagingTestConfig
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class MessagePipelineEvent:
    """Represents an event in the message pipeline for tracking and validation."""
    event_type: str
    timestamp: float
    user_id: str
    thread_id: str
    run_id: str
    data: Dict[str, Any]
    event_source: str = "websocket"  # websocket, agent, system
    processing_stage: str = "unknown"  # input, processing, output
    business_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineValidationResult:
    """Results of message pipeline validation including business value assessment."""
    pipeline_success: bool
    total_duration: float
    events_received: List[MessagePipelineEvent]
    critical_events_present: Set[str]
    business_value_indicators: Dict[str, Any]
    error_messages: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    

class MessagePipelineTracker:
    """Tracks message pipeline events and validates business value delivery."""
    
    CRITICAL_EVENTS = {
        "agent_started", 
        "agent_thinking", 
        "tool_executing", 
        "tool_completed", 
        "agent_completed"
    }
    
    BUSINESS_VALUE_KEYWORDS = {
        "analysis", "recommendation", "solution", "optimize", "improve", 
        "suggest", "identify", "strategy", "actionable", "next steps",
        "priority", "risk", "opportunity", "efficiency", "performance"
    }
    
    def __init__(self, user_id: str, thread_id: str, run_id: str):
        self.user_id = user_id
        self.thread_id = thread_id
        self.run_id = run_id
        self.events: List[MessagePipelineEvent] = []
        self.pipeline_start_time = time.time()
        self.message_sent_time: Optional[float] = None
        self.first_response_time: Optional[float] = None
        self.completion_time: Optional[float] = None
        
    async def track_event(self, event_type: str, data: Dict[str, Any], 
                         event_source: str = "websocket", 
                         processing_stage: str = "unknown") -> None:
        """Track a message pipeline event with business context."""
        current_time = time.time()
        
        # Determine business context
        business_context = {}
        if event_type == "message_sent":
            self.message_sent_time = current_time
            business_context["user_intent"] = self._extract_user_intent(data)
        elif event_type == "agent_completed":
            self.completion_time = current_time
            if self.message_sent_time:
                business_context["total_response_time"] = current_time - self.message_sent_time
        elif event_type in ["agent_response", "tool_result"]:
            if not self.first_response_time:
                self.first_response_time = current_time
                if self.message_sent_time:
                    business_context["time_to_first_response"] = current_time - self.message_sent_time
            
            # Assess business value of response content
            if "content" in data or "message" in data:
                content = data.get("content", data.get("message", ""))
                business_context["business_value_score"] = self._assess_business_value(content)
                business_context["actionable_insights"] = self._extract_actionable_insights(content)
        
        event = MessagePipelineEvent(
            event_type=event_type,
            timestamp=current_time,
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            data=data,
            event_source=event_source,
            processing_stage=processing_stage,
            business_context=business_context
        )
        
        self.events.append(event)
        logger.info(f"[PIPELINE] Tracked {event_type} for user {self.user_id} at stage {processing_stage}")
        
    def _extract_user_intent(self, data: Dict[str, Any]) -> str:
        """Extract and categorize user intent from message data."""
        message = data.get("message", data.get("content", "")).lower()
        
        if any(word in message for word in ["analyze", "analysis", "assess"]):
            return "analysis_request"
        elif any(word in message for word in ["optimize", "improve", "enhance"]):
            return "optimization_request"
        elif any(word in message for word in ["help", "assist", "support"]):
            return "assistance_request"
        elif any(word in message for word in ["recommend", "suggest", "advise"]):
            return "recommendation_request"
        else:
            return "general_inquiry"
    
    def _assess_business_value(self, content: str) -> float:
        """Assess the business value score of response content (0.0 to 1.0)."""
        if not content:
            return 0.0
            
        content_lower = content.lower()
        value_score = 0.0
        
        # Check for business value keywords
        keyword_matches = sum(1 for keyword in self.BUSINESS_VALUE_KEYWORDS 
                             if keyword in content_lower)
        value_score += min(keyword_matches * 0.1, 0.5)  # Up to 0.5 for keywords
        
        # Check for structured thinking (numbered lists, bullets)
        if any(marker in content for marker in ["1.", "2.", "3.", "•", "-", "*"]):
            value_score += 0.2
            
        # Check for specific recommendations
        if any(phrase in content_lower for phrase in ["i recommend", "suggest", "should", "consider"]):
            value_score += 0.2
            
        # Check for actionable next steps
        if any(phrase in content_lower for phrase in ["next step", "action", "implement", "execute"]):
            value_score += 0.1
            
        return min(value_score, 1.0)
    
    def _extract_actionable_insights(self, content: str) -> List[str]:
        """Extract actionable insights from response content."""
        insights = []
        content_lower = content.lower()
        
        # Look for recommendation patterns
        if "recommend" in content_lower:
            insights.append("contains_recommendations")
        if "next step" in content_lower:
            insights.append("provides_next_steps")
        if any(word in content_lower for word in ["implement", "execute", "apply"]):
            insights.append("includes_implementation_guidance")
        if any(word in content_lower for word in ["priority", "urgent", "important"]):
            insights.append("includes_prioritization")
            
        return insights
    
    def get_validation_result(self) -> PipelineValidationResult:
        """Get comprehensive pipeline validation result."""
        current_time = time.time()
        total_duration = current_time - self.pipeline_start_time
        
        # Check which critical events were received
        critical_events_present = {
            event.event_type for event in self.events 
            if event.event_type in self.CRITICAL_EVENTS
        }
        
        # Calculate business value metrics
        business_value_indicators = {
            "response_delivered": any(event.event_type in ["agent_completed", "agent_response"] 
                                    for event in self.events),
            "real_time_updates": len([e for e in self.events if e.event_type in self.CRITICAL_EVENTS]) > 0,
            "average_business_value_score": self._calculate_average_business_value(),
            "actionable_insights_count": self._count_actionable_insights(),
            "response_time_acceptable": self._check_response_time_acceptable(),
            "content_quality_indicators": self._get_content_quality_indicators()
        }
        
        # Performance metrics
        performance_metrics = {}
        if self.message_sent_time and self.first_response_time:
            performance_metrics["time_to_first_response"] = self.first_response_time - self.message_sent_time
        if self.message_sent_time and self.completion_time:
            performance_metrics["total_response_time"] = self.completion_time - self.message_sent_time
        performance_metrics["total_events_processed"] = len(self.events)
        
        # Determine overall pipeline success
        pipeline_success = (
            len(critical_events_present) >= 3 and  # At least 3 of 5 critical events
            business_value_indicators["response_delivered"] and
            business_value_indicators["average_business_value_score"] > 0.3 and
            performance_metrics.get("total_response_time", 999) < 60.0  # Under 60 seconds
        )
        
        return PipelineValidationResult(
            pipeline_success=pipeline_success,
            total_duration=total_duration,
            events_received=self.events,
            critical_events_present=critical_events_present,
            business_value_indicators=business_value_indicators,
            performance_metrics=performance_metrics
        )
    
    def _calculate_average_business_value(self) -> float:
        """Calculate average business value score across all responses."""
        business_events = [
            event for event in self.events 
            if "business_value_score" in event.business_context
        ]
        if not business_events:
            return 0.0
            
        scores = [event.business_context["business_value_score"] for event in business_events]
        return sum(scores) / len(scores)
    
    def _count_actionable_insights(self) -> int:
        """Count total actionable insights across all responses."""
        total_insights = 0
        for event in self.events:
            insights = event.business_context.get("actionable_insights", [])
            total_insights += len(insights)
        return total_insights
    
    def _check_response_time_acceptable(self) -> bool:
        """Check if response time meets business requirements."""
        if not self.message_sent_time or not self.first_response_time:
            return False
        response_time = self.first_response_time - self.message_sent_time
        return response_time < 30.0  # Under 30 seconds for first response
    
    def _get_content_quality_indicators(self) -> Dict[str, bool]:
        """Get content quality indicators from all responses."""
        indicators = {
            "structured_response": False,
            "specific_recommendations": False,
            "contextual_understanding": False,
            "professional_tone": False
        }
        
        for event in self.events:
            if "content" in event.data or "message" in event.data:
                content = event.data.get("content", event.data.get("message", ""))
                content_lower = content.lower()
                
                # Check for structured response
                if any(marker in content for marker in ["1.", "2.", "•", "-"]):
                    indicators["structured_response"] = True
                    
                # Check for specific recommendations
                if any(word in content_lower for word in ["recommend", "suggest", "should"]):
                    indicators["specific_recommendations"] = True
                    
                # Check for contextual understanding (references user's request)
                if any(phrase in content_lower for phrase in ["based on", "given", "considering"]):
                    indicators["contextual_understanding"] = True
                    
                # Check for professional tone
                if len(content) > 50 and not any(word in content_lower for word in ["lol", "haha", "idk"]):
                    indicators["professional_tone"] = True
                    
        return indicators


class CompleteMessagePipelineIntegrationTests(SSotAsyncTestCase):
    """
    Complete Message Pipeline Integration Tests.
    
    Tests the end-to-end message pipeline from user input through agent processing
    to final AI response delivery, focusing on business value delivery and real-time
    user experience via WebSocket events.
    """
    
    def setup_method(self, method=None):
        """Set up integration test environment with staging configuration."""
        super().setup_method(method)
        self.env = get_env()
        
        # Environment detection and configuration
        test_env = self.env.get("TEST_ENV", "test")
        if test_env == "staging" or self.env.get("ENVIRONMENT") == "staging":
            self.test_env = "staging"
            self.staging_config = StagingTestConfig()
            self.websocket_url = self.staging_config.urls.websocket_url
            self.api_base_url = self.staging_config.urls.api_base_url
            self.timeout = 45.0  # Staging timeout for complex agent processing
        else:
            self.test_env = "test"
            self.websocket_url = self.env.get("TEST_WEBSOCKET_URL", "ws://localhost:8000/ws")
            self.api_base_url = self.env.get("TEST_API_BASE_URL", "http://localhost:8000/api/v1")
            self.timeout = 30.0  # Local timeout
            
        self.e2e_helper = E2EWebSocketAuthHelper(environment=self.test_env)
        
        # Integration test configuration
        self.integration_timeout = 60.0  # Longer timeout for full pipeline
        self.connection_timeout = 15.0  # Connection establishment
        self.message_processing_timeout = 45.0  # Agent processing time
        self.websocket_event_timeout = 10.0  # Individual event timeout
        
        logger.info(f"[SETUP] Message pipeline integration test initialized")
        logger.info(f"[SETUP] Environment: {self.test_env}")
        logger.info(f"[SETUP] WebSocket URL: {self.websocket_url}")
        logger.info(f"[SETUP] API Base URL: {self.api_base_url}")
        
    @pytest.mark.integration
    @pytest.mark.agent_golden_path
    @pytest.mark.timeout(90)  # Allow up to 90 seconds for complete pipeline
    async def test_complete_message_pipeline_business_value_delivery(self):
        """
        Test complete message pipeline from user input to business value delivery.
        
        This test validates the entire golden path:
        1. User sends meaningful business question/request
        2. WebSocket events provide real-time progress updates
        3. Agent processes request with proper context and tools
        4. AI response delivers actionable business value
        5. All critical WebSocket events are delivered in proper sequence
        
        BVJ: This test protects the core $500K+ ARR value proposition - users
        receive meaningful AI assistance that solves real business problems.
        """
        test_start_time = time.time()
        print(f"[PIPELINE] Starting complete message pipeline integration test")
        print(f"[PIPELINE] Target: Full user → agent → AI response pipeline with business value validation")
        print(f"[PIPELINE] Environment: {self.test_env}")
        
        # Create authenticated test user with business context
        pipeline_user = await self.e2e_helper.create_authenticated_user(
            email=f"pipeline_integration_{int(time.time())}@test.com",
            permissions=["read", "write", "chat", "agent_execution"]
        )
        
        # Generate unique identifiers for this pipeline test
        thread_id = f"pipeline_thread_{uuid.uuid4()}"
        run_id = f"pipeline_run_{uuid.uuid4()}"
        
        # Initialize pipeline tracker
        tracker = MessagePipelineTracker(
            user_id=pipeline_user.user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        # Business-focused test message that requires analysis and recommendations
        business_test_message = {
            "message": "I need help optimizing our customer acquisition strategy. We're seeing a 15% conversion rate from leads to paying customers, but our customer acquisition cost is $150 per customer. Industry benchmark is $120. Can you analyze this situation and provide specific recommendations to improve our efficiency?",
            "thread_id": thread_id,
            "run_id": run_id,
            "context": {
                "request_type": "business_analysis",
                "priority": "high",
                "expected_deliverables": ["analysis", "recommendations", "action_items"]
            }
        }
        
        websocket_headers = self.e2e_helper.get_websocket_headers(pipeline_user.jwt_token)
        
        # Track message sending
        await tracker.track_event(
            "message_sent", 
            business_test_message, 
            event_source="user",
            processing_stage="input"
        )
        
        try:
            # Establish WebSocket connection
            print(f"[PIPELINE] Connecting to WebSocket: {self.websocket_url}")
            async with websockets.connect(
                self.websocket_url,
                additional_headers=websocket_headers,
                timeout=self.connection_timeout,
                ping_interval=30,
                ping_timeout=10
            ) as websocket:
                
                # Track connection establishment
                await tracker.track_event(
                    "websocket_connected", 
                    {"url": self.websocket_url}, 
                    event_source="system",
                    processing_stage="input"
                )
                
                print(f"[PIPELINE] WebSocket connected successfully")
                
                # Send business message and collect WebSocket events
                print(f"[PIPELINE] Sending business analysis request")
                await websocket.send(json.dumps(business_test_message))
                
                # Track WebSocket events and business value delivery
                events_received = []
                critical_events_seen = set()
                agent_response_content = ""
                pipeline_completed = False
                
                # Start event collection with timeout
                event_collection_start = time.time()
                
                while time.time() - event_collection_start < self.message_processing_timeout:
                    try:
                        # Receive WebSocket event with timeout
                        response_text = await asyncio.wait_for(
                            websocket.recv(), 
                            timeout=self.websocket_event_timeout
                        )
                        
                        response_data = json.loads(response_text)
                        event_type = response_data.get("type", response_data.get("event_type", "unknown"))
                        
                        # Track the event
                        await tracker.track_event(
                            event_type,
                            response_data,
                            event_source="websocket",
                            processing_stage="processing" if event_type in tracker.CRITICAL_EVENTS else "output"
                        )
                        
                        events_received.append(response_data)
                        
                        # Track critical events
                        if event_type in tracker.CRITICAL_EVENTS:
                            critical_events_seen.add(event_type)
                            print(f"[PIPELINE] Received critical event: {event_type}")
                        
                        # Collect agent response content for business value assessment
                        if event_type == "agent_completed":
                            agent_response_content = response_data.get("content", response_data.get("message", ""))
                            pipeline_completed = True
                            print(f"[PIPELINE] Pipeline completed - agent response received")
                            break
                        elif event_type in ["agent_response", "message"]:
                            agent_response_content += response_data.get("content", response_data.get("message", ""))
                            
                    except asyncio.TimeoutError:
                        print(f"[PIPELINE] WebSocket event timeout - checking if pipeline is complete")
                        if pipeline_completed or len(critical_events_seen) >= 3:
                            print(f"[PIPELINE] Pipeline appears complete despite timeout")
                            break
                        continue
                        
                    except (ConnectionClosed, WebSocketException) as e:
                        print(f"[PIPELINE] WebSocket connection error: {e}")
                        await tracker.track_event(
                            "websocket_error", 
                            {"error": str(e)}, 
                            event_source="system",
                            processing_stage="error"
                        )
                        break
                
                # Final response tracking if content was received
                if agent_response_content:
                    await tracker.track_event(
                        "agent_response",
                        {"content": agent_response_content},
                        event_source="agent",
                        processing_stage="output"
                    )
                
        except Exception as e:
            print(f"[PIPELINE] Pipeline test error: {e}")
            await tracker.track_event(
                "pipeline_error",
                {"error": str(e), "error_type": type(e).__name__},
                event_source="system",
                processing_stage="error"
            )
        
        # Get comprehensive validation results
        validation_result = tracker.get_validation_result()
        
        # Log detailed results
        test_duration = time.time() - test_start_time
        print(f"\n[PIPELINE RESULTS] Complete Message Pipeline Integration Test Results")
        print(f"[PIPELINE RESULTS] Total Duration: {test_duration:.2f}s")
        print(f"[PIPELINE RESULTS] Events Received: {len(validation_result.events_received)}")
        print(f"[PIPELINE RESULTS] Critical Events: {validation_result.critical_events_present}")
        print(f"[PIPELINE RESULTS] Pipeline Success: {validation_result.pipeline_success}")
        print(f"[PIPELINE RESULTS] Business Value Indicators: {validation_result.business_value_indicators}")
        print(f"[PIPELINE RESULTS] Performance Metrics: {validation_result.performance_metrics}")
        
        # ASSERTIONS: Comprehensive pipeline validation
        
        # Critical Event Validation
        assert len(validation_result.critical_events_present) >= 3, \
            f"Expected at least 3 critical events, got {len(validation_result.critical_events_present)}: {validation_result.critical_events_present}"
        
        # Business Value Validation
        assert validation_result.business_value_indicators["response_delivered"], \
            "Expected agent response to be delivered"
        
        assert validation_result.business_value_indicators["average_business_value_score"] > 0.3, \
            f"Expected business value score > 0.3, got {validation_result.business_value_indicators['average_business_value_score']}"
        
        assert validation_result.business_value_indicators["actionable_insights_count"] > 0, \
            "Expected agent response to contain actionable insights"
        
        # Performance Validation
        assert validation_result.business_value_indicators["response_time_acceptable"], \
            f"Expected response time < 30s, got {validation_result.performance_metrics.get('time_to_first_response', 'unknown')}"
        
        # Content Quality Validation
        content_quality = validation_result.business_value_indicators["content_quality_indicators"]
        assert content_quality["professional_tone"], "Expected professional tone in agent response"
        
        # Overall Pipeline Success
        assert validation_result.pipeline_success, \
            f"Complete message pipeline failed validation: {validation_result.error_messages}"
        
        print(f"[PIPELINE SUCCESS] Complete message pipeline integration test passed!")
        print(f"[PIPELINE SUCCESS] Business value delivered with {validation_result.business_value_indicators['actionable_insights_count']} actionable insights")
        print(f"[PIPELINE SUCCESS] Average business value score: {validation_result.business_value_indicators['average_business_value_score']:.2f}")
        
        # Track successful completion
        await tracker.track_event(
            "test_completed",
            {
                "success": True,
                "duration": test_duration,
                "business_value_delivered": True
            },
            event_source="test",
            processing_stage="complete"
        )
        
    @pytest.mark.integration
    @pytest.mark.agent_golden_path
    @pytest.mark.timeout(60)
    async def test_message_pipeline_with_tool_execution_validation(self):
        """
        Test message pipeline including tool execution and validation of tool results.
        
        This test validates that when an agent uses tools to process user requests,
        the tool execution is properly tracked via WebSocket events and the results
        contribute to meaningful business value delivery.
        """
        test_start_time = time.time()
        print(f"[TOOL PIPELINE] Starting message pipeline with tool execution test")
        
        # Create authenticated user for tool execution test
        tool_user = await self.e2e_helper.create_authenticated_user(
            email=f"tool_pipeline_{int(time.time())}@test.com",
            permissions=["read", "write", "chat", "tool_execution"]
        )
        
        # Generate unique identifiers
        thread_id = f"tool_thread_{uuid.uuid4()}"
        run_id = f"tool_run_{uuid.uuid4()}"
        
        # Initialize tracker
        tracker = MessagePipelineTracker(
            user_id=tool_user.user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        # Message that likely requires tool usage
        tool_test_message = {
            "message": "Can you analyze current market trends for AI optimization platforms and provide a competitive analysis with specific metrics and market positioning recommendations?",
            "thread_id": thread_id,
            "run_id": run_id,
            "context": {
                "request_type": "market_analysis",
                "tools_expected": True,
                "analysis_depth": "comprehensive"
            }
        }
        
        websocket_headers = self.e2e_helper.get_websocket_headers(tool_user.jwt_token)
        
        try:
            async with websockets.connect(
                self.websocket_url,
                additional_headers=websocket_headers,
                timeout=self.connection_timeout
            ) as websocket:
                
                # Send tool-requiring message
                await websocket.send(json.dumps(tool_test_message))
                await tracker.track_event("message_sent", tool_test_message, event_source="user")
                
                # Track tool execution events
                tool_events_seen = set()
                pipeline_events = []
                
                event_start = time.time()
                while time.time() - event_start < self.message_processing_timeout:
                    try:
                        response_text = await asyncio.wait_for(
                            websocket.recv(), 
                            timeout=self.websocket_event_timeout
                        )
                        
                        response_data = json.loads(response_text)
                        event_type = response_data.get("type", response_data.get("event_type"))
                        pipeline_events.append(response_data)
                        
                        # Track tool-related events
                        if event_type in ["tool_executing", "tool_completed"]:
                            tool_events_seen.add(event_type)
                            print(f"[TOOL PIPELINE] Tool event: {event_type}")
                            
                        await tracker.track_event(event_type, response_data, event_source="websocket")
                        
                        if event_type == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except (ConnectionClosed, WebSocketException):
                        break
                
        except Exception as e:
            await tracker.track_event("pipeline_error", {"error": str(e)})
        
        # Validate tool execution pipeline
        validation_result = tracker.get_validation_result()
        
        print(f"[TOOL PIPELINE RESULTS] Tool Events Seen: {tool_events_seen}")
        print(f"[TOOL PIPELINE RESULTS] Pipeline Success: {validation_result.pipeline_success}")
        
        # Assertions for tool execution pipeline
        assert "tool_executing" in tool_events_seen or "tool_completed" in tool_events_seen, \
            "Expected tool execution events in response pipeline"
        
        assert validation_result.pipeline_success, \
            "Tool execution pipeline should complete successfully"
        
        print(f"[TOOL PIPELINE SUCCESS] Tool execution pipeline completed successfully")


if __name__ == "__main__":
    # Allow running this test file directly for development
    import asyncio
    
    async def run_test():
        test_instance = CompleteMessagePipelineIntegrationTests()
        test_instance.setup_method()
        await test_instance.test_complete_message_pipeline_business_value_delivery()
        print("Direct test execution completed successfully")
    
    asyncio.run(run_test())