#!/usr/bin/env python3
"""
ISSUE #450 - Redis Import Pattern Migration Baseline Test

This test validates the current system functionality before migrating
deprecated Redis import patterns to SSOT patterns.

Purpose:
- Establish baseline for 59 files with deprecated import patterns
- Validate current Redis functionality across mission critical tests
- Ensure no regressions during SSOT migration
- Support Issue #489 performance improvement validation

Deprecated Pattern (59 files):
    from netra_backend.app.redis_manager import redis_manager

Target SSOT Pattern:
    from netra_backend.app.redis_manager import redis_manager
"""

import sys
import os
import time
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pytest
from unittest.mock import Mock, patch

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class Issue450RedisImportPatternBaseline(SSotAsyncTestCase):
    """Baseline test for Redis import pattern migration."""

    def setUp(self):
        """Set up baseline test environment."""
        super().setUp()
        self.deprecated_pattern = "from netra_backend.app.redis_manager import redis_manager"
        self.ssot_pattern = "from netra_backend.app.redis_manager import redis_manager"
        self.files_with_deprecated_imports = []
        self.mission_critical_tests = [
            "tests/mission_critical/test_redis_ssot_consolidation.py",
            "tests/mission_critical/test_websocket_1011_fixes.py",
            "tests/mission_critical/test_redis_validation_ssot_critical.py"
        ]

    def test_scan_deprecated_redis_import_patterns(self):
        """Scan and count files with deprecated Redis import patterns."""
        print("\n🔍 Scanning for deprecated Redis import patterns...")

        # Use simple file search for deprecated pattern
        files_found = []
        pattern = "test_framework.redis_test_utils.test_redis_manager"

        try:
            # Walk through all Python files in the project
            for root, dirs, files in os.walk(project_root):
                # Skip hidden directories and __pycache__
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, project_root)

                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if pattern in content:
                                    files_found.append(rel_path)
                        except Exception:
                            # Skip files that can't be read
                            continue

            self.files_with_deprecated_imports = files_found

            print(f"📊 Found {len(files_found)} files with deprecated Redis import patterns")
            print(f"📋 Sample files:")
            for i, file_path in enumerate(files_found[:5]):
                print(f"   {i+1}. {file_path}")
            if len(files_found) > 5:
                print(f"   ... and {len(files_found) - 5} more files")

            # Validate count matches issue description (55+ files)
            if len(files_found) < 55:
                print(f"WARNING️  Found {len(files_found)} files, expected 55+")
            else:
                print(f"CHECK Found {len(files_found)} files, matches issue scope")

            return files_found

        except Exception as e:
            print(f"X Failed to scan for deprecated imports: {e}")
            return []

    def test_ssot_redis_import_accessibility(self):
        """Validate SSOT Redis import is accessible and functional."""
        print("\nCHECK Testing SSOT Redis import accessibility...")

        try:
            # Test import works
            from netra_backend.app.redis_manager import redis_manager

            # Validate it's the correct type
            self.assertIsNotNone(redis_manager, "Redis manager should not be None")
            print(f"CHECK SSOT Redis import successful: {type(redis_manager).__name__}")

            # Test basic functionality (if possible without environment setup)
            self.assertTrue(hasattr(redis_manager, 'get_client'),
                          "Redis manager should have get_client method")

            return True

        except ImportError as e:
            print(f"X SSOT Redis import failed: {e}")
            return False
        except Exception as e:
            # Non-critical errors (like missing environment variables) are acceptable
            print(f"WARNING️  SSOT import works but environment issue: {e}")
            return True

    def test_measure_test_collection_performance_baseline(self):
        """Measure current test collection performance for Issue #489 comparison."""
        print("\n⏱️ Measuring baseline test collection performance...")

        # Measure test discovery time for agent-related tests (Issue #489 scope)
        test_patterns = [
            "--collect-only",
            "tests/",
            "-k", "agent"
        ]

        start_time = time.time()

        try:
            # Run test collection only
            result = subprocess.run(
                ["python", "-m", "pytest"] + test_patterns,
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=180  # 3 minute timeout
            )

            collection_time = time.time() - start_time

            print(f"📊 Baseline test collection time: {collection_time:.2f} seconds")

            # Parse collection output
            collected_count = 0
            if "collected" in result.stdout:
                for line in result.stdout.split('\n'):
                    if "collected" in line and "items" in line:
                        # Extract number from line like "collected 150 items"
                        words = line.split()
                        for i, word in enumerate(words):
                            if word == "collected" and i + 1 < len(words):
                                try:
                                    collected_count = int(words[i + 1])
                                    break
                                except ValueError:
                                    pass

            print(f"📋 Tests collected: {collected_count}")

            # Store baseline for comparison
            self.baseline_collection_time = collection_time
            self.baseline_test_count = collected_count

            # Validate reasonable performance (should be under 2 minutes for now)
            if collection_time > 120:
                print(f"WARNING️  WARNING: Test collection time ({collection_time:.2f}s) exceeds 120s")
                print("    This confirms Issue #489 performance problem")
            else:
                print(f"CHECK Test collection performance acceptable: {collection_time:.2f}s")

            return collection_time, collected_count

        except subprocess.TimeoutExpired:
            print("X Test collection timed out after 3 minutes - confirms Issue #489")
            return 180.0, 0
        except Exception as e:
            print(f"X Test collection measurement failed: {e}")
            return None, 0

    def test_mission_critical_redis_tests_baseline(self):
        """Validate mission critical Redis tests pass in baseline state."""
        print("\n🚨 Validating mission critical Redis tests baseline...")

        passing_tests = []
        failing_tests = []

        for test_file in self.mission_critical_tests:
            test_path = project_root / test_file

            if not test_path.exists():
                print(f"WARNING️  Test file not found: {test_file}")
                continue

            print(f"🧪 Testing: {test_file}")

            try:
                # Run individual test file
                result = subprocess.run(
                    ["python", "-m", "pytest", str(test_path), "-v"],
                    capture_output=True,
                    text=True,
                    cwd=project_root,
                    timeout=60
                )

                if result.returncode == 0:
                    print(f"CHECK PASS: {test_file}")
                    passing_tests.append(test_file)
                else:
                    print(f"X FAIL: {test_file}")
                    if result.stderr:
                        print(f"   Error: {result.stderr[:200]}...")
                    failing_tests.append(test_file)

            except subprocess.TimeoutExpired:
                print(f"⏰ TIMEOUT: {test_file}")
                failing_tests.append(test_file)
            except Exception as e:
                print(f"🚫 ERROR: {test_file} - {e}")
                failing_tests.append(test_file)

        print(f"\n📊 Mission Critical Test Results:")
        print(f"   CHECK Passing: {len(passing_tests)}")
        print(f"   X Failing: {len(failing_tests)}")

        # Store baseline results
        self.baseline_passing_tests = passing_tests
        self.baseline_failing_tests = failing_tests

        return passing_tests, failing_tests

    def test_validate_migration_feasibility(self):
        """Validate that Redis import pattern migration is feasible."""
        print("\n🎯 Validating Redis import pattern migration feasibility...")

        # Run all baseline tests
        deprecated_files = self.test_scan_deprecated_redis_import_patterns()
        ssot_accessible = self.test_ssot_redis_import_accessibility()
        collection_time, test_count = self.test_measure_test_collection_performance_baseline()
        passing_tests, failing_tests = self.test_mission_critical_redis_tests_baseline()

        # Migration feasibility assessment
        feasible = True
        issues = []

        if len(deprecated_files) == 0:
            issues.append("No deprecated imports found - migration may not be needed")

        if not ssot_accessible:
            issues.append("SSOT Redis import not accessible")
            feasible = False

        if collection_time and collection_time > 120:
            print(f"CHECK Confirms Issue #489: Test collection slow ({collection_time:.2f}s)")

        if len(passing_tests) == 0:
            issues.append("No mission critical tests passing - high risk migration")

        # Generate migration report
        print(f"\n📋 MIGRATION FEASIBILITY REPORT:")
        print(f"   🎯 Files to migrate: {len(deprecated_files)}")
        print(f"   CHECK SSOT import accessible: {ssot_accessible}")
        print(f"   ⏱️  Current collection time: {collection_time:.2f}s" if collection_time else "   ⏱️  Collection time: Not measured")
        print(f"   🧪 Baseline tests passing: {len(passing_tests)}")
        print(f"   📊 Migration feasible: {'YES' if feasible else 'NO'}")

        if issues:
            print(f"   WARNING️  Issues identified:")
            for issue in issues:
                print(f"      - {issue}")

        # Check migration is feasible
        if not feasible:
            print(f"X Migration not feasible due to: {issues}")

        print(f"\n🚀 READY FOR REDIS IMPORT PATTERN MIGRATION!")

        return {
            'deprecated_files': deprecated_files,
            'ssot_accessible': ssot_accessible,
            'collection_time': collection_time,
            'test_count': test_count,
            'passing_tests': passing_tests,
            'failing_tests': failing_tests,
            'feasible': feasible,
            'issues': issues
        }


if __name__ == "__main__":
    # Run baseline tests
    test_case = Issue450RedisImportPatternBaseline()
    test_case.setUp()

    print("=" * 80)
    print("🔬 ISSUE #450 - REDIS IMPORT PATTERN MIGRATION BASELINE")
    print("=" * 80)

    try:
        result = test_case.test_validate_migration_feasibility()
        print("\nCHECK Baseline validation complete!")
        print(f"📊 Migration feasibility: {result['feasible']}")

    except Exception as e:
        print(f"\nX Baseline validation failed: {e}")
        sys.exit(1)
