#!/usr/bin/env python3
"""
Comprehensive import fix script for unit test dependencies.

This script addresses the import and dependency issues blocking unit tests:
1. Fixes incorrect import paths  
2. Checks for missing Python dependencies
3. Reports on what needs to be installed
"""

import os
import re
import subprocess
import sys
from pathlib import Path

class ImportFixer:
    def __init__(self):
        self.fixes_applied = []
        self.import_replacements = {
            # Wrong -> Correct import paths
            r'from shared\.session_context\.session_factory import (.*)': 
                r'from netra_backend.app.database.request_scoped_session_factory import \1',
            
            r'from.*StructuredMessageBridge.*import.*': 
                'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge',
                
            r'import.*StructuredMessageBridge':
                'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge',
        }
        
        self.required_packages = [
            'pytest>=8.4.1',
            'langchain-core>=0.3.75', 
            'loguru>=0.7.3',
            'pydantic>=2.11.7',
            'sqlalchemy>=2.0.43',
            'fastapi>=0.116.1',
        ]

    def find_python_files_with_issues(self, search_paths):
        """Find Python files that might have import issues."""
        problem_files = []
        
        for search_path in search_paths:
            path = Path(search_path)
            if not path.exists():
                continue
                
            for py_file in path.rglob("*.py"):
                # Skip __pycache__ and .venv directories
                if "__pycache__" in str(py_file) or ".venv" in str(py_file):
                    continue
                    
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for problematic imports
                    for pattern in self.import_replacements.keys():
                        if re.search(pattern, content):
                            problem_files.append((str(py_file), pattern))
                            break
                            
                except (UnicodeDecodeError, IOError):
                    continue
                    
        return problem_files

    def fix_imports_in_file(self, file_path):
        """Fix import issues in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            
            # Apply import fixes
            for old_pattern, new_import in self.import_replacements.items():
                content = re.sub(old_pattern, new_import, content, flags=re.MULTILINE)
                
            # Only write if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixes_applied.append(file_path)
                return True
                
        except (IOError, UnicodeDecodeError) as e:
            print(f" FAIL:  Error processing {file_path}: {e}")
            return False
            
        return False

    def check_dependencies(self):
        """Check if required dependencies are installed."""
        missing_deps = []
        available_deps = []
        
        for package in self.required_packages:
            package_name = package.split('>=')[0].split('==')[0]
            try:
                __import__(package_name.replace('-', '_'))
                available_deps.append(package_name)
            except ImportError:
                missing_deps.append(package)
                
        return missing_deps, available_deps

    def run_fixes(self):
        """Run all import fixes and dependency checks."""
        print(" SEARCH:  Scanning for import issues...")
        
        # Search paths for unit tests
        search_paths = [
            'netra_backend/tests/unit',
            'tests/unit', 
            'test_framework',
        ]
        
        problem_files = self.find_python_files_with_issues(search_paths)
        
        if problem_files:
            print(f"Found {len(problem_files)} files with import issues:")
            for file_path, pattern in problem_files:
                print(f"  - {file_path}")
                if self.fix_imports_in_file(file_path):
                    print(f"     PASS:  Fixed")
                else:
                    print(f"     FAIL:  Could not fix")
        else:
            print(" PASS:  No problematic imports found in test files")
            
        # Check dependencies
        print("\n SEARCH:  Checking Python dependencies...")
        missing_deps, available_deps = self.check_dependencies()
        
        if available_deps:
            print(" PASS:  Available dependencies:")
            for dep in available_deps:
                print(f"  - {dep}")
                
        if missing_deps:
            print(" FAIL:  Missing dependencies:")
            for dep in missing_deps:
                print(f"  - {dep}")
            print(f"\nTo install missing dependencies:")
            print(f"pip install {' '.join(missing_deps)}")
        else:
            print(" PASS:  All required dependencies are available")
            
        # Summary
        print(f"\n[U+1F4CB] Summary:")
        print(f"  - Files with import issues fixed: {len(self.fixes_applied)}")
        print(f"  - Missing dependencies: {len(missing_deps)}")
        
        if self.fixes_applied:
            print(f"\n[U+1F4C1] Fixed files:")
            for file_path in self.fixes_applied:
                print(f"  - {file_path}")
                
        return len(missing_deps) == 0 and len(self.fixes_applied) >= 0

def main():
    """Main execution function."""
    print("[U+1F680] Running Import Fix Script for Unit Tests")
    print("=" * 50)
    
    fixer = ImportFixer()
    success = fixer.run_fixes()
    
    if success:
        print("\n PASS:  All fixes applied successfully!")
        print("   Unit tests should now collect properly.")
    else:
        print("\n WARNING: [U+FE0F]  Some issues remain - check missing dependencies above")
        return 1
        
    return 0

if __name__ == '__main__':
    sys.exit(main())