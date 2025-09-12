"""Test Single WebSocket Manager SSOT Validation - Phase 2 SSOT Validation Test

This test validates Issue #564: Successful SSOT consolidation of WebSocket managers.

CRITICAL BUSINESS CONTEXT:
- Issue: Validation that only one WebSocket manager implementation exists post-SSOT consolidation
- Business Impact: $500K+ ARR protected through consolidated, reliable WebSocket management  
- SSOT Achievement: Single source of truth eliminates fragmentation and user isolation failures
- Golden Path Impact: Reliable WebSocket manager ensures consistent chat functionality delivery

TEST PURPOSE:
This test MUST FAIL initially (multiple implementations found), then PASS after SSOT consolidation.
It validates that the SSOT consolidation successfully eliminated all duplicate implementations.

Expected Behavior:
- BEFORE SSOT Fix: FAIL (multiple WebSocket manager implementations detected)
- AFTER SSOT Fix: PASS (single consolidated SSOT WebSocket manager implementation)

Business Value Justification:
- Segment: Platform/Internal - SSOT compliance validation
- Business Goal: Ensure SSOT consolidation maintains system architecture integrity
- Value Impact: Validates that consolidation preserves Golden Path functionality
- Revenue Impact: Confirms $500K+ ARR protection through reliable consolidated manager
"""

import pytest
import sys
import inspect
from typing import Dict, List, Set
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestSingleWebSocketManagerSsotValidation(SSotBaseTestCase):
    """Phase 2 SSOT Validation Test: Validate only one WebSocket manager implementation exists."""
    
    def setup_method(self, method):
        """Set up test environment for SSOT validation."""
        super().setup_method(method)
        logger.info(f"Setting up SSOT validation test: {method.__name__}")
        
        # Clear module cache to ensure fresh imports for validation
        websocket_modules = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core.manager'
        ]
        
        for module_name in websocket_modules:
            if module_name in sys.modules:
                logger.debug(f"Clearing cached module for clean validation: {module_name}")
                del sys.modules[module_name]
    
    def test_single_websocket_manager_implementation_exists(self):
        """
        CRITICAL SSOT VALIDATION TEST: Validate only one WebSocket manager implementation exists.
        
        SSOT REQUIREMENT: After consolidation, there should be exactly one WebSocket manager
        class implementation, with all other paths being aliases or re-exports.
        
        Expected Results:
        - BEFORE SSOT Fix: This test FAILS (multiple implementations detected)  
        - AFTER SSOT Fix: This test PASSES (single implementation with proper aliasing)
        """
        logger.info("Validating single WebSocket manager implementation (SSOT compliance)")
        
        # Import all WebSocket manager references
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as ManagerAlias
        from netra_backend.app.websocket_core.manager import WebSocketManager as CompatibilityManager
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as UnifiedManager
        
        # Get the actual class objects and their implementation details
        manager_classes = {
            'ManagerAlias': ManagerAlias,
            'CompatibilityManager': CompatibilityManager,  
            'UnifiedManager': UnifiedManager
        }
        
        logger.info("Analyzing WebSocket manager class references:")
        for name, cls in manager_classes.items():
            logger.info(f"  {name}: {cls} (id: {id(cls)}, module: {cls.__module__})")
        
        # CRITICAL SSOT TEST 1: All references should point to the same class object
        unique_class_ids = set(id(cls) for cls in manager_classes.values())
        
        if len(unique_class_ids) > 1:
            logger.error("❌ SSOT VIOLATION: Multiple distinct WebSocket manager implementations detected!")
            
            # Detailed analysis of the violation
            class_id_mapping = {id(cls): (name, cls) for name, cls in manager_classes.items()}
            for class_id, (name, cls) in class_id_mapping.items():
                logger.error(f"  Implementation {class_id}: {name} -> {cls} from {cls.__module__}")
            
            pytest.fail(
                f"SSOT CONSOLIDATION INCOMPLETE: Found {len(unique_class_ids)} distinct WebSocket manager implementations. "
                f"Expected: 1 implementation with proper aliasing. "
                f"SSOT Requirement: All import paths must resolve to the same class object. "
                f"Business Impact: Multiple implementations maintain fragmentation issues, "
                f"continuing user isolation failures and affecting $500K+ ARR chat reliability."
            )
        
        logger.info("✅ SSOT COMPLIANCE: All WebSocket manager references point to single implementation")
        
        # CRITICAL SSOT TEST 2: Verify the single implementation is the intended SSOT class
        ssot_implementation = list(manager_classes.values())[0]  # All should be the same
        
        # The SSOT should be UnifiedWebSocketManager (the actual implementation)
        if ssot_implementation.__name__ != 'UnifiedWebSocketManager':
            logger.error(f"❌ SSOT IMPLEMENTATION ERROR: Expected 'UnifiedWebSocketManager', got '{ssot_implementation.__name__}'")
            pytest.fail(
                f"INCORRECT SSOT IMPLEMENTATION: All references resolve to '{ssot_implementation.__name__}' "
                f"instead of 'UnifiedWebSocketManager'. "
                f"SSOT Requirement: The unified implementation should be the canonical class. "
                f"Business Impact: Wrong implementation as SSOT may not have full feature set."
            )
        
        logger.info(f"✅ CORRECT SSOT IMPLEMENTATION: All references resolve to {ssot_implementation.__name__}")
        
        # CRITICAL SSOT TEST 3: Verify aliases are properly configured
        self._validate_alias_configuration(manager_classes)
        
        logger.info("✅ SSOT VALIDATION PASSED: Single WebSocket manager implementation confirmed")
    
    def _validate_alias_configuration(self, manager_classes: Dict[str, type]):
        """Validate that aliases are properly configured and documented."""
        logger.info("Validating alias configuration for SSOT compliance")
        
        # All classes should be identical (same object reference)
        reference_class = manager_classes['UnifiedManager']  # The actual implementation
        
        for alias_name, alias_class in manager_classes.items():
            if alias_name != 'UnifiedManager':
                try:
                    assert alias_class is reference_class, (
                        f"ALIAS CONFIGURATION ERROR: {alias_name} ({id(alias_class)}) is not "
                        f"properly aliased to UnifiedManager ({id(reference_class)}). "
                        f"SSOT Requirement: All aliases must reference the same object. "
                        f"Business Impact: Improper aliasing maintains fragmentation issues."
                    )
                    logger.info(f"✅ {alias_name} properly aliases UnifiedWebSocketManager")
                except AssertionError as e:
                    logger.error(f"❌ ALIAS CONFIGURATION FAILURE: {e}")
                    raise
    
    def test_websocket_manager_module_consolidation(self):
        """
        SSOT VALIDATION TEST: Validate WebSocket manager modules are properly consolidated.
        
        SSOT REQUIREMENT: Module structure should support the consolidated implementation
        while maintaining backward compatibility through proper imports/exports.
        """
        logger.info("Validating WebSocket manager module consolidation")
        
        # Import modules (not classes) to analyze module structure
        import netra_backend.app.websocket_core.websocket_manager as websocket_manager_module
        import netra_backend.app.websocket_core.manager as manager_module  
        import netra_backend.app.websocket_core.unified_manager as unified_manager_module
        
        # Analyze module exports
        modules_info = {
            'websocket_manager': {
                'module': websocket_manager_module,
                'exports': getattr(websocket_manager_module, '__all__', [])
            },
            'manager': {
                'module': manager_module,
                'exports': getattr(manager_module, '__all__', [])
            },
            'unified_manager': {
                'module': unified_manager_module,
                'exports': getattr(unified_manager_module, '__all__', [])
            }
        }
        
        logger.info("Module export analysis:")
        for module_name, info in modules_info.items():
            logger.info(f"  {module_name}: exports {info['exports']}")
        
        # CRITICAL SSOT TEST: Verify unified_manager contains the actual implementation
        if not hasattr(unified_manager_module, 'UnifiedWebSocketManager'):
            pytest.fail(
                "SSOT MODULE STRUCTURE ERROR: unified_manager module missing UnifiedWebSocketManager class. "
                "SSOT Requirement: The actual implementation must be in the unified module. "
                "Business Impact: Missing core implementation breaks SSOT architecture."
            )
        
        # CRITICAL SSOT TEST: Verify compatibility modules properly re-export
        compatibility_modules = ['websocket_manager', 'manager']
        for module_name in compatibility_modules:
            module_info = modules_info[module_name]
            
            if 'WebSocketManager' not in module_info['exports']:
                logger.warning(f"⚠️ {module_name} does not export WebSocketManager in __all__")
            
            if not hasattr(module_info['module'], 'WebSocketManager'):
                pytest.fail(
                    f"COMPATIBILITY MODULE ERROR: {module_name} missing WebSocketManager export. "
                    f"SSOT Requirement: Compatibility modules must re-export the SSOT implementation. "
                    f"Business Impact: Backward compatibility broken, existing imports will fail."
                )
        
        logger.info("✅ Module consolidation structure validated successfully")
    
    def test_websocket_manager_interface_completeness(self):
        """
        SSOT VALIDATION TEST: Validate the consolidated WebSocket manager has complete interface.
        
        SSOT REQUIREMENT: The single implementation must provide all functionality
        that was previously spread across multiple implementations.
        """
        logger.info("Validating consolidated WebSocket manager interface completeness")
        
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        
        # Define required methods for complete WebSocket manager functionality
        required_methods = [
            'add_connection',
            'remove_connection', 
            'get_connection',
            'broadcast_message',
            'send_message',
            '__init__'
        ]
        
        # Additional methods that may be present for enhanced functionality
        enhanced_methods = [
            'send_event',
            'broadcast_event', 
            'emit_event',
            'get_connections_for_user',
            'get_user_connections',
            'close_user_connections'
        ]
        
        all_expected_methods = required_methods + enhanced_methods
        
        # Check method presence
        missing_methods = []
        present_methods = []
        
        for method_name in all_expected_methods:
            if hasattr(WebSocketManager, method_name):
                method = getattr(WebSocketManager, method_name)
                if callable(method):
                    present_methods.append(method_name)
                    logger.debug(f"✅ Method present: {method_name}")
                else:
                    logger.warning(f"⚠️ Attribute {method_name} exists but is not callable")
            else:
                missing_methods.append(method_name)
                logger.debug(f"❌ Method missing: {method_name}")
        
        # Validate required methods are present
        missing_required = [m for m in missing_methods if m in required_methods]
        if missing_required:
            pytest.fail(
                f"SSOT INTERFACE INCOMPLETE: Missing required methods {missing_required}. "
                f"SSOT Requirement: Consolidated implementation must provide complete interface. "
                f"Business Impact: Missing methods break existing functionality, "
                f"affecting Golden Path WebSocket operations and $500K+ ARR chat features."
            )
        
        # Report on enhanced methods (optional but good for feature completeness)
        missing_enhanced = [m for m in missing_methods if m in enhanced_methods]
        if missing_enhanced:
            logger.warning(f"⚠️ Missing enhanced methods: {missing_enhanced}")
            logger.info("These methods may be implemented differently or not required for current SSOT")
        
        logger.info(f"✅ Interface validation complete: {len(present_methods)}/{len(all_expected_methods)} methods available")
        logger.info(f"Required methods: {len([m for m in present_methods if m in required_methods])}/{len(required_methods)} ✅")
    
    def test_websocket_manager_instantiation_consistency(self):
        """
        SSOT VALIDATION TEST: Validate consistent instantiation across all import paths.
        
        SSOT REQUIREMENT: All import paths should support identical instantiation patterns
        and produce functionally equivalent instances.
        """
        logger.info("Validating WebSocket manager instantiation consistency")
        
        # Import from different paths
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as Path1
        from netra_backend.app.websocket_core.manager import WebSocketManager as Path2
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as Path3
        
        # Create test user context
        test_context = type('TestContext', (), {
            'user_id': 'ssot_validation_user',
            'thread_id': 'ssot_validation_thread',
            'request_id': 'ssot_validation_request',
            'is_test': True
        })()
        
        from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
        
        # Test instantiation from all paths
        instances = []
        instantiation_results = {}
        
        for path_name, manager_class in [('Path1', Path1), ('Path2', Path2), ('Path3', Path3)]:
            try:
                instance = manager_class(
                    mode=WebSocketManagerMode.UNIFIED,
                    user_context=test_context
                )
                instances.append((path_name, instance))
                instantiation_results[path_name] = 'SUCCESS'
                logger.info(f"✅ {path_name} instantiation successful: {type(instance)}")
            except Exception as e:
                instantiation_results[path_name] = f'FAILED: {e}'
                logger.error(f"❌ {path_name} instantiation failed: {e}")
        
        # CRITICAL SSOT TEST: All paths should instantiate successfully
        failed_instantiations = [path for path, result in instantiation_results.items() if 'FAILED' in result]
        if failed_instantiations:
            pytest.fail(
                f"SSOT INSTANTIATION FAILURE: Paths {failed_instantiations} failed to instantiate. "
                f"Results: {instantiation_results}. "
                f"SSOT Requirement: All import paths must support identical instantiation. "
                f"Business Impact: Inconsistent instantiation breaks backward compatibility "
                f"and affects existing Golden Path integrations."
            )
        
        # CRITICAL SSOT TEST: All instances should have the same type
        if len(instances) >= 2:
            reference_type = type(instances[0][1])
            for path_name, instance in instances[1:]:
                if type(instance) != reference_type:
                    pytest.fail(
                        f"SSOT TYPE INCONSISTENCY: {path_name} instance type {type(instance)} != "
                        f"reference type {reference_type}. "
                        f"SSOT Requirement: All paths should create instances of the same type. "
                        f"Business Impact: Type inconsistencies break polymorphism and integration."
                    )
        
        logger.info("✅ WebSocket manager instantiation consistency validated")

    def teardown_method(self, method):
        """Clean up test environment."""
        logger.info(f"Tearing down SSOT validation test: {method.__name__}")
        super().teardown_method(method)