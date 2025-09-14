#!/usr/bin/env python3
"""
Test Collection Issue Analyzer - Find specific problems in test files
"""

import ast
import subprocess
import sys
from pathlib import Path
import re

def analyze_python_syntax(file_path):
    """Check for Python syntax errors in test files"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try to parse the AST
        ast.parse(content)
        return {'type': 'syntax', 'valid': True}

    except SyntaxError as e:
        return {
            'type': 'syntax',
            'valid': False,
            'error': str(e),
            'line': e.lineno
        }
    except UnicodeDecodeError as e:
        return {
            'type': 'encoding',
            'valid': False,
            'error': str(e)
        }
    except Exception as e:
        return {
            'type': 'other',
            'valid': False,
            'error': str(e)
        }

def analyze_imports(file_path):
    """Analyze import statements for potential issues"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        issues = []

        # Check for relative imports
        relative_imports = re.findall(r'^from\s+\.\.?\s*.*?import', content, re.MULTILINE)
        if relative_imports:
            issues.append({
                'type': 'relative_import',
                'count': len(relative_imports),
                'examples': relative_imports[:3]
            })

        # Check for direct os.environ usage
        os_environ_usage = re.findall(r'os\.environ', content)
        if os_environ_usage:
            issues.append({
                'type': 'os_environ',
                'count': len(os_environ_usage)
            })

        # Check for potentially problematic imports
        problematic_patterns = [
            r'from\s+.*?import\s+.*?\*',  # star imports
            r'import\s+.*?\..*?\..*?\..*?\.',  # very deep imports
        ]

        for pattern in problematic_patterns:
            matches = re.findall(pattern, content)
            if matches:
                issues.append({
                    'type': 'star_import' if '*' in pattern else 'deep_import',
                    'count': len(matches),
                    'examples': matches[:3]
                })

        return {'type': 'imports', 'issues': issues}

    except Exception as e:
        return {'type': 'imports', 'error': str(e)}

def test_single_file_collection(file_path):
    """Test if a single file can be collected"""
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            '--collect-only', str(file_path), '--tb=line', '-q'
        ], capture_output=True, text=True, timeout=10)

        test_count = result.stdout.count('::test_')
        has_errors = 'Error' in result.stderr or 'ModuleNotFoundError' in result.stderr

        errors = []
        if has_errors:
            error_lines = [line.strip() for line in result.stderr.split('\n')
                          if 'Error' in line or 'ModuleNotFoundError' in line]
            errors = error_lines[:3]  # First 3 errors

        return {
            'type': 'collection',
            'success': result.returncode == 0 and not has_errors,
            'test_count': test_count,
            'errors': errors,
            'stderr_size': len(result.stderr)
        }

    except subprocess.TimeoutExpired:
        return {
            'type': 'collection',
            'success': False,
            'timeout': True
        }
    except Exception as e:
        return {
            'type': 'collection',
            'success': False,
            'error': str(e)
        }

def main():
    """Main analysis"""
    print("DETAILED TEST COLLECTION ISSUE ANALYSIS")
    print("=" * 60)

    # Find all test files
    test_patterns = ['**/test_*.py', '**/tests.py']
    test_files = []

    for pattern in test_patterns:
        test_files.extend(Path('.').glob(pattern))

    # Filter out venv files
    test_files = [f for f in test_files if 'venv' not in str(f) and '.venv' not in str(f)]

    print(f"Found {len(test_files)} test files")

    # Categories for analysis
    syntax_errors = []
    import_issues = []
    collection_failures = []

    # Sample analysis on a subset
    sample_size = min(100, len(test_files))
    sample_files = test_files[:sample_size]

    print(f"Analyzing sample of {sample_size} files...")

    for i, test_file in enumerate(sample_files):
        if i % 20 == 0:
            print(f"  Progress: {i}/{sample_size}")

        # Syntax analysis
        syntax_result = analyze_python_syntax(test_file)
        if not syntax_result.get('valid', True):
            syntax_errors.append({
                'file': str(test_file),
                'result': syntax_result
            })

        # Import analysis
        import_result = analyze_imports(test_file)
        if import_result.get('issues'):
            import_issues.append({
                'file': str(test_file),
                'result': import_result
            })

        # Collection analysis (only for files without syntax errors)
        if syntax_result.get('valid', True):
            collection_result = test_single_file_collection(test_file)
            if not collection_result.get('success', False):
                collection_failures.append({
                    'file': str(test_file),
                    'result': collection_result
                })

    # Report results
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)

    print(f"Files analyzed: {sample_size}")
    print(f"Syntax errors: {len(syntax_errors)}")
    print(f"Import issues: {len(import_issues)}")
    print(f"Collection failures: {len(collection_failures)}")

    if syntax_errors:
        print(f"\nSYNTAX ERRORS ({len(syntax_errors)}):")
        for error in syntax_errors[:5]:
            print(f"  {error['file']}: {error['result']['error']}")

    if import_issues:
        print(f"\nIMPORT ISSUES ({len(import_issues)}):")
        issue_types = {}
        for issue in import_issues:
            for problem in issue['result']['issues']:
                issue_type = problem['type']
                if issue_type not in issue_types:
                    issue_types[issue_type] = []
                issue_types[issue_type].append(issue['file'])

        for issue_type, files in issue_types.items():
            print(f"  {issue_type}: {len(files)} files")
            for file in files[:3]:
                print(f"    {file}")

    if collection_failures:
        print(f"\nCOLLECTION FAILURES ({len(collection_failures)}):")
        for failure in collection_failures[:10]:
            result = failure['result']
            if result.get('timeout'):
                print(f"  {failure['file']}: TIMEOUT")
            elif result.get('errors'):
                print(f"  {failure['file']}: {result['errors'][0] if result['errors'] else 'Unknown error'}")

    # Overall health
    total_issues = len(syntax_errors) + len(import_issues) + len(collection_failures)
    health_rate = (sample_size - total_issues) / sample_size * 100
    print(f"\nOVERALL HEALTH: {health_rate:.1f}% ({sample_size - total_issues}/{sample_size} files healthy)")

if __name__ == "__main__":
    main()