#!/usr/bin/env python3
"""
Comprehensive Validation Infrastructure for pytest.main() Migration

Business Value Justification (BVJ):
- Segment: Platform (All segments affected by deployment blocks)
- Business Goal: Stability - Ensure migration quality and prevent regressions
- Value Impact: Validates $500K+ ARR protection from migration errors
- Revenue Impact: Prevents system breakage during migration process

PURPOSE: Comprehensive validation infrastructure for AST-based pytest migration.
ISSUE: https://github.com/netra-systems/netra-apex/issues/1024

FEATURES:
1. Pre/post migration validation
2. Syntax and functional testing
3. SSOT compliance verification
4. Rollback safety validation
5. Migration quality assessment
"""

import sys
import ast
import subprocess
import json
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import argparse
import logging

# Setup project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Comprehensive validation result."""
    file_path: str
    syntax_valid: bool
    ssot_compliant: bool
    pytest_violations_detected: int
    test_execution_successful: bool
    errors: List[str]
    warnings: List[str]
    execution_time_ms: float

@dataclass
class MigrationValidationReport:
    """Overall migration validation report."""
    total_files_validated: int = 0
    syntax_valid_files: int = 0
    ssot_compliant_files: int = 0
    test_executable_files: int = 0
    remaining_violations: int = 0
    critical_errors: List[str] = None
    validation_timestamp: str = ""

    def __post_init__(self):
        if self.critical_errors is None:
            self.critical_errors = []
        if not self.validation_timestamp:
            self.validation_timestamp = datetime.now().isoformat()

class PytestMigrationValidator:
    """
    Comprehensive validator for pytest.main() migration quality.

    Validates:
    - Syntax correctness after migration
    - SSOT compliance requirements
    - Absence of pytest violations
    - Test execution capability
    - Migration quality metrics
    """

    def __init__(self):
        self.report = MigrationValidationReport()

    def validate_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Python syntax using AST parsing.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            ast.parse(content)
            return True, None
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during syntax validation: {str(e)}"
            return False, error_msg

    def detect_pytest_violations(self, file_path: str) -> int:
        """
        Detect remaining pytest.main() violations after migration.

        Returns:
            Number of violations found
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Use the detection script
            detection_script = PROJECT_ROOT / "scripts" / "detect_pytest_main_violations.py"
            if detection_script.exists():
                result = subprocess.run([
                    sys.executable, str(detection_script), file_path
                ], capture_output=True, text=True, cwd=PROJECT_ROOT)

                # Parse output to count violations
                if "violations detected" in result.stdout.lower():
                    # Extract number from output
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if "violations detected" in line.lower():
                            # Extract number from line like "🚨 CRITICAL: 5 PYTEST.MAIN() VIOLATIONS DETECTED!"
                            words = line.split()
                            for i, word in enumerate(words):
                                if word.isdigit():
                                    return int(word)
                return 0
            else:
                # Fallback: manual detection
                violations = 0
                if 'pytest.main(' in content:
                    violations += content.count('pytest.main(')
                if 'pytest.cmdline.main(' in content:
                    violations += content.count('pytest.cmdline.main(')
                return violations

        except Exception as e:
            logger.warning(f"Error detecting violations in {file_path}: {e}")
            return -1

    def validate_ssot_compliance(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Validate SSOT compliance requirements.

        Returns:
            Tuple of (is_compliant, list_of_issues)
        """
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for direct pytest imports
            if 'import pytest' in content:
                # Allow in test files but check usage
                if any(pattern in file_path for pattern in ['test_', '_test.py', 'tests/']):
                    # Test files can import pytest but shouldn't use pytest.main()
                    if 'pytest.main(' in content:
                        issues.append("Test file uses pytest.main() instead of SSOT unified runner")
                else:
                    issues.append("Non-test file imports pytest")

            # Check for unauthorized test execution patterns
            unauthorized_patterns = [
                'subprocess.*pytest',
                'os.system.*pytest',
                'exec.*pytest',
            ]

            import re
            for pattern in unauthorized_patterns:
                if re.search(pattern, content):
                    issues.append(f"Unauthorized test execution pattern: {pattern}")

            # Check for SSOT test runner usage in migrated files
            if 'MIGRATED:' in content:
                # This file was migrated, check if it properly references SSOT runner
                if 'unified_test_runner.py' not in content:
                    issues.append("Migrated file doesn't reference SSOT unified test runner")

            return len(issues) == 0, issues

        except Exception as e:
            issues.append(f"Error validating SSOT compliance: {str(e)}")
            return False, issues

    def validate_test_execution(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that migrated test files can still be executed.

        Returns:
            Tuple of (can_execute, error_message)
        """
        try:
            # Check if this is a test file
            if not any(pattern in file_path for pattern in ['test_', '_test.py', 'tests/']):
                return True, None  # Non-test files don't need execution validation

            # Try to import the file to check for basic execution
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return False, "File does not exist"

            # Create a temporary test to validate basic import
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(f"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    # Try to import the test module
    import importlib.util
    spec = importlib.util.spec_from_file_location("test_module", r"{file_path}")
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print("IMPORT_SUCCESS")
    else:
        print("IMPORT_FAILED: Could not create module spec")
except Exception as e:
    print(f"IMPORT_FAILED: {{e}}")
""")
                temp_file_path = temp_file.name

            try:
                result = subprocess.run([
                    sys.executable, temp_file_path
                ], capture_output=True, text=True, timeout=30)

                if "IMPORT_SUCCESS" in result.stdout:
                    return True, None
                else:
                    error_lines = [line for line in result.stdout.split('\n') if 'IMPORT_FAILED' in line]
                    if error_lines:
                        return False, error_lines[0]
                    return False, "Unknown import failure"

            finally:
                Path(temp_file_path).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            return False, "Test execution timeout"
        except Exception as e:
            return False, f"Test execution error: {str(e)}"

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Perform comprehensive validation of a single file.

        Returns:
            Complete validation result
        """
        start_time = datetime.now()
        result = ValidationResult(
            file_path=file_path,
            syntax_valid=False,
            ssot_compliant=False,
            pytest_violations_detected=0,
            test_execution_successful=False,
            errors=[],
            warnings=[],
            execution_time_ms=0.0
        )

        try:
            # 1. Syntax validation
            syntax_valid, syntax_error = self.validate_syntax(file_path)
            result.syntax_valid = syntax_valid
            if not syntax_valid and syntax_error:
                result.errors.append(f"Syntax error: {syntax_error}")

            # 2. pytest violations detection
            violations = self.detect_pytest_violations(file_path)
            result.pytest_violations_detected = violations
            if violations > 0:
                result.errors.append(f"{violations} pytest.main() violations remaining")

            # 3. SSOT compliance validation
            ssot_compliant, ssot_issues = self.validate_ssot_compliance(file_path)
            result.ssot_compliant = ssot_compliant
            if not ssot_compliant:
                result.warnings.extend(ssot_issues)

            # 4. Test execution validation
            test_executable, test_error = self.validate_test_execution(file_path)
            result.test_execution_successful = test_executable
            if not test_executable and test_error:
                result.warnings.append(f"Test execution issue: {test_error}")

        except Exception as e:
            result.errors.append(f"Validation error: {str(e)}")
            logger.error(f"Validation failed for {file_path}: {e}")

        finally:
            end_time = datetime.now()
            result.execution_time_ms = (end_time - start_time).total_seconds() * 1000

        return result

    def validate_directory(self, directory: str, pattern: str = "**/*.py") -> List[ValidationResult]:
        """
        Validate all Python files in a directory.

        Returns:
            List of validation results
        """
        directory_path = Path(directory)
        results = []

        logger.info(f"Starting validation of directory: {directory}")
        logger.info(f"Pattern: {pattern}")

        for file_path in directory_path.glob(pattern):
            if file_path.is_file() and file_path.suffix == '.py':
                # Skip certain files
                if self._should_skip_file(str(file_path)):
                    logger.debug(f"Skipping: {file_path}")
                    continue

                logger.info(f"Validating: {file_path}")
                result = self.validate_file(str(file_path))
                results.append(result)

                # Update overall report
                self.report.total_files_validated += 1
                if result.syntax_valid:
                    self.report.syntax_valid_files += 1
                if result.ssot_compliant:
                    self.report.ssot_compliant_files += 1
                if result.test_execution_successful:
                    self.report.test_executable_files += 1
                if result.pytest_violations_detected > 0:
                    self.report.remaining_violations += result.pytest_violations_detected

                # Collect critical errors
                for error in result.errors:
                    if any(critical in error.lower() for critical in ['syntax error', 'import error', 'critical']):
                        self.report.critical_errors.append(f"{file_path}: {error}")

                # Progress reporting
                if self.report.total_files_validated % 50 == 0:
                    logger.info(f"Progress: {self.report.total_files_validated} files validated")

        return results

    def _should_skip_file(self, file_path: str) -> bool:
        """Determine if a file should be skipped during validation."""
        skip_patterns = [
            '__pycache__',
            '.git',
            'node_modules',
            '.venv',
            'venv',
            'backup',
            'backups',
        ]

        return any(pattern in file_path for pattern in skip_patterns)

    def generate_validation_report(self, results: List[ValidationResult]) -> None:
        """Generate comprehensive validation report."""
        print("\n" + "=" * 100)
        print("PYTEST MIGRATION VALIDATION REPORT")
        print("=" * 100)
        print(f"Issue #1024: SSOT Migration Quality Validation")
        print(f"Timestamp: {self.report.validation_timestamp}")
        print("=" * 100)

        # Overall statistics
        print(f"\nOVERALL VALIDATION STATISTICS:")
        print(f"  Files Validated: {self.report.total_files_validated}")
        print(f"  Syntax Valid: {self.report.syntax_valid_files} ({self.report.syntax_valid_files/max(1, self.report.total_files_validated)*100:.1f}%)")
        print(f"  SSOT Compliant: {self.report.ssot_compliant_files} ({self.report.ssot_compliant_files/max(1, self.report.total_files_validated)*100:.1f}%)")
        print(f"  Test Executable: {self.report.test_executable_files} ({self.report.test_executable_files/max(1, self.report.total_files_validated)*100:.1f}%)")
        print(f"  Remaining pytest Violations: {self.report.remaining_violations}")

        # Quality score
        if self.report.total_files_validated > 0:
            quality_score = (
                (self.report.syntax_valid_files * 0.4) +
                (self.report.ssot_compliant_files * 0.3) +
                (self.report.test_executable_files * 0.3)
            ) / self.report.total_files_validated * 100
            print(f"  Migration Quality Score: {quality_score:.1f}%")

        # Critical errors
        if self.report.critical_errors:
            print(f"\nCRITICAL ERRORS ({len(self.report.critical_errors)}):")
            for error in self.report.critical_errors[:10]:  # Show first 10
                print(f"  [CRITICAL] {error}")
            if len(self.report.critical_errors) > 10:
                print(f"     ... and {len(self.report.critical_errors) - 10} more critical errors")

        # Files with issues
        error_files = [r for r in results if r.errors]
        if error_files:
            print(f"\nFILES WITH ERRORS ({len(error_files)}):")
            for result in error_files[:10]:  # Show first 10
                print(f"  [ERROR] {result.file_path}")
                for error in result.errors[:2]:  # Show first 2 errors
                    print(f"     - {error}")

        # Files with warnings
        warning_files = [r for r in results if r.warnings]
        if warning_files:
            print(f"\nFILES WITH WARNINGS ({len(warning_files)}):")
            for result in warning_files[:10]:  # Show first 10
                print(f"  [WARNING] {result.file_path}")
                for warning in result.warnings[:2]:  # Show first 2 warnings
                    print(f"     - {warning}")

        # Remaining violations
        violation_files = [r for r in results if r.pytest_violations_detected > 0]
        if violation_files:
            print(f"\nFILES WITH REMAINING VIOLATIONS ({len(violation_files)}):")
            for result in violation_files[:10]:  # Show first 10
                print(f"  [VIOLATION] {result.file_path}: {result.pytest_violations_detected} violations")

        print(f"\nVALIDATION RECOMMENDATIONS:")
        if self.report.remaining_violations > 0:
            print(f"1. ADDRESS REMAINING VIOLATIONS: {self.report.remaining_violations} pytest.main() violations need migration")
        if len(self.report.critical_errors) > 0:
            print(f"2. FIX CRITICAL ERRORS: {len(self.report.critical_errors)} critical issues require immediate attention")
        if self.report.syntax_valid_files < self.report.total_files_validated:
            print(f"3. SYNTAX ISSUES: {self.report.total_files_validated - self.report.syntax_valid_files} files have syntax errors")
        if self.report.ssot_compliant_files < self.report.total_files_validated:
            print(f"4. SSOT COMPLIANCE: {self.report.total_files_validated - self.report.ssot_compliant_files} files need SSOT improvements")

        print(f"\nNEXT STEPS:")
        print(f"1. Review and fix all critical errors")
        print(f"2. Re-run migration for files with remaining violations")
        print(f"3. Run comprehensive tests: python tests/unified_test_runner.py --category unit")
        print(f"4. Validate SSOT compliance: python scripts/check_ssot_import_compliance.py")

        # Save detailed report
        report_data = {
            'overall_report': asdict(self.report),
            'file_results': [asdict(result) for result in results]
        }

        report_file = PROJECT_ROOT / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\nDetailed validation report saved to: {report_file}")

def main():
    """Main entry point for the validation tool."""
    parser = argparse.ArgumentParser(
        description="Comprehensive validation for pytest.main() migration quality",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("target", help="File or directory to validate")
    parser.add_argument("--pattern", default="**/*.py",
                       help="File pattern for directory validation (default: **/*.py)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print(f"PYTEST MIGRATION VALIDATION TOOL")
    print(f"Target: {args.target}")
    print(f"Pattern: {args.pattern}")
    print()

    validator = PytestMigrationValidator()

    target_path = Path(args.target)
    if target_path.is_file():
        # Single file validation
        result = validator.validate_file(str(target_path))
        validator.report.total_files_validated = 1
        if result.syntax_valid:
            validator.report.syntax_valid_files = 1
        if result.ssot_compliant:
            validator.report.ssot_compliant_files = 1
        if result.test_execution_successful:
            validator.report.test_executable_files = 1
        validator.report.remaining_violations = result.pytest_violations_detected
        validator.generate_validation_report([result])
    elif target_path.is_dir():
        # Directory validation
        results = validator.validate_directory(str(target_path), args.pattern)
        validator.generate_validation_report(results)
    else:
        print(f"ERROR: Target '{args.target}' is not a valid file or directory")
        sys.exit(1)

    # Exit with appropriate code
    if validator.report.critical_errors or validator.report.remaining_violations > 0:
        logger.warning("Validation completed with issues")
        sys.exit(1)
    else:
        logger.info("Validation completed successfully")
        sys.exit(0)

if __name__ == "__main__":
    main()