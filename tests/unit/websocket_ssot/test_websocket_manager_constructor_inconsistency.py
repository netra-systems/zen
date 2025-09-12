"""Test WebSocket Manager Constructor Inconsistency - Phase 1 Reproduction Test

This test validates Issue #564: Constructor signature differences between WebSocket manager implementations.

CRITICAL BUSINESS CONTEXT:
- Issue: Different constructor signatures across WebSocket manager implementations
- Business Impact: $500K+ ARR chat functionality fails due to inconsistent instantiation
- SSOT Violation: Different constructor parameters break factory pattern consistency
- Golden Path Impact: User context isolation failures due to constructor inconsistencies

TEST PURPOSE:
This test MUST FAIL initially to prove constructor inconsistencies exist, then PASS after SSOT consolidation.
It demonstrates that different implementations require different initialization parameters.

Expected Behavior:
- BEFORE SSOT Fix: FAIL (different constructor signatures cause instantiation failures)
- AFTER SSOT Fix: PASS (consistent constructor signature across all implementations)

Business Value Justification:
- Segment: ALL (Free -> Enterprise) 
- Business Goal: Ensure consistent WebSocket manager instantiation for Golden Path
- Value Impact: Protects factory pattern reliability (core of user isolation system)
- Revenue Impact: Prevents instantiation failures affecting $500K+ ARR chat functionality
"""

import pytest
import inspect
import asyncio
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketManagerConstructorInconsistency(SSotBaseTestCase):
    """Phase 1 Reproduction Test: Prove constructor signatures differ between implementations."""
    
    def setup_method(self, method):
        """Set up test environment for constructor analysis."""
        super().setup_method(method)
        logger.info(f"Setting up constructor inconsistency test: {method.__name__}")
        
    def test_constructor_signature_consistency(self):
        """
        CRITICAL REPRODUCTION TEST: Prove constructor signatures are inconsistent across implementations.
        
        SSOT VIOLATION: All WebSocket manager implementations should have identical constructor
        signatures to ensure factory pattern consistency and proper user isolation.
        
        Expected Results:
        - BEFORE SSOT Fix: This test FAILS (different signatures proving inconsistency)
        - AFTER SSOT Fix: This test PASSES (identical signatures across implementations)
        """
        logger.info("Analyzing constructor signatures across WebSocket manager implementations")
        
        # Import different WebSocket manager implementations
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as ManagerAlias
        from netra_backend.app.websocket_core.manager import WebSocketManager as CompatibilityManager
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as UnifiedManager
        
        # Get constructor signatures
        alias_signature = inspect.signature(ManagerAlias.__init__)
        compatibility_signature = inspect.signature(CompatibilityManager.__init__)
        unified_signature = inspect.signature(UnifiedManager.__init__)
        
        logger.info(f"Alias constructor signature: {alias_signature}")
        logger.info(f"Compatibility constructor signature: {compatibility_signature}")
        logger.info(f"Unified constructor signature: {unified_signature}")
        
        # CRITICAL SSOT TEST: All signatures should be identical
        try:
            # Test alias vs unified (should be identical if aliasing works)
            assert alias_signature == unified_signature, (
                f"CONSTRUCTOR INCONSISTENCY DETECTED: "
                f"Alias signature {alias_signature} != Unified signature {unified_signature}. "
                f"SSOT Violation: WebSocketManager alias should have identical constructor to UnifiedWebSocketManager. "
                f"Business Impact: Factory pattern cannot reliably instantiate managers, "
                f"causing user isolation failures in $500K+ ARR chat functionality."
            )
            logger.info("✅ Alias and unified constructors have identical signatures")
        except AssertionError as e:
            logger.error(f"❌ ALIAS CONSTRUCTOR INCONSISTENCY: {e}")
            raise
            
        try:
            # Test compatibility vs unified (should be identical for SSOT compliance)
            assert compatibility_signature == unified_signature, (
                f"CONSTRUCTOR INCONSISTENCY DETECTED: "
                f"Compatibility signature {compatibility_signature} != Unified signature {unified_signature}. "
                f"SSOT Violation: Compatibility layer should have identical constructor to UnifiedWebSocketManager. "
                f"Business Impact: Legacy import paths cannot instantiate managers consistently, "
                f"breaking user isolation and affecting enterprise customers."
            )
            logger.info("✅ Compatibility and unified constructors have identical signatures")
        except AssertionError as e:
            logger.error(f"❌ COMPATIBILITY CONSTRUCTOR INCONSISTENCY: {e}")
            raise
    
    def test_constructor_parameter_validation(self):
        """
        REPRODUCTION TEST: Validate that constructor parameters work consistently across implementations.
        
        SSOT VIOLATION: Same parameters should work for all implementations. Inconsistencies
        indicate fragmentation where different implementations have different requirements.
        """
        logger.info("Testing constructor parameter consistency across implementations")
        
        # Create test user context for instantiation testing
        test_context = type('MockUserContext', (), {
            'user_id': 'test_user_constructor',
            'thread_id': 'test_thread_constructor',
            'request_id': 'test_request_constructor', 
            'is_test': True
        })()
        
        # Import required enums and classes
        from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as ManagerAlias
        from netra_backend.app.websocket_core.manager import WebSocketManager as CompatibilityManager
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as UnifiedManager
        
        # Test that same parameters work for all constructors
        test_parameters = {
            'mode': WebSocketManagerMode.UNIFIED,
            'user_context': test_context
        }
        
        instances = []
        
        try:
            # Test unified manager (baseline)
            unified_instance = UnifiedManager(**test_parameters)
            instances.append(('UnifiedManager', unified_instance))
            logger.info("✅ UnifiedWebSocketManager instantiated successfully")
        except Exception as e:
            logger.error(f"❌ UnifiedWebSocketManager instantiation failed: {e}")
            pytest.fail(f"Baseline unified manager instantiation failed: {e}")
            
        try:
            # Test alias manager (should work identically) 
            alias_instance = ManagerAlias(**test_parameters)
            instances.append(('ManagerAlias', alias_instance))
            logger.info("✅ WebSocketManager (alias) instantiated successfully")
        except Exception as e:
            logger.error(f"❌ ALIAS CONSTRUCTOR FAILURE: WebSocketManager alias instantiation failed: {e}")
            logger.error(f"This indicates the alias is not properly configured for SSOT compliance")
            pytest.fail(f"Alias constructor inconsistency: {e}")
            
        try:
            # Test compatibility manager (should work identically)
            compatibility_instance = CompatibilityManager(**test_parameters)
            instances.append(('CompatibilityManager', compatibility_instance))
            logger.info("✅ WebSocketManager (compatibility) instantiated successfully")  
        except Exception as e:
            logger.error(f"❌ COMPATIBILITY CONSTRUCTOR FAILURE: Compatibility manager instantiation failed: {e}")
            logger.error(f"This indicates the compatibility layer has different constructor requirements")
            pytest.fail(f"Compatibility constructor inconsistency: {e}")
        
        # Verify all instances have the same type (proving they're all the same class)
        if len(instances) >= 2:
            base_type = type(instances[0][1])
            for name, instance in instances[1:]:
                try:
                    assert type(instance) == base_type, (
                        f"INSTANCE TYPE INCONSISTENCY: {name} type {type(instance)} != "
                        f"baseline type {base_type}. "
                        f"SSOT Violation: All constructors should create instances of the same type. "
                        f"Business Impact: Different instance types break polymorphism and user isolation."
                    )
                    logger.info(f"✅ {name} creates correct instance type")
                except AssertionError as e:
                    logger.error(f"❌ INSTANCE TYPE MISMATCH: {e}")
                    raise
    
    def test_factory_function_parameter_consistency(self):
        """
        REPRODUCTION TEST: Validate factory function parameters work consistently.
        
        SSOT VIOLATION: Factory functions should have consistent parameter handling
        to ensure reliable manager instantiation across the system.
        """
        logger.info("Testing factory function parameter consistency")
        
        # Create test context
        test_context = type('MockUserContext', (), {
            'user_id': 'test_user_factory',
            'thread_id': 'test_thread_factory',
            'request_id': 'test_request_factory',
            'is_test': True
        })()
        
        from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        async def test_factory_consistency():
            """Test factory function parameter consistency."""
            try:
                # Test factory with user context
                manager_with_context = await get_websocket_manager(
                    user_context=test_context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                assert manager_with_context is not None, "Factory should return manager with user context"
                logger.info("✅ Factory function works with user context")
                
                # Test factory without user context (should handle gracefully)
                manager_without_context = await get_websocket_manager()
                assert manager_without_context is not None, "Factory should handle missing user context gracefully"
                logger.info("✅ Factory function handles missing user context")
                
                # Test that both instances have consistent types
                assert type(manager_with_context) == type(manager_without_context), (
                    f"FACTORY INCONSISTENCY: Manager with context type {type(manager_with_context)} != "
                    f"manager without context type {type(manager_without_context)}. "
                    f"SSOT Violation: Factory should create consistent instance types. "
                    f"Business Impact: Unpredictable manager behavior affects user isolation."
                )
                logger.info("✅ Factory creates consistent instance types")
                
            except Exception as e:
                logger.error(f"❌ FACTORY FUNCTION INCONSISTENCY: {e}")
                pytest.fail(f"Factory function parameter inconsistency: {e}")
        
        # Run async test
        asyncio.run(test_factory_consistency())
        
    def test_constructor_error_handling_consistency(self):
        """
        REPRODUCTION TEST: Validate error handling consistency across constructors.
        
        SSOT VIOLATION: All constructors should handle errors consistently to ensure
        predictable behavior across different import paths and implementations.
        """
        logger.info("Testing constructor error handling consistency")
        
        from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as ManagerAlias  
        from netra_backend.app.websocket_core.manager import WebSocketManager as CompatibilityManager
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as UnifiedManager
        
        # Test with invalid parameters to check error handling consistency
        invalid_parameters = {
            'mode': 'invalid_mode',  # Invalid mode type
            'user_context': None     # Invalid user context
        }
        
        error_behaviors = []
        
        # Test each constructor's error handling
        constructors = [
            ('UnifiedManager', UnifiedManager),
            ('ManagerAlias', ManagerAlias),
            ('CompatibilityManager', CompatibilityManager)
        ]
        
        for name, constructor in constructors:
            try:
                # Attempt invalid instantiation
                constructor(**invalid_parameters)
                error_behaviors.append((name, 'no_error', None))
                logger.warning(f"⚠️ {name} accepted invalid parameters - potential validation issue")
            except Exception as e:
                error_behaviors.append((name, type(e).__name__, str(e)))
                logger.info(f"✅ {name} properly rejected invalid parameters: {type(e).__name__}")
        
        # Verify all constructors handle errors consistently
        if len(error_behaviors) >= 2:
            baseline_error_type = error_behaviors[0][1] 
            baseline_name = error_behaviors[0][0]
            
            for name, error_type, error_msg in error_behaviors[1:]:
                try:
                    assert error_type == baseline_error_type, (
                        f"ERROR HANDLING INCONSISTENCY: {name} error handling ({error_type}) != "
                        f"{baseline_name} error handling ({baseline_error_type}). "
                        f"SSOT Violation: All constructors should handle errors consistently. "
                        f"Business Impact: Unpredictable error behavior complicates debugging and "
                        f"error recovery in production, affecting system reliability."
                    )
                    logger.info(f"✅ {name} has consistent error handling with {baseline_name}")
                except AssertionError as e:
                    logger.error(f"❌ ERROR HANDLING INCONSISTENCY: {e}")
                    raise

    def teardown_method(self, method):
        """Clean up test environment."""
        logger.info(f"Tearing down constructor inconsistency test: {method.__name__}")
        super().teardown_method(method)