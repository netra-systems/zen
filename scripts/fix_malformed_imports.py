#!/usr/bin/env python3
"""
Fix malformed import patterns in test files.

This script fixes the common pattern where setup_test_path() calls are incorrectly
placed inside import statements, causing syntax errors.

The broken pattern looks like:
    from module import (
    
    # Add project root to path
    from netra_backend.tests.test_utils import setup_test_path
    setup_test_path()
    
        item1,
        item2
    )

This script converts it to:
    # Add project root to path
    from netra_backend.tests.test_utils import setup_test_path
    setup_test_path()
    
    from module import (
        item1,
        item2
    )
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import ast
import argparse


class MalformedImportFixer:
    """Fixes malformed import patterns in Python files."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.files_fixed = 0
        self.files_skipped = 0
        self.files_errored = 0
        self.fixes_applied = []
        
    def check_syntax(self, content: str, file_path: Path) -> bool:
        """Check if the file has valid Python syntax."""
        try:
            ast.parse(content)
            return True
        except SyntaxError as e:
            if self.verbose:
                print(f"  Syntax error in {file_path}: {e}")
            return False
            
    def find_malformed_pattern(self, content: str) -> List[Tuple[int, int, str]]:
        """Find malformed import patterns in content.
        
        Returns list of (start_line, end_line, setup_block) tuples.
        """
        patterns = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for "from X import (" pattern
            if re.match(r'^from .+ import \($', line.strip()):
                start_line = i
                
                # Look ahead for the setup_test_path pattern
                j = i + 1
                setup_block_lines = []
                found_setup = False
                
                while j < len(lines):
                    next_line = lines[j]
                    
                    # Check if this is the setup_test_path import
                    if 'from netra_backend.tests.test_utils import setup_test_path' in next_line:
                        found_setup = True
                        # Collect the setup block (usually 3-4 lines)
                        k = j
                        while k < len(lines) and not lines[k].strip().startswith(')'):
                            if lines[k].strip() and not lines[k].strip().startswith('#'):
                                # Found the continuation of import items
                                if ',' in lines[k] or lines[k].strip().endswith(')'):
                                    break
                            setup_block_lines.append(lines[k])
                            k += 1
                            if 'setup_test_path()' in lines[k-1]:
                                break
                        
                        if found_setup:
                            setup_block = '\n'.join(setup_block_lines)
                            patterns.append((start_line, j, setup_block))
                        break
                    
                    # If we hit a closing paren without finding setup, it's not our pattern
                    if ')' in next_line and not found_setup:
                        break
                        
                    j += 1
                    
            i += 1
            
        return patterns
        
    def fix_malformed_imports(self, content: str) -> Tuple[str, int]:
        """Fix malformed import patterns in content.
        
        Returns (fixed_content, number_of_fixes).
        """
        lines = content.split('\n')
        patterns = self.find_malformed_pattern(content)
        
        if not patterns:
            return content, 0
            
        # Process patterns in reverse order to maintain line indices
        patterns.sort(reverse=True, key=lambda x: x[0])
        
        fixes_count = 0
        for start_line, setup_start, setup_block in patterns:
            # Find the end of the import statement
            import_items = []
            current_line = setup_start
            
            # Skip past the setup block
            while current_line < len(lines):
                if 'setup_test_path()' in lines[current_line]:
                    current_line += 1
                    break
                current_line += 1
                
            # Now collect the import items
            while current_line < len(lines):
                line = lines[current_line].strip()
                if line:
                    import_items.append(lines[current_line])
                    if ')' in line:
                        break
                current_line += 1
                
            # Reconstruct the import
            original_import_line = lines[start_line]
            
            # Build the fixed version
            fixed_lines = []
            
            # Add setup block first (if not already at the top)
            if setup_block.strip():
                fixed_lines.extend(setup_block.split('\n'))
                fixed_lines.append('')  # Empty line after setup
                
            # Add the import statement
            fixed_lines.append(original_import_line)
            fixed_lines.extend(import_items)
            
            # Replace the malformed section
            del lines[start_line:current_line + 1]
            for i, line in enumerate(fixed_lines):
                lines.insert(start_line + i, line)
                
            fixes_count += 1
            
        return '\n'.join(lines), fixes_count
        
    def process_file(self, file_path: Path) -> bool:
        """Process a single file to fix malformed imports.
        
        Returns True if the file was fixed, False otherwise.
        """
        try:
            # Read the file
            content = file_path.read_text(encoding='utf-8')
            
            # Check if it already has valid syntax
            if self.check_syntax(content, file_path):
                if self.verbose:
                    print(f"  Skipping {file_path.name} - syntax already valid")
                self.files_skipped += 1
                return False
                
            # Try to fix the malformed imports
            fixed_content, fixes_count = self.fix_malformed_imports(content)
            
            if fixes_count > 0:
                # Verify the fix produces valid syntax
                if self.check_syntax(fixed_content, file_path):
                    if not self.dry_run:
                        file_path.write_text(fixed_content, encoding='utf-8')
                    
                    self.files_fixed += 1
                    self.fixes_applied.append({
                        'file': str(file_path),
                        'fixes': fixes_count
                    })
                    
                    if self.verbose:
                        print(f"  Fixed {file_path.name} - {fixes_count} pattern(s) corrected")
                    return True
                else:
                    if self.verbose:
                        print(f"  WARNING: Fix did not resolve syntax error in {file_path.name}")
                    self.files_errored += 1
                    return False
            else:
                # No malformed pattern found but syntax is still invalid
                if self.verbose:
                    print(f"  No malformed pattern found in {file_path.name} (has other syntax errors)")
                self.files_errored += 1
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"  ERROR processing {file_path}: {e}")
            self.files_errored += 1
            return False
            
    def process_directory(self, directory: Path) -> None:
        """Process all Python files in a directory recursively."""
        python_files = list(directory.rglob("*.py"))
        
        print(f"Found {len(python_files)} Python files in {directory}")
        print("Checking for malformed import patterns...")
        
        for file_path in python_files:
            self.process_file(file_path)
            
    def generate_report(self) -> str:
        """Generate a summary report of fixes applied."""
        report = []
        report.append("=" * 80)
        report.append("MALFORMED IMPORT FIX REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Files processed: {self.files_fixed + self.files_skipped + self.files_errored}")
        report.append(f"Files fixed: {self.files_fixed}")
        report.append(f"Files skipped (already valid): {self.files_skipped}")
        report.append(f"Files with unfixable errors: {self.files_errored}")
        report.append("")
        
        if self.fixes_applied:
            report.append("FILES FIXED")
            report.append("-" * 40)
            for fix in self.fixes_applied[:20]:  # Show first 20
                rel_path = Path(fix['file']).relative_to(Path.cwd())
                report.append(f"  {rel_path} ({fix['fixes']} fixes)")
            if len(self.fixes_applied) > 20:
                report.append(f"  ... and {len(self.fixes_applied) - 20} more files")
            report.append("")
            
        if self.dry_run:
            report.append("[DRY RUN] No files were actually modified")
        elif self.files_fixed > 0:
            report.append(f"[SUCCESS] Fixed {self.files_fixed} files with malformed imports")
        else:
            report.append("[INFO] No malformed import patterns found to fix")
            
        return '\n'.join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix malformed import patterns in Python test files"
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='netra_backend/tests',
        help='Path to directory or file to process (default: netra_backend/tests)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be fixed without making changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed progress'
    )
    parser.add_argument(
        '--check-all',
        action='store_true',
        help='Check all Python files in the project'
    )
    
    args = parser.parse_args()
    
    # Determine path to process
    if args.check_all:
        target_path = Path.cwd()
    else:
        target_path = Path(args.path)
        
    if not target_path.exists():
        print(f"Error: Path {target_path} does not exist")
        return 1
        
    # Create fixer
    fixer = MalformedImportFixer(dry_run=args.dry_run, verbose=args.verbose)
    
    # Process files
    if target_path.is_file():
        print(f"Processing single file: {target_path}")
        fixer.process_file(target_path)
    else:
        print(f"Processing directory: {target_path}")
        fixer.process_directory(target_path)
        
    # Generate and print report
    report = fixer.generate_report()
    print()
    print(report)
    
    # Return appropriate exit code
    if fixer.files_errored > 0:
        return 2  # Partial success
    elif fixer.files_fixed > 0:
        return 0  # Success
    else:
        return 0  # No changes needed


if __name__ == "__main__":
    sys.exit(main())