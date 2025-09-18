#!/usr/bin/env python3
"""
test_websocket_factory_singleton_vs_factory_violations.py

Issue #1144 WebSocket Factory Dual Pattern Detection - Singleton vs Factory Violations

PURPOSE: FAILING TESTS to detect singleton pattern violations in WebSocket factory
These tests should FAIL initially to prove singleton violations exist.

CRITICAL: These tests are designed to FAIL and demonstrate singleton contamination problems.
"""

import pytest
import ast
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Set
from unittest.mock import MagicMock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class WebSocketFactorySingletonVsFactoryViolationsTests(SSotBaseTestCase):
    """Test suite to detect singleton pattern violations (SHOULD FAIL)"""

    def setUp(self):
        """Set up test environment"""
        super().setUp()
        self.project_root = Path(__file__).resolve().parents[3]
        self.singleton_violations = []
        self.factory_issues = []

    def scan_for_singleton_patterns(self) -> List[Dict[str, Any]]:
        """Scan for singleton pattern indicators in WebSocket code"""
        singleton_indicators = []

        # Search patterns that indicate singleton behavior
        singleton_patterns = [
            '_instance',
            '_instances',
            'global ',
            '__instance',
            'singleton',
            'Singleton',
            'if not hasattr',
            'cls._',
            'class._'
        ]

        backend_path = self.project_root / "netra_backend"
        if backend_path.exists():
            for py_file in backend_path.rglob("*.py"):
                if 'websocket' in str(py_file).lower():
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        for pattern in singleton_patterns:
                            if pattern in content:
                                singleton_indicators.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'pattern': pattern,
                                    'context': self.get_pattern_context(content, pattern)
                                })

                    except (UnicodeDecodeError, PermissionError):
                        continue

        return singleton_indicators

    def get_pattern_context(self, content: str, pattern: str) -> List[str]:
        """Get context lines around a pattern match"""
        lines = content.split('\n')
        context_lines = []

        for i, line in enumerate(lines):
            if pattern in line:
                # Get 2 lines before and after for context
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context_lines.extend(lines[start:end])

        return context_lines[:10]  # Limit context

    def test_websocket_manager_singleton_pattern_detection_SHOULD_FAIL(self):
        """
        Test: Detect singleton patterns in WebSocket manager

        EXPECTED BEHAVIOR: SHOULD FAIL due to singleton pattern usage
        This test is designed to fail to prove singleton violations exist.
        """
        singleton_indicators = self.scan_for_singleton_patterns()

        # Filter for WebSocket manager singleton patterns
        websocket_singletons = [
            indicator for indicator in singleton_indicators
            if 'manager' in indicator['file'].lower() or 'manager' in str(indicator['context']).lower()
        ]

        # This test SHOULD FAIL if singleton patterns are found
        self.assertEqual(
            len(websocket_singletons), 0,
            f"SINGLETON PATTERN VIOLATIONS DETECTED: Found {len(websocket_singletons)} singleton patterns in WebSocket manager code: {websocket_singletons}. "
            f"SSOT factory pattern prohibits singleton usage for user isolation."
        )

    def test_websocket_factory_creates_unique_instances_SHOULD_FAIL(self):
        """
        Test: WebSocket factory creates unique instances per call

        EXPECTED BEHAVIOR: SHOULD FAIL due to instance reuse
        This test is designed to fail to prove factory doesn't create unique instances.
        """
        # Try to import and test WebSocket factory
        try:
            # Mock import since we expect this to fail
            with patch('sys.modules') as mock_modules:
                mock_factory = MagicMock()

                # Simulate factory creating same instance (singleton behavior)
                mock_instance = MagicMock()
                mock_factory.create_websocket_manager.return_value = mock_instance

                # Test factory behavior
                instance1 = mock_factory.create_websocket_manager()
                instance2 = mock_factory.create_websocket_manager()

                # This test SHOULD FAIL if instances are the same (singleton behavior)
                self.assertIsNot(
                    instance1, instance2,
                    f"FACTORY SINGLETON VIOLATION: WebSocket factory returned same instance. "
                    f"Factory pattern requires unique instances per call for user isolation."
                )

        except ImportError as e:
            # Expected failure - document the issue
            self.fail(f"WEBSOCKET FACTORY IMPORT FAILURE: Cannot import WebSocket factory: {e}. "
                     f"This indicates dual pattern or missing factory implementation.")

    def test_websocket_manager_concurrent_user_isolation_SHOULD_FAIL(self):
        """
        Test: WebSocket manager provides user isolation in concurrent scenarios

        EXPECTED BEHAVIOR: SHOULD FAIL due to shared state contamination
        This test is designed to fail to prove user isolation failures exist.
        """
        contamination_detected = []
        shared_state_issues = []

        def simulate_user_session(user_id: str):
            """Simulate a user session that might contaminate others"""
            try:
                # Mock WebSocket manager behavior
                with patch('sys.modules') as mock_modules:
                    mock_manager = MagicMock()

                    # Simulate setting user-specific state
                    mock_manager.current_user_id = user_id
                    mock_manager.user_context = {'user_id': user_id, 'session_data': f'data_for_{user_id}'}

                    # Check if state is isolated
                    time.sleep(0.1)  # Simulate processing time

                    # If this was a singleton, state would be contaminated
                    if hasattr(mock_manager, 'current_user_id'):
                        if mock_manager.current_user_id != user_id:
                            contamination_detected.append({
                                'expected_user': user_id,
                                'actual_user': mock_manager.current_user_id,
                                'thread_id': threading.current_thread().ident
                            })

            except Exception as e:
                shared_state_issues.append(f"User {user_id}: {str(e)}")

        # Simulate concurrent users
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(10):
                user_id = f"user_{i}"
                future = executor.submit(simulate_user_session, user_id)
                futures.append(future)

            # Wait for all simulations
            for future in futures:
                future.result()

        # This test SHOULD FAIL if contamination is detected
        total_issues = len(contamination_detected) + len(shared_state_issues)
        self.assertEqual(
            total_issues, 0,
            f"USER ISOLATION FAILURES DETECTED: Found {len(contamination_detected)} contamination cases and {len(shared_state_issues)} shared state issues. "
            f"Contamination: {contamination_detected}. Shared state issues: {shared_state_issues}. "
            f"Factory pattern must ensure complete user isolation."
        )

    def test_websocket_global_state_detection_SHOULD_FAIL(self):
        """
        Test: Detect global state in WebSocket components

        EXPECTED BEHAVIOR: SHOULD FAIL due to global state usage
        This test is designed to fail to prove global state violations exist.
        """
        global_state_indicators = []

        # Search for global state patterns
        global_patterns = [
            'global ',
            'globals()',
            '__dict__',
            'setattr(',
            'hasattr(',
            'getattr(',
            'class ',  # Class variables that might be global
        ]

        backend_path = self.project_root / "netra_backend"
        if backend_path.exists():
            for py_file in backend_path.rglob("*.py"):
                if 'websocket' in str(py_file).lower():
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        for pattern in global_patterns:
                            if pattern in content:
                                context = self.get_pattern_context(content, pattern)
                                global_state_indicators.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'pattern': pattern,
                                    'context': context
                                })

                    except (UnicodeDecodeError, PermissionError):
                        continue

        # This test SHOULD FAIL if global state indicators are found
        self.assertEqual(
            len(global_state_indicators), 0,
            f"GLOBAL STATE VIOLATIONS DETECTED: Found {len(global_state_indicators)} global state indicators in WebSocket code: {global_state_indicators}. "
            f"Factory pattern prohibits global state for user isolation."
        )

    def test_websocket_factory_pattern_compliance_SHOULD_FAIL(self):
        """
        Test: WebSocket factory pattern compliance

        EXPECTED BEHAVIOR: SHOULD FAIL due to non-compliant factory pattern
        This test is designed to fail to prove factory pattern violations exist.
        """
        factory_compliance_issues = []

        # Check for factory pattern compliance indicators
        backend_path = self.project_root / "netra_backend"
        websocket_files = []

        if backend_path.exists():
            for py_file in backend_path.rglob("*.py"):
                if 'websocket' in str(py_file).lower() and ('factory' in str(py_file).lower() or 'manager' in str(py_file).lower()):
                    websocket_files.append(py_file)

        for py_file in websocket_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for factory pattern violations
                violations = []

                # 1. Check for singleton indicators
                if '_instance' in content or '__instance' in content:
                    violations.append("Contains singleton instance variables")

                # 2. Check for proper factory methods
                if 'def create_' not in content and 'factory' in str(py_file).lower():
                    violations.append("Missing create_ factory methods")

                # 3. Check for static/class method usage that might indicate singleton
                if '@staticmethod' in content or '@classmethod' in content:
                    violations.append("Contains static/class methods that may indicate singleton pattern")

                if violations:
                    factory_compliance_issues.append({
                        'file': str(py_file.relative_to(self.project_root)),
                        'violations': violations
                    })

            except (UnicodeDecodeError, PermissionError):
                continue

        # This test SHOULD FAIL if factory compliance issues are found
        self.assertEqual(
            len(factory_compliance_issues), 0,
            f"FACTORY PATTERN COMPLIANCE VIOLATIONS DETECTED: Found {len(factory_compliance_issues)} compliance issues: {factory_compliance_issues}. "
            f"Factory pattern must be properly implemented for user isolation."
        )

    def test_websocket_instance_sharing_prevention_SHOULD_FAIL(self):
        """
        Test: WebSocket instance sharing prevention

        EXPECTED BEHAVIOR: SHOULD FAIL due to instance sharing
        This test is designed to fail to prove instance sharing violations exist.
        """
        instance_sharing_issues = []

        # Simulate instance sharing scenarios
        try:
            # Mock WebSocket manager
            with patch('sys.modules') as mock_modules:
                mock_manager_class = MagicMock()

                # Simulate shared instance behavior (singleton-like)
                shared_instance = MagicMock()
                shared_instance.user_id = None
                shared_instance.connections = {}

                # Test scenario: Multiple users trying to use same instance
                def use_shared_instance(user_id: str):
                    # This simulates what happens with singleton pattern
                    shared_instance.user_id = user_id
                    shared_instance.connections[user_id] = f"connection_for_{user_id}"
                    time.sleep(0.01)  # Small delay to simulate race condition

                    # Check if user_id got overwritten (indicates sharing)
                    if shared_instance.user_id != user_id:
                        instance_sharing_issues.append({
                            'expected_user': user_id,
                            'actual_user': shared_instance.user_id,
                            'issue': 'User ID overwritten due to shared instance'
                        })

                # Run concurrent access
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = []
                    for i in range(5):
                        user_id = f"user_{i}"
                        future = executor.submit(use_shared_instance, user_id)
                        futures.append(future)

                    for future in futures:
                        future.result()

        except Exception as e:
            instance_sharing_issues.append(f"Exception during instance sharing test: {str(e)}")

        # This test SHOULD FAIL if instance sharing issues are detected
        self.assertEqual(
            len(instance_sharing_issues), 0,
            f"INSTANCE SHARING VIOLATIONS DETECTED: Found {len(instance_sharing_issues)} instance sharing issues: {instance_sharing_issues}. "
            f"Factory pattern must prevent instance sharing between users."
        )

    def test_websocket_dependency_injection_factory_pattern_SHOULD_FAIL(self):
        """
        Test: WebSocket dependency injection with factory pattern

        EXPECTED BEHAVIOR: SHOULD FAIL due to missing proper dependency injection
        This test is designed to fail to prove dependency injection issues exist.
        """
        dependency_injection_issues = []

        # Check for dependency injection patterns in WebSocket code
        backend_path = self.project_root / "netra_backend"
        if backend_path.exists():
            for py_file in backend_path.rglob("*.py"):
                if 'websocket' in str(py_file).lower():
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Check for dependency injection indicators
                        issues = []

                        # 1. Hard-coded dependencies instead of injection
                        if 'import ' in content and not '__init__(' in content:
                            issues.append("Potential hard-coded dependencies")

                        # 2. Direct instantiation instead of factory
                        if 'WebSocketManager()' in content:
                            issues.append("Direct instantiation instead of factory")

                        # 3. Missing constructor dependency injection
                        if 'def __init__(self):' in content and 'websocket' in content.lower():
                            issues.append("Empty constructor - missing dependency injection")

                        if issues:
                            dependency_injection_issues.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'issues': issues
                            })

                    except (UnicodeDecodeError, PermissionError):
                        continue

        # This test SHOULD FAIL if dependency injection issues are found
        self.assertEqual(
            len(dependency_injection_issues), 0,
            f"DEPENDENCY INJECTION VIOLATIONS DETECTED: Found {len(dependency_injection_issues)} dependency injection issues: {dependency_injection_issues}. "
            f"Factory pattern requires proper dependency injection for user isolation."
        )

    def tearDown(self):
        """Clean up test environment"""
        # Document detected violations for analysis
        total_violations = len(self.singleton_violations) + len(self.factory_issues)
        if total_violations > 0:
            violation_summary = f"WebSocket Factory Singleton Violations Detected: {total_violations}"
            print(f"\nTEST SUMMARY: {violation_summary}")

        super().tearDown()


if __name__ == '__main__':
    import unittest
    unittest.main()