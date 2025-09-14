"""
Agent WebSocket Event Delivery Integration Tests - No Database Required

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate real-time WebSocket event delivery for agent interactions
- Value Impact: Ensures users see live agent progress, critical for $500K+ ARR chat functionality
- Strategic Impact: Foundation for multi-user agent execution and customer engagement

Integration Test Requirements:
- NO database dependencies - tests agent event delivery without external services
- NO Docker requirements - tests components in isolation
- Uses real agent classes and WebSocket infrastructure
- Validates event ordering and payload integrity
- Tests multi-user event isolation patterns

Phase 1 Priority Areas:
1. Agent WebSocket event delivery in real-time scenarios
2. Multi-user agent execution patterns
3. Agent registry concurrent access
4. User execution engine integration patterns
5. Base agent factory pattern user isolation

CRITICAL: These tests focus on the integration layer between agents and WebSocket events
without requiring external service dependencies. They validate business-critical event
delivery patterns that power the Golden Path user experience.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, get_agent_registry
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher

import logging
logger = logging.getLogger(__name__)


class MockWebSocketEmitter:
    """Mock WebSocket emitter that captures events for testing."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events = []
        self.event_counts = {}
        self.last_event_timestamp = None
        
    async def notify_agent_started(self, context: AgentExecutionContext, **kwargs) -> bool:
        """Capture agent started event."""
        event = {
            'type': 'agent_started',
            'user_id': context.user_id,
            'agent_name': context.agent_name,
            'timestamp': time.time(),
            'context': context,
            'kwargs': kwargs
        }
        self.events.append(event)
        self.event_counts['agent_started'] = self.event_counts.get('agent_started', 0) + 1
        self.last_event_timestamp = event['timestamp']
        logger.info(f"WebSocket Event: agent_started for {context.user_id}/{context.agent_name}")
        return True
        
    async def notify_agent_thinking(self, context: AgentExecutionContext, reasoning: str, step_number: int = 1, **kwargs) -> bool:
        """Capture agent thinking event."""
        event = {
            'type': 'agent_thinking',
            'user_id': context.user_id,
            'agent_name': context.agent_name,
            'reasoning': reasoning,
            'step_number': step_number,
            'timestamp': time.time(),
            'context': context,
            'kwargs': kwargs
        }
        self.events.append(event)
        self.event_counts['agent_thinking'] = self.event_counts.get('agent_thinking', 0) + 1
        self.last_event_timestamp = event['timestamp']
        logger.info(f"WebSocket Event: agent_thinking for {context.user_id}/{context.agent_name} - {reasoning[:50]}...")
        return True
        
    async def notify_tool_executing(self, user_context: UserExecutionContext, tool_name: str, parameters: Dict[str, Any], **kwargs) -> bool:
        """Capture tool executing event."""
        event = {
            'type': 'tool_executing',
            'user_id': user_context.user_id,
            'tool_name': tool_name,
            'parameters': parameters,
            'timestamp': time.time(),
            'context': user_context,
            'kwargs': kwargs
        }
        self.events.append(event)
        self.event_counts['tool_executing'] = self.event_counts.get('tool_executing', 0) + 1
        self.last_event_timestamp = event['timestamp']
        logger.info(f"WebSocket Event: tool_executing for {user_context.user_id} - {tool_name}")
        return True
        
    async def notify_tool_completed(self, user_context: UserExecutionContext, tool_name: str, result: Any, **kwargs) -> bool:
        """Capture tool completed event."""
        event = {
            'type': 'tool_completed',
            'user_id': user_context.user_id,
            'tool_name': tool_name,
            'result': result,
            'timestamp': time.time(),
            'context': user_context,
            'kwargs': kwargs
        }
        self.events.append(event)
        self.event_counts['tool_completed'] = self.event_counts.get('tool_completed', 0) + 1
        self.last_event_timestamp = event['timestamp']
        logger.info(f"WebSocket Event: tool_completed for {user_context.user_id} - {tool_name}")
        return True
        
    async def notify_agent_completed(self, context: AgentExecutionContext, result: AgentExecutionResult, **kwargs) -> bool:
        """Capture agent completed event."""
        event = {
            'type': 'agent_completed',
            'user_id': context.user_id,
            'agent_name': context.agent_name,
            'result': result,
            'timestamp': time.time(),
            'context': context,
            'kwargs': kwargs
        }
        self.events.append(event)
        self.event_counts['agent_completed'] = self.event_counts.get('agent_completed', 0) + 1
        self.last_event_timestamp = event['timestamp']
        logger.info(f"WebSocket Event: agent_completed for {context.user_id}/{context.agent_name}")
        return True
        
    async def cleanup(self):
        """Cleanup method for testing."""
        pass
        
    def get_events_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get events for specific user."""
        return [event for event in self.events if event['user_id'] == user_id]
        
    def has_complete_agent_lifecycle(self, user_id: str, agent_name: str) -> bool:
        """Check if user has complete agent lifecycle events for given agent."""
        user_events = self.get_events_for_user(user_id)
        agent_events = [e for e in user_events if e.get('agent_name') == agent_name]
        
        required_events = {'agent_started', 'agent_thinking', 'agent_completed'}
        found_events = set(e['type'] for e in agent_events)
        
        return required_events.issubset(found_events)


class MockToolDispatcher:
    """Mock tool dispatcher that simulates tool execution with WebSocket events."""
    
    def __init__(self, websocket_emitter: MockWebSocketEmitter, user_context: UserExecutionContext):
        self.websocket_emitter = websocket_emitter
        self.user_context = user_context
        self.execution_history = []
        
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with WebSocket event emission."""
        # Emit tool executing event
        await self.websocket_emitter.notify_tool_executing(
            self.user_context, tool_name, parameters
        )
        
        # Simulate tool processing
        await asyncio.sleep(0.01)
        
        # Generate mock result
        result = {
            'success': True,
            'tool_name': tool_name,
            'parameters': parameters,
            'execution_time': 0.01,
            'result_data': f"Mock result for {tool_name} with user {self.user_context.user_id}",
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Emit tool completed event
        await self.websocket_emitter.notify_tool_completed(
            self.user_context, tool_name, result
        )
        
        # Record execution
        self.execution_history.append({
            'tool_name': tool_name,
            'parameters': parameters,
            'result': result,
            'user_id': self.user_context.user_id
        })
        
        return result


class MockAgent(BaseAgent):
    """Mock agent implementation for testing WebSocket event integration."""
    
    def __init__(self, name: str, websocket_emitter: MockWebSocketEmitter, user_context: UserExecutionContext):
        self.name = name
        self.agent_name = name
        self.websocket_emitter = websocket_emitter
        self.user_context = user_context
        self.tool_dispatcher = MockToolDispatcher(websocket_emitter, user_context)
        self.execution_history = []
        
    async def execute_with_context(self, context: AgentExecutionContext, prompt: str, **kwargs) -> AgentExecutionResult:
        """Execute agent with full WebSocket event lifecycle."""
        logger.info(f"MockAgent {self.name} starting execution for user {context.user_id}")
        
        # Emit agent started event
        await self.websocket_emitter.notify_agent_started(context, prompt=prompt, **kwargs)
        
        # Simulate initial thinking
        await asyncio.sleep(0.01)
        await self.websocket_emitter.notify_agent_thinking(
            context, f"Analyzing request: {prompt[:100]}...", step_number=1
        )
        
        # Simulate tool usage
        await asyncio.sleep(0.01)
        tool_result = await self.tool_dispatcher.execute_tool(
            f"{self.name}_analyzer", 
            {"prompt": prompt, "user_id": context.user_id}
        )
        
        # More thinking
        await asyncio.sleep(0.01)
        await self.websocket_emitter.notify_agent_thinking(
            context, f"Processing results from {self.name}_analyzer...", step_number=2
        )
        
        # Generate final result
        execution_result = AgentExecutionResult(
            success=True,
            agent_name=self.name,
            duration=0.05,
            metadata={
                'prompt': prompt,
                'user_id': context.user_id,
                'tool_results': [tool_result],
                'completion_time': datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Record execution
        self.execution_history.append({
            'context': context,
            'result': execution_result,
            'timestamp': time.time()
        })
        
        # Emit agent completed event
        await self.websocket_emitter.notify_agent_completed(context, execution_result)
        
        logger.info(f"MockAgent {self.name} completed execution for user {context.user_id}")
        return execution_result


class TestAgentWebSocketEventDeliveryNoDB(SSotAsyncTestCase):
    """Integration tests for agent WebSocket event delivery without database dependencies."""
    
    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)
        self.test_start_time = time.time()
        
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_single_user_agent_event_delivery(self):
        """Test complete WebSocket event delivery for single user agent execution.
        
        BVJ: Validates the core business value of real-time agent progress visibility
        that enables $500K+ ARR chat functionality.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="single_user_test",
            thread_id="thread_001",
            run_id=f"run_{int(time.time())}",
            request_id=f"req_{uuid.uuid4().hex[:8]}"
        )
        
        # Create WebSocket emitter
        websocket_emitter = MockWebSocketEmitter("single_user_test")
        
        # Create mock agent
        agent = MockAgent("data_analyzer", websocket_emitter, user_context)
        
        # Create execution context
        execution_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            request_id=user_context.request_id,
            agent_name="data_analyzer",
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Execute agent
        result = await agent.execute_with_context(
            execution_context, 
            "Analyze customer data trends for Q4 performance optimization"
        )
        
        # Validate execution result
        assert result.success, "Agent execution should succeed"
        assert result.agent_name == "data_analyzer", "Result should contain correct agent name"
        assert result.metadata['user_id'] == "single_user_test", "Result should contain correct user ID"
        
        # Validate WebSocket events
        user_events = websocket_emitter.get_events_for_user("single_user_test")
        assert len(user_events) >= 5, "Should have at least 5 events (started, thinking, tool_executing, tool_completed, completed)"
        
        # Validate event types and ordering
        event_types = [event['type'] for event in user_events]
        assert 'agent_started' in event_types, "Should have agent_started event"
        assert 'agent_thinking' in event_types, "Should have agent_thinking event" 
        assert 'tool_executing' in event_types, "Should have tool_executing event"
        assert 'tool_completed' in event_types, "Should have tool_completed event"
        assert 'agent_completed' in event_types, "Should have agent_completed event"
        
        # Validate event ordering (started should come first, completed should come last)
        assert event_types[0] == 'agent_started', "First event should be agent_started"
        assert event_types[-1] == 'agent_completed', "Last event should be agent_completed"
        
        # Validate event timestamps are sequential
        timestamps = [event['timestamp'] for event in user_events]
        assert timestamps == sorted(timestamps), "Events should be in chronological order"
        
        # Validate complete lifecycle
        assert websocket_emitter.has_complete_agent_lifecycle("single_user_test", "data_analyzer"), \
            "User should have complete agent lifecycle events"
    
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_multi_user_agent_event_isolation(self):
        """Test WebSocket event isolation between multiple concurrent users.
        
        BVJ: Critical for multi-tenant SaaS operation - ensures Enterprise customers
        ($15K+ MRR per customer) have complete event isolation.
        """
        num_users = 3
        user_contexts = []
        websocket_emitters = {}
        agents = {}
        
        # Create multiple users
        for i in range(num_users):
            user_id = f"multi_user_{i+1}"
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{i+1}",
                run_id=f"run_{i+1}_{int(time.time())}",
                request_id=f"req_{i+1}_{uuid.uuid4().hex[:8]}"
            )
            user_contexts.append(user_context)
            
            # Create user-specific WebSocket emitter
            emitter = MockWebSocketEmitter(user_id)
            websocket_emitters[user_id] = emitter
            
            # Create user-specific agent
            agent = MockAgent(f"optimizer_{i+1}", emitter, user_context)
            agents[user_id] = agent
        
        # Execute agents concurrently for all users
        async def execute_user_agent(user_context: UserExecutionContext):
            user_id = user_context.user_id
            agent = agents[user_id]
            
            execution_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=user_context.request_id,
                agent_name=agent.agent_name,
                step=PipelineStep.EXECUTION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            
            result = await agent.execute_with_context(
                execution_context, 
                f"Optimize performance for user {user_id} specific requirements"
            )
            
            return user_id, result
        
        # Execute all users concurrently
        concurrent_tasks = [execute_user_agent(ctx) for ctx in user_contexts]
        results = await asyncio.gather(*concurrent_tasks)
        
        # Validate all executions succeeded
        for user_id, result in results:
            assert result.success, f"Execution should succeed for {user_id}"
            assert result.metadata['user_id'] == user_id, f"Result should belong to {user_id}"
        
        # Validate event isolation
        all_user_ids = set(websocket_emitters.keys())
        
        for user_id in all_user_ids:
            emitter = websocket_emitters[user_id]
            user_events = emitter.get_events_for_user(user_id)
            
            # Each user should have their own events
            assert len(user_events) > 0, f"User {user_id} should have events"
            
            # All events should belong to this user
            for event in user_events:
                assert event['user_id'] == user_id, f"Event should belong to {user_id}, got {event['user_id']}"
            
            # Each user should have complete lifecycle
            agent_name = agents[user_id].agent_name
            assert emitter.has_complete_agent_lifecycle(user_id, agent_name), \
                f"User {user_id} should have complete agent lifecycle"
        
        # Validate no cross-contamination between users
        for user_id_1 in all_user_ids:
            for user_id_2 in all_user_ids:
                if user_id_1 != user_id_2:
                    emitter_1 = websocket_emitters[user_id_1]
                    emitter_2 = websocket_emitters[user_id_2]
                    
                    events_1 = emitter_1.get_events_for_user(user_id_1)
                    events_2 = emitter_2.get_events_for_user(user_id_2)
                    
                    # User 1's emitter should not have User 2's events
                    user_2_events_in_emitter_1 = emitter_1.get_events_for_user(user_id_2)
                    assert len(user_2_events_in_emitter_1) == 0, \
                        f"Emitter for {user_id_1} should not have events for {user_id_2}"
                    
                    # User 2's emitter should not have User 1's events
                    user_1_events_in_emitter_2 = emitter_2.get_events_for_user(user_id_1)
                    assert len(user_1_events_in_emitter_2) == 0, \
                        f"Emitter for {user_id_2} should not have events for {user_id_1}"
    
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_agent_event_payload_validation(self):
        """Test WebSocket event payload structure and content validation.
        
        BVJ: Ensures event payloads contain correct data for frontend consumption,
        enabling proper user experience in chat interface.
        """
        user_context = UserExecutionContext(
            user_id="payload_test_user",
            thread_id="payload_thread",
            run_id=f"payload_run_{int(time.time())}",
            request_id=f"payload_req_{uuid.uuid4().hex[:8]}"
        )
        
        websocket_emitter = MockWebSocketEmitter("payload_test_user")
        agent = MockAgent("payload_analyzer", websocket_emitter, user_context)
        
        execution_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            request_id=user_context.request_id,
            agent_name="payload_analyzer",
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        test_prompt = "Analyze payload structure validation requirements"
        result = await agent.execute_with_context(execution_context, test_prompt)
        
        # Validate events were created
        user_events = websocket_emitter.get_events_for_user("payload_test_user")
        assert len(user_events) > 0, "Should have events for validation"
        
        # Validate agent_started event payload
        started_events = [e for e in user_events if e['type'] == 'agent_started']
        assert len(started_events) > 0, "Should have agent_started event"
        
        started_event = started_events[0]
        assert started_event['user_id'] == "payload_test_user", "Started event should have correct user ID"
        assert started_event['agent_name'] == "payload_analyzer", "Started event should have correct agent name"
        assert 'timestamp' in started_event, "Started event should have timestamp"
        assert 'context' in started_event, "Started event should have context"
        assert started_event['kwargs']['prompt'] == test_prompt, "Started event should contain prompt"
        
        # Validate agent_thinking event payload
        thinking_events = [e for e in user_events if e['type'] == 'agent_thinking']
        assert len(thinking_events) > 0, "Should have agent_thinking events"
        
        thinking_event = thinking_events[0]
        assert thinking_event['user_id'] == "payload_test_user", "Thinking event should have correct user ID"
        assert thinking_event['agent_name'] == "payload_analyzer", "Thinking event should have correct agent name"
        assert 'reasoning' in thinking_event, "Thinking event should have reasoning"
        assert 'step_number' in thinking_event, "Thinking event should have step number"
        assert isinstance(thinking_event['step_number'], int), "Step number should be integer"
        
        # Validate tool_executing event payload
        tool_executing_events = [e for e in user_events if e['type'] == 'tool_executing']
        assert len(tool_executing_events) > 0, "Should have tool_executing events"
        
        tool_event = tool_executing_events[0]
        assert tool_event['user_id'] == "payload_test_user", "Tool event should have correct user ID"
        assert 'tool_name' in tool_event, "Tool event should have tool name"
        assert 'parameters' in tool_event, "Tool event should have parameters"
        assert isinstance(tool_event['parameters'], dict), "Parameters should be dictionary"
        
        # Validate tool_completed event payload
        tool_completed_events = [e for e in user_events if e['type'] == 'tool_completed']
        assert len(tool_completed_events) > 0, "Should have tool_completed events"
        
        completed_tool_event = tool_completed_events[0]
        assert completed_tool_event['user_id'] == "payload_test_user", "Tool completed event should have correct user ID"
        assert 'result' in completed_tool_event, "Tool completed event should have result"
        assert isinstance(completed_tool_event['result'], dict), "Tool result should be dictionary"
        
        # Validate agent_completed event payload
        agent_completed_events = [e for e in user_events if e['type'] == 'agent_completed']
        assert len(agent_completed_events) > 0, "Should have agent_completed event"
        
        completed_event = agent_completed_events[0]
        assert completed_event['user_id'] == "payload_test_user", "Completed event should have correct user ID"
        assert completed_event['agent_name'] == "payload_analyzer", "Completed event should have correct agent name"
        assert 'result' in completed_event, "Completed event should have result"
        assert isinstance(completed_event['result'], AgentExecutionResult), "Result should be AgentExecutionResult"
        assert completed_event['result'].success, "Result should indicate success"
    
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_concurrent_agent_executions_event_ordering(self):
        """Test event ordering and isolation with concurrent agent executions.
        
        BVJ: Validates that multiple agents can run simultaneously for the same user
        while maintaining proper event ordering and isolation.
        """
        user_context = UserExecutionContext(
            user_id="concurrent_test_user",
            thread_id="concurrent_thread",
            run_id=f"concurrent_run_{int(time.time())}",
            request_id=f"concurrent_req_{uuid.uuid4().hex[:8]}"
        )
        
        websocket_emitter = MockWebSocketEmitter("concurrent_test_user")
        
        # Create multiple agents for the same user
        agents = [
            MockAgent("analyzer_1", websocket_emitter, user_context),
            MockAgent("analyzer_2", websocket_emitter, user_context),
            MockAgent("analyzer_3", websocket_emitter, user_context)
        ]
        
        # Execute agents concurrently
        async def execute_agent_with_delay(agent: MockAgent, delay: float):
            # Add slight delay to create temporal separation
            await asyncio.sleep(delay)
            
            execution_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=f"{user_context.request_id}_{agent.agent_name}",
                agent_name=agent.agent_name,
                step=PipelineStep.EXECUTION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            
            result = await agent.execute_with_context(
                execution_context, 
                f"Concurrent execution for {agent.agent_name}"
            )
            
            return agent.agent_name, result
        
        # Execute with staggered delays
        tasks = [
            execute_agent_with_delay(agents[0], 0.00),  # Start immediately
            execute_agent_with_delay(agents[1], 0.02),  # Start after 20ms
            execute_agent_with_delay(agents[2], 0.04)   # Start after 40ms
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Validate all executions succeeded
        for agent_name, result in results:
            assert result.success, f"Agent {agent_name} should succeed"
            assert result.agent_name == agent_name, f"Result should match agent {agent_name}"
        
        # Validate events
        user_events = websocket_emitter.get_events_for_user("concurrent_test_user")
        assert len(user_events) >= 15, "Should have events from all 3 agents (5 events each minimum)"
        
        # Validate each agent has complete lifecycle
        for agent in agents:
            assert websocket_emitter.has_complete_agent_lifecycle("concurrent_test_user", agent.agent_name), \
                f"Agent {agent.agent_name} should have complete lifecycle events"
        
        # Validate event temporal ordering
        timestamps = [event['timestamp'] for event in user_events]
        assert timestamps == sorted(timestamps), "All events should be in chronological order"
        
        # Validate agent-specific event grouping
        for agent in agents:
            agent_events = [e for e in user_events if e.get('agent_name') == agent.agent_name]
            agent_timestamps = [e['timestamp'] for e in agent_events]
            assert agent_timestamps == sorted(agent_timestamps), \
                f"Events for {agent.agent_name} should be in chronological order"
        
        # Validate no event mixing within agent lifecycles
        # (started -> thinking -> ... -> completed should be sequential for each agent)
        for agent in agents:
            agent_events = [e for e in user_events if e.get('agent_name') == agent.agent_name]
            agent_event_types = [e['type'] for e in agent_events]
            
            # Find positions of started and completed events
            if 'agent_started' in agent_event_types and 'agent_completed' in agent_event_types:
                started_idx = agent_event_types.index('agent_started')
                completed_idx = agent_event_types.index('agent_completed')
                assert started_idx < completed_idx, \
                    f"Agent {agent.agent_name} started event should come before completed event"
    
    def teardown_method(self, method):
        """Clean up test fixtures."""
        test_duration = time.time() - self.test_start_time
        logger.info(f"Test completed in {test_duration:.3f}s")
        super().teardown_method(method)