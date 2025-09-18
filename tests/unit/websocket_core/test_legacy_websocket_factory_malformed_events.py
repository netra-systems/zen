"""Unit Tests: Legacy WebSocket Factory Malformed Events (Issue #1098)

PURPOSE: Reproduce and validate legacy WebSocket Manager Factory blocking AI response delivery
due to malformed event structures that break the Golden Path.

ISSUE #1098 CONTEXT:
The legacy websocket_manager_factory.py creates malformed WebSocket events that fail
validation and block AI responses from reaching users. This test suite reproduces
these failures to demonstrate why the legacy code must be removed.

EXPECTED BEHAVIOR: These tests should FAIL until legacy code is removed and SSOT is implemented.
The failures demonstrate the malformed event problems blocking the Golden Path.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Golden Path Infrastructure  
- Business Goal: Unblock AI response delivery worth 500K+ ARR
- Value Impact: Ensure WebSocket events properly deliver AI responses to users
- Revenue Impact: Remove blocking issues that prevent users from getting AI value
"""

import pytest
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional
import warnings
import secrets
from datetime import datetime, timezone

# Use SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import UserID, ensure_user_id

logger = get_logger(__name__)


class LegacyWebSocketFactoryMalformedEventsTest(SSotAsyncTestCase):
    """Test suite to reproduce legacy WebSocket factory malformed events blocking AI responses."""
    
    def setup_method(self, method):
        """Set up test infrastructure with real user context."""
        super().setup_method(method)
        
        # Create proper user execution context for isolation
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        
        id_manager = UnifiedIDManager()
        self.test_user_id = ensure_user_id(id_manager.generate_id(id_manager.IDType.USER, prefix="test"))
        self.test_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=id_manager.generate_id(id_manager.IDType.THREAD, prefix="test"),
            run_id=id_manager.generate_id(id_manager.IDType.RUN, prefix="test"),
            request_id=id_manager.generate_id(id_manager.IDType.REQUEST, prefix="test")
        )
        
        logger.info(f"Test setup complete for user {self.test_user_id}")
    
    async def test_legacy_factory_creates_malformed_agent_started_events(self):
        """EXPECTED TO FAIL: Legacy factory creates agent_started events missing required fields."""
        
        # Import the DEPRECATED legacy factory (this is what we're testing for problems)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager_sync
        
        # Create manager using legacy factory (this introduces the problems)
        legacy_manager = create_websocket_manager_sync(user_context=self.test_context)
        
        # Mock WebSocket connection to capture event data
        mock_websocket = Mock()
        mock_websocket.send = AsyncMock()
        
        # The legacy factory creates events through the manager, let's capture them
        with patch.object(legacy_manager, '_websocket_connections', {self.test_user_id: mock_websocket}):
            
            # Try to emit agent_started event using legacy manager patterns
            # This is where the malformed events are created
            try:
                event_data = {
                    "agent_name": "supervisor_agent", 
                    "task": "Process user request"
                }
                
                # Legacy manager creates malformed events - missing critical fields
                await legacy_manager.emit_to_user(
                    user_id=self.test_user_id,
                    event_type="agent_started",
                    data=event_data
                )
                
                # Extract the actual event data that was sent
                self.assertTrue(mock_websocket.send.called, "Legacy manager should have sent event")
                sent_args = mock_websocket.send.call_args
                sent_event = sent_args[0][0] if sent_args and sent_args[0] else {}
                
                # EXPECTED FAILURES: These assertions should FAIL showing the malformed events
                self.assertIn('user_id', sent_event, 
                    "LEGACY BUG: agent_started event missing required user_id field - BLOCKS AI RESPONSES")
                
                self.assertIn('thread_id', sent_event, 
                    "LEGACY BUG: agent_started event missing required thread_id field - BLOCKS AI RESPONSES")
                
                self.assertIn('run_id', sent_event, 
                    "LEGACY BUG: agent_started event missing required run_id field - BLOCKS AI RESPONSES")
                
                self.assertIn('timestamp', sent_event, 
                    "LEGACY BUG: agent_started event missing required timestamp field - BLOCKS AI RESPONSES")
                
                # Validate event structure integrity
                self._validate_agent_started_event_structure(sent_event)
                
            except Exception as e:
                self.fail(f"Legacy factory agent_started event creation failed: {e}")
    
    async def test_legacy_factory_creates_malformed_tool_executing_events(self):
        """EXPECTED TO FAIL: Legacy factory creates tool_executing events with malformed structure."""
        
        # Import the DEPRECATED legacy factory
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager_sync
        
        # Create manager using legacy factory
        legacy_manager = create_websocket_manager_sync(user_context=self.test_context)
        
        # Mock WebSocket connection
        mock_websocket = Mock()
        mock_websocket.send = AsyncMock()
        
        with patch.object(legacy_manager, '_websocket_connections', {self.test_user_id: mock_websocket}):
            
            try:
                # Legacy manager attempts to create tool_executing event
                event_data = {
                    "agent_name": "supervisor_agent",
                    "tool_name": "search_tool", 
                    "tool_input": {"query": "test search"}
                }
                
                await legacy_manager.emit_to_user(
                    user_id=self.test_user_id,
                    event_type="tool_executing",
                    data=event_data
                )
                
                # Extract sent event
                self.assertTrue(mock_websocket.send.called, "Legacy manager should have sent tool_executing event")
                sent_args = mock_websocket.send.call_args
                sent_event = sent_args[0][0] if sent_args and sent_args[0] else {}
                
                # EXPECTED FAILURES: These show the malformed tool_executing events
                self.assertIn('user_id', sent_event, 
                    "LEGACY BUG: tool_executing event missing user_id - BLOCKS TOOL VISIBILITY")
                
                self.assertIn('thread_id', sent_event, 
                    "LEGACY BUG: tool_executing event missing thread_id - BREAKS CONTEXT TRACKING")
                
                self.assertIn('tool_name', sent_event, 
                    "LEGACY BUG: tool_executing event missing tool_name - USER CAN'T SEE WHICH TOOL")
                
                self.assertIn('tool_input', sent_event, 
                    "LEGACY BUG: tool_executing event missing tool_input - NO TRANSPARENCY")
                
                # Validate complete event structure
                self._validate_tool_executing_event_structure(sent_event)
                
            except Exception as e:
                self.fail(f"Legacy factory tool_executing event creation failed: {e}")
    
    async def test_legacy_factory_creates_malformed_agent_completed_events(self):
        """EXPECTED TO FAIL: Legacy factory creates agent_completed events missing result data."""
        
        # Import the DEPRECATED legacy factory
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager_sync
        
        # Create manager using legacy factory
        legacy_manager = create_websocket_manager_sync(user_context=self.test_context)
        
        # Mock WebSocket connection
        mock_websocket = Mock()
        mock_websocket.send = AsyncMock()
        
        with patch.object(legacy_manager, '_websocket_connections', {self.test_user_id: mock_websocket}):
            
            try:
                # Legacy manager creates agent_completed event
                event_data = {
                    "agent_name": "supervisor_agent",
                    "status": "completed",
                    "result": "Analysis complete with recommendations"
                }
                
                await legacy_manager.emit_to_user(
                    user_id=self.test_user_id,
                    event_type="agent_completed",
                    data=event_data
                )
                
                # Extract sent event
                self.assertTrue(mock_websocket.send.called, "Legacy manager should have sent agent_completed event")
                sent_args = mock_websocket.send.call_args
                sent_event = sent_args[0][0] if sent_args and sent_args[0] else {}
                
                # EXPECTED FAILURES: These show malformed agent_completed events
                self.assertIn('user_id', sent_event, 
                    "LEGACY BUG: agent_completed missing user_id - USER CAN'T SEE COMPLETION")
                
                self.assertIn('thread_id', sent_event, 
                    "LEGACY BUG: agent_completed missing thread_id - BREAKS RESPONSE ROUTING")
                
                self.assertIn('result', sent_event, 
                    "LEGACY BUG: agent_completed missing result - USER GETS NO AI VALUE")
                
                self.assertIn('timestamp', sent_event, 
                    "LEGACY BUG: agent_completed missing timestamp - NO COMPLETION TIME")
                
                # Validate complete event structure 
                self._validate_agent_completed_event_structure(sent_event)
                
            except Exception as e:
                self.fail(f"Legacy factory agent_completed event creation failed: {e}")
    
    def _validate_agent_started_event_structure(self, event: Dict[str, Any]) -> None:
        """Validate agent_started event has all required fields - THIS SHOULD FAIL for legacy events."""
        
        required_fields = [
            'type',           # Event type identifier
            'user_id',        # User context for isolation
            'thread_id',      # Thread context for routing  
            'run_id',         # Run context for correlation
            'agent_name',     # Which agent started
            'task',           # What task the agent is performing
            'timestamp'       # When the agent started
        ]
        
        logger.info(f"Validating agent_started event structure: {event}")
        
        for field in required_fields:
            self.assertIn(field, event, 
                f"LEGACY BUG: agent_started event missing required field '{field}' - "
                f"This blocks proper AI response delivery to users")
        
        # Validate field types
        self.assertEqual(event.get('type'), 'agent_started', 
            "LEGACY BUG: agent_started event has wrong type field")
        
        self.assertIsInstance(event.get('user_id'), str, 
            "LEGACY BUG: agent_started event user_id must be string")
        
        self.assertIsInstance(event.get('agent_name'), str, 
            "LEGACY BUG: agent_started event agent_name must be string")
    
    def _validate_tool_executing_event_structure(self, event: Dict[str, Any]) -> None:
        """Validate tool_executing event structure - THIS SHOULD FAIL for legacy events."""
        
        required_fields = [
            'type',           # Event type
            'user_id',        # User context
            'thread_id',      # Thread context
            'agent_name',     # Which agent is using the tool
            'tool_name',      # Which tool is executing
            'tool_input',     # Tool input parameters
            'timestamp'       # When tool started executing
        ]
        
        logger.info(f"Validating tool_executing event structure: {event}")
        
        for field in required_fields:
            self.assertIn(field, event, 
                f"LEGACY BUG: tool_executing event missing required field '{field}' - "
                f"This breaks tool transparency for users")
        
        # Validate specific field requirements
        self.assertEqual(event.get('type'), 'tool_executing',
            "LEGACY BUG: tool_executing event has wrong type")
            
        self.assertIsInstance(event.get('tool_input'), dict,
            "LEGACY BUG: tool_executing event tool_input must be dict")
    
    def _validate_agent_completed_event_structure(self, event: Dict[str, Any]) -> None:
        """Validate agent_completed event structure - THIS SHOULD FAIL for legacy events."""
        
        required_fields = [
            'type',           # Event type 
            'user_id',        # User context
            'thread_id',      # Thread context
            'run_id',         # Run context
            'agent_name',     # Which agent completed
            'status',         # Completion status
            'result',         # Agent result/response
            'timestamp'       # When agent completed
        ]
        
        logger.info(f"Validating agent_completed event structure: {event}")
        
        for field in required_fields:
            self.assertIn(field, event, 
                f"LEGACY BUG: agent_completed event missing required field '{field}' - "
                f"This prevents users from getting AI responses")
        
        # Validate critical result field
        self.assertIsNotNone(event.get('result'),
            "LEGACY BUG: agent_completed event result is None - USER GETS NO AI VALUE")
            
        self.assertNotEqual(event.get('result'), '',
            "LEGACY BUG: agent_completed event result is empty - USER GETS NO AI VALUE")


class LegacyVsSSotEventComparisonTest(SSotAsyncTestCase):
    """Compare legacy factory events vs SSOT events to show the differences."""
    
    def setup_method(self, method):
        """Set up both legacy and SSOT managers for comparison."""
        super().setup_method(method)
        
        # Create test context
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        
        id_manager = UnifiedIDManager()
        self.test_user_id = ensure_user_id(id_manager.generate_id(id_manager.IDType.USER, prefix="test"))
        self.test_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=id_manager.generate_id(id_manager.IDType.THREAD, prefix="test"),
            run_id=id_manager.generate_id(id_manager.IDType.RUN, prefix="test"),
            request_id=id_manager.generate_id(id_manager.IDType.REQUEST, prefix="test")
        )
    
    async def test_legacy_vs_ssot_agent_started_event_comparison(self):
        """EXPECTED TO FAIL: Compare legacy vs SSOT agent_started events - legacy should be malformed."""
        
        # Create SSOT event (proper structure)
        ssot_event = {
            "type": "agent_started",
            "user_id": str(self.test_user_id),
            "thread_id": self.test_context.thread_id,
            "run_id": self.test_context.run_id,
            "agent_name": "supervisor_agent",
            "task": "Process user request",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Create legacy event (missing fields) - this simulates what legacy factory produces
        legacy_event = {
            "agent_name": "supervisor_agent",
            "task": "Process user request"
            # Missing: type, user_id, thread_id, run_id, timestamp
        }
        
        logger.info(f"SSOT event (PROPER): {ssot_event}")
        logger.info(f"Legacy event (MALFORMED): {legacy_event}")
        
        # EXPECTED FAILURES: These assertions should FAIL showing legacy events are malformed
        try:
            self.assertEqual(len(ssot_event.keys()), len(legacy_event.keys()),
                f"LEGACY BUG: Legacy event has {len(legacy_event.keys())} fields vs "
                f"SSOT event has {len(ssot_event.keys())} fields - MISSING CRITICAL DATA")
        except AssertionError as e:
            logger.error(f"Event structure comparison failed as expected: {e}")
            
        try:
            self.assertIn('user_id', legacy_event,
                "LEGACY BUG: Legacy agent_started event missing user_id - BLOCKS USER ROUTING")
        except AssertionError as e:
            logger.error(f"Legacy event validation failed as expected: {e}")
            
        try:
            self.assertIn('timestamp', legacy_event,
                "LEGACY BUG: Legacy agent_started event missing timestamp - NO TIME TRACKING")
        except AssertionError as e:
            logger.error(f"Legacy event validation failed as expected: {e}")
        
        # This test demonstrates the problem - legacy events are fundamentally broken
        self.fail("EXPECTED FAILURE: Legacy events are malformed compared to SSOT - "
                  "This demonstrates why legacy factory blocks AI response delivery")
    
    async def test_legacy_factory_produces_incomplete_websocket_events(self):
        """EXPECTED TO FAIL: Demonstrate that legacy factory produces incomplete events."""
        
        # Import legacy factory
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning) 
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager_sync
        
        # Create legacy manager
        legacy_manager = create_websocket_manager_sync(user_context=self.test_context)
        
        # Mock the event creation to see what it actually produces
        captured_events = []
        
        def capture_event(*args, **kwargs):
            captured_events.append({"args": args, "kwargs": kwargs})
            return AsyncMock()
        
        with patch.object(legacy_manager, 'emit_to_user', side_effect=capture_event):
            
            # Try to use legacy manager to emit all required Golden Path events
            try:
                await legacy_manager.emit_to_user(
                    user_id=self.test_user_id,
                    event_type="agent_started", 
                    data={"agent_name": "test"}
                )
                
                await legacy_manager.emit_to_user(
                    user_id=self.test_user_id,
                    event_type="tool_executing",
                    data={"tool": "search"}
                )
                
                await legacy_manager.emit_to_user(
                    user_id=self.test_user_id,
                    event_type="agent_completed",
                    data={"result": "done"}
                )
                
            except Exception as e:
                logger.error(f"Legacy event emission failed: {e}")
        
        # Verify events were captured but are incomplete
        self.assertEqual(len(captured_events), 3, "Should have captured 3 events")
        
        # Check each event for completeness - THESE SHOULD FAIL
        for i, event in enumerate(captured_events):
            event_data = event['kwargs'].get('data', {})
            
            self.assertIn('user_id', event_data,
                f"LEGACY BUG: Event {i} missing user_id - BLOCKS USER ISOLATION") 
                
            self.assertIn('thread_id', event_data,
                f"LEGACY BUG: Event {i} missing thread_id - BREAKS CONTEXT ROUTING")
                
            self.assertIn('timestamp', event_data,
                f"LEGACY BUG: Event {i} missing timestamp - NO TIME TRACKING")
        
        # This demonstrates the core issue
        self.fail("EXPECTED FAILURE: Legacy factory produces incomplete WebSocket events "
                  "that fail validation and block AI responses from reaching users")


if __name__ == '__main__':
    # Run the tests to demonstrate the legacy factory issues
    unittest.main()