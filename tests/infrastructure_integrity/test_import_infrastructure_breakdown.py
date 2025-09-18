#!/usr/bin/env python
"""
ISSUE #1176 - IMPORT INFRASTRUCTURE BREAKDOWN VALIDATION
=======================================================

This test suite validates critical import paths and exposes:
1. Missing modules that break test collection
2. Circular import dependencies
3. SSOT import registry inconsistencies
4. Silent import failures that mask test execution

BUSINESS IMPACT: Import failures prevent test execution, creating false confidence
"""

import pytest
import subprocess
import sys
import os
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


class TestImportInfrastructureBreakdown:
    """Validate critical import infrastructure integrity."""

    def test_ssot_imports_registry_consistency(self):
        """
        Validate that all imports listed in SSOT_IMPORT_REGISTRY.md actually work.

        This exposes the gap between documented SSOT patterns and reality.
        """
        ssot_registry_path = PROJECT_ROOT / "SSOT_IMPORT_REGISTRY.md"

        if not ssot_registry_path.exists():
            pytest.fail(f"SSOT_IMPORT_REGISTRY.md not found at {ssot_registry_path}")

        # Parse the registry for import statements
        import_failures = []
        documented_imports = []

        with open(ssot_registry_path, 'r') as f:
            content = f.read()

        # Extract import patterns from the registry
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('from ') or line.startswith('import '):
                # Clean up markdown formatting
                import_line = line.replace('`', '').strip()
                documented_imports.append(import_line)

        print(f"Found {len(documented_imports)} documented imports in SSOT registry")

        # Test each documented import
        for import_statement in documented_imports:
            try:
                # Execute the import statement
                result = subprocess.run([
                    sys.executable, '-c',
                    f'{import_statement}; print("SUCCESS: {import_statement}")'
                ], capture_output=True, text=True, cwd=PROJECT_ROOT)

                if result.returncode != 0:
                    import_failures.append({
                        "import": import_statement,
                        "error": result.stderr.strip(),
                        "registry_source": "SSOT_IMPORT_REGISTRY.md"
                    })

            except Exception as e:
                import_failures.append({
                    "import": import_statement,
                    "error": str(e),
                    "registry_source": "SSOT_IMPORT_REGISTRY.md"
                })

        if import_failures:
            failure_details = json.dumps(import_failures, indent=2)
            pytest.fail(f"SSOT IMPORT REGISTRY BREAKDOWN: {len(import_failures)} documented imports failed:\n{failure_details}")

    def test_critical_test_framework_imports(self):
        """
        Test the most critical test framework imports that test execution depends on.
        """
        critical_test_imports = [
            # SSOT Test Framework
            "test_framework.ssot.base_test_case",
            "test_framework.ssot.mock_factory",
            "test_framework.ssot.database_test_utility",
            "test_framework.ssot.websocket_test_utility",
            "test_framework.ssot.orchestration",
            "test_framework.ssot.orchestration_enums",

            # Core Backend
            "netra_backend.app.config",
            "netra_backend.app.core.configuration.base",
            "netra_backend.app.websocket_core.manager",
            "netra_backend.app.agents.registry",

            # Shared Infrastructure
            "shared.cors_config",
            "dev_launcher.isolated_environment",

            # Test Infrastructure
            "tests.conftest",
        ]

        import_failures = []

        for import_path in critical_test_imports:
            try:
                result = subprocess.run([
                    sys.executable, '-c',
                    f'import {import_path}; print("SUCCESS: {import_path}")'
                ], capture_output=True, text=True, cwd=PROJECT_ROOT)

                if result.returncode != 0:
                    import_failures.append({
                        "import": import_path,
                        "error": result.stderr.strip(),
                        "category": "critical_test_framework"
                    })

            except Exception as e:
                import_failures.append({
                    "import": import_path,
                    "error": str(e),
                    "category": "critical_test_framework"
                })

        if import_failures:
            failure_details = json.dumps(import_failures, indent=2)
            pytest.fail(f"CRITICAL TEST FRAMEWORK IMPORTS FAILED: {len(import_failures)} imports broken:\n{failure_details}")

    def test_circular_dependency_detection(self):
        """
        Detect circular dependencies that can cause import failures in tests.
        """
        # Test known problematic import patterns
        circular_test_cases = [
            # Test potential circular dependencies
            ("netra_backend.app.config", "netra_backend.app.core.configuration.base"),
            ("test_framework.ssot.base_test_case", "tests.conftest"),
            ("netra_backend.app.websocket_core.manager", "netra_backend.app.agents.registry"),
        ]

        circular_dependencies = []

        for module_a, module_b in circular_test_cases:
            try:
                # Try importing A then B
                result_a_then_b = subprocess.run([
                    sys.executable, '-c',
                    f'import {module_a}; import {module_b}; print("A->B OK")'
                ], capture_output=True, text=True, cwd=PROJECT_ROOT)

                # Try importing B then A
                result_b_then_a = subprocess.run([
                    sys.executable, '-c',
                    f'import {module_b}; import {module_a}; print("B->A OK")'
                ], capture_output=True, text=True, cwd=PROJECT_ROOT)

                # If one direction fails but the other succeeds, it suggests circular dependency issues
                if result_a_then_b.returncode != result_b_then_a.returncode:
                    circular_dependencies.append({
                        "module_a": module_a,
                        "module_b": module_b,
                        "a_then_b_result": result_a_then_b.returncode,
                        "b_then_a_result": result_b_then_a.returncode,
                        "a_then_b_error": result_a_then_b.stderr.strip(),
                        "b_then_a_error": result_b_then_a.stderr.strip()
                    })

            except Exception as e:
                circular_dependencies.append({
                    "module_a": module_a,
                    "module_b": module_b,
                    "error": str(e)
                })

        if circular_dependencies:
            dependency_details = json.dumps(circular_dependencies, indent=2)
            pytest.fail(f"CIRCULAR DEPENDENCY DETECTED: {len(circular_dependencies)} potential circular dependencies:\n{dependency_details}")

    def test_missing_test_dependencies(self):
        """
        Check for missing test dependencies that cause silent test collection failures.
        """
        # Common test dependencies that might be missing
        test_dependencies = [
            "pytest",
            "pytest_asyncio",
            "pytest_mock",
            "aiohttp",
            "websockets",
            "fastapi",
            "uvicorn",
            "redis",
            "psycopg2",
            "clickhouse_driver"
        ]

        missing_dependencies = []

        for dependency in test_dependencies:
            try:
                result = subprocess.run([
                    sys.executable, '-c',
                    f'import {dependency}; print("AVAILABLE: {dependency}")'
                ], capture_output=True, text=True, cwd=PROJECT_ROOT)

                if result.returncode != 0:
                    missing_dependencies.append({
                        "dependency": dependency,
                        "error": result.stderr.strip(),
                        "category": "test_dependency"
                    })

            except Exception as e:
                missing_dependencies.append({
                    "dependency": dependency,
                    "error": str(e),
                    "category": "test_dependency"
                })

        # Don't fail for missing dependencies, just report them
        if missing_dependencies:
            dependency_details = json.dumps(missing_dependencies, indent=2)
            print(f"MISSING TEST DEPENDENCIES: {len(missing_dependencies)} dependencies not available:\n{dependency_details}")

    def test_path_resolution_integrity(self):
        """
        Test that Python path resolution works correctly for test execution.
        """
        path_issues = []

        # Check that project root is in sys.path
        if str(PROJECT_ROOT) not in sys.path:
            path_issues.append({
                "issue": "PROJECT_ROOT not in sys.path",
                "project_root": str(PROJECT_ROOT),
                "current_path": sys.path[:5]  # First 5 entries
            })

        # Check for duplicate paths
        path_counts = {}
        for path in sys.path:
            path_counts[path] = path_counts.get(path, 0) + 1

        duplicates = {path: count for path, count in path_counts.items() if count > 1}
        if duplicates:
            path_issues.append({
                "issue": "Duplicate paths in sys.path",
                "duplicates": duplicates
            })

        # Check that critical directories exist and are accessible
        critical_dirs = [
            PROJECT_ROOT / "netra_backend",
            PROJECT_ROOT / "test_framework",
            PROJECT_ROOT / "shared",
            PROJECT_ROOT / "tests"
        ]

        for dir_path in critical_dirs:
            if not dir_path.exists():
                path_issues.append({
                    "issue": f"Critical directory missing: {dir_path}",
                    "path": str(dir_path)
                })
            elif not dir_path.is_dir():
                path_issues.append({
                    "issue": f"Critical path is not a directory: {dir_path}",
                    "path": str(dir_path)
                })

        if path_issues:
            path_details = json.dumps(path_issues, indent=2)
            pytest.fail(f"PATH RESOLUTION INTEGRITY ISSUES: {len(path_issues)} problems detected:\n{path_details}")

    def test_test_collection_baseline_validation(self):
        """
        Establish baseline for test collection to detect collection failures.
        """
        # Run test collection on a few known test directories
        test_directories = [
            PROJECT_ROOT / "tests" / "unit",
            PROJECT_ROOT / "tests" / "integration",
            PROJECT_ROOT / "tests" / "mission_critical"
        ]

        collection_results = {}

        for test_dir in test_directories:
            if not test_dir.exists():
                collection_results[str(test_dir)] = {
                    "status": "directory_missing",
                    "collected": 0,
                    "errors": ["Directory does not exist"]
                }
                continue

            try:
                # Run collection only (don't execute tests)
                result = subprocess.run([
                    sys.executable, '-m', 'pytest',
                    str(test_dir),
                    '--collect-only',
                    '-v'
                ], capture_output=True, text=True, cwd=PROJECT_ROOT)

                # Parse collection results
                stdout_lines = result.stdout.split('\n')
                collected_count = 0
                for line in stdout_lines:
                    if "collected" in line and "item" in line:
                        # Extract number from line like "collected 5 items"
                        words = line.split()
                        for i, word in enumerate(words):
                            if word == "collected" and i + 1 < len(words):
                                try:
                                    collected_count = int(words[i + 1])
                                    break
                                except ValueError:
                                    pass

                collection_results[str(test_dir)] = {
                    "status": "success" if result.returncode == 0 else "failed",
                    "collected": collected_count,
                    "return_code": result.returncode,
                    "errors": [result.stderr.strip()] if result.stderr.strip() else []
                }

            except Exception as e:
                collection_results[str(test_dir)] = {
                    "status": "exception",
                    "collected": 0,
                    "errors": [str(e)]
                }

        # Analyze results
        failed_collections = {
            path: result for path, result in collection_results.items()
            if result["status"] != "success" or result["collected"] == 0
        }

        print(f"Test Collection Baseline: {json.dumps(collection_results, indent=2)}")

        if failed_collections:
            failure_details = json.dumps(failed_collections, indent=2)
            pytest.fail(f"TEST COLLECTION BASELINE FAILURES: {len(failed_collections)} directories failed collection:\n{failure_details}")


if __name__ == "__main__":
    # Run this test suite directly
    pytest.main([__file__, "-v", "--tb=short"])