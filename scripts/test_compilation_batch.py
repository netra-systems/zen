#!/usr/bin/env python3
"""
Batch test compilation verification script.

Verifies that Python test files can be compiled successfully
after syntax error fixes are applied.
"""

import ast
import sys
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict


class TestCompilationChecker:
    """Check compilation status of test files."""
    
    def __init__(self):
        self.results = {
            'total_files': 0,
            'compilation_success': 0,
            'compilation_failures': 0,
            'failures': []
        }
    
    def check_file_compilation(self, file_path: Path) -> Tuple[Path, bool, str]:
        """Check if a single file compiles successfully."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Try to parse the file
            ast.parse(content, filename=str(file_path))
            return file_path, True, ""
            
        except SyntaxError as e:
            error_msg = f"Line {e.lineno}: {e.msg}"
            return file_path, False, error_msg
        except Exception as e:
            return file_path, False, f"Compilation error: {str(e)}"
    
    def batch_check_compilation(self, files: List[Path], max_workers: int = 10) -> Dict:
        """Check compilation for multiple files in parallel."""
        self.results['total_files'] = len(files)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.check_file_compilation, file_path): file_path 
                for file_path in files
            }
            
            # Collect results
            for future in as_completed(future_to_file):
                file_path, success, error_msg = future.result()
                
                if success:
                    self.results['compilation_success'] += 1
                else:
                    self.results['compilation_failures'] += 1
                    self.results['failures'].append({
                        'file': str(file_path),
                        'error': error_msg
                    })
        
        return self.results
    
    def print_results(self, verbose: bool = False):
        """Print compilation check results."""
        total = self.results['total_files']
        success = self.results['compilation_success']
        failures = self.results['compilation_failures']
        
        print(f"\n📊 COMPILATION CHECK RESULTS")
        print(f"=" * 50)
        print(f"Total files checked: {total}")
        print(f"Successful compilation: {success} ({success/total*100:.1f}%)")
        print(f"Compilation failures: {failures} ({failures/total*100:.1f}%)")
        
        if failures > 0:
            print(f"\n❌ FILES WITH COMPILATION ERRORS:")
            for i, failure in enumerate(self.results['failures'][:20], 1):  # Show first 20
                print(f"{i:3}. {failure['file']}")
                if verbose:
                    print(f"     Error: {failure['error']}")
            
            if len(self.results['failures']) > 20:
                print(f"     ... and {len(self.results['failures']) - 20} more files")
        else:
            print("\n✅ All files compile successfully!")


def main():
    parser = argparse.ArgumentParser(description='Batch check test file compilation')
    parser.add_argument('--verify', type=str, default='tests',
                        help='Directory to verify compilation')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed error messages')
    parser.add_argument('--workers', type=int, default=10,
                        help='Number of parallel workers')
    parser.add_argument('--filter', type=str, default='',
                        help='Filter files containing this string')
    
    args = parser.parse_args()
    
    directory = Path(args.verify)
    
    if not directory.exists():
        print(f"Directory {directory} does not exist")
        return 1
    
    # Find Python files
    python_files = list(directory.rglob('*.py'))
    
    # Apply filter if specified
    if args.filter:
        python_files = [f for f in python_files if args.filter in str(f)]
    
    print(f"Checking compilation for {len(python_files)} Python files in {directory}")
    
    # Check compilation
    checker = TestCompilationChecker()
    results = checker.batch_check_compilation(python_files, max_workers=args.workers)
    
    # Print results
    checker.print_results(verbose=args.verbose)
    
    # Return appropriate exit code
    return 0 if results['compilation_failures'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())