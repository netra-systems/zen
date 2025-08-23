#!/usr/bin/env python3
"""
Fix httpx.AsyncClient calls in E2E tests to include follow_redirects=True

This script systematically fixes all httpx.AsyncClient instantiations in the E2E test suite
to follow redirects, which is needed because the backend service redirects /health to /health/
"""
import os
import re
import sys
from pathlib import Path

def fix_httpx_redirects_in_file(file_path: Path) -> bool:
    """Fix httpx.AsyncClient calls in a single file to include follow_redirects=True."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern 1: httpx.AsyncClient() - no parameters
        content = re.sub(
            r'httpx\.AsyncClient\(\)',
            'httpx.AsyncClient(follow_redirects=True)',
            content
        )
        
        # Pattern 2: httpx.AsyncClient(timeout=X) - only timeout
        content = re.sub(
            r'httpx\.AsyncClient\(timeout=([^)]+)\)',
            r'httpx.AsyncClient(timeout=\1, follow_redirects=True)',
            content
        )
        
        # Pattern 3: httpx.AsyncClient(...) that already has follow_redirects - skip these
        # This pattern prevents double-adding follow_redirects
        if 'follow_redirects' in content:
            # If file already has follow_redirects, check if all instances have it
            lines = content.split('\n')
            modified = False
            for i, line in enumerate(lines):
                # Look for httpx.AsyncClient that don't have follow_redirects in the same logical block
                if 'httpx.AsyncClient(' in line and 'follow_redirects' not in line:
                    # Look ahead a few lines to see if follow_redirects is there
                    context_lines = lines[i:i+3]  # Check current and next 2 lines
                    context = ' '.join(context_lines)
                    if 'follow_redirects' not in context:
                        # This line needs to be fixed
                        if 'httpx.AsyncClient()' in line:
                            lines[i] = line.replace('httpx.AsyncClient()', 'httpx.AsyncClient(follow_redirects=True)')
                            modified = True
                        elif 'timeout=' in line and ')' in line:
                            # Find the closing parenthesis and add follow_redirects before it
                            lines[i] = line.replace(')', ', follow_redirects=True)')
                            modified = True
            
            if modified:
                content = '\n'.join(lines)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all E2E test files."""
    project_root = Path(__file__).parent
    e2e_dir = project_root / 'tests' / 'e2e'
    
    if not e2e_dir.exists():
        print(f"E2E test directory not found: {e2e_dir}")
        sys.exit(1)
    
    files_changed = []
    files_processed = 0
    
    # Find all Python files in the E2E directory
    for py_file in e2e_dir.rglob('*.py'):
        # Skip __pycache__ and other non-test directories
        if '__pycache__' in str(py_file) or '.git' in str(py_file):
            continue
        
        files_processed += 1
        
        # Read file and check if it uses httpx.AsyncClient
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'httpx.AsyncClient' in content:
                print(f"Processing: {py_file.relative_to(project_root)}")
                if fix_httpx_redirects_in_file(py_file):
                    files_changed.append(py_file.relative_to(project_root))
                    print(f"  ✓ Fixed httpx redirects")
                else:
                    print(f"  - No changes needed")
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    print(f"\nProcessed {files_processed} files")
    print(f"Modified {len(files_changed)} files")
    
    if files_changed:
        print("\nModified files:")
        for file_path in files_changed:
            print(f"  - {file_path}")
    
    print("\nAll E2E test httpx.AsyncClient calls now follow redirects!")

if __name__ == '__main__':
    main()