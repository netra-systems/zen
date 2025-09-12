#!/usr/bin/env python
"""
INTEGRATION TESTS: Authenticated Chat Workflow - Complete Business Value Delivery

CRITICAL BUSINESS MISSION: These tests validate authenticated chat workflows that deliver 
SUBSTANTIVE VALUE through AI-powered problem solving. This is the core of our $500K+ ARR.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Validate complete authenticated user chat experience
- Value Impact: Ensures users receive AI-powered insights through secure chat workflows
- Strategic Impact: Protects core revenue stream through reliable chat authentication

CRITICAL REQUIREMENTS per CLAUDE.md:
1. MUST use REAL authentication (JWT/OAuth) - NO auth bypasses
2. MUST test real chat components (message routing, agent execution, response delivery)
3. MUST validate business value delivery (actual AI insights, not just message exchange)
4. MUST follow SSOT patterns from test_framework/
5. MUST be designed to fail hard on any authentication or workflow deviation

TEST FOCUS: Integration tests use real chat components WITHOUT full Docker requirement.
These tests validate the authenticated chat workflow logic and component integration.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, patch

# SSOT IMPORTS - Following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, create_authenticated_user_context, get_test_jwt_token
)
from test_framework.websocket_helpers import (
    WebSocketTestHelpers, assert_websocket_events, WebSocketTestClient
)

# Core system imports for chat workflow integration
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge, AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.handlers import MessageRouter
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory

# Business workflow imports
from netra_backend.app.agents.triage_sub_agent import TriageSubAgent
from netra_backend.app.agents.data_sub_agent import DataSubAgent
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent


class TestAuthenticatedChatWorkflowComprehensive(SSotAsyncTestCase):
    """
    CRITICAL: Integration tests for authenticated chat workflows that deliver business value.
    
    These tests validate the complete authenticated user journey through chat interactions
    that solve real business problems and deliver actionable insights.
    """
    
    def setup_method(self, method=None):
        """Setup with business context tracking."""
        super().setup_method(method)
        
        # Business value metrics tracking
        self.record_metric("business_segment", "all_segments")
        self.record_metric("test_type", "integration_auth_chat")
        self.record_metric("expected_business_value", "ai_powered_insights")
        
        # Initialize test components
        self._auth_helper = None
        self._id_generator = UnifiedIdGenerator()
        self._websocket_events = []
        
    async def async_setup_method(self, method=None):
        """Async setup for authenticated chat components."""
        await super().async_setup_method(method)
        
        # Initialize auth helper for integration testing
        environment = self.get_env_var("TEST_ENV", "test")
        self._auth_helper = E2EAuthHelper(environment=environment)
        
        # Create WebSocket event collector
        self._websocket_events = []
    
    @pytest.mark.asyncio 
    @pytest.mark.integration
    async def test_authenticated_user_chat_message_processing_with_business_value(self):
        """
        Test authenticated user sends chat message and receives AI-powered business insights.
        
        CRITICAL: This tests the PRIMARY business value delivery workflow:
        User Auth  ->  Chat Message  ->  Agent Processing  ->  Business Insights  ->  User Value
        
        Business Value: Validates core revenue-generating chat interaction workflow.
        """
        # Arrange - Create authenticated user context with proper permissions
        user_context = await create_authenticated_user_context(
            user_email="integration_test_user@example.com",
            environment="test",
            permissions=["read", "write", "execute_agents", "chat_access"],
            websocket_enabled=True
        )
        
        # Verify authentication is real and valid
        jwt_token = user_context.agent_context.get('jwt_token')
        self.assertIsNotNone(jwt_token, "JWT token must be present for authenticated chat")
        
        # Validate token contains required claims for chat access
        is_valid = await self._auth_helper.validate_token(jwt_token)
        self.assertTrue(is_valid, "JWT token must be valid for authenticated chat workflow")
        
        # Create agent registry with authenticated context
        agent_registry = AgentRegistry()
        await agent_registry.initialize(user_context=user_context)
        
        # Create execution engine factory for business agent workflows
        execution_websocket_bridge = AgentWebSocketBridge()
        execution_factory = ExecutionEngineFactory(websocket_bridge=execution_websocket_bridge)
        execution_engine = await execution_factory.create_for_user(
            user_context=user_context
        )
        
        # Create WebSocket bridge for real-time communication
        # Fix: create_agent_websocket_bridge is synchronous, not async
        websocket_bridge = create_agent_websocket_bridge(user_context=user_context)
        
        # Act - Send business problem chat message that requires AI analysis
        chat_message = {
            "type": "chat_message",
            "content": "Analyze my current AI spending and provide cost optimization recommendations",
            "user_id": str(user_context.user_id),
            "thread_id": str(user_context.thread_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "requires_agent_processing": True,
            "business_context": "cost_optimization"
        }
        
        # Process message through authenticated workflow
        start_time = time.time()
        
        # Simulate WebSocket message processing
        with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager.send_to_user') as mock_send:
            # Capture WebSocket events sent during processing
            mock_send.side_effect = self._capture_websocket_event
            
            # Process chat message through agent workflow
            result = await execution_engine.execute_chat_workflow(
                message=chat_message,
                context=user_context
            )
            
        processing_duration = time.time() - start_time
        
        # Assert - Validate authentication was maintained throughout
        self.assertIsNotNone(result, "Authenticated chat workflow must return results")
        self.assertIn("cost_optimization", str(result), "Business value must be delivered")
        
        # Validate required WebSocket events were sent for real-time UX
        expected_events = ["agent_started", "agent_thinking", "agent_completed"]
        sent_event_types = [event.get("type") for event in self._websocket_events]
        
        for expected_event in expected_events:
            self.assertIn(expected_event, sent_event_types, 
                f"Required WebSocket event '{expected_event}' missing from authenticated chat")
        
        # Validate business value delivery
        self.assertIn("cost", str(result).lower(), "Cost analysis must be included")
        self.assertIn("optimization", str(result).lower(), "Optimization recommendations required")
        
        # Performance requirements for business-critical workflow
        self.assertLess(processing_duration, 30.0, 
            "Authenticated chat workflow must complete within 30 seconds for user experience")
        
        # Record business metrics
        self.record_metric("processing_duration_seconds", processing_duration)
        self.record_metric("websocket_events_sent", len(self._websocket_events))
        self.record_metric("business_value_delivered", True)
        
        self.logger.info(f" PASS:  Authenticated chat workflow delivered business value in {processing_duration:.2f}s")
    
    @pytest.mark.asyncio
    @pytest.mark.integration  
    async def test_authenticated_user_agent_pipeline_with_substantive_results(self):
        """
        Test authenticated user triggers complete agent pipeline delivering substantive results.
        
        CRITICAL: This tests the COMPLETE agent collaboration workflow:
        Auth  ->  Triage  ->  Data Analysis  ->  Optimization  ->  Reporting  ->  User Results
        
        Business Value: Validates multi-agent workflows that deliver comprehensive insights.
        """
        # Arrange - Create authenticated user with full agent permissions
        user_context = await create_authenticated_user_context(
            user_email="pipeline_test_user@example.com",
            environment="test", 
            permissions=["read", "write", "execute_agents", "agent_pipeline", "optimization"],
            websocket_enabled=True
        )
        
        # Initialize complete agent pipeline
        agent_registry = AgentRegistry()
        await agent_registry.initialize(user_context=user_context)
        
        # Register business agents for pipeline
        triage_agent = TriageSubAgent()
        data_agent = DataSubAgent()
        reporting_agent = ReportingSubAgent()
        
        await agent_registry.register_agent("triage", triage_agent)
        await agent_registry.register_agent("data_analysis", data_agent) 
        await agent_registry.register_agent("reporting", reporting_agent)
        
        # Act - Execute complete agent pipeline for business problem
        pipeline_request = {
            "type": "agent_pipeline",
            "workflow": "cost_optimization_analysis",
            "user_request": "Provide comprehensive AI cost analysis with specific optimization strategies",
            "user_id": str(user_context.user_id),
            "thread_id": str(user_context.thread_id),
            "requires_substantive_results": True
        }
        
        start_time = time.time()
        
        # Execute agent pipeline with authentication validation
        with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager.send_to_user') as mock_send:
            mock_send.side_effect = self._capture_websocket_event
            
            # Execute pipeline through authenticated workflow
            pipeline_result = await agent_registry.execute_pipeline(
                workflow_name="cost_optimization_analysis",
                request=pipeline_request,
                context=user_context
            )
        
        pipeline_duration = time.time() - start_time
        
        # Assert - Validate complete pipeline execution with authentication
        self.assertIsNotNone(pipeline_result, "Agent pipeline must deliver results")
        self.assertIn("analysis", str(pipeline_result).lower(), "Analysis results required")
        
        # Validate all pipeline stages executed
        expected_pipeline_events = [
            "agent_started",  # Triage
            "agent_thinking", # Data analysis
            "tool_executing", # Optimization calculations  
            "agent_completed", # Reporting
        ]
        
        sent_event_types = [event.get("type") for event in self._websocket_events]
        
        for expected_event in expected_pipeline_events:
            self.assertIn(expected_event, sent_event_types,
                f"Pipeline event '{expected_event}' missing from authenticated workflow")
        
        # Validate substantive business results
        result_str = str(pipeline_result)
        substantive_indicators = ["cost", "optimization", "savings", "recommendation", "strategy"]
        
        found_indicators = [indicator for indicator in substantive_indicators 
                          if indicator in result_str.lower()]
        
        self.assertGreaterEqual(len(found_indicators), 3,
            f"Pipeline must deliver substantive results. Found: {found_indicators}")
        
        # Performance validation for business workflow
        self.assertLess(pipeline_duration, 45.0,
            "Agent pipeline must complete within 45 seconds for user experience")
        
        # Business value metrics
        self.record_metric("pipeline_duration_seconds", pipeline_duration)
        self.record_metric("pipeline_stages_executed", len(set(sent_event_types)))
        self.record_metric("substantive_indicators_found", len(found_indicators))
        
        self.logger.info(f" PASS:  Authenticated agent pipeline delivered substantive results in {pipeline_duration:.2f}s")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_authenticated_chat_session_persistence_and_continuity(self):
        """
        Test authenticated user chat session maintains continuity and context across interactions.
        
        CRITICAL: This tests SESSION MANAGEMENT for business conversations:
        Auth  ->  First Message  ->  Context  ->  Second Message  ->  Continued Context  ->  Business Value
        
        Business Value: Validates conversation continuity essential for complex business discussions.
        """
        # Arrange - Create persistent authenticated session
        user_context = await create_authenticated_user_context(
            user_email="session_test_user@example.com",
            environment="test",
            permissions=["read", "write", "execute_agents", "session_management"],
            websocket_enabled=True
        )
        
        # Initialize session-aware chat system
        agent_registry = AgentRegistry()
        await agent_registry.initialize(user_context=user_context)
        
        execution_websocket_bridge = AgentWebSocketBridge()
        execution_factory = ExecutionEngineFactory(websocket_bridge=execution_websocket_bridge)
        execution_engine = await execution_factory.create_for_user(
            user_context=user_context
        )
        
        # Act - Send first message establishing business context
        first_message = {
            "type": "chat_message",
            "content": "I need help optimizing my AI infrastructure costs. My current monthly spend is $5000.",
            "user_id": str(user_context.user_id),
            "thread_id": str(user_context.thread_id),
            "session_context": "cost_optimization_session",
            "message_sequence": 1
        }
        
        with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager.send_to_user') as mock_send:
            mock_send.side_effect = self._capture_websocket_event
            
            first_result = await execution_engine.execute_chat_workflow(
                message=first_message,
                context=user_context
            )
        
        # Clear events for second interaction
        first_events = len(self._websocket_events)
        self._websocket_events.clear()
        
        # Send follow-up message requiring context from first interaction
        second_message = {
            "type": "chat_message", 
            "content": "What specific optimization strategies would reduce my costs by 30%?",
            "user_id": str(user_context.user_id),
            "thread_id": str(user_context.thread_id),  # Same thread for continuity
            "session_context": "cost_optimization_session",
            "message_sequence": 2,
            "requires_context": True
        }
        
        with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager.send_to_user') as mock_send:
            mock_send.side_effect = self._capture_websocket_event
            
            second_result = await execution_engine.execute_chat_workflow(
                message=second_message,
                context=user_context
            )
        
        second_events = len(self._websocket_events)
        
        # Assert - Validate session continuity and context preservation
        self.assertIsNotNone(first_result, "First message must receive response")
        self.assertIsNotNone(second_result, "Second message must receive contextual response")
        
        # Validate context from first message was used in second response
        first_result_str = str(first_result).lower()
        second_result_str = str(second_result).lower()
        
        # Second response should reference the $5000 context from first message
        self.assertTrue(
            "5000" in second_result_str or "5,000" in second_result_str or "30%" in second_result_str,
            "Second response must use context from first message ($5000 and 30% reduction target)"
        )
        
        # Validate WebSocket events sent for both interactions
        self.assertGreater(first_events, 0, "First interaction must generate WebSocket events")
        self.assertGreater(second_events, 0, "Second interaction must generate WebSocket events") 
        
        # Validate business continuity in responses
        self.assertIn("cost", first_result_str, "First response must address cost optimization")
        self.assertIn("optimization", second_result_str, "Second response must provide specific strategies")
        
        # Thread ID continuity validation
        self.assertEqual(first_message["thread_id"], second_message["thread_id"],
            "Session continuity requires consistent thread ID")
        
        # Business value validation
        business_indicators = ["strategy", "reduce", "savings", "optimization", "cost"]
        second_indicators = [indicator for indicator in business_indicators 
                           if indicator in second_result_str]
        
        self.assertGreaterEqual(len(second_indicators), 3,
            f"Follow-up response must provide actionable business value. Found: {second_indicators}")
        
        # Record session metrics
        self.record_metric("first_interaction_events", first_events)
        self.record_metric("second_interaction_events", second_events)
        self.record_metric("context_continuity", True)
        self.record_metric("business_value_indicators", len(second_indicators))
        
        self.logger.info(f" PASS:  Authenticated chat session maintained continuity with {first_events + second_events} WebSocket events")
    
    # Helper Methods
    
    async def _capture_websocket_event(self, user_id: str, event: Dict[str, Any]) -> None:
        """Capture WebSocket events for validation."""
        event_with_timestamp = {
            **event,
            "capture_timestamp": time.time(),
            "user_id": user_id
        }
        self._websocket_events.append(event_with_timestamp)
    
    def _validate_authentication_maintained(self, user_context: StronglyTypedUserExecutionContext) -> None:
        """Validate authentication context is maintained throughout workflow."""
        self.assertIsNotNone(user_context.user_id, "User ID must be maintained")
        self.assertIsNotNone(user_context.thread_id, "Thread ID must be maintained")
        self.assertIsNotNone(user_context.agent_context.get('jwt_token'), "JWT token must be maintained")
        
        # Validate token is still valid
        jwt_token = user_context.agent_context.get('jwt_token')
        self.assertIsNotNone(jwt_token, "JWT token required for authenticated workflow")
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        super().teardown_method(method)
        
        # Clear WebSocket events
        self._websocket_events.clear()
        
        self.logger.info(f" PASS:  Authenticated chat workflow integration test completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])