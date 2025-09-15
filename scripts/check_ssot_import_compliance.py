#!/usr/bin/env python3
"""
SSOT Import Compliance Checker for Pre-Commit Hooks

Business Value Justification (BVJ):
- Segment: Platform (All segments affected by import chaos)
- Business Goal: Stability - Prevent import-related deployment failures
- Value Impact: Protects $500K+ ARR from import inconsistency issues
- Revenue Impact: Prevents system instability from fragmented imports

PURPOSE: Enforce SSOT import patterns to prevent import chaos.
ISSUE: https://github.com/netra-systems/netra-apex/issues/1024

SSOT Requirements:
1. Use tests/unified_test_runner.py for all test execution
2. Use test_framework.ssot.base_test_case for test base classes
3. Use test_framework.unified_docker_manager for Docker operations
4. No relative imports (. or ..)
5. No direct os.environ access (use IsolatedEnvironment)
"""

import sys
import re
import ast
from pathlib import Path
from typing import List, Tuple, Dict, Set

# Setup project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# SSOT Import Requirements
SSOT_IMPORT_REQUIREMENTS = {
    # Test infrastructure SSOT
    'test_base': {
        'required_pattern': r'from\s+test_framework\.ssot\.base_test_case\s+import',
        'prohibited_patterns': [
            r'import\s+unittest',
            r'from\s+unittest\s+import',
            r'class.*\(unittest\.TestCase\)',
            r'class.*\(TestCase\)',
        ],
        'applies_to': ['test_*.py', '*_test.py', 'tests/**/*.py'],
        'message': 'Use SSOT base test case: from test_framework.ssot.base_test_case import SSotTestCase'
    },

    # Docker management SSOT
    'docker_management': {
        'required_pattern': r'from\s+test_framework\.unified_docker_manager\s+import',
        'prohibited_patterns': [
            r'import\s+docker\b',
            r'from\s+docker\s+import',
            r'docker\.from_env\(',
            r'docker\.client\.',
        ],
        'applies_to': ['test_*.py', '*_test.py', 'tests/**/*.py'],
        'message': 'Use SSOT Docker management: from test_framework.unified_docker_manager import UnifiedDockerManager'
    },

    # Environment access SSOT
    'environment_access': {
        'prohibited_patterns': [
            r'import\s+os\b.*os\.environ',
            r'os\.environ\[',
            r'os\.getenv\(',
            r'from\s+os\s+import\s+environ',
        ],
        'required_pattern': r'from\s+dev_launcher\.isolated_environment\s+import',
        'applies_to': ['**/*.py'],
        'exceptions': ['dev_launcher/isolated_environment.py', 'scripts/**/*.py'],
        'message': 'Use SSOT environment access: from dev_launcher.isolated_environment import IsolatedEnvironment'
    },

    # Relative imports prohibition
    'relative_imports': {
        'prohibited_patterns': [
            r'from\s+\.\s+import',
            r'from\s+\.\.',
            r'import\s+\.',
        ],
        'applies_to': ['**/*.py'],
        'message': 'Use absolute imports only. Relative imports (. or ..) are prohibited.'
    },
}

def check_file_ssot_compliance(file_path: str) -> List[Dict]:
    """
    Check a file for SSOT import compliance violations.

    Returns:
        List of violation dictionaries
    """
    violations = []

    if not file_path.endswith('.py'):
        return violations

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()

        # Check each SSOT requirement
        for requirement_name, requirement in SSOT_IMPORT_REQUIREMENTS.items():
            file_violations = _check_requirement(
                file_path, content, lines, requirement_name, requirement
            )
            violations.extend(file_violations)

    except Exception as e:
        print(f"Warning: Could not analyze {file_path}: {e}")

    return violations

def _check_requirement(file_path: str, content: str, lines: List[str],
                      requirement_name: str, requirement: Dict) -> List[Dict]:
    """Check a specific SSOT requirement against a file."""
    violations = []

    # Check if requirement applies to this file
    if not _file_matches_patterns(file_path, requirement.get('applies_to', [])):
        return violations

    # Check for exceptions
    if _file_matches_patterns(file_path, requirement.get('exceptions', [])):
        return violations

    # Check prohibited patterns
    for prohibited_pattern in requirement.get('prohibited_patterns', []):
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Skip comments and docstrings
            if line_stripped.startswith('#') or line_stripped.startswith('"""') or line_stripped.startswith("'''"):
                continue

            if re.search(prohibited_pattern, line, re.IGNORECASE):
                violations.append({
                    'file_path': file_path,
                    'line_number': line_num,
                    'line_content': line_stripped,
                    'requirement': requirement_name,
                    'pattern': prohibited_pattern,
                    'type': 'prohibited_pattern',
                    'severity': 'HIGH',
                    'message': requirement.get('message', 'SSOT compliance violation'),
                    'context': _get_context(lines, line_num)
                })

    # Check for required patterns (if specified)
    required_pattern = requirement.get('required_pattern')
    if required_pattern and requirement.get('prohibited_patterns'):
        # Only check required pattern if prohibited patterns were found
        has_prohibited = any(
            re.search(pattern, content, re.IGNORECASE)
            for pattern in requirement.get('prohibited_patterns', [])
        )

        if has_prohibited and not re.search(required_pattern, content, re.IGNORECASE):
            violations.append({
                'file_path': file_path,
                'line_number': 1,
                'line_content': '# Missing required SSOT import',
                'requirement': requirement_name,
                'pattern': required_pattern,
                'type': 'missing_required',
                'severity': 'CRITICAL',
                'message': f"Missing required SSOT import: {requirement.get('message', '')}",
                'context': {'function_context': 'module level'}
            })

    return violations

def _file_matches_patterns(file_path: str, patterns: List[str]) -> bool:
    """Check if a file path matches any of the given patterns."""
    if not patterns:
        return True

    path_obj = Path(file_path)

    for pattern in patterns:
        # Convert glob pattern to regex-like matching
        if pattern.startswith('**'):
            # Recursive pattern
            if pattern.endswith('*.py'):
                if str(path_obj).endswith('.py'):
                    return True
            elif any(part in str(path_obj) for part in pattern.split('/')):
                return True
        elif pattern.startswith('test_') or pattern.endswith('_test.py'):
            if path_obj.name.startswith('test_') or path_obj.name.endswith('_test.py'):
                return True
        elif 'tests/' in pattern:
            if 'tests' in str(path_obj):
                return True
        elif pattern in str(path_obj):
            return True

    return False

def _get_context(lines: List[str], line_num: int) -> Dict:
    """Get context around a line."""
    return {
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

def generate_compliance_report(all_violations: List[Dict]) -> None:
    """Generate comprehensive SSOT compliance report."""
    if not all_violations:
        print("✅ No SSOT import compliance violations detected.")
        return

    print(f"\n🚨 CRITICAL: {len(all_violations)} SSOT IMPORT VIOLATIONS DETECTED!")
    print("=" * 80)
    print("ISSUE #1024: SSOT import patterns must be enforced")
    print("BUSINESS IMPACT: $500K+ ARR at risk from import fragmentation")
    print("=" * 80)

    # Group by requirement and severity
    by_requirement = {}
    for violation in all_violations:
        req = violation['requirement']
        if req not in by_requirement:
            by_requirement[req] = []
        by_requirement[req].append(violation)

    for requirement, violations in by_requirement.items():
        print(f"\n📍 {requirement.upper()} VIOLATIONS ({len(violations)}):")

        for violation in violations:
            severity_icon = "🔥" if violation['severity'] == 'CRITICAL' else "⚠️"
            print(f"  {severity_icon} {violation['file_path']}:{violation['line_number']}")
            print(f"     Type: {violation['type']}")
            print(f"     Message: {violation['message']}")
            if violation['line_content'] and not violation['line_content'].startswith('#'):
                print(f"     Line: {violation['line_content']}")
            print()

    print("🔧 REMEDIATION ACTIONS:")
    print("1. Replace unittest with SSOT base test case imports")
    print("2. Replace direct Docker usage with UnifiedDockerManager")
    print("3. Replace os.environ with IsolatedEnvironment")
    print("4. Convert relative imports to absolute imports")
    print()
    print("📚 SSOT DOCUMENTATION:")
    print("- SSOT Guide: reports/TEST_EXECUTION_GUIDE.md")
    print("- Import Registry: docs/SSOT_IMPORT_REGISTRY.md")
    print("- Issue #1024: https://github.com/netra-systems/netra-apex/issues/1024")

def main():
    """Main entry point for pre-commit hook."""
    if len(sys.argv) < 2:
        print("Usage: check_ssot_import_compliance.py <file1> <file2> ...")
        sys.exit(0)

    file_paths = sys.argv[1:]
    all_violations = []

    for file_path in file_paths:
        violations = check_file_ssot_compliance(file_path)
        all_violations.extend(violations)

    generate_compliance_report(all_violations)

    if all_violations:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()