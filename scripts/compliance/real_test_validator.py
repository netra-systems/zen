"""Real Test Requirements Validator

Validates test files against SPEC/testing.xml real test requirements:
1. No mock component implementations inside test files
2. Integration tests use real child components  
3. Files must not exceed 300 lines
4. Functions must not exceed 8 lines
5. Minimal mocking (only external APIs)

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity, Risk Reduction
- Value Impact: Prevents regression from invalid test patterns
- Strategic Impact: Ensures test reliability and system integrity
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TestViolation:
    """Represents a test requirement violation"""
    file_path: str
    violation_type: str
    line_number: int
    description: str
    severity: str  # "critical", "major", "minor"


class RealTestValidator:
    """Validates test files against real test requirements"""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.violations: List[TestViolation] = []
        
    def validate_all_tests(self) -> List[TestViolation]:
        """Validate all test files in the project"""
        test_patterns = [
            "**/test_*.py",
            "**/*_test.py", 
            "**/tests/**/*.py"
        ]
        
        test_files = set()
        for pattern in test_patterns:
            test_files.update(self.root_path.glob(pattern))
            
        # Filter out non-test utility files
        test_files = {f for f in test_files if self._is_test_file(f)}
        
        for test_file in test_files:
            self._validate_file(test_file)
            
        return self.violations
    
    def _is_test_file(self, file_path: Path) -> bool:
        """Check if file is actually a test file"""
        if not file_path.name.endswith('.py'):
            return False
            
        # Skip utility files
        skip_patterns = [
            'conftest.py', 'fixtures.py', 'helpers.py', 
            'utils.py', '__init__.py'
        ]
        
        if any(pattern in file_path.name for pattern in skip_patterns):
            return False
            
        return True
    
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
                if 'mock' in node.name.lower() and 'component' in node.name.lower():
                    self.validator._add_violation(
                        self.file_path, "mock_component_class", node.lineno,
                        f"Mock component class '{node.name}' defined in test file",
                        "critical"
                    )
                self.generic_visit(node)
                
            def visit_FunctionDef(self, node):
                # Check for mock component functions
                if ('mock' in node.name.lower() and 
                    any(term in node.name.lower() for term in ['component', 'widget', 'element'])):
                    self.validator._add_violation(
                        self.file_path, "mock_component_function", node.lineno,
                        f"Mock component function '{node.name}' defined in test file",
                        "critical"
                    )
                self.generic_visit(node)
        
        visitor = MockComponentVisitor(self)
        visitor.visit(tree)
        
        # Also check for string patterns indicating mock components
        mock_patterns = [
            r'class\s+Mock\w*Component',
            r'def\s+create_mock_\w*component',
            r'def\s+mock_\w*_component'
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in mock_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self._add_violation(
                        file_path, "mock_component_pattern", i,
                        f"Mock component pattern found: {line.strip()}",
                        "critical"
                    )
    
    def _check_function_sizes(self, file_path: Path, tree: ast.AST, lines: List[str]):
        """Check if functions exceed 8-line limit"""
        
        class FunctionSizeVisitor(ast.NodeVisitor):
            def __init__(self, validator):
                self.validator = validator
                self.file_path = file_path
                
            def visit_FunctionDef(self, node):
                self._check_function_size(node)
                self.generic_visit(node)
                
            def visit_AsyncFunctionDef(self, node):
                self._check_function_size(node)
                self.generic_visit(node)
                
            def _check_function_size(self, node):
                # Calculate actual function body lines (excluding docstring and decorators)
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                
                # More accurate line counting
                actual_lines = 0
                in_docstring = False
                
                for line_num in range(start_line, end_line + 1):
                    if line_num <= len(lines):
                        line = lines[line_num - 1].strip()
                        
                        # Skip empty lines and comments
                        if not line or line.startswith('#'):
                            continue
                            
                        # Skip docstring
                        if line.startswith('"""') or line.startswith("'''"):
                            in_docstring = not in_docstring
                            continue
                        
                        if in_docstring:
                            continue
                            
                        # Skip function definition line
                        if 'def ' in line and ':' in line:
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
            
        # Count mock usage
        mock_count = 0
        mock_patterns = [
            r'Mock\(\)', r'AsyncMock\(\)', r'MagicMock\(\)',
            r'patch\(', r'mock_\w+\s*=', r'\.return_value\s*='
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in mock_patterns:
                if re.search(pattern, line):
                    mock_count += 1
                    
        # If integration test has too many mocks, flag it
        if mock_count > 5:  # Threshold for "excessive mocking"
            self._add_violation(
                file_path, "excessive_mocking", 1,
                f"Integration test has {mock_count} mock usages, should use real components",
                "major"
            )
    
    def _add_violation(self, file_path: Path, violation_type: str, line_number: int, 
                      description: str, severity: str):
        """Add a violation to the list"""
        self.violations.append(TestViolation(
            file_path=str(file_path.relative_to(self.root_path)),
            violation_type=violation_type,
            line_number=line_number,
            description=description,
            severity=severity
        ))
    
    def generate_report(self) -> str:
        """Generate a comprehensive report of violations"""
        if not self.violations:
            return "All tests comply with real test requirements!"
        
        # Group violations by type and severity
        by_severity = {"critical": [], "major": [], "minor": []}
        by_type = {}
        
        for violation in self.violations:
            by_severity[violation.severity].append(violation)
            if violation.violation_type not in by_type:
                by_type[violation.violation_type] = []
            by_type[violation.violation_type].append(violation)
        
        report = ["# Real Test Requirements Violations Report", ""]
        
        # Summary
        total = len(self.violations)
        critical = len(by_severity["critical"])
        major = len(by_severity["major"])
        minor = len(by_severity["minor"])
        
        report.extend([
            f"**Total Violations:** {total}",
            f"- CRITICAL: {critical}",
            f"- MAJOR: {major}",
            f"- MINOR: {minor}",
            ""
        ])
        
        # Violations by type
        report.extend(["## Violations by Type", ""])
        
        for violation_type, violations in by_type.items():
            report.extend([f"### {violation_type.replace('_', ' ').title()} ({len(violations)})", ""])
            
            for violation in violations[:10]:  # Show first 10 per type
                severity_prefix = {"critical": "[CRITICAL]", "major": "[MAJOR]", "minor": "[MINOR]"}[violation.severity]
                report.append(f"{severity_prefix} **{violation.file_path}:{violation.line_number}** - {violation.description}")
            
            if len(violations) > 10:
                report.append(f"... and {len(violations) - 10} more")
            report.append("")
        
        # Most problematic files
        file_counts = {}
        for violation in self.violations:
            file_counts[violation.file_path] = file_counts.get(violation.file_path, 0) + 1
        
        top_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        if top_files:
            report.extend(["## Most Problematic Files", ""])
            for file_path, count in top_files:
                report.append(f"- **{file_path}** ({count} violations)")
            report.append("")
        
        return '\n'.join(report)


def main():
    """Main validation entry point"""
    import sys
    import os
    
    # Add scripts directory to path for standalone execution
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    
    root_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    try:
        validator = RealTestValidator(root_path)
        violations = validator.validate_all_tests()
        
        report = validator.generate_report()
        
        # Ensure output is properly encoded
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        
        print(report)
        
        # Return non-zero exit code if critical violations found
        critical_violations = [v for v in violations if v.severity == "critical"]
        return len(critical_violations)
        
    except Exception as e:
        print(f"Error running validator: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit(main())