"""WebSocket Emitter SSOT Compliance Tests

MISSION CRITICAL: Validate Issue #200 SSOT consolidation compliance.
Ensures all WebSocket emitter implementations redirect to UnifiedWebSocketEmitter
to prevent race conditions and maintain Golden Path reliability.

NON-DOCKER TESTS ONLY: These tests run without Docker orchestration requirements.

Test Strategy:
1. Import Validation - Verify imports redirect to SSOT
2. Instance Validation - Verify all instances are SSOT types
3. Method Validation - Verify SSOT methods are available
4. Emission Source Validation - Track emission sources

Business Impact: Protects $500K+ ARR chat functionality from race conditions.
"""

import pytest
import inspect
import importlib
from typing import Dict, List, Any, Type
from unittest.mock import AsyncMock, MagicMock, patch

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# SSOT imports to validate against
from netra_backend.app.websocket_core.unified_emitter import (
    UnifiedWebSocketEmitter,
    WebSocketEmitterFactory,
    AuthenticationWebSocketEmitter,
    WebSocketEmitterPool
)


class TestEmitterImportCompliance(SSotAsyncTestCase):
    """
    Test that all WebSocket emitter imports redirect to SSOT.
    
    Validates Issue #200 requirement that multiple emitter sources
    are eliminated and all imports redirect to unified_emitter.py.
    """
    
    def test_transparent_emitter_import_redirection(self):
        """
        Test that transparent_websocket_events redirects to SSOT.
        """
        
        # Import the transparent module
        from netra_backend.app.services.websocket.transparent_websocket_events import (
            TransparentWebSocketEmitter,
            TransparentWebSocketEvents
        )
        
        # Validate redirection to SSOT
        self.assertIs(TransparentWebSocketEmitter, UnifiedWebSocketEmitter,
                     "TransparentWebSocketEmitter should redirect to UnifiedWebSocketEmitter")
        
        self.assertIs(TransparentWebSocketEvents, UnifiedWebSocketEmitter,
                     "TransparentWebSocketEvents should redirect to UnifiedWebSocketEmitter")
    
    def test_agent_websocket_bridge_import_redirection(self):
        """
        Test that agent_websocket_bridge imports SSOT components.
        """
        
        # Import the bridge module
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Check that the module imports from unified_emitter
        import netra_backend.app.services.agent_websocket_bridge as bridge_module
        
        # Verify imports redirect to SSOT
        source_lines = inspect.getsource(bridge_module)
        
        self.assertIn('from netra_backend.app.websocket_core.unified_emitter import',
                     source_lines,
                     "agent_websocket_bridge should import from unified_emitter")
        
        self.assertIn('WebSocketEmitterFactory',
                     source_lines,
                     "agent_websocket_bridge should use WebSocketEmitterFactory")
    
    def test_base_agent_import_redirection(self):
        """
        Test that base_agent imports SSOT components.
        """
        
        # Import base agent module
        import netra_backend.app.agents.base_agent as base_agent_module
        
        # Verify imports redirect to SSOT
        source_lines = inspect.getsource(base_agent_module)
        
        # Should import from unified_emitter for WebSocket functionality
        self.assertIn('WebSocketEmitterFactory',
                     source_lines,
                     "base_agent should use WebSocketEmitterFactory from SSOT")
    
    def test_no_direct_emitter_implementations(self):
        """
        Test that no duplicate emitter class implementations exist.
        
        Validates that only UnifiedWebSocketEmitter contains the actual
        implementation and all others are redirections.
        """
        
        # Check transparent_websocket_events has no class definitions
        import netra_backend.app.services.websocket.transparent_websocket_events as transparent_module
        
        source_lines = inspect.getsource(transparent_module)
        
        # Should not define its own emitter classes
        self.assertNotIn('class TransparentWebSocketEmitter(',
                        source_lines,
                        "transparent_websocket_events should not define its own emitter class")
        
        # Should redirect via import alias
        self.assertIn('from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as TransparentWebSocketEmitter',
                     source_lines,
                     "Should redirect via import alias")


class TestEmitterInstanceCompliance(SSotAsyncTestCase):
    """
    Test that all emitter instances are SSOT types.
    
    Validates that factory methods and direct instantiation
    create proper SSOT instances.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_mock_websocket_manager()
        self.mock_manager.emit_critical_event = AsyncMock()
        self.mock_manager.is_connection_active.return_value = True
        
        self.test_user_id = "ssot_instance_user"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
    
    def test_factory_creates_ssot_instances(self):
        """Test that all factory methods create SSOT instances."""
        
        # Test create_emitter
        emitter = WebSocketEmitterFactory.create_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        self.assertIsInstance(emitter, UnifiedWebSocketEmitter,
                             "create_emitter should return UnifiedWebSocketEmitter")
        
        # Test create_scoped_emitter
        scoped_emitter = WebSocketEmitterFactory.create_scoped_emitter(
            manager=self.mock_manager,
            context=self.test_context
        )
        
        self.assertIsInstance(scoped_emitter, UnifiedWebSocketEmitter,
                             "create_scoped_emitter should return UnifiedWebSocketEmitter")
        
        # Test create_performance_emitter
        perf_emitter = WebSocketEmitterFactory.create_performance_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        self.assertIsInstance(perf_emitter, UnifiedWebSocketEmitter,
                             "create_performance_emitter should return UnifiedWebSocketEmitter")
        
        # Test create_auth_emitter
        auth_emitter = WebSocketEmitterFactory.create_auth_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        self.assertIsInstance(auth_emitter, AuthenticationWebSocketEmitter,
                             "create_auth_emitter should return AuthenticationWebSocketEmitter")
        
        # Auth emitter should also be instance of SSOT base
        self.assertIsInstance(auth_emitter, UnifiedWebSocketEmitter,
                             "AuthenticationWebSocketEmitter should extend UnifiedWebSocketEmitter")
    
    def test_direct_instantiation_compliance(self):
        """Test direct instantiation creates proper SSOT instances."""
        
        # Test UnifiedWebSocketEmitter direct instantiation
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        self.assertIsInstance(emitter, UnifiedWebSocketEmitter)
        self.assertEqual(emitter.user_id, self.test_user_id)
        self.assertEqual(emitter.context, self.test_context)
        
        # Test AuthenticationWebSocketEmitter direct instantiation
        auth_emitter = AuthenticationWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        self.assertIsInstance(auth_emitter, AuthenticationWebSocketEmitter)
        self.assertIsInstance(auth_emitter, UnifiedWebSocketEmitter)
    
    async def test_transparent_emitter_factory_compliance(self):
        """Test transparent emitter factory creates SSOT instances."""
        
        from netra_backend.app.services.websocket.transparent_websocket_events import (
            create_transparent_emitter
        )
        
        # Mock the create_websocket_manager function
        with patch('netra_backend.app.websocket_core.create_websocket_manager') as mock_create_manager:
            mock_create_manager.return_value = self.mock_manager
            
            # Create transparent emitter
            transparent_emitter = await create_transparent_emitter(self.test_context)
            
            # Should be SSOT instance
            self.assertIsInstance(transparent_emitter, UnifiedWebSocketEmitter,
                                 "create_transparent_emitter should return UnifiedWebSocketEmitter")
            
            self.assertEqual(transparent_emitter.user_id, self.test_user_id)
            self.assertEqual(transparent_emitter.context, self.test_context)


class TestEmitterMethodCompliance(SSotAsyncTestCase):
    """
    Test that all emitter instances have required SSOT methods.
    
    Validates that the SSOT interface is consistently available
    across all emitter variants.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_mock_websocket_manager()
        self.mock_manager.emit_critical_event = AsyncMock()
        self.mock_manager.is_connection_active.return_value = True
        
        self.test_user_id = "method_compliance_user"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
    
    def test_critical_event_methods_present(self):
        """Test that all critical event methods are present."""
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Critical event methods
        critical_methods = [
            'emit_agent_started',
            'emit_agent_thinking',
            'emit_tool_executing',
            'emit_tool_completed',
            'emit_agent_completed'
        ]
        
        for method_name in critical_methods:
            self.assertTrue(hasattr(emitter, method_name),
                           f"SSOT emitter should have {method_name} method")
            
            method = getattr(emitter, method_name)
            self.assertTrue(callable(method),
                           f"{method_name} should be callable")
    
    def test_backward_compatibility_methods_present(self):
        """Test that backward compatibility methods are present."""
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Backward compatibility methods
        compat_methods = [
            'notify_agent_started',
            'notify_agent_thinking',
            'notify_tool_executing',
            'notify_tool_completed',
            'notify_agent_completed',
            'notify_agent_error',
            'notify_progress_update',
            'notify_custom'
        ]
        
        for method_name in compat_methods:
            self.assertTrue(hasattr(emitter, method_name),
                           f"SSOT emitter should have {method_name} compatibility method")
    
    def test_management_methods_present(self):
        """Test that management methods are present."""
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Management methods
        mgmt_methods = [
            'get_stats',
            'get_context',
            'set_context',
            'cleanup',
            'acquire',
            'release'
        ]
        
        for method_name in mgmt_methods:
            self.assertTrue(hasattr(emitter, method_name),
                           f"SSOT emitter should have {method_name} management method")
    
    def test_auth_emitter_extended_methods(self):
        """Test that auth emitter has extended methods."""
        
        auth_emitter = AuthenticationWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Auth-specific methods
        auth_methods = [
            'emit_auth_event',
            'ensure_auth_connection_health',
            'get_auth_stats'
        ]
        
        for method_name in auth_methods:
            self.assertTrue(hasattr(auth_emitter, method_name),
                           f"Auth emitter should have {method_name} method")
        
        # Should also have all base SSOT methods
        base_methods = ['emit_agent_started', 'emit_agent_thinking']
        for method_name in base_methods:
            self.assertTrue(hasattr(auth_emitter, method_name),
                           f"Auth emitter should have base {method_name} method")


class TestEmissionSourceCompliance(SSotAsyncTestCase):
    """
    Test emission source compliance.
    
    Validates that all emissions go through the SSOT manager
    and no duplicate emission sources exist.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_mock_websocket_manager()
        self.mock_manager.emit_critical_event = AsyncMock()
        self.mock_manager.is_connection_active.return_value = True
        
        self.test_user_id = "emission_source_user"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
        
        # Track emission calls
        self.emission_calls = []
        
        async def track_emissions(user_id: str, event_type: str, data: Dict[str, Any]):
            self.emission_calls.append({
                'user_id': user_id,
                'event_type': event_type,
                'data': data,
                'manager': self.mock_manager
            })
        
        self.mock_manager.emit_critical_event.side_effect = track_emissions
    
    async def test_unified_emitter_emission_source(self):
        """Test that UnifiedWebSocketEmitter emissions go through manager."""
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        await emitter.emit_agent_started({'agent_name': 'test_agent'})
        
        # Verify emission went through SSOT manager
        self.assertEqual(len(self.emission_calls), 1)
        call = self.emission_calls[0]
        
        self.assertEqual(call['user_id'], self.test_user_id)
        self.assertEqual(call['event_type'], 'agent_started')
        self.assertEqual(call['manager'], self.mock_manager)
    
    async def test_transparent_emitter_emission_source(self):
        """Test that transparent emitter emissions go through SSOT."""
        
        from netra_backend.app.services.websocket.transparent_websocket_events import (
            TransparentWebSocketEmitter
        )
        
        # TransparentWebSocketEmitter is aliased to UnifiedWebSocketEmitter
        emitter = TransparentWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        await emitter.emit_agent_thinking({'thought': 'transparent test'})
        
        # Verify emission went through SSOT manager
        self.assertEqual(len(self.emission_calls), 1)
        call = self.emission_calls[0]
        
        self.assertEqual(call['event_type'], 'agent_thinking')
        self.assertEqual(call['manager'], self.mock_manager)
    
    async def test_auth_emitter_emission_source(self):
        """Test that auth emitter emissions go through SSOT."""
        
        auth_emitter = AuthenticationWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        await auth_emitter.emit_agent_completed({'agent_name': 'auth_test'})
        
        # Verify emission went through SSOT manager
        self.assertEqual(len(self.emission_calls), 1)
        call = self.emission_calls[0]
        
        self.assertEqual(call['event_type'], 'agent_completed')
        self.assertEqual(call['manager'], self.mock_manager)
    
    async def test_factory_emitter_emission_source(self):
        """Test that factory-created emitters use SSOT source."""
        
        emitter = WebSocketEmitterFactory.create_emitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        await emitter.emit_tool_executing({'tool': 'factory_test'})
        
        # Verify emission went through SSOT manager
        self.assertEqual(len(self.emission_calls), 1)
        call = self.emission_calls[0]
        
        self.assertEqual(call['event_type'], 'tool_executing')
        self.assertEqual(call['manager'], self.mock_manager)
    
    async def test_no_bypass_emission_sources(self):
        """Test that no emissions bypass the SSOT manager."""
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Test multiple emission methods
        await emitter.emit_agent_started({'agent_name': 'bypass_test'})
        await emitter.notify_agent_thinking(agent_name='bypass_test', reasoning='test')
        await emitter.emit('tool_executing', {'tool': 'bypass_test'})
        await emitter.notify_custom('custom_event', {'custom': 'data'})
        
        # All emissions should go through the same manager
        self.assertEqual(len(self.emission_calls), 4)
        
        for call in self.emission_calls:
            self.assertEqual(call['manager'], self.mock_manager,
                           "All emissions should go through SSOT manager")
            self.assertEqual(call['user_id'], self.test_user_id,
                           "All emissions should have correct user_id")


class TestSSotConfigurationCompliance(SSotAsyncTestCase):
    """
    Test SSOT configuration compliance.
    
    Validates that SSOT emitters have proper configuration
    and maintain consistency across instances.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.mock_manager = SSotMockFactory.create_mock_websocket_manager()
        self.mock_manager.emit_critical_event = AsyncMock()
        self.mock_manager.is_connection_active.return_value = True
        
        self.test_user_id = "config_compliance_user"
        self.test_context = SSotMockFactory.create_mock_user_context(user_id=self.test_user_id)
    
    def test_critical_events_configuration(self):
        """Test that critical events are properly configured."""
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Validate critical events configuration
        self.assertTrue(hasattr(emitter, 'CRITICAL_EVENTS'))
        self.assertIsInstance(emitter.CRITICAL_EVENTS, list)
        self.assertEqual(len(emitter.CRITICAL_EVENTS), 5)
        
        expected_events = {
            'agent_started', 'agent_thinking', 'tool_executing',
            'tool_completed', 'agent_completed'
        }
        self.assertEqual(set(emitter.CRITICAL_EVENTS), expected_events)
    
    def test_retry_configuration(self):
        """Test that retry configuration is properly set."""
        
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Validate retry configuration
        self.assertTrue(hasattr(emitter, 'MAX_RETRIES'))
        self.assertTrue(hasattr(emitter, 'RETRY_BASE_DELAY'))
        self.assertTrue(hasattr(emitter, 'RETRY_MAX_DELAY'))
        
        self.assertGreater(emitter.MAX_RETRIES, 0)
        self.assertGreater(emitter.RETRY_BASE_DELAY, 0)
        self.assertGreater(emitter.RETRY_MAX_DELAY, emitter.RETRY_BASE_DELAY)
    
    def test_performance_mode_configuration(self):
        """Test performance mode configuration."""
        
        # Test normal mode
        normal_emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context,
            performance_mode=False
        )
        
        self.assertFalse(normal_emitter.performance_mode)
        
        # Test performance mode
        perf_emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context,
            performance_mode=True
        )
        
        self.assertTrue(perf_emitter.performance_mode)
        
        # Performance mode should have different retry settings
        self.assertTrue(hasattr(perf_emitter, 'FAST_MODE_MAX_RETRIES'))
        self.assertTrue(hasattr(perf_emitter, 'FAST_MODE_BASE_DELAY'))
    
    def test_auth_configuration_compliance(self):
        """Test authentication emitter configuration."""
        
        auth_emitter = AuthenticationWebSocketEmitter(
            manager=self.mock_manager,
            user_id=self.test_user_id,
            context=self.test_context
        )
        
        # Should have base SSOT configuration
        self.assertTrue(hasattr(auth_emitter, 'CRITICAL_EVENTS'))
        
        # Should have auth-specific configuration
        self.assertTrue(hasattr(auth_emitter, 'AUTHENTICATION_CRITICAL_EVENTS'))
        self.assertIsInstance(auth_emitter.AUTHENTICATION_CRITICAL_EVENTS, list)
        
        # Should have enhanced retry configuration
        self.assertTrue(hasattr(auth_emitter, 'MAX_CRITICAL_RETRIES'))


if __name__ == '__main__':
    # Run tests directly
    pytest.main([__file__, '-v', '--tb=short'])