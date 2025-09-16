"""Integration tests for Issue #1176 - Factory Pattern Integration Conflicts (Non-Docker)

TARGET: Factory Pattern Integration Conflicts - Component Integration Issues

This module tests factory pattern integration conflicts at the integration level
without requiring Docker infrastructure. These tests focus on how different factory
patterns fail to integrate correctly between agents, WebSocket managers, and
execution engines.

Key Integration Conflicts Being Tested:
1. Agent factory + WebSocket manager integration failures  
2. ExecutionEngineFactory + StandardWebSocketBridge integration conflicts
3. Factory pattern interface mismatches during component initialization
4. Cross-component factory dependency injection failures

These tests are designed to FAIL initially to prove the integration conflicts exist.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: System Stability & SSOT Compliance
- Value Impact: Ensures factory patterns work together across component boundaries
- Strategic Impact: Protects $500K+ ARR by preventing integration cascade failures
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, Optional

# Import SSOT BaseTestCase for proper test infrastructure
try:
    from test_framework.ssot.base_test_case import SSotBaseTestCase
except ImportError:
    # Fallback for environments without SSOT test framework
    SSotBaseTestCase = object
    
# Import components for integration testing
try:
    from netra_backend.app.factories.websocket_bridge_factory import (
        StandardWebSocketBridge,
        create_standard_websocket_bridge,
        create_agent_bridge_adapter,
        create_emitter_bridge_adapter
    )
except ImportError as e:
    pytest.skip(f"WebSocket bridge factory not available: {e}", allow_module_level=True)

try:
    from netra_backend.app.agents.supervisor.execution_engine_factory import (
        ExecutionEngineFactory,
        configure_execution_engine_factory,
        get_execution_engine_factory
    )
except ImportError as e:
    pytest.skip(f"Execution engine factory not available: {e}", allow_module_level=True)

try:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
except ImportError as e:
    pytest.skip(f"User execution engine not available: {e}", allow_module_level=True)

try:
    from netra_backend.app.services.user_execution_context import (
        UserExecutionContext,
        create_user_execution_context
    )
except ImportError:
    UserExecutionContext = None

try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
except ImportError:
    AgentWebSocketBridge = None

try:
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
except ImportError:
    UnifiedWebSocketEmitter = None


@pytest.mark.integration
class AgentFactoryWebSocketManagerIntegrationTests(SSotBaseTestCase):
    """Test agent factory and WebSocket manager integration conflicts."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        if hasattr(super(), 'asyncSetUp'):
            await super().asyncSetUp()
        
        # Create test user context
        self.user_context = Mock()
        self.user_context.user_id = "test-user-123"
        self.user_context.run_id = "test-run-456"
        self.user_context.session_id = "test-session-789"
        self.user_context.get_correlation_id.return_value = "test-user-123:test-run-456"
        
        # Mock infrastructure components
        self.mock_database_manager = Mock()
        self.mock_redis_manager = Mock()
    
    @pytest.mark.asyncio
    async def test_execution_engine_factory_standard_bridge_integration_conflict(self):
        """Test ExecutionEngineFactory integration with StandardWebSocketBridge.
        
        This test exposes integration conflicts when ExecutionEngineFactory
        tries to integrate with StandardWebSocketBridge instead of expected 
        AgentWebSocketBridge, causing initialization and runtime failures.
        """
        # Create StandardWebSocketBridge 
        standard_bridge = StandardWebSocketBridge(self.user_context)
        
        # Try to create ExecutionEngineFactory with StandardWebSocketBridge
        # This should cause integration conflicts since factory expects AgentWebSocketBridge
        try:
            factory = ExecutionEngineFactory(
                websocket_bridge=standard_bridge,  # Wrong type - should cause conflict
                database_session_manager=self.mock_database_manager,
                redis_manager=self.mock_redis_manager
            )
            
            # If factory creation succeeds, try to create engine - should expose conflicts
            engine = await factory.create_for_user(self.user_context)
            
            # If engine creation succeeds, there's no integration conflict
            assert False, "ExecutionEngineFactory integrated with StandardWebSocketBridge without conflicts"
            
        except (TypeError, AttributeError, ValueError) as e:
            # Expected - StandardWebSocketBridge should cause integration conflicts
            self.assertIn("websocket", str(e).lower())
    
    @pytest.mark.asyncio  
    async def test_user_execution_engine_websocket_emitter_integration_conflict(self):
        """Test UserExecutionEngine integration with WebSocket emitter conflicts.
        
        This test exposes conflicts when UserExecutionEngine receives WebSocket
        emitters that don't match expected interfaces or parameter signatures.
        """
        # Create ExecutionEngineFactory without WebSocket bridge (test mode)
        factory = ExecutionEngineFactory(
            websocket_bridge=None,  # Test mode - should create fallback emitter
            database_session_manager=self.mock_database_manager,
            redis_manager=self.mock_redis_manager
        )
        
        # Create WebSocket emitter through factory method
        emitter = await factory._create_user_websocket_emitter(
            context=self.user_context,
            agent_factory=None
        )
        
        # Test emitter integration with UserExecutionEngine
        try:
            # Create mock agent factory
            mock_agent_factory = Mock()
            mock_agent_factory.create_agent_instance = AsyncMock(return_value=Mock())
            
            # Try to create UserExecutionEngine with test emitter
            engine = UserExecutionEngine(
                context=self.user_context,
                agent_factory=mock_agent_factory,
                websocket_emitter=emitter
            )
            
            # Test that engine can use emitter without conflicts
            # This should expose interface or parameter conflicts
            result = await engine.websocket_emitter.notify_agent_started(
                run_id=self.user_context.run_id,
                agent_name="test-agent",
                context={}
            )
            
            # If emitter works without conflicts, test should fail initially
            if result is True:
                assert False, "WebSocket emitter integration works without conflicts"
            
        except (AttributeError, TypeError) as e:
            # Expected - emitter integration should have conflicts
            self.assertIn("websocket", str(e).lower())
    
    @pytest.mark.asyncio
    async def test_agent_bridge_adapter_factory_integration_conflict(self):
        """Test agent bridge adapter factory integration conflicts.
        
        This test exposes conflicts when create_agent_bridge_adapter tries to
        integrate with components that expect different WebSocket interfaces.
        """
        # Create mock AgentWebSocketBridge
        mock_agent_bridge = Mock(spec=AgentWebSocketBridge if AgentWebSocketBridge else object)
        mock_agent_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_agent_bridge.notify_agent_thinking = AsyncMock(return_value=True)
        mock_agent_bridge.notify_tool_executing = AsyncMock(return_value=True)
        mock_agent_bridge.notify_tool_completed = AsyncMock(return_value=True)
        mock_agent_bridge.notify_agent_completed = AsyncMock(return_value=True)
        
        # Create agent bridge adapter
        adapter = create_agent_bridge_adapter(mock_agent_bridge, self.user_context)
        
        # Test adapter integration with ExecutionEngineFactory
        try:
            factory = ExecutionEngineFactory(
                websocket_bridge=adapter,  # Use adapter instead of raw bridge
                database_session_manager=self.mock_database_manager,
                redis_manager=self.mock_redis_manager
            )
            
            # Try to create engine - should expose adapter integration conflicts
            engine = await factory.create_for_user(self.user_context)
            
            # If adapter integration works, there's no conflict
            assert False, "Agent bridge adapter integrated without conflicts"
            
        except (TypeError, AttributeError) as e:
            # Expected - adapter should have integration conflicts with factory
            self.assertIn("websocket", str(e).lower())
    
    @pytest.mark.asyncio
    async def test_emitter_bridge_adapter_integration_conflict(self):
        """Test emitter bridge adapter integration conflicts.
        
        This test exposes conflicts when create_emitter_bridge_adapter creates
        adapters that can't integrate properly with agent execution systems.
        """
        # Create mock WebSocket emitter
        mock_emitter = Mock(spec=UnifiedWebSocketEmitter if UnifiedWebSocketEmitter else object)
        mock_emitter.notify_agent_started = AsyncMock(return_value=True)
        mock_emitter.notify_agent_thinking = AsyncMock(return_value=True)
        mock_emitter.notify_tool_executing = AsyncMock(return_value=True)
        mock_emitter.notify_tool_completed = AsyncMock(return_value=True)
        mock_emitter.notify_agent_completed = AsyncMock(return_value=True)
        
        # Create emitter bridge adapter
        adapter = create_emitter_bridge_adapter(mock_emitter, self.user_context)
        
        # Test adapter metrics and diagnostics integration
        try:
            # Get bridge metrics - should work for integration
            metrics = adapter.get_bridge_metrics()
            self.assertIsInstance(metrics, dict)
            
            # Get bridge health - should work for monitoring integration  
            health = adapter.diagnose_bridge_health()
            self.assertIsInstance(health, dict)
            
            # Test adapter event delivery integration
            result = await adapter.notify_agent_started(
                run_id=self.user_context.run_id,
                agent_name="test-agent",
                context={}
            )
            
            # If adapter works seamlessly, there's no integration conflict
            if result is True and health['status'] == 'healthy':
                assert False, "Emitter bridge adapter integrated without conflicts"
            
        except (AttributeError, KeyError, TypeError) as e:
            # Expected - adapter should have integration conflicts
            self.assertIn("bridge", str(e).lower())


@pytest.mark.integration
class FactoryPatternCrossComponentIntegrationTests(SSotBaseTestCase):
    """Test factory pattern cross-component integration conflicts."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        if hasattr(super(), 'asyncSetUp'):
            await super().asyncSetUp()
        
        # Create test user context
        self.user_context = Mock()
        self.user_context.user_id = "test-user-123"
        self.user_context.run_id = "test-run-456"
        self.user_context.session_id = "test-session-789"
        self.user_context.get_correlation_id.return_value = "test-user-123:test-run-456"
    
    @pytest.mark.asyncio
    async def test_factory_dependency_injection_integration_conflict(self):
        """Test factory dependency injection integration conflicts.
        
        This test exposes conflicts when factory patterns inject dependencies
        that don't match the expected interfaces of receiving components.
        """
        # Create standard WebSocket bridge
        standard_bridge = create_standard_websocket_bridge(self.user_context)
        
        # Configure with mock WebSocket emitter
        mock_emitter = Mock()
        mock_emitter.notify_agent_started = AsyncMock(return_value=True)
        standard_bridge.set_websocket_emitter(mock_emitter)
        
        # Test dependency injection conflicts
        try:
            # Try to configure ExecutionEngineFactory with StandardWebSocketBridge
            factory = await configure_execution_engine_factory(
                websocket_bridge=standard_bridge,  # Wrong type injection
                database_session_manager=None,
                redis_manager=None
            )
            
            # If configuration succeeds, test engine creation
            engine = await factory.create_for_user(self.user_context)
            
            # If everything works, there's no dependency injection conflict
            assert False, "Factory dependency injection works without conflicts"
            
        except (TypeError, AttributeError, ValueError) as e:
            # Expected - dependency injection should cause conflicts
            self.assertIn("websocket", str(e).lower())
    
    @pytest.mark.asyncio
    async def test_cross_component_factory_initialization_conflict(self):
        """Test cross-component factory initialization conflicts.
        
        This test exposes conflicts when different factory patterns initialize
        components with incompatible parameters or interfaces.
        """
        # Create ExecutionEngineFactory in test mode
        factory = ExecutionEngineFactory(
            websocket_bridge=None,  # Test mode
            database_session_manager=None,
            redis_manager=None
        )
        
        # Test cross-component initialization
        try:
            # Create engine - this should create test WebSocket emitter
            engine = await factory.create_for_user(self.user_context)
            
            # Test that engine components can interact without conflicts
            self.assertIsNotNone(engine.websocket_emitter)
            self.assertIsNotNone(engine.get_user_context())
            
            # Test component interaction - should expose interface conflicts
            result = await engine.websocket_emitter.notify_agent_started(
                run_id=self.user_context.run_id,
                agent_name="test-agent",
                context={}
            )
            
            # If all components work together, there's no initialization conflict
            if result is not False:  # Could be True or None, both indicate success
                assert False, "Cross-component factory initialization works without conflicts"
            
        except (AttributeError, TypeError) as e:
            # Expected - initialization should cause cross-component conflicts
            self.assertIn("initialization", str(e).lower())
    
    @pytest.mark.asyncio
    async def test_factory_pattern_interface_compatibility_conflict(self):
        """Test factory pattern interface compatibility conflicts.
        
        This test exposes conflicts when factory patterns create components
        with interfaces that are incompatible with each other.
        """
        # Test StandardWebSocketBridge interface compatibility
        bridge = StandardWebSocketBridge(self.user_context)
        
        # Test different adapter patterns for interface conflicts
        adapters = []
        
        # Create mock adapters with slightly different interfaces
        mock_agent_bridge = Mock()
        mock_agent_bridge.notify_agent_started = AsyncMock(return_value=True)
        bridge.set_agent_bridge(mock_agent_bridge)
        adapters.append(("AgentWebSocketBridge", bridge.get_active_adapter_type()))
        
        mock_emitter = Mock()  
        mock_emitter.notify_agent_started = AsyncMock(return_value=False)  # Different return
        bridge.set_websocket_emitter(mock_emitter)
        adapters.append(("WebSocketEventEmitter", bridge.get_active_adapter_type()))
        
        mock_manager = Mock()
        mock_manager.send_event = AsyncMock(side_effect=AttributeError("Method not found"))
        bridge.set_websocket_manager(mock_manager)
        adapters.append(("UnifiedWebSocketManager", bridge.get_active_adapter_type()))
        
        # Test that adapter switches indicate interface conflicts
        metrics = bridge.get_bridge_metrics()
        adapter_switches = metrics.get('adapter_switches', 0)
        
        # If no adapter switches occurred, interfaces are compatible
        if adapter_switches == 0:
            assert False, "Factory pattern interfaces are compatible - no conflicts detected"
        
        # Test interface compatibility by calling methods
        try:
            result = await bridge.notify_agent_started(
                run_id=self.user_context.run_id,
                agent_name="test-agent", 
                context={}
            )
            
            # If call succeeds, interface is compatible
            if result is not False:
                assert False, "Factory pattern interfaces are compatible"
            
        except Exception as e:
            # Expected - interface incompatibility should cause errors
            self.assertIn("interface", str(e).lower())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])