#!/usr/bin/env python3
"""
Test Import Validation Script

Validates that all test module __init__.py files can be imported successfully,
preventing import name mismatches from incomplete SSOT refactoring.

This addresses the Five Whys root cause analysis:
- WHY: Import statements are outdated after class renaming during SSOT consolidation
- WHY: Test class definitions don't match their import statements in __init__.py files
- WHY: Development process lacks import validation

Usage:
    python scripts/validate_test_imports.py                    # Validate all test modules
    python scripts/validate_test_imports.py --fast             # Skip slow modules
    python scripts/validate_test_imports.py --service auth     # Validate specific service
    python scripts/validate_test_imports.py --ci               # CI-friendly output

Exit codes:
    0: All imports successful
    1: Some imports failed
    2: Critical failures (>50% failure rate)
"""

import sys
import argparse
import importlib
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Test modules to validate (discovered automatically but can be overridden)
DEFAULT_TEST_MODULES = [
    # Auth Service Tests
    'auth_service.tests.base',
    'auth_service.tests.config',
    'auth_service.tests.factories',
    'auth_service.tests.utils',

    # Backend Service Tests
    'netra_backend.tests.unit',
    'netra_backend.tests.core',
    'netra_backend.tests.agents.data_helper',
    'netra_backend.tests.e2e',

    # Test Framework
    'test_framework.ssot.base_test_case',
    'test_framework.base',

    # Shared Tests
    'shared.tests.unit.test_isolated_environment',
]

# Service-specific module groups
SERVICE_MODULES = {
    'auth': [
        'auth_service.tests.base',
        'auth_service.tests.config',
        'auth_service.tests.factories',
        'auth_service.tests.utils',
    ],
    'backend': [
        'netra_backend.tests.unit',
        'netra_backend.tests.core',
        'netra_backend.tests.agents.data_helper',
        'netra_backend.tests.e2e',
    ],
    'shared': [
        'test_framework.ssot.base_test_case',
        'test_framework.base',
        'shared.tests.unit.test_isolated_environment',
    ]
}

class ImportValidator:
    def __init__(self, ci_mode: bool = False, verbose: bool = True):
        self.ci_mode = ci_mode
        self.verbose = verbose
        self.results: List[Tuple[str, bool, str]] = []

    def log(self, message: str, level: str = "INFO"):
        """Log message with appropriate formatting"""
        if self.ci_mode:
            if level == "ERROR":
                print(f"::error::{message}")
            elif level == "WARNING":
                print(f"::warning::{message}")
            else:
                print(message)
        elif self.verbose:
            print(message)

    def validate_module(self, module_name: str) -> Tuple[bool, str]:
        """
        Validate a single module import

        Returns:
            (success: bool, error_message: str)
        """
        try:
            start_time = time.time()
            importlib.import_module(module_name)
            elapsed = time.time() - start_time

            if elapsed > 10.0:  # Warn about slow imports
                self.log(f"SLOW: {module_name} took {elapsed:.1f}s to import", "WARNING")

            return True, ""

        except Exception as e:
            error_msg = str(e)
            # Clean up common error messages
            if "No module named" in error_msg:
                error_msg = f"Missing module: {error_msg.split('No module named ')[-1]}"
            return False, error_msg

    def validate_modules(self, modules: List[str]) -> Dict[str, Any]:
        """
        Validate a list of modules

        Returns:
            Dict with validation results and statistics
        """
        self.log("Test Import Validation Starting")
        self.log("=" * 50)

        successful_imports = []
        failed_imports = []

        for module in modules:
            success, error = self.validate_module(module)
            self.results.append((module, success, error))

            if success:
                successful_imports.append(module)
                self.log(f"PASS: {module}")
            else:
                failed_imports.append((module, error))
                self.log(f"FAIL: {module} - {error}", "ERROR")

        # Calculate statistics
        total_modules = len(modules)
        success_count = len(successful_imports)
        failure_count = len(failed_imports)
        success_rate = (success_count / total_modules) * 100 if total_modules > 0 else 0

        # Summary
        self.log("")
        self.log(f"SUMMARY: {success_count}/{total_modules} imports successful")
        self.log(f"Success rate: {success_rate:.1f}%")

        if failed_imports:
            self.log("")
            self.log("FAILED IMPORTS:")
            for module, error in failed_imports:
                self.log(f"  - {module}: {error}", "ERROR")

        return {
            'total_modules': total_modules,
            'successful_imports': successful_imports,
            'failed_imports': failed_imports,
            'success_count': success_count,
            'failure_count': failure_count,
            'success_rate': success_rate,
            'results': self.results
        }

def discover_test_modules() -> List[str]:
    """
    Automatically discover test modules by scanning for __init__.py files
    in test directories
    """
    test_modules = []

    # Common test directory patterns
    test_patterns = [
        "*/tests/__init__.py",
        "*/tests/*/__init__.py",
        "test_framework/*/__init__.py"
    ]

    project_root = Path(__file__).parent.parent

    for pattern in test_patterns:
        for init_file in project_root.glob(pattern):
            # Convert path to module name
            relative_path = init_file.relative_to(project_root)
            module_parts = list(relative_path.parts[:-1])  # Remove __init__.py
            module_name = ".".join(module_parts)

            # Filter out problematic patterns
            if not any(skip in module_name for skip in ['__pycache__', '.git', 'node_modules']):
                test_modules.append(module_name)

    return sorted(list(set(test_modules)))

def main():
    parser = argparse.ArgumentParser(description="Validate test module imports")
    parser.add_argument('--fast', action='store_true',
                        help='Skip slow/heavy modules for faster validation')
    parser.add_argument('--service', choices=['auth', 'backend', 'shared'],
                        help='Validate specific service modules only')
    parser.add_argument('--ci', action='store_true',
                        help='CI-friendly output with GitHub Actions annotations')
    parser.add_argument('--discover', action='store_true',
                        help='Auto-discover test modules instead of using defaults')
    parser.add_argument('--verbose', action='store_true', default=True,
                        help='Verbose output (default: True)')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress verbose output')

    args = parser.parse_args()

    # Determine modules to validate
    if args.service:
        modules = SERVICE_MODULES[args.service]
    elif args.discover:
        modules = discover_test_modules()
    else:
        modules = DEFAULT_TEST_MODULES

    # Filter out slow modules if requested
    if args.fast:
        # Remove modules known to be slow
        slow_modules = [
            'netra_backend.tests.e2e',
            'test_framework.ssot.base_test_case'
        ]
        modules = [m for m in modules if m not in slow_modules]

    # Create validator
    verbose = args.verbose and not args.quiet
    validator = ImportValidator(ci_mode=args.ci, verbose=verbose)

    # Run validation
    results = validator.validate_modules(modules)

    # Determine exit code
    success_rate = results['success_rate']
    failure_count = results['failure_count']

    if failure_count == 0:
        exit_code = 0  # Perfect success
    elif success_rate < 50:
        exit_code = 2  # Critical failure
    else:
        exit_code = 1  # Some failures

    # Final status
    if args.ci:
        if exit_code == 0:
            print("::notice::All test imports validated successfully")
        else:
            print(f"::error::Import validation failed with {failure_count} failures")

    sys.exit(exit_code)

if __name__ == "__main__":
    main()