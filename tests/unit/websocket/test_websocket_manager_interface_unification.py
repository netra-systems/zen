"""
WebSocket Manager Interface Unification Validation Test

This test file validates that WebSocket manager interfaces are unified and consistent
across all implementations in the codebase.

EXPECTED BEHAVIOR: These tests should FAIL initially to prove interface fragmentation exists.
After SSOT refactor (Step 4), they should PASS with unified interfaces.

Business Value: Platform/Internal - Interface Consistency & API Design
Ensures WebSocket manager interfaces are consistent, preventing integration errors.

Test Strategy: Static analysis of class interfaces and method signatures.
NO DOCKER required - pure Python AST parsing and interface inspection.
"""

import ast
import inspect
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any, Optional
import unittest
from collections import defaultdict

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketManagerInterfaceUnification(SSotBaseTestCase, unittest.TestCase):
    """Test suite to validate interface unification for WebSocket managers.
    
    These tests should FAIL initially, proving fragmented interfaces exist.
    After refactor, they should PASS with unified, consistent interfaces.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.codebase_root = Path(__file__).parent.parent.parent.parent
        self.manager_interfaces = {}
        self.interface_violations = []
        self.method_signatures = {}

    def _extract_class_interface(self, file_path: Path, class_name: str) -> Optional[Dict[str, Any]]:
        """Extract interface information from a class.
        
        Args:
            file_path: Path to the Python file
            class_name: Name of the class to analyze
            
        Returns:
            Dict containing interface information or None if not found
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    interface_info = {
                        "class_name": class_name,
                        "file_path": str(file_path.relative_to(self.codebase_root)),
                        "methods": {},
                        "properties": [],
                        "base_classes": [],
                        "async_methods": []
                    }
                    
                    # Extract base classes
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            interface_info["base_classes"].append(base.id)
                        elif isinstance(base, ast.Attribute):
                            interface_info["base_classes"].append(ast.unparse(base))
                    
                    # Extract methods and their signatures
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = self._extract_method_signature(item)
                            interface_info["methods"][item.name] = method_info
                            
                            # Track async methods
                            if isinstance(item, ast.AsyncFunctionDef):
                                interface_info["async_methods"].append(item.name)
                        
                        elif isinstance(item, ast.AsyncFunctionDef):
                            method_info = self._extract_method_signature(item)
                            interface_info["methods"][item.name] = method_info
                            interface_info["async_methods"].append(item.name)
                    
                    return interface_info
                    
        except (UnicodeDecodeError, PermissionError, SyntaxError):
            return None
        
        return None

    def _extract_method_signature(self, method_node: ast.FunctionDef) -> Dict[str, Any]:
        """Extract method signature information.
        
        Args:
            method_node: AST node for the method
            
        Returns:
            Dict containing method signature information
        """
        signature_info = {
            "args": [],
            "return_annotation": None,
            "is_async": isinstance(method_node, ast.AsyncFunctionDef),
            "is_property": False,
            "is_classmethod": False,
            "is_staticmethod": False
        }
        
        # Extract arguments
        for arg in method_node.args.args:
            arg_info = {"name": arg.arg}
            if arg.annotation:
                arg_info["annotation"] = ast.unparse(arg.annotation)
            signature_info["args"].append(arg_info)
        
        # Extract return annotation
        if method_node.returns:
            signature_info["return_annotation"] = ast.unparse(method_node.returns)
        
        # Check for decorators
        for decorator in method_node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == "property":
                    signature_info["is_property"] = True
                elif decorator.id == "classmethod":
                    signature_info["is_classmethod"] = True
                elif decorator.id == "staticmethod":
                    signature_info["is_staticmethod"] = True
        
        return signature_info

    def _discover_websocket_manager_interfaces(self) -> Dict[str, Dict[str, Any]]:
        """Discover all WebSocket manager interfaces.
        
        Returns:
            Dict mapping class names to their interface information
        """
        interfaces = {}
        
        # Manager class patterns to look for
        manager_patterns = [
            "UnifiedWebSocketManager",
            "IsolatedWebSocketManager", 
            "WebSocketConnectionManager",
            "WebSocketManager",
            "EmergencyWebSocketManager",
            "DegradedWebSocketManager",
            "ConnectionManager"
        ]
        
        # Search in WebSocket modules
        websocket_paths = [
            self.codebase_root / "netra_backend" / "app" / "websocket_core",
            self.codebase_root / "netra_backend" / "app" / "websocket"
        ]
        
        for websocket_path in websocket_paths:
            if websocket_path.exists():
                for py_file in websocket_path.rglob("*.py"):
                    if py_file.name.startswith("__"):
                        continue
                    
                    for pattern in manager_patterns:
                        interface_info = self._extract_class_interface(py_file, pattern)
                        if interface_info:
                            interfaces[pattern] = interface_info
        
        return interfaces

    def _analyze_interface_consistency(self) -> List[Dict[str, Any]]:
        """Analyze interface consistency across WebSocket managers.
        
        Returns:
            List of interface violations found
        """
        interfaces = self._discover_websocket_manager_interfaces()
        violations = []
        
        if len(interfaces) <= 1:
            return violations  # No violations if only one interface exists
        
        # Group interfaces by expected functionality
        manager_interfaces = list(interfaces.values())
        
        # Core methods that should be consistent across all managers
        core_methods = {
            "connect", "disconnect", "send_message", "handle_message",
            "add_connection", "remove_connection", "get_connection",
            "broadcast", "send_to_user", "is_connected"
        }
        
        # Find method signature inconsistencies
        method_signatures = defaultdict(list)
        
        for interface in manager_interfaces:
            for method_name, method_info in interface["methods"].items():
                if method_name in core_methods:
                    signature_key = self._create_signature_key(method_info)
                    method_signatures[method_name].append({
                        "class": interface["class_name"],
                        "file": interface["file_path"],
                        "signature": signature_key,
                        "is_async": method_info["is_async"]
                    })
        
        # Check for signature inconsistencies
        for method_name, signatures in method_signatures.items():
            if len(signatures) > 1:
                unique_signatures = set(sig["signature"] for sig in signatures)
                if len(unique_signatures) > 1:
                    violations.append({
                        "type": "method_signature_inconsistency",
                        "method": method_name,
                        "signatures": signatures
                    })
        
        return violations

    def _create_signature_key(self, method_info: Dict[str, Any]) -> str:
        """Create a signature key for comparison.
        
        Args:
            method_info: Method information dict
            
        Returns:
            String representation of the method signature
        """
        args = [arg["name"] for arg in method_info["args"]]
        arg_types = [arg.get("annotation", "Any") for arg in method_info["args"]]
        return_type = method_info.get("return_annotation", "Any")
        
        signature_parts = [
            f"args:{','.join(args)}",
            f"types:{','.join(arg_types)}",
            f"return:{return_type}",
            f"async:{method_info['is_async']}"
        ]
        
        return "|".join(signature_parts)

    def _find_missing_core_methods(self) -> List[Dict[str, Any]]:
        """Find core methods missing from manager interfaces.
        
        Returns:
            List of missing method violations
        """
        interfaces = self._discover_websocket_manager_interfaces()
        violations = []
        
        # Core methods that should exist in all WebSocket managers
        required_core_methods = {
            "connect", "disconnect", "send_message", "handle_message",
            "add_connection", "remove_connection"
        }
        
        for class_name, interface in interfaces.items():
            existing_methods = set(interface["methods"].keys())
            missing_methods = required_core_methods - existing_methods
            
            if missing_methods:
                violations.append({
                    "type": "missing_core_methods",
                    "class": class_name,
                    "file": interface["file_path"],
                    "missing_methods": list(missing_methods)
                })
        
        return violations

    def test_websocket_manager_interface_consistency(self):
        """Test that WebSocket manager interfaces are consistent.
        
        EXPECTED: This test should FAIL initially - inconsistent interfaces exist.
        After refactor: Should PASS with consistent interfaces.
        """
        violations = self._analyze_interface_consistency()
        
        # SSOT Requirement: No interface inconsistencies
        self.assertEqual(
            len(violations), 0,
            f"INTERFACE CONSISTENCY VIOLATION: Found {len(violations)} interface "
            f"inconsistencies across WebSocket managers: {violations}. "
            "All WebSocket manager interfaces should be consistent."
        )

    def test_core_method_completeness(self):
        """Test that all WebSocket managers implement core methods.
        
        EXPECTED: This test should FAIL initially if core methods are missing.
        After refactor: Should PASS with complete core method implementation.
        """
        missing_method_violations = self._find_missing_core_methods()
        
        # SSOT Requirement: All managers should have core methods
        self.assertEqual(
            len(missing_method_violations), 0,
            f"CORE METHOD VIOLATION: Found {len(missing_method_violations)} managers "
            f"with missing core methods: {missing_method_violations}. "
            "All WebSocket managers should implement the complete core interface."
        )

    def test_async_method_consistency(self):
        """Test that async method usage is consistent across managers.
        
        EXPECTED: This test should FAIL initially if async inconsistencies exist.
        After refactor: Should PASS with consistent async patterns.
        """
        interfaces = self._discover_websocket_manager_interfaces()
        violations = []
        
        # Find async method inconsistencies
        method_async_status = defaultdict(set)
        
        for interface in interfaces.values():
            for method_name, method_info in interface["methods"].items():
                is_async = method_info["is_async"]
                method_async_status[method_name].add((interface["class_name"], is_async))
        
        # Check for methods that are async in some classes but not others
        for method_name, async_status_set in method_async_status.items():
            if len(async_status_set) > 1:
                async_values = set(status[1] for status in async_status_set)
                if len(async_values) > 1:  # Both True and False present
                    violations.append({
                        "method": method_name,
                        "inconsistent_async": list(async_status_set)
                    })
        
        # SSOT Requirement: Consistent async method usage
        self.assertEqual(
            len(violations), 0,
            f"ASYNC CONSISTENCY VIOLATION: Found {len(violations)} methods with "
            f"inconsistent async usage: {violations}. "
            "Async method usage should be consistent across all managers."
        )

    def test_base_class_unification(self):
        """Test that base classes are unified across WebSocket managers.
        
        EXPECTED: This test should FAIL initially if fragmented inheritance exists.
        After refactor: Should PASS with unified base class hierarchy.
        """
        interfaces = self._discover_websocket_manager_interfaces()
        violations = []
        
        # Analyze base class patterns
        base_class_patterns = defaultdict(list)
        
        for interface in interfaces.values():
            base_classes = tuple(sorted(interface["base_classes"]))
            base_class_patterns[base_classes].append(interface["class_name"])
        
        # Check for multiple inheritance patterns (potential fragmentation)
        if len(base_class_patterns) > 2:  # Allow for some variation, but not excessive
            violations.append({
                "type": "fragmented_inheritance",
                "patterns": dict(base_class_patterns)
            })
        
        # Check for inconsistent protocol implementation
        protocol_implementations = []
        for interface in interfaces.values():
            for base_class in interface["base_classes"]:
                if "Protocol" in base_class:
                    protocol_implementations.append({
                        "class": interface["class_name"],
                        "protocol": base_class
                    })
        
        # All managers should implement the same protocol (if any)
        if protocol_implementations:
            protocols = set(impl["protocol"] for impl in protocol_implementations)
            if len(protocols) > 1:
                violations.append({
                    "type": "inconsistent_protocol_implementation",
                    "protocols": list(protocols),
                    "implementations": protocol_implementations
                })
        
        # SSOT Requirement: Unified base class hierarchy
        self.assertEqual(
            len(violations), 0,
            f"BASE CLASS VIOLATION: Found {len(violations)} base class "
            f"inconsistencies: {violations}. "
            "Base class hierarchy should be unified across WebSocket managers."
        )

    def test_method_naming_consistency(self):
        """Test that method naming is consistent across managers.
        
        EXPECTED: This test should FAIL initially if naming inconsistencies exist.
        After refactor: Should PASS with consistent naming conventions.
        """
        interfaces = self._discover_websocket_manager_interfaces()
        violations = []
        
        # Common method name variations that should be standardized
        method_variations = {
            "connection": ["connect", "create_connection", "establish_connection"],
            "disconnection": ["disconnect", "close_connection", "terminate_connection"],
            "message_sending": ["send_message", "send", "emit", "publish"],
            "message_handling": ["handle_message", "process_message", "on_message"],
            "user_messaging": ["send_to_user", "message_user", "notify_user"]
        }
        
        # Find naming inconsistencies
        for category, variations in method_variations.items():
            methods_found = defaultdict(list)
            
            for interface in interfaces.values():
                for method_name in interface["methods"]:
                    if method_name in variations:
                        methods_found[method_name].append(interface["class_name"])
            
            # If multiple variations of the same concept exist, it's a violation
            if len(methods_found) > 1:
                violations.append({
                    "category": category,
                    "variations_found": dict(methods_found)
                })
        
        # SSOT Requirement: Consistent method naming
        self.assertEqual(
            len(violations), 0,
            f"METHOD NAMING VIOLATION: Found {len(violations)} naming "
            f"inconsistencies: {violations}. "
            "Method naming should be consistent across WebSocket managers."
        )

    def teardown_method(self, method=None):
        """Clean up after test."""
        # Log discovered interface violations for debugging Step 4 refactor
        interfaces = self._discover_websocket_manager_interfaces()
        if interfaces:
            print(f"\n=== INTERFACE UNIFICATION VIOLATIONS ===")
            print(f"Total manager interfaces found: {len(interfaces)}")
            for class_name, interface in interfaces.items():
                method_count = len(interface["methods"])
                async_count = len(interface["async_methods"])
                print(f"  - {class_name} in {interface['file_path']} "
                      f"({method_count} methods, {async_count} async)")
            print(f"=== END INTERFACE VIOLATIONS ===\n")
        
        super().teardown_method(method)


if __name__ == "__main__":
    # Run tests to demonstrate interface unification violations
    unittest.main(verbosity=2)