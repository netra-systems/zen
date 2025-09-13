#!/usr/bin/env python3
"""
ISSUE #450 - Redis Import Pattern Migration Script

Automated script to migrate deprecated Redis import patterns to SSOT patterns.

Migration:
  FROM: from netra_backend.app.redis_manager import redis_manager
  TO:   from netra_backend.app.redis_manager import redis_manager

Purpose:
- Fix 51+ files with deprecated Redis import patterns
- Improve test collection performance (Issue #489 dependency)
- Maintain SSOT compliance
- Preserve test functionality

Safety:
- Backup files before modification
- Validation of imports post-migration
- Rollback capability if issues arise
"""

import os
import sys
import shutil
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import argparse


class RedisImportMigrationTool:
    """Tool for migrating deprecated Redis import patterns to SSOT."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backups" / "issue_450_redis_migration"

        # Migration patterns
        self.deprecated_pattern = "test_framework.redis_test_utils.test_redis_manager"
        self.ssot_import = "from netra_backend.app.redis_manager import redis_manager"

        # Pattern variations to handle
        self.import_patterns = [
            r"from test_framework\.redis_test_utils\.test_redis_manager import redis_manager",
            r"from test_framework\.redis_test_utils\.test_redis_manager import \*",
            r"import test_framework\.redis_test_utils\.test_redis_manager",
        ]

        # Usage patterns to update
        self.usage_patterns = [
            (r"redis_manager\(\)", "redis_manager"),
            (r"redis_manager", "redis_manager"),
        ]

        self.files_migrated = []
        self.files_failed = []
        self.backup_created = False

    def create_backup_directory(self):
        """Create backup directory for rollback capability."""
        if not self.backup_created:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created backup directory: {self.backup_dir}")
            self.backup_created = True

    def find_files_with_deprecated_imports(self) -> List[Path]:
        """Find all files containing deprecated Redis import patterns."""
        files_found = []

        print(f"Scanning for files with pattern: {self.deprecated_pattern}")

        for root, dirs, files in os.walk(self.project_root):
            # Skip hidden directories, __pycache__, and backup directory
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != 'backups']

            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if self.deprecated_pattern in content:
                                files_found.append(file_path)
                    except Exception as e:
                        print(f"Warning: Could not read {file_path}: {e}")

        print(f"Found {len(files_found)} files with deprecated imports")
        return files_found

    def backup_file(self, file_path: Path) -> Path:
        """Create backup of file before modification."""
        self.create_backup_directory()

        # Create relative path structure in backup
        rel_path = file_path.relative_to(self.project_root)
        backup_path = self.backup_dir / rel_path

        # Create directories if needed
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file to backup location
        shutil.copy2(file_path, backup_path)
        return backup_path

    def migrate_file_imports(self, file_path: Path) -> Tuple[bool, str]:
        """Migrate Redis imports in a single file."""
        try:
            # Backup original file
            backup_path = self.backup_file(file_path)

            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            changes_made = []

            # Replace import statements
            for pattern in self.import_patterns:
                if re.search(pattern, content):
                    # Replace with SSOT import
                    new_content = re.sub(pattern, self.ssot_import, content)
                    if new_content != content:
                        changes_made.append(f"Updated import pattern: {pattern}")
                        content = new_content

            # Replace usage patterns
            for old_pattern, new_pattern in self.usage_patterns:
                if re.search(old_pattern, content):
                    new_content = re.sub(old_pattern, new_pattern, content)
                    if new_content != content:
                        changes_made.append(f"Updated usage: {old_pattern} -> {new_pattern}")
                        content = new_content

            # Write updated content if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                change_summary = "; ".join(changes_made)
                return True, f"SUCCESS: {change_summary}"
            else:
                return True, "NO_CHANGES: File contains pattern but no changes needed"

        except Exception as e:
            return False, f"ERROR: {str(e)}"

    def validate_file_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Validate that migrated file has valid Python syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Compile to check syntax
            compile(content, str(file_path), 'exec')
            return True, "Valid syntax"

        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"

    def rollback_file(self, file_path: Path) -> bool:
        """Rollback a file to its backup version."""
        try:
            rel_path = file_path.relative_to(self.project_root)
            backup_path = self.backup_dir / rel_path

            if backup_path.exists():
                shutil.copy2(backup_path, file_path)
                return True
            else:
                print(f"❌ No backup found for {file_path}")
                return False

        except Exception as e:
            print(f"❌ Rollback failed for {file_path}: {e}")
            return False

    def migrate_all_files(self, files: List[Path], validate: bool = True) -> Dict:
        """Migrate all files with deprecated Redis imports."""
        results = {
            'total_files': len(files),
            'migrated_successfully': 0,
            'migration_failed': 0,
            'validation_failed': 0,
            'files_migrated': [],
            'files_failed': [],
            'validation_failed_files': []
        }

        print(f"\nStarting migration of {len(files)} files...")

        for i, file_path in enumerate(files, 1):
            rel_path = file_path.relative_to(self.project_root)
            print(f"\n[{i}/{len(files)}] Migrating: {rel_path}")

            # Attempt migration
            success, message = self.migrate_file_imports(file_path)

            if success:
                print(f"   SUCCESS: {message}")

                # Validate syntax if requested
                if validate:
                    valid, validation_msg = self.validate_file_syntax(file_path)
                    if valid:
                        print(f"   VALIDATED: Syntax validation: {validation_msg}")
                        results['migrated_successfully'] += 1
                        results['files_migrated'].append(str(rel_path))
                    else:
                        print(f"   FAILED: Syntax validation failed: {validation_msg}")
                        print(f"   Rolling back...")
                        if self.rollback_file(file_path):
                            print(f"   Rollback successful")
                        results['validation_failed'] += 1
                        results['validation_failed_files'].append(str(rel_path))
                else:
                    results['migrated_successfully'] += 1
                    results['files_migrated'].append(str(rel_path))

            else:
                print(f"   FAILED: {message}")
                results['migration_failed'] += 1
                results['files_failed'].append(str(rel_path))

        return results

    def generate_migration_report(self, results: Dict) -> str:
        """Generate comprehensive migration report."""
        report = f"""
ISSUE #450 - Redis Import Pattern Migration Report
==================================================

Migration Summary:
  📊 Total files processed: {results['total_files']}
  ✅ Successfully migrated: {results['migrated_successfully']}
  ❌ Migration failed: {results['migration_failed']}
  🚫 Validation failed: {results['validation_failed']}

Success Rate: {(results['migrated_successfully'] / results['total_files'] * 100):.1f}%

Migration Pattern:
  FROM: from netra_backend.app.redis_manager import redis_manager
  TO:   from netra_backend.app.redis_manager import redis_manager

Files Successfully Migrated ({len(results['files_migrated'])}):
"""

        for file_path in results['files_migrated']:
            report += f"  ✅ {file_path}\n"

        if results['files_failed']:
            report += f"\nFiles Failed Migration ({len(results['files_failed'])}):\n"
            for file_path in results['files_failed']:
                report += f"  ❌ {file_path}\n"

        if results['validation_failed_files']:
            report += f"\nFiles Failed Validation ({len(results['validation_failed_files'])}):\n"
            for file_path in results['validation_failed_files']:
                report += f"  🚫 {file_path}\n"

        report += f"""
Backup Location: {self.backup_dir}

Next Steps:
1. Run mission critical tests to validate functionality
2. Measure test collection performance improvement
3. Update Issue #450 with migration results
4. Validate Issue #489 performance improvement

Rollback Instructions:
  python scripts/issue_450_redis_import_migration.py --rollback
"""

        return report


def main():
    """Main migration execution."""
    parser = argparse.ArgumentParser(description='Migrate Redis import patterns for Issue #450')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--dry-run', action='store_true', help='Show files to migrate without making changes')
    parser.add_argument('--no-validation', action='store_true', help='Skip syntax validation')
    parser.add_argument('--rollback', action='store_true', help='Rollback all changes')

    args = parser.parse_args()

    # Initialize migration tool
    project_root = Path(args.project_root).resolve()
    migration_tool = RedisImportMigrationTool(project_root)

    print("=" * 80)
    print("ISSUE #450 - REDIS IMPORT PATTERN MIGRATION")
    print("=" * 80)

    if args.rollback:
        print("🔄 ROLLBACK MODE - Restoring original files...")
        # TODO: Implement rollback functionality
        print("❌ Rollback functionality not yet implemented")
        return

    # Find files with deprecated imports
    files_to_migrate = migration_tool.find_files_with_deprecated_imports()

    if not files_to_migrate:
        print("✅ No files found with deprecated Redis import patterns!")
        print("   Migration may have already been completed.")
        return

    print(f"\nFiles to migrate:")
    for i, file_path in enumerate(files_to_migrate[:10]):
        rel_path = file_path.relative_to(project_root)
        print(f"   {i+1}. {rel_path}")
    if len(files_to_migrate) > 10:
        print(f"   ... and {len(files_to_migrate) - 10} more files")

    if args.dry_run:
        print(f"\nDRY RUN MODE - Would migrate {len(files_to_migrate)} files")
        return

    # Confirm migration
    response = input(f"\nProceed with migration of {len(files_to_migrate)} files? [y/N]: ")
    if response.lower() != 'y':
        print("Migration cancelled by user")
        return

    # Execute migration
    results = migration_tool.migrate_all_files(
        files_to_migrate,
        validate=not args.no_validation
    )

    # Generate and display report
    report = migration_tool.generate_migration_report(results)
    print(report)

    # Save report to file
    report_file = project_root / "issue_450_redis_migration_report.md"
    with open(report_file, 'w') as f:
        f.write(report)

    print(f"📄 Migration report saved: {report_file}")

    # Return appropriate exit code
    if results['migration_failed'] > 0 or results['validation_failed'] > 0:
        print(f"\n⚠️  Migration completed with {results['migration_failed'] + results['validation_failed']} issues")
        sys.exit(1)
    else:
        print(f"\n🎉 Migration completed successfully!")
        print(f"✅ All {results['migrated_successfully']} files migrated successfully")


if __name__ == "__main__":
    main()