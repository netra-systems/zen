#!/usr/bin/env python3
"""
Architecture Scanner Helper Functions
Helper functions and utilities for the architecture scanner
"""

import ast
from typing import Any, Dict, List


class ScannerHelpers:
    """Helper functions for architecture scanning"""
    
    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    MAX_FILE_LINES = 300
    MAX_FUNCTION_LINES = 8
    
    @staticmethod
    def should_skip_file(filepath: str) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            '__pycache__', 'node_modules', '.git', 'migrations',
            'test_reports', 'docs', '.pytest_cache', 'htmlcov',
            'coverage', 'venv', '.venv', 'dist', 'build'
        ]
        return any(pattern in filepath for pattern in skip_patterns)
    
    @staticmethod
    def count_function_lines(node: ast.FunctionDef) -> int:
        """Count actual code lines in function (excluding docstrings)"""
        if not node.body:
            return 0
        
        start_idx = ScannerHelpers._get_function_start_index(node)
        if start_idx >= len(node.body):
            return 0
        
        return ScannerHelpers._calculate_function_line_count(node, start_idx)
    
    @staticmethod
    def _get_function_start_index(node: ast.FunctionDef) -> int:
        """Get start index after docstring"""
        if (len(node.body) > 0 and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, (ast.Str, ast.Constant))):
            return 1
        return 0
    
    @staticmethod
    def _calculate_function_line_count(node: ast.FunctionDef, start_idx: int) -> int:
        """Calculate actual function line count"""
        first_line = node.body[start_idx].lineno
        last_line = node.body[-1].end_lineno if hasattr(node.body[-1], 'end_lineno') else node.body[-1].lineno
        return max(1, last_line - first_line + 1)
    
    @staticmethod
    def get_file_severity(lines: int) -> str:
        """Get severity level for file size violation"""
        if lines > 500:
            return ScannerHelpers.SEVERITY_CRITICAL
        elif lines > 400:
            return ScannerHelpers.SEVERITY_HIGH
        else:
            return ScannerHelpers.SEVERITY_MEDIUM
    
    @staticmethod
    def get_function_severity(lines: int) -> str:
        """Get severity level for function complexity"""
        if lines > 20:
            return ScannerHelpers.SEVERITY_CRITICAL
        elif lines > 15:
            return ScannerHelpers.SEVERITY_HIGH
        else:
            return ScannerHelpers.SEVERITY_MEDIUM
    
    @staticmethod
    def get_duplicate_severity(count: int) -> str:
        """Get severity level for duplicate types"""
        if count > 5:
            return ScannerHelpers.SEVERITY_HIGH
        elif count > 3:
            return ScannerHelpers.SEVERITY_MEDIUM
        else:
            return ScannerHelpers.SEVERITY_MEDIUM
    
    @staticmethod
    def get_file_recommendation(lines: int) -> str:
        """Get recommendation for file size violation"""
        if lines > 500:
            return "Critical: Split into 3+ focused modules immediately"
        elif lines > 400:
            return "High: Split into 2+ modules within this sprint"
        else:
            return "Medium: Plan modular refactoring for next sprint"
    
    @staticmethod
    def get_function_recommendation(lines: int) -> str:
        """Get recommendation for function complexity"""
        if lines > 20:
            return "Critical: Extract into 3+ smaller functions immediately"
        elif lines > 15:
            return "High: Split into 2+ functions this sprint"
        else:
            return "Medium: Consider extracting helper functions"
    
    @staticmethod
    def get_stub_patterns() -> List[tuple]:
        """Get patterns that indicate test stubs"""
        return [
            (r'# Mock implementation', 'Mock implementation comment'),
            (r'# Test stub', 'Test stub comment'),
            (r'""".*test implementation.*"""', 'Test implementation docstring'),
            (r'""".*for testing.*"""', 'For testing docstring'),
            (r'return \[{"id": "1"', 'Hardcoded test data'),
            (r'return {"test": "data"}', 'Test data return'),
            (r'return {"status": "ok"}', 'Static status return'),
            (r'def \w+\(\*args, \*\*kwargs\).*return {', 'Args/kwargs with static return'),
            (r'pass\s*#.*TODO', 'TODO placeholder'),
            (r'raise NotImplementedError', 'Not implemented placeholder')
        ]
    
    @staticmethod
    def get_debt_patterns() -> List[tuple]:
        """Get patterns that indicate architectural debt"""
        return [
            (r'TODO:', 'TODO comment'),
            (r'FIXME:', 'FIXME comment'),
            (r'HACK:', 'HACK comment'),
            (r'XXX:', 'XXX comment'),
            (r'import \*', 'Star import'),
            (r'from .* import \*', 'Star import'),
            (r'except Exception:', 'Bare exception catch'),
            (r'except:', 'Bare except clause')
        ]
    
    @staticmethod
    def get_quality_patterns() -> List[tuple]:
        """Get patterns that indicate code quality issues"""
        return [
            (r'print\(', 'Print statement (use logging)'),
            (r'\.strip\(\)\.split\(\)', 'Chain operations - consider readability'),
            (r'if.*and.*and.*and', 'Complex conditional - consider extraction'),
            (r'lambda.*lambda', 'Nested lambda - consider function'),
        ]
    
    @staticmethod
    def get_scan_patterns() -> List[str]:
        """Get file patterns to scan"""
        return [
            'app/**/*.py', 
            'frontend/**/*.tsx', 
            'frontend/**/*.ts',
            'scripts/**/*.py'
        ]
    
    @staticmethod
    def create_file_violation(filepath: str, line_count: int) -> Dict[str, Any]:
        """Create file size violation record"""
        return {
            'file': filepath,
            'lines': line_count,
            'excess_lines': line_count - ScannerHelpers.MAX_FILE_LINES,
            'severity': ScannerHelpers.get_file_severity(line_count),
            'type': 'file_size',
            'recommendation': ScannerHelpers.get_file_recommendation(line_count)
        }
    
    @staticmethod
    def create_function_violation(filepath: str, node: ast.FunctionDef, lines: int) -> Dict[str, Any]:
        """Create function complexity violation record"""
        return {
            'file': filepath,
            'function': node.name,
            'lines': lines,
            'excess_lines': lines - ScannerHelpers.MAX_FUNCTION_LINES,
            'line_number': node.lineno,
            'severity': ScannerHelpers.get_function_severity(lines),
            'type': 'function_complexity',
            'recommendation': ScannerHelpers.get_function_recommendation(lines)
        }
    
    @staticmethod
    def create_missing_return_type(filepath: str, node: ast.FunctionDef) -> Dict[str, Any]:
        """Create missing return type violation"""
        return {
            'file': filepath,
            'function': node.name,
            'line': node.lineno,
            'issue': 'Missing return type annotation',
            'severity': ScannerHelpers.SEVERITY_MEDIUM,
            'type': 'missing_type',
            'recommendation': 'Add return type annotation'
        }
    
    @staticmethod
    def create_missing_param_type(filepath: str, node: ast.FunctionDef, arg: ast.arg) -> Dict[str, Any]:
        """Create missing parameter type violation"""
        return {
            'file': filepath,
            'function': node.name,
            'parameter': arg.arg,
            'line': node.lineno,
            'issue': f'Missing type annotation for parameter: {arg.arg}',
            'severity': ScannerHelpers.SEVERITY_MEDIUM,
            'type': 'missing_type',
            'recommendation': f'Add type annotation for {arg.arg}'
        }