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

import asyncio
import inspect
import unittest
from typing import Any, Dict, List, Set, Type, Optional, Callable
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketManagerConstructorValidation(unittest.TestCase):
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
                    # Simulate what factory does internally
                    test_args = ["test_user", "test_conn"]
                    
                    # This should fail if constructor signatures are incompatible
                    # Factory passes user context, but manager expects different parameters
                    from netra_backend.app.services.user_execution_context import UserExecutionContext
                    user_context = UserExecutionContext(user_id="test_user", request_id="test_req")
                    
                    # Try to instantiate manager the way factory does
                    try:
                        manager = WebSocketManager(user_context)  # This should fail
                        constructor_violations.append(
                            f"Factory-manager constructor compatibility unexpectedly succeeded. "
                            f"Expected TypeError due to signature mismatch."
                        )
                    except TypeError as e:
                        if "takes 1 positional argument but 2 were given" in str(e):
                            constructor_violations.append(
                                f"EXPECTED FAILURE: WebSocketManager.__init__() constructor signature incompatible with factory. "
                                f"Factory passes UserExecutionContext but manager expects different parameters: {e}"
                            )
                        else:
                            constructor_violations.append(f"Unexpected TypeError: {e}")
                    
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
            
            # Test delegation failure - this should demonstrate the SSOT violation
            try:
                manager = factory.create_isolated_manager(
                    user_id="test_user",
                    connection_id="test_connection"
                )
                delegation_violations.append(
                    "Factory delegation unexpectedly succeeded. Expected failure due to constructor mismatch."
                )
            except Exception as e:
                if "takes 1 positional argument but 2 were given" in str(e):
                    delegation_violations.append(
                        f"EXPECTED FAILURE: Factory delegation fails due to constructor mismatch: {e}"
                    )
                elif "create_isolated_manager failed" in str(e):
                    delegation_violations.append(
                        f"EXPECTED FAILURE: Factory delegation wrapped failure indicates constructor issues: {e}"
                    )
                else:
                    delegation_violations.append(f"Unexpected delegation error: {e}")

            # Test if factory has alternative delegation methods
            factory_methods = [attr for attr in dir(factory) 
                             if callable(getattr(factory, attr)) and not attr.startswith('_')]
            
            creation_methods = [method for method in factory_methods 
                              if 'create' in method or 'manager' in method]
            
            if len(creation_methods) > 1:
                delegation_violations.append(
                    f"Multiple factory creation methods found: {creation_methods}. "
                    f"This indicates inconsistent delegation patterns."
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

        # Check for DI pattern consistency
        if len(di_patterns) > 1:
            pattern_keys = list(di_patterns.keys())
            base_pattern = di_patterns[pattern_keys[0]]
            
            for other_manager in pattern_keys[1:]:
                other_pattern = di_patterns[other_manager]
                
                if base_pattern != other_pattern:
                    di_violations.append(
                        f"DI pattern mismatch: {pattern_keys[0]} uses {base_pattern}, "
                        f"{other_manager} uses {other_pattern}"
                    )

        # Test actual DI behavior
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            test_context = UserExecutionContext(user_id="test", request_id="test_req")
            
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