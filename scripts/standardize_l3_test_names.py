#!/usr/bin/env python3
"""
Script to standardize L3 test file naming convention
Renames test_*_l3.py files to test_*.py and updates references
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def find_l3_files() -> List[Path]:
    """Find all L3 test files in the project"""
    l3_files = []
    for pattern in ["**/*_l3.py"]:
        l3_files.extend(PROJECT_ROOT.glob(pattern))
    return sorted(l3_files)

def get_new_filename(l3_file: Path) -> str:
    """Generate the new standardized filename"""
    old_name = l3_file.name
    # Remove _l3 suffix: test_something_l3.py -> test_something.py
    new_name = old_name.replace("_l3.py", ".py")
    return new_name

def check_name_conflicts(l3_files: List[Path]) -> Dict[str, List[Path]]:
    """Check for potential naming conflicts after renaming"""
    conflicts = {}
    
    for l3_file in l3_files:
        new_name = get_new_filename(l3_file)
        new_path = l3_file.parent / new_name
        
        # Check if target already exists
        if new_path.exists():
            dir_key = str(l3_file.parent)
            if dir_key not in conflicts:
                conflicts[dir_key] = []
            conflicts[dir_key].append(l3_file)
    
    return conflicts

def find_references_to_file(file_path: Path) -> List[Tuple[Path, List[str]]]:
    """Find all references to a specific L3 file in the codebase (optimized)"""
    references = []
    file_stem = file_path.stem  # filename without extension
    
    # Only search in likely locations for references
    search_dirs = [
        PROJECT_ROOT / "scripts",
        PROJECT_ROOT / "test_framework", 
        PROJECT_ROOT / "netra_backend" / "tests",
        PROJECT_ROOT / "frontend" / "__tests__"
    ]
    
    search_patterns = [
        f"'{file_path.name}'",
        f'"{file_path.name}"',
        f"'{file_stem}'",
        f'"{file_stem}"'
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
            
        for py_file in search_dir.glob("**/*.py"):
            if py_file == file_path:
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                matching_lines = []
                for i, line in enumerate(content.splitlines(), 1):
                    for pattern in search_patterns:
                        if pattern in line:
                            matching_lines.append(f"Line {i}: {line.strip()}")
                            
                if matching_lines:
                    references.append((py_file, matching_lines))
                    
            except (UnicodeDecodeError, PermissionError):
                continue
    
    return references

def update_file_references(file_path: Path, old_name: str, new_name: str):
    """Update references in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace various reference patterns
        old_stem = old_name.replace('.py', '')
        new_stem = new_name.replace('.py', '')
        
        replacements = [
            (f"'{old_name}'", f"'{new_name}'"),
            (f'"{old_name}"', f'"{new_name}"'),
            (f"'{old_stem}'", f"'{new_stem}'"),
            (f'"{old_stem}"', f'"{new_stem}"'),
            (f"from {old_stem}", f"from {new_stem}"),
            (f"import {old_stem}", f"import {new_stem}"),
        ]
        
        updated = False
        for old_ref, new_ref in replacements:
            if old_ref in content:
                content = content.replace(old_ref, new_ref)
                updated = True
        
        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Updated references in: {file_path}")
            
    except Exception as e:
        print(f"  Error updating {file_path}: {e}")

def rename_with_git(old_path: Path, new_path: Path) -> bool:
    """Rename file using git mv to preserve history"""
    try:
        result = subprocess.run([
            'git', 'mv', str(old_path), str(new_path)
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            return True
        else:
            print(f"  Git mv failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  Git mv error: {e}")
        return False

def rename_file_standard(old_path: Path, new_path: Path) -> bool:
    """Standard file rename as fallback"""
    try:
        shutil.move(str(old_path), str(new_path))
        return True
    except Exception as e:
        print(f"  Standard rename failed: {e}")
        return False

def rename_l3_file(l3_file: Path, dry_run: bool = True) -> bool:
    """Rename a single L3 file and update references"""
    old_name = l3_file.name
    new_name = get_new_filename(l3_file)
    new_path = l3_file.parent / new_name
    
    print(f"\nProcessing: {l3_file}")
    print(f"  Renaming: {old_name} -> {new_name}")
    
    # Check for conflicts
    if new_path.exists():
        print(f"  ERROR: Target file already exists: {new_path}")
        return False
    
    # Find and update references
    references = find_references_to_file(l3_file)
    if references:
        print(f"  Found {len(references)} files with references:")
        for ref_file, lines in references:
            print(f"    {ref_file}")
            for line in lines[:3]:  # Show first 3 matches
                print(f"      {line}")
    
    if dry_run:
        print(f"  [DRY RUN] Would rename to: {new_path}")
        return True
    
    # Update references first
    for ref_file, _ in references:
        update_file_references(ref_file, old_name, new_name)
    
    # Try git mv first, fallback to standard rename
    success = rename_with_git(l3_file, new_path)
    if not success:
        success = rename_file_standard(l3_file, new_path)
    
    if success:
        print(f"  SUCCESS: Renamed to {new_path}")
        return True
    else:
        print(f"  FAILED: Could not rename {l3_file}")
        return False

def prioritize_files(l3_files: List[Path]) -> List[Path]:
    """Prioritize files by importance (critical paths first)"""
    priority_patterns = [
        "critical_paths",
        "integration", 
        "auth",
        "websocket",
        "session",
        "api",
        "core"
    ]
    
    prioritized = []
    remaining = l3_files.copy()
    
    # Add files matching priority patterns first
    for pattern in priority_patterns:
        matches = [f for f in remaining if pattern in str(f).lower()]
        prioritized.extend(sorted(matches))
        for match in matches:
            remaining.remove(match)
    
    # Add remaining files
    prioritized.extend(sorted(remaining))
    
    return prioritized

def main():
    """Main execution function"""
    print("=== L3 Test File Standardization ===\n")
    
    # Find all L3 files
    l3_files = find_l3_files()
    print(f"Found {len(l3_files)} L3 test files")
    
    if not l3_files:
        print("No L3 files found!")
        return
    
    # Check for naming conflicts
    conflicts = check_name_conflicts(l3_files)
    if conflicts:
        print(f"\nWARNING: Found naming conflicts in {len(conflicts)} directories:")
        for directory, conflict_files in conflicts.items():
            print(f"  {directory}:")
            for conflict_file in conflict_files:
                print(f"    {conflict_file.name}")
        print("\nThese files will be skipped to avoid overwrites.\n")
    
    # Prioritize files by importance
    prioritized_files = prioritize_files(l3_files)
    
    # Get command line arguments
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    limit = None
    
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])
        elif arg.startswith("-l"):
            limit = int(arg[2:]) if len(arg) > 2 else 30
    
    if limit:
        prioritized_files = prioritized_files[:limit]
        print(f"Processing first {limit} files (use --limit=N to change)")
    
    if dry_run:
        print("DRY RUN MODE - No files will be renamed")
    
    print(f"\nProcessing {len(prioritized_files)} files in priority order:\n")
    
    # Process files
    success_count = 0
    failed_count = 0
    
    for i, l3_file in enumerate(prioritized_files, 1):
        print(f"[{i}/{len(prioritized_files)}]", end=" ")
        
        if rename_l3_file(l3_file, dry_run):
            success_count += 1
        else:
            failed_count += 1
    
    # Summary
    print(f"\n=== Summary ===")
    print(f"Total files processed: {len(prioritized_files)}")
    print(f"Successful renames: {success_count}")
    print(f"Failed renames: {failed_count}")
    
    if dry_run:
        print(f"\nTo execute the renames, run: python {__file__} --execute")
        print(f"To limit to first N files: python {__file__} --execute --limit=30")
    else:
        print(f"\nRemaining L3 files: {len(l3_files) - len(prioritized_files)}")
        if success_count > 0:
            print("\nNext steps:")
            print("1. Run tests to verify functionality: python unified_test_runner.py")
            print("2. Check git status: git status")
            print("3. Commit changes: git add . && git commit -m 'Standardize L3 test naming'")

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python standardize_l3_test_names.py [options]")
        print("Options:")
        print("  --dry-run, -n     : Show what would be renamed without doing it")
        print("  --execute         : Actually perform the renames")
        print("  --limit=N, -lN    : Process only first N files")
        print("  --help, -h        : Show this help")
        sys.exit(0)
    
    main()