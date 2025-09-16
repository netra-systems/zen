#!/usr/bin/env python
"""
E2E Collection Performance Optimizer

Optimizes pytest test collection for E2E directory with 1,300+ files.
Implements parallel collection, caching, and smart filtering to eliminate timeouts.

Usage:
    python e2e_collection_optimizer.py --pattern "*agent*"
    python e2e_collection_optimizer.py --collect-only
    python e2e_collection_optimizer.py --clear-cache
"""

import sys
import os
import argparse
import concurrent.futures
import threading
import time
from pathlib import Path
from typing import Dict, List, Set
import json
import hashlib

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


class E2ECollectionOptimizer:
    """Optimized E2E test collection with parallel processing and caching"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.e2e_dir = project_root / "tests" / "e2e"
        self.cache_file = self.e2e_dir / ".collection_cache.json"
        self.cache = {}
        self.load_cache()

    def load_cache(self):
        """Load collection cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                print(f"[INFO] Loaded collection cache with {len(self.cache)} entries")
            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARNING] Failed to load cache: {e}")
                self.cache = {}

    def save_cache(self):
        """Save collection cache to disk"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
            print(f"[INFO] Saved collection cache with {len(self.cache)} entries")
        except IOError as e:
            print(f"[WARNING] Failed to save cache: {e}")

    def clear_cache(self):
        """Clear the collection cache"""
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        print("[INFO] Collection cache cleared")

    def get_directory_hash(self, directory: Path) -> str:
        """Get hash of directory modification times for cache invalidation"""
        if not directory.exists():
            return "missing"

        try:
            # Use directory modification time as simple hash
            return str(directory.stat().st_mtime)
        except OSError:
            return "error"

    def collect_tests_optimized(self, pattern: str = "*") -> List[str]:
        """Optimized E2E test collection with parallel processing"""

        if not self.e2e_dir.exists():
            print(f"[ERROR] E2E directory not found: {self.e2e_dir}")
            return []

        # Generate cache key
        dir_hash = self.get_directory_hash(self.e2e_dir)
        cache_key = f"{pattern}:{dir_hash}"

        # Check cache first
        if cache_key in self.cache:
            cached_files = self.cache[cache_key]
            print(f"[INFO] Cache hit: {len(cached_files)} files for pattern '{pattern}'")
            return cached_files

        print(f"[INFO] Starting optimized E2E collection for pattern: {pattern}")
        start_time = time.time()

        # Get subdirectories to process
        subdirs_to_collect = []
        excluded_dirs = {
            '__pycache__', '.pytest_cache', '.netra', '.service_discovery',
            'logs', 'crash_reports', '*.egg-info'
        }

        # Collect root level files first
        root_files = self._collect_root_files(pattern)

        # Get subdirectories for parallel processing
        for item in self.e2e_dir.iterdir():
            if item.is_dir() and item.name not in excluded_dirs:
                subdirs_to_collect.append(item)

        print(f"[INFO] Found {len(root_files)} root files, {len(subdirs_to_collect)} subdirectories to process")

        # Parallel collection of subdirectories
        collected_files = root_files.copy()

        if subdirs_to_collect:
            collected_files.extend(self._collect_parallel(subdirs_to_collect, pattern))

        # Cache the result
        self.cache[cache_key] = collected_files

        elapsed_time = time.time() - start_time
        print(f"[INFO] E2E collection completed: {len(collected_files)} test files found in {elapsed_time:.2f}s")

        return collected_files

    def _collect_root_files(self, pattern: str) -> List[str]:
        """Collect test files from E2E root directory"""
        root_files = []

        for item in self.e2e_dir.iterdir():
            if (item.is_file() and
                item.name.endswith('.py') and
                'test_' in item.name and
                (pattern == '*' or pattern.lower() in item.name.lower())):
                root_files.append(str(item))

        return root_files

    def _collect_parallel(self, subdirs: List[Path], pattern: str) -> List[str]:
        """Collect tests from subdirectories in parallel"""

        def collect_subdir(subdir_path: Path) -> List[str]:
            """Collect tests from a single subdirectory"""
            try:
                subdir_files = []
                excluded_dirs = {'__pycache__', '.pytest_cache'}

                for py_file in subdir_path.rglob("*.py"):
                    if (py_file.is_file() and
                        'test_' in py_file.name and
                        not any(excl in str(py_file) for excl in excluded_dirs)):

                        # Apply pattern filtering
                        if pattern == '*' or pattern.lower() in py_file.name.lower():
                            subdir_files.append(str(py_file))

                return subdir_files
            except (OSError, PermissionError) as e:
                print(f"[WARNING] Failed to collect from {subdir_path}: {e}")
                return []

        collected_files = []
        max_workers = min(8, len(subdirs))

        if max_workers > 1:
            print(f"[INFO] Using {max_workers} workers for parallel collection")

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_subdir = {
                    executor.submit(collect_subdir, subdir): subdir
                    for subdir in subdirs
                }

                for future in concurrent.futures.as_completed(future_to_subdir):
                    try:
                        subdir_files = future.result(timeout=15)  # 15s timeout per directory
                        collected_files.extend(subdir_files)
                    except concurrent.futures.TimeoutError:
                        subdir = future_to_subdir[future]
                        print(f"[WARNING] Timeout collecting from {subdir.name}")
                    except Exception as e:
                        subdir = future_to_subdir[future]
                        print(f"[WARNING] Error collecting from {subdir.name}: {e}")
        else:
            # Sequential fallback
            for subdir in subdirs:
                collected_files.extend(collect_subdir(subdir))

        return collected_files

    def collect_and_run_pytest(self, pattern: str = "*", extra_args: List[str] = None) -> int:
        """Collect tests and run pytest with optimized collection"""

        # First collect tests optimized
        test_files = self.collect_tests_optimized(pattern)

        if not test_files:
            print("[INFO] No test files found")
            return 0

        # Use fast collection pytest config
        fast_config = self.e2e_dir / "pytest_e2e_fast_collection.ini"

        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            "-c", str(fast_config) if fast_config.exists() else str(PROJECT_ROOT / "pytest.ini"),
            "--collect-only",
            "--quiet"
        ]

        if extra_args:
            cmd.extend(extra_args)

        # Add test files (batch them to avoid command line length limits)
        batch_size = 50  # Avoid command line length limits

        for i in range(0, len(test_files), batch_size):
            batch = test_files[i:i + batch_size]
            batch_cmd = cmd + batch

            print(f"[INFO] Running pytest on batch {i//batch_size + 1}/{(len(test_files)-1)//batch_size + 1} ({len(batch)} files)")

            import subprocess
            result = subprocess.run(batch_cmd, cwd=self.project_root, capture_output=False)

            if result.returncode != 0:
                print(f"[WARNING] Batch {i//batch_size + 1} returned code {result.returncode}")

        return 0

    def get_statistics(self) -> Dict[str, any]:
        """Get collection statistics"""
        stats = {
            "total_directories": 0,
            "total_files": 0,
            "test_files": 0,
            "cache_entries": len(self.cache)
        }

        if self.e2e_dir.exists():
            for root, dirs, files in os.walk(self.e2e_dir):
                stats["total_directories"] += len(dirs)
                stats["total_files"] += len(files)
                stats["test_files"] += sum(1 for f in files if f.startswith("test_") and f.endswith(".py"))

        return stats


def main():
    parser = argparse.ArgumentParser(description="E2E Collection Performance Optimizer")
    parser.add_argument("--pattern", default="*", help="Test file pattern to collect")
    parser.add_argument("--collect-only", action="store_true", help="Only collect tests, don't run")
    parser.add_argument("--clear-cache", action="store_true", help="Clear collection cache")
    parser.add_argument("--stats", action="store_true", help="Show collection statistics")
    parser.add_argument("--run-pytest", action="store_true", help="Run pytest with optimized collection")

    args = parser.parse_args()

    optimizer = E2ECollectionOptimizer(PROJECT_ROOT)

    if args.clear_cache:
        optimizer.clear_cache()
        return 0

    if args.stats:
        stats = optimizer.get_statistics()
        print("[STATISTICS]")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return 0

    if args.run_pytest:
        exit_code = optimizer.collect_and_run_pytest(args.pattern)
        optimizer.save_cache()
        return exit_code

    # Default: optimized collection
    test_files = optimizer.collect_tests_optimized(args.pattern)
    optimizer.save_cache()

    if args.collect_only:
        print(f"[RESULT] Found {len(test_files)} test files")
        for test_file in test_files[:10]:  # Show first 10
            print(f"  {test_file}")
        if len(test_files) > 10:
            print(f"  ... and {len(test_files) - 10} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())