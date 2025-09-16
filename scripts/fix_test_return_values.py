#!/usr/bin/env python3
"""
Test Warning Remediation: Test Return Value Cleanup Script

Business Value Justification (BVJ):
- Segment: Platform/Code Quality
- Business Goal: Technical debt reduction and test framework compliance
- Value Impact: Minimal business impact - improves code hygiene
- Strategic Impact: LOW PRIORITY - Can be deferred during critical periods

This script identifies and fixes test methods that return values instead of
using assertions, improving test framework compliance.
"""

import os
import re
import ast
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

class TestReturnValueFixer:
    """Fixes test methods that return values instead of using assertions"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.changes_made = []
        self.backup_dir = Path("backups/test_returns_fix_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        # Common patterns for return statements in tests that should be assertions
        self.return_patterns = [
            # return True/False should be assertions
            (r'(\s+)return\s+True(?:\s*#.*)?$', r'\1assert True  # Converted from return'),
            (r'(\s+)return\s+False(?:\s*#.*)?$', r'\1assert False  # Converted from return'),
            
            # return variable comparisons should be assertions
            (r'(\s+)return\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*==\s*([^#\n]+?)(?:\s*#.*)?$', 
             r'\1assert \2 == \3  # Converted from return'),
            (r'(\s+)return\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*!=\s*([^#\n]+?)(?:\s*#.*)?$', 
             r'\1assert \2 != \3  # Converted from return'),
            
            # return boolean expressions should be assertions
            (r'(\s+)return\s+(len\([^)]+\)\s*[><=!]+\s*[^#\n]+?)(?:\s*#.*)?$',
             r'\1assert \2  # Converted from return'),
            (r'(\s+)return\s+([a-zA-Z_][a-zA-Z0-9_]*\s+in\s+[^#\n]+?)(?:\s*#.*)?$',
             r'\1assert \2  # Converted from return'),
        ]
    
    def create_backup(self, file_path: Path) -> None:
        """Create backup of file before modification"""
        if not self.dry_run:
            backup_path = self.backup_dir / file_path.relative_to(Path.cwd())
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
    
    def analyze_test_returns(self, file_path: Path) -> List[Dict]:
        """Analyze file for test methods with problematic return statements"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use AST analysis for more accurate detection
            try:
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                        # Find return statements in test methods
                        for child in ast.walk(node):
                            if isinstance(child, ast.Return) and child.value is not None:
                                # Determine the type of return value
                                return_type = self._analyze_return_value(child.value)
                                
                                issues.append({
                                    'type': 'test_return_value',
                                    'line': child.lineno,
                                    'function': node.name,
                                    'return_type': return_type,
                                    'description': f"Test method {node.name} returns {return_type} instead of using assertion"
                                })
            
            except SyntaxError:
                # Fall back to regex analysis if AST parsing fails
                issues.extend(self._regex_analysis(content))
        
        except Exception as e:
            issues.append({
                'type': 'analysis_error',
                'line': 0,
                'function': 'unknown',
                'description': f"Error analyzing file: {e}"
            })
        
        return issues
    
    def _analyze_return_value(self, return_node) -> str:
        """Analyze the type of value being returned"""
        if isinstance(return_node, ast.Constant):
            if isinstance(return_node.value, bool):
                return f"boolean ({return_node.value})"
            return f"constant ({return_node.value})"
        elif isinstance(return_node, ast.Compare):
            return "comparison expression"
        elif isinstance(return_node, ast.BoolOp):
            return "boolean expression"
        elif isinstance(return_node, ast.Name):
            return f"variable ({return_node.id})"
        else:
            return "complex expression"
    
    def _regex_analysis(self, content: str) -> List[Dict]:
        """Fallback regex-based analysis for return statements in tests"""
        issues = []
        lines = content.split('\n')
        current_test_function = None
        
        for i, line in enumerate(lines, 1):
            # Track current test function
            test_match = re.match(r'\s*(?:async\s+)?def\s+(test_\w+)', line)
            if test_match:
                current_test_function = test_match.group(1)
                continue
            
            # Look for return statements in test functions
            if current_test_function and re.match(r'\s+return\s+', line):
                # Skip empty returns or returns of None
                if not re.match(r'\s+return\s*(?:#.*)?$', line) and 'return None' not in line:
                    issues.append({
                        'type': 'regex_test_return',
                        'line': i,
                        'function': current_test_function,
                        'return_type': 'unknown',
                        'description': f"Return statement found in test function {current_test_function}"
                    })
            
            # Reset function tracking on class/function boundary
            if re.match(r'^\s*(class|def)\s+(?!test_)', line):
                current_test_function = None
        
        return issues
    
    def fix_file(self, file_path: Path) -> Dict:
        """Fix test return value issues in a single file"""
        result = {
            'file': str(file_path),
            'issues_found': 0,
            'fixes_applied': 0,
            'manual_review_needed': []
        }
        
        try:
            issues = self.analyze_test_returns(file_path)
            result['issues_found'] = len(issues)
            
            if not issues:
                return result
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply regex-based fixes
            original_content = content
            fixes_applied = 0
            
            for pattern, replacement in self.return_patterns:
                new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
                if count > 0:
                    fixes_applied += count
                    content = new_content
            
            # Check for complex cases that need manual review
            complex_issues = []
            for issue in issues:
                if issue.get('return_type') in ['complex expression', 'unknown']:
                    complex_issues.append(issue)
            
            result['manual_review_needed'] = complex_issues
            result['fixes_applied'] = fixes_applied
            
            # Write changes if any were made
            if content != original_content and not self.dry_run:
                self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
        except Exception as e:
            result['manual_review_needed'].append({
                'type': 'fix_error',
                'description': f"Error fixing file: {e}"
            })
        
        return result
    
    def scan_and_fix(self, target_dirs: List[str]) -> Dict:
        """Scan target directories and fix test return value issues"""
        results = {
            'files_processed': 0,
            'files_with_issues': 0,
            'total_issues': 0,
            'total_fixes': 0,
            'manual_review_files': [],
            'detailed_results': []
        }
        
        for target_dir in target_dirs:
            if not os.path.exists(target_dir):
                print(f"Warning: Directory {target_dir} does not exist")
                continue
                
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    if file.endswith('.py') and 'test' in file:
                        file_path = Path(root) / file
                        results['files_processed'] += 1
                        
                        result = self.fix_file(file_path)
                        results['detailed_results'].append(result)
                        
                        if result['issues_found'] > 0:
                            results['files_with_issues'] += 1
                            results['total_issues'] += result['issues_found']
                            results['total_fixes'] += result['fixes_applied']
                            
                            if result['manual_review_needed']:
                                results['manual_review_files'].append(result)
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Fix test return value issues')
    parser.add_argument('--execute', action='store_true', help='Execute fixes (default is dry run)')
    parser.add_argument('--target-dirs', nargs='+', default=['tests', 'netra_backend/tests'], 
                       help='Directories to scan')
    parser.add_argument('--report-file', default='test_returns_fix_report.txt',
                       help='Output file for fix report')
    
    args = parser.parse_args()
    
    fixer = TestReturnValueFixer(dry_run=not args.execute)
    
    print(f"Starting test return value analysis ({'EXECUTION' if args.execute else 'DRY RUN'})...")
    print(f"Target directories: {args.target_dirs}")
    
    results = fixer.scan_and_fix(args.target_dirs)
    
    print(f"\nTest Return Value Fix Results:")
    print(f"Files processed: {results['files_processed']}")
    print(f"Files with issues: {results['files_with_issues']}")
    print(f"Total issues found: {results['total_issues']}")
    print(f"Automatic fixes applied: {results['total_fixes']}")
    print(f"Files needing manual review: {len(results['manual_review_files'])}")
    
    # Generate detailed report
    report = f"""
Test Return Value Fix Report
Generated: {datetime.now().isoformat()}
Mode: {'EXECUTION' if args.execute else 'DRY RUN'}

Summary:
- Files processed: {results['files_processed']}
- Files with return value issues: {results['files_with_issues']}
- Total issues found: {results['total_issues']}
- Automatic fixes applied: {results['total_fixes']}
- Files needing manual review: {len(results['manual_review_files'])}

Manual Review Required:
"""
    
    for file_result in results['manual_review_files']:
        report += f"\nFile: {file_result['file']}\n"
        for issue in file_result['manual_review_needed']:
            report += f"  - Line {issue.get('line', 'unknown')}: {issue.get('description', 'No description')}\n"
    
    with open(args.report_file, 'w') as f:
        f.write(report)
    
    print(f"\nDetailed report saved to: {args.report_file}")
    
    if not args.execute:
        print("\nThis was a DRY RUN. Use --execute to apply automatic fixes.")
        print("This is LOW PRIORITY - can be deferred during critical periods.")

if __name__ == "__main__":
    main()