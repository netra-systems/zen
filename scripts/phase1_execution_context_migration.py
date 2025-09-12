#!/usr/bin/env python3
"""
Phase 1: UserExecutionContext ID Migration Script for Issue #89

ENTERPRISE CRITICAL: This script addresses UserExecutionContext isolation issues 
that risk cross-user data leakage in multi-user environments.

TARGET FILES:
1. netra_backend/app/agents/base/execution_context.py
2. netra_backend/app/agents/supervisor/agent_execution_context_manager.py

MIGRATION APPROACH:
- Replace uuid.uuid4() with user-specific UnifiedIdGenerator methods
- Ensure proper user isolation in ID generation
- Update context factory patterns to use SSOT methods
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Dict
import argparse


class ExecutionContextIDMigrationTool:
    """Tool for migrating UserExecutionContext UUID patterns to SSOT compliance."""
    
    def __init__(self, project_root: str, dry_run: bool = True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.backup_dir = self.project_root / "backup" / "execution_context_migration"
        self.migrations_applied = []
        
    def run_migration(self) -> None:
        """Execute the complete UserExecutionContext ID migration."""
        print("Starting Phase 1: UserExecutionContext ID Migration")
        print("=" * 55)
        
        if not self.dry_run:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            print(f"Backup directory: {self.backup_dir}")
        
        # Migration targets
        migration_targets = [
            {
                'file': 'netra_backend/app/agents/base/execution_context.py',
                'patterns': [
                    {
                        'search': r'self\.execution_id = execution_id or str\(uuid\.uuid4\(\)\)',
                        'replace': '''self.execution_id = execution_id or UnifiedIdGenerator.generate_agent_execution_id(
            agent_type=getattr(self, 'agent_type', 'unknown'), 
            user_id=getattr(self, 'user_id', 'system')
        )''',
                        'imports': ['from shared.id_generation.unified_id_generator import UnifiedIdGenerator'],
                        'line_context': 'execution_id_generation',
                        'description': 'Replace execution_id generation with user-aware SSOT method'
                    }
                ]
            },
            {
                'file': 'netra_backend/app/agents/supervisor/agent_execution_context_manager.py',
                'patterns': [
                    {
                        'search': r'session_id = f"session_\{uuid\.uuid4\(\)\.hex\[:12\]\}"',
                        'replace': '''# Generate user-specific context IDs for proper isolation
        context_ids = UnifiedIdGenerator.generate_user_context_ids(user_id, "agent_execution")
        session_id = context_ids[0]  # thread_id for session tracking''',
                        'imports': ['from shared.id_generation.unified_id_generator import UnifiedIdGenerator'],
                        'line_context': 'session_id_generation',
                        'description': 'Replace session_id with user-specific SSOT generation'
                    },
                    {
                        'search': r'run_id = RunID\(f"run_\{uuid\.uuid4\(\)\.hex\[:12\]\}"\)',
                        'replace': '''# Use SSOT context generation for run_id
        if 'context_ids' not in locals():
            context_ids = UnifiedIdGenerator.generate_user_context_ids(user_id, "agent_execution")
        run_id = RunID(context_ids[1])  # run_id from SSOT generation''',
                        'imports': ['from shared.id_generation.unified_id_generator import UnifiedIdGenerator'],
                        'line_context': 'run_id_generation',
                        'description': 'Replace run_id with SSOT-compliant user context ID'
                    },
                    {
                        'search': r'request_id = RequestID\(f"req_\{uuid\.uuid4\(\)\.hex\[:12\]\}"\)',
                        'replace': '''# Use SSOT context generation for request_id
        if 'context_ids' not in locals():
            context_ids = UnifiedIdGenerator.generate_user_context_ids(user_id, "agent_execution")
        request_id = RequestID(context_ids[2])  # request_id from SSOT generation''',
                        'imports': ['from shared.id_generation.unified_id_generator import UnifiedIdGenerator'],
                        'line_context': 'request_id_generation',
                        'description': 'Replace request_id with SSOT-compliant user context ID'
                    }
                ]
            }
        ]
        
        # Apply migrations
        for target in migration_targets:
            self.migrate_file(target)
        
        # Summary
        print("\nMigration Summary:")
        print("-" * 30)
        if self.migrations_applied:
            for migration in self.migrations_applied:
                print(f"[OK] {migration}")
        else:
            print("No migrations applied (files may not exist or already migrated)")
        
        if self.dry_run:
            print("\n*** DRY RUN MODE - No files were actually modified ***")
        else:
            print(f"\n*** LIVE MODE - {len(self.migrations_applied)} files modified ***")
            print(f"Backups saved to: {self.backup_dir}")
    
    def migrate_file(self, target: Dict) -> None:
        """Migrate a single file according to its pattern specifications."""
        file_path = self.project_root / target['file']
        
        if not file_path.exists():
            print(f"WARNING: File not found: {file_path}")
            return
        
        print(f"\nMigrating: {target['file']}")
        
        # Read current content
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        modified_content = original_content
        patterns_applied = []
        imports_needed = set()
        
        # Apply each pattern
        for pattern in target['patterns']:
            search_pattern = pattern['search']
            replacement = pattern['replace']
            
            if re.search(search_pattern, modified_content, re.MULTILINE):
                modified_content = re.sub(search_pattern, replacement, modified_content, flags=re.MULTILINE)
                patterns_applied.append(f"  [OK] {pattern['line_context']}: {pattern['description']}")
                imports_needed.update(pattern['imports'])
                
                print(f"  Pattern matched: {pattern['line_context']}")
                print(f"    Description: {pattern['description']}")
            else:
                print(f"  Pattern not found: {pattern['line_context']} (may be already migrated)")
        
        # Add required imports if content was modified
        if patterns_applied and imports_needed:
            modified_content = self.add_imports(modified_content, list(imports_needed))
        
        # Apply changes if any patterns matched
        if patterns_applied:
            if not self.dry_run:
                # Create backup
                backup_path = self.backup_dir / target['file'].replace('/', '_').replace('\\', '_')
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, backup_path)
                
                # Write modified content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                self.migrations_applied.append(f"{target['file']} ({len(patterns_applied)} patterns)")
            else:
                print(f"  DRY RUN: Would apply {len(patterns_applied)} patterns")
                for pattern in patterns_applied:
                    print(pattern)
        else:
            print(f"  No changes needed for {target['file']}")
    
    def add_imports(self, content: str, imports: List[str]) -> str:
        """Add required imports to the file content."""
        lines = content.split('\n')
        
        # Find the best place to insert imports (after existing imports)
        import_end_index = 0
        for i, line in enumerate(lines):
            if (line.strip().startswith('import ') or 
                line.strip().startswith('from ') or
                line.strip().startswith('#') or
                line.strip() == '' or
                '"""' in line):
                import_end_index = i
            else:
                break
        
        # Check if imports already exist
        imports_to_add = []
        for import_line in imports:
            if import_line not in content:
                imports_to_add.append(import_line)
        
        # Add new imports after existing imports
        if imports_to_add:
            # Add blank line before new imports if needed
            if import_end_index < len(lines) and lines[import_end_index].strip():
                lines.insert(import_end_index + 1, '')
                import_end_index += 1
            
            for import_line in imports_to_add:
                lines.insert(import_end_index + 1, import_line)
                import_end_index += 1
            
            print(f"  Adding imports: {', '.join(imports_to_add)}")
        
        return '\n'.join(lines)
    
    def validate_migration(self, file_path: Path) -> List[str]:
        """Validate that the migration was successful."""
        issues = []
        
        if not file_path.exists():
            issues.append(f"File not found: {file_path}")
            return issues
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for remaining uuid.uuid4() patterns
        remaining_uuids = re.findall(r'uuid\.uuid4\(\)', content)
        if remaining_uuids:
            issues.append(f"Found {len(remaining_uuids)} remaining uuid.uuid4() patterns")
        
        # Check that UnifiedIdGenerator import was added
        if 'UnifiedIdGenerator' in content and 'from shared.id_generation.unified_id_generator import UnifiedIdGenerator' not in content:
            issues.append("UnifiedIdGenerator used but import not found")
        
        return issues


def main():
    """Main migration entry point."""
    parser = argparse.ArgumentParser(description="Migrate UserExecutionContext UUID patterns to SSOT compliance")
    parser.add_argument('--project-root', default='C:/GitHub/netra-apex',
                       help='Project root directory')
    parser.add_argument('--live', action='store_true',
                       help='Apply changes (default is dry run)')
    parser.add_argument('--force', action='store_true',
                       help='Force migration even if backups exist')
    parser.add_argument('--validate', action='store_true',
                       help='Validate migration results after applying')
    
    args = parser.parse_args()
    
    # Check for existing backups if in live mode
    if args.live and not args.force:
        backup_dir = Path(args.project_root) / "backup" / "execution_context_migration"
        if backup_dir.exists() and any(backup_dir.iterdir()):
            print("WARNING: Backup directory exists with files. Use --force to override.")
            print(f"Backup directory: {backup_dir}")
            return
    
    # Run migration
    migrator = ExecutionContextIDMigrationTool(args.project_root, dry_run=not args.live)
    migrator.run_migration()
    
    # Validate migration if requested and in live mode
    if args.validate and args.live:
        print("\nValidating Migration Results:")
        print("-" * 30)
        
        validation_files = [
            'netra_backend/app/agents/base/execution_context.py',
            'netra_backend/app/agents/supervisor/agent_execution_context_manager.py'
        ]
        
        all_issues = []
        for file_path in validation_files:
            full_path = Path(args.project_root) / file_path
            issues = migrator.validate_migration(full_path)
            if issues:
                print(f"Issues in {file_path}:")
                for issue in issues:
                    print(f"  WARNING: {issue}")
                all_issues.extend(issues)
            else:
                print(f"[OK] {file_path} - No issues found")
        
        if all_issues:
            print(f"\nWARNING: Found {len(all_issues)} validation issues")
        else:
            print("\n[OK] All validations passed")
    
    print("\nNext Steps:")
    print("1. Review changed files for correctness")
    print("2. Run UserExecutionContext tests to validate functionality") 
    print("3. Test multi-user isolation in staging environment")
    print("4. Run failing migration compliance tests to verify fixes")
    print("5. Monitor for cross-user data leakage issues after deployment")


if __name__ == "__main__":
    main()