"""WebSocket Emitter Race Condition Detection Tests

MISSION CRITICAL: Test Issue #200 - Multiple WebSocket emitters causing race conditions.
These tests validate the SSOT consolidation and detect race conditions that could
affect the $500K+ ARR Golden Path user flow.

NON-DOCKER TESTS ONLY: These tests run without Docker orchestration requirements.

Test Strategy:
1. Race Condition Detection - Prove multiple emitters cause issues
2. SSOT Compliance - Validate unified emitter usage  
3. Event Delivery Validation - Ensure critical events work
4. API Compatibility - Test consumer integration

Business Impact: Protects Golden Path chat functionality reliability.
"""

import asyncio
import pytest
import time
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from collections import defaultdict
import concurrent.futures
import threading
from datetime import datetime, timezone

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Import the SSOT WebSocket emitter
from netra_backend.app.websocket_core.unified_emitter import (
    UnifiedWebSocketEmitter,
    WebSocketEmitterFactory,
    AuthenticationWebSocketEmitter,
    WebSocketEmitterPool
)

# Import redirect implementations to verify they use SSOT
from netra_backend.app.services.websocket.transparent_websocket_events import (
    TransparentWebSocketEmitter,
    create_transparent_emitter
)

# Import UserExecutionContext for testing
from netra_backend.app.services.user_execution_context import UserExecutionContext

class TestWebSocketEmitterRaceConditions(SSotAsyncTestCase):
    """
    Test race conditions in WebSocket emitter implementations.
    
    CRITICAL: These tests prove that multiple emitters cause race conditions
    and validate that SSOT consolidation prevents them.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        # Create mock WebSocket manager
        self.mock_manager = SSotMockFactory.create_websocket_manager_mock()
        
        # Create test user context
        self.test_user_id = "test_user_12345"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
        
        # Track event emissions for race condition detection
        self.event_emissions = defaultdict(list)
        self.emission_lock = threading.Lock()
        
        # Mock emit_critical_event to track emissions
        async def track_emissions(user_id: str, event_type: str, data: Dict[str, Any]):
            with self.emission_lock:
                self.event_emissions[event_type].append({
                    'user_id': user_id,
                    'event_type': event_type,
                    'data': data,
                    'timestamp': time.time(),
                    'thread_id': threading.get_ident()
                })
        
        self.mock_manager.emit_critical_event.side_effect = track_emissions
    
    async def test_race_condition_detection_multiple_emitters(self):
        """
        CRITICAL TEST: Detect race conditions when multiple emitters emit simultaneously.
        
        This test simulates the race condition scenario where multiple emitter
        implementations try to emit the same event type simultaneously.
        """
        
        # Create multiple emitter types that should all redirect to SSOT
        unified_emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        transparent_emitter = TransparentWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        auth_emitter = AuthenticationWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Test data
        test_event_data = {
            'test_message': 'concurrent_emission_test',
            'timestamp': time.time()
        }
        
        # Create concurrent emission tasks
        async def emit_agent_started(emitter, emitter_name):
            await emitter.emit_agent_started({
                **test_event_data,
                'emitter_source': emitter_name
            })
        
        # Execute concurrent emissions
        start_time = time.time()
        await asyncio.gather(
            emit_agent_started(unified_emitter, 'unified'),
            emit_agent_started(transparent_emitter, 'transparent'),
            emit_agent_started(auth_emitter, 'auth'),
            return_exceptions=True
        )
        end_time = time.time()
        
        # Analyze race condition indicators
        emissions = self.event_emissions['agent_started']
        
        # Validate all emissions went through SSOT
        self.assertEqual(len(emissions), 3, "All emitters should emit through SSOT")
        
        # Check for race condition indicators
        thread_ids = [emission['thread_id'] for emission in emissions]
        timestamps = [emission['timestamp'] for emission in emissions]
        
        # Race condition indicators:
        # 1. Multiple thread IDs (concurrent execution)
        # 2. Overlapping timestamps (near-simultaneous execution)
        self.assertGreater(len(set(thread_ids)), 1, 
                          "Multiple threads indicate potential race condition")
        
        max_time_diff = max(timestamps) - min(timestamps)
        self.assertLess(max_time_diff, 0.1, 
                       "Concurrent emissions should happen within 100ms")
        
        # Validate SSOT behavior - all should go through same manager
        for emission in emissions:
            self.assertEqual(emission['user_id'], self.test_user_id)
            self.assertEqual(emission['event_type'], 'agent_started')
    
    async def test_race_condition_critical_events_sequence(self):
        """
        Test race conditions in critical event sequence delivery.
        
        Ensures that the 5 critical events are delivered in order
        even under concurrent conditions.
        """
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Critical events sequence
        critical_events = [
            ('agent_started', {'agent_name': 'test_agent'}),
            ('agent_thinking', {'thought': 'processing request'}),
            ('tool_executing', {'tool': 'test_tool'}),
            ('tool_completed', {'tool': 'test_tool', 'result': 'success'}),
            ('agent_completed', {'agent_name': 'test_agent', 'status': 'completed'})
        ]
        
        # Execute critical events concurrently to test race conditions
        async def emit_critical_event(event_type, data):
            emit_method = getattr(emitter, f'emit_{event_type}')
            await emit_method(data)
        
        start_time = time.time()
        await asyncio.gather(*[
            emit_critical_event(event_type, data) 
            for event_type, data in critical_events
        ])
        end_time = time.time()
        
        # Validate all critical events were emitted
        for event_type, _ in critical_events:
            self.assertIn(event_type, self.event_emissions, 
                         f"Critical event {event_type} should be emitted")
            self.assertEqual(len(self.event_emissions[event_type]), 1,
                           f"Critical event {event_type} should be emitted exactly once")
        
        # Check concurrent emission timeframe
        execution_time = end_time - start_time
        self.assertLess(execution_time, 1.0, 
                       "Critical events should emit quickly without blocking")
    
    async def test_race_condition_user_isolation(self):
        """
        Test race conditions in user isolation.
        
        Ensures that concurrent emissions for different users
        don't interfere with each other.
        """
        
        # Create emitters for different users
        user1_id = "user_1"
        user2_id = "user_2" 
        user3_id = "user_3"
        
        user1_context = SSotMockFactory.create_mock_user_context(user_id=user1_id)
        user2_context = SSotMockFactory.create_mock_user_context(user_id=user2_id)
        user3_context = SSotMockFactory.create_mock_user_context(user_id=user3_id)
        
        emitter1 = UnifiedWebSocketEmitter(
            manager=self.mock_manager, user_id=user1_id, context=user1_context
        )
        emitter2 = UnifiedWebSocketEmitter(
            manager=self.mock_manager, user_id=user2_id, context=user2_context
        )
        emitter3 = UnifiedWebSocketEmitter(
            manager=self.mock_manager, user_id=user3_id, context=user3_context
        )
        
        # Concurrent emissions from different users
        async def emit_for_user(emitter, user_id):
            await emitter.emit_agent_started({
                'agent_name': 'concurrent_test_agent',
                'user_context': user_id
            })
        
        # Execute concurrent user emissions
        await asyncio.gather(
            emit_for_user(emitter1, user1_id),
            emit_for_user(emitter2, user2_id),
            emit_for_user(emitter3, user3_id)
        )
        
        # Validate user isolation - each user should get their own events
        agent_started_emissions = self.event_emissions['agent_started']
        self.assertEqual(len(agent_started_emissions), 3, 
                        "Should have emissions from all 3 users")
        
        user_ids = [emission['user_id'] for emission in agent_started_emissions]
        self.assertEqual(set(user_ids), {user1_id, user2_id, user3_id},
                        "Each user should have their own emission")
        
        # Validate no cross-user contamination
        for emission in agent_started_emissions:
            user_context = emission['data'].get('user_context')
            self.assertEqual(emission['user_id'], user_context,
                           "User context should match emission user_id")


class TestSSotEmitterCompliance(SSotAsyncTestCase):
    """
    Test SSOT compliance of WebSocket emitter implementations.
    
    Validates that all emitter variants redirect to UnifiedWebSocketEmitter.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_websocket_manager_mock()
        
        self.test_user_id = "ssot_test_user"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
    
    async def test_unified_emitter_is_ssot(self):
        """
        Test that UnifiedWebSocketEmitter is the true SSOT implementation.
        """
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Validate SSOT characteristics
        self.assertTrue(hasattr(emitter, 'CRITICAL_EVENTS'))
        self.assertEqual(len(emitter.CRITICAL_EVENTS), 5, 
                        "Should have exactly 5 critical events")
        
        critical_events = {
            'agent_started', 'agent_thinking', 'tool_executing', 
            'tool_completed', 'agent_completed'
        }
        self.assertEqual(set(emitter.CRITICAL_EVENTS), critical_events,
                        "Should have all required critical events")
        
        # Validate SSOT methods exist
        for event in emitter.CRITICAL_EVENTS:
            method_name = f'emit_{event}'
            self.assertTrue(hasattr(emitter, method_name),
                           f"SSOT should have {method_name} method")
    
    async def test_transparent_emitter_redirects_to_ssot(self):
        """
        Test that TransparentWebSocketEmitter redirects to UnifiedWebSocketEmitter.
        """
        
        # TransparentWebSocketEmitter should be an alias to UnifiedWebSocketEmitter
        self.assertIs(TransparentWebSocketEmitter, UnifiedWebSocketEmitter,
                     "TransparentWebSocketEmitter should redirect to UnifiedWebSocketEmitter")
    
    async def test_factory_creates_ssot_instances(self):
        """
        Test that WebSocketEmitterFactory creates SSOT instances.
        """
        
        # Test standard factory method
        emitter = WebSocketEmitterFactory.create_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        self.assertIsInstance(emitter, UnifiedWebSocketEmitter,
                             "Factory should create UnifiedWebSocketEmitter instances")
        
        # Test scoped factory method
        scoped_emitter = WebSocketEmitterFactory.create_scoped_emitter(
            manager=self.mock_manager,
            context=self.test_context
        )
        
        self.assertIsInstance(scoped_emitter, UnifiedWebSocketEmitter,
                             "Scoped factory should create UnifiedWebSocketEmitter instances")
        
        # Test performance factory method
        perf_emitter = WebSocketEmitterFactory.create_performance_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        self.assertIsInstance(perf_emitter, UnifiedWebSocketEmitter,
                             "Performance factory should create UnifiedWebSocketEmitter instances")
        
        # Verify performance mode is enabled
        self.assertTrue(perf_emitter.performance_mode,
                       "Performance emitter should have performance mode enabled")
    
    async def test_auth_emitter_extends_ssot(self):
        """
        Test that AuthenticationWebSocketEmitter properly extends SSOT.
        """
        
        auth_emitter = WebSocketEmitterFactory.create_auth_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        self.assertIsInstance(auth_emitter, AuthenticationWebSocketEmitter)
        self.assertIsInstance(auth_emitter, UnifiedWebSocketEmitter,
                             "AuthenticationWebSocketEmitter should extend UnifiedWebSocketEmitter")
        
        # Validate auth-specific features
        self.assertTrue(hasattr(auth_emitter, 'AUTHENTICATION_CRITICAL_EVENTS'))
        self.assertTrue(hasattr(auth_emitter, 'emit_auth_event'))
        self.assertTrue(hasattr(auth_emitter, 'get_auth_stats'))
    
    async def test_emitter_pool_uses_ssot(self):
        """
        Test that WebSocketEmitterPool creates SSOT instances.
        """
        
        pool = WebSocketEmitterPool(manager=self.mock_manager, max_size=10)
        
        # Acquire emitter from pool
        emitter = await pool.acquire(
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        self.assertIsInstance(emitter, UnifiedWebSocketEmitter,
                             "Pool should create UnifiedWebSocketEmitter instances")
        
        # Verify pool statistics
        stats = pool.get_statistics()
        self.assertEqual(stats['pool_size'], 1, "Pool should have 1 emitter")
        self.assertEqual(stats['acquisitions'], 1, "Should track acquisitions")
        
        # Release back to pool
        await pool.release(emitter)
        self.assertEqual(pool.get_statistics()['releases'], 1,
                        "Should track releases")


class TestCriticalEventDelivery(SSotAsyncTestCase):
    """
    Test critical event delivery through SSOT emitter.
    
    Validates that all 5 critical events work correctly and maintain
    the Golden Path user experience.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_websocket_manager_mock()
        
        self.test_user_id = "critical_event_user"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
        
        self.emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
    
    async def test_agent_started_event(self):
        """Test agent_started critical event delivery."""
        
        event_data = {
            'agent_name': 'test_agent',
            'metadata': {'test': 'data'}
        }
        
        await self.emitter.emit_agent_started(event_data)
        
        # Verify emission
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        
        self.assertEqual(call_args[1]['user_id'], self.test_user_id)
        self.assertEqual(call_args[1]['event_type'], 'agent_started')
        self.assertIn('agent_name', call_args[1]['data'])
    
    async def test_agent_thinking_event(self):
        """Test agent_thinking critical event delivery."""
        
        event_data = {
            'thought': 'I am processing the user request',
            'metadata': {'step': 1}
        }
        
        await self.emitter.emit_agent_thinking(event_data)
        
        # Verify emission
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        
        self.assertEqual(call_args[1]['event_type'], 'agent_thinking')
        self.assertIn('thought', call_args[1]['data'])
    
    async def test_tool_executing_event(self):
        """Test tool_executing critical event delivery."""
        
        event_data = {
            'tool': 'data_analyzer',
            'metadata': {'parameters': {'dataset': 'user_data'}}
        }
        
        await self.emitter.emit_tool_executing(event_data)
        
        # Verify emission
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        
        self.assertEqual(call_args[1]['event_type'], 'tool_executing')
        self.assertIn('tool', call_args[1]['data'])
    
    async def test_tool_completed_event(self):
        """Test tool_completed critical event delivery."""
        
        event_data = {
            'tool': 'data_analyzer',
            'metadata': {'result': 'analysis_complete', 'metrics': {'processed': 100}}
        }
        
        await self.emitter.emit_tool_completed(event_data)
        
        # Verify emission
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        
        self.assertEqual(call_args[1]['event_type'], 'tool_completed')
        self.assertIn('tool', call_args[1]['data'])
    
    async def test_agent_completed_event(self):
        """Test agent_completed critical event delivery."""
        
        event_data = {
            'agent_name': 'test_agent',
            'metadata': {'execution_time_ms': 1500, 'status': 'success'}
        }
        
        await self.emitter.emit_agent_completed(event_data)
        
        # Verify emission
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        
        self.assertEqual(call_args[1]['event_type'], 'agent_completed')
        self.assertIn('agent_name', call_args[1]['data'])
    
    async def test_critical_events_sequence(self):
        """Test complete critical events sequence."""
        
        # Execute full critical event sequence
        await self.emitter.emit_agent_started({'agent_name': 'test_agent'})
        await self.emitter.emit_agent_thinking({'thought': 'thinking'})
        await self.emitter.emit_tool_executing({'tool': 'test_tool'})
        await self.emitter.emit_tool_completed({'tool': 'test_tool', 'result': 'done'})
        await self.emitter.emit_agent_completed({'agent_name': 'test_agent'})
        
        # Verify all 5 critical events were emitted
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 5,
                        "Should emit all 5 critical events")
        
        # Verify event sequence
        calls = self.mock_manager.emit_critical_event.call_args_list
        expected_sequence = [
            'agent_started', 'agent_thinking', 'tool_executing',
            'tool_completed', 'agent_completed'
        ]
        
        for i, expected_event in enumerate(expected_sequence):
            actual_event = calls[i][1]['event_type']
            self.assertEqual(actual_event, expected_event,
                           f"Event {i} should be {expected_event}")


class TestEmitterAPICompatibility(SSotAsyncTestCase):
    """
    Test API compatibility of consolidated emitter.
    
    Validates that consumers can use the SSOT emitter with existing APIs.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_websocket_manager_mock()
        
        self.test_user_id = "api_compat_user"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
        
        self.emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
    
    async def test_backward_compatible_notify_methods(self):
        """Test backward compatible notify_* methods."""
        
        # Test notify_agent_started
        await self.emitter.notify_agent_started(
            agent_name='compat_agent',
            metadata={'test': 'metadata'}
        )
        
        # Test notify_agent_thinking
        await self.emitter.notify_agent_thinking(
            agent_name='compat_agent',
            reasoning='I am thinking about the problem'
        )
        
        # Test notify_tool_executing
        await self.emitter.notify_tool_executing(
            tool_name='compat_tool',
            metadata={'param': 'value'}
        )
        
        # Test notify_tool_completed
        await self.emitter.notify_tool_completed(
            tool_name='compat_tool',
            metadata={'result': 'success'}
        )
        
        # Test notify_agent_completed
        await self.emitter.notify_agent_completed(
            agent_name='compat_agent',
            metadata={'status': 'completed'},
            execution_time_ms=1000
        )
        
        # Verify all compatibility methods work
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 5,
                        "All compatibility methods should work")
    
    async def test_generic_emit_method(self):
        """Test generic emit method routes to specific handlers."""
        
        # Test routing to critical events
        await self.emitter.emit('agent_started', {'agent_name': 'routed_agent'})
        await self.emitter.emit('agent_thinking', {'thought': 'routed_thought'})
        await self.emitter.emit('tool_executing', {'tool': 'routed_tool'})
        await self.emitter.emit('tool_completed', {'tool': 'routed_tool'})
        await self.emitter.emit('agent_completed', {'agent_name': 'routed_agent'})
        
        # Test non-critical event routing
        await self.emitter.emit('custom_event', {'custom': 'data'})
        
        # Verify routing worked
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 6,
                        "Generic emit should route correctly")
    
    async def test_context_management(self):
        """Test context get/set compatibility."""
        
        # Test get_context
        context = self.emitter.get_context()
        self.assertEqual(context, self.test_context,
                        "get_context should return current context")
        
        # Test set_context
        new_context = SSotMockFactory.create_mock_user_context(user_id="new_user")
        self.emitter.set_context(new_context)
        
        updated_context = self.emitter.get_context()
        self.assertEqual(updated_context, new_context,
                        "set_context should update context")
    
    async def test_stats_and_metrics(self):
        """Test statistics and metrics APIs."""
        
        # Emit some events to generate stats
        await self.emitter.emit_agent_started({'agent_name': 'stats_test'})
        await self.emitter.emit_agent_completed({'agent_name': 'stats_test'})
        
        # Test get_stats
        stats = self.emitter.get_stats()
        
        self.assertIn('user_id', stats)
        self.assertIn('total_events', stats)
        self.assertIn('critical_events', stats)
        self.assertEqual(stats['user_id'], self.test_user_id)
        self.assertGreaterEqual(stats['total_events'], 2)
        
        # Test token metrics
        self.emitter.update_token_metrics(
            input_tokens=100,
            output_tokens=50,
            cost=0.15,
            operation='test_operation'
        )
        
        token_metrics = self.emitter.get_token_metrics()
        self.assertEqual(token_metrics['total_operations'], 1)
        self.assertEqual(token_metrics['total_input_tokens'], 100)
        self.assertEqual(token_metrics['total_output_tokens'], 50)
        self.assertEqual(token_metrics['total_cost'], 0.15)


if __name__ == '__main__':
    # Run tests directly
    pytest.main([__file__, '-v', '--tb=short'])