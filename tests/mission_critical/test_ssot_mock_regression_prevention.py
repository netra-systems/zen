"""
SSOT Mock Factory Regression Prevention Tests
Test 4 - Important Priority

Mission Critical test suite preventing regression back to direct mock creation patterns.
Automatically detects and prevents introduction of new SSOT violations.

Business Value:
- Prevents regression to duplicate mock patterns during development
- Ensures SSOT mock factory consolidation gains are maintained
- Protects development velocity through automated violation detection

Issue: #1107 - SSOT Mock Factory Duplication
Phase: 2 - Test Creation
Priority: Important (Mission Critical)
"

"""
import pytest
import ast
import os
import re
from typing import Dict, List, Tuple, Set
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase


class SSotMockRegressionPreventionTests(SSotBaseTestCase):
    "
    Mission Critical test suite preventing SSOT mock factory regression.
    
    Automatically scans codebase for new mock violations and prevents
    regression back to direct mock creation patterns.
"

    # Define SSOT violation patterns to detect
    VIOLATION_PATTERNS = {
        'direct_mock_creation': [
            r'Mock\(\)',
            r'AsyncMock\(\)',  
            r'MagicMock\(\)',
            r'= Mock\(',
            r'= AsyncMock\(',
            r'= MagicMock\('
        ],
        'websocket_mock_violations': [
            r'mock_websocket\s*=.*Mock',
            r'websocket.*=.*Mock\(\)',
            r'mock.*websocket.*send_text.*=.*AsyncMock',
            r'mock.*websocket.*send_json.*=.*AsyncMock'
        ],
        'agent_mock_violations': [
            r'mock_agent\s*=.*Mock',
            r'agent.*=.*Mock\(\)',
            r'mock.*agent.*execute.*=.*AsyncMock',
            r'agent.*execute.*AsyncMock\('
        ],
        'database_mock_violations': [
            r'mock_session\s*=.*Mock',
            r'session.*=.*Mock\(\)',
            r'mock.*session.*execute.*=.*AsyncMock',
            r'db.*session.*AsyncMock\('
        ]
    }

    # Allowed exceptions (legacy code or specific use cases)
    ALLOWED_EXCEPTIONS = {
        'files': [
            'test_legacy_mock_patterns.py',  # Legacy test file with documented violations
            'test_mock_factory_internals.py',  # Internal mock factory testing
            'test_framework/ssot/mock_factory.py'  # The mock factory itself
        ],
        'patterns': [
            r'# LEGACY_MOCK_ALLOWED',  # Explicit exemption comment
            r'# SSOT_EXCEPTION',  # Documented SSOT exception
            r'return.*Mock\(',  # Return statements in factory methods
        ]
    }

    def setUp(self):
        "Set up regression prevention testing.
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.violation_count = 0
        self.regression_violations = []

    def test_no_new_direct_mock_creation(self):
        ""
        Test that no new direct Mock() creation patterns have been introduced.
        
        CRITICAL: Direct mock creation violates SSOT principles.

        violations = self._scan_for_violations('direct_mock_creation')
        
        # Filter out allowed exceptions
        filtered_violations = self._filter_allowed_violations(violations)
        
        # Assert no new violations
        self.assertEqual(len(filtered_violations), 0, 
                        f"New direct mock creation violations detected: {filtered_violations})

    def test_no_new_websocket_mock_violations(self):
        "
        Test that no new WebSocket mock violations have been introduced.
        
        CRITICAL: WebSocket mock violations impact Golden Path testing.
"
        violations = self._scan_for_violations('websocket_mock_violations')
        filtered_violations = self._filter_allowed_violations(violations)
        
        # WebSocket violations are high-impact for Golden Path
        self.assertEqual(len(filtered_violations), 0,
                        f"New WebSocket mock violations detected: {filtered_violations})

    def test_no_new_agent_mock_violations(self):
        
        Test that no new agent mock violations have been introduced.
        
        CRITICAL: Agent mock violations impact AI response testing.
""
        violations = self._scan_for_violations('agent_mock_violations')
        filtered_violations = self._filter_allowed_violations(violations)
        
        self.assertEqual(len(filtered_violations), 0,
                        fNew agent mock violations detected: {filtered_violations})

    def test_no_new_database_mock_violations(self):
        
        Test that no new database mock violations have been introduced.
        
        IMPORTANT: Database mock violations impact persistence testing.
""
        violations = self._scan_for_violations('database_mock_violations')
        filtered_violations = self._filter_allowed_violations(violations)
        
        self.assertEqual(len(filtered_violations), 0,
                        fNew database mock violations detected: {filtered_violations})

    def test_ssot_mock_factory_usage_compliance(self):
        "
        Test that new test files use SSotMockFactory instead of direct mocks.
        
        IMPORTANT: Ensures new code follows SSOT patterns.
"
        # Scan for test files that should be using SSOT patterns
        test_files = self._get_test_files()
        non_compliant_files = []
        
        for test_file in test_files:
            if self._file_should_use_ssot(test_file):
                if not self._file_uses_ssot_factory(test_file):
                    # Check if file has mock creation without SSOT
                    if self._file_has_mock_creation(test_file):
                        non_compliant_files.append(test_file)
        
        self.assertEqual(len(non_compliant_files), 0,
                        fTest files using mocks without SSOT factory: {non_compliant_files})

    def test_import_compliance_validation(self):
        ""
        Test that new files import from SSOT mock factory correctly.
        
        IMPORTANT: Proper imports are essential for SSOT compliance.

        violations = []
        test_files = self._get_test_files()
        
        for test_file in test_files:
            if self._file_has_mock_usage(test_file):
                imports = self._get_file_imports(test_file)
                
                # Check if file uses mocks but doesn't import SSOT factory
                if self._file_has_mock_creation(test_file):
                    ssot_import_found = any(
                        'test_framework.ssot.mock_factory' in imp or
                        'SSotMockFactory' in imp
                        for imp in imports
                    )
                    
                    if not ssot_import_found:
                        violations.append({
                            'file': test_file,
                            'issue': 'Uses mocks without SSOT factory import',
                            'imports': imports
                        }
        
        self.assertEqual(len(violations), 0,
                        f"Files missing SSOT factory imports: {[v['file'] for v in violations]})

    def test_mock_pattern_consistency_enforcement(self):
        "
        Test that mock creation patterns are consistent with SSOT standards.
        
        IMPORTANT: Pattern consistency ensures maintainable test code.
"
        pattern_violations = []
        test_files = self._get_test_files()
        
        # Define expected SSOT patterns
        expected_patterns = [
            r'SSotMockFactory\.create_agent_mock\(',
            r'SSotMockFactory\.create_websocket_mock\(',
            r'SSotMockFactory\.create_database_session_mock\(',
            r'SSotMockFactory\.create_mock_user_context\(',
        ]
        
        # Define deprecated patterns that should not be used
        deprecated_patterns = [
            r'mock_agent\s*=\s*AsyncMock\(\)',
            r'mock_websocket\s*=\s*MagicMock\(\)',
            r'mock_session\s*=\s*AsyncMock\(\)',
        ]
        
        for test_file in test_files:
            content = self._get_file_content(test_file)
            
            # Check for deprecated patterns
            for pattern in deprecated_patterns:
                matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    if not self._is_violation_allowed(test_file, match.group()):
                        pattern_violations.append({
                            'file': test_file,
                            'line': self._get_line_number(content, match.start()),
                            'pattern': match.group(),
                            'issue': 'Uses deprecated mock pattern'
                        }
        
        self.assertEqual(len(pattern_violations), 0,
                        f"Deprecated mock patterns found: {pattern_violations})

    def test_regression_baseline_validation(self):
        
        Test current state against known baseline of SSOT violations.
        
        CRITICAL: Ensures no regression beyond established baseline.
""
        # Get current violation count
        all_violations = {}
        for violation_type in self.VIOLATION_PATTERNS:
            violations = self._scan_for_violations(violation_type)
            all_violations[violation_type] = len(self._filter_allowed_violations(violations))
        
        # Define baseline violation counts (from Phase 1 discovery)
        baseline_violations = {
            'direct_mock_creation': 0,  # Target: zero new violations
            'websocket_mock_violations': 0,  # Target: zero new violations  
            'agent_mock_violations': 0,  # Target: zero new violations
            'database_mock_violations': 0,  # Target: zero new violations
        }
        
        # Compare current state to baseline
        regression_detected = False
        regression_details = []
        
        for violation_type, current_count in all_violations.items():
            baseline_count = baseline_violations.get(violation_type, 0)
            
            if current_count > baseline_count:
                regression_detected = True
                regression_details.append({
                    'violation_type': violation_type,
                    'baseline': baseline_count,
                    'current': current_count,
                    'regression': current_count - baseline_count
                }
        
        if regression_detected:
            regression_summary = \n.join([
                f  {detail['violation_type']}: {detail['baseline']} -> {detail['current']} (+{detail['regression']}"
                for detail in regression_details
            ]
            self.fail(f"SSOT mock regression detected:\n{regression_summary})

    def test_automated_violation_detection_coverage(self):
        
        Test that violation detection covers all critical mock patterns.
        
        IMPORTANT: Ensures comprehensive regression prevention.
""
        # Verify violation patterns cover expected mock types
        required_coverage = {
            'Mock()': 'direct_mock_creation',
            'AsyncMock()': 'direct_mock_creation', 
            'MagicMock()': 'direct_mock_creation',
            'websocket': 'websocket_mock_violations',
            'agent': 'agent_mock_violations',
            'session': 'database_mock_violations'
        }
        
        coverage_gaps = []
        for pattern, expected_category in required_coverage.items():
            # Check if pattern is covered by violation detection
            category_patterns = self.VIOLATION_PATTERNS.get(expected_category, []
            pattern_covered = any(
                pattern.lower() in cat_pattern.lower()
                for cat_pattern in category_patterns
            )
            
            if not pattern_covered:
                coverage_gaps.append({
                    'pattern': pattern,
                    'expected_category': expected_category,
                    'available_patterns': category_patterns
                }
        
        self.assertEqual(len(coverage_gaps), 0,
                        fViolation detection coverage gaps: {coverage_gaps})

    def test_ci_cd_integration_readiness(self):
        
        Test that regression prevention is ready for CI/CD integration.
        
        IMPORTANT: Ensures automated prevention in development workflow.
""
        # Verify test can be run in CI environment
        ci_readiness_checks = []
        
        # Check performance - should complete in reasonable time
        import time
        start_time = time.time()
        
        # Run a subset of violation scanning
        violations = self._scan_for_violations('direct_mock_creation')
        
        end_time = time.time()
        scan_duration = end_time - start_time
        
        # Should complete in under 10 seconds for CI efficiency
        if scan_duration > 10.0:
            ci_readiness_checks.append(fScan too slow for CI: {scan_duration:.1f}s > 10.0s)
        
        # Check that violation detection produces actionable results
        if not hasattr(self, '_scan_for_violations'):
            ci_readiness_checks.append(Violation scanning method not implemented)"
        
        # Check that results can be formatted for CI output
        try:
            violation_summary = self._generate_violation_summary(violations)
            if not isinstance(violation_summary, str):
                ci_readiness_checks.append("Cannot generate CI-compatible violation summary)
        except Exception as e:
            ci_readiness_checks.append(fViolation summary generation failed: {e})
        
        self.assertEqual(len(ci_readiness_checks), 0,
                        f"CI/CD readiness issues: {ci_readiness_checks})

    # Helper methods for regression prevention

    def _scan_for_violations(self, violation_type: str) -> List[Dict]:
        "Scan codebase for specific violation type.
        violations = []
        patterns = self.VIOLATION_PATTERNS.get(violation_type, []
        
        for pattern in patterns:
            violations.extend(self._scan_pattern(pattern, violation_type))
        
        return violations

    def _scan_pattern(self, pattern: str, violation_type: str) -> List[Dict]:
        "Scan for specific pattern in codebase."
        violations = []
        test_files = self._get_test_files()
        
        for test_file in test_files:
            content = self._get_file_content(test_file)
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            
            for match in matches:
                violations.append({
                    'file': test_file,
                    'line': self._get_line_number(content, match.start()),
                    'pattern': match.group(),
                    'violation_type': violation_type,
                    'context': self._get_line_context(content, match.start())
                }
        
        return violations

    def _filter_allowed_violations(self, violations: List[Dict] -> List[Dict]:
        "Filter out violations that are explicitly allowed."
        filtered = []
        
        for violation in violations:
            if not self._is_violation_allowed(violation['file'], violation['pattern']:
                filtered.append(violation)
        
        return filtered

    def _is_violation_allowed(self, file_path: str, pattern: str) -> bool:
        Check if violation is explicitly allowed.""
        # Check allowed files
        for allowed_file in self.ALLOWED_EXCEPTIONS['files']:
            if allowed_file in file_path:
                return True
        
        # Check allowed patterns  
        for allowed_pattern in self.ALLOWED_EXCEPTIONS['patterns']:
            if re.search(allowed_pattern, pattern):
                return True
        
        return False

    def _get_test_files(self) -> List[str]:
        Get all test files in the project."
        test_files = []
        test_dirs = ['tests', 'netra_backend/tests', 'test_framework/tests']
        
        for test_dir in test_dirs:
            test_dir_path = self.project_root / test_dir
            if test_dir_path.exists():
                for py_file in test_dir_path.rglob('*.py'):
                    if 'test_' in py_file.name or py_file.name.startswith('test_'):
                        test_files.append(str(py_file))
        
        return test_files

    def _file_should_use_ssot(self, file_path: str) -> bool:
        "Check if file should be using SSOT patterns.
        # New test files should use SSOT
        return (
            'test_' in os.path.basename(file_path) and
            not any(exc in file_path for exc in self.ALLOWED_EXCEPTIONS['files']
        )

    def _file_uses_ssot_factory(self, file_path: str) -> bool:
        ""Check if file imports and uses SSOT mock factory.
        content = self._get_file_content(file_path)
        return (
            'SSotMockFactory' in content or
            'test_framework.ssot.mock_factory' in content
        )

    def _file_has_mock_creation(self, file_path: str) -> bool:
        Check if file creates mocks.""
        content = self._get_file_content(file_path)
        mock_patterns = [
            r'Mock\(',
            r'AsyncMock\(',
            r'MagicMock\(',
            r'mock_\w+\s*='
        ]
        
        return any(re.search(pattern, content) for pattern in mock_patterns)

    def _file_has_mock_usage(self, file_path: str) -> bool:
        Check if file uses mocks in any way.""
        content = self._get_file_content(file_path)
        return 'mock' in content.lower()

    def _get_file_imports(self, file_path: str) -> List[str]:
        Extract import statements from file."
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Use AST to parse imports properly
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ''
                        for alias in node.names:
                            imports.append(f{module}.{alias.name}")
            except SyntaxError:
                # Fallback to regex for files with syntax issues
                import_lines = re.findall(r'^(?:from|import)\s+(.+)', content, re.MULTILINE)
                imports.extend(import_lines)
                
        except Exception:
            # Handle file read errors gracefully
            pass
            
        return imports

    def _get_file_content(self, file_path: str) -> str:
        Get file content safely.""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return 

    def _get_line_number(self, content: str, position: int) -> int:
        Get line number for character position in content.""
        return content[:position].count('\n') + 1

    def _get_line_context(self, content: str, position: int) -> str:
        Get context around violation for better debugging.""
        lines = content.split('\n')
        line_num = self._get_line_number(content, position) - 1
        
        start_line = max(0, line_num - 1)
        end_line = min(len(lines), line_num + 2)
        
        context_lines = []
        for i in range(start_line, end_line):
            marker =  ->  if i == line_num else     
            context_lines.append(f{marker}Line {i+1}: {lines[i]})
        
        return \n".join(context_lines)"

    def _generate_violation_summary(self, violations: List[Dict] -> str:
        Generate violation summary for CI/CD output."
        if not violations:
            return No SSOT mock violations detected."
        
        summary_lines = [
            fSSOT Mock Violations Detected: {len(violations)},
            = * 50"
        ]
        
        # Group violations by type
        by_type = {}
        for violation in violations:
            vtype = violation['violation_type']
            if vtype not in by_type:
                by_type[vtype] = []
            by_type[vtype].append(violation)
        
        for vtype, vlist in by_type.items():
            summary_lines.append(f"\n{vtype}: {len(vlist)} violations)
            for v in vlist[:3]:  # Show first 3 for brevity
                summary_lines.append(f  - {v['file']}:L{v['line']} - {v['pattern']})
            if len(vlist) > 3:
                summary_lines.append(f  ... and {len(vlist) - 3} more)
        
        return \n".join(summary_lines)"


if __name__ == "__main__":
    # Run as standalone test for development and CI integration
    # MIGRATED: Use SSOT unified test runner
    # python tests/unified_test_runner.py --category unit
    pass  # TODO: Replace with appropriate SSOT test execution  # -x to stop on first failure for faster CI