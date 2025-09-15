#!/usr/bin/env python3
"""
Test File Corruption Restoration Script

Restores 406 corrupted test files by removing REMOVED_SYNTAX_ERROR prefixes.
Prioritizes business value: Mission Critical > Integration > Supporting tests.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Stability & Test Coverage Recovery
- Value Impact: Restores $500K+ ARR protection via mission critical tests
- Strategic Impact: Enables Golden Path validation and deployment confidence

Usage:
    python scripts/restore_corrupted_tests.py --dry-run  # Preview changes
    python scripts/restore_corrupted_tests.py --tier 1  # Restore mission critical only
    python scripts/restore_corrupted_tests.py --all     # Restore all corrupted files
"""

import os
import sys
import re
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import IsolatedEnvironment


class TestRestorationManager:
    """Manages systematic restoration of corrupted test files."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backup_dir = project_root / "backups" / f"test_restoration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.corruption_pattern = re.compile(r'^(\s*)# REMOVED_SYNTAX_ERROR:\s*(.*)$', re.MULTILINE)

        # Business value prioritization
        self.tier_1_patterns = [
            "tests/mission_critical/test_websocket_*",
            "tests/mission_critical/test_multiuser_security_*",
            "tests/unit/test_message_router_ssot_*",
            "tests/unit/ssot_validation/test_websocket_*",
            "tests/infrastructure/test_ssot_*",
            "tests/security/test_websocket_v2_*",
            "tests/security/test_factory_pattern_*"
        ]

        self.tier_2_patterns = [
            "auth_service/tests/integration/test_*",
            "auth_service/tests/unit/test_*",
            "tests/mission_critical/test_docker_*",
            "tests/integration/test_*docker*",
            "tests/integration/test_auth_*"
        ]

        self.tier_3_patterns = [
            "tests/performance/test_*",
            "tests/stress/test_*",
            "tests/e2e/test_*",
            "tests/manual/test_*"
        ]

    def find_corrupted_files(self) -> List[Path]:
        """Find all files with REMOVED_SYNTAX_ERROR corruption."""
        corrupted_files = []

        for py_file in self.project_root.rglob("*.py"):
            # Skip backups and non-test files
            if "backup" in str(py_file) or "tests" not in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "REMOVED_SYNTAX_ERROR:" in content:
                        corrupted_files.append(py_file)
            except (UnicodeDecodeError, PermissionError):
                continue

        return corrupted_files

    def categorize_by_tier(self, files: List[Path]) -> Dict[int, List[Path]]:
        """Categorize files by business value tier."""
        categorized = {1: [], 2: [], 3: []}

        for file_path in files:
            relative_path = str(file_path.relative_to(self.project_root))

            # Check tier 1 (mission critical)
            if any(self._matches_pattern(relative_path, pattern) for pattern in self.tier_1_patterns):
                categorized[1].append(file_path)
            # Check tier 2 (integration)
            elif any(self._matches_pattern(relative_path, pattern) for pattern in self.tier_2_patterns):
                categorized[2].append(file_path)
            # Tier 3 (supporting)
            else:
                categorized[3].append(file_path)

        return categorized

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches glob-like pattern."""
        pattern_regex = pattern.replace("*", ".*").replace("?", ".")
        return re.match(pattern_regex, file_path) is not None

    def restore_file(self, file_path: Path, backup: bool = True) -> bool:
        """Restore a single corrupted file."""
        try:
            # Read corrupted content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if actually corrupted
            if "REMOVED_SYNTAX_ERROR:" not in content:
                print(f"SKIP: {file_path} - Not corrupted")
                return True

            # Create backup if requested
            if backup:
                backup_file = self.backup_dir / file_path.relative_to(self.project_root)
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, backup_file)

            # Restore content by removing corruption prefixes
            restored_content = self.corruption_pattern.sub(r'\1\2', content)

            # Write restored content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(restored_content)

            print(f"RESTORED: {file_path}")
            return True

        except Exception as e:
            print(f"ERROR restoring {file_path}: {e}")
            return False

    def validate_restoration(self, file_path: Path) -> bool:
        """Validate that restored file has valid Python syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Try to compile to check syntax
            compile(content, str(file_path), 'exec')
            return True

        except SyntaxError as e:
            print(f"SYNTAX ERROR in {file_path}: {e}")
            return False
        except Exception as e:
            print(f"VALIDATION ERROR in {file_path}: {e}")
            return False

    def restore_tier(self, tier: int, dry_run: bool = False, validate: bool = True) -> Dict[str, int]:
        """Restore all files in a specific tier."""
        print(f"\n{'='*60}")
        print(f"RESTORING TIER {tier} - BUSINESS VALUE PRIORITY")
        print(f"{'='*60}")

        corrupted_files = self.find_corrupted_files()
        categorized = self.categorize_by_tier(corrupted_files)
        tier_files = categorized[tier]

        print(f"Found {len(tier_files)} Tier {tier} corrupted files")

        if dry_run:
            print("DRY RUN - Would restore:")
            for file_path in tier_files:
                print(f"  - {file_path.relative_to(self.project_root)}")
            return {"total": len(tier_files), "restored": 0, "failed": 0}

        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        results = {"total": len(tier_files), "restored": 0, "failed": 0}

        for file_path in tier_files:
            if self.restore_file(file_path, backup=True):
                if validate and self.validate_restoration(file_path):
                    results["restored"] += 1
                elif validate:
                    results["failed"] += 1
                    print(f"FAILED VALIDATION: {file_path}")
                else:
                    results["restored"] += 1
            else:
                results["failed"] += 1

        print(f"\nTier {tier} Results:")
        print(f"  Total files: {results['total']}")
        print(f"  Successfully restored: {results['restored']}")
        print(f"  Failed: {results['failed']}")
        print(f"  Success rate: {results['restored']/results['total']*100:.1f}%")

        return results


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Restore corrupted test files")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3],
                       help="Restore specific tier (1=Mission Critical, 2=Integration, 3=Supporting)")
    parser.add_argument("--all", action="store_true",
                       help="Restore all tiers")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview changes without making them")
    parser.add_argument("--no-validate", action="store_true",
                       help="Skip syntax validation after restoration")

    args = parser.parse_args()

    if not (args.tier or args.all):
        parser.print_help()
        print("\nRECOMMENDED: Start with --tier 1 to restore mission critical tests first")
        return

    manager = TestRestorationManager(Path(__file__).parent.parent)

    print("NETRA TEST RESTORATION UTILITY")
    print("=" * 50)
    print("BUSINESS PRIORITY: Restore Golden Path protection ($500K+ ARR)")
    print("STRATEGY: Tier-based restoration by business value")

    if args.dry_run:
        print("\nDRY RUN MODE - No files will be modified")

    total_results = {"total": 0, "restored": 0, "failed": 0}

    if args.all:
        for tier in [1, 2, 3]:
            results = manager.restore_tier(tier, dry_run=args.dry_run,
                                         validate=not args.no_validate)
            for key in total_results:
                total_results[key] += results[key]
    else:
        results = manager.restore_tier(args.tier, dry_run=args.dry_run,
                                     validate=not args.no_validate)
        total_results = results

    print(f"\n{'='*60}")
    print("FINAL RESTORATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total files processed: {total_results['total']}")
    print(f"Successfully restored: {total_results['restored']}")
    print(f"Failed restorations: {total_results['failed']}")
    print(f"Overall success rate: {total_results['restored']/total_results['total']*100:.1f}%")

    if not args.dry_run and total_results['restored'] > 0:
        print(f"\nNEXT STEPS:")
        print(f"1. Run mission critical tests: python tests/unified_test_runner.py --category mission_critical")
        print(f"2. Validate test discovery: python -m pytest --collect-only tests/mission_critical/")
        print(f"3. Check business value protection via staging validation")
        print(f"4. Backup created at: {manager.backup_dir}")


if __name__ == "__main__":
    main()