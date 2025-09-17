"
SSOT Test Infrastructure Violations Test Suite

Detects test infrastructure conflicts that violate Single Source of Truth principles.
This test is designed to FAIL initially to detect current violations (70+ expected conflicts).

Business Value: Platform/Internal - System Stability & Development Velocity
Validates SSOT test infrastructure compliance to eliminate conftest.py conflicts and fixture duplication.

Test Strategy:
1. Scan entire codebase for duplicate conftest.py files
2. Identify conflicting fixture definitions across modules
3. Flag pytest configuration conflicts
4. Detect test runner duplication patterns

Expected Initial Results: FAILING (detecting current violations)
Target State: PASSING (all test infrastructure uses SSOT patterns)

Compliance Rules:
- ONLY test_framework/ssot/conftest_*.py files allowed for global fixtures
- NO duplicate conftest.py files across services
- ALL test execution MUST use tests/unified_test_runner.py
- NO ad-hoc pytest.ini or setup.cfg configurations
- ALL fixtures MUST be centralized through SSOT conftest files
"

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
import configparser
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class InfrastructureViolationTests:
    "Represents a detected test infrastructure violation.
    file_path: str
    line_number: Optional[int]
    violation_type: str  # DUPLICATE_CONFTEST, FIXTURE_CONFLICT, CONFIG_CONFLICT, RUNNER_DUPLICATION
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    recommended_fix: str


@dataclass
class FixtureDefinition:
    "Represents a pytest fixture definition."
    name: str
    file_path: str
    line_number: int
    scope: str
    parameters: List[str]


class SSOTTestInfrastructureViolationsTests(SSotBaseTestCase):
    "
    Mission Critical test suite to detect and validate SSOT test infrastructure compliance.
    
    This test is designed to FAIL initially to expose current violations,
    providing actionable remediation targets for SSOT infrastructure consolidation.
"
    
    def setup_method(self, method):
        Set up test environment.""
        super().setup_method(method)
        self.project_root = Path(/Users/anthony/Desktop/netra-apex)
        self.violations = []
        
        # SSOT conftest files (authorized)
        self.authorized_conftest_files = {
            'test_framework/ssot/conftest_base.py',
            'test_framework/ssot/conftest_real_services.py', 
            'test_framework/ssot/conftest_websocket.py',
            'test_framework/ssot/conftest_database.py',
        }
        
        # Known fixture conflicts to detect
        self.common_fixture_names = [
            'mock_agent',
            'mock_websocket', 
            'mock_database_session',
            'test_client',
            'event_loop',
            'isolated_environment',
            'docker_manager',
        ]
        
    def test_detect_duplicate_conftest_files(self):
    ""
        CRITICAL: Detect duplicate conftest.py files across services.
        
        Expected violations: 20+ duplicate conftest.py files
        Target: Only SSOT conftest files in test_framework/ssot/
        
        conftest_files = self._find_all_conftest_files()
        
        # Filter out authorized SSOT conftest files
        unauthorized_conftest = []
        for conftest_path in conftest_files:
            relative_path = str(conftest_path.relative_to(self.project_root))
            if not any(authorized in relative_path for authorized in self.authorized_conftest_files):
                unauthorized_conftest.append(conftest_path)
                
        violation_count = len(unauthorized_conftest)
        
        if violation_count > 0:
            violation_details = []
            for conftest_path in unauthorized_conftest[:15]:  # Show first 15
                violation_details.append(f  - {conftest_path}")"
                
            if len(unauthorized_conftest) > 15:
                violation_details.append(f  ... and {len(unauthorized_conftest) - 15} more conftest.py files)
                
            pytest.fail(
                fDETECTED {violation_count} duplicate conftest.py SSOT violations.\n
                f"ONLY SSOT conftest files in test_framework/ssot/ are authorized.\n\n
                fUnauthorized conftest.py files:\n + \n.join(violation_details) + \n\n"
                fAUTHORIZED SSOT CONFTEST FILES:\n + 
                \n.join(f"  ✓ {auth} for auth in self.authorized_conftest_files) + \n\n"
                fREMEDIATION:\n
                f1. Move fixtures to appropriate SSOT conftest file\n
                f"2. Remove duplicate conftest.py files\n
                f3. Update imports to use SSOT fixtures"
            )
            
    def test_detect_fixture_definition_conflicts(self):
    "
        HIGH: Detect conflicting fixture definitions across modules.
        
        Expected violations: 25+ fixture conflicts
        Target: All fixtures centralized in SSOT conftest files
        "
        fixture_conflicts = self._find_fixture_conflicts()
        
        violation_count = sum(len(conflicts) for conflicts in fixture_conflicts.values())
        
        if violation_count > 0:
            conflict_details = []
            for fixture_name, conflicts in fixture_conflicts.items():
                if len(conflicts) > 1:  # Only report actual conflicts
                    conflict_details.append(f  FIXTURE '{fixture_name}' defined in {len(conflicts)} locations:)
                    for conflict in conflicts:
                        conflict_details.append(f"    - {conflict.file_path}:{conflict.line_number})
                        
            pytest.fail(
                fDETECTED {violation_count} fixture definition SSOT violations.\n"
                fAll fixtures MUST be centralized in SSOT conftest files.\n\n
                fConflicting fixtures:\n + \n.join(conflict_details) + \n\n"
                f"REMEDIATION:\n
                f1. Consolidate duplicate fixtures into single SSOT definition\n
                f2. Move fixtures to appropriate test_framework/ssot/conftest_*.py\n
                f3. Remove duplicate fixture definitions from local conftest files""
            )
            
    def test_detect_pytest_configuration_conflicts(self):

        MEDIUM: Detect conflicting pytest configuration files.
        
        Expected violations: 15+ configuration conflicts
        Target: Single pytest.ini configuration in project root
        ""
        config_conflicts = self._find_pytest_config_conflicts()
        
        violation_count = len(config_conflicts)
        
        if violation_count > 0:
            conflict_details = []
            for violation in config_conflicts:
                conflict_details.append(f  - {violation.file_path}: {violation.description})
                
            pytest.fail(
                fDETECTED {violation_count} pytest configuration SSOT violations.\n
                fONLY single pytest.ini in project root is authorized.\n\n""
                fConfiguration conflicts:\n + \n.join(conflict_details) + \n\n
                fREMEDIATION:\n""
                f1. Consolidate all pytest configuration into project root pytest.ini\n
                f2. Remove duplicate setup.cfg [tool:pytest] sections\n
                f"3. Remove pyproject.toml [tool.pytest] configurations\n
                f4. Ensure consistent test discovery patterns"
            )
            
    def test_detect_test_runner_duplication(self):
    "
        MEDIUM: Detect duplicate test runner implementations.
        
        Expected violations: 10+ test runner duplicates
        Target: Only tests/unified_test_runner.py authorized
        "
        test_runner_violations = self._find_test_runner_duplicates()
        
        violation_count = len(test_runner_violations)
        
        if violation_count > 0:
            violation_details = []
            for violation in test_runner_violations:
                violation_details.append(f  - {violation.file_path}: {violation.description})
                
            pytest.fail(
                f"DETECTED {violation_count} test runner duplication SSOT violations.\n
                fONLY tests/unified_test_runner.py is authorized for test execution.\n\n"
                fDuplicate test runners:\n + \n.join(violation_details) + \n\n"
                fREMEDIATION:\n"
                f1. Remove duplicate test runner scripts\n
                f2. Update all scripts to use tests/unified_test_runner.py\n"
                f"3. Migrate custom test execution logic to unified runner\n
                f4. Update CI/CD to use single SSOT test runner
            )
            
    def test_detect_direct_pytest_execution_patterns(self):
    ""
        LOW: Detect direct pytest execution bypassing SSOT runner.
        
        Expected violations: 10+ direct pytest calls
        Target: All test execution through unified_test_runner.py
        
        direct_pytest_violations = self._find_direct_pytest_patterns()
        
        violation_count = len(direct_pytest_violations)
        
        if violation_count > 0:
            violation_details = []
            for violation in direct_pytest_violations:
                violation_details.append(f  - {violation.file_path}:{violation.line_number}: {violation.description})"
                
            pytest.fail(
                f"DETECTED {violation_count} direct pytest execution SSOT violations.\n
                fAll test execution MUST use tests/unified_test_runner.py.\n\n
                fDirect pytest calls:\n + \n.join(violation_details) + "\n\n"
                fREMEDIATION:\n
                fReplace: pytest path/to/tests\n
                fWith: python tests/unified_test_runner.py --path path/to/tests\n\n""
                fReplace: python -m pytest\n
                fWith: python tests/unified_test_runner.py
            )
            
    def test_comprehensive_infrastructure_violation_report(self):
    ""
        Generate comprehensive SSOT test infrastructure violation report.
        
        This test provides actionable intelligence for SSOT infrastructure remediation.
        
        all_violations = []
        
        # Collect conftest violations
        conftest_files = self._find_all_conftest_files()
        for conftest_path in conftest_files:
            relative_path = str(conftest_path.relative_to(self.project_root))
            if not any(authorized in relative_path for authorized in self.authorized_conftest_files):
                all_violations.append(InfrastructureViolationTests(
                    file_path=str(conftest_path),
                    line_number=None,
                    violation_type='DUPLICATE_CONFTEST',
                    severity='CRITICAL',
                    description='Unauthorized conftest.py file',
                    recommended_fix='Move fixtures to SSOT conftest files'
                ))
                
        # Collect fixture conflicts
        fixture_conflicts = self._find_fixture_conflicts()
        for fixture_name, conflicts in fixture_conflicts.items():
            if len(conflicts) > 1:
                for conflict in conflicts[1:]:  # Skip first as reference
                    all_violations.append(InfrastructureViolationTests(
                        file_path=conflict.file_path,
                        line_number=conflict.line_number,
                        violation_type='FIXTURE_CONFLICT',
                        severity='HIGH',
                        description=f'Duplicate fixture: {fixture_name}',
                        recommended_fix='Consolidate into SSOT fixture'
                    ))
                    
        # Collect config conflicts
        config_conflicts = self._find_pytest_config_conflicts()
        all_violations.extend(config_conflicts)
        
        # Collect runner duplicates
        runner_violations = self._find_test_runner_duplicates()
        all_violations.extend(runner_violations)
        
        # Collect direct pytest patterns
        pytest_violations = self._find_direct_pytest_patterns()
        all_violations.extend(pytest_violations)
        
        total_violations = len(all_violations)
        
        # Generate detailed report
        violation_by_type = {}
        violation_by_severity = {}
        
        for violation in all_violations:
            # Count by type
            if violation.violation_type not in violation_by_type:
                violation_by_type[violation.violation_type] = 0
            violation_by_type[violation.violation_type] += 1
            
            # Count by severity
            if violation.severity not in violation_by_severity:
                violation_by_severity[violation.severity] = 0
            violation_by_severity[violation.severity] += 1
            
        report = f"
SSOT TEST INFRASTRUCTURE VIOLATIONS REPORT
==========================================

TOTAL VIOLATIONS: {total_violations}
TARGET REDUCTION: {total_violations} violations → 0 violations

VIOLATIONS BY TYPE:
{self._format_violation_counts(violation_by_type)}

VIOLATIONS BY SEVERITY:
{self._format_violation_counts(violation_by_severity)}

REMEDIATION PRIORITY:
1. CRITICAL: Duplicate conftest files ({violation_by_severity.get('CRITICAL', 0)} violations)
2. HIGH: Fixture conflicts ({violation_by_severity.get('HIGH', 0)} violations)
3. MEDIUM: Config/runner conflicts ({violation_by_severity.get('MEDIUM', 0)} violations)
4. LOW: Direct pytest usage ({violation_by_severity.get('LOW', 0)} violations)

BUSINESS IMPACT:
- Test Reliability: Eliminate fixture conflicts causing test failures
- Developer Experience: Reduce confusion about test infrastructure
- Maintenance Overhead: Centralize test configuration for easier updates
- CI/CD Stability: Ensure consistent test execution across environments

SSOT TARGET STATE:
- Single unified_test_runner.py for all test execution
- Centralized fixtures in test_framework/ssot/conftest_*.py
- Single pytest.ini configuration in project root
- Zero duplicate test infrastructure components
"
        
        # This test SHOULD FAIL to provide actionable violation report
        if total_violations > 0:
            pytest.fail(fSSOT Test Infrastructure Violation Report:\n{report})
            
    def _find_all_conftest_files(self) -> List[Path]:
        ""Find all conftest.py files in the project.
        conftest_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            if 'conftest.py' in files:
                conftest_files.append(Path(root) / 'conftest.py')
                
        return conftest_files
        
    def _find_fixture_conflicts(self) -> Dict[str, List[FixtureDefinition]]:
        Find conflicting fixture definitions.""
        fixtures_by_name = {}
        
        conftest_files = self._find_all_conftest_files()
        
        for conftest_file in conftest_files:
            try:
                with open(conftest_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Parse with AST to find fixture decorators
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            for decorator in node.decorator_list:
                                if self._is_pytest_fixture_decorator(decorator):
                                    fixture_name = node.name
                                    if fixture_name not in fixtures_by_name:
                                        fixtures_by_name[fixture_name] = []
                                        
                                    fixtures_by_name[fixture_name].append(FixtureDefinition(
                                        name=fixture_name,
                                        file_path=str(conftest_file),
                                        line_number=node.lineno,
                                        scope=self._extract_fixture_scope(decorator),
                                        parameters=[arg.arg for arg in node.args.args])
                                    
                except (SyntaxError, UnicodeDecodeError):
                    # Skip files with syntax errors
                    continue
                    
            except Exception as e:
                continue
                
        return fixtures_by_name
        
    def _is_pytest_fixture_decorator(self, decorator) -> bool:
        Check if decorator is a pytest fixture.""
        if isinstance(decorator, ast.Name):
            return decorator.id == 'fixture'
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id == 'fixture'
            elif isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr == 'fixture'
        return False
        
    def _extract_fixture_scope(self, decorator) -> str:
        Extract fixture scope from decorator."
        if isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if keyword.arg == 'scope':
                    if isinstance(keyword.value, ast.Str):
                        return keyword.value.s
        return 'function'
        
    def _find_pytest_config_conflicts(self) -> List[InfrastructureViolationTests]:
        "Find conflicting pytest configuration files.
        violations = []
        
        # Look for pytest.ini files
        pytest_ini_files = list(self.project_root.rglob('pytest.ini'))
        if len(pytest_ini_files) > 1:
            for pytest_ini in pytest_ini_files[1:]:  # Skip first as reference
                violations.append(InfrastructureViolationTests(
                    file_path=str(pytest_ini),
                    line_number=None,
                    violation_type='CONFIG_CONFLICT',
                    severity='MEDIUM',
                    description='Duplicate pytest.ini configuration',
                    recommended_fix='Consolidate into project root pytest.ini'
                ))
                
        # Look for setup.cfg with pytest sections
        setup_cfg_files = list(self.project_root.rglob('setup.cfg'))
        for setup_cfg in setup_cfg_files:
            try:
                config = configparser.ConfigParser()
                config.read(setup_cfg)
                if 'tool:pytest' in config.sections():
                    violations.append(InfrastructureViolationTests(
                        file_path=str(setup_cfg),
                        line_number=None,
                        violation_type='CONFIG_CONFLICT',
                        severity='MEDIUM',
                        description='setup.cfg contains pytest configuration',
                        recommended_fix='Move pytest config to pytest.ini'
                    ))
            except Exception:
                continue
                
        # Look for pyproject.toml with pytest sections
        pyproject_files = list(self.project_root.rglob('pyproject.toml'))
        for pyproject_file in pyproject_files:
            try:
                with open(pyproject_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '[tool.pytest' in content:
                        violations.append(InfrastructureViolationTests(
                            file_path=str(pyproject_file),
                            line_number=None,
                            violation_type='CONFIG_CONFLICT',
                            severity='MEDIUM',
                            description='pyproject.toml contains pytest configuration',
                            recommended_fix='Move pytest config to pytest.ini'
                        ))
            except Exception:
                continue
                
        return violations
        
    def _find_test_runner_duplicates(self) -> List[InfrastructureViolationTests]:
        "Find duplicate test runner implementations."
        violations = []
        
        # Look for test runner patterns
        runner_patterns = [
            r'test.*runner.*\.py$',
            r'run.*test.*\.py$',
            r'pytest.*runner.*\.py$',
        ]
        
        for pattern in runner_patterns:
            for file_path in self.project_root.rglob('*.py'):
                if re.search(pattern, file_path.name, re.IGNORECASE):
                    # Skip the authorized unified test runner
                    if 'unified_test_runner.py' in file_path.name:
                        continue
                        
                    violations.append(InfrastructureViolationTests(
                        file_path=str(file_path),
                        line_number=None,
                        violation_type='RUNNER_DUPLICATION',
                        severity='MEDIUM',
                        description=f'Duplicate test runner: {file_path.name}',
                        recommended_fix='Use tests/unified_test_runner.py instead'
                    ))
                    
        return violations
        
    def _find_direct_pytest_patterns(self) -> List[InfrastructureViolationTests]:
        "Find direct pytest execution patterns."
        violations = []
        
        # Scan script files for direct pytest calls
        script_dirs = [
            self.project_root / scripts,
            self.project_root / .github","
            self.project_root / tests,
        ]
        
        pytest_patterns = [
            r'pytest\s+',
            r'python\s+-m\s+pytest',
            r'py\.test\s+',
        ]
        
        for script_dir in script_dirs:
            if script_dir.exists():
                for file_path in script_dir.rglob('*'):
                    if file_path.suffix in ['.py', '.sh', '.yml', '.yaml']:
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                
                            for line_num, line in enumerate(content.splitlines(), 1):
                                for pattern in pytest_patterns:
                                    if re.search(pattern, line):
                                        violations.append(InfrastructureViolationTests(
                                            file_path=str(file_path),
                                            line_number=line_num,
                                            violation_type='DIRECT_PYTEST',
                                            severity='LOW',
                                            description=f'Direct pytest execution: {line.strip()}',
                                            recommended_fix='Use tests/unified_test_runner.py'
                                        ))
                                        
                        except Exception:
                            continue
                            
        return violations
        
    def _format_violation_counts(self, violation_counts: Dict[str, int] -> str:
        "Format violation counts."
        formatted = []
        for violation_type, count in sorted(violation_counts.items(), key=lambda x: x[1], reverse=True):
            formatted.append(f- {violation_type}: {count} violations)
        return \n.join(formatted)"