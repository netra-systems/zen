#!/usr/bin/env python3
"""
Test Warning Remediation: Async Test Pattern Cleanup Script

Business Value Justification (BVJ):
- Segment: Platform/Test Infrastructure
- Business Goal: Test reliability and CI/CD stability  
- Value Impact: Prevents async test failures that could mask Golden Path issues
- Strategic Impact: Ensures test infrastructure supports rapid debugging during incidents

This script identifies and fixes common async test pattern issues that cause
unawaited coroutine warnings and test instability.
"""

import os
import re
import shutil
import ast
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

class AsyncTestFixer:
    """Fixes async test patterns and unawaited coroutine issues"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.changes_made = []
        self.backup_dir = Path("backups/async_test_fix_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        # Patterns that indicate async test issues
        self.async_patterns = [
            # Test methods that should be async but aren't awaited properly
            (r'def (test_.*?)\(.*?\):(.*?)async def', r'async def \1(self):\2await async def', re.DOTALL),
            # Direct calls to async functions without await
            (r'(\s+)([a-zA-Z_][a-zA-Z0-9_]*\.(?:async_)?[a-zA-Z_][a-zA-Z0-9_]*\([^)]*\))(?!\s*[)\]},\n])', r'\1await \2'),
            # Async context managers without proper await
            (r'with\s+([a-zA-Z_][a-zA-Z0-9_]*\.(?:async_)?[a-zA-Z_][a-zA-Z0-9_]*\([^)]*\))', r'async with \1'),
        ]
    
    def create_backup(self, file_path: Path) -> None:
        """Create backup of file before modification"""
        if not self.dry_run:
            backup_path = self.backup_dir / file_path.relative_to(Path.cwd())
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
    
    def analyze_async_issues(self, file_path: Path) -> List[Dict]:
        """Analyze file for async test issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to find async issues
            try:
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    # Find test methods
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        # Check if test method has async calls but isn't async itself
                        has_async_calls = False
                        is_async = isinstance(node, ast.AsyncFunctionDef)
                        
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call):
                                # Check for common async method names
                                if isinstance(child.func, ast.Attribute):
                                    method_name = child.func.attr
                                    if any(async_hint in method_name.lower() for async_hint in 
                                          ['async', 'connect', 'execute', 'fetch', 'send', 'receive']):
                                        has_async_calls = True
                                        break
                        
                        if has_async_calls and not is_async:
                            issues.append({
                                'type': 'missing_async_def',
                                'line': node.lineno,
                                'function': node.name,
                                'description': f"Test method {node.name} has async calls but isn't async"
                            })
                        
                        # Check for unawaited calls in async methods
                        if is_async:
                            for child in ast.walk(node):
                                if isinstance(child, ast.Call) and not self._is_awaited(child, tree):
                                    if self._looks_async(child):
                                        issues.append({
                                            'type': 'unawaited_call',
                                            'line': child.lineno,
                                            'function': node.name,
                                            'description': f"Potentially unawaited async call in {node.name}"
                                        })
            
            except SyntaxError:
                # If we can't parse, fall back to regex analysis
                issues.extend(self._regex_analysis(content))
        
        except Exception as e:
            issues.append({
                'type': 'analysis_error',
                'line': 0,
                'function': 'unknown',
                'description': f"Error analyzing file: {e}"
            })
        
        return issues
    
    def _is_awaited(self, call_node, tree) -> bool:
        """Check if a call is properly awaited"""
        # This is a simplified check - in practice, AST analysis is complex
        # For now, we'll use heuristics
        return False  # Conservative approach - flag for manual review
    
    def _looks_async(self, call_node) -> bool:
        """Heuristic to determine if a call looks async"""
        if isinstance(call_node.func, ast.Attribute):
            method_name = call_node.func.attr.lower()
            return any(hint in method_name for hint in 
                      ['async', 'connect', 'execute', 'fetch', 'send', 'receive', 'close'])
        return False
    
    def _regex_analysis(self, content: str) -> List[Dict]:
        """Fallback regex-based analysis"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Look for test methods with async calls but no async def
            if re.match(r'\s*def test_', line) and 'async' not in line:
                # Check next few lines for async patterns
                for j in range(i, min(i + 10, len(lines))):
                    if any(pattern in lines[j] for pattern in ['await ', 'async with', '.async_']):
                        issues.append({
                            'type': 'regex_async_mismatch',
                            'line': i,
                            'function': line.strip(),
                            'description': f"Non-async test method may have async calls"
                        })
                        break
        
        return issues
    
    def generate_fixes(self, file_path: Path, issues: List[Dict]) -> str:
        """Generate recommended fixes for async issues"""
        if not issues:
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        fixes = []
        
        for issue in issues:
            if issue['type'] == 'missing_async_def':
                line_idx = issue['line'] - 1
                if line_idx < len(lines):
                    original_line = lines[line_idx]
                    if 'def test_' in original_line and 'async' not in original_line:
                        # Add async keyword
                        fixed_line = original_line.replace('def ', 'async def ')
                        lines[line_idx] = fixed_line
                        fixes.append(f"Line {issue['line']}: Added async to {issue['function']}")
        
        if fixes:
            return '\n'.join(lines)
        return None
    
    def fix_file(self, file_path: Path) -> Dict:
        """Fix async issues in a single file"""
        result = {
            'file': str(file_path),
            'issues_found': 0,
            'fixes_applied': 0,
            'manual_review_needed': []
        }
        
        try:
            issues = self.analyze_async_issues(file_path)
            result['issues_found'] = len(issues)
            
            if not issues:
                return result
            
            # Generate fixes
            fixed_content = self.generate_fixes(file_path, issues)
            
            if fixed_content:
                if not self.dry_run:
                    self.create_backup(file_path)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                result['fixes_applied'] = len([i for i in issues if i['type'] == 'missing_async_def'])
            
            # Flag complex issues for manual review
            manual_issues = [i for i in issues if i['type'] in ['unawaited_call', 'analysis_error']]
            result['manual_review_needed'] = manual_issues
            
        except Exception as e:
            result['manual_review_needed'].append({
                'type': 'fix_error',
                'description': f"Error fixing file: {e}"
            })
        
        return result
    
    def scan_and_fix(self, target_dirs: List[str]) -> Dict:
        """Scan target directories and fix async test issues"""
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
    parser = argparse.ArgumentParser(description='Fix async test pattern issues')
    parser.add_argument('--execute', action='store_true', help='Execute fixes (default is dry run)')
    parser.add_argument('--target-dirs', nargs='+', default=['tests', 'netra_backend/tests'], 
                       help='Directories to scan')
    parser.add_argument('--report-file', default='async_test_fix_report.txt',
                       help='Output file for fix report')
    
    args = parser.parse_args()
    
    fixer = AsyncTestFixer(dry_run=not args.execute)
    
    print(f"Starting async test pattern analysis ({'EXECUTION' if args.execute else 'DRY RUN'})...")
    print(f"Target directories: {args.target_dirs}")
    
    results = fixer.scan_and_fix(args.target_dirs)
    
    print(f"\nAsync Test Fix Results:")
    print(f"Files processed: {results['files_processed']}")
    print(f"Files with issues: {results['files_with_issues']}")
    print(f"Total issues found: {results['total_issues']}")
    print(f"Automatic fixes applied: {results['total_fixes']}")
    print(f"Files needing manual review: {len(results['manual_review_files'])}")
    
    # Generate detailed report
    report = f"""
Async Test Pattern Fix Report
Generated: {datetime.now().isoformat()}
Mode: {'EXECUTION' if args.execute else 'DRY RUN'}

Summary:
- Files processed: {results['files_processed']}
- Files with async issues: {results['files_with_issues']}
- Total issues found: {results['total_issues']}
- Automatic fixes applied: {results['total_fixes']}
- Files needing manual review: {len(results['manual_review_files'])}

Manual Review Required:
"""
    
    for file_result in results['manual_review_files']:
        report += f"\nFile: {file_result['file']}\n"
        for issue in file_result['manual_review_needed']:
            report += f"  - {issue.get('type', 'unknown')}: {issue.get('description', 'No description')}\n"
    
    with open(args.report_file, 'w') as f:
        f.write(report)
    
    print(f"\nDetailed report saved to: {args.report_file}")
    
    if not args.execute:
        print("\nThis was a DRY RUN. Use --execute to apply automatic fixes.")
        print("Manual review is recommended for complex async patterns.")

if __name__ == "__main__":
    main()