#!/usr/bin/env python3
"""
Function Decomposition Tool
Analyzes Python files for functions exceeding 8 lines and suggests decomposition.
"""

import ast
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass
class FunctionInfo:
    name: str
    line_count: int
    start_line: int
    end_line: int
    file_path: str
    complexity_score: int
    
class FunctionAnalyzer(ast.NodeVisitor):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.functions = []
        self.current_line = 1
        
    def visit_FunctionDef(self, node):
        line_count = self._calculate_lines(node)
        complexity = self._calculate_complexity(node)
        
        func_info = FunctionInfo(
            name=node.name,
            line_count=line_count,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno + line_count,
            file_path=self.filepath,
            complexity_score=complexity
        )
        
        if line_count > 8:
            self.functions.append(func_info)
            
        self.generic_visit(node)
        
    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)
        
    def _calculate_lines(self, node) -> int:
        """Calculate actual lines of code (excluding empty lines and comments)."""
        if not node.end_lineno:
            return 1
        return node.end_lineno - node.lineno + 1
        
    def _calculate_complexity(self, node) -> int:
        """Basic complexity scoring."""
        complexity = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
        return complexity

def find_violations(directory: str) -> List[FunctionInfo]:
    """Find all functions exceeding 8 lines in Python files."""
    violations = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith('.py'):
                continue
                
            filepath = os.path.join(root, file)
            if _should_skip_file(filepath):
                continue
                
            try:
                violations.extend(_analyze_file(filepath))
            except Exception as e:
                print(f"Error analyzing {filepath}: {e}")
                
    return sorted(violations, key=lambda x: x.line_count, reverse=True)

def _should_skip_file(filepath: str) -> bool:
    """Skip files that shouldn't be analyzed."""
    skip_patterns = ['venv/', '__pycache__/', '.pytest_cache/', 'tests/']
    return any(pattern in filepath for pattern in skip_patterns)

def _analyze_file(filepath: str) -> List[FunctionInfo]:
    """Analyze a single Python file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return []
            
    analyzer = FunctionAnalyzer(filepath)
    analyzer.visit(tree)
    return analyzer.functions

def suggest_decomposition(func_info: FunctionInfo) -> Dict[str, Any]:
    """Suggest how to decompose a large function."""
    suggestions = {
        'function': func_info.name,
        'current_lines': func_info.line_count,
        'target_functions': max(2, func_info.line_count // 8),
        'strategies': []
    }
    
    # Read the actual function code
    try:
        with open(func_info.file_path, 'r') as f:
            lines = f.readlines()
            func_lines = lines[func_info.start_line-1:func_info.end_line]
            suggestions['code'] = ''.join(func_lines)
            
        # Basic decomposition strategies
        if func_info.complexity_score > 5:
            suggestions['strategies'].append("Extract conditional logic into helper functions")
        if func_info.line_count > 20:
            suggestions['strategies'].append("Split into setup, execution, and cleanup phases")
        if 'try:' in suggestions['code'] or 'except' in suggestions['code']:
            suggestions['strategies'].append("Extract error handling into separate functions")
        if 'for ' in suggestions['code'] or 'while ' in suggestions['code']:
            suggestions['strategies'].append("Extract loop logic into helper functions")
            
    except Exception as e:
        suggestions['error'] = str(e)
        
    return suggestions

def generate_report(violations: List[FunctionInfo]) -> str:
    """Generate a comprehensive report of violations."""
    report = [
        "# Function Decomposition Analysis Report",
        f"Found {len(violations)} functions exceeding 8 lines\n",
        "## Worst Offenders (Top 20)\n"
    ]
    
    for i, func in enumerate(violations[:20], 1):
        report.append(f"{i}. **{func.name}()** in `{func.file_path}`")
        report.append(f"   - Lines: {func.line_count} (start: {func.start_line})")
        report.append(f"   - Complexity: {func.complexity_score}")
        report.append("")
    
    # Group by file
    by_file = {}
    for func in violations:
        if func.file_path not in by_file:
            by_file[func.file_path] = []
        by_file[func.file_path].append(func)
    
    report.append("\n## Violations by File\n")
    for filepath, funcs in sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True):
        report.append(f"**{filepath}** ({len(funcs)} violations)")
        for func in sorted(funcs, key=lambda x: x.line_count, reverse=True):
            report.append(f"  - {func.name}(): {func.line_count} lines")
        report.append("")
    
    return '\n'.join(report)

def main():
    """Main analysis function."""
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = os.getcwd()
        
    print(f"Analyzing functions in: {directory}")
    violations = find_violations(directory)
    
    print(f"\nFound {len(violations)} functions exceeding 8 lines")
    
    if violations:
        print("\n[U+1F534] TOP 10 WORST OFFENDERS:")
        for i, func in enumerate(violations[:10], 1):
            print(f"{i:2}. {func.name}() - {func.line_count} lines in {func.file_path}")
            
        # Generate detailed suggestions for top 3
        print("\n[U+1F4CB] DECOMPOSITION SUGGESTIONS:")
        for func in violations[:3]:
            suggestions = suggest_decomposition(func)
            print(f"\n{func.name}() ({func.line_count} lines):")
            for strategy in suggestions['strategies']:
                print(f"  - {strategy}")
                
        # Save report
        report = generate_report(violations)
        report_path = 'function_decomposition_report.md'
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"\n[U+1F4C4] Full report saved to: {report_path}")
        
    return len(violations)

if __name__ == "__main__":
    violations_count = main()
    sys.exit(0 if violations_count == 0 else 1)