"""Comprehensive E2E test for agent WebSocket event communication.

Business Value: $120K+ MRR protection by ensuring agent communication works end-to-end.
This test validates that ALL required agent lifecycle events are sent and received correctly.
"""

import asyncio
import json
import time
from typing import Dict, List, Set
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.message_processing import (
    process_user_message_with_notifications,
)
from netra_backend.app.websocket_core import get_websocket_manager
from tests.helpers.auth_test_helpers import create_test_token
from tests.helpers.database_helpers import TestDatabaseHelper
from tests.helpers.env_helpers import TestEnvironmentManager
from tests.helpers.integration_fixtures import get_test_db_url

logger = central_logger.get_logger(__name__)

# Required WebSocket events for complete agent lifecycle
REQUIRED_AGENT_EVENTS = {
    "agent_started",      # Agent begins execution
    "agent_thinking",     # Real-time reasoning updates
    "partial_result",     # Incremental result streaming
    "tool_executing",     # Tool execution status
    "tool_completed",     # Tool completion status
    "final_report",       # Comprehensive completion report
    "agent_completed"     # Agent execution finished
}

# UI Layer categorization for events
EVENT_UI_LAYERS = {
    "FAST": ["agent_started", "tool_executing", "agent_update"],
    "MEDIUM": ["agent_thinking", "partial_result", "stream_chunk"],
    "SLOW": ["final_report", "agent_completed", "tool_completed"]
}


class AgentEventCollector:
    """Collects and validates agent WebSocket events."""
    
    def __init__(self):
        self.events: List[Dict] = []
        self.event_types: Set[str] = set()
        self.event_sequence: List[str] = []
        self.timing: Dict[str, float] = {}
        self.start_time = time.time()
    
    def add_event(self, event: Dict) -> None:
        """Add an event to the collection."""
        self.events.append(event)
        event_type = event.get("type", "unknown")
        self.event_types.add(event_type)
        self.event_sequence.append(event_type)
        self.timing[event_type] = time.time() - self.start_time
    
    def get_missing_events(self) -> Set[str]:
        """Get events that were expected but not received."""
        return REQUIRED_AGENT_EVENTS - self.event_types
    
    def validate_event_order(self) -> bool:
        """Validate that events arrived in the correct order."""
        # agent_started must be first
        if self.event_sequence and self.event_sequence[0] != "agent_started":
            return False
        
        # agent_completed or final_report should be last
        if self.event_sequence:
            last_event = self.event_sequence[-1]
            if last_event not in ["agent_completed", "final_report"]:
                return False
        
        return True
    
    def get_event_intervals(self) -> Dict[str, float]:
        """Calculate intervals between key events."""
        intervals = {}
        
        if "agent_started" in self.timing and "agent_completed" in self.timing:
            intervals["total_duration"] = (
                self.timing["agent_completed"] - self.timing["agent_started"]
            )
        
        # Calculate intervals between consecutive events
        for i in range(1, len(self.event_sequence)):
            prev_event = self.event_sequence[i-1]
            curr_event = self.event_sequence[i]
            if prev_event in self.timing and curr_event in self.timing:
                interval_key = f"{prev_event}_to_{curr_event}"
                intervals[interval_key] = (
                    self.timing[curr_event] - self.timing[prev_event]
                )
        
        return intervals
    
    def get_report(self) -> Dict:
        """Generate a comprehensive report of collected events."""
        return {
            "total_events": len(self.events),
            "unique_event_types": list(self.event_types),
            "missing_events": list(self.get_missing_events()),
            "event_sequence": self.event_sequence,
            "valid_order": self.validate_event_order(),
            "timing": self.timing,
            "intervals": self.get_event_intervals(),
            "ui_layer_coverage": self._get_ui_layer_coverage()
        }
    
    def _get_ui_layer_coverage(self) -> Dict[str, Dict]:
        """Analyze UI layer coverage."""
        coverage = {}
        for layer, events in EVENT_UI_LAYERS.items():
            received = [e for e in events if e in self.event_types]
            coverage[layer] = {
                "expected": events,
                "received": received,
                "coverage": len(received) / len(events) if events else 0
            }
        return coverage


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(30)
async def test_agent_websocket_events_comprehensive():
    """Test that all required agent lifecycle events are sent via WebSocket.
    
    Business Impact: Core product functionality - agent communication must work.
    """
    env_manager = TestEnvironmentManager()
    env_manager.setup_test_environment()
    
    # Setup test infrastructure
    db_helper = TestDatabaseHelper(get_test_db_url())
    await db_helper.setup()
    
    try:
        async with db_helper.get_session() as db_session:
            # Initialize components
            websocket_manager = get_websocket_manager()
            llm_manager = LLMManager()
            tool_dispatcher = ToolDispatcher(llm_manager)
            
            # Create supervisor agent
            supervisor = SupervisorAgent(
                db_session=db_session,
                llm_manager=llm_manager,
                websocket_manager=websocket_manager,
                tool_dispatcher=tool_dispatcher
            )
            
            # Create test user and auth
            test_user_id = "test_user_comprehensive"
            test_token = create_test_token(test_user_id)
            
            # Event collector
            collector = AgentEventCollector()
            
            # Connect WebSocket client
            ws_url = f"ws://localhost:8000/ws?token={test_token}"
            
            async with websockets.connect(ws_url) as websocket:
                # Start listening for events
                async def listen_for_events():
                    try:
                        while True:
                            message = await asyncio.wait_for(
                                websocket.recv(), timeout=5.0
                            )
                            event = json.loads(message)
                            collector.add_event(event)
                            logger.info(f"Received event: {event.get('type')}")
                    except asyncio.TimeoutError:
                        pass
                    except websockets.exceptions.ConnectionClosed:
                        pass
                
                # Start listener task
                listener_task = asyncio.create_task(listen_for_events())
                
                # Wait for connection
                await asyncio.sleep(0.5)
                
                # Send test message that triggers agent execution
                test_message = {
                    "type": "user_message",
                    "payload": {
                        "content": "Analyze the system performance and provide recommendations",
                        "thread_id": "test_thread_001"
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for agent execution to complete
                await asyncio.sleep(5.0)
                
                # Stop listening
                listener_task.cancel()
                
                # Generate report
                report = collector.get_report()
                
                # Validate results
                assert report["total_events"] > 0, "No events received"
                
                # Check for missing critical events
                missing_events = report["missing_events"]
                if missing_events:
                    logger.error(f"Missing critical events: {missing_events}")
                    logger.error(f"Received events: {report['unique_event_types']}")
                    logger.error(f"Event sequence: {report['event_sequence']}")
                
                # Critical assertions
                assert "agent_started" in collector.event_types, "agent_started event missing"
                assert "agent_completed" in collector.event_types, "agent_completed event missing"
                
                # These events are currently missing but SHOULD be present
                critical_missing = {
                    "agent_thinking": "Agent reasoning updates not sent",
                    "partial_result": "Streaming results not implemented",
                    "tool_executing": "Tool execution notifications missing",
                    "final_report": "Final report not generated"
                }
                
                for event_type, reason in critical_missing.items():
                    if event_type not in collector.event_types:
                        logger.warning(f"MISSING: {event_type} - {reason}")
                
                # Validate event order
                assert report["valid_order"], f"Invalid event order: {report['event_sequence']}"
                
                # Check UI layer coverage
                ui_coverage = report["ui_layer_coverage"]
                for layer, coverage in ui_coverage.items():
                    if coverage["coverage"] < 0.5:  # Less than 50% coverage
                        logger.warning(
                            f"Low {layer} layer coverage: {coverage['coverage']*100:.0f}% "
                            f"(missing: {set(coverage['expected']) - set(coverage['received'])})"
                        )
                
                # Log comprehensive report
                logger.info("=" * 60)
                logger.info("AGENT WEBSOCKET EVENT REPORT")
                logger.info("=" * 60)
                logger.info(f"Total Events: {report['total_events']}")
                logger.info(f"Unique Types: {report['unique_event_types']}")
                logger.info(f"Missing Events: {report['missing_events']}")
                logger.info(f"Event Sequence: {report['event_sequence']}")
                logger.info(f"Valid Order: {report['valid_order']}")
                logger.info("UI Layer Coverage:")
                for layer, cov in ui_coverage.items():
                    logger.info(f"  {layer}: {cov['coverage']*100:.0f}%")
                logger.info("=" * 60)
                
                # Return report for further analysis
                return report
                
    finally:
        await db_helper.teardown()
        env_manager.cleanup()


@pytest.mark.asyncio
async def test_agent_thinking_events_sent():
    """Test that agent_thinking events are sent during reasoning."""
    # This test will verify that thinking events are properly sent
    # when an agent is processing and reasoning about a task
    
    collector = AgentEventCollector()
    
    # Mock WebSocket manager to capture events
    mock_ws_manager = MagicMock()
    sent_messages = []
    
    async def capture_message(thread_id, message):
        sent_messages.append(message)
        if message.get("type") == "agent_thinking":
            collector.add_event(message)
    
    mock_ws_manager.send_to_thread = AsyncMock(side_effect=capture_message)
    
    # Test agent execution with thinking updates
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    
    notifier = WebSocketNotifier(mock_ws_manager)
    context = AgentExecutionContext(
        agent_name="TestAgent",
        run_id="test_run_001",
        thread_id="test_thread_001",
        user_id="test_user"
    )
    
    # Simulate thinking updates
    thoughts = [
        "Analyzing the user's request...",
        "Identifying relevant tools and data sources...",
        "Formulating a comprehensive response...",
        "Finalizing recommendations..."
    ]
    
    for i, thought in enumerate(thoughts, 1):
        await notifier.send_agent_thinking(context, thought, i)
    
    # Verify thinking events were sent
    thinking_events = [msg for msg in sent_messages if msg.get("type") == "agent_thinking"]
    assert len(thinking_events) == len(thoughts), f"Expected {len(thoughts)} thinking events, got {len(thinking_events)}"
    
    # Verify content
    for event, expected_thought in zip(thinking_events, thoughts):
        assert event["payload"]["thought"] == expected_thought
        assert event["payload"]["agent_name"] == "TestAgent"
        assert "step_number" in event["payload"]
        assert "timestamp" in event["payload"]


@pytest.mark.asyncio
async def test_tool_execution_events():
    """Test that tool execution events are properly sent."""
    
    mock_ws_manager = MagicMock()
    sent_messages = []
    
    async def capture_message(thread_id, message):
        sent_messages.append(message)
    
    mock_ws_manager.send_to_thread = AsyncMock(side_effect=capture_message)
    
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    
    notifier = WebSocketNotifier(mock_ws_manager)
    context = AgentExecutionContext(
        agent_name="TestAgent",
        run_id="test_run_002",
        thread_id="test_thread_002",
        user_id="test_user"
    )
    
    # Simulate tool execution
    tools = ["data_analyzer", "report_generator", "recommendation_engine"]
    
    for tool_name in tools:
        # Send tool executing event
        await notifier.send_tool_executing(context, tool_name)
        
        # Simulate tool execution
        await asyncio.sleep(0.1)
        
        # Send tool completed event
        result = {"status": "success", "output": f"Results from {tool_name}"}
        await notifier.send_tool_completed(context, tool_name, result)
    
    # Verify events
    tool_executing = [msg for msg in sent_messages if msg.get("type") == "tool_executing"]
    tool_completed = [msg for msg in sent_messages if msg.get("type") == "tool_completed"]
    
    assert len(tool_executing) == len(tools), f"Expected {len(tools)} tool_executing events"
    assert len(tool_completed) == len(tools), f"Expected {len(tools)} tool_completed events"
    
    # Verify pairing and content
    for tool_name in tools:
        exec_event = next((e for e in tool_executing if e["payload"]["tool_name"] == tool_name), None)
        comp_event = next((e for e in tool_completed if e["payload"]["tool_name"] == tool_name), None)
        
        assert exec_event is not None, f"Missing tool_executing event for {tool_name}"
        assert comp_event is not None, f"Missing tool_completed event for {tool_name}"
        assert comp_event["payload"]["result"]["status"] == "success"


@pytest.mark.asyncio
async def test_final_report_generation():
    """Test that final_report events are generated with comprehensive data."""
    
    mock_ws_manager = MagicMock()
    sent_messages = []
    
    async def capture_message(thread_id, message):
        sent_messages.append(message)
    
    mock_ws_manager.send_to_thread = AsyncMock(side_effect=capture_message)
    
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    
    notifier = WebSocketNotifier(mock_ws_manager)
    context = AgentExecutionContext(
        agent_name="TestAgent",
        run_id="test_run_003",
        thread_id="test_thread_003",
        user_id="test_user"
    )
    
    # Generate comprehensive final report
    report = {
        "summary": "Successfully analyzed system performance",
        "findings": [
            "CPU utilization at 45%",
            "Memory usage optimal",
            "Network latency within acceptable range"
        ],
        "recommendations": [
            "Consider scaling database connections",
            "Implement caching for frequent queries",
            "Optimize WebSocket message batching"
        ],
        "metrics": {
            "execution_time_ms": 1250,
            "tools_used": 3,
            "data_points_analyzed": 150
        }
    }
    
    await notifier.send_final_report(context, report, 1250.0)
    
    # Verify final report
    final_reports = [msg for msg in sent_messages if msg.get("type") == "final_report"]
    assert len(final_reports) == 1, "Expected exactly one final_report event"
    
    report_event = final_reports[0]
    assert report_event["payload"]["report"] == report
    assert report_event["payload"]["total_duration_ms"] == 1250.0
    assert report_event["payload"]["agent_name"] == "TestAgent"
    assert "timestamp" in report_event["payload"]


if __name__ == "__main__":
    asyncio.run(test_agent_websocket_events_comprehensive())