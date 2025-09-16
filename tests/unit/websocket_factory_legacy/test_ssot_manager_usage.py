"""
Test SSOT WebSocket Manager Usage Patterns - Issue #1098

CRITICAL: This test must FAIL initially to prove SSOT violations exist.
After SSOT migration, this test must PASS to prove success.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: Ensure all WebSocket managers use SSOT patterns exclusively
- Value Impact: Prevents multiple manager instances from breaking Golden Path
- Revenue Impact: Protects $500K+ ARR by ensuring consistent WebSocket behavior

FAILING TEST STRATEGY:
1. Test initially FAILS proving non-SSOT manager usage
2. SSOT migration consolidates to UnifiedWebSocketManager
3. Test PASSES proving SSOT compliance achieved
"""

import pytest
import ast
import glob
import os
import re
from typing import List, Dict, Set, Tuple
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestSSoTManagerUsage(SSotBaseTestCase):
    """
    Unit tests to validate SSOT WebSocket Manager usage patterns.

    CRITICAL: These tests are designed to FAIL initially, proving SSOT violations exist.
    After remediation, they must PASS to prove SSOT compliance achieved.
    """

    def setUp(self):
        """Set up test environment for SSOT manager usage validation."""
        super().setUp()
        self.netra_apex_root = "/c/netra-apex"

        # SSOT-compliant patterns (these should be used)
        self.ssot_patterns = [
            "UnifiedWebSocketManager",
            "_UnifiedWebSocketManagerImplementation",
            "from netra_backend.app.websocket_core.unified_manager import",
            "from netra_backend.app.websocket_core.canonical_imports import"
        ]

        # Non-SSOT patterns (these violate SSOT)
        self.violation_patterns = [
            "WebSocketManagerFactory",
            "IsolatedWebSocketManager",
            "ConnectionLifecycleManager",
            "FactoryInitializationError",
            "factory.create_manager",
            "manager_factory.get_instance",
            "websocket_manager_factory."
        ]

        # Expected SSOT implementation
        self.expected_ssot_manager = "UnifiedWebSocketManager"

    def test_direct_manager_instantiation_forbidden(self):
        """
        Test that WebSocket managers are NOT created via direct instantiation

        CRITICAL: Must detect direct instantiation violations
        """
        direct_instantiation_violations = []

        python_files = self._get_websocket_related_files()

        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue

            violations = self._scan_for_direct_instantiation(py_file)
            direct_instantiation_violations.extend(violations)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(direct_instantiation_violations) == 0, (
            f"DIRECT INSTANTIATION VIOLATIONS: Found {len(direct_instantiation_violations)} "
            f"direct WebSocket manager instantiation violations.\n"
            f"SSOT requires factory-based creation only.\n"
            f"Violations:\n{self._format_violations(direct_instantiation_violations[:5])}"
        )

    def test_unified_websocket_manager_ssot_usage(self):
        """
        Test that all managers use UnifiedWebSocketManager SSOT implementation

        CRITICAL: Validates SSOT consolidation compliance
        """
        non_ssot_manager_usage = []
        missing_ssot_usage = []

        python_files = self._get_websocket_related_files()

        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue

            # Check for non-SSOT usage
            violations = self._scan_for_non_ssot_usage(py_file)
            non_ssot_manager_usage.extend(violations)

            # Check for missing SSOT usage where needed
            if self._needs_websocket_manager(py_file):
                if not self._has_ssot_manager_usage(py_file):
                    missing_ssot_usage.append(py_file)

        # CRITICAL: These assertions MUST FAIL initially
        assert len(non_ssot_manager_usage) == 0, (
            f"NON-SSOT MANAGER USAGE: Found {len(non_ssot_manager_usage)} "
            f"non-SSOT manager usage violations.\n"
            f"All managers must use UnifiedWebSocketManager SSOT.\n"
            f"Violations:\n{self._format_violations(non_ssot_manager_usage[:5])}"
        )

        if missing_ssot_usage:
            assert len(missing_ssot_usage) == 0, (
                f"MISSING SSOT USAGE: {len(missing_ssot_usage)} files need WebSocket "
                f"functionality but don't use SSOT patterns.\n"
                f"Files: {missing_ssot_usage[:5]}"
            )

    def test_multiple_websocket_manager_types_forbidden(self):
        """
        Test that only ONE WebSocket manager type exists (SSOT)

        CRITICAL: Detects multiple manager implementations violating SSOT
        """
        manager_types_found = set()
        files_with_multiple_types = []

        python_files = self._get_websocket_related_files()

        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue

            file_manager_types = self._identify_manager_types_in_file(py_file)
            manager_types_found.update(file_manager_types)

            if len(file_manager_types) > 1:
                files_with_multiple_types.append({
                    'file': py_file,
                    'types': file_manager_types
                })

        # CRITICAL: This assertion MUST FAIL initially
        assert len(manager_types_found) <= 1, (
            f"MULTIPLE MANAGER TYPES VIOLATION: Found {len(manager_types_found)} "
            f"different WebSocket manager types. SSOT requires exactly ONE.\n"
            f"Manager types found: {list(manager_types_found)}\n"
            f"Expected: ['{self.expected_ssot_manager}'] only"
        )

        assert len(files_with_multiple_types) == 0, (
            f"FILES WITH MULTIPLE MANAGER TYPES: {len(files_with_multiple_types)} files "
            f"use multiple manager types violating SSOT.\n"
            f"Files: {[f['file'].split('/')[-1] for f in files_with_multiple_types[:3]]}"
        )

    def test_websocket_notifier_ssot_compliance(self):
        """
        Test WebSocket notifier uses SSOT patterns exclusively

        CRITICAL: Validates notifier SSOT compliance
        """
        notifier_violations = []
        multiple_notifier_implementations = []

        # Find all notifier files
        notifier_files = self._find_notifier_files()

        # Check for SSOT violations in notifiers
        for notifier_file in notifier_files:
            if self._should_skip_file(notifier_file):
                continue

            violations = self._scan_notifier_ssot_compliance(notifier_file)
            notifier_violations.extend(violations)

        # Check for multiple notifier implementations
        notifier_implementations = self._identify_notifier_implementations()

        if len(notifier_implementations) > 1:
            multiple_notifier_implementations = notifier_implementations

        # CRITICAL: These assertions MUST FAIL initially
        assert len(notifier_violations) == 0, (
            f"NOTIFIER SSOT VIOLATIONS: Found {len(notifier_violations)} "
            f"notifier SSOT compliance violations.\n"
            f"Violations:\n{self._format_violations(notifier_violations[:5])}"
        )

        assert len(multiple_notifier_implementations) <= 1, (
            f"MULTIPLE NOTIFIER IMPLEMENTATIONS: Found {len(multiple_notifier_implementations)} "
            f"notifier implementations. SSOT requires exactly ONE.\n"
            f"Implementations: {multiple_notifier_implementations}"
        )

    def test_user_context_isolation_ssot_compliance(self):
        """
        Test that user context isolation uses SSOT patterns

        CRITICAL: Validates user isolation SSOT compliance for multi-user system
        """
        isolation_violations = []

        python_files = self._get_user_context_files()

        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue

            violations = self._scan_user_context_isolation_ssot(py_file)
            isolation_violations.extend(violations)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(isolation_violations) == 0, (
            f"USER ISOLATION SSOT VIOLATIONS: Found {len(isolation_violations)} "
            f"user context isolation violations.\n"
            f"SSOT requires factory-based user isolation.\n"
            f"Violations:\n{self._format_violations(isolation_violations[:5])}"
        )

    def test_websocket_event_delivery_ssot_compliance(self):
        """
        Test that WebSocket event delivery uses SSOT patterns

        CRITICAL: Validates the 5 critical events use SSOT delivery
        """
        event_delivery_violations = []

        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        # Files that handle event delivery
        event_files = [
            "/c/netra-apex/netra_backend/app/agents/supervisor/execution_engine.py",
            "/c/netra-apex/netra_backend/app/tools/enhanced_dispatcher.py",
            "/c/netra-apex/netra_backend/app/websocket_core/unified_manager.py"
        ]

        for event_file in event_files:
            if not os.path.exists(event_file) or self._should_skip_file(event_file):
                continue

            violations = self._scan_event_delivery_ssot(event_file, critical_events)
            event_delivery_violations.extend(violations)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(event_delivery_violations) == 0, (
            f"EVENT DELIVERY SSOT VIOLATIONS: Found {len(event_delivery_violations)} "
            f"event delivery SSOT violations.\n"
            f"All 5 critical events must use SSOT delivery patterns.\n"
            f"Violations:\n{self._format_violations(event_delivery_violations[:5])}"
        )

    # Helper methods for SSOT validation

    def _get_websocket_related_files(self) -> List[str]:
        """Get all files that use WebSocket functionality."""
        patterns = [
            f"{self.netra_apex_root}/**/websocket*.py",
            f"{self.netra_apex_root}/**/manager*.py",
            f"{self.netra_apex_root}/**/agent*.py",
            f"{self.netra_apex_root}/**/execution*.py",
            f"{self.netra_apex_root}/**/notifier*.py"
        ]

        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))

        return list(set(files))

    def _get_user_context_files(self) -> List[str]:
        """Get files that handle user context."""
        patterns = [
            f"{self.netra_apex_root}/**/user_execution_context*.py",
            f"{self.netra_apex_root}/**/user_context*.py",
            f"{self.netra_apex_root}/**/isolation*.py"
        ]

        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))

        return list(set(files))

    def _should_skip_file(self, file_path: str) -> bool:
        """Determine if file should be skipped."""
        skip_patterns = [
            "backup", "__pycache__", ".git", ".pytest_cache",
            "test_ssot_manager_usage.py",  # Skip this test file
            "migration_report", "archive", ".pyc",
            ".backup", "deprecated"
        ]

        return any(pattern in file_path for pattern in skip_patterns)

    def _scan_for_direct_instantiation(self, file_path: str) -> List[Dict]:
        """Scan for direct WebSocket manager instantiation."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Patterns that indicate direct instantiation
            instantiation_patterns = [
                r"WebSocketManager\s*\(",
                r"IsolatedWebSocketManager\s*\(",
                r"UnifiedWebSocketManager\s*\(",
                r"WebSocketManagerFactory\s*\(",
                r"manager\s*=\s*WebSocket\w+Manager\s*\(",
                r"new\s+WebSocket\w+Manager"
            ]

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in instantiation_patterns:
                    if re.search(pattern, line):
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': pattern,
                            'content': line.strip(),
                            'type': 'direct_instantiation'
                        })

        except Exception:
            pass

        return violations

    def _scan_for_non_ssot_usage(self, file_path: str) -> List[Dict]:
        """Scan for non-SSOT manager usage patterns."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in self.violation_patterns:
                    if pattern in line:
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': pattern,
                            'content': line.strip(),
                            'type': 'non_ssot_usage'
                        })

        except Exception:
            pass

        return violations

    def _needs_websocket_manager(self, file_path: str) -> bool:
        """Check if file needs WebSocket manager functionality."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            websocket_indicators = [
                "send_message", "websocket_manager", "connection_id",
                "agent_started", "agent_thinking", "WebSocket"
            ]

            return any(indicator in content for indicator in websocket_indicators)

        except Exception:
            return False

    def _has_ssot_manager_usage(self, file_path: str) -> bool:
        """Check if file uses SSOT manager patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            return any(pattern in content for pattern in self.ssot_patterns)

        except Exception:
            return False

    def _identify_manager_types_in_file(self, file_path: str) -> Set[str]:
        """Identify all WebSocket manager types used in file."""
        manager_types = set()

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            manager_patterns = [
                r"class\s+(\w*WebSocketManager\w*)",
                r"(\w*WebSocketManager\w*)\s*\(",
                r"from\s+\S+\s+import\s+(\w*WebSocketManager\w*)",
                r"import\s+(\w*WebSocketManager\w*)"
            ]

            for pattern in manager_patterns:
                matches = re.findall(pattern, content)
                manager_types.update(matches)

        except Exception:
            pass

        return manager_types

    def _find_notifier_files(self) -> List[str]:
        """Find all WebSocket notifier files."""
        patterns = [
            f"{self.netra_apex_root}/**/websocket*notifier*.py",
            f"{self.netra_apex_root}/**/*notifier*websocket*.py",
            f"{self.netra_apex_root}/**/notifier*.py"
        ]

        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))

        return list(set(files))

    def _scan_notifier_ssot_compliance(self, file_path: str) -> List[Dict]:
        """Scan notifier file for SSOT compliance."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Check for non-SSOT notifier patterns
            non_ssot_notifier_patterns = [
                "WebSocketNotifierFactory",
                "IsolatedWebSocketNotifier",
                "factory.create_notifier",
                "notifier_factory.get_instance"
            ]

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in non_ssot_notifier_patterns:
                    if pattern in line:
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': pattern,
                            'content': line.strip(),
                            'type': 'notifier_ssot_violation'
                        })

        except Exception:
            pass

        return violations

    def _identify_notifier_implementations(self) -> List[str]:
        """Identify all notifier implementations."""
        implementations = []

        notifier_files = self._find_notifier_files()

        for notifier_file in notifier_files:
            if self._should_skip_file(notifier_file):
                continue

            try:
                with open(notifier_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Look for class definitions
                class_pattern = r"class\s+(\w*Notifier\w*)"
                matches = re.findall(class_pattern, content)
                implementations.extend(matches)

            except Exception:
                pass

        return list(set(implementations))

    def _scan_user_context_isolation_ssot(self, file_path: str) -> List[Dict]:
        """Scan for user context isolation SSOT violations."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Non-SSOT isolation patterns
            non_ssot_isolation_patterns = [
                "factory.create_user_context",
                "isolated_manager_factory",
                "per_user_manager_factory",
                "user_manager_singleton"
            ]

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in non_ssot_isolation_patterns:
                    if pattern in line:
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': pattern,
                            'content': line.strip(),
                            'type': 'isolation_ssot_violation'
                        })

        except Exception:
            pass

        return violations

    def _scan_event_delivery_ssot(self, file_path: str, critical_events: List[str]) -> List[Dict]:
        """Scan for event delivery SSOT violations."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Check for non-SSOT event delivery patterns
            for event in critical_events:
                non_ssot_patterns = [
                    f"factory.send_{event}",
                    f"manager_factory.emit_{event}",
                    f"isolated_manager.{event}"
                ]

                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern in non_ssot_patterns:
                        if pattern in line:
                            violations.append({
                                'file': file_path,
                                'line': line_num,
                                'event': event,
                                'pattern': pattern,
                                'content': line.strip(),
                                'type': 'event_delivery_ssot_violation'
                            })

        except Exception:
            pass

        return violations

    def _format_violations(self, violations: List[Dict]) -> str:
        """Format violations for error messages."""
        if not violations:
            return "No violations to display"

        formatted = []
        for violation in violations:
            file_short = violation.get('file', '').split('/')[-1]
            violation_type = violation.get('type', 'unknown')
            pattern = violation.get('pattern', 'unknown')
            line = violation.get('line', '?')

            formatted.append(f"  - {file_short}:{line} [{violation_type}] {pattern}")

        return "\n".join(formatted)


if __name__ == "__main__":
    # Run this test independently to check for SSOT violations
    pytest.main([__file__, "-v"])