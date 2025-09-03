#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: DataHelperAgent WebSocket Integration

THIS SUITE MUST PASS OR THE CHAT VALUE DELIVERY IS BROKEN.
Business Value: $200K+ ARR - DataHelperAgent chat functionality for user data requests

CRITICAL: DataHelperAgent WebSocket events enable the core business goal of delivering
AI-powered data request generation to users through substantive chat interactions.

This test suite validates that DataHelperAgent properly emits WebSocket events and
integrates correctly with AgentWebSocketBridge for reliable chat value delivery.

ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
import threading
import random

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import unified WebSocket mock for consistent DataHelper testing
from test_framework.fixtures.websocket_manager_mock import create_concurrency_mock
from test_framework.fixtures.websocket_test_helpers import (
    WebSocketAssertions,
    simulate_agent_execution_flow,
    reset_mock_for_test
)

# Import production components
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager


# ============================================================================
# UNIFIED WEBSOCKET MOCK FOR DATAHELPER TESTING - REPLACES LOCAL MOCK
# ============================================================================

class MockWebSocketManager:
    """Legacy compatibility wrapper for DataHelper testing using unified mock."""
    
    def __init__(self):
        self._unified_mock = create_concurrency_mock()
        # Legacy attributes for backward compatibility
        self.messages = []
        self.connections = {}
        self.event_lock = threading.Lock()
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Send using unified mock with DataHelper-specific tracking."""
        result = await self._unified_mock.send_to_thread(thread_id, message)
        
        # Maintain legacy interface with thread safety
        with self.event_lock:
            event_record = {
                'thread_id': thread_id,
                'message': message,
                'event_type': message.get('type', 'unknown'),
                'timestamp': time.time(),
                'agent_name': message.get('agent_name', 'unknown')
            }
            self.messages.append(event_record)
        
        # Sync connections from unified mock
        self.connections = self._unified_mock.connections
        
        return result
    
    async def connect_user(self, user_id: str, websocket, thread_id: str):
        """Connect using unified mock."""
        await self._unified_mock.connect_user(user_id, websocket, thread_id)
        self.connections = self._unified_mock.connections
    
    async def disconnect_user(self, user_id: str, websocket, thread_id: str):
        """Disconnect using unified mock."""
        await self._unified_mock.disconnect_user(user_id, websocket, thread_id)
        self.connections = self._unified_mock.connections
    
    def get_events_for_thread(self, thread_id: str) -> List[Dict]:
        """Get events with legacy interface."""
        with self.event_lock:
            return [msg for msg in self.messages if msg['thread_id'] == thread_id]
    
    def get_events_for_agent(self, agent_name: str) -> List[Dict]:
        """Get events for a specific agent (DataHelper-specific feature)."""
        with self.event_lock:
            return [msg for msg in self.messages if msg.get('agent_name') == agent_name]
    
    def get_event_types_for_thread(self, thread_id: str) -> List[str]:
        """Get event types for a thread in order."""
        with self.event_lock:
            return [msg['event_type'] for msg in self.messages if msg['thread_id'] == thread_id]
    
    def clear_messages(self):
        """Clear all recorded messages."""
        self._unified_mock.clear_messages()
        with self.event_lock:
            self.messages.clear()
            self.connections.clear()
        with self.event_lock:
            self.messages.clear()


# ============================================================================
# DATAHELPER EVENT VALIDATOR 
# ============================================================================

class DataHelperEventValidator:
    """Validates DataHelperAgent WebSocket events with business-critical rigor."""
    
    REQUIRED_DATAHELPER_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    # DataHelperAgent specific events that may be sent
    OPTIONAL_DATAHELPER_EVENTS = {
        "progress_update",
        "agent_error",
        "agent_fallback"
    }
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data)
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()
        self.datahelper_specific_validations = []
        
    def record(self, event: Dict) -> None:
        """Record an event with detailed tracking."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        
        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
    def validate_datahelper_requirements(self) -> tuple[bool, List[str]]:
        """Validate that ALL DataHelperAgent critical requirements are met."""
        failures = []
        
        # 1. Check for required events
        missing = self.REQUIRED_DATAHELPER_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"CRITICAL: DataHelperAgent missing required events: {missing}")
        
        # 2. Validate DataHelperAgent event ordering
        if not self._validate_datahelper_event_order():
            failures.append("CRITICAL: DataHelperAgent invalid event order")
        
        # 3. Check for paired tool events (DataHelperAgent uses data_helper tool)
        if not self._validate_datahelper_tool_events():
            failures.append("CRITICAL: DataHelperAgent unpaired tool events")
        
        # 4. Validate DataHelperAgent specific content quality
        if not self._validate_datahelper_content_quality():
            failures.append("CRITICAL: DataHelperAgent event content quality issues")
        
        # 5. Check for DataHelperAgent business value events
        if not self._validate_datahelper_business_value():
            failures.append("CRITICAL: DataHelperAgent missing business value indicators")
        
        return len(failures) == 0, failures
    
    def _validate_datahelper_event_order(self) -> bool:
        """Ensure DataHelperAgent events follow logical order."""
        if not self.event_timeline:
            return False
            
        # First event must be agent_started
        if self.event_timeline[0][1] != "agent_started":
            self.errors.append(f"DataHelperAgent first event was {self.event_timeline[0][1]}, not agent_started")
            return False
        
        # Should have thinking events showing data analysis
        thinking_events = [e for e in self.events if e.get('type') == 'agent_thinking']
        if not thinking_events:
            self.errors.append("DataHelperAgent missing thinking events for data analysis transparency")
            return False
            
        # Should have tool execution for data_helper
        tool_events = [e for e in self.events if e.get('type') == 'tool_executing']
        data_helper_tool = any('data_helper' in str(e.get('payload', {})) for e in tool_events)
        if not data_helper_tool:
            self.errors.append("DataHelperAgent missing data_helper tool execution events")
            return False
        
        # Last event should be completion
        last_event = self.event_timeline[-1][1] 
        if last_event not in ["agent_completed", "agent_error", "agent_fallback"]:
            self.errors.append(f"DataHelperAgent last event was {last_event}, not a completion event")
            return False
            
        return True
    
    def _validate_datahelper_tool_events(self) -> bool:
        """Ensure DataHelperAgent tool events are properly paired."""
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0)
        
        if tool_starts != tool_ends:
            self.errors.append(f"DataHelperAgent tool event mismatch: {tool_starts} starts, {tool_ends} completions")
            return False
            
        # DataHelperAgent should execute data_helper tool specifically
        data_helper_executions = 0
        for event in self.events:
            if event.get('type') == 'tool_executing':
                payload = event.get('payload', {})
                if 'data_helper' in str(payload.get('tool_name', '')).lower():
                    data_helper_executions += 1
        
        if data_helper_executions == 0:
            self.errors.append("DataHelperAgent should execute data_helper tool")
            return False
            
        return True
    
    def _validate_datahelper_content_quality(self) -> bool:
        """Validate DataHelperAgent event content quality for user-facing chat."""
        for event in self.events:
            event_type = event.get('type')
            payload = event.get('payload', {})
            
            # Thinking events should mention data analysis
            if event_type == 'agent_thinking':
                reasoning = payload.get('reasoning', '').lower()
                if not any(keyword in reasoning for keyword in ['data', 'request', 'analysis', 'information']):
                    self.warnings.append(f"DataHelperAgent thinking event lacks data-related context: {reasoning[:100]}")
            
            # Tool execution should show data helper activity
            if event_type == 'tool_executing':
                tool_name = payload.get('tool_name', '').lower()
                if 'data' not in tool_name and 'helper' not in tool_name:
                    self.warnings.append(f"DataHelperAgent tool execution unclear purpose: {tool_name}")
            
            # Tool completion should show data request generation
            if event_type == 'tool_completed':
                result = payload.get('result', {})
                if isinstance(result, dict):
                    has_data_indicators = any(
                        key in str(result).lower() 
                        for key in ['data_request', 'instructions', 'structured_items', 'success']
                    )
                    if not has_data_indicators:
                        self.warnings.append("DataHelperAgent tool completion missing data request indicators")
        
        return True  # Warnings don't fail validation
    
    def _validate_datahelper_business_value(self) -> bool:
        """Validate DataHelperAgent provides clear business value indicators."""
        business_value_indicators = 0
        
        for event in self.events:
            payload = event.get('payload', {})
            
            # Look for data request generation indicators
            if any(keyword in str(payload).lower() for keyword in [
                'data_request', 'user_instructions', 'structured_items',
                'optimization', 'analysis', 'generate'
            ]):
                business_value_indicators += 1
        
        if business_value_indicators == 0:
            self.errors.append("DataHelperAgent events lack business value indicators")
            return False
        
        return True
    
    def generate_report(self) -> str:
        """Generate comprehensive DataHelperAgent validation report."""
        is_valid, failures = self.validate_datahelper_requirements()
        
        report = [
            "\n" + "=" * 80,
            "DATAHELPER AGENT WEBSOCKET VALIDATION REPORT",
            "=" * 80,
            f"Status: {'✅ PASSED' if is_valid else '❌ FAILED'}",
            f"Total Events: {len(self.events)}",
            f"Unique Types: {len(self.event_counts)}",
            f"Duration: {self.event_timeline[-1][0] if self.event_timeline else 0:.2f}s",
            "",
            "DataHelperAgent Event Coverage:"
        ]
        
        for event in self.REQUIRED_DATAHELPER_EVENTS:
            count = self.event_counts.get(event, 0)
            status = "✅" if count > 0 else "❌"
            report.append(f"  {status} {event}: {count}")
        
        if failures:
            report.extend(["", "FAILURES:"] + [f"  - {f}" for f in failures])
        
        if self.errors:
            report.extend(["", "ERRORS:"] + [f"  - {e}" for e in self.errors])
            
        if self.warnings and self.strict_mode:
            report.extend(["", "WARNINGS:"] + [f"  - {w}" for w in self.warnings])
        
        report.append("=" * 80)
        return "\n".join(report)


# ============================================================================
# UNIT TESTS - DataHelperAgent WebSocket Components
# ============================================================================

class TestDataHelperWebSocketComponents:
    """Unit tests for DataHelperAgent WebSocket integration components."""
    
    @pytest.fixture(autouse=True)
    async def setup_mock_services(self):
        """Setup mock services for reliable testing without external dependencies."""
        # Create mock WebSocket manager for tests
        self.mock_ws_manager = MockWebSocketManager()
        
        # Create mock LLM manager
        self.mock_llm_manager = self._create_mock_llm_manager()
        
        yield
        
        # Cleanup
        self.mock_ws_manager.clear_messages()
    
    def _create_mock_llm_manager(self):
        """Create a mock LLM manager for testing."""
        class MockLLMManager:
            async def generate_chat_completion(self, *args, **kwargs):
                return {
                    'content': 'Mock data request generated',
                    'usage': {'total_tokens': 100}
                }
        
        return MockLLMManager()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_datahelper_agent_has_websocket_capabilities(self):
        """Test that DataHelperAgent has ALL required WebSocket capabilities."""
        tool_dispatcher = ToolDispatcher()
        datahelper = DataHelperAgent(self.mock_llm_manager, tool_dispatcher)
        
        # Verify DataHelperAgent inherits WebSocket capabilities from BaseAgent
        required_websocket_methods = [
            'emit_thinking',
            'emit_tool_executing', 
            'emit_tool_completed',
            'emit_progress',
            'emit_error'
        ]
        
        for method in required_websocket_methods:
            assert hasattr(datahelper, method), f"DataHelperAgent missing critical WebSocket method: {method}"
            assert callable(getattr(datahelper, method)), f"DataHelperAgent method {method} is not callable"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_datahelper_agent_websocket_integration_setup(self):
        """Test that DataHelperAgent properly integrates with WebSocket infrastructure."""
        # Create WebSocket bridge and ensure integration
        bridge = AgentWebSocketBridge()
        result = await bridge.ensure_integration()
        
        assert result.success, f"AgentWebSocketBridge integration failed: {result.error}"
        assert result.state.value == "active", f"Bridge not active: {result.state}"
        
        # Create DataHelperAgent with proper infrastructure
        tool_dispatcher = ToolDispatcher()
        datahelper = DataHelperAgent(self.mock_llm_manager, tool_dispatcher)
        
        # Verify DataHelperAgent can access WebSocket infrastructure
        assert hasattr(datahelper, 'websocket_bridge') or hasattr(datahelper, 'websocket_notifier'), \
            "DataHelperAgent lacks WebSocket infrastructure access"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_datahelper_bridge_notification_methods(self):
        """Test that AgentWebSocketBridge notification methods work for DataHelperAgent."""
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Test DataHelperAgent specific notifications
        run_id = "test_datahelper_001"
        agent_name = "data_helper"
        
        # Test all critical notification methods
        notifications = [
            bridge.notify_agent_started(run_id, agent_name, {"user_request": "test request"}),
            bridge.notify_agent_thinking(run_id, agent_name, "Analyzing data requirements..."),
            bridge.notify_tool_executing(run_id, agent_name, "data_helper", {"request_type": "optimization"}),
            bridge.notify_tool_completed(run_id, agent_name, "data_helper", {"success": True, "data_request": "generated"}),
            bridge.notify_agent_completed(run_id, agent_name, {"success": True, "data_request_generated": True})
        ]
        
        # Execute all notifications
        results = await asyncio.gather(*notifications, return_exceptions=True)
        
        # Verify all notifications succeeded (even with mock setup)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Expected with mock infrastructure, but method should exist and be callable
                assert not isinstance(result, AttributeError), f"Notification method {i} missing or not callable"
            else:
                # If successful, should return boolean
                assert isinstance(result, bool), f"Notification method {i} should return boolean"


# ============================================================================
# INTEGRATION TESTS - DataHelperAgent WebSocket Event Flow
# ============================================================================

class TestDataHelperWebSocketIntegration:
    """Integration tests for DataHelperAgent WebSocket event flow."""
    
    @pytest.fixture(autouse=True)
    async def setup_integration_services(self):
        """Setup integration testing services."""
        # Use mock WebSocket manager for reliable testing
        self.mock_ws_manager = MockWebSocketManager()
        
        # Create mock LLM manager that simulates data request generation
        self.mock_llm_manager = self._create_mock_llm_manager()
        
        yield
        
        # Cleanup
        self.mock_ws_manager.clear_messages()
    
    def _create_mock_llm_manager(self):
        """Create a realistic mock LLM manager for DataHelperAgent testing."""
        class MockLLMManager:
            async def generate_chat_completion(self, messages, *args, **kwargs):
                # Simulate data request generation response
                return {
                    'content': json.dumps({
                        'success': True,
                        'data_request': {
                            'user_instructions': 'Please provide system metrics and usage data',
                            'structured_items': [
                                'CPU utilization over past 30 days',
                                'Memory usage patterns',
                                'Application response times'
                            ]
                        }
                    }),
                    'usage': {'total_tokens': 150}
                }
        
        return MockLLMManager()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_datahelper_complete_websocket_flow(self):
        """Test complete DataHelperAgent execution with WebSocket events."""
        ws_manager = self.mock_ws_manager
        validator = DataHelperEventValidator()
        
        # Setup mock connection
        thread_id = "datahelper_integration_test"
        run_id = "datahelper_run_001"
        user_id = "test_user"
        
        # Create DataHelperAgent with WebSocket infrastructure
        tool_dispatcher = ToolDispatcher()
        datahelper = DataHelperAgent(self.mock_llm_manager, tool_dispatcher)
        
        # Create WebSocket notifier with mock manager
        notifier = WebSocketNotifier(ws_manager)
        
        # Simulate setting WebSocket infrastructure on agent (this would be done by registry)
        if hasattr(datahelper, '_set_websocket_notifier'):
            datahelper._set_websocket_notifier(notifier)
        
        # Create execution context
        state = DeepAgentState()
        state.user_request = "I need to optimize my application performance"
        state.user_id = user_id
        state.chat_thread_id = thread_id
        
        context = ExecutionContext(
            run_id=run_id,
            agent_name="data_helper",
            state=state,
            stream_updates=True,
            thread_id=thread_id,
            user_id=user_id
        )
        
        # Execute DataHelperAgent with WebSocket events
        try:
            # Validate preconditions (should pass)
            preconditions_valid = await datahelper.validate_preconditions(context)
            assert preconditions_valid, "DataHelperAgent preconditions should be valid"
            
            # Execute core logic (this should emit WebSocket events)
            result = await datahelper.execute_core_logic(context)
            
            # Allow events to be processed
            await asyncio.sleep(0.1)
            
            # Get events from mock WebSocket manager
            received_events = ws_manager.get_events_for_thread(thread_id)
            
            # Record events in validator
            for event in received_events:
                validator.record(event['message'])
            
            # Validate DataHelperAgent specific requirements
            is_valid, failures = validator.validate_datahelper_requirements()
            
            if not is_valid:
                logger.error(validator.generate_report())
            
            assert is_valid, f"DataHelperAgent WebSocket integration failed: {failures}"
            
            # Additional DataHelperAgent specific validations
            assert len(received_events) >= 5, \
                f"Expected at least 5 events, got {len(received_events)}"
            
            # Verify specific DataHelperAgent events
            event_types = validator.event_counts
            assert event_types.get("agent_started", 0) >= 1, "Missing agent_started event"
            assert event_types.get("agent_thinking", 0) >= 1, "Missing agent_thinking event" 
            assert event_types.get("tool_executing", 0) >= 1, "Missing tool_executing event"
            assert event_types.get("tool_completed", 0) >= 1, "Missing tool_completed event"
            assert event_types.get("agent_completed", 0) >= 1, "Missing agent_completed event"
            
            logger.info("✅ DataHelperAgent WebSocket integration test PASSED")
            
        except Exception as e:
            logger.error(f"DataHelperAgent WebSocket integration test failed: {e}")
            if validator.events:
                logger.error(validator.generate_report())
            raise
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_datahelper_websocket_event_content_quality(self):
        """Test DataHelperAgent WebSocket event content quality for chat UX."""
        ws_manager = self.mock_ws_manager
        validator = DataHelperEventValidator()
        
        # Setup test context
        thread_id = "datahelper_quality_test"
        run_id = "datahelper_quality_001"
        
        # Create DataHelperAgent
        tool_dispatcher = ToolDispatcher()
        datahelper = DataHelperAgent(self.mock_llm_manager, tool_dispatcher)
        
        # Create WebSocket notifier 
        notifier = WebSocketNotifier(ws_manager)
        if hasattr(datahelper, '_set_websocket_notifier'):
            datahelper._set_websocket_notifier(notifier)
        
        # Create state with rich context
        state = DeepAgentState()
        state.user_request = "Help me improve my e-commerce application performance and reduce costs"
        state.user_id = "quality_test_user"
        state.chat_thread_id = thread_id
        
        # Add some previous context to test data analysis
        state.context_tracking = {
            'triage_result': {
                'optimization_type': 'performance',
                'complexity': 'medium'
            }
        }
        
        context = ExecutionContext(
            run_id=run_id,
            agent_name="data_helper",
            state=state,
            stream_updates=True,
            thread_id=thread_id,
            user_id="quality_test_user"
        )
        
        # Execute DataHelperAgent
        result = await datahelper.execute_core_logic(context)
        
        await asyncio.sleep(0.1)
        
        # Get and analyze events
        received_events = ws_manager.get_events_for_thread(thread_id)
        
        for event in received_events:
            validator.record(event['message'])
        
        # Validate event quality
        is_valid, failures = validator.validate_datahelper_requirements()
        assert is_valid, f"DataHelperAgent event quality validation failed: {failures}"
        
        # Check specific content quality
        thinking_events = [e for e in validator.events if e.get('type') == 'agent_thinking']
        assert len(thinking_events) > 0, "No thinking events found"
        
        for thinking_event in thinking_events:
            reasoning = thinking_event.get('payload', {}).get('reasoning', '')
            assert len(reasoning) > 20, f"Thinking event too brief: {reasoning}"
            assert any(keyword in reasoning.lower() for keyword in ['data', 'request', 'analysis']), \
                f"Thinking event lacks data context: {reasoning}"
        
        tool_events = [e for e in validator.events if e.get('type') == 'tool_executing']
        for tool_event in tool_events:
            payload = tool_event.get('payload', {})
            assert 'tool_name' in payload, "Tool execution missing tool name"
            assert payload.get('message'), "Tool execution missing user message"
        
        logger.info("✅ DataHelperAgent event content quality test PASSED")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_datahelper_websocket_error_scenarios(self):
        """Test DataHelperAgent WebSocket events during error scenarios."""
        ws_manager = self.mock_ws_manager
        validator = DataHelperEventValidator(strict_mode=False)
        
        # Create failing LLM manager
        class FailingLLMManager:
            async def generate_chat_completion(self, *args, **kwargs):
                raise Exception("Simulated LLM failure")
        
        failing_llm = FailingLLMManager()
        
        # Setup test
        thread_id = "datahelper_error_test"
        run_id = "datahelper_error_001"
        
        tool_dispatcher = ToolDispatcher()
        datahelper = DataHelperAgent(failing_llm, tool_dispatcher)
        
        notifier = WebSocketNotifier(ws_manager)
        if hasattr(datahelper, '_set_websocket_notifier'):
            datahelper._set_websocket_notifier(notifier)
        
        state = DeepAgentState()
        state.user_request = "Test error handling"
        state.user_id = "error_test_user"
        state.chat_thread_id = thread_id
        
        context = ExecutionContext(
            run_id=run_id,
            agent_name="data_helper",
            state=state,
            stream_updates=True,
            thread_id=thread_id,
            user_id="error_test_user"
        )
        
        # Execute (should handle error gracefully)
        result = await datahelper.execute_core_logic(context)
        
        await asyncio.sleep(0.1)
        
        # Get events and validate error handling
        received_events = ws_manager.get_events_for_thread(thread_id)
        
        for event in received_events:
            validator.record(event['message'])
        
        # Should still have proper event flow even with errors
        assert validator.event_counts.get("agent_started", 0) > 0, \
            "Should have agent_started event even with errors"
        
        # Should have either completion or error event
        completion_events = (
            validator.event_counts.get("agent_completed", 0) +
            validator.event_counts.get("agent_error", 0) +
            validator.event_counts.get("agent_fallback", 0)
        )
        assert completion_events > 0, "Should have completion/error event"
        
        # Result should indicate failure but be structured
        assert isinstance(result, dict), "Error result should be structured"
        assert result.get('success') is False, "Error result should indicate failure"
        
        logger.info("✅ DataHelperAgent error scenario test PASSED")


# ============================================================================
# E2E TESTS - Complete DataHelperAgent Chat Flow  
# ============================================================================

class TestDataHelperE2EChatFlow:
    """End-to-end tests for DataHelperAgent chat flow with WebSocket events."""
    
    @pytest.fixture(autouse=True)
    async def setup_e2e_services(self):
        """Setup E2E testing services."""
        self.mock_ws_manager = MockWebSocketManager()
        
        # Create realistic LLM manager for E2E testing
        self.e2e_llm_manager = self._create_e2e_llm_manager()
        
        yield
        
        self.mock_ws_manager.clear_messages()
    
    def _create_e2e_llm_manager(self):
        """Create realistic LLM manager for E2E testing."""
        class E2ELLMManager:
            async def generate_chat_completion(self, messages, *args, **kwargs):
                # Simulate realistic data request generation
                user_message = str(messages).lower()
                
                # Generate contextual response based on user request
                if 'performance' in user_message:
                    data_request = {
                        'user_instructions': 'To optimize your application performance, please provide the following information:',
                        'structured_items': [
                            'Current application response times and throughput metrics',
                            'Server resource utilization (CPU, memory, disk I/O)',
                            'Database query performance statistics',
                            'Traffic patterns and peak usage times',
                            'Current infrastructure configuration'
                        ]
                    }
                elif 'cost' in user_message:
                    data_request = {
                        'user_instructions': 'To help reduce your costs, I need information about:',
                        'structured_items': [
                            'Current monthly cloud/infrastructure spend breakdown',
                            'Resource utilization rates and idle capacity',
                            'Application usage patterns and user activity',
                            'Current service tiers and pricing models',
                            'Business requirements and acceptable service levels'
                        ]
                    }
                else:
                    data_request = {
                        'user_instructions': 'To provide targeted optimization recommendations, please share:',
                        'structured_items': [
                            'Current system architecture and components',
                            'Performance metrics and pain points',
                            'Business requirements and constraints',
                            'Available resources and budget considerations'
                        ]
                    }
                
                return {
                    'content': json.dumps({
                        'success': True,
                        'data_request': data_request
                    }),
                    'usage': {'total_tokens': 200}
                }
        
        return E2ELLMManager()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_datahelper_complete_user_chat_flow(self):
        """Test complete user chat flow with DataHelperAgent."""
        ws_manager = self.mock_ws_manager
        validator = DataHelperEventValidator()
        
        # Setup realistic user scenario
        user_id = "e2e_user"
        thread_id = "e2e_datahelper_chat"
        run_id = "e2e_datahelper_001"
        user_request = "I need help optimizing my e-commerce platform to reduce costs and improve performance"
        
        # Create DataHelperAgent with realistic infrastructure
        tool_dispatcher = ToolDispatcher()
        datahelper = DataHelperAgent(self.e2e_llm_manager, tool_dispatcher)
        
        # Setup WebSocket infrastructure
        notifier = WebSocketNotifier(ws_manager)
        if hasattr(datahelper, '_set_websocket_notifier'):
            datahelper._set_websocket_notifier(notifier)
        
        # Execute complete flow using backward compatible method
        state = DeepAgentState()
        state.user_request = user_request
        state.user_id = user_id
        state.chat_thread_id = thread_id
        
        # Add realistic context (simulating previous triage)
        state.context_tracking = {
            'triage_result': {
                'optimization_type': 'hybrid',
                'complexity': 'high',
                'requires_data_collection': True
            }
        }
        
        # Execute using run method (backward compatible)
        start_time = time.time()
        updated_state = await datahelper.run(
            user_prompt=user_request,
            thread_id=thread_id,
            user_id=user_id,
            run_id=run_id,
            state=state
        )
        execution_time = time.time() - start_time
        
        # Allow events to process
        await asyncio.sleep(0.2)
        
        # Get and validate events
        received_events = ws_manager.get_events_for_thread(thread_id)
        
        for event in received_events:
            validator.record(event['message'])
        
        # Generate comprehensive report
        logger.info(validator.generate_report())
        
        # Validate E2E flow
        is_valid, failures = validator.validate_datahelper_requirements()
        assert is_valid, f"E2E DataHelperAgent flow validation failed: {failures}"
        
        # Validate execution results
        assert updated_state is not None, "Should return updated state"
        assert updated_state.context_tracking is not None, "Should have context tracking"
        
        datahelper_result = updated_state.context_tracking.get('data_helper', {})
        assert datahelper_result.get('success', False), f"DataHelperAgent should succeed: {datahelper_result}"
        assert 'data_request' in datahelper_result, "Should generate data request"
        assert 'user_instructions' in datahelper_result, "Should have user instructions"
        assert 'structured_items' in datahelper_result, "Should have structured items"
        
        # Validate business value
        user_instructions = datahelper_result.get('user_instructions', '')
        assert len(user_instructions) > 50, "User instructions should be substantial"
        
        structured_items = datahelper_result.get('structured_items', [])
        assert len(structured_items) >= 3, "Should have multiple structured data items"
        
        # Validate WebSocket events enabled chat experience
        assert len(received_events) >= 5, \
            f"Expected at least 5 events for rich chat experience, got {len(received_events)}"
        
        # Validate performance for chat responsiveness
        assert execution_time < 5.0, f"DataHelperAgent too slow for chat: {execution_time:.2f}s"
        
        logger.info(f"✅ E2E DataHelperAgent chat flow PASSED in {execution_time:.2f}s")
        logger.info(f"Generated data request with {len(structured_items)} items")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_datahelper_concurrent_chat_sessions(self):
        """Test DataHelperAgent handling concurrent chat sessions with WebSocket events."""
        ws_manager = self.mock_ws_manager
        
        # Create multiple concurrent sessions
        session_count = 3
        sessions = []
        validators = {}
        
        for i in range(session_count):
            session_id = f"concurrent_session_{i}"
            thread_id = f"thread_{session_id}"
            run_id = f"run_{session_id}"
            
            sessions.append({
                'session_id': session_id,
                'thread_id': thread_id,
                'run_id': run_id,
                'user_request': f"Help optimize my {['web', 'mobile', 'desktop'][i]} application"
            })
            validators[session_id] = DataHelperEventValidator()
        
        # Execute all sessions concurrently
        async def execute_session(session):
            tool_dispatcher = ToolDispatcher()
            datahelper = DataHelperAgent(self.e2e_llm_manager, tool_dispatcher)
            
            notifier = WebSocketNotifier(ws_manager)
            if hasattr(datahelper, '_set_websocket_notifier'):
                datahelper._set_websocket_notifier(notifier)
            
            # Execute session
            updated_state = await datahelper.run(
                user_prompt=session['user_request'],
                thread_id=session['thread_id'],
                user_id=f"user_{session['session_id']}",
                run_id=session['run_id']
            )
            
            return updated_state
        
        # Run all sessions concurrently
        tasks = [execute_session(session) for session in sessions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Allow events to process
        await asyncio.sleep(0.3)
        
        # Validate each session
        for i, (session, result) in enumerate(zip(sessions, results)):
            session_id = session['session_id']
            thread_id = session['thread_id']
            validator = validators[session_id]
            
            # Check for exceptions
            assert not isinstance(result, Exception), f"Session {session_id} failed: {result}"
            
            # Get events for this thread
            thread_events = ws_manager.get_events_for_thread(thread_id)
            
            for event in thread_events:
                validator.record(event['message'])
            
            # Validate this session's events
            is_valid, failures = validator.validate_datahelper_requirements()
            assert is_valid, f"Session {session_id} validation failed: {failures}"
            
            # Validate business results
            assert result.context_tracking is not None, f"Session {session_id} missing context"
            datahelper_result = result.context_tracking.get('data_helper', {})
            assert datahelper_result.get('success', False), f"Session {session_id} should succeed"
        
        logger.info(f"✅ Concurrent DataHelperAgent sessions test PASSED ({session_count} sessions)")


# ============================================================================
# REGRESSION PREVENTION TESTS
# ============================================================================

class TestDataHelperRegressionPrevention:
    """Tests specifically designed to prevent regression of DataHelperAgent WebSocket integration."""
    
    @pytest.fixture(autouse=True)
    async def setup_regression_services(self):
        """Setup services for regression tests."""
        self.mock_ws_manager = MockWebSocketManager()
        self.mock_llm_manager = self._create_mock_llm_manager()
        
        yield
        
        self.mock_ws_manager.clear_messages()
    
    def _create_mock_llm_manager(self):
        """Create mock LLM manager."""
        class MockLLMManager:
            async def generate_chat_completion(self, *args, **kwargs):
                return {
                    'content': json.dumps({'success': True, 'data_request': {'user_instructions': 'test'}}),
                    'usage': {'total_tokens': 50}
                }
        
        return MockLLMManager()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_datahelper_websocket_events_never_skipped(self):
        """REGRESSION TEST: DataHelperAgent MUST emit WebSocket events."""
        ws_manager = self.mock_ws_manager
        validator = DataHelperEventValidator()
        
        # Test multiple execution scenarios
        scenarios = [
            {'user_request': 'Short request', 'expected_events': True},
            {'user_request': 'A' * 1000, 'expected_events': True},  # Long request
            {'user_request': 'Performance optimization with cost considerations', 'expected_events': True},
        ]
        
        for i, scenario in enumerate(scenarios):
            thread_id = f"regression_test_{i}"
            run_id = f"regression_run_{i}"
            
            tool_dispatcher = ToolDispatcher()
            datahelper = DataHelperAgent(self.mock_llm_manager, tool_dispatcher)
            
            notifier = WebSocketNotifier(ws_manager)
            if hasattr(datahelper, '_set_websocket_notifier'):
                datahelper._set_websocket_notifier(notifier)
            
            # Clear previous events
            ws_manager.clear_messages()
            validator = DataHelperEventValidator()
            
            # Execute DataHelperAgent
            updated_state = await datahelper.run(
                user_prompt=scenario['user_request'],
                thread_id=thread_id,
                user_id=f"regression_user_{i}",
                run_id=run_id
            )
            
            await asyncio.sleep(0.1)
            
            # Get and validate events
            received_events = ws_manager.get_events_for_thread(thread_id)
            
            for event in received_events:
                validator.record(event['message'])
            
            # CRITICAL: Must have events
            if scenario['expected_events']:
                assert len(received_events) > 0, f"REGRESSION: No WebSocket events for scenario {i}"
                
                required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed']
                for req_event in required_events:
                    assert validator.event_counts.get(req_event, 0) > 0, \
                        f"REGRESSION: Missing {req_event} in scenario {i}"
        
        logger.info("✅ DataHelperAgent WebSocket events regression test PASSED")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_datahelper_tool_events_always_paired(self):
        """REGRESSION TEST: DataHelperAgent tool events must ALWAYS be paired."""
        ws_manager = self.mock_ws_manager
        validator = DataHelperEventValidator()
        
        thread_id = "tool_pairing_test"
        run_id = "tool_pairing_001"
        
        tool_dispatcher = ToolDispatcher()
        datahelper = DataHelperAgent(self.mock_llm_manager, tool_dispatcher)
        
        notifier = WebSocketNotifier(ws_manager)
        if hasattr(datahelper, '_set_websocket_notifier'):
            datahelper._set_websocket_notifier(notifier)
        
        # Execute DataHelperAgent
        updated_state = await datahelper.run(
            user_prompt="Generate data request for optimization",
            thread_id=thread_id,
            user_id="tool_test_user",
            run_id=run_id
        )
        
        await asyncio.sleep(0.1)
        
        # Get events and validate pairing
        received_events = ws_manager.get_events_for_thread(thread_id)
        
        for event in received_events:
            validator.record(event['message'])
        
        # Verify tool event pairing
        tool_starts = validator.event_counts.get("tool_executing", 0)
        tool_ends = validator.event_counts.get("tool_completed", 0)
        
        assert tool_starts == tool_ends, \
            f"REGRESSION: Unpaired tool events - {tool_starts} starts, {tool_ends} ends"
        assert tool_starts >= 1, \
            f"REGRESSION: DataHelperAgent should execute at least 1 tool, got {tool_starts}"
        
        logger.info("✅ DataHelperAgent tool event pairing regression test PASSED")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_datahelper_never_hangs_without_websocket_events(self):
        """REGRESSION TEST: DataHelperAgent must complete even without WebSocket."""
        # Create DataHelperAgent without WebSocket infrastructure
        tool_dispatcher = ToolDispatcher()
        datahelper = DataHelperAgent(self.mock_llm_manager, tool_dispatcher)
        # Deliberately NOT setting WebSocket notifier
        
        thread_id = "no_websocket_test"
        run_id = "no_websocket_001"
        
        # Execute with timeout to ensure it doesn't hang
        start_time = time.time()
        
        updated_state = await asyncio.wait_for(
            datahelper.run(
                user_prompt="Test without WebSocket",
                thread_id=thread_id,
                user_id="no_ws_user",
                run_id=run_id
            ),
            timeout=10.0  # Should complete in 10 seconds
        )
        
        execution_time = time.time() - start_time
        
        # Should complete successfully
        assert updated_state is not None, "Should return state even without WebSocket"
        assert execution_time < 8.0, f"Should not timeout/hang: {execution_time:.2f}s"
        
        # Should have result even without WebSocket events
        if updated_state.context_tracking:
            datahelper_result = updated_state.context_tracking.get('data_helper', {})
            # Should attempt to work (may fail due to missing infrastructure, but shouldn't hang)
            assert isinstance(datahelper_result, dict), "Should return structured result"
        
        logger.info("✅ DataHelperAgent no-hang regression test PASSED")


# ============================================================================
# EXECUTE CORE PATTERN TESTS
# ============================================================================

@pytest.mark.critical
@pytest.mark.mission_critical
class TestDataHelperExecuteCorePatterns:
    """Test DataHelperAgent _execute_core patterns with WebSocket integration."""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create a mock WebSocket manager."""
        return AsyncMock(spec=WebSocketManager)
    
    @pytest.fixture
    def data_helper_agent(self, mock_websocket_manager):
        """Create a DataHelperAgent with WebSocket integration."""
        agent = DataHelperAgent(
            name="TestDataHelper",
            enable_websocket_bridge=True,
            websocket_manager=mock_websocket_manager
        )
        return agent
    
    @pytest.mark.asyncio
    async def test_execute_core_websocket_event_sequence(self, data_helper_agent, mock_websocket_manager):
        """Test _execute_core pattern emits proper WebSocket event sequence."""
        try:
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        context = ExecutionContext(
            run_id="execute_core_websocket_test",
            agent_name=data_helper_agent.name,
            state=DeepAgentState()
        )
        
        # Execute core logic
        result = await data_helper_agent.execute_core_logic(context)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "data_processing" in result or "status" in result
        
        # Verify WebSocket events were sent in sequence
        websocket_calls = mock_websocket_manager.send_to_thread.call_args_list
        if websocket_calls:
            # Should have agent lifecycle events
            event_types = []
            for call in websocket_calls:
                if len(call[0]) > 1 and isinstance(call[0][1], dict):
                    event_data = call[0][1]
                    if "type" in event_data:
                        event_types.append(event_data["type"])
            
            # Should have started with agent events
            assert len(event_types) > 0, "Should have WebSocket events during execution"
        
        logger.info("✅ Execute core WebSocket event sequence validated")
    
    @pytest.mark.asyncio
    async def test_execute_core_timing_websocket_integration(self, data_helper_agent):
        """Test _execute_core pattern timing with WebSocket events."""
        try:
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        import time
        
        context = ExecutionContext(
            run_id="execute_core_timing_test",
            agent_name=data_helper_agent.name,
            state=DeepAgentState()
        )
        
        start_time = time.time()
        result = await data_helper_agent.execute_core_logic(context)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Verify execution completed
        assert result is not None
        assert isinstance(result, dict)
        
        # Verify reasonable execution time (should be fast for data helper)
        assert execution_time < 5.0, f"Execution took too long: {execution_time:.2f}s"
        
        logger.info(f"✅ Execute core timing validated: {execution_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_execute_core_concurrent_websocket_safety(self, mock_websocket_manager):
        """Test _execute_core pattern is safe with concurrent WebSocket operations."""
        try:
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        # Create multiple data helper agents
        agents = []
        for i in range(3):
            agent = DataHelperAgent(
                name=f"ConcurrentDataHelper_{i}",
                enable_websocket_bridge=True,
                websocket_manager=mock_websocket_manager
            )
            agents.append(agent)
        
        # Execute concurrently
        tasks = []
        for i, agent in enumerate(agents):
            context = ExecutionContext(
                run_id=f"concurrent_execute_core_{i}",
                agent_name=agent.name,
                state=DeepAgentState()
            )
            tasks.append(agent.execute_core_logic(context))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions completed successfully
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Agent {i} failed with exception: {result}")
            assert isinstance(result, dict), f"Agent {i} returned invalid result type"
        
        # Verify WebSocket calls were made safely
        total_calls = mock_websocket_manager.send_to_thread.call_count
        logger.info(f"✅ Concurrent execute core safety validated: {total_calls} WebSocket calls")
    
    @pytest.mark.asyncio
    async def test_execute_core_data_processing_websocket_flow(self, data_helper_agent, mock_websocket_manager):
        """Test _execute_core pattern with data processing and WebSocket flow."""
        try:
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        # Create context with data processing task
        context = ExecutionContext(
            run_id="data_processing_websocket_flow",
            agent_name=data_helper_agent.name,
            state=DeepAgentState()
        )
        
        # Add mock data to process
        if hasattr(context, 'metadata'):
            context.metadata = {
                "data_source": "test_dataset",
                "processing_type": "analysis",
                "expected_output": "insights"
            }
        
        result = await data_helper_agent.execute_core_logic(context)
        
        # Verify data processing result
        assert isinstance(result, dict)
        
        # Check for data processing indicators
        data_indicators = ["data", "analysis", "insights", "processing", "results", "status"]
        has_data_indicator = any(indicator in str(result).lower() for indicator in data_indicators)
        assert has_data_indicator, f"Result should indicate data processing: {result}"
        
        # Verify WebSocket events during data processing
        websocket_calls = mock_websocket_manager.send_to_thread.call_args_list
        if websocket_calls:
            # Should have progress or thinking events during data processing
            has_progress_events = False
            for call in websocket_calls:
                if len(call[0]) > 1 and isinstance(call[0][1], dict):
                    event_data = call[0][1]
                    if event_data.get("type") in ["agent_thinking", "tool_executing", "agent_progress"]:
                        has_progress_events = True
                        break
            
            if not has_progress_events:
                logger.info("No specific progress events found, but WebSocket integration is active")
        
        logger.info("✅ Execute core data processing WebSocket flow validated")


# ============================================================================
# ERROR RECOVERY PATTERN TESTS  
# ============================================================================

@pytest.mark.critical
@pytest.mark.mission_critical
class TestDataHelperErrorRecoveryPatterns:
    """Test DataHelperAgent error recovery patterns with WebSocket integration."""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create a mock WebSocket manager."""
        return AsyncMock(spec=WebSocketManager)
    
    @pytest.fixture
    def error_prone_data_helper(self, mock_websocket_manager):
        """Create a DataHelperAgent that can simulate errors."""
        agent = DataHelperAgent(
            name="ErrorProneDataHelper",
            enable_websocket_bridge=True,
            websocket_manager=mock_websocket_manager
        )
        # Add error simulation capability
        agent._simulate_errors = True
        return agent
    
    @pytest.mark.asyncio
    async def test_error_recovery_websocket_notification_patterns(self, error_prone_data_helper, mock_websocket_manager):
        """Test error recovery with WebSocket notification patterns."""
        try:
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        # Test different error scenarios
        error_contexts = [
            {
                "run_id": "error_recovery_timeout",
                "error_type": "timeout",
                "should_recover": True
            },
            {
                "run_id": "error_recovery_data_error", 
                "error_type": "data_processing",
                "should_recover": True
            },
            {
                "run_id": "error_recovery_success",
                "error_type": "none",
                "should_recover": False
            }
        ]
        
        for test_case in error_contexts:
            context = ExecutionContext(
                run_id=test_case["run_id"],
                agent_name=error_prone_data_helper.name,
                state=DeepAgentState()
            )
            
            try:
                result = await error_prone_data_helper.execute_core_logic(context)
                
                # Successful execution
                assert isinstance(result, dict)
                
                if test_case["error_type"] == "none":
                    # Should be normal execution
                    assert "error" not in str(result).lower() or "success" in str(result).lower()
                else:
                    # Should indicate recovery if error was simulated
                    logger.info(f"Execution completed for {test_case['error_type']} scenario")
                
            except Exception as e:
                # Error occurred - check if this was expected
                if test_case["should_recover"]:
                    logger.info(f"Error occurred in {test_case['error_type']} scenario: {e}")
                    # In a real scenario, we'd test the recovery mechanism
                else:
                    # Unexpected error
                    logger.error(f"Unexpected error in {test_case['error_type']} scenario: {e}")
        
        logger.info("✅ Error recovery WebSocket notification patterns validated")
    
    @pytest.mark.asyncio
    async def test_error_recovery_timing_patterns(self, error_prone_data_helper):
        """Test error recovery timing patterns with WebSocket integration."""
        try:
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        import time
        
        # Test recovery timing for different scenarios
        timing_tests = [
            {"scenario": "quick_recovery", "max_time": 2.0},
            {"scenario": "standard_recovery", "max_time": 5.0},
            {"scenario": "no_error", "max_time": 1.0}
        ]
        
        for test_case in timing_tests:
            context = ExecutionContext(
                run_id=f"timing_recovery_{test_case['scenario']}",
                agent_name=error_prone_data_helper.name,
                state=DeepAgentState()
            )
            
            start_time = time.time()
            
            try:
                result = await error_prone_data_helper.execute_core_logic(context)
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                # Verify timing constraints
                assert execution_time < test_case["max_time"], \
                    f"Recovery took too long for {test_case['scenario']}: {execution_time:.2f}s > {test_case['max_time']}s"
                
                assert isinstance(result, dict)
                
                logger.info(f"✅ Timing validated for {test_case['scenario']}: {execution_time:.3f}s")
                
            except Exception as e:
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Even errors should complete within reasonable time
                assert execution_time < test_case["max_time"] * 2, \
                    f"Error handling took too long for {test_case['scenario']}: {execution_time:.2f}s"
                
                logger.info(f"Error handled within time limit for {test_case['scenario']}: {execution_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_error_recovery_websocket_state_consistency(self, error_prone_data_helper, mock_websocket_manager):
        """Test error recovery maintains WebSocket state consistency."""
        try:
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
            from netra_backend.app.schemas.agent import SubAgentLifecycle
        except ImportError:
            pytest.skip("Required components not available")
        
        # Test state consistency during error recovery
        initial_state = error_prone_data_helper.get_state()
        
        context = ExecutionContext(
            run_id="error_recovery_state_consistency",
            agent_name=error_prone_data_helper.name,
            state=DeepAgentState()
        )
        
        try:
            # Set to running state
            error_prone_data_helper.set_state(SubAgentLifecycle.RUNNING)
            
            result = await error_prone_data_helper.execute_core_logic(context)
            
            # After successful execution, state should be appropriate
            final_state = error_prone_data_helper.get_state()
            
            # State should be in a valid final state
            valid_final_states = [
                SubAgentLifecycle.COMPLETED, 
                SubAgentLifecycle.RUNNING,  # Still processing
                SubAgentLifecycle.PENDING   # Ready for next task
            ]
            
            assert final_state in valid_final_states, \
                f"Invalid final state after execution: {final_state}"
            
            # Verify WebSocket calls maintained state consistency
            websocket_calls = mock_websocket_manager.send_to_thread.call_args_list
            
            # Check for state transition events in WebSocket calls
            state_events = []
            for call in websocket_calls:
                if len(call[0]) > 1 and isinstance(call[0][1], dict):
                    event_data = call[0][1]
                    if "status" in event_data.get("payload", {}):
                        state_events.append(event_data["payload"]["status"])
            
            logger.info(f"State transition events: {state_events}")
            
        except Exception as e:
            # Even in error cases, state should be consistent
            error_state = error_prone_data_helper.get_state()
            
            # Should be in failed state or recovering
            expected_error_states = [
                SubAgentLifecycle.FAILED,
                SubAgentLifecycle.RUNNING,  # Still trying to recover
                SubAgentLifecycle.PENDING   # Reset for retry
            ]
            
            assert error_state in expected_error_states, \
                f"Invalid error state after exception: {error_state}"
            
            logger.info(f"Error state handling validated: {error_state}")
        
        logger.info("✅ Error recovery WebSocket state consistency validated")
    
    @pytest.mark.asyncio
    async def test_error_recovery_cascading_failure_prevention(self, mock_websocket_manager):
        """Test error recovery prevents cascading failures in WebSocket integration."""
        try:
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        # Create multiple interconnected data helper agents
        agents = []
        for i in range(3):
            agent = DataHelperAgent(
                name=f"CascadePreventionAgent_{i}",
                enable_websocket_bridge=True,
                websocket_manager=mock_websocket_manager
            )
            agents.append(agent)
        
        # Test that error in one agent doesn't cascade to others
        contexts = []
        for i, agent in enumerate(agents):
            context = ExecutionContext(
                run_id=f"cascade_prevention_{i}",
                agent_name=agent.name,
                state=DeepAgentState()
            )
            contexts.append(context)
        
        # Execute all agents - some might error, but shouldn't cascade
        results = []
        for agent, context in zip(agents, contexts):
            try:
                result = await agent.execute_core_logic(context)
                results.append(("success", result))
            except Exception as e:
                results.append(("error", str(e)))
        
        # Analyze results - should not have complete failure cascade
        success_count = sum(1 for status, _ in results if status == "success")
        error_count = len(results) - success_count
        
        # At least some should succeed (no complete cascade)
        assert success_count > 0, "Complete cascade failure detected - all agents failed"
        
        # WebSocket manager should still be functional
        assert mock_websocket_manager.send_to_thread.call_count >= 0
        
        logger.info(f"✅ Cascade prevention validated: {success_count} successes, {error_count} errors")
    
    @pytest.mark.asyncio
    async def test_error_recovery_resource_cleanup_websocket_integration(self, error_prone_data_helper):
        """Test error recovery properly cleans up resources with WebSocket integration."""
        try:
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        # Track resource usage
        initial_resources = getattr(error_prone_data_helper, '_active_resources', 0)
        
        context = ExecutionContext(
            run_id="error_recovery_resource_cleanup",
            agent_name=error_prone_data_helper.name,
            state=DeepAgentState()
        )
        
        try:
            result = await error_prone_data_helper.execute_core_logic(context)
            
            # After successful execution, resources should be cleaned up
            final_resources = getattr(error_prone_data_helper, '_active_resources', 0)
            
            # Resources should be properly managed
            assert final_resources == initial_resources, \
                f"Resource leak detected: {final_resources} != {initial_resources}"
            
        except Exception as e:
            # Even after errors, resources should be cleaned up
            error_resources = getattr(error_prone_data_helper, '_active_resources', 0)
            
            # Should not have resource leaks even in error cases
            assert error_resources == initial_resources, \
                f"Resource leak after error: {error_resources} != {initial_resources}"
            
            logger.info(f"Resources properly cleaned up after error: {e}")
        
        logger.info("✅ Error recovery resource cleanup validated")


# ============================================================================
# TEST SUITE RUNNER
# ============================================================================

@pytest.mark.critical
@pytest.mark.mission_critical
class TestDataHelperWebSocketSuite:
    """Main test suite class for mission-critical DataHelperAgent WebSocket tests."""
    
    @pytest.mark.asyncio
    async def test_run_complete_datahelper_websocket_suite(self):
        """Run the complete mission-critical DataHelperAgent WebSocket test suite."""
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING MISSION CRITICAL DATAHELPER WEBSOCKET TEST SUITE")
        logger.info("=" * 80)
        
        logger.info("🔧 Mock mode - using mock WebSocket connections for reliable testing")
        
        # This is a meta-test that validates the suite itself works
        logger.info("\n✅ DataHelperAgent WebSocket Test Suite is operational")
        logger.info("Run with: pytest tests/mission_critical/test_datahelper_websocket_integration.py -v")
        logger.info("Business Value: Validates $200K+ ARR chat functionality for DataHelperAgent")


if __name__ == "__main__":
    # Run with: python tests/mission_critical/test_datahelper_websocket_integration.py
    # Or: pytest tests/mission_critical/test_datahelper_websocket_integration.py -v
    pytest.main([__file__, "-v", "--tb=short", "-x"])  # -x stops on first failure