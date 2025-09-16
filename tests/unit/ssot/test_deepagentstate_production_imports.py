"""
FAILING TESTS: DeepAgentState Production Import Violations (Issue #871)

These tests SCAN production files and FAIL when deprecated DeepAgentState imports are found.
Tests will PASS only AFTER all 28 production files are migrated to SSOT source.

Business Impact: $500K+ ARR protection from multi-tenant security breach.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.user_execution_context import UserExecutionContext


@pytest.mark.unit
class DeepAgentStateProductionImportsTests(SSotAsyncTestCase):
    """Test suite proving production files still use deprecated DeepAgentState imports"""

    def setup_method(self, method):
        super().setup_method(method)
        self.netra_backend_root = Path(__file__).parent.parent.parent.parent
        self._setup_known_violation_files()

    def _setup_known_violation_files(self):
        """Initialize list of 28 production files with known DeepAgentState violations"""

        # Based on Issue #871 audit findings - 28 production files
        self.known_violation_files = [
            # Supervisor execution components (critical Golden Path)
            "netra_backend/app/agents/supervisor/execution_engine.py",
            "netra_backend/app/agents/supervisor/pipeline_executor.py",
            "netra_backend/app/agents/supervisor/workflow_orchestrator.py",
            "netra_backend/app/agents/supervisor/user_execution_engine.py",
            "netra_backend/app/agents/supervisor/mcp_execution_engine.py",
            "netra_backend/app/agents/supervisor/agent_execution_core.py",
            "netra_backend/app/agents/supervisor/agent_routing.py",

            # WebSocket core components (business critical)
            "netra_backend/app/websocket_core/unified_manager.py",
            "netra_backend/app/websocket_core/connection_executor.py",
            "netra_backend/app/websocket_core/agent_bridge.py",

            # Core agent implementations
            "netra_backend/app/agents/base_agent.py",
            "netra_backend/app/agents/triage_agent.py",
            "netra_backend/app/agents/supervisor_agent_modern.py",
            "netra_backend/app/agents/reporting_sub_agent.py",
            "netra_backend/app/agents/data_helper_agent.py",
            "netra_backend/app/agents/apex_optimizer_agent.py",

            # Agent factories and registries
            "netra_backend/app/agents/registry.py",
            "netra_backend/app/agents/factories/agent_factory.py",
            "netra_backend/app/agents/factories/execution_factory.py",

            # Service components
            "netra_backend/app/services/agent_service.py",
            "netra_backend/app/services/state_persistence_optimized.py",
            "netra_backend/app/services/user_execution_context.py",

            # Tools and dispatchers
            "netra_backend/app/tools/enhanced_dispatcher.py",
            "netra_backend/app/tools/tool_executor.py",

            # Route handlers
            "netra_backend/app/routes/websocket.py",
            "netra_backend/app/routes/agents.py",

            # Core schemas (migration adapters)
            "netra_backend/app/agents/migration/deepagentstate_adapter.py",
            "netra_backend/app/schemas/response_models.py"
        ]

    def test_scan_all_known_violation_files(self):
        """
        FAILING TEST: Scans all 28 known production files for deprecated imports

        Expected: FAIL with ~28 violations initially
        After Fix: PASS with 0 violations
        """
        violations_found = {}
        missing_files = []

        for file_path in self.known_violation_files:
            full_path = self.netra_backend_root / file_path

            if not full_path.exists():
                missing_files.append(file_path)
                continue

            violations = self._scan_file_for_deprecated_imports(full_path)
            if violations:
                violations_found[file_path] = violations

        # Report missing files (they may have been moved/renamed)
        if missing_files:
            self.logger.warning(f"Missing expected files: {missing_files}")

        # This assertion will FAIL initially - proving violations exist
        violation_count = len(violations_found)

        if violation_count > 0:
            violation_report = self._build_violation_report(violations_found)
            pytest.fail(f"""
🚨 ISSUE #871 - DEEPAGENTSTATE PRODUCTION IMPORT VIOLATIONS DETECTED

Found deprecated DeepAgentState imports in {violation_count} production files:

{violation_report}

SECURITY RISK: Multi-tenant user isolation vulnerability exists.
BUSINESS IMPACT: $500K+ ARR at risk from cross-user data contamination.

REMEDIATION REQUIRED:
1. Replace all deprecated imports with: from netra_backend.app.schemas.agent_models import DeepAgentState
2. Update code to use SSOT DeepAgentState consistently
3. Remove deprecated DeepAgentState from netra_backend.app.agents.state module

TRACKING: Issue #871 - P0 Critical SSOT violation
            """)

    def test_scan_critical_golden_path_components(self):
        """
        FAILING TEST: Focuses on Golden Path critical components

        These files are essential for $500K+ ARR chat functionality.
        Expected: FAIL if any critical files use deprecated imports
        """
        critical_golden_path_files = [
            "netra_backend/app/agents/supervisor/execution_engine.py",
            "netra_backend/app/websocket_core/unified_manager.py",
            "netra_backend/app/agents/base_agent.py",
            "netra_backend/app/routes/websocket.py"
        ]

        critical_violations = {}

        for file_path in critical_golden_path_files:
            full_path = self.netra_backend_root / file_path

            if full_path.exists():
                violations = self._scan_file_for_deprecated_imports(full_path)
                if violations:
                    critical_violations[file_path] = violations

        # Critical files MUST be clean for Golden Path protection
        if critical_violations:
            critical_report = self._build_violation_report(critical_violations)
            pytest.fail(f"""
🚨 CRITICAL GOLDEN PATH VIOLATIONS - IMMEDIATE ACTION REQUIRED

DeepAgentState violations found in CRITICAL Golden Path components:

{critical_report}

IMPACT: Core chat functionality ($500K+ ARR) depends on these components.
PRIORITY: P0 - Fix these files FIRST to protect business value.

Golden Path Requirements:
- User isolation MUST be enforced in execution_engine.py
- WebSocket events MUST maintain state consistency
- Agent creation MUST prevent cross-user contamination
            """)

    def test_validate_ssot_source_integrity(self):
        """
        FAILING TEST: Ensures SSOT source remains authoritative

        Expected: PASS (SSOT source should always be clean)
        """
        ssot_file = "netra_backend/app/schemas/agent_models.py"
        ssot_path = self.netra_backend_root / ssot_file

        if not ssot_path.exists():
            pytest.fail(f"SSOT SOURCE MISSING: {ssot_file} not found!")

        # SSOT file should NOT import deprecated DeepAgentState
        violations = self._scan_file_for_deprecated_imports(ssot_path)

        if violations:
            pytest.fail(f"""
🚨 SSOT SOURCE COMPROMISED

The authoritative SSOT source has deprecated import violations:
File: {ssot_file}
Violations: {violations}

This indicates the SSOT source itself is importing the deprecated version!
IMMEDIATE FIX REQUIRED: Clean the authoritative source first.
            """)

    def test_measure_migration_progress(self):
        """
        PROGRESS TRACKER: Measures migration completion percentage

        This test provides progress metrics but doesn't fail.
        Used to track remediation progress over time.
        """
        total_files_scanned = 0
        files_with_violations = 0
        total_violations = 0

        # Scan broader codebase for comprehensive measurement
        scan_directories = [
            "netra_backend/app/agents",
            "netra_backend/app/websocket_core",
            "netra_backend/app/services",
            "netra_backend/app/routes",
            "netra_backend/app/tools"
        ]

        all_violations = {}

        for scan_dir in scan_directories:
            dir_violations = self._scan_directory_recursively(scan_dir)
            all_violations.update(dir_violations)

        total_files_scanned = len(self._get_all_python_files(scan_directories))
        files_with_violations = len(all_violations)
        total_violations = sum(len(violations) for violations in all_violations.values())

        # Calculate progress metrics
        files_clean_percentage = ((total_files_scanned - files_with_violations) / total_files_scanned * 100) if total_files_scanned > 0 else 0

        progress_report = f"""
📊 MIGRATION PROGRESS REPORT (Issue #871)

Files Scanned: {total_files_scanned}
Files with Violations: {files_with_violations}
Files Clean: {total_files_scanned - files_with_violations}
Clean Percentage: {files_clean_percentage:.1f}%

Total Violations: {total_violations}
Known Critical Files: {len(self.known_violation_files)}

Progress Status: {"🔴 REMEDIATION NEEDED" if files_with_violations > 0 else "✅ MIGRATION COMPLETE"}
        """

        self.logger.info(progress_report)

        # For visibility in test output, always log current status
        print(f"\n{progress_report}")

    def _scan_file_for_deprecated_imports(self, file_path: Path) -> List[str]:
        """Scan a single file for deprecated DeepAgentState imports"""
        violations = []

        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            # Pattern 1: Direct deprecated import
            if 'from netra_backend.app.schemas.agent_models import DeepAgentState' in content:
                violations.append("Direct deprecated import: 'from netra_backend.app.schemas.agent_models import DeepAgentState'")

            # Pattern 2: Wildcard import including DeepAgentState
            if 'from netra_backend.app.schemas.agent_models import DeepAgentState' in content:
                violations.append("Wildcard import with DeepAgentState usage")

            # Pattern 3: Multi-line import including DeepAgentState
            import_patterns = [
                'from netra_backend.app.agents.state import (',
                'from netra_backend.app.schemas.agent_models import DeepAgentState,',
                ', DeepAgentState'
            ]

            for pattern in import_patterns:
                if pattern in content:
                    violations.append(f"Multi-line import pattern: '{pattern}'")

            # Pattern 4: Usage indicators (might be using imported DeepAgentState)
            for i, line in enumerate(lines, 1):
                if 'UserExecutionContext.create_isolated_context(user_id="test_user", ' in line or 'state: DeepAgentState' in line:
                    violations.append(f"Usage at line {i}: {line.strip()}")

        except Exception as e:
            violations.append(f"Scan error: {str(e)}")

        return violations

    def _scan_directory_recursively(self, dir_path: str) -> Dict[str, List[str]]:
        """Recursively scan directory for deprecated imports"""
        violations = {}
        search_path = self.netra_backend_root / dir_path

        if not search_path.exists():
            return violations

        for py_file in search_path.rglob("*.py"):
            # Skip test files and cache directories
            if self._should_skip_file(py_file):
                continue

            relative_path = py_file.relative_to(self.netra_backend_root)
            file_violations = self._scan_file_for_deprecated_imports(py_file)

            if file_violations:
                violations[str(relative_path)] = file_violations

        return violations

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped during scanning"""
        skip_patterns = [
            'test_',
            '__pycache__',
            '.pytest_cache',
            'conftest.py',
            'migration/', # Skip migration utilities themselves
        ]

        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)

    def _get_all_python_files(self, directories: List[str]) -> List[Path]:
        """Get list of all Python files in given directories"""
        all_files = []

        for dir_path in directories:
            search_path = self.netra_backend_root / dir_path
            if search_path.exists():
                for py_file in search_path.rglob("*.py"):
                    if not self._should_skip_file(py_file):
                        all_files.append(py_file)

        return all_files

    def _build_violation_report(self, violations: Dict[str, List[str]]) -> str:
        """Build formatted violation report for test failure messages"""
        report_lines = []

        for file_path, file_violations in violations.items():
            report_lines.append(f"📁 {file_path}:")
            for violation in file_violations:
                report_lines.append(f"   ⚠️  {violation}")
            report_lines.append("")

        return '\n'.join(report_lines)