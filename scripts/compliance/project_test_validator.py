"""Project-Only Real Test Requirements Validator

Validates only project test files against SPEC/testing.xml real test requirements.
Excludes virtual environments and external libraries.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity, Risk Reduction
- Value Impact: Prevents regression from invalid test patterns in our code
- Strategic Impact: Ensures test reliability and system integrity
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass


@dataclass
class TestViolation:
    """Represents a test requirement violation"""
    file_path: str
    violation_type: str
    line_number: int
    description: str
    severity: str


class ProjectTestValidator:
    """Validates project test files only"""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.violations: List[TestViolation] = []
        
        # Directories to exclude from scanning
        self.exclude_dirs = {
            '.venv', 'venv', 'venv_test', '__pycache__',
            '.git', '.pytest_cache', 'node_modules',
            '.env', 'env'
        }
        
    def validate_project_tests(self) -> List[TestViolation]:
        """Validate project test files only"""
        project_test_files = self._find_project_test_files()
        
        for test_file in project_test_files:
            self._validate_file(test_file)
            
        return self.violations
    
    def _find_project_test_files(self) -> Set[Path]:
        """Find test files in the project, excluding external dependencies"""
        test_files = set()
        
        # Search in key project directories
        project_dirs = [
            'app/tests',
            'tests', 
            'auth_service/tests',
            'frontend/tests',
            'integration_tests'
        ]
        
        for dir_name in project_dirs:
            dir_path = self.root_path / dir_name
            if dir_path.exists():
                test_files.update(self._scan_directory_for_tests(dir_path))
        
        # Also check for test files in main project directories
        for pattern in ['**/test_*.py', '**/*_test.py']:
            for file_path in self.root_path.glob(pattern):
                if self._is_project_file(file_path):
                    test_files.add(file_path)
        
        return test_files
    
    def _scan_directory_for_tests(self, directory: Path) -> Set[Path]:
        """Recursively scan directory for test files"""
        test_files = set()
        
        for file_path in directory.rglob('*.py'):
            if self._is_test_file(file_path) and self._is_project_file(file_path):
                test_files.add(file_path)
                
        return test_files
    
    def _is_project_file(self, file_path: Path) -> bool:
        """Check if file is part of the project (not external dependency)"""
        path_parts = file_path.parts
        
        # Skip if any part of path is an excluded directory
        for part in path_parts:
            if part in self.exclude_dirs:
                return False
        
        # Check if starts with site-packages (Python dependencies)
        path_str = str(file_path)
        if 'site-packages' in path_str:
            return False
            
        return True
    
    def _is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file"""
        name = file_path.name
        
        # Skip utility files
        skip_patterns = [
            'conftest.py', 'fixtures.py', 'helpers.py', 
            'utils.py', '__init__.py', 'harness.py',
            'runners.py', 'context.py'
        ]
        
        if any(pattern in name for pattern in skip_patterns):
            return False
            
        # Must be a test file
        return name.startswith('test_') or name.endswith('_test.py') or '_test_' in name
    
    def _validate_file(self, file_path: Path):
        """Validate a single test file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            # Check file size limit
            self._check_file_size(file_path, lines)
            
            # Parse AST for detailed analysis
            try:
                tree = ast.parse(content)
                self._check_mock_components(file_path, tree, lines)
                self._check_function_sizes(file_path, tree, lines)
                self._check_integration_test_mocking(file_path, tree, lines)
            except SyntaxError as e:
                self._add_violation(
                    file_path, "syntax_error", getattr(e, 'lineno', 1),
                    f"Syntax error: {e}", "critical"
                )
                
        except Exception as e:
            self._add_violation(
                file_path, "file_error", 1,
                f"Could not read file: {e}", "critical"
            )
    
    def _check_file_size(self, file_path: Path, lines: List[str]):
        """Check if file exceeds 300-line limit"""
        if len(lines) > 300:
            self._add_violation(
                file_path, "file_size", len(lines),
                f"File has {len(lines)} lines, exceeds 300-line limit", 
                "major"
            )
    
    def _check_mock_components(self, file_path: Path, tree: ast.AST, lines: List[str]):
        """Check for mock component definitions inside test files"""
        
        class MockComponentVisitor(ast.NodeVisitor):
            def __init__(self, validator):
                self.validator = validator
                self.file_path = file_path
                
            def visit_ClassDef(self, node):
                # Check for mock component classes
                name_lower = node.name.lower()
                if ('mock' in name_lower and 
                    any(term in name_lower for term in ['component', 'widget', 'element', 'view'])):
                    self.validator._add_violation(
                        self.file_path, "mock_component_class", node.lineno,
                        f"Mock component class '{node.name}' defined in test file",
                        "critical"
                    )
                self.generic_visit(node)
                
            def visit_FunctionDef(self, node):
                # Check for mock component functions
                name_lower = node.name.lower()
                if ('mock' in name_lower and 
                    any(term in name_lower for term in ['component', 'widget', 'element'])):
                    self.validator._add_violation(
                        self.file_path, "mock_component_function", node.lineno,
                        f"Mock component function '{node.name}' defined in test file",
                        "critical"
                    )
                self.generic_visit(node)
        
        visitor = MockComponentVisitor(self)
        visitor.visit(tree)
    
    def _check_function_sizes(self, file_path: Path, tree: ast.AST, lines: List[str]):
        """Check if functions exceed 8-line limit"""
        
        class FunctionSizeVisitor(ast.NodeVisitor):
            def __init__(self, validator):
                self.validator = validator
                self.file_path = file_path
                self.lines = lines
                
            def visit_FunctionDef(self, node):
                self._check_function_size(node)
                self.generic_visit(node)
                
            def visit_AsyncFunctionDef(self, node):
                self._check_function_size(node)
                self.generic_visit(node)
                
            def _check_function_size(self, node):
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                
                # Count meaningful lines (exclude docstring, comments, empty lines)
                actual_lines = 0
                in_docstring = False
                skip_def_line = True
                
                for line_num in range(start_line, end_line + 1):
                    if line_num <= len(self.lines):
                        line = self.lines[line_num - 1].strip()
                        
                        # Skip empty lines and comments
                        if not line or line.startswith('#'):
                            continue
                            
                        # Skip function definition line
                        if skip_def_line and ('def ' in line):
                            skip_def_line = False
                            continue
                            
                        # Handle docstrings
                        if line.startswith('"""') or line.startswith("'''"):
                            if line.count('"""') == 2 or line.count("'''") == 2:
                                # Single-line docstring
                                continue
                            else:
                                in_docstring = not in_docstring
                                continue
                        
                        if in_docstring:
                            continue
                            
                        actual_lines += 1
                
                if actual_lines > 8:
                    self.validator._add_violation(
                        self.file_path, "function_size", node.lineno,
                        f"Function '{node.name}' has {actual_lines} lines, exceeds 8-line limit",
                        "major"
                    )
        
        visitor = FunctionSizeVisitor(self)
        visitor.visit(tree)
    
    def _check_integration_test_mocking(self, file_path: Path, tree: ast.AST, lines: List[str]):
        """Check for excessive mocking in integration tests"""
        
        # Check if this appears to be an integration test
        file_content = '\n'.join(lines)
        is_integration_test = any(indicator in file_content.lower() for indicator in [
            'integration', 'e2e', 'end-to-end', 'test_integration'
        ])
        
        if not is_integration_test:
            return
            
        # Count mock usage patterns
        mock_count = 0
        mock_patterns = [
            'Mock\\(', 'AsyncMock\\(', 'MagicMock\\(',
            'patch\\(', '@patch', 'mock_\\w+\\s*=', 
            '\\.return_value\\s*=', '\\.side_effect\\s*='
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in mock_patterns:
                if re.search(pattern, line):
                    mock_count += 1
                    
        # Threshold for excessive mocking in integration tests
        if mock_count > 5:
            self._add_violation(
                file_path, "excessive_mocking", 1,
                f"Integration test has {mock_count} mock usages, should use real components",
                "major"
            )
    
    def _add_violation(self, file_path: Path, violation_type: str, line_number: int, 
                      description: str, severity: str):
        """Add a violation to the list"""
        try:
            rel_path = file_path.relative_to(self.root_path)
        except ValueError:
            rel_path = file_path
            
        self.violations.append(TestViolation(
            file_path=str(rel_path),
            violation_type=violation_type,
            line_number=line_number,
            description=description,
            severity=severity
        ))
    
    def generate_report(self) -> str:
        """Generate a comprehensive report of project violations"""
        if not self.violations:
            return "[OK] All project tests comply with real test requirements!"
        
        # Group violations by type and severity
        by_severity = {"critical": [], "major": [], "minor": []}
        by_type = {}
        
        for violation in self.violations:
            by_severity[violation.severity].append(violation)
            if violation.violation_type not in by_type:
                by_type[violation.violation_type] = []
            by_type[violation.violation_type].append(violation)
        
        report = ["# Project Real Test Requirements Violations", ""]
        
        # Summary
        total = len(self.violations)
        critical = len(by_severity["critical"])
        major = len(by_severity["major"])
        minor = len(by_severity["minor"])
        
        report.extend([
            f"**Total Violations:** {total}",
            f"- [CRITICAL]: {critical}",
            f"- [MAJOR]: {major}",
            f"- [MINOR]: {minor}",
            ""
        ])
        
        # Most severe violations first
        for severity in ["critical", "major", "minor"]:
            violations = by_severity[severity]
            if not violations:
                continue
                
            report.extend([f"## {severity.upper()} Violations ({len(violations)})", ""])
            
            # Group by type within severity
            type_groups = {}
            for v in violations:
                if v.violation_type not in type_groups:
                    type_groups[v.violation_type] = []
                type_groups[v.violation_type].append(v)
            
            for violation_type, type_violations in type_groups.items():
                type_name = violation_type.replace('_', ' ').title()
                report.extend([f"### {type_name} ({len(type_violations)})", ""])
                
                for violation in type_violations[:20]:  # Show first 20 per type
                    report.append(f"- **{violation.file_path}:{violation.line_number}** {violation.description}")
                
                if len(type_violations) > 20:
                    report.append(f"- ... and {len(type_violations) - 20} more")
                report.append("")
        
        return '\n'.join(report)
    
    def get_examples_for_fixes(self) -> Dict[str, List[str]]:
        """Get example violations for each type to guide fixes"""
        examples = {}
        
        for violation in self.violations:
            if violation.violation_type not in examples:
                examples[violation.violation_type] = []
            
            if len(examples[violation.violation_type]) < 5:  # Max 5 examples per type
                examples[violation.violation_type].append(
                    f"{violation.file_path}:{violation.line_number} - {violation.description}"
                )
        
        return examples


def main():
    """Main validation entry point"""
    import sys
    
    root_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    validator = ProjectTestValidator(root_path)
    violations = validator.validate_project_tests()
    
    report = validator.generate_report()
    print(report)
    
    # Show examples for fixes if violations found
    if violations:
        print("\n" + "="*50)
        print("VIOLATION EXAMPLES FOR FIXES:")
        examples = validator.get_examples_for_fixes()
        
        for violation_type, example_list in examples.items():
            print(f"\n{violation_type.replace('_', ' ').upper()}:")
            for example in example_list:
                print(f"  - {example}")
    
    # Return non-zero exit code if critical violations found
    critical_violations = [v for v in violations if v.severity == "critical"]
    return len(critical_violations)


if __name__ == "__main__":
    exit(main())