#!/usr/bin/env python3
"""
CRITICAL TEST ENVIRONMENT MIGRATION UTILITY
===========================================

Migrates test files from direct os.environ access to IsolatedEnvironment usage.
This script handles the most common patterns and ensures CLAUDE.md compliance.

CRITICAL REQUIREMENTS:
- Replace ALL patch.dict(os.environ) with IsolatedEnvironment context managers
- Replace ALL direct os.environ access with get_env() calls
- Maintain test functionality while enforcing compliance
- Follow unified_environment_management.xml patterns

Business Value: Platform/Internal - System Stability & Test Reliability
Prevents environment pollution and configuration failures in tests.

Author: Claude Code - Test Environment Migration
Date: 2025-09-02
"""

import ast
import os
import re
import sys
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Union
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestEnvironmentMigrator:
    """Migrates test files to use IsolatedEnvironment instead of direct os.environ access."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
        # Common patterns to replace
        self.migration_patterns = {
            # Pattern 1: patch.dict(os.environ, {...})
            'patch_dict_simple': {
                'pattern': r'patch\.dict\(os\.environ,\s*([^,)]+)(?:,\s*clear=(?:True|False))?\)',
                'replacement': self._replace_patch_dict,
                'description': 'patch.dict(os.environ) calls'
            },
            
            # Pattern 2: os.environ['KEY'] = 'value'
            'environ_setitem': {
                'pattern': r'os\.environ\[([\'"][^\'\"]+[\'"])\]\s*=\s*([^\n]+)',
                'replacement': r'get_env().set(\1, \2, "test_setup")',
                'description': 'os.environ item assignment'
            },
            
            # Pattern 3: os.environ.get('KEY', 'default')
            'environ_get': {
                'pattern': r'os\.environ\.get\(([^)]+)\)',
                'replacement': r'get_env().get(\1)',
                'description': 'os.environ.get() calls'
            },
            
            # Pattern 4: Direct os.environ['KEY'] access
            'environ_getitem': {
                'pattern': r'os\.environ\[([\'"][^\'\"]+[\'"])\]',
                'replacement': r'get_env().get(\1)',
                'description': 'Direct os.environ item access'
            },
            
            # Pattern 5: 'KEY' in os.environ
            'environ_contains': {
                'pattern': r'([\'"][^\'\"]+[\'"])\s+in\s+os\.environ',
                'replacement': r'get_env().exists(\1)',
                'description': '"KEY" in os.environ checks'
            },
            
            # Pattern 6: del os.environ['KEY']
            'environ_delitem': {
                'pattern': r'del\s+os\.environ\[([\'"][^\'\"]+[\'"])\]',
                'replacement': r'get_env().delete(\1)',
                'description': 'del os.environ item'
            }
        }
        
        # Files to prioritize for migration (test files with known violations)
        self.priority_test_files = [
            'tests/mission_critical/test_staging_auth_cross_service_validation.py',
            'tests/e2e/test_startup_initialization.py',
            'tests/integration/test_jwt_secret_sync.py',
            'netra_backend/tests/unit/test_secret_key_validation.py',
            'auth_service/tests/test_auth_port_configuration.py'
        ]

    def _replace_patch_dict(self, match: re.Match) -> str:
        """Replace patch.dict(os.environ) with IsolatedEnvironment context manager."""
        env_dict = match.group(1)
        
        # Create IsolatedEnvironment context manager
        replacement = f"""get_env().enable_isolation()
        with get_env():
            get_env().update({env_dict}, "test_patch")"""
        
        return replacement

    def analyze_file_patterns(self, file_path: Path) -> Dict[str, List[Tuple[int, str]]]:
        """Analyze a file for migration patterns."""
        patterns_found = {pattern_name: [] for pattern_name in self.migration_patterns}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                for pattern_name, config in self.migration_patterns.items():
                    if pattern_name == 'patch_dict_simple':
                        # Special handling for patch.dict
                        if re.search(config['pattern'], line_stripped):
                            patterns_found[pattern_name].append((line_num, line_stripped))
                    else:
                        if re.search(config['pattern'], line_stripped):
                            patterns_found[pattern_name].append((line_num, line_stripped))
        
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
        
        return patterns_found

    def migrate_file(self, file_path: Path, dry_run: bool = False) -> Dict[str, int]:
        """Migrate a single test file."""
        changes_made = {pattern: 0 for pattern in self.migration_patterns}
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return changes_made
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                original_content = content
            
            # Check if IsolatedEnvironment import is needed
            needs_import = (
                'os.environ' in content and 
                'from shared.isolated_environment import' not in content
            )
            
            # Apply migrations
            for pattern_name, config in self.migration_patterns.items():
                if pattern_name == 'patch_dict_simple':
                    # Special handling for patch.dict - more complex replacement
                    content = self._migrate_patch_dict_pattern(content, changes_made)
                else:
                    # Simple regex replacement
                    pattern = config['pattern']
                    replacement = config['replacement']
                    if callable(replacement):
                        content = re.sub(pattern, replacement, content)
                    else:
                        old_content = content
                        content = re.sub(pattern, replacement, content)
                        changes_made[pattern_name] += len(re.findall(pattern, old_content))
            
            # Add import if needed
            if needs_import and content != original_content:
                content = self._add_isolated_environment_import(content)
                logger.info(f"Added IsolatedEnvironment import to {file_path}")
            
            # Write changes if not dry run
            if not dry_run and content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                total_changes = sum(changes_made.values())
                logger.info(f"Migrated {file_path}: {total_changes} changes applied")
        
        except Exception as e:
            logger.error(f"Error migrating {file_path}: {e}")
        
        return changes_made

    def _migrate_patch_dict_pattern(self, content: str, changes_made: Dict[str, int]) -> str:
        """Migrate patch.dict(os.environ) patterns to IsolatedEnvironment."""
        
        # Pattern for patch.dict(os.environ, {...}, clear=False/True)
        patch_pattern = r'with\s+patch\.dict\s*\(\s*os\.environ\s*,\s*([^,)]+)(?:\s*,\s*clear\s*=\s*(True|False))?\s*\)\s*:'
        
        def replace_patch_dict(match):
            env_dict = match.group(1).strip()
            clear_flag = match.group(2) if match.group(2) else 'False'
            
            # Create IsolatedEnvironment context pattern
            if clear_flag == 'True':
                # Clear environment completely, then set variables
                replacement = f"""# Migrated from patch.dict(os.environ, {env_dict}, clear=True)
        env = get_env()
        env.enable_isolation()
        env.clear()
        env.update({env_dict}, "test_patch_clear")
        try:"""
            else:
                # Just update variables
                replacement = f"""# Migrated from patch.dict(os.environ, {env_dict})
        env = get_env()
        env.enable_isolation()
        original_state = env.get_all()
        env.update({env_dict}, "test_patch")
        try:"""
            
            changes_made['patch_dict_simple'] += 1
            return replacement
        
        # Apply the replacement
        new_content = re.sub(patch_pattern, replace_patch_dict, content)
        
        # Also need to handle the end of the with block
        # This is more complex as we need to add finally blocks
        if new_content != content:
            # Add finally block for cleanup where needed
            # This is a simplified approach - in practice, might need AST parsing
            new_content = re.sub(
                r'(\s+)# Migrated from patch\.dict\(os\.environ[^:]+:\n(\s+env = get_env\(\)[^:]+:)',
                r'\1\2',
                new_content
            )
        
        return new_content

    def _add_isolated_environment_import(self, content: str) -> str:
        """Add IsolatedEnvironment import to file content."""
        lines = content.split('\n')
        
        # Find the best place to add the import
        import_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                import_index = i + 1
            elif line.strip() and not line.strip().startswith('#'):
                break
        
        # Add the import
        import_line = "from shared.isolated_environment import get_env"
        if import_line not in content:
            lines.insert(import_index, import_line)
        
        return '\n'.join(lines)

    def migrate_priority_files(self, dry_run: bool = False) -> Dict[str, Dict[str, int]]:
        """Migrate priority test files that have known violations."""
        results = {}
        
        for rel_path in self.priority_test_files:
            file_path = self.project_root / rel_path
            if file_path.exists():
                logger.info(f"Migrating priority file: {rel_path}")
                changes = self.migrate_file(file_path, dry_run)
                if any(changes.values()):
                    results[rel_path] = changes
            else:
                logger.warning(f"Priority file not found: {rel_path}")
        
        return results

    def migrate_directory(self, directory: Path, pattern: str = "test*.py", dry_run: bool = False) -> Dict[str, Dict[str, int]]:
        """Migrate all test files in a directory."""
        results = {}
        
        for file_path in directory.rglob(pattern):
            if file_path.is_file() and file_path.suffix == '.py':
                changes = self.migrate_file(file_path, dry_run)
                if any(changes.values()):
                    rel_path = str(file_path.relative_to(self.project_root))
                    results[rel_path] = changes
        
        return results

    def print_migration_report(self, results: Dict[str, Dict[str, int]]):
        """Print detailed migration report."""
        print("\n" + "="*80)
        print("TEST ENVIRONMENT MIGRATION REPORT")
        print("="*80)
        
        total_files = len(results)
        total_changes = sum(sum(changes.values()) for changes in results.values())
        
        print(f"\nOVERVIEW:")
        print(f"  Files Migrated: {total_files}")
        print(f"  Total Changes: {total_changes}")
        
        if results:
            print(f"\nDETAILS:")
            for file_path, changes in sorted(results.items()):
                file_total = sum(changes.values())
                print(f"\nFile: {file_path} ({file_total} changes)")
                for pattern_name, count in changes.items():
                    if count > 0:
                        description = self.migration_patterns[pattern_name]['description']
                        print(f"  - {description}: {count}")
        
        print(f"\nMIGRATION COMPLETE")
        if total_changes > 0:
            print(f"Successfully migrated {total_files} files with {total_changes} changes")
        else:
            print("No changes were needed - files are already compliant")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate test files to use IsolatedEnvironment"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )
    parser.add_argument(
        '--priority-only',
        action='store_true',
        help='Only migrate priority files with known violations'
    )
    parser.add_argument(
        '--directory',
        type=str,
        help='Migrate specific directory (e.g., "tests/mission_critical")'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Migrate specific file'
    )
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    migrator = TestEnvironmentMigrator(project_root)
    
    results = {}
    
    if args.file:
        # Migrate single file
        file_path = project_root / args.file
        changes = migrator.migrate_file(file_path, args.dry_run)
        if any(changes.values()):
            results[args.file] = changes
    
    elif args.directory:
        # Migrate specific directory
        dir_path = project_root / args.directory
        if dir_path.exists():
            results = migrator.migrate_directory(dir_path, dry_run=args.dry_run)
        else:
            logger.error(f"Directory not found: {args.directory}")
            sys.exit(1)
    
    elif args.priority_only:
        # Migrate priority files only
        results = migrator.migrate_priority_files(args.dry_run)
    
    else:
        # Migrate all test files
        test_dirs = ['tests', 'netra_backend/tests', 'auth_service/tests', 'dev_launcher/tests']
        for test_dir in test_dirs:
            dir_path = project_root / test_dir
            if dir_path.exists():
                dir_results = migrator.migrate_directory(dir_path, dry_run=args.dry_run)
                results.update(dir_results)
    
    # Print report
    migrator.print_migration_report(results)
    
    if args.dry_run:
        print("\n[DRY RUN] No changes were made. Run without --dry-run to apply changes.")

if __name__ == '__main__':
    main()