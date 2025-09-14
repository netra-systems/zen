"""SSOT Validation Tests - WebSocket Manager Consolidation (Issue #954 Step 2)

Category 1: SSOT Consolidation Validation Tests

Purpose: Create NEW validation tests (20% of SSOT Gardener effort) to verify 
WebSocket Manager consolidation from 3 competing implementations down to 1 SSOT.

These tests are DESIGNED TO FAIL until SSOT consolidation is complete.
After consolidation, they should PASS to validate successful unification.

Business Value: Protects $500K+ ARR by ensuring Golden Path WebSocket reliability.
"""

import ast
import importlib
import inspect
import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Set, Any, Type
from unittest import TestCase

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class WebSocketManagerSsotConsolidationValidationTest(SSotAsyncTestCase):
    """SSOT Consolidation Validation - Tests to verify only ONE WebSocket manager exists.
    
    EXPECTED BEHAVIOR:
    - BEFORE consolidation: These tests SHOULD FAIL (detecting multiple implementations)  
    - AFTER consolidation: These tests SHOULD PASS (detecting single SSOT implementation)
    """

    def setUp(self):
        super().setUp()
        self.websocket_core_path = Path(__file__).parent.parent.parent / "netra_backend" / "app" / "websocket_core"
        self.test_results = {}
        
    def test_single_websocket_manager_class_exists(self):
        """Verify only ONE WebSocket Manager class implementation exists in codebase.
        
        EXPECTED TO FAIL UNTIL CONSOLIDATION: Currently 3+ competing implementations.
        SHOULD PASS AFTER CONSOLIDATION: Only 1 canonical SSOT implementation.
        """
        websocket_manager_classes = self._find_websocket_manager_classes()
        
        # Log current state for debugging
        logger.info(f"Found {len(websocket_manager_classes)} WebSocket Manager classes:")
        for class_info in websocket_manager_classes:
            logger.info(f"  - {class_info['name']} in {class_info['file']}")
        
        # SSOT Requirement: Only ONE WebSocket Manager class should exist
        self.assertEqual(
            len(websocket_manager_classes), 
            1,
            f"SSOT VIOLATION: Found {len(websocket_manager_classes)} WebSocket Manager classes. "
            f"Expected exactly 1 after consolidation. Classes found: "
            f"{[cls['name'] + ' in ' + cls['file'] for cls in websocket_manager_classes]}"
        )
        
        # Verify the single class is the canonical SSOT implementation
        if websocket_manager_classes:
            canonical_class = websocket_manager_classes[0]
            self.assertIn(
                "unified", 
                canonical_class['file'].lower(),
                f"SSOT VIOLATION: Canonical class should be in unified module, "
                f"found in {canonical_class['file']}"
            )

    def test_no_duplicate_manager_implementations(self):
        """Verify no duplicate manager implementation patterns exist.
        
        EXPECTED TO FAIL UNTIL CONSOLIDATION: Multiple competing implementations.
        SHOULD PASS AFTER CONSOLIDATION: No duplicates detected.
        """
        implementation_patterns = self._analyze_implementation_patterns()
        
        # Check for duplicate method signatures
        duplicate_methods = self._find_duplicate_methods(implementation_patterns)
        
        self.assertEqual(
            len(duplicate_methods),
            0,
            f"SSOT VIOLATION: Found duplicate method implementations: {duplicate_methods}. "
            f"All methods should be consolidated into single SSOT implementation."
        )

    def test_websocket_manager_factory_deprecation_enforced(self):
        """Verify WebSocket Manager Factory is properly deprecated and redirects to SSOT.
        
        EXPECTED TO FAIL UNTIL CONSOLIDATION: Factory still creating separate instances.
        SHOULD PASS AFTER CONSOLIDATION: Factory redirects to canonical SSOT.
        """
        try:
            # Try to import factory module
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            
            # Check if factory is properly deprecated
            factory_source = inspect.getsource(create_websocket_manager)
            
            # SSOT Requirement: Factory should redirect to canonical implementation
            self.assertIn(
                "DEPRECATED",
                factory_source.upper(),
                "SSOT VIOLATION: WebSocket Manager Factory should be marked DEPRECATED"
            )
            
            # Verify factory redirects to SSOT implementation
            self.assertIn(
                "websocket_manager",
                factory_source.lower(),
                "SSOT VIOLATION: Factory should redirect to canonical websocket_manager module"
            )
            
        except ImportError:
            # If factory is completely removed, that's SSOT compliance
            logger.info("WebSocket Manager Factory completely removed - SSOT compliant")
            pass

    def test_import_path_consistency_validation(self):
        """Verify all WebSocket Manager imports resolve to same implementation.
        
        EXPECTED TO FAIL UNTIL CONSOLIDATION: Different import paths lead to different objects.
        SHOULD PASS AFTER CONSOLIDATION: All paths resolve to same SSOT object.
        """
        import_paths_to_test = [
            "netra_backend.app.websocket_core.websocket_manager.WebSocketManager",
            "netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager", 
        ]
        
        imported_classes = {}
        
        for import_path in import_paths_to_test:
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                imported_classes[import_path] = cls
                logger.info(f"Successfully imported {import_path}: {cls}")
            except (ImportError, AttributeError) as e:
                logger.warning(f"Could not import {import_path}: {e}")
                continue
        
        if len(imported_classes) > 1:
            # Get all unique class objects
            unique_classes = set(imported_classes.values())
            
            # SSOT Requirement: All imports should resolve to same class object
            self.assertEqual(
                len(unique_classes),
                1,
                f"SSOT VIOLATION: Different import paths resolve to different classes. "
                f"Found {len(unique_classes)} unique classes from paths: {list(imported_classes.keys())}"
            )

    def test_websocket_core_module_structure_consolidation(self):
        """Verify WebSocket core module has consolidated structure.
        
        EXPECTED TO FAIL UNTIL CONSOLIDATION: Multiple manager files exist.
        SHOULD PASS AFTER CONSOLIDATION: Clean, minimal module structure.
        """
        if not self.websocket_core_path.exists():
            self.skipTest("WebSocket core path does not exist")
            
        websocket_files = list(self.websocket_core_path.glob("*websocket*manager*.py"))
        
        # Log current files for analysis
        logger.info(f"WebSocket Manager files found: {[f.name for f in websocket_files]}")
        
        # SSOT Requirement: Minimal file structure
        # After consolidation, should have at most 2 files:
        # 1. The main SSOT implementation
        # 2. Optional compatibility layer (temporary)
        self.assertLessEqual(
            len(websocket_files),
            2,
            f"SSOT VIOLATION: Too many WebSocket Manager files. "
            f"Expected ≤2 after consolidation, found {len(websocket_files)}: "
            f"{[f.name for f in websocket_files]}"
        )

    def _find_websocket_manager_classes(self) -> List[Dict[str, Any]]:
        """Find all WebSocket Manager class definitions in codebase."""
        classes = []
        
        # Search in websocket_core directory
        if self.websocket_core_path.exists():
            for py_file in self.websocket_core_path.glob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Parse AST to find class definitions
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if "websocketmanager" in node.name.lower():
                                classes.append({
                                    'name': node.name,
                                    'file': str(py_file),
                                    'line': node.lineno
                                })
                except Exception as e:
                    logger.warning(f"Error parsing {py_file}: {e}")
                    continue
        
        return classes

    def _analyze_implementation_patterns(self) -> Dict[str, List[str]]:
        """Analyze implementation patterns across WebSocket Manager classes."""
        patterns = {}
        
        websocket_classes = self._find_websocket_manager_classes()
        
        for class_info in websocket_classes:
            try:
                # Read file and extract methods
                with open(class_info['file'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                class_methods = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == class_info['name']:
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                class_methods.append(item.name)
                
                patterns[class_info['name']] = class_methods
                
            except Exception as e:
                logger.warning(f"Error analyzing {class_info['file']}: {e}")
                continue
        
        return patterns

    def _find_duplicate_methods(self, patterns: Dict[str, List[str]]) -> List[str]:
        """Find methods that appear in multiple WebSocket Manager implementations."""
        method_counts = {}
        
        for class_name, methods in patterns.items():
            for method in methods:
                if method not in method_counts:
                    method_counts[method] = []
                method_counts[method].append(class_name)
        
        # Find methods that appear in multiple classes
        duplicates = []
        for method, classes in method_counts.items():
            if len(classes) > 1 and not method.startswith('_'):  # Ignore private methods
                duplicates.append(f"{method} (in {', '.join(classes)})")
        
        return duplicates


class WebSocketManagerSsotIntegrationValidationTest(SSotAsyncTestCase):
    """SSOT Integration Validation - Tests to verify consolidated manager works correctly."""
    
    def setUp(self):
        super().setUp()
        
    def test_consolidated_manager_can_be_imported(self):
        """Verify consolidated manager can be imported successfully.
        
        EXPECTED TO FAIL UNTIL CONSOLIDATION: Import conflicts or circular dependencies.
        SHOULD PASS AFTER CONSOLIDATION: Clean import of single SSOT implementation.
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Verify it's a proper class
            self.assertTrue(
                inspect.isclass(WebSocketManager),
                "WebSocketManager should be importable as a class"
            )
            
            # Verify it has expected interface methods
            expected_methods = ['emit_event', 'connect_user', 'disconnect_user']
            for method_name in expected_methods:
                self.assertTrue(
                    hasattr(WebSocketManager, method_name),
                    f"WebSocketManager should have {method_name} method"
                )
                
            logger.info("✅ WebSocketManager import and interface validation passed")
            
        except ImportError as e:
            self.fail(f"SSOT VIOLATION: Cannot import WebSocketManager: {e}")
        except Exception as e:
            self.fail(f"SSOT VIOLATION: WebSocketManager import error: {e}")
    
    def test_consolidated_manager_instantiation(self):
        """Verify consolidated manager can be instantiated properly.
        
        EXPECTED TO FAIL UNTIL CONSOLIDATION: Constructor conflicts or missing dependencies.
        SHOULD PASS AFTER CONSOLIDATION: Clean instantiation of SSOT implementation.
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Create test user context
            test_context = self._create_test_user_context()
            
            # Attempt instantiation
            manager = WebSocketManager(user_context=test_context)
            
            self.assertIsNotNone(manager, "WebSocketManager should instantiate successfully")
            self.assertTrue(hasattr(manager, 'user_context'), "Manager should have user_context")
            
            logger.info("✅ WebSocketManager instantiation validation passed")
            
        except Exception as e:
            self.fail(f"SSOT VIOLATION: WebSocketManager instantiation failed: {e}")
    
    def _create_test_user_context(self):
        """Create minimal test user context for manager instantiation."""
        from dataclasses import dataclass
        from shared.types.core_types import UserID, ThreadID
        
        @dataclass
        class TestUserContext:
            user_id: UserID
            thread_id: ThreadID
            request_id: str = "test_request"
            
        return TestUserContext(
            user_id=UserID("test_user_123"),
            thread_id=ThreadID("test_thread_456")
        )


if __name__ == '__main__':
    unittest.main()