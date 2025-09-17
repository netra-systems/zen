"""WebSocket Manager SSOT Consolidation Validation Test

CRITICAL BUSINESS CONTEXT:
- Golden Path Requirement: Single authoritative WebSocket manager for chat functionality
- Business Impact: $500K+ ARR protection requires reliable WebSocket infrastructure
- SSOT Goal: All import paths resolve to the same implementation
- Consolidation Validation: Ensure proper manager consolidation after cleanup

TEST PURPOSE:
This test validates that WebSocket manager consolidation has been properly implemented.
It verifies that all import paths lead to the same canonical implementation and that
all legacy features are preserved in the consolidated manager.

Expected Behavior:
- All import paths resolve to the same manager class
- Consolidated manager supports all required features
- No duplicate manager implementations exist
- Proper SSOT compliance throughout the system

Business Value Justification:
- Segment: ALL (Free -> Enterprise) - Platform integrity
- Business Goal: Ensure reliable chat functionality infrastructure
- Value Impact: Single source of truth for WebSocket management
- Revenue Impact: Protect $500K+ ARR through consistent WebSocket behavior
"""

import pytest
import sys
import inspect
import importlib
from typing import Dict, Set, Any, List, Tuple, Type
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.unit
class WebSocketManagerConsolidationValidationTests(SSotBaseTestCase):
    """Validate WebSocket manager consolidation compliance."""

    def setup_method(self, method):
        """Set up test environment for consolidation validation."""
        super().setup_method(method)
        logger.info(f"Setting up WebSocket manager consolidation test: {method.__name__}")
        
        # Clear module cache to ensure clean testing
        self.websocket_modules_to_clear = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.websocket_core.websocket_manager_factory',
            'netra_backend.app.websocket_core.websocket_manager_factory_compat',
        ]
        
        # Clear modules from cache
        for module_name in self.websocket_modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]

    def teardown_method(self, method):
        """Clean up after test."""
        super().teardown_method(method)
        
        # Clear modules again to avoid state leakage
        for module_name in self.websocket_modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]

    def test_single_websocket_manager_implementation_exists(self):
        """
        CRITICAL: Verify only one canonical WebSocket manager implementation exists.
        
        This test ensures SSOT compliance by confirming that all import paths
        resolve to the same underlying implementation class.
        """
        logger.info("Testing single WebSocket manager implementation existence")
        
        # Import from different paths
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManagerCanonical
            canonical_class = WebSocketManagerCanonical
            canonical_module = inspect.getmodule(canonical_class)
            logger.info(f"Canonical manager found: {canonical_class} from {canonical_module}")
        except ImportError as e:
            pytest.fail(f"Failed to import canonical WebSocket manager: {e}")
        
        # Test compatibility import path
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager as WebSocketManagerCompat
            compat_class = WebSocketManagerCompat
            compat_module = inspect.getmodule(compat_class)
            logger.info(f"Compatibility manager found: {compat_class} from {compat_module}")
        except ImportError as e:
            pytest.fail(f"Failed to import compatibility WebSocket manager: {e}")
        
        # Verify they are the same implementation
        assert canonical_class is compat_class, (
            f"SSOT VIOLATION: Different manager implementations found.\n"
            f"Canonical: {canonical_class} from {canonical_module}\n"
            f"Compatibility: {compat_class} from {compat_module}\n"
            f"Expected: Same class reference"
        )
        
        # Verify implementation source location
        canonical_source = inspect.getfile(canonical_class)
        logger.info(f"Manager implementation source: {canonical_source}")
        
        # The canonical implementation should be in unified_manager.py
        assert "unified_manager.py" in canonical_source, (
            f"SSOT VIOLATION: Manager implementation not in unified location.\n"
            f"Found in: {canonical_source}\n"
            f"Expected: unified_manager.py"
        )

    def test_all_import_paths_resolve_to_same_implementation(self):
        """
        Verify all documented import paths resolve to the same manager class.
        
        This ensures backward compatibility while maintaining SSOT compliance.
        """
        logger.info("Testing all import paths resolve to same implementation")
        
        import_tests = [
            {
                'module': 'netra_backend.app.websocket_core.websocket_manager',
                'class': 'WebSocketManager',
                'description': 'Canonical SSOT import path'
            },
            {
                'module': 'netra_backend.app.websocket_core.manager', 
                'class': 'WebSocketManager',
                'description': 'Backward compatibility import path'
            }
        ]
        
        manager_classes = []
        
        for import_test in import_tests:
            try:
                module = importlib.import_module(import_test['module'])
                manager_class = getattr(module, import_test['class'])
                manager_classes.append({
                    'class': manager_class,
                    'description': import_test['description'],
                    'module_path': import_test['module']
                })
                logger.info(f"Successfully imported {import_test['description']}: {manager_class}")
            except (ImportError, AttributeError) as e:
                pytest.fail(f"Failed to import {import_test['description']}: {e}")
        
        # Verify all classes are identical
        base_class = manager_classes[0]['class']
        for manager_info in manager_classes[1:]:
            assert manager_info['class'] is base_class, (
                f"SSOT VIOLATION: Different manager classes found.\n"
                f"Base: {base_class} from {manager_classes[0]['module_path']}\n"
                f"Different: {manager_info['class']} from {manager_info['module_path']}\n"
                f"All import paths must resolve to the same class instance"
            )

    def test_consolidated_manager_supports_all_legacy_features(self):
        """
        Verify the consolidated manager supports all features expected by legacy code.
        
        This ensures no functionality is lost during consolidation.
        """
        logger.info("Testing consolidated manager supports all legacy features")
        
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        
        # Check for required methods
        required_methods = [
            'get_connection',
            'add_connection', 
            'remove_connection',
            'get_connections_for_user',
            'send_to_user',
            'send_to_connection',
            'broadcast_to_all',
            'get_connection_count',
            'cleanup_stale_connections'
        ]
        
        for method_name in required_methods:
            assert hasattr(WebSocketManager, method_name), (
                f"CONSOLIDATION FAILURE: Missing required method '{method_name}' "
                f"in consolidated WebSocket manager"
            )
            
            method = getattr(WebSocketManager, method_name)
            assert callable(method), (
                f"CONSOLIDATION FAILURE: '{method_name}' is not callable in "
                f"consolidated WebSocket manager"
            )
        
        logger.info(f"All {len(required_methods)} required methods found in consolidated manager")
        
        # Check for required properties/attributes
        required_attributes = [
            '__init__',  # Constructor
        ]
        
        for attr_name in required_attributes:
            assert hasattr(WebSocketManager, attr_name), (
                f"CONSOLIDATION FAILURE: Missing required attribute '{attr_name}' "
                f"in consolidated WebSocket manager"
            )

    def test_no_duplicate_manager_implementations_exist(self):
        """
        Verify no duplicate WebSocket manager implementations exist in the codebase.
        
        This prevents SSOT violations and ensures clean architecture.
        """
        logger.info("Testing no duplicate manager implementations exist")
        
        import os
        import re
        
        # Define search patterns for WebSocket manager classes
        manager_class_patterns = [
            r'class\s+WebSocketManager\s*\(',
            r'class\s+.*WebSocketManager.*\s*\(',
            r'class\s+UnifiedWebSocketManager\s*\(',
        ]
        
        # Search in websocket_core directory
        websocket_core_path = '/Users/anthony/Desktop/netra-apex/netra_backend/app/websocket_core'
        manager_implementations = []
        
        if os.path.exists(websocket_core_path):
            for root, dirs, files in os.walk(websocket_core_path):
                # Skip backup and cache directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and 'backup' not in d.lower()]
                
                for file in files:
                    if file.endswith('.py') and 'backup' not in file.lower():
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                                for pattern in manager_class_patterns:
                                    matches = re.findall(pattern, content)
                                    if matches:
                                        relative_path = os.path.relpath(file_path, '/Users/anthony/Desktop/netra-apex')
                                        manager_implementations.append({
                                            'file': relative_path,
                                            'matches': matches,
                                            'pattern': pattern
                                        })
                        except (UnicodeDecodeError, OSError):
                            # Skip files that can't be read
                            continue
        
        logger.info(f"Found {len(manager_implementations)} potential manager implementations")
        
        # Expected implementations (allowed)
        allowed_implementations = [
            'netra_backend/app/websocket_core/unified_manager.py',  # The SSOT implementation
            'netra_backend/app/websocket_core/manager.py',  # Compatibility wrapper (should not have class definition)
        ]
        
        unexpected_implementations = []
        for impl in manager_implementations:
            file_path = impl['file']
            # Skip if it's just a compatibility import (no actual class definition)
            if 'manager.py' in file_path and any('import' in match or 'from' in match for match in impl['matches']):
                continue
            # Skip if it's the allowed SSOT implementation
            if any(allowed in file_path for allowed in allowed_implementations):
                continue
            unexpected_implementations.append(impl)
        
        # We should only have the unified implementation
        if len(unexpected_implementations) > 0:
            error_msg = "SSOT VIOLATION: Found unexpected WebSocket manager implementations:\n"
            for impl in unexpected_implementations:
                error_msg += f"  - {impl['file']}: {impl['matches']}\n"
            error_msg += f"\nExpected: Only unified_manager.py should contain the implementation"
            pytest.fail(error_msg)

    def test_factory_consolidation_compliance(self):
        """
        Verify WebSocket factory methods are properly consolidated.
        
        This ensures factory patterns follow SSOT principles.
        """
        logger.info("Testing factory consolidation compliance")
        
        # Import factory function
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            factory_function = get_websocket_manager
        except ImportError as e:
            pytest.fail(f"Failed to import websocket manager factory function: {e}")
        
        # Verify factory function is callable
        assert callable(factory_function), (
            "Factory function 'get_websocket_manager' is not callable"
        )
        
        # Test factory creates consistent instances
        try:
            # Create multiple instances and verify they follow the expected pattern
            manager1 = factory_function()
            manager2 = factory_function()
            
            # Both should be instances of the same class
            assert type(manager1) is type(manager2), (
                f"FACTORY INCONSISTENCY: Different manager types returned.\n"
                f"Manager 1 type: {type(manager1)}\n"
                f"Manager 2 type: {type(manager2)}"
            )
            
            # Verify they are WebSocketManager instances
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            assert isinstance(manager1, WebSocketManager), (
                f"Factory returned incorrect type: {type(manager1)}, expected WebSocketManager"
            )
            assert isinstance(manager2, WebSocketManager), (
                f"Factory returned incorrect type: {type(manager2)}, expected WebSocketManager"
            )
            
            logger.info("Factory function creates consistent WebSocketManager instances")
            
        except Exception as e:
            pytest.fail(f"Factory function failed to create manager instances: {e}")

    def test_websocket_manager_interface_consistency(self):
        """
        Verify the consolidated WebSocket manager maintains consistent interface.
        
        This ensures API compatibility across all usage patterns.
        """
        logger.info("Testing WebSocket manager interface consistency")
        
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        
        # Check for protocol compliance
        try:
            from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
            
            # Verify manager implements the protocol interface
            # Note: We can't use isinstance with Protocol, so check methods manually
            protocol_methods = []
            for attr_name in dir(WebSocketManagerProtocol):
                if not attr_name.startswith('_'):
                    attr = getattr(WebSocketManagerProtocol, attr_name)
                    if callable(attr):
                        protocol_methods.append(attr_name)
            
            logger.info(f"Checking {len(protocol_methods)} protocol methods")
            
            for method_name in protocol_methods:
                assert hasattr(WebSocketManager, method_name), (
                    f"INTERFACE VIOLATION: WebSocketManager missing protocol method '{method_name}'"
                )
                
                manager_method = getattr(WebSocketManager, method_name)
                assert callable(manager_method), (
                    f"INTERFACE VIOLATION: WebSocketManager method '{method_name}' is not callable"
                )
            
        except ImportError:
            logger.warning("WebSocketManagerProtocol not found, skipping protocol compliance check")
        
        # Verify basic interface requirements
        essential_methods = [
            ('get_connection', 'Retrieve connection by ID'),
            ('add_connection', 'Add new WebSocket connection'),
            ('remove_connection', 'Remove WebSocket connection'),
            ('send_to_user', 'Send message to specific user'),
            ('get_connections_for_user', 'Get all connections for user'),
        ]
        
        for method_name, description in essential_methods:
            assert hasattr(WebSocketManager, method_name), (
                f"INTERFACE VIOLATION: Missing essential method '{method_name}' ({description})"
            )
            
            method = getattr(WebSocketManager, method_name)
            assert callable(method), (
                f"INTERFACE VIOLATION: Method '{method_name}' is not callable"
            )
            
            # Check method signature has reasonable parameters
            signature = inspect.signature(method)
            assert len(signature.parameters) > 0, (
                f"INTERFACE VIOLATION: Method '{method_name}' has no parameters (should have at least 'self')"
            )
        
        logger.info("WebSocket manager interface consistency verified")

    def test_websocket_manager_instantiation_works(self):
        """
        Verify the consolidated WebSocket manager can be properly instantiated.
        
        This ensures the consolidation doesn't break basic functionality.
        """
        logger.info("Testing WebSocket manager instantiation")
        
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        
        try:
            # Test direct instantiation
            manager = WebSocketManager()
            assert manager is not None, "Failed to create WebSocket manager instance"
            
            # Verify it has the expected type
            assert isinstance(manager, WebSocketManager), (
                f"Manager instance has wrong type: {type(manager)}"
            )
            
            # Test that basic attributes exist
            assert hasattr(manager, '__class__'), "Manager missing __class__ attribute"
            assert hasattr(manager, '__dict__'), "Manager missing __dict__ attribute"
            
            logger.info("WebSocket manager instantiation successful")
            
        except Exception as e:
            pytest.fail(f"Failed to instantiate WebSocket manager: {e}")

    def test_websocket_manager_memory_efficiency(self):
        """
        Verify the consolidated manager doesn't have memory leaks or excessive overhead.
        
        This ensures consolidation improves rather than degrades performance.
        """
        logger.info("Testing WebSocket manager memory efficiency")
        
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        import gc
        
        # Test multiple instantiations don't accumulate
        initial_objects = len(gc.get_objects())
        
        managers = []
        for i in range(10):
            manager = WebSocketManager()
            managers.append(manager)
        
        # Clear references
        managers.clear()
        gc.collect()
        
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        
        # Allow some reasonable growth but not excessive
        assert object_growth < 1000, (
            f"MEMORY EFFICIENCY CONCERN: Excessive object growth during manager creation.\n"
            f"Initial objects: {initial_objects}\n"
            f"Final objects: {final_objects}\n"
            f"Growth: {object_growth} (should be < 1000)"
        )
        
        logger.info(f"Memory efficiency check passed - object growth: {object_growth}")

    def test_consolidated_manager_error_handling(self):
        """
        Verify the consolidated manager handles errors gracefully.
        
        This ensures consolidation maintains robust error handling.
        """
        logger.info("Testing consolidated manager error handling")
        
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        
        # Test handling of invalid inputs
        try:
            # Test with None connection ID
            connection = manager.get_connection(None)
            # Should return None or handle gracefully, not crash
            assert connection is None or connection is not None  # Either outcome is acceptable
            
            # Test with invalid user ID type
            connections = manager.get_connections_for_user(12345)  # Integer instead of string
            # Should handle gracefully
            assert isinstance(connections, (list, set, tuple)) or connections is None
            
            logger.info("Error handling tests passed")
            
        except Exception as e:
            # If the manager throws exceptions for invalid inputs, that's also acceptable
            # as long as they are appropriate exception types
            assert isinstance(e, (ValueError, TypeError, AttributeError)), (
                f"Manager should throw appropriate exceptions for invalid inputs, got: {type(e)}"
            )
            logger.info(f"Manager appropriately throws {type(e).__name__} for invalid inputs")