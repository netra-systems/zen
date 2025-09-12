#!/usr/bin/env python3
"""
Phase 2A: DeepAgentState Simple Import Migration
===============================================

Automated migration script for Phase 2A - Simple Import Migrations.
This script handles files with straightforward DeepAgentState imports and usage
that can be safely automated.

MIGRATION APPROACH:
1. Import replacement: DeepAgentState → UserExecutionContext
2. Constructor calls: DeepAgentState(...) → UserExecutionContext.from_state_data(...)
3. Type hints: DeepAgentState → UserExecutionContext
4. Validation: Syntax check after each file

SAFETY MEASURES:
- Git status check before starting
- Backup each file before modification
- Syntax validation after each change
- Progress tracking with rollback capability
"""

import os
import re
import ast
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
import shutil
import tempfile

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class MigrationResult:
    """Result of migrating a single file."""
    file_path: str
    original_references: int
    migrated_references: int
    success: bool
    error_message: Optional[str] = None
    syntax_valid: bool = False


class Phase2ASimpleMigrator:
    """Handles Phase 2A simple import migrations for DeepAgentState elimination."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[MigrationResult] = []
        self.backup_dir = None
        
        # Migration patterns
        self.import_patterns = [
            # Standard import
            (r'from\s+netra_backend\.app\.agents\.state\s+import\s+DeepAgentState',
             'from netra_backend.app.services.user_execution_context import UserExecutionContext'),
            
            # Import with other classes
            (r'from\s+netra_backend\.app\.agents\.state\s+import\s+([^,]*,\s*)*DeepAgentState([^,\n]*)',
             lambda m: m.group(0).replace('DeepAgentState', 'UserExecutionContext').replace(
                 'netra_backend.app.agents.state', 'netra_backend.app.services.user_execution_context')),
            
            # Multiple imports on same line
            (r'from\s+netra_backend\.app\.agents\.state\s+import\s+[^,]*DeepAgentState[^,\n]*',
             'from netra_backend.app.services.user_execution_context import UserExecutionContext'),
        ]
        
        self.usage_patterns = [
            # Simple constructor calls - this needs careful handling
            # We'll identify these but handle them manually in complex cases
            (r'DeepAgentState\s*\(([^)]*)\)', self._convert_constructor_call),
            
            # Type hints
            (r':\s*DeepAgentState', ': UserExecutionContext'),
            (r'->\s*DeepAgentState', '-> UserExecutionContext'),
            
            # Variable declarations
            (r'=\s*DeepAgentState\(', '= UserExecutionContext.from_state_data('),
        ]
    
    def _convert_constructor_call(self, match) -> str:
        """Convert DeepAgentState constructor call to UserExecutionContext.from_state_data."""
        args = match.group(1).strip()
        if not args:
            # Empty constructor - needs manual handling
            return f"# TODO: MIGRATE - DeepAgentState() needs manual conversion to UserExecutionContext"
        
        # For now, use from_state_data wrapper
        return f"UserExecutionContext.from_state_data({args})"
    
    def setup_backup_directory(self) -> Path:
        """Create backup directory for modified files."""
        timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = self.project_root / f"migration_backups/phase_2a_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir = backup_dir
        print(f"Created backup directory: {backup_dir}")
        return backup_dir
    
    def backup_file(self, file_path: Path) -> Path:
        """Create backup of file before modification."""
        if not self.backup_dir:
            self.setup_backup_directory()
        
        # Create relative path structure in backup
        rel_path = file_path.relative_to(self.project_root)
        backup_file_path = self.backup_dir / rel_path
        backup_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(file_path, backup_file_path)
        return backup_file_path
    
    def validate_git_status(self) -> bool:
        """Ensure git working directory is clean before migration."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'], 
                cwd=self.project_root, 
                capture_output=True, 
                text=True, 
                check=True
            )
            if result.stdout.strip():
                print("WARNING: Git working directory is not clean.")
                print("   Uncommitted changes detected:")
                print(result.stdout)
                response = input("   Continue anyway? (y/N): ")
                return response.lower() == 'y'
            return True
        except subprocess.CalledProcessError:
            print("WARNING: Could not check git status. Continuing...")
            return True
    
    def count_deepagentstate_references(self, file_path: Path) -> int:
        """Count DeepAgentState references in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content.count('DeepAgentState')
        except Exception:
            return 0
    
    def validate_syntax(self, file_path: Path) -> bool:
        """Validate Python syntax of file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            return True
        except SyntaxError as e:
            print(f"ERROR: Syntax error in {file_path}:{e.lineno}: {e.msg}")
            return False
        except Exception as e:
            print(f"ERROR: Error validating {file_path}: {e}")
            return False
    
    def migrate_file(self, file_path: Path) -> MigrationResult:
        """Migrate a single file from DeepAgentState to UserExecutionContext."""
        
        print(f"Migrating: {file_path}")
        
        # Count original references
        original_refs = self.count_deepagentstate_references(file_path)
        print(f"   Original DeepAgentState references: {original_refs}")
        
        if original_refs == 0:
            return MigrationResult(
                file_path=str(file_path),
                original_references=0,
                migrated_references=0,
                success=True,
                syntax_valid=True
            )
        
        # Backup original file
        backup_path = self.backup_file(file_path)
        print(f"   Backed up to: {backup_path}")
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply import pattern replacements
            for pattern, replacement in self.import_patterns:
                if callable(replacement):
                    content = re.sub(pattern, replacement, content)
                else:
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            # Apply usage pattern replacements
            for pattern, replacement in self.usage_patterns:
                if callable(replacement):
                    content = re.sub(pattern, replacement, content)
                else:
                    content = re.sub(pattern, replacement, content)
            
            # Write modified content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Count remaining references
            remaining_refs = self.count_deepagentstate_references(file_path)
            migrated_count = original_refs - remaining_refs
            
            # Validate syntax
            syntax_valid = self.validate_syntax(file_path)
            
            if not syntax_valid:
                # Restore backup
                shutil.copy2(backup_path, file_path)
                return MigrationResult(
                    file_path=str(file_path),
                    original_references=original_refs,
                    migrated_references=0,
                    success=False,
                    error_message="Syntax validation failed - restored backup",
                    syntax_valid=False
                )
            
            success = migrated_count > 0
            if success:
                print(f"   SUCCESS: Migrated {migrated_count} references ({remaining_refs} remaining)")
            else:
                print(f"   WARNING: No references migrated ({remaining_refs} remaining)")
            
            return MigrationResult(
                file_path=str(file_path),
                original_references=original_refs,
                migrated_references=migrated_count,
                success=success,
                syntax_valid=syntax_valid
            )
            
        except Exception as e:
            # Restore backup on any error
            if backup_path.exists():
                shutil.copy2(backup_path, file_path)
            
            return MigrationResult(
                file_path=str(file_path),
                original_references=original_refs,
                migrated_references=0,
                success=False,
                error_message=str(e),
                syntax_valid=False
            )
    
    def find_simple_migration_candidates(self) -> List[Path]:
        """Find files suitable for Phase 2A simple migration."""
        
        # Get files with single DeepAgentState references (likely simple imports)
        simple_candidates = []
        
        try:
            result = subprocess.run(
                ['rg', 'DeepAgentState', '--type', 'py', '-c'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            for line in result.stdout.strip().split('\n'):
                if ':' not in line:
                    continue
                    
                file_path_str, count_str = line.split(':', 1)
                try:
                    count = int(count_str)
                    file_path = self.project_root / file_path_str
                    
                    # Consider files with 1-3 references as simple candidates
                    if count <= 3 and file_path.exists():
                        simple_candidates.append(file_path)
                        
                except (ValueError, OSError):
                    continue
                    
        except subprocess.CalledProcessError:
            print("ERROR: Could not find DeepAgentState references with ripgrep")
            return []
        
        print(f"Found {len(simple_candidates)} simple migration candidates")
        return simple_candidates[:20]  # Limit to first 20 for Phase 2A
    
    def run_migration_batch(self, files: List[Path]) -> Dict:
        """Run migration on a batch of files."""
        
        print(f"\nStarting Phase 2A migration on {len(files)} files")
        print("=" * 60)
        
        results = []
        successful = 0
        failed = 0
        
        for file_path in files:
            result = self.migrate_file(file_path)
            results.append(result)
            
            if result.success:
                successful += 1
            else:
                failed += 1
                print(f"   FAILED: {result.error_message}")
        
        # Summary
        total_original_refs = sum(r.original_references for r in results)
        total_migrated_refs = sum(r.migrated_references for r in results)
        
        print("\n" + "=" * 60)
        print("PHASE 2A MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Files processed: {len(files)}")
        print(f"Successful migrations: {successful}")
        print(f"Failed migrations: {failed}")
        print(f"Original references: {total_original_refs}")
        print(f"Migrated references: {total_migrated_refs}")
        print(f"Migration rate: {(total_migrated_refs/total_original_refs*100):.1f}%" if total_original_refs > 0 else "0%")
        
        if self.backup_dir:
            print(f"Backups stored in: {self.backup_dir}")
        
        return {
            'files_processed': len(files),
            'successful': successful,
            'failed': failed,
            'total_original_refs': total_original_refs,
            'total_migrated_refs': total_migrated_refs,
            'results': results,
            'backup_dir': str(self.backup_dir) if self.backup_dir else None
        }


def main():
    """Main migration execution."""
    
    print("DeepAgentState Phase 2A: Simple Import Migration")
    print("=" * 60)
    print("This script migrates simple DeepAgentState imports to UserExecutionContext.")
    print("Files are backed up before modification and syntax validated after.")
    print("=" * 60)
    
    migrator = Phase2ASimpleMigrator(PROJECT_ROOT)
    
    # Validate git status
    if not migrator.validate_git_status():
        print("ERROR: Aborting migration due to git status")
        return 1
    
    # Find candidates
    candidates = migrator.find_simple_migration_candidates()
    if not candidates:
        print("ERROR: No suitable candidates found for Phase 2A migration")
        return 1
    
    print(f"\nMigration candidates:")
    for i, file_path in enumerate(candidates[:10], 1):  # Show first 10
        refs = migrator.count_deepagentstate_references(file_path)
        rel_path = file_path.relative_to(PROJECT_ROOT)
        print(f"   {i:2d}. {rel_path} ({refs} refs)")
    
    if len(candidates) > 10:
        print(f"   ... and {len(candidates) - 10} more files")
    
    print(f"\nReady to migrate {len(candidates)} files.")
    response = input("Continue with migration? (y/N): ")
    
    if response.lower() != 'y':
        print("ERROR: Migration cancelled by user")
        return 1
    
    # Run migration
    summary = migrator.run_migration_batch(candidates)
    
    # Final validation - check remaining references
    try:
        result = subprocess.run(
            ['rg', 'DeepAgentState', '--type', 'py'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        remaining_refs = len(result.stdout.split('\n')) if result.stdout else 0
        print(f"\nRemaining DeepAgentState references after Phase 2A: {remaining_refs}")
    except:
        print("Could not count remaining references")
    
    # Success criteria
    if summary['successful'] > 0 and summary['total_migrated_refs'] > 0:
        print("\nSUCCESS: Phase 2A migration completed successfully!")
        print("   Next step: Run Phase 2B for method signature updates")
        return 0
    else:
        print("\nWARNING: Phase 2A migration had limited impact")
        print("   Consider manual review of candidates")
        return 1


if __name__ == '__main__':
    sys.exit(main())