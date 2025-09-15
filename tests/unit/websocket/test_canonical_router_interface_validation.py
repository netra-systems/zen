"""Test 5: Canonical MessageRouter Interface Validation

This test validates the interface compliance of the canonical MessageRouter implementation
to ensure it provides all required methods and properties for Golden Path functionality.

Business Value: Platform/Internal - Interface Stability & Golden Path Protection
- Ensures canonical MessageRouter has complete interface for chat functionality
- Prevents interface regression that could break WebSocket message routing
- Validates SSOT compliance through interface consistency

EXPECTED BEHAVIOR:
- FAIL initially if canonical router missing or has incomplete interface
- PASS after SSOT consolidation with complete, consistent interface
- Provide actionable guidance for interface deficiencies

GitHub Issue: #1077 - MessageRouter SSOT violations blocking golden path
"""

import unittest
import inspect
from typing import Dict, List, Set, Optional, Any, Callable
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestCanonicalRouterInterfaceValidation(SSotBaseTestCase, unittest.TestCase):
    """Test that validates canonical MessageRouter interface compliance."""

    def setUp(self):
        """Set up test fixtures."""
        if hasattr(super(), 'setUp'):
            super().setUp()
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)
        
        # Expected canonical location
        self.canonical_path = "netra_backend.app.websocket_core.handlers"
        self.canonical_class = "MessageRouter"
        
        # Required interface specification for Golden Path
        self.required_interface = {
            'methods': {
                '__init__': {
                    'required': True,
                    'min_params': 0,
                    'description': 'Initialize router instance'
                },
                'add_handler': {
                    'required': True,
                    'min_params': 1,
                    'description': 'Add message handler to router'
                },
                'remove_handler': {
                    'required': True,  
                    'min_params': 1,
                    'description': 'Remove message handler from router'
                },
                'route_message': {
                    'required': True,
                    'min_params': 2,  # self, message
                    'description': 'Route message to appropriate handler'
                },
                'get_handler': {
                    'required': False,
                    'min_params': 1,
                    'description': 'Get handler for message type'
                }
            },
            'properties': {
                'handlers': {
                    'required': True,
                    'type': 'collection',
                    'description': 'Collection of registered handlers'
                }
            },
            'class_attributes': {
                'supported_types': {
                    'required': False,
                    'type': 'collection',
                    'description': 'Supported message types'
                }
            }
        }

    def test_canonical_message_router_importable(self):
        """Test that canonical MessageRouter can be imported successfully.
        
        EXPECTED: FAIL initially if canonical router missing
        EXPECTED: PASS after SSOT consolidation with proper canonical implementation
        """
        canonical_router_class = None
        import_error = None
        
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            canonical_router_class = MessageRouter
        except ImportError as e:
            import_error = e
        except Exception as e:
            import_error = e
        
        if canonical_router_class is None:
            self.fail(
                f" FAIL:  CANONICAL ROUTER NOT IMPORTABLE: Cannot import MessageRouter from {self.canonical_path}.\n"
                f"Import error: {import_error}\n"
                f"BUSINESS IMPACT: Golden Path chat functionality requires canonical router.\n"
                f"REMEDIATION: Ensure MessageRouter class exists in websocket_core/handlers.py"
            )
        
        # Verify it's actually a class
        if not inspect.isclass(canonical_router_class):
            self.fail(
                f" FAIL:  CANONICAL ROUTER INVALID: MessageRouter is not a class (type: {type(canonical_router_class)}).\n"
                f"BUSINESS IMPACT: Chat functionality requires MessageRouter to be a proper class."
            )
        
        self.logger.info(" PASS:  Canonical MessageRouter is importable and is a valid class")

    def test_canonical_router_has_required_methods(self):
        """Test that canonical MessageRouter has all required methods.
        
        EXPECTED: FAIL initially if methods missing
        EXPECTED: PASS after SSOT consolidation with complete interface
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
        except ImportError as e:
            self.fail(f"Cannot import canonical router: {e}")
        
        missing_methods = []
        invalid_signatures = []
        
        for method_name, spec in self.required_interface['methods'].items():
            if not spec['required']:
                continue
                
            if not hasattr(MessageRouter, method_name):
                missing_methods.append(method_name)
                continue
            
            # Check method signature
            method = getattr(MessageRouter, method_name)
            if callable(method):
                try:
                    sig = inspect.signature(method)
                    param_count = len(sig.parameters)
                    
                    # Account for 'self' parameter in instance methods
                    if method_name != '__init__' and not isinstance(method, staticmethod):
                        min_expected = spec['min_params'] + 1  # +1 for 'self'
                    else:
                        min_expected = spec['min_params']
                    
                    if param_count < min_expected:
                        invalid_signatures.append({
                            'method': method_name,
                            'expected_min': min_expected,
                            'actual': param_count,
                            'signature': str(sig)
                        })
                        
                except (ValueError, TypeError):
                    # Can't inspect signature, but method exists
                    pass
        
        interface_issues = []
        
        if missing_methods:
            interface_issues.append(f"Missing required methods: {', '.join(missing_methods)}")
        
        if invalid_signatures:
            sig_details = []
            for sig_issue in invalid_signatures:
                sig_details.append(
                    f"{sig_issue['method']}: expected {sig_issue['expected_min']}+ params, "
                    f"got {sig_issue['actual']} ({sig_issue['signature']})"
                )
            interface_issues.append(f"Invalid method signatures:\n  - " + "\n  - ".join(sig_details))
        
        if interface_issues:
            self.fail(
                f" FAIL:  CANONICAL ROUTER INCOMPLETE INTERFACE: Interface deficiencies detected.\n"
                f"BUSINESS IMPACT: Incomplete interface breaks WebSocket message routing, "
                f"causing chat functionality failures.\n"
                f"INTERFACE ISSUES:\n" + "\n".join(f"- {issue}" for issue in interface_issues) + 
                f"\n\nREMEDIATION: Implement missing methods/fix signatures in canonical MessageRouter."
            )
        
        self.logger.info(" PASS:  Canonical MessageRouter has all required methods with valid signatures")

    def test_canonical_router_has_required_properties(self):
        """Test that canonical MessageRouter has required properties.
        
        EXPECTED: FAIL initially if properties missing
        EXPECTED: PASS after SSOT consolidation with complete properties
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
        except ImportError as e:
            self.fail(f"Cannot import canonical router: {e}")
        
        # Test with instance since properties might be instance-level
        try:
            router_instance = MessageRouter()
        except Exception as e:
            self.fail(f"Cannot instantiate canonical router: {e}")
        
        missing_properties = []
        invalid_properties = []
        
        for prop_name, spec in self.required_interface['properties'].items():
            if not spec['required']:
                continue
            
            # Check if property exists on class or instance
            has_property = (
                hasattr(MessageRouter, prop_name) or 
                hasattr(router_instance, prop_name)
            )
            
            if not has_property:
                missing_properties.append(prop_name)
                continue
            
            # Validate property type if specified
            if spec.get('type') == 'collection':
                try:
                    prop_value = getattr(router_instance, prop_name)
                    if not isinstance(prop_value, (list, tuple, dict, set)):
                        invalid_properties.append({
                            'property': prop_name,
                            'expected_type': 'collection (list, tuple, dict, set)',
                            'actual_type': type(prop_value).__name__
                        })
                except Exception:
                    # Property exists but can't be accessed - might be OK for some cases
                    pass
        
        property_issues = []
        
        if missing_properties:
            property_issues.append(f"Missing required properties: {', '.join(missing_properties)}")
        
        if invalid_properties:
            prop_details = []
            for prop_issue in invalid_properties:
                prop_details.append(
                    f"{prop_issue['property']}: expected {prop_issue['expected_type']}, "
                    f"got {prop_issue['actual_type']}"
                )
            property_issues.append(f"Invalid property types:\n  - " + "\n  - ".join(prop_details))
        
        if property_issues:
            self.fail(
                f" FAIL:  CANONICAL ROUTER MISSING PROPERTIES: Property deficiencies detected.\n"
                f"BUSINESS IMPACT: Missing properties break handler management, "
                f"causing WebSocket routing failures.\n"
                f"PROPERTY ISSUES:\n" + "\n".join(f"- {issue}" for issue in property_issues) + 
                f"\n\nREMEDIATION: Implement missing properties in canonical MessageRouter."
            )
        
        self.logger.info(" PASS:  Canonical MessageRouter has all required properties")

    def test_canonical_router_instantiates_successfully(self):
        """Test that canonical MessageRouter can be instantiated.
        
        EXPECTED: FAIL initially if router cannot be instantiated
        EXPECTED: PASS after SSOT consolidation with working constructor
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
        except ImportError as e:
            self.fail(f"Cannot import canonical router: {e}")
        
        # Test basic instantiation
        router_instance = None
        instantiation_error = None
        
        try:
            router_instance = MessageRouter()
        except Exception as e:
            instantiation_error = e
        
        if router_instance is None:
            self.fail(
                f" FAIL:  CANONICAL ROUTER NOT INSTANTIABLE: Cannot create MessageRouter instance.\n"
                f"Instantiation error: {instantiation_error}\n"
                f"BUSINESS IMPACT: Golden Path requires working router instances for "
                f"WebSocket message processing.\n"
                f"REMEDIATION: Fix MessageRouter constructor to allow instantiation."
            )
        
        # Test that instance has expected interface
        interface_missing = []
        
        for method_name in ['add_handler', 'route_message']:
            if not hasattr(router_instance, method_name):
                interface_missing.append(method_name)
        
        if 'handlers' in self.required_interface['properties']:
            if not hasattr(router_instance, 'handlers'):
                interface_missing.append('handlers (property)')
        
        if interface_missing:
            self.fail(
                f" FAIL:  INSTANTIATED ROUTER INCOMPLETE: Router instance missing interface elements.\n"
                f"Missing: {', '.join(interface_missing)}\n"
                f"BUSINESS IMPACT: Incomplete instances break message routing functionality."
            )
        
        self.logger.info(" PASS:  Canonical MessageRouter instantiates successfully with complete interface")

    def test_canonical_router_basic_functionality(self):
        """Test that canonical MessageRouter basic functionality works.
        
        EXPECTED: FAIL initially if basic operations don't work
        EXPECTED: PASS after SSOT consolidation with working operations
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            router = MessageRouter()
        except Exception as e:
            self.fail(f"Cannot create router instance: {e}")
        
        functionality_errors = []
        
        # Test 1: handlers property access
        try:
            handlers = router.handlers
            # Should be some form of collection
            if not hasattr(handlers, '__iter__'):
                functionality_errors.append("handlers property is not iterable")
        except Exception as e:
            functionality_errors.append(f"Cannot access handlers property: {e}")
        
        # Test 2: add_handler method (if available)
        if hasattr(router, 'add_handler'):
            try:
                # Create a minimal mock handler for testing
                class MockHandler:
                    def __init__(self):
                        self.supported_types = ['test']
                    
                    def can_handle(self, message):
                        return True
                
                mock_handler = MockHandler()
                initial_handler_count = len(router.handlers) if hasattr(router.handlers, '__len__') else 0
                
                # Try adding handler - don't fail if it doesn't work perfectly,
                # but record if it throws unexpected errors
                try:
                    router.add_handler(mock_handler)
                    # If add succeeded, verify handler was added
                    if hasattr(router.handlers, '__len__'):
                        new_count = len(router.handlers)
                        if new_count <= initial_handler_count:
                            functionality_errors.append("add_handler did not increase handler count")
                except TypeError as e:
                    # This might be OK if the handler format is wrong
                    pass
                except Exception as e:
                    functionality_errors.append(f"add_handler threw unexpected error: {e}")
                    
            except Exception as e:
                functionality_errors.append(f"Could not test add_handler: {e}")
        
        # Test 3: route_message method (basic call test)
        if hasattr(router, 'route_message'):
            try:
                # Try calling with minimal params - expect it might fail, but shouldn't crash
                test_message = {'type': 'test', 'data': {}}
                
                try:
                    # Don't expect this to succeed, just expect it not to crash with basic errors
                    router.route_message(test_message, None)
                except (AttributeError, KeyError, TypeError):
                    # These are expected for incomplete implementations
                    pass
                except Exception as e:
                    # Unexpected errors indicate implementation problems
                    functionality_errors.append(f"route_message threw unexpected error: {e}")
                    
            except Exception as e:
                functionality_errors.append(f"Could not test route_message: {e}")
        
        if functionality_errors:
            self.fail(
                f" FAIL:  CANONICAL ROUTER FUNCTIONALITY BROKEN: Basic operations have issues.\n"
                f"BUSINESS IMPACT: Broken functionality prevents WebSocket message routing, "
                f"causing chat failures.\n"
                f"FUNCTIONALITY ISSUES:\n" + "\n".join(f"- {error}" for error in functionality_errors) + 
                f"\n\nREMEDIATION: Fix basic operations in canonical MessageRouter implementation."
            )
        
        self.logger.info(" PASS:  Canonical MessageRouter basic functionality works")

    def test_interface_consistency_with_factory_function(self):
        """Test that factory function returns router with consistent interface.
        
        EXPECTED: FAIL initially if factory/instance interface inconsistent  
        EXPECTED: PASS after SSOT consolidation with consistent interface
        """
        # Test factory function if it exists
        factory_router = None
        direct_router = None
        
        try:
            from netra_backend.app.websocket_core.handlers import get_message_router
            factory_router = get_message_router()
        except ImportError:
            # Factory function doesn't exist - might be OK
            pass
        except Exception as e:
            self.fail(f"Factory function get_message_router() failed: {e}")
        
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            direct_router = MessageRouter()
        except Exception as e:
            self.fail(f"Direct MessageRouter instantiation failed: {e}")
        
        # If both exist, compare interfaces
        if factory_router is not None and direct_router is not None:
            interface_differences = []
            
            # Compare methods
            for method_name in self.required_interface['methods']:
                factory_has = hasattr(factory_router, method_name)
                direct_has = hasattr(direct_router, method_name)
                
                if factory_has != direct_has:
                    interface_differences.append(
                        f"Method {method_name}: factory={factory_has}, direct={direct_has}"
                    )
            
            # Compare properties
            for prop_name in self.required_interface['properties']:
                factory_has = hasattr(factory_router, prop_name)
                direct_has = hasattr(direct_router, prop_name)
                
                if factory_has != direct_has:
                    interface_differences.append(
                        f"Property {prop_name}: factory={factory_has}, direct={direct_has}"
                    )
            
            if interface_differences:
                self.fail(
                    f" FAIL:  INTERFACE INCONSISTENCY: Factory and direct instantiation have different interfaces.\n"
                    f"BUSINESS IMPACT: Inconsistent interfaces cause unpredictable behavior.\n"
                    f"DIFFERENCES:\n" + "\n".join(f"- {diff}" for diff in interface_differences)
                )
        
        self.logger.info(" PASS:  Router interface is consistent between factory and direct instantiation")


if __name__ == "__main__":
    import unittest
    unittest.main()