#!/usr/bin/env python3
"""
Fix embedded setup_test_path() calls inside import statements.

This script fixes the specific pattern where setup code is embedded inside
import parentheses, causing syntax errors:

from module import (

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path  
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    item1,
    item2
)
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


class EmbeddedSetupImportFixer:
    """Fixes embedded setup_test_path patterns in import statements."""
    
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
        except SyntaxError:
            return False
            
    def fix_embedded_setup(self, content: str) -> Tuple[str, int]:
        """Fix embedded setup_test_path patterns in content.
        
        Returns (fixed_content, number_of_fixes).
        """
        lines = content.split('\n')
        fixes_count = 0
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Look for "from module import (" pattern
            if re.match(r'^from .+ import \($', line.strip()):
                # Look ahead to find if setup code is embedded
                embedded_start = -1
                embedded_end = -1
                import_items_start = -1
                import_close = -1
                
                # Check if the next lines contain the embedded setup
                for j in range(i + 1, min(i + 30, len(lines))):
                    curr_line = lines[j]
                    
                    # Check for the start of embedded setup
                    if '# Add project root to path' in curr_line and embedded_start == -1:
                        embedded_start = j
                        
                    # Check for the end of embedded setup
                    if embedded_start != -1 and 'setup_test_path()' in curr_line:
                        embedded_end = j
                        
                    # Check for import items after setup
                    if embedded_end != -1 and import_items_start == -1:
                        # Look for lines with import items (indented, contains comma or closing paren)
                        if curr_line.strip() and not curr_line.strip().startswith('#'):
                            if ',' in curr_line or ')' in curr_line:
                                import_items_start = j
                                
                    # Check for closing paren
                    if ')' in curr_line and not '(' in curr_line:
                        import_close = j
                        break
                
                # If we found the embedded pattern, fix it
                if embedded_start != -1 and embedded_end != -1 and import_items_start != -1:
                    # Extract components
                    import_line = lines[i]
                    setup_lines = lines[embedded_start:embedded_end + 1]
                    import_items = []
                    
                    for j in range(import_items_start, import_close + 1):
                        import_items.append(lines[j])
                    
                    # Rebuild in correct order
                    new_lines = []
                    
                    # Add setup block first
                    new_lines.extend(setup_lines)
                    new_lines.append('')  # Empty line after setup
                    
                    # Add the import statement with items
                    new_lines.append(import_line)
                    new_lines.extend(import_items)
                    
                    # Replace the malformed section
                    del lines[i:import_close + 1]
                    for idx, new_line in enumerate(new_lines):
                        lines.insert(i + idx, new_line)
                    
                    fixes_count += 1
                    i = i + len(new_lines)  # Skip past the fixed section
                    continue
                    
            i += 1
            
        return '\n'.join(lines), fixes_count
        
    def process_file(self, file_path: Path) -> bool:
        """Process a single file to fix embedded imports.
        
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
                
            # Try to fix the embedded imports
            fixed_content, fixes_count = self.fix_embedded_setup(content)
            
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
                # No embedded pattern found but syntax is still invalid
                if self.verbose:
                    print(f"  No embedded pattern found in {file_path.name} (has other syntax errors)")
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
        print("Checking for embedded setup patterns...")
        
        for file_path in python_files:
            self.process_file(file_path)
            
    def generate_report(self) -> str:
        """Generate a summary report of fixes applied."""
        report = []
        report.append("=" * 80)
        report.append("EMBEDDED SETUP IMPORT FIX REPORT")
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
            report.append(f"[SUCCESS] Fixed {self.files_fixed} files with embedded setup imports")
        else:
            report.append("[INFO] No embedded setup patterns found to fix")
            
        return '\n'.join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix embedded setup_test_path patterns in Python test files"
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
    
    args = parser.parse_args()
    
    # Determine path to process
    target_path = Path(args.path)
        
    if not target_path.exists():
        print(f"Error: Path {target_path} does not exist")
        return 1
        
    # Create fixer
    fixer = EmbeddedSetupImportFixer(dry_run=args.dry_run, verbose=args.verbose)
    
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