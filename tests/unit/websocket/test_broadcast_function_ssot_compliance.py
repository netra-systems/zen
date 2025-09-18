"""
Test Suite: SSOT Compliance Detection for Broadcast Functions (Issue #982)

This test suite detects duplicate broadcast function implementations that violate
SSOT principles and block Golden Path functionality.

Business Value Justification:
- Segment: Platform/Core Infrastructure
- Business Goal: $500K+ ARR Protection through SSOT Compliance
- Value Impact: Prevent cross-user event leakage and Golden Path blocking
- Strategic Impact: Ensure secure, reliable WebSocket event broadcasting

Test Strategy: Static analysis and dynamic discovery of broadcast function duplicates
Expected Behavior: All tests should FAIL initially, then PASS after SSOT remediation

GitHub Issue: https://github.com/netra-systems/netra-apex/issues/982
"""

import pytest
import ast
import inspect
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass
import unittest
import sys
import os

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class BroadcastFunction:
    """Information about a discovered broadcast function."""
    name: str
    module_path: str
    class_name: Optional[str]
    signature: str
    line_number: int
    parameters: List[str]
    return_type: Optional[str]
    docstring: Optional[str]

    @property
    def full_identifier(self) -> str:
        """Get full identifier for this function."""
        if self.class_name:
            return f"{self.module_path}:{self.class_name}.{self.name}"
        return f"{self.module_path}:{self.name}"


class BroadcastFunctionDiscovery:
    """Static analysis tool to discover broadcast function implementations."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.discovered_functions: List[BroadcastFunction] = []

    def scan_for_broadcast_functions(self) -> List[BroadcastFunction]:
        """Scan project for broadcast function implementations."""
        self.discovered_functions = []

        # Target directories for scanning
        scan_dirs = [
            self.project_root / "netra_backend" / "app" / "services",
            self.project_root / "netra_backend" / "app" / "websocket_core",
            self.project_root / "netra_backend" / "app" / "agents",
            self.project_root / "shared",
        ]

        for scan_dir in scan_dirs:
            if scan_dir.exists():
                self._scan_directory(scan_dir)

        return self.discovered_functions

    def _scan_directory(self, directory: Path):
        """Recursively scan directory for Python files."""
        for py_file in directory.rglob("*.py"):
            if py_file.name.startswith("test_"):
                continue  # Skip test files
            self._scan_file(py_file)

    def _scan_file(self, file_path: Path):
        """Scan individual Python file for broadcast functions."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            relative_path = file_path.relative_to(self.project_root)

            # First try AST parsing
            try:
                tree = ast.parse(content)
                self._scan_ast_tree(tree, str(relative_path))
            except SyntaxError:
                # If AST fails, try regex-based scanning
                self._scan_with_regex(content, str(relative_path))

        except Exception as e:
            # Skip files that can't be parsed
            pass

    def _scan_ast_tree(self, tree: ast.AST, relative_path: str):
        """Scan AST tree for broadcast functions."""
        # Scan for function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self._is_broadcast_function(node):
                    func_info = self._extract_function_info(node, relative_path, None)
                    self.discovered_functions.append(func_info)

            elif isinstance(node, ast.ClassDef):
                # Scan class methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if self._is_broadcast_function(item):
                            func_info = self._extract_function_info(item, relative_path, node.name)
                            self.discovered_functions.append(func_info)

    def _scan_with_regex(self, content: str, relative_path: str):
        """Fallback regex-based scanning for broadcast functions."""
        import re
        lines = content.split('\n')

        # Pattern for async/sync methods and functions
        patterns = [
            r'async\s+def\s+(broadcast_to_user|broadcast_user_event)\s*\(',
            r'def\s+(broadcast_to_user|broadcast_user_event)\s*\(',
        ]

        current_class = None
        for line_num, line in enumerate(lines, 1):
            # Track class context
            class_match = re.match(r'class\s+(\w+)', line.strip())
            if class_match:
                current_class = class_match.group(1)
                continue

            # Check for broadcast functions
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    func_name = match.group(1)
                    # Extract basic parameter info from the line
                    params_match = re.search(r'\((.*?)\)', line)
                    parameters = []
                    if params_match:
                        param_str = params_match.group(1)
                        if param_str.strip():
                            # Simple parameter parsing
                            parameters = [p.strip().split(':')[0].strip()
                                        for p in param_str.split(',') if p.strip()]

                    func_info = BroadcastFunction(
                        name=func_name,
                        module_path=relative_path,
                        class_name=current_class,
                        signature=f"{func_name}({', '.join(parameters)})",
                        line_number=line_num,
                        parameters=parameters,
                        return_type=None,
                        docstring=None
                    )
                    self.discovered_functions.append(func_info)
                    break

    def _is_broadcast_function(self, node: ast.FunctionDef) -> bool:
        """Check if function node is a broadcast function."""
        # Look for broadcast-related function names
        broadcast_patterns = [
            "broadcast_to_user",
            "broadcast_user_event",
            "broadcast_event",
            "send_broadcast",
            "emit_broadcast",
            "broadcast_to_users"  # Additional pattern
        ]

        # Direct name match (more specific)
        return node.name in broadcast_patterns or any(pattern in node.name.lower() for pattern in broadcast_patterns)

    def _extract_function_info(self, node: ast.FunctionDef, module_path: str, class_name: Optional[str]) -> BroadcastFunction:
        """Extract information about a function node."""
        # Get parameter names
        parameters = []
        for arg in node.args.args:
            parameters.append(arg.arg)

        # Get signature (simplified)
        signature = f"{node.name}({', '.join(parameters)})"

        # Get return type if annotated
        return_type = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return_type = node.returns.id
            elif isinstance(node.returns, ast.Constant):
                return_type = str(node.returns.value)

        # Get docstring
        docstring = None
        if (node.body and
            isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value.strip()

        return BroadcastFunction(
            name=node.name,
            module_path=module_path,
            class_name=class_name,
            signature=signature,
            line_number=node.lineno,
            parameters=parameters,
            return_type=return_type,
            docstring=docstring
        )


@pytest.mark.unit
class BroadcastFunctionSSotComplianceTests(SSotBaseTestCase):
    """Test suite for broadcast function SSOT compliance detection."""

    def _get_broadcast_functions(self):
        """Get broadcast functions."""
        if not hasattr(self, '_broadcast_functions_cache'):
            project_root = Path(__file__).parent.parent.parent.parent
            discovery = BroadcastFunctionDiscovery(project_root)
            self._broadcast_functions_cache = discovery.scan_for_broadcast_functions()
        return self._broadcast_functions_cache

    def test_discover_all_broadcast_functions(self):
        """
        Discover all broadcast functions to ensure SSOT compliance.

        Expected Behavior: FAIL - Should detect 3+ duplicate functions
        After SSOT remediation: PASS - Should find exactly 1 canonical function
        """
        # This test should FAIL initially with 3+ functions found
        # After SSOT remediation, should PASS with exactly 1 function

        broadcast_functions = self._get_broadcast_functions()

        print(f"\n=== BROADCAST FUNCTION DISCOVERY ===")
        print(f"Total broadcast functions discovered: {len(broadcast_functions)}")

        if len(broadcast_functions) == 0:
            # Debug: Let's see what files were scanned
            project_root = Path(__file__).parent.parent.parent.parent
            target_files = [
                project_root / "netra_backend" / "app" / "services" / "websocket_event_router.py",
                project_root / "netra_backend" / "app" / "services" / "user_scoped_websocket_event_router.py"
            ]

            print("\nDebug: Checking specific target files:")
            for file_path in target_files:
                if file_path.exists():
                    print(f"  CHECK {file_path} exists")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        if "broadcast_to_user" in content:
                            print(f"    - Contains 'broadcast_to_user'")
                        if "broadcast_user_event" in content:
                            print(f"    - Contains 'broadcast_user_event'")
                    except Exception as e:
                        print(f"    - Error reading file: {e}")
                else:
                    print(f"  ✗ {file_path} does not exist")

        for func in broadcast_functions:
            print(f"- {func.full_identifier} (line {func.line_number})")
            print(f"  Signature: {func.signature}")
            if func.docstring:
                print(f"  Doc: {func.docstring[:100]}...")
            print()

        # Identify the specific duplicate functions we're looking for
        expected_duplicates = [
            "websocket_event_router.py:WebSocketEventRouter.broadcast_to_user",
            "user_scoped_websocket_event_router.py:UserScopedWebSocketEventRouter.broadcast_to_user",
            "user_scoped_websocket_event_router.py:broadcast_user_event"
        ]

        found_duplicates = []
        for func in broadcast_functions:
            # Check if this function matches our expected duplicates
            module_name = func.module_path.split('/')[-1] if '/' in func.module_path else func.module_path.split('\\')[-1]
            if func.class_name:
                identifier = f"{module_name}:{func.class_name}.{func.name}"
            else:
                identifier = f"{module_name}:{func.name}"

            for expected in expected_duplicates:
                if expected.endswith(identifier):
                    found_duplicates.append(func)
                    break

        print(f"Expected duplicate functions found: {len(found_duplicates)}")
        for func in found_duplicates:
            print(f"  - {func.full_identifier}")

        # ASSERTION: Should find the 3 specific duplicate functions
        # This test SHOULD FAIL initially (indicating duplicates exist)
        # After SSOT remediation, this should PASS (only 1 canonical function)

        if len(broadcast_functions) <= 1:
            # SSOT remediation complete - single canonical function
            self.assertEqual(len(broadcast_functions), 1,
                           "SSOT remediation complete: Should have exactly 1 canonical broadcast function")
        else:
            # Pre-SSOT remediation - multiple duplicates detected
            self.fail(f"SSOT VIOLATION: Found {len(broadcast_functions)} broadcast functions. "
                     f"Expected duplicates: {len(found_duplicates)}. "
                     f"This violates SSOT principles and blocks Golden Path functionality. "
                     f"Remediation required to consolidate to single canonical function.")

    def test_broadcast_function_signature_consistency(self):
        """
        Ensure all broadcast functions have consistent signatures.

        Expected Behavior: FAIL - Different signatures detected
        After SSOT remediation: PASS - Single consistent signature
        """
        broadcast_functions = self._get_broadcast_functions()

        if len(broadcast_functions) <= 1:
            self.skipTest("SSOT remediation complete - single function, signature consistency not applicable")

        print(f"\n=== SIGNATURE CONSISTENCY ANALYSIS ===")

        # Group functions by signature patterns
        signature_groups: Dict[str, List[BroadcastFunction]] = {}

        for func in broadcast_functions:
            # Normalize signature for comparison
            normalized_sig = self._normalize_signature(func.parameters)

            if normalized_sig not in signature_groups:
                signature_groups[normalized_sig] = []
            signature_groups[normalized_sig].append(func)

        print(f"Signature groups found: {len(signature_groups)}")
        for sig, funcs in signature_groups.items():
            print(f"  Signature pattern: {sig}")
            for func in funcs:
                print(f"    - {func.full_identifier}")
            print()

        # ASSERTION: Should have inconsistent signatures (indicating SSOT violation)
        # This test SHOULD FAIL initially
        self.fail(f"SSOT SIGNATURE VIOLATION: Found {len(signature_groups)} different signature patterns. "
                 f"Broadcast functions have inconsistent interfaces: {list(signature_groups.keys())}. "
                 f"This creates unpredictable behavior and violates SSOT principles. "
                 f"Consolidation to single canonical signature required.")

    def test_no_duplicate_implementations(self):
        """
        Verify no duplicate broadcast logic exists.

        Expected Behavior: FAIL - Multiple implementations found
        After SSOT remediation: PASS - Single implementation
        """
        print(f"\n=== DUPLICATE IMPLEMENTATION ANALYSIS ===")

        broadcast_functions = self._get_broadcast_functions()

        # Check for duplicate logic patterns
        implementations = {}

        for func in broadcast_functions:
            # Categorize implementation by context
            if "WebSocketEventRouter" in func.full_identifier and func.name == "broadcast_to_user":
                implementations["singleton_router"] = func
            elif "UserScopedWebSocketEventRouter" in func.full_identifier and func.name == "broadcast_to_user":
                implementations["scoped_router"] = func
            elif func.name == "broadcast_user_event":
                implementations["convenience_function"] = func
            else:
                implementations[f"other_{func.name}"] = func

        print(f"Implementation patterns found: {len(implementations)}")
        for pattern, func in implementations.items():
            print(f"  {pattern}: {func.full_identifier}")

        # ASSERTION: Should find multiple implementations (SSOT violation)
        # This test SHOULD FAIL initially
        if len(implementations) <= 1:
            self.assertEqual(len(implementations), 1,
                           "SSOT remediation complete: Single broadcast implementation found")
        else:
            self.fail(f"SSOT IMPLEMENTATION VIOLATION: Found {len(implementations)} different broadcast implementations. "
                     f"Patterns: {list(implementations.keys())}. "
                     f"Multiple implementations create maintenance burden, inconsistent behavior, "
                     f"and potential cross-user event leakage. Single canonical implementation required.")

    def test_canonical_broadcast_function_exists(self):
        """
        Verify canonical broadcast function is properly defined.

        Expected Behavior: FAIL initially, PASS after SSOT remediation
        """
        print(f"\n=== CANONICAL FUNCTION VALIDATION ===")

        broadcast_functions = self._get_broadcast_functions()

        if len(broadcast_functions) == 0:
            self.fail("NO BROADCAST FUNCTION: No broadcast functions found. "
                     "System requires at least one canonical broadcast function for WebSocket events.")

        if len(broadcast_functions) > 1:
            self.fail(f"MULTIPLE IMPLEMENTATIONS: Found {len(broadcast_functions)} broadcast functions. "
                     f"SSOT requires exactly one canonical implementation.")

        # Single function found - validate it's properly canonical
        canonical_func = broadcast_functions[0]

        print(f"Canonical function: {canonical_func.full_identifier}")
        print(f"Signature: {canonical_func.signature}")
        print(f"Module: {canonical_func.module_path}")

        # Validate canonical function properties
        self.assertIsNotNone(canonical_func.docstring,
                           "Canonical broadcast function must have documentation")

        # Check for required parameters
        required_params = ["user_id", "event"]
        missing_params = [param for param in required_params
                         if not any(param in p for p in canonical_func.parameters)]

        if missing_params:
            self.fail(f"Canonical function missing required parameters: {missing_params}. "
                     f"Current parameters: {canonical_func.parameters}")

        print("CHECK Canonical broadcast function validation complete")

    def _normalize_signature(self, parameters: List[str]) -> str:
        """Normalize function signature for comparison."""
        # Remove 'self' parameter for methods
        filtered_params = [p for p in parameters if p != 'self']

        # Sort parameters to handle order differences
        # Keep first parameter in place (usually the main identifier)
        if filtered_params:
            first_param = filtered_params[0]
            other_params = sorted(filtered_params[1:])
            normalized = [first_param] + other_params
        else:
            normalized = []

        return f"({', '.join(normalized)})"


@pytest.mark.unit
class BroadcastFunctionDiscoveryTests(SSotBaseTestCase):
    """Test suite for broadcast function discovery and analysis."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent.parent

    def test_static_code_analysis_broadcast_functions(self):
        """
        Use static analysis to discover all broadcast implementations.

        Expected Behavior: FAIL - Detects 3+ duplicate functions
        After SSOT remediation: PASS - Single canonical function
        """
        discovery = BroadcastFunctionDiscovery(self.project_root)
        functions = discovery.scan_for_broadcast_functions()

        print(f"\n=== STATIC CODE ANALYSIS ===")
        print(f"Broadcast functions discovered: {len(functions)}")

        # Detailed analysis of each function
        analysis = {
            "total_functions": len(functions),
            "modules_with_broadcast": set(),
            "classes_with_broadcast": set(),
            "standalone_functions": 0,
            "method_functions": 0
        }

        for func in functions:
            module_name = func.module_path.split('/')[-1] if '/' in func.module_path else func.module_path.split('\\')[-1]
            analysis["modules_with_broadcast"].add(module_name)

            if func.class_name:
                analysis["classes_with_broadcast"].add(f"{module_name}:{func.class_name}")
                analysis["method_functions"] += 1
            else:
                analysis["standalone_functions"] += 1

        print(f"Analysis results:")
        print(f"  - Total functions: {analysis['total_functions']}")
        print(f"  - Modules with broadcast: {len(analysis['modules_with_broadcast'])}")
        print(f"  - Classes with broadcast: {len(analysis['classes_with_broadcast'])}")
        print(f"  - Standalone functions: {analysis['standalone_functions']}")
        print(f"  - Method functions: {analysis['method_functions']}")

        # Expected violation detection
        expected_issues = []

        # Check for specific known duplicates
        websocket_router_found = False
        user_scoped_router_found = False
        convenience_function_found = False

        for func in functions:
            if "websocket_event_router" in func.module_path and func.name == "broadcast_to_user":
                websocket_router_found = True
            elif "user_scoped_websocket_event_router" in func.module_path and func.name == "broadcast_to_user":
                user_scoped_router_found = True
            elif func.name == "broadcast_user_event":
                convenience_function_found = True

        if websocket_router_found:
            expected_issues.append("WebSocketEventRouter.broadcast_to_user")
        if user_scoped_router_found:
            expected_issues.append("UserScopedWebSocketEventRouter.broadcast_to_user")
        if convenience_function_found:
            expected_issues.append("broadcast_user_event function")

        print(f"Expected SSOT violations detected: {len(expected_issues)}")
        for issue in expected_issues:
            print(f"  - {issue}")

        # ASSERTION: Static analysis should detect violations
        if analysis["total_functions"] <= 1:
            # SSOT remediation successful
            self.assertEqual(analysis["total_functions"], 1,
                           "SSOT remediation complete: Single canonical broadcast function")
        else:
            # Pre-SSOT remediation - violations detected
            self.fail(f"STATIC ANALYSIS VIOLATION: Discovered {analysis['total_functions']} broadcast functions. "
                     f"Expected violations found: {expected_issues}. "
                     f"SSOT principles require single canonical implementation. "
                     f"Multiple implementations risk cross-user event leakage and Golden Path failures.")

    def test_import_path_analysis_broadcast(self):
        """
        Analyze import paths for broadcast function access.

        Expected Behavior: FAIL - Multiple import paths for broadcast functionality
        After SSOT remediation: PASS - Single canonical import path
        """
        print(f"\n=== IMPORT PATH ANALYSIS ===")

        # Scan for import statements that access broadcast functions
        import_patterns = []

        # Search common import locations
        search_dirs = [
            self.project_root / "netra_backend",
            self.project_root / "tests",
            self.project_root / "shared"
        ]

        broadcast_imports = []

        for search_dir in search_dirs:
            if search_dir.exists():
                for py_file in search_dir.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Look for broadcast-related imports
                        lines = content.split('\n')
                        for line_num, line in enumerate(lines, 1):
                            line = line.strip()
                            if ('import' in line and
                                ('broadcast' in line.lower() or
                                 'websocket_event_router' in line or
                                 'user_scoped_websocket' in line)):

                                relative_path = py_file.relative_to(self.project_root)
                                broadcast_imports.append({
                                    "file": str(relative_path),
                                    "line": line_num,
                                    "import_statement": line
                                })
                    except:
                        continue

        print(f"Broadcast-related imports found: {len(broadcast_imports)}")

        # Group by import patterns
        import_modules = set()
        for imp in broadcast_imports:
            import_modules.add(imp["import_statement"])

        print(f"Unique import patterns: {len(import_modules)}")
        for pattern in sorted(import_modules):
            print(f"  - {pattern}")

        # Count imports by target module
        module_counts = {}
        for imp in broadcast_imports:
            statement = imp["import_statement"]
            if "websocket_event_router" in statement:
                module_counts["websocket_event_router"] = module_counts.get("websocket_event_router", 0) + 1
            if "user_scoped_websocket_event_router" in statement:
                module_counts["user_scoped_websocket_event_router"] = module_counts.get("user_scoped_websocket_event_router", 0) + 1

        print(f"Import counts by module:")
        for module, count in module_counts.items():
            print(f"  - {module}: {count} imports")

        # ASSERTION: Should detect multiple import paths (SSOT violation)
        if len(import_modules) <= 2:  # Allow some flexibility for test imports
            print("CHECK Reasonable number of import patterns found")
        else:
            self.fail(f"IMPORT PATH VIOLATION: Found {len(import_modules)} different import patterns "
                     f"for broadcast functionality. Multiple import paths indicate SSOT violation. "
                     f"Should consolidate to single canonical import path after SSOT remediation.")


if __name__ == "__main__":
    unittest.main()