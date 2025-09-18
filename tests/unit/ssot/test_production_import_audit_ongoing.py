"""
Test 3: Production Import Audit Test for Ongoing Monitoring (Issue #877)

PURPOSE: Ongoing monitoring to prevent future DeepAgentState SSOT regressions
SCOPE: Scan production files for deprecated imports and provide audit trail

This test should PASS after fix and continue passing to prevent future regressions.
It serves as a monitoring system for SSOT compliance across the entire codebase.

Design:
- Scan all production Python files
- Detect deprecated DeepAgentState imports
- Generate comprehensive audit report
- Monitor compliance over time
"""
import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class ProductionImportAuditOngoingTests(SSotBaseTestCase):
    """Ongoing audit test for production import compliance"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with scan configuration"""
        cls.root_path = Path(__file__).parent.parent.parent.parent
        cls.production_paths = ['netra_backend/app', 'auth_service', 'shared', 'frontend/src']
        cls.deprecated_patterns = {'DeepAgentState': ['netra_backend.app.agents.state', 'from netra_backend.app.schemas.agent_models import DeepAgentState', 'import netra_backend.app.agents.state']}
        cls.ssot_approved = {'DeepAgentState': 'netra_backend.app.schemas.agent_models', 'UserExecutionContext': 'netra_backend.app.services.user_execution_context'}
        cls.excluded_patterns = ['test_*.py', '*_test.py', 'tests/*', 'migrations/*', '__pycache__/*', '*.pyc', 'backup*']

    def test_production_files_discovery(self):
        """Validate production files can be discovered and scanned"""
        production_files = self._discover_production_files()
        self.assertGreater(len(production_files), 100, f'Should find substantial number of production files, found {len(production_files)}')
        key_files = ['netra_backend/app/agents/agent_lifecycle.py', 'netra_backend/app/agents/base_agent.py', 'netra_backend/app/services/user_execution_context.py']
        for key_file in key_files:
            key_path = self.root_path / key_file
            if key_path.exists():
                self.assertIn(str(key_path), [str(f) for f in production_files], f'Key file {key_file} should be included in production scan')

    def test_deprecated_deepagentstate_import_scan(self):
        """
        MONITORING TEST: Scan for deprecated DeepAgentState imports in production

        Expected: PASS after fix (no deprecated imports in production)
        Ongoing: Continue to PASS (prevent future regressions)
        """
        scan_results = self._scan_deprecated_imports()
        audit_report = self._generate_audit_report(scan_results)
        total_violations = sum((len(files) for files in scan_results.values()))
        self.assertEqual(total_violations, 0, f'PRODUCTION IMPORT VIOLATIONS DETECTED:\n{audit_report}\n  - Total violations: {total_violations}\n  - REMEDIATION: Replace deprecated imports with SSOT sources\n  - Issue #877: Production SSOT compliance monitoring failed')

    def test_ssot_import_coverage_validation(self):
        """
        MONITORING TEST: Validate SSOT imports are being used correctly

        Expected: PASS (production files use SSOT imports)
        Ongoing: Monitor SSOT adoption and compliance
        """
        ssot_usage = self._scan_ssot_import_usage()
        user_context_files = ssot_usage.get('UserExecutionContext', [])
        self.assertGreaterEqual(len(user_context_files), 1, f'UserExecutionContext should be used in production files.\n  - Current usage: {len(user_context_files)} files\n  - Files using UserExecutionContext: {user_context_files}\n  - Issue #877: SSOT adoption monitoring')

    def test_agent_lifecycle_specific_compliance(self):
        """
        REGRESSION-SPECIFIC TEST: Monitor agent_lifecycle.py compliance

        Expected: PASS after fix (agent_lifecycle.py uses SSOT imports)
        Ongoing: Ensure agent_lifecycle.py remains compliant
        """
        agent_lifecycle_path = self.root_path / 'netra_backend/app/agents/agent_lifecycle.py'
        if not agent_lifecycle_path.exists():
            self.skipTest('agent_lifecycle.py not found')
        violations = self._scan_file_for_violations(agent_lifecycle_path)
        self.assertEqual(len(violations), 0, f'AGENT_LIFECYCLE.PY SSOT VIOLATIONS:\n  - File: {agent_lifecycle_path}\n  - Violations: {violations}\n  - Issue #877: agent_lifecycle.py must remain SSOT compliant')

    def test_cross_service_import_consistency(self):
        """
        ARCHITECTURAL TEST: Validate import consistency across services

        Expected: PASS (consistent SSOT imports across all services)
        Ongoing: Monitor architectural consistency
        """
        cross_service_analysis = self._analyze_cross_service_imports()
        inconsistencies = []
        for import_name, service_usage in cross_service_analysis.items():
            if len(service_usage) > 1:
                import_paths = set()
                for service, files in service_usage.items():
                    for file_info in files:
                        import_paths.add(file_info.get('import_path', ''))
                if len(import_paths) > 1:
                    inconsistencies.append({'import_name': import_name, 'services': service_usage, 'import_paths': list(import_paths)})
        self.assertEqual(len(inconsistencies), 0, f'CROSS-SERVICE IMPORT INCONSISTENCIES:\n  - Inconsistencies: {inconsistencies}\n  - REMEDIATION: Standardize imports across services\n  - Issue #877: Cross-service SSOT consistency violation')

    def test_future_regression_prevention_monitoring(self):
        """
        PREVENTIVE TEST: Monitor for patterns that could lead to future regressions

        Expected: PASS (no regression-prone patterns)
        Ongoing: Early warning for potential SSOT violations
        """
        risk_patterns = self._scan_regression_risk_patterns()
        high_risk_findings = [finding for finding in risk_patterns if finding['risk_level'] == 'HIGH']
        self.assertEqual(len(high_risk_findings), 0, f'HIGH-RISK REGRESSION PATTERNS DETECTED:\n  - Findings: {high_risk_findings}\n  - PREVENTION: Address patterns before they become violations\n  - Issue #877: Regression prevention monitoring')

    def _discover_production_files(self) -> List[Path]:
        """Discover all production Python files for scanning"""
        production_files = []
        for prod_path in self.production_paths:
            full_path = self.root_path / prod_path
            if full_path.exists():
                if full_path.is_file():
                    if full_path.suffix == '.py':
                        production_files.append(full_path)
                else:
                    for py_file in full_path.rglob('*.py'):
                        if not self._should_exclude_file(py_file):
                            production_files.append(py_file)
        return production_files

    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from audit"""
        file_str = str(file_path)
        exclude_patterns = ['/tests/', '/test_', '_test.py', 'test_*.py', '__pycache__', '.pyc', '/migrations/', '/backup']
        for pattern in exclude_patterns:
            if pattern in file_str:
                return True
        return False

    def _scan_deprecated_imports(self) -> Dict[str, List[Dict[str, Any]]]:
        """Scan production files for deprecated imports"""
        production_files = self._discover_production_files()
        violations = defaultdict(list)
        for file_path in production_files:
            file_violations = self._scan_file_for_violations(file_path)
            if file_violations:
                violations[str(file_path.relative_to(self.root_path))] = file_violations
        return dict(violations)

    def _scan_file_for_violations(self, file_path: Path) -> List[Dict[str, Any]]:
        """Scan single file for deprecated import violations"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return []
        violations = []
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for deprecated_name, patterns in self.deprecated_patterns.items():
                for pattern in patterns:
                    if pattern in line and (not line.strip().startswith('#')):
                        violations.append({'line': line_num, 'content': line.strip(), 'violation_type': f'deprecated_{deprecated_name}_import', 'pattern': pattern})
        return violations

    def _scan_ssot_import_usage(self) -> Dict[str, List[str]]:
        """Scan for SSOT import usage in production"""
        production_files = self._discover_production_files()
        ssot_usage = defaultdict(list)
        for file_path in production_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            for ssot_name, ssot_module in self.ssot_approved.items():
                if f'from {ssot_module} import' in content and ssot_name in content:
                    ssot_usage[ssot_name].append(str(file_path.relative_to(self.root_path)))
        return dict(ssot_usage)

    def _analyze_cross_service_imports(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Analyze import consistency across services"""
        production_files = self._discover_production_files()
        cross_service_analysis = defaultdict(lambda: defaultdict(list))
        for file_path in production_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree = ast.parse(content)
            except Exception:
                continue
            service = self._determine_service(file_path)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for alias in node.names or []:
                        import_info = {'file': str(file_path.relative_to(self.root_path)), 'import_path': node.module, 'line': node.lineno}
                        cross_service_analysis[alias.name][service].append(import_info)
        return dict(cross_service_analysis)

    def _determine_service(self, file_path: Path) -> str:
        """Determine which service a file belongs to"""
        path_str = str(file_path)
        if 'netra_backend' in path_str:
            return 'backend'
        elif 'auth_service' in path_str:
            return 'auth'
        elif 'frontend' in path_str:
            return 'frontend'
        elif 'shared' in path_str:
            return 'shared'
        else:
            return 'unknown'

    def _scan_regression_risk_patterns(self) -> List[Dict[str, Any]]:
        """Scan for patterns that could lead to future SSOT regressions"""
        production_files = self._discover_production_files()
        risk_patterns = []
        risk_indicators = [{'pattern': 'class.*DeepAgentState', 'risk_level': 'HIGH', 'description': 'New DeepAgentState class definition'}, {'pattern': 'import.*agents\\.state', 'risk_level': 'HIGH', 'description': 'Import from deprecated agents.state module'}, {'pattern': 'DeepAgentState\\s*=', 'risk_level': 'MEDIUM', 'description': 'DeepAgentState assignment'}, {'pattern': 'from.*import.*DeepAgentState', 'risk_level': 'MEDIUM', 'description': 'DeepAgentState import'}]
        for file_path in production_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                for indicator in risk_indicators:
                    if re.search(indicator['pattern'], line, re.IGNORECASE):
                        risk_patterns.append({'file': str(file_path.relative_to(self.root_path)), 'line': line_num, 'content': line.strip(), 'risk_level': indicator['risk_level'], 'description': indicator['description'], 'pattern': indicator['pattern']})
        return risk_patterns

    def _generate_audit_report(self, scan_results: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate detailed audit report"""
        if not scan_results:
            return 'CHECK NO VIOLATIONS FOUND - Production code is SSOT compliant'
        report_lines = ['🚨 SSOT IMPORT AUDIT REPORT', '=' * 50, f'Total files with violations: {len(scan_results)}', '']
        for file_path, violations in scan_results.items():
            report_lines.append(f'📄 {file_path}')
            report_lines.append(f'   Violations: {len(violations)}')
            for violation in violations:
                report_lines.append(f"   WARNING️  Line {violation['line']}: {violation['violation_type']}")
                report_lines.append(f"      Content: {violation['content']}")
            report_lines.append('')
        return '\n'.join(report_lines)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')