#!/usr/bin/env python3
"""
Comprehensive test size limits validator for Netra testing system.

Enforces SPEC/testing.xml requirements:
- Test files MUST follow same 450-line limit as production code
- Test functions MUST follow same 25-line limit as production code
- Prevents test files from becoming unmaintainable "ravioli code"

Features:
- Scans all test files for size violations
- Reports files exceeding 300 lines
- Reports functions exceeding 8 lines  
- Provides refactoring suggestions
- Can auto-split large test files
- Integration with test runner
"""

import ast
import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

@dataclass
class SizeViolation:
    """Represents a test size violation"""
    file_path: str
    violation_type: str  # 'file_size' or 'function_size'
    severity: str
    actual_value: int
    expected_value: int
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    description: str = ""
    fix_suggestion: str = ""

@dataclass
class TestFileAnalysis:
    """Analysis results for a test file"""
    file_path: str
    total_lines: int
    test_functions: List[Dict]
    test_classes: List[Dict]
    helper_functions: List[Dict]
    violations: List[SizeViolation]
    splitting_suggestions: List[str]

class TestSizeValidator:
    """Comprehensive test size limits validator"""
    
    # Constants from SPEC/testing.xml
    MAX_TEST_FILE_LINES = 300
    MAX_TEST_FUNCTION_LINES = 8
    
    def __init__(self, root_path: Path = None):
        self.root_path = root_path or PROJECT_ROOT
        self.violations = []
        self.file_analyses = {}
        
    def validate_all_tests(self) -> Dict:
        """Validate all test files for size compliance"""
        print("Scanning for test size violations...")
        
        test_files = self._discover_test_files()
        print(f"Found {len(test_files)} test files")
        
        results = {
            "total_files": len(test_files),
            "violations": [],
            "file_analyses": {},
            "summary": {
                "files_exceeding_limit": 0,
                "functions_exceeding_limit": 0,
                "total_violations": 0,
                "largest_file": {"path": "", "lines": 0},
                "largest_function": {"path": "", "name": "", "lines": 0}
            }
        }
        
        for file_path in test_files:
            try:
                analysis = self._analyze_test_file(file_path)
                results["file_analyses"][analysis.file_path] = asdict(analysis)
                results["violations"].extend([asdict(v) for v in analysis.violations])
                
                # Update summary stats
                if analysis.total_lines > self.MAX_TEST_FILE_LINES:
                    results["summary"]["files_exceeding_limit"] += 1
                    
                if analysis.total_lines > results["summary"]["largest_file"]["lines"]:
                    results["summary"]["largest_file"] = {
                        "path": analysis.file_path,
                        "lines": analysis.total_lines
                    }
                
                for func in analysis.test_functions:
                    if func["lines"] > self.MAX_TEST_FUNCTION_LINES:
                        results["summary"]["functions_exceeding_limit"] += 1
                        
                    if func["lines"] > results["summary"]["largest_function"]["lines"]:
                        results["summary"]["largest_function"] = {
                            "path": analysis.file_path,
                            "name": func["name"],
                            "lines": func["lines"]
                        }
                        
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
                
        results["summary"]["total_violations"] = len(results["violations"])
        return results
    
    def _discover_test_files(self) -> List[Path]:
        """Discover all test files in the project"""
        test_files = []
        
        # Define specific test directories to search
        test_directories = [
            self.root_path / "app" / "tests",
            self.root_path / "tests",
            self.root_path / "auth_service" / "tests",
            self.root_path / "frontend" / "__tests__",
            self.root_path / "test_framework",
        ]
        
        # Search only in known test directories
        for test_dir in test_directories:
            if test_dir.exists():
                # Search for test files in this directory
                for path in test_dir.rglob("*.py"):
                    if self._is_test_file(path):
                        test_files.append(path)
        
        # Also check root level test files (but not recursively)
        for path in self.root_path.glob("test_*.py"):
            if self._is_test_file(path):
                test_files.append(path)
                    
        return list(set(test_files))  # Remove duplicates
    
    def _is_test_file(self, path: Path) -> bool:
        """Check if file is a test file"""
        if not path.suffix == '.py':
            return False
            
        # Exclude virtual environments and site-packages
        path_str = str(path)
        excluded_dirs = ['venv', '.venv', 'venv_test', 'site-packages', '__pycache__', 
                        'node_modules', '.git', '.pytest_cache', '.tox', 'env']
        for excluded in excluded_dirs:
            if f'{os.sep}{excluded}{os.sep}' in path_str or f'/{excluded}/' in path_str:
                return False
                
        # Check by path
        if any(pattern in path_str for pattern in ['/tests/', 'test_', '_test.py']):
            return True
            
        # Check by content - look for test functions
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'def test_' in content or 'class Test' in content
        except:
            return False
    
    def _analyze_test_file(self, file_path: Path) -> TestFileAnalysis:
        """Analyze a single test file for size violations"""
        rel_path = str(file_path.relative_to(self.root_path))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
        total_lines = len(lines)
        violations = []
        
        # Check file size
        if total_lines > self.MAX_TEST_FILE_LINES:
            violations.append(SizeViolation(
                file_path=rel_path,
                violation_type="file_size",
                severity="high",
                actual_value=total_lines,
                expected_value=self.MAX_TEST_FILE_LINES,
                description=f"Test file exceeds {self.MAX_TEST_FILE_LINES} line limit",
                fix_suggestion=f"Split into {(total_lines // self.MAX_TEST_FILE_LINES) + 1} focused test modules"
            ))
        
        # Parse AST for function analysis
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return TestFileAnalysis(
                file_path=rel_path,
                total_lines=total_lines,
                test_functions=[],
                test_classes=[],
                helper_functions=[],
                violations=violations,
                splitting_suggestions=[]
            )
        
        # Analyze functions and classes
        test_functions = []
        test_classes = []
        helper_functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = self._analyze_function(node, content, rel_path)
                if self._is_test_function(node):
                    test_functions.append(func_info)
                    # Check for function size violation
                    if func_info["lines"] > self.MAX_TEST_FUNCTION_LINES:
                        violations.append(SizeViolation(
                            file_path=rel_path,
                            violation_type="function_size",
                            severity="high",
                            actual_value=func_info["lines"],
                            expected_value=self.MAX_TEST_FUNCTION_LINES,
                            line_number=node.lineno,
                            function_name=node.name,
                            description=f"Test function '{node.name}' exceeds {self.MAX_TEST_FUNCTION_LINES} line limit",
                            fix_suggestion="Split into multiple focused test functions or extract helper methods"
                        ))
                else:
                    helper_functions.append(func_info)
                    
            elif isinstance(node, ast.ClassDef):
                if self._is_test_class(node):
                    class_info = self._analyze_class(node, content)
                    test_classes.append(class_info)
        
        # Generate splitting suggestions
        splitting_suggestions = self._generate_splitting_suggestions(
            rel_path, total_lines, test_functions, test_classes, helper_functions
        )
        
        return TestFileAnalysis(
            file_path=rel_path,
            total_lines=total_lines,
            test_functions=test_functions,
            test_classes=test_classes,
            helper_functions=helper_functions,
            violations=violations,
            splitting_suggestions=splitting_suggestions
        )
    
    def _is_test_function(self, node: ast.FunctionDef) -> bool:
        """Check if function is a test function"""
        return (node.name.startswith('test_') or
                node.name.startswith('pytest_') or
                any(self._is_pytest_decorator(decorator) for decorator in node.decorator_list))
    
    def _is_pytest_decorator(self, decorator) -> bool:
        """Check if decorator is a pytest decorator"""
        if isinstance(decorator, ast.Name):
            return decorator.id.startswith('pytest')
        elif isinstance(decorator, ast.Attribute):
            return (hasattr(decorator, 'value') and 
                    isinstance(decorator.value, ast.Name) and
                    decorator.value.id == 'pytest')
        return False
    
    def _is_test_class(self, node: ast.ClassDef) -> bool:
        """Check if class is a test class"""
        return (node.name.startswith('Test') or
                'test' in node.name.lower() or
                any(base.id.startswith('Test') for base in node.bases
                    if isinstance(base, ast.Name)))
    
    def _analyze_function(self, node: ast.FunctionDef, content: str, file_path: str) -> Dict:
        """Analyze a function for metrics"""
        lines = content.split('\n')
        start_line = node.lineno - 1  # Convert to 0-based
        
        # Find end line
        end_line = start_line
        if hasattr(node, 'end_lineno') and node.end_lineno:
            end_line = node.end_lineno - 1
        else:
            # Estimate end line by finding next function or class
            for i in range(start_line + 1, len(lines)):
                if lines[i].strip() and not lines[i].startswith((' ', '\t')):
                    end_line = i - 1
                    break
            else:
                end_line = len(lines) - 1
        
        func_lines = end_line - start_line + 1
        
        # Count actual code lines (excluding empty lines and comments)
        code_lines = 0
        for i in range(start_line, min(end_line + 1, len(lines))):
            line = lines[i].strip()
            if line and not line.startswith('#'):
                code_lines += 1
        
        return {
            "name": node.name,
            "line_number": node.lineno,
            "lines": func_lines,
            "code_lines": code_lines,
            "complexity": self._estimate_complexity(node),
            "has_docstring": self._has_docstring(node)
        }
    
    def _analyze_class(self, node: ast.ClassDef, content: str) -> Dict:
        """Analyze a test class"""
        lines = content.split('\n')
        start_line = node.lineno - 1
        
        # Count methods
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        test_methods = [m for m in methods if self._is_test_function(m)]
        
        return {
            "name": node.name,
            "line_number": node.lineno,
            "total_methods": len(methods),
            "test_methods": len(test_methods),
            "method_names": [m.name for m in test_methods]
        }
    
    def _estimate_complexity(self, node: ast.FunctionDef) -> int:
        """Estimate cyclomatic complexity of function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.Try):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
                
        return complexity
    
    def _has_docstring(self, node: ast.FunctionDef) -> bool:
        """Check if function has a docstring"""
        return (len(node.body) > 0 and
                isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, ast.Constant) and
                isinstance(node.body[0].value.value, str))
    
    def _generate_splitting_suggestions(self, file_path: str, total_lines: int,
                                      test_functions: List, test_classes: List,
                                      helper_functions: List) -> List[str]:
        """Generate suggestions for splitting large test files"""
        suggestions = []
        
        if total_lines <= self.MAX_TEST_FILE_LINES:
            return suggestions
            
        suggestions.append(f"File has {total_lines} lines (limit: {self.MAX_TEST_FILE_LINES})")
        suggestions.append("Recommended splitting strategies:")
        
        # Strategy 1: Split by test type
        if len(test_functions) > 10:
            suggestions.append("1. Split by test categories:")
            suggestions.append(f"   - {file_path.replace('.py', '_unit.py')} (unit tests)")
            suggestions.append(f"   - {file_path.replace('.py', '_integration.py')} (integration tests)")
            suggestions.append(f"   - {file_path.replace('.py', '_e2e.py')} (end-to-end tests)")
        
        # Strategy 2: Split by functionality
        if len(test_classes) > 1:
            suggestions.append("2. Split by test classes:")
            for cls in test_classes[:3]:  # Show first 3
                suggestions.append(f"   - {file_path.replace('.py', f'_{cls['name'].lower()}.py')}")
        
        # Strategy 3: Extract helpers
        if len(helper_functions) > 3:
            suggestions.append("3. Extract helper functions:")
            suggestions.append(f"   - {file_path.replace('.py', '_helpers.py')} ({len(helper_functions)} helpers)")
        
        # Strategy 4: Split by feature
        suggestions.append("4. Split by feature being tested:")
        suggestions.append(f"   - {file_path.replace('.py', '_feature1.py')}")
        suggestions.append(f"   - {file_path.replace('.py', '_feature2.py')}")
        
        return suggestions
    
    def auto_split_file(self, file_path: str, strategy: str = "by_class") -> Dict:
        """Auto-split a large test file (experimental)"""
        # This is a complex operation that would require careful implementation
        # For now, return a plan
        return {
            "original_file": file_path,
            "strategy": strategy,
            "proposed_files": [],
            "warnings": ["Auto-splitting is experimental - manual review required"]
        }
    
    def generate_report(self, results: Dict, output_format: str = "text") -> str:
        """Generate comprehensive report"""
        if output_format == "json":
            return json.dumps(results, indent=2)
        elif output_format == "markdown":
            return self._generate_markdown_report(results)
        else:
            return self._generate_text_report(results)
    
    def _generate_text_report(self, results: Dict) -> str:
        """Generate text format report"""
        lines = []
        lines.append("=" * 80)
        lines.append("TEST SIZE COMPLIANCE REPORT")
        lines.append("=" * 80)
        
        summary = results["summary"]
        lines.append(f"Total test files scanned: {results['total_files']}")
        lines.append(f"Files exceeding {self.MAX_TEST_FILE_LINES} line limit: {summary['files_exceeding_limit']}")
        lines.append(f"Functions exceeding {self.MAX_TEST_FUNCTION_LINES} line limit: {summary['functions_exceeding_limit']}")
        lines.append(f"Total violations: {summary['total_violations']}")
        lines.append("")
        
        if summary["largest_file"]["lines"] > 0:
            lines.append("LARGEST FILES:")
            lines.append(f"  {summary['largest_file']['path']}: {summary['largest_file']['lines']} lines")
            
        if summary["largest_function"]["lines"] > 0:
            lines.append("LARGEST FUNCTIONS:")
            lines.append(f"  {summary['largest_function']['name']} in {summary['largest_function']['path']}: {summary['largest_function']['lines']} lines")
        
        lines.append("")
        
        if results["violations"]:
            lines.append("VIOLATIONS:")
            lines.append("-" * 40)
            for violation in results["violations"]:
                lines.append(f"[X] {violation['file_path']}")
                lines.append(f"   Type: {violation['violation_type']}")
                lines.append(f"   {violation['description']}")
                lines.append(f"   Fix: {violation['fix_suggestion']}")
                lines.append("")
        else:
            lines.append("[OK] No size violations found!")
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self, results: Dict) -> str:
        """Generate markdown format report"""
        lines = []
        lines.append("# Test Size Compliance Report")
        lines.append()
        
        summary = results["summary"]
        lines.append("## Summary")
        lines.append()
        lines.append(f"- **Total test files scanned:** {results['total_files']}")
        lines.append(f"- **Files exceeding {self.MAX_TEST_FILE_LINES} line limit:** {summary['files_exceeding_limit']}")
        lines.append(f"- **Functions exceeding {self.MAX_TEST_FUNCTION_LINES} line limit:** {summary['functions_exceeding_limit']}")
        lines.append(f"- **Total violations:** {summary['total_violations']}")
        lines.append()
        
        if results["violations"]:
            lines.append("## Violations")
            lines.append()
            
            # Group violations by type
            file_violations = [v for v in results["violations"] if v["violation_type"] == "file_size"]
            func_violations = [v for v in results["violations"] if v["violation_type"] == "function_size"]
            
            if file_violations:
                lines.append("### File Size Violations")
                lines.append()
                lines.append("| File | Lines | Limit | Fix Suggestion |")
                lines.append("|------|-------|-------|----------------|")
                for v in file_violations:
                    lines.append(f"| {v['file_path']} | {v['actual_value']} | {v['expected_value']} | {v['fix_suggestion']} |")
                lines.append()
            
            if func_violations:
                lines.append("### Function Size Violations")
                lines.append()
                lines.append("| File | Function | Lines | Limit | Fix Suggestion |")
                lines.append("|------|----------|-------|-------|----------------|")
                for v in func_violations:
                    lines.append(f"| {v['file_path']} | {v['function_name']} | {v['actual_value']} | {v['expected_value']} | {v['fix_suggestion']} |")
                lines.append()
        
        # Add splitting suggestions for large files
        lines.append("## Splitting Suggestions")
        lines.append()
        for file_path, analysis in results["file_analyses"].items():
            if analysis["splitting_suggestions"]:
                lines.append(f"### {file_path}")
                lines.append()
                for suggestion in analysis["splitting_suggestions"]:
                    lines.append(f"- {suggestion}")
                lines.append()
        
        return "\n".join(lines)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Test size limits validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_size_validator.py                    # Validate all tests
  python test_size_validator.py --format json     # JSON output
  python test_size_validator.py --format markdown # Markdown output
  python test_size_validator.py --output report.md # Save to file
  python test_size_validator.py --auto-split      # Auto-split violations
        """
    )
    
    parser.add_argument("--format", choices=["text", "json", "markdown"],
                       default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--auto-split", action="store_true",
                       help="Generate auto-split suggestions")
    parser.add_argument("--strict", action="store_true",
                       help="Strict mode - fail on any violations")
    
    args = parser.parse_args()
    
    # Run validation
    validator = TestSizeValidator()
    results = validator.validate_all_tests()
    
    # Generate report
    report = validator.generate_report(results, args.format)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)
    
    # Exit with appropriate code
    if args.strict and results["summary"]["total_violations"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()