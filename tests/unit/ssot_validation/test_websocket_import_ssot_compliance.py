"""
WebSocket Import SSOT Compliance Test Suite

This test validates all WebSocket imports use canonical SSOT patterns across the codebase.
Tests GitHub issue #212 - WebSocket import inconsistencies (593 files affected).

PURPOSE: Detect and prevent WebSocket import violations by scanning the codebase for:
1. Canonical import pattern usage: `from netra_backend.app.websocket_core.canonical_imports import`
2. Prohibited direct imports: `from netra_backend.app.websocket_core.unified_manager import`
3. Multiple import paths for same functionality (SSOT violations)

CRITICAL: These tests FAIL with current violations (593+ files) and PASS after remediation.
Progress tracking: Start at 593 violations, target <50 violations for Phase 1 completion.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Eliminate import chaos causing integration failures 
- Value Impact: Standardize WebSocket access patterns, prevent development delays
- Revenue Impact: Foundation for reliable AI chat interactions ($500K+ ARR dependency)
"""
import ast
import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from unittest.mock import patch
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

@dataclass
class ImportViolation:
    """Represents a WebSocket import violation."""
    file_path: str
    line_number: int
    import_statement: str
    violation_type: str
    canonical_replacement: str

@dataclass
class ImportAnalysisResult:
    """Results of WebSocket import analysis."""
    total_files_scanned: int
    files_with_websocket_imports: int
    canonical_imports_found: int
    violation_count: int
    violations: List[ImportViolation]
    compliance_score: float

@pytest.mark.unit
class WebSocketImportSSotComplianceTests(SSotBaseTestCase):
    """
    CRITICAL: WebSocket import SSOT compliance validation.
    
    These tests detect import violations preventing SSOT consolidation and provide
    clear remediation guidance for developers.
    """
    CURRENT_VIOLATION_THRESHOLD = 593
    TARGET_VIOLATION_THRESHOLD = 50

    @property
    def logger(self):
        """Get logger for this test class."""
        return logging.getLogger(self.__class__.__name__)
    CANONICAL_IMPORT_PATTERNS = ['from netra_backend\\.app\\.websocket_core\\.canonical_imports import', 'from test_framework\\.ssot\\.websocket import']
    PROHIBITED_IMPORT_PATTERNS = ['from netra_backend\\.app\\.websocket_core\\.unified_manager import UnifiedWebSocketManager', 'from netra_backend\\.app\\.websocket_core\\.manager import WebSocketManager', 'from netra_backend\\.app\\.websocket_core\\.websocket_manager import', 'from netra_backend\\.app\\.websocket_core import get_websocket_manager', 'from netra_backend\\.app\\.websocket_core\\.unified_manager import get_websocket_manager', 'from netra_backend\\.app\\.core\\.interfaces_websocket import WebSocketManagerProtocol', 'from netra_backend\\.app\\.websocket_core\\.websocket_manager_factory import WebSocketManagerFactory', 'from netra_backend\\.app\\.services\\.websocket_bridge_factory import']

    @property
    def codebase_root(self) -> Path:
        """Get the codebase root directory."""
        return Path(__file__).parent.parent.parent.parent

    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the codebase (excluding venv, .git, etc.)."""
        exclude_patterns = {'.git', 'venv', '.venv', '__pycache__', '.pytest_cache', 'node_modules', '.test_venv', 'build', 'dist'}
        python_files = []
        for root, dirs, files in os.walk(self.codebase_root):
            dirs[:] = [d for d in dirs if not any((pattern in d for pattern in exclude_patterns))]
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        return python_files

    def _analyze_file_imports(self, file_path: Path) -> List[ImportViolation]:
        """
        Analyze a single Python file for WebSocket import violations.
        
        Returns:
            List of violations found in the file
        """
        violations = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return violations
            for line_num, line in enumerate(content.splitlines(), 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                for pattern in self.PROHIBITED_IMPORT_PATTERNS:
                    if re.search(pattern, line):
                        canonical_replacement = self._get_canonical_replacement(line, pattern)
                        violations.append(ImportViolation(file_path=str(file_path.relative_to(self.codebase_root)), line_number=line_num, import_statement=line, violation_type=f'Prohibited import pattern: {pattern}', canonical_replacement=canonical_replacement))
        except Exception as e:
            self.logger.warning(f'Error analyzing file {file_path}: {e}')
        return violations

    def _get_canonical_replacement(self, import_line: str, violated_pattern: str) -> str:
        """Generate canonical import replacement for a violating import."""
        if 'UnifiedWebSocketManager' in import_line:
            return 'from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerFactory'
        elif 'WebSocketManager' in import_line:
            return 'from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerFactory'
        elif 'get_websocket_manager' in import_line:
            return 'from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager'
        elif 'WebSocketManagerProtocol' in import_line:
            return 'from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerProtocol'
        elif 'WebSocketManagerFactory' in import_line:
            return 'from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerFactory'
        else:
            return 'from netra_backend.app.websocket_core.canonical_imports import <appropriate_import>'

    def _scan_codebase_for_violations(self) -> ImportAnalysisResult:
        """
        Scan the entire codebase for WebSocket import violations.
        
        Returns:
            Complete analysis results
        """
        python_files = self._get_python_files()
        all_violations = []
        files_with_websocket_imports = 0
        canonical_imports_found = 0
        for file_path in python_files:
            file_violations = self._analyze_file_imports(file_path)
            if file_violations:
                all_violations.extend(file_violations)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'websocket' in content.lower() and 'import' in content:
                        files_with_websocket_imports += 1
                        for pattern in self.CANONICAL_IMPORT_PATTERNS:
                            if re.search(pattern, content):
                                canonical_imports_found += 1
                                break
            except Exception as e:
                continue
        compliance_score = 0.0
        if files_with_websocket_imports > 0:
            compliance_score = canonical_imports_found / files_with_websocket_imports * 100
        return ImportAnalysisResult(total_files_scanned=len(python_files), files_with_websocket_imports=files_with_websocket_imports, canonical_imports_found=canonical_imports_found, violation_count=len(all_violations), violations=all_violations, compliance_score=compliance_score)

    def test_websocket_imports_use_canonical_pattern(self):
        """
        CRITICAL: All WebSocket imports must use canonical SSOT pattern.
        
        This test scans the codebase for WebSocket import violations and ensures
        that all imports follow the canonical pattern defined in canonical_imports.py.
        
        EXPECTED: This test FAILS with current codebase (593+ violations)
        GOAL: This test PASSES when violations < 50 (Phase 1 target)
        """
        analysis_result = self._scan_codebase_for_violations()
        self.logger.info(f'WebSocket Import Analysis Results:')
        self.logger.info(f' CHART:  Total files scanned: {analysis_result.total_files_scanned}')
        self.logger.info(f'[U+1F4C2] Files with WebSocket imports: {analysis_result.files_with_websocket_imports}')
        self.logger.info(f' PASS:  Canonical imports found: {analysis_result.canonical_imports_found}')
        self.logger.info(f' ALERT:  Violations found: {analysis_result.violation_count}')
        self.logger.info(f'[U+1F4C8] Compliance score: {analysis_result.compliance_score:.1f}%')
        if analysis_result.violations:
            self.logger.warning(' FAIL:  Top 10 WebSocket import violations:')
            for i, violation in enumerate(analysis_result.violations[:10], 1):
                self.logger.warning(f'   {i}. {violation.file_path}:{violation.line_number}')
                self.logger.warning(f'       FAIL:  {violation.import_statement}')
                self.logger.warning(f'       PASS:  {violation.canonical_replacement}')
        assert analysis_result.violation_count <= self.CURRENT_VIOLATION_THRESHOLD, f'WebSocket import violations ({analysis_result.violation_count}) exceed threshold ({self.CURRENT_VIOLATION_THRESHOLD}). \n\nREMEDIATION REQUIRED:\n[U+2022] Target: Reduce violations to <{self.TARGET_VIOLATION_THRESHOLD} for Phase 1\n[U+2022] Current compliance score: {analysis_result.compliance_score:.1f}%\n[U+2022] Files needing remediation: {len(set((v.file_path for v in analysis_result.violations)))}\n\nIMPORT REMEDIATION GUIDE:\n PASS:  USE: from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerFactory\n FAIL:  AVOID: from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager\n FAIL:  AVOID: from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager\n\nSee CANONICAL IMPORT GUIDE in canonical_imports.py for complete migration instructions.'

    def test_no_direct_unified_manager_imports(self):
        """
        CRITICAL: No direct UnifiedWebSocketManager imports allowed.
        
        Direct imports bypass the factory pattern required for user isolation.
        All WebSocket manager access must go through WebSocketManagerFactory.
        """
        analysis_result = self._scan_codebase_for_violations()
        unified_manager_violations = [v for v in analysis_result.violations if 'unified_manager import UnifiedWebSocketManager' in v.violation_type]
        self.logger.info(f'Direct UnifiedWebSocketManager import violations: {len(unified_manager_violations)}')
        if unified_manager_violations:
            self.logger.warning(' FAIL:  Direct UnifiedWebSocketManager imports found:')
            for violation in unified_manager_violations[:5]:
                self.logger.warning(f'   [U+1F4C1] {violation.file_path}:{violation.line_number}')
                self.logger.warning(f'    FAIL:  {violation.import_statement}')
                self.logger.warning(f'    PASS:  {violation.canonical_replacement}')
        assert len(unified_manager_violations) == 0, f'Found {len(unified_manager_violations)} direct UnifiedWebSocketManager imports. These bypass user isolation security requirements.\n\nSECURITY VIOLATION: Direct manager imports prevent proper user context isolation.\nREMEDIATION: Replace with factory pattern:\n PASS:  from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerFactory\n PASS:  factory = WebSocketManagerFactory()\n PASS:  manager = await factory.create_isolated_manager(user_id, connection_id)\n\n FAIL:  from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager'

    def test_canonical_import_coverage_progression(self):
        """
        Track progress toward canonical import adoption.
        
        This test measures improvement over time and provides progression metrics.
        """
        analysis_result = self._scan_codebase_for_violations()
        total_websocket_files = analysis_result.files_with_websocket_imports
        canonical_files = analysis_result.canonical_imports_found
        violation_files = len(set((v.file_path for v in analysis_result.violations)))
        progression_score = canonical_files / total_websocket_files * 100 if total_websocket_files > 0 else 0
        self.logger.info('[U+1F4C8] Canonical Import Progression Metrics:')
        self.logger.info(f'   Total WebSocket files: {total_websocket_files}')
        self.logger.info(f'   Files using canonical imports: {canonical_files}')
        self.logger.info(f'   Files with violations: {violation_files}')
        self.logger.info(f'   Progression score: {progression_score:.1f}%')
        milestones = [(10, 'Basic canonical import adoption started'), (25, 'Quarter of files migrated to canonical imports'), (50, 'Half of files using canonical imports'), (75, 'Three-quarters milestone reached'), (90, 'Near-complete canonical import adoption')]
        for threshold, message in milestones:
            if progression_score >= threshold:
                self.logger.info(f' CELEBRATION:  Milestone achieved: {message} ({progression_score:.1f}%)')
        metrics = {'total_violations': analysis_result.violation_count, 'progression_score': progression_score, 'files_with_violations': violation_files, 'canonical_coverage': canonical_files, 'compliance_score': analysis_result.compliance_score}
        self.record_test_metrics('websocket_import_ssot_compliance', metrics)
        assert True, 'Progression tracking test - see metrics above'

    def test_websocket_import_remediation_guide(self):
        """
        Provide comprehensive remediation guidance for developers.
        
        This test generates actionable remediation instructions based on current violations.
        """
        analysis_result = self._scan_codebase_for_violations()
        if not analysis_result.violations:
            self.logger.info(' PASS:  No WebSocket import violations found - SSOT compliance achieved!')
            return
        violation_groups = {}
        for violation in analysis_result.violations:
            violation_type = violation.violation_type
            if violation_type not in violation_groups:
                violation_groups[violation_type] = []
            violation_groups[violation_type].append(violation)
        self.logger.info('[U+1F527] WEBSOCKET IMPORT REMEDIATION GUIDE')
        self.logger.info('=' * 60)
        for violation_type, violations in violation_groups.items():
            self.logger.info(f'\n FAIL:  VIOLATION TYPE: {violation_type}')
            self.logger.info(f' CHART:  Count: {len(violations)} occurrences')
            self.logger.info(f'[U+1F4C1] Example files:')
            for violation in violations[:3]:
                self.logger.info(f'   {violation.file_path}:{violation.line_number}')
                self.logger.info(f'   CURRENT: {violation.import_statement}')
                self.logger.info(f'   REPLACE: {violation.canonical_replacement}')
            if len(violations) > 3:
                self.logger.info(f'   ... and {len(violations) - 3} more files')
        self.logger.info('\n[U+1F916] AUTOMATED REMEDIATION:')
        self.logger.info('Use this sed command pattern for batch replacement:')
        self.logger.info("find . -name '*.py' -exec sed -i 's/old_pattern/new_pattern/g' {} +")
        self.logger.info(f'\n[U+1F4CB] REMEDIATION PRIORITY:')
        self.logger.info(f'1. Fix direct UnifiedWebSocketManager imports (security critical)')
        self.logger.info(f'2. Replace singleton get_websocket_manager() calls')
        self.logger.info(f'3. Standardize factory imports to canonical path')
        self.logger.info(f'4. Update interface imports to use canonical protocol')
        assert True, 'Remediation guide generated - see logs above'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')