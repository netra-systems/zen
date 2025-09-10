"""
SSOT WebSocket Manager Single Source of Truth Validation Test

This test file validates that there is only ONE canonical WebSocket manager implementation
in the codebase, following SSOT principles. 

EXPECTED BEHAVIOR: These tests should FAIL initially to prove SSOT violations exist.
After SSOT refactor (Step 4), they should PASS.

Business Value: Platform/Internal - System Architecture Compliance
Ensures single source of truth for WebSocket management, preventing fragmentation.

Test Strategy: Static analysis and import inspection (no runtime dependencies).
NO DOCKER required - pure Python module discovery and analysis.
"""

import importlib
import inspect
import pkgutil
import sys
from pathlib import Path
from typing import List, Set, Tuple, Dict, Any
import unittest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketManagerSSotCompliance(SSotBaseTestCase):
    """Test suite to validate SSOT compliance for WebSocket managers.
    
    These tests should FAIL initially, proving 7+ managers exist.
    After refactor, they should PASS with only UnifiedWebSocketManager.
    """

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.codebase_root = Path(__file__).parent.parent.parent.parent
        self.websocket_manager_classes = []
        self.discovered_violations = []

    def _discover_websocket_manager_classes(self) -> List[Tuple[str, str, type]]:
        """Discover all WebSocket manager classes in the codebase.
        
        Returns:
            List of tuples: (module_path, class_name, class_object)
        """
        manager_classes = []
        
        # Search patterns for WebSocket manager classes
        search_patterns = [
            "WebSocketManager",
            "UnifiedWebSocketManager", 
            "IsolatedWebSocketManager",
            "WebSocketConnectionManager",
            "ConnectionManager",
            "EmergencyWebSocketManager",
            "DegradedWebSocketManager"
        ]
        
        # Search in main backend modules
        backend_paths = [
            self.codebase_root / "netra_backend" / "app" / "websocket_core",
            self.codebase_root / "netra_backend" / "app" / "websocket", 
            self.codebase_root / "netra_backend" / "app" / "services" / "websocket"
        ]
        
        for backend_path in backend_paths:
            if backend_path.exists():
                for py_file in backend_path.rglob("*.py"):
                    if py_file.name.startswith("__"):
                        continue
                        
                    try:
                        # Read file content to find class definitions
                        content = py_file.read_text(encoding="utf-8")
                        
                        for pattern in search_patterns:
                            if f"class {pattern}" in content:
                                # Found a potential WebSocket manager class
                                rel_path = py_file.relative_to(self.codebase_root)
                                module_path = str(rel_path).replace("/", ".").replace("\\", ".").replace(".py", "")
                                
                                manager_classes.append((
                                    module_path,
                                    pattern, 
                                    py_file
                                ))
                                
                    except (UnicodeDecodeError, PermissionError):
                        # Skip files that can't be read
                        continue
        
        return manager_classes

    def _get_websocket_manager_implementations(self) -> Dict[str, List[str]]:
        """Get all WebSocket manager implementations by analyzing file contents.
        
        Returns:
            Dict mapping implementation type to list of file paths
        """
        implementations = {
            "managers": [],
            "factories": [],
            "protocols": [],
            "adapters": []
        }
        
        # Find all WebSocket-related Python files
        websocket_files = []
        backend_paths = [
            self.codebase_root / "netra_backend" / "app" / "websocket_core",
            self.codebase_root / "netra_backend" / "app" / "websocket"
        ]
        
        for backend_path in backend_paths:
            if backend_path.exists():
                websocket_files.extend(list(backend_path.rglob("*.py")))
        
        for py_file in websocket_files:
            if py_file.name.startswith("__"):
                continue
                
            try:
                content = py_file.read_text(encoding="utf-8")
                file_path = str(py_file.relative_to(self.codebase_root))
                
                # Categorize files by their WebSocket manager role
                if any(pattern in content for pattern in [
                    "class UnifiedWebSocketManager",
                    "class IsolatedWebSocketManager", 
                    "class WebSocketConnectionManager",
                    "class EmergencyWebSocketManager",
                    "class DegradedWebSocketManager"
                ]):
                    implementations["managers"].append(file_path)
                    
                if "class WebSocketManagerFactory" in content:
                    implementations["factories"].append(file_path)
                    
                if "class WebSocketManagerProtocol" in content:
                    implementations["protocols"].append(file_path)
                    
                if "Adapter" in py_file.name and "WebSocket" in content:
                    implementations["adapters"].append(file_path)
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return implementations

    def test_only_unified_websocket_manager_exists(self):
        """Test that only UnifiedWebSocketManager exists as the SSOT.
        
        EXPECTED: This test should FAIL initially - proves 7+ managers exist.
        After refactor: Should PASS with only UnifiedWebSocketManager.
        """
        manager_classes = self._discover_websocket_manager_classes()
        
        # Extract just the class names for easier analysis
        class_names = [class_name for _, class_name, _ in manager_classes]
        unique_classes = set(class_names)
        
        # Log discovered violations for debugging
        self.discovered_violations = manager_classes
        
        # SSOT Requirement: Only UnifiedWebSocketManager should exist
        expected_manager = "UnifiedWebSocketManager"
        
        # This should FAIL initially - multiple managers exist
        self.assertEqual(
            len(unique_classes), 1,
            f"SSOT VIOLATION: Found {len(unique_classes)} WebSocket manager types, expected 1. "
            f"Classes found: {sorted(unique_classes)}. "
            f"Only {expected_manager} should exist as the SSOT."
        )
        
        # Verify the one manager is the expected SSOT
        self.assertIn(
            expected_manager, unique_classes,
            f"SSOT VIOLATION: Expected {expected_manager} not found. "
            f"Available classes: {sorted(unique_classes)}"
        )

    def test_no_duplicate_websocket_manager_implementations(self):
        """Test that there are no duplicate WebSocket manager implementations.
        
        EXPECTED: This test should FAIL initially - multiple implementations exist.
        After refactor: Should PASS with consolidated implementation.
        """
        implementations = self._get_websocket_manager_implementations()
        
        # Count total manager implementations
        total_managers = len(implementations["managers"])
        
        # SSOT Requirement: Only 1 manager implementation should exist
        self.assertEqual(
            total_managers, 1,
            f"SSOT VIOLATION: Found {total_managers} WebSocket manager implementations, expected 1. "
            f"Manager files: {implementations['managers']}. "
            "Only unified_manager.py should contain the SSOT implementation."
        )
        
        # Verify the single implementation is in the expected location
        if total_managers > 0:
            expected_path_pattern = "netra_backend/app/websocket_core/unified_manager.py"
            manager_paths = implementations["managers"]
            
            expected_file_found = any(
                expected_path_pattern in path.replace("\\", "/")
                for path in manager_paths
            )
            
            self.assertTrue(
                expected_file_found,
                f"SSOT VIOLATION: Expected manager implementation not found in {expected_path_pattern}. "
                f"Found implementations in: {manager_paths}"
            )

    def test_websocket_factory_consolidation(self):
        """Test that WebSocket factory implementations are consolidated.
        
        EXPECTED: This test should FAIL initially - multiple factories exist.
        After refactor: Should PASS with single factory pattern.
        """
        implementations = self._get_websocket_manager_implementations()
        
        # Count factory implementations  
        total_factories = len(implementations["factories"])
        
        # SSOT Requirement: Only 1 factory should exist (or 0 if factories are eliminated)
        self.assertLessEqual(
            total_factories, 1,
            f"SSOT VIOLATION: Found {total_factories} WebSocket factory implementations, expected ≤1. "
            f"Factory files: {implementations['factories']}. "
            "Factory pattern should be consolidated or eliminated in favor of direct instantiation."
        )

    def test_websocket_protocol_consolidation(self):
        """Test that WebSocket protocol definitions are consolidated.
        
        EXPECTED: This test should FAIL initially if multiple protocols exist.
        After refactor: Should PASS with single protocol definition.
        """
        implementations = self._get_websocket_manager_implementations()
        
        # Count protocol implementations
        total_protocols = len(implementations["protocols"])
        
        # SSOT Requirement: Only 1 protocol definition should exist
        self.assertEqual(
            total_protocols, 1,
            f"SSOT VIOLATION: Found {total_protocols} WebSocket protocol implementations, expected 1. "
            f"Protocol files: {implementations['protocols']}. "
            "Only one canonical protocol definition should exist."
        )

    def test_no_legacy_websocket_adapters(self):
        """Test that legacy WebSocket adapters are eliminated.
        
        EXPECTED: This test should FAIL initially if adapters exist.
        After refactor: Should PASS with no legacy adapters.
        """
        implementations = self._get_websocket_manager_implementations()
        
        # Count adapter implementations
        total_adapters = len(implementations["adapters"])
        
        # SSOT Requirement: No legacy adapters should exist after consolidation
        self.assertEqual(
            total_adapters, 0,
            f"SSOT VIOLATION: Found {total_adapters} WebSocket adapter implementations, expected 0. "
            f"Adapter files: {implementations['adapters']}. "
            "Legacy adapters should be eliminated in favor of direct SSOT usage."
        )

    def tearDown(self):
        """Clean up after test."""
        # Log discovered violations for debugging Step 4 refactor
        if self.discovered_violations:
            print(f"\n=== SSOT VIOLATIONS DISCOVERED ===")
            print(f"Total WebSocket manager classes found: {len(self.discovered_violations)}")
            for module_path, class_name, file_path in self.discovered_violations:
                print(f"  - {class_name} in {module_path}")
            print(f"=== END VIOLATIONS ===\n")
        
        super().tearDown()


if __name__ == "__main__":
    # Run tests to demonstrate SSOT violations
    unittest.main(verbosity=2)