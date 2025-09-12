#!/usr/bin/env python3
"""
Fix trailing slash issues in FastAPI routes to prevent CORS redirect problems.

This script identifies routes that only define "/" and adds a duplicate route
without the trailing slash to prevent 307 redirects that can lose CORS headers.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def find_routes_with_trailing_slash(file_path: Path) -> List[Tuple[int, str]]:
    """Find route definitions with only trailing slash."""
    routes = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            # Match routes that only define "/"
            if re.match(r'^@router\.(get|post|put|delete|patch)\(["\']\/["\']\)', line.strip()):
                routes.append((i, line.strip()))
    return routes

def needs_fix(file_path: Path) -> bool:
    """Check if file needs fixing."""
    content = file_path.read_text(encoding='utf-8')
    
    # Check if file already has the fix (both "" and "/" routes)
    has_empty_route = '@router.get("")' in content or '@router.post("")' in content
    has_slash_route = '@router.get("/")' in content or '@router.post("/")' in content
    
    # If file has slash route but no empty route, it needs fixing
    return has_slash_route and not has_empty_route

def fix_route_file(file_path: Path) -> bool:
    """Fix a single route file."""
    if not needs_fix(file_path):
        return False
        
    print(f"Fixing: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a route with only "/"
        match = re.match(r'^(@router\.(get|post|put|delete|patch))\(["\']\/["\'](.*)\)', line)
        if match:
            # Extract the method and remaining parameters
            prefix = match.group(1)
            method = match.group(2)
            rest = match.group(3)
            
            # Add the route without trailing slash first
            new_lines.append(f'{prefix}(""{rest}\n')
            # Then add the original with include_in_schema=False
            if 'include_in_schema=False' not in rest:
                # Modify the original line to include include_in_schema=False
                if rest.strip().endswith(')'):
                    rest = rest.rstrip(')') + ', include_in_schema=False)'
                new_lines.append(f'{prefix}("/"{rest}\n')
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
        i += 1
    
    # Write back the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    return True

def main():
    """Main function to fix all route files."""
    # Find all Python files in routes directory
    routes_dir = Path("netra_backend/app/routes")
    
    if not routes_dir.exists():
        print("Routes directory not found!")
        return
    
    fixed_files = []
    
    # Process each Python file
    for py_file in routes_dir.glob("**/*.py"):
        if fix_route_file(py_file):
            fixed_files.append(py_file)
    
    # Summary
    if fixed_files:
        print(f"\n PASS:  Fixed {len(fixed_files)} files:")
        for f in fixed_files:
            print(f"  - {f}")
    else:
        print("\n PASS:  No files needed fixing - all routes properly configured!")
    
    # Also ensure all routers have redirect_slashes=False
    print("\n SEARCH:  Checking router configurations...")
    for py_file in routes_dir.glob("**/*.py"):
        content = py_file.read_text(encoding='utf-8')
        if 'APIRouter(' in content and 'redirect_slashes' not in content:
            print(f"   WARNING: [U+FE0F]  {py_file} - Missing redirect_slashes=False in APIRouter")

if __name__ == "__main__":
    main()