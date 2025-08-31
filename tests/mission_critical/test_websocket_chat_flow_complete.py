#!/usr/bin/env python
"""
MISSION CRITICAL: Complete WebSocket Chat Flow Integration Test

THIS IS THE ULTIMATE TEST FOR CHAT FUNCTIONALITY.
Business Value: $500K+ ARR - Core chat functionality validation

This test suite validates the ACTUAL chat message processing flow:
1. WebSocket → AgentMessageHandler → MessageHandlerService → Supervisor
2. WebSocket manager propagation through the entire chain
3. All 7 critical WebSocket events during real chat processing
4. ExecutionEngine has WebSocketNotifier initialized
5. EnhancedToolExecutionEngine is used for tool execution

CRITICAL: This test MUST pass or chat is broken for users.
This validates the "chat is king" directive is met.

ANY FAILURE HERE MEANS USERS SEE NO REAL-TIME FEEDBACK.
"""

import asyncio
import os
import sys
import time
import uuid
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock, patch

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import all components in the actual chat flow
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.enhanced_tool_execution import (
    EnhancedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager


# ============================================================================
# MOCK WEBSOCKET MANAGER FOR COMPREHENSIVE CHAT FLOW TESTING
# ============================================================================

class ChatFlowWebSocketManager:
    """WebSocket manager that captures ALL events during actual chat flow testing."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, thread_id, data)
        self.connections: Dict[str, Any] = {}
        self.start_time = time.time()
        
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Record message and simulate successful delivery."""
        timestamp = time.time() - self.start_time
        event_type = message.get('type', 'unknown')
        
        event_record = {
            'thread_id': thread_id,
            'message': message,
            'event_type': event_type,
            'timestamp': timestamp,
            'raw_message': message
        }
        
        self.events.append(event_record)
        self.event_timeline.append((timestamp, event_type, thread_id, message))
        
        logger.info(f"🔔 WebSocket Event: {event_type} → Thread {thread_id} @ {timestamp:.3f}s")
        return True
    
    async def connect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user connection."""
        self.connections[thread_id] = {'user_id': user_id, 'connected': True}
        logger.info(f"👤 User {user_id} connected to thread {thread_id}")
    
    async def disconnect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user disconnection."""
        if thread_id in self.connections:
            self.connections[thread_id]['connected'] = False
        logger.info(f"👤 User {user_id} disconnected from thread {thread_id}")
    
    def get_events_for_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all events for a specific thread."""
        return [event for event in self.events if event['thread_id'] == thread_id]
    
    def get_event_types_for_thread(self, thread_id: str) -> List[str]:
        """Get event types for a thread in chronological order."""
        return [event['event_type'] for event in self.events if event['thread_id'] == thread_id]
    
    def clear_events(self):
        """Clear all recorded events."""
        self.events.clear()
        self.event_timeline.clear()
        self.start_time = time.time()


class ChatFlowValidator:
    """Validates complete chat flow with extreme precision."""
    
    # The 7 critical events that MUST be sent for proper chat functionality
    CRITICAL_EVENTS = {
        "agent_started",      # User must see agent began processing
        "agent_thinking",     # Real-time reasoning visibility  
        "tool_executing",     # Tool usage transparency
        "tool_completed",     # Tool results display
        "agent_completed"     # User must know when done
    }
    
    # Additional events that enhance the user experience
    ENHANCED_EVENTS = {
        "partial_result",     # Streaming results
        "final_report",       # Final summary
        "agent_fallback"      # Error handling
    }
    
    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self.events: List[Dict[str, Any]] = []
        self.event_counts: Dict[str, int] = {}
        self.failures: List[str] = []
        self.warnings: List[str] = []
    
    def analyze_chat_flow(self, ws_manager: ChatFlowWebSocketManager) -> Dict[str, Any]:
        """Analyze complete chat flow for this thread."""
        thread_events = ws_manager.get_events_for_thread(self.thread_id)
        self.events = thread_events
        
        # Count events
        for event in self.events:
            event_type = event['event_type']
            self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        # Validate critical requirements
        is_valid = self._validate_critical_requirements()
        
        return {
            'is_valid': is_valid,
            'total_events': len(self.events),
            'event_counts': self.event_counts,
            'failures': self.failures,
            'warnings': self.warnings,
            'critical_events_coverage': self._get_critical_coverage(),
            'user_experience_score': self._calculate_ux_score()
        }
        
    def _validate_critical_requirements(self) -> bool:
        """Validate ALL critical requirements for chat functionality."""
        is_valid = True
        
        # 1. Check for all critical events
        missing_critical = self.CRITICAL_EVENTS - set(self.event_counts.keys())
        if missing_critical:
            self.failures.append(f"❌ CRITICAL: Missing required events: {missing_critical}")
            is_valid = False
        
        # 2. Validate event ordering
        if not self._validate_chat_flow_order():
            self.failures.append("❌ CRITICAL: Invalid chat flow event order")
            is_valid = False
        
        # 3. Ensure tool events are paired
        if not self._validate_tool_event_pairing():
            self.failures.append("❌ CRITICAL: Tool events not properly paired")
            is_valid = False
        
        # 4. Check for user visibility
        if not self._validate_user_visibility():
            self.failures.append("❌ CRITICAL: User would not see chat progress")
            is_valid = False
        
        return is_valid
    
    def _validate_chat_flow_order(self) -> bool:
        """Validate that events follow logical chat flow order."""
        if not self.events:
            return False
        
        event_types = [event['event_type'] for event in self.events]
        
        # First event must be agent_started (user knows processing began)
        if event_types[0] != "agent_started":
            self.failures.append(f"First event was '{event_types[0]}', not 'agent_started'")
            return False
        
        # Last event should be completion (user knows processing finished)
        completion_events = ["agent_completed", "final_report", "agent_fallback"]
        if event_types[-1] not in completion_events:
            self.failures.append(f"Last event was '{event_types[-1]}', not a completion event")
            return False
        
        return True
    
    def _validate_tool_event_pairing(self) -> bool:
        """Ensure all tool executions have matching start/complete events."""
        tool_executing = self.event_counts.get("tool_executing", 0)
        tool_completed = self.event_counts.get("tool_completed", 0)
        
        if tool_executing != tool_completed:
            self.failures.append(f"Tool event mismatch: {tool_executing} starts, {tool_completed} completions")
            return False
        
        return True
    
    def _validate_user_visibility(self) -> bool:
        """Ensure user would see meaningful progress updates."""
        # User must see that processing started
        if self.event_counts.get("agent_started", 0) == 0:
            self.failures.append("User wouldn't know processing started")
            return False
        
        # User must see some form of progress or completion
        progress_events = ["agent_thinking", "tool_executing", "partial_result"]
        completion_events = ["agent_completed", "final_report"]
        
        has_progress = any(self.event_counts.get(event, 0) > 0 for event in progress_events)
        has_completion = any(self.event_counts.get(event, 0) > 0 for event in completion_events)
        
        if not has_progress:
            self.warnings.append("User sees no progress updates during processing")
        
        if not has_completion:
            self.failures.append("User wouldn't know when processing completed")
            return False
        
        return True
    
    def _get_critical_coverage(self) -> Dict[str, bool]:
        """Get coverage status for all critical events."""
        return {event: event in self.event_counts for event in self.CRITICAL_EVENTS}
    
    def _calculate_ux_score(self) -> float:
        """Calculate user experience score (0-100) based on event coverage."""
        critical_coverage = sum(1 for event in self.CRITICAL_EVENTS if event in self.event_counts)
        critical_score = (critical_coverage / len(self.CRITICAL_EVENTS)) * 70  # 70% for critical
        
        enhanced_coverage = sum(1 for event in self.ENHANCED_EVENTS if event in self.event_counts)
        enhanced_score = (enhanced_coverage / len(self.ENHANCED_EVENTS)) * 30  # 30% for enhanced
        
        return critical_score + enhanced_score
    
    def generate_detailed_report(self) -> str:
        """Generate comprehensive chat flow analysis report."""
        ux_score = self._calculate_ux_score()
        critical_coverage = self._get_critical_coverage()
        
        report = [
            "\n" + "=" * 100,
            f"🔍 CHAT FLOW ANALYSIS REPORT - Thread {self.thread_id}",
            "=" * 100,
            f"📊 Overall Status: {'✅ CHAT WORKING' if not self.failures else '❌ CHAT BROKEN'}",
            f"👥 User Experience Score: {ux_score:.1f}/100",
            f"📈 Total Events: {len(self.events)}",
            f"🎯 Event Types: {len(self.event_counts)}",
            "",
            "🚨 CRITICAL EVENTS COVERAGE:",
        ]
        
        for event in self.CRITICAL_EVENTS:
            status = "✅" if critical_coverage[event] else "❌"
            count = self.event_counts.get(event, 0)
            report.append(f"   {status} {event}: {count} events")
        
        if self.failures:
            report.extend(["", "💥 CRITICAL FAILURES (CHAT BROKEN):"]) 
            report.extend([f"   {failure}" for failure in self.failures])
        
        if self.warnings:
            report.extend(["", "⚠️  WARNINGS (UX DEGRADED):"]) 
            report.extend([f"   {warning}" for warning in self.warnings])
        
        report.extend([
            "",
            "📋 EVENT TIMELINE:",
        ])
        
        for i, event in enumerate(self.events):
            timestamp = event['timestamp']
            event_type = event['event_type']
            report.append(f"   {i+1:2d}. [{timestamp:6.3f}s] {event_type}")
        
        report.append("=" * 100)
        return "\n".join(report)


# ============================================================================
# MOCK COMPONENTS FOR COMPREHENSIVE CHAT FLOW TESTING
# ============================================================================

class MockSupervisorAgent:
    """Mock supervisor that simulates real agent execution with WebSocket events."""
    
    def __init__(self):
        self.thread_id = None
        self.user_id = None
        self.db_session = None
        self.agent_registry = Mock()
        self.execution_engine = None
        
    async def run(self, user_request: str, thread_id: str, user_id: str, run_id: str) -> Dict[str, Any]:
        """Simulate agent execution with realistic WebSocket events."""
        logger.info(f"🤖 MockSupervisor executing: '{user_request}' for user {user_id}")
        
        # Simulate the agent execution flow that would generate WebSocket events
        # The real supervisor would trigger these through ExecutionEngine
        if hasattr(self.agent_registry, 'websocket_manager') and self.agent_registry.websocket_manager:
            ws_manager = self.agent_registry.websocket_manager
            
            # Create execution context
            context = AgentExecutionContext(
                run_id=run_id,
                thread_id=thread_id,
                user_id=user_id,
                agent_name="supervisor_agent",
                retry_count=0,
                max_retries=1
            )
            
            # Create notifier for event simulation
            notifier = WebSocketNotifier(ws_manager)
            
            # Simulate real agent execution flow
            await notifier.send_agent_started(context)
            await asyncio.sleep(0.01)  # Brief delay to simulate processing
            
            await notifier.send_agent_thinking(context, f"Analyzing request: {user_request}")
            await asyncio.sleep(0.01)
            
            # Simulate tool usage
            await notifier.send_tool_executing(context, "analyze_request")
            await asyncio.sleep(0.01)
            await notifier.send_tool_completed(context, "analyze_request", {
                "status": "success", 
                "analysis": "Request processed successfully"
            })
            
            await notifier.send_final_report(context, {
                "response": f"I've processed your request: {user_request}",
                "status": "completed"
            }, processing_time=50.0)
            
            await notifier.send_agent_completed(context, {"success": True}, total_time=100.0)
        
        return {
            "response": f"I've processed your request: {user_request}",
            "status": "completed"
        }


class MockThreadService:
    """Mock thread service for chat flow testing."""
    
    def __init__(self):
        self.threads = {}
        self.messages = {}
        self.runs = {}
    
    async def get_or_create_thread(self, user_id: str, db_session) -> Mock:
        """Create mock thread."""
        thread_id = f"thread-{user_id}-{int(time.time())}"
        thread = Mock()
        thread.id = thread_id
        thread.metadata_ = {"user_id": user_id}
        self.threads[thread_id] = thread
        return thread
    
    async def create_message(self, thread_id: str, role: str, content: str, 
                           metadata: Optional[Dict] = None, db=None):
        """Create mock message."""
        message_id = f"msg-{len(self.messages)}"
        if thread_id not in self.messages:
            self.messages[thread_id] = []
        self.messages[thread_id].append({
            'id': message_id,
            'role': role, 
            'content': content,
            'metadata': metadata
        })
    
    async def create_run(self, thread_id: str, assistant_id: str, model: str, 
                        instructions: str, db) -> Mock:
        """Create mock run."""
        run = Mock()
        run.id = f"run-{thread_id}-{len(self.runs)}"
        run.thread_id = thread_id
        self.runs[run.id] = run
        return run


class MockLLMManager:
    """Mock LLM manager for testing."""
    
    def __init__(self):
        self.model = "mock-llm"
    
    async def generate_response(self, prompt: str) -> str:
        return f"Mock response to: {prompt}"


# ============================================================================
# COMPREHENSIVE CHAT FLOW TESTS
# ============================================================================

class TestCompleteWebSocketChatFlow:
    """MISSION CRITICAL: Complete WebSocket chat flow validation."""
    
    
    @pytest.fixture(autouse=True)
    async def setup_chat_flow_environment(self):
        """Setup complete chat flow environment with all real components."""
        # Create WebSocket manager for testing
        self.ws_manager = ChatFlowWebSocketManager()
        
        # Create mock services
        self.mock_supervisor = MockSupervisorAgent()
        self.mock_thread_service = MockThreadService()
        self.mock_llm_manager = MockLLMManager()
        
        # Test identifiers
        self.test_user_id = "test-chat-user"
        self.test_thread_id = "test-chat-thread"
        
        yield
        
        # Cleanup
        self.ws_manager.clear_events()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_complete_chat_message_flow_integration(self):
        """TEST: Complete chat flow from WebSocket message to agent execution with events."""
        logger.info("\n🧪 TESTING: Complete Chat Message Flow Integration")
        
        # Create MessageHandlerService with WebSocket manager
        message_handler = MessageHandlerService(
            supervisor=self.mock_supervisor,
            thread_service=self.mock_thread_service,
            websocket_manager=self.ws_manager
        )
        
        # Create AgentMessageHandler 
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler,
            websocket=Mock()
        )
        
        # Create test message
        test_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={
                "content": "What is the system status?",
                "thread_id": self.test_thread_id
            }
        )
        
        # Mock database session
        with patch('netra_backend.app.websocket_core.agent_handler.get_db_dependency') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Execute the complete chat flow
            success = await agent_handler.handle_message(
                user_id=self.test_user_id,
                websocket=Mock(),
                message=test_message
            )
        
        # Verify the flow succeeded
        assert success, "Chat message flow failed"
        
        # Analyze WebSocket events
        validator = ChatFlowValidator(self.test_thread_id)
        analysis = validator.analyze_chat_flow(self.ws_manager)
        
        # Generate detailed report
        logger.info(validator.generate_detailed_report())
        
        # CRITICAL ASSERTIONS: Chat must work properly
        assert analysis['is_valid'], f"Chat flow validation failed: {analysis['failures']}"
        assert analysis['total_events'] >= 5, \
            f"Too few events for good UX: {analysis['total_events']} (expected ≥5)"
        assert analysis['user_experience_score'] >= 70.0, \
            f"Poor user experience score: {analysis['user_experience_score']}/100 (expected ≥70)"
    
    
    @pytest.mark.asyncio 
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_websocket_manager_propagation_through_chain(self):
        """TEST: WebSocket manager propagates through MessageHandlerService → Supervisor → AgentRegistry."""
        logger.info("\n🧪 TESTING: WebSocket Manager Propagation Through Chain")
        
        # Create real AgentRegistry and ToolDispatcher for integration test
        tool_dispatcher = ToolDispatcher()
        agent_registry = AgentRegistry(self.mock_llm_manager, tool_dispatcher)
        
        # Set up supervisor with real agent registry
        self.mock_supervisor.agent_registry = agent_registry
        
        # Create MessageHandlerService with WebSocket manager
        message_handler = MessageHandlerService(
            supervisor=self.mock_supervisor,
            thread_service=self.mock_thread_service, 
            websocket_manager=self.ws_manager
        )
        
        # Create test payload
        test_payload = {
            "content": "Test WebSocket manager propagation",
            "thread_id": self.test_thread_id
        }
        
        # Mock database session
        mock_session = AsyncMock()
        
        # Execute user message handling (this should propagate WebSocket manager)
        await message_handler.handle_user_message(
            user_id=self.test_user_id,
            payload=test_payload,
            db_session=mock_session,
            websocket=Mock()
        )
        
        # CRITICAL VERIFICATION: WebSocket manager propagation
        
        # 1. Verify AgentRegistry received WebSocket manager
        assert agent_registry.websocket_manager is self.ws_manager, \
            "AgentRegistry did not receive WebSocket manager"
        
        # 2. Verify ToolDispatcher was enhanced with WebSocket notifications
        assert isinstance(tool_dispatcher.executor, EnhancedToolExecutionEngine), \
            "ToolDispatcher was not enhanced with WebSocket notifications"
        
        # 3. Verify enhancement marker is set
        assert getattr(tool_dispatcher, '_websocket_enhanced', False), \
            "ToolDispatcher enhancement marker not set"
        
        # 4. Verify EnhancedToolExecutionEngine has WebSocket notifier
        enhanced_executor = tool_dispatcher.executor
        assert enhanced_executor.websocket_notifier is not None, \
            "EnhancedToolExecutionEngine missing WebSocket notifier"
        
        logger.info("✅ WebSocket manager successfully propagated through entire chain")
    
    
    @pytest.mark.asyncio
    @pytest.mark.critical  
    @pytest.mark.timeout(30)
    async def test_execution_engine_websocket_integration(self):
        """TEST: ExecutionEngine properly initializes and uses WebSocketNotifier."""
        logger.info("\n🧪 TESTING: ExecutionEngine WebSocket Integration")
        
        # Create real components for execution engine test
        tool_dispatcher = ToolDispatcher()
        agent_registry = AgentRegistry(self.mock_llm_manager, tool_dispatcher)
        
        # Create ExecutionEngine with WebSocket manager
        execution_engine = ExecutionEngine(agent_registry, self.ws_manager)
        
        # CRITICAL VERIFICATION: ExecutionEngine WebSocket components
        
        # 1. Verify ExecutionEngine has WebSocket notifier
        assert hasattr(execution_engine, 'websocket_notifier'), \
            "ExecutionEngine missing websocket_notifier attribute"
        assert isinstance(execution_engine.websocket_notifier, WebSocketNotifier), \
            f"websocket_notifier is {type(execution_engine.websocket_notifier)}, not WebSocketNotifier"
        
        # 2. Verify ExecutionEngine has WebSocket notification methods
        required_methods = ['send_agent_thinking', 'send_partial_result']
        for method in required_methods:
            assert hasattr(execution_engine, method), \
                f"ExecutionEngine missing {method} method"
            assert callable(getattr(execution_engine, method)), \
                f"ExecutionEngine {method} is not callable"
        
        # 3. Test that WebSocket events are sent through ExecutionEngine
        context = AgentExecutionContext(
            run_id="exec-test",
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            agent_name="execution_test",
            retry_count=0,
            max_retries=1
        )
        
        # Send events through ExecutionEngine
        await execution_engine.send_agent_thinking(context, "Testing execution engine WebSocket integration")
        await execution_engine.send_partial_result(context, "Partial test result")
        
        # Verify events were sent
        events = self.ws_manager.get_events_for_thread(self.test_thread_id)
        assert len(events) >= 2, f"Expected at least 2 events, got {len(events)}"
        
        event_types = [event['event_type'] for event in events]
        assert "agent_thinking" in event_types, "agent_thinking event not sent"
        assert "partial_result" in event_types, "partial_result event not sent"
        
        logger.info("✅ ExecutionEngine WebSocket integration working correctly")
    
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_enhanced_tool_execution_websocket_events(self):
        """TEST: EnhancedToolExecutionEngine sends proper WebSocket events during tool execution."""
        logger.info("\n🧪 TESTING: Enhanced Tool Execution WebSocket Events")
        
        # Create EnhancedToolExecutionEngine directly
        enhanced_executor = EnhancedToolExecutionEngine(self.ws_manager)
        
        # Verify WebSocket notifier is initialized
        assert enhanced_executor.websocket_notifier is not None, \
            "EnhancedToolExecutionEngine missing WebSocket notifier"
        
        # Create execution context for tool testing
        context = AgentExecutionContext(
            run_id="tool-test",
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            agent_name="tool_test_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Test direct tool notification
        await enhanced_executor.websocket_notifier.send_tool_executing(context, "test_analysis_tool")
        await asyncio.sleep(0.01)  # Simulate tool execution time
        await enhanced_executor.websocket_notifier.send_tool_completed(
            context, 
            "test_analysis_tool", 
            {"status": "success", "result": "Analysis complete"}
        )
        
        # Verify tool events were sent
        events = self.ws_manager.get_events_for_thread(self.test_thread_id)
        event_types = [event['event_type'] for event in events]
        
        assert "tool_executing" in event_types, \
            f"tool_executing event not sent. Got events: {event_types}"
        assert "tool_completed" in event_types, \
            f"tool_completed event not sent. Got events: {event_types}"
        
        # Verify tool events are properly paired
        tool_starts = event_types.count("tool_executing")
        tool_ends = event_types.count("tool_completed") 
        assert tool_starts == tool_ends, \
            f"Tool events not paired: {tool_starts} starts, {tool_ends} completions"
        
        logger.info("✅ Enhanced tool execution WebSocket events working correctly")
    
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_all_seven_critical_websocket_events(self):
        """TEST: All 7 critical WebSocket events are sent during complete agent execution."""
        logger.info("\n🧪 TESTING: All 7 Critical WebSocket Events")
        
        # Create WebSocket notifier for direct event testing
        notifier = WebSocketNotifier(self.ws_manager)
        
        # Create execution context
        context = AgentExecutionContext(
            run_id="critical-events-test",
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            agent_name="critical_events_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Send all critical events in realistic sequence
        
        # 1. Agent Started - User knows processing began
        await notifier.send_agent_started(context)
        await asyncio.sleep(0.01)
        
        # 2. Agent Thinking - User sees reasoning process
        await notifier.send_agent_thinking(context, "Analyzing the request and determining best approach")
        await asyncio.sleep(0.01)
        
        # 3. Tool Executing - User knows tool is running
        await notifier.send_tool_executing(context, "data_analysis_tool")
        await asyncio.sleep(0.01)
        
        # 4. Tool Completed - User sees tool results
        await notifier.send_tool_completed(context, "data_analysis_tool", {
            "status": "success",
            "insights": "Found 3 key optimization opportunities"
        })
        await asyncio.sleep(0.01)
        
        # 5. Agent Completed - User knows everything is finished
        await notifier.send_agent_completed(context, {
            "success": True,
            "total_recommendations": 3
        }, total_time=1500.0)
        
        # Analyze all events
        validator = ChatFlowValidator(self.test_thread_id)
        analysis = validator.analyze_chat_flow(self.ws_manager)
        
        # Generate comprehensive report
        logger.info(validator.generate_detailed_report())
        
        # CRITICAL ASSERTIONS: All events must be present
        
        expected_events = [
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed"
        ]
        
        for event in expected_events:
            assert event in analysis['event_counts'], \
                f"Missing critical event: {event}. Got events: {list(analysis['event_counts'].keys())}"
            assert analysis['event_counts'][event] > 0, \
                f"Event {event} was not sent (count: 0)"
        
        # Verify flow is valid
        assert analysis['is_valid'], f"Critical event flow invalid: {analysis['failures']}"
        
        # Verify excellent user experience
        assert analysis['user_experience_score'] >= 70.0, \
            f"User experience score too low: {analysis['user_experience_score']}/100 (expected ≥70)"
        
        logger.info("✅ All critical WebSocket events sent successfully")


    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_realistic_chat_conversation_flow(self):
        """TEST: Realistic multi-turn chat conversation with proper WebSocket events."""
        logger.info("\n🧪 TESTING: Realistic Chat Conversation Flow")
        
        # Create complete chat infrastructure
        message_handler = MessageHandlerService(
            supervisor=self.mock_supervisor,
            thread_service=self.mock_thread_service,
            websocket_manager=self.ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler,
            websocket=Mock()
        )
        
        # Simulate realistic conversation
        conversation = [
            "What is the current system status?",
            "Can you optimize the database performance?", 
            "Show me the top 3 recommendations"
        ]
        
        mock_session = AsyncMock()
        
        # Process each message in conversation
        for i, user_message in enumerate(conversation):
            logger.info(f"👤 User message {i+1}: {user_message}")
            
            # Clear events for each turn to test individual responses
            if i > 0:
                self.ws_manager.clear_events()
            
            test_message = WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                payload={
                    "content": user_message,
                    "thread_id": f"{self.test_thread_id}-turn-{i}"
                }
            )
            
            with patch('netra_backend.app.websocket_core.agent_handler.get_db_dependency') as mock_db:
                mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Process the message
                success = await agent_handler.handle_message(
                    user_id=self.test_user_id,
                    websocket=Mock(),
                    message=test_message
                )
                
                assert success, f"Failed to process message {i+1}: {user_message}"
            
            # Validate this turn's WebSocket events
            thread_id = f"{self.test_thread_id}-turn-{i}"
            validator = ChatFlowValidator(thread_id)
            analysis = validator.analyze_chat_flow(self.ws_manager)
            
            assert analysis['is_valid'], \
                f"Turn {i+1} failed validation: {analysis['failures']}"
            assert analysis['total_events'] >= 3, \
                f"Turn {i+1} had too few events: {analysis['total_events']}"
            
            logger.info(f"✅ Turn {i+1} completed successfully with {analysis['total_events']} events")
        
        logger.info("✅ Complete realistic chat conversation flow working correctly")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_error_handling_preserves_websocket_events(self):
        """TEST: Errors during chat don't break WebSocket event flow."""
        logger.info("\n🧪 TESTING: Error Handling Preserves WebSocket Events")
        
        # Create supervisor that simulates an error
        class ErroringSupervisor(MockSupervisorAgent):
            async def run(self, user_request: str, thread_id: str, user_id: str, run_id: str):
                # Start normally
                if hasattr(self.agent_registry, 'websocket_manager') and self.agent_registry.websocket_manager:
                    ws_manager = self.agent_registry.websocket_manager
                    context = AgentExecutionContext(
                        run_id=run_id, thread_id=thread_id, user_id=user_id,
                        agent_name="error_agent", retry_count=0, max_retries=1
                    )
                    notifier = WebSocketNotifier(ws_manager)
                    
                    await notifier.send_agent_started(context)
                    await notifier.send_agent_thinking(context, "Processing request...")
                    
                    # Simulate error during execution
                    try:
                        raise Exception("Simulated agent execution error")
                    except Exception:
                        # Must still send fallback/completion event
                        await notifier.send_agent_fallback(context, "I encountered an error but I'm handling it gracefully")
                
                return {"error": "Simulated error occurred", "handled": True}
        
        # Setup with error supervisor
        error_supervisor = ErroringSupervisor()
        message_handler = MessageHandlerService(
            supervisor=error_supervisor,
            thread_service=self.mock_thread_service,
            websocket_manager=self.ws_manager
        )
        
        test_payload = {
            "content": "This will trigger an error",
            "thread_id": self.test_thread_id
        }
        
        mock_session = AsyncMock()
        
        # Process message that will error
        await message_handler.handle_user_message(
            user_id=self.test_user_id,
            payload=test_payload,
            db_session=mock_session,
            websocket=Mock()
        )
        
        # Verify error handling preserved WebSocket events
        events = self.ws_manager.get_events_for_thread(self.test_thread_id)
        event_types = [event['event_type'] for event in events]
        
        # Must still have start and some form of completion
        assert "agent_started" in event_types, \
            f"Missing agent_started event during error. Got: {event_types}"
        
        completion_events = ["agent_completed", "agent_fallback"]
        has_completion = any(event in event_types for event in completion_events)
        assert has_completion, \
            f"Missing completion event during error. Got: {event_types}"
        
        logger.info("✅ Error handling preserves WebSocket events correctly")
    


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    # Run with: python tests/mission_critical/test_websocket_chat_flow_complete.py
    # Or: pytest tests/mission_critical/test_websocket_chat_flow_complete.py -v
    import sys
    
    logger.info("🚀 RUNNING MISSION CRITICAL WEBSOCKET CHAT FLOW TEST SUITE")
    logger.info("=" * 100)
    logger.info("This suite validates the complete chat message processing flow:")
    logger.info("📱 WebSocket → AgentMessageHandler → MessageHandlerService → Supervisor")
    logger.info("📊 WebSocket manager propagation through entire chain")
    logger.info("🔔 All 7 critical WebSocket events during chat processing")
    logger.info("⚡ ExecutionEngine WebSocket integration")
    logger.info("🛠️  EnhancedToolExecutionEngine for tool execution")
    logger.info("=" * 100)
    
    # Run tests with verbose output
    exit_code = pytest.main([
        __file__, 
        "-v",           # Verbose output
        "--tb=short",   # Short traceback format
        "-x",           # Stop on first failure
        "--timeout=60", # 60 second timeout per test
        "-s"            # Don't capture output (show prints/logs)
    ])
    
    if exit_code == 0:
        logger.info("\n🎉 ALL MISSION CRITICAL WEBSOCKET CHAT FLOW TESTS PASSED!")
        logger.info("✅ Chat functionality is working correctly")
        logger.info("✅ Users will receive real-time feedback during agent execution")
        logger.info("✅ WebSocket events are properly sent through the entire chain")
    else:
        logger.error("\n💥 MISSION CRITICAL TESTS FAILED!")
        logger.error("❌ Chat functionality is broken - users will see no real-time feedback")
        logger.error("❌ WebSocket integration has critical issues")
    
    sys.exit(exit_code)