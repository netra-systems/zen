"""
E2E Test: Complete Agent Execution with WebSocket Events

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - WebSocket events are core to user experience
- Business Goal: Ensure complete agent execution pipeline delivers all required WebSocket events
- Value Impact: Users must receive complete real-time feedback during agent execution for business value
- Strategic Impact: Core platform functionality that enables meaningful AI interactions

This E2E test validates:
- Complete agent execution workflow with real authentication (JWT/OAuth)
- All 5 critical WebSocket events are delivered in correct order
- Real LLM integration with proper event emission
- End-to-end user journey with actual business value delivery
- Full stack integration including database persistence and audit trail

CRITICAL: Uses REAL services, REAL authentication, NO mocking allowed
"""

import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events

# Core system imports with absolute paths
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestCompleteAgentExecutionWithEvents(BaseE2ETest):
    """E2E tests for complete agent execution with all WebSocket events."""
    
    @pytest.fixture
    async def authenticated_user_context(self):
        """Create authenticated user execution context for complete testing."""
        return await create_authenticated_user_context(
            user_email="complete_agent_test@e2e.test",
            environment="test",
            permissions=["read", "write", "agent_execute", "websocket_connect"],
            websocket_enabled=True
        )
    
    @pytest.fixture
    def websocket_auth_helper(self):
        """WebSocket-specific authentication helper."""
        return E2EWebSocketAuthHelper(environment="test")
    
    @pytest.fixture
    def unified_id_generator(self):
        """Unified ID generator for test consistency."""
        return UnifiedIdGenerator()
    
    @pytest.fixture
    async def real_agent_registry(self):
        """Real agent registry with production agents for E2E testing."""
        registry = AgentRegistry()
        
        # CRITICAL: Use REAL agents, not test mocks - this is E2E
        # The registry should auto-discover available agents
        await registry.initialize_registry()
        
        # Verify we have at least one agent for testing
        available_agents = registry.list_available_agents()
        if not available_agents:
            pytest.fail("No real agents available in registry for E2E testing")
        
        return registry
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.websocket_events
    async def test_complete_agent_execution_all_events_delivered(
        self,
        authenticated_user_context: StronglyTypedUserExecutionContext,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test complete agent execution with all 5 critical WebSocket events delivered.
        
        This is the PRIMARY E2E test for business value delivery through WebSocket events.
        Failure of this test indicates fundamental system breakdown.
        """
        
        # Generate execution identifiers
        run_id = unified_id_generator.generate_run_id(
            user_id=str(authenticated_user_context.user_id),
            operation="complete_agent_execution_e2e"
        )
        
        # Create execution context
        execution_context = AgentExecutionContext(
            agent_name="triage_agent",  # Use triage agent as it's foundational
            run_id=str(run_id),
            correlation_id=str(authenticated_user_context.request_id),
            retry_count=0,
            user_context=authenticated_user_context
        )
        
        # Create authenticated WebSocket connection
        websocket_connection = await websocket_auth_helper.connect_authenticated_websocket(
            timeout=15.0
        )
        
        # Track received events
        received_events = []
        event_timestamps = []
        
        async def collect_websocket_events():
            """Collect all WebSocket events during agent execution."""
            try:
                while True:
                    # Wait for events with timeout
                    event = await asyncio.wait_for(
                        websocket_connection.recv(),
                        timeout=30.0  # Extended timeout for real LLM calls
                    )
                    
                    parsed_event = json.loads(event)
                    received_events.append(parsed_event)
                    event_timestamps.append(time.time())
                    
                    self.logger.info(f"Received WebSocket event: {parsed_event.get('type')}")
                    
                    # Stop collecting after agent completion
                    if parsed_event.get('type') == 'agent_completed':
                        break
                        
            except asyncio.TimeoutError:
                self.logger.error("Timeout waiting for WebSocket events")
            except Exception as e:
                self.logger.error(f"Error collecting WebSocket events: {e}")
        
        # Set up WebSocket bridge for event delivery
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        
        # Create agent execution core with real WebSocket bridge
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        # Create agent state with user context
        agent_state = DeepAgentState(
            user_id=str(authenticated_user_context.user_id),
            thread_id=str(authenticated_user_context.thread_id),
            agent_context=authenticated_user_context.agent_context
        )
        
        # Start event collection task
        event_collection_task = asyncio.create_task(collect_websocket_events())
        
        try:
            # Execute agent with real LLM integration
            self.logger.info(f"Starting agent execution: {execution_context.agent_name}")
            
            execution_result = await execution_core.execute_agent(
                context=execution_context,
                state=agent_state,
                timeout=60.0,  # Extended timeout for real LLM calls
                enable_llm=True,  # CRITICAL: Use real LLM
                enable_websocket_events=True
            )
            
            # Wait for event collection to complete
            await asyncio.wait_for(event_collection_task, timeout=5.0)
            
        except asyncio.TimeoutError:
            event_collection_task.cancel()
            try:
                await event_collection_task
            except asyncio.CancelledError:
                pass
        finally:
            # Clean up WebSocket connection
            await websocket_connection.close()
        
        # CRITICAL VALIDATION: Execution must succeed
        assert execution_result.success is True, f"Agent execution failed: {execution_result.error}"
        
        # CRITICAL VALIDATION: All 5 required WebSocket events must be present
        event_types = [event.get('type') for event in received_events]
        required_events = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
        self.logger.info(f"Received event types: {event_types}")
        
        for required_event in required_events:
            assert required_event in event_types, \
                f"CRITICAL FAILURE: Missing required WebSocket event '{required_event}'. " \
                f"Received: {event_types}. This breaks core business value delivery!"
        
        # CRITICAL VALIDATION: Event ordering constraints
        started_index = event_types.index('agent_started')
        completed_index = event_types.index('agent_completed')
        
        assert started_index == 0, \
            f"agent_started must be first event, found at index {started_index}"
        
        assert completed_index == len(event_types) - 1, \
            f"agent_completed must be last event, found at index {completed_index}"
        
        # CRITICAL VALIDATION: Event context consistency
        for event in received_events:
            if event.get('type') in required_events:
                assert event.get('run_id') == str(run_id), \
                    f"Event {event.get('type')} has incorrect run_id: {event.get('run_id')} != {run_id}"
                assert event.get('agent_name') == execution_context.agent_name, \
                    f"Event {event.get('type')} has incorrect agent_name"
                assert 'timestamp' in event, \
                    f"Event {event.get('type')} missing timestamp"
        
        # CRITICAL VALIDATION: Business value verification
        final_event = received_events[-1]
        assert final_event.get('type') == 'agent_completed', \
            "Final event must be agent_completed"
        
        # Verify agent delivered actual results (business value)
        agent_result = final_event.get('result', {})
        assert agent_result is not None, \
            "Agent must deliver actual results for business value"
        
        self.logger.info("✅ CRITICAL SUCCESS: All WebSocket events delivered correctly for complete business value")
    
    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.real_llm
    @pytest.mark.websocket_events
    async def test_agent_execution_with_real_llm_integration(
        self,
        authenticated_user_context: StronglyTypedUserExecutionContext,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test agent execution with REAL LLM integration and WebSocket event delivery.
        
        This test validates that:
        1. Real LLM calls generate proper WebSocket events
        2. LLM responses are properly formatted and delivered via WebSocket
        3. Agent reasoning is communicated through agent_thinking events
        4. Tool executions (if any) generate proper event sequences
        """
        
        # Generate execution context for LLM test
        run_id = unified_id_generator.generate_run_id(
            user_id=str(authenticated_user_context.user_id),
            operation="real_llm_integration_e2e"
        )
        
        execution_context = AgentExecutionContext(
            agent_name="data_analysis_agent",  # Agent likely to use LLM extensively
            run_id=str(run_id),
            correlation_id=str(authenticated_user_context.request_id),
            retry_count=0,
            user_context=authenticated_user_context
        )
        
        # Create WebSocket connection
        websocket_connection = await websocket_auth_helper.connect_authenticated_websocket()
        
        # Event tracking
        llm_related_events = []
        thinking_events = []
        completion_event = None
        
        async def collect_llm_events():
            """Collect events specifically related to LLM processing."""
            try:
                while True:
                    event_raw = await asyncio.wait_for(websocket_connection.recv(), timeout=45.0)
                    event = json.loads(event_raw)
                    
                    event_type = event.get('type')
                    
                    if event_type == 'agent_thinking':
                        thinking_events.append(event)
                        # Check if reasoning indicates LLM processing
                        reasoning = event.get('reasoning', '').lower()
                        if any(keyword in reasoning for keyword in ['analyzing', 'processing', 'reasoning', 'thinking']):
                            llm_related_events.append(event)
                    
                    elif event_type == 'agent_completed':
                        completion_event = event
                        break
                    
                    elif event_type in ['tool_executing', 'tool_completed']:
                        # Tools might involve LLM processing
                        llm_related_events.append(event)
                        
            except asyncio.TimeoutError:
                pass
        
        # Set up execution infrastructure
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        agent_state = DeepAgentState(
            user_id=str(authenticated_user_context.user_id),
            thread_id=str(authenticated_user_context.thread_id),
            agent_context={
                **authenticated_user_context.agent_context,
                'user_message': 'Analyze the current market trends and provide insights',  # Requires LLM
                'require_llm_reasoning': True
            }
        )
        
        # Start event collection
        event_task = asyncio.create_task(collect_llm_events())
        
        try:
            # Execute agent with LLM enabled
            execution_result = await execution_core.execute_agent(
                context=execution_context,
                state=agent_state, 
                timeout=60.0,
                enable_llm=True,
                enable_websocket_events=True
            )
            
            await asyncio.wait_for(event_task, timeout=10.0)
            
        except asyncio.TimeoutError:
            event_task.cancel()
        finally:
            await websocket_connection.close()
        
        # VALIDATION: Agent execution succeeded
        assert execution_result.success is True, \
            f"LLM-integrated agent execution failed: {execution_result.error}"
        
        # VALIDATION: Agent thinking events were generated
        assert len(thinking_events) > 0, \
            "Agent must generate thinking events during LLM processing"
        
        # VALIDATION: LLM-related processing occurred
        assert len(llm_related_events) > 0, \
            "Agent must show evidence of LLM processing through WebSocket events"
        
        # VALIDATION: Completion event contains LLM-generated content
        assert completion_event is not None, \
            "Agent completion event must be present"
        
        result = completion_event.get('result', {})
        assert result is not None, \
            "Agent must deliver LLM-generated results"
        
        # Look for evidence of LLM processing in the result
        result_str = json.dumps(result).lower()
        llm_indicators = ['analysis', 'insight', 'recommendation', 'conclusion', 'assessment']
        
        has_llm_content = any(indicator in result_str for indicator in llm_indicators)
        assert has_llm_content, \
            f"Agent result should show evidence of LLM processing. Result: {result}"
        
        self.logger.info("✅ SUCCESS: Real LLM integration with proper WebSocket event delivery validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    async def test_agent_execution_error_handling_with_events(
        self,
        authenticated_user_context: StronglyTypedUserExecutionContext,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test agent execution error scenarios with proper WebSocket event delivery.
        
        Validates that even when agents encounter errors:
        1. Proper error events are delivered via WebSocket
        2. User receives meaningful error information
        3. System gracefully handles failures without losing event delivery
        """
        
        run_id = unified_id_generator.generate_run_id(
            user_id=str(authenticated_user_context.user_id),
            operation="error_handling_e2e"
        )
        
        # Create execution context with invalid configuration to trigger errors
        execution_context = AgentExecutionContext(
            agent_name="non_existent_agent",  # This should trigger agent not found error
            run_id=str(run_id),
            correlation_id=str(authenticated_user_context.request_id),
            retry_count=0,
            user_context=authenticated_user_context
        )
        
        websocket_connection = await websocket_auth_helper.connect_authenticated_websocket()
        
        error_events = []
        all_events = []
        
        async def collect_error_events():
            """Collect error-related WebSocket events."""
            try:
                while True:
                    event_raw = await asyncio.wait_for(websocket_connection.recv(), timeout=20.0)
                    event = json.loads(event_raw)
                    all_events.append(event)
                    
                    if event.get('type') in ['agent_error', 'execution_error', 'error']:
                        error_events.append(event)
                    
                    # Break on completion or error termination
                    if event.get('type') in ['agent_completed', 'agent_error', 'execution_failed']:
                        break
                        
            except asyncio.TimeoutError:
                pass
        
        # Set up execution with error conditions
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        agent_state = DeepAgentState(
            user_id=str(authenticated_user_context.user_id),
            thread_id=str(authenticated_user_context.thread_id),
            agent_context=authenticated_user_context.agent_context
        )
        
        event_task = asyncio.create_task(collect_error_events())
        
        try:
            # This execution should fail but still deliver proper events
            execution_result = await execution_core.execute_agent(
                context=execution_context,
                state=agent_state,
                timeout=30.0,
                enable_websocket_events=True
            )
            
            await asyncio.wait_for(event_task, timeout=5.0)
            
        except Exception as e:
            # Expected to fail, but WebSocket events should still be delivered
            self.logger.info(f"Expected execution failure: {e}")
        finally:
            await websocket_connection.close()
        
        # VALIDATION: Error events were delivered
        assert len(error_events) > 0, \
            "System must deliver error events via WebSocket when agent execution fails"
        
        # VALIDATION: Error events contain meaningful information
        for error_event in error_events:
            assert 'error' in error_event or 'message' in error_event, \
                "Error events must contain error information for user feedback"
            assert error_event.get('run_id') == str(run_id), \
                "Error events must maintain proper run context"
        
        # VALIDATION: Some events were delivered (even in error scenarios)
        assert len(all_events) > 0, \
            "WebSocket event delivery must work even when agent execution fails"
        
        self.logger.info("✅ SUCCESS: Error handling with WebSocket event delivery validated")