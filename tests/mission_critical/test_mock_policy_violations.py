"""
Mission Critical Test Suite: Mock Usage Policy Violations

This test suite ensures compliance with CLAUDE.md policy: "MOCKS = Abomination", "MOCKS are FORBIDDEN"
Tests will FAIL if any mock usage is detected in test files, enforcing real service testing.

Business Value: Platform/Internal - Test Reliability
$500K+ ARR at risk from false test confidence and hidden integration failures

Author: Principal Engineer AI
Date: 2025-08-30
"""

import ast
import os
import sys
import re
from pathlib import Path
from typing import List, Tuple, Dict, Set
import pytest
from dataclasses import dataclass
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class MockViolation:
    """Represents a single mock usage violation."""
    file_path: str
    line_number: int
    violation_type: str
    code_snippet: str
    service: str
    
    def __str__(self):
        return f"{self.file_path}:{self.line_number} - {self.violation_type}"


class MockDetector(ast.NodeVisitor):
    """AST visitor to detect mock usage patterns."""
    
    MOCK_MODULES = {
        'unittest.mock', 'mock', 'pytest_mock', 'mocker',
        'unittest.mock.Mock', 'unittest.mock.MagicMock',
        'unittest.mock.AsyncMock', 'unittest.mock.patch',
        'pytest_mock', 'asynctest'
    }
    
    MOCK_FUNCTIONS = {
        'Mock', 'MagicMock', 'AsyncMock', 'PropertyMock',
        'patch', 'patch.object', 'patch.dict', 'patch.multiple',
        'create_autospec', 'mock_open', 'ANY', 'call', 'sentinel',
        'NonCallableMock', 'CallableMixin', 'mock_calls', 'call_args',
        'call_args_list', 'method_calls', 'configure_mock', 'attach_mock',
        'assert_called', 'assert_called_once', 'assert_called_with',
        'assert_called_once_with', 'assert_any_call', 'assert_has_calls',
        'assert_not_called', 'reset_mock', 'return_value', 'side_effect',
        'spec', 'spec_set', 'wraps', 'name', 'unsafe', 'new', 'new_callable',
        'mocker', 'monkeypatch'
    }
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations = []
        self.imports = set()
        
    def visit_ImportFrom(self, node):
        """Detect 'from unittest.mock import ...' patterns."""
        if node.module and any(mock in node.module for mock in self.MOCK_MODULES):
            for alias in node.names:
                self.violations.append(MockViolation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    violation_type="Mock Import",
                    code_snippet=f"from {node.module} import {alias.name}",
                    service=self._get_service_name()
                ))
                self.imports.add(alias.name if not alias.asname else alias.asname)
        self.generic_visit(node)
        
    def visit_Import(self, node):
        """Detect 'import unittest.mock' patterns."""
        for alias in node.names:
            if any(mock in alias.name for mock in self.MOCK_MODULES):
                self.violations.append(MockViolation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    violation_type="Mock Import",
                    code_snippet=f"import {alias.name}",
                    service=self._get_service_name()
                ))
                self.imports.add(alias.name if not alias.asname else alias.asname)
        self.generic_visit(node)
        
    def visit_Call(self, node):
        """Detect mock function calls."""
        func_name = self._get_func_name(node.func)
        if func_name in self.MOCK_FUNCTIONS or func_name in self.imports:
            self.violations.append(MockViolation(
                file_path=self.file_path,
                line_number=node.lineno,
                violation_type="Mock Usage",
                code_snippet=f"{func_name}(...)",
                service=self._get_service_name()
            ))
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node):
        """Detect @patch decorators."""
        for decorator in node.decorator_list:
            dec_name = self._get_decorator_name(decorator)
            if 'patch' in dec_name or dec_name in self.imports:
                self.violations.append(MockViolation(
                    file_path=self.file_path,
                    line_number=decorator.lineno,
                    violation_type="Patch Decorator",
                    code_snippet=f"@{dec_name}",
                    service=self._get_service_name()
                ))
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        """Detect mock attribute access like mock.patch or mock.return_value."""
        attr_name = node.attr
        if attr_name in self.MOCK_FUNCTIONS:
            self.violations.append(MockViolation(
                file_path=self.file_path,
                line_number=node.lineno,
                violation_type="Mock Attribute Access",
                code_snippet=f"*.{attr_name}",
                service=self._get_service_name()
            ))
        self.generic_visit(node)
        
    def visit_With(self, node):
        """Detect 'with patch(...):' context managers."""
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                func_name = self._get_func_name(item.context_expr.func)
                if 'patch' in func_name or func_name in self.imports:
                    self.violations.append(MockViolation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        violation_type="Mock Context Manager",
                        code_snippet=f"with {func_name}(...):",
                        service=self._get_service_name()
                    ))
        self.generic_visit(node)
        
    def visit_Assign(self, node):
        """Detect mock assignments like mock = Mock()."""
        if isinstance(node.value, ast.Call):
            func_name = self._get_func_name(node.value.func)
            if func_name in self.MOCK_FUNCTIONS or func_name in self.imports:
                # Get variable name being assigned
                var_names = []
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_names.append(target.id)
                
                self.violations.append(MockViolation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    violation_type="Mock Assignment",
                    code_snippet=f"{', '.join(var_names)} = {func_name}(...)",
                    service=self._get_service_name()
                ))
        self.generic_visit(node)
        
    def _get_func_name(self, node) -> str:
        """Extract function name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Call):
            return self._get_func_name(node.func)
        return ""
        
    def _get_decorator_name(self, node) -> str:
        """Extract decorator name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return ""
        
    def _get_service_name(self) -> str:
        """Determine which service the file belongs to."""
        if '/auth_service/' in self.file_path:
            return 'auth_service'
        elif '/analytics_service/' in self.file_path:
            return 'analytics_service'
        elif '/netra_backend/' in self.file_path:
            return 'netra_backend'
        elif '/frontend/' in self.file_path:
            return 'frontend'
        elif '/dev_launcher/' in self.file_path:
            return 'dev_launcher'
        else:
            return 'tests'


class TestMockPolicyCompliance:
    """Test suite to enforce mock usage policy across all services."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.test_directories = [
            self.project_root / 'auth_service' / 'tests',
            self.project_root / 'analytics_service' / 'tests',
            self.project_root / 'netra_backend' / 'tests',
            self.project_root / 'tests',
            self.project_root / 'dev_launcher' / 'tests',
        ]
        
    def scan_for_mock_usage(self, directory: Path) -> List[MockViolation]:
        """Scan directory for mock usage violations."""
        violations = []
        
        for py_file in directory.rglob('*.py'):
            # Skip this test file itself
            if py_file.name == 'test_mock_policy_violations.py':
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # First pass: Regex-based detection for edge cases
                violations.extend(self._regex_mock_detection(py_file, content))
                    
                # Second pass: AST-based detection
                tree = ast.parse(content)
                detector = MockDetector(str(py_file))
                detector.visit(tree)
                violations.extend(detector.violations)
                
            except (SyntaxError, UnicodeDecodeError) as e:
                # Skip files with syntax errors or encoding issues
                print(f"Warning: Could not parse {py_file}: {e}")
                continue
                
        return violations
    
    def _regex_mock_detection(self, py_file: Path, content: str) -> List[MockViolation]:
        """Use regex to catch mock patterns that AST might miss."""
        violations = []
        lines = content.split('\n')
        
        # Patterns to detect various mock usage
        mock_patterns = [
            (r'@patch\s*\(', 'Patch Decorator'),
            (r'@mock\.patch', 'Mock Patch Decorator'),
            (r'Mock\s*\(', 'Mock Constructor'),
            (r'MagicMock\s*\(', 'MagicMock Constructor'),
            (r'AsyncMock\s*\(', 'AsyncMock Constructor'),
            (r'\.patch\s*\(', 'Patch Method Call'),
            (r'mock_calls', 'Mock Calls Usage'),
            (r'return_value\s*=', 'Mock Return Value'),
            (r'side_effect\s*=', 'Mock Side Effect'),
            (r'assert_called', 'Mock Assertion'),
            (r'pytest\.fixture.*mock', 'Pytest Mock Fixture'),
            (r'monkeypatch\.|mocker\.', 'Pytest Mock Usage'),
            (r'create_autospec\s*\(', 'Mock Autospec'),
            (r'spec\s*=.*Mock', 'Mock Spec'),
            (r'patch\.object\s*\(', 'Patch Object'),
            (r'patch\.dict\s*\(', 'Patch Dict'),
            (r'mock_open\s*\(', 'Mock Open'),
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern, violation_type in mock_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(MockViolation(
                        file_path=str(py_file),
                        line_number=line_num,
                        violation_type=f"Regex {violation_type}",
                        code_snippet=line.strip()[:100],
                        service=self._get_service_name_from_path(str(py_file))
                    ))
        
        return violations
    
    def _get_service_name_from_path(self, file_path: str) -> str:
        """Determine service name from file path."""
        if '/auth_service/' in file_path:
            return 'auth_service'
        elif '/analytics_service/' in file_path:
            return 'analytics_service'
        elif '/netra_backend/' in file_path:
            return 'netra_backend'
        elif '/frontend/' in file_path:
            return 'frontend'
        elif '/dev_launcher/' in file_path:
            return 'dev_launcher'
        else:
            return 'tests'
    
    def test_no_mock_imports_in_auth_service(self):
        """
        CRITICAL: auth_service tests must not use mocks.
        
        Policy: Real service testing only
        Violation: 23 test files currently using mocks
        Impact: False authentication test confidence
        """
        auth_tests = self.project_root / 'auth_service' / 'tests'
        violations = self.scan_for_mock_usage(auth_tests)
        
        if violations:
            report = "\n\nMock Policy Violations in auth_service:\n"
            report += "=" * 60 + "\n"
            for v in violations[:10]:  # Show first 10 violations
                report += f"  ❌ {v}\n"
            if len(violations) > 10:
                report += f"  ... and {len(violations) - 10} more violations\n"
            report += "\nRequired Action: Replace ALL mocks with real service tests\n"
            report += "Use IsolatedEnvironment from test_framework/environment_isolation.py\n"
            
            pytest.fail(f"{report}\nTotal violations: {len(violations)}")
    
    def test_no_mock_imports_in_analytics_service(self):
        """
        CRITICAL: analytics_service tests must not use mocks.
        
        Policy: Real service testing only
        Violation: 136 mock instances across 6 files
        Impact: Hidden analytics integration failures
        """
        analytics_tests = self.project_root / 'analytics_service' / 'tests'
        violations = self.scan_for_mock_usage(analytics_tests)
        
        if violations:
            report = "\n\nMock Policy Violations in analytics_service:\n"
            report += "=" * 60 + "\n"
            for v in violations[:10]:
                report += f"  ❌ {v}\n"
            if len(violations) > 10:
                report += f"  ... and {len(violations) - 10} more violations\n"
            report += "\nRequired Action: Use real ClickHouse/Redis for testing\n"
            
            pytest.fail(f"{report}\nTotal violations: {len(violations)}")
    
    def test_no_mock_imports_in_netra_backend(self):
        """
        CRITICAL: netra_backend tests must not use mocks.
        
        Policy: Real service testing only
        Violation: 20+ test files using mocks
        Impact: WebSocket and agent failures not detected
        """
        backend_tests = self.project_root / 'netra_backend' / 'tests'
        violations = self.scan_for_mock_usage(backend_tests)
        
        if violations:
            report = "\n\nMock Policy Violations in netra_backend:\n"
            report += "=" * 60 + "\n"
            for v in violations[:10]:
                report += f"  ❌ {v}\n"
            if len(violations) > 10:
                report += f"  ... and {len(violations) - 10} more violations\n"
            report += "\nRequired Action: Use real WebSocket connections and databases\n"
            
            pytest.fail(f"{report}\nTotal violations: {len(violations)}")
    
    def test_comprehensive_mock_audit(self):
        """
        COMPREHENSIVE: Full platform mock usage audit.
        
        This test scans ALL test directories and provides a complete
        violation report across all services.
        """
        all_violations = []
        service_violations = defaultdict(list)
        
        for test_dir in self.test_directories:
            if test_dir.exists():
                violations = self.scan_for_mock_usage(test_dir)
                all_violations.extend(violations)
                for v in violations:
                    service_violations[v.service].append(v)
        
        if all_violations:
            report = "\n" + "=" * 80 + "\n"
            report += "COMPREHENSIVE MOCK POLICY VIOLATION REPORT\n"
            report += "=" * 80 + "\n\n"
            report += f"Total Violations: {len(all_violations)}\n"
            report += f"Services Affected: {len(service_violations)}\n\n"
            
            for service, violations in service_violations.items():
                report += f"\n{service.upper()} ({len(violations)} violations):\n"
                report += "-" * 40 + "\n"
                
                # Group by violation type
                by_type = defaultdict(list)
                for v in violations:
                    by_type[v.violation_type].append(v)
                
                for vtype, vlist in by_type.items():
                    report += f"  {vtype}: {len(vlist)} occurrences\n"
                    for v in vlist[:3]:  # Show first 3 of each type
                        report += f"    • {v.file_path.split('/netra-apex/')[-1]}:{v.line_number}\n"
                    if len(vlist) > 3:
                        report += f"    ... and {len(vlist) - 3} more\n"
            
            report += "\n" + "=" * 80 + "\n"
            report += "REQUIRED ACTIONS:\n"
            report += "1. Replace ALL mocks with real service tests\n"
            report += "2. Use IsolatedEnvironment for test isolation\n"
            report += "3. Use docker-compose for service dependencies\n"
            report += "4. Implement real WebSocket/database connections\n"
            report += "=" * 80 + "\n"
            
            pytest.fail(report)
    
    def test_isolated_environment_usage(self):
        """
        Verify tests use IsolatedEnvironment instead of direct os.environ.
        
        Policy: All environment access through IsolatedEnvironment
        Impact: Test pollution and flaky tests
        """
        violations = []
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            for py_file in test_dir.rglob('*.py'):
                if py_file.name == 'test_mock_policy_violations.py':
                    continue
                    
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for direct os.environ access
                    if 'os.environ[' in content or 'os.environ.get(' in content:
                        # Count occurrences
                        count = content.count('os.environ[') + content.count('os.environ.get(')
                        violations.append((str(py_file), count))
                        
                except Exception as e:
                    print(f"Warning: Could not read {py_file}: {e}")
                    
        if violations:
            report = "\n\nDirect os.environ Access Violations:\n"
            report += "=" * 60 + "\n"
            for file_path, count in violations[:10]:
                short_path = file_path.split('/netra-apex/')[-1]
                report += f"  ❌ {short_path}: {count} occurrences\n"
            if len(violations) > 10:
                report += f"  ... and {len(violations) - 10} more files\n"
            report += "\nRequired: Use IsolatedEnvironment from test_framework\n"
            
            pytest.fail(report)
    
    def test_real_service_configuration(self):
        """
        Verify tests are configured to use real services.
        
        Policy: Real databases, real Redis, real services
        Impact: Integration issues not caught by tests
        """
        required_patterns = {
            'IsolatedEnvironment': 'Using IsolatedEnvironment for test isolation',
            'docker-compose': 'Using docker-compose for service dependencies',
            'USE_MEMORY_DB': 'Using real SQLite for database tests',
            'TESTING.*=.*1': 'Setting TESTING environment flag',
        }
        
        missing_patterns = defaultdict(list)
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            service_name = test_dir.parent.name
            
            # Check if conftest.py has proper setup
            conftest = test_dir / 'conftest.py'
            if conftest.exists():
                with open(conftest, 'r') as f:
                    content = f.read()
                    
                for pattern, description in required_patterns.items():
                    if not re.search(pattern, content):
                        missing_patterns[service_name].append(description)
        
        if missing_patterns:
            report = "\n\nReal Service Configuration Missing:\n"
            report += "=" * 60 + "\n"
            for service, missing in missing_patterns.items():
                report += f"\n{service}:\n"
                for item in missing:
                    report += f"  ❌ Missing: {item}\n"
            report += "\nRequired: Configure tests to use real services\n"
            
            # This is a warning, not a failure yet
            print(report)
    
    def test_mock_free_test_examples(self):
        """
        Verify existence of mock-free test examples.
        
        Each service should have at least one example of proper
        real service testing without mocks.
        """
        good_examples = []
        
        # Look for test files that don't use mocks
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            for py_file in test_dir.rglob('test_*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check if file uses IsolatedEnvironment and no mocks
                    has_isolated_env = 'IsolatedEnvironment' in content or 'isolated_test_env' in content
                    has_no_mocks = not any(mock in content for mock in [
                        'Mock(', 'MagicMock(', 'AsyncMock(', 'patch(',
                        'from unittest.mock', 'from mock import'
                    ])
                    
                    if has_isolated_env and has_no_mocks:
                        good_examples.append(str(py_file))
                        
                except Exception:
                    continue
        
        if len(good_examples) < 5:
            report = "\n\nInsufficient Mock-Free Test Examples:\n"
            report += "=" * 60 + "\n"
            report += f"Found only {len(good_examples)} mock-free test files\n"
            report += "Each service needs proper examples of real service testing\n"
            
            if good_examples:
                report += "\nGood examples found:\n"
                for example in good_examples:
                    short_path = example.split('/netra-apex/')[-1]
                    report += f"  ✅ {short_path}\n"
            
            # This is informational
            print(report)
    
    def test_generate_remediation_report(self):
        """
        Generate detailed remediation report for mock removal.
        
        This test always passes but generates a report file
        with specific remediation steps for each service.
        """
        report_path = self.project_root / 'MOCK_REMEDIATION_PLAN.md'
        
        all_violations = []
        service_violations = defaultdict(list)
        
        for test_dir in self.test_directories:
            if test_dir.exists():
                violations = self.scan_for_mock_usage(test_dir)
                all_violations.extend(violations)
                for v in violations:
                    service_violations[v.service].append(v)
        
        # Generate remediation plan
        with open(report_path, 'w') as f:
            f.write("# Mock Usage Remediation Plan\n\n")
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Violations**: {len(all_violations)}\n")
            f.write(f"- **Services Affected**: {len(service_violations)}\n")
            f.write("- **Estimated Effort**: 2-3 days with multi-agent approach\n\n")
            
            f.write("## Remediation Strategy\n\n")
            f.write("1. Use multi-agent team (3-7 agents) per service\n")
            f.write("2. Replace mocks with real service connections\n")
            f.write("3. Use IsolatedEnvironment for test isolation\n")
            f.write("4. Implement docker-compose for service dependencies\n\n")
            
            f.write("## Service-Specific Plans\n\n")
            
            for service, violations in service_violations.items():
                f.write(f"### {service}\n\n")
                f.write(f"**Violations**: {len(violations)}\n\n")
                
                # Group by file
                by_file = defaultdict(list)
                for v in violations:
                    by_file[v.file_path].append(v)
                
                f.write("**Files to Fix**:\n\n")
                for file_path, file_violations in list(by_file.items())[:10]:
                    short_path = file_path.split('/netra-apex/')[-1]
                    f.write(f"- `{short_path}` ({len(file_violations)} violations)\n")
                
                if len(by_file) > 10:
                    f.write(f"- ... and {len(by_file) - 10} more files\n")
                
                f.write("\n**Replacement Strategy**:\n\n")
                if service == 'auth_service':
                    f.write("- Replace AsyncMock with real PostgreSQL connections\n")
                    f.write("- Use real Redis for session management\n")
                    f.write("- Implement real JWT validation\n")
                elif service == 'analytics_service':
                    f.write("- Use real ClickHouse connections\n")
                    f.write("- Implement real event processing\n")
                    f.write("- Use docker-compose for ClickHouse setup\n")
                elif service == 'netra_backend':
                    f.write("- Replace WebSocket mocks with real connections\n")
                    f.write("- Use real agent execution\n")
                    f.write("- Implement real database connections\n")
                
                f.write("\n---\n\n")
            
            f.write("## Implementation Order\n\n")
            f.write("1. **Phase 1**: auth_service (highest risk)\n")
            f.write("2. **Phase 2**: netra_backend (WebSocket critical)\n")
            f.write("3. **Phase 3**: analytics_service\n")
            f.write("4. **Phase 4**: Integration tests\n\n")
            
            f.write("## Success Criteria\n\n")
            f.write("- [ ] All mock imports removed\n")
            f.write("- [ ] All tests use IsolatedEnvironment\n")
            f.write("- [ ] Docker-compose configured for dependencies\n")
            f.write("- [ ] All tests pass with real services\n")
            f.write("- [ ] Architecture compliance > 90%\n")
        
        print(f"\n✅ Remediation plan generated: {report_path}")


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v', '--tb=short'])