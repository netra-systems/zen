#!/usr/bin/env python3
"""
Critical Test File Syntax Error Detection Script
Focuses on primary test directories, excluding backup directories.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict

def find_critical_test_files(root_dir: str) -> List[Path]:
    """Find test files in primary directories, excluding backups."""
    test_files = []
    root_path = Path(root_dir)
    
    # Primary test directories (exclude backups)
    critical_dirs = [
        "tests/",
        "netra_backend/tests/",
        "auth_service/tests/",
        "frontend/tests/",
        "test_framework/"
    ]
    
    for test_dir in critical_dirs:
        test_path = root_path / test_dir
        if test_path.exists():
            # Find all Python files in this directory
            for py_file in test_path.rglob("*.py"):
                # Skip backup directories
                path_str = str(py_file)
                if any(skip in path_str for skip in ["backup", "archive", "_old", "snapshot"]):
                    continue
                test_files.append(py_file)
    
    return sorted(list(set(test_files)))

def check_syntax_error(file_path: Path) -> Tuple[bool, str]:
    """Check if a file has syntax errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the file
        ast.parse(content, filename=str(file_path))
        return False, ""
    
    except SyntaxError as e:
        error_msg = f"Line {e.lineno}: {e.msg}"
        if e.text:
            error_msg += f" - '{e.text.strip()}'"
        return True, error_msg
    
    except UnicodeDecodeError as e:
        return True, f"Unicode decode error: {e}"
    
    except Exception as e:
        return True, f"Unexpected error: {e}"

def categorize_error(error_msg: str) -> str:
    """Categorize the type of syntax error."""
    error_lower = error_msg.lower()
    
    if "unterminated string" in error_lower or "eol while scanning" in error_lower:
        return "unterminated_string"
    elif "unmatched" in error_lower or "closing parenthesis" in error_lower:
        return "unmatched_parentheses" 
    elif "indent" in error_lower or "indentation" in error_lower:
        return "indentation_error"
    elif "invalid syntax" in error_lower:
        return "invalid_syntax"
    elif "unicode" in error_lower:
        return "encoding_error"
    else:
        return "other"

def prioritize_files(files_with_errors: List[Tuple[Path, str]]) -> List[Tuple[Path, str, int]]:
    """Prioritize files by importance (higher number = higher priority)."""
    prioritized = []
    
    for file_path, error in files_with_errors:
        priority = 0
        path_str = str(file_path).lower()
        
        # Critical business components (highest priority)
        if "websocket" in path_str:
            priority += 100
        if "agent" in path_str and "message" in path_str:
            priority += 90
        if "mission_critical" in path_str:
            priority += 85
        
        # Important test categories
        if "test_websocket" in path_str:
            priority += 80
        if "test_agent" in path_str:
            priority += 70
        if "/e2e/" in path_str:
            priority += 60
        if "/integration/" in path_str:
            priority += 50
        
        # Test framework infrastructure
        if "test_framework" in path_str:
            priority += 40
        if "/tests/" in path_str:
            priority += 30
        
        # Base priority for any test file
        priority += 10
        
        prioritized.append((file_path, error, priority))
    
    # Sort by priority (descending)
    return sorted(prioritized, key=lambda x: x[2], reverse=True)

def main():
    """Main execution function."""
    print("🔍 CRITICAL SYNTAX ERROR DETECTION (Primary Directories Only)")
    print("=" * 70)
    
    # Find critical test files
    print("Finding critical test files (excluding backups)...")
    test_files = find_critical_test_files("/Users/anthony/Desktop/netra-apex")
    print(f"Found {len(test_files)} critical test files to check")
    
    # Check each file for syntax errors
    print("\nChecking for syntax errors...")
    files_with_errors = []
    files_clean = []
    error_categories = {}
    
    for i, file_path in enumerate(test_files):
        if i % 50 == 0:
            print(f"  Checked {i}/{len(test_files)} files...")
            
        has_error, error_msg = check_syntax_error(file_path)
        
        if has_error:
            files_with_errors.append((file_path, error_msg))
            category = categorize_error(error_msg)
            error_categories[category] = error_categories.get(category, 0) + 1
        else:
            files_clean.append(file_path)
    
    print(f"\n📊 CRITICAL RESULTS:")
    print(f"  Total files checked: {len(test_files)}")
    print(f"  Files with syntax errors: {len(files_with_errors)}")
    print(f"  Clean files: {len(files_clean)}")
    
    if not files_with_errors:
        print("✅ No syntax errors found in critical directories!")
        return
    
    print(f"\n🔥 ERROR CATEGORIES:")
    for category, count in sorted(error_categories.items()):
        print(f"  {category}: {count} files")
    
    # Prioritize files
    prioritized_errors = prioritize_files(files_with_errors)
    
    print(f"\n🎯 ALL CRITICAL FILES TO FIX ({len(files_with_errors)} files):")
    print("-" * 80)
    for i, (file_path, error, priority) in enumerate(prioritized_errors):
        rel_path = str(file_path).replace("/Users/anthony/Desktop/netra-apex/", "")
        print(f"{i+1:3d}. [{priority:3d}] {rel_path}")
        print(f"     {error}")
    
    print(f"\n🚀 IMMEDIATE ACTION PLAN:")
    print("1. Fix the highest priority files first")
    print("2. Focus on mission_critical and WebSocket tests")
    print("3. Common fixes: unterminated strings, unmatched parentheses, indentation")
    print("4. Re-run this script after each batch to verify fixes")

if __name__ == "__main__":
    main()