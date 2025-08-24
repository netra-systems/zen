#!/usr/bin/env python3
"""
Fix WebSocket ConnectionManager Import Errors

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Stability & Development Velocity
- Value Impact: Fixes 23+ test files blocking the unified test pipeline
- Strategic Impact: Enables proper WebSocket testing, prevents CI failures

This script systematically fixes all imports of the legacy ConnectionManager
to use the new unified WebSocketManager from the websocket_core package.

Root Cause: WebSocket consolidation renamed ConnectionManager to WebSocketManager
and moved it from connection_manager.py to manager.py, but test imports weren't updated.

Five Whys Analysis:
1. Import fails because connection_manager.py doesn't exist
2. File doesn't exist because ConnectionManager was renamed to WebSocketManager 
3. Imports weren't updated during WebSocket consolidation refactor
4. Many test files had this pattern from legacy WebSocket architecture
5. No systematic import migration process was implemented during consolidation
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


class WebSocketImportFixer:
    """Fix WebSocket ConnectionManager import issues systematically."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.files_fixed = []
        self.patterns_fixed = []
        
        # Define the import patterns to fix
        self.import_fixes = [
            # Pattern 1: Direct ConnectionManager import with alias
            {
                'pattern': r'from netra_backend\.app\.websocket_core\.connection_manager import ConnectionManager as (\w+)',
                'replacement': r'from netra_backend.app.websocket_core import WebSocketManager as \1',
                'description': 'ConnectionManager as alias -> WebSocketManager as alias'
            },
            # Pattern 2: Direct ConnectionManager import
            {
                'pattern': r'from netra_backend\.app\.websocket_core\.connection_manager import ConnectionManager',
                'replacement': 'from netra_backend.app.websocket_core import WebSocketManager as ConnectionManager',
                'description': 'ConnectionManager -> WebSocketManager as ConnectionManager'
            },
            # Pattern 3: Multi-import with ConnectionManager
            {
                'pattern': r'from netra_backend\.app\.websocket_core\.connection_manager import \(\s*ConnectionManager([^)]*)\)',
                'replacement': r'from netra_backend.app.websocket_core import (\n    WebSocketManager as ConnectionManager\1)',
                'description': 'Multi-import with ConnectionManager -> WebSocketManager'
            }
        ]
    
    def find_affected_files(self) -> List[Path]:
        """Find all Python files with problematic imports."""
        affected_files = []
        
        for file_path in self.root_dir.rglob("*.py"):
            if self._file_has_problematic_import(file_path):
                affected_files.append(file_path)
        
        return affected_files
    
    def _file_has_problematic_import(self, file_path: Path) -> bool:
        """Check if file has problematic WebSocket imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'netra_backend.app.websocket_core.connection_manager' in content
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return False
    
    def fix_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Fix imports in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            fixes_applied = []
            
            # Apply each import fix pattern
            for fix in self.import_fixes:
                pattern = fix['pattern']
                replacement = fix['replacement']
                description = fix['description']
                
                new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                if new_content != content:
                    fixes_applied.append(description)
                    content = new_content
            
            # Only write if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True, fixes_applied
            
            return False, []
            
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")
            return False, []
    
    def fix_all_imports(self) -> Dict[str, any]:
        """Fix all WebSocket import issues in the codebase."""
        print("Finding files with WebSocket import issues...")
        affected_files = self.find_affected_files()
        
        if not affected_files:
            print("No files found with WebSocket import issues")
            return {
                'total_files': 0,
                'files_fixed': [],
                'total_fixes': 0,
                'summary': "No issues found"
            }
        
        print(f"Found {len(affected_files)} files with import issues")
        
        total_fixes = 0
        files_fixed = []
        
        for file_path in affected_files:
            print(f"\nFixing: {file_path.relative_to(self.root_dir)}")
            
            was_fixed, fixes_applied = self.fix_file(file_path)
            
            if was_fixed:
                files_fixed.append(str(file_path.relative_to(self.root_dir)))
                total_fixes += len(fixes_applied)
                
                for fix in fixes_applied:
                    print(f"   FIXED: {fix}")
            else:
                print(f"   WARNING: No changes needed or unable to fix")
        
        return {
            'total_files': len(affected_files),
            'files_fixed': files_fixed,
            'total_fixes': total_fixes,
            'summary': f"Fixed {len(files_fixed)} files with {total_fixes} import corrections"
        }
    
    def verify_fixes(self) -> bool:
        """Verify that all fixes were applied correctly."""
        print("\nVerifying fixes...")
        remaining_issues = self.find_affected_files()
        
        if not remaining_issues:
            print("All WebSocket import issues resolved")
            return True
        else:
            print(f"ERROR: {len(remaining_issues)} files still have issues:")
            for file_path in remaining_issues[:5]:  # Show first 5
                print(f"   - {file_path.relative_to(self.root_dir)}")
            return False


def main():
    """Main execution function."""
    print("WebSocket ConnectionManager Import Fixer")
    print("=" * 50)
    
    # Get the project root directory
    current_dir = Path(__file__).parent.parent
    print(f"Working directory: {current_dir}")
    
    # Create fixer instance
    fixer = WebSocketImportFixer(str(current_dir))
    
    # Fix all imports
    results = fixer.fix_all_imports()
    
    # Display results
    print("\nRESULTS SUMMARY")
    print("=" * 30)
    print(f"Files processed: {results['total_files']}")
    print(f"Files fixed: {len(results['files_fixed'])}")
    print(f"Total fixes applied: {results['total_fixes']}")
    print(f"\n{results['summary']}")
    
    if results['files_fixed']:
        print(f"\nFixed files:")
        for file_path in results['files_fixed'][:10]:  # Show first 10
            print(f"   - {file_path}")
        
        if len(results['files_fixed']) > 10:
            print(f"   ... and {len(results['files_fixed']) - 10} more files")
    
    # Verify fixes
    success = fixer.verify_fixes()
    
    if success:
        print(f"\nSUCCESS: All WebSocket import issues have been resolved!")
        print(f"You can now run the tests without ConnectionManager import errors")
    else:
        print(f"\nWARNING: Some issues may remain. Check the output above.")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())