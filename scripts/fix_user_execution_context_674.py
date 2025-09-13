#!/usr/bin/env python3
"""
Fix Script for Issue #674: Replace UserExecutionContext.create_for_user() calls

This script systematically replaces all instances of UserExecutionContext.create_for_user()
with UserExecutionContext.from_request() across the codebase.

Business Value Justification (BVJ):
- Segment: Platform Infrastructure  
- Business Goal: Fix critical test infrastructure blocking multi-user validation
- Value Impact: Enables $500K+ ARR multi-user functionality testing
- Strategic Impact: Resolves 0% success rate in golden path concurrency tests

ROOT CAUSE: 80+ test files call UserExecutionContext.create_for_user() but this method doesn't exist.
SOLUTION: Replace with UserExecutionContext.from_request() which has compatible signature.
"""

import re
import os
import sys
from pathlib import Path
from typing import List, Tuple


class UserExecutionContextFix674:
    """Fix script for Issue #674 UserExecutionContext method calls."""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.pattern = r'UserExecutionContext\.create_for_user\('
        self.replacement = 'UserExecutionContext.from_request('
        self.fixed_files: List[Path] = []
        self.errors: List[Tuple[Path, str]] = []
    
    def find_affected_files(self, search_dir: Path = Path("tests/")) -> List[Path]:
        """Find all Python files that contain the problematic method call."""
        affected_files = []
        
        for py_file in search_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'UserExecutionContext.create_for_user(' in content:
                        affected_files.append(py_file)
            except Exception as e:
                self.errors.append((py_file, f"Error reading file: {e}"))
        
        return affected_files
    
    def fix_file(self, file_path: Path) -> bool:
        """Fix create_for_user calls in a single file."""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Check if file needs fixing
            if 'UserExecutionContext.create_for_user(' not in original_content:
                return False
            
            # Apply fix
            fixed_content = re.sub(self.pattern, self.replacement, original_content)
            
            # Count replacements
            original_count = original_content.count('UserExecutionContext.create_for_user(')
            fixed_count = fixed_content.count('UserExecutionContext.from_request(')
            replacement_count = original_count
            
            if self.dry_run:
                print(f"[DRY RUN] Would fix {file_path}: {replacement_count} replacements")
                return True
            else:
                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                print(f"[FIXED] {file_path}: {replacement_count} replacements")
                return True
                
        except Exception as e:
            self.errors.append((file_path, f"Error fixing file: {e}"))
            return False
    
    def validate_fix(self, file_path: Path) -> bool:
        """Validate that a file was fixed correctly."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check that no create_for_user calls remain
            if 'UserExecutionContext.create_for_user(' in content:
                self.errors.append((file_path, "create_for_user calls still present after fix"))
                return False
            
            # Check that from_request calls exist
            if 'UserExecutionContext.from_request(' not in content:
                self.errors.append((file_path, "No from_request calls found after fix"))
                return False
            
            return True
            
        except Exception as e:
            self.errors.append((file_path, f"Error validating file: {e}"))
            return False
    
    def run_fix(self, search_dirs: List[Path] = None) -> dict:
        """Run the complete fix process."""
        if search_dirs is None:
            search_dirs = [Path("tests/")]
        
        print(f"🔍 Issue #674 Fix Script - UserExecutionContext.create_for_user() → from_request()")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE FIX'}")
        
        # Find all affected files
        all_affected_files = []
        for search_dir in search_dirs:
            print(f"\n📂 Searching {search_dir} for affected files...")
            affected_files = self.find_affected_files(search_dir)
            all_affected_files.extend(affected_files)
            print(f"   Found {len(affected_files)} files with create_for_user() calls")
        
        print(f"\n📊 Total affected files: {len(all_affected_files)}")
        
        if not all_affected_files:
            print("✅ No files need fixing - all create_for_user() calls already resolved!")
            return {
                "total_files": 0,
                "fixed_files": 0,
                "errors": 0,
                "success": True
            }
        
        # Show sample of affected files
        print(f"\n📄 Sample affected files:")
        for file_path in all_affected_files[:10]:
            print(f"   - {file_path}")
        if len(all_affected_files) > 10:
            print(f"   ... and {len(all_affected_files) - 10} more")
        
        # Apply fixes
        print(f"\n🛠️  Applying fixes...")
        fixed_count = 0
        
        for file_path in all_affected_files:
            if self.fix_file(file_path):
                fixed_count += 1
                self.fixed_files.append(file_path)
        
        # Validation (only for live fixes)
        validation_failures = 0
        if not self.dry_run:
            print(f"\n✅ Validating fixes...")
            for file_path in self.fixed_files:
                if not self.validate_fix(file_path):
                    validation_failures += 1
        
        # Summary
        print(f"\n📋 Fix Summary:")
        print(f"   Total files scanned: {len(all_affected_files)}")
        print(f"   Files fixed: {fixed_count}")
        print(f"   Errors: {len(self.errors)}")
        print(f"   Validation failures: {validation_failures}")
        
        if self.errors:
            print(f"\n❌ Errors encountered:")
            for file_path, error in self.errors[:5]:
                print(f"   - {file_path}: {error}")
            if len(self.errors) > 5:
                print(f"   ... and {len(self.errors) - 5} more errors")
        
        success = (len(self.errors) == 0 and validation_failures == 0)
        
        if self.dry_run:
            print(f"\n🎯 DRY RUN COMPLETE - No files were modified")
            print(f"   Run with --live to apply fixes")
        elif success:
            print(f"\n🎉 SUCCESS - All files fixed successfully!")
        else:
            print(f"\n⚠️  PARTIAL SUCCESS - Some issues encountered")
        
        return {
            "total_files": len(all_affected_files),
            "fixed_files": fixed_count,
            "errors": len(self.errors),
            "validation_failures": validation_failures,
            "success": success
        }


def main():
    """Main entry point for the fix script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fix Issue #674: Replace UserExecutionContext.create_for_user() calls"
    )
    parser.add_argument(
        "--live", 
        action="store_true",
        help="Apply fixes (default is dry run)"
    )
    parser.add_argument(
        "--search-dirs",
        nargs="+",
        default=["tests/"],
        help="Directories to search for affected files"
    )
    
    args = parser.parse_args()
    
    # Create and run fixer
    fixer = UserExecutionContextFix674(dry_run=not args.live)
    search_dirs = [Path(d) for d in args.search_dirs]
    
    try:
        result = fixer.run_fix(search_dirs)
        
        # Exit with appropriate code
        if result["success"]:
            sys.exit(0)
        else:
            print(f"\n💡 To fix remaining issues, check the error messages above")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()