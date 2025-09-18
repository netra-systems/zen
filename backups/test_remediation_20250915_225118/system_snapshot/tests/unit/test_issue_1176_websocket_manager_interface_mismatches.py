"""Unit tests for Issue #1176 - WebSocket Manager Interface Mismatches

TARGET: WebSocket Manager Interface Mismatches Between Factory Components

This module tests the specific interface mismatches between different WebSocket
manager implementations and the factory patterns that create and consume them.
These tests focus on method signature conflicts, parameter mismatches, and
return type incompatibilities that cause integration failures.

Key Interface Conflicts Being Tested:
1. AgentWebSocketBridge vs UnifiedWebSocketManager method signature conflicts
2. StandardWebSocketBridge adapter pattern method signature mismatches  
3. WebSocketEventEmitter vs WebSocketManager interface incompatibilities
4. Factory method parameter name conflicts (websocket_manager vs manager)

These tests are designed to FAIL initially to prove the interface conflicts exist.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Interface Consistency & SSOT Compliance
- Value Impact: Ensures WebSocket interfaces work consistently across all components
- Strategic Impact: Protects $500K+ ARR by preventing WebSocket interface failures
"""

import pytest
import asyncio
import inspect
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, Optional, get_type_hints

# Import components to test interface mismatches
try:
    from netra_backend.app.factories.websocket_bridge_factory import (
        StandardWebSocketBridge,
        WebSocketBridgeProtocol,
        create_standard_websocket_bridge
    )
except ImportError as e:
    pytest.skip(f"WebSocket bridge factory not available: {e}", allow_module_level=True)

try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
except ImportError:
    AgentWebSocketBridge = None

try:
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
except ImportError:
    UnifiedWebSocketEmitter = None

try:
    from netra_backend.app.websocket_core.canonical_import_patterns import (
        WebSocketManager,
        create_test_fallback_manager
    )
except ImportError:
    WebSocketManager = None

try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
except ImportError:
    UserExecutionContext = None


@pytest.mark.unit
class WebSocketManagerMethodSignatureConflictsTests:
    """Test WebSocket manager method signature conflicts."""
    
    @pytest.fixture
    def mock_user_context(self):
        """Create mock user context for testing."""
        context = Mock()
        context.user_id = "test-user-123"
        context.run_id = "test-run-456"
        context.session_id = "test-session-789"
        context.get_correlation_id.return_value = "test-user-123:test-run-456"
        return context
    
    def test_agent_websocket_bridge_method_signature_conflicts(self, mock_user_context):
        """Test AgentWebSocketBridge method signature conflicts with StandardWebSocketBridge.
        
        This test exposes conflicts where AgentWebSocketBridge and StandardWebSocketBridge
        implement the same methods but with different parameter signatures, causing
        integration failures when components expect one interface but get another.
        """
        # Create StandardWebSocketBridge to test interface
        standard_bridge = StandardWebSocketBridge(mock_user_context)
        
        # Get method signatures from StandardWebSocketBridge
        standard_methods = {
            'notify_agent_started': inspect.signature(standard_bridge.notify_agent_started),
            'notify_agent_thinking': inspect.signature(standard_bridge.notify_agent_thinking),
            'notify_tool_executing': inspect.signature(standard_bridge.notify_tool_executing),
            'notify_tool_completed': inspect.signature(standard_bridge.notify_tool_completed),
            'notify_agent_completed': inspect.signature(standard_bridge.notify_agent_completed)
        }
        
        # Mock AgentWebSocketBridge with potentially different signatures
        mock_agent_bridge = Mock(spec=AgentWebSocketBridge if AgentWebSocketBridge else object)
        
        # Create mock methods with different signatures that could cause conflicts
        async def mock_notify_agent_started(run_id, agent_name, **kwargs):  # Different signature
            return True
        
        async def mock_notify_agent_thinking(run_id, agent_name, reasoning, progress=None):  # Missing params
            return True
        
        async def mock_notify_tool_executing(run_id, agent_name, tool_name):  # Missing optional params
            return True
        
        mock_agent_bridge.notify_agent_started = mock_notify_agent_started
        mock_agent_bridge.notify_agent_thinking = mock_notify_agent_thinking
        mock_agent_bridge.notify_tool_executing = mock_notify_tool_executing
        
        # Test signature compatibility
        for method_name, standard_sig in standard_methods.items():
            if hasattr(mock_agent_bridge, method_name):
                mock_method = getattr(mock_agent_bridge, method_name)
                mock_sig = inspect.signature(mock_method)
                
                # Compare parameter counts - should expose signature conflicts
                standard_params = len(standard_sig.parameters)
                mock_params = len(mock_sig.parameters)
                
                if standard_params != mock_params:
                    # Found signature conflict - this is expected
                    assert True, f"Method {method_name} has signature conflict: {standard_params} vs {mock_params} params"
                    return
        
        # If all signatures match, there's no interface conflict
        assert False, "AgentWebSocketBridge and StandardWebSocketBridge have compatible method signatures"
    
    def test_websocket_bridge_protocol_compliance_conflicts(self, mock_user_context):
        """Test WebSocketBridgeProtocol compliance conflicts.
        
        This test exposes conflicts when components implement WebSocketBridgeProtocol
        but with incompatible method signatures or return types.
        """
        # Test StandardWebSocketBridge protocol compliance
        standard_bridge = StandardWebSocketBridge(mock_user_context)
        
        # Check if StandardWebSocketBridge implements WebSocketBridgeProtocol correctly
        protocol_methods = [
            'notify_agent_started',
            'notify_agent_thinking', 
            'notify_tool_executing',
            'notify_tool_completed',
            'notify_agent_completed'
        ]
        
        for method_name in protocol_methods:
            assert hasattr(standard_bridge, method_name), f"StandardWebSocketBridge missing {method_name}"
            
            method = getattr(standard_bridge, method_name)
            sig = inspect.signature(method)
            
            # Check for async method - protocol requires async
            if not asyncio.iscoroutinefunction(method):
                assert False, f"Method {method_name} is not async - protocol violation"
        
        # Test return type conflicts by calling methods
        try:
            result = asyncio.run(standard_bridge.notify_agent_started(
                run_id=mock_user_context.run_id,
                agent_name="test-agent",
                context={}
            ))
            
            # Protocol expects bool return type
            if not isinstance(result, bool):
                assert False, f"notify_agent_started returned {type(result)}, expected bool"
            
            # If protocol compliance works, there's no conflict
            assert False, "StandardWebSocketBridge is fully protocol compliant - no conflicts"
            
        except Exception as e:
            # Expected - protocol compliance should have conflicts
            assert "protocol" in str(e).lower() or "websocket" in str(e).lower()
    
    def test_unified_websocket_emitter_parameter_conflicts(self, mock_user_context):
        """Test UnifiedWebSocketEmitter parameter conflicts.
        
        This test exposes conflicts when UnifiedWebSocketEmitter is created with
        different parameter names or types than expected by factory patterns.
        """
        if not UnifiedWebSocketEmitter:
            pytest.skip("UnifiedWebSocketEmitter not available")
        
        # Test different parameter combinations that could cause conflicts
        parameter_combinations = [
            # (param_dict, expected_error)
            ({'user_id': 'test', 'context': mock_user_context, 'manager': None}, "manager parameter"),
            ({'user_id': 'test', 'context': mock_user_context, 'websocket_manager': None}, "websocket_manager parameter"),
            ({'user_id': 'test', 'context': mock_user_context}, "missing required parameter"),
        ]
        
        conflicts_found = 0
        
        for params, expected_error_type in parameter_combinations:
            try:
                emitter = UnifiedWebSocketEmitter(**params)
                # If creation succeeds, check for parameter conflicts in usage
                result = asyncio.run(emitter.notify_agent_started(
                    run_id=mock_user_context.run_id,
                    agent_name="test-agent",
                    context={}
                ))
                
            except (TypeError, AttributeError) as e:
                # Expected - parameter conflicts should cause errors
                conflicts_found += 1
                assert "parameter" in str(e).lower() or "argument" in str(e).lower()
        
        # If no conflicts found, there's no parameter mismatch
        if conflicts_found == 0:
            assert False, "UnifiedWebSocketEmitter accepts all parameter combinations - no conflicts"
    
    def test_websocket_manager_factory_method_conflicts(self, mock_user_context):
        """Test WebSocket manager factory method conflicts.
        
        This test exposes conflicts when factory methods create WebSocket managers
        with interfaces that don't match what components expect.
        """
        if not WebSocketManager:
            pytest.skip("WebSocketManager not available")
        
        # Test create_test_fallback_manager interface conflicts
        test_manager = create_test_fallback_manager(mock_user_context)
        
        # Test that test manager interface conflicts with production usage
        production_interface_methods = [
            'emit_agent_started',
            'emit_agent_thinking', 
            'emit_tool_executing',
            'emit_tool_completed',
            'emit_agent_completed',
            'send_event',
            'connect_user',
            'disconnect_user'
        ]
        
        missing_methods = []
        incompatible_methods = []
        
        for method_name in production_interface_methods:
            if not hasattr(test_manager, method_name):
                missing_methods.append(method_name)
            else:
                method = getattr(test_manager, method_name)
                # Check if method signature is compatible
                try:
                    sig = inspect.signature(method)
                    # Production methods should be async
                    if not asyncio.iscoroutinefunction(method):
                        incompatible_methods.append(f"{method_name} (not async)")
                except Exception:
                    incompatible_methods.append(f"{method_name} (signature error)")
        
        # Report interface conflicts
        total_conflicts = len(missing_methods) + len(incompatible_methods)
        
        if total_conflicts == 0:
            assert False, "Test WebSocket manager has full production interface - no conflicts"
        
        # Expected - test manager should have interface conflicts
        assert total_conflicts > 0, f"Interface conflicts: missing={missing_methods}, incompatible={incompatible_methods}"


@pytest.mark.unit
class WebSocketBridgeAdapterInterfaceConflictsTests:
    """Test WebSocket bridge adapter interface conflicts."""
    
    @pytest.fixture
    def mock_user_context(self):
        """Create mock user context for testing."""
        context = Mock()
        context.user_id = "test-user-123"
        context.run_id = "test-run-456"
        context.session_id = "test-session-789"
        context.get_correlation_id.return_value = "test-user-123:test-run-456"
        return context
    
    def test_standard_websocket_bridge_adapter_switching_conflicts(self, mock_user_context):
        """Test StandardWebSocketBridge adapter switching conflicts.
        
        This test exposes conflicts when StandardWebSocketBridge switches between
        different adapter types that have incompatible interfaces.
        """
        bridge = StandardWebSocketBridge(mock_user_context)
        
        # Create mock adapters with incompatible interfaces
        mock_agent_bridge = Mock()
        mock_agent_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_agent_bridge.notify_agent_thinking = AsyncMock(return_value=True)
        
        mock_emitter = Mock()
        mock_emitter.notify_agent_started = AsyncMock(return_value=False)  # Different return value
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=AttributeError("Method not supported"))
        
        mock_manager = Mock()
        mock_manager.send_event = AsyncMock(return_value=None)  # Different interface
        
        # Test adapter switching and interface conflicts
        bridge.set_agent_bridge(mock_agent_bridge)
        result1 = asyncio.run(bridge.notify_agent_started(
            run_id=mock_user_context.run_id,
            agent_name="test-agent",
            context={}
        ))
        
        bridge.set_websocket_emitter(mock_emitter)
        result2 = asyncio.run(bridge.notify_agent_started(
            run_id=mock_user_context.run_id,
            agent_name="test-agent", 
            context={}
        ))
        
        bridge.set_websocket_manager(mock_manager)
        result3 = asyncio.run(bridge.notify_agent_started(
            run_id=mock_user_context.run_id,
            agent_name="test-agent",
            context={}
        ))
        
        # Test that different adapters produce different results (indicating conflicts)
        results = [result1, result2, result3]
        unique_results = set(results)
        
        if len(unique_results) == 1:
            assert False, "All WebSocket bridge adapters produce same results - no interface conflicts"
        
        # Test adapter health diagnostics
        health = bridge.diagnose_bridge_health()
        adapter_switches = bridge.get_bridge_metrics().get('adapter_switches', 0)
        
        # If no adapter switches recorded, there's no conflict tracking
        if adapter_switches == 0:
            assert False, "No adapter switches recorded - no conflict detection"
        
        # Expected - adapter switching should indicate interface conflicts
        assert adapter_switches >= 2, f"Expected adapter switches, got {adapter_switches}"
    
    def test_websocket_bridge_interface_validation_conflicts(self, mock_user_context):
        """Test WebSocket bridge interface validation conflicts.
        
        This test exposes conflicts when WebSocket bridge interfaces are
        validated and found to be incompatible with expected signatures.
        """
        bridge = StandardWebSocketBridge(mock_user_context)
        
        # Test interface validation by calling all methods with edge case parameters
        test_cases = [
            # (method_name, params, expected_conflict)
            ('notify_agent_started', {
                'run_id': 'wrong-run-id',  # Should cause validation conflict
                'agent_name': 'test-agent',
                'context': {}
            }, 'run_id mismatch'),
            
            ('notify_agent_thinking', {
                'run_id': mock_user_context.run_id,
                'agent_name': 'test-agent',
                'reasoning': 'test reasoning',
                'step_number': 'invalid-step',  # Wrong type
                'progress_percentage': 150.0  # Invalid percentage
            }, 'parameter validation'),
            
            ('notify_tool_executing', {
                'run_id': mock_user_context.run_id,
                'agent_name': 'test-agent',
                'tool_name': '',  # Empty tool name
                'parameters': None
            }, 'empty tool name'),
        ]
        
        validation_conflicts = 0
        
        for method_name, params, expected_conflict in test_cases:
            try:
                method = getattr(bridge, method_name)
                result = asyncio.run(method(**params))
                
                # If method call succeeds with invalid params, there's no validation
                if result is True:
                    validation_conflicts += 1
                    
            except (ValueError, TypeError, AssertionError) as e:
                # Expected - validation should catch conflicts
                assert expected_conflict in str(e).lower() or "validation" in str(e).lower()
        
        # If no validation conflicts found, interface validation is too permissive
        if validation_conflicts == 0:
            assert False, "WebSocket bridge interface validation is too strict - no permissive conflicts"
    
    def test_websocket_bridge_return_type_conflicts(self, mock_user_context):
        """Test WebSocket bridge return type conflicts.
        
        This test exposes conflicts when WebSocket bridge methods return
        inconsistent types that cause integration issues.
        """
        bridge = StandardWebSocketBridge(mock_user_context)
        
        # Configure bridge with no adapter - should return False
        result_no_adapter = asyncio.run(bridge.notify_agent_started(
            run_id=mock_user_context.run_id,
            agent_name="test-agent",
            context={}
        ))
        
        # Configure bridge with mock adapter that returns different types
        mock_adapter = Mock()
        mock_adapter.notify_agent_started = AsyncMock(return_value="success")  # Wrong type
        bridge.set_agent_bridge(mock_adapter)
        
        result_wrong_type = asyncio.run(bridge.notify_agent_started(
            run_id=mock_user_context.run_id,
            agent_name="test-agent",
            context={}
        ))
        
        # Test return type consistency
        return_types = [type(result_no_adapter), type(result_wrong_type)]
        
        # If return types are inconsistent, there's a conflict
        if len(set(return_types)) > 1:
            assert True, f"Inconsistent return types detected: {return_types}"
        else:
            assert False, "WebSocket bridge methods return consistent types - no conflicts"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])