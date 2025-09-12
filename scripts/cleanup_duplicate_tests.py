#!/usr/bin/env python3
"""
Cleanup Script for Duplicate test_module_import Functions

This script identifies and removes duplicate test_module_import functions from 
auto-generated test files. These are placeholder tests that simply assert True
and provide no value.

The script:
1. Scans all Python test files for auto-generated templates
2. Identifies standalone test_module_import functions
3. Removes these functions while preserving the rest of the file
4. Reports all changes made

Usage:
    python scripts/cleanup_duplicate_tests.py [--dry-run] [--verbose]
"""

import argparse
import ast
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class TestModuleImportCleaner:
    """Handles cleanup of duplicate test_module_import functions."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.files_modified = 0
        self.functions_removed = 0
        self.processed_files: List[str] = []
        
        if verbose:
            logger.setLevel(logging.DEBUG)
    
    def is_auto_generated_file(self, file_path: str) -> bool:
        """Check if a file is auto-generated based on its content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Look for auto-generation markers
            auto_gen_markers = [
                "This file has been auto-generated",
                "auto-generated to fix syntax errors",
                "Original content had structural issues"
            ]
            
            return any(marker in content for marker in auto_gen_markers)
            
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return False
    
    def has_standalone_test_module_import(self, file_path: str) -> Tuple[bool, str]:
        """
        Check if file has standalone test_module_import function.
        Returns (has_function, file_content).
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse the AST to find standalone functions
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                logger.warning(f"Syntax error in {file_path}: {e}")
                return False, ""
            
            # Look for standalone test_module_import function (not in a class)
            for node in ast.walk(tree):
                if (isinstance(node, ast.FunctionDef) and 
                    node.name == 'test_module_import' and
                    not self._is_method_in_class(node, tree)):
                    logger.debug(f"Found standalone test_module_import in {file_path}")
                    return True, content
                    
            return False, content
            
        except Exception as e:
            logger.warning(f"Could not analyze {file_path}: {e}")
            return False, ""
    
    def _is_method_in_class(self, func_node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if a function is a method inside a class."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if item is func_node:
                        return True
        return False
    
    def remove_test_module_import_function(self, content: str) -> str:
        """Remove the standalone test_module_import function from content."""
        lines = content.split('\n')
        new_lines = []
        skip_lines = False
        function_start = None
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Look for the function definition
            if re.match(r'^def test_module_import\(\):', line):
                function_start = i
                skip_lines = True
                logger.debug(f"Found function start at line {i + 1}")
                
                # Skip the function definition and its content
                i += 1
                indent_level = None
                
                # Process function body
                while i < len(lines):
                    current_line = lines[i].rstrip()
                    
                    # Empty line - continue
                    if not current_line:
                        i += 1
                        continue
                    
                    # Calculate indentation
                    current_indent = len(current_line) - len(current_line.lstrip())
                    
                    # Set expected indentation from first non-empty line in function
                    if indent_level is None and current_indent > 0:
                        indent_level = current_indent
                        logger.debug(f"Function indent level: {indent_level}")
                    
                    # If we're back to top level or another function, stop skipping
                    if (current_indent == 0 and 
                        (current_line.startswith('def ') or 
                         current_line.startswith('class ') or
                         current_line.startswith('if __name__'))):
                        skip_lines = False
                        break
                    
                    i += 1
                
                # Remove empty lines after the function
                while (i < len(lines) and 
                       i > function_start and 
                       not lines[i].strip()):
                    i += 1
                
                skip_lines = False
                continue
            
            if not skip_lines:
                new_lines.append(lines[i])
            
            i += 1
        
        # Clean up extra blank lines
        result_content = '\n'.join(new_lines)
        
        # Remove excessive blank lines (more than 2 consecutive)
        result_content = re.sub(r'\n\n\n+', '\n\n', result_content)
        
        return result_content
    
    def find_test_files(self) -> List[str]:
        """Find all Python test files in the project (excluding virtual environments)."""
        test_files = []
        
        project_root = Path(__file__).parent.parent
        
        # Define search paths (avoid virtual environments)
        search_paths = [
            project_root / "tests",
            project_root / "netra_backend" / "tests"
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                for file_path in search_path.rglob("*.py"):
                    if (file_path.is_file() and 
                        file_path.suffix == '.py' and
                        not any(part in str(file_path).lower() for part in ['venv', '.venv', '__pycache__'])):
                        test_files.append(str(file_path))
        
        # Remove duplicates
        test_files = list(set(test_files))
        
        logger.info(f"Found {len(test_files)} test files to scan")
        return test_files
    
    def process_file(self, file_path: str) -> bool:
        """Process a single file and remove test_module_import if needed."""
        logger.debug(f"Processing: {file_path}")
        
        # Check if it's auto-generated
        if not self.is_auto_generated_file(file_path):
            logger.debug(f"Skipping non-auto-generated file: {file_path}")
            return False
        
        # Check if it has the target function
        has_function, original_content = self.has_standalone_test_module_import(file_path)
        if not has_function:
            logger.debug(f"No standalone test_module_import found in: {file_path}")
            return False
        
        logger.info(f"Found target function in: {file_path}")
        
        # Remove the function
        new_content = self.remove_test_module_import_function(original_content)
        
        # Verify the content changed
        if new_content == original_content:
            logger.warning(f"Content unchanged for: {file_path}")
            return False
        
        # Write the modified content
        if not self.dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                logger.info(f"[U+2713] Modified: {file_path}")
            except Exception as e:
                logger.error(f"Failed to write {file_path}: {e}")
                return False
        else:
            logger.info(f"[U+2713] Would modify: {file_path}")
        
        self.processed_files.append(file_path)
        return True
    
    def run_cleanup(self) -> Dict[str, int]:
        """Run the full cleanup process."""
        logger.info("Starting test_module_import cleanup process...")
        
        if self.dry_run:
            logger.info("DRY RUN MODE - No files will be modified")
        
        # Find all test files
        test_files = self.find_test_files()
        
        # Process each file
        for file_path in test_files:
            if self.process_file(file_path):
                self.files_modified += 1
                self.functions_removed += 1
        
        # Generate report
        report = {
            'total_files_scanned': len(test_files),
            'files_modified': self.files_modified,
            'functions_removed': self.functions_removed
        }
        
        logger.info("\n" + "="*50)
        logger.info("CLEANUP REPORT")
        logger.info("="*50)
        logger.info(f"Total test files scanned: {report['total_files_scanned']}")
        logger.info(f"Files modified: {report['files_modified']}")
        logger.info(f"Functions removed: {report['functions_removed']}")
        
        if self.processed_files:
            logger.info(f"\nModified files:")
            for file_path in self.processed_files:
                logger.info(f"  - {file_path}")
        
        if self.dry_run:
            logger.info("\nNOTE: This was a dry run. No files were actually modified.")
        
        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Remove duplicate test_module_import functions from auto-generated test files"
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    cleaner = TestModuleImportCleaner(
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    try:
        report = cleaner.run_cleanup()
        
        if report['functions_removed'] == 0:
            logger.info("No duplicate test_module_import functions found.")
            return 0
        else:
            logger.info(f"Successfully processed {report['functions_removed']} files.")
            return 0
            
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())