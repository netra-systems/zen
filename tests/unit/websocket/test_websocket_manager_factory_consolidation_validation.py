"""
WebSocket Manager Factory Consolidation Validation Test

This test file validates that WebSocket factory patterns are consolidated and follow
consistent interfaces across the codebase.

EXPECTED BEHAVIOR: These tests should FAIL initially to prove factory fragmentation exists.
After SSOT refactor (Step 4), they should PASS with consolidated factory patterns.

Business Value: Platform/Internal - Factory Pattern Consistency
Ensures factory patterns are consistent and not over-engineered across WebSocket components.

Test Strategy: Static analysis of factory classes and their interfaces.
NO DOCKER required - pure Python inspection and analysis.
"""

import ast
import inspect
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any, Optional
import unittest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketManagerFactoryConsolidation(SSotBaseTestCase, unittest.TestCase):
    """Test suite to validate factory consolidation for WebSocket managers.
    
    These tests should FAIL initially, proving fragmented factory patterns exist.
    After refactor, they should PASS with consolidated, consistent factories.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.codebase_root = Path(__file__).parent.parent.parent.parent
        self.factory_classes = []
        self.factory_methods = []
        self.interface_violations = []

    def _discover_factory_classes(self) -> List[Dict[str, Any]]:
        """Discover all factory classes related to WebSocket managers.
        
        Returns:
            List of factory class information dictionaries
        """
        factory_classes = []
        
        # Search patterns for factory classes
        factory_patterns = [
            "WebSocketManagerFactory",
            "WebSocketFactory", 
            "ConnectionFactory",
            "ManagerFactory",
            "WebSocketConnectionFactory"
        ]
        
        # Search in WebSocket modules
        websocket_paths = [
            self.codebase_root / "netra_backend" / "app" / "websocket_core",
            self.codebase_root / "netra_backend" / "app" / "websocket",
            self.codebase_root / "netra_backend" / "app" / "services" / "websocket"
        ]
        
        for websocket_path in websocket_paths:
            if websocket_path.exists():
                for py_file in websocket_path.rglob("*.py"):
                    if py_file.name.startswith("__"):
                        continue
                        
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        
                        # Parse AST to find class definitions
                        try:
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.ClassDef):
                                    if any(pattern in node.name for pattern in factory_patterns):
                                        factory_info = {
                                            "name": node.name,
                                            "file_path": str(py_file.relative_to(self.codebase_root)),
                                            "methods": [method.name for method in node.body 
                                                      if isinstance(method, ast.FunctionDef)],
                                            "bases": [base.id for base in node.bases 
                                                    if isinstance(base, ast.Name)],
                                            "line_number": node.lineno
                                        }
                                        factory_classes.append(factory_info)
                        except SyntaxError:
                            # Skip files with syntax errors
                            continue
                            
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        return factory_classes

    def _analyze_factory_methods(self) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze factory methods for consistency.
        
        Returns:
            Dict mapping method names to their implementations across factories
        """
        method_analysis = {}
        
        factory_classes = self._discover_factory_classes()
        
        for factory in factory_classes:
            for method_name in factory["methods"]:
                if method_name not in method_analysis:
                    method_analysis[method_name] = []
                
                method_analysis[method_name].append({
                    "factory_class": factory["name"],
                    "file_path": factory["file_path"],
                    "line_number": factory.get("line_number", 0)
                })
        
        return method_analysis

    def _get_factory_interface_signatures(self) -> Dict[str, Dict[str, str]]:
        """Get method signatures for factory interfaces.
        
        Returns:
            Dict mapping factory class names to their method signatures
        """
        signatures = {}
        factory_classes = self._discover_factory_classes()
        
        for factory in factory_classes:
            file_path = self.codebase_root / factory["file_path"]
            
            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == factory["name"]:
                        class_signatures = {}
                        
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                # Extract method signature
                                args = [arg.arg for arg in item.args.args]
                                signature = f"({', '.join(args)})"
                                class_signatures[item.name] = signature
                        
                        signatures[factory["name"]] = class_signatures
                        break
                        
            except (UnicodeDecodeError, PermissionError, SyntaxError):
                continue
        
        return signatures

    def test_factory_consolidation_compliance(self):
        """Test that factory implementations are consolidated.
        
        EXPECTED: This test should FAIL initially - multiple factory patterns exist.
        After refactor: Should PASS with consolidated factory approach.
        """
        factory_classes = self._discover_factory_classes()
        
        # Count total factory classes
        total_factories = len(factory_classes)
        
        # SSOT Requirement: Maximum 1 factory class (or 0 if factories are eliminated)
        self.assertLessEqual(
            total_factories, 1,
            f"FACTORY CONSOLIDATION VIOLATION: Found {total_factories} factory classes, expected  <= 1. "
            f"Factory classes found: {[f['name'] for f in factory_classes]}. "
            f"Files: {[f['file_path'] for f in factory_classes]}. "
            "Factory pattern should be consolidated or eliminated in favor of direct instantiation."
        )

    def test_factory_method_consistency(self):
        """Test that factory methods are consistent across implementations.
        
        EXPECTED: This test should FAIL initially if inconsistent factory methods exist.
        After refactor: Should PASS with consistent factory interfaces.
        """
        method_analysis = self._analyze_factory_methods()
        
        # Find methods that appear in multiple factories with potentially different implementations
        inconsistent_methods = []
        
        for method_name, implementations in method_analysis.items():
            if len(implementations) > 1:
                # Check if these are truly different implementations (not inheritance)
                unique_files = set(impl["file_path"] for impl in implementations)
                if len(unique_files) > 1:
                    inconsistent_methods.append({
                        "method": method_name,
                        "implementations": implementations
                    })
        
        # SSOT Requirement: No inconsistent factory method implementations
        self.assertEqual(
            len(inconsistent_methods), 0,
            f"FACTORY CONSISTENCY VIOLATION: Found {len(inconsistent_methods)} methods with "
            f"inconsistent implementations across factories: "
            f"{[m['method'] for m in inconsistent_methods]}. "
            "Factory methods should be consistent or consolidated."
        )

    def test_factory_interface_unification(self):
        """Test that factory interfaces are unified and not fragmented.
        
        EXPECTED: This test should FAIL initially if fragmented interfaces exist.
        After refactor: Should PASS with unified factory interface.
        """
        signatures = self._get_factory_interface_signatures()
        
        # If multiple factories exist, their interfaces should be identical
        if len(signatures) > 1:
            factory_names = list(signatures.keys())
            base_factory = factory_names[0]
            base_methods = signatures[base_factory]
            
            interface_violations = []
            
            for factory_name in factory_names[1:]:
                factory_methods = signatures[factory_name]
                
                # Check for method signature differences
                for method_name, base_sig in base_methods.items():
                    if method_name in factory_methods:
                        if factory_methods[method_name] != base_sig:
                            interface_violations.append({
                                "method": method_name,
                                "base_factory": base_factory,
                                "base_signature": base_sig,
                                "other_factory": factory_name,
                                "other_signature": factory_methods[method_name]
                            })
                
                # Check for missing methods
                for method_name in base_methods:
                    if method_name not in factory_methods:
                        interface_violations.append({
                            "method": method_name,
                            "issue": "missing_method",
                            "factory": factory_name
                        })
            
            # SSOT Requirement: No interface violations
            self.assertEqual(
                len(interface_violations), 0,
                f"FACTORY INTERFACE VIOLATION: Found {len(interface_violations)} interface "
                f"inconsistencies: {interface_violations}. "
                "Factory interfaces should be unified and consistent."
            )

    def test_no_unnecessary_factory_abstraction(self):
        """Test that factory patterns are not over-engineered.
        
        EXPECTED: This test may FAIL initially if over-engineered factories exist.
        After refactor: Should PASS with simplified or eliminated factory patterns.
        """
        factory_classes = self._discover_factory_classes()
        
        # Analyze complexity indicators
        complexity_violations = []
        
        for factory in factory_classes:
            method_count = len(factory["methods"])
            
            # Flag factories with excessive method counts (potential over-engineering)
            if method_count > 10:
                complexity_violations.append({
                    "factory": factory["name"],
                    "file": factory["file_path"],
                    "method_count": method_count,
                    "issue": "excessive_methods"
                })
            
            # Flag factories that might be unnecessary abstractions
            basic_methods = {"create", "get", "build", "__init__"}
            factory_methods = set(factory["methods"])
            
            if factory_methods.issubset(basic_methods.union({"__init__", "__new__"})):
                complexity_violations.append({
                    "factory": factory["name"],
                    "file": factory["file_path"],
                    "issue": "potential_over_abstraction",
                    "methods": factory["methods"]
                })
        
        # SSOT Requirement: No over-engineered factory patterns
        self.assertEqual(
            len(complexity_violations), 0,
            f"FACTORY COMPLEXITY VIOLATION: Found {len(complexity_violations)} "
            f"over-engineered factory patterns: {complexity_violations}. "
            "Factory patterns should be simplified or eliminated if they don't add value."
        )

    def test_factory_dependency_consolidation(self):
        """Test that factory dependencies are consolidated and not circular.
        
        EXPECTED: This test should FAIL initially if dependency violations exist.
        After refactor: Should PASS with clean dependency structure.
        """
        factory_classes = self._discover_factory_classes()
        
        # Check for potential circular dependencies
        dependency_violations = []
        
        for factory in factory_classes:
            file_path = self.codebase_root / factory["file_path"]
            
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Check if factory imports other factories (potential circular dependency)
                other_factories = [f["name"] for f in factory_classes if f["name"] != factory["name"]]
                
                for other_factory in other_factories:
                    if f"from {other_factory}" in content or f"import {other_factory}" in content:
                        dependency_violations.append({
                            "factory": factory["name"],
                            "imports": other_factory,
                            "file": factory["file_path"]
                        })
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # SSOT Requirement: No circular factory dependencies
        self.assertEqual(
            len(dependency_violations), 0,
            f"FACTORY DEPENDENCY VIOLATION: Found {len(dependency_violations)} "
            f"potential circular dependencies: {dependency_violations}. "
            "Factory dependencies should be simplified and not circular."
        )

    def teardown_method(self, method=None):
        """Clean up after test."""
        # Log discovered factory violations for debugging Step 4 refactor
        factory_classes = self._discover_factory_classes()
        if factory_classes:
            print(f"\n=== FACTORY CONSOLIDATION VIOLATIONS ===")
            print(f"Total factory classes found: {len(factory_classes)}")
            for factory in factory_classes:
                print(f"  - {factory['name']} in {factory['file_path']} "
                      f"({len(factory['methods'])} methods)")
            print(f"=== END FACTORY VIOLATIONS ===\n")
        
        super().teardown_method(method)


if __name__ == "__main__":
    # Run tests to demonstrate factory consolidation violations
    unittest.main(verbosity=2)