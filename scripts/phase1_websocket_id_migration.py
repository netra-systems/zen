#!/usr/bin/env python3
"""
Phase 1: WebSocket ID Migration Script for Issue #89

BUSINESS CRITICAL: This script addresses WebSocket ID consistency issues that cause
1011 errors and break $500K+ ARR chat functionality.

TARGET FILES:
1. netra_backend/app/core/websocket_message_handler.py
2. netra_backend/app/agents/supervisor/agent_registry.py  
3. WebSocket factory cleanup patterns

MIGRATION APPROACH:
- Replace uuid.uuid4() patterns with UnifiedIdGenerator methods
- Maintain backward compatibility during transition
- Enable cleanup logic to work with mixed ID formats
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Dict
import argparse


class WebSocketIDMigrationTool:
    """Tool for migrating WebSocket-related UUID patterns to SSOT compliance."""
    
    def __init__(self, project_root: str, dry_run: bool = True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.backup_dir = self.project_root / "backup" / "websocket_id_migration"
        self.migrations_applied = []
        
    def run_migration(self) -> None:
        """Execute the complete WebSocket ID migration."""
        print("Starting Phase 1: WebSocket ID Migration")
        print("=" * 50)
        
        if not self.dry_run:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            print(f"Backup directory: {self.backup_dir}")
        
        # Migration targets with specific patterns
        migration_targets = [
            {
                'file': 'netra_backend/app/core/websocket_message_handler.py',
                'patterns': [
                    {
                        'search': r'return str\(uuid\.uuid4\(\)\)',
                        'replace': 'return UnifiedIdGenerator.generate_base_id("websocket_message")',
                        'imports': ['from shared.id_generation.unified_id_generator import UnifiedIdGenerator'],
                        'line_context': 'generate_message_id'
                    }
                ]
            },
            {
                'file': 'netra_backend/app/agents/supervisor/agent_registry.py',
                'patterns': [
                    {
                        'search': r'f"websocket_setup_\{uuid\.uuid4\(\)\.hex\[:8\]\}"',
                        'replace': 'UnifiedIdGenerator.generate_base_id("websocket_setup")',
                        'imports': ['from shared.id_generation.unified_id_generator import UnifiedIdGenerator'],
                        'line_context': 'request_id'
                    },
                    {
                        'search': r'f"websocket_run_\{uuid\.uuid4\(\)\.hex\[:8\]\}"',
                        'replace': 'UnifiedIdGenerator.generate_base_id("websocket_run")',
                        'imports': ['from shared.id_generation.unified_id_generator import UnifiedIdGenerator'],
                        'line_context': 'run_id'
                    },
                    {
                        'search': r'f"websocket_setup_async_\{uuid\.uuid4\(\)\.hex\[:8\]\}"',
                        'replace': 'UnifiedIdGenerator.generate_base_id("websocket_setup_async")',
                        'imports': ['from shared.id_generation.unified_id_generator import UnifiedIdGenerator'],
                        'line_context': 'async_request_id'
                    },
                    {
                        'search': r'f"websocket_run_async_\{uuid\.uuid4\(\)\.hex\[:8\]\}"',
                        'replace': 'UnifiedIdGenerator.generate_base_id("websocket_run_async")',
                        'imports': ['from shared.id_generation.unified_id_generator import UnifiedIdGenerator'],
                        'line_context': 'async_run_id'
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
            print(f"⚠️  File not found: {file_path}")
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
            
            if re.search(search_pattern, modified_content):
                modified_content = re.sub(search_pattern, replacement, modified_content)
                patterns_applied.append(f"  [OK] {pattern['line_context']}: {search_pattern[:30]}...")
                imports_needed.update(pattern['imports'])
                
                print(f"  Pattern matched: {pattern['line_context']}")
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
            print(f"  No changes needed")
    
    def add_imports(self, content: str, imports: List[str]) -> str:
        """Add required imports to the file content."""
        lines = content.split('\n')
        
        # Find existing imports section
        import_end_index = 0
        for i, line in enumerate(lines):
            if (line.strip().startswith('import ') or 
                line.strip().startswith('from ') or
                line.strip().startswith('#') or
                line.strip() == ''):
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
            lines.insert(import_end_index + 1, '')
            for import_line in reversed(imports_to_add):
                lines.insert(import_end_index + 1, import_line)
            
            print(f"  Adding imports: {', '.join(imports_to_add)}")
        
        return '\n'.join(lines)


def main():
    """Main migration entry point."""
    parser = argparse.ArgumentParser(description="Migrate WebSocket UUID patterns to SSOT compliance")
    parser.add_argument('--project-root', default='C:/GitHub/netra-apex',
                       help='Project root directory')
    parser.add_argument('--live', action='store_true',
                       help='Apply changes (default is dry run)')
    parser.add_argument('--force', action='store_true',
                       help='Force migration even if backups exist')
    
    args = parser.parse_args()
    
    # Check for existing backups if in live mode
    if args.live and not args.force:
        backup_dir = Path(args.project_root) / "backup" / "websocket_id_migration"
        if backup_dir.exists() and any(backup_dir.iterdir()):
            print("⚠️  Backup directory exists with files. Use --force to override.")
            print(f"Backup directory: {backup_dir}")
            return
    
    # Run migration
    migrator = WebSocketIDMigrationTool(args.project_root, dry_run=not args.live)
    migrator.run_migration()
    
    print("\nNext Steps:")
    print("1. Review changed files for correctness")
    print("2. Run WebSocket tests to validate functionality")
    print("3. Test WebSocket connections in staging environment")
    print("4. Monitor for WebSocket 1011 errors after deployment")


if __name__ == "__main__":
    main()