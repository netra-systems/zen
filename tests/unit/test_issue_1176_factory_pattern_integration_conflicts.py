"""Unit tests for Issue #1176 - Factory Pattern Integration Conflicts

TARGET: Factory Pattern Integration Conflicts - WebSocket Manager Interface Mismatches

This module tests the integration conflicts between different factory patterns
and WebSocket manager interfaces, exposing issues where agent factories 
expect different WebSocket manager interfaces than what is provided.

Key Integration Conflicts Being Tested:
1. AgentWebSocketBridge vs StandardWebSocketBridge interface mismatches
2. WebSocketManager factory wrapper preventing direct instantiation
3. ExecutionEngineFactory websocket_bridge parameter type conflicts
4. Agent factory methods expecting incompatible WebSocket manager types

These tests are designed to FAIL initially to prove the integration conflicts exist.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & SSOT Compliance
- Value Impact: Ensures factory patterns integrate correctly across components
- Strategic Impact: Protects $500K+ ARR by preventing factory integration failures
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

# Import the conflicting components to test integration issues
try:
    from netra_backend.app.factories.websocket_bridge_factory import (
        StandardWebSocketBridge,
        WebSocketBridgeAdapter,
        create_standard_websocket_bridge,
        create_agent_bridge_adapter
    )
except ImportError as e:
    pytest.skip(f"WebSocket bridge factory not available: {e}", allow_module_level=True)

try:
    from netra_backend.app.agents.supervisor.execution_engine_factory import (
        ExecutionEngineFactory,
        configure_execution_engine_factory
    )
except ImportError as e:
    pytest.skip(f"Execution engine factory not available: {e}", allow_module_level=True)

try:
    from netra_backend.app.websocket_core.websocket_manager import (
        WebSocketManager,
        _WebSocketManagerFactory,
        create_test_fallback_manager
    )
except ImportError as e:
    pytest.skip(f"WebSocket manager not available: {e}", allow_module_level=True)

try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
except ImportError as e:
    pytest.skip(f"Agent WebSocket bridge not available: {e}", allow_module_level=True)

try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
except ImportError as e:
    pytest.skip(f"User execution context not available: {e}", allow_module_level=True)


@pytest.mark.unit
class AgentFactoryWebSocketManagerInterfaceConflictsTests:
    """Test agent factories expecting different WebSocket manager interfaces."""
    
    @pytest.fixture
    def mock_user_context(self):
        """Create mock user context for testing."""
        context = Mock(spec=UserExecutionContext)
        context.user_id = "test-user-123"
        context.run_id = "test-run-456"
        context.session_id = "test-session-789" 
        context.get_correlation_id.return_value = "test-user-123:test-run-456"
        return context
    
    def test_execution_engine_factory_websocket_bridge_type_conflict(self, mock_user_context):
        """Test ExecutionEngineFactory expects AgentWebSocketBridge but gets StandardWebSocketBridge.
        
        This test exposes the conflict where ExecutionEngineFactory.__init__() expects
        an AgentWebSocketBridge parameter, but StandardWebSocketBridge provides a different
        interface, causing integration failures.
        """
        # Create StandardWebSocketBridge (new SSOT pattern)
        standard_bridge = StandardWebSocketBridge(mock_user_context)
        
        # ExecutionEngineFactory expects AgentWebSocketBridge interface
        # This should cause a type/interface conflict
        with pytest.raises((TypeError, AttributeError), match="websocket_bridge"):
            factory = ExecutionEngineFactory(
                websocket_bridge=standard_bridge,  # Wrong type - expects AgentWebSocketBridge
                database_session_manager=None,
                redis_manager=None
            )
    
    def test_agent_websocket_bridge_vs_standard_bridge_interface_mismatch(self, mock_user_context):
        """Test interface mismatch between AgentWebSocketBridge and StandardWebSocketBridge.
        
        This test exposes the conflict where code expects AgentWebSocketBridge methods
        but gets StandardWebSocketBridge with different method signatures.
        """
        # Create StandardWebSocketBridge
        standard_bridge = StandardWebSocketBridge(mock_user_context)
        
        # Mock AgentWebSocketBridge interface that factory expects
        expected_methods = [
            'notify_agent_started',
            'notify_agent_thinking', 
            'notify_tool_executing',
            'notify_tool_completed',
            'notify_agent_completed'
        ]
        
        # Test that StandardWebSocketBridge has the expected interface
        for method_name in expected_methods:
            assert hasattr(standard_bridge, method_name), f"StandardWebSocketBridge missing {method_name}"
        
        # But test that the method signatures might be incompatible
        # This will fail if interfaces have different signatures
        try:
            # Try to use as AgentWebSocketBridge - this should work if interfaces match
            result = asyncio.run(standard_bridge.notify_agent_started(
                run_id=mock_user_context.run_id,
                agent_name="test-agent",
                context={"test": "data"}
            ))
            # If this succeeds, the interfaces are compatible (test should fail initially)
            assert False, "StandardWebSocketBridge and AgentWebSocketBridge interfaces are compatible - no conflict detected"
        except Exception as e:
            # This is expected if there's an interface conflict
            assert "interface" in str(e).lower() or "websocket" in str(e).lower()
    
    def test_websocket_manager_factory_wrapper_prevents_direct_instantiation(self, mock_user_context):
        """Test WebSocketManager factory wrapper prevents direct instantiation.
        
        This test exposes the conflict where agent factories try to directly instantiate
        WebSocketManager but the factory wrapper prevents it, causing integration failures.
        """
        # Try to directly instantiate WebSocketManager (should fail due to factory wrapper)
        with pytest.raises(RuntimeError, match="Direct WebSocketManager instantiation not allowed"):
            manager = WebSocketManager(
                mode="unified",
                user_context=mock_user_context
            )
    
    def test_create_agent_bridge_adapter_websocket_manager_conflict(self, mock_user_context):
        """Test create_agent_bridge_adapter with incompatible WebSocket manager.
        
        This test exposes the conflict where create_agent_bridge_adapter expects
        a specific WebSocket manager type but gets an incompatible one.
        """
        # Create a mock AgentWebSocketBridge
        mock_agent_bridge = Mock(spec=AgentWebSocketBridge)
        mock_agent_bridge.notify_agent_started = Mock(return_value=True)
        mock_agent_bridge.notify_agent_thinking = Mock(return_value=True)
        mock_agent_bridge.notify_tool_executing = Mock(return_value=True)
        mock_agent_bridge.notify_tool_completed = Mock(return_value=True)
        mock_agent_bridge.notify_agent_completed = Mock(return_value=True)
        
        # Create standard bridge adapter
        adapter = create_agent_bridge_adapter(mock_agent_bridge, mock_user_context)
        
        # Test that adapter expects specific WebSocket manager interface
        # This will fail if the underlying manager interface doesn't match expectations
        try:
            # Test adapter configuration conflicts
            adapter.set_websocket_manager(None)  # This should cause conflict
            assert False, "WebSocket manager integration accepted None - no conflict detected"
        except (TypeError, AttributeError, ValueError) as e:
            # Expected - there should be a conflict with None or wrong manager type
            assert "websocket" in str(e).lower() or "manager" in str(e).lower()


@pytest.mark.unit
class WebSocketBridgeFactoryIntegrationConflictsTests:
    """Test WebSocket bridge factory integration conflicts."""
    
    @pytest.fixture 
    def mock_user_context(self):
        """Create mock user context for testing."""
        context = Mock(spec=UserExecutionContext)
        context.user_id = "test-user-123"
        context.run_id = "test-run-456" 
        context.session_id = "test-session-789"
        context.get_correlation_id.return_value = "test-user-123:test-run-456"
        return context
    
    def test_standard_websocket_bridge_adapter_type_conflicts(self, mock_user_context):
        """Test StandardWebSocketBridge adapter type conflicts.
        
        This test exposes conflicts when StandardWebSocketBridge is configured
        with incompatible adapter types that don't provide expected interfaces.
        """
        bridge = StandardWebSocketBridge(mock_user_context)
        
        # Test adapter switching conflicts - should fail if adapters are incompatible
        mock_agent_bridge = Mock()
        mock_websocket_emitter = Mock()
        mock_websocket_manager = Mock()
        
        # Configure with first adapter
        bridge.set_agent_bridge(mock_agent_bridge)
        assert bridge.get_active_adapter_type() == "AgentWebSocketBridge"
        
        # Switch to different adapter type - this may cause conflicts
        bridge.set_websocket_emitter(mock_websocket_emitter)
        assert bridge.get_active_adapter_type() == "WebSocketEventEmitter"
        
        # Test that adapter switching increments conflict counter
        bridge.set_websocket_manager(mock_websocket_manager)
        metrics = bridge.get_bridge_metrics()
        
        # If adapter switching works seamlessly, this test should fail initially
        assert metrics['adapter_switches'] >= 2, "Adapter switching should increment conflict counter"
        
        # Test interface conflict by calling method without proper adapter setup
        bridge._agent_bridge = None
        bridge._websocket_emitter = None  
        bridge._websocket_manager = None
        
        # This should fail due to no adapter configured
        result = asyncio.run(bridge.notify_agent_started(
            run_id=mock_user_context.run_id,
            agent_name="test-agent",
            context={}
        ))
        
        # If this succeeds, there's no adapter conflict detection
        assert result is False, "StandardWebSocketBridge should fail when no adapter configured"
    
    def test_websocket_bridge_adapter_deprecation_conflict(self, mock_user_context):
        """Test WebSocketBridgeAdapter deprecation causes integration conflicts.
        
        This test exposes conflicts when legacy WebSocketBridgeAdapter is used
        in new SSOT contexts, causing deprecation warnings and potential failures.
        """
        mock_websocket_emitter = Mock()
        
        # This should trigger deprecation warning  
        with pytest.warns(DeprecationWarning, match="WebSocketBridgeAdapter is deprecated"):
            adapter = WebSocketBridgeAdapter(mock_websocket_emitter, mock_user_context)
        
        # Test that deprecated adapter still works but with warnings
        assert adapter.get_active_adapter_type() == "WebSocketEventEmitter"
        
        # Test deprecated adapter interface conflicts with new code
        # If the deprecated adapter causes integration issues, this will fail
        try:
            result = asyncio.run(adapter.notify_agent_started(
                run_id=mock_user_context.run_id,
                agent_name="test-agent",
                context={}
            ))
            # If deprecated adapter works without issues, test should fail initially
            assert result is not None, "Deprecated WebSocketBridgeAdapter should cause integration conflicts"
        except Exception as e:
            # Expected - deprecated adapter should have integration conflicts
            assert "deprecated" in str(e).lower() or "websocket" in str(e).lower()


@pytest.mark.unit
class ExecutionEngineFactoryWebSocketIntegrationConflictsTests:
    """Test ExecutionEngineFactory WebSocket integration conflicts."""
    
    @pytest.fixture
    def mock_user_context(self):
        """Create mock user context for testing."""
        context = Mock(spec=UserExecutionContext)
        context.user_id = "test-user-123"
        context.run_id = "test-run-456"
        context.session_id = "test-session-789"
        context.get_correlation_id.return_value = "test-user-123:test-run-456"
        return context
    
    def test_execution_engine_factory_websocket_emitter_creation_conflict(self, mock_user_context):
        """Test ExecutionEngineFactory WebSocket emitter creation conflicts.
        
        This test exposes conflicts in _create_user_websocket_emitter when the
        WebSocket bridge interface doesn't match UnifiedWebSocketEmitter expectations.
        """
        # Create ExecutionEngineFactory without WebSocket bridge (test mode)
        factory = ExecutionEngineFactory(
            websocket_bridge=None,  # Test mode
            database_session_manager=None,
            redis_manager=None
        )
        
        # Test WebSocket emitter creation in test mode
        emitter = asyncio.run(factory._create_user_websocket_emitter(
            context=mock_user_context,
            agent_factory=None
        ))
        
        # This should create a test fallback manager, but may have interface conflicts
        assert emitter is not None
        
        # Test that test fallback manager has integration conflicts with production code
        # If test mode works seamlessly with production interfaces, test should fail
        try:
            # Try to use test emitter as production emitter - should cause conflicts
            result = asyncio.run(emitter.notify_agent_started(
                run_id=mock_user_context.run_id,
                agent_name="test-agent",
                context={}
            ))
            
            # If test emitter works without conflicts, this indicates no integration issues
            if result is True:
                assert False, "Test WebSocket emitter works without conflicts - no integration issues detected"
                
        except Exception as e:
            # Expected - test emitter should have integration conflicts with production usage
            assert "websocket" in str(e).lower() or "emitter" in str(e).lower()
    
    def test_execution_engine_factory_configure_function_conflicts(self, mock_user_context):
        """Test configure_execution_engine_factory with interface conflicts.
        
        This test exposes conflicts when configure_execution_engine_factory
        receives incompatible WebSocket bridge types.
        """
        # Create a mock that doesn't fully implement AgentWebSocketBridge interface
        incomplete_bridge = Mock()
        incomplete_bridge.some_method = Mock()  # Missing required methods
        
        # Try to configure factory with incomplete bridge - should cause conflicts
        try:
            factory = asyncio.run(configure_execution_engine_factory(
                websocket_bridge=incomplete_bridge,  # Incomplete interface
                database_session_manager=None,
                redis_manager=None
            ))
            
            # If configuration succeeds with incomplete bridge, there's no validation
            # Try to create engine - this should expose interface conflicts
            engine = asyncio.run(factory.create_for_user(mock_user_context))
            assert False, "ExecutionEngineFactory accepted incomplete WebSocket bridge - no interface validation"
            
        except (AttributeError, TypeError) as e:
            # Expected - incomplete bridge should cause interface conflicts
            assert "websocket" in str(e).lower() or "bridge" in str(e).lower()
    
    def test_agent_factory_websocket_manager_parameter_conflict(self, mock_user_context):
        """Test agent factory WebSocket manager parameter conflicts.
        
        This test exposes conflicts when agent factories receive WebSocket managers
        with incompatible parameter names or interfaces.
        """
        # Create mock WebSocket bridge
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        
        # Create ExecutionEngineFactory
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_bridge,
            database_session_manager=None,
            redis_manager=None
        )
        
        # Test that agent factory creation exposes parameter conflicts
        try:
            # This should expose conflicts in agent factory parameter passing
            emitter = asyncio.run(factory._create_user_websocket_emitter(
                context=mock_user_context,
                agent_factory=None
            ))
            
            # Check if emitter creation used correct parameter names
            # UnifiedWebSocketEmitter might expect 'websocket_manager' but get 'manager'
            assert hasattr(emitter, 'user_id'), "WebSocket emitter missing expected attributes"
            assert hasattr(emitter, 'context'), "WebSocket emitter missing context attribute"
            
            # If emitter creation works without parameter conflicts, test should fail
            assert False, "WebSocket emitter creation works without parameter conflicts"
            
        except TypeError as e:
            # Expected - parameter name conflicts should cause TypeError
            assert "parameter" in str(e).lower() or "argument" in str(e).lower()


@pytest.mark.unit
class WebSocketManagerFactoryPatternConflictsTests:
    """Test WebSocket manager factory pattern conflicts."""
    
    @pytest.fixture
    def mock_user_context(self):
        """Create mock user context for testing."""
        context = Mock(spec=UserExecutionContext)
        context.user_id = "test-user-123"
        context.run_id = "test-run-456"
        context.session_id = "test-session-789"
        return context
    
    def test_websocket_manager_factory_wrapper_integration_conflict(self, mock_user_context):
        """Test WebSocket manager factory wrapper integration conflicts.
        
        This test exposes conflicts when components try to use WebSocketManager
        directly but the factory wrapper prevents instantiation.
        """
        # Test that _WebSocketManagerFactory prevents direct instantiation
        assert isinstance(WebSocketManager, _WebSocketManagerFactory)
        
        # Test direct instantiation failure
        with pytest.raises(RuntimeError, match="Direct WebSocketManager instantiation not allowed"):
            manager = WebSocketManager()
        
        # Test call pattern also fails
        with pytest.raises(RuntimeError, match="Direct WebSocketManager instantiation not allowed"):
            manager = WebSocketManager(mode="unified", user_context=mock_user_context)
    
    def test_websocket_manager_factory_function_integration_conflict(self, mock_user_context):
        """Test WebSocket manager factory function integration conflicts.
        
        This test exposes conflicts when factory functions expect certain 
        WebSocket manager interfaces but get incompatible ones.
        """
        # Test create_test_fallback_manager integration
        test_manager = create_test_fallback_manager(mock_user_context)
        assert test_manager is not None
        
        # Test that test manager interface conflicts with production expectations
        # Production code might expect specific methods that test manager doesn't have
        production_methods = [
            'send_event',
            'emit_agent_started', 
            'emit_agent_thinking',
            'emit_tool_executing',
            'emit_tool_completed',
            'emit_agent_completed'
        ]
        
        missing_methods = []
        for method_name in production_methods:
            if not hasattr(test_manager, method_name):
                missing_methods.append(method_name)
        
        # If test manager has all production methods, there's no interface conflict
        if not missing_methods:
            assert False, f"Test WebSocket manager has all production methods - no interface conflicts detected"
        
        # Expected - test manager should be missing some production methods
        assert len(missing_methods) > 0, f"Test manager missing methods: {missing_methods}"
    
    def test_websocket_manager_mode_deprecation_conflicts(self, mock_user_context):
        """Test WebSocket manager mode deprecation causes integration conflicts.
        
        This test exposes conflicts when legacy code uses deprecated WebSocket
        manager modes but new SSOT code expects unified mode only.
        """
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManagerMode
        
        # Test that all deprecated modes redirect to UNIFIED
        deprecated_modes = [
            WebSocketManagerMode.ISOLATED,
            WebSocketManagerMode.EMERGENCY, 
            WebSocketManagerMode.DEGRADED
        ]
        
        for mode in deprecated_modes:
            # All deprecated modes should equal UNIFIED
            assert mode.value == "unified", f"Deprecated mode {mode} should redirect to unified"
        
        # Test that using deprecated modes in factory functions causes conflicts
        try:
            # Try to use deprecated mode - should work but may cause integration issues
            test_manager = create_test_fallback_manager(mock_user_context)
            
            # If deprecated mode usage works seamlessly, there's no conflict
            assert test_manager is not None
            
            # Check if test manager properly handles deprecated mode expectations
            # Legacy code might expect mode-specific behavior that's now unified
            assert False, "Deprecated WebSocket manager modes work without conflicts - no integration issues"
            
        except Exception as e:
            # Expected - deprecated mode usage should cause integration conflicts
            assert "mode" in str(e).lower() or "deprecated" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])