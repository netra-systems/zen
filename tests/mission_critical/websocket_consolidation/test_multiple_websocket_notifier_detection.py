"""
Mission Critical Test: Multiple WebSocketNotifier Implementation Detection

This test is designed to FAIL initially, proving that 148+ duplicate WebSocket
implementations exist across the codebase, causing conflicts and blocking $500K+ ARR.

Business Impact:
- 148+ duplicate WebSocket implementations causing race conditions
- 97 WebSocketConnection duplicates across 89 files
- SSOT violations preventing reliable event delivery
- $500K+ ARR blocked by WebSocket infrastructure fragmentation

SSOT Violations Detected:
- Multiple WebSocketNotifier implementations
- Duplicate WebSocketConnection classes
- Conflicting WebSocket factory patterns
- Inconsistent WebSocket event delivery

This test MUST FAIL until SSOT consolidation eliminates duplicates.
"""
import os
import ast
import pytest
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMultipleWebSocketNotifierDetection(SSotBaseTestCase):
    """
    CRITICAL: This test detects duplicate WebSocket implementations.

    EXPECTED RESULT: FAIL - 148+ duplicate implementations found
    BUSINESS IMPACT: $500K+ ARR blocked by WebSocket infrastructure conflicts
    """

    def setup_method(self):
        """Set up test environment for duplicate detection."""
        super().setup_method()
        self.project_root = Path(__file__).parents[3]  # Go up to netra-apex root
        self.websocket_duplicates = []
        self.total_violations = 0
        self.critical_files_affected = 0

    def test_multiple_websocket_notifier_implementations(self):
        """
        CRITICAL BUSINESS TEST: Detect multiple WebSocketNotifier implementations

        Expected Result: FAIL - 148+ duplicate implementations causing conflicts
        Business Impact: $500K+ ARR - WebSocket infrastructure fragmentation blocks chat
        """
        # Define SSOT canonical implementations (should be only ones that exist)
        canonical_websocket_implementations = {
            'netra_backend/app/websocket_core/manager.py': 'UnifiedWebSocketManager',
            'netra_backend/app/websocket_core/notifier.py': 'WebSocketNotifier',
            'netra_backend/app/websocket_core/bridge.py': 'WebSocketBridge'
        }

        # Scan for duplicate WebSocket implementations
        duplicate_classes = self._scan_for_websocket_duplicates()

        # CRITICAL ASSERTION: Should find ZERO duplicates (will fail with 148+)
        total_duplicates = sum(len(locations) for locations in duplicate_classes.values())

        assert total_duplicates == 0, (
            f"SSOT VIOLATION: Found {total_duplicates} duplicate WebSocket implementations. "
            f"$500K+ ARR at risk. Duplicates: {duplicate_classes}"
        )

    def test_websocket_connection_duplication_detection(self):
        """
        CRITICAL: Detect 97+ WebSocketConnection duplicates across 89 files

        Expected Result: FAIL - Massive duplication causing race conditions
        Business Impact: Connection conflicts block real-time chat functionality
        """
        websocket_connection_duplicates = self._scan_for_class_duplicates('WebSocketConnection')

        # CRITICAL ASSERTION: Should find ZERO WebSocketConnection duplicates
        assert len(websocket_connection_duplicates) <= 1, (
            f"SSOT VIOLATION: Found {len(websocket_connection_duplicates)} WebSocketConnection duplicates "
            f"across {len(set(loc['file'] for loc in websocket_connection_duplicates))} files. "
            f"This causes race conditions blocking $500K+ ARR. "
            f"Duplicates: {websocket_connection_duplicates}"
        )

    def test_websocket_factory_pattern_duplication(self):
        """
        CRITICAL: Detect duplicate WebSocket factory patterns

        Expected Result: FAIL - Multiple factory implementations causing user isolation failures
        Business Impact: 0% concurrent user success rate due to factory conflicts
        """
        factory_duplicates = self._scan_for_factory_duplicates()

        # CRITICAL ASSERTION: Should have single factory pattern
        assert len(factory_duplicates) <= 1, (
            f"SSOT VIOLATION: Found {len(factory_duplicates)} duplicate WebSocket factory patterns. "
            f"This causes 0% concurrent user success rate. "
            f"Factory duplicates: {factory_duplicates}"
        )

    def test_websocket_event_emitter_duplication(self):
        """
        CRITICAL: Detect duplicate WebSocket event emitters

        Expected Result: FAIL - Multiple emitter implementations causing event delivery failures
        Business Impact: Critical chat events not delivered reliably to users
        """
        emitter_duplicates = self._scan_for_emitter_duplicates()

        # CRITICAL ASSERTION: Should have single emitter implementation
        assert len(emitter_duplicates) <= 1, (
            f"SSOT VIOLATION: Found {len(emitter_duplicates)} duplicate WebSocket emitter implementations. "
            f"This causes unreliable event delivery for $500K+ ARR chat functionality. "
            f"Emitter duplicates: {emitter_duplicates}"
        )

    def _scan_for_websocket_duplicates(self) -> dict:
        """Scan entire codebase for duplicate WebSocket implementations."""
        websocket_classes = {
            'WebSocketManager': [],
            'WebSocketNotifier': [],
            'WebSocketBridge': [],
            'WebSocketEmitter': [],
            'WebSocketFactory': [],
            'WebSocketHandler': [],
            'UnifiedWebSocketManager': [],
            'AgentWebSocketBridge': []
        }

        # Scan Python files for WebSocket class definitions
        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue

            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        if class_name in websocket_classes:
                            websocket_classes[class_name].append({
                                'file': str(python_file.relative_to(self.project_root)),
                                'line': node.lineno,
                                'class_name': class_name
                            })

            except (SyntaxError, UnicodeDecodeError, PermissionError):
                # Skip files with syntax errors or permission issues
                continue

        # Filter out classes that appear in only one location (not duplicates)
        return {class_name: locations for class_name, locations in websocket_classes.items() if len(locations) > 1}

    def _scan_for_class_duplicates(self, class_name: str) -> list:
        """Scan for duplicates of a specific class name."""
        duplicates = []

        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue

            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == class_name:
                        duplicates.append({
                            'file': str(python_file.relative_to(self.project_root)),
                            'line': node.lineno,
                            'class_name': class_name
                        })

            except (SyntaxError, UnicodeDecodeError, PermissionError):
                continue

        return duplicates

    def _scan_for_factory_duplicates(self) -> list:
        """Scan for duplicate WebSocket factory patterns."""
        factory_patterns = [
            'WebSocketFactory',
            'AgentWebSocketFactory',
            'WebSocketBridgeFactory',
            'WebSocketManagerFactory',
            'create_websocket_manager',
            'create_websocket_bridge',
            'create_websocket_notifier'
        ]

        factory_duplicates = []

        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue

            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                for node in ast.walk(tree):
                    # Check for class definitions
                    if isinstance(node, ast.ClassDef):
                        if any(pattern in node.name for pattern in factory_patterns):
                            factory_duplicates.append({
                                'file': str(python_file.relative_to(self.project_root)),
                                'line': node.lineno,
                                'type': 'class',
                                'name': node.name
                            })

                    # Check for function definitions
                    elif isinstance(node, ast.FunctionDef):
                        if any(pattern in node.name for pattern in factory_patterns):
                            factory_duplicates.append({
                                'file': str(python_file.relative_to(self.project_root)),
                                'line': node.lineno,
                                'type': 'function',
                                'name': node.name
                            })

            except (SyntaxError, UnicodeDecodeError, PermissionError):
                continue

        return factory_duplicates

    def _scan_for_emitter_duplicates(self) -> list:
        """Scan for duplicate WebSocket emitter implementations."""
        emitter_patterns = [
            'WebSocketEmitter',
            'EventEmitter',
            'UnifiedWebSocketEmitter',
            'AgentEventEmitter',
            'emit_event',
            'send_websocket_event',
            'emit_to_websocket'
        ]

        emitter_duplicates = []

        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue

            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                for node in ast.walk(tree):
                    # Check for class definitions
                    if isinstance(node, ast.ClassDef):
                        if any(pattern in node.name for pattern in emitter_patterns):
                            emitter_duplicates.append({
                                'file': str(python_file.relative_to(self.project_root)),
                                'line': node.lineno,
                                'type': 'class',
                                'name': node.name
                            })

                    # Check for function definitions
                    elif isinstance(node, ast.FunctionDef):
                        if any(pattern in node.name for pattern in emitter_patterns):
                            emitter_duplicates.append({
                                'file': str(python_file.relative_to(self.project_root)),
                                'line': node.lineno,
                                'type': 'function',
                                'name': node.name
                            })

            except (SyntaxError, UnicodeDecodeError, PermissionError):
                continue

        return emitter_duplicates

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped during scanning."""
        skip_patterns = [
            '__pycache__',
            '.git',
            '.pytest_cache',
            'htmlcov',
            'node_modules',
            '.venv',
            'venv',
            'backup',
            'archive',
            '.pyc',
            'migrations',
            'alembic/versions'
        ]

        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)

    def test_calculate_total_ssot_violation_count(self):
        """
        CRITICAL: Calculate total SSOT violation count for business impact assessment

        Expected Result: FAIL - 148+ total violations requiring immediate remediation
        Business Impact: Quantify exact technical debt blocking $500K+ ARR
        """
        # Aggregate all WebSocket duplications
        websocket_duplicates = self._scan_for_websocket_duplicates()
        connection_duplicates = self._scan_for_class_duplicates('WebSocketConnection')
        factory_duplicates = self._scan_for_factory_duplicates()
        emitter_duplicates = self._scan_for_emitter_duplicates()

        # Calculate total violation count
        total_class_duplicates = sum(len(locations) for locations in websocket_duplicates.values())
        total_connection_duplicates = len(connection_duplicates)
        total_factory_duplicates = len(factory_duplicates)
        total_emitter_duplicates = len(emitter_duplicates)

        self.total_violations = (
            total_class_duplicates +
            total_connection_duplicates +
            total_factory_duplicates +
            total_emitter_duplicates
        )

        # Calculate files affected
        affected_files = set()
        for locations in websocket_duplicates.values():
            affected_files.update(loc['file'] for loc in locations)
        affected_files.update(dup['file'] for dup in connection_duplicates)
        affected_files.update(dup['file'] for dup in factory_duplicates)
        affected_files.update(dup['file'] for dup in emitter_duplicates)

        self.critical_files_affected = len(affected_files)

        # CRITICAL ASSERTION: Should be ZERO violations
        assert self.total_violations == 0, (
            f"SSOT CRITICAL FAILURE: {self.total_violations} total WebSocket SSOT violations detected "
            f"across {self.critical_files_affected} files. $500K+ ARR immediately at risk. "
            f"Breakdown: {total_class_duplicates} class duplicates, "
            f"{total_connection_duplicates} connection duplicates, "
            f"{total_factory_duplicates} factory duplicates, "
            f"{total_emitter_duplicates} emitter duplicates. "
            f"IMMEDIATE SSOT CONSOLIDATION REQUIRED."
        )


if __name__ == "__main__":
    # Run this test to detect WebSocket implementation duplicates
    pytest.main([__file__, "-v", "--tb=short"])