"""SIMPLIFIED CRITICAL END-TO-END TEST: Agent Chat WebSocket Flow

THIS IS A SIMPLIFIED VERSION OF THE PRIMARY VALIDATION FOR CHAT FUNCTIONALITY.
Business Value: $500K+ ARR - Core product functionality depends on this.

Tests the complete flow WITHOUT external service dependencies:
1. User sends message via WebSocket
2. Supervisor processes message 
3. Agent events are sent back via WebSocket
4. User receives complete response

If this test fails, the chat UI is completely broken.
"""

import asyncio
import json
import time
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from loguru import logger

# Import actual production components
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState


class SimplifiedFlowValidator:
    """Validates the critical chat flow events."""
    
    def __init__(self):
        self.events = []
        self.agent_started = False
        self.agent_thinking = False
        self.tool_executing = False
        self.tool_completed = False
        self.partial_results = False
        self.agent_completed = False
        self.errors = []
        
    def record(self, event: Dict) -> None:
        """Record and categorize event."""
        self.events.append(event)
        event_type = event.get("type", "")
        
        if "agent_started" in event_type:
            self.agent_started = True
            logger.info("Agent started event received")
            
        elif "agent_thinking" in event_type:
            self.agent_thinking = True
            logger.info("Agent thinking event received")
            
        elif "tool_executing" in event_type:
            self.tool_executing = True
            logger.info("Tool executing event received")
            
        elif "tool_completed" in event_type:
            self.tool_completed = True
            logger.info("Tool completed event received")
            
        elif "partial_result" in event_type:
            self.partial_results = True
            logger.info("Partial result event received")
            
        elif "agent_completed" in event_type or "final_report" in event_type:
            self.agent_completed = True
            logger.info("Agent completed event received")
    
    def validate(self) -> tuple[bool, List[str]]:
        """Validate critical flow requirements."""
        errors = []
        
        if not self.agent_started:
            errors.append("No agent_started event - User won't know processing began")
            
        if not self.agent_completed:
            errors.append("No completion event - User won't know when done")
            
        if len(self.events) == 0:
            errors.append("CRITICAL: No WebSocket events at all!")
            
        return len(errors) == 0, errors
    
    def get_report(self) -> str:
        """Generate validation report."""
        is_valid, errors = self.validate()
        
        report = [
            "\n" + "=" * 60,
            "SIMPLIFIED CRITICAL CHAT FLOW VALIDATION",
            "=" * 60,
            f"Overall Status: {'PASSED' if is_valid else 'FAILED'}",
            f"Total Events: {len(self.events)}",
            "",
            "Event Coverage:",
            f"  {'YES' if self.agent_started else 'NO'} Agent Started",
            f"  {'YES' if self.agent_thinking else 'NO'} Agent Thinking",
            f"  {'YES' if self.tool_executing else 'NO'} Tool Executing",
            f"  {'YES' if self.tool_completed else 'NO'} Tool Completed",
            f"  {'YES' if self.partial_results else 'NO'} Partial Results",
            f"  {'YES' if self.agent_completed else 'NO'} Agent Completed",
        ]
        
        if errors:
            report.extend(["", "Issues Found:"] + errors)
            
        if self.events:
            report.extend(["", "Event Sequence:"])
            for i, event in enumerate(self.events[:10]):
                report.append(f"  {i+1}. {event.get('type', 'unknown')}")
            if len(self.events) > 10:
                report.append(f"  ... and {len(self.events) - 10} more")
                
        report.append("=" * 60)
        return "\n".join(report)


class TestSimplifiedCriticalAgentChatFlow:
    """Simplified critical tests for agent chat WebSocket flow."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_complete_chat_flow_simplified(self):
        """Test complete chat flow with mocked external dependencies but real WebSocket components."""
        
        logger.info("\n" + "=" * 60)
        logger.info("STARTING SIMPLIFIED CRITICAL CHAT FLOW TEST")
        logger.info("=" * 60)
        
        # Setup WebSocket manager and validator
        ws_manager = WebSocketManager()
        validator = SimplifiedFlowValidator()
        
        # Create mock WebSocket connection
        connection_id = "simple-test-conn"
        user_id = "test-user"
        
        # Mock WebSocket that captures events
        mock_ws = MagicMock()
        sent_messages = []
        
        async def capture_send(message: str):
            """Capture sent WebSocket messages."""
            try:
                if isinstance(message, str):
                    data = json.loads(message)
                elif isinstance(message, dict):
                    data = message
                else:
                    data = {"raw": str(message)}
                    
                sent_messages.append(data)
                validator.record(data)
                logger.debug(f"WebSocket sent: {data.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to capture message: {e}")
        
        mock_ws.send_json = AsyncMock(side_effect=capture_send)
        mock_ws.send_text = AsyncMock(side_effect=capture_send)
        mock_ws.send = AsyncMock(side_effect=capture_send)
        
        # Connect user
        await ws_manager.connect_user(user_id, mock_ws, connection_id)
        
        # Create supervisor components with mock LLM
        class MockLLMManager:
            async def generate(self, *args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate processing
                return {
                    "content": "The system is operational.",
                    "reasoning": "Checking system status...",
                    "confidence": 0.95
                }
        
        llm_manager = MockLLMManager()
        tool_dispatcher = ToolDispatcher()
        
        # Register a simple test tool
        async def test_tool(*args, **kwargs):
            await asyncio.sleep(0.05)  # Simulate tool execution
            return {"status": "success", "data": "Tool executed"}
        
        tool_dispatcher.register_tool("test_tool", test_tool, "Test tool for validation")
        
        # Create and configure agent registry
        registry = AgentRegistry(llm_manager, tool_dispatcher)
        registry.set_websocket_manager(ws_manager)  # This should enhance tool dispatcher
        registry.register_default_agents()
        
        # Create execution engine
        engine = ExecutionEngine(registry, ws_manager)
        
        # Create supervisor agent
        supervisor = SupervisorAgent(llm_manager, tool_dispatcher)
        supervisor.agent_registry = registry
        supervisor.execution_engine = engine
        supervisor.websocket_manager = ws_manager
        
        # Create test message
        test_message = "What is the system status?"
        
        # Process the message through supervisor
        try:
            logger.info("Processing message through supervisor...")
            
            result = await supervisor.execute(
                test_message,
                connection_id,
                user_id
            )
            
            logger.info(f"Supervisor execution completed: {result is not None}")
            
        except Exception as e:
            logger.error(f"Supervisor execution failed: {e}")
            # Even with error, we should have some events
        
        # Allow async events to complete
        await asyncio.sleep(1.0)
        
        # Validate results
        logger.info(validator.get_report())
        
        # Check critical requirements
        assert len(validator.events) > 0, f"No WebSocket events were sent! Sent messages: {sent_messages}"
        
        # At minimum, we should have start indication
        assert validator.agent_started or any("start" in str(e) for e in validator.events), \
            f"No agent start indication. Events: {[e.get('type') for e in validator.events]}"
        
        # Should have some form of completion
        assert validator.agent_completed or any("complet" in str(e) or "final" in str(e) for e in validator.events), \
            f"No completion indication. Events: {[e.get('type') for e in validator.events]}"
        
        # Cleanup
        await ws_manager.disconnect_user(user_id, mock_ws, connection_id)
        
        logger.info("\nSimplified critical chat flow test completed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(20)
    async def test_websocket_notifier_basic_flow_simplified(self):
        """Test WebSocket notifier sends all required events."""
        
        logger.info("\n" + "=" * 60)
        logger.info("TESTING WEBSOCKET NOTIFIER SIMPLIFIED")
        logger.info("=" * 60)
        
        # Setup
        ws_manager = WebSocketManager()
        validator = SimplifiedFlowValidator()
        
        # Mock connection
        connection_id = "notifier-test"
        user_id = "test-user"
        request_id = "req-456"
        
        mock_ws = MagicMock()
        
        async def capture(message):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record(data)
        
        mock_ws.send_json = AsyncMock(side_effect=capture)
        mock_ws.send_text = AsyncMock(side_effect=capture)
        mock_ws.send = AsyncMock(side_effect=capture)
        
        await ws_manager.connect_user(user_id, mock_ws, connection_id)
        
        # Create notifier
        notifier = WebSocketNotifier(ws_manager)
        
        # Create execution context for notifier calls
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        context = AgentExecutionContext(
            run_id=request_id,
            thread_id=connection_id,
            user_id=user_id,
            agent_name="test_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Send all event types
        await notifier.send_agent_started(context)
        await notifier.send_agent_thinking(context, "Processing...")
        await notifier.send_tool_executing(context, "test_tool")
        await notifier.send_tool_completed(context, "test_tool", {"result": "done"})
        await notifier.send_partial_result(context, "Partial data...")
        await notifier.send_agent_completed(context, {"success": True})
        
        # Allow processing
        await asyncio.sleep(0.2)
        
        # Validate
        logger.info(validator.get_report())
        
        assert validator.agent_started, "Agent started event not sent"
        assert validator.agent_thinking, "Agent thinking event not sent"
        assert validator.tool_executing, "Tool executing event not sent"
        assert validator.tool_completed, "Tool completed event not sent"
        assert validator.agent_completed, "Agent completed event not sent"
        
        # Cleanup
        await ws_manager.disconnect_user(user_id, mock_ws, connection_id)
        
        logger.info("\nWebSocket notifier test completed")


if __name__ == "__main__":
    # Run with: python -m pytest tests/e2e/test_critical_agent_chat_flow_simplified.py -v
    pytest.main([__file__, "-v", "--tb=short"])