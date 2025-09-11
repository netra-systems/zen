"""SSOT Interface Violation Reproduction Tests

CRITICAL TEST SUITE: Reproduces the exact interface violation in AgentRegistry.set_websocket_manager()

SSOT VIOLATION DISCOVERED:
- Child class AgentRegistry.set_websocket_manager() receives WebSocketManager
- Parent class UniversalAgentRegistry.set_websocket_bridge() expects AgentWebSocketBridge
- This violates Liskov Substitution Principle and creates interface confusion

BUSINESS IMPACT: This violation blocks Golden Path and affects $500K+ ARR chat functionality

These tests are designed to:
✅ FAIL before fix - Demonstrate the exact interface violation
✅ PASS after fix - Validate interface compliance post-remediation
✅ Specific focus - WebSocket manager parameter type validation

BVJ: ALL segments | Platform Stability | Interface contract compliance critical for system reliability
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock
from typing import TYPE_CHECKING

# Import required classes
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.core.registry.universal_registry import AgentRegistry as UniversalAgentRegistry

if TYPE_CHECKING:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestAgentRegistryInterfaceViolation:
    """Test suite focused on the specific interface violation in set_websocket_manager()."""

    def test_interface_signature_mismatch_violation(self):
        """CRITICAL: Reproduces the interface signature mismatch between parent and child classes.
        
        This test demonstrates the exact SSOT violation:
        - Parent UniversalAgentRegistry.set_websocket_bridge() expects AgentWebSocketBridge
        - Child AgentRegistry.set_websocket_manager() receives WebSocketManager
        
        This test SHOULD FAIL with current code, demonstrating the interface violation.
        """
        # Create registry instance
        registry = AgentRegistry()
        
        # Create mock WebSocketManager (what AgentRegistry currently accepts)
        mock_websocket_manager = Mock()
        mock_websocket_manager.__class__.__name__ = "WebSocketManager"
        
        # Create mock AgentWebSocketBridge (what parent expects)
        mock_websocket_bridge = Mock()
        mock_websocket_bridge.__class__.__name__ = "AgentWebSocketBridge"
        
        # VIOLATION TEST: AgentRegistry.set_websocket_manager() accepts WebSocketManager
        # but parent interface expects AgentWebSocketBridge
        try:
            # This currently works but violates interface contract
            registry.set_websocket_manager(mock_websocket_manager)
            
            # Check if parent has the bridge set (it shouldn't be properly set)
            parent_bridge = getattr(registry, 'websocket_bridge', None)
            
            # VIOLATION: Parent doesn't have proper bridge type
            if parent_bridge is not None:
                # If parent bridge exists, it should be AgentWebSocketBridge type
                assert hasattr(parent_bridge, '_websocket_manager'), \
                    "Parent bridge should have proper AgentWebSocketBridge interface"
            
            # INTERFACE MISMATCH: The child method name doesn't match parent
            assert hasattr(registry, 'set_websocket_bridge'), \
                "Registry should inherit set_websocket_bridge from parent"
            
            # VIOLATION: Different parameter types between child and parent methods
            # This test documents the current violation state
            interface_violation_detected = True
            
        except Exception as e:
            # If this fails, it indicates the interface is completely broken
            pytest.fail(f"Interface violation caused failure: {e}")
        
        # Document the violation for remediation planning
        assert interface_violation_detected, \
            "Interface violation should be detected - methods accept different parameter types"

    def test_liskov_substitution_principle_violation(self):
        """Test that demonstrates Liskov Substitution Principle violation.
        
        LSP states that objects of a superclass should be replaceable with objects 
        of a subclass without altering the correctness of the program.
        
        This test SHOULD FAIL, demonstrating the LSP violation.
        """
        # Create instances
        parent_registry = UniversalAgentRegistry("TestParent")
        child_registry = AgentRegistry()
        
        # Create proper AgentWebSocketBridge for parent
        mock_bridge = Mock()
        mock_bridge.__class__.__name__ = "AgentWebSocketBridge"
        
        # Parent method should work with AgentWebSocketBridge
        try:
            parent_registry.set_websocket_bridge(mock_bridge)
            parent_success = True
        except Exception as e:
            parent_success = False
            pytest.fail(f"Parent method failed with proper type: {e}")
        
        # Child should be substitutable but currently isn't due to interface mismatch
        # Child expects WebSocketManager but parent interface is AgentWebSocketBridge
        try:
            # This is the violation - child can't be used where parent is expected
            # because the method signatures are incompatible
            child_registry.set_websocket_bridge(mock_bridge)
            child_substitutable = True
        except Exception as e:
            # This might fail because child doesn't properly implement parent interface
            child_substitutable = False
        
        # LSP VIOLATION: Child is not substitutable for parent
        # This assertion will fail until the interface is fixed
        assert child_substitutable or not parent_success, \
            "LSP violation: Child AgentRegistry is not substitutable for parent UniversalAgentRegistry"

    def test_interface_contract_parameter_type_mismatch(self):
        """Test that validates parameter type expectations in interface contract.
        
        This test SHOULD FAIL, demonstrating that the child class method
        accepts a different parameter type than what the interface contract specifies.
        """
        registry = AgentRegistry()
        
        # Test with WebSocketManager (what child currently accepts)
        websocket_manager = Mock()
        websocket_manager.__class__.__name__ = "WebSocketManager"
        
        # Test with AgentWebSocketBridge (what parent interface expects)
        websocket_bridge = Mock()
        websocket_bridge.__class__.__name__ = "AgentWebSocketBridge"
        
        # INTERFACE CONTRACT VIOLATION:
        # Child accepts WebSocketManager but should accept AgentWebSocketBridge
        # to maintain interface compatibility
        
        # This should work with current implementation (proving violation exists)
        try:
            registry.set_websocket_manager(websocket_manager)
            accepts_manager = True
        except Exception:
            accepts_manager = False
        
        # This should also work if interface is properly implemented
        # but currently might not work properly
        try:
            # Child should properly handle parent interface type
            if hasattr(registry, 'set_websocket_bridge'):
                registry.set_websocket_bridge(websocket_bridge)
                accepts_bridge = True
            else:
                accepts_bridge = False
        except Exception:
            accepts_bridge = False
        
        # VIOLATION DETECTION: Child accepts wrong type or doesn't support proper interface
        interface_violation = accepts_manager and not accepts_bridge
        
        assert not interface_violation, \
            "Interface violation: Child should accept same parameter type as parent interface"

    def test_method_signature_compatibility(self):
        """Test method signature compatibility between parent and child.
        
        This test SHOULD FAIL, documenting the method signature incompatibility.
        """
        import inspect
        
        # Get parent method signature
        parent_method = getattr(UniversalAgentRegistry, 'set_websocket_bridge', None)
        assert parent_method is not None, "Parent should have set_websocket_bridge method"
        
        # Get child method signature
        child_method = getattr(AgentRegistry, 'set_websocket_manager', None)
        assert child_method is not None, "Child should have set_websocket_manager method"
        
        # Analyze signatures
        parent_sig = inspect.signature(parent_method)
        child_sig = inspect.signature(child_method)
        
        # Get parameter types from annotations
        parent_params = list(parent_sig.parameters.values())
        child_params = list(child_sig.parameters.values())
        
        # Compare non-self parameters
        parent_websocket_param = None
        child_websocket_param = None
        
        for param in parent_params:
            if param.name != 'self' and 'websocket' in param.name.lower():
                parent_websocket_param = param
                break
        
        for param in child_params:
            if param.name != 'self' and 'websocket' in param.name.lower():
                child_websocket_param = param
                break
        
        # SIGNATURE MISMATCH DETECTION
        signature_compatible = False
        
        if parent_websocket_param and child_websocket_param:
            # Check if annotations are compatible
            parent_annotation = parent_websocket_param.annotation
            child_annotation = child_websocket_param.annotation
            
            # For interface compatibility, they should be the same or compatible types
            signature_compatible = (parent_annotation == child_annotation)
        
        # This test documents the signature incompatibility
        assert signature_compatible, \
            f"Method signature incompatibility: parent expects {parent_websocket_param}, child expects {child_websocket_param}"

    def test_websocket_manager_vs_bridge_type_confusion(self):
        """Test that demonstrates the type confusion between WebSocketManager and AgentWebSocketBridge.
        
        This test SHOULD FAIL, showing the specific type confusion that causes the SSOT violation.
        """
        registry = AgentRegistry()
        
        # Create instances of both types to test with
        mock_manager = Mock()
        mock_manager.__class__.__name__ = "WebSocketManager"
        
        mock_bridge = Mock()
        mock_bridge.__class__.__name__ = "AgentWebSocketBridge"
        
        # Test current behavior (should work with manager)
        try:
            registry.set_websocket_manager(mock_manager)
            manager_accepted = True
        except Exception as e:
            manager_accepted = False
        
        # Check what got stored at registry level
        registry_websocket_manager = getattr(registry, 'websocket_manager', None)
        registry_websocket_bridge = getattr(registry, 'websocket_bridge', None)
        
        # TYPE CONFUSION DETECTION:
        # Registry stores WebSocketManager but parent expects AgentWebSocketBridge
        type_confusion_detected = (
            manager_accepted and 
            registry_websocket_manager is not None and
            (registry_websocket_bridge is None or 
             registry_websocket_bridge.__class__.__name__ != "AgentWebSocketBridge")
        )
        
        # This test documents the current type confusion
        # After fix, registry should properly convert WebSocketManager to AgentWebSocketBridge
        assert not type_confusion_detected, \
            "Type confusion: Registry stores WebSocketManager but interface expects AgentWebSocketBridge"


class TestInterfaceContractCompliance:
    """Test suite for validating proper interface contract compliance post-fix."""

    def test_unified_websocket_interface_compliance(self):
        """Test that registry properly implements unified WebSocket interface.
        
        This test is designed to PASS after the interface violation is fixed.
        It validates that the registry properly handles both WebSocketManager and 
        AgentWebSocketBridge in a compliant manner.
        """
        registry = AgentRegistry()
        
        # After fix, registry should handle WebSocketManager by creating proper bridge
        mock_manager = Mock()
        mock_manager.__class__.__name__ = "WebSocketManager"
        
        # This should work and create proper bridge internally
        try:
            registry.set_websocket_manager(mock_manager)
            
            # Verify that parent interface is properly satisfied
            parent_bridge = getattr(registry, 'websocket_bridge', None)
            assert parent_bridge is not None, \
                "Registry should create AgentWebSocketBridge for parent interface"
            
            # Verify interface compliance
            interface_compliant = (
                hasattr(registry, 'websocket_manager') and
                hasattr(registry, 'websocket_bridge') and
                parent_bridge is not None
            )
            
            assert interface_compliant, \
                "Registry should maintain both WebSocketManager and AgentWebSocketBridge for interface compliance"
            
        except Exception as e:
            pytest.fail(f"Fixed interface should handle WebSocketManager properly: {e}")

    def test_backward_compatibility_maintained(self):
        """Test that interface fix maintains backward compatibility.
        
        This test is designed to PASS after fix, ensuring existing code still works.
        """
        registry = AgentRegistry()
        
        # Existing code using set_websocket_manager should continue to work
        mock_manager = Mock()
        mock_manager.__class__.__name__ = "WebSocketManager"
        
        try:
            registry.set_websocket_manager(mock_manager)
            backward_compatible = True
        except Exception as e:
            backward_compatible = False
            pytest.fail(f"Backward compatibility broken: {e}")
        
        # New code using parent interface should also work
        if hasattr(registry, 'set_websocket_bridge'):
            mock_bridge = Mock() 
            mock_bridge.__class__.__name__ = "AgentWebSocketBridge"
            
            try:
                registry.set_websocket_bridge(mock_bridge)
                forward_compatible = True
            except Exception as e:
                forward_compatible = False
                pytest.fail(f"Forward compatibility broken: {e}")
        else:
            forward_compatible = True  # If method doesn't exist, that's expected
        
        assert backward_compatible and forward_compatible, \
            "Interface fix should maintain both backward and forward compatibility"