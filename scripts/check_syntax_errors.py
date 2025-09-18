#!/usr/bin/env python3
"""
Comprehensive syntax error checker for test files.

Scans directories for Python files with syntax errors and categorizes them.
"""

import ast
import sys
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict
from collections import defaultdict


class SyntaxErrorChecker:
    """Check and categorize syntax errors in Python files."""
    
    def __init__(self):
        self.error_categories = defaultdict(list)
        self.error_patterns = defaultdict(int)
        self.total_files = 0
        self.files_with_errors = 0
    
    def categorize_error(self, error_msg: str) -> str:
        """Categorize syntax error by type."""
        error_lower = error_msg.lower()
        
        if 'unterminated string' in error_lower:
            return 'unterminated_strings'
        elif 'unmatched' in error_lower or 'does not match' in error_lower:
            return 'unmatched_delimiters'
        elif 'invalid decimal' in error_lower:
            return 'invalid_decimals'
        elif 'unexpected indent' in error_lower or 'unindent' in error_lower:
            return 'indentation_errors'
        elif 'expected an indented block' in error_lower:
            return 'missing_indentation'
        elif 'triple-quoted string' in error_lower:
            return 'triple_quote_errors'
        elif 'invalid syntax' in error_lower:
            return 'general_syntax'
        else:
            return 'other_errors'
    
    def check_file_syntax(self, file_path: Path) -> Tuple[Path, bool, str, int]:
        """Check syntax of a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Try to parse the file
            ast.parse(content, filename=str(file_path))
            return file_path, True, "", 0
            
        except SyntaxError as e:
            error_msg = f"{e.msg}"
            line_num = e.lineno or 0
            return file_path, False, error_msg, line_num
        except Exception as e:
            return file_path, False, f"Parse error: {str(e)}", 0
    
    def scan_directory(self, directory: Path, max_workers: int = 10) -> Dict:
        """Scan directory for Python files with syntax errors."""
        # Find all Python files
        python_files = list(directory.rglob('*.py'))
        self.total_files = len(python_files)
        
        print(f"Scanning {self.total_files} Python files in {directory}...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.check_file_syntax, file_path): file_path 
                for file_path in python_files
            }
            
            # Collect results
            for future in as_completed(future_to_file):
                file_path, success, error_msg, line_num = future.result()
                
                if not success:
                    self.files_with_errors += 1
                    category = self.categorize_error(error_msg)
                    self.error_categories[category].append({
                        'file': file_path,
                        'error': error_msg,
                        'line': line_num
                    })
                    self.error_patterns[category] += 1
        
        return self.get_summary()
    
    def get_summary(self) -> Dict:
        """Get summary of syntax error analysis."""
        return {
            'total_files': self.total_files,
            'files_with_errors': self.files_with_errors,
            'files_without_errors': self.total_files - self.files_with_errors,
            'error_categories': dict(self.error_categories),
            'error_patterns': dict(self.error_patterns)
        }
    
    def print_results(self, verbose: bool = False, limit: int = 10):
        """Print detailed results."""
        print(f"\n📊 SYNTAX ERROR ANALYSIS RESULTS")
        print(f"=" * 50)
        print(f"Total files scanned: {self.total_files}")
        print(f"Files with syntax errors: {self.files_with_errors}")
        print(f"Files without errors: {self.total_files - self.files_with_errors}")
        
        if self.files_with_errors > 0:
            print(f"\n🎯 ERROR BREAKDOWN BY CATEGORY:")
            for category, count in sorted(self.error_patterns.items(), 
                                        key=lambda x: x[1], reverse=True):
                print(f"  {category}: {count} files")
            
            print(f"\n🚨 PRIORITY FILES TO FIX:")
            # Show most common error types first
            for category in sorted(self.error_patterns.keys(), 
                                 key=lambda x: self.error_patterns[x], reverse=True):
                errors = self.error_categories[category]
                print(f"\n{category.upper()} ({len(errors)} files):")
                
                for i, error_info in enumerate(errors[:limit], 1):
                    rel_path = str(error_info['file']).replace(str(Path.cwd()), '.')
                    print(f"  {i:2}. {rel_path}")
                    if verbose:
                        print(f"      Line {error_info['line']}: {error_info['error']}")
                
                if len(errors) > limit:
                    print(f"      ... and {len(errors) - limit} more files")


def main():
    parser = argparse.ArgumentParser(description='Check syntax errors in Python files')
    parser.add_argument('--category', type=str, choices=['tests', 'websocket', 'mission_critical', 'all'],
                        default='tests', help='Category of files to check')
    parser.add_argument('--directory', type=str, help='Custom directory to check')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed error information')
    parser.add_argument('--limit', type=int, default=10,
                        help='Limit number of files shown per category')
    parser.add_argument('--workers', type=int, default=10,
                        help='Number of parallel workers')
    
    args = parser.parse_args()
    
    # Determine directory to scan
    if args.directory:
        directory = Path(args.directory)
    elif args.category == 'tests':
        directory = Path('tests')
    elif args.category == 'websocket':
        directory = Path('tests')  # Will filter for websocket files
    elif args.category == 'mission_critical':
        directory = Path('tests/mission_critical')
    elif args.category == 'all':
        directory = Path('.')
    else:
        directory = Path('tests')
    
    if not directory.exists():
        print(f"Directory {directory} does not exist")
        return 1
    
    # Run syntax error check
    checker = SyntaxErrorChecker()
    results = checker.scan_directory(directory, max_workers=args.workers)
    
    # Print results
    checker.print_results(verbose=args.verbose, limit=args.limit)
    
    # Return appropriate exit code
    return 0 if results['files_with_errors'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())