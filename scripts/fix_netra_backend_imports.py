#!/usr/bin/env python3
"""
Automatic import fixer for netra_backend structure.
Fixes all legacy import patterns to use the correct netra_backend.app and netra_backend.tests structure.
"""

import ast
import os
import sys
import re
from pathlib import Path
from typing import List, Set, Tuple, Dict
from dataclasses import dataclass
import logging
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ImportFix:
    """Represents a single import fix to be applied."""
    line_number: int
    original: str
    replacement: str
    fix_type: str

class ImportFixer:
    """Fixes Python imports to follow the correct netra_backend structure."""
    
    def __init__(self, root_path: Path, dry_run: bool = False):
        self.root_path = root_path
        self.dry_run = dry_run
        self.netra_backend_path = root_path / "netra_backend"
        self.files_fixed = 0
        self.total_fixes = 0
        self.errors = []
        
        # Patterns to fix
        self.fix_patterns = [
            # Simple from imports
            (r'^(\s*)from app\.', r'\1from netra_backend.app.'),
            (r'^(\s*)from tests\.', r'\1from netra_backend.tests.'),
            
            # Simple import statements
            (r'^(\s*)import app\.', r'\1import netra_backend.app.'),
            (r'^(\s*)import tests\.', r'\1import netra_backend.tests.'),
            
            # From app/tests root imports
            (r'^(\s*)from app import', r'\1from netra_backend.app import'),
            (r'^(\s*)from tests import', r'\1from netra_backend.tests import'),
            
            # Import app/tests root
            (r'^(\s*)import app(\s|$)', r'\1import netra_backend.app\2'),
            (r'^(\s*)import tests(\s|$)', r'\1import netra_backend.tests\2'),
        ]
        
    def fix_file(self, file_path: Path) -> List[ImportFix]:
        """Fix imports in a single file."""
        fixes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            modified_lines = []
            file_modified = False
            
            for i, line in enumerate(lines, 1):
                original_line = line
                modified_line = line
                
                # Apply all fix patterns
                for pattern, replacement in self.fix_patterns:
                    if re.match(pattern, line):
                        modified_line = re.sub(pattern, replacement, line)
                        if modified_line != original_line:
                            fix_type = self._determine_fix_type(pattern)
                            fixes.append(ImportFix(
                                line_number=i,
                                original=original_line.strip(),
                                replacement=modified_line.strip(),
                                fix_type=fix_type
                            ))
                            file_modified = True
                            break
                
                modified_lines.append(modified_line)
            
            # Write the file if modifications were made and not in dry run
            if file_modified and not self.dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(modified_lines)
                self.files_fixed += 1
                self.total_fixes += len(fixes)
                
        except Exception as e:
            error_msg = f"Error processing {file_path}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            
        return fixes
    
    def _determine_fix_type(self, pattern: str) -> str:
        """Determine the type of fix based on the pattern."""
        if 'from app\\.' in pattern:
            return "Legacy app import"
        elif 'from tests\\.' in pattern:
            return "Legacy tests import"
        elif 'import app' in pattern:
            return "Legacy app module import"
        elif 'import tests' in pattern:
            return "Legacy tests module import"
        else:
            return "Unknown import fix"
    
    def fix_directory(self, directory: Path) -> Dict[str, List[ImportFix]]:
        """Fix all Python files in a directory."""
        all_fixes = {}
        
        for root, dirs, files in os.walk(directory):
            # Skip __pycache__ and hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    fixes = self.fix_file(file_path)
                    
                    if fixes:
                        rel_path = file_path.relative_to(self.root_path)
                        all_fixes[str(rel_path)] = fixes
                        
                        if not self.dry_run:
                            logger.info(f"Fixed {len(fixes)} imports in {rel_path}")
                        else:
                            logger.info(f"Would fix {len(fixes)} imports in {rel_path}")
                            
        return all_fixes
    
    def generate_report(self, all_fixes: Dict[str, List[ImportFix]]) -> str:
        """Generate a report of all fixes."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("NETRA BACKEND IMPORT FIX REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        if self.dry_run:
            report_lines.append("[DRY RUN MODE - No files were actually modified]")
            report_lines.append("")
        
        # Summary
        report_lines.append("SUMMARY")
        report_lines.append("-" * 40)
        total_files = len(all_fixes)
        total_fixes = sum(len(fixes) for fixes in all_fixes.values())
        
        if self.dry_run:
            report_lines.append(f"Files that would be fixed: {total_files}")
            report_lines.append(f"Total imports that would be fixed: {total_fixes}")
        else:
            report_lines.append(f"Files fixed: {self.files_fixed}")
            report_lines.append(f"Total imports fixed: {self.total_fixes}")
        
        if self.errors:
            report_lines.append(f"Errors encountered: {len(self.errors)}")
        
        report_lines.append("")
        
        # Group fixes by type
        fixes_by_type = {}
        for file_path, fixes in all_fixes.items():
            for fix in fixes:
                if fix.fix_type not in fixes_by_type:
                    fixes_by_type[fix.fix_type] = []
                fixes_by_type[fix.fix_type].append((file_path, fix))
        
        # Report fixes by type
        if fixes_by_type:
            report_lines.append("FIXES BY TYPE")
            report_lines.append("-" * 40)
            
            for fix_type, type_fixes in sorted(fixes_by_type.items()):
                report_lines.append(f"\n{fix_type}: {len(type_fixes)} fixes")
                report_lines.append("-" * 30)
                
                # Show first 5 examples
                for file_path, fix in type_fixes[:5]:
                    report_lines.append(f"  {file_path} (Line {fix.line_number}):")
                    report_lines.append(f"    - {fix.original}")
                    report_lines.append(f"    + {fix.replacement}")
                
                if len(type_fixes) > 5:
                    report_lines.append(f"  ... and {len(type_fixes) - 5} more")
        
        # Errors section
        if self.errors:
            report_lines.append("\n" + "=" * 40)
            report_lines.append("ERRORS")
            report_lines.append("-" * 40)
            for error in self.errors[:10]:  # Show first 10 errors
                report_lines.append(f"  - {error}")
            if len(self.errors) > 10:
                report_lines.append(f"  ... and {len(self.errors) - 10} more errors")
        
        # Success message
        if not self.dry_run and self.files_fixed > 0:
            report_lines.append("\n" + "=" * 40)
            report_lines.append("[SUCCESS] All import issues have been fixed!")
            report_lines.append("Next steps:")
            report_lines.append("  1. Run tests to ensure everything still works")
            report_lines.append("  2. Review the changes with git diff")
            report_lines.append("  3. Commit the changes if everything looks good")
        elif self.dry_run and total_fixes > 0:
            report_lines.append("\n" + "=" * 40)
            report_lines.append("To apply these fixes, run without --dry-run:")
            report_lines.append("  python scripts/fix_netra_backend_imports.py")
        
        return "\n".join(report_lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix legacy import patterns in netra_backend structure"
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
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Get the project root
    root_path = Path.cwd()
    
    # Verify we're in the right directory
    if not (root_path / "netra_backend").exists():
        print("Error: netra_backend directory not found. Please run from project root.")
        sys.exit(1)
    
    print("Starting netra_backend import fixes...")
    print(f"Project root: {root_path}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'FIXING FILES'}")
    print()
    
    fixer = ImportFixer(root_path, dry_run=args.dry_run)
    
    all_fixes = {}
    
    # Fix app directory
    print("Processing netra_backend/app...")
    app_fixes = fixer.fix_directory(fixer.netra_backend_path / "app")
    all_fixes.update(app_fixes)
    print(f"  Found {len(app_fixes)} files with import issues")
    
    # Fix tests directory
    print("Processing netra_backend/tests...")
    tests_fixes = fixer.fix_directory(fixer.netra_backend_path / "tests")
    all_fixes.update(tests_fixes)
    print(f"  Found {len(tests_fixes)} files with import issues")
    
    print()
    
    # Generate and print report
    report = fixer.generate_report(all_fixes)
    print(report)
    
    # Save report to file
    if not args.dry_run and fixer.files_fixed > 0:
        report_path = root_path / "import_fix_report.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"\nReport saved to: {report_path}")
    
    return 0 if len(fixer.errors) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())