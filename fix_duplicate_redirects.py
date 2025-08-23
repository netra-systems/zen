#!/usr/bin/env python3
"""
Fix duplicate follow_redirects=True parameters in httpx.AsyncClient calls
"""
import re
from pathlib import Path

def fix_duplicates_in_file(file_path: Path) -> bool:
    """Fix duplicate follow_redirects=True parameters in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern to find duplicate follow_redirects=True in the same httpx.AsyncClient call
        # This matches patterns like: httpx.AsyncClient(timeout=3.0, follow_redirects=True, follow_redirects=True)
        pattern = r'httpx\.AsyncClient\(([^)]*follow_redirects=True[^)]*), follow_redirects=True([^)]*)\)'
        
        def replace_duplicates(match):
            # Extract the parts before and after the duplicate
            before_and_first = match.group(1)
            after_second = match.group(2)
            
            # Reconstruct without the duplicate
            return f'httpx.AsyncClient({before_and_first}{after_second})'
        
        content = re.sub(pattern, replace_duplicates, content)
        
        # Handle cases where there might be more complex duplicate patterns
        # This is a more general cleanup for any duplicate follow_redirects=True
        lines = content.split('\n')
        modified_lines = []
        
        for line in lines:
            if 'httpx.AsyncClient' in line and line.count('follow_redirects=True') > 1:
                # Find all occurrences and keep only one
                parts = line.split('follow_redirects=True')
                if len(parts) > 2:  # More than one occurrence
                    # Reconstruct with only one follow_redirects=True
                    new_line = parts[0] + 'follow_redirects=True'
                    for part in parts[2:]:  # Skip the first duplicate
                        # Remove the leading comma and space if present
                        part = part.lstrip(', ')
                        if part:  # Only add if there's content after cleaning
                            new_line += ', ' + part if not new_line.endswith('(') else part
                    line = new_line
            modified_lines.append(line)
        
        content = '\n'.join(modified_lines)
        
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
    """Main function to fix duplicate parameters in all E2E test files."""
    project_root = Path(__file__).parent
    e2e_dir = project_root / 'tests' / 'e2e'
    
    files_changed = []
    files_processed = 0
    
    # Find all Python files in the E2E directory
    for py_file in e2e_dir.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
        
        files_processed += 1
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'follow_redirects=True, follow_redirects=True' in content:
                print(f"Fixing duplicates in: {py_file.relative_to(project_root)}")
                if fix_duplicates_in_file(py_file):
                    files_changed.append(py_file.relative_to(project_root))
                    print(f"  ✓ Fixed duplicate parameters")
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

if __name__ == '__main__':
    main()