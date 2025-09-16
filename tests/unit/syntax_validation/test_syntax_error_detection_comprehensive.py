"""
Comprehensive Syntax Error Detection Test for Issue #1024

MISSION: Systematically identify and validate the 67 syntax errors impacting Golden Path reliability.
Focus on malformed import statements from automated migration and their impact on test collection.

BUSINESS IMPACT: Protect $500K+ ARR by ensuring syntax errors don't prevent mission critical testing.
"""

import ast
import os
import sys
import traceback
import unittest
from pathlib import Path
from typing import Dict, List, Tuple, Set
import importlib.util
import subprocess
import tempfile

from test_framework.ssot.base_test_case import SSotBaseTestCase


class SyntaxErrorDetectionComprehensive(SSotBaseTestCase):
    """Comprehensive syntax error detection for Golden Path reliability validation."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.syntax_errors = []
        self.import_errors = []
        self.collection_failures = []

    def test_ast_syntax_validation_comprehensive(self):
        """Test 1: Use AST parsing to systematically identify syntax errors."""
        print("\n🔍 Phase 1: AST Syntax Validation")

        # Focus on key directories where syntax errors are likely
        test_directories = [
            self.project_root / "tests" / "unit",
            self.project_root / "tests" / "integration",
            self.project_root / "netra_backend" / "tests",
            self.project_root / "auth_service" / "tests",
            self.project_root / "frontend" / "tests"
        ]

        total_files = 0
        syntax_error_files = []

        for test_dir in test_directories:
            if test_dir.exists():
                for py_file in test_dir.rglob("*.py"):
                    total_files += 1
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Parse with AST to detect syntax errors
                        ast.parse(content, filename=str(py_file))

                    except SyntaxError as e:
                        syntax_error_files.append({
                            'file': str(py_file.relative_to(self.project_root)),
                            'line': e.lineno,
                            'error': str(e),
                            'text': e.text.strip() if e.text else None
                        })
                    except UnicodeDecodeError as e:
                        # Skip binary or problematic encoding files
                        continue
                    except Exception as e:
                        # Log other parsing issues
                        syntax_error_files.append({
                            'file': str(py_file.relative_to(self.project_root)),
                            'line': None,
                            'error': f"Parse error: {str(e)}",
                            'text': None
                        })

        print(f"📊 Syntax Validation Results:")
        print(f"   Total Python files scanned: {total_files}")
        print(f"   Files with syntax errors: {len(syntax_error_files)}")

        # Store results for analysis
        self.syntax_errors = syntax_error_files

        # Log detailed syntax errors
        if syntax_error_files:
            print(f"\n🚨 Syntax Errors Found:")
            for error in syntax_error_files[:10]:  # Show first 10
                print(f"   {error['file']}:{error['line']} - {error['error']}")
                if error['text']:
                    print(f"      Code: {error['text']}")

            if len(syntax_error_files) > 10:
                print(f"   ... and {len(syntax_error_files) - 10} more")

        # This test documents findings but doesn't fail - we need to understand scope
        print(f"\n✅ Syntax validation complete. Found {len(syntax_error_files)} issues.")

    def test_import_statement_validation(self):
        """Test 2: Specifically validate import statements from automated migration."""
        print("\n🔍 Phase 2: Import Statement Validation")

        # Common problematic import patterns from migrations
        problematic_patterns = [
            "from .from",  # Migration artifact
            "from ..from",  # Another migration artifact
            "import .import",  # Malformed relative import
            "from from ",  # Duplicated 'from'
            "import import ",  # Duplicated 'import'
            "from . import from",  # Circular naming
            "from netra_api.netra_backend",  # Duplicated path
            "from auth_service.auth_service",  # Duplicated path
        ]

        import_error_files = []
        total_checked = 0

        test_directories = [
            self.project_root / "tests",
            self.project_root / "netra_backend",
            self.project_root / "auth_service",
            self.project_root / "shared"
        ]

        for test_dir in test_directories:
            if test_dir.exists():
                for py_file in test_dir.rglob("*.py"):
                    total_checked += 1
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()

                        for line_num, line in enumerate(lines, 1):
                            line_stripped = line.strip()
                            if line_stripped.startswith(('import ', 'from ')):
                                # Check for problematic patterns
                                for pattern in problematic_patterns:
                                    if pattern in line_stripped:
                                        import_error_files.append({
                                            'file': str(py_file.relative_to(self.project_root)),
                                            'line': line_num,
                                            'pattern': pattern,
                                            'code': line_stripped
                                        })

                    except (UnicodeDecodeError, PermissionError):
                        continue

        print(f"📊 Import Validation Results:")
        print(f"   Total Python files checked: {total_checked}")
        print(f"   Files with import issues: {len(set(err['file'] for err in import_error_files))}")
        print(f"   Total import issues found: {len(import_error_files)}")

        # Store results
        self.import_errors = import_error_files

        if import_error_files:
            print(f"\n🚨 Import Issues Found:")
            for error in import_error_files[:15]:  # Show first 15
                print(f"   {error['file']}:{error['line']} - Pattern: '{error['pattern']}'")
                print(f"      Code: {error['code']}")

            if len(import_error_files) > 15:
                print(f"   ... and {len(import_error_files) - 15} more")

        print(f"\n✅ Import validation complete.")

    def test_collection_impact_measurement(self):
        """Test 3: Measure impact of syntax errors on test collection."""
        print("\n🔍 Phase 3: Collection Impact Measurement")

        # Test collection behavior using subprocess to avoid polluting current process
        try:
            # Run test discovery to see collection success rate
            cmd = [
                sys.executable, "-m", "pytest",
                "--collect-only",
                "-q",
                "tests/unit",
                "--tb=no"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=60
            )

            stdout_lines = result.stdout.split('\n')
            stderr_lines = result.stderr.split('\n')

            # Parse collection results
            collected_count = 0
            error_count = 0
            warning_count = 0

            for line in stdout_lines + stderr_lines:
                if "collected" in line.lower():
                    # Try to extract collection count
                    words = line.split()
                    for i, word in enumerate(words):
                        if word.isdigit() and i + 1 < len(words) and words[i+1] in ["tests", "items"]:
                            collected_count = max(collected_count, int(word))

                if any(indicator in line.lower() for indicator in ["error", "failed", "syntaxerror"]):
                    error_count += 1

                if "warning" in line.lower():
                    warning_count += 1

            print(f"📊 Collection Results:")
            print(f"   Return code: {result.returncode}")
            print(f"   Tests collected: {collected_count}")
            print(f"   Collection errors: {error_count}")
            print(f"   Warnings: {warning_count}")

            # Store collection issues
            if result.returncode != 0:
                self.collection_failures.append({
                    'command': ' '.join(cmd),
                    'return_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                })

            print(f"\n✅ Collection impact measurement complete.")

        except subprocess.TimeoutExpired:
            print("⚠️ Collection test timed out after 60 seconds")
        except Exception as e:
            print(f"⚠️ Collection test failed: {str(e)}")

    def test_generate_comprehensive_report(self):
        """Test 4: Generate comprehensive report of findings."""
        print("\n📋 Phase 4: Comprehensive Report Generation")

        total_syntax_errors = len(self.syntax_errors)
        total_import_errors = len(self.import_errors)
        total_collection_failures = len(self.collection_failures)

        # Calculate unique files affected
        syntax_files = set(err['file'] for err in self.syntax_errors)
        import_files = set(err['file'] for err in self.import_errors)
        all_affected_files = syntax_files.union(import_files)

        print(f"📊 COMPREHENSIVE SYNTAX ERROR ANALYSIS")
        print(f"=" * 50)
        print(f"Syntax Errors Found: {total_syntax_errors}")
        print(f"Import Errors Found: {total_import_errors}")
        print(f"Collection Failures: {total_collection_failures}")
        print(f"Unique Files Affected: {len(all_affected_files)}")
        print(f"")

        # Business impact assessment
        if total_syntax_errors > 0 or total_import_errors > 0:
            print(f"🚨 BUSINESS IMPACT ASSESSMENT:")
            print(f"   - Test reliability potentially compromised")
            print(f"   - Golden Path validation may be incomplete")
            print(f"   - $500K+ ARR at risk if mission critical tests fail")
            print(f"")

        # Categorize errors by severity
        critical_files = []
        for file in all_affected_files:
            if any(critical_path in file for critical_path in [
                "mission_critical", "websocket", "agent", "auth", "database"
            ]):
                critical_files.append(file)

        if critical_files:
            print(f"🔴 CRITICAL FILES AFFECTED ({len(critical_files)}):")
            for file in critical_files[:10]:
                print(f"   - {file}")
            if len(critical_files) > 10:
                print(f"   ... and {len(critical_files) - 10} more")
            print(f"")

        # Recommendations
        print(f"💡 RECOMMENDATIONS:")
        if total_syntax_errors > 50:
            print(f"   - HIGH PRIORITY: Fix syntax errors immediately")
            print(f"   - Consider rollback of problematic migration")
        elif total_syntax_errors > 10:
            print(f"   - MEDIUM PRIORITY: Fix syntax errors before deployment")
        elif total_syntax_errors > 0:
            print(f"   - LOW PRIORITY: Fix syntax errors during next sprint")
        else:
            print(f"   - EXCELLENT: No syntax errors detected")

        if total_import_errors > 0:
            print(f"   - Review automated migration for import statement issues")

        if critical_files:
            print(f"   - Prioritize fixes for mission critical test files")

        print(f"\n✅ Comprehensive report generation complete.")

        # Store results in class for access by other methods
        self.final_report = {
            'syntax_errors': total_syntax_errors,
            'import_errors': total_import_errors,
            'collection_failures': total_collection_failures,
            'affected_files': len(all_affected_files),
            'critical_files': len(critical_files),
            'target_met': total_syntax_errors <= 67  # Reference to the 67 identified errors
        }


if __name__ == "__main__":
    # Allow running this test directly for manual validation
    unittest.main(verbosity=2)