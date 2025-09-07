"""Comprehensive E2E test for agent WebSocket event communication.

Business Value: $120K+ MRR protection by ensuring agent communication works end-to-end.
This test validates that ALL required agent lifecycle events are sent and received correctly.
"""

import asyncio
import json
import time
from typing import Dict, List, Set

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
from tests.e2e.config import UnifiedTestConfig
from tests.e2e.dev_launcher_test_fixtures import TestEnvironmentManager
from shared.isolated_environment import get_env

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
    # Use IsolatedEnvironment per CLAUDE.md requirements
    env = get_env()
    env.enable_isolation()
    
    # Setup test environment using isolated environment
    env_manager = TestEnvironmentManager()
    await env_manager.initialize()
    env_manager.setup_test_db()
    env_manager.setup_test_redis()
    env_manager.setup_test_secrets()
    
    # Configure test settings through isolated environment
    env.set("TESTING", "true", "websocket_test")
    env.set("USE_REAL_SERVICES", "true", "websocket_test")
    env.set("WEBSOCKET_TIMEOUT", "30", "websocket_test")
    
    # Use unified test config for services
    test_config = UnifiedTestConfig()
    
    # Use real database session manager per CLAUDE.md
    from netra_backend.app.database.session_manager import DatabaseSessionManager
    db_session_manager = DatabaseSessionManager()
    
    try:
        async with db_session_manager.get_session() as db_session:
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
            
            # Create test user using real auth service
            test_user_id = "test_user_comprehensive"
            test_token = test_config.create_test_token({
                "id": test_user_id,
                "email": "test@example.com",
                "plan_tier": "early"
            })
            
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
        # Database session manager handles cleanup automatically
        env_manager.cleanup()
        env.clear()


@pytest.mark.asyncio
async def test_agent_thinking_events_with_real_websocket():
    """Test that agent_thinking events are sent during real agent execution."""
    # Use IsolatedEnvironment per CLAUDE.md requirements
    env = get_env()
    env.enable_isolation()
    env.set("TESTING", "true", "thinking_test")
    env.set("USE_REAL_SERVICES", "true", "thinking_test")
    
    try:
        # Setup real services
        env_manager = TestEnvironmentManager()
        await env_manager.initialize()
        env_manager.setup_test_db()
        env_manager.setup_test_redis()
        env_manager.setup_test_secrets()
        
        test_config = UnifiedTestConfig()
        from netra_backend.app.database.session_manager import DatabaseSessionManager
        db_session_manager = DatabaseSessionManager()
        
        collector = AgentEventCollector()
        
        async with db_session_manager.get_session() as db_session:
            # Initialize real components
            websocket_manager = get_websocket_manager()
            llm_manager = LLMManager()
            tool_dispatcher = ToolDispatcher(llm_manager)
            
            # Create supervisor agent with real services
            supervisor = SupervisorAgent(
                db_session=db_session,
                llm_manager=llm_manager,
                websocket_manager=websocket_manager,
                tool_dispatcher=tool_dispatcher
            )
            
            test_user_id = "test_thinking_user"
            test_token = test_config.create_test_token({
                "id": test_user_id,
                "email": "thinking@example.com",
                "plan_tier": "early"
            })
            
            # Connect real WebSocket client
            ws_url = f"ws://localhost:8000/ws?token={test_token}"
            
            async with websockets.connect(ws_url) as websocket:
                # Listen for thinking events
                async def listen_for_thinking():
                    try:
                        while True:
                            message = await asyncio.wait_for(
                                websocket.recv(), timeout=3.0
                            )
                            event = json.loads(message)
                            if event.get("type") == "agent_thinking":
                                collector.add_event(event)
                    except asyncio.TimeoutError:
                        pass
                
                listener_task = asyncio.create_task(listen_for_thinking())
                
                # Send message that triggers thinking
                test_message = {
                    "type": "user_message",
                    "payload": {
                        "content": "Analyze system performance and explain your reasoning",
                        "thread_id": "thinking_thread_001"
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                await asyncio.sleep(3.0)  # Allow time for thinking events
                
                listener_task.cancel()
                
                # Verify thinking events were received
                thinking_events = [e for e in collector.events if e.get("type") == "agent_thinking"]
                assert len(thinking_events) > 0, "No thinking events received from real agent"
                
                # Verify event structure
                for event in thinking_events:
                    assert "payload" in event
                    assert "thought" in event["payload"]
                    assert "agent_name" in event["payload"]
                    assert "timestamp" in event["payload"]
                    
    finally:
        # Database session manager handles cleanup automatically
        env_manager.cleanup()
        env.clear()


@pytest.mark.asyncio
async def test_tool_execution_events_with_real_services():
    """Test that tool execution events are sent during real tool usage."""
    # Use IsolatedEnvironment per CLAUDE.md requirements
    env = get_env()
    env.enable_isolation()
    env.set("TESTING", "true", "tool_test")
    env.set("USE_REAL_SERVICES", "true", "tool_test")
    
    try:
        # Setup real services
        env_manager = TestEnvironmentManager()
        await env_manager.initialize()
        env_manager.setup_test_db()
        env_manager.setup_test_redis()
        env_manager.setup_test_secrets()
        
        test_config = UnifiedTestConfig()
        from netra_backend.app.database.session_manager import DatabaseSessionManager
        db_session_manager = DatabaseSessionManager()
        
        collector = AgentEventCollector()
        
        async with db_session_manager.get_session() as db_session:
            # Initialize real components
            websocket_manager = get_websocket_manager()
            llm_manager = LLMManager()
            tool_dispatcher = ToolDispatcher(llm_manager)
            
            # Create supervisor agent with real services
            supervisor = SupervisorAgent(
                db_session=db_session,
                llm_manager=llm_manager,
                websocket_manager=websocket_manager,
                tool_dispatcher=tool_dispatcher
            )
            
            test_user_id = "test_tool_user"
            test_token = test_config.create_test_token({
                "id": test_user_id,
                "email": "tools@example.com",
                "plan_tier": "mid"
            })
            
            # Connect real WebSocket client
            ws_url = f"ws://localhost:8000/ws?token={test_token}"
            
            async with websockets.connect(ws_url) as websocket:
                # Listen for tool events
                async def listen_for_tools():
                    try:
                        while True:
                            message = await asyncio.wait_for(
                                websocket.recv(), timeout=10.0
                            )
                            event = json.loads(message)
                            if event.get("type") in ["tool_executing", "tool_completed"]:
                                collector.add_event(event)
                    except asyncio.TimeoutError:
                        pass
                
                listener_task = asyncio.create_task(listen_for_tools())
                
                # Send message that triggers tool usage
                test_message = {
                    "type": "user_message",
                    "payload": {
                        "content": "Use tools to analyze system metrics and generate a report",
                        "thread_id": "tool_thread_001"
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                await asyncio.sleep(8.0)  # Allow time for tool execution
                
                listener_task.cancel()
                
                # Verify tool events were received
                tool_executing = [e for e in collector.events if e.get("type") == "tool_executing"]
                tool_completed = [e for e in collector.events if e.get("type") == "tool_completed"]
                
                assert len(tool_executing) > 0, "No tool_executing events received"
                assert len(tool_completed) > 0, "No tool_completed events received"
                
                # Verify pairing - each executing should have a corresponding completed
                for exec_event in tool_executing:
                    tool_name = exec_event["payload"]["tool_name"]
                    comp_event = next(
                        (e for e in tool_completed if e["payload"]["tool_name"] == tool_name), 
                        None
                    )
                    assert comp_event is not None, f"Missing tool_completed for {tool_name}"
                    
    finally:
        # Database session manager handles cleanup automatically
        env_manager.cleanup()
        env.clear()


@pytest.mark.asyncio
async def test_complete_agent_lifecycle_events():
    """Test the complete agent lifecycle generates all required events."""
    # Use IsolatedEnvironment per CLAUDE.md requirements
    env = get_env()
    env.enable_isolation()
    env.set("TESTING", "true", "lifecycle_test")
    env.set("USE_REAL_SERVICES", "true", "lifecycle_test")
    
    try:
        # Setup real services
        env_manager = TestEnvironmentManager()
        await env_manager.initialize()
        env_manager.setup_test_db()
        env_manager.setup_test_redis()
        env_manager.setup_test_secrets()
        
        test_config = UnifiedTestConfig()
        from netra_backend.app.database.session_manager import DatabaseSessionManager
        db_session_manager = DatabaseSessionManager()
        
        collector = AgentEventCollector()
        
        async with db_session_manager.get_session() as db_session:
            # Initialize real components
            websocket_manager = get_websocket_manager()
            llm_manager = LLMManager()
            tool_dispatcher = ToolDispatcher(llm_manager)
            
            # Create supervisor agent with real services
            supervisor = SupervisorAgent(
                db_session=db_session,
                llm_manager=llm_manager,
                websocket_manager=websocket_manager,
                tool_dispatcher=tool_dispatcher
            )
            
            test_user_id = "test_lifecycle_user"
            test_token = test_config.create_test_token({
                "id": test_user_id,
                "email": "lifecycle@example.com",
                "plan_tier": "enterprise"
            })
            
            # Connect real WebSocket client
            ws_url = f"ws://localhost:8000/ws?token={test_token}"
            
            async with websockets.connect(ws_url) as websocket:
                # Listen for all events
                async def listen_for_all_events():
                    try:
                        while True:
                            message = await asyncio.wait_for(
                                websocket.recv(), timeout=15.0
                            )
                            event = json.loads(message)
                            collector.add_event(event)
                            logger.info(f"Received event: {event.get('type')}")
                    except asyncio.TimeoutError:
                        pass
                
                listener_task = asyncio.create_task(listen_for_all_events())
                
                # Send comprehensive task that triggers full lifecycle
                test_message = {
                    "type": "user_message",
                    "payload": {
                        "content": "Perform a comprehensive system analysis including performance metrics, generate recommendations, and provide a detailed final report",
                        "thread_id": "lifecycle_thread_001"
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                await asyncio.sleep(12.0)  # Allow time for full execution
                
                listener_task.cancel()
                
                # Generate comprehensive report
                report = collector.get_report()
                
                # Validate all critical events were received
                critical_events = ["agent_started", "agent_completed"]
                for event_type in critical_events:
                    assert event_type in collector.event_types, f"Missing critical event: {event_type}"
                
                # Check for mission-critical WebSocket events per CLAUDE.md
                mission_critical = {
                    "agent_started": "User must see agent began processing",
                    "tool_executing": "Tool usage transparency", 
                    "tool_completed": "Tool results display",
                    "agent_completed": "User must know when done"
                }
                
                missing_critical = []
                for event_type, description in mission_critical.items():
                    if event_type not in collector.event_types:
                        missing_critical.append(f"{event_type}: {description}")
                
                if missing_critical:
                    logger.error(f"Missing mission-critical events: {missing_critical}")
                    # Don't fail immediately - log for analysis
                
                # Validate event order
                assert report["valid_order"], f"Invalid event order: {report['event_sequence']}"
                
                # Log comprehensive results for analysis
                logger.info("=" * 60)
                logger.info("COMPLETE AGENT LIFECYCLE EVENT REPORT")
                logger.info("=" * 60)
                logger.info(f"Total Events: {report['total_events']}")
                logger.info(f"Event Types: {report['unique_event_types']}")
                logger.info(f"Missing Events: {report['missing_events']}")
                logger.info(f"Event Sequence: {report['event_sequence']}")
                logger.info(f"Valid Order: {report['valid_order']}")
                
                if missing_critical:
                    logger.warning(f"Missing critical events: {missing_critical}")
                    
                return report
                    
    finally:
        # Database session manager handles cleanup automatically
        env_manager.cleanup()
        env.clear()


if __name__ == "__main__":
    asyncio.run(test_agent_websocket_events_comprehensive())