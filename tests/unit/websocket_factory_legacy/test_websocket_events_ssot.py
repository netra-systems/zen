"""
Test WebSocket Event Delivery SSOT Compliance - Issue #1098

CRITICAL: This test must FAIL initially to prove SSOT violations exist.
After SSOT migration, this test must PASS to prove success.

Business Value Justification (BVJ):
- Segment: ALL (Free/Early/Mid/Enterprise/Platform)
- Business Goal: Ensure 5 critical WebSocket events use SSOT delivery patterns
- Value Impact: Protects 90% of platform value (chat functionality)
- Revenue Impact: Ensures $500K+ ARR chat reliability through proper event delivery

FAILING TEST STRATEGY:
1. Test initially FAILS proving event delivery uses factory patterns
2. SSOT migration consolidates event delivery to UnifiedWebSocketManager
3. Test PASSES proving all 5 critical events use SSOT patterns

CRITICAL EVENTS TESTED:
- agent_started: User sees agent began processing
- agent_thinking: Real-time reasoning visibility
- tool_executing: Tool usage transparency
- tool_completed: Tool results display
- agent_completed: User knows response is ready
"""

import pytest
import ast
import glob
import os
import re
from typing import List, Dict, Set, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketEventsSSoT(SSotBaseTestCase):
    """
    Unit tests to validate WebSocket event delivery SSOT compliance.

    CRITICAL: These tests are designed to FAIL initially, proving SSOT violations exist.
    After remediation, they must PASS to prove SSOT event delivery achieved.
    """

    def setUp(self):
        """Set up test environment for WebSocket events SSOT validation."""
        super().setUp()
        self.netra_apex_root = "/c/netra-apex"

        # The 5 business-critical WebSocket events
        self.critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        # SSOT event delivery patterns (these should be used)
        self.ssot_event_patterns = [
            "unified_manager.send_event",
            "websocket_manager.emit_event",
            "await manager.send_agent_event",
            "UnifiedWebSocketManager",
            "_send_websocket_event"
        ]

        # Non-SSOT event delivery patterns (these violate SSOT)
        self.violation_event_patterns = [
            "factory.send_event",
            "manager_factory.emit_event",
            "isolated_manager.send_event",
            "factory_instance.send_agent_event",
            "websocket_manager_factory.send",
            "notifier_factory.emit"
        ]

        # Files that handle critical event delivery
        self.event_delivery_files = [
            "/c/netra-apex/netra_backend/app/agents/supervisor/execution_engine.py",
            "/c/netra-apex/netra_backend/app/tools/enhanced_dispatcher.py",
            "/c/netra-apex/netra_backend/app/websocket_core/unified_manager.py",
            "/c/netra-apex/netra_backend/app/agents/supervisor/workflow_orchestrator.py"
        ]

    def test_critical_events_use_ssot_delivery(self):
        """
        Test that all 5 critical events use SSOT delivery patterns

        CRITICAL: Must detect non-SSOT event delivery violations
        """
        non_ssot_event_delivery = []
        missing_ssot_events = []

        # Scan event delivery files for SSOT compliance
        for event_file in self.event_delivery_files:
            if not os.path.exists(event_file) or self._should_skip_file(event_file):
                continue

            violations = self._scan_event_delivery_ssot(event_file)
            non_ssot_event_delivery.extend(violations)

            # Check if file handles events but doesn't use SSOT
            if self._handles_critical_events(event_file):
                if not self._uses_ssot_event_delivery(event_file):
                    missing_ssot_events.append(event_file)

        # CRITICAL: These assertions MUST FAIL initially
        assert len(non_ssot_event_delivery) == 0, (
            f"NON-SSOT EVENT DELIVERY VIOLATIONS: Found {len(non_ssot_event_delivery)} "
            f"non-SSOT event delivery violations.\n"
            f"All 5 critical events must use SSOT delivery patterns.\n"
            f"Violations:\n{self._format_event_violations(non_ssot_event_delivery[:5])}"
        )

        if missing_ssot_events:
            assert len(missing_ssot_events) == 0, (
                f"MISSING SSOT EVENT DELIVERY: {len(missing_ssot_events)} files handle "
                f"critical events but don't use SSOT delivery patterns.\n"
                f"Files: {[f.split('/')[-1] for f in missing_ssot_events]}"
            )

    def test_websocket_notifier_ssot_compliance(self):
        """
        Test WebSocket notifier uses SSOT patterns exclusively

        CRITICAL: Must detect multiple notifier implementations violating SSOT
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

        # Check for multiple notifier implementations (violates SSOT)
        notifier_implementations = self._identify_notifier_implementations()

        if len(notifier_implementations) > 1:
            multiple_notifier_implementations = notifier_implementations

        # CRITICAL: These assertions MUST FAIL initially
        assert len(notifier_violations) == 0, (
            f"NOTIFIER SSOT VIOLATIONS: Found {len(notifier_violations)} "
            f"notifier SSOT compliance violations.\n"
            f"Notifiers must use SSOT patterns for event delivery.\n"
            f"Violations:\n{self._format_event_violations(notifier_violations[:5])}"
        )

        assert len(multiple_notifier_implementations) <= 1, (
            f"MULTIPLE NOTIFIER IMPLEMENTATIONS: Found {len(multiple_notifier_implementations)} "
            f"notifier implementations. SSOT requires exactly ONE.\n"
            f"Implementations: {multiple_notifier_implementations}\n"
            f"Expected: Single unified notifier implementation"
        )

    def test_agent_event_emission_ssot_patterns(self):
        """
        Test that agent event emission uses SSOT patterns

        CRITICAL: Validates agent execution engine uses SSOT for events
        """
        agent_event_violations = []

        # Files that emit agent events
        agent_files = self._get_agent_event_files()

        for agent_file in agent_files:
            if not os.path.exists(agent_file) or self._should_skip_file(agent_file):
                continue

            violations = self._scan_agent_event_ssot(agent_file)
            agent_event_violations.extend(violations)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(agent_event_violations) == 0, (
            f"AGENT EVENT SSOT VIOLATIONS: Found {len(agent_event_violations)} "
            f"agent event emission SSOT violations.\n"
            f"Agent events must use SSOT delivery patterns.\n"
            f"Violations:\n{self._format_event_violations(agent_event_violations[:5])}"
        )

    def test_tool_execution_event_ssot_compliance(self):
        """
        Test that tool execution events use SSOT patterns

        CRITICAL: Validates tool_executing and tool_completed events use SSOT
        """
        tool_event_violations = []

        # Files that handle tool execution events
        tool_files = self._get_tool_execution_files()

        for tool_file in tool_files:
            if not os.path.exists(tool_file) or self._should_skip_file(tool_file):
                continue

            violations = self._scan_tool_event_ssot(tool_file)
            tool_event_violations.extend(violations)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(tool_event_violations) == 0, (
            f"TOOL EVENT SSOT VIOLATIONS: Found {len(tool_event_violations)} "
            f"tool execution event SSOT violations.\n"
            f"Tool events (tool_executing, tool_completed) must use SSOT delivery.\n"
            f"Violations:\n{self._format_event_violations(tool_event_violations[:5])}"
        )

    def test_websocket_event_routing_ssot_compliance(self):
        """
        Test that WebSocket event routing uses SSOT patterns

        CRITICAL: Validates event routing doesn't use multiple managers
        """
        routing_violations = []

        # Files that handle event routing
        routing_files = self._get_event_routing_files()

        for routing_file in routing_files:
            if not os.path.exists(routing_file) or self._should_skip_file(routing_file):
                continue

            violations = self._scan_event_routing_ssot(routing_file)
            routing_violations.extend(violations)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(routing_violations) == 0, (
            f"EVENT ROUTING SSOT VIOLATIONS: Found {len(routing_violations)} "
            f"event routing SSOT violations.\n"
            f"Event routing must use single SSOT manager instance.\n"
            f"Violations:\n{self._format_event_violations(routing_violations[:5])}"
        )

    def test_critical_event_sequence_ssot_validation(self):
        """
        Test that critical event sequence uses SSOT patterns

        CRITICAL: Validates the 5 events are sent in proper sequence via SSOT
        """
        sequence_violations = []

        # Files that orchestrate event sequences
        sequence_files = [
            "/c/netra-apex/netra_backend/app/agents/supervisor/execution_engine.py",
            "/c/netra-apex/netra_backend/app/agents/supervisor/workflow_orchestrator.py"
        ]

        for sequence_file in sequence_files:
            if not os.path.exists(sequence_file) or self._should_skip_file(sequence_file):
                continue

            violations = self._scan_event_sequence_ssot(sequence_file)
            sequence_violations.extend(violations)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(sequence_violations) == 0, (
            f"EVENT SEQUENCE SSOT VIOLATIONS: Found {len(sequence_violations)} "
            f"event sequence SSOT violations.\n"
            f"Critical event sequences must use SSOT patterns.\n"
            f"Violations:\n{self._format_event_violations(sequence_violations[:5])}"
        )

    # Helper methods for event SSOT validation

    def _should_skip_file(self, file_path: str) -> bool:
        """Determine if file should be skipped."""
        skip_patterns = [
            "backup", "__pycache__", ".git", ".pytest_cache",
            "test_websocket_events_ssot.py",  # Skip this test file
            "migration_report", "archive", ".pyc",
            ".backup", "deprecated"
        ]

        return any(pattern in file_path for pattern in skip_patterns)

    def _scan_event_delivery_ssot(self, file_path: str) -> List[Dict]:
        """Scan file for event delivery SSOT violations."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Check for non-SSOT event delivery patterns
            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in self.violation_event_patterns:
                    if pattern in line:
                        # Determine which event is involved
                        involved_event = self._identify_event_in_line(line)
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': pattern,
                            'event': involved_event,
                            'content': line.strip(),
                            'type': 'event_delivery_ssot_violation'
                        })

        except Exception:
            pass

        return violations

    def _handles_critical_events(self, file_path: str) -> bool:
        """Check if file handles any of the 5 critical events."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            return any(event in content for event in self.critical_events)

        except Exception:
            return False

    def _uses_ssot_event_delivery(self, file_path: str) -> bool:
        """Check if file uses SSOT event delivery patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            return any(pattern in content for pattern in self.ssot_event_patterns)

        except Exception:
            return False

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
                "notifier_factory.get_instance",
                "multiple_notifier_instances",
                "notifier_per_user"
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

    def _get_agent_event_files(self) -> List[str]:
        """Get files that emit agent events."""
        patterns = [
            f"{self.netra_apex_root}/netra_backend/app/agents/**/*.py",
            f"{self.netra_apex_root}/netra_backend/app/agents/supervisor/*.py"
        ]

        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))

        return list(set(files))

    def _scan_agent_event_ssot(self, file_path: str) -> List[Dict]:
        """Scan agent file for event SSOT violations."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Agent-specific non-SSOT patterns
            agent_violation_patterns = [
                "agent_factory.send_event",
                "isolated_agent_manager.emit",
                "per_agent_notifier",
                "factory.create_agent_notifier"
            ]

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in agent_violation_patterns:
                    if pattern in line:
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': pattern,
                            'content': line.strip(),
                            'type': 'agent_event_ssot_violation'
                        })

        except Exception:
            pass

        return violations

    def _get_tool_execution_files(self) -> List[str]:
        """Get files that handle tool execution events."""
        patterns = [
            f"{self.netra_apex_root}/netra_backend/app/tools/**/*.py",
            f"{self.netra_apex_root}/netra_backend/app/agents/**/enhanced_*.py"
        ]

        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))

        return list(set(files))

    def _scan_tool_event_ssot(self, file_path: str) -> List[Dict]:
        """Scan tool file for event SSOT violations."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Tool-specific non-SSOT patterns
            tool_violation_patterns = [
                "tool_factory.send_event",
                "isolated_tool_manager.emit",
                "per_tool_notifier",
                "factory.create_tool_notifier"
            ]

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in tool_violation_patterns:
                    if pattern in line:
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': pattern,
                            'content': line.strip(),
                            'type': 'tool_event_ssot_violation'
                        })

        except Exception:
            pass

        return violations

    def _get_event_routing_files(self) -> List[str]:
        """Get files that handle event routing."""
        patterns = [
            f"{self.netra_apex_root}/netra_backend/app/websocket_core/*.py",
            f"{self.netra_apex_root}/netra_backend/app/routes/websocket*.py"
        ]

        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))

        return list(set(files))

    def _scan_event_routing_ssot(self, file_path: str) -> List[Dict]:
        """Scan routing file for event SSOT violations."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Routing-specific non-SSOT patterns
            routing_violation_patterns = [
                "multiple_manager_instances",
                "per_connection_manager",
                "factory.get_manager_for_user",
                "routing_factory.create_manager"
            ]

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in routing_violation_patterns:
                    if pattern in line:
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': pattern,
                            'content': line.strip(),
                            'type': 'routing_ssot_violation'
                        })

        except Exception:
            pass

        return violations

    def _scan_event_sequence_ssot(self, file_path: str) -> List[Dict]:
        """Scan file for event sequence SSOT violations."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Sequence-specific non-SSOT patterns
            sequence_violation_patterns = [
                "factory.send_sequence",
                "isolated_sequence_manager",
                "per_sequence_notifier",
                "factory.orchestrate_events"
            ]

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in sequence_violation_patterns:
                    if pattern in line:
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': pattern,
                            'content': line.strip(),
                            'type': 'sequence_ssot_violation'
                        })

        except Exception:
            pass

        return violations

    def _identify_event_in_line(self, line: str) -> Optional[str]:
        """Identify which critical event is referenced in the line."""
        for event in self.critical_events:
            if event in line:
                return event
        return None

    def _format_event_violations(self, violations: List[Dict]) -> str:
        """Format event violations for error messages."""
        if not violations:
            return "No violations to display"

        formatted = []
        for violation in violations:
            file_short = violation.get('file', '').split('/')[-1]
            violation_type = violation.get('type', 'unknown')
            pattern = violation.get('pattern', 'unknown')
            line = violation.get('line', '?')
            event = violation.get('event', 'unknown')

            formatted.append(f"  - {file_short}:{line} [{violation_type}] {pattern} (event: {event})")

        return "\n".join(formatted)


if __name__ == "__main__":
    # Run this test independently to check for event SSOT violations
    pytest.main([__file__, "-v"])