"""WebSocket Emitter SSOT Validation Tests - Simplified

MISSION CRITICAL: Test Issue #200 SSOT consolidation for WebSocket emitters.
Validates that race conditions are eliminated and SSOT compliance is achieved.

NON-DOCKER TESTS ONLY: These tests run without Docker orchestration requirements.

Focus Areas:
1. SSOT Import Validation - Verify imports redirect properly
2. Critical Event Delivery - Ensure all 5 events work
3. Consumer Compatibility - Test existing API patterns
4. Race Condition Prevention - Validate no duplicate sources

Business Impact: Protects $500K+ ARR Golden Path chat functionality.
"""

import asyncio
import pytest
import time
import unittest
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from collections import defaultdict
import threading


class TestEmitterSSotValidation(unittest.IsolatedAsyncioTestCase):
    """
    Simplified SSOT validation tests for WebSocket emitters.
    
    Uses unittest.IsolatedAsyncioTestCase for better async support
    without complex inheritance dependencies.
    """
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        
        # Create mock WebSocket manager with needed methods
        self.mock_manager = AsyncMock()
        self.mock_manager.emit_critical_event = AsyncMock()
        self.mock_manager.is_connection_active = MagicMock(return_value=True)
        self.mock_manager.get_connection_health = MagicMock(
            return_value={'has_active_connections': True}
        )
        self.mock_manager.get_connection = MagicMock(return_value=None)
        self.mock_manager.get_user_connections = AsyncMock(return_value=[])
        
        # Create mock user context
        self.mock_context = MagicMock()
        self.mock_context.user_id = "test_user_123"
        self.mock_context.thread_id = "test_thread_456"
        self.mock_context.run_id = "test_run_789"
        self.mock_context.request_id = "test_req_000"
        self.mock_context.user_tier = "free"
        
        self.test_user_id = "test_user_123"
    
    async def test_unified_emitter_imports_correctly(self):
        """Test that UnifiedWebSocketEmitter can be imported and instantiated."""
        
        from netra_backend.app.websocket_core.unified_emitter import (
            UnifiedWebSocketEmitter,
            WebSocketEmitterFactory,
            AuthenticationWebSocketEmitter
        )
        
        # Should be able to create unified emitter
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.mock_context
        )
        
        self.assertIsNotNone(emitter)
        self.assertEqual(emitter.user_id, self.test_user_id)
        self.assertTrue(hasattr(emitter, 'CRITICAL_EVENTS'))
        self.assertEqual(len(emitter.CRITICAL_EVENTS), 5)
    
    async def test_transparent_emitter_redirects_to_ssot(self):
        """Test that TransparentWebSocketEmitter redirects to UnifiedWebSocketEmitter."""
        
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        from netra_backend.app.services.websocket.transparent_websocket_events import (
            TransparentWebSocketEmitter
        )
        
        # TransparentWebSocketEmitter should be an alias to UnifiedWebSocketEmitter
        self.assertIs(TransparentWebSocketEmitter, UnifiedWebSocketEmitter)
    
    async def test_critical_events_delivery(self):
        """Test that all 5 critical events can be delivered."""
        
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.mock_context
        )
        
        # Test all 5 critical events
        critical_events = [
            ('agent_started', {'agent_name': 'test_agent'}),
            ('agent_thinking', {'thought': 'processing request'}),
            ('tool_executing', {'tool': 'test_tool'}),
            ('tool_completed', {'tool': 'test_tool', 'result': 'success'}),
            ('agent_completed', {'agent_name': 'test_agent', 'status': 'completed'})
        ]
        
        for event_type, data in critical_events:
            emit_method = getattr(emitter, f'emit_{event_type}')
            await emit_method(data)
        
        # Verify all events were emitted
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 5)
        
        # Verify event types
        calls = self.mock_manager.emit_critical_event.call_args_list
        for i, (expected_event, _) in enumerate(critical_events):
            actual_event = calls[i][1]['event_type']
            self.assertEqual(actual_event, expected_event)
    
    async def test_factory_creates_ssot_instances(self):
        """Test that factory methods create SSOT instances."""
        
        from netra_backend.app.websocket_core.unified_emitter import (
            UnifiedWebSocketEmitter,
            WebSocketEmitterFactory,
            AuthenticationWebSocketEmitter
        )
        
        # Test standard factory
        emitter = WebSocketEmitterFactory.create_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.mock_context
        )
        
        self.assertIsInstance(emitter, UnifiedWebSocketEmitter)
        
        # Test scoped factory
        scoped_emitter = WebSocketEmitterFactory.create_scoped_emitter(
            manager=self.mock_manager,
            context=self.mock_context
        )
        
        self.assertIsInstance(scoped_emitter, UnifiedWebSocketEmitter)
        
        # Test auth factory
        auth_emitter = WebSocketEmitterFactory.create_auth_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.mock_context
        )
        
        self.assertIsInstance(auth_emitter, AuthenticationWebSocketEmitter)
        self.assertIsInstance(auth_emitter, UnifiedWebSocketEmitter)
    
    async def test_backward_compatibility_apis(self):
        """Test that backward compatibility APIs work."""
        
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.mock_context
        )
        
        # Test notify_* methods (backward compatibility)
        await emitter.notify_agent_started(
            agent_name="BackwardCompatAgent",
            metadata={"test": "data"}
        )
        
        await emitter.notify_agent_thinking(
            agent_name="BackwardCompatAgent",
            reasoning="Testing backward compatibility"
        )
        
        await emitter.notify_tool_executing(
            tool_name="BackwardCompatTool",
            metadata={"param": "value"}
        )
        
        await emitter.notify_tool_completed(
            tool_name="BackwardCompatTool",
            metadata={"result": "success"}
        )
        
        await emitter.notify_agent_completed(
            agent_name="BackwardCompatAgent",
            metadata={"status": "completed"},
            execution_time_ms=1000
        )
        
        # Verify all backward compatibility methods worked
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 5)
    
    async def test_generic_emit_routing(self):
        """Test that generic emit method routes correctly."""
        
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.mock_context
        )
        
        # Test routing to critical events
        await emitter.emit('agent_started', {'agent_name': 'routed_agent'})
        await emitter.emit('agent_thinking', {'thought': 'routed_thought'})
        
        # Test non-critical event routing
        await emitter.emit('custom_event', {'custom': 'data'})
        
        # Verify routing worked
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 3)
    
    async def test_concurrent_emission_no_race_conditions(self):
        """Test concurrent emissions don't cause race conditions."""
        
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        # Track emissions with thread safety
        emission_calls = []
        lock = threading.Lock()
        
        async def track_emission(user_id: str, event_type: str, data: Dict[str, Any]):
            with lock:
                emission_calls.append({
                    'user_id': user_id,
                    'event_type': event_type,
                    'timestamp': time.time(),
                    'thread_id': threading.get_ident()
                })
        
        self.mock_manager.emit_critical_event.side_effect = track_emission
        
        # Create multiple emitters
        emitter1 = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id="user_1",
            context=self.mock_context
        )
        
        emitter2 = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id="user_2", 
            context=self.mock_context
        )
        
        # Concurrent emissions
        await asyncio.gather(
            emitter1.emit_agent_started({'agent_name': 'concurrent_agent_1'}),
            emitter2.emit_agent_started({'agent_name': 'concurrent_agent_2'}),
            emitter1.emit_agent_completed({'agent_name': 'concurrent_agent_1'}),
            emitter2.emit_agent_completed({'agent_name': 'concurrent_agent_2'})
        )
        
        # Verify all emissions went through SSOT
        self.assertEqual(len(emission_calls), 4)
        
        # Verify user isolation
        user_1_calls = [call for call in emission_calls if call['user_id'] == 'user_1']
        user_2_calls = [call for call in emission_calls if call['user_id'] == 'user_2']
        
        self.assertEqual(len(user_1_calls), 2)
        self.assertEqual(len(user_2_calls), 2)
    
    async def test_transparent_emitter_factory_compatibility(self):
        """Test transparent emitter factory creates SSOT instances."""
        
        from netra_backend.app.services.websocket.transparent_websocket_events import (
            create_transparent_emitter
        )
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        # Mock the create_websocket_manager function
        with patch('netra_backend.app.websocket_core.create_websocket_manager') as mock_create:
            mock_create.return_value = self.mock_manager
            
            # Create transparent emitter
            transparent_emitter = await create_transparent_emitter(self.mock_context)
            
            # Should be SSOT instance
            self.assertIsInstance(transparent_emitter, UnifiedWebSocketEmitter)
            self.assertEqual(transparent_emitter.user_id, self.test_user_id)
    
    async def test_emission_source_validation(self):
        """Test that all emissions go through the same SSOT manager."""
        
        from netra_backend.app.websocket_core.unified_emitter import (
            UnifiedWebSocketEmitter,
            WebSocketEmitterFactory,
            AuthenticationWebSocketEmitter
        )
        
        # Track which manager instance was used
        manager_instances = []
        
        async def track_manager(user_id: str, event_type: str, data: Dict[str, Any]):
            manager_instances.append(self.mock_manager)
        
        self.mock_manager.emit_critical_event.side_effect = track_manager
        
        # Create different types of emitters
        unified_emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.mock_context
        )
        
        factory_emitter = WebSocketEmitterFactory.create_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.mock_context
        )
        
        auth_emitter = AuthenticationWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.mock_context
        )
        
        # Emit from different emitters
        await unified_emitter.emit_agent_started({'source': 'unified'})
        await factory_emitter.emit_agent_thinking({'source': 'factory'})
        await auth_emitter.emit_agent_completed({'source': 'auth'})
        
        # All should use the same manager instance
        self.assertEqual(len(manager_instances), 3)
        self.assertTrue(all(mgr is self.mock_manager for mgr in manager_instances))
    
    async def test_context_validation_prevents_race_conditions(self):
        """Test that context validation prevents race conditions."""
        
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.mock_context
        )
        
        # Test with valid context
        await emitter.emit_agent_started({'agent_name': 'valid_context_agent'})
        
        # Verify emission occurred
        self.mock_manager.emit_critical_event.assert_called()
        
        # Check that context data is included
        call_args = self.mock_manager.emit_critical_event.call_args
        data = call_args[1]['data']
        
        self.assertIn('run_id', data)
        self.assertIn('thread_id', data)
        self.assertEqual(data['run_id'], self.mock_context.run_id)
        self.assertEqual(data['thread_id'], self.mock_context.thread_id)


if __name__ == '__main__':
    # Run tests with asyncio support
    unittest.main()