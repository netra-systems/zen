"""
Interface Violation Tests - Issue #186 WebSocket Manager Fragmentation

Tests that prove WebSocket manager interface violations exist across different implementations.
These tests are designed to FAIL initially, proving that managers don't implement
consistent interfaces that would enable proper factory delegation.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Stability - Prove interface mismatches break factory delegation
- Value Impact: Demonstrate root cause of WebSocket event delivery failures
- Revenue Impact: Enable interface standardization to restore $500K+ ARR chat functionality

SSOT Violations This Module Proves:
1. Missing send_event method on factory-created managers
2. Constructor argument count mismatches (1 vs 2 args)
3. Protocol compliance failures across implementations
4. Method signature inconsistencies between manager types
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import asyncio
import inspect
import unittest
from typing import Any, Dict, List, Set, Type, Optional, Protocol, runtime_checkable
from unittest.mock import Mock, AsyncMock, patch
import warnings

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@runtime_checkable
class ExpectedWebSocketManagerProtocol(Protocol):
    """
    Expected protocol that all WebSocket managers should implement.
    This represents what the Golden Path requires for proper operation.
    """
    
    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Send WebSocket event to user - CRITICAL for Golden Path"""
        ...
        
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send general message to user"""
        ...
        
    async def add_connection(self, connection: Any) -> None:
        """Add WebSocket connection"""
        ...
        
    async def remove_connection(self, connection_id: str) -> None:
        """Remove WebSocket connection"""
        ...
        
    def is_connection_active(self, user_id: str) -> bool:
        """Check if connection is active for user"""
        ...


class TestWebSocketManagerInterfaceViolations(SSotAsyncTestCase):
    """
    Tests to prove WebSocket manager interface violations exist.
    
    These tests are designed to FAIL initially, proving interface inconsistencies.
    After interface standardization, they should PASS.
    """

    def test_missing_send_event_method_on_factory_managers(self):
        """
        Test that factory-created managers are missing critical send_event method.
        
        EXPECTED INITIAL STATE: FAIL - Factory managers missing send_event method
        EXPECTED POST-SSOT STATE: PASS - All managers have send_event method
        
        VIOLATION BEING PROVED: Factory managers missing critical Golden Path method
        """
        missing_method_violations = []
        
        try:
            # Test WebSocketManagerFactory created managers
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            factory = WebSocketManagerFactory()
            
            # Create test user context
            import uuid
            test_user_id = str(uuid.uuid4())
            test_connection_id = str(uuid.uuid4())
            
            try:
                user_context = UserExecutionContext.from_websocket_request(
                    user_id=test_user_id,
                    websocket_client_id=test_connection_id,
                    operation="test_interface_validation"
                )
                
                # Test factory manager creation
                if hasattr(factory, 'create_isolated_manager'):
                    try:
                        manager = factory.create_isolated_manager(user_context.user_id, test_connection_id)
                        
                        # Check if manager has send_event method (CRITICAL for Golden Path)
                        if not hasattr(manager, 'send_event'):
                            missing_method_violations.append(
                                f"Factory-created manager missing send_event method. "
                                f"Manager type: {type(manager)}. "
                                f"Available methods: {[m for m in dir(manager) if not m.startswith('_')]}"
                            )
                        elif not callable(getattr(manager, 'send_event')):
                            missing_method_violations.append(
                                f"Factory-created manager send_event is not callable. "
                                f"Type: {type(getattr(manager, 'send_event'))}"
                            )
                        else:
                            # Test method signature
                            try:
                                sig = inspect.signature(manager.send_event)
                                params = list(sig.parameters.keys())
                                
                                # Expected signature: send_event(self, event_type: str, data: Dict[str, Any])
                                expected_min_params = ['event_type', 'data']
                                missing_params = [p for p in expected_min_params if p not in params]
                                
                                if missing_params:
                                    missing_method_violations.append(
                                        f"Factory-created manager send_event missing parameters: {missing_params}. "
                                        f"Found parameters: {params}"
                                    )
                            except Exception as e:
                                missing_method_violations.append(
                                    f"Could not analyze send_event signature: {e}"
                                )
                        
                        # Check other critical methods
                        critical_methods = ['send_message', 'add_connection', 'remove_connection', 'is_connection_active']
                        for method_name in critical_methods:
                            if not hasattr(manager, method_name):
                                missing_method_violations.append(
                                    f"Factory-created manager missing {method_name} method"
                                )
                                
                    except Exception as e:
                        missing_method_violations.append(f"Factory manager creation failed: {e}")
                        
            except Exception as e:
                missing_method_violations.append(f"User context creation failed: {e}")
                
        except ImportError as e:
            missing_method_violations.append(f"Required factory classes not available: {e}")
        except Exception as e:
            missing_method_violations.append(f"Factory testing failed: {e}")
            
        # Test direct manager implementations
        manager_classes = []
        
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager_classes.append(('UnifiedWebSocketManager', UnifiedWebSocketManager))
        except ImportError:
            pass
            
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager
            manager_classes.append(('WebSocketManager', WebSocketManager))
        except ImportError:
            pass
        
        # Test direct instantiation of managers
        for manager_name, manager_class in manager_classes:
            try:
                # Test with no arguments (backward compatibility)
                manager = manager_class()
                
                if not hasattr(manager, 'send_event'):
                    missing_method_violations.append(
                        f"{manager_name} direct instantiation missing send_event method"
                    )
                    
            except Exception as e:
                # This might be expected if constructor requires arguments
                logger.debug(f"Could not directly instantiate {manager_name}: {e}")
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: All managers should have send_event method
        self.assertEqual(
            len(missing_method_violations), 0,
            f"SSOT VIOLATION: Factory managers missing critical methods: {missing_method_violations}. "
            f"This proves interface compliance is broken across manager implementations."
        )

    def test_constructor_argument_count_mismatch(self):
        """
        Test constructor signature mismatches between factory and manager expectations.
        
        EXPECTED INITIAL STATE: FAIL - Constructor expects different argument counts
        EXPECTED POST-SSOT STATE: PASS - Constructor signatures are consistent
        
        VIOLATION BEING PROVED: Factory passes wrong number of arguments to constructors
        """
        constructor_violations = []
        
        # Test known problematic constructor patterns
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            # Test 1: Factory method signature vs manager constructor
            factory = WebSocketManagerFactory()
            
            if hasattr(factory, 'create_isolated_manager'):
                factory_sig = inspect.signature(factory.create_isolated_manager)
                factory_params = list(factory_sig.parameters.keys())
                
                manager_sig = inspect.signature(UnifiedWebSocketManager.__init__)
                manager_params = list(manager_sig.parameters.keys())
                
                # Remove 'self' from manager params for comparison
                manager_params_no_self = [p for p in manager_params if p != 'self']
                factory_params_no_self = [p for p in factory_params if p != 'self']
                
                # Test argument count compatibility
                if len(factory_params_no_self) != len(manager_params_no_self):
                    # Different argument counts - check if factory does delegation correctly
                    try:
                        import uuid
                        test_user_id = str(uuid.uuid4())
                        test_connection_id = str(uuid.uuid4())
                        
                        # Test if factory can create manager with direct constructor
                        try:
                            # This should fail if constructor signatures don't match
                            if len(manager_params_no_self) == 0:
                                # Manager takes no args, factory should use different creation pattern
                                manager = UnifiedWebSocketManager()
                                
                                # But then factory should configure it somehow
                                if not hasattr(manager, '_user_context') and not hasattr(manager, 'user_id'):
                                    constructor_violations.append(
                                        f"Factory creates manager with no user context configuration. "
                                        f"Manager params: {manager_params}, Factory params: {factory_params}"
                                    )
                            else:
                                # Manager expects arguments, test if factory passes them correctly
                                try:
                                    # This should fail if factory doesn't match manager constructor
                                    manager = UnifiedWebSocketManager(test_user_id, test_connection_id)
                                    constructor_violations.append(
                                        f"Manager constructor accepts arguments but factory pattern unclear. "
                                        f"Manager params: {manager_params}, Factory params: {factory_params}"
                                    )
                                except TypeError as e:
                                    # Expected if constructor signatures are mismatched
                                    constructor_violations.append(
                                        f"Constructor signature mismatch: Factory expects {len(factory_params_no_self)} args, "
                                        f"Manager constructor expects {len(manager_params_no_self)} args. "
                                        f"Factory params: {factory_params}, Manager params: {manager_params}. Error: {e}"
                                    )
                                    
                        except Exception as e:
                            constructor_violations.append(f"Constructor testing failed: {e}")
                            
                    except Exception as e:
                        constructor_violations.append(f"Argument count testing failed: {e}")
                        
        except ImportError as e:
            constructor_violations.append(f"Required classes for constructor testing not available: {e}")
        except Exception as e:
            constructor_violations.append(f"Constructor analysis failed: {e}")
        
        # Test multiple manager constructors for consistency
        manager_constructors = {}
        
        manager_classes = []
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager_classes.append(('UnifiedWebSocketManager', UnifiedWebSocketManager))
        except ImportError:
            pass
            
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager  
            manager_classes.append(('WebSocketManager', WebSocketManager))
        except ImportError:
            pass
        
        for name, cls in manager_classes:
            try:
                sig = inspect.signature(cls.__init__)
                params = [p for p in sig.parameters.keys() if p != 'self']
                manager_constructors[name] = {
                    'param_count': len(params),
                    'params': params,
                    'signature': str(sig)
                }
            except Exception as e:
                constructor_violations.append(f"Could not analyze {name} constructor: {e}")
        
        # Check for constructor consistency across managers
        if len(manager_constructors) > 1:
            param_counts = {name: info['param_count'] for name, info in manager_constructors.items()}
            unique_counts = set(param_counts.values())
            
            if len(unique_counts) > 1:
                constructor_violations.append(
                    f"Inconsistent constructor parameter counts across managers: {param_counts}. "
                    f"Manager constructors: {manager_constructors}"
                )
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: Constructor signatures should be consistent
        self.assertEqual(
            len(constructor_violations), 0,
            f"SSOT VIOLATION: Constructor argument mismatches found: {constructor_violations}. "
            f"This proves factory delegation patterns are broken due to signature incompatibility."
        )

    def test_protocol_compliance_failures(self):
        """
        Test that manager implementations don't comply with expected protocols.
        
        EXPECTED INITIAL STATE: FAIL - Managers don't implement consistent protocol
        EXPECTED POST-SSOT STATE: PASS - All managers implement same protocol
        
        VIOLATION BEING PROVED: Protocol compliance failures prevent interface substitution
        """
        protocol_violations = []
        
        # Test manager classes against expected protocol
        manager_classes = []
        
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager_classes.append(('UnifiedWebSocketManager', UnifiedWebSocketManager))
        except ImportError:
            pass
            
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager
            manager_classes.append(('WebSocketManager', WebSocketManager))
        except ImportError:
            pass
            
        # Test protocol compliance for each manager
        for manager_name, manager_class in manager_classes:
            try:
                # Test instantiation
                manager = manager_class()
                
                # Test against expected protocol
                try:
                    # Check if instance implements expected protocol
                    is_protocol_compliant = isinstance(manager, ExpectedWebSocketManagerProtocol)
                    
                    if not is_protocol_compliant:
                        # Check which methods are missing
                        required_methods = [
                            'send_event', 'send_message', 'add_connection', 
                            'remove_connection', 'is_connection_active'
                        ]
                        
                        missing_methods = []
                        signature_mismatches = []
                        
                        for method_name in required_methods:
                            if not hasattr(manager, method_name):
                                missing_methods.append(method_name)
                            else:
                                method = getattr(manager, method_name)
                                if not callable(method):
                                    missing_methods.append(f"{method_name} (not callable)")
                                else:
                                    # Check method signature
                                    try:
                                        sig = inspect.signature(method)
                                        
                                        # Check specific method signatures
                                        if method_name == 'send_event':
                                            params = list(sig.parameters.keys())
                                            if 'event_type' not in params or 'data' not in params:
                                                signature_mismatches.append(
                                                    f"{method_name} signature mismatch: {params}"
                                                )
                                        elif method_name == 'send_message':
                                            params = list(sig.parameters.keys())
                                            if 'message' not in params:
                                                signature_mismatches.append(
                                                    f"{method_name} signature mismatch: {params}"
                                                )
                                                
                                    except Exception as e:
                                        signature_mismatches.append(
                                            f"{method_name} signature analysis failed: {e}"
                                        )
                        
                        if missing_methods or signature_mismatches:
                            protocol_violations.append(
                                f"{manager_name} protocol compliance failure. "
                                f"Missing methods: {missing_methods}. "
                                f"Signature mismatches: {signature_mismatches}"
                            )
                            
                except Exception as e:
                    protocol_violations.append(f"{manager_name} protocol compliance testing failed: {e}")
                    
            except Exception as e:
                protocol_violations.append(f"Could not instantiate {manager_name} for protocol testing: {e}")
        
        # Test factory-created managers for protocol compliance
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            factory = WebSocketManagerFactory()
            
            if hasattr(factory, 'create_isolated_manager'):
                import uuid
                test_user_id = str(uuid.uuid4())
                test_connection_id = str(uuid.uuid4())
                
                try:
                    user_context = UserExecutionContext.from_websocket_request(
                        user_id=test_user_id,
                        websocket_client_id=test_connection_id,
                        operation="protocol_compliance_test"
                    )
                    
                    manager = factory.create_isolated_manager(user_context.user_id, test_connection_id)
                    
                    # Test protocol compliance of factory-created manager
                    is_protocol_compliant = isinstance(manager, ExpectedWebSocketManagerProtocol)
                    
                    if not is_protocol_compliant:
                        protocol_violations.append(
                            f"Factory-created manager not protocol compliant. "
                            f"Type: {type(manager)}"
                        )
                        
                except Exception as e:
                    protocol_violations.append(f"Factory manager protocol testing failed: {e}")
                    
        except ImportError:
            pass
        except Exception as e:
            protocol_violations.append(f"Factory protocol testing failed: {e}")
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: All managers should be protocol compliant
        self.assertEqual(
            len(protocol_violations), 0,
            f"SSOT VIOLATION: Protocol compliance failures found: {protocol_violations}. "
            f"This proves managers don't implement consistent interfaces required for substitution."
        )

    def test_method_signature_inconsistencies(self):
        """
        Test that method signatures are inconsistent across manager implementations.
        
        EXPECTED INITIAL STATE: FAIL - Method signatures vary between implementations
        EXPECTED POST-SSOT STATE: PASS - All implementations have consistent method signatures
        
        VIOLATION BEING PROVED: Method signature inconsistencies prevent interface unification
        """
        signature_violations = []
        
        # Collect method signatures from different managers
        manager_signatures = {}
        
        manager_classes = []
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager_classes.append(('UnifiedWebSocketManager', UnifiedWebSocketManager))
        except ImportError:
            pass
            
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager
            manager_classes.append(('WebSocketManager', WebSocketManager))
        except ImportError:
            pass
        
        # Common methods that should have consistent signatures
        target_methods = [
            'send_message', 'add_connection', 'remove_connection', 
            'is_connection_active', 'send_event'
        ]
        
        for manager_name, manager_class in manager_classes:
            manager_methods = {}
            
            for method_name in target_methods:
                if hasattr(manager_class, method_name):
                    method = getattr(manager_class, method_name)
                    if callable(method):
                        try:
                            sig = inspect.signature(method)
                            manager_methods[method_name] = {
                                'params': list(sig.parameters.keys()),
                                'signature': str(sig),
                                'return_annotation': sig.return_annotation
                            }
                        except Exception as e:
                            manager_methods[method_name] = {'error': str(e)}
                            
            manager_signatures[manager_name] = manager_methods
        
        # Compare signatures across managers
        if len(manager_signatures) > 1:
            manager_names = list(manager_signatures.keys())
            
            for method_name in target_methods:
                method_signatures = {}
                
                for manager_name in manager_names:
                    if method_name in manager_signatures[manager_name]:
                        method_info = manager_signatures[manager_name][method_name]
                        if 'error' not in method_info:
                            method_signatures[manager_name] = method_info
                
                # Check for signature consistency
                if len(method_signatures) > 1:
                    param_lists = [info['params'] for info in method_signatures.values()]
                    unique_param_lists = list(set(tuple(params) for params in param_lists))
                    
                    if len(unique_param_lists) > 1:
                        signature_violations.append(
                            f"Method {method_name} has inconsistent signatures across managers: "
                            f"{dict(zip(method_signatures.keys(), param_lists))}"
                        )
                    
                    # Check return annotation consistency
                    return_annotations = [str(info['return_annotation']) for info in method_signatures.values()]
                    unique_returns = set(return_annotations)
                    
                    if len(unique_returns) > 1:
                        signature_violations.append(
                            f"Method {method_name} has inconsistent return annotations: "
                            f"{dict(zip(method_signatures.keys(), return_annotations))}"
                        )
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: Method signatures should be consistent
        self.assertEqual(
            len(signature_violations), 0,
            f"SSOT VIOLATION: Method signature inconsistencies found: {signature_violations}. "
            f"Manager signatures: {manager_signatures}. "
            f"This proves method signatures need standardization across implementations."
        )


if __name__ == '__main__':
    unittest.main()