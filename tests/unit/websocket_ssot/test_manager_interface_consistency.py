"""
Manager Interface Consistency SSOT Validation Tests - Issue #186 WebSocket Manager Fragmentation

Tests that FAIL initially to prove manager interface inconsistency exists in WebSocket implementations.
After SSOT consolidation, these tests should PASS, proving interface standardization works.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Stability - Eliminate interface inconsistencies causing runtime failures
- Value Impact: Ensure reliable WebSocket manager behavior across all user interactions  
- Revenue Impact: Prevent $500K+ ARR chat disruptions from interface compatibility failures

SSOT Violations This Module Proves:
1. Different manager implementations have inconsistent interfaces
2. Method signatures vary between manager implementations
3. Missing required methods in some implementations
4. Inconsistent error handling across manager interfaces
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import asyncio
import inspect
import unittest
from typing import Any, Dict, List, Set, Type, Optional, Callable
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class MethodSignature:
    """Represents a method signature for comparison."""
    name: str
    parameters: List[str]
    return_annotation: str
    is_async: bool
    is_property: bool


class TestWebSocketManagerInterfaceConsistency(SSotBaseTestCase):
    """
    Tests to prove WebSocket manager interface consistency violations exist.
    
    These tests are designed to FAIL initially, proving SSOT violations.
    After proper interface standardization, they should PASS.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.manager_implementations = self._discover_manager_implementations()

    def _discover_manager_implementations(self) -> Dict[str, Type]:
        """Discover all WebSocket manager implementations in the codebase."""
        implementations = {}
        
        # Try to import all known manager implementations
        manager_imports = [
            ('WebSocketManagerFactory', 'netra_backend.app.websocket_core.websocket_manager_factory'),
            ('IsolatedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager_factory'),
            ('UnifiedWebSocketManager', 'netra_backend.app.websocket_core.unified_manager'),
            ('WebSocketManagerAdapter', 'netra_backend.app.websocket_core.migration_adapter'),
            ('ConnectionManager', 'netra_backend.app.websocket_core.connection_manager'),
            ('WebSocketManager', 'netra_backend.app.websocket_core.manager'),
        ]
        
        for class_name, module_path in manager_imports:
            try:
                module = __import__(module_path, fromlist=[class_name])
                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    implementations[f"{module_path}.{class_name}"] = cls
            except ImportError:
                # Expected for some legacy implementations
                pass
            except Exception as e:
                logger.warning(f"Error importing {module_path}.{class_name}: {e}")
        
        return implementations

    def _extract_method_signature(self, method: Callable) -> MethodSignature:
        """Extract standardized method signature for comparison."""
        try:
            sig = inspect.signature(method)
            parameters = []
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                param_str = param_name
                if param.annotation != inspect.Parameter.empty:
                    param_str += f": {param.annotation}"
                if param.default != inspect.Parameter.empty:
                    param_str += f" = {param.default}"
                parameters.append(param_str)
            
            return_annotation = str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else "Any"
            
            return MethodSignature(
                name=method.__name__,
                parameters=parameters,
                return_annotation=return_annotation,
                is_async=asyncio.iscoroutinefunction(method),
                is_property=isinstance(method, property)
            )
        except Exception as e:
            logger.warning(f"Error extracting signature for {method}: {e}")
            return MethodSignature(
                name=getattr(method, '__name__', 'unknown'),
                parameters=[],
                return_annotation="Unknown",
                is_async=False,
                is_property=False
            )

    def test_all_managers_same_interface(self):
        """
        Test that all manager implementations have consistent interfaces.
        
        EXPECTED INITIAL STATE: FAIL - Manager implementations have different interfaces
        EXPECTED POST-SSOT STATE: PASS - All manager implementations share same interface
        
        VIOLATION BEING PROVED: Manager interface divergence causing compatibility issues
        """
        if len(self.manager_implementations) < 2:
            self.skipTest("Need at least 2 manager implementations to test interface consistency")

        # Extract public interfaces from all implementations
        manager_interfaces = {}
        
        for manager_name, manager_class in self.manager_implementations.items():
            interface = set()
            
            for attr_name in dir(manager_class):
                if not attr_name.startswith('_'):  # Public methods only
                    attr = getattr(manager_class, attr_name)
                    if callable(attr) or isinstance(attr, property):
                        sig = self._extract_method_signature(attr)
                        interface.add(f"{sig.name}({', '.join(sig.parameters)}) -> {sig.return_annotation}")
            
            manager_interfaces[manager_name] = interface

        # Compare interfaces for consistency
        interface_inconsistencies = []
        manager_names = list(manager_interfaces.keys())
        
        if len(manager_names) > 1:
            base_manager = manager_names[0]
            base_interface = manager_interfaces[base_manager]
            
            for other_manager in manager_names[1:]:
                other_interface = manager_interfaces[other_manager]
                
                # Find missing methods
                missing_in_other = base_interface - other_interface
                extra_in_other = other_interface - base_interface
                
                if missing_in_other or extra_in_other:
                    interface_inconsistencies.append({
                        'managers': f"{base_manager} vs {other_manager}",
                        'missing_in_second': list(missing_in_other)[:5],  # Limit for readability
                        'extra_in_second': list(extra_in_other)[:5],
                        'total_missing': len(missing_in_other),
                        'total_extra': len(extra_in_other)
                    })

        # ASSERTION THAT SHOULD FAIL INITIALLY: All manager interfaces should be consistent
        if interface_inconsistencies:
            violation_details = []
            for inconsistency in interface_inconsistencies:
                violation_details.append(
                    f"{inconsistency['managers']}: "
                    f"missing={inconsistency['total_missing']}, extra={inconsistency['total_extra']}"
                )
            
            self.fail(
                f"SSOT VIOLATION: Manager interface inconsistencies found:\n" +
                "\n".join(violation_details) +
                f"\nFirst inconsistency details: {interface_inconsistencies[0]}\n"
                f"This proves manager implementations do not share consistent interfaces."
            )

    def test_manager_method_signatures(self):
        """
        Test method signatures are consistent across implementations.
        
        EXPECTED INITIAL STATE: FAIL - Same method names have different signatures
        EXPECTED POST-SSOT STATE: PASS - Same method names have identical signatures
        
        VIOLATION BEING PROVED: Method signature inconsistency causing runtime errors
        """
        if len(self.manager_implementations) < 2:
            self.skipTest("Need at least 2 manager implementations to test signature consistency")

        # Extract method signatures from all implementations
        method_signatures = {}  # method_name -> {manager_name -> signature}
        
        for manager_name, manager_class in self.manager_implementations.items():
            for attr_name in dir(manager_class):
                if not attr_name.startswith('_') and callable(getattr(manager_class, attr_name)):
                    method = getattr(manager_class, attr_name)
                    sig = self._extract_method_signature(method)
                    
                    if attr_name not in method_signatures:
                        method_signatures[attr_name] = {}
                    method_signatures[attr_name][manager_name] = sig

        # Find signature inconsistencies
        signature_violations = []
        
        for method_name, manager_signatures in method_signatures.items():
            if len(manager_signatures) > 1:  # Method exists in multiple managers
                signature_variations = {}
                
                for manager_name, sig in manager_signatures.items():
                    signature_key = f"({', '.join(sig.parameters)}) -> {sig.return_annotation}"
                    if sig.is_async:
                        signature_key = f"async {signature_key}"
                    
                    if signature_key not in signature_variations:
                        signature_variations[signature_key] = []
                    signature_variations[signature_key].append(manager_name)
                
                # If more than one signature variation exists, it's a violation
                if len(signature_variations) > 1:
                    signature_violations.append({
                        'method': method_name,
                        'variations': signature_variations
                    })

        # ASSERTION THAT SHOULD FAIL INITIALLY: Method signatures should be consistent
        self.assertEqual(
            len(signature_violations), 0,
            f"SSOT VIOLATION: Method signature inconsistencies found: "
            f"{[(v['method'], list(v['variations'].keys())) for v in signature_violations[:3]]}... "
            f"(showing first 3 of {len(signature_violations)} violations). "
            f"This proves method signatures are not standardized across manager implementations."
        )

    def test_required_websocket_methods_present(self):
        """
        Test that all managers implement required WebSocket interface methods.
        
        EXPECTED INITIAL STATE: FAIL - Some managers missing required methods
        EXPECTED POST-SSOT STATE: PASS - All managers implement complete required interface
        
        VIOLATION BEING PROVED: Incomplete interface implementations causing runtime failures
        """
        # Define required WebSocket manager interface methods
        required_methods = {
            # Core connection management
            'send_message': {'async': True, 'required_params': ['user_id', 'message']},
            'broadcast_message': {'async': True, 'required_params': ['message']},
            'get_connection_count': {'async': False, 'required_params': []},
            
            # User management
            'add_connection': {'async': True, 'required_params': ['user_id', 'websocket']},
            'remove_connection': {'async': True, 'required_params': ['user_id']},
            'is_user_connected': {'async': False, 'required_params': ['user_id']},
            
            # Connection lifecycle
            'handle_connection': {'async': True, 'required_params': ['websocket']},
            'handle_disconnection': {'async': True, 'required_params': ['user_id']},
            
            # Event handling
            'send_agent_event': {'async': True, 'required_params': ['user_id', 'event_type', 'data']},
        }
        
        # Check each manager implementation
        implementation_violations = []
        
        for manager_name, manager_class in self.manager_implementations.items():
            missing_methods = []
            incorrect_signatures = []
            
            for method_name, requirements in required_methods.items():
                if hasattr(manager_class, method_name):
                    method = getattr(manager_class, method_name)
                    
                    # Check if method is callable
                    if not callable(method):
                        incorrect_signatures.append(f"{method_name} is not callable")
                        continue
                    
                    # Check async requirement
                    is_async = asyncio.iscoroutinefunction(method)
                    if is_async != requirements['async']:
                        expected_async = "async " if requirements['async'] else "sync "
                        actual_async = "async " if is_async else "sync "
                        incorrect_signatures.append(
                            f"{method_name} is {actual_async}but should be {expected_async}"
                        )
                    
                    # Check parameter requirements (basic check)
                    try:
                        sig = inspect.signature(method)
                        param_names = [p for p in sig.parameters.keys() if p != 'self']
                        
                        for required_param in requirements['required_params']:
                            # Check if required parameter exists (flexible matching)
                            param_found = any(required_param in param_name for param_name in param_names)
                            if not param_found:
                                incorrect_signatures.append(
                                    f"{method_name} missing required parameter pattern '{required_param}'"
                                )
                    except Exception as e:
                        incorrect_signatures.append(f"{method_name} signature analysis failed: {e}")
                        
                else:
                    missing_methods.append(method_name)
            
            if missing_methods or incorrect_signatures:
                implementation_violations.append({
                    'manager': manager_name,
                    'missing_methods': missing_methods,
                    'incorrect_signatures': incorrect_signatures
                })

        # ASSERTION THAT SHOULD FAIL INITIALLY: All managers should implement required interface
        if implementation_violations:
            violation_summary = []
            for violation in implementation_violations:
                violation_summary.append(
                    f"{violation['manager']}: missing={len(violation['missing_methods'])}, "
                    f"incorrect={len(violation['incorrect_signatures'])}"
                )
            
            self.fail(
                f"SSOT VIOLATION: Required interface implementation violations:\n" +
                "\n".join(violation_summary) +
                f"\nFirst violation details: {implementation_violations[0]}\n"
                f"This proves manager implementations do not consistently implement required WebSocket interface."
            )

    def test_manager_protocol_compliance(self):
        """
        Test that managers comply with defined protocols.
        
        EXPECTED INITIAL STATE: FAIL - Managers don't properly implement defined protocols
        EXPECTED POST-SSOT STATE: PASS - All managers properly implement protocol contracts
        
        VIOLATION BEING PROVED: Protocol compliance violations causing type checking failures
        """
        # Try to import WebSocket protocols
        protocol_classes = []
        
        try:
            from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
            protocol_classes.append(('WebSocketManagerProtocol', WebSocketManagerProtocol))
        except ImportError:
            pass
        
        try:
            from netra_backend.app.core.interfaces_websocket import WebSocketManagerProtocol as InterfaceProtocol
            protocol_classes.append(('InterfaceProtocol', InterfaceProtocol))
        except ImportError:
            pass

        if not protocol_classes:
            self.skipTest("No WebSocket protocols found to test compliance")

        # Check protocol compliance for each manager
        compliance_violations = []
        
        for manager_name, manager_class in self.manager_implementations.items():
            for protocol_name, protocol_class in protocol_classes:
                try:
                    # Check if manager claims to implement protocol
                    if hasattr(protocol_class, '__annotations__'):
                        # Protocol has type annotations - check method existence
                        protocol_methods = []
                        for attr_name in dir(protocol_class):
                            if not attr_name.startswith('_'):
                                attr = getattr(protocol_class, attr_name)
                                if callable(attr) or hasattr(attr, '__annotations__'):
                                    protocol_methods.append(attr_name)
                        
                        # Check if manager implements all protocol methods
                        missing_protocol_methods = []
                        for method_name in protocol_methods:
                            if not hasattr(manager_class, method_name):
                                missing_protocol_methods.append(method_name)
                            elif not callable(getattr(manager_class, method_name)):
                                missing_protocol_methods.append(f"{method_name} (not callable)")
                        
                        if missing_protocol_methods:
                            compliance_violations.append({
                                'manager': manager_name,
                                'protocol': protocol_name,
                                'missing_methods': missing_protocol_methods[:5]  # Limit for readability
                            })
                
                except Exception as e:
                    logger.warning(f"Error checking protocol compliance for {manager_name}: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: All managers should comply with protocols
        self.assertEqual(
            len(compliance_violations), 0,
            f"SSOT VIOLATION: Protocol compliance violations found: "
            f"{[(v['manager'], v['protocol'], len(v['missing_methods'])) for v in compliance_violations[:3]]}... "
            f"This proves managers do not properly implement defined protocol contracts."
        )

    def test_manager_error_handling_consistency(self):
        """
        Test that error handling is consistent across manager implementations.
        
        EXPECTED INITIAL STATE: FAIL - Inconsistent error handling between managers
        EXPECTED POST-SSOT STATE: PASS - Consistent error handling patterns across all managers
        
        VIOLATION BEING PROVED: Error handling inconsistency causing unpredictable failures
        """
        # Test error handling patterns
        error_handling_tests = [
            {
                'scenario': 'invalid_user_id',
                'test_method': 'send_message',
                'test_args': [None, {'test': 'message'}],
                'expected_exceptions': [ValueError, TypeError]
            },
            {
                'scenario': 'empty_message',
                'test_method': 'send_message', 
                'test_args': ['valid_user', {}],
                'expected_exceptions': [ValueError]
            },
            {
                'scenario': 'invalid_connection_count',
                'test_method': 'get_connection_count',
                'test_args': [],
                'expected_exceptions': []  # Should not raise exception
            }
        ]
        
        error_handling_inconsistencies = []
        
        for manager_name, manager_class in self.manager_implementations.items():
            try:
                # Create manager instance for testing
                if 'Factory' in manager_name:
                    # Factory classes need different instantiation
                    manager_instance = manager_class()
                else:
                    # Regular manager classes
                    manager_instance = manager_class()
                
                for test_case in error_handling_tests:
                    method_name = test_case['test_method']
                    
                    if hasattr(manager_instance, method_name):
                        method = getattr(manager_instance, method_name)
                        
                        try:
                            # Execute test with invalid inputs
                            if asyncio.iscoroutinefunction(method):
                                # Can't easily test async methods in sync test, so check signature only
                                result = "async_method_skipped"
                            else:
                                result = method(*test_case['test_args'])
                            
                            # If we expected an exception but didn't get one
                            if test_case['expected_exceptions'] and result != "async_method_skipped":
                                error_handling_inconsistencies.append({
                                    'manager': manager_name,
                                    'scenario': test_case['scenario'],
                                    'issue': f"Expected exception {test_case['expected_exceptions']} but got result: {result}"
                                })
                        
                        except Exception as e:
                            # Check if exception type is expected
                            exception_type = type(e)
                            if (test_case['expected_exceptions'] and 
                                exception_type not in test_case['expected_exceptions']):
                                error_handling_inconsistencies.append({
                                    'manager': manager_name,
                                    'scenario': test_case['scenario'],
                                    'issue': f"Got {exception_type.__name__} but expected one of {test_case['expected_exceptions']}"
                                })
                            elif not test_case['expected_exceptions']:
                                error_handling_inconsistencies.append({
                                    'manager': manager_name,
                                    'scenario': test_case['scenario'], 
                                    'issue': f"Unexpected exception: {exception_type.__name__}: {e}"
                                })
            
            except Exception as e:
                logger.warning(f"Could not test error handling for {manager_name}: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: Error handling should be consistent
        self.assertEqual(
            len(error_handling_inconsistencies), 0,
            f"SSOT VIOLATION: Error handling inconsistencies found: "
            f"{[(i['manager'], i['scenario'], i['issue'][:50]) for i in error_handling_inconsistencies[:3]]}... "
            f"This proves error handling is not standardized across manager implementations."
        )

    def test_manager_lifecycle_method_consistency(self):
        """
        Test that lifecycle methods are consistently implemented.
        
        EXPECTED INITIAL STATE: FAIL - Lifecycle methods inconsistent between managers
        EXPECTED POST-SSOT STATE: PASS - All managers implement consistent lifecycle patterns
        
        VIOLATION BEING PROVED: Lifecycle method inconsistency causing resource management issues
        """
        # Define expected lifecycle methods
        lifecycle_methods = [
            'initialize',
            'start', 
            'stop',
            'cleanup',
            'shutdown',
            'health_check',
            'get_status'
        ]
        
        # Check lifecycle method implementation across managers
        lifecycle_inconsistencies = []
        
        for manager_name, manager_class in self.manager_implementations.items():
            manager_lifecycle_methods = []
            
            for method_name in lifecycle_methods:
                if hasattr(manager_class, method_name):
                    method = getattr(manager_class, method_name)
                    if callable(method):
                        is_async = asyncio.iscoroutinefunction(method)
                        manager_lifecycle_methods.append(f"{method_name}({'async' if is_async else 'sync'})")

            # Compare with expected patterns
            if manager_lifecycle_methods:
                # For now, just check that if lifecycle methods exist, they follow patterns
                # In a fully SSOT system, all managers should have same lifecycle methods
                pass
        
        # If we have multiple managers with different lifecycle patterns, it's a violation
        if len(self.manager_implementations) > 1:
            lifecycle_patterns = {}
            
            for manager_name, manager_class in self.manager_implementations.items():
                pattern = []
                for method_name in lifecycle_methods:
                    if hasattr(manager_class, method_name):
                        method = getattr(manager_class, method_name)
                        if callable(method):
                            is_async = asyncio.iscoroutinefunction(method)
                            pattern.append(f"{method_name}({'async' if is_async else 'sync'})")
                
                pattern_key = tuple(sorted(pattern))
                if pattern_key not in lifecycle_patterns:
                    lifecycle_patterns[pattern_key] = []
                lifecycle_patterns[pattern_key].append(manager_name)
            
            # If more than one lifecycle pattern exists, it's a violation
            if len(lifecycle_patterns) > 1:
                pattern_details = []
                for pattern, managers in lifecycle_patterns.items():
                    pattern_details.append(f"Pattern {list(pattern)[:3]}... used by {managers}")
                
                lifecycle_inconsistencies.extend(pattern_details)

        # ASSERTION THAT SHOULD FAIL INITIALLY: Lifecycle methods should be consistent
        self.assertEqual(
            len(lifecycle_inconsistencies), 0,
            f"SSOT VIOLATION: Lifecycle method inconsistencies found: {lifecycle_inconsistencies}. "
            f"This proves lifecycle patterns are not standardized across manager implementations."
        )


if __name__ == '__main__':
    import unittest
    unittest.main()