"""
Test SSOT Migration Completeness Validation

Business Value Justification (BVJ):
- Segment: Platform (Infrastructure)
- Business Goal: System Stability - Ensure complete SSOT migration
- Value Impact: Prevents future issues from incomplete automation
- Strategic Impact: Test infrastructure reliability and maintainability

CRITICAL: This test MUST FAIL until SSOT migration artifacts are cleaned up.
Expected: Migration artifacts in mission-critical test files from incomplete automation.
"""

import glob
import os
import re
import pytest
from typing import List, Dict, Tuple

class TestSSOTMigrationCompleteness:
    """Test suite to validate SSOT migration completed successfully."""

    def test_no_migration_artifacts_in_mission_critical_files(self):
        """
        CRITICAL TEST: Validate no SSOT migration artifacts remain in mission-critical files.

        This test MUST FAIL initially to prove migration artifacts exist.
        Expected: Files containing "REMOVED_SYNTAX_ERROR" comments and malformed code.

        Business Impact: Migration artifacts indicate incomplete automation that could
        cause future stability issues and technical debt.
        """
        # Get all mission-critical test files
        mission_critical_pattern = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "mission_critical",
            "**",
            "*.py"
        )

        test_files = glob.glob(mission_critical_pattern, recursive=True)

        migration_artifacts = []
        artifact_patterns = [
            "REMOVED_SYNTAX_ERROR",
            "MIGRATED:",
            "TODO: Replace with appropriate SSOT test execution",
        ]

        for file_path in test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = f.readlines()

                file_artifacts = []

                # Check for each artifact pattern
                for pattern in artifact_patterns:
                    if pattern in content:
                        # Find specific line numbers where artifacts occur
                        for line_num, line in enumerate(lines, 1):
                            if pattern in line:
                                file_artifacts.append({
                                    'pattern': pattern,
                                    'line': line_num,
                                    'content': line.strip()
                                })

                if file_artifacts:
                    migration_artifacts.append({
                        'file': os.path.relpath(file_path),
                        'artifacts': file_artifacts
                    })

            except Exception as e:
                # Handle file reading errors
                migration_artifacts.append({
                    'file': os.path.relpath(file_path),
                    'artifacts': [{'pattern': 'FILE_READ_ERROR', 'line': 0, 'content': str(e)}]
                })

        # Generate detailed artifact report
        total_files = len(test_files)
        affected_files = len(migration_artifacts)
        total_artifacts = sum(len(item['artifacts']) for item in migration_artifacts)

        artifact_report = f"""
SSOT MIGRATION ARTIFACT ANALYSIS
================================

Total Files Analyzed: {total_files}
Files with Migration Artifacts: {affected_files}
Total Artifacts Found: {total_artifacts}

MIGRATION ARTIFACTS DETECTED:
"""

        for file_info in migration_artifacts[:5]:  # Show first 5 files for readability
            artifact_report += f"""
File: {file_info['file']}
Artifacts:"""
            for artifact in file_info['artifacts']:
                artifact_report += f"""
  Line {artifact['line']}: {artifact['pattern']}
  Content: {artifact['content'][:100]}..."""
            artifact_report += "\n---"

        if len(migration_artifacts) > 5:
            artifact_report += f"\n... and {len(migration_artifacts) - 5} more files with artifacts."

        artifact_report += f"""

EXPECTED RESULT: This test should FAIL until migration artifacts are cleaned up.
BUSINESS IMPACT: {total_artifacts} migration artifacts indicate incomplete automation.
TECHNICAL DEBT: Manual cleanup required to complete SSOT migration.

NEXT ACTION: Remove all migration artifacts from mission-critical test files.
"""

        # This assertion MUST FAIL initially to prove migration artifacts exist
        assert total_artifacts == 0, artifact_report

    def test_proper_indentation_in_mission_critical_files(self):
        """
        Validate proper Python indentation in mission-critical test files.

        Expected: Files have consistent indentation without malformed blocks.
        This test specifically targets the "unexpected indent" errors from Issue #1024.
        """
        # Get all mission-critical test files
        mission_critical_pattern = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "mission_critical",
            "**",
            "*.py"
        )

        test_files = glob.glob(mission_critical_pattern, recursive=True)

        indentation_issues = []

        for file_path in test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                file_issues = []

                # Analyze indentation patterns
                for line_num, line in enumerate(lines, 1):
                    # Skip empty lines and comments
                    stripped = line.strip()
                    if not stripped or stripped.startswith('#'):
                        continue

                    # Check for suspicious indentation patterns
                    leading_spaces = len(line) - len(line.lstrip())

                    # Flag lines with irregular indentation (not multiples of 4)
                    if leading_spaces > 0 and leading_spaces % 4 != 0:
                        # Exception: Allow 2-space indentation for specific contexts
                        if leading_spaces % 2 != 0:
                            file_issues.append({
                                'line': line_num,
                                'spaces': leading_spaces,
                                'content': line.strip(),
                                'issue': 'irregular_indentation'
                            })

                    # Flag lines that appear to be malformed (excessive indentation)
                    if leading_spaces > 60:  # Suspiciously deep indentation
                        file_issues.append({
                            'line': line_num,
                            'spaces': leading_spaces,
                            'content': line.strip(),
                            'issue': 'excessive_indentation'
                        })

                    # Flag specific problematic patterns from SSOT migration
                    if 'pass' in stripped and 'TODO' in stripped and leading_spaces > 20:
                        file_issues.append({
                            'line': line_num,
                            'spaces': leading_spaces,
                            'content': line.strip(),
                            'issue': 'malformed_ssot_todo'
                        })

                if file_issues:
                    indentation_issues.append({
                        'file': os.path.relpath(file_path),
                        'issues': file_issues
                    })

            except Exception as e:
                indentation_issues.append({
                    'file': os.path.relpath(file_path),
                    'issues': [{'line': 0, 'spaces': 0, 'content': str(e), 'issue': 'read_error'}]
                })

        # Generate indentation analysis report
        total_files = len(test_files)
        affected_files = len(indentation_issues)
        total_issues = sum(len(item['issues']) for item in indentation_issues)

        indentation_report = f"""
INDENTATION ANALYSIS REPORT
===========================

Total Files Analyzed: {total_files}
Files with Indentation Issues: {affected_files}
Total Indentation Issues: {total_issues}

INDENTATION ISSUES DETECTED:
"""

        for file_info in indentation_issues[:3]:  # Show first 3 files for readability
            indentation_report += f"""
File: {file_info['file']}
Issues:"""
            for issue in file_info['issues'][:3]:  # Show first 3 issues per file
                indentation_report += f"""
  Line {issue['line']}: {issue['issue']} ({issue['spaces']} spaces)
  Content: {issue['content'][:80]}..."""
            indentation_report += "\n---"

        if affected_files > 3:
            indentation_report += f"\n... and {affected_files - 3} more files with indentation issues."

        indentation_report += f"""

EXPECTED RESULT: Files should have clean, consistent indentation.
BUSINESS IMPACT: Indentation issues prevent test execution and code maintainability.
SSOT MIGRATION IMPACT: Malformed indentation from automated migration needs manual cleanup.

NEXT ACTION: Fix indentation in all affected mission-critical test files.
"""

        # This assertion documents indentation issues for cleanup
        if total_issues > 0:
            pytest.fail(indentation_report)

    def test_proper_ssot_imports_in_mission_critical_files(self):
        """
        Validate that mission-critical test files use proper SSOT imports.

        Expected: All imports follow SSOT patterns and no legacy import patterns exist.
        """
        # Get all mission-critical test files
        mission_critical_pattern = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "mission_critical",
            "**",
            "*.py"
        )

        test_files = glob.glob(mission_critical_pattern, recursive=True)

        import_issues = []
        legacy_patterns = [
            r"from\s+test_framework\..*mock.*import",  # Legacy mock imports
            r"import\s+mock\b",  # Direct mock imports
            r"from\s+unittest\.mock\s+import",  # unittest.mock instead of SSOT
            r"os\.environ\[",  # Direct environment access
            r"\.\.\/",  # Relative imports
        ]

        required_ssot_patterns = [
            "test_framework.ssot",  # SSOT test framework imports
            "shared.isolated_environment",  # Environment management
        ]

        for file_path in test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = f.readlines()

                file_issues = []

                # Check for legacy patterns
                for pattern in legacy_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        file_issues.append({
                            'line': line_num,
                            'type': 'legacy_pattern',
                            'pattern': pattern,
                            'content': lines[line_num - 1].strip() if line_num <= len(lines) else 'N/A'
                        })

                # Check for presence of required SSOT imports (only in files that need them)
                if any(keyword in content for keyword in ['test', 'mock', 'env']):
                    has_ssot_imports = any(pattern in content for pattern in required_ssot_patterns)
                    if not has_ssot_imports and len(content.strip()) > 100:  # Ignore very small files
                        file_issues.append({
                            'line': 1,
                            'type': 'missing_ssot_imports',
                            'pattern': 'required_ssot_imports',
                            'content': 'File appears to need SSOT imports but none found'
                        })

                if file_issues:
                    import_issues.append({
                        'file': os.path.relpath(file_path),
                        'issues': file_issues
                    })

            except Exception as e:
                import_issues.append({
                    'file': os.path.relpath(file_path),
                    'issues': [{'line': 0, 'type': 'read_error', 'pattern': 'file_error', 'content': str(e)}]
                })

        # Generate import analysis report
        total_files = len(test_files)
        affected_files = len(import_issues)
        total_issues = sum(len(item['issues']) for item in import_issues)

        import_report = f"""
SSOT IMPORT ANALYSIS REPORT
===========================

Total Files Analyzed: {total_files}
Files with Import Issues: {affected_files}
Total Import Issues: {total_issues}

IMPORT ISSUES DETECTED:
"""

        for file_info in import_issues[:3]:  # Show first 3 files for readability
            import_report += f"""
File: {file_info['file']}
Issues:"""
            for issue in file_info['issues'][:2]:  # Show first 2 issues per file
                import_report += f"""
  Line {issue['line']}: {issue['type']}
  Pattern: {issue['pattern']}
  Content: {issue['content'][:80]}..."""
            import_report += "\n---"

        if affected_files > 3:
            import_report += f"\n... and {affected_files - 3} more files with import issues."

        import_report += f"""

EXPECTED RESULT: All files should use SSOT import patterns.
BUSINESS IMPACT: Legacy imports violate SSOT architecture and cause maintenance issues.
SSOT COMPLIANCE: Import patterns must follow latest CLAUDE.md standards.

NEXT ACTION: Update imports in affected mission-critical test files to use SSOT patterns.
"""

        # Document import issues but don't fail test (lower priority than syntax)
        if total_issues > 0:
            print(import_report)


if __name__ == "__main__":
    # SSOT Test Execution: Use unified test runner
    # python tests/unified_test_runner.py --category infrastructure
    pytest.main([__file__, "-v"])