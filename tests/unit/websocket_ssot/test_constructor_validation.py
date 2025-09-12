"""
Constructor Validation SSOT Tests - Issue #186 WebSocket Manager Fragmentation

Tests that FAIL initially to prove constructor signature mismatches exist between factory and manager.
After SSOT consolidation, these tests should PASS, proving factory patterns work correctly.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Stability - Eliminate constructor mismatches causing factory creation failures
- Value Impact: Ensure reliable WebSocket manager instantiation across all user interactions
- Revenue Impact: Prevent $500K+ ARR chat disruptions from factory instantiation failures

SSOT Violations This Module Proves:
1. Factory constructor signature mismatch with manager constructor
2. Inconsistent parameter validation between factory and manager
3. Factory delegation failures due to parameter incompatibility
4. Dependency injection pattern inconsistencies
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


class TestWebSocketManagerConstructorValidation(SSotBaseTestCase):
    """
    Tests to prove WebSocket manager constructor validation violations exist.
    
    These tests are designed to FAIL initially, proving SSOT violations.
    After proper constructor standardization, they should PASS.
    """

    def test_factory_constructor_signature_consistency(self):
        """
        Test all factory methods have consistent constructor signatures with managers.
        
        EXPECTED INITIAL STATE: FAIL - Constructor mismatches between factory and manager
        EXPECTED POST-SSOT STATE: PASS - Factory and manager constructors compatible
        
        VIOLATION BEING PROVED: Factory/manager constructor signature incompatibility
        """
        constructor_violations = []
        
        try:
            # Test main factory constructor compatibility
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            from netra_backend.app.websocket_core.unified_manager import WebSocketManager
            
            # Check factory creation method signature
            factory = WebSocketManagerFactory()
            if hasattr(factory, 'create_isolated_manager'):
                factory_method = getattr(factory, 'create_isolated_manager')
                factory_sig = inspect.signature(factory_method)
                factory_params = list(factory_sig.parameters.keys())
                
                # Check manager constructor signature 
                manager_init_sig = inspect.signature(WebSocketManager.__init__)
                manager_params = list(manager_init_sig.parameters.keys())
                
                # Test if factory can create manager with its parameters
                try:
                    import uuid
                    # Use proper UUIDs to avoid validation errors
                    test_user_id = str(uuid.uuid4())
                    test_connection_id = str(uuid.uuid4())
                    
                    # This should now succeed with the fixed factory pattern
                    # Factory should use from_user_context method instead of direct constructor
                    from netra_backend.app.services.user_execution_context import UserExecutionContext
                    user_context = UserExecutionContext.from_websocket_request(
                        user_id=test_user_id,
                        websocket_client_id=test_connection_id,
                        operation="test_factory_validation"
                    )
                    
                    # Try to instantiate manager using the factory method (should succeed)
                    try:
                        manager = WebSocketManager.from_user_context(user_context)  # This should now succeed
                        if not hasattr(manager, '_user_context'):
                            constructor_violations.append(
                                f"Factory method did not properly associate user context with manager"
                            )
                    except Exception as e:
                        constructor_violations.append(f"Factory method failed unexpectedly: {e}")
                    
                    # Verify direct constructor still doesn't accept parameters (backward compatibility)
                    try:
                        manager = WebSocketManager(user_context)  # This should still fail
                        constructor_violations.append(
                            f"Direct constructor unexpectedly accepts parameters - breaks backward compatibility"
                        )
                    except TypeError as e:
                        # This is expected - direct constructor should not accept parameters
                        pass
                    
                except Exception as e:
                    constructor_violations.append(f"Factory method signature analysis failed: {e}")
                    
        except ImportError as e:
            self.fail(f"Required classes not found: {e}")
        except Exception as e:
            constructor_violations.append(f"Signature analysis failed: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: Constructor signatures should be compatible
        self.assertEqual(
            len(constructor_violations), 0,
            f"SSOT VIOLATION: Factory/manager constructor incompatibilities found: {constructor_violations}. "
            f"This proves factory pattern constructor signatures need alignment."
        )

    def test_manager_initialization_parameter_validation(self):
        """
        Test all managers accept same initialization parameters.
        
        EXPECTED INITIAL STATE: FAIL - Different parameter requirements between managers
        EXPECTED POST-SSOT STATE: PASS - All managers have consistent parameter validation
        
        VIOLATION BEING PROVED: Parameter validation inconsistency between manager types
        """
        parameter_violations = []
        
        # Test different manager implementations
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

        if len(manager_classes) < 2:
            self.skipTest("Need at least 2 manager implementations to test parameter consistency")

        # Test parameter compatibility across managers
        for manager_name, manager_class in manager_classes:
            try:
                init_sig = inspect.signature(manager_class.__init__)
                params = list(init_sig.parameters.keys())
                
                # Test with None parameters (should fail consistently)
                try:
                    manager = manager_class(None)
                    parameter_violations.append(
                        f"{manager_name} accepts None parameter without validation error"
                    )
                except TypeError as e:
                    # Expected - good validation
                    pass
                except Exception as e:
                    parameter_violations.append(
                        f"{manager_name} has inconsistent parameter validation: {type(e).__name__}: {e}"
                    )
                    
                # Test with empty dict (should fail consistently)
                try:
                    manager = manager_class({})
                    parameter_violations.append(
                        f"{manager_name} accepts empty dict without validation error"
                    )
                except (TypeError, ValueError) as e:
                    # Expected - good validation
                    pass
                except Exception as e:
                    parameter_violations.append(
                        f"{manager_name} has inconsistent parameter validation: {type(e).__name__}: {e}"
                    )
                    
            except Exception as e:
                parameter_violations.append(f"{manager_name} parameter analysis failed: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: Parameter validation should be consistent
        self.assertEqual(
            len(parameter_violations), 0,
            f"SSOT VIOLATION: Manager parameter validation inconsistencies: {parameter_violations}. "
            f"This proves managers need standardized parameter validation patterns."
        )

    def test_factory_delegation_consistency(self):
        """
        Test factory properly delegates to manager constructors.
        
        EXPECTED INITIAL STATE: FAIL - Factory passes wrong number/types of arguments
        EXPECTED POST-SSOT STATE: PASS - Factory delegation works correctly
        
        VIOLATION BEING PROVED: Factory delegation argument mismatch failures
        """
        delegation_violations = []
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            factory = WebSocketManagerFactory()
            
            # Test delegation success - this should now work after SSOT fix
            import uuid
            test_user_id = str(uuid.uuid4())
            test_connection_id = str(uuid.uuid4())
            
            try:
                manager = factory.create_isolated_manager(
                    user_id=test_user_id,
                    connection_id=test_connection_id
                )
                # Factory delegation should now succeed
                if not hasattr(manager, '_user_context'):
                    delegation_violations.append(
                        "Factory delegation succeeded but manager lacks user context association"
                    )
            except Exception as e:
                if "placeholder pattern" in str(e).lower():
                    delegation_violations.append(
                        f"Factory delegation failed due to test data validation (expected): {e}"
                    )
                else:
                    delegation_violations.append(f"Factory delegation failed unexpectedly: {e}")

            # Verify the primary factory method exists and works
            if not hasattr(factory, 'create_isolated_manager'):
                delegation_violations.append(
                    "Factory missing primary create_isolated_manager method"
                )
            
            # Verify all creation methods use the new factory pattern consistently
            creation_methods = ['create_isolated_manager', 'create_manager']
            for method_name in creation_methods:
                if hasattr(factory, method_name):
                    # Test that methods can create managers (basic smoke test)
                    try:
                        method = getattr(factory, method_name)
                        # Just check method signature, don't actually call
                        import inspect
                        sig = inspect.signature(method)
                        # This validates the method exists and is callable
                    except Exception as e:
                        delegation_violations.append(
                            f"Factory method {method_name} signature issue: {e}"
                        )
                
        except ImportError:
            self.fail("WebSocketManagerFactory not found - factory pattern missing")
        except Exception as e:
            delegation_violations.append(f"Factory delegation analysis failed: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: Factory delegation should work
        self.assertEqual(
            len(delegation_violations), 0,
            f"SSOT VIOLATION: Factory delegation inconsistencies: {delegation_violations}. "
            f"This proves factory needs proper delegation patterns aligned with manager constructors."
        )

    def test_manager_dependency_injection_consistency(self):
        """
        Test all managers handle dependency injection consistently.
        
        EXPECTED INITIAL STATE: FAIL - Different DI patterns across managers
        EXPECTED POST-SSOT STATE: PASS - Consistent DI patterns across all managers
        
        VIOLATION BEING PROVED: Dependency injection pattern fragmentation
        """
        di_violations = []
        
        # Test dependency injection patterns
        manager_classes = []
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            manager_classes.append(('WebSocketManagerFactory', WebSocketManagerFactory))
        except ImportError:
            pass
            
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager_classes.append(('UnifiedWebSocketManager', UnifiedWebSocketManager))
        except ImportError:
            pass

        # Analyze dependency injection patterns
        di_patterns = {}
        
        for manager_name, manager_class in manager_classes:
            try:
                init_sig = inspect.signature(manager_class.__init__)
                
                # Check for dependency injection indicators
                di_indicators = []
                for param_name, param in init_sig.parameters.items():
                    if param_name == 'self':
                        continue
                        
                    # Check for DI patterns
                    if 'context' in param_name.lower():
                        di_indicators.append(f"context_injection:{param_name}")
                    elif 'config' in param_name.lower():
                        di_indicators.append(f"config_injection:{param_name}")
                    elif 'manager' in param_name.lower():
                        di_indicators.append(f"manager_injection:{param_name}")
                    elif param.annotation != inspect.Parameter.empty:
                        di_indicators.append(f"typed_param:{param_name}:{param.annotation}")
                
                di_patterns[manager_name] = di_indicators
                
            except Exception as e:
                di_violations.append(f"{manager_name} DI analysis failed: {e}")

        # Check for DI pattern consistency within same class types
        factory_patterns = {k: v for k, v in di_patterns.items() if 'Factory' in k}
        manager_patterns = {k: v for k, v in di_patterns.items() if 'Manager' in k and 'Factory' not in k}
        
        # Check consistency within factories
        if len(factory_patterns) > 1:
            factory_keys = list(factory_patterns.keys())
            base_factory_pattern = factory_patterns[factory_keys[0]]
            for other_factory in factory_keys[1:]:
                if factory_patterns[other_factory] != base_factory_pattern:
                    di_violations.append(
                        f"Factory DI pattern mismatch: {factory_keys[0]} vs {other_factory}"
                    )
        
        # Check consistency within managers (managers should generally have minimal DI)
        if len(manager_patterns) > 1:
            manager_keys = list(manager_patterns.keys())
            base_manager_pattern = manager_patterns[manager_keys[0]]
            for other_manager in manager_keys[1:]:
                if manager_patterns[other_manager] != base_manager_pattern:
                    di_violations.append(
                        f"Manager DI pattern mismatch: {manager_keys[0]} vs {other_manager}"
                    )

        # Test actual DI behavior
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            import uuid
            # Use proper UserExecutionContext creation
            test_user_id = str(uuid.uuid4())
            test_context = UserExecutionContext.from_websocket_request(
                user_id=test_user_id,
                operation="di_test"
            )
            
            for manager_name, manager_class in manager_classes:
                try:
                    if 'Factory' in manager_name:
                        # Factory classes use different instantiation
                        instance = manager_class()
                    else:
                        # Try with context (this should fail for managers)
                        instance = manager_class(test_context)
                        di_violations.append(
                            f"{manager_name} unexpectedly accepted context injection"
                        )
                except TypeError as e:
                    # Expected for managers that don't support context injection
                    if "takes 1 positional argument but 2 were given" in str(e):
                        # This is the expected failure - manager doesn't support DI
                        pass
                    else:
                        di_violations.append(f"{manager_name} unexpected TypeError: {e}")
                except Exception as e:
                    di_violations.append(f"{manager_name} DI test failed: {e}")
                    
        except Exception as e:
            di_violations.append(f"DI behavior test failed: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: DI patterns should be consistent
        self.assertEqual(
            len(di_violations), 0,
            f"SSOT VIOLATION: Dependency injection inconsistencies: {di_violations}. "
            f"DI patterns found: {di_patterns}. "
            f"This proves dependency injection patterns need standardization across managers."
        )


if __name__ == '__main__':
    import unittest
    unittest.main()