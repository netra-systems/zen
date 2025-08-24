#!/usr/bin/env python3
"""
Fix dev_launcher import issues across the entire netra_backend directory.

This script replaces all instances of:
  from dev_launcher.isolated_environment import get_env

With a production-safe version that can fallback to os.environ
"""

import os
import re
from pathlib import Path

def fix_file(file_path: Path) -> bool:
    """Fix dev_launcher import in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        changed = False
        
        # Pattern 1: Direct dev_launcher import
        dev_launcher_import = 'from dev_launcher.isolated_environment import get_env'
        if dev_launcher_import in content:
            # Replace with production-safe version
            new_import = '''# Environment access: Development vs Production
try:
    # Development: Use IsolatedEnvironment for full feature set
    from dev_launcher.isolated_environment import get_env
    _has_isolated_env = True
except ImportError:
    # Production: Direct environment access when dev_launcher unavailable
    import os
    _has_isolated_env = False
    
    def get_env():
        """Fallback environment accessor for production."""
        class FallbackEnv:
            def get(self, key, default=None):
                return os.environ.get(key, default)
            def set(self, key, value, source="production"):
                os.environ[key] = value
        return FallbackEnv()'''
            content = content.replace(dev_launcher_import, new_import)
            changed = True
        
        # Pattern 2: Incorrect backend-internal import (this should use the proper backend implementation)
        backend_import = 'from netra_backend.app.core.isolated_environment import get_env'
        if backend_import in content:
            # Replace with correct backend import that includes fallback
            new_import = '''# Use backend-specific isolated environment
try:
    from netra_backend.app.core.isolated_environment import get_env
except ImportError:
    # Production fallback if isolated_environment module unavailable
    import os
    def get_env():
        """Fallback environment accessor for production."""
        class FallbackEnv:
            def get(self, key, default=None):
                return os.environ.get(key, default)
            def set(self, key, value, source="production"):
                os.environ[key] = value
        return FallbackEnv()'''
            content = content.replace(backend_import, new_import)
            changed = True
        
        if changed:
            # Write back the fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix all Python files in netra_backend directory."""
    backend_dir = Path("netra_backend")
    
    if not backend_dir.exists():
        print("Error: netra_backend directory not found")
        return
    
    print("Fixing dev_launcher import issues in netra_backend...")
    
    fixed_count = 0
    total_count = 0
    
    # Find all Python files
    for py_file in backend_dir.rglob("*.py"):
        total_count += 1
        
        if fix_file(py_file):
            fixed_count += 1
            print(f"FIXED: {py_file}")
    
    print(f"\nSummary:")
    print(f"   Files scanned: {total_count}")
    print(f"   Files fixed: {fixed_count}")
    print(f"   Files unchanged: {total_count - fixed_count}")
    
    if fixed_count > 0:
        print(f"\nAll import issues fixed! Ready for deployment.")
    else:
        print(f"\nNo import issues found.")

if __name__ == "__main__":
    main()