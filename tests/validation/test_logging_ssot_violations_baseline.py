"""
Baseline Tests: Logging SSOT Violations - Issue #885

Purpose: Validate current state of logging SSOT violations to establish
baseline before remediation. These tests SHOULD FAIL to demonstrate
the problem exists.

Business Impact:
- 1,886 logging import violations reduce operational visibility
- Inconsistent logging patterns make debugging harder
- WebSocket logging issues affect $500K+ ARR chat functionality

Expected Results: FAILURES demonstrating violations exist
"""

import os
import ast
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestLoggingSSOTViolationsBaseline(SSotBaseTestCase):
    """Baseline tests demonstrating current logging SSOT violations"""

    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.violation_count = 0
        self.violations_by_type = {}
        self.critical_files_violations = []

    def test_baseline_logging_import_violations_exist(self):
        """
        BASELINE TEST: Should FAIL - demonstrates deprecated logging imports exist

        This test validates that the problem exists by counting violations.
        Expected: FAILURE with 1,886+ violations found
        """
        violations = self._scan_for_deprecated_logging_imports()

        # This test SHOULD FAIL to prove violations exist
        assert len(violations) == 0, (
            f"BASELINE FAILURE (EXPECTED): Found {len(violations)} deprecated logging imports. "
            f"This proves the SSOT violation problem exists. "
            f"Violations found in: {list(violations.keys())[:10]}..."
        )

    def test_baseline_websocket_logging_inconsistency(self):
        """
        BASELINE TEST: Should FAIL - demonstrates WebSocket logging inconsistency

        Critical for $500K+ ARR chat functionality
        Expected: FAILURE showing inconsistent patterns
        """
        websocket_files = self._find_websocket_related_files()
        logging_patterns = self._analyze_logging_patterns(websocket_files)

        # Count different logging approaches
        pattern_count = len(set(logging_patterns.values()))

        # Should FAIL - we expect multiple different patterns
        assert pattern_count <= 1, (
            f"BASELINE FAILURE (EXPECTED): Found {pattern_count} different logging patterns "
            f"in WebSocket files. This proves inconsistent logging affects chat functionality. "
            f"Patterns: {set(logging_patterns.values())}"
        )

    def test_baseline_critical_services_logging_violations(self):
        """
        BASELINE TEST: Should FAIL - demonstrates violations in critical services

        Tests core business services for logging SSOT compliance
        Expected: FAILURE showing violations in critical paths
        """
        critical_services = [
            "netra_backend/app/websocket_core",
            "netra_backend/app/agents",
            "netra_backend/app/core",
            "auth_service/auth_core"
        ]

        total_violations = 0
        service_violations = {}

        for service in critical_services:
            service_path = self.project_root / service
            if service_path.exists():
                violations = self._scan_directory_for_violations(service_path)
                service_violations[service] = len(violations)
                total_violations += len(violations)

        # Should FAIL - we expect violations in critical services
        assert total_violations == 0, (
            f"BASELINE FAILURE (EXPECTED): Found {total_violations} logging violations "
            f"in critical services. This proves business-critical paths have SSOT issues. "
            f"Service breakdown: {service_violations}"
        )

    def test_baseline_logger_configuration_inconsistency(self):
        """
        BASELINE TEST: Should FAIL - demonstrates logger configuration inconsistency

        Tests for multiple logger configuration approaches
        Expected: FAILURE showing inconsistent configurations
        """
        config_patterns = self._find_logger_configurations()

        # Count unique configuration patterns
        unique_patterns = len(set(config_patterns))

        # Should FAIL - we expect multiple different configuration approaches
        assert unique_patterns <= 1, (
            f"BASELINE FAILURE (EXPECTED): Found {unique_patterns} different logger "
            f"configuration patterns. This proves inconsistent logging setup. "
            f"This affects operational visibility and debugging."
        )

    def _scan_for_deprecated_logging_imports(self) -> Dict[str, List[str]]:
        """Scan for deprecated logging import patterns"""
        violations = {}
        deprecated_patterns = [
            "import logging",
            "from logging import",
            "logging.getLogger",
            "logger = logging"
        ]

        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue

            try:
                content = python_file.read_text(encoding='utf-8')
                file_violations = []

                for pattern in deprecated_patterns:
                    if pattern in content:
                        # Count occurrences
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if pattern in line and not line.strip().startswith('#'):
                                file_violations.append(f"Line {i}: {line.strip()}")

                if file_violations:
                    violations[str(python_file.relative_to(self.project_root))] = file_violations

            except Exception as e:
                # Skip files that can't be read
                continue

        return violations

    def _find_websocket_related_files(self) -> List[Path]:
        """Find WebSocket-related files for analysis"""
        websocket_patterns = [
            "**/websocket*.py",
            "**/manager.py",
            "**/unified_manager.py"
        ]

        files = []
        for pattern in websocket_patterns:
            files.extend(self.project_root.glob(pattern))

        return [f for f in files if self._is_websocket_file(f)]

    def _is_websocket_file(self, file_path: Path) -> bool:
        """Check if file is WebSocket-related"""
        try:
            content = file_path.read_text(encoding='utf-8')
            websocket_indicators = [
                "websocket", "WebSocket", "ws://", "wss://",
                "ConnectionManager", "send_message", "receive_message"
            ]
            return any(indicator in content for indicator in websocket_indicators)
        except:
            return False

    def _analyze_logging_patterns(self, files: List[Path]) -> Dict[str, str]:
        """Analyze logging patterns in given files"""
        patterns = {}

        for file_path in files:
            try:
                content = file_path.read_text(encoding='utf-8')

                # Detect logging pattern
                if "import logging" in content:
                    patterns[str(file_path)] = "standard_logging"
                elif "logger = " in content and "getLogger" in content:
                    patterns[str(file_path)] = "manual_logger"
                elif "self.logger" in content:
                    patterns[str(file_path)] = "instance_logger"
                elif "LoggerMixin" in content:
                    patterns[str(file_path)] = "mixin_logger"
                else:
                    patterns[str(file_path)] = "unknown_or_none"

            except:
                patterns[str(file_path)] = "read_error"

        return patterns

    def _scan_directory_for_violations(self, directory: Path) -> List[str]:
        """Scan directory for logging violations"""
        violations = []

        for python_file in directory.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue

            try:
                content = python_file.read_text(encoding='utf-8')

                # Check for deprecated patterns
                if "import logging" in content and "# SSOT" not in content:
                    violations.append(str(python_file.relative_to(self.project_root)))

            except:
                continue

        return violations

    def _find_logger_configurations(self) -> List[str]:
        """Find different logger configuration patterns"""
        config_patterns = []

        config_files = list(self.project_root.rglob("*config*.py")) + \
                      list(self.project_root.rglob("*settings*.py")) + \
                      list(self.project_root.rglob("*logging*.py"))

        for config_file in config_files:
            if self._should_skip_file(config_file):
                continue

            try:
                content = config_file.read_text(encoding='utf-8')

                # Detect configuration patterns
                if "logging.basicConfig" in content:
                    config_patterns.append("basicConfig")
                elif "logging.config.dictConfig" in content:
                    config_patterns.append("dictConfig")
                elif "LoggerFactory" in content:
                    config_patterns.append("factory_pattern")
                elif "LOGGING = {" in content:
                    config_patterns.append("django_style")
                elif "logger.setLevel" in content:
                    config_patterns.append("manual_setup")

            except:
                continue

        return config_patterns

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning"""
        skip_patterns = [
            "__pycache__", ".git", ".venv", "venv", "node_modules",
            ".pytest_cache", "build", "dist", ".tox"
        ]

        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)


if __name__ == "__main__":
    # Run tests to demonstrate violations exist
    pytest.main([__file__, "-v", "--tb=short"])