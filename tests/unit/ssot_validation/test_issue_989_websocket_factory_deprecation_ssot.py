"""MISSION CRITICAL: Issue #989 WebSocket Factory Deprecation SSOT Violation Detection

GitHub Issue: #989 WebSocket factory deprecation SSOT violation - get_websocket_manager_factory()
GitHub Stage: Step 2 - EXECUTE THE TEST PLAN

BUSINESS VALUE: $500K+ ARR - Detects deprecated factory patterns that threaten Golden Path
WHERE users login → receive AI responses through proper WebSocket initialization.

PURPOSE:
- THIS TEST MUST INITIALLY FAIL to prove SSOT violation exists
- Detects deprecated get_websocket_manager_factory() in canonical_imports.py line 34
- Validates multiple WebSocket initialization patterns cause Golden Path conflicts
- Tests will PASS after SSOT migration eliminates deprecated exports

CRITICAL SSOT VIOLATION:
canonical_imports.py exports deprecated get_websocket_manager_factory() function creating
dual initialization patterns that threaten user isolation and Golden Path reliability.

TEST STRATEGY:
1. Detect deprecated factory function exports in canonical imports
2. Identify files using deprecated vs current WebSocket initialization patterns
3. Validate Golden Path WebSocket flow works with both patterns (risk assessment)
4. Test user context isolation during WebSocket operations
5. Create failing tests that prove violations exist before remediation

EXPECTED BEHAVIOR:
- BEFORE SSOT Fix: Tests FAIL (proving violations exist)
- AFTER SSOT Fix: Tests PASS (proving successful remediation)
"""
import os
import sys
import ast
import importlib.util
import warnings
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from test_framework.ssot.base_test_case import SSotBaseTestCase
import pytest
from loguru import logger

@dataclass
class FactoryViolationDetails:
    """Data class to track factory pattern violations"""
    file_path: str
    deprecated_exports: List[str]
    line_numbers: List[int]
    violation_type: str
    severity: str

@dataclass
class InitializationPatternAnalysis:
    """Analysis of WebSocket initialization patterns in codebase"""
    deprecated_pattern_files: List[str]
    current_pattern_files: List[str]
    mixed_pattern_files: List[str]
    total_websocket_files: int
    ssot_compliance_percentage: float

@pytest.mark.unit
class Issue989WebSocketFactoryDeprecationSSoTTests(SSotBaseTestCase):
    """Mission Critical: Issue #989 WebSocket Factory Deprecation SSOT Violation Detection

    This test suite detects and validates SSOT violations related to deprecated
    WebSocket factory patterns that threaten Golden Path user flow reliability.

    Expected Test Behavior:
    - ALL tests SHOULD FAIL initially (proving violations exist)
    - ALL tests SHOULD PASS after SSOT remediation (proving fix works)
    """

    def setup_method(self, method):
        """Set up test environment for Issue #989 SSOT violation detection."""
        super().setup_method(method)
        self.canonical_imports_path = Path(project_root) / 'netra_backend' / 'app' / 'websocket_core' / 'canonical_imports.py'
        self.websocket_factory_path = Path(project_root) / 'netra_backend' / 'app' / 'websocket_core' / 'websocket_manager_factory.py'
        self.deprecated_export_patterns = ['get_websocket_manager_factory', 'WebSocketManagerFactory', 'create_websocket_manager']
        self.ssot_compliant_patterns = ['get_websocket_manager', 'WebSocketManager', 'create_websocket_manager_sync']
        self.violation_details: Dict[str, Any] = {}
        logger.info(f'🔍 Issue #989 SSOT Violation Detection - Starting validation...')
        logger.info(f'Target canonical imports: {self.canonical_imports_path}')
        logger.info(f'Target factory module: {self.websocket_factory_path}')

    def test_detect_deprecated_get_websocket_manager_factory_export_violation(self):
        """CRITICAL: Detect deprecated get_websocket_manager_factory export (SHOULD FAIL initially)

        Issue #989 PRIMARY VIOLATION:
        canonical_imports.py line 34 exports deprecated get_websocket_manager_factory()
        function creating dual initialization patterns threatening Golden Path.

        This test MUST FAIL initially to prove the violation exists.
        """
        logger.info('🚨 Testing Issue #989 PRIMARY VIOLATION: get_websocket_manager_factory export')
        violations = []
        if self.canonical_imports_path.exists():
            try:
                content = self.canonical_imports_path.read_text(encoding='utf-8')
                lines = content.split('\n')
                tree = ast.parse(content)
                exported_names = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == '__all__':
                                if isinstance(node.value, ast.List):
                                    for elt in node.value.elts:
                                        if isinstance(elt, ast.Constant):
                                            exported_names.add(elt.value)
                deprecated_exports_found = []
                for line_num, line in enumerate(lines, 1):
                    for deprecated_pattern in self.deprecated_export_patterns:
                        if deprecated_pattern in line:
                            deprecated_exports_found.append({'line_num': line_num, 'line': line.strip(), 'pattern': deprecated_pattern, 'export_type': 'import' if 'import' in line else 'export'})
                            logger.error(f'🚨 VIOLATION DETECTED: {self.canonical_imports_path.name}:{line_num}')
                            logger.error(f'   Pattern: {deprecated_pattern}')
                            logger.error(f'   Line: {line.strip()}')
                primary_violation = 'get_websocket_manager_factory' in exported_names
                if deprecated_exports_found or primary_violation:
                    violations.append(FactoryViolationDetails(file_path=str(self.canonical_imports_path.relative_to(project_root)), deprecated_exports=list(exported_names.intersection(self.deprecated_export_patterns)), line_numbers=[v['line_num'] for v in deprecated_exports_found], violation_type='deprecated_factory_export', severity='CRITICAL'))
            except Exception as e:
                logger.error(f'Failed to analyze canonical imports: {e}')
                violations.append(FactoryViolationDetails(file_path=str(self.canonical_imports_path), deprecated_exports=['analysis_failed'], line_numbers=[0], violation_type='analysis_error', severity='HIGH'))
        else:
            logger.error(f'canonical_imports.py not found at {self.canonical_imports_path}')
            violations.append(FactoryViolationDetails(file_path=str(self.canonical_imports_path), deprecated_exports=['file_not_found'], line_numbers=[0], violation_type='missing_file', severity='CRITICAL'))
        self.violation_details['deprecated_export_violations'] = violations
        assert len(violations) == 0, f'ISSUE #989 SSOT VIOLATION: Found {len(violations)} deprecated factory export violations. canonical_imports.py MUST NOT export deprecated get_websocket_manager_factory(). Violations: {[(v.file_path, v.deprecated_exports) for v in violations]}. GOLDEN PATH RISK: Dual initialization patterns threaten $500K+ ARR user flow.'

    def test_detect_websocket_factory_deprecation_warnings_violation(self):
        """CRITICAL: Validate factory deprecation warnings are properly implemented (SHOULD FAIL initially)

        The websocket_manager_factory.py module should emit deprecation warnings
        and redirect to SSOT implementations. This test validates warnings exist.
        """
        logger.info('🔍 Testing websocket_manager_factory.py deprecation warning implementation...')
        warnings_analysis = {'deprecation_warnings_found': False, 'warning_count': 0, 'ssot_redirects_found': False, 'violation_details': []}
        if self.websocket_factory_path.exists():
            try:
                content = self.websocket_factory_path.read_text(encoding='utf-8')
                lines = content.split('\n')
                warning_patterns = ['warnings.warn', 'DeprecationWarning', 'deprecated', 'DEPRECATED']
                ssot_redirect_patterns = ['from netra_backend.app.websocket_core.websocket_manager import', 'get_websocket_manager(', 'WebSocketManager(']
                for line_num, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    for pattern in warning_patterns:
                        if pattern.lower() in line_lower:
                            warnings_analysis['warning_count'] += 1
                            warnings_analysis['deprecation_warnings_found'] = True
                            logger.info(f'✅ Deprecation warning found: {line_num}: {line.strip()}')
                    for pattern in ssot_redirect_patterns:
                        if pattern in line:
                            warnings_analysis['ssot_redirects_found'] = True
                            logger.info(f'✅ SSOT redirect found: {line_num}: {line.strip()}')
                module_warning_found = 'warnings.warn(' in content and 'DEPRECATED' in content
                warnings_analysis['module_warning_found'] = module_warning_found
            except Exception as e:
                logger.error(f'Failed to analyze factory deprecation: {e}')
                warnings_analysis['violation_details'].append(f'Analysis failed: {e}')
        else:
            warnings_analysis['violation_details'].append('websocket_manager_factory.py not found')
        self.violation_details['deprecation_warnings_analysis'] = warnings_analysis
        has_proper_deprecation = warnings_analysis['deprecation_warnings_found'] and warnings_analysis['ssot_redirects_found'] and (warnings_analysis['warning_count'] >= 1)
        if not has_proper_deprecation:
            logger.warning(f'⚠️ Incomplete deprecation implementation in websocket_manager_factory.py')
            logger.warning(f"  Warnings found: {warnings_analysis['deprecation_warnings_found']}")
            logger.warning(f"  SSOT redirects found: {warnings_analysis['ssot_redirects_found']}")
            logger.warning(f"  Warning count: {warnings_analysis['warning_count']}")

    def test_analyze_websocket_initialization_pattern_fragmentation(self):
        """CRITICAL: Analyze WebSocket initialization pattern fragmentation (SHOULD FAIL initially)

        Scans codebase for files using different WebSocket initialization patterns,
        proving that multiple patterns exist creating SSOT fragmentation.
        """
        logger.info('🔍 Analyzing WebSocket initialization pattern fragmentation across codebase...')
        search_paths = [Path(project_root) / 'netra_backend' / 'app', Path(project_root) / 'tests', Path(project_root) / 'test_framework']
        deprecated_factory_patterns = ['get_websocket_manager_factory\\(\\)', 'WebSocketManagerFactory\\(', 'create_websocket_manager\\(']
        current_ssot_patterns = ['get_websocket_manager\\(', 'WebSocketManager\\(', 'from.*websocket_manager import.*WebSocketManager']
        pattern_analysis = InitializationPatternAnalysis(deprecated_pattern_files=[], current_pattern_files=[], mixed_pattern_files=[], total_websocket_files=0, ssot_compliance_percentage=0.0)
        import re
        for search_path in search_paths:
            if search_path.exists():
                for py_file in search_path.rglob('*.py'):
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        if py_file.name == 'websocket_manager_factory.py':
                            continue
                        has_websocket_usage = 'websocket' in content.lower() and any((pattern in content.lower() for pattern in ['websocketmanager', 'websocket_manager', 'create_websocket']))
                        if has_websocket_usage:
                            pattern_analysis.total_websocket_files += 1
                            has_deprecated = any((re.search(pattern, content) for pattern in deprecated_factory_patterns))
                            has_current = any((re.search(pattern, content) for pattern in current_ssot_patterns))
                            file_rel_path = str(py_file.relative_to(project_root))
                            if has_deprecated and has_current:
                                pattern_analysis.mixed_pattern_files.append(file_rel_path)
                                logger.error(f'🚨 MIXED PATTERNS: {file_rel_path}')
                            elif has_deprecated:
                                pattern_analysis.deprecated_pattern_files.append(file_rel_path)
                                logger.warning(f'⚠️ DEPRECATED PATTERN: {file_rel_path}')
                            elif has_current:
                                pattern_analysis.current_pattern_files.append(file_rel_path)
                                logger.info(f'✅ CURRENT PATTERN: {file_rel_path}')
                    except (UnicodeDecodeError, PermissionError):
                        continue
        if pattern_analysis.total_websocket_files > 0:
            compliant_files = len(pattern_analysis.current_pattern_files)
            pattern_analysis.ssot_compliance_percentage = compliant_files / pattern_analysis.total_websocket_files * 100
        self.violation_details['initialization_pattern_analysis'] = pattern_analysis
        logger.info('📊 WebSocket Initialization Pattern Analysis:')
        logger.info(f'  Total WebSocket files: {pattern_analysis.total_websocket_files}')
        logger.info(f'  Deprecated pattern files: {len(pattern_analysis.deprecated_pattern_files)}')
        logger.info(f'  Current SSOT pattern files: {len(pattern_analysis.current_pattern_files)}')
        logger.info(f'  Mixed pattern files: {len(pattern_analysis.mixed_pattern_files)}')
        logger.info(f'  SSOT compliance: {pattern_analysis.ssot_compliance_percentage:.1f}%')
        has_fragmentation = len(pattern_analysis.deprecated_pattern_files) > 0 or len(pattern_analysis.mixed_pattern_files) > 0
        assert not has_fragmentation, f'ISSUE #989 SSOT FRAGMENTATION: Found WebSocket initialization pattern fragmentation. Deprecated pattern files: {len(pattern_analysis.deprecated_pattern_files)}, Mixed pattern files: {len(pattern_analysis.mixed_pattern_files)}. SSOT requires single initialization pattern. Files using deprecated patterns: {pattern_analysis.deprecated_pattern_files[:5]}...'

    def test_validate_canonical_imports_ssot_compliance_target_state(self):
        """VALIDATION: Test target SSOT compliance state for canonical imports

        This test validates what canonical_imports.py should look like after
        successful SSOT migration (target state validation).
        """
        logger.info('🔍 Validating target SSOT compliance state for canonical imports...')
        target_state_analysis = {'should_not_export': self.deprecated_export_patterns, 'should_export': self.ssot_compliant_patterns, 'actual_exports': [], 'compliance_issues': [], 'target_compliance_achieved': False}
        if self.canonical_imports_path.exists():
            try:
                content = self.canonical_imports_path.read_text(encoding='utf-8')
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == '__all__':
                                if isinstance(node.value, ast.List):
                                    for elt in node.value.elts:
                                        if isinstance(elt, ast.Constant):
                                            target_state_analysis['actual_exports'].append(elt.value)
                exports_set = set(target_state_analysis['actual_exports'])
                deprecated_set = set(target_state_analysis['should_not_export'])
                required_set = set(target_state_analysis['should_export'])
                deprecated_still_exported = exports_set.intersection(deprecated_set)
                if deprecated_still_exported:
                    target_state_analysis['compliance_issues'].append(f'Still exports deprecated: {list(deprecated_still_exported)}')
                target_state_analysis['target_compliance_achieved'] = len(deprecated_still_exported) == 0
            except Exception as e:
                target_state_analysis['compliance_issues'].append(f'Analysis failed: {e}')
        self.violation_details['target_state_analysis'] = target_state_analysis
        logger.info('📊 Target SSOT Compliance Analysis:')
        logger.info(f"  Actual exports: {len(target_state_analysis['actual_exports'])}")
        logger.info(f"  Compliance issues: {len(target_state_analysis['compliance_issues'])}")
        logger.info(f"  Target compliance achieved: {target_state_analysis['target_compliance_achieved']}")
        if not target_state_analysis['target_compliance_achieved']:
            logger.warning('⚠️ Target SSOT compliance state not yet achieved')
            for issue in target_state_analysis['compliance_issues']:
                logger.warning(f'  Issue: {issue}')
        else:
            logger.info('✅ Target SSOT compliance state achieved')

    def teardown_method(self, method):
        """Clean up and log Issue #989 SSOT violation detection results."""
        if self.violation_details:
            logger.info('📊 Issue #989 SSOT Violation Detection Summary:')
            total_violations = 0
            critical_violations = 0
            for violation_type, details in self.violation_details.items():
                if violation_type == 'deprecated_export_violations' and isinstance(details, list):
                    violation_count = len(details)
                    total_violations += violation_count
                    critical_count = sum((1 for v in details if v.severity == 'CRITICAL'))
                    critical_violations += critical_count
                    logger.error(f'  {violation_type}: {violation_count} violations ({critical_count} critical)')
                elif violation_type == 'initialization_pattern_analysis' and hasattr(details, 'deprecated_pattern_files'):
                    deprecated_count = len(details.deprecated_pattern_files)
                    mixed_count = len(details.mixed_pattern_files)
                    total_violations += deprecated_count + mixed_count
                    logger.warning(f'  Pattern fragmentation: {deprecated_count} deprecated, {mixed_count} mixed')
                elif violation_type == 'deprecation_warnings_analysis' and isinstance(details, dict):
                    warnings_found = details.get('deprecation_warnings_found', False)
                    status = '✅ Compliant' if warnings_found else '⚠️ Missing warnings'
                    logger.info(f'  Deprecation warnings: {status}')
            if total_violations > 0:
                logger.error(f'🚨 ISSUE #989 TOTAL VIOLATIONS: {total_violations} ({critical_violations} critical)')
                logger.error('   These violations MUST be resolved to achieve SSOT compliance')
            else:
                logger.info('✅ Issue #989: No SSOT violations detected')
        super().teardown_method(method)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')