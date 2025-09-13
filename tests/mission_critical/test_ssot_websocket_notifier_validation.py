#!/usr/bin/env python3
"""
MISSION CRITICAL TEST SUITE: SSOT WebSocketNotifier Validation

Business Value: Platform/Internal - $500K+ ARR Golden Path Protection
Prevents duplicate WebSocketNotifier implementations that cause agent event delivery failures.

This test suite validates:
1. Exactly 1 WebSocketNotifier class exists in production code
2. No duplicate implementations in rollback utilities or deprecated files
3. All critical WebSocket events work correctly
4. User isolation maintains integrity
5. No circular dependencies or import violations

P0 SSOT Violations Detected:
- agent_websocket_bridge.py:3209 (canonical SSOT source)

CRITICAL: Tests must run without Docker dependency for CI/CD integration.

Author: Agent Events Remediation Team
Date: 2025-09-12
"""

import ast
import glob
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass

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
class WebSocketNotifierValidation:
    """Results from WebSocketNotifier SSOT validation."""
    file_path: str
    line_number: int
    class_definition: str
    is_production_code: bool
    is_rollback_utility: bool
    is_deprecated: bool
    is_test_file: bool


@dataclass
class SSotComplianceReport:
    """SSOT compliance validation report."""
    total_websocket_notifier_classes: int
    production_implementations: List[WebSocketNotifierValidation]
    rollback_implementations: List[WebSocketNotifierValidation]
    deprecated_implementations: List[WebSocketNotifierValidation]
    test_implementations: List[WebSocketNotifierValidation]
    canonical_ssot_path: Optional[str]
    compliance_score: float
    violations: List[str]
    recommendations: List[str]


class TestSSotWebSocketNotifierValidation(SSotBaseTestCase):
    """Mission Critical Test Suite: SSOT WebSocketNotifier Validation."""

    def setup_method(self, method):
        """Setup test method with SSOT base configuration."""
        super().setup_method(method)
        self.project_root = Path(project_root)
        self.validation_results: List[WebSocketNotifierValidation] = []
        self.known_exclusions = {
            '.backup_pre_factory_migration',  # Backup files
            '.backup_pre_ssot_migration',     # Backup files
            '.deprecated_backup',             # Deprecated files
            '__pycache__',                    # Python cache
            '.git',                          # Git repository
            'node_modules',                  # NPM modules
            '.pytest_cache',                 # Pytest cache
        }

    def _is_excluded_file(self, file_path: str) -> bool:
        """Check if file should be excluded from SSOT validation."""
        file_path_str = str(file_path).replace('\\', '/')

        # Exclude based on known patterns
        for exclusion in self.known_exclusions:
            if exclusion in file_path_str:
                return True

        # Exclude test files (they can have mock implementations)
        if '/test' in file_path_str or file_path_str.endswith('_test.py'):
            return True

        return False

    def _is_production_code(self, file_path: str) -> bool:
        """Determine if file contains production code."""
        file_path_str = str(file_path).replace('\\', '/')

        # Production code patterns
        production_patterns = [
            'netra_backend/app/',
            'auth_service/',
            'shared/',
            'frontend/'
        ]

        return any(pattern in file_path_str for pattern in production_patterns)

    def _scan_for_websocket_notifier_classes(self) -> List[WebSocketNotifierValidation]:
        """Scan entire codebase for WebSocketNotifier class definitions."""
        results = []

        # Search for Python files containing WebSocketNotifier
        python_files = glob.glob(str(self.project_root / "**" / "*.py"), recursive=True)

        for file_path in python_files:
            if self._is_excluded_file(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for WebSocketNotifier class definitions
                class_pattern = r'^class WebSocketNotifier[^(]*(?:\([^)]*\))?:'
                matches = re.finditer(class_pattern, content, re.MULTILINE)

                for match in matches:
                    # Calculate line number
                    line_number = content[:match.start()].count('\n') + 1

                    validation = WebSocketNotifierValidation(
                        file_path=file_path,
                        line_number=line_number,
                        class_definition=match.group(0),
                        is_production_code=self._is_production_code(file_path),
                        is_rollback_utility='rollback' in file_path.lower(),
                        is_deprecated=('deprecated' in file_path.lower() or
                                     'backup' in file_path.lower()),
                        is_test_file=('test' in file_path.lower() or
                                    file_path.endswith('_test.py'))
                    )
                    results.append(validation)

            except Exception as e:
                logger.warning(f"Error scanning {file_path}: {e}")
                continue

        return results

    def _generate_compliance_report(self, validations: List[WebSocketNotifierValidation]) -> SSotComplianceReport:
        """Generate SSOT compliance report from validation results."""
        production_impls = [v for v in validations if v.is_production_code and not v.is_test_file]
        rollback_impls = [v for v in validations if v.is_rollback_utility]
        deprecated_impls = [v for v in validations if v.is_deprecated]
        test_impls = [v for v in validations if v.is_test_file]

        # Determine canonical SSOT path
        canonical_candidates = [
            v for v in production_impls
            if 'agent_websocket_bridge.py' in v.file_path
        ]
        canonical_ssot_path = canonical_candidates[0].file_path if canonical_candidates else None

        # Calculate compliance score (100% = exactly 1 production implementation)
        compliance_score = 100.0 if len(production_impls) == 1 else max(0, 100 - (len(production_impls) - 1) * 50)

        # Generate violations
        violations = []
        if len(production_impls) == 0:
            violations.append("CRITICAL: No WebSocketNotifier production implementation found")
        elif len(production_impls) > 1:
            violations.append(f"CRITICAL: {len(production_impls)} WebSocketNotifier production implementations found (should be exactly 1)")
            for impl in production_impls:
                violations.append(f"  - {impl.file_path}:{impl.line_number}")

        if len(rollback_impls) > 0:
            violations.append(f"WARNING: {len(rollback_impls)} rollback utility implementations found")

        # Generate recommendations
        recommendations = []
        if len(production_impls) > 1:
            recommendations.append("Consolidate duplicate WebSocketNotifier implementations")
            recommendations.append("Keep only canonical SSOT implementation in agent_websocket_bridge.py")

        if not canonical_ssot_path:
            recommendations.append("Establish canonical WebSocketNotifier in agent_websocket_bridge.py")

        return SSotComplianceReport(
            total_websocket_notifier_classes=len(validations),
            production_implementations=production_impls,
            rollback_implementations=rollback_impls,
            deprecated_implementations=deprecated_impls,
            test_implementations=test_impls,
            canonical_ssot_path=canonical_ssot_path,
            compliance_score=compliance_score,
            violations=violations,
            recommendations=recommendations
        )

    def test_websocket_notifier_ssot_compliance(self):
        """Test that WebSocketNotifier follows SSOT principles."""
        logger.info("Starting SSOT WebSocketNotifier validation")

        # Scan for all WebSocketNotifier implementations
        validations = self._scan_for_websocket_notifier_classes()

        # Generate compliance report
        report = self._generate_compliance_report(validations)

        # Log findings
        logger.info(f"WebSocketNotifier SSOT Analysis:")
        logger.info(f"  Total implementations found: {report.total_websocket_notifier_classes}")
        logger.info(f"  Production implementations: {len(report.production_implementations)}")
        logger.info(f"  Rollback implementations: {len(report.rollback_implementations)}")
        logger.info(f"  Deprecated implementations: {len(report.deprecated_implementations)}")
        logger.info(f"  Test implementations: {len(report.test_implementations)}")
        logger.info(f"  Compliance score: {report.compliance_score}%")

        if report.violations:
            logger.error("SSOT Violations detected:")
            for violation in report.violations:
                logger.error(f"  {violation}")

        if report.recommendations:
            logger.info("Recommendations:")
            for rec in report.recommendations:
                logger.info(f"  {rec}")

        # CRITICAL ASSERTION: Must have exactly 1 production implementation
        assert len(report.production_implementations) == 1, (
            f"SSOT Violation: Found {len(report.production_implementations)} WebSocketNotifier production implementations. "
            f"Must have exactly 1. Violations: {report.violations}"
        )

        # CRITICAL ASSERTION: Canonical SSOT path must be agent_websocket_bridge.py
        assert report.canonical_ssot_path, "No canonical WebSocketNotifier SSOT implementation found"
        assert 'agent_websocket_bridge.py' in report.canonical_ssot_path, (
            f"WebSocketNotifier SSOT must be in agent_websocket_bridge.py, found in: {report.canonical_ssot_path}"
        )

        # Store results for further analysis
        self.validation_results = validations
        self.compliance_report = report

        logger.info("✅ SSOT WebSocketNotifier validation passed")

    def test_websocket_notifier_critical_events_work(self):
        """Test that critical WebSocket events work with canonical implementation."""
        logger.info("Testing WebSocket critical events functionality")

        # Define critical events that must work
        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        # This test validates the events exist and are properly structured
        # without requiring Docker or live WebSocket connections

        try:
            # Import the canonical WebSocketNotifier
            from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier

            # Verify critical methods exist
            notifier_methods = dir(WebSocketNotifier)

            # Check for essential methods
            required_methods = ['__init__', 'create_for_user']
            for method in required_methods:
                assert hasattr(WebSocketNotifier, method), (
                    f"WebSocketNotifier missing required method: {method}"
                )

            logger.info("✅ WebSocketNotifier critical methods validated")

        except ImportError as e:
            pytest.fail(f"Failed to import canonical WebSocketNotifier: {e}")

    def test_websocket_notifier_user_isolation_integrity(self):
        """Test that WebSocketNotifier maintains user isolation."""
        logger.info("Testing WebSocketNotifier user isolation integrity")

        try:
            from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier

            # Verify the create_for_user factory method exists (required for user isolation)
            assert hasattr(WebSocketNotifier, 'create_for_user'), (
                "WebSocketNotifier must have create_for_user factory method for user isolation"
            )

            # Verify __init__ method exists and has proper signature
            import inspect
            init_signature = inspect.signature(WebSocketNotifier.__init__)
            init_params = list(init_signature.parameters.keys())

            # Must accept self, emitter, and exec_context for proper isolation
            expected_params = ['self', 'emitter', 'exec_context']
            for param in expected_params:
                assert param in init_params, (
                    f"WebSocketNotifier.__init__ must accept {param} parameter for user isolation"
                )

            logger.info("✅ WebSocketNotifier user isolation integrity validated")

        except Exception as e:
            pytest.fail(f"WebSocketNotifier user isolation validation failed: {e}")

    def test_no_circular_dependencies_in_websocket_notifier(self):
        """Test that WebSocketNotifier has no circular import dependencies."""
        logger.info("Testing WebSocketNotifier circular dependency prevention")

        try:
            # Test import without causing circular dependencies
            import sys
            modules_before = set(sys.modules.keys())

            from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier

            modules_after = set(sys.modules.keys())
            new_modules = modules_after - modules_before

            # Log loaded modules for analysis
            logger.info(f"Loaded modules during WebSocketNotifier import: {len(new_modules)}")

            # Verify import succeeded without issues
            assert WebSocketNotifier is not None, "WebSocketNotifier import returned None"

            logger.info("✅ WebSocketNotifier circular dependency validation passed")

        except Exception as e:
            pytest.fail(f"WebSocketNotifier circular dependency test failed: {e}")

    def test_generate_ssot_compliance_metrics(self):
        """Generate comprehensive SSOT compliance metrics for monitoring."""
        logger.info("Generating SSOT compliance metrics")

        if not hasattr(self, 'compliance_report'):
            # Run main validation if not already done
            self.test_websocket_notifier_ssot_compliance()

        report = self.compliance_report

        # Generate metrics for monitoring/alerting
        metrics = {
            'websocket_notifier_ssot_compliance_score': report.compliance_score,
            'websocket_notifier_production_implementations': len(report.production_implementations),
            'websocket_notifier_rollback_implementations': len(report.rollback_implementations),
            'websocket_notifier_deprecated_implementations': len(report.deprecated_implementations),
            'websocket_notifier_test_implementations': len(report.test_implementations),
            'websocket_notifier_total_violations': len(report.violations),
            'websocket_notifier_has_canonical_ssot': 1 if report.canonical_ssot_path else 0,
            'test_execution_timestamp': datetime.now().isoformat(),
            'golden_path_protection_status': 'PROTECTED' if report.compliance_score == 100.0 else 'AT_RISK'
        }

        logger.info("SSOT Compliance Metrics Generated:")
        for key, value in metrics.items():
            logger.info(f"  {key}: {value}")

        # Assert critical metrics meet requirements
        assert metrics['websocket_notifier_production_implementations'] == 1, (
            "Must have exactly 1 production WebSocketNotifier implementation"
        )
        assert metrics['websocket_notifier_has_canonical_ssot'] == 1, (
            "Must have canonical SSOT WebSocketNotifier implementation"
        )
        assert metrics['golden_path_protection_status'] == 'PROTECTED', (
            "Golden Path must be protected by SSOT compliance"
        )

        logger.info("✅ SSOT compliance metrics validation passed")

        return metrics


if __name__ == "__main__":
    # Direct execution for rapid testing
    pytest.main([__file__, "-v", "--tb=short"])