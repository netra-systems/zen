#!/usr/bin/env python3
"""
MISSION CRITICAL: SSOT Test Runner Enforcement
==============================================
This test prevents the creation of additional test runners, enforcing the
Single Source of Truth (SSOT) principle mandated by CLAUDE.md.

The ONLY allowed test runner is tests/unified_test_runner.py.
Any additional test runners will cause spacecraft test execution failure.
"""

import os
import sys
from pathlib import Path
from typing import List, Set
import pytest
from shared.isolated_environment import IsolatedEnvironment

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()

# SSOT: The ONLY allowed test runner
ALLOWED_TEST_RUNNER = PROJECT_ROOT / "tests" / "unified_test_runner.py"

# Allowed legacy wrappers (deprecation wrappers that redirect to SSOT)
ALLOWED_LEGACY_WRAPPERS = {
    PROJECT_ROOT / "scripts" / "test_backend.py",
    PROJECT_ROOT / "scripts" / "test_frontend.py", 
    PROJECT_ROOT / "test_framework" / "integrated_test_runner.py",
    PROJECT_ROOT / "tests" / "staging" / "run_staging_tests.py",
}

# Allowed backup/original files
ALLOWED_BACKUP_PATTERNS = {
    "_ORIGINAL.py",
    "_BACKUP.py", 
    "_OLD.py",
    "_DEPRECATED_BACKUP.py"
}

# Paths to scan for test runners
SCAN_PATHS = [
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "tests", 
    PROJECT_ROOT / "test_framework",
    PROJECT_ROOT / "netra_backend" / "tests",
    PROJECT_ROOT / "auth_service" / "tests",
    PROJECT_ROOT / "frontend" / "tests",
    PROJECT_ROOT / "analytics_service" / "tests"
]


def is_test_runner_file(file_path: Path) -> bool:
    """Check if a file appears to be a test runner (very strict to avoid false positives)."""
    if not file_path.is_file() or not file_path.name.endswith('.py'):
        return False
    
    # Skip allowed backups
    for pattern in ALLOWED_BACKUP_PATTERNS:
        if file_path.name.endswith(pattern):
            return False
    
    # Skip our own enforcement test
    if file_path.name == 'test_ssot_test_runner_enforcement.py':
        return False
    
    # VERY SPECIFIC filename patterns that indicate test runners (not regular tests)
    filename_lower = file_path.name.lower()
    specific_runner_patterns = [
        'unified_test_runner.py',
        'integrated_test_runner.py',
        'test_backend.py',
        'test_frontend.py', 
        'run_staging_tests.py',
        'run_all_tests.py',
        'test_suite_runner.py',
        'cypress_runner.py',
        'pytest_runner.py'
    ]
    
    # Only match exact filenames or very specific patterns
    if any(pattern == file_path.name.lower() for pattern in specific_runner_patterns):
        return True
    
    # Check for files that explicitly call themselves test runners
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        content_lower = content.lower()
        
        # Must have BOTH main execution AND test runner behavior
        has_main = '__name__ == "__main__"' in content_lower
        has_argparse = 'argparse' in content_lower and 'argumentparser' in content_lower
        
        # AND must have clear test execution behavior
        has_pytest_main = 'pytest.main(' in content_lower
        has_subprocess_pytest = 'subprocess' in content_lower and 'pytest' in content_lower
        has_npm_test = 'subprocess' in content_lower and 'npm' in content_lower and 'test' in content_lower
        has_test_execution = has_pytest_main or has_subprocess_pytest or has_npm_test
        
        return has_main and has_argparse and has_test_execution
        
    except Exception:
        return False


def find_all_test_runners() -> List[Path]:
    """Find all potential test runner files."""
    test_runners = []
    
    for scan_path in SCAN_PATHS:
        if not scan_path.exists():
            continue
            
        # Recursive search for Python files
        for file_path in scan_path.rglob('*.py'):
            if is_test_runner_file(file_path):
                test_runners.append(file_path)
    
    return test_runners


def verify_legacy_wrapper(file_path: Path) -> bool:
    """Verify a file is a proper legacy wrapper that redirects to SSOT."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        # Must contain deprecation warning
        if 'DEPRECATION WARNING' not in content and 'DEPRECATED' not in content:
            return False
        
        # Must redirect to unified_test_runner.py
        if 'unified_test_runner.py' not in content:
            return False
            
        # Must not contain substantial test logic (should be wrapper only)
        if 'pytest.main(' in content or 'unittest.main(' in content:
            return False
            
        return True
        
    except Exception:
        return False


class TestSSOTTestRunnerEnforcement:
    """Enforce SSOT test runner policy."""
    
    def test_ssot_test_runner_exists(self):
        """Verify the SSOT test runner exists."""
        assert ALLOWED_TEST_RUNNER.exists(), (
            f"CRITICAL: SSOT test runner missing: {ALLOWED_TEST_RUNNER}"
        )
        
        # Verify it's actually a test runner
        assert is_test_runner_file(ALLOWED_TEST_RUNNER), (
            f"CRITICAL: SSOT file is not a proper test runner: {ALLOWED_TEST_RUNNER}"
        )
    
    def test_no_duplicate_test_runners(self):
        """Ensure no duplicate test runners exist."""
    pass
        all_test_runners = find_all_test_runners()
        
        # Filter out allowed files
        unauthorized_runners = []
        for runner in all_test_runners:
            if runner == ALLOWED_TEST_RUNNER:
                continue
                
            if runner in ALLOWED_LEGACY_WRAPPERS:
                # Verify it's a proper deprecation wrapper
                if not verify_legacy_wrapper(runner):
                    unauthorized_runners.append(
                        f"{runner} - INVALID: Not a proper deprecation wrapper"
                    )
                continue
            
            unauthorized_runners.append(str(runner))
        
        if unauthorized_runners:
            failure_msg = (
                "CRITICAL SSOT VIOLATION: Unauthorized test runners found!
"
                "The spacecraft test execution requires a Single Source of Truth.
"
                "Only tests/unified_test_runner.py is allowed.

"
                "Unauthorized runners found:
" +
                "
".join(f"  - {runner}" for runner in unauthorized_runners) +
                "

REMEDIATION:
"
                "1. Remove unauthorized test runners
"
                "2. Update scripts to use: python tests/unified_test_runner.py
"
                "3. For service-specific tests use: --service backend|frontend
"
                "4. For legacy compatibility, create deprecation wrappers only"
            )
            pytest.fail(failure_msg)
    
    def test_legacy_wrappers_are_proper_deprecation_wrappers(self):
        """Verify legacy wrappers properly redirect to SSOT."""
        failures = []
        
        for wrapper_path in ALLOWED_LEGACY_WRAPPERS:
            if not wrapper_path.exists():
                continue  # Optional legacy wrapper
                
            if not verify_legacy_wrapper(wrapper_path):
                failures.append(str(wrapper_path))
        
        if failures:
            failure_msg = (
                "CRITICAL: Legacy wrapper files are not proper deprecation wrappers!
"
                "They must:
"
                "1. Show DEPRECATION WARNING
"
                "2. Redirect to tests/unified_test_runner.py
"
                "3. Not contain substantial test logic

"
                "Invalid wrappers:
" +
                "
".join(f"  - {wrapper}" for wrapper in failures)
            )
            pytest.fail(failure_msg)
    
    def test_unified_runner_has_service_compatibility(self):
        """Verify unified runner supports legacy --service argument."""
    pass
        content = ALLOWED_TEST_RUNNER.read_text(encoding='utf-8', errors='ignore')
        
        assert '--service' in content, (
            "CRITICAL: Unified test runner missing --service compatibility argument"
        )
        
        assert 'legacy compatibility' in content.lower(), (
            "CRITICAL: Unified test runner missing legacy compatibility features"
        )
    
    def test_ci_scripts_use_ssot_runner(self):
        """Verify CI/CD scripts use the SSOT test runner."""
        ci_paths = [
            PROJECT_ROOT / ".github" / "workflows",
            PROJECT_ROOT / ".github" / "scripts", 
            PROJECT_ROOT / "scripts"
        ]
        
        problematic_files = []
        
        for ci_path in ci_paths:
            if not ci_path.exists():
                continue
                
            for file_path in ci_path.rglob('*'):
                if not file_path.is_file():
                    continue
                    
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    content_lower = content.lower()
                    
                    # Check for references to old test runners
                    old_runners = [
                        'scripts/test_backend.py',
                        'scripts/test_frontend.py',
                        'test_framework/integrated_test_runner.py'
                    ]
                    
                    for old_runner in old_runners:
                        if old_runner in content and 'unified_test_runner.py' not in content:
                            problematic_files.append(f"{file_path}: references {old_runner}")
                            
                except Exception:
                    continue
        
        if problematic_files:
            warning_msg = (
                "WARNING: CI/CD scripts may reference old test runners.
"
                "Consider updating to use tests/unified_test_runner.py:

" +
                "
".join(f"  - {issue}" for issue in problematic_files) +
                "

This is a warning, not a failure, but should be addressed."
            )
            print(warning_msg)


if __name__ == "__main__":
    # Can be run directly for validation
    print("SSOT Test Runner Enforcement Validation")
    print("=" * 50)
    
    # Find all test runners
    all_runners = find_all_test_runners()
    print(f"Found {len(all_runners)} potential test runner files:")
    
    for runner in sorted(all_runners):
        if runner == ALLOWED_TEST_RUNNER:
            print(f"  [OK] {runner} (SSOT - ALLOWED)")
        elif runner in ALLOWED_LEGACY_WRAPPERS:
            if verify_legacy_wrapper(runner):
                print(f"  [WARN] {runner} (Legacy wrapper - ALLOWED)")
            else:
                print(f"  [FAIL] {runner} (Invalid legacy wrapper - VIOLATION)")
        else:
            print(f"  [FAIL] {runner} (UNAUTHORIZED - VIOLATION)")
    
    print(f"
SSOT Runner: {ALLOWED_TEST_RUNNER}")
    print(f"Exists: {ALLOWED_TEST_RUNNER.exists()}")
    
    if all_runners:
        unauthorized = [r for r in all_runners 
                       if r != ALLOWED_TEST_RUNNER and r not in ALLOWED_LEGACY_WRAPPERS]
        if unauthorized:
            print(f"
[FAIL] SSOT VIOLATION: {len(unauthorized)} unauthorized test runners found!")
            sys.exit(1)
        else:
            print(f"
[OK] SSOT COMPLIANCE: Only authorized test runners found")
    else:
        print("
[WARN] No test runners found")
    pass