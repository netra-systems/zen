#!/usr/bin/env python3
"""
Type Deduplication Script

This script automatically migrates the codebase from duplicate type definitions
to the unified type registry, ensuring no breaking changes.

CRITICAL ARCHITECTURAL COMPLIANCE:
- Enforces single source of truth for all types
- Updates all import statements automatically
- Validates no breaking changes before deletion
- Maintains strong typing throughout migration

Usage:
    python scripts/deduplicate_types.py --dry-run  # Preview changes
    python scripts/deduplicate_types.py --migrate  # Apply changes
    python scripts/deduplicate_types.py --validate # Validate migration
"""

import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add project root to path

@dataclass
class ImportReplacement:
    """Represents an import that needs to be replaced."""
    old_import: str
    new_import: str
    file_path: str
    line_number: int
    type_name: str


@dataclass
class DuplicateTypeInfo:
    """Information about a duplicate type definition."""
    type_name: str
    file_path: str
    line_range: Tuple[int, int]
    is_canonical: bool = False
    references: List[str] = None


class TypeDeduplicator:
    """Main class for type deduplication process."""
    
    def _setup_project_paths(self, project_root):
        """Setup project directory paths"""
        self.project_root = project_root
        self.app_dir = project_root / "app"
        self.frontend_dir = project_root / "frontend"

    def _setup_duplicate_files_list(self):
        """Setup list of files to be deleted after migration"""
        self.duplicate_files = [
            "app/agents/state.py",  # AgentState duplicates
            "app/schemas/websocket_types.py",  # WebSocket duplicates
            "app/schemas/WebSocket.py",  # Basic WebSocket duplicates
            "frontend/types/agent.ts",  # Agent type duplicates
            "frontend/types/chat.ts",  # Chat type duplicates
        ]

    def _setup_python_mappings(self):
        """Setup Python type mapping configurations"""
        self.python_type_mappings = {
            "AgentState": "app.schemas.registry.AgentState",
            "AgentResult": "app.schemas.registry.AgentResult", 
            "AgentStatus": "app.schemas.registry.AgentStatus",
            "AgentMetadata": "app.schemas.registry.AgentMetadata",
            "ToolResultData": "app.schemas.registry.ToolResultData",
            "User": "app.schemas.registry.User", "Message": "app.schemas.registry.Message",
            "MessageType": "app.schemas.registry.MessageType", "Thread": "app.schemas.registry.Thread",
        }

    def _setup_websocket_mappings(self):
        """Setup WebSocket type mappings for Python"""
        websocket_mappings = {
            "WebSocketMessage": "app.schemas.registry.WebSocketMessage",
            "WebSocketMessageType": "app.schemas.registry.WebSocketMessageType",
            "WebSocketError": "app.schemas.registry.WebSocketError",
            "UserMessagePayload": "app.schemas.registry.UserMessagePayload",
            "AgentUpdatePayload": "app.schemas.registry.AgentUpdatePayload",
            "BaseWebSocketPayload": "app.schemas.registry.BaseWebSocketPayload",
        }
        self.python_type_mappings.update(websocket_mappings)

    def _setup_typescript_mappings(self):
        """Setup TypeScript type mapping configurations"""
        self.typescript_type_mappings = {
            "AgentState": "@/types/registry.AgentState", "AgentResult": "@/types/registry.AgentResult",
            "AgentStatus": "@/types/registry.AgentStatus", "AgentMetadata": "@/types/registry.AgentMetadata",
            "ToolResultData": "@/types/registry.ToolResultData", "User": "@/types/registry.User",
            "Message": "@/types/registry.Message", "MessageType": "@/types/registry.MessageType",
            "Thread": "@/types/registry.Thread", "ThreadMetadata": "@/types/registry.ThreadMetadata",
        }

    def _setup_typescript_websocket_mappings(self):
        """Setup WebSocket type mappings for TypeScript"""
        websocket_mappings = {
            "WebSocketMessage": "@/types/registry.WebSocketMessage",
            "WebSocketMessageType": "@/types/registry.WebSocketMessageType",
            "WebSocketError": "@/types/registry.WebSocketError",
            "UserMessagePayload": "@/types/registry.UserMessagePayload",
            "AgentUpdatePayload": "@/types/registry.AgentUpdatePayload",
        }
        self.typescript_type_mappings.update(websocket_mappings)

    def __init__(self, project_root: Path = PROJECT_ROOT):
        self._setup_project_paths(project_root)
        self._setup_duplicate_files_list()
        self._setup_python_mappings()
        self._setup_websocket_mappings()
        self._setup_typescript_mappings()
        self._setup_typescript_websocket_mappings()
        self.replacements: List[ImportReplacement] = []
        
    def find_python_imports(self) -> List[ImportReplacement]:
        """Find all Python imports that need to be replaced."""
        replacements = []
        
        # Patterns to match imports
        import_patterns = [
            # from netra_backend.app.agents.state import AgentState
            r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import\s+([a-zA-Z_][a-zA-Z0-9_,\s]*)',
            # import app.agents.state
            r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)',
        ]
        
        for py_file in self.app_dir.rglob("*.py"):
            if py_file.name == "registry.py":
                continue  # Skip the registry file itself
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line_num, line in enumerate(lines, 1):
                    for pattern in import_patterns:
                        matches = re.findall(pattern, line.strip())
                        for match in matches:
                            if isinstance(match, tuple):
                                module_path, imported_names = match
                                # Check if any imported names are in our mapping
                                for name in [n.strip() for n in imported_names.split(',')]:
                                    if name in self.python_type_mappings:
                                        replacements.append(ImportReplacement(
                                            old_import=line.strip(),
                                            new_import=f"from netra_backend.app.schemas.registry import {name}",
                                            file_path=str(py_file),
                                            line_number=line_num,
                                            type_name=name
                                        ))
            except (UnicodeDecodeError, IOError) as e:
                print(f"Warning: Could not read {py_file}: {e}")
                
        return replacements
    
    def find_typescript_imports(self) -> List[ImportReplacement]:
        """Find all TypeScript imports that need to be replaced."""
        replacements = []
        
        # TypeScript import patterns
        import_patterns = [
            # import { AgentState } from '@/types/agent';
            r'import\s*\{\s*([^}]+)\s*\}\s*from\s*[\'"]([^\'\"]+)[\'"];?',
            # import AgentState from '@/types/agent';
            r'import\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+from\s*[\'"]([^\'\"]+)[\'"];?',
        ]
        
        for ts_file in self.frontend_dir.rglob("*.ts"):
            if ts_file.name == "registry.ts":
                continue  # Skip the registry file itself
                
            try:
                with open(ts_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line_num, line in enumerate(lines, 1):
                    for pattern in import_patterns:
                        matches = re.findall(pattern, line.strip())
                        for match in matches:
                            if isinstance(match, tuple) and len(match) == 2:
                                imported_items, module_path = match
                                # Check if importing from duplicate type files
                                if any(dup in module_path for dup in ['/types/agent', '/types/chat', '/types/Message']):
                                    # Parse imported types
                                    types = [t.strip() for t in imported_items.split(',')]
                                    unified_types = [t for t in types if t in self.typescript_type_mappings]
                                    
                                    if unified_types:
                                        new_import = f"import {{ {', '.join(unified_types)} }} from '@/types/registry';"
                                        replacements.append(ImportReplacement(
                                            old_import=line.strip(),
                                            new_import=new_import,
                                            file_path=str(ts_file),
                                            line_number=line_num,
                                            type_name=','.join(unified_types)
                                        ))
            except (UnicodeDecodeError, IOError) as e:
                print(f"Warning: Could not read {ts_file}: {e}")
                
        return replacements
    
    def find_all_replacements(self) -> List[ImportReplacement]:
        """Find all imports that need to be replaced."""
        python_replacements = self.find_python_imports()
        typescript_replacements = self.find_typescript_imports()
        
        self.replacements = python_replacements + typescript_replacements
        return self.replacements
    
    def preview_changes(self) -> None:
        """Preview all changes without applying them."""
        replacements = self.find_all_replacements()
        
        print(f"\n SEARCH:  DEDUPLICATION PREVIEW - {len(replacements)} changes found\n")
        
        # Group by file
        by_file = {}
        for repl in replacements:
            if repl.file_path not in by_file:
                by_file[repl.file_path] = []
            by_file[repl.file_path].append(repl)
        
        for file_path, repls in by_file.items():
            rel_path = Path(file_path).relative_to(self.project_root)
            print(f"[U+1F4C4] {rel_path}")
            for repl in repls:
                print(f"  Line {repl.line_number}: {repl.type_name}")
                print(f"    - {repl.old_import}")
                print(f"    + {repl.new_import}")
            print()
        
        # Show files to be deleted
        print("[U+1F5D1][U+FE0F]  FILES TO BE DELETED AFTER MIGRATION:")
        for file_path in self.duplicate_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"   FAIL:  {file_path}")
        print()
    
    def apply_replacements(self) -> bool:
        """Apply all import replacements."""
        try:
            replacements = self.find_all_replacements()
            
            # Group by file for efficient processing  
            by_file = {}
            for repl in replacements:
                if repl.file_path not in by_file:
                    by_file[repl.file_path] = []
                by_file[repl.file_path].append(repl)
            
            files_modified = 0
            
            for file_path, repls in by_file.items():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Sort by line number (descending) to avoid line number shifts
                    repls.sort(key=lambda r: r.line_number, reverse=True)
                    
                    for repl in repls:
                        if repl.line_number <= len(lines):
                            lines[repl.line_number - 1] = repl.new_import + '\n'
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    files_modified += 1
                    rel_path = Path(file_path).relative_to(self.project_root)
                    print(f" PASS:  Updated {rel_path}")
                    
                except (IOError, UnicodeDecodeError) as e:
                    print(f" FAIL:  Failed to update {file_path}: {e}")
                    return False
            
            print(f"\n CELEBRATION:  Successfully updated {files_modified} files with unified type imports!")
            return True
            
        except Exception as e:
            print(f" FAIL:  Migration failed: {e}")
            return False
    
    def run_tests(self) -> bool:
        """Run tests to validate the migration."""
        print("\n[U+1F9EA] Running tests to validate migration...")
        
        try:
            # Run Python tests
            result = subprocess.run([
                "python", "test_runner.py", "--level", "unit", "--fast"
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(" FAIL:  Python tests failed:")
                print(result.stdout)
                print(result.stderr)
                return False
            
            print(" PASS:  Python tests passed")
            
            # Check TypeScript compilation
            if (self.frontend_dir / "package.json").exists():
                result = subprocess.run([
                    "npm", "run", "type-check"
                ], cwd=self.frontend_dir, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(" FAIL:  TypeScript compilation failed:")
                    print(result.stdout) 
                    print(result.stderr)
                    return False
                
                print(" PASS:  TypeScript compilation passed")
            
            return True
            
        except Exception as e:
            print(f" FAIL:  Test validation failed: {e}")
            return False
    
    def delete_duplicate_files(self) -> bool:
        """Delete duplicate type definition files."""
        print("\n[U+1F5D1][U+FE0F]  Deleting duplicate type files...")
        
        deleted_count = 0
        
        for file_path in self.duplicate_files:
            full_path = self.project_root / file_path
            
            if full_path.exists():
                try:
                    # Create backup first
                    backup_path = full_path.with_suffix(full_path.suffix + '.bak')
                    full_path.rename(backup_path)
                    
                    deleted_count += 1
                    print(f" PASS:  Moved {file_path} to backup")
                    
                except OSError as e:
                    print(f" FAIL:  Failed to delete {file_path}: {e}")
                    return False
        
        print(f"\n CELEBRATION:  Successfully moved {deleted_count} duplicate files to backup!")
        return True
    
    def generate_report(self) -> Dict:
        """Generate a deduplication report."""
        replacements = self.find_all_replacements()
        
        report = {
            "timestamp": subprocess.check_output(['date'], text=True).strip(),
            "total_replacements": len(replacements),
            "files_affected": len(set(r.file_path for r in replacements)),
            "types_unified": len(set(r.type_name for r in replacements)),
            "python_files": len([r for r in replacements if r.file_path.endswith('.py')]),
            "typescript_files": len([r for r in replacements if r.file_path.endswith('.ts')]),
            "duplicate_files_removed": len(self.duplicate_files),
            "replacements": [
                {
                    "file": str(Path(r.file_path).relative_to(self.project_root)),
                    "line": r.line_number,
                    "type": r.type_name,
                    "old": r.old_import,
                    "new": r.new_import
                } for r in replacements[:50]  # Limit to first 50 for readability
            ]
        }
        
        return report


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/deduplicate_types.py [--dry-run|--migrate|--validate|--clean]")
        sys.exit(1)
    
    command = sys.argv[1]
    deduplicator = TypeDeduplicator()
    
    if command == "--dry-run":
        deduplicator.preview_changes()
        
    elif command == "--migrate":
        print("[U+1F680] Starting type deduplication migration...")
        
        # Step 1: Preview changes
        deduplicator.preview_changes()
        
        # Step 2: Apply import replacements
        if not deduplicator.apply_replacements():
            print(" FAIL:  Migration failed at import replacement step")
            sys.exit(1)
        
        # Step 3: Validate with tests
        if not deduplicator.run_tests():
            print(" FAIL:  Migration failed validation - imports may be incorrect")
            print(" IDEA:  Please check the registry imports and fix manually")
            sys.exit(1)
        
        # Step 4: Generate report
        report = deduplicator.generate_report()
        with open(PROJECT_ROOT / "type_deduplication_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n CELEBRATION:  Type deduplication completed successfully!")
        print(f" CHART:  Report saved to type_deduplication_report.json")
        print(f"[U+1F4C8] {report['total_replacements']} imports updated across {report['files_affected']} files")
        print(f" TARGET:  {report['types_unified']} types unified into single sources of truth")
        
    elif command == "--clean":
        print("[U+1F9F9] Cleaning duplicate files after successful migration...")
        if deduplicator.delete_duplicate_files():
            print(" PASS:  Duplicate files cleaned up successfully!")
        else:
            print(" FAIL:  Failed to clean duplicate files")
            sys.exit(1)
            
    elif command == "--validate":
        if deduplicator.run_tests():
            print(" PASS:  Type deduplication validation passed!")
        else:
            print(" FAIL:  Type deduplication validation failed!")
            sys.exit(1)
            
    else:
        print(f" FAIL:  Unknown command: {command}")
        print("Usage: python scripts/deduplicate_types.py [--dry-run|--migrate|--validate|--clean]")
        sys.exit(1)


if __name__ == "__main__":
    main()