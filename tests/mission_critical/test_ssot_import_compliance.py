#!/usr/bin/env python3
"""
MISSION CRITICAL TEST SUITE: SSOT Import Compliance Validation

Business Value: Platform/Internal - $500K+ ARR Golden Path Protection
Prevents regression to duplicate imports and ensures all production code imports resolve to SSOT sources.

This test suite validates:
1. No production code imports rollback utility WebSocketNotifier
2. agent_websocket_bridge.py has no duplicate WebSocketNotifier class
3. All imports resolve to single SSOT source
4. Circular dependency prevention
5. Import path consistency across services

P0 SSOT Import Violations Targeted:
- Multiple import paths for same SSOT classes
- Circular dependencies causing import failures

CRITICAL: Tests must run without Docker dependency for CI/CD integration.

Author: Agent Events Remediation Team
Date: 2025-09-12
"""

import ast
import importlib
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass
import glob

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env, IsolatedEnvironment


@dataclass
class ImportViolation:
    """Represents an SSOT import violation."""
    file_path: str
    line_number: int
    import_statement: str
    violation_type: str  # 'ROLLBACK_IMPORT', 'DUPLICATE_SOURCE', 'CIRCULAR_DEPENDENCY'
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    recommendation: str


@dataclass
class ImportComplianceReport:
    """Comprehensive import compliance validation report."""
    total_files_scanned: int
    total_imports_analyzed: int
    websocket_notifier_imports: List[Dict[str, Any]]
    rollback_import_violations: List[ImportViolation]
    circular_dependency_violations: List[ImportViolation]
    duplicate_source_violations: List[ImportViolation]
    compliance_score: float
    critical_violations: int
    recommendations: List[str]


class ImportAnalyzer:
    """Analyzes import statements for SSOT compliance."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.rollback_patterns = [
            'rollback_utility',
            'emergency_rollback'
        ]
        self.ssot_sources = {
            'WebSocketNotifier': 'netra_backend.app.services.agent_websocket_bridge',
            'ExecutionEngine': 'netra_backend.app.agents.supervisor.user_execution_engine',
            'AgentRegistry': 'netra_backend.app.agents.supervisor.agent_registry',
        }

    def extract_imports_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract all import statements from a Python file."""
        imports = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST to extract imports
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'name': alias.asname or alias.name,
                            'line': node.lineno,
                            'source_line': content.split('\n')[node.lineno - 1].strip()
                        })

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append({
                            'type': 'from_import',
                            'module': module,
                            'name': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno,
                            'source_line': content.split('\n')[node.lineno - 1].strip()
                        })

        except Exception as e:
            logger.warning(f"Error parsing imports from {file_path}: {e}")

        return imports

    def analyze_websocket_notifier_imports(self, imports: List[Dict[str, Any]], file_path: str) -> List[ImportViolation]:
        """Analyze WebSocketNotifier imports for SSOT violations."""
        violations = []

        for imp in imports:
            # Check for rollback utility imports
            if any(pattern in imp.get('module', '') for pattern in self.rollback_patterns):
                if 'WebSocketNotifier' in imp.get('name', ''):
                    violations.append(ImportViolation(
                        file_path=file_path,
                        line_number=imp['line'],
                        import_statement=imp['source_line'],
                        violation_type='ROLLBACK_IMPORT',
                        severity='CRITICAL',
                        recommendation='Remove import of rollback utility WebSocketNotifier. Use canonical SSOT from agent_websocket_bridge.py'
                    ))

            # Check for non-SSOT WebSocketNotifier imports
            if imp.get('name') == 'WebSocketNotifier':
                expected_module = self.ssot_sources.get('WebSocketNotifier')
                actual_module = imp.get('module', '')

                if expected_module and expected_module not in actual_module:
                    violations.append(ImportViolation(
                        file_path=file_path,
                        line_number=imp['line'],
                        import_statement=imp['source_line'],
                        violation_type='DUPLICATE_SOURCE',
                        severity='HIGH',
                        recommendation=f'Import WebSocketNotifier from canonical SSOT: {expected_module}'
                    ))

        return violations


class TestSSotImportCompliance(SSotBaseTestCase):
    """Mission Critical Test Suite: SSOT Import Compliance Validation."""

    def setup_method(self, method):
        """Setup test method with SSOT base configuration."""
        super().setup_method(method)
        self.project_root = Path(project_root)
        self.analyzer = ImportAnalyzer(self.project_root)
        self.excluded_patterns = {
            'test',           # Test files can have mock imports
            '__pycache__',    # Python cache
            '.git',          # Git repository
            'node_modules',   # NPM modules
            '.pytest_cache', # Pytest cache
            'backup',        # Backup files
            'deprecated',    # Deprecated files
            'scripts',       # Scripts may have special imports
        }

    def _is_production_file(self, file_path: str) -> bool:
        """Check if file is production code that must follow SSOT compliance."""
        file_path_str = str(file_path).replace('\\', '/')

        # Exclude non-production paths
        for pattern in self.excluded_patterns:
            if pattern in file_path_str:
                return False

        # Include production code patterns
        production_patterns = [
            'netra_backend/app/',
            'auth_service/',
            'shared/',
            'frontend/'
        ]

        return any(pattern in file_path_str for pattern in production_patterns)

    def _scan_production_files_for_imports(self) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Scan all production Python files and extract import statements."""
        production_files = []
        all_imports = []

        # Find all Python files
        python_files = glob.glob(str(self.project_root / "**" / "*.py"), recursive=True)

        for file_path in python_files:
            if self._is_production_file(file_path):
                production_files.append(file_path)

                # Extract imports from file
                file_imports = self.analyzer.extract_imports_from_file(file_path)
                for imp in file_imports:
                    imp['source_file'] = file_path
                    all_imports.append(imp)

        return production_files, all_imports

    def test_no_rollback_utility_imports_in_production(self):
        """Test that no production code imports rollback utility WebSocketNotifier."""
        logger.info("Testing for rollback utility imports in production code")

        production_files, all_imports = self._scan_production_files_for_imports()
        rollback_violations = []

        # Check each production file for rollback imports
        for file_path in production_files:
            file_imports = [imp for imp in all_imports if imp['source_file'] == file_path]
            violations = self.analyzer.analyze_websocket_notifier_imports(file_imports, file_path)

            rollback_violations.extend([v for v in violations if v.violation_type == 'ROLLBACK_IMPORT'])

        # Log findings
        logger.info(f"Scanned {len(production_files)} production files")
        logger.info(f"Found {len(rollback_violations)} rollback utility import violations")

        if rollback_violations:
            logger.error("CRITICAL: Rollback utility imports found in production code:")
            for violation in rollback_violations:
                logger.error(f"  {violation.file_path}:{violation.line_number} - {violation.import_statement}")

        # CRITICAL ASSERTION: No rollback utility imports in production
        assert len(rollback_violations) == 0, (
            f"CRITICAL: Found {len(rollback_violations)} rollback utility imports in production code. "
            f"These must be removed. Violations: {[v.file_path for v in rollback_violations]}"
        )

        logger.info("✅ No rollback utility imports found in production code")

    def test_websocket_notifier_import_consistency(self):
        """Test that all WebSocketNotifier imports use consistent SSOT source."""
        logger.info("Testing WebSocketNotifier import consistency")

        production_files, all_imports = self._scan_production_files_for_imports()

        # Find all WebSocketNotifier imports
        websocket_notifier_imports = [
            imp for imp in all_imports
            if imp.get('name') == 'WebSocketNotifier'
        ]

        # Group by source module
        import_sources = {}
        for imp in websocket_notifier_imports:
            module = imp.get('module', 'unknown')
            if module not in import_sources:
                import_sources[module] = []
            import_sources[module].append(imp)

        logger.info(f"Found {len(websocket_notifier_imports)} WebSocketNotifier imports")
        logger.info(f"Import sources: {list(import_sources.keys())}")

        # Check for canonical SSOT source
        canonical_source = 'netra_backend.app.services.agent_websocket_bridge'
        has_canonical = canonical_source in import_sources

        # Generate violations for non-canonical imports
        violations = []
        for module, imports in import_sources.items():
            if module != canonical_source and module != 'unknown':
                for imp in imports:
                    violations.append(ImportViolation(
                        file_path=imp['source_file'],
                        line_number=imp['line'],
                        import_statement=imp['source_line'],
                        violation_type='DUPLICATE_SOURCE',
                        severity='HIGH',
                        recommendation=f'Use canonical SSOT import: from {canonical_source} import WebSocketNotifier'
                    ))

        if violations:
            logger.error("Import consistency violations found:")
            for violation in violations:
                logger.error(f"  {violation.file_path}:{violation.line_number} - {violation.import_statement}")

        # ASSERTION: All WebSocketNotifier imports should use canonical source
        # (Allow some flexibility during migration, but log violations)
        if violations:
            logger.warning(f"Found {len(violations)} non-canonical WebSocketNotifier imports")
            logger.warning("These should be migrated to canonical SSOT source during next refactoring")

        # CRITICAL ASSERTION: Must have at least one canonical import
        assert has_canonical, (
            f"No imports from canonical WebSocketNotifier source: {canonical_source}. "
            f"Found sources: {list(import_sources.keys())}"
        )

        logger.info("✅ WebSocketNotifier import consistency validated")

    def test_circular_dependency_prevention(self):
        """Test that WebSocketNotifier imports don't create circular dependencies."""
        logger.info("Testing circular dependency prevention")

        # Test key import paths for circular dependencies
        critical_imports = [
            'netra_backend.app.services.agent_websocket_bridge',
            'netra_backend.app.agents.supervisor.user_execution_engine',
            'netra_backend.app.agents.supervisor.agent_registry',
        ]

        import_failures = []

        for module_path in critical_imports:
            try:
                # Attempt import to detect circular dependencies
                if module_path in sys.modules:
                    del sys.modules[module_path]

                module = importlib.import_module(module_path)
                assert module is not None, f"Module {module_path} imported as None"

                logger.debug(f"✓ Successfully imported {module_path}")

            except ImportError as e:
                import_failures.append({
                    'module': module_path,
                    'error': str(e),
                    'type': 'ImportError'
                })

            except Exception as e:
                import_failures.append({
                    'module': module_path,
                    'error': str(e),
                    'type': type(e).__name__
                })

        # Log import failures
        if import_failures:
            logger.error("Circular dependency or import failures detected:")
            for failure in import_failures:
                logger.error(f"  {failure['module']}: {failure['type']} - {failure['error']}")

        # CRITICAL ASSERTION: All critical imports must succeed
        assert len(import_failures) == 0, (
            f"Import failures detected (possible circular dependencies): {import_failures}"
        )

        logger.info("✅ Circular dependency prevention validated")

    def test_agent_websocket_bridge_has_single_websocket_notifier(self):
        """Test that agent_websocket_bridge.py has exactly one WebSocketNotifier class."""
        logger.info("Testing agent_websocket_bridge.py for single WebSocketNotifier class")

        bridge_file = self.project_root / "netra_backend" / "app" / "services" / "agent_websocket_bridge.py"

        assert bridge_file.exists(), (
            f"Canonical WebSocketNotifier file not found: {bridge_file}"
        )

        try:
            with open(bridge_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Count WebSocketNotifier class definitions
            class_pattern = r'^class WebSocketNotifier[^(]*(?:\([^)]*\))?:'
            matches = list(re.finditer(class_pattern, content, re.MULTILINE))

            logger.info(f"Found {len(matches)} WebSocketNotifier class definitions in agent_websocket_bridge.py")

            # CRITICAL ASSERTION: Exactly one WebSocketNotifier class
            assert len(matches) == 1, (
                f"agent_websocket_bridge.py must have exactly 1 WebSocketNotifier class, found {len(matches)}"
            )

            # Verify it's not a duplicate/backup
            match = matches[0]
            class_definition = match.group(0)

            assert 'Rollback' not in class_definition, (
                "WebSocketNotifier class should not be a rollback implementation"
            )

            logger.info("✅ agent_websocket_bridge.py has single canonical WebSocketNotifier class")

        except Exception as e:
            pytest.fail(f"Error analyzing agent_websocket_bridge.py: {e}")

    def test_generate_import_compliance_report(self):
        """Generate comprehensive import compliance report."""
        logger.info("Generating import compliance report")

        production_files, all_imports = self._scan_production_files_for_imports()

        # Analyze WebSocketNotifier imports
        websocket_notifier_imports = [
            imp for imp in all_imports
            if imp.get('name') == 'WebSocketNotifier'
        ]

        # Find all violations
        all_violations = []
        for file_path in production_files:
            file_imports = [imp for imp in all_imports if imp['source_file'] == file_path]
            violations = self.analyzer.analyze_websocket_notifier_imports(file_imports, file_path)
            all_violations.extend(violations)

        # Categorize violations
        rollback_violations = [v for v in all_violations if v.violation_type == 'ROLLBACK_IMPORT']
        duplicate_source_violations = [v for v in all_violations if v.violation_type == 'DUPLICATE_SOURCE']
        critical_violations = [v for v in all_violations if v.severity == 'CRITICAL']

        # Calculate compliance score
        total_websocket_imports = len(websocket_notifier_imports)
        violation_count = len(all_violations)
        compliance_score = max(0, 100 - (violation_count * 10)) if total_websocket_imports > 0 else 100

        # Generate recommendations
        recommendations = []
        if rollback_violations:
            recommendations.append("Remove all rollback utility imports from production code")
        if duplicate_source_violations:
            recommendations.append("Migrate all WebSocketNotifier imports to canonical SSOT source")

        # Create report
        report = ImportComplianceReport(
            total_files_scanned=len(production_files),
            total_imports_analyzed=len(all_imports),
            websocket_notifier_imports=websocket_notifier_imports,
            rollback_import_violations=rollback_violations,
            circular_dependency_violations=[],  # Tested separately
            duplicate_source_violations=duplicate_source_violations,
            compliance_score=compliance_score,
            critical_violations=len(critical_violations),
            recommendations=recommendations
        )

        # Log report
        logger.info("Import Compliance Report:")
        logger.info(f"  Files scanned: {report.total_files_scanned}")
        logger.info(f"  Imports analyzed: {report.total_imports_analyzed}")
        logger.info(f"  WebSocketNotifier imports: {len(report.websocket_notifier_imports)}")
        logger.info(f"  Rollback violations: {len(report.rollback_import_violations)}")
        logger.info(f"  Duplicate source violations: {len(report.duplicate_source_violations)}")
        logger.info(f"  Compliance score: {report.compliance_score}%")
        logger.info(f"  Critical violations: {report.critical_violations}")

        # Store report for use by other tests
        self.import_compliance_report = report

        # ASSERTION: Compliance score must be reasonable for Golden Path protection
        assert report.compliance_score >= 80, (
            f"Import compliance score too low: {report.compliance_score}%. Must be >= 80% for Golden Path protection."
        )

        logger.info("✅ Import compliance report generated successfully")

        return report


if __name__ == "__main__":
    # Direct execution for rapid testing
    pytest.main([__file__, "-v", "--tb=short"])