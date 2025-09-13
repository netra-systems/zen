#!/usr/bin/env python3
"""
SSOT UUID Compliance Checker for Issue #584 Prevention

This script checks for direct uuid.uuid4() usage that bypasses SSOT patterns,
helping prevent future instances of Issue #584 (ID generation inconsistencies).

Usage:
    python scripts/check_uuid_ssot_compliance.py [--fix] [--path PATH]

Returns:
    0: No violations found
    1: Violations found (or fix applied)
    2: Error occurred
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class UUIDViolation:
    """Represents a UUID SSOT compliance violation."""
    file_path: str
    line_number: int
    line_content: str
    violation_type: str
    severity: str


class UUIDSSOTChecker:
    """Checks for UUID SSOT compliance violations."""

    # Patterns that violate SSOT UUID generation
    VIOLATION_PATTERNS = [
        (r'uuid\.uuid4\(\)', 'direct_uuid4', 'HIGH'),
        (r'str\(uuid\.uuid4\(\)\)', 'str_uuid4', 'HIGH'),
        (r'f"[^"]*{uuid\.uuid4\(\)}[^"]*"', 'fstring_uuid4', 'HIGH'),
        (r'f\'[^\']*{uuid\.uuid4\(\)}[^\']*\'', 'fstring_uuid4', 'HIGH'),
        (r'uuid\.uuid4\(\)\.hex', 'uuid4_hex', 'HIGH'),
        (r'uuid\.uuid4\(\)\.hex\[:8\]', 'uuid4_hex_slice', 'CRITICAL'),
    ]

    # File patterns to check
    INCLUDE_PATTERNS = [
        '**/*.py',
    ]

    # File patterns to exclude
    EXCLUDE_PATTERNS = [
        '**/test_*uuid*.py',  # UUID-specific tests are allowed
        '**/migration_*.py',  # Migration scripts may need direct UUID
        '**/scripts/scan_*.py',  # Scanning scripts are allowed
        '**/scripts/check_*.py',  # Check scripts are allowed
        '**/unified_id_*.py',  # SSOT implementation files
        '**/test_framework/**',  # Test framework files
    ]

    # Approved exceptions (files allowed to use direct UUID)
    APPROVED_EXCEPTIONS = [
        'netra_backend/app/core/unified_id_manager.py',  # SSOT implementation
        'shared/id_generation/unified_id_generator.py',  # SSOT implementation
        'tests/unit/id_generation/test_id_generation_inconsistency_reproduction.py',  # Testing violations
    ]

    def __init__(self, root_path: str = '.'):
        self.root_path = Path(root_path)
        self.violations: List[UUIDViolation] = []

    def check_compliance(self) -> List[UUIDViolation]:
        """Check for UUID SSOT compliance violations."""
        self.violations.clear()

        for file_path in self._get_files_to_check():
            self._check_file(file_path)

        return self.violations

    def _get_files_to_check(self) -> List[Path]:
        """Get list of Python files to check."""
        files = []

        for pattern in self.INCLUDE_PATTERNS:
            files.extend(self.root_path.glob(pattern))

        # Filter out excluded patterns
        filtered_files = []
        for file_path in files:
            relative_path = file_path.relative_to(self.root_path)

            # Check if file should be excluded
            excluded = False
            for exclude_pattern in self.EXCLUDE_PATTERNS:
                if file_path.match(exclude_pattern):
                    excluded = True
                    break

            # Check if file is an approved exception
            if str(relative_path).replace('\\', '/') in self.APPROVED_EXCEPTIONS:
                excluded = True

            if not excluded and file_path.is_file():
                filtered_files.append(file_path)

        return filtered_files

    def _check_file(self, file_path: Path) -> None:
        """Check a single file for violations."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                self._check_line(file_path, line_num, line)

        except Exception as e:
            print(f"Error checking file {file_path}: {e}", file=sys.stderr)

    def _check_line(self, file_path: Path, line_num: int, line: str) -> None:
        """Check a single line for violations."""
        line_stripped = line.strip()

        # Skip comments
        if line_stripped.startswith('#'):
            return

        # Check each violation pattern
        for pattern, violation_type, severity in self.VIOLATION_PATTERNS:
            if re.search(pattern, line):
                violation = UUIDViolation(
                    file_path=str(file_path.relative_to(self.root_path)),
                    line_number=line_num,
                    line_content=line.rstrip(),
                    violation_type=violation_type,
                    severity=severity
                )
                self.violations.append(violation)

    def print_violations(self) -> None:
        """Print violations in a readable format."""
        if not self.violations:
            print("[PASS] No UUID SSOT compliance violations found!")
            return

        print(f"[FAIL] Found {len(self.violations)} UUID SSOT compliance violations:")
        print()

        violations_by_severity = {}
        for violation in self.violations:
            if violation.severity not in violations_by_severity:
                violations_by_severity[violation.severity] = []
            violations_by_severity[violation.severity].append(violation)

        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if severity not in violations_by_severity:
                continue

            violations = violations_by_severity[severity]
            print(f"[{severity}] VIOLATIONS ({len(violations)}):")

            for violation in violations:
                print(f"  FILE: {violation.file_path}:{violation.line_number}")
                print(f"     {violation.line_content}")
                print(f"     Type: {violation.violation_type}")
                print()

        print("RECOMMENDED FIXES:")
        print()
        print("Replace direct uuid.uuid4() usage with SSOT patterns:")
        print()
        print("WRONG:")
        print("   demo_user_id = f\"demo-user-{uuid.uuid4()}\"")
        print("   thread_id = f\"demo-thread-{uuid.uuid4()}\"")
        print()
        print("CORRECT:")
        print("   from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType")
        print("   id_manager = UnifiedIDManager()")
        print("   demo_user_id = id_manager.generate_id(IDType.USER, prefix=\"demo\")")
        print("   thread_id = id_manager.generate_id(IDType.THREAD, prefix=\"demo\")")
        print()

    def generate_fix_suggestions(self) -> Dict[str, List[str]]:
        """Generate fix suggestions for each violation."""
        suggestions = {}

        for violation in self.violations:
            if violation.file_path not in suggestions:
                suggestions[violation.file_path] = []

            line_content = violation.line_content.strip()

            if violation.violation_type == 'direct_uuid4':
                suggestion = self._suggest_direct_uuid4_fix(line_content)
            elif violation.violation_type in ['str_uuid4', 'fstring_uuid4']:
                suggestion = self._suggest_formatted_uuid4_fix(line_content)
            elif violation.violation_type in ['uuid4_hex', 'uuid4_hex_slice']:
                suggestion = self._suggest_hex_uuid4_fix(line_content)
            else:
                suggestion = "Replace with appropriate UnifiedIDManager pattern"

            suggestions[violation.file_path].append(
                f"Line {violation.line_number}: {suggestion}"
            )

        return suggestions

    def _suggest_direct_uuid4_fix(self, line_content: str) -> str:
        """Suggest fix for direct uuid.uuid4() usage."""
        return (
            "Replace 'uuid.uuid4()' with 'id_manager.generate_id(IDType.APPROPRIATE_TYPE)'"
        )

    def _suggest_formatted_uuid4_fix(self, line_content: str) -> str:
        """Suggest fix for formatted uuid.uuid4() usage."""
        # Try to detect the prefix pattern
        if 'user' in line_content.lower():
            id_type = 'IDType.USER'
        elif 'thread' in line_content.lower():
            id_type = 'IDType.THREAD'
        elif 'request' in line_content.lower() or 'req' in line_content.lower():
            id_type = 'IDType.REQUEST'
        elif 'websocket' in line_content.lower() or 'ws' in line_content.lower():
            id_type = 'IDType.WEBSOCKET'
        else:
            id_type = 'IDType.APPROPRIATE_TYPE'

        return (
            f"Replace with 'id_manager.generate_id({id_type}, prefix=\"your_prefix\")'"
        )

    def _suggest_hex_uuid4_fix(self, line_content: str) -> str:
        """Suggest fix for uuid.uuid4().hex usage."""
        return (
            "Replace 'uuid.uuid4().hex[:8]' with UnifiedIDManager structured format"
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Check for UUID SSOT compliance violations'
    )
    parser.add_argument(
        '--path', default='.',
        help='Path to check (default: current directory)'
    )
    parser.add_argument(
        '--fix', action='store_true',
        help='Generate fix suggestions'
    )
    parser.add_argument(
        '--quiet', action='store_true',
        help='Quiet mode - only return exit code'
    )

    args = parser.parse_args()

    try:
        checker = UUIDSSOTChecker(args.path)
        violations = checker.check_compliance()

        if not args.quiet:
            checker.print_violations()

            if args.fix and violations:
                print("🔧 FIX SUGGESTIONS:")
                print()
                suggestions = checker.generate_fix_suggestions()
                for file_path, file_suggestions in suggestions.items():
                    print(f"📁 {file_path}:")
                    for suggestion in file_suggestions:
                        print(f"   {suggestion}")
                    print()

        # Return appropriate exit code
        if violations:
            return 1
        else:
            return 0

    except Exception as e:
        if not args.quiet:
            print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())