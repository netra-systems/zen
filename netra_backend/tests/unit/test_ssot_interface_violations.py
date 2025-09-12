"""SSOT Interface Violations Test Suite

CRITICAL MISSION: Comprehensive testing of SSOT interface contract violations across the codebase.

This test suite focuses on detecting and documenting interface violations that break
Single Source of Truth (SSOT) principles and compromise system architecture integrity.

BUSINESS IMPACT: Interface violations can cause:
- Golden Path failures ($500K+ ARR risk)
- Service integration failures
- User isolation breaks
- WebSocket event system failures

PRIMARY VIOLATIONS COVERED:
1. AgentRegistry.set_websocket_manager() vs UniversalAgentRegistry.set_websocket_bridge()
2. Parameter type mismatches between parent and child classes
3. Liskov Substitution Principle violations
4. Interface contract inconsistencies

BVJ: ALL segments | Platform Stability | SSOT compliance critical for system reliability

TESTING STRATEGY:
 PASS:  FAIL before fix - Demonstrate violations exist with current code
 PASS:  PASS after fix - Validate compliance post-remediation  
 PASS:  Specific focus - Interface contract violations only
 PASS:  Comprehensive coverage - All known SSOT interface issues
"""

import pytest
import inspect
from typing import get_type_hints
from unittest.mock import Mock, MagicMock


class TestAgentRegistryInterfaceViolations:
    """Test suite for AgentRegistry interface violations."""

    def test_websocket_parameter_type_violation(self):
        """Test the specific WebSocket parameter type violation.
        
        VIOLATION: AgentRegistry.set_websocket_manager() accepts WebSocketManager
        but parent UniversalAgentRegistry.set_websocket_bridge() expects AgentWebSocketBridge.
        
        This test SHOULD FAIL with current code, proving the violation exists.
        """
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.core.registry.universal_registry import AgentRegistry as UniversalAgentRegistry
        
        # Get the actual method signatures
        parent_method = getattr(UniversalAgentRegistry, 'set_websocket_bridge')
        child_method = getattr(AgentRegistry, 'set_websocket_manager')
        
        # Analyze parameter types using inspection
        parent_sig = inspect.signature(parent_method)
        child_sig = inspect.signature(child_method)
        
        # Extract parameter information
        parent_params = list(parent_sig.parameters.values())[1:]  # Skip 'self'
        child_params = list(child_sig.parameters.values())[1:]    # Skip 'self'
        
        assert len(parent_params) == 1, "Parent method should have one websocket parameter"
        assert len(child_params) == 1, "Child method should have one websocket parameter"
        
        parent_param = parent_params[0]
        child_param = child_params[0]
        
        # Check type annotations
        parent_type = str(parent_param.annotation) if parent_param.annotation != inspect.Parameter.empty else "Any"
        child_type = str(child_param.annotation) if child_param.annotation != inspect.Parameter.empty else "Any"
        
        # VIOLATION DETECTION: Different parameter types between parent and child
        type_mismatch = (
            'AgentWebSocketBridge' in parent_type and 
            'WebSocketManager' in child_type
        )
        
        if type_mismatch:
            pytest.fail(
                f"SSOT VIOLATION DETECTED: Interface parameter type mismatch\n"
                f"Parent method expects: {parent_type}\n"
                f"Child method expects: {child_type}\n"
                f"This violates interface contract and SSOT principles."
            )
        
        # If no mismatch detected, document current state
        print(f"Parameter types - Parent: {parent_type}, Child: {child_type}")

    def test_interface_substitutability_violation(self):
        """Test Liskov Substitution Principle violation.
        
        Child class should be substitutable for parent class without breaking functionality.
        This test SHOULD FAIL, demonstrating the substitutability violation.
        """
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.core.registry.universal_registry import AgentRegistry as UniversalAgentRegistry
        
        # Create instances
        parent_registry = UniversalAgentRegistry("TestParent")
        child_registry = AgentRegistry()
        
        # Create proper bridge object for parent interface
        mock_bridge = Mock()
        mock_bridge.__class__.__name__ = "AgentWebSocketBridge"
        
        # Test parent functionality
        try:
            parent_registry.set_websocket_bridge(mock_bridge)
            parent_works = True
        except Exception as e:
            parent_works = False
            pytest.fail(f"Parent interface failed unexpectedly: {e}")
        
        # Test child substitutability
        try:
            # Child should implement parent interface
            child_registry.set_websocket_bridge(mock_bridge)
            child_substitutable = True
        except AttributeError:
            # Method doesn't exist - interface violation
            child_substitutable = False
        except Exception as e:
            # Method exists but fails - implementation violation
            child_substitutable = False
            print(f"Child interface implementation failed: {e}")
        
        # LSP VIOLATION: Child is not substitutable for parent
        if not child_substitutable:
            pytest.fail(
                "SSOT VIOLATION: Liskov Substitution Principle violated\n"
                f"Child AgentRegistry cannot be substituted for parent UniversalAgentRegistry\n"
                f"Parent interface works: {parent_works}\n"
                f"Child substitutable: {child_substitutable}"
            )

    def test_method_name_interface_violation(self):
        """Test method naming interface violation.
        
        Child class uses different method name (set_websocket_manager) 
        than parent interface (set_websocket_bridge).
        
        This test SHOULD FAIL, documenting the method naming inconsistency.
        """
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.core.registry.universal_registry import AgentRegistry as UniversalAgentRegistry
        
        # Check method presence
        parent_has_bridge_method = hasattr(UniversalAgentRegistry, 'set_websocket_bridge')
        child_has_bridge_method = hasattr(AgentRegistry, 'set_websocket_bridge')
        child_has_manager_method = hasattr(AgentRegistry, 'set_websocket_manager')
        
        # INTERFACE CONSISTENCY CHECK
        interface_inconsistent = (
            parent_has_bridge_method and 
            child_has_manager_method and 
            not child_has_bridge_method
        )
        
        if interface_inconsistent:
            pytest.fail(
                "SSOT VIOLATION: Interface method naming inconsistency\n"
                f"Parent has 'set_websocket_bridge': {parent_has_bridge_method}\n"
                f"Child has 'set_websocket_bridge': {child_has_bridge_method}\n"
                f"Child has 'set_websocket_manager': {child_has_manager_method}\n"
                "Child should implement parent interface methods for SSOT compliance."
            )

    def test_interface_contract_parameter_count_violation(self):
        """Test parameter count consistency between interface methods.
        
        Interface methods should have consistent parameter signatures.
        This test SHOULD FAIL if parameter counts don't match.
        """
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.core.registry.universal_registry import AgentRegistry as UniversalAgentRegistry
        
        # Get method signatures
        parent_method = getattr(UniversalAgentRegistry, 'set_websocket_bridge', None)
        child_method = getattr(AgentRegistry, 'set_websocket_manager', None)
        
        if not parent_method or not child_method:
            pytest.skip("Required methods not found for parameter count validation")
        
        parent_sig = inspect.signature(parent_method)
        child_sig = inspect.signature(child_method)
        
        # Count non-self parameters
        parent_param_count = len([p for name, p in parent_sig.parameters.items() if name != 'self'])
        child_param_count = len([p for name, p in child_sig.parameters.items() if name != 'self'])
        
        # PARAMETER COUNT CONSISTENCY CHECK
        if parent_param_count != child_param_count:
            pytest.fail(
                "SSOT VIOLATION: Interface parameter count mismatch\n"
                f"Parent method parameter count: {parent_param_count}\n"
                f"Child method parameter count: {child_param_count}\n"
                "Interface methods should have consistent parameter counts."
            )


class TestInterfaceContractCompliance:
    """Test suite for validating proper interface contract compliance post-fix."""

    def test_websocket_interface_unified_compliance(self):
        """Test that WebSocket interface is properly unified after fix.
        
        This test should PASS after the interface violation is remediated.
        It validates that both methods work correctly and maintain interface compatibility.
        """
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        
        registry = AgentRegistry()
        
        # Test with WebSocketManager (child interface)
        mock_manager = Mock()
        mock_manager.__class__.__name__ = "WebSocketManager"
        
        try:
            registry.set_websocket_manager(mock_manager)
            manager_interface_works = True
        except Exception as e:
            manager_interface_works = False
            print(f"WebSocketManager interface failed: {e}")
        
        # Test with AgentWebSocketBridge (parent interface) if method exists
        bridge_interface_works = True
        if hasattr(registry, 'set_websocket_bridge'):
            mock_bridge = Mock()
            mock_bridge.__class__.__name__ = "AgentWebSocketBridge"
            
            try:
                registry.set_websocket_bridge(mock_bridge)
            except Exception as e:
                bridge_interface_works = False
                print(f"AgentWebSocketBridge interface failed: {e}")
        
        # Both interfaces should work for unified compliance
        assert manager_interface_works, "WebSocketManager interface should work"
        assert bridge_interface_works, "AgentWebSocketBridge interface should work"

    def test_interface_type_conversion_compliance(self):
        """Test that registry properly converts between WebSocket types.
        
        This test should PASS after fix, validating proper type conversion
        between WebSocketManager and AgentWebSocketBridge.
        """
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        
        registry = AgentRegistry()
        
        # Set WebSocketManager
        mock_manager = Mock()
        mock_manager.__class__.__name__ = "WebSocketManager"
        registry.set_websocket_manager(mock_manager)
        
        # Verify both storage types exist
        manager_stored = getattr(registry, 'websocket_manager', None)
        bridge_stored = getattr(registry, 'websocket_bridge', None)
        
        # After fix, both should be properly set
        assert manager_stored is not None, "WebSocketManager should be stored"
        assert bridge_stored is not None, "AgentWebSocketBridge should be created for parent interface"
        
        # Verify bridge has proper interface
        if bridge_stored:
            bridge_has_proper_interface = (
                hasattr(bridge_stored, '__class__') and
                'Bridge' in str(bridge_stored.__class__.__name__)
            )
            assert bridge_has_proper_interface, "Created bridge should have proper interface"

    def test_backward_compatibility_maintained(self):
        """Test that interface fixes maintain backward compatibility.
        
        This test should PASS after fix, ensuring existing code continues to work.
        """
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        
        registry = AgentRegistry()
        
        # Existing code using set_websocket_manager should still work
        mock_manager = Mock()
        mock_manager.__class__.__name__ = "WebSocketManager"
        
        try:
            registry.set_websocket_manager(mock_manager)
            backward_compatible = True
        except Exception as e:
            backward_compatible = False
            print(f"Backward compatibility broken: {e}")
        
        assert backward_compatible, "Interface fix should maintain backward compatibility"


class TestSSoTComplianceValidation:
    """Test suite for comprehensive SSOT compliance validation."""

    def test_single_source_of_truth_enforcement(self):
        """Test that registry enforces SSOT principles.
        
        This test validates that there's only one authoritative source for
        WebSocket management in the registry hierarchy.
        """
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        
        registry = AgentRegistry()
        
        # After SSOT compliance fix, there should be clear hierarchy
        # with one source of truth for WebSocket management
        
        # Check for proper inheritance structure
        assert hasattr(registry, 'set_websocket_manager'), \
            "Registry should have child-specific WebSocket manager method"
        
        # Check for parent interface compliance
        assert hasattr(registry, 'set_websocket_bridge'), \
            "Registry should inherit parent WebSocket bridge interface"
        
        # Verify SSOT compliance - no conflicting implementations
        manager_method = getattr(registry, 'set_websocket_manager')
        bridge_method = getattr(registry, 'set_websocket_bridge')
        
        assert callable(manager_method), "Manager method should be callable"
        assert callable(bridge_method), "Bridge method should be callable"

    def test_interface_documentation_compliance(self):
        """Test that interface methods have proper documentation.
        
        This test validates that interface violations are properly documented
        and methods have clear contracts.
        """
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.core.registry.universal_registry import AgentRegistry as UniversalAgentRegistry
        
        # Check method documentation
        parent_method = getattr(UniversalAgentRegistry, 'set_websocket_bridge', None)
        child_method = getattr(AgentRegistry, 'set_websocket_manager', None)
        
        if parent_method:
            parent_doc = parent_method.__doc__
            assert parent_doc is not None, "Parent method should have documentation"
            assert len(parent_doc.strip()) > 0, "Parent method documentation should not be empty"
        
        if child_method:
            child_doc = child_method.__doc__
            assert child_doc is not None, "Child method should have documentation"
            assert len(child_doc.strip()) > 0, "Child method documentation should not be empty"
            
            # Documentation should mention interface compatibility
            doc_mentions_interface = (
                'interface' in child_doc.lower() or 
                'parent' in child_doc.lower() or
                'bridge' in child_doc.lower()
            )
            assert doc_mentions_interface, \
                "Child method documentation should mention interface compatibility"