#!/usr/bin/env python3
"""
Issue #1186 SSOT Violation Reproduction Test
=============================================

This script reproduces the specific SSOT violations detected by the comprehensive
test execution for Issue #1186 UserExecutionEngine SSOT Consolidation.

Purpose: Demonstrate current violations exist before remediation begins.
Target: Prove baseline metrics are accurate for systematic fix tracking.

SSOT Violations Reproduced:
1. WebSocket Auth Violations: 5 found (target: 0)
2. Import Fragmentation: 264 found (target: <5)
3. Singleton Patterns: 3 found (target: 0)
4. Constructor Issues: Multiple dependency injection problems
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def test_websocket_auth_violations() -> Dict[str, int]:
    """Reproduce WebSocket authentication SSOT violations"""
    print("Testing WebSocket Auth SSOT Violations...")
    violations = {
        'token_validation_patterns': 0,
        'auth_bypasses': 0,
        'fallback_auth_paths': 0
    }

    search_patterns = [
        (r'validate_token\(', 'token_validation_patterns'),
        (r'jwt\.decode\(', 'token_validation_patterns'),
        (r'MOCK_AUTH.*=.*True', 'auth_bypasses'),
        (r'fallback.*auth', 'fallback_auth_paths'),
    ]

    base_path = Path.cwd()
    py_files = list(base_path.rglob("*.py"))

    for file_path in py_files:
        if 'test' in str(file_path) or 'backup' in str(file_path):
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            for pattern, violation_type in search_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                violations[violation_type] += len(matches)
        except Exception:
            continue

    total_violations = sum(violations.values())
    print(f"FAIL: Found {total_violations} WebSocket auth violations")
    print(f"  - Token validation patterns: {violations['token_validation_patterns']}")
    print(f"  - Auth bypasses: {violations['auth_bypasses']}")
    print(f"  - Fallback auth paths: {violations['fallback_auth_paths']}")

    return violations

def test_import_fragmentation_violations() -> Dict[str, int]:
    """Reproduce import fragmentation SSOT violations"""
    print("\nTesting Import Fragmentation SSOT Violations...")
    violations = {
        'fragmented_imports': 0,
        'deprecated_imports': 0,
        'direct_instantiations': 0
    }

    fragmentation_patterns = [
        r'from netra_backend\.app\.agents\.supervisor\.execution_engine_factory import',
        r'from netra_backend\.app\.agents\.supervisor\.user_execution_engine import',
        r'import.*ExecutionEngine.*as.*'
    ]

    direct_instantiation_pattern = r'ExecutionEngine\(\)'

    base_path = Path.cwd()
    py_files = list(base_path.rglob("*.py"))

    for file_path in py_files:
        if 'backup' in str(file_path):
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            # Count fragmented imports
            for pattern in fragmentation_patterns:
                matches = re.findall(pattern, content)
                violations['fragmented_imports'] += len(matches)

            # Count deprecated imports
            if 'supervisor.execution_engine' in content or 'supervisor.user_execution' in content:
                violations['deprecated_imports'] += content.count('from netra_backend.app.agents.supervisor')

            # Count direct instantiations
            direct_matches = re.findall(direct_instantiation_pattern, content)
            violations['direct_instantiations'] += len(direct_matches)

        except Exception:
            continue

    total_violations = sum(violations.values())
    print(f" Found {total_violations} import fragmentation violations")
    print(f"  - Fragmented imports: {violations['fragmented_imports']}")
    print(f"  - Deprecated imports: {violations['deprecated_imports']}")
    print(f"  - Direct instantiations: {violations['direct_instantiations']}")

    return violations

def test_singleton_pattern_violations() -> Dict[str, int]:
    """Reproduce singleton pattern SSOT violations"""
    print("\n Testing Singleton Pattern SSOT Violations...")
    violations = {
        'global_instances': 0,
        'singleton_classes': 0,
        'shared_state_patterns': 0
    }

    singleton_patterns = [
        (r'global _factory_instance', 'global_instances'),
        (r'global _bridge_instance', 'global_instances'),
        (r'class.*Singleton', 'singleton_classes'),
        (r'_instance\s*=\s*None', 'shared_state_patterns'),
    ]

    base_path = Path.cwd()
    py_files = list(base_path.rglob("*.py"))

    for file_path in py_files:
        if 'test' in str(file_path) or 'backup' in str(file_path):
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            for pattern, violation_type in singleton_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                violations[violation_type] += len(matches)
        except Exception:
            continue

    total_violations = sum(violations.values())
    print(f" Found {total_violations} singleton pattern violations")
    print(f"  - Global instances: {violations['global_instances']}")
    print(f"  - Singleton classes: {violations['singleton_classes']}")
    print(f"  - Shared state patterns: {violations['shared_state_patterns']}")

    return violations

def test_constructor_dependency_violations() -> Dict[str, int]:
    """Reproduce constructor dependency injection violations"""
    print("\n Testing Constructor Dependency SSOT Violations...")
    violations = {
        'missing_type_hints': 0,
        'no_required_deps': 0,
        'parameterless_allowed': 0
    }

    # Check UserExecutionEngine constructor specifically
    target_file = Path.cwd() / "netra_backend" / "app" / "agents" / "supervisor" / "user_execution_engine.py"

    if target_file.exists():
        try:
            content = target_file.read_text(encoding='utf-8')

            # Parse AST to check constructor
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "UserExecutionEngine":
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                            # Check for required parameters
                            required_params = ['context', 'agent_factory', 'websocket_emitter']
                            actual_params = [arg.arg for arg in item.args.args if arg.arg != 'self']

                            if not all(param in str(actual_params) for param in required_params):
                                violations['no_required_deps'] += 1

                            # Check type annotations
                            for arg in item.args.args:
                                if arg.arg != 'self' and not arg.annotation:
                                    violations['missing_type_hints'] += 1

                            # Check if parameterless instantiation is allowed
                            if len(item.args.args) <= 1:  # Only self
                                violations['parameterless_allowed'] += 1

        except Exception as e:
            print(f"  Error analyzing constructor: {e}")
            violations['no_required_deps'] += 1

    total_violations = sum(violations.values())
    print(f" Found {total_violations} constructor dependency violations")
    print(f"  - Missing type hints: {violations['missing_type_hints']}")
    print(f"  - No required dependencies: {violations['no_required_deps']}")
    print(f"  - Parameterless allowed: {violations['parameterless_allowed']}")

    return violations

def main():
    """Execute SSOT violation reproduction tests"""
    print("=" * 80)
    print("Issue #1186 SSOT Violation Reproduction Test")
    print("=" * 80)
    print("Purpose: Reproduce current violations to establish baseline metrics")
    print("Target: Prove systematic remediation is needed\n")

    # Run all violation tests
    websocket_violations = test_websocket_auth_violations()
    import_violations = test_import_fragmentation_violations()
    singleton_violations = test_singleton_pattern_violations()
    constructor_violations = test_constructor_dependency_violations()

    # Summary
    print("\n" + "=" * 80)
    print("SSOT VIOLATION SUMMARY - BASELINE METRICS")
    print("=" * 80)

    total_websocket = sum(websocket_violations.values())
    total_import = sum(import_violations.values())
    total_singleton = sum(singleton_violations.values())
    total_constructor = sum(constructor_violations.values())
    grand_total = total_websocket + total_import + total_singleton + total_constructor

    print(f" WebSocket Auth Violations: {total_websocket} (Target: 0)")
    print(f" Import Fragmentation: {total_import} (Target: <5)")
    print(f" Singleton Patterns: {total_singleton} (Target: 0)")
    print(f" Constructor Issues: {total_constructor} (Target: 0)")
    print(f"\n TOTAL SSOT VIOLATIONS: {grand_total}")

    print("\n REPRODUCTION TEST COMPLETE")
    print("These violations prove that systematic SSOT remediation is required.")
    print("Use these baseline metrics to track remediation progress.")

    return {
        'websocket_auth': websocket_violations,
        'import_fragmentation': import_violations,
        'singleton_patterns': singleton_violations,
        'constructor_dependency': constructor_violations,
        'total_violations': grand_total
    }

if __name__ == "__main__":
    results = main()

    # Exit with non-zero code to indicate violations found (expected for baseline)
    if results['total_violations'] > 0:
        print(f"\n EXPECTED FAILURE: {results['total_violations']} SSOT violations found.")
        print("This is expected behavior - violations must exist before remediation.")
        sys.exit(1)
    else:
        print("\n No violations found - unexpected for baseline measurement.")
        sys.exit(0)