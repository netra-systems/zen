#!/usr/bin/env python3
"""
Automated Migration Tool for pytest.main() Violations

Business Value Justification (BVJ):
- Segment: Platform (All segments affected by deployment blocks)
- Business Goal: Stability - Restore deployment reliability
- Value Impact: Unblocks $500K+ ARR from deployment failures
- Revenue Impact: Restores customer confidence in system stability

PURPOSE: Systematically convert unauthorized test runners to SSOT patterns.
ISSUE: https://github.com/netra-systems/netra-apex/issues/1024

MIGRATION STRATEGY:
1. Phase 1: Convert simple pytest.main() calls
2. Phase 2: Migrate __main__ blocks
3. Phase 3: Update complex test orchestration
4. Phase 4: Validate and fix imports
"""

import sys
import re
import ast
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional
import argparse
import logging

# Setup project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Migration templates
SSOT_IMPORT_TEMPLATE = """# SSOT Import - Use unified test base
try:
    from test_framework.ssot.base_test_case import SSotTestCase, SSotAsyncTestCase
    BaseTestCase = SSotTestCase
    AsyncBaseTestCase = SSotAsyncTestCase
except ImportError:
    import unittest
    BaseTestCase = unittest.TestCase
    AsyncBaseTestCase = unittest.TestCase
"""

UNIFIED_RUNNER_TEMPLATE = '''
def run_tests_via_ssot_runner():
    """
    MIGRATED: Use SSOT unified test runner instead of direct pytest.main()
    Issue #1024: Unauthorized test runners blocking Golden Path
    """
    import subprocess
    import sys
    from pathlib import Path

    # Get project root
    project_root = Path(__file__).parent
    while not (project_root / "tests" / "unified_test_runner.py").exists() and project_root.parent != project_root:
        project_root = project_root.parent

    unified_runner = project_root / "tests" / "unified_test_runner.py"

    if not unified_runner.exists():
        print("ERROR: Could not find tests/unified_test_runner.py")
        print("Please run tests using: python tests/unified_test_runner.py --category <category>")
        return 1

    # Use SSOT unified test runner
    cmd = [sys.executable, str(unified_runner), "--category", "unit", "--fast-fail"]
    result = subprocess.run(cmd, cwd=str(project_root))
    return result.returncode
'''

class PytestMainMigrator:
    """Automated migrator for pytest.main() violations."""

    def __init__(self, dry_run: bool = True, backup: bool = True):
        self.dry_run = dry_run
        self.backup = backup
        self.migration_stats = {
            'files_processed': 0,
            'pytest_main_replacements': 0,
            'main_block_replacements': 0,
            'import_additions': 0,
            'errors': 0
        }

    def migrate_file(self, file_path: str) -> Dict:
        """
        Migrate a single file from pytest.main() to SSOT patterns.

        Returns:
            Migration result dictionary
        """
        result = {
            'file_path': file_path,
            'success': False,
            'changes_made': [],
            'errors': []
        }

        try:
            # Read original file
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Create backup if requested
            if self.backup and not self.dry_run:
                backup_path = f"{file_path}.backup"
                shutil.copy2(file_path, backup_path)
                logger.info(f"Created backup: {backup_path}")

            # Apply migrations
            modified_content = original_content

            # 1. Replace simple pytest.main() calls
            modified_content, pytest_replacements = self._replace_pytest_main_calls(modified_content)
            if pytest_replacements > 0:
                result['changes_made'].append(f"Replaced {pytest_replacements} pytest.main() calls")
                self.migration_stats['pytest_main_replacements'] += pytest_replacements

            # 2. Migrate __main__ blocks
            modified_content, main_replacements = self._migrate_main_blocks(modified_content)
            if main_replacements > 0:
                result['changes_made'].append(f"Migrated {main_replacements} __main__ blocks")
                self.migration_stats['main_block_replacements'] += main_replacements

            # 3. Add SSOT imports if needed
            modified_content, import_added = self._ensure_ssot_imports(modified_content, file_path)
            if import_added:
                result['changes_made'].append("Added SSOT imports")
                self.migration_stats['import_additions'] += 1

            # 4. Write changes if not dry run
            if modified_content != original_content:
                if not self.dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                    logger.info(f"Successfully migrated: {file_path}")
                else:
                    logger.info(f"[DRY RUN] Would migrate: {file_path}")

                result['success'] = True
            else:
                logger.info(f"No changes needed: {file_path}")
                result['success'] = True

            self.migration_stats['files_processed'] += 1

        except Exception as e:
            error_msg = f"Error migrating {file_path}: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            self.migration_stats['errors'] += 1

        return result

    def _replace_pytest_main_calls(self, content: str) -> Tuple[str, int]:
        """Replace direct pytest.main() calls with SSOT patterns."""
        replacements = 0

        # Pattern 1: Simple pytest.main() calls
        def replace_simple_pytest_main(match):
            nonlocal replacements
            replacements += 1
            return "# MIGRATED: Use SSOT unified test runner\n    # python tests/unified_test_runner.py --category unit\n    pass  # TODO: Replace with appropriate SSOT test execution"

        content = re.sub(
            r'pytest\.main\s*\([^)]*\)',
            replace_simple_pytest_main,
            content,
            flags=re.MULTILINE
        )

        # Pattern 2: pytest.cmdline.main() calls
        def replace_cmdline_main(match):
            nonlocal replacements
            replacements += 1
            return "# MIGRATED: Use SSOT unified test runner\n    # python tests/unified_test_runner.py --category unit"

        content = re.sub(
            r'pytest\.cmdline\.main\s*\([^)]*\)',
            replace_cmdline_main,
            content,
            flags=re.MULTILINE
        )

        return content, replacements

    def _migrate_main_blocks(self, content: str) -> Tuple[str, int]:
        """Migrate __main__ blocks with pytest execution."""
        replacements = 0

        # Find __main__ blocks with pytest calls
        main_block_pattern = r'if\s+__name__\s*==\s*["\']__main__["\']:\s*\n((?:\s{4,}.*\n)*)'

        def replace_main_block(match):
            nonlocal replacements
            block_content = match.group(1)

            if 'pytest' in block_content:
                replacements += 1
                return '''if __name__ == "__main__":
    # MIGRATED: Use SSOT unified test runner instead of direct pytest execution
    # Issue #1024: Unauthorized test runners blocking Golden Path
    print("MIGRATION NOTICE: This file previously used direct pytest execution.")
    print("Please use: python tests/unified_test_runner.py --category <appropriate_category>")
    print("For more info: reports/TEST_EXECUTION_GUIDE.md")

    # Uncomment and customize the following for SSOT execution:
    # result = run_tests_via_ssot_runner()
    # sys.exit(result)
'''
            return match.group(0)  # No change if no pytest

        content = re.sub(main_block_pattern, replace_main_block, content, flags=re.MULTILINE)

        # Add SSOT runner function if we made main block replacements
        if replacements > 0 and 'run_tests_via_ssot_runner' not in content:
            content = content + '\n' + UNIFIED_RUNNER_TEMPLATE

        return content, replacements

    def _ensure_ssot_imports(self, content: str, file_path: str) -> Tuple[str, bool]:
        """Ensure SSOT imports are present if this is a test file."""

        # Only add imports to test files
        if not (file_path.endswith('_test.py') or 'test_' in Path(file_path).name or 'tests/' in file_path):
            return content, False

        # Check if SSOT imports already exist
        if 'test_framework.ssot.base_test_case' in content:
            return content, False

        # Check if unittest is used (indicating need for SSOT migration)
        if 'unittest.TestCase' in content or 'from unittest import' in content:
            # Add SSOT imports at the top after existing imports
            import_insertion_point = self._find_import_insertion_point(content)

            lines = content.splitlines()
            lines.insert(import_insertion_point, SSOT_IMPORT_TEMPLATE)

            return '\n'.join(lines), True

        return content, False

    def _find_import_insertion_point(self, content: str) -> int:
        """Find the best place to insert SSOT imports."""
        lines = content.splitlines()

        # Find last import statement
        last_import_line = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                last_import_line = i
            elif stripped and not stripped.startswith('#') and not stripped.startswith('"""'):
                # First non-import, non-comment line
                break

        return last_import_line + 1

    def migrate_directory(self, directory: str, pattern: str = "**/*.py") -> List[Dict]:
        """Migrate all Python files in a directory."""
        directory_path = Path(directory)
        results = []

        logger.info(f"Migrating directory: {directory}")
        logger.info(f"Pattern: {pattern}")
        logger.info(f"Dry run: {self.dry_run}")

        for file_path in directory_path.glob(pattern):
            if file_path.is_file() and file_path.suffix == '.py':
                # Skip certain files
                if self._should_skip_file(str(file_path)):
                    logger.info(f"Skipping: {file_path}")
                    continue

                result = self.migrate_file(str(file_path))
                results.append(result)

        return results

    def _should_skip_file(self, file_path: str) -> bool:
        """Determine if a file should be skipped during migration."""
        skip_patterns = [
            'unified_test_runner.py',  # SSOT runner itself
            'base_test_case.py',       # SSOT base classes
            'migrate_pytest_main_violations.py',  # This script
            'detect_pytest_main_violations.py',   # Detection script
            '__pycache__',
            '.git',
            'node_modules',
            '.venv',
            'venv',
        ]

        return any(pattern in file_path for pattern in skip_patterns)

    def generate_migration_report(self, results: List[Dict]) -> None:
        """Generate comprehensive migration report."""
        print("\n" + "=" * 80)
        print("PYTEST.MAIN() MIGRATION REPORT")
        print("=" * 80)
        print(f"Issue #1024: SSOT Regression - Unauthorized Test Runners")
        print(f"Migration Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        print("=" * 80)

        print(f"\nMIGRATION STATISTICS:")
        print(f"  Files Processed: {self.migration_stats['files_processed']}")
        print(f"  pytest.main() Calls Replaced: {self.migration_stats['pytest_main_replacements']}")
        print(f"  __main__ Blocks Migrated: {self.migration_stats['main_block_replacements']}")
        print(f"  SSOT Imports Added: {self.migration_stats['import_additions']}")
        print(f"  Errors: {self.migration_stats['errors']}")

        # Files with changes
        changed_files = [r for r in results if r['changes_made']]
        if changed_files:
            print(f"\nFILES WITH CHANGES ({len(changed_files)}):")
            for result in changed_files:
                print(f"  OK {result['file_path']}")
                for change in result['changes_made']:
                    print(f"     - {change}")

        # Files with errors
        error_files = [r for r in results if r['errors']]
        if error_files:
            print(f"\nFILES WITH ERRORS ({len(error_files)}):")
            for result in error_files:
                print(f"  ERROR {result['file_path']}")
                for error in result['errors']:
                    print(f"     - {error}")

        print(f"\nNEXT STEPS:")
        print(f"1. Review migrated files for correctness")
        print(f"2. Run tests to validate: python tests/unified_test_runner.py --category unit")
        print(f"3. Update any remaining manual test execution patterns")
        print(f"4. Commit changes: git add . && git commit -m 'fix: migrate pytest.main() to SSOT patterns (Issue #1024)'")

def main():
    """Main entry point for the migration tool."""
    parser = argparse.ArgumentParser(description="Migrate pytest.main() violations to SSOT patterns")
    parser.add_argument("target", help="File or directory to migrate")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Preview changes without modifying files (default)")
    parser.add_argument("--live", action="store_true",
                       help="Actually modify files (overrides --dry-run)")
    parser.add_argument("--no-backup", action="store_true",
                       help="Skip creating backup files")
    parser.add_argument("--pattern", default="**/*.py",
                       help="File pattern for directory migration (default: **/*.py)")

    args = parser.parse_args()

    # Determine run mode
    dry_run = not args.live
    backup = not args.no_backup

    print(f"PYTEST.MAIN() MIGRATION TOOL")
    print(f"Target: {args.target}")
    print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'LIVE MIGRATION'}")
    print(f"Backup: {'Enabled' if backup else 'Disabled'}")
    print()

    migrator = PytestMainMigrator(dry_run=dry_run, backup=backup)

    target_path = Path(args.target)
    if target_path.is_file():
        # Single file migration
        result = migrator.migrate_file(str(target_path))
        migrator.generate_migration_report([result])
    elif target_path.is_dir():
        # Directory migration
        results = migrator.migrate_directory(str(target_path), args.pattern)
        migrator.generate_migration_report(results)
    else:
        print(f"ERROR: Target '{args.target}' is not a valid file or directory")
        sys.exit(1)

    if migrator.migration_stats['errors'] > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()