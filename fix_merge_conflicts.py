#!/usr/bin/env python3
"""
Quick merge conflict resolution script - selects HEAD version for all conflicts
"""
import re
import sys
from pathlib import Path

def fix_merge_conflicts_in_file(file_path):
    """Fix merge conflicts by selecting the HEAD (current) version."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Multiple patterns to catch different conflict formats
        conflict_patterns = [
            r'<<<<<<< HEAD\n(.*?)\n=======\n.*?\n>>>>>>> 93a151c0bcee56c055b10ba3706818f11c802129',
            r'<<<<<<< HEAD\n(.*?)=======\n.*?\n>>>>>>> 93a151c0bcee56c055b10ba3706818f11c802129',
            r'<<<<<<< HEAD\n(.*?)\n=======.*?\n>>>>>>> 93a151c0bcee56c055b10ba3706818f11c802129',
            r'<<<<<<< HEAD\n(.*?)=======.*?>>>>>>> 93a151c0bcee56c055b10ba3706818f11c802129'
        ]
        
        # Replace all conflict blocks with just the HEAD version
        def replace_conflict(match):
            head_content = match.group(1)
            return head_content
        
        # Fix all conflicts using different patterns
        fixed_content = content
        for pattern in conflict_patterns:
            fixed_content = re.sub(pattern, replace_conflict, fixed_content, flags=re.DOTALL)
        
        # Also handle simple orphaned conflict markers
        fixed_content = re.sub(r'<<<<<<< HEAD\n', '', fixed_content)
        fixed_content = re.sub(r'=======\n.*?\n>>>>>>> 93a151c0bcee56c055b10ba3706818f11c802129\n', '', fixed_content, flags=re.DOTALL)
        fixed_content = re.sub(r'>>>>>>> 93a151c0bcee56c055b10ba3706818f11c802129\n?', '', fixed_content)
        
        # Write back the fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
            
        print(f"Fixed merge conflicts in {file_path}")
        return True
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix merge conflicts in the problematic files."""
    files_to_fix = [
        "tests/mission_critical/test_ssot_regression_prevention.py",
        "tests/mission_critical/test_ssot_backward_compatibility.py",
        "tests/integration/test_docker_redis_connectivity.py"
    ]
    
    base_path = Path("C:/GitHub/netra-apex")
    
    for file_path in files_to_fix:
        full_path = base_path / file_path
        if full_path.exists():
            fix_merge_conflicts_in_file(full_path)
        else:
            print(f"File not found: {full_path}")

if __name__ == "__main__":
    main()