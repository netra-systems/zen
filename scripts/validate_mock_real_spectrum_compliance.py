"""Validation script for Mock-Real Spectrum compliance.

This script validates that database tests comply with testing.xml Mock-Real Spectrum
requirements, ensuring proper use of L3 real containers vs justified L1 mocks.

Usage:
    python scripts/validate_mock_real_spectrum_compliance.py
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class MockViolation:
    """Represents a mock usage violation."""
    file_path: str
    line_number: int
    function_name: str
    mock_type: str
    violation_type: str
    description: str
    suggested_fix: str


@dataclass 
class ComplianceReport:
    """Mock-Real Spectrum compliance report."""
    total_files_scanned: int
    violation_count: int
    justified_mocks: int
    l3_integration_tests: int
    violations: List[MockViolation]
    compliant_files: List[str]


class MockRealSpectrumValidator:
    """Validates Mock-Real Spectrum compliance according to testing.xml."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.database_mock_patterns = [
            r'@patch.*db_manager',
            r'@patch.*database_manager',
            r'@patch.*postgres',
            r'@patch.*clickhouse',
            r'@patch.*redis',
            r'Mock.*Database',
            r'Mock.*Session',
            r'AsyncMock.*engine',
        ]
        self.justified_decorator_pattern = r'@mock_justified\s*\('
        self.integration_test_patterns = [
            'testcontainers',
            'PostgresContainer', 
            'RedisContainer',
            'ClickHouseContainer',
            'real.*database',
            'real.*postgres',
            'real.*redis'
        ]
    
    def scan_test_files(self) -> List[Path]:
        """Scan for test files to analyze."""
        test_files = []
        
        # Scan test directories
        for test_dir in ['netra_backend/tests', 'auth_service/tests', 'tests']:
            test_path = self.project_root / test_dir
            if test_path.exists():
                test_files.extend(test_path.rglob('test_*.py'))
        
        return test_files
    
    def analyze_file(self, file_path: Path) -> Tuple[List[MockViolation], bool, bool]:
        """Analyze a single test file for Mock-Real Spectrum compliance."""
        violations = []
        has_justified_mocks = False
        has_l3_patterns = False
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()
            
            # Check for L3 integration patterns
            has_l3_patterns = any(
                re.search(pattern, content, re.IGNORECASE) 
                for pattern in self.integration_test_patterns
            )
            
            # Parse AST to find mock usage
            try:
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        self._analyze_function(node, lines, file_path, violations)
                        
                        # Check for @mock_justified decorator
                        for decorator in node.decorator_list:
                            if self._is_mock_justified_decorator(decorator):
                                has_justified_mocks = True
                
            except SyntaxError:
                # Skip files with syntax errors
                pass
                
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
        
        return violations, has_justified_mocks, has_l3_patterns
    
    def _analyze_function(self, node: ast.FunctionDef, lines: List[str], 
                         file_path: Path, violations: List[MockViolation]):
        """Analyze a function for mock usage violations."""
        function_name = node.name
        
        # Skip if function has @mock_justified decorator
        has_justification = any(
            self._is_mock_justified_decorator(decorator) 
            for decorator in node.decorator_list
        )
        
        if has_justification:
            return  # Justified mocks are allowed
        
        # Check for database mocks in decorators and function body
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'attr'):
                if decorator.func.attr == 'patch':
                    patch_target = self._get_patch_target(decorator)
                    if patch_target and self._is_database_mock(patch_target):
                        violations.append(MockViolation(
                            file_path=str(file_path),
                            line_number=decorator.lineno,
                            function_name=function_name,
                            mock_type=f"@patch({patch_target})",
                            violation_type="UNJUSTIFIED_DATABASE_MOCK",
                            description=f"Database mock without @mock_justified decorator",
                            suggested_fix="Add @mock_justified decorator with L1/L3 justification"
                        ))
        
        # Check function body for Mock() usage
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if hasattr(child.func, 'id') and 'Mock' in child.func.id:
                    line_no = getattr(child, 'lineno', node.lineno)
                    if line_no < len(lines):
                        line_content = lines[line_no - 1]
                        if any(pattern in line_content.lower() for pattern in 
                               ['database', 'db', 'postgres', 'redis', 'clickhouse']):
                            violations.append(MockViolation(
                                file_path=str(file_path),
                                line_number=line_no,
                                function_name=function_name,
                                mock_type="Mock() instantiation",
                                violation_type="UNJUSTIFIED_DATABASE_MOCK",
                                description="Database mock without justification",
                                suggested_fix="Use real containers (L3) or add @mock_justified decorator"
                            ))
    
    def _is_mock_justified_decorator(self, decorator) -> bool:
        """Check if decorator is @mock_justified."""
        if isinstance(decorator, ast.Call):
            if hasattr(decorator.func, 'id') and decorator.func.id == 'mock_justified':
                return True
        elif isinstance(decorator, ast.Name):
            if decorator.id == 'mock_justified':
                return True
        return False
    
    def _get_patch_target(self, decorator) -> str:
        """Extract patch target from @patch decorator."""
        if isinstance(decorator, ast.Call) and decorator.args:
            if isinstance(decorator.args[0], ast.Str):
                return decorator.args[0].s
            elif isinstance(decorator.args[0], ast.Constant):
                return decorator.args[0].value
        return ""
    
    def _is_database_mock(self, patch_target: str) -> bool:
        """Check if patch target is a database-related mock."""
        return any(
            re.search(pattern, patch_target, re.IGNORECASE)
            for pattern in self.database_mock_patterns
        )
    
    def validate_compliance(self) -> ComplianceReport:
        """Run complete Mock-Real Spectrum compliance validation."""
        test_files = self.scan_test_files()
        
        all_violations = []
        justified_mock_count = 0
        l3_test_count = 0
        compliant_files = []
        
        print(f"Scanning {len(test_files)} test files for Mock-Real Spectrum compliance...")
        
        for file_path in test_files:
            violations, has_justified, has_l3 = self.analyze_file(file_path)
            
            all_violations.extend(violations)
            
            if has_justified:
                justified_mock_count += 1
            
            if has_l3:
                l3_test_count += 1
            
            if not violations:
                compliant_files.append(str(file_path))
        
        return ComplianceReport(
            total_files_scanned=len(test_files),
            violation_count=len(all_violations),
            justified_mocks=justified_mock_count,
            l3_integration_tests=l3_test_count,
            violations=all_violations,
            compliant_files=compliant_files
        )
    
    def generate_report(self, report: ComplianceReport) -> str:
        """Generate human-readable compliance report."""
        lines = [
            "=" * 80,
            "MOCK-REAL SPECTRUM COMPLIANCE REPORT",
            "=" * 80,
            f"Files Scanned: {report.total_files_scanned}",
            f"Violations Found: {report.violation_count}",
            f"Files with Justified Mocks: {report.justified_mocks}",
            f"L3 Integration Test Files: {report.l3_integration_tests}",
            f"Compliant Files: {len(report.compliant_files)}",
            "",
            f"Compliance Rate: {((report.total_files_scanned - len([v for v in report.violations if v.file_path not in [f for f in report.compliant_files]])) / report.total_files_scanned * 100):.1f}%",
            ""
        ]
        
        if report.violations:
            lines.extend([
                "VIOLATIONS FOUND:",
                "-" * 40
            ])
            
            # Group violations by file
            violations_by_file = {}
            for violation in report.violations:
                if violation.file_path not in violations_by_file:
                    violations_by_file[violation.file_path] = []
                violations_by_file[violation.file_path].append(violation)
            
            for file_path, violations in violations_by_file.items():
                lines.append(f"\n{file_path}:")
                for violation in violations:
                    lines.extend([
                        f"  Line {violation.line_number} in {violation.function_name}():",
                        f"    Mock Type: {violation.mock_type}",
                        f"    Issue: {violation.description}",
                        f"    Fix: {violation.suggested_fix}",
                        ""
                    ])
        
        if report.l3_integration_tests > 0:
            lines.extend([
                "L3 INTEGRATION TESTS FOUND:",
                "-" * 30,
                f"Found {report.l3_integration_tests} files with L3 real container patterns",
                "These files properly use Testcontainers for L3 realism testing.",
                ""
            ])
        
        lines.extend([
            "RECOMMENDATIONS:",
            "-" * 20,
            "1. Replace unjustified database mocks with L3 real containers using Testcontainers",
            "2. Add @mock_justified decorators to remaining L1 unit test mocks",
            "3. Ensure integration tests use L2 (real internal) or L3 (real containerized) services", 
            "4. Move database connectivity tests to L3 integration test suites",
            "",
            "For more information, see SPEC/testing.xml Mock-Real Spectrum section.",
            "=" * 80
        ])
        
        return "\n".join(lines)


def main():
    """Main validation entry point."""
    project_root = Path(__file__).parent.parent
    validator = MockRealSpectrumValidator(project_root)
    
    print("Running Mock-Real Spectrum compliance validation...")
    print("This validates that database tests use L3 real containers or justified L1 mocks.")
    print()
    
    report = validator.validate_compliance()
    report_text = validator.generate_report(report)
    
    print(report_text)
    
    # Save report to file
    report_file = project_root / "test_reports" / "mock_real_spectrum_compliance.txt"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report_text, encoding='utf-8')
    
    print(f"\nDetailed report saved to: {report_file}")
    
    # Exit with appropriate code
    if report.violation_count > 0:
        print(f"\n FAIL:  COMPLIANCE CHECK FAILED: {report.violation_count} violations found")
        return 1
    else:
        print("\n PASS:  COMPLIANCE CHECK PASSED: No violations found")
        return 0


if __name__ == "__main__":
    exit(main())