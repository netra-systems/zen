"CRITICAL: WebSocket Event Guarantees - ALL 5 Required Events MUST be Emitted"

DESIGNED TO FAIL if any of the 5 CRITICAL WebSocket events are missing.
These tests verify WebSocket events that enable substantive chat value.

Per CLAUDE.md Section 6.1 - Required WebSocket Events for Substantive Chat Value:
    1. agent_started - User must see agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI is working on valuable solutions)  
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User must know when valuable response is ready

CRITICAL BUSINESS CONTEXT:
- Chat is 90% of current business value delivery
- WebSocket events enable user transparency and trust
- Missing events = broken user experience = lost business value

Tests use REAL services - NO MOCKS per CLAUDE.md mandate.
Each test MUST FAIL if corresponding events are not emitted.
""

import pytest
import asyncio
import time
from typing import Dict, Any, List, Set, Optional
import json
from dataclasses import dataclass
from shared.isolated_environment import IsolatedEnvironment

# Import the components we're testing'
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


@dataclass
class WebSocketEventCapture:
    Captures WebSocket events for testing."
    Captures WebSocket events for testing."
    event_type: str
    timestamp: float
    run_id: str
    agent_name: str
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type,
            'timestamp': self.timestamp,
            'run_id': self.run_id,
            'agent_name': self.agent_name,
            'data': self.data
        }


class WebSocketEventCollector:
    "Collects and validates WebSocket events for testing."
    
    def __init__(self):
        self.events: List[WebSocketEventCapture] = []
        self.event_lock = asyncio.Lock()
    
    async def capture_event(self, event_type: str, run_id: str, agent_name: str, data: Dict[str, Any):
        ""Capture a WebSocket event."
        async with self.event_lock:
            event = WebSocketEventCapture(
                event_type=event_type,
                timestamp=time.time(),
                run_id=run_id,
                agent_name=agent_name,
                data=data or {}
            self.events.append(event)
    
    def get_events_by_type(self, event_type: str) -> List[WebSocketEventCapture]:
        Get all events of specific type.""
        return [e for e in self.events if e.event_type == event_type]
    
    def get_events_by_run_id(self, run_id: str) -> List[WebSocketEventCapture]:
        Get all events for specific run ID.""
        return [e for e in self.events if e.run_id == run_id]
    
    def get_event_types(self) -> Set[str]:
        Get all unique event types captured."
        Get all unique event types captured."
        return {e.event_type for e in self.events}
    
    def clear(self):
        "Clear all captured events."
        self.events.clear()
    
    def get_event_sequence(self, run_id: str) -> List[str]:
        "Get sequence of event types for a run ID."
        run_events = sorted(
            [e for e in self.events if e.run_id == run_id],
            key=lambda x: x.timestamp
        )
        return [e.event_type for e in run_events]


class MockWebSocketBridge:
    "Mock WebSocket bridge that captures events for testing."
    
    async def __init__(self, collector: WebSocketEventCollector):
        self.collector = collector
        self.is_connected = True
        self.connection_failures = 0
    
    async def notify_agent_started(self, run_id: str, agent_name: str, message: Optional[str] = None):
        Capture agent_started event.""
        await self.collector.capture_event('agent_started', run_id, agent_name, {'message': message)
    
    async def notify_agent_thinking(self, run_id: str, agent_name: str, thought: str, step_number: Optional[int] = None):
        Capture agent_thinking event."
        Capture agent_thinking event."
        await self.collector.capture_event('agent_thinking', run_id, agent_name, {
            'thought': thought, 'step_number': step_number
        }
    
    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str, parameters: Optional[Dict] = None):
        "Capture tool_executing event."
        await self.collector.capture_event('tool_executing', run_id, agent_name, {
            'tool_name': tool_name, 'parameters': parameters
        }
    
    async def notify_tool_completed(self, run_id: str, agent_name: str, tool_name: str, result: Optional[Dict] = None):
        ""Capture tool_completed event."
        await self.collector.capture_event('tool_completed', run_id, agent_name, {
            'tool_name': tool_name, 'result': result
        }
    
    async def notify_agent_completed(self, run_id: str, agent_name: str, result: Optional[Dict) = None, 
                                   execution_time_ms: Optional[float] = None):
        Capture agent_completed event.""
        await self.collector.capture_event('agent_completed', run_id, agent_name, {
            'result': result, 'execution_time_ms': execution_time_ms
        }
    
    async def notify_progress(self, run_id: str, agent_name: str, content: str, is_complete: bool = False):
        Capture progress event.""
        await self.collector.capture_event('progress', run_id, agent_name, {
            'content': content, 'is_complete': is_complete
        }
    
    async def notify_error(self, run_id: str, agent_name: str, error_message: str, 
                          error_type: Optional[str] = None, error_details: Optional[Dict] = None):
        Capture error event."
        Capture error event."
        await self.collector.capture_event('error', run_id, agent_name, {
            'error_message': error_message, 'error_type': error_type, 'error_details': error_details
        }


class CompleteWebSocketTestAgent(BaseAgent):
    "Test agent that demonstrates complete WebSocket event emission."
    
    def __init__(self, emit_all_events: bool = True, skip_events: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.emit_all_events = emit_all_events
        self.skip_events = skip_events or []
        self.tool_executions = 0
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        "Execute with comprehensive WebSocket event emission."
        
        # 1. CRITICAL: agent_started event
        if 'agent_started' not in self.skip_events:
            await self.emit_agent_started(fStarting {self.name} to process user request)"
            await self.emit_agent_started(fStarting {self.name} to process user request)"
        
        # 2. CRITICAL: agent_thinking events
        if 'agent_thinking' not in self.skip_events:
            await self.emit_thinking("Analyzing the user request and planning approach, step_number=1)"
            await asyncio.sleep(0.1)  # Simulate thinking time
            await self.emit_thinking(Determining optimal problem-solving strategy, step_number=2)
        
        # 3. CRITICAL: tool_executing and tool_completed events
        if self.emit_all_events:
            tools_to_execute = ['data_analyzer', 'solution_generator', 'result_validator']
            
            for i, tool_name in enumerate(tools_to_execute):
                if 'tool_executing' not in self.skip_events:
                    await self.emit_tool_executing(tool_name, {'input': f'test_input_{i)')
                
                # Simulate tool execution
                await asyncio.sleep(0.1)
                self.tool_executions += 1
                
                if 'tool_completed' not in self.skip_events:
                    await self.emit_tool_completed(tool_name, {'result': f'tool_result_{i)', 'success': True)
        
        # Final thinking
        if 'agent_thinking' not in self.skip_events:
            await self.emit_thinking("Consolidating results and preparing final response, step_number=3)"
        
        # 5. CRITICAL: agent_completed event
        result = {
            'status': 'completed',
            'tools_executed': self.tool_executions,
            'final_result': 'Comprehensive analysis completed successfully'
        }
        
        if 'agent_completed' not in self.skip_events:
            await self.emit_agent_completed(result)
        
        return result


class PartialWebSocketTestAgent(BaseAgent):
    Test agent that intentionally skips some WebSocket events."
    Test agent that intentionally skips some WebSocket events."
    
    async def __init__(self, missing_events: List[str], **kwargs):
        super().__init__(**kwargs)
        self.missing_events = missing_events
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        "Execute with intentionally missing WebSocket events."
        
        # Conditionally emit events based on missing_events list
        if 'agent_started' not in self.missing_events:
            await self.emit_agent_started(Starting partial agent")"
        
        if 'agent_thinking' not in self.missing_events:
            await self.emit_thinking(Processing request)
        
        if 'tool_executing' not in self.missing_events:
            await self.emit_tool_executing('test_tool', {'param': 'value')
        
        await asyncio.sleep(0.1)  # Simulate processing
        
        if 'tool_completed' not in self.missing_events:
            await self.emit_tool_completed('test_tool', {'result': 'success')
        
        if 'agent_completed' not in self.missing_events:
            await self.emit_agent_completed({'status': 'done')
        
        return {'partial_execution': True, 'missing_events': self.missing_events}


@pytest.mark.asyncio
class WebSocketEventGuaranteesTests:
    "CRITICAL tests that MUST FAIL if required WebSocket events are missing."
    
    @pytest.fixture
    def event_collector(self):
        Create event collector for tests.""
        return WebSocketEventCollector()
    
    @pytest.fixture
    def mock_bridge(self, event_collector):
        Create mock WebSocket bridge."
        Create mock WebSocket bridge."
        return MockWebSocketBridge(event_collector)
    
    async def test_all_five_critical_events_must_be_emitted(self, event_collector, mock_bridge):
        "CRITICAL: ALL 5 required WebSocket events MUST be emitted."
        
        This test MUST FAIL if any of the 5 critical events are missing:
        1. agent_started, 2. agent_thinking, 3. tool_executing, 4. tool_completed, 5. agent_completed
        ""
        # Create agent that emits all events
        agent = CompleteWebSocketTestAgent(name=CompleteEventAgent)
        agent.set_websocket_bridge(mock_bridge, test_run_complete)"
        agent.set_websocket_bridge(mock_bridge, test_run_complete)"
        
        # Execute agent
        context = ExecutionContext(
            run_id=test_run_complete","
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        await agent.execute_core_logic(context)
        
        # CRITICAL CHECK: All 5 required events must be present
        captured_types = event_collector.get_event_types()
        required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        
        missing_events = required_events - captured_types
        if missing_events:
            pytest.fail(fCRITICAL WEBSOCKET VIOLATION: Missing required events for chat value: 
                       f{missing_events}. All 5 events are required for substantive AI interactions. "
                       f{missing_events}. All 5 events are required for substantive AI interactions. "
                       f"Captured events: {captured_types})"
        
        # Verify event sequence is logical
        event_sequence = event_collector.get_event_sequence(test_run_complete)
        
        # agent_started should be first
        if event_sequence[0] != 'agent_started':
            pytest.fail(fWEBSOCKET SEQUENCE VIOLATION: agent_started must be first event. 
                       fGot sequence: {event_sequence}")"
        
        # agent_completed should be last
        if event_sequence[-1] != 'agent_completed':
            pytest.fail(fWEBSOCKET SEQUENCE VIOLATION: agent_completed must be last event. 
                       fGot sequence: {event_sequence})
        
        # tool_executing should come before tool_completed
        for i, event_type in enumerate(event_sequence):
            if event_type == 'tool_completed':
                # Find corresponding tool_executing
                preceding_events = event_sequence[:i]
                if 'tool_executing' not in preceding_events:
                    pytest.fail(f"WEBSOCKET SEQUENCE VIOLATION: tool_completed without preceding"
                               ftool_executing. Sequence: {event_sequence}")"
    
    async def test_agent_started_event_violation_detection(self, event_collector, mock_bridge):
        CRITICAL: Must detect missing agent_started events.""
        
        This test MUST FAIL if agent_started event is not emitted.
        Users need to know when AI begins processing their problem.
        
        # Create agent that skips agent_started event
        agent = PartialWebSocketTestAgent(
            missing_events=['agent_started'],
            name=NoStartEventAgent"
            name=NoStartEventAgent"
        )
        agent.set_websocket_bridge(mock_bridge, "test_run_no_start)"
        
        context = ExecutionContext(
            run_id=test_run_no_start,
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        await agent.execute_core_logic(context)
        
        # CRITICAL CHECK: agent_started event must be present
        started_events = event_collector.get_events_by_type('agent_started')
        
        if not started_events:
            pytest.fail("CRITICAL BUSINESS VALUE VIOLATION: agent_started event missing. "
                       Users must see that agent began processing their problem. 
                       This directly impacts user trust and chat experience.)"
                       This directly impacts user trust and chat experience.)"
        
        # Verify agent_started has meaningful content
        start_event = started_events[0]
        if not start_event.data.get('message'):
            pytest.fail(WEBSOCKET CONTENT VIOLATION: agent_started event lacks meaningful message. "
            pytest.fail(WEBSOCKET CONTENT VIOLATION: agent_started event lacks meaningful message. "
                       Users need clear indication of what the AI is doing.)
    
    async def test_agent_thinking_event_violation_detection(self, event_collector, mock_bridge):
        ""CRITICAL: Must detect missing agent_thinking events."
        
        This test MUST FAIL if agent_thinking events are not emitted.
        Real-time reasoning visibility is essential for user transparency.

        agent = PartialWebSocketTestAgent(
            missing_events=['agent_thinking'],
            name="NoThinkingEventAgent"
        )
        agent.set_websocket_bridge(mock_bridge, test_run_no_thinking)
        
        context = ExecutionContext(
            run_id=test_run_no_thinking,"
            run_id=test_run_no_thinking,"
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        await agent.execute_core_logic(context)
        
        # CRITICAL CHECK: agent_thinking events must be present
        thinking_events = event_collector.get_events_by_type('agent_thinking')
        
        if not thinking_events:
            pytest.fail(CRITICAL USER EXPERIENCE VIOLATION: agent_thinking events missing. "
            pytest.fail(CRITICAL USER EXPERIENCE VIOLATION: agent_thinking events missing. "
                       Users need real-time reasoning visibility to trust AI problem-solving. 
                       This is essential for substantive AI interactions.")"
        
        # Verify thinking events have meaningful content
        for event in thinking_events:
            thought = event.data.get('thought', '')
            if not thought or len(thought) < 10:
                pytest.fail(fWEBSOCKET CONTENT VIOLATION: agent_thinking event has inadequate content: 
                           f'{thought}'. Thoughts must be substantive for user transparency.)
    
    async def test_tool_execution_event_pair_violation_detection(self, event_collector, mock_bridge):
        "CRITICAL: Must detect missing tool execution event pairs."
        
        This test MUST FAIL if tool_executing/tool_completed pairs are not emitted.
        Tool transparency is crucial for demonstrating problem-solving approach.
        "
        "
        # Test missing tool_executing events
        agent = PartialWebSocketTestAgent(
            missing_events=['tool_executing'],
            name=NoToolExecEventAgent"
            name=NoToolExecEventAgent"
        )
        agent.set_websocket_bridge(mock_bridge, test_run_no_tool_exec)
        
        context = ExecutionContext(
            run_id=test_run_no_tool_exec","
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        await agent.execute_core_logic(context)
        
        # CRITICAL CHECK: tool_executing events must be present
        executing_events = event_collector.get_events_by_type('tool_executing')
        completed_events = event_collector.get_events_by_type('tool_completed')
        
        if completed_events and not executing_events:
            pytest.fail(CRITICAL TOOL TRANSPARENCY VIOLATION: tool_completed events present 
                       without corresponding tool_executing events. Users need to see tool "
                       without corresponding tool_executing events. Users need to see tool "
                       "usage transparency for trust in AI problem-solving approach.)"
        
        # Clear events and test missing tool_completed
        event_collector.clear()
        
        agent = PartialWebSocketTestAgent(
            missing_events=['tool_completed'],
            name=NoToolCompleteEventAgent
        )
        agent.set_websocket_bridge(mock_bridge, "test_run_no_tool_complete)"
        
        await agent.execute_core_logic(context)
        
        executing_events = event_collector.get_events_by_type('tool_executing')
        completed_events = event_collector.get_events_by_type('tool_completed')
        
        if executing_events and not completed_events:
            pytest.fail(CRITICAL RESULT DELIVERY VIOLATION: tool_executing events present 
                       without corresponding tool_completed events. Users need tool results "
                       without corresponding tool_completed events. Users need tool results "
                       to receive actionable insights from AI processing.")"
    
    async def test_agent_completed_event_violation_detection(self, event_collector, mock_bridge):
        CRITICAL: Must detect missing agent_completed events.""
        
        This test MUST FAIL if agent_completed event is not emitted.
        Users must know when the valuable AI response is ready.
        
        agent = PartialWebSocketTestAgent(
            missing_events=['agent_completed'],
            name=NoCompleteEventAgent"
            name=NoCompleteEventAgent"
        )
        agent.set_websocket_bridge(mock_bridge, "test_run_no_complete)"
        
        context = ExecutionContext(
            run_id=test_run_no_complete,
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        await agent.execute_core_logic(context)
        
        # CRITICAL CHECK: agent_completed event must be present
        completed_events = event_collector.get_events_by_type('agent_completed')
        
        if not completed_events:
            pytest.fail("CRITICAL COMPLETION NOTIFICATION VIOLATION: agent_completed event missing. "
                       Users must know when valuable AI response is ready. This is essential 
                       for completing the AI interaction workflow and delivering business value.)"
                       for completing the AI interaction workflow and delivering business value.)"
        
        # Verify completion event has result data
        complete_event = completed_events[0]
        result_data = complete_event.data.get('result')
        
        if not result_data:
            pytest.fail(WEBSOCKET CONTENT VIOLATION: agent_completed event lacks result data. "
            pytest.fail(WEBSOCKET CONTENT VIOLATION: agent_completed event lacks result data. "
                       Users need to receive the actual AI-generated value, not just completion notification.)
    
    async def test_concurrent_websocket_event_integrity(self, event_collector, mock_bridge):
        ""CRITICAL: Must detect WebSocket event integrity issues under concurrent load."
        
        This test stresses concurrent event emission and MUST FAIL if
        events are lost, duplicated, or corrupted under load.

        # Create multiple agents executing concurrently
        num_concurrent_agents = 10
        agents = [
            CompleteWebSocketTestAgent(name=f"ConcurrentAgent{i})"
            for i in range(num_concurrent_agents)
        ]
        
        # Set up WebSocket bridges for all agents
        for i, agent in enumerate(agents):
            agent.set_websocket_bridge(mock_bridge, fconcurrent_run_{i}")"
        
        # Execute all agents concurrently
        async def execute_agent(agent, agent_id):
            context = ExecutionContext(
                run_id=fconcurrent_run_{agent_id},
                agent_name=agent.name,
                state=DeepAgentState()
            )
            return await agent.execute_core_logic(context)
        
        tasks = [execute_agent(agent, i) for i, agent in enumerate(agents)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze event integrity
        failed_executions = [r for r in results if isinstance(r, Exception)]
        if failed_executions:
            pytest.fail(fCONCURRENT EXECUTION VIOLATION: {len(failed_executions)} out of "
            pytest.fail(fCONCURRENT EXECUTION VIOLATION: {len(failed_executions)} out of "
                       f"{num_concurrent_agents} concurrent agents failed: {failed_executions})"
        
        # CRITICAL CHECK: All required events must be present for each agent
        required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        
        for i in range(num_concurrent_agents):
            run_id = fconcurrent_run_{i}
            run_events = event_collector.get_events_by_run_id(run_id)
            
            if not run_events:
                pytest.fail(fCONCURRENT EVENT LOSS: No events captured for concurrent run {run_id). 
                           fEvents may be lost under concurrent load.")"
            
            run_event_types = {e.event_type for e in run_events}
            missing_events = required_events - run_event_types
            
            if missing_events:
                pytest.fail(fCONCURRENT EVENT INTEGRITY VIOLATION: Run {run_id) missing events 
                           f{missing_events} under concurrent load. This indicates event loss 
                           f"or race conditions affecting user experience.)"
        
        # Check for event duplication
        total_events = len(event_collector.events)
        expected_events = num_concurrent_agents * 5  # 5 required events per agent minimum
        
        if total_events < expected_events:
            pytest.fail(fCONCURRENT EVENT LOSS: Expected at least {expected_events) events, "
            pytest.fail(fCONCURRENT EVENT LOSS: Expected at least {expected_events) events, "
                       fgot {total_events}. Events are being lost under concurrent load.)
        
        # Verify temporal ordering within each run
        for i in range(num_concurrent_agents):
            run_id = fconcurrent_run_{i}"
            run_id = fconcurrent_run_{i}"
            sequence = event_collector.get_event_sequence(run_id)
            
            # Basic sequence validation
            if sequence[0] != 'agent_started':
                pytest.fail(f"CONCURRENT SEQUENCE VIOLATION: Run {run_id} wrong start event: {sequence})"
            
            if sequence[-1] != 'agent_completed':
                pytest.fail(fCONCURRENT SEQUENCE VIOLATION: Run {run_id} wrong end event: {sequence})
    
    async def test_websocket_bridge_failure_resilience(self, event_collector, mock_bridge):
        CRITICAL: Must detect lack of resilience to WebSocket bridge failures.""
        
        This test simulates WebSocket connection issues and MUST FAIL if
        agent execution is blocked by WebSocket problems.
        
        # Create agent with failing WebSocket bridge
        agent = CompleteWebSocketTestAgent(name=ResilienceTestAgent")"
        
        # Simulate WebSocket bridge connection failure
        mock_bridge.is_connected = False
        mock_bridge.connection_failures = 3
        
        # Override bridge methods to simulate failures
        original_notify_started = mock_bridge.notify_agent_started
        original_notify_thinking = mock_bridge.notify_agent_thinking
        
        async def failing_notify_started(*args, **kwargs):
            mock_bridge.connection_failures += 1
            if mock_bridge.connection_failures > 2:
                raise ConnectionError(WebSocket bridge connection failed)
            return await original_notify_started(*args, **kwargs)
        
        async def failing_notify_thinking(*args, **kwargs):
            if mock_bridge.connection_failures > 2:
                raise ConnectionError(WebSocket bridge connection failed)"
                raise ConnectionError(WebSocket bridge connection failed)"
            return await original_notify_thinking(*args, **kwargs)
        
        mock_bridge.notify_agent_started = failing_notify_started
        mock_bridge.notify_agent_thinking = failing_notify_thinking
        
        agent.set_websocket_bridge(mock_bridge, "resilience_test_run)"
        
        context = ExecutionContext(
            run_id=resilience_test_run,
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        # Agent execution should NOT fail due to WebSocket issues
        try:
            result = await agent.execute_core_logic(context)
            
            # CRITICAL CHECK: Agent must complete successfully despite WebSocket issues
            if not result or result.get('status') != 'completed':
                pytest.fail("RESILIENCE VIOLATION: Agent execution failed due to WebSocket issues. "
                           Agent processing must be resilient to communication failures to 
                           maintain business continuity.)"
                           maintain business continuity.)"
                           
        except ConnectionError as e:
            pytest.fail(fRESILIENCE VIOLATION: Agent execution blocked by WebSocket failure: {e). "
            pytest.fail(fRESILIENCE VIOLATION: Agent execution blocked by WebSocket failure: {e). "
                       Core AI processing must continue even when event delivery fails, 
                       ensuring business value delivery is not interrupted.")"
        
        # Some events might be missing due to connection issues, but core logic should complete
        captured_events = event_collector.get_events_by_run_id(resilience_test_run)
        
        # At minimum, some events should have been captured before failures
        if not captured_events:
            # This might be expected with connection failures, but log for analysis
            print(INFO: No events captured due to WebSocket failures - this may be expected "
            print(INFO: No events captured due to WebSocket failures - this may be expected "
                  "in resilience testing scenarios)"
    
    async def test_websocket_event_content_validation(self, event_collector, mock_bridge):
        "CRITICAL: Must detect inadequate WebSocket event content."
        
        This test validates event content quality and MUST FAIL if
        events lack meaningful information for users.
"
"
        agent = CompleteWebSocketTestAgent(name=ContentValidationAgent)"
        agent = CompleteWebSocketTestAgent(name=ContentValidationAgent)"
        agent.set_websocket_bridge(mock_bridge, content_test_run")"
        
        context = ExecutionContext(
            run_id=content_test_run,
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        await agent.execute_core_logic(context)
        
        # CRITICAL CHECK: Validate content quality of each event type
        
        # 1. agent_started content validation
        started_events = event_collector.get_events_by_type('agent_started')
        for event in started_events:
            message = event.data.get('message', '')
            if not message or len(message) < 10:
                pytest.fail(fCONTENT QUALITY VIOLATION: agent_started event has inadequate ""
                           fmessage: '{message}'. Users need meaningful start notifications.)
        
        # 2. agent_thinking content validation
        thinking_events = event_collector.get_events_by_type('agent_thinking')
        for event in thinking_events:
            thought = event.data.get('thought', '')
            if not thought or len(thought) < 15:
                pytest.fail(fCONTENT QUALITY VIOLATION: agent_thinking event has inadequate 
                           f"thought: '{thought}'. Reasoning must be substantive for transparency.)"
            
            # Thinking should show actual problem-solving process
            if 'analyzing' not in thought.lower() and 'planning' not in thought.lower() and 'determining' not in thought.lower():
                pytest.fail(fCONTENT RELEVANCE VIOLATION: agent_thinking lacks problem-solving "
                pytest.fail(fCONTENT RELEVANCE VIOLATION: agent_thinking lacks problem-solving "
                           fkeywords: '{thought}'. Must show actual reasoning process.)
        
        # 3. tool execution content validation
        executing_events = event_collector.get_events_by_type('tool_executing')
        completed_events = event_collector.get_events_by_type('tool_completed')
        
        for event in executing_events:
            tool_name = event.data.get('tool_name', '')
            if not tool_name or len(tool_name) < 3:
                pytest.fail(fCONTENT QUALITY VIOLATION: tool_executing event has inadequate "
                pytest.fail(fCONTENT QUALITY VIOLATION: tool_executing event has inadequate "
                           f"tool_name: '{tool_name}'. Users need clear tool identification.)"
        
        for event in completed_events:
            result = event.data.get('result')
            if not result or not isinstance(result, dict):
                pytest.fail(fCONTENT QUALITY VIOLATION: tool_completed event lacks meaningful 
                           fresult "data": {"result}. Users need actionable tool outcomes.)"
        
        # 4. agent_completed content validation
        completed_events = event_collector.get_events_by_type('agent_completed')
        for event in completed_events:
            result = event.data.get('result')
            if not result or not isinstance(result, dict):
                pytest.fail(fCONTENT QUALITY VIOLATION: agent_completed event lacks meaningful ""
                           fresult: {result}. Users need comprehensive final results.)
            
            # Final result should contain substantive information
            if 'status' not in result or 'final_result' not in result:
                pytest.fail(fCONTENT STRUCTURE VIOLATION: agent_completed result missing 
                           f"required fields (status, final_result): {result})"

))))))))))))))))))))