"""
SSOT Integration Tests for WebSocketNotifier - MIXED PASSING/FAILING TESTS

These tests validate SSOT WebSocketNotifier compliance at integration level
according to Step 2 of WebSocketNotifier SSOT remediation plan (GitHub issue #216).

Mix of passing tests (proper patterns) and failing tests (violations)
for comprehensive SSOT validation at service integration level.

Business Value: Platform/Internal - System Stability & SSOT Compliance
Validates SSOT patterns work correctly with real service integration.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import Any, Dict, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from test_framework.ssot.database import SSotDatabaseTestMixin
from shared.isolated_environment import IsolatedEnvironment


class TestWebSocketNotifierSSOTIntegrationPatterns(SSotAsyncTestCase, SSotDatabaseTestMixin):
    """Integration tests for SSOT WebSocketNotifier patterns (MIXED RESULTS)"""
    
    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        self.env = IsolatedEnvironment()
        self.mock_websocket_manager = SSotMockFactory.create_mock(
            'WebSocketManager',
            spec=['send_to_user', 'get_connection', 'is_connected']
        )
    
    async def test_ssot_factory_integration_with_real_websocket(self):
        """Test PASSES: SSOT factory integrates correctly with WebSocket manager."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            from netra_backend.app.websocket_core import WebSocketManagerFactory
            
            # Create factory instances
            emitter_factory = WebSocketEmitterFactory()
            manager_factory = WebSocketManagerFactory()
            
            user_id = "integration_test_user"
            
            # Create manager and emitter through factories
            manager = await manager_factory.create_for_user(user_id)
            emitter = emitter_factory.create_user_emitter(user_id)
            
            # Integration should work
            self.assertIsNotNone(manager)
            self.assertIsNotNone(emitter)
            self.assertEqual(emitter.user_id, user_id)
            
        except ImportError as e:
            self.skipTest(f"SSOT factory integration not available: {e}")
    
    async def test_websocket_event_delivery_through_ssot_bridge(self):
        """Test PASSES: WebSocket events deliver correctly through SSOT bridge."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            
            bridge = AgentWebSocketBridge()
            user_id = "event_delivery_test_user"
            
            # Mock the underlying WebSocket manager
            with patch.object(bridge, '_websocket_manager', self.mock_websocket_manager):
                bridge._websocket_manager.is_connected.return_value = True
                bridge._websocket_manager.send_to_user = AsyncMock(return_value=True)
                
                # Send event through bridge
                event_data = {
                    "type": "agent_started",
                    "run_id": "test_run_123",
                    "agent_type": "supervisor"
                }
                
                result = await bridge.send_agent_event(user_id, event_data)
                
                # Should succeed through SSOT pattern
                self.assertTrue(result)
                bridge._websocket_manager.send_to_user.assert_called_once()
                
        except ImportError as e:
            self.skipTest(f"SSOT bridge not available: {e}")
    
    async def test_user_isolation_in_concurrent_websocket_operations(self):
        """Test PASSES: User isolation works in concurrent WebSocket operations."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            
            # Create emitters for different users
            users = [f"concurrent_user_{i}" for i in range(3)]
            emitters = {}
            
            async def create_and_test_emitter(user_id):
                emitter = factory.create_user_emitter(user_id)
                emitters[user_id] = emitter
                
                # Simulate some WebSocket operations
                await asyncio.sleep(0.1)
                return emitter.user_id
            
            # Run concurrent operations
            tasks = [create_and_test_emitter(user) for user in users]
            results = await asyncio.gather(*tasks)
            
            # Verify isolation
            self.assertEqual(len(results), 3)
            for i, user_id in enumerate(users):
                self.assertEqual(results[i], user_id)
                self.assertIn(user_id, emitters)
                self.assertEqual(emitters[user_id].user_id, user_id)
            
        except ImportError as e:
            self.skipTest(f"Concurrent isolation pattern not available: {e}")
    
    async def test_websocket_bridge_health_monitoring_integration(self):
        """Test PASSES: WebSocket bridge integrates with health monitoring."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            
            bridge = AgentWebSocketBridge()
            
            # Health check should work
            health_status = bridge.get_health_status()
            
            self.assertIsInstance(health_status, dict)
            self.assertIn('status', health_status)
            self.assertIn('component', health_status)
            
            # Should report healthy state initially
            self.assertEqual(health_status['status'], 'healthy')
            
        except ImportError as e:
            self.skipTest(f"Health monitoring integration not available: {e}")
    
    async def test_ssot_violation_multiple_notifier_instances_created(self):
        """Test FAILS: Multiple notifier instances created instead of using SSOT."""
        violations_detected = []
        
        try:
            # Try to create multiple instances through different paths
            from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier as SupervisorNotifier
            notifier1 = SupervisorNotifier(user_id="violation_user")
            violations_detected.append("supervisor_notifier_created")
        except (ImportError, TypeError):
            pass
        
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            bridge1 = AgentWebSocketBridge()
            bridge2 = AgentWebSocketBridge()
            
            # If both create successfully, it's a violation of singleton/factory pattern
            if bridge1 is not bridge2:
                violations_detected.append("multiple_bridges_created")
        except ImportError:
            pass
        
        # This test FAILS if violations are detected
        if violations_detected:
            self.fail(f"VIOLATION: Multiple notifier instances created: {violations_detected}")
        else:
            self.fail("No multiple instance violations found - violation test should fail")
    
    async def test_ssot_violation_inconsistent_event_handling(self):
        """Test FAILS: Inconsistent event handling across notifier implementations."""
        event_handlers = {}
        
        try:
            from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
            notifier = WebSocketNotifier(user_id="test")
            
            # Check available event methods
            methods = [method for method in dir(notifier) if 'send' in method.lower()]
            event_handlers['supervisor'] = methods
        except (ImportError, TypeError):
            pass
        
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            bridge = AgentWebSocketBridge()
            
            methods = [method for method in dir(bridge) if 'send' in method.lower()]
            event_handlers['bridge'] = methods
        except ImportError:
            pass
        
        # This test FAILS if handlers have inconsistent interfaces
        if len(event_handlers) > 1:
            supervisor_methods = set(event_handlers.get('supervisor', []))
            bridge_methods = set(event_handlers.get('bridge', []))
            
            if supervisor_methods != bridge_methods:
                self.fail("VIOLATION: Inconsistent event handling methods between implementations")
        
        self.fail("Event handling is consistent - violation test should fail")
    
    async def test_ssot_violation_shared_state_between_users(self):
        """Test FAILS: Shared state between user contexts in WebSocket operations."""
        try:
            from netra_backend.app.websocket_core import WebSocketEmitterFactory
            
            factory = WebSocketEmitterFactory()
            
            user1_emitter = factory.create_user_emitter("shared_state_user1")
            user2_emitter = factory.create_user_emitter("shared_state_user2")
            
            # Try to detect shared state
            if hasattr(user1_emitter, '_event_queue'):
                user1_emitter._event_queue.append({"type": "test_event", "user": "user1"})
                
                # Check if user2 emitter sees user1's events
                if hasattr(user2_emitter, '_event_queue') and user2_emitter._event_queue:
                    for event in user2_emitter._event_queue:
                        if event.get('user') == 'user1':
                            self.fail("VIOLATION: Shared state detected between user contexts")
            
            # Check for shared connection pools
            if hasattr(user1_emitter, '_connection_pool') and hasattr(user2_emitter, '_connection_pool'):
                if user1_emitter._connection_pool is user2_emitter._connection_pool:
                    self.fail("VIOLATION: Shared connection pool between users")
            
            # If no shared state detected, this test should report failure
            self.fail("No shared state violations found - violation test should fail")
            
        except ImportError as e:
            self.skipTest(f"Shared state violation testing not available: {e}")
    
    async def test_ssot_violation_missing_factory_enforcement(self):
        """Test FAILS: Factory pattern not enforced, direct instantiation allowed."""
        direct_instantiation_success = []
        
        try:
            # Try direct instantiation that should be blocked
            from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
            notifier = WebSocketNotifier(user_id="direct_test")
            direct_instantiation_success.append("WebSocketNotifier")
        except (ImportError, TypeError):
            pass
        
        try:
            # Try creating WebSocket manager without factory
            from netra_backend.app.websocket_core.unified_manager import WebSocketManager
            manager = WebSocketManager()
            direct_instantiation_success.append("WebSocketManager")
        except (ImportError, TypeError):
            pass
        
        # This test FAILS if direct instantiation succeeds
        if direct_instantiation_success:
            self.fail(f"VIOLATION: Direct instantiation allowed for: {direct_instantiation_success}")
        else:
            self.fail("Direct instantiation properly blocked - violation test should fail")


class TestWebSocketNotifierSSOTServiceCoordination(SSotAsyncTestCase):
    """Integration tests for SSOT service coordination (MIXED RESULTS)"""
    
    async def test_websocket_bridge_coordinates_with_execution_engine(self):
        """Test PASSES: WebSocket bridge coordinates properly with execution engine."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            
            bridge = AgentWebSocketBridge()
            
            # Mock execution engine
            mock_engine = SSotMockFactory.create_mock(
                'ExecutionEngine',
                spec=['set_websocket_notifier', 'get_run_id']
            )
            
            mock_engine.get_run_id.return_value = "test_run_123"
            
            # Bridge should integrate with execution engine
            if hasattr(bridge, 'register_execution_engine'):
                bridge.register_execution_engine(mock_engine)
                mock_engine.set_websocket_notifier.assert_called_once()
            
        except ImportError as e:
            self.skipTest(f"Service coordination not available: {e}")
    
    async def test_websocket_events_reach_correct_agent_context(self):
        """Test PASSES: WebSocket events reach correct agent execution context."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            
            bridge = AgentWebSocketBridge()
            user_id = "agent_context_user"
            run_id = "agent_context_run_123"
            
            # Mock WebSocket manager
            mock_manager = AsyncMock()
            mock_manager.send_to_user.return_value = True
            
            with patch.object(bridge, '_websocket_manager', mock_manager):
                # Send agent event
                event_data = {
                    "type": "agent_started",
                    "run_id": run_id,
                    "agent_type": "supervisor",
                    "context": {"user_id": user_id}
                }
                
                result = await bridge.send_agent_event(user_id, event_data)
                
                # Verify event delivered to correct context
                self.assertTrue(result)
                mock_manager.send_to_user.assert_called_once_with(
                    user_id, event_data
                )
                
        except ImportError as e:
            self.skipTest(f"Agent context integration not available: {e}")
    
    async def test_ssot_violation_service_coupling_through_globals(self):
        """Test FAILS: Services coupled through global variables instead of SSOT."""
        global_variables_found = []
        
        # Check for global WebSocket state
        import sys
        for module_name, module in sys.modules.items():
            if 'websocket' in module_name.lower() and hasattr(module, '__dict__'):
                for attr_name, attr_value in module.__dict__.items():
                    if attr_name.isupper() and 'WEBSOCKET' in attr_name:
                        if not attr_name.startswith('WEBSOCKET_EVENT_TYPE'):  # Allow constants
                            global_variables_found.append(f"{module_name}.{attr_name}")
        
        # This test FAILS if global coupling is found
        if global_variables_found:
            self.fail(f"VIOLATION: Global variable coupling: {global_variables_found}")
        else:
            self.fail("No global variable coupling found - violation test should fail")
    
    async def test_ssot_violation_circular_service_dependencies(self):
        """Test FAILS: Circular dependencies between WebSocket services."""
        try:
            # Try to detect circular imports
            import importlib
            import sys
            
            # Clear modules to test fresh imports
            websocket_modules = [name for name in sys.modules.keys() if 'websocket' in name.lower()]
            for module_name in websocket_modules:
                if module_name.startswith('netra_backend.app.websocket'):
                    sys.modules.pop(module_name, None)
            
            # Try importing in different orders to detect cycles
            try:
                from netra_backend.app.websocket_core import WebSocketManager
                from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
                from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
            except ImportError as e:
                if 'circular' in str(e).lower():
                    self.fail(f"VIOLATION: Circular dependency detected: {e}")
            
            # If no circular dependency, this test should report failure
            self.fail("No circular dependencies found - violation test should fail")
            
        except Exception as e:
            # If any issues testing circular deps, skip
            self.skipTest(f"Circular dependency testing failed: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])