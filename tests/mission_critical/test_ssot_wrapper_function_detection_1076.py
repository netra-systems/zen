""""

SSOT Wrapper Function Detection Tests for Issue #1076

Test Plan: Detect backward compatibility wrapper functions that create SSOT violations.
Should FAIL initially (detecting violations) and PASS after remediation.

Key violations to detect:
    1. Remaining wrapper functions in auth integration
2. Backward compatibility functions that should be removed
3. Functions that delegate to legacy patterns instead of using SSOT directly

Related Issues: #1076 - SSOT compliance verification
Priority: CRITICAL - These tests protect against regression during SSOT migration
"
""


""""

import pytest
import ast
import os
from pathlib import Path
from typing import List, Dict, Set
import sys
import inspect

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class SSotWrapperFunctionDetectionTests(SSotBaseTestCase):
    "Tests to detect SSOT wrapper function violations that need remediation."

    def setUp(self):
        "Set up test environment."
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.wrapper_violations = []
        self.backward_compatibility_violations = []

    def test_auth_integration_wrapper_detection(self):
        """
        ""

        CRITICAL: Detect wrapper functions in auth integration that bypass SSOT.

        EXPECTED: Should FAIL initially - detects remaining wrapper functions
        REMEDIATION: Remove wrapper functions, use SSOT auth service directly
"
"
        auth_integration_path = self.project_root / netra_backend / app" / auth_integration"

        if not auth_integration_path.exists():
            self.fail(fAuth integration path not found: {auth_integration_path})

        wrapper_functions_found = []

        for py_file in auth_integration_path.glob("*.py):"
            if py_file.name.startswith(__):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                # Look for function definitions that might be wrappers
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name

                        # Check for wrapper patterns
                        if self._is_wrapper_function(node, content):
                            wrapper_functions_found.append({
                                'file': str(py_file),
                                'function': func_name,
                                'line': node.lineno,
                                'reason': 'Wrapper function detected'
                            }

            except Exception as e:
                # Continue processing other files if one fails
                print(fWarning: Could not parse {py_file}: {e}")"
                continue

        # This test should FAIL initially if wrapper functions exist
        if wrapper_functions_found:
            violation_details = \n".join(["
                f  - {v['file']):{v['line']) - {v['function']) ({v['reason'])
                for v in wrapper_functions_found
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(wrapper_functions_found)} wrapper functions in auth integration:\n"
                fSSOT VIOLATION: Found {len(wrapper_functions_found)} wrapper functions in auth integration:\n"
                f"{violation_details}\n\n"
                fREMEDIATION REQUIRED:\n
                f1. Remove wrapper functions\n
                f2. Update callers to use SSOT auth service directly\n""
                f3. Ensure auth_service is the single source of truth for auth operations
            )

    def test_backward_compatibility_function_detection(self):
        pass
        CRITICAL: Detect backward compatibility functions that should be removed.

        EXPECTED: Should FAIL initially - detects remaining backward compatibility
        REMEDIATION: Remove backward compatibility, enforce SSOT patterns
""
        suspicious_patterns = [
            legacy_,
            _legacy","
            backward_compat,
            deprecated_,"
            deprecated_,"
            "_deprecated,"
            fallback_,
            "_fallback,"
            compat_,
            _compat"
            _compat""

        ]

        backward_compat_functions = []

        # Search in key SSOT directories
        search_paths = [
            self.project_root / netra_backend" / app / auth_integration,"
            self.project_root / "netra_backend / app / core,"
            self.project_root / netra_backend / "app / websocket_core,"
            self.project_root / shared
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob(*.py"):"
                if py_file.name.startswith(__):
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            func_name = node.name.lower()

                            # Check for backward compatibility patterns
                            for pattern in suspicious_patterns:
                                if pattern in func_name:
                                    backward_compat_functions.append({
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'function': node.name,
                                        'line': node.lineno,
                                        'pattern': pattern,
                                        'reason': f'Backward compatibility pattern: {pattern}'
                                    }

                except Exception as e:
                    continue

        # This test should FAIL initially if backward compatibility functions exist
        if backward_compat_functions:
            violation_details = \n.join(["
            violation_details = \n.join(["
                f"  - {v['file']):{v['line']) - {v['function']) (pattern: {v['pattern'])"
                for v in backward_compat_functions
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(backward_compat_functions)} backward compatibility functions:\n
                f{violation_details}\n\n
                fREMEDIATION REQUIRED:\n""
                f1. Remove all backward compatibility functions\n
                f2. Update callers to use SSOT patterns directly\n
                f"3. Ensure complete migration to SSOT architecture"
            )

    def test_function_delegation_pattern_detection(self):
        """
        ""

        CRITICAL: Detect functions that delegate to legacy patterns instead of SSOT.

        EXPECTED: Should FAIL initially - detects delegation violations
        REMEDIATION: Update functions to use SSOT directly
"
""

        delegation_violations = []

        # Search for functions that import and delegate to legacy modules
        legacy_import_patterns = [
            "from netra_backend.app.logging_config import,"
            import netra_backend.app.logging_config,
            "from auth_service.legacy import,"
            import auth_service.legacy
        ]

        search_paths = [
            self.project_root / netra_backend / app","
            self.project_root / "auth_service,"
            self.project_root / shared
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob("*.py):"
                if py_file.name.startswith(__):
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for legacy import patterns
                    for pattern in legacy_import_patterns:
                        if pattern in content:
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if pattern in line:
                                    delegation_violations.append({
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'line': i,
                                        'pattern': pattern,
                                        'content': line.strip(),
                                        'reason': 'Legacy import delegation'
                                    }

                except Exception as e:
                    continue

        # This test should FAIL initially if delegation violations exist
        if delegation_violations:
            violation_details = \n.join(["
            violation_details = \n.join(["
                f  - {v['file']):{v['line']) - {v['content']) (pattern: {v['pattern'])"
                f  - {v['file']):{v['line']) - {v['content']) (pattern: {v['pattern'])""

                for v in delegation_violations
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(delegation_violations)} function delegation violations:\n
                f{violation_details}\n\n"
                f{violation_details}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f1. Replace legacy imports with SSOT imports\n
                f2. Update function implementations to use SSOT directly\n
                f3. Remove all delegation to legacy modules""
            )

    def test_duplicate_function_implementation_detection(self):
        pass
        CRITICAL: Detect duplicate function implementations across services.

        EXPECTED: Should FAIL initially - detects duplicate implementations
        REMEDIATION: Consolidate to single SSOT implementation per function
        ""
        function_signatures = {}
        duplicate_implementations = []

        # Search in all Python files
        for py_file in self.project_root.rglob(*.py):
            if any(skip in str(py_file) for skip in [
                __pycache__, .git", venv, node_modules,"
                tests/, test_, "_test"
            ]:
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Create a signature based on function name and parameters
                        func_name = node.name
                        params = [arg.arg for arg in node.args.args]
                        signature = f{func_name}({', '.join(params)}

                        # Skip common/generic function names
                        if func_name in ['__init__', '__str__', '__repr__', 'setup', 'teardown']:
                            continue

                        if signature in function_signatures:
                            # Found duplicate implementation
                            existing_file = function_signatures[signature]
                            current_file = str(py_file.relative_to(self.project_root))

                            if existing_file != current_file:
                                duplicate_implementations.append({
                                    'signature': signature,
                                    'file1': existing_file,
                                    'file2': current_file,
                                    'function': func_name
                                }
                        else:
                            function_signatures[signature] = str(py_file.relative_to(self.project_root))

            except Exception as e:
                continue

        # Filter duplicates to focus on business logic (not test/utility functions)
        business_duplicates = [
            dup for dup in duplicate_implementations
            if not any(skip in dup['file1'].lower() or skip in dup['file2'].lower()
                      for skip in ['test', 'mock', 'fixture', 'util']
        ]

        # This test should FAIL initially if business logic duplicates exist
        if business_duplicates:
            violation_details = \n.join(["
            violation_details = \n.join(["
                f  - {dup['function']}: {dup['file1']} vs {dup['file2']}"
                f  - {dup['function']}: {dup['file1']} vs {dup['file2']}""

                for dup in business_duplicates[:10]  # Limit output
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(business_duplicates)} duplicate function implementations:\n
                f{violation_details}\n"
                f{violation_details}\n"
                f"{'... and more' if len(business_duplicates) > 10 else ''}\n\n"
                fREMEDIATION REQUIRED:\n
                f1. Consolidate duplicate implementations to single SSOT location\n
                f2. Update all callers to use SSOT implementation\n""
                f3. Remove duplicate implementations
            )

    def _is_wrapper_function(self, node: ast.FunctionDef, content: str) -> bool:
        Check if a function appears to be a wrapper function.""
        # Get the function body as string
        func_lines = content.split('\n')[node.lineno-1:node.end_lineno]
        func_body = '\n'.join(func_lines)

        # Wrapper function indicators
        wrapper_indicators = [
            'return ' and len(node.body) <= 3,  # Simple wrapper with return
            'jwt.decode' in func_body and 'auth_service' not in func_body,  # JWT wrapper
            'validate_token' in node.name and len(node.body) <= 2,  # Token validation wrapper
            '_wrapper' in node.name.lower(),  # Explicitly named wrapper
            'def get_' in func_body and 'return config' in func_body  # Config getter wrapper
        ]

        return any(wrapper_indicators)


if __name__ == '__main__':
    pytest.main([__file__, '-v')
)))))))))))))))))))
]]]