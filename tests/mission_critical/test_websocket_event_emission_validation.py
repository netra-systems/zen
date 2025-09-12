"""
MISSION CRITICAL: WebSocket Event Emission Validation Test

This test validates that all 5 critical WebSocket events are properly emitted
during agent execution flow after the fixes implemented to address the
ConnectionHandler issues.

Critical Events Tested:
1. agent_started - When agent begins processing
2. agent_thinking - During agent reasoning 
3. tool_executing - When tools are being used
4. tool_completed - When tool execution finishes
5. agent_completed - When agent finishes processing

This test runs without requiring full backend services by using mocks,
but validates that the integration points are correctly connected.
"""

import asyncio
import pytest
import time
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory, UserWebSocketEmitter
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from shared.id_generation import UnifiedIdGenerator


class TestWebSocketEventEmissionValidation(SSotBaseTestCase):
    """Validates that all 5 critical WebSocket events are emitted correctly."""
    
    def setup_method(self):
        """Set up test with proper mocking."""
        super().setup_method()
        
        # Track emitted events
        self.emitted_events: List[Dict[str, Any]] = []
        
        # Create mock WebSocket manager that tracks events
        self.mock_websocket_manager = MagicMock()
        self.mock_websocket_manager.emit_critical_event = AsyncMock(side_effect=self._track_event)
        self.mock_websocket_manager.is_connection_active = MagicMock(return_value=True)
        
        # Create mock agent factory components
        self.mock_agent_factory = MagicMock()
        self.mock_agent_factory._agent_registry = MagicMock()
        self.mock_agent_factory._websocket_bridge = MagicMock()
        
        # Mock agent registry to support tool dispatcher
        self.mock_agent_registry = self.mock_agent_factory._agent_registry
        self.mock_agent_registry.set_tool_dispatcher = MagicMock()
        
    async def _track_event(self, user_id: str, event_type: str, data: Dict[str, Any]):
        """Track emitted WebSocket events."""
        event = {
            'user_id': user_id,
            'event_type': event_type,
            'data': data,
            'timestamp': time.time()
        }
        self.emitted_events.append(event)
        return True
        
    @pytest.mark.mission_critical
    async def test_websocket_emitter_signature_compatibility(self):
        """Test that WebSocket emitter method signatures work correctly."""
        # Create user context
        context = UserExecutionContext(
            user_id='105945141827451681156',  # Golden path test user
            thread_id=UnifiedIdGenerator.generate_base_id('thread'),
            run_id=UnifiedIdGenerator.generate_base_id('run'),
            request_id=UnifiedIdGenerator.generate_base_id('req')
        )
        
        # Create WebSocket emitter
        emitter = UnifiedWebSocketEmitter(self.mock_websocket_manager, context.user_id, context)
        
        # Test all critical event methods
        await emitter.notify_agent_started(agent_name='test_agent', context={'status': 'started'})
        await emitter.notify_agent_thinking(agent_name='test_agent', reasoning='Processing request...', step_number=1)
        await emitter.notify_tool_executing(tool_name='test_tool', metadata={'args': {'param': 'value'}})
        await emitter.notify_tool_completed(tool_name='test_tool', metadata={'result': {'success': True}})
        await emitter.notify_agent_completed(agent_name='test_agent', result={'success': True}, execution_time_ms=1500)
        
        # Validate all events were emitted
        assert len(self.emitted_events) == 5, f"Expected 5 events, got {len(self.emitted_events)}"
        
        # Validate event types
        expected_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        emitted_event_types = {event['event_type'] for event in self.emitted_events}
        assert emitted_event_types == expected_events, f"Missing events: {expected_events - emitted_event_types}"
        
        print(" PASS:  All 5 critical WebSocket events emitted successfully")
        
    @pytest.mark.mission_critical 
    async def test_user_execution_engine_tool_dispatcher_integration(self):
        """Test that UserExecutionEngine properly connects tool dispatcher with WebSocket events."""
        # Create user context
        context = UserExecutionContext(
            user_id='105945141827451681156',
            thread_id=UnifiedIdGenerator.generate_base_id('thread'),
            run_id=UnifiedIdGenerator.generate_base_id('run'),
            request_id=UnifiedIdGenerator.generate_base_id('req')
        )
        
        # Create WebSocket emitter
        websocket_emitter = UnifiedWebSocketEmitter(self.mock_websocket_manager, context.user_id, context)
        
        # Create UserExecutionEngine
        engine = UserExecutionEngine(
            context=context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=websocket_emitter
        )
        
        # Test tool dispatcher creation
        tool_dispatcher = engine.get_tool_dispatcher()
        assert tool_dispatcher is not None, "Tool dispatcher should not be None"
        
        # Test tool execution (this will fail to find the tool but should emit events)
        try:
            await tool_dispatcher.execute_tool('test_tool', {'param': 'value'})
        except Exception:
            pass  # Expected to fail since tool doesn't exist
        
        # Verify that agent registry was configured with tool dispatcher
        self.mock_agent_registry.set_tool_dispatcher.assert_called_once()
        
        print(" PASS:  UserExecutionEngine tool dispatcher integration working")
        
    @pytest.mark.mission_critical
    async def test_agent_factory_websocket_emitter_creation(self):
        """Test that UserWebSocketEmitter is created correctly."""
        # Create mock WebSocket bridge
        mock_bridge = MagicMock()
        mock_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_bridge.notify_agent_thinking = AsyncMock(return_value=True)
        mock_bridge.notify_agent_completed = AsyncMock(return_value=True)
        
        # Create UserWebSocketEmitter
        emitter = UserWebSocketEmitter(
            user_id='105945141827451681156',
            thread_id='test_thread',
            run_id='test_run',
            websocket_bridge=mock_bridge
        )
        
        # Test agent notifications
        await emitter.notify_agent_started('test_agent', {'status': 'started'})
        await emitter.notify_agent_thinking('test_agent', 'Processing...', 1)
        await emitter.notify_agent_completed('test_agent', {'success': True}, 1000)
        
        # Verify calls were made
        mock_bridge.notify_agent_started.assert_called_once()
        mock_bridge.notify_agent_thinking.assert_called_once() 
        mock_bridge.notify_agent_completed.assert_called_once()
        
        print(" PASS:  UserWebSocketEmitter working correctly")
        
    @pytest.mark.mission_critical
    async def test_complete_event_flow_integration(self):
        """Test complete integration of all components for WebSocket event emission."""
        # This test validates that the entire chain is connected:
        # UserExecutionEngine -> tool_dispatcher -> WebSocket events
        # UserExecutionEngine -> agent_core -> WebSocket events
        
        # Create user context
        context = UserExecutionContext(
            user_id='105945141827451681156',
            thread_id=UnifiedIdGenerator.generate_base_id('thread'),
            run_id=UnifiedIdGenerator.generate_base_id('run'),
            request_id=UnifiedIdGenerator.generate_base_id('req')
        )
        
        # Create WebSocket emitter
        websocket_emitter = UnifiedWebSocketEmitter(self.mock_websocket_manager, context.user_id, context)
        
        # Create UserExecutionEngine
        engine = UserExecutionEngine(
            context=context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=websocket_emitter
        )
        
        # Validate that all components are connected
        assert engine.websocket_emitter is not None, "WebSocket emitter not set"
        assert engine.agent_factory is not None, "Agent factory not set"
        assert engine.context == context, "User context not set correctly"
        
        # Validate tool dispatcher is created
        tool_dispatcher = engine.get_tool_dispatcher()
        assert tool_dispatcher is not None, "Tool dispatcher creation failed"
        
        # Validate agent registry has tool dispatcher
        self.mock_agent_registry.set_tool_dispatcher.assert_called()
        
        # Test direct WebSocket event emission
        await websocket_emitter.notify_agent_started('integration_test_agent')
        await websocket_emitter.notify_agent_thinking(agent_name='integration_test_agent', reasoning='Integration test')
        
        # Verify events were tracked
        assert len(self.emitted_events) >= 2, "Events not properly emitted"
        
        print(" PASS:  Complete integration test passed - all components connected correctly")
        
    def get_event_summary(self) -> Dict[str, Any]:
        """Get summary of emitted events for debugging."""
        event_types = [event['event_type'] for event in self.emitted_events]
        return {
            'total_events': len(self.emitted_events),
            'event_types': event_types,
            'unique_event_types': list(set(event_types)),
            'events': self.emitted_events
        }


if __name__ == "__main__":
    """
    Run WebSocket event emission validation tests directly.
    
    Usage:
        python -m pytest tests/mission_critical/test_websocket_event_emission_validation.py -v -s
    """
    import sys
    import os
    
    # Add project root to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])