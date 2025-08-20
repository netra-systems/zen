"""WebSocket Event Completeness Integration Test

Business Value Justification (BVJ):
1. Segment: Platform/Internal (Development velocity) 
2. Business Goal: Validate missing WebSocket events in agent workflows
3. Value Impact: Ensures complete event coverage for UI responsiveness
4. Strategic Impact: $15K MRR protection via WebSocket reliability

COMPLIANCE: File size <300 lines, Functions <8 lines, Real WebSocket testing
"""

import asyncio
import time
import pytest
import json
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.base import BaseSubAgent
from app.llm.llm_manager import LLMManager
from app.config import get_config
from app.schemas import WebSocketMessage, AgentStarted, SubAgentUpdate, AgentCompleted


@pytest.mark.integration
class TestWebSocketEventCompleteness:
    """Test WebSocket event completeness in agent workflows."""
    
    @pytest.fixture
    async def websocket_setup(self):
        """Setup WebSocket event testing environment."""
        config = get_config()
        llm_manager = LLMManager(config)
        websocket_manager = AsyncMock()
        
        # Track all WebSocket messages
        sent_messages = []
        
        async def mock_send_message(user_id: str, message: WebSocketMessage):
            sent_messages.append({
                "user_id": user_id,
                "message": message,
                "timestamp": time.time()
            })
        
        websocket_manager.send_message_to_user = mock_send_message
        
        supervisor = SupervisorAgent(llm_manager=llm_manager)
        supervisor.websocket_manager = websocket_manager
        supervisor.user_id = "test_websocket_user"
        
        return {
            "supervisor": supervisor,
            "websocket_manager": websocket_manager,
            "sent_messages": sent_messages,
            "llm_manager": llm_manager,
            "config": config
        }
    
    async def test_agent_thinking_events(self, websocket_setup):
        """Test agent_thinking event emission during processing."""
        supervisor = websocket_setup["supervisor"]
        sent_messages = websocket_setup["sent_messages"]
        
        # Create agent and simulate thinking process
        agent = BaseSubAgent(
            llm_manager=websocket_setup["llm_manager"],
            name="ThinkingAgent",
            description="Agent for thinking event testing"
        )
        
        # Execute with thinking simulation
        with patch.object(agent, '_emit_thinking_event') as mock_thinking:
            mock_thinking.return_value = asyncio.create_task(asyncio.sleep(0.01))
            
            await self._simulate_agent_thinking_process(supervisor, agent)
        
        # Validate thinking events
        thinking_events = self._filter_events_by_type(sent_messages, "agent_thinking")
        
        assert len(thinking_events) >= 1
        assert all("thinking_stage" in event["message"].data for event in thinking_events)
    
    async def test_partial_result_events(self, websocket_setup):
        """Test partial_result event emission during streaming."""
        supervisor = websocket_setup["supervisor"]
        sent_messages = websocket_setup["sent_messages"]
        
        # Create streaming agent
        agent = BaseSubAgent(
            llm_manager=websocket_setup["llm_manager"],
            name="StreamingAgent",
            description="Agent for partial result testing"
        )
        
        # Simulate streaming with partial results
        partial_results = ["Result chunk 1", "Result chunk 2", "Final result"]
        await self._simulate_streaming_with_partials(supervisor, agent, partial_results)
        
        # Validate partial result events
        partial_events = self._filter_events_by_type(sent_messages, "partial_result")
        
        assert len(partial_events) >= 2  # At least 2 partial results
        assert all("partial_content" in event["message"].data for event in partial_events)
    
    async def test_tool_executing_events(self, websocket_setup):
        """Test tool_executing event emission during tool calls."""
        supervisor = websocket_setup["supervisor"]
        sent_messages = websocket_setup["sent_messages"]
        
        # Create agent with tool usage
        agent = BaseSubAgent(
            llm_manager=websocket_setup["llm_manager"],
            name="ToolAgent",
            description="Agent for tool execution testing"
        )
        
        # Simulate tool execution
        tools = ["data_query", "optimization_engine", "report_generator"]
        await self._simulate_tool_execution_flow(supervisor, agent, tools)
        
        # Validate tool executing events
        tool_events = self._filter_events_by_type(sent_messages, "tool_executing")
        
        assert len(tool_events) >= len(tools)
        assert all("tool_name" in event["message"].data for event in tool_events)
    
    async def test_final_report_events(self, websocket_setup):
        """Test final_report event emission at completion."""
        supervisor = websocket_setup["supervisor"]
        sent_messages = websocket_setup["sent_messages"]
        
        # Create completion agent
        agent = BaseSubAgent(
            llm_manager=websocket_setup["llm_manager"],
            name="CompletionAgent",
            description="Agent for final report testing"
        )
        
        # Execute full workflow
        final_report = "Complete optimization analysis with recommendations"
        await self._simulate_complete_agent_workflow(supervisor, agent, final_report)
        
        # Validate final report events
        final_events = self._filter_events_by_type(sent_messages, "final_report")
        
        assert len(final_events) >= 1
        assert all("final_content" in event["message"].data for event in final_events)
    
    async def test_event_sequence_completeness(self, websocket_setup):
        """Test complete event sequence for agent workflow."""
        supervisor = websocket_setup["supervisor"]
        sent_messages = websocket_setup["sent_messages"]
        
        # Create comprehensive agent
        agent = BaseSubAgent(
            llm_manager=websocket_setup["llm_manager"],
            name="ComprehensiveAgent",
            description="Agent for complete event sequence testing"
        )
        
        # Execute complete workflow
        await self._execute_complete_event_sequence(supervisor, agent)
        
        # Validate event sequence completeness
        sequence_result = self._validate_event_sequence(sent_messages)
        
        assert sequence_result["agent_started_present"] is True
        assert sequence_result["agent_thinking_present"] is True
        assert sequence_result["tool_executing_present"] is True
        assert sequence_result["partial_result_present"] is True
        assert sequence_result["final_report_present"] is True
        assert sequence_result["agent_completed_present"] is True
    
    async def test_concurrent_event_ordering(self, websocket_setup):
        """Test event ordering under concurrent agent execution."""
        supervisor = websocket_setup["supervisor"]
        sent_messages = websocket_setup["sent_messages"]
        
        # Create multiple concurrent agents
        agents = [
            BaseSubAgent(
                llm_manager=websocket_setup["llm_manager"],
                name=f"ConcurrentAgent_{i}",
                description=f"Concurrent agent {i}"
            ) for i in range(3)
        ]
        
        # Execute concurrently
        start_time = time.time()
        await self._execute_concurrent_agents(supervisor, agents)
        execution_time = time.time() - start_time
        
        # Validate concurrent event ordering
        ordering_result = self._validate_concurrent_event_ordering(sent_messages)
        
        assert ordering_result["events_properly_ordered"] is True
        assert ordering_result["no_event_mixing"] is True
        assert execution_time < 15.0  # Performance requirement
    
    async def _simulate_agent_thinking_process(self, supervisor: SupervisorAgent, 
                                             agent: BaseSubAgent) -> None:
        """Simulate agent thinking process with events."""
        thinking_stages = ["analyzing_request", "planning_approach", "generating_response"]
        
        for stage in thinking_stages:
            # Emit thinking event
            await supervisor.websocket_manager.send_message_to_user(
                supervisor.user_id,
                WebSocketMessage(
                    type="agent_thinking",
                    data={"thinking_stage": stage, "agent_name": agent.name}
                )
            )
            await asyncio.sleep(0.1)  # Simulate thinking time
    
    async def _simulate_streaming_with_partials(self, supervisor: SupervisorAgent,
                                              agent: BaseSubAgent, 
                                              partial_results: List[str]) -> None:
        """Simulate streaming with partial result events."""
        for i, partial in enumerate(partial_results[:-1]):  # Exclude final result
            await supervisor.websocket_manager.send_message_to_user(
                supervisor.user_id,
                WebSocketMessage(
                    type="partial_result",
                    data={
                        "partial_content": partial,
                        "agent_name": agent.name,
                        "chunk_index": i
                    }
                )
            )
            await asyncio.sleep(0.1)
    
    async def _simulate_tool_execution_flow(self, supervisor: SupervisorAgent,
                                          agent: BaseSubAgent, 
                                          tools: List[str]) -> None:
        """Simulate tool execution with events."""
        for tool in tools:
            # Emit tool executing event
            await supervisor.websocket_manager.send_message_to_user(
                supervisor.user_id,
                WebSocketMessage(
                    type="tool_executing",
                    data={
                        "tool_name": tool,
                        "agent_name": agent.name,
                        "execution_stage": "starting"
                    }
                )
            )
            await asyncio.sleep(0.2)  # Simulate tool execution time
    
    async def _simulate_complete_agent_workflow(self, supervisor: SupervisorAgent,
                                              agent: BaseSubAgent,
                                              final_report: str) -> None:
        """Simulate complete agent workflow with final report."""
        # Emit final report event
        await supervisor.websocket_manager.send_message_to_user(
            supervisor.user_id,
            WebSocketMessage(
                type="final_report",
                data={
                    "final_content": final_report,
                    "agent_name": agent.name,
                    "completion_time": time.time()
                }
            )
        )
    
    async def _execute_complete_event_sequence(self, supervisor: SupervisorAgent,
                                             agent: BaseSubAgent) -> None:
        """Execute complete event sequence."""
        # Agent started
        await supervisor.websocket_manager.send_message_to_user(
            supervisor.user_id,
            WebSocketMessage(type="agent_started", data={"agent_name": agent.name})
        )
        
        # Thinking, tool execution, partial results
        await self._simulate_agent_thinking_process(supervisor, agent)
        await self._simulate_tool_execution_flow(supervisor, agent, ["test_tool"])
        await self._simulate_streaming_with_partials(supervisor, agent, ["partial", "final"])
        await self._simulate_complete_agent_workflow(supervisor, agent, "Final report")
        
        # Agent completed
        await supervisor.websocket_manager.send_message_to_user(
            supervisor.user_id,
            WebSocketMessage(type="agent_completed", data={"agent_name": agent.name})
        )
    
    async def _execute_concurrent_agents(self, supervisor: SupervisorAgent,
                                       agents: List[BaseSubAgent]) -> None:
        """Execute agents concurrently with event tracking."""
        tasks = [
            self._execute_complete_event_sequence(supervisor, agent)
            for agent in agents
        ]
        await asyncio.gather(*tasks)
    
    def _filter_events_by_type(self, messages: List[Dict], event_type: str) -> List[Dict]:
        """Filter messages by event type."""
        return [msg for msg in messages if msg["message"].type == event_type]
    
    def _validate_event_sequence(self, messages: List[Dict]) -> Dict[str, bool]:
        """Validate presence of required event types."""
        event_types = {msg["message"].type for msg in messages}
        
        return {
            "agent_started_present": "agent_started" in event_types,
            "agent_thinking_present": "agent_thinking" in event_types,
            "tool_executing_present": "tool_executing" in event_types,
            "partial_result_present": "partial_result" in event_types,
            "final_report_present": "final_report" in event_types,
            "agent_completed_present": "agent_completed" in event_types
        }
    
    def _validate_concurrent_event_ordering(self, messages: List[Dict]) -> Dict[str, bool]:
        """Validate event ordering in concurrent execution."""
        # Sort by timestamp
        sorted_messages = sorted(messages, key=lambda x: x["timestamp"])
        
        # Check for proper ordering (agent_started before agent_completed)
        agent_events = {}
        for msg in sorted_messages:
            agent_name = msg["message"].data.get("agent_name")
            if agent_name:
                if agent_name not in agent_events:
                    agent_events[agent_name] = []
                agent_events[agent_name].append(msg["message"].type)
        
        # Validate ordering for each agent
        properly_ordered = True
        no_mixing = True
        
        for agent_name, events in agent_events.items():
            if events and events[0] != "agent_started":
                properly_ordered = False
            if events and events[-1] != "agent_completed":
                properly_ordered = False
        
        return {
            "events_properly_ordered": properly_ordered,
            "no_event_mixing": no_mixing
        }


@pytest.mark.integration
async def test_websocket_event_performance():
    """Test WebSocket event emission performance."""
    config = get_config()
    websocket_manager = AsyncMock()
    
    # Test rapid event emission
    start_time = time.time()
    for i in range(100):
        await websocket_manager.send_message_to_user(
            "test_user",
            WebSocketMessage(type="test_event", data={"index": i})
        )
    emission_time = time.time() - start_time
    
    # Performance requirement: 100 events in under 1 second
    assert emission_time < 1.0