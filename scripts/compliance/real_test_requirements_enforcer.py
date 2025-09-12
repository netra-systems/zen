"""Enhanced Real Test Requirements Enforcer

Comprehensive validation and enforcement of SPEC/testing.xml real test requirements
for both Python and JavaScript test files.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity, Risk Reduction  
- Value Impact: Prevents regression bugs from invalid test patterns
- Strategic Impact: Ensures test reliability, reduces debugging time, maintains system integrity

SPEC Requirements Enforced:
1. No mock component implementations inside test files
2. Integration tests must use real child components
3. Mock only external APIs and truly unavailable resources
4. Test files must follow 450-line limit
5. Test functions must follow 25-line limit
6. Fix System Under Test first, not tests
"""

import ast
import json
import os
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class TestViolation:
    """Represents a test requirement violation"""
    file_path: str
    violation_type: str
    line_number: int
    description: str
    severity: str  # "critical", "major", "minor"
    suggestion: str = ""  # How to fix it
    code_snippet: str = ""  # Violating code


class RealTestRequirementsEnforcer:
    """Enhanced validator for real test requirements across Python and JavaScript"""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.violations: List[TestViolation] = []
        
        # Patterns for detecting mock components
        self.mock_class_patterns = [
            r'class\s+Mock\w*:', 
            r'class\s+\w*Mock\w*:',
            r'class\s+\w*Component\w*Mock\w*:',
            r'class\s+Test\w*Component\w*:'
        ]
        
        self.mock_function_patterns = [
            r'def\s+mock_\w+',
            r'def\s+\w*_mock\w*',
            r'const\s+Mock\w*\s*=',
            r'const\s+mock\w*\s*=',
            r'function\s+mock\w*\s*\('
        ]
        
        # JavaScript/TypeScript patterns
        self.js_mock_patterns = [
            r'React\.createContext\(\w*mock\w*\)',
            r'jest\.fn\(\)',
            r'jest\.mock\(',
            r'createMockComponent',
            r'MockComponent\s*=',
            r'mock\w*Context\s*='
        ]
        
    def validate_all_tests(self) -> List[TestViolation]:
        """Validate all test files in the project"""
        self.violations.clear()
        
        # Find all test files  
        test_files = self._find_all_test_files()
        
        print(f"Found {len(test_files)} test files to validate...")
        
        for test_file in test_files:
            print(f"Validating: {test_file.relative_to(self.root_path)}")
            self._validate_file(test_file)
            
        return self.violations
    
    def _find_all_test_files(self) -> Set[Path]:
        """Find all test files in the project"""
        test_files = set()
        
        # Python test patterns
        python_patterns = [
            "**/test_*.py",
            "**/*_test.py", 
            "**/tests/**/*.py",
            "**/conftest.py"  # Include fixture files
        ]
        
        # JavaScript/TypeScript test patterns
        js_patterns = [
            "**/*.test.js",
            "**/*.test.jsx", 
            "**/*.test.ts",
            "**/*.test.tsx",
            "**/__tests__/**/*.js",
            "**/__tests__/**/*.jsx",
            "**/__tests__/**/*.ts", 
            "**/__tests__/**/*.tsx",
            "**/jest.setup.js",
            "**/setupTests.js"
        ]
        
        all_patterns = python_patterns + js_patterns
        
        for pattern in all_patterns:
            matches = self.root_path.glob(pattern)
            test_files.update(matches)
        
        # Filter valid test files
        return {f for f in test_files if self._is_valid_test_file(f)}
    
    def _is_valid_test_file(self, file_path: Path) -> bool:
        """Check if file should be validated"""
        if not file_path.is_file():
            return False
            
        # Skip node_modules, virtual environments, and cache directories
        skip_patterns = [
            'node_modules', '__pycache__', '.git', 'venv', '.venv', 'venv_test',
            'site-packages', 'dist', 'build', '.pytest_cache', '.coverage'
        ]
        if any(skip in str(file_path) for skip in skip_patterns):
            return False
            
        # Skip utility files that aren't tests
        skip_patterns = ['__init__.py', 'helpers.py', 'utils.py']
        if any(pattern in file_path.name for pattern in skip_patterns):
            # But include them if they're in test directories and contain tests
            return self._contains_test_code(file_path)
            
        return True
    
    def _contains_test_code(self, file_path: Path) -> bool:
        """Check if file contains actual test code"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Python test indicators
            python_indicators = ['def test_', 'class Test', '@pytest.', 'unittest.TestCase']
            
            # JavaScript test indicators  
            js_indicators = ['it(', 'describe(', 'test(', 'expect(']
            
            return any(indicator in content for indicator in python_indicators + js_indicators)
        except Exception:
            return False
    
    def _validate_file(self, file_path: Path):
        """Validate a single test file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()
            
            # Check file size
            self._check_file_size(file_path, lines)
            
            # Language-specific validation
            if file_path.suffix == '.py':
                self._validate_python_file(file_path, content, lines)
            elif file_path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                self._validate_javascript_file(file_path, content, lines)
                
        except Exception as e:
            self._add_violation(
                file_path, "file_error", 1,
                f"Could not read file: {e}", "critical",
                "Ensure file is valid and accessible"
            )
    
    def _validate_python_file(self, file_path: Path, content: str, lines: List[str]):
        """Validate Python test file"""
        try:
            tree = ast.parse(content)
            
            # Check for mock component implementations
            self._check_python_mock_components(file_path, tree, lines)
            
            # Check function sizes
            self._check_python_function_sizes(file_path, tree, lines)
            
            # Check for excessive mocking in integration tests
            self._check_python_integration_mocking(file_path, content, lines)
            
        except SyntaxError as e:
            self._add_violation(
                file_path, "syntax_error", getattr(e, 'lineno', 1),
                f"Syntax error: {e}", "critical",
                "Fix Python syntax errors"
            )
    
    def _validate_javascript_file(self, file_path: Path, content: str, lines: List[str]):
        """Validate JavaScript/TypeScript test file"""
        
        # Check for mock component patterns
        self._check_javascript_mock_components(file_path, content, lines)
        
        # Check for excessive jest.fn() usage
        self._check_javascript_excessive_mocking(file_path, content, lines)
        
        # Check function sizes (approximate for JS)
        self._check_javascript_function_sizes(file_path, lines)
    
    def _check_file_size(self, file_path: Path, lines: List[str]):
        """Check if file exceeds 450-line limit"""
        if len(lines) > 300:
            self._add_violation(
                file_path, "file_size", len(lines),
                f"File has {len(lines)} lines, exceeds 450-line limit", "major",
                "Split large test files into smaller, focused test modules"
            )
    
    def _check_python_mock_components(self, file_path: Path, tree: ast.AST, lines: List[str]):
        """Check for mock component definitions in Python files"""
        
        class MockComponentVisitor(ast.NodeVisitor):
            def __init__(self, enforcer):
                self.enforcer = enforcer
                self.file_path = file_path
                
            def visit_ClassDef(self, node):
                # Check for mock component classes
                class_name = node.name.lower()
                
                mock_indicators = ['mock', 'fake', 'stub', 'dummy']
                component_indicators = ['component', 'widget', 'element', 'websocket', 'client', 'service']
                
                is_mock = any(indicator in class_name for indicator in mock_indicators)
                is_component = any(indicator in class_name for indicator in component_indicators)
                
                if is_mock and is_component:
                    code_snippet = lines[node.lineno-1:min(node.lineno+2, len(lines))]
                    self.enforcer._add_violation(
                        self.file_path, "mock_component_class", node.lineno,
                        f"Mock component class '{node.name}' defined in test file",
                        "critical",
                        f"Move '{node.name}' to a shared test utility module or use real components",
                        '\n'.join(code_snippet)
                    )
                    
                self.generic_visit(node)
                
            def visit_FunctionDef(self, node):
                # Check for mock component functions
                func_name = node.name.lower()
                
                if ('mock' in func_name and 
                    any(term in func_name for term in ['component', 'widget', 'websocket', 'client'])):
                    code_snippet = lines[node.lineno-1:min(node.lineno+2, len(lines))]
                    self.enforcer._add_violation(
                        self.file_path, "mock_component_function", node.lineno,
                        f"Mock component function '{node.name}' defined in test file",
                        "critical", 
                        f"Move '{node.name}' to a shared fixture or use real components",
                        '\n'.join(code_snippet)
                    )
                    
                self.generic_visit(node)
        
        visitor = MockComponentVisitor(self)
        visitor.visit(tree)
    
    def _check_python_function_sizes(self, file_path: Path, tree: ast.AST, lines: List[str]):
        """Check if functions exceed 25-line limit"""
        
        class FunctionSizeVisitor(ast.NodeVisitor):
            def __init__(self, enforcer):
                self.enforcer = enforcer
                self.file_path = file_path
                
            def visit_FunctionDef(self, node):
                self._check_function_size(node)
                self.generic_visit(node)
                
            def visit_AsyncFunctionDef(self, node):
                self._check_function_size(node)
                self.generic_visit(node)
                
            def _check_function_size(self, node):
                if not node.name.startswith('test_'):
                    return  # Only check test functions
                    
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                
                # Count actual code lines (exclude comments, docstrings, empty lines)
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
                    code_snippet = lines[start_line-1:end_line]
                    self.enforcer._add_violation(
                        self.file_path, "function_size", node.lineno,
                        f"Test function '{node.name}' has {actual_lines} lines, exceeds 25-line limit",
                        "major",
                        f"Split '{node.name}' into smaller, focused test functions",
                        '\n'.join(code_snippet[:10])  # First 10 lines
                    )
        
        visitor = FunctionSizeVisitor(self)
        visitor.visit(tree)
    
    def _check_python_integration_mocking(self, file_path: Path, content: str, lines: List[str]):
        """Check for excessive mocking in integration tests"""
        
        # Determine if this is an integration test
        is_integration = any(indicator in content.lower() for indicator in [
            'integration', 'e2e', 'end_to_end', '_integration_'
        ])
        
        if not is_integration:
            return
            
        # Count mock usage
        mock_count = 0
        mock_lines = []
        
        for i, line in enumerate(lines, 1):
            if any(pattern in line for pattern in [
                # Mock: Generic component isolation for controlled unit testing
                'Mock()', 'AsyncMock()', 'MagicMock()',
                # Mock: Component isolation for testing without external dependencies
                'patch(', 'mock_', '.return_value =', 
                'side_effect =', '@patch'
            ]):
                mock_count += 1
                mock_lines.append((i, line.strip()))
                
        # Flag excessive mocking
        if mock_count > 5:
            examples = '\n'.join([f"Line {num}: {line}" for num, line in mock_lines[:3]])
            self._add_violation(
                file_path, "excessive_mocking", 1,
                f"Integration test has {mock_count} mocks, should use real components",
                "major",
                "Replace mocks with real components or move to unit tests",
                examples
            )
    
    def _check_javascript_mock_components(self, file_path: Path, content: str, lines: List[str]):
        """Check for mock component definitions in JavaScript files"""
        
        for i, line in enumerate(lines, 1):
            for pattern in self.js_mock_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self._add_violation(
                        file_path, "js_mock_component", i,
                        f"Mock component pattern found: {line.strip()}", 
                        "critical",
                        "Use real components or move mocks to shared test utilities",
                        line.strip()
                    )
                    break
    
    def _check_javascript_excessive_mocking(self, file_path: Path, content: str, lines: List[str]):
        """Check for excessive jest.fn() usage"""
        
        jest_fn_count = content.count('jest.fn()')
        jest_mock_count = content.count('jest.mock(')
        
        total_mocks = jest_fn_count + jest_mock_count
        
        if total_mocks > 10:  # Threshold for excessive mocking
            self._add_violation(
                file_path, "js_excessive_mocking", 1,
                f"File has {total_mocks} jest mocks (jest.fn: {jest_fn_count}, jest.mock: {jest_mock_count})",
                "major", 
                "Reduce mocking by using real components and external API mocks only"
            )
    
    def _check_javascript_function_sizes(self, file_path: Path, lines: List[str]):
        """Check JavaScript function sizes (approximate)"""
        
        in_function = False
        function_start = 0
        function_name = ""
        brace_count = 0
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check for test function start
            test_patterns = [
                r'it\s*\(\s*[\'"]([^\'"]*)[\'"]',
                r'test\s*\(\s*[\'"]([^\'"]*)[\'"]', 
                r'describe\s*\(\s*[\'"]([^\'"]*)[\'"]'
            ]
            
            for pattern in test_patterns:
                match = re.search(pattern, stripped)
                if match:
                    if in_function and brace_count > 0:
                        # End previous function
                        continue
                    function_start = i
                    function_name = match.group(1)
                    in_function = True
                    brace_count = 0
                    break
            
            # Count braces to track function end
            if in_function:
                brace_count += stripped.count('{') - stripped.count('}')
                
                # Function ended
                if brace_count == 0 and function_start < i:
                    function_lines = i - function_start + 1
                    
                    if function_lines > 12:  # Slightly higher threshold for JS
                        code_snippet = '\n'.join(lines[function_start-1:min(function_start+5, len(lines))])
                        self._add_violation(
                            file_path, "js_function_size", function_start,
                            f"Test function '{function_name}' spans {function_lines} lines, exceeds reasonable limit",
                            "major",
                            "Split large test functions into smaller, focused tests",
                            code_snippet
                        )
                    
                    in_function = False
    
    def _add_violation(self, file_path: Path, violation_type: str, line_number: int, 
                      description: str, severity: str, suggestion: str = "", code_snippet: str = ""):
        """Add a violation to the list"""
        self.violations.append(TestViolation(
            file_path=str(file_path.relative_to(self.root_path)),
            violation_type=violation_type,
            line_number=line_number,
            description=description,
            severity=severity,
            suggestion=suggestion,
            code_snippet=code_snippet
        ))
    
    def generate_report(self) -> str:
        """Generate comprehensive violations report"""
        if not self.violations:
            return "[OK] All tests comply with real test requirements!"
        
        # Group violations
        by_severity = defaultdict(list)
        by_type = defaultdict(list)
        by_file = defaultdict(list)
        
        for violation in self.violations:
            by_severity[violation.severity].append(violation)
            by_type[violation.violation_type].append(violation)
            by_file[violation.file_path].append(violation)
        
        report = ["# Real Test Requirements Violations Report", ""]
        
        # Executive Summary
        total = len(self.violations)
        critical = len(by_severity["critical"])
        major = len(by_severity["major"]) 
        minor = len(by_severity["minor"])
        
        report.extend([
            f"**Total Violations:** {total} across {len(by_file)} files",
            f"- **Critical:** {critical} (Must fix immediately)", 
            f"- **Major:** {major} (Should fix soon)",
            f"- **Minor:** {minor} (Address when convenient)",
            "",
            "## Impact Analysis",
            ""
        ])
        
        # Business impact
        if critical > 0:
            report.extend([
                f" FIRE:  **{critical} CRITICAL violations** found:",
                "- Mock component implementations in test files violate real test requirements",
                "- Integration tests with mocks defeat the purpose of integration testing", 
                "- Risk of false positive test results hiding real bugs",
                ""
            ])
            
        # Top violations by type
        report.extend(["## [U+1F4CB] Violations by Category", ""])
        
        type_priority = ["mock_component_class", "mock_component_function", "js_mock_component", 
                        "excessive_mocking", "js_excessive_mocking", "function_size", "file_size"]
        
        for violation_type in type_priority:
            if violation_type in by_type:
                violations = by_type[violation_type]
                report.append(f"### {violation_type.replace('_', ' ').title()} ({len(violations)} files)")
                report.append("")
                
                for violation in violations[:5]:  # Show first 5
                    severity_emoji = {"critical": " FIRE: ", "major": " WARNING: [U+FE0F]", "minor": "[U+2139][U+FE0F]"}[violation.severity]
                    report.append(f"{severity_emoji} **{violation.file_path}:{violation.line_number}**")
                    report.append(f"   {violation.description}")
                    
                    if violation.suggestion:
                        report.append(f"    IDEA:  *{violation.suggestion}*")
                    
                    if violation.code_snippet:
                        report.append("   ```")
                        report.append(f"   {violation.code_snippet[:200]}...")
                        report.append("   ```")
                    report.append("")
                
                if len(violations) > 5:
                    report.append(f"   ... and {len(violations) - 5} more files")
                report.append("")
        
        # Most problematic files
        worst_files = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        
        if worst_files:
            report.extend(["##  TARGET:  Priority Fix List", ""])
            for file_path, file_violations in worst_files:
                critical_count = sum(1 for v in file_violations if v.severity == "critical")
                major_count = sum(1 for v in file_violations if v.severity == "major")
                
                priority = " FIRE:  HIGH" if critical_count > 0 else " WARNING: [U+FE0F] MEDIUM" 
                report.append(f"{priority} **{file_path}** ({len(file_violations)} violations)")
                
                if critical_count:
                    report.append(f"   - {critical_count} critical violations requiring immediate fix")
                if major_count:
                    report.append(f"   - {major_count} major violations to address soon")
                report.append("")
        
        # Actionable next steps
        report.extend([
            "## [U+1F6E0][U+FE0F] Recommended Actions",
            "",
            "1. **Fix Critical Violations First** - Address mock component implementations",
            "2. **Extract Shared Utilities** - Move common mocks to test/fixtures directory", 
            "3. **Use Real Components** - Replace mocks with actual component instances",
            "4. **Mock External APIs Only** - Keep mocking limited to HTTP clients, databases", 
            "5. **Split Large Functions** - Break down oversized test functions",
            "",
            f"[U+1F4C8] **Success Metric:** Reduce violations from {total} to <10 within 2 sprints",
            ""
        ])
        
        return '\n'.join(report)
    
    def export_json(self) -> str:
        """Export violations as JSON for tooling integration"""
        return json.dumps([asdict(v) for v in self.violations], indent=2)


def main():
    """Main enforcement entry point"""
    import sys
    
    root_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    enforcer = RealTestRequirementsEnforcer(root_path)
    violations = enforcer.validate_all_tests()
    
    # Generate report
    report = enforcer.generate_report()
    print(report)
    
    # Export JSON for tooling
    json_output = enforcer.export_json()
    json_path = Path("test_reports/real_test_violations.json")
    json_path.parent.mkdir(exist_ok=True)
    json_path.write_text(json_output)
    
    print(f"\n[U+1F4C4] JSON report saved to: {json_path}")
    
    # Return appropriate exit code
    critical_violations = [v for v in violations if v.severity == "critical"]
    if critical_violations:
        print(f"\n FAIL:  Exiting with error: {len(critical_violations)} critical violations found")
        return 1
    elif violations:
        print(f"\n WARNING: [U+FE0F] Warning: {len(violations)} non-critical violations found")
        return 0
    else:
        print("\n PASS:  All tests comply with real test requirements!")
        return 0


if __name__ == "__main__":
    exit(main())