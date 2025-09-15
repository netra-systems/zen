#!/usr/bin/env python3
"""
pytest.main() Violation Detection Script for Pre-Commit Hooks

Business Value Justification (BVJ):
- Segment: Platform (All segments affected by deployment blocks)
- Business Goal: Stability - Prevent deployment blocking from test chaos
- Value Impact: Protects $500K+ ARR from deployment delays and failures
- Revenue Impact: Prevents customer churn from unreliable system deployments

PURPOSE: Detect and prevent pytest.main() bypasses that create test infrastructure chaos.
ISSUE: https://github.com/netra-systems/netra-apex/issues/1024

CRITICAL: 1,909 direct pytest bypasses identified causing Golden Path degradation.
"""

import sys
import re
import ast
from pathlib import Path
from typing import List, Tuple, Dict, Set

# Setup project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Files that are explicitly allowed to use pytest.main() (minimal SSOT exceptions)
PYTEST_MAIN_ALLOWLIST = {
    "tests/unified_test_runner.py",  # SSOT test runner - allowed
    "test_framework/ssot/base_test_case.py",  # SSOT framework - allowed
    "scripts/detect_pytest_main_violations.py",  # This script - allowed
}

# Critical pytest.main() patterns to detect
PYTEST_MAIN_PATTERNS = [
    r'pytest\.main\s*\(',
    r'pytest\.cmdline\.main\s*\(',
    r'from\s+pytest\s+import\s+main',
    r'import\s+pytest.*\.main',
]

# Context patterns that indicate test infrastructure bypassing
INFRASTRUCTURE_BYPASS_PATTERNS = [
    r'if\s+__name__\s*==\s*["\']__main__["\'].*pytest\.main',
    r'subprocess\..*pytest\.main',
    r'os\.system.*pytest\.main',
    r'exec.*pytest\.main',
]

def analyze_pytest_main_usage(file_path: str) -> List[Dict]:
    """
    Analyze pytest.main() usage in a file with context.

    Returns:
        List of violation dictionaries with context
    """
    violations = []

    # Skip allowlisted files
    if any(allowed in file_path for allowed in PYTEST_MAIN_ALLOWLIST):
        return violations

    if not file_path.endswith('.py'):
        return violations

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()

        # Pattern-based detection
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Skip comments and docstrings
            if line_stripped.startswith('#') or line_stripped.startswith('"""') or line_stripped.startswith("'''"):
                continue

            # Check for pytest.main() patterns
            for pattern in PYTEST_MAIN_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append({
                        'file_path': file_path,
                        'line_number': line_num,
                        'line_content': line_stripped,
                        'pattern': pattern,
                        'type': 'direct_pytest_main',
                        'severity': 'HIGH',
                        'context': _get_line_context(lines, line_num)
                    })

            # Check for infrastructure bypass patterns
            for pattern in INFRASTRUCTURE_BYPASS_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append({
                        'file_path': file_path,
                        'line_number': line_num,
                        'line_content': line_stripped,
                        'pattern': pattern,
                        'type': 'infrastructure_bypass',
                        'severity': 'CRITICAL',
                        'context': _get_line_context(lines, line_num)
                    })

        # AST-based analysis for deeper detection
        try:
            tree = ast.parse(content)
            ast_violations = _analyze_ast_pytest_usage(tree, file_path, lines)
            violations.extend(ast_violations)
        except SyntaxError:
            # If AST parsing fails, we already have regex detection
            pass

    except Exception as e:
        print(f"Warning: Could not analyze {file_path}: {e}")

    return violations

def _get_line_context(lines: List[str], line_num: int, context_size: int = 3) -> Dict:
    """Get context around a line for better violation reporting."""
    start = max(0, line_num - context_size - 1)
    end = min(len(lines), line_num + context_size)

    return {
        'before': lines[start:line_num-1],
        'after': lines[line_num:end],
        'function_context': _find_function_context(lines, line_num)
    }

def _find_function_context(lines: List[str], line_num: int) -> str:
    """Find the function or class context for a line."""
    for i in range(line_num - 1, -1, -1):
        line = lines[i].strip()
        if line.startswith('def ') or line.startswith('class '):
            return line
        if line.startswith('if __name__'):
            return '__main__ block'
    return 'module level'

def _analyze_ast_pytest_usage(tree: ast.AST, file_path: str, lines: List[str]) -> List[Dict]:
    """Analyze AST for pytest.main() usage patterns."""
    violations = []

    class PytestMainVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            # Check for pytest.main() calls
            if (isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'pytest' and
                node.func.attr == 'main'):

                line_num = node.lineno
                violations.append({
                    'file_path': file_path,
                    'line_number': line_num,
                    'line_content': lines[line_num - 1] if line_num <= len(lines) else '',
                    'pattern': 'AST: pytest.main() call',
                    'type': 'ast_pytest_main',
                    'severity': 'HIGH',
                    'context': _get_line_context(lines, line_num)
                })

            self.generic_visit(node)

        def visit_If(self, node):
            # Check for __main__ blocks with pytest calls
            if (isinstance(node.test, ast.Compare) and
                isinstance(node.test.left, ast.Name) and
                node.test.left.id == '__name__'):

                # Check if the body contains pytest-related calls
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Call):
                        call_str = ast.dump(stmt)
                        if 'pytest' in call_str and 'main' in call_str:
                            line_num = node.lineno
                            violations.append({
                                'file_path': file_path,
                                'line_number': line_num,
                                'line_content': lines[line_num - 1] if line_num <= len(lines) else '',
                                'pattern': 'AST: __main__ block with pytest',
                                'type': 'main_block_pytest',
                                'severity': 'CRITICAL',
                                'context': _get_line_context(lines, line_num)
                            })
                            break

            self.generic_visit(node)

    visitor = PytestMainVisitor()
    visitor.visit(tree)
    return violations

def generate_violation_report(all_violations: List[Dict]) -> None:
    """Generate comprehensive violation report."""
    if not all_violations:
        print("✅ No pytest.main() violations detected.")
        return

    print(f"\n🚨 CRITICAL: {len(all_violations)} PYTEST.MAIN() VIOLATIONS DETECTED!")
    print("=" * 80)
    print("ISSUE #1024: Direct pytest bypasses causing Golden Path degradation")
    print("BUSINESS IMPACT: $500K+ ARR at risk from test infrastructure chaos")
    print("=" * 80)

    # Group by severity
    critical_violations = [v for v in all_violations if v['severity'] == 'CRITICAL']
    high_violations = [v for v in all_violations if v['severity'] == 'HIGH']

    if critical_violations:
        print(f"\n🔥 CRITICAL VIOLATIONS ({len(critical_violations)}):")
        for violation in critical_violations:
            print(f"  ❌ {violation['file_path']}:{violation['line_number']}")
            print(f"     Type: {violation['type']}")
            print(f"     Pattern: {violation['pattern']}")
            print(f"     Line: {violation['line_content']}")
            print(f"     Context: {violation['context']['function_context']}")
            print()

    if high_violations:
        print(f"\n⚠️  HIGH PRIORITY VIOLATIONS ({len(high_violations)}):")
        for violation in high_violations:
            print(f"  ❌ {violation['file_path']}:{violation['line_number']}")
            print(f"     Type: {violation['type']}")
            print(f"     Line: {violation['line_content']}")
            print()

    print("🔧 REQUIRED REMEDIATION:")
    print("1. Replace all pytest.main() calls with SSOT unified_test_runner.py")
    print("2. Remove __main__ blocks with direct test execution")
    print("3. Use: python tests/unified_test_runner.py --category <category>")
    print()
    print("📚 MIGRATION GUIDE:")
    print("- SSOT Guide: reports/TEST_EXECUTION_GUIDE.md")
    print("- Issue #1024: https://github.com/netra-systems/netra-apex/issues/1024")
    print("- Migration Tool: scripts/migrate_pytest_main_violations.py (coming soon)")

def main():
    """Main entry point for pre-commit hook."""
    if len(sys.argv) < 2:
        print("Usage: detect_pytest_main_violations.py <file1> <file2> ...")
        sys.exit(0)

    file_paths = sys.argv[1:]
    all_violations = []

    for file_path in file_paths:
        violations = analyze_pytest_main_usage(file_path)
        all_violations.extend(violations)

    generate_violation_report(all_violations)

    if all_violations:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()