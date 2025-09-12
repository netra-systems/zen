#!/usr/bin/env python3
"""
Check only edited lines - validates only the specific lines being modified,
not the entire file. This allows incremental improvement without requiring
full file refactoring.
"""
import sys
import subprocess
import re
from pathlib import Path

def get_modified_lines(filepath):
    """Get line numbers that were modified in this commit."""
    try:
        # Get the diff for this specific file
        result = subprocess.run(
            ['git', 'diff', '--cached', '--unified=0', filepath],
            capture_output=True,
            text=True,
            check=True
        )
        
        modified_lines = set()
        for line in result.stdout.split('\n'):
            # Parse the @@ -old +new @@ format
            match = re.match(r'^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@', line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2)) if match.group(2) else 1
                modified_lines.update(range(start, start + count))
        
        return modified_lines
    except subprocess.CalledProcessError:
        return set()

def check_modified_lines(filepath, modified_lines):
    """Check only the modified lines for issues."""
    path = Path(filepath)
    
    if not path.exists() or not modified_lines:
        return True, []
    
    issues = []
    
    # Only check Python files
    if path.suffix == '.py':
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num in modified_lines:
            if line_num <= len(lines):
                line = lines[line_num - 1]
                
                # Check for relative imports in modified lines only
                if re.match(r'^\s*from\s+\.', line) or re.match(r'^\s*from\s+\.\.', line):
                    issues.append(f"Line {line_num}: Please use absolute imports in new code")
                
                # Check for print statements (should use logging)
                if re.match(r'^\s*print\s*\(', line):
                    issues.append(f"Line {line_num}: Consider using logging instead of print")
                
                # Check for bare except
                if re.match(r'^\s*except\s*:', line):
                    issues.append(f"Line {line_num}: Avoid bare except, specify exception type")
                
                # Check line length (but be lenient - 120 chars)
                if len(line.rstrip()) > 120:
                    issues.append(f"Line {line_num}: Line exceeds 120 characters ({len(line.rstrip())})")
    
    return len(issues) == 0, issues

def main():
    """Main entry point for pre-commit hook."""
    # Get list of modified files
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True,
            text=True,
            check=True
        )
        modified_files = result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        return 0
    
    if not modified_files or modified_files == ['']:
        return 0
    
    print("Checking modified lines only...")
    
    all_passed = True
    total_issues = 0
    
    for filepath in modified_files:
        # Only check Python/TypeScript files
        if not filepath.endswith(('.py', '.ts', '.tsx')):
            continue
        
        modified_lines = get_modified_lines(filepath)
        if not modified_lines:
            continue
        
        passed, issues = check_modified_lines(filepath, modified_lines)
        
        if not passed:
            all_passed = False
            total_issues += len(issues)
            print(f"\n WARNING: [U+FE0F]  {filepath} (checking {len(modified_lines)} modified lines)")
            for issue in issues:
                print(f"   - {issue}")
    
    if not all_passed:
        print(f"\nFound {total_issues} issue(s) in modified lines")
        print("These checks apply only to the lines you're changing")
        # Don't block commit for minor issues in edited lines
        if total_issues > 10:
            print("ERROR: Too many issues in modified code. Please fix critical issues.")
            return 1
        else:
            print("WARNING: Issues found but allowing commit (incremental improvement)")
            return 0
    else:
        print("OK: All modified lines pass quality checks")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())