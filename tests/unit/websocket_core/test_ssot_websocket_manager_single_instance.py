#!/usr/bin/env python
"""SSOT WebSocket Manager Single Instance Validation Test

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Golden Path Protection
- Business Goal: $500K+ ARR protection during SSOT consolidation
- Value Impact: Prevent race conditions from multiple WebSocket manager instances
- Revenue Impact: Ensures reliable WebSocket communication foundation

Test Strategy: This test MUST FAIL before SSOT consolidation and PASS after
- FAIL: Multiple WebSocket manager implementations exist (SSOT violation)
- PASS: Only one canonical WebSocket manager implementation exists

Issue #1033: WebSocket Manager SSOT Consolidation
This test validates that only ONE WebSocket manager implementation exists in the system
to prevent race conditions, event delivery inconsistencies, and connection state confusion.
"""

import ast
import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
import pytest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.logging.unified_logging_ssot import get_logger
from test_framework.ssot.base_test_case import SSotBaseTestCase as BaseTestCase

logger = get_logger(__name__)


class TestSSoTWebSocketManagerSingleInstance(BaseTestCase):
    """Test SSOT compliance for WebSocket Manager implementations.
    
    This test suite validates that only one authoritative WebSocket Manager 
    implementation exists in the system, preventing SSOT violations.
    """

    def test_single_websocket_manager_class_definition(self):
        """Test that only ONE WebSocket manager class is defined in the codebase.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently multiple manager classes exist (violation detected)
        - PASS: After SSOT consolidation, only one canonical manager exists
        
        This test scans all Python files to find WebSocket manager class definitions
        and ensures only one authoritative implementation exists.
        """
        logger.info("🔍 Scanning codebase for WebSocket manager class definitions...")
        
        websocket_manager_classes = self._find_websocket_manager_classes()
        
        logger.info(f"Found {len(websocket_manager_classes)} WebSocket manager classes:")
        for class_info in websocket_manager_classes:
            logger.info(f"  - {class_info['name']} in {class_info['file']}")
        
        # SSOT VIOLATION CHECK: Should have exactly ONE canonical implementation
        # This assertion WILL FAIL until SSOT consolidation is complete
        assert len(websocket_manager_classes) == 1, (
            f"SSOT VIOLATION: Found {len(websocket_manager_classes)} WebSocket manager classes. "
            f"Expected exactly 1 canonical implementation. "
            f"Classes found: {[c['name'] for c in websocket_manager_classes]}"
        )
        
        # Validate the single manager is the canonical SSOT implementation
        canonical_manager = websocket_manager_classes[0]
        expected_canonical_path = "netra_backend/app/websocket_core/websocket_manager.py"
        
        assert expected_canonical_path in canonical_manager['file'], (
            f"SSOT VIOLATION: WebSocket manager found at '{canonical_manager['file']}', "
            f"but canonical SSOT path should be '{expected_canonical_path}'"
        )

    def test_no_duplicate_websocket_manager_implementations(self):
        """Test that no duplicate WebSocket manager implementations exist.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently multiple implementations exist (SSOT violation)  
        - PASS: After SSOT consolidation, only one implementation
        
        This test checks for duplicate method implementations across different
        WebSocket manager classes that could cause inconsistent behavior.
        """
        logger.info("🔍 Checking for duplicate WebSocket manager implementations...")
        
        manager_implementations = self._find_websocket_manager_implementations()
        
        # Check for duplicate method implementations
        method_locations: Dict[str, List[str]] = {}
        
        for impl in manager_implementations:
            for method in impl['methods']:
                if method not in method_locations:
                    method_locations[method] = []
                method_locations[method].append(f"{impl['class_name']} in {impl['file']}")
        
        # Find methods implemented in multiple places (SSOT violations)
        duplicate_methods = {
            method: locations 
            for method, locations in method_locations.items() 
            if len(locations) > 1
        }
        
        if duplicate_methods:
            logger.error("SSOT VIOLATIONS: Duplicate method implementations found:")
            for method, locations in duplicate_methods.items():
                logger.error(f"  Method '{method}' implemented in:")
                for location in locations:
                    logger.error(f"    - {location}")
        
        # SSOT VIOLATION CHECK: No method should be implemented multiple times
        # This assertion WILL FAIL until duplicate implementations are consolidated
        assert len(duplicate_methods) == 0, (
            f"SSOT VIOLATION: Found duplicate method implementations: {list(duplicate_methods.keys())}. "
            f"Each method should exist in exactly one canonical location."
        )

    def test_websocket_manager_import_consolidation(self):
        """Test that all WebSocket manager imports resolve to the same class.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently different import paths resolve to different classes
        - PASS: After SSOT consolidation, all imports resolve to same class
        
        This test validates that various import paths all lead to the same
        WebSocket manager implementation.
        """
        logger.info("🔍 Testing WebSocket manager import consolidation...")
        
        # Common import patterns found in the codebase
        import_patterns = [
            "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager",
            "from netra_backend.app.websocket_core import WebSocketManager", 
            "from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation",
            "from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager"
        ]
        
        imported_classes = {}
        import_errors = []
        
        for import_pattern in import_patterns:
            try:
                # Extract module and class names
                if " import " in import_pattern:
                    module_part, import_part = import_pattern.split(" import ", 1)
                    module_name = module_part.replace("from ", "")
                    class_or_func_name = import_part
                else:
                    continue  # Skip malformed patterns
                
                # Import the module
                module = importlib.import_module(module_name)
                
                # Get the class or function
                if hasattr(module, class_or_func_name):
                    obj = getattr(module, class_or_func_name)
                    imported_classes[import_pattern] = obj
                    logger.info(f"✓ Imported: {import_pattern} -> {type(obj)}")
                else:
                    import_errors.append(f"'{class_or_func_name}' not found in {module_name}")
                    
            except Exception as e:
                import_errors.append(f"Failed to import '{import_pattern}': {str(e)}")
        
        # Log any import errors (expected during transition)
        for error in import_errors:
            logger.warning(f"Import error: {error}")
        
        # Check if all successfully imported classes are the same
        if len(imported_classes) > 1:
            class_types = set()
            for pattern, obj in imported_classes.items():
                if inspect.isclass(obj):
                    class_types.add(obj)
                elif callable(obj):
                    # For factory functions, we can't easily check what they return
                    # without calling them, so we'll skip this check
                    continue
            
            # SSOT VIOLATION CHECK: All imports should resolve to same class
            # This assertion WILL FAIL until import consolidation is complete
            if len(class_types) > 1:
                logger.error("SSOT VIOLATION: Different imports resolve to different classes:")
                for pattern, obj in imported_classes.items():
                    logger.error(f"  {pattern} -> {type(obj)} ({id(obj)})")
                
                assert len(class_types) == 1, (
                    f"SSOT VIOLATION: {len(class_types)} different WebSocket manager classes "
                    f"found through different import paths. Expected exactly 1 canonical class."
                )

    def _find_websocket_manager_classes(self) -> List[Dict[str, Any]]:
        """Find all WebSocket manager class definitions in the codebase."""
        websocket_manager_classes = []
        
        # Search in the main backend directory
        backend_path = Path(project_root) / "netra_backend"
        
        if not backend_path.exists():
            logger.warning(f"Backend path not found: {backend_path}")
            return websocket_manager_classes
        
        for py_file in backend_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST to find class definitions
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_name = node.name
                            # Look for WebSocket manager related class names
                            if any(keyword in class_name.lower() for keyword in ['websocket', 'websocketmanager']):
                                websocket_manager_classes.append({
                                    'name': class_name,
                                    'file': str(py_file.relative_to(Path(project_root))),
                                    'full_path': str(py_file)
                                })
                except SyntaxError:
                    # Skip files with syntax errors
                    continue
                    
            except (UnicodeDecodeError, PermissionError):
                # Skip files we can't read
                continue
        
        return websocket_manager_classes
    
    def _find_websocket_manager_implementations(self) -> List[Dict[str, Any]]:
        """Find all WebSocket manager method implementations."""
        implementations = []
        
        # Key WebSocket manager methods to look for
        websocket_methods = [
            'connect', 'disconnect', 'send_message', 'broadcast',
            'add_connection', 'remove_connection', 'emit_event',
            'handle_agent_event', 'notify_agent_started', 'notify_agent_completed'
        ]
        
        # Search in the main backend directory
        backend_path = Path(project_root) / "netra_backend"
        
        if not backend_path.exists():
            return implementations
        
        for py_file in backend_path.rglob("*.py"):
            # Focus on WebSocket-related files
            if 'websocket' not in py_file.name.lower():
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_name = node.name
                            if 'websocket' in class_name.lower():
                                # Find methods in this class
                                methods = []
                                for item in node.body:
                                    if isinstance(item, ast.FunctionDef):
                                        if item.name in websocket_methods:
                                            methods.append(item.name)
                                
                                if methods:
                                    implementations.append({
                                        'class_name': class_name,
                                        'file': str(py_file.relative_to(Path(project_root))),
                                        'methods': methods
                                    })
                except SyntaxError:
                    continue
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return implementations


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])