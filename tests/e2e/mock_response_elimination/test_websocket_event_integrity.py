"""
WebSocket Event Integrity Tests

Business Value Justification (BVJ):
- Segment: All segments - WebSocket events are foundation of chat value
- Business Goal: Ensure WebSocket events accurately represent AI processing authenticity  
- Value Impact: Users must know when receiving authentic AI vs fallback responses
- Strategic Impact: Chat UI/UX credibility depends on honest event communication

CRITICAL: These tests validate that WebSocket events accurately reflect the authenticity
of AI processing and do not mislead users about whether they're receiving real AI
responses or fallback/mock responses.

Test Status: FAILING (Expected) - Proves WebSocket events can mislead users
Fix Required: Events must clearly distinguish authentic AI from fallback responses
"""

import asyncio
import pytest
import json
import logging
import time
from typing import Dict, List, Any, Optional, Set
import aiohttp
import websockets
from dataclasses import dataclass

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID

logger = logging.getLogger(__name__)


@dataclass
class WebSocketEventTrace:
    """Track WebSocket events with timing and authenticity indicators."""
    timestamp: float
    event_type: str
    data: Dict[str, Any]
    authenticity_indicators: Dict[str, Any]
    processing_context: Dict[str, Any]


class TestWebSocketEventIntegrity(BaseE2ETest):
    """
    FAILING TESTS: Prove WebSocket events can mislead users about AI authenticity.
    
    These tests validate that WebSocket events honestly communicate whether
    users are receiving authentic AI processing or fallback responses.
    """

    # Required WebSocket events for authentic AI interactions
    AUTHENTIC_AI_EVENTS = [
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    ]

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_websocket_events_distinguish_authentic_vs_fallback(
        self, real_services_fixture
    ):
        """
        FAILING TEST: WebSocket events don't distinguish authentic AI from fallback.
        
        Business Value: Users must know when they're receiving authentic AI analysis
        vs generic fallback responses to make informed decisions about the insights.
        
        Expected Failure: Events may indicate "agent_thinking" and "agent_completed"
        even when returning fallback responses, misleading users.
        """
        auth_helper = E2EAuthHelper()
        user = await auth_helper.create_authenticated_user(
            email="event.integrity.test@test.com",
            subscription_tier="mid"
        )
        
        backend_url = real_services_fixture["backend_url"]
        ws_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=ws_url,
            auth_token=user.jwt_token
        ) as websocket_client:
            
            # Send query designed to trigger fallback response
            fallback_trigger_query = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": " ALERT:  FORCE_FALLBACK_SCENARIO  ALERT:  " + "INVALID" * 1000,
                "context": {
                    "user_id": str(user.user_id),
                    "test_scenario": "fallback_trigger"
                },
                "request_id": f"fallback_event_test_{int(time.time())}"
            }
            
            await websocket_client.send_json(fallback_trigger_query)
            
            # Collect detailed event trace
            event_trace = []
            authentic_processing_detected = False
            fallback_response_detected = False
            
            async for event in websocket_client.receive_events(timeout=30):
                timestamp = time.time()
                event_type = event.get("type", "unknown")
                event_data = event.get("data", {})
                
                # Create detailed trace entry
                trace_entry = WebSocketEventTrace(
                    timestamp=timestamp,
                    event_type=event_type,
                    data=event_data,
                    authenticity_indicators=event_data.get("authenticity", {}),
                    processing_context=event_data.get("context", {})
                )
                event_trace.append(trace_entry)
                
                logger.info(f"Event: {event_type} at {timestamp}")
                
                # Check if this event indicates authentic processing
                if event_type == "agent_thinking":
                    thinking_content = event_data.get("content", "").lower()
                    if any(indicator in thinking_content 
                           for indicator in ["analyzing", "processing", "calculating"]):
                        authentic_processing_detected = True
                
                # Check for completion with fallback response
                if event_type == "agent_completed":
                    response_content = event_data.get("response", "").lower()
                    if any(fallback in response_content 
                           for fallback in [
                               "i apologize, but i encountered an error",
                               "processing completed with fallback",
                               "fallback response"
                           ]):
                        fallback_response_detected = True
                    break
            
            assert len(event_trace) > 0, "No WebSocket events received"
            
            #  WARNING: [U+FE0F] THIS IS THE FAILING ASSERTION  WARNING: [U+FE0F]
            # If we detected both authentic processing events AND fallback response,
            # this is misleading to users
            
            if authentic_processing_detected and fallback_response_detected:
                assert False, (
                    f"MISLEADING WEBSOCKET EVENTS: Events indicated authentic processing "
                    f"(agent_thinking with analysis content) but final response was fallback. "
                    f"This misleads users about the authenticity of the AI response. "
                    f"Event trace: {[e.event_type for e in event_trace]}"
                )
            
            # Verify events have proper authenticity indicators
            completion_events = [e for e in event_trace if e.event_type == "agent_completed"]
            if completion_events:
                completion_event = completion_events[-1]
                
                if fallback_response_detected:
                    # Must have authenticity indicators showing this was fallback
                    authenticity = completion_event.authenticity_indicators
                    
                    if not authenticity:
                        assert False, (
                            f"MISSING AUTHENTICITY METADATA: Fallback response sent "
                            f"without authenticity indicators in WebSocket event. "
                            f"Users need to know response authenticity."
                        )
                    
                    is_fallback = authenticity.get("is_fallback", False)
                    is_authentic = authenticity.get("is_authentic", True)
                    
                    assert is_fallback == True, (
                        f"INCORRECT AUTHENTICITY METADATA: Fallback response but "
                        f"is_fallback != True. Authenticity data: {authenticity}"
                    )
                    
                    assert is_authentic == False, (
                        f"INCORRECT AUTHENTICITY METADATA: Fallback response but "
                        f"is_authentic != False. Authenticity data: {authenticity}"
                    )

    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.mission_critical
    async def test_websocket_events_preserve_user_trust_during_failures(
        self, real_services_fixture
    ):
        """
        FAILING TEST: WebSocket events may not maintain user trust during system failures.
        
        Business Value: When systems fail, WebSocket events must honestly communicate
        the failure without creating false impression of AI processing success.
        
        Expected Failure: Events may suggest successful AI processing even when
        returning generic error messages.
        """
        auth_helper = E2EAuthHelper()
        user = await auth_helper.create_authenticated_user(
            email="trust.preservation.test@test.com",
            subscription_tier="enterprise"
        )
        
        backend_url = real_services_fixture["backend_url"]
        ws_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=ws_url,
            auth_token=user.jwt_token
        ) as websocket_client:
            
            # Send query to trigger system failure scenario
            system_failure_query = {
                "type": "agent_request",
                "agent": "unified_data_agent", 
                "message": (
                    "SYSTEM_FAILURE_TEST: Request analytics data that should trigger "
                    "data access failure and return to fallback data generation"
                ),
                "context": {
                    "user_id": str(user.user_id),
                    "subscription": "enterprise",
                    "failure_test": True
                },
                "request_id": f"system_failure_test_{int(time.time())}"
            }
            
            await websocket_client.send_json(system_failure_query)
            
            # Monitor events for trust-preserving communication
            events = []
            trust_indicators = []
            system_status_updates = []
            
            async for event in websocket_client.receive_events(timeout=45):
                events.append(event)
                event_type = event.get("type")
                event_data = event.get("data", {})
                
                # Look for trust-preserving communication
                if event_type == "system_status":
                    system_status_updates.append(event_data)
                
                if event_type in ["agent_thinking", "agent_completed"]:
                    content = event_data.get("content", "") or event_data.get("response", "")
                    
                    # Check for trust-preserving language
                    trust_preserving_phrases = [
                        "experiencing difficulty",
                        "system temporarily unavailable", 
                        "working to resolve",
                        "please try again",
                        "service interruption"
                    ]
                    
                    if any(phrase in content.lower() for phrase in trust_preserving_phrases):
                        trust_indicators.append({
                            "event_type": event_type,
                            "content": content[:100],
                            "timestamp": time.time()
                        })
                
                if event_type == "agent_completed":
                    break
            
            assert len(events) > 0, "No events for system failure scenario"
            
            # Find final response
            completion_event = None
            for event in reversed(events):
                if event.get("type") == "agent_completed":
                    completion_event = event
                    break
            
            assert completion_event is not None, "No completion event"
            
            response_data = completion_event.get("data", {})
            response_content = response_data.get("response", "")
            
            # Check if this was a system failure that returned fallback
            is_system_failure = any(
                indicator in response_content.lower()
                for indicator in [
                    "i apologize, but i encountered an error",
                    "processing completed with fallback",  
                    "data access failed",
                    "system error"
                ]
            )
            
            if is_system_failure:
                #  WARNING: [U+FE0F] THIS IS THE FAILING ASSERTION  WARNING: [U+FE0F] 
                # System failures must be communicated with trust-preserving events
                
                assert len(trust_indicators) > 0, (
                    f"TRUST VIOLATION: System failure occurred but no trust-preserving "
                    f"communication sent via WebSocket events. Users deserve honest "
                    f"communication about system status. Response: {response_content[:200]}..."
                )
                
                # Events should not suggest successful processing during failure
                thinking_events = [e for e in events if e.get("type") == "agent_thinking"]
                
                for thinking_event in thinking_events:
                    thinking_data = thinking_event.get("data", {})
                    thinking_content = thinking_data.get("content", "").lower()
                    
                    success_indicators = [
                        "analysis complete",
                        "processing successful", 
                        "data retrieved successfully",
                        "optimization found"
                    ]
                    
                    for success_indicator in success_indicators:
                        assert success_indicator not in thinking_content, (
                            f"MISLEADING SUCCESS INDICATION: agent_thinking event "
                            f"indicated '{success_indicator}' but system actually failed. "
                            f"Full thinking content: {thinking_content}"
                        )
                
                # Completion event must indicate the failure honestly
                completion_data = completion_event.get("data", {})
                failure_acknowledged = completion_data.get("failure_acknowledged", False)
                
                assert failure_acknowledged == True, (
                    f"FAILURE NOT ACKNOWLEDGED: System failure occurred but "
                    f"completion event did not acknowledge failure to user. "
                    f"Completion data: {completion_data}"
                )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_websocket_events_validate_authentic_ai_workflow(
        self, real_services_fixture
    ):
        """
        FAILING TEST: WebSocket events may not properly validate authentic AI workflow.
        
        Business Value: The 5 critical WebSocket events (agent_started, agent_thinking,
        tool_executing, tool_completed, agent_completed) must only be sent when
        genuine AI processing occurs, not during fallback responses.
        
        Expected Failure: All 5 events may be sent even when no authentic AI 
        processing occurred.
        """
        auth_helper = E2EAuthHelper()
        user = await auth_helper.create_authenticated_user(
            email="ai.workflow.test@test.com",
            subscription_tier="mid"
        )
        
        backend_url = real_services_fixture["backend_url"]
        ws_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=ws_url,
            auth_token=user.jwt_token
        ) as websocket_client:
            
            # Query designed to trigger mock/fallback without real AI
            mock_trigger_query = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "MOCK_TRIGGER: " + "X" * 5000,  # Overwhelm system
                "context": {
                    "user_id": str(user.user_id),
                    "ai_workflow_test": True
                },
                "request_id": f"ai_workflow_test_{int(time.time())}"
            }
            
            await websocket_client.send_json(mock_trigger_query)
            
            # Track the 5 critical AI events
            ai_event_tracker = {
                "agent_started": [],
                "agent_thinking": [],
                "tool_executing": [],
                "tool_completed": [],
                "agent_completed": []
            }
            
            genuine_ai_indicators = {
                "llm_api_called": False,
                "tool_execution": False, 
                "data_analysis": False,
                "reasoning_process": False
            }
            
            async for event in websocket_client.receive_events(timeout=30):
                event_type = event.get("type")
                event_data = event.get("data", {})
                
                # Track the 5 critical events
                if event_type in ai_event_tracker:
                    ai_event_tracker[event_type].append({
                        "timestamp": time.time(),
                        "data": event_data
                    })
                
                # Look for genuine AI processing indicators
                if event_type == "agent_thinking":
                    thinking_content = event_data.get("content", "").lower()
                    if any(indicator in thinking_content for indicator in [
                        "llm", "openai", "model", "api", "reasoning"
                    ]):
                        genuine_ai_indicators["reasoning_process"] = True
                
                if event_type == "tool_executing":
                    genuine_ai_indicators["tool_execution"] = True
                
                if event_type == "tool_completed":
                    tool_result = event_data.get("result", {})
                    if tool_result and not event_data.get("is_fallback", False):
                        genuine_ai_indicators["data_analysis"] = True
                
                # Check for LLM API indicators
                processing_meta = event_data.get("processing_metadata", {})
                if processing_meta.get("llm_api_called"):
                    genuine_ai_indicators["llm_api_called"] = True
                
                if event_type == "agent_completed":
                    break
            
            # Analyze what events were sent
            events_sent = [event_type for event_type, events in ai_event_tracker.items() if events]
            
            # Check if final response was mock/fallback
            completion_events = ai_event_tracker["agent_completed"]
            assert len(completion_events) > 0, "No completion event received"
            
            final_response_data = completion_events[-1]["data"]
            response_content = final_response_data.get("response", "").lower()
            
            is_fallback_response = any(
                fallback in response_content
                for fallback in [
                    "i apologize, but i encountered an error",
                    "processing completed with fallback",
                    "fallback response"
                ]
            )
            
            # Count genuine AI processing indicators
            genuine_indicators_count = sum(genuine_ai_indicators.values())
            
            if is_fallback_response:
                #  WARNING: [U+FE0F] THIS IS THE FAILING ASSERTION  WARNING: [U+FE0F]
                # If response was fallback, events should reflect this honestly
                
                # Should not send "agent_thinking" for fallback responses
                thinking_events = ai_event_tracker["agent_thinking"]
                if thinking_events and genuine_indicators_count == 0:
                    assert False, (
                        f"MISLEADING AI WORKFLOW EVENTS: Sent 'agent_thinking' events "
                        f"but no genuine AI processing detected and response was fallback. "
                        f"Events sent: {events_sent}, Response: {response_content[:100]}..."
                    )
                
                # Should not send tool events for fallback responses
                tool_executing = ai_event_tracker["tool_executing"]
                tool_completed = ai_event_tracker["tool_completed"]
                
                if tool_executing and not genuine_ai_indicators["tool_execution"]:
                    assert False, (
                        f"MISLEADING TOOL EXECUTION: Sent 'tool_executing' events "
                        f"but no actual tool execution occurred (fallback response). "
                        f"Tool events: {len(tool_executing)}"
                    )
                
                if tool_completed and not genuine_ai_indicators["data_analysis"]:
                    assert False, (
                        f"MISLEADING TOOL COMPLETION: Sent 'tool_completed' events "
                        f"but no actual analysis occurred (fallback response). "
                        f"Tool completion events: {len(tool_completed)}"
                    )
            
            # Verify completion event has authenticity metadata
            final_completion_data = completion_events[-1]["data"]
            authenticity_meta = final_completion_data.get("authenticity", {})
            
            if not authenticity_meta:
                assert False, (
                    f"MISSING AUTHENTICITY METADATA: No authenticity information "
                    f"provided in agent_completed event. Users need to know if "
                    f"response is from genuine AI processing or fallback."
                )
            
            # Verify authenticity metadata matches actual processing
            claimed_authentic = authenticity_meta.get("is_authentic", True)
            actual_authentic = genuine_indicators_count > 0 and not is_fallback_response
            
            assert claimed_authentic == actual_authentic, (
                f"AUTHENTICITY METADATA MISMATCH: Claimed authentic={claimed_authentic} "
                f"but actual authentic processing={actual_authentic}. "
                f"Genuine indicators: {genuine_ai_indicators}, "
                f"Fallback response: {is_fallback_response}"
            )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_enterprise_websocket_events_premium_transparency(
        self, real_services_fixture
    ):
        """
        FAILING TEST: Enterprise customers may not receive premium transparency in events.
        
        Business Value: Enterprise customers ($500K+ ARR) deserve the highest level 
        of transparency about AI processing authenticity through WebSocket events.
        
        Expected Failure: Enterprise customers may receive same generic events as 
        free tier, lacking the premium transparency they pay for.
        """
        auth_helper = E2EAuthHelper()
        enterprise_user = await auth_helper.create_authenticated_user(
            email="enterprise.cto@fortune100.com",
            subscription_tier="enterprise",
            metadata={
                "arr_value": 750000,
                "premium_transparency": True,
                "executive_user": True
            }
        )
        
        backend_url = real_services_fixture["backend_url"]
        ws_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=ws_url,
            auth_token=enterprise_user.jwt_token
        ) as websocket_client:
            
            # Enterprise-level request requiring premium transparency
            enterprise_query = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": (
                    "Enterprise AI analysis: Provide comprehensive cost optimization "
                    "strategy for $10M annual cloud spend. Board presentation required."
                ),
                "context": {
                    "user_id": str(enterprise_user.user_id),
                    "subscription": "enterprise",
                    "arr_value": 750000,
                    "premium_transparency": True,
                    "executive_request": True
                },
                "request_id": f"enterprise_transparency_test_{int(time.time())}"
            }
            
            await websocket_client.send_json(enterprise_query)
            
            # Track enterprise-specific event enhancements
            enterprise_events = []
            transparency_features = {
                "detailed_processing_steps": False,
                "llm_model_information": False,
                "confidence_scores": False,
                "processing_time_breakdown": False,
                "data_source_attribution": False,
                "quality_indicators": False
            }
            
            async for event in websocket_client.receive_events(timeout=60):
                event_type = event.get("type")
                event_data = event.get("data", {})
                
                enterprise_events.append({
                    "type": event_type,
                    "timestamp": time.time(),
                    "data": event_data
                })
                
                # Check for enterprise transparency features
                if event_type == "agent_thinking":
                    thinking_data = event_data.get("processing_details", {})
                    if thinking_data.get("detailed_steps"):
                        transparency_features["detailed_processing_steps"] = True
                    
                    if thinking_data.get("llm_model"):
                        transparency_features["llm_model_information"] = True
                
                if event_type in ["tool_executing", "tool_completed"]:
                    if event_data.get("confidence_score") is not None:
                        transparency_features["confidence_scores"] = True
                    
                    if event_data.get("processing_time_ms"):
                        transparency_features["processing_time_breakdown"] = True
                    
                    if event_data.get("data_sources"):
                        transparency_features["data_source_attribution"] = True
                
                if event_type == "agent_completed":
                    quality_meta = event_data.get("quality_indicators", {})
                    if quality_meta:
                        transparency_features["quality_indicators"] = True
                    break
            
            assert len(enterprise_events) > 0, "No events for enterprise request"
            
            #  WARNING: [U+FE0F] ENTERPRISE TRANSPARENCY FAILING ASSERTIONS  WARNING: [U+FE0F]
            # Enterprise customers must receive premium transparency features
            
            transparency_score = sum(transparency_features.values())
            minimum_enterprise_features = 4  # At least 4 out of 6 features
            
            assert transparency_score >= minimum_enterprise_features, (
                f"INSUFFICIENT ENTERPRISE TRANSPARENCY: Only {transparency_score} "
                f"transparency features provided out of 6 available. Enterprise "
                f"customers ($750K ARR) deserve premium transparency. "
                f"Missing features: {[k for k, v in transparency_features.items() if not v]}"
            )
            
            # Verify completion event has enterprise-grade metadata
            completion_events = [e for e in enterprise_events if e["type"] == "agent_completed"]
            assert len(completion_events) > 0, "No completion event for enterprise user"
            
            completion_data = completion_events[-1]["data"]
            enterprise_metadata = completion_data.get("enterprise_metadata", {})
            
            required_enterprise_fields = [
                "processing_transparency_level",
                "ai_authenticity_verification",
                "quality_assurance_score",
                "premium_features_used"
            ]
            
            missing_fields = [
                field for field in required_enterprise_fields 
                if field not in enterprise_metadata
            ]
            
            assert len(missing_fields) == 0, (
                f"MISSING ENTERPRISE METADATA: Enterprise completion event lacks "
                f"required premium fields: {missing_fields}. Enterprise customers "
                f"deserve comprehensive metadata about AI processing quality."
            )
            
            # Verify authenticity verification is comprehensive for enterprise
            auth_verification = enterprise_metadata.get("ai_authenticity_verification", {})
            required_auth_fields = [
                "llm_api_verified",
                "processing_chain_validated", 
                "result_quality_confirmed",
                "fallback_usage_disclosed"
            ]
            
            missing_auth_fields = [
                field for field in required_auth_fields
                if field not in auth_verification
            ]
            
            assert len(missing_auth_fields) == 0, (
                f"INCOMPLETE AUTHENTICITY VERIFICATION: Enterprise users need "
                f"comprehensive AI authenticity verification. Missing: {missing_auth_fields}"
            )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_websocket_events_business_impact_transparency(
        self, real_services_fixture  
    ):
        """
        FAILING TEST: WebSocket events may not communicate business impact of AI authenticity.
        
        Business Value: Users need to understand the business implications of receiving
        authentic vs fallback AI responses to make informed decisions.
        
        Expected Failure: Events may not provide context about how response authenticity
        affects the business value or reliability of the insights provided.
        """
        auth_helper = E2EAuthHelper()
        business_user = await auth_helper.create_authenticated_user(
            email="business.strategist@company.com",
            subscription_tier="mid",
            metadata={
                "role": "business_strategist",
                "decision_authority": True
            }
        )
        
        backend_url = real_services_fixture["backend_url"]
        ws_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=ws_url,
            auth_token=business_user.jwt_token
        ) as websocket_client:
            
            # Business-critical query where authenticity matters
            critical_business_query = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": (
                    "Critical business decision: Should we migrate 500 servers to "
                    "reduce costs by 40%? Need AI analysis for executive recommendation."
                ),
                "context": {
                    "user_id": str(business_user.user_id),
                    "business_critical": True,
                    "decision_impact": "high",
                    "financial_implications": 500000
                },
                "request_id": f"business_impact_test_{int(time.time())}"
            }
            
            await websocket_client.send_json(critical_business_query)
            
            events = []
            business_impact_communication = []
            
            async for event in websocket_client.receive_events(timeout=45):
                events.append(event)
                event_type = event.get("type")
                event_data = event.get("data", {})
                
                # Look for business impact communication
                business_context = event_data.get("business_context", {})
                if business_context:
                    business_impact_communication.append({
                        "event_type": event_type,
                        "business_context": business_context,
                        "timestamp": time.time()
                    })
                
                # Check for reliability indicators
                reliability_info = event_data.get("reliability", {})
                if reliability_info:
                    business_impact_communication.append({
                        "event_type": event_type,  
                        "reliability_info": reliability_info,
                        "timestamp": time.time()
                    })
                
                if event_type == "agent_completed":
                    break
            
            assert len(events) > 0, "No events for business-critical query"
            
            # Find completion event and check response authenticity
            completion_event = None
            for event in reversed(events):
                if event.get("type") == "agent_completed":
                    completion_event = event
                    break
            
            assert completion_event is not None, "No completion for business query"
            
            completion_data = completion_event.get("data", {})
            response_content = completion_data.get("response", "")
            
            # Determine if response was authentic or fallback
            is_fallback = any(
                fallback_indicator in response_content.lower()
                for fallback_indicator in [
                    "i apologize, but i encountered an error",
                    "processing completed with fallback",
                    "fallback response"
                ]
            )
            
            #  WARNING: [U+FE0F] BUSINESS IMPACT TRANSPARENCY FAILING ASSERTION  WARNING: [U+FE0F]
            # Business-critical queries must have clear impact communication
            
            if is_fallback:
                # Must communicate business implications of fallback response
                business_impact_indicators = completion_data.get("business_impact", {})
                
                if not business_impact_indicators:
                    assert False, (
                        f"MISSING BUSINESS IMPACT COMMUNICATION: Business-critical query "
                        f"received fallback response but no communication about business "
                        f"implications. Users need to understand reliability impact."
                    )
                
                # Should warn about decision-making reliability
                reliability_warning = business_impact_indicators.get("reliability_warning")
                decision_confidence = business_impact_indicators.get("decision_confidence")
                
                assert reliability_warning is not None, (
                    f"MISSING RELIABILITY WARNING: Business-critical fallback response "
                    f"lacks warning about reliability for decision-making."
                )
                
                assert decision_confidence is not None and decision_confidence < 0.5, (
                    f"INCORRECT DECISION CONFIDENCE: Fallback response for business "
                    f"decision should have low confidence score. Got: {decision_confidence}"
                )
            
            else:
                # Authentic response should communicate confidence level
                authenticity_data = completion_data.get("authenticity", {})
                confidence_data = completion_data.get("confidence", {})
                
                if not authenticity_data and not confidence_data:
                    assert False, (
                        f"MISSING CONFIDENCE COMMUNICATION: Business-critical query "
                        f"received authentic response but no confidence/reliability "
                        f"information provided for decision-making."
                    )
            
            # Verify business context was maintained throughout conversation
            business_aware_events = [
                event for event in events 
                if event.get("data", {}).get("business_context") or 
                   event.get("data", {}).get("decision_impact")
            ]
            
            assert len(business_aware_events) >= 2, (
                f"INSUFFICIENT BUSINESS CONTEXT: Only {len(business_aware_events)} "
                f"events maintained business context awareness. Business-critical "
                f"queries need consistent business impact communication."
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])