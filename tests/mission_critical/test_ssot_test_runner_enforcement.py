#!/usr/bin/env python3
# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: MISSION CRITICAL: SSOT Test Runner Enforcement
# REMOVED_SYNTAX_ERROR: ==============================================
# REMOVED_SYNTAX_ERROR: This test prevents the creation of additional test runners, enforcing the
# REMOVED_SYNTAX_ERROR: Single Source of Truth (SSOT) principle mandated by CLAUDE.md.

# REMOVED_SYNTAX_ERROR: The ONLY allowed test runner is tests/unified_test_runner.py.
# REMOVED_SYNTAX_ERROR: Any additional test runners will cause spacecraft test execution failure.
# REMOVED_SYNTAX_ERROR: '''

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
ALLOWED_LEGACY_WRAPPERS = { }
PROJECT_ROOT / "scripts" / "test_backend.py",
PROJECT_ROOT / "scripts" / "test_frontend.py",
PROJECT_ROOT / "test_framework" / "integrated_test_runner.py",
PROJECT_ROOT / "tests" / "staging" / "run_staging_tests.py",


# Allowed backup/original files
ALLOWED_BACKUP_PATTERNS = { }
"_ORIGINAL.py",
"_BACKUP.py",
"_OLD.py",
"_DEPRECATED_BACKUP.py"


# Paths to scan for test runners
SCAN_PATHS = [ ]
PROJECT_ROOT / "scripts",
PROJECT_ROOT / "tests",
PROJECT_ROOT / "test_framework",
PROJECT_ROOT / "netra_backend" / "tests",
PROJECT_ROOT / "auth_service" / "tests",
PROJECT_ROOT / "frontend" / "tests",
PROJECT_ROOT / "analytics_service" / "tests"



# REMOVED_SYNTAX_ERROR: def is_test_runner_file(file_path: Path) -> bool:
    # REMOVED_SYNTAX_ERROR: """Check if a file appears to be a test runner (very strict to avoid false positives)."""
    # REMOVED_SYNTAX_ERROR: if not file_path.is_file() or not file_path.name.endswith('.py'):
        # REMOVED_SYNTAX_ERROR: return False

        # Skip allowed backups
        # REMOVED_SYNTAX_ERROR: for pattern in ALLOWED_BACKUP_PATTERNS:
            # REMOVED_SYNTAX_ERROR: if file_path.name.endswith(pattern):
                # REMOVED_SYNTAX_ERROR: return False

                # Skip our own enforcement test
                # REMOVED_SYNTAX_ERROR: if file_path.name == 'test_ssot_test_runner_enforcement.py':
                    # REMOVED_SYNTAX_ERROR: return False

                    # VERY SPECIFIC filename patterns that indicate test runners (not regular tests)
                    # REMOVED_SYNTAX_ERROR: filename_lower = file_path.name.lower()
                    # REMOVED_SYNTAX_ERROR: specific_runner_patterns = [ )
                    # REMOVED_SYNTAX_ERROR: 'unified_test_runner.py',
                    # REMOVED_SYNTAX_ERROR: 'integrated_test_runner.py',
                    # REMOVED_SYNTAX_ERROR: 'test_backend.py',
                    # REMOVED_SYNTAX_ERROR: 'test_frontend.py',
                    # REMOVED_SYNTAX_ERROR: 'run_staging_tests.py',
                    # REMOVED_SYNTAX_ERROR: 'run_all_tests.py',
                    # REMOVED_SYNTAX_ERROR: 'test_suite_runner.py',
                    # REMOVED_SYNTAX_ERROR: 'cypress_runner.py',
                    # REMOVED_SYNTAX_ERROR: 'pytest_runner.py'
                    

                    # Only match exact filenames or very specific patterns
                    # REMOVED_SYNTAX_ERROR: if any(pattern == file_path.name.lower() for pattern in specific_runner_patterns):
                        # REMOVED_SYNTAX_ERROR: return True

                        # Check for files that explicitly call themselves test runners
                        # REMOVED_SYNTAX_ERROR: try:
                            # REMOVED_SYNTAX_ERROR: content = file_path.read_text(encoding='utf-8', errors='ignore')
                            # REMOVED_SYNTAX_ERROR: content_lower = content.lower()

                            # Must have BOTH main execution AND test runner behavior
                            # REMOVED_SYNTAX_ERROR: has_main = '__name__ == "__main__"' in content_lower
                            # REMOVED_SYNTAX_ERROR: has_argparse = 'argparse' in content_lower and 'argumentparser' in content_lower

                            # AND must have clear test execution behavior
                            # REMOVED_SYNTAX_ERROR: has_pytest_main = 'pytest.main(' in content_lower )
                            # REMOVED_SYNTAX_ERROR: has_subprocess_pytest = 'subprocess' in content_lower and 'pytest' in content_lower
                            # REMOVED_SYNTAX_ERROR: has_npm_test = 'subprocess' in content_lower and 'npm' in content_lower and 'test' in content_lower
                            # REMOVED_SYNTAX_ERROR: has_test_execution = has_pytest_main or has_subprocess_pytest or has_npm_test

                            # REMOVED_SYNTAX_ERROR: return has_main and has_argparse and has_test_execution

                            # REMOVED_SYNTAX_ERROR: except Exception:
                                # REMOVED_SYNTAX_ERROR: return False


# REMOVED_SYNTAX_ERROR: def find_all_test_runners() -> List[Path]:
    # REMOVED_SYNTAX_ERROR: """Find all potential test runner files."""
    # REMOVED_SYNTAX_ERROR: test_runners = []

    # REMOVED_SYNTAX_ERROR: for scan_path in SCAN_PATHS:
        # REMOVED_SYNTAX_ERROR: if not scan_path.exists():
            # REMOVED_SYNTAX_ERROR: continue

            # Recursive search for Python files
            # REMOVED_SYNTAX_ERROR: for file_path in scan_path.rglob('*.py'):
                # REMOVED_SYNTAX_ERROR: if is_test_runner_file(file_path):
                    # REMOVED_SYNTAX_ERROR: test_runners.append(file_path)

                    # REMOVED_SYNTAX_ERROR: return test_runners


# REMOVED_SYNTAX_ERROR: def verify_legacy_wrapper(file_path: Path) -> bool:
    # REMOVED_SYNTAX_ERROR: """Verify a file is a proper legacy wrapper that redirects to SSOT."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: content = file_path.read_text(encoding='utf-8', errors='ignore')

        # Must contain deprecation warning
        # REMOVED_SYNTAX_ERROR: if 'DEPRECATION WARNING' not in content and 'DEPRECATED' not in content:
            # REMOVED_SYNTAX_ERROR: return False

            # Must redirect to unified_test_runner.py
            # REMOVED_SYNTAX_ERROR: if 'unified_test_runner.py' not in content:
                # REMOVED_SYNTAX_ERROR: return False

                # Must not contain substantial test logic (should be wrapper only)
                # REMOVED_SYNTAX_ERROR: if 'pytest.main(' in content or 'unittest.main(' in content: ))
                # REMOVED_SYNTAX_ERROR: return False

                # REMOVED_SYNTAX_ERROR: return True

                # REMOVED_SYNTAX_ERROR: except Exception:
                    # REMOVED_SYNTAX_ERROR: return False


# REMOVED_SYNTAX_ERROR: class TestSSOTTestRunnerEnforcement:
    # REMOVED_SYNTAX_ERROR: """Enforce SSOT test runner policy."""

# REMOVED_SYNTAX_ERROR: def test_ssot_test_runner_exists(self):
    # REMOVED_SYNTAX_ERROR: """Verify the SSOT test runner exists."""
    # REMOVED_SYNTAX_ERROR: assert ALLOWED_TEST_RUNNER.exists(), ( )
    # REMOVED_SYNTAX_ERROR: "formatted_string"
    

    # Verify it's actually a test runner
    # REMOVED_SYNTAX_ERROR: assert is_test_runner_file(ALLOWED_TEST_RUNNER), ( )
    # REMOVED_SYNTAX_ERROR: "formatted_string"
    

# REMOVED_SYNTAX_ERROR: def test_no_duplicate_test_runners(self):
    # REMOVED_SYNTAX_ERROR: """Ensure no duplicate test runners exist."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: all_test_runners = find_all_test_runners()

    # Filter out allowed files
    # REMOVED_SYNTAX_ERROR: unauthorized_runners = []
    # REMOVED_SYNTAX_ERROR: for runner in all_test_runners:
        # REMOVED_SYNTAX_ERROR: if runner == ALLOWED_TEST_RUNNER:
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: if runner in ALLOWED_LEGACY_WRAPPERS:
                # Verify it's a proper deprecation wrapper
                # REMOVED_SYNTAX_ERROR: if not verify_legacy_wrapper(runner):
                    # REMOVED_SYNTAX_ERROR: unauthorized_runners.append( )
                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                    
                    # REMOVED_SYNTAX_ERROR: continue

                    # REMOVED_SYNTAX_ERROR: unauthorized_runners.append(str(runner))

                    # REMOVED_SYNTAX_ERROR: if unauthorized_runners:
                        # REMOVED_SYNTAX_ERROR: failure_msg = ( )
                        # REMOVED_SYNTAX_ERROR: "CRITICAL SSOT VIOLATION: Unauthorized test runners found!
                        # REMOVED_SYNTAX_ERROR: "
                        # REMOVED_SYNTAX_ERROR: "The spacecraft test execution requires a Single Source of Truth.
                        # REMOVED_SYNTAX_ERROR: "
                        # REMOVED_SYNTAX_ERROR: "Only tests/unified_test_runner.py is allowed.

                        # REMOVED_SYNTAX_ERROR: "
                        # REMOVED_SYNTAX_ERROR: "Unauthorized runners found:
                            # REMOVED_SYNTAX_ERROR: " +
                            # REMOVED_SYNTAX_ERROR: "
                            # REMOVED_SYNTAX_ERROR: ".join("formatted_string" for runner in unauthorized_runners) +
                            # REMOVED_SYNTAX_ERROR: "

                            # REMOVED_SYNTAX_ERROR: REMEDIATION:
                                # REMOVED_SYNTAX_ERROR: "
                                # REMOVED_SYNTAX_ERROR: "1. Remove unauthorized test runners
                                # REMOVED_SYNTAX_ERROR: "
                                # REMOVED_SYNTAX_ERROR: "2. Update scripts to use: python tests/unified_test_runner.py
                                # REMOVED_SYNTAX_ERROR: "
                                # REMOVED_SYNTAX_ERROR: "3. For service-specific tests use: --service backend|frontend
                                # REMOVED_SYNTAX_ERROR: "
                                # REMOVED_SYNTAX_ERROR: "4. For legacy compatibility, create deprecation wrappers only"
                                
                                # REMOVED_SYNTAX_ERROR: pytest.fail(failure_msg)

# REMOVED_SYNTAX_ERROR: def test_legacy_wrappers_are_proper_deprecation_wrappers(self):
    # REMOVED_SYNTAX_ERROR: """Verify legacy wrappers properly redirect to SSOT."""
    # REMOVED_SYNTAX_ERROR: failures = []

    # REMOVED_SYNTAX_ERROR: for wrapper_path in ALLOWED_LEGACY_WRAPPERS:
        # REMOVED_SYNTAX_ERROR: if not wrapper_path.exists():
            # REMOVED_SYNTAX_ERROR: continue  # Optional legacy wrapper

            # REMOVED_SYNTAX_ERROR: if not verify_legacy_wrapper(wrapper_path):
                # REMOVED_SYNTAX_ERROR: failures.append(str(wrapper_path))

                # REMOVED_SYNTAX_ERROR: if failures:
                    # REMOVED_SYNTAX_ERROR: failure_msg = ( )
                    # REMOVED_SYNTAX_ERROR: "CRITICAL: Legacy wrapper files are not proper deprecation wrappers!
                    # REMOVED_SYNTAX_ERROR: "
                    # REMOVED_SYNTAX_ERROR: "They must:
                        # REMOVED_SYNTAX_ERROR: "
                        # REMOVED_SYNTAX_ERROR: "1. Show DEPRECATION WARNING
                        # REMOVED_SYNTAX_ERROR: "
                        # REMOVED_SYNTAX_ERROR: "2. Redirect to tests/unified_test_runner.py
                        # REMOVED_SYNTAX_ERROR: "
                        # REMOVED_SYNTAX_ERROR: "3. Not contain substantial test logic

                        # REMOVED_SYNTAX_ERROR: "
                        # REMOVED_SYNTAX_ERROR: "Invalid wrappers:
                            # REMOVED_SYNTAX_ERROR: " +
                            # REMOVED_SYNTAX_ERROR: "
                            # REMOVED_SYNTAX_ERROR: ".join("formatted_string" for wrapper in failures)
                            
                            # REMOVED_SYNTAX_ERROR: pytest.fail(failure_msg)

# REMOVED_SYNTAX_ERROR: def test_unified_runner_has_service_compatibility(self):
    # REMOVED_SYNTAX_ERROR: """Verify unified runner supports legacy --service argument."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: content = ALLOWED_TEST_RUNNER.read_text(encoding='utf-8', errors='ignore')

    # REMOVED_SYNTAX_ERROR: assert '--service' in content, ( )
    # REMOVED_SYNTAX_ERROR: "CRITICAL: Unified test runner missing --service compatibility argument"
    

    # REMOVED_SYNTAX_ERROR: assert 'legacy compatibility' in content.lower(), ( )
    # REMOVED_SYNTAX_ERROR: "CRITICAL: Unified test runner missing legacy compatibility features"
    

# REMOVED_SYNTAX_ERROR: def test_ci_scripts_use_ssot_runner(self):
    # REMOVED_SYNTAX_ERROR: """Verify CI/CD scripts use the SSOT test runner."""
    # REMOVED_SYNTAX_ERROR: ci_paths = [ )
    # REMOVED_SYNTAX_ERROR: PROJECT_ROOT / ".github" / "workflows",
    # REMOVED_SYNTAX_ERROR: PROJECT_ROOT / ".github" / "scripts",
    # REMOVED_SYNTAX_ERROR: PROJECT_ROOT / "scripts"
    

    # REMOVED_SYNTAX_ERROR: problematic_files = []

    # REMOVED_SYNTAX_ERROR: for ci_path in ci_paths:
        # REMOVED_SYNTAX_ERROR: if not ci_path.exists():
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: for file_path in ci_path.rglob('*'):
                # REMOVED_SYNTAX_ERROR: if not file_path.is_file():
                    # REMOVED_SYNTAX_ERROR: continue

                    # REMOVED_SYNTAX_ERROR: try:
                        # REMOVED_SYNTAX_ERROR: content = file_path.read_text(encoding='utf-8', errors='ignore')
                        # REMOVED_SYNTAX_ERROR: content_lower = content.lower()

                        # Check for references to old test runners
                        # REMOVED_SYNTAX_ERROR: old_runners = [ )
                        # REMOVED_SYNTAX_ERROR: 'scripts/test_backend.py',
                        # REMOVED_SYNTAX_ERROR: 'scripts/test_frontend.py',
                        # REMOVED_SYNTAX_ERROR: 'test_framework/integrated_test_runner.py'
                        

                        # REMOVED_SYNTAX_ERROR: for old_runner in old_runners:
                            # REMOVED_SYNTAX_ERROR: if old_runner in content and 'unified_test_runner.py' not in content:
                                # REMOVED_SYNTAX_ERROR: problematic_files.append("formatted_string")

                                # REMOVED_SYNTAX_ERROR: except Exception:
                                    # REMOVED_SYNTAX_ERROR: continue

                                    # REMOVED_SYNTAX_ERROR: if problematic_files:
                                        # REMOVED_SYNTAX_ERROR: warning_msg = ( )
                                        # REMOVED_SYNTAX_ERROR: "WARNING: CI/CD scripts may reference old test runners.
                                        # REMOVED_SYNTAX_ERROR: "
                                        # REMOVED_SYNTAX_ERROR: "Consider updating to use tests/unified_test_runner.py:

                                            # REMOVED_SYNTAX_ERROR: " +
                                            # REMOVED_SYNTAX_ERROR: "
                                            # REMOVED_SYNTAX_ERROR: ".join("formatted_string" for issue in problematic_files) +
                                            # REMOVED_SYNTAX_ERROR: "

                                            # REMOVED_SYNTAX_ERROR: This is a warning, not a failure, but should be addressed."
                                            
                                            # REMOVED_SYNTAX_ERROR: print(warning_msg)


                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                # Can be run directly for validation
                                                # REMOVED_SYNTAX_ERROR: print("SSOT Test Runner Enforcement Validation")
                                                # REMOVED_SYNTAX_ERROR: print("=" * 50)

                                                # Find all test runners
                                                # REMOVED_SYNTAX_ERROR: all_runners = find_all_test_runners()
                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                # REMOVED_SYNTAX_ERROR: for runner in sorted(all_runners):
                                                    # REMOVED_SYNTAX_ERROR: if runner == ALLOWED_TEST_RUNNER:
                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                        # REMOVED_SYNTAX_ERROR: elif runner in ALLOWED_LEGACY_WRAPPERS:
                                                            # REMOVED_SYNTAX_ERROR: if verify_legacy_wrapper(runner):
                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                # REMOVED_SYNTAX_ERROR: else:
                                                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                    # REMOVED_SYNTAX_ERROR: else:
                                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                                        # REMOVED_SYNTAX_ERROR: if all_runners:
                                                                            # REMOVED_SYNTAX_ERROR: unauthorized = [r for r in all_runners )
                                                                            # REMOVED_SYNTAX_ERROR: if r != ALLOWED_TEST_RUNNER and r not in ALLOWED_LEGACY_WRAPPERS]
                                                                            # REMOVED_SYNTAX_ERROR: if unauthorized:
                                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                                # REMOVED_SYNTAX_ERROR: sys.exit(1)
                                                                                # REMOVED_SYNTAX_ERROR: else:
                                                                                    # REMOVED_SYNTAX_ERROR: print(f" )
                                                                                    # REMOVED_SYNTAX_ERROR: [OK] SSOT COMPLIANCE: Only authorized test runners found")
                                                                                    # REMOVED_SYNTAX_ERROR: else:
                                                                                        # REMOVED_SYNTAX_ERROR: print(" )
                                                                                        # REMOVED_SYNTAX_ERROR: [WARN] No test runners found")
                                                                                        # REMOVED_SYNTAX_ERROR: pass