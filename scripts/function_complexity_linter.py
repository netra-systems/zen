#!/usr/bin/env python3
"""
Function Complexity Linter
Enforces the 8-line maximum function rule from CLAUDE.md

This linter analyzes Python files and reports functions that exceed the 8-line limit.
It integrates with the existing architecture compliance checker.
"""

import ast
import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

@dataclass
class FunctionComplexityViolation:
    """Function complexity violation data"""
    file_path: str
    function_name: str
    line_number: int
    actual_lines: int
    max_lines: int = 8
    severity: str = "error"
    message: str = ""

class FunctionComplexityLinter:
    """Linter for enforcing function complexity rules"""
    
    def __init__(self, max_lines: int = 8, root_path: str = "."):
        self.max_lines = max_lines
        self.root_path = Path(root_path)
        self.violations: List[FunctionComplexityViolation] = []
    
    def _count_function_lines(self, node: ast.FunctionDef) -> int:
        """Count actual code lines in function (excluding docstrings)"""
        if not node.body:
            return 0
        
        # Skip docstring if present
        start_idx = 0
        if (len(node.body) > 0 and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, (ast.Constant, ast.Str))):
            start_idx = 1
        
        if start_idx >= len(node.body):
            return 0
            
        # Count lines from first real statement to last
        first_line = node.body[start_idx].lineno
        last_line = node.body[-1].end_lineno if hasattr(node.body[-1], 'end_lineno') else node.body[-1].lineno
        return last_line - first_line + 1
    
    def _should_skip_function(self, function_name: str, file_path: str) -> bool:
        """Check if function should be skipped from linting"""
        # Skip test functions and example files
        skip_patterns = [
            "__init__", "__str__", "__repr__", "__eq__",
            "test_", "setUp", "tearDown"
        ]
        
        skip_files = [
            "test_", "example_", "demo_", "sample_",
            "__init__.py", "conftest.py"
        ]
        
        if any(pattern in function_name for pattern in skip_patterns):
            return True
            
        if any(pattern in file_path for pattern in skip_files):
            return True
            
        return False
    
    def lint_file(self, file_path: Path) -> List[FunctionComplexityViolation]:
        """Lint a single Python file for function complexity"""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if self._should_skip_function(node.name, str(file_path)):
                        continue
                        
                    lines = self._count_function_lines(node)
                    if lines > self.max_lines:
                        rel_path = str(file_path.relative_to(self.root_path))
                        violation = FunctionComplexityViolation(
                            file_path=rel_path,
                            function_name=node.name,
                            line_number=node.lineno,
                            actual_lines=lines,
                            max_lines=self.max_lines,
                            message=f"Function '{node.name}' has {lines} lines (max: {self.max_lines})"
                        )
                        violations.append(violation)
        
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
        
        return violations
    
    def lint_directory(self, patterns: List[str] = None) -> None:
        """Lint all Python files in directory"""
        if patterns is None:
            patterns = ["**/*.py"]
        
        for pattern in patterns:
            for file_path in self.root_path.rglob(pattern):
                if self._should_skip_file(file_path):
                    continue
                
                file_violations = self.lint_file(file_path)
                self.violations.extend(file_violations)
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_dirs = {
            "__pycache__", ".git", "node_modules", 
            ".pytest_cache", "migrations", "venv", 
            ".venv", "env", ".env"
        }
        
        # Skip if any parent directory is in skip list
        if any(part in skip_dirs for part in file_path.parts):
            return True
        
        # Skip generated or third-party files
        if "site-packages" in str(file_path):
            return True
            
        return False
    
    def generate_report(self) -> Dict:
        """Generate linting report"""
        return {
            "total_violations": len(self.violations),
            "max_lines_allowed": self.max_lines,
            "violations": [asdict(v) for v in self.violations],
            "files_with_violations": len(set(v.file_path for v in self.violations)),
            "worst_violations": sorted(
                [asdict(v) for v in self.violations], 
                key=lambda x: x["actual_lines"], 
                reverse=True
            )[:10]
        }
    
    def print_report(self) -> None:
        """Print human-readable report"""
        print(f"\nFunction Complexity Linter Report")
        print("=" * 50)
        print(f"Maximum lines allowed: {self.max_lines}")
        print(f"Total violations: {len(self.violations)}")
        print(f"Files with violations: {len(set(v.file_path for v in self.violations))}")
        
        if self.violations:
            print(f"\nWorst violations:")
            sorted_violations = sorted(
                self.violations, 
                key=lambda x: x.actual_lines, 
                reverse=True
            )
            
            for i, violation in enumerate(sorted_violations[:10], 1):
                print(f"  {i}. {violation.function_name}() - {violation.actual_lines} lines")
                print(f"     {violation.file_path}:{violation.line_number}")
            
            if len(self.violations) > 10:
                print(f"     ... and {len(self.violations) - 10} more violations")
        else:
            print("\n✅ No function complexity violations found!")

def create_pre_commit_hook() -> str:
    """Create pre-commit hook script content"""
    return '''#!/bin/bash
# Function Complexity Pre-commit Hook
# Enforces 8-line function limit

echo "Checking function complexity..."

python scripts/function_complexity_linter.py --check

if [ $? -ne 0 ]; then
    echo "❌ Function complexity violations found!"
    echo "Please refactor functions to be ≤ 8 lines each."
    echo "Run: python scripts/function_complexity_linter.py --fix-suggestions"
    exit 1
fi

echo "✅ Function complexity check passed"
exit 0
'''

def create_ci_integration() -> str:
    """Create CI integration script"""
    return '''# GitHub Actions Integration
name: Function Complexity Check

on: [push, pull_request]

jobs:
  function-complexity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Check Function Complexity
        run: |
          python scripts/function_complexity_linter.py --check --fail-on-violation
'''

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Function Complexity Linter - Enforce 8-line function limit"
    )
    
    parser.add_argument(
        "--max-lines", 
        type=int, 
        default=8,
        help="Maximum lines per function (default: 8)"
    )
    
    parser.add_argument(
        "--path", 
        default=".",
        help="Root path to lint (default: current directory)"
    )
    
    parser.add_argument(
        "--check", 
        action="store_true",
        help="Check for violations and exit with error code if found"
    )
    
    parser.add_argument(
        "--json", 
        action="store_true",
        help="Output results in JSON format"
    )
    
    parser.add_argument(
        "--fail-on-violation", 
        action="store_true",
        help="Exit with non-zero code if violations found"
    )
    
    parser.add_argument(
        "--fix-suggestions", 
        action="store_true",
        help="Provide suggestions for fixing violations"
    )
    
    parser.add_argument(
        "--install-hook", 
        action="store_true",
        help="Install pre-commit hook"
    )
    
    args = parser.parse_args()
    
    if args.install_hook:
        hook_path = Path(".git/hooks/pre-commit")
        hook_path.parent.mkdir(exist_ok=True)
        hook_path.write_text(create_pre_commit_hook())
        hook_path.chmod(0o755)
        print("✅ Pre-commit hook installed")
        return
    
    linter = FunctionComplexityLinter(
        max_lines=args.max_lines,
        root_path=args.path
    )
    
    linter.lint_directory()
    
    if args.json:
        print(json.dumps(linter.generate_report(), indent=2))
    else:
        linter.print_report()
    
    if args.fix_suggestions and linter.violations:
        print(f"\n🔧 Fix Suggestions:")
        print("1. Break large functions into smaller helper functions")
        print("2. Extract complex logic into separate methods")
        print("3. Use early returns to reduce nesting")
        print("4. Consider using design patterns like Strategy or Command")
        print("5. Move validation logic to separate validator functions")
    
    if args.fail_on_violation and linter.violations:
        sys.exit(1)
    
    if args.check:
        sys.exit(1 if linter.violations else 0)

if __name__ == "__main__":
    main()