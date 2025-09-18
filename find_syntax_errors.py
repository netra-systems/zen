#!/usr/bin/env python3
"""
Test File Syntax Error Detection Script
Finds all Python test files with syntax errors that prevent test collection.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict

def find_test_files(root_dir: str) -> List[Path]:
    """Find all Python test files in the project."""
    test_files = []
    root_path = Path(root_dir)
    
    # Common test directory patterns
    test_patterns = [
        "**/test_*.py",
        "**/*_test.py", 
        "**/tests/**/*.py",
        "**/test/**/*.py"
    ]
    
    for pattern in test_patterns:
        test_files.extend(root_path.glob(pattern))
    
    # Remove duplicates and sort
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
    print("🔍 PHASE 1: Test File Syntax Error Detection")
    print("=" * 60)
    
    # Find all test files
    print("Finding all test files...")
    test_files = find_test_files("/Users/anthony/Desktop/netra-apex")
    print(f"Found {len(test_files)} test files to check")
    
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
    
    print(f"\n📊 RESULTS:")
    print(f"  Total files checked: {len(test_files)}")
    print(f"  Files with syntax errors: {len(files_with_errors)}")
    print(f"  Clean files: {len(files_clean)}")
    
    if not files_with_errors:
        print("✅ No syntax errors found!")
        return
    
    print(f"\n🔥 ERROR CATEGORIES:")
    for category, count in sorted(error_categories.items()):
        print(f"  {category}: {count} files")
    
    # Prioritize files
    prioritized_errors = prioritize_files(files_with_errors)
    
    print(f"\n🎯 TOP 20 PRIORITY FILES TO FIX:")
    print("-" * 80)
    for i, (file_path, error, priority) in enumerate(prioritized_errors[:20]):
        rel_path = str(file_path).replace("/Users/anthony/Desktop/netra-apex/", "")
        print(f"{i+1:2d}. [{priority:3d}] {rel_path}")
        print(f"    Error: {error}")
    
    print(f"\n📝 DETAILED ERROR LIST (All {len(files_with_errors)} files):")
    print("-" * 80)
    for i, (file_path, error, priority) in enumerate(prioritized_errors):
        rel_path = str(file_path).replace("/Users/anthony/Desktop/netra-apex/", "")
        print(f"{i+1:3d}. [{priority:3d}] {rel_path}")
        print(f"     {error}")
    
    print(f"\n🚀 NEXT STEPS:")
    print("1. Start with highest priority files (priority 100+)")
    print("2. Focus on WebSocket and agent message handling tests first")
    print("3. Fix common error patterns in batches")
    print("4. Validate fixes by re-running this script")

if __name__ == "__main__":
    main()