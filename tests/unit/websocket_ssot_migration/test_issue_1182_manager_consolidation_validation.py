"""
Test WebSocket Manager SSOT consolidation for Issue #1182.

CRITICAL BUSINESS IMPACT: $500K+ ARR Golden Path depends on WebSocket functionality.
This test validates elimination of competing implementations and import path consistency.

ISSUE #1182: WebSocket Manager SSOT Migration
- Problem: 3 competing WebSocket manager implementations causing SSOT violations
- Impact: Race conditions, user isolation failures, interface inconsistencies
- Solution: Consolidate to single SSOT implementation with proper factory patterns

RELATED ISSUES:
- Issue #1209: DemoWebSocketBridge interface failure (regression from SSOT violations)
- Issue #1116: User isolation vulnerabilities in multi-user scenarios

Test Strategy:
1. Detect competing WebSocket manager implementations (SHOULD FAIL INITIALLY)
2. Validate import path consolidation (SHOULD FAIL INITIALLY) 
3. Ensure legacy compatibility maintained (SHOULD PASS)
4. Verify interface consistency across implementations (SHOULD FAIL INITIALLY)

Business Value Justification:
- Segment: Platform Infrastructure
- Business Goal: System Stability & Golden Path Protection
- Value Impact: Eliminates race conditions and user isolation failures
- Revenue Impact: Protects $500K+ ARR chat functionality reliability
"""

import unittest
import importlib
import inspect
from typing import Dict, List, Set, Any, Type
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestWebSocketManagerConsolidationValidation(SSotBaseTestCase):
    """
    CRITICAL: Tests for Issue #1182 WebSocket Manager SSOT consolidation.
    
    These tests SHOULD FAIL INITIALLY to demonstrate the current SSOT violations.
    Success indicates proper WebSocket manager consolidation is complete.
    """

    def setUp(self):
        """Set up test environment for WebSocket manager consolidation validation."""
        super().setUp()
        self.websocket_manager_import_paths = [
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.websocket_core.websocket_manager', 
            'netra_backend.app.websocket_core.unified_manager',
        ]
        self.expected_websocket_classes = [
            'WebSocketManager',
            'UnifiedWebSocketManager',
            '_UnifiedWebSocketManagerImplementation'
        ]

    def test_single_websocket_manager_implementation_exists(self):
        """
        CRITICAL: Validate only ONE WebSocket manager implementation exists.
        
        CURRENT STATE: SHOULD FAIL - 3 competing implementations detected
        TARGET STATE: SHOULD PASS - Single SSOT implementation only
        
        Business Impact: Eliminates race conditions and ensures consistent behavior
        """
        logger.info("🚨 Testing for single WebSocket manager implementation (Issue #1182)")
        
        discovered_implementations = {}
        implementation_sources = set()
        
        for import_path in self.websocket_manager_import_paths:
            try:
                module = importlib.import_module(import_path)
                logger.info(f"📁 Analyzing module: {import_path}")
                
                for class_name in self.expected_websocket_classes:
                    if hasattr(module, class_name):
                        cls = getattr(module, class_name)
                        class_id = f"{cls.__module__}.{cls.__qualname__}"
                        
                        if class_id not in discovered_implementations:
                            discovered_implementations[class_id] = {
                                'class': cls,
                                'import_paths': [],
                                'module_file': getattr(module, '__file__', 'unknown')
                            }
                        
                        discovered_implementations[class_id]['import_paths'].append(import_path)
                        implementation_sources.add(cls.__module__)
                        
                        logger.info(f"  ✓ Found {class_name} -> {class_id}")
                        
            except ImportError as e:
                logger.warning(f"⚠️  Could not import {import_path}: {e}")
                continue
        
        # Log all discovered implementations
        logger.info(f"📊 SSOT Analysis Results:")
        logger.info(f"   Unique implementations: {len(discovered_implementations)}")
        logger.info(f"   Implementation sources: {len(implementation_sources)}")
        
        for class_id, details in discovered_implementations.items():
            logger.info(f"   🔍 {class_id}")
            logger.info(f"      Import paths: {details['import_paths']}")
            logger.info(f"      Source file: {details['module_file']}")
        
        # CRITICAL: Should have exactly 1 implementation for SSOT compliance
        # CURRENT STATE: This assertion SHOULD FAIL (multiple implementations exist)
        # TARGET STATE: This assertion SHOULD PASS (single implementation only)
        self.assertEqual(
            len(implementation_sources), 1,
            f"SSOT VIOLATION: Found {len(implementation_sources)} WebSocket manager implementation sources. "
            f"Expected exactly 1 for SSOT compliance. Sources: {implementation_sources}. "
            f"This indicates Issue #1182 SSOT consolidation is incomplete."
        )
        
        # Additional validation: All classes should resolve to same implementation
        unique_classes = set(details['class'] for details in discovered_implementations.values())
        self.assertEqual(
            len(unique_classes), 1,
            f"SSOT VIOLATION: Found {len(unique_classes)} unique WebSocket manager classes. "
            f"Expected exactly 1 for SSOT compliance. "
            f"Classes: {[cls.__name__ for cls in unique_classes]}"
        )

    def test_import_path_consolidation_complete(self):
        """
        Validate all import paths resolve to same implementation.
        
        CURRENT STATE: SHOULD FAIL - Multiple implementations found
        TARGET STATE: SHOULD PASS - All paths resolve to single SSOT implementation
        
        Business Impact: Prevents import confusion and ensures consistent behavior
        """
        logger.info("🔗 Testing import path consolidation (Issue #1182)")
        
        resolved_classes = {}
        
        # Test primary import paths
        import_scenarios = [
            ('netra_backend.app.websocket_core.manager', 'WebSocketManager'),
            ('netra_backend.app.websocket_core.websocket_manager', 'WebSocketManager'),
            ('netra_backend.app.websocket_core.websocket_manager', 'UnifiedWebSocketManager'),
            ('netra_backend.app.websocket_core.unified_manager', '_UnifiedWebSocketManagerImplementation'),
        ]
        
        for module_path, class_name in import_scenarios:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    class_key = f"{module_path}.{class_name}"
                    resolved_classes[class_key] = {
                        'class': cls,
                        'class_id': f"{cls.__module__}.{cls.__qualname__}",
                        'memory_address': id(cls)
                    }
                    logger.info(f"✓ {class_key} -> {cls}")
                    
            except ImportError as e:
                logger.warning(f"⚠️  Could not import {module_path}: {e}")
                continue
        
        # Analyze resolution patterns
        unique_class_ids = set(details['class_id'] for details in resolved_classes.values())
        unique_memory_addresses = set(details['memory_address'] for details in resolved_classes.values())
        
        logger.info(f"📊 Import Path Analysis:")
        logger.info(f"   Total import paths tested: {len(import_scenarios)}")
        logger.info(f"   Successfully resolved: {len(resolved_classes)}")
        logger.info(f"   Unique class IDs: {len(unique_class_ids)}")
        logger.info(f"   Unique memory addresses: {len(unique_memory_addresses)}")
        
        for class_key, details in resolved_classes.items():
            logger.info(f"   🔍 {class_key}")
            logger.info(f"      Resolves to: {details['class_id']}")
            logger.info(f"      Memory: {hex(details['memory_address'])}")
        
        # CRITICAL: All import paths should resolve to same class for SSOT compliance
        # CURRENT STATE: This assertion SHOULD FAIL (multiple implementations)
        # TARGET STATE: This assertion SHOULD PASS (single implementation)
        self.assertLessEqual(
            len(unique_class_ids), 1,
            f"SSOT VIOLATION: Import paths resolve to {len(unique_class_ids)} different implementations. "
            f"Expected all paths to resolve to 1 SSOT implementation. "
            f"Class IDs: {unique_class_ids}. "
            f"This indicates Issue #1182 import consolidation is incomplete."
        )

    def test_legacy_compatibility_layer_functions(self):
        """
        Ensure legacy imports still work during transition.
        
        CURRENT STATE: SHOULD PASS - Compatibility maintained
        TARGET STATE: SHOULD PASS - Compatibility preserved during migration
        
        Business Impact: Prevents breaking changes during SSOT migration
        """
        logger.info("🔄 Testing legacy compatibility layer (Issue #1182)")
        
        compatibility_scenarios = [
            # Legacy import that should still work
            ('netra_backend.app.websocket_core.manager', 'WebSocketManager'),
            # Primary SSOT import
            ('netra_backend.app.websocket_core.websocket_manager', 'WebSocketManager'),
        ]
        
        working_imports = []
        broken_imports = []
        
        for module_path, class_name in compatibility_scenarios:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    # Verify class is callable and has expected interface
                    self.assertTrue(inspect.isclass(cls), f"{class_name} should be a class")
                    working_imports.append((module_path, class_name))
                    logger.info(f"✓ Legacy import working: {module_path}.{class_name}")
                else:
                    broken_imports.append((module_path, class_name, "Class not found"))
                    
            except ImportError as e:
                broken_imports.append((module_path, class_name, str(e)))
                logger.error(f"❌ Legacy import broken: {module_path}.{class_name} - {e}")
        
        logger.info(f"📊 Compatibility Analysis:")
        logger.info(f"   Working imports: {len(working_imports)}")
        logger.info(f"   Broken imports: {len(broken_imports)}")
        
        # CRITICAL: Legacy compatibility should be maintained
        # This should PASS during transition to prevent breaking changes
        self.assertEqual(
            len(broken_imports), 0,
            f"Legacy compatibility broken for imports: {broken_imports}. "
            f"Issue #1182 migration must maintain backward compatibility."
        )
        
        # Verify at least one working import exists
        self.assertGreater(
            len(working_imports), 0,
            "No working WebSocket manager imports found. "
            "This indicates critical regression in Issue #1182 migration."
        )

    def test_websocket_manager_interface_consistency(self):
        """
        Validate consistent signatures across all manager implementations.
        
        CURRENT STATE: SHOULD FAIL - Interface inconsistencies detected  
        TARGET STATE: SHOULD PASS - All interfaces consistent and compatible
        
        Business Impact: Prevents interface mismatches that cause runtime failures
        Related: Issue #1209 DemoWebSocketBridge interface compatibility
        """
        logger.info("🔌 Testing WebSocket manager interface consistency (Issue #1182)")
        
        # Collect all available WebSocket manager classes
        manager_classes = []
        
        for module_path in self.websocket_manager_import_paths:
            try:
                module = importlib.import_module(module_path)
                for class_name in self.expected_websocket_classes:
                    if hasattr(module, class_name):
                        cls = getattr(module, class_name)
                        manager_classes.append((f"{module_path}.{class_name}", cls))
                        
            except ImportError:
                continue
        
        logger.info(f"🔍 Analyzing {len(manager_classes)} WebSocket manager interfaces")
        
        # Define expected interface methods for consistency checking
        expected_methods = [
            ('emit_agent_event', 'async'),
            ('get_active_connections', 'sync'),
            ('send_message', 'async'),
            ('disconnect_user', 'async'),
        ]
        
        interface_analysis = {}
        
        for class_key, cls in manager_classes:
            interface_analysis[class_key] = {
                'methods': {},
                'missing_methods': [],
                'extra_methods': []
            }
            
            # Check expected methods
            for method_name, expected_type in expected_methods:
                if hasattr(cls, method_name):
                    method = getattr(cls, method_name)
                    is_async = inspect.iscoroutinefunction(method)
                    actual_type = 'async' if is_async else 'sync'
                    
                    interface_analysis[class_key]['methods'][method_name] = {
                        'exists': True,
                        'type': actual_type,
                        'signature': str(inspect.signature(method)),
                        'matches_expected': actual_type == expected_type
                    }
                else:
                    interface_analysis[class_key]['missing_methods'].append(method_name)
                    interface_analysis[class_key]['methods'][method_name] = {
                        'exists': False,
                        'matches_expected': False
                    }
        
        # Analyze interface consistency
        inconsistencies = []
        
        for class_key, analysis in interface_analysis.items():
            logger.info(f"📋 Interface analysis for {class_key}:")
            
            for method_name, method_info in analysis['methods'].items():
                if method_info['exists']:
                    match_status = "✓" if method_info['matches_expected'] else "❌"
                    logger.info(f"   {match_status} {method_name}: {method_info['type']} - {method_info['signature']}")
                    
                    if not method_info['matches_expected']:
                        inconsistencies.append(f"{class_key}.{method_name}")
                else:
                    logger.info(f"   ❌ {method_name}: MISSING")
                    inconsistencies.append(f"{class_key}.{method_name}")
            
            if analysis['missing_methods']:
                logger.warning(f"   Missing methods: {analysis['missing_methods']}")
        
        # CRITICAL: All interfaces should be consistent for SSOT compliance
        # CURRENT STATE: This assertion SHOULD FAIL (interface inconsistencies)
        # TARGET STATE: This assertion SHOULD PASS (consistent interfaces)
        self.assertEqual(
            len(inconsistencies), 0,
            f"Interface inconsistencies found in {len(inconsistencies)} methods: {inconsistencies}. "
            f"This indicates Issue #1182 interface standardization is incomplete. "
            f"Related to Issue #1209 DemoWebSocketBridge compatibility failures."
        )

    def test_demo_websocket_bridge_compatibility_validation(self):
        """
        Validate DemoWebSocketBridge interface compatibility (Issue #1209).
        
        CURRENT STATE: SHOULD FAIL - Interface mismatch with consolidated manager
        TARGET STATE: SHOULD PASS - DemoWebSocketBridge works with SSOT manager
        
        Business Impact: Critical for staging demo functionality
        Related: Issue #1209 regression from WebSocket SSOT violations
        """
        logger.info("🎭 Testing DemoWebSocketBridge compatibility (Issues #1182 + #1209)")
        
        demo_bridge_compatibility = {
            'import_success': False,
            'interface_match': False,
            'instantiation_success': False,
            'error_details': []
        }
        
        try:
            # Test DemoWebSocketBridge import and compatibility
            from netra_backend.app.routes.demo_websocket import execute_real_agent_workflow
            demo_bridge_compatibility['import_success'] = True
            logger.info("✓ DemoWebSocketBridge imports successfully")
            
            # Test WebSocket manager compatibility with demo bridge
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Check if WebSocketManager can be used in demo context
            # This simulates the integration pattern used in demo_websocket.py
            try:
                # Create a mock WebSocket to test interface compatibility
                from unittest.mock import AsyncMock, MagicMock
                mock_websocket = AsyncMock()
                mock_websocket.send_text = AsyncMock()
                
                # Test the interface pattern used in demo bridge
                manager_instance = WebSocketManager(websocket=mock_websocket, user_id="demo_user")
                demo_bridge_compatibility['instantiation_success'] = True
                demo_bridge_compatibility['interface_match'] = True
                logger.info("✓ WebSocketManager compatible with DemoWebSocketBridge pattern")
                
            except Exception as e:
                demo_bridge_compatibility['error_details'].append(f"Instantiation failed: {e}")
                logger.error(f"❌ WebSocketManager instantiation failed: {e}")
                
        except ImportError as e:
            demo_bridge_compatibility['error_details'].append(f"Import failed: {e}")
            logger.error(f"❌ DemoWebSocketBridge import failed: {e}")
            
        except Exception as e:
            demo_bridge_compatibility['error_details'].append(f"Compatibility test failed: {e}")
            logger.error(f"❌ DemoWebSocketBridge compatibility test failed: {e}")
        
        logger.info(f"📊 DemoWebSocketBridge Compatibility Report:")
        logger.info(f"   Import success: {demo_bridge_compatibility['import_success']}")
        logger.info(f"   Interface match: {demo_bridge_compatibility['interface_match']}")
        logger.info(f"   Instantiation success: {demo_bridge_compatibility['instantiation_success']}")
        
        if demo_bridge_compatibility['error_details']:
            logger.error(f"   Errors: {demo_bridge_compatibility['error_details']}")
        
        # CRITICAL: DemoWebSocketBridge should be compatible with SSOT manager
        # CURRENT STATE: This assertion SHOULD FAIL (Issue #1209 regression)
        # TARGET STATE: This assertion SHOULD PASS (compatibility restored)
        self.assertTrue(
            demo_bridge_compatibility['import_success'],
            f"DemoWebSocketBridge import failed. Issue #1209 regression from WebSocket SSOT violations. "
            f"Errors: {demo_bridge_compatibility['error_details']}"
        )
        
        self.assertTrue(
            demo_bridge_compatibility['interface_match'] and demo_bridge_compatibility['instantiation_success'],
            f"DemoWebSocketBridge interface incompatible with SSOT WebSocketManager. "
            f"Issue #1209 regression requires interface alignment. "
            f"Errors: {demo_bridge_compatibility['error_details']}"
        )


if __name__ == '__main__':
    unittest.main()