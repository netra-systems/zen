#!/usr/bin/env python3
"""
Automated fix for Issue #1041 - rename Test* classes to avoid pytest collection.

Business Value Justification (BVJ):
- Segment: Platform (testing infrastructure)
- Business Goal: Stability (reliable test discovery and execution)
- Value Impact: Enables fast, comprehensive test coverage validation
- Strategic Impact: $500K+ ARR protection through testing reliability

This script automatically renames problematic Test* classes to *Tests pattern,
resolving pytest collection failures while preserving test functionality.

Usage:
    python scripts/fix_issue_1041_test_class_renaming.py [--dry-run] [--backup]

Options:
    --dry-run: Show what would be changed without making modifications
    --backup: Create .backup files before making changes (default: True)
    --no-backup: Skip creating backup files
"""
import os
import re
import shutil
import argparse
import sys
from datetime import datetime
from typing import List, Dict, Tuple

class TestClassRenamer:
    """Automated renamer for Test* classes to resolve pytest collection issues."""

    def __init__(self, dry_run: bool = False, create_backup: bool = True):
        self.dry_run = dry_run
        self.create_backup = create_backup
        self.files_processed = 0
        self.classes_renamed = 0
        self.errors = []

    def find_test_star_classes(self, file_path: str) -> List[Tuple[str, str]]:
        """Find all Test* class definitions in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Pattern to match class definitions starting with Test
            pattern = re.compile(r'^(\s*)class (Test[A-Z]\w*)(\([^)]*\))?:', re.MULTILINE)
            matches = []

            for match in pattern.finditer(content):
                indent = match.group(1)
                class_name = match.group(2)
                inheritance = match.group(3) or ''

                # Skip classes that are already properly named
                if class_name.endswith('Tests') or class_name.endswith('TestCase'):
                    continue

                # Convert TestClassName to ClassNameTests
                new_name = class_name[4:] + 'Tests'  # Remove 'Test' prefix, add 'Tests' suffix

                matches.append((class_name, new_name))

            return matches

        except Exception as e:
            self.errors.append(f"Error reading {file_path}: {e}")
            return []

    def rename_classes_in_file(self, file_path: str) -> bool:
        """Rename Test* classes in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            classes_in_file = []

            # Pattern to match class definitions
            def replace_class_definition(match):
                indent = match.group(1)
                class_name = match.group(2)
                inheritance = match.group(3) or ''

                # Skip already properly named classes
                if class_name.endswith('Tests') or class_name.endswith('TestCase'):
                    return match.group(0)

                # Convert TestClassName to ClassNameTests
                new_name = class_name[4:] + 'Tests'
                classes_in_file.append((class_name, new_name))

                return f'{indent}class {new_name}{inheritance}:'

            # Replace class definitions
            pattern = re.compile(r'^(\s*)class (Test[A-Z]\w*)(\([^)]*\))?:', re.MULTILINE)
            new_content = pattern.sub(replace_class_definition, content)

            # Also replace any references to the old class names in the same file
            for old_name, new_name in classes_in_file:
                # Replace references (but be careful not to replace partial matches)
                reference_pattern = re.compile(r'\b' + re.escape(old_name) + r'\b')
                new_content = reference_pattern.sub(new_name, new_content)

            if new_content != original_content:
                if not self.dry_run:
                    # Create backup if requested
                    if self.create_backup:
                        backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.copy2(file_path, backup_path)

                    # Write the modified content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                self.files_processed += 1
                self.classes_renamed += len(classes_in_file)

                print(f"{'[DRY RUN] ' if self.dry_run else ''}Fixed: {file_path}")
                for old_name, new_name in classes_in_file:
                    print(f"  {old_name} -> {new_name}")

                return True

            return False

        except Exception as e:
            self.errors.append(f"Error processing {file_path}: {e}")
            return False

    def find_test_files(self) -> List[str]:
        """Find all test files that might contain Test* classes."""
        test_files = []

        # Directories to scan for test files
        test_directories = [
            'netra_backend/tests',
            'tests',
            'auth_service/tests',
            'analytics_service/tests',
            'dev_launcher/tests'
        ]

        for test_dir in test_directories:
            if os.path.exists(test_dir):
                for root, dirs, files in os.walk(test_dir):
                    # Skip backup directories and git directories
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

                    for file in files:
                        if file.startswith('test_') and file.endswith('.py'):
                            # Skip backup files
                            if '.backup.' not in file:
                                file_path = os.path.join(root, file)
                                test_files.append(file_path)

        return test_files

    def analyze_scope(self) -> Dict:
        """Analyze the scope of Test* classes across the codebase."""
        test_files = self.find_test_files()
        analysis = {
            'total_files': len(test_files),
            'files_with_test_classes': 0,
            'total_test_classes': 0,
            'problematic_classes': []
        }

        for file_path in test_files:
            test_classes = self.find_test_star_classes(file_path)
            if test_classes:
                analysis['files_with_test_classes'] += 1
                analysis['total_test_classes'] += len(test_classes)
                analysis['problematic_classes'].extend([
                    {'file': file_path, 'old_name': old, 'new_name': new}
                    for old, new in test_classes
                ])

        return analysis

    def run_fix(self) -> bool:
        """Run the complete fix process."""
        print(f"Issue #1041 Test* Class Renaming Fix")
        print(f"{'=' * 50}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Backup: {'YES' if self.create_backup else 'NO'}")
        print()

        # First, analyze the scope
        print("Analyzing scope...")
        analysis = self.analyze_scope()

        print(f"Analysis Results:")
        print(f"  Total test files: {analysis['total_files']}")
        print(f"  Files with Test* classes: {analysis['files_with_test_classes']}")
        print(f"  Total Test* classes to rename: {analysis['total_test_classes']}")
        print()

        if analysis['total_test_classes'] == 0:
            print("No Test* classes found that need renaming.")
            return True

        # Show first 10 classes as examples
        print("Example Test* classes to be renamed:")
        for i, cls in enumerate(analysis['problematic_classes'][:10]):
            print(f"  {cls['old_name']} -> {cls['new_name']} ({cls['file']})")
        if len(analysis['problematic_classes']) > 10:
            print(f"  ... and {len(analysis['problematic_classes']) - 10} more")
        print()

        if self.dry_run:
            print("DRY RUN: No changes will be made.")
            return True

        # Confirm with user if not dry run
        try:
            response = input(f"Proceed with renaming {analysis['total_test_classes']} classes in {analysis['files_with_test_classes']} files? (y/N): ")
            if response.lower() != 'y':
                print("Operation cancelled.")
                return False
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return False

        # Process files
        print("\nProcessing files...")
        test_files = self.find_test_files()

        for file_path in test_files:
            test_classes = self.find_test_star_classes(file_path)
            if test_classes:
                self.rename_classes_in_file(file_path)

        # Report results
        print(f"\nResults:")
        print(f"  Files processed: {self.files_processed}")
        print(f"  Classes renamed: {self.classes_renamed}")

        if self.errors:
            print(f"  Errors: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"    {error}")
            if len(self.errors) > 5:
                print(f"    ... and {len(self.errors) - 5} more errors")

        return len(self.errors) == 0

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix Issue #1041 by renaming Test* classes to *Tests pattern"
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help="Show what would be changed without making modifications"
    )
    parser.add_argument(
        '--no-backup', action='store_true',
        help="Skip creating backup files (default: create backups)"
    )
    parser.add_argument(
        '--analyze-only', action='store_true',
        help="Only analyze the scope without making changes"
    )

    args = parser.parse_args()

    # Create renamer instance
    renamer = TestClassRenamer(
        dry_run=args.dry_run or args.analyze_only,
        create_backup=not args.no_backup
    )

    if args.analyze_only:
        print("Issue #1041 Scope Analysis")
        print("=" * 30)
        analysis = renamer.analyze_scope()

        print(f"Total test files: {analysis['total_files']}")
        print(f"Files with Test* classes: {analysis['files_with_test_classes']}")
        print(f"Total Test* classes: {analysis['total_test_classes']}")

        if analysis['problematic_classes']:
            print("\nProblematic classes:")
            for i, cls in enumerate(analysis['problematic_classes'][:20]):
                print(f"  {i+1:2d}. {cls['old_name']} -> {cls['new_name']}")
                print(f"      in {cls['file']}")

            if len(analysis['problematic_classes']) > 20:
                print(f"  ... and {len(analysis['problematic_classes']) - 20} more")

        return 0

    # Run the fix
    success = renamer.run_fix()

    if success:
        print("\nFix completed successfully!")
        print("\nNext steps:")
        print("1. Run validation tests:")
        print("   python -m pytest tests/validation/test_collection_failure_reproduction.py")
        print("   python -m pytest tests/validation/test_rename_validation.py")
        print("2. Test collection performance:")
        print("   python -m pytest --collect-only -q netra_backend/tests/unit/websocket")
        print("3. Verify no regressions in test execution")
        return 0
    else:
        print("\nFix completed with errors. Check the error messages above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())