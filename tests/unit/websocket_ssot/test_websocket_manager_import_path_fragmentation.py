"""Test WebSocket Manager Import Path Fragmentation - Phase 1 Reproduction Test

This test validates Issue #564: WebSocket Manager SSOT fragmentation blocking Golden Path.

CRITICAL BUSINESS CONTEXT:
- Issue: Multiple import paths leading to different WebSocket manager instances
- Business Impact: $500K+ ARR from chat functionality failures due to user isolation violations
- SSOT Violation: Different objects returned from different import paths breaks user isolation
- Golden Path Impact: User data contamination in multi-tenant chat environment

TEST PURPOSE:
This test MUST FAIL initially to prove SSOT fragmentation exists, then PASS after SSOT consolidation.
It demonstrates that different import paths create different manager instances, violating SSOT principles.

Expected Behavior:
- BEFORE SSOT Fix: FAIL (different objects from different import paths)  
- AFTER SSOT Fix: PASS (same object reference from all import paths)

Business Value Justification:
- Segment: ALL (Free -> Enterprise)
- Business Goal: Ensure user isolation integrity for Golden Path  
- Value Impact: Protects chat functionality reliability (90% of platform value)
- Revenue Impact: Prevents user data contamination affecting $500K+ ARR
"""

import pytest
import sys
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketManagerImportPathFragmentation(SSotBaseTestCase):
    """Phase 1 Reproduction Test: Prove import path fragmentation creates different instances."""
    
    def setup_method(self, method):
        """Set up test environment with clean import state."""
        super().setup_method(method)
        logger.info(f"Setting up import fragmentation test: {method.__name__}")
        
        # Clear any cached WebSocket manager modules to ensure clean test
        websocket_modules = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager', 
            'netra_backend.app.websocket_core.manager'
        ]
        
        for module_name in websocket_modules:
            if module_name in sys.modules:
                logger.debug(f"Clearing cached module: {module_name}")
                del sys.modules[module_name]
    
    def test_different_import_paths_create_different_instances(self):
        """
        CRITICAL REPRODUCTION TEST: Prove multiple import paths create different manager instances.
        
        SSOT VIOLATION: Different import paths should return the SAME object reference,
        but fragmentation causes different instances to be created.
        
        Expected Results:
        - BEFORE SSOT Fix: This test FAILS (different instances proving fragmentation)
        - AFTER SSOT Fix: This test PASSES (same instance from all paths)
        """
        logger.info("Testing import path fragmentation - this MUST fail initially to prove violation")
        
        # Import WebSocketManager from primary path (websocket_manager.py)
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as ManagerPath1
        
        # Import WebSocketManager from compatibility path (manager.py)  
        from netra_backend.app.websocket_core.manager import WebSocketManager as ManagerPath2
        
        # Import UnifiedWebSocketManager directly
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as ManagerPath3
        
        logger.info(f"ManagerPath1 class: {ManagerPath1}")
        logger.info(f"ManagerPath2 class: {ManagerPath2}")
        logger.info(f"ManagerPath3 class: {ManagerPath3}")
        
        # CRITICAL SSOT REQUIREMENT: All import paths MUST return the exact same class reference
        # If this fails, it proves SSOT fragmentation exists
        
        # Test 1: Primary path and compatibility path should be identical
        try:
            assert ManagerPath1 is ManagerPath2, (
                f"SSOT VIOLATION DETECTED: Primary path {ManagerPath1} != Compatibility path {ManagerPath2}. "
                f"This proves import path fragmentation exists, violating SSOT principles. "
                f"Business Impact: User isolation failures affecting $500K+ ARR chat functionality."
            )
            logger.info("✅ Primary and compatibility paths return same class - SSOT compliant")
        except AssertionError as e:
            logger.error(f"❌ SSOT FRAGMENTATION CONFIRMED: {e}")
            raise
        
        # Test 2: All paths should reference the same underlying implementation
        try:
            assert ManagerPath1 is ManagerPath3, (
                f"SSOT VIOLATION DETECTED: Primary path {ManagerPath1} != Unified path {ManagerPath3}. "
                f"This indicates the alias system is not properly consolidating to SSOT. "
                f"Business Impact: Different manager instances cause user data contamination."
            )
            logger.info("✅ Primary and unified paths return same class - SSOT compliant")
        except AssertionError as e:
            logger.error(f"❌ ALIAS FRAGMENTATION CONFIRMED: {e}")
            raise
            
        # Test 3: Compatibility path should reference unified implementation
        try:
            assert ManagerPath2 is ManagerPath3, (
                f"SSOT VIOLATION DETECTED: Compatibility path {ManagerPath2} != Unified path {ManagerPath3}. "
                f"This proves the compatibility layer is not properly aliasing to SSOT implementation. "
                f"Business Impact: Legacy imports create separate instances, breaking user isolation."
            )
            logger.info("✅ Compatibility and unified paths return same class - SSOT compliant")
        except AssertionError as e:
            logger.error(f"❌ COMPATIBILITY FRAGMENTATION CONFIRMED: {e}")
            raise
    
    def test_instance_creation_consistency_across_paths(self):
        """
        CRITICAL REPRODUCTION TEST: Prove instances from different paths have different behavior.
        
        SSOT VIOLATION: Instance creation should be consistent regardless of import path,
        but fragmentation may cause different initialization behavior.
        
        Expected Results:
        - BEFORE SSOT Fix: Different behaviors or incompatible instances
        - AFTER SSOT Fix: Identical behavior from all import paths
        """
        logger.info("Testing instance creation consistency across import paths")
        
        try:
            # Create instances from different import paths
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager as factory1
            from netra_backend.app.websocket_core.manager import WebSocketManager as DirectClass
            
            # Test async factory creation
            import asyncio
            
            async def test_factory_consistency():
                # Create instance via factory function
                manager1 = await factory1()
                
                # Create instance via direct class instantiation
                # Note: This may require different parameters due to fragmentation
                from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
                
                # Create test user context for direct instantiation
                test_context = type('MockUserContext', (), {
                    'user_id': 'test_user_import_path',
                    'thread_id': 'test_thread_import_path',  
                    'request_id': 'test_request_import_path',
                    'is_test': True
                })()
                
                manager2 = DirectClass(mode=WebSocketManagerMode.UNIFIED, user_context=test_context)
                
                # SSOT REQUIREMENT: Both instances should have identical type and interface
                assert type(manager1) == type(manager2), (
                    f"SSOT VIOLATION: Factory instance type {type(manager1)} != "
                    f"Direct instance type {type(manager2)}. "
                    f"Business Impact: Inconsistent WebSocket behavior across import paths."
                )
                
                # Test that both instances have the same essential attributes/methods
                essential_methods = ['add_connection', 'remove_connection', 'broadcast_message']
                
                for method_name in essential_methods:
                    assert hasattr(manager1, method_name), (
                        f"Factory instance missing essential method: {method_name}"
                    )
                    assert hasattr(manager2, method_name), (
                        f"Direct instance missing essential method: {method_name}"  
                    )
                    assert callable(getattr(manager1, method_name)), (
                        f"Factory instance method {method_name} is not callable"
                    )
                    assert callable(getattr(manager2, method_name)), (
                        f"Direct instance method {method_name} is not callable"
                    )
                
                logger.info("✅ Instance consistency verified across import paths")
                
            # Run async test
            asyncio.run(test_factory_consistency())
            
        except Exception as e:
            logger.error(f"❌ INSTANCE CREATION FRAGMENTATION: {e}")
            pytest.fail(f"Instance creation inconsistency detected: {e}")
            
    def test_module_identity_verification(self):
        """
        REPRODUCTION TEST: Verify that different import paths reference same module objects.
        
        SSOT REQUIREMENT: All imports should resolve to the same underlying module identity.
        Fragmentation violates this by creating multiple module references.
        """
        logger.info("Testing module identity consistency across import paths")
        
        # Import modules (not classes) to test identity
        import netra_backend.app.websocket_core.websocket_manager as module1
        import netra_backend.app.websocket_core.manager as module2
        import netra_backend.app.websocket_core.unified_manager as module3
        
        # Get WebSocketManager classes from each module
        manager_class_1 = getattr(module1, 'WebSocketManager', None)
        manager_class_2 = getattr(module2, 'WebSocketManager', None) 
        manager_class_3 = getattr(module3, 'UnifiedWebSocketManager', None)
        
        # Verify all classes were found
        assert manager_class_1 is not None, "WebSocketManager not found in websocket_manager module"
        assert manager_class_2 is not None, "WebSocketManager not found in manager module"
        assert manager_class_3 is not None, "UnifiedWebSocketManager not found in unified_manager module"
        
        # CRITICAL SSOT TEST: All should reference the same class object
        try:
            assert manager_class_1 is manager_class_3, (
                f"SSOT VIOLATION: websocket_manager.WebSocketManager ({id(manager_class_1)}) != "
                f"unified_manager.UnifiedWebSocketManager ({id(manager_class_3)}). "
                f"Expected: websocket_manager.WebSocketManager should be alias to UnifiedWebSocketManager."
            )
            logger.info("✅ Primary module correctly aliases to unified implementation")
        except AssertionError as e:
            logger.error(f"❌ PRIMARY MODULE ALIASING FAILURE: {e}")
            raise
            
        try:
            assert manager_class_2 is manager_class_3, (
                f"SSOT VIOLATION: manager.WebSocketManager ({id(manager_class_2)}) != "
                f"unified_manager.UnifiedWebSocketManager ({id(manager_class_3)}). "
                f"Expected: manager.WebSocketManager should be alias to UnifiedWebSocketManager."
            )
            logger.info("✅ Compatibility module correctly aliases to unified implementation")
        except AssertionError as e:
            logger.error(f"❌ COMPATIBILITY MODULE ALIASING FAILURE: {e}")
            raise

    def teardown_method(self, method):
        """Clean up test environment."""
        logger.info(f"Tearing down import fragmentation test: {method.__name__}")
        super().teardown_method(method)