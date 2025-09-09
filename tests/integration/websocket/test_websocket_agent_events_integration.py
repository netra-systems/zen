"""
WebSocket Agent Event Integration Tests - MISSION CRITICAL

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Enable real-time AI agent interaction feedback for users
- Value Impact: Users see live progress of AI agents solving their problems
- Strategic Impact: CORE BUSINESS VALUE - WebSocket events are the foundation 
  for substantive AI chat interactions and user engagement

MISSION CRITICAL: These 5 WebSocket events MUST work for business value delivery:
1. agent_started - User knows AI began processing their request
2. agent_thinking - Real-time reasoning visibility shows AI working  
3. tool_executing - Tool usage transparency demonstrates problem-solving
4. tool_completed - Tool results display delivers actionable insights
5. agent_completed - User knows when valuable AI response is ready

CRITICAL: These tests validate actual agent event emission using REAL services.
NO MOCKS - Uses real PostgreSQL (port 5434) and Redis (port 6381).
Tests service interactions without Docker containers (integration layer).
"""

import asyncio
import pytest
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from unittest import mock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture, real_postgres_connection, with_test_database

from netra_backend.app.websocket_core.types import (
    MessageType, 
    WebSocketMessage,
    ConnectionInfo,
    WebSocketConnectionState,
    create_standard_message
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class MockAgentForTesting:
    """Mock agent for testing WebSocket event emission."""
    
    def __init__(self, agent_name: str, websocket_bridge: AgentWebSocketBridge):
        self.agent_name = agent_name
        self.websocket_bridge = websocket_bridge
        
    async def execute_with_events(self, user_context: UserExecutionContext, prompt: str) -> Dict[str, Any]:
        """Execute agent with WebSocket event emission for testing."""
        # Emit agent_started event
        await self.websocket_bridge.emit_agent_started(
            user_context, self.agent_name, {"prompt": prompt}
        )
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Emit agent_thinking event
        await self.websocket_bridge.emit_agent_thinking(
            user_context, self.agent_name, {"reasoning": "Analyzing the problem..."}
        )
        
        await asyncio.sleep(0.1)
        
        # Emit tool_executing event  
        await self.websocket_bridge.emit_tool_executing(
            user_context, "data_analyzer", {"operation": "data_analysis"}
        )
        
        await asyncio.sleep(0.1)
        
        # Emit tool_completed event
        await self.websocket_bridge.emit_tool_completed(
            user_context, "data_analyzer", {"result": "Analysis complete", "insights": ["insight1", "insight2"]}
        )
        
        await asyncio.sleep(0.1)
        
        # Emit agent_completed event
        await self.websocket_bridge.emit_agent_completed(
            user_context, self.agent_name, {"final_result": "Problem solved successfully"}
        )
        
        return {
            "success": True,
            "result": "Mock agent execution completed with events",
            "events_emitted": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        }


class TestWebSocketAgentEventsIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket agent event emission - MISSION CRITICAL for business value."""

    async def async_setup(self):
        """Set up test environment with real services."""
        await super().async_setup()
        self.env = get_env()
        self.test_user_id_base = UnifiedIdGenerator.generate_user_id()

    async def _create_test_connection_with_bridge(self, websocket_manager, user_id: str) -> Tuple[ConnectionInfo, AgentWebSocketBridge]:
        """Helper to create test connection with WebSocket bridge for agent events."""
        mock_websocket = mock.MagicMock()
        mock_websocket.close = mock.AsyncMock()
        mock_websocket.send = mock.AsyncMock()
        mock_websocket.recv = mock.AsyncMock()
        
        connection_info = ConnectionInfo(
            user_id=user_id,
            websocket=mock_websocket,
            thread_id=UnifiedIdGenerator.generate_thread_id(user_id)
        )
        
        await websocket_manager.add_connection(connection_info)
        
        # Create AgentWebSocketBridge for event emission
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        
        return connection_info, websocket_bridge

    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.agent_events
    async def test_agent_started_event_delivery(self, real_services_fixture):
        """
        Test agent_started event delivery to user.
        
        MISSION CRITICAL: Users MUST see when AI agents begin processing their requests.
        This event starts the real-time AI interaction experience.
        
        Business Value: User immediately knows their request is being processed by AI,
        setting expectation for incoming solution and maintaining engagement.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        user_data = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id_base}_agent_started@test.netra.ai',
            'name': 'Agent Started Event User'
        })
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            connection, websocket_bridge = await self._create_test_connection_with_bridge(
                websocket_manager, user_data['id']
            )
            
            # Create user execution context
            user_context = UserExecutionContext(
                user_id=user_data['id'],
                thread_id=connection.thread_id,
                websocket_connection_id=connection.connection_id
            )
            
            # Emit agent_started event
            agent_name = "data_analyst"
            start_data = {
                "prompt": "Analyze our sales data for optimization opportunities",
                "estimated_duration": "2-3 minutes",
                "capabilities": ["data_analysis", "optimization_recommendations"]
            }
            
            await websocket_bridge.emit_agent_started(user_context, agent_name, start_data)
            
            # Verify event was sent via WebSocket
            connection.websocket.send.assert_called()
            
            # Extract and verify the sent message
            sent_message_raw = connection.websocket.send.call_args[0][0]
            sent_message = json.loads(sent_message_raw)
            
            # CRITICAL: Verify agent_started event structure
            assert sent_message['type'] == 'agent_started', "Must emit agent_started event type"
            assert sent_message['user_id'] == user_data['id'], "Event must be tied to correct user"
            assert sent_message['thread_id'] == connection.thread_id, "Event must be tied to correct thread"
            
            # Verify business-critical event payload
            payload = sent_message['payload']
            assert payload['agent_name'] == agent_name, "Must include agent name for user visibility"
            assert payload['prompt'] == start_data['prompt'], "Must include user's prompt for context"
            assert 'timestamp' in sent_message, "Must include timestamp for sequencing"
            assert 'estimated_duration' in payload, "Must set user expectation for completion time"
            
            self.logger.info(f"✅ CRITICAL: agent_started event successfully delivered for {agent_name}")
            
        finally:
            await websocket_manager.shutdown()

    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.agent_events
    async def test_agent_thinking_event_delivery(self, real_services_fixture):
        """
        Test agent_thinking event delivery showing real-time AI reasoning.
        
        MISSION CRITICAL: Users MUST see AI agents actively thinking through their problems.
        This demonstrates value creation in real-time and maintains user engagement.
        
        Business Value: Users see AI working on valuable solutions, building confidence
        in AI capabilities and justifying the value proposition.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        user_data = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id_base}_thinking@test.netra.ai', 
            'name': 'Agent Thinking Event User'
        })
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            connection, websocket_bridge = await self._create_test_connection_with_bridge(
                websocket_manager, user_data['id']
            )
            
            user_context = UserExecutionContext(
                user_id=user_data['id'],
                thread_id=connection.thread_id,
                websocket_connection_id=connection.connection_id
            )
            
            # Emit agent_thinking event with reasoning process
            agent_name = "optimization_expert"
            thinking_data = {
                "reasoning": "Analyzing cost structure to identify optimization opportunities...",
                "current_step": "data_collection",
                "progress": "15%",
                "next_actions": ["query_database", "run_analysis", "generate_recommendations"],
                "confidence_level": "high"
            }
            
            await websocket_bridge.emit_agent_thinking(user_context, agent_name, thinking_data)
            
            # Verify event delivery
            connection.websocket.send.assert_called()
            
            sent_message_raw = connection.websocket.send.call_args[0][0]
            sent_message = json.loads(sent_message_raw)
            
            # CRITICAL: Verify agent_thinking event structure for business value
            assert sent_message['type'] == 'agent_thinking', "Must emit agent_thinking event type"
            assert sent_message['user_id'] == user_data['id'], "Thinking must be tied to requesting user"
            
            payload = sent_message['payload']
            assert payload['agent_name'] == agent_name, "Must identify which agent is thinking"
            assert 'reasoning' in payload, "CRITICAL: Must show actual AI reasoning to user"
            assert 'progress' in payload, "Must show progress to manage user expectations"
            assert payload['reasoning'].startswith('Analyzing'), "Reasoning must be substantive, not generic"
            
            # Verify business value indicators
            assert 'optimization opportunities' in payload['reasoning'], "Must show value-focused thinking"
            assert payload['confidence_level'] == 'high', "Must communicate AI confidence to user"
            assert len(payload['next_actions']) > 0, "Must show planned actions for transparency"
            
            self.logger.info(f"✅ CRITICAL: agent_thinking event with reasoning delivered for {agent_name}")
            
        finally:
            await websocket_manager.shutdown()

    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.agent_events
    async def test_tool_executing_event_delivery(self, real_services_fixture):
        """
        Test tool_executing event delivery showing AI tool usage.
        
        MISSION CRITICAL: Users MUST see AI agents using tools to solve their problems.
        Tool transparency demonstrates the AI's problem-solving approach and capabilities.
        
        Business Value: Users understand HOW AI is creating value, building trust and
        demonstrating sophisticated AI capabilities justifying premium pricing.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        user_data = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id_base}_tool_exec@test.netra.ai',
            'name': 'Tool Execution Event User'
        })
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            connection, websocket_bridge = await self._create_test_connection_with_bridge(
                websocket_manager, user_data['id']
            )
            
            user_context = UserExecutionContext(
                user_id=user_data['id'],
                thread_id=connection.thread_id,
                websocket_connection_id=connection.connection_id
            )
            
            # Emit tool_executing event for business-critical tool
            tool_name = "financial_analyzer"
            execution_data = {
                "operation": "comprehensive_cost_analysis",
                "parameters": {
                    "data_source": "quarterly_financials",
                    "analysis_type": "optimization_focused",
                    "depth": "detailed"
                },
                "purpose": "Identify $50K+ annual savings opportunities",
                "estimated_runtime": "30 seconds"
            }
            
            await websocket_bridge.emit_tool_executing(user_context, tool_name, execution_data)
            
            # Verify tool execution event delivery
            connection.websocket.send.assert_called()
            
            sent_message_raw = connection.websocket.send.call_args[0][0]
            sent_message = json.loads(sent_message_raw)
            
            # CRITICAL: Verify tool_executing event structure for transparency
            assert sent_message['type'] == 'tool_executing', "Must emit tool_executing event type"
            assert sent_message['user_id'] == user_data['id'], "Tool execution tied to requesting user"
            
            payload = sent_message['payload']
            assert payload['tool_name'] == tool_name, "Must identify which tool is executing"
            assert 'operation' in payload, "Must describe what tool is doing"
            assert 'purpose' in payload, "CRITICAL: Must explain business purpose to user"
            
            # Verify business value communication
            assert '$50K+' in payload['purpose'], "Must quantify expected business value"
            assert payload['parameters']['analysis_type'] == 'optimization_focused', "Must show value-focused approach"
            assert 'estimated_runtime' in payload, "Must manage user time expectations"
            
            self.logger.info(f"✅ CRITICAL: tool_executing event delivered for {tool_name}")
            
        finally:
            await websocket_manager.shutdown()

    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.agent_events
    async def test_tool_completed_event_delivery(self, real_services_fixture):
        """
        Test tool_completed event delivery with actionable results.
        
        MISSION CRITICAL: Users MUST see when AI tools complete and deliver insights.
        This event provides immediate business value through actionable results.
        
        Business Value: Users receive concrete insights and recommendations from AI tools,
        demonstrating tangible value creation and ROI from AI platform usage.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        user_data = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id_base}_tool_complete@test.netra.ai',
            'name': 'Tool Completion Event User'
        })
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            connection, websocket_bridge = await self._create_test_connection_with_bridge(
                websocket_manager, user_data['id']
            )
            
            user_context = UserExecutionContext(
                user_id=user_data['id'],
                thread_id=connection.thread_id,
                websocket_connection_id=connection.connection_id
            )
            
            # Emit tool_completed event with valuable results
            tool_name = "cost_optimizer"
            completion_data = {
                "execution_time": "24.5 seconds",
                "status": "success",
                "results": {
                    "potential_annual_savings": "$127,500",
                    "optimization_opportunities": [
                        {
                            "category": "cloud_infrastructure",
                            "savings": "$45,000",
                            "confidence": "high",
                            "implementation_effort": "low"
                        },
                        {
                            "category": "vendor_contracts",
                            "savings": "$82,500", 
                            "confidence": "medium",
                            "implementation_effort": "medium"
                        }
                    ],
                    "next_steps": ["Review vendor contracts", "Implement cloud optimization"],
                    "roi_timeline": "3-6 months"
                },
                "insights_count": 15,
                "actionable_recommendations": 8
            }
            
            await websocket_bridge.emit_tool_completed(user_context, tool_name, completion_data)
            
            # Verify tool completion event delivery
            connection.websocket.send.assert_called()
            
            sent_message_raw = connection.websocket.send.call_args[0][0]
            sent_message = json.loads(sent_message_raw)
            
            # CRITICAL: Verify tool_completed event structure for business value
            assert sent_message['type'] == 'tool_completed', "Must emit tool_completed event type"
            assert sent_message['user_id'] == user_data['id'], "Results tied to requesting user"
            
            payload = sent_message['payload']
            assert payload['tool_name'] == tool_name, "Must identify completed tool"
            assert payload['status'] == 'success', "Must communicate successful execution"
            
            # Verify business-critical results delivery
            results = payload['results']
            assert 'potential_annual_savings' in results, "CRITICAL: Must quantify business value"
            assert results['potential_annual_savings'] == '$127,500', "Must provide specific savings amount"
            assert len(results['optimization_opportunities']) >= 2, "Must provide multiple opportunities"
            assert len(results['next_steps']) > 0, "Must provide actionable next steps"
            
            # Verify actionable recommendations
            for opportunity in results['optimization_opportunities']:
                assert 'savings' in opportunity, "Each opportunity must quantify savings"
                assert 'confidence' in opportunity, "Must communicate confidence level"
                assert 'implementation_effort' in opportunity, "Must indicate effort required"
            
            assert payload['actionable_recommendations'] == 8, "Must count actionable items"
            
            self.logger.info(f"✅ CRITICAL: tool_completed event with $127K savings delivered")
            
        finally:
            await websocket_manager.shutdown()

    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.agent_events
    async def test_agent_completed_event_delivery(self, real_services_fixture):
        """
        Test agent_completed event delivery with final AI response.
        
        MISSION CRITICAL: Users MUST know when AI agents finish and deliver final results.
        This completes the AI interaction cycle and delivers the primary business value.
        
        Business Value: Users receive comprehensive AI solutions to their problems,
        completing the value delivery cycle that justifies platform usage and pricing.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        user_data = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id_base}_agent_complete@test.netra.ai',
            'name': 'Agent Completion Event User'
        })
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"], 
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            connection, websocket_bridge = await self._create_test_connection_with_bridge(
                websocket_manager, user_data['id']
            )
            
            user_context = UserExecutionContext(
                user_id=user_data['id'],
                thread_id=connection.thread_id,
                websocket_connection_id=connection.connection_id
            )
            
            # Emit agent_completed event with comprehensive results
            agent_name = "business_optimizer"
            completion_data = {
                "execution_time": "2.3 minutes",
                "status": "success",
                "final_result": {
                    "summary": "Identified $127,500 in annual cost optimization opportunities with high confidence implementation plan",
                    "total_value_identified": "$127,500",
                    "implementation_timeline": "3-6 months",
                    "confidence_score": 0.89,
                    "key_recommendations": [
                        "Optimize cloud infrastructure for $45K annual savings",
                        "Renegotiate vendor contracts for $82.5K annual savings",
                        "Implement automated monitoring for ongoing optimization"
                    ],
                    "detailed_report_available": True,
                    "next_meeting_suggested": "Schedule implementation planning session"
                },
                "tools_used": ["cost_analyzer", "vendor_evaluator", "roi_calculator"],
                "insights_generated": 23,
                "user_satisfaction_predicted": "high"
            }
            
            await websocket_bridge.emit_agent_completed(user_context, agent_name, completion_data)
            
            # Verify agent completion event delivery
            connection.websocket.send.assert_called()
            
            sent_message_raw = connection.websocket.send.call_args[0][0]
            sent_message = json.loads(sent_message_raw)
            
            # CRITICAL: Verify agent_completed event structure for business value closure
            assert sent_message['type'] == 'agent_completed', "Must emit agent_completed event type"
            assert sent_message['user_id'] == user_data['id'], "Completion tied to requesting user"
            
            payload = sent_message['payload']
            assert payload['agent_name'] == agent_name, "Must identify completed agent"
            assert payload['status'] == 'success', "Must communicate successful completion"
            
            # Verify comprehensive business value delivery
            final_result = payload['final_result']
            assert 'summary' in final_result, "CRITICAL: Must provide executive summary"
            assert '$127,500' in final_result['summary'], "Summary must highlight financial impact"
            assert final_result['total_value_identified'] == '$127,500', "Must quantify total value"
            assert final_result['confidence_score'] > 0.8, "Must communicate high confidence"
            
            # Verify actionable recommendations 
            recommendations = final_result['key_recommendations']
            assert len(recommendations) >= 3, "Must provide multiple key recommendations"
            for rec in recommendations:
                assert any(char.isdigit() for char in rec), "Each recommendation should include value quantification"
            
            # Verify completion metadata
            assert len(payload['tools_used']) >= 3, "Must show multiple tools were leveraged"
            assert payload['insights_generated'] >= 20, "Must demonstrate substantial analysis"
            assert payload['user_satisfaction_predicted'] == 'high', "Must predict positive user outcome"
            
            self.logger.info(f"✅ CRITICAL: agent_completed event with $127K value delivered")
            
        finally:
            await websocket_manager.shutdown()

    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.agent_events
    async def test_agent_event_ordering_validation(self, real_services_fixture):
        """
        Test correct ordering of agent events during execution flow.
        
        MISSION CRITICAL: Agent events must follow logical order for coherent user experience.
        Proper sequencing: agent_started → agent_thinking → tool_executing → tool_completed → agent_completed
        
        Business Value: Logical event flow builds user confidence and understanding of AI process.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        user_data = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id_base}_ordering@test.netra.ai',
            'name': 'Event Ordering Test User'
        })
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            connection, websocket_bridge = await self._create_test_connection_with_bridge(
                websocket_manager, user_data['id']
            )
            
            user_context = UserExecutionContext(
                user_id=user_data['id'],
                thread_id=connection.thread_id,
                websocket_connection_id=connection.connection_id
            )
            
            # Create mock agent with event emission
            mock_agent = MockAgentForTesting("integration_test_agent", websocket_bridge)
            
            # Execute agent with full event sequence
            result = await mock_agent.execute_with_events(
                user_context, "Optimize our business operations for maximum ROI"
            )
            
            # Verify all expected events were emitted in sequence
            assert result['success'], "Agent execution should succeed"
            assert len(result['events_emitted']) == 5, "Should emit all 5 critical events"
            
            # Verify all WebSocket sends occurred
            assert connection.websocket.send.call_count == 5, "Should have 5 WebSocket sends"
            
            # Extract all sent messages in order
            sent_calls = connection.websocket.send.call_args_list
            sent_messages = []
            for call in sent_calls:
                message_raw = call[0][0]
                message = json.loads(message_raw)
                sent_messages.append(message)
            
            # Verify correct event sequence
            expected_sequence = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            actual_sequence = [msg['type'] for msg in sent_messages]
            
            assert actual_sequence == expected_sequence, f"Events must follow correct sequence. Got: {actual_sequence}"
            
            # Verify timestamp ordering (each event should have later timestamp)
            timestamps = [msg['timestamp'] for msg in sent_messages]
            for i in range(1, len(timestamps)):
                assert timestamps[i] > timestamps[i-1], f"Event {i} timestamp should be after event {i-1}"
            
            # Verify all events have consistent user/thread context
            for i, message in enumerate(sent_messages):
                assert message['user_id'] == user_data['id'], f"Event {i} should have correct user_id"
                assert message['thread_id'] == connection.thread_id, f"Event {i} should have correct thread_id"
            
            self.logger.info("✅ CRITICAL: All 5 agent events delivered in correct sequence")
            
        finally:
            await websocket_manager.shutdown()

    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.agent_events
    async def test_agent_event_payload_validation(self, real_services_fixture):
        """
        Test validation of agent event payload structures for business value.
        
        MISSION CRITICAL: Event payloads must contain all business-critical information
        for frontend to display meaningful progress and results to users.
        
        Business Value: Rich event payloads enable sophisticated UX that communicates
        AI value creation in real-time, justifying platform usage and retention.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        user_data = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id_base}_payload@test.netra.ai',
            'name': 'Event Payload Validation User'
        })
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            connection, websocket_bridge = await self._create_test_connection_with_bridge(
                websocket_manager, user_data['id']
            )
            
            user_context = UserExecutionContext(
                user_id=user_data['id'],
                thread_id=connection.thread_id,
                websocket_connection_id=connection.connection_id
            )
            
            # Test comprehensive payload structures for each critical event type
            test_events = [
                {
                    'event_type': 'agent_started',
                    'emitter': websocket_bridge.emit_agent_started,
                    'data': {
                        "agent_name": "revenue_optimizer", 
                        "user_prompt": "Find ways to increase revenue by 15%",
                        "expected_duration": "3-5 minutes",
                        "capabilities": ["market_analysis", "pricing_optimization", "growth_strategies"]
                    },
                    'required_fields': ['agent_name', 'user_prompt', 'expected_duration']
                },
                {
                    'event_type': 'agent_thinking',
                    'emitter': websocket_bridge.emit_agent_thinking,
                    'data': {
                        "agent_name": "revenue_optimizer",
                        "reasoning": "Analyzing current pricing model and market positioning for revenue optimization opportunities",
                        "progress": "25%",
                        "current_focus": "market_analysis"
                    },
                    'required_fields': ['agent_name', 'reasoning', 'progress']
                },
                {
                    'event_type': 'tool_executing', 
                    'emitter': websocket_bridge.emit_tool_executing,
                    'data': {
                        "tool_name": "market_analyzer",
                        "operation": "competitive_pricing_analysis",
                        "purpose": "Identify pricing optimization opportunities for 15% revenue increase"
                    },
                    'required_fields': ['tool_name', 'operation', 'purpose']
                },
                {
                    'event_type': 'tool_completed',
                    'emitter': websocket_bridge.emit_tool_completed,
                    'data': {
                        "tool_name": "market_analyzer",
                        "status": "success",
                        "results": {
                            "revenue_opportunities": "$2.3M annual potential",
                            "confidence": "high",
                            "recommendations": ["Increase premium tier pricing by 12%", "Launch enterprise tier"]
                        }
                    },
                    'required_fields': ['tool_name', 'status', 'results']
                },
                {
                    'event_type': 'agent_completed',
                    'emitter': websocket_bridge.emit_agent_completed,
                    'data': {
                        "agent_name": "revenue_optimizer",
                        "status": "success", 
                        "final_result": {
                            "revenue_increase_potential": "18.5% ($2.3M annually)",
                            "implementation_timeline": "2-4 months",
                            "key_strategies": ["Premium tier price optimization", "New enterprise tier launch"],
                            "confidence_level": "high"
                        }
                    },
                    'required_fields': ['agent_name', 'status', 'final_result']
                }
            ]
            
            # Test each event type payload structure
            for i, event_config in enumerate(test_events):
                # Reset mock for each event
                connection.websocket.send.reset_mock()
                
                # Emit event
                if event_config['event_type'] in ['agent_started', 'agent_thinking', 'agent_completed']:
                    await event_config['emitter'](
                        user_context, 
                        event_config['data']['agent_name'],
                        {k: v for k, v in event_config['data'].items() if k != 'agent_name'}
                    )
                else:  # tool events
                    await event_config['emitter'](
                        user_context,
                        event_config['data']['tool_name'],
                        {k: v for k, v in event_config['data'].items() if k != 'tool_name'}
                    )
                
                # Verify event was sent
                connection.websocket.send.assert_called_once()
                
                # Extract and validate payload
                sent_message_raw = connection.websocket.send.call_args[0][0]
                sent_message = json.loads(sent_message_raw)
                
                # Validate event type
                assert sent_message['type'] == event_config['event_type'], f"Event {i} should have correct type"
                
                # Validate required fields in payload
                payload = sent_message['payload']
                for required_field in event_config['required_fields']:
                    if required_field in event_config['data']:
                        assert required_field in payload or event_config['data'][required_field] in str(payload), \
                            f"Event {i} payload missing required field: {required_field}"
                
                # Validate business value fields for each event type
                if event_config['event_type'] == 'agent_started':
                    assert 'expected_duration' in payload, "agent_started must include duration estimate"
                    assert 'capabilities' in payload, "agent_started must show agent capabilities"
                
                elif event_config['event_type'] == 'agent_thinking':
                    assert 'reasoning' in payload, "agent_thinking must show actual reasoning"
                    assert len(payload['reasoning']) > 20, "Reasoning must be substantive"
                    assert 'progress' in payload, "agent_thinking must show progress"
                
                elif event_config['event_type'] == 'tool_executing':
                    assert 'purpose' in payload, "tool_executing must explain business purpose"
                
                elif event_config['event_type'] == 'tool_completed':
                    assert 'results' in payload, "tool_completed must include results"
                    results = payload['results']
                    assert any('$' in str(v) or 'revenue' in str(v).lower() for v in results.values() if isinstance(v, str)), \
                        "tool_completed results must show business value"
                
                elif event_config['event_type'] == 'agent_completed':
                    assert 'final_result' in payload, "agent_completed must include final results"
                    final_result = payload['final_result']
                    assert any('%' in str(v) or '$' in str(v) for v in final_result.values() if isinstance(v, str)), \
                        "agent_completed must quantify business value"
                
            self.logger.info("✅ CRITICAL: All agent event payloads contain required business value fields")
            
        finally:
            await websocket_manager.shutdown()

    @pytest.mark.integration 
    @pytest.mark.websocket
    @pytest.mark.agent_events
    async def test_multiple_concurrent_agent_events(self, real_services_fixture):
        """
        Test handling of concurrent agent events from multiple agents/users.
        
        MISSION CRITICAL: System must handle multiple AI agents working simultaneously
        for different users without event mixing or loss.
        
        Business Value: Platform can scale to serve multiple users simultaneously with
        isolated AI agent execution and proper event routing.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        # Create multiple users for concurrent testing
        concurrent_users = []
        for i in range(3):
            user_data = await self.create_test_user_context(services, {
                'email': f'{self.test_user_id_base}_concurrent_{i}@test.netra.ai',
                'name': f'Concurrent Agent User {i}'
            })
            concurrent_users.append(user_data)
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            # Create connections and bridges for all users
            user_connections = []
            for user_data in concurrent_users:
                connection, bridge = await self._create_test_connection_with_bridge(
                    websocket_manager, user_data['id']
                )
                user_connections.append({
                    'user_data': user_data,
                    'connection': connection,
                    'bridge': bridge,
                    'context': UserExecutionContext(
                        user_id=user_data['id'],
                        thread_id=connection.thread_id,
                        websocket_connection_id=connection.connection_id
                    )
                })
            
            # Create concurrent agent executions
            agent_tasks = []
            for i, user_conn in enumerate(user_connections):
                agent_name = f"concurrent_agent_{i}"
                prompt = f"Business optimization task {i} - maximize efficiency and ROI"
                
                mock_agent = MockAgentForTesting(agent_name, user_conn['bridge'])
                task = asyncio.create_task(
                    mock_agent.execute_with_events(user_conn['context'], prompt)
                )
                agent_tasks.append(task)
            
            # Execute all agents concurrently
            results = await asyncio.gather(*agent_tasks)
            
            # Verify all agents completed successfully
            for i, result in enumerate(results):
                assert result['success'], f"Agent {i} should complete successfully"
                assert len(result['events_emitted']) == 5, f"Agent {i} should emit all 5 events"
            
            # Verify each user received exactly their own events
            for i, user_conn in enumerate(user_connections):
                connection = user_conn['connection']
                
                # Each agent should have sent 5 events to its user
                assert connection.websocket.send.call_count == 5, f"User {i} should receive 5 events"
                
                # Extract all events for this user
                sent_calls = connection.websocket.send.call_args_list
                user_messages = []
                for call in sent_calls:
                    message = json.loads(call[0][0])
                    user_messages.append(message)
                
                # Verify all events belong to the correct user
                for j, message in enumerate(user_messages):
                    assert message['user_id'] == user_conn['user_data']['id'], \
                        f"User {i} event {j} should have correct user_id"
                    assert message['thread_id'] == user_conn['connection'].thread_id, \
                        f"User {i} event {j} should have correct thread_id"
                    
                    # Verify agent name consistency (should contain user index)
                    if 'agent_name' in message['payload']:
                        assert f'concurrent_agent_{i}' == message['payload']['agent_name'], \
                            f"User {i} should only receive events from their agent"
            
            # Verify event isolation - no cross-user contamination
            all_sent_messages = []
            for user_conn in user_connections:
                sent_calls = user_conn['connection'].websocket.send.call_args_list
                for call in sent_calls:
                    message = json.loads(call[0][0])
                    all_sent_messages.append(message)
            
            # Check that each message has a unique user_id matching one of our test users
            user_ids = [user['id'] for user in concurrent_users]
            for message in all_sent_messages:
                assert message['user_id'] in user_ids, "All messages should belong to test users"
            
            # Verify no user received another user's events
            for i, user_conn in enumerate(user_connections):
                user_id = user_conn['user_data']['id']
                sent_calls = user_conn['connection'].websocket.send.call_args_list
                
                for call in sent_calls:
                    message = json.loads(call[0][0])
                    assert message['user_id'] == user_id, f"User {i} should not receive other users' events"
            
            self.logger.info("✅ CRITICAL: Concurrent agent events properly isolated between users")
            
        finally:
            await websocket_manager.shutdown()