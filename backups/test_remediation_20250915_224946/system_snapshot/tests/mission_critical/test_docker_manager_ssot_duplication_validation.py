"""
MISSION CRITICAL: Docker Manager SSOT Duplication Validation Tests

BUSINESS VALUE JUSTIFICATION (BVJ):
1. Segment: Platform/Infrastructure - SSOT Compliance and Architecture Integrity
2. Business Goal: Eliminate SSOT violations that cause inconsistent behavior and deployment failures
3. Value Impact: Prevents developer confusion, reduces debugging time, ensures reliable test execution
4. Revenue Impact: Protects $500K+ ARR by maintaining stable testing infrastructure

PURPOSE:
This test suite validates that SSOT violations in Docker Manager implementations are detected
and prevented. These tests MUST FAIL initially to prove the duplication exists, then pass
after remediation.

SSOT VIOLATION DISCOVERED:
- test_framework/unified_docker_manager.py (Real implementation)
- test_framework/docker/unified_docker_manager.py (Mock implementation)

This violates the SSOT principle of having exactly ONE authoritative implementation.
"""

import os
import ast
import glob
from pathlib import Path
from typing import List, Dict, Set
import unittest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class DockerManagerSSOTDuplicationValidationTests(SSotBaseTestCase, unittest.TestCase):
    """
    CRITICAL: Tests that validate Docker Manager SSOT compliance.

    These tests MUST FAIL initially to prove SSOT violations exist.
    After remediation, they should pass to prevent regression.
    """

    def setUp(self):
        """Set up test environment for SSOT validation."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent

    def test_docker_manager_class_implementations_are_unique(self):
        """
        CRITICAL SSOT TEST: Validates that UnifiedDockerManager class exists only once.

        EXPECTED BEHAVIOR (AFTER REMEDIATION):
        - Should find exactly ONE UnifiedDockerManager class implementation
        - Should be located in the canonical SSOT location: test_framework/unified_docker_manager.py

        CURRENT BEHAVIOR (BEFORE REMEDIATION):
        - WILL FIND MULTIPLE implementations, causing this test to FAIL
        - This failure proves the SSOT violation exists
        """
        docker_manager_classes = []

        # Search for all UnifiedDockerManager class definitions
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse AST to find class definitions
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and node.name == "UnifiedDockerManager":
                            docker_manager_classes.append({
                                'file': str(file_path.relative_to(self.project_root)),
                                'line': node.lineno,
                                'class_name': node.name
                            })
                except SyntaxError:
                    # Skip files with syntax errors
                    continue

            except (UnicodeDecodeError, PermissionError):
                # Skip binary files or files we can't read
                continue

        # SSOT VALIDATION: Should have exactly ONE UnifiedDockerManager implementation
        self.assertEqual(
            len(docker_manager_classes), 1,
            f"SSOT VIOLATION: Found {len(docker_manager_classes)} UnifiedDockerManager implementations. "
            f"SSOT requires exactly 1. Implementations found: {docker_manager_classes}"
        )

        # Validate it's in the canonical location
        canonical_location = "test_framework/unified_docker_manager.py"
        actual_location = docker_manager_classes[0]['file'].replace('\\', '/')

        self.assertEqual(
            actual_location, canonical_location,
            f"SSOT VIOLATION: UnifiedDockerManager found at {actual_location}, "
            f"but canonical SSOT location should be {canonical_location}"
        )

    def test_docker_manager_import_paths_are_consistent(self):
        """
        CRITICAL SSOT TEST: Validates that all imports use the same canonical path.

        EXPECTED BEHAVIOR (AFTER REMEDIATION):
        - All imports should use: from test_framework.unified_docker_manager import UnifiedDockerManager
        - No imports from test_framework.docker.unified_docker_manager

        CURRENT BEHAVIOR (BEFORE REMEDIATION):
        - WILL FIND inconsistent import paths, causing this test to FAIL
        - This failure proves import path fragmentation exists
        """
        import_patterns = []
        canonical_import = "from test_framework.unified_docker_manager import"
        violation_import = "from test_framework.docker.unified_docker_manager import"

        # Search for import statements
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if "unified_docker_manager import" in line.lower():
                        import_patterns.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'line': line_num,
                            'import_statement': line,
                            'is_canonical': canonical_import.lower() in line.lower(),
                            'is_violation': violation_import.lower() in line.lower()
                        })

            except (UnicodeDecodeError, PermissionError):
                continue

        # Find violation imports
        violation_imports = [imp for imp in import_patterns if imp['is_violation']]

        # SSOT VALIDATION: Should have NO violation imports
        self.assertEqual(
            len(violation_imports), 0,
            f"SSOT VIOLATION: Found {len(violation_imports)} imports using non-canonical path. "
            f"All imports must use canonical path. Violations: {violation_imports}"
        )

        # Additional validation: All imports should be canonical
        non_canonical_imports = [imp for imp in import_patterns if not imp['is_canonical'] and not imp['is_violation']]

        self.assertEqual(
            len(non_canonical_imports), 0,
            f"IMPORT PATH INCONSISTENCY: Found {len(non_canonical_imports)} imports using unknown paths. "
            f"All imports must use canonical SSOT path. Unknown imports: {non_canonical_imports}"
        )

    def test_docker_manager_functionality_consistency(self):
        """
        CRITICAL SSOT TEST: Validates that Docker Manager behavior is consistent.

        EXPECTED BEHAVIOR (AFTER REMEDIATION):
        - Should have only ONE implementation with consistent interface
        - Mock implementations should be clearly marked as test utilities

        CURRENT BEHAVIOR (BEFORE REMEDIATION):
        - WILL FIND inconsistent implementations, causing this test to FAIL
        - This failure proves functional duplication exists
        """
        # Find all files containing UnifiedDockerManager
        manager_files = []
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if "class UnifiedDockerManager" in content:
                    # Analyze the implementation type
                    is_mock = (
                        "mock" in content.lower() or
                        "Mock" in content or
                        "MagicMock" in content or
                        "AsyncMock" in content
                    )

                    is_real = (
                        "docker" in content.lower() and
                        "client" in content.lower() and
                        not is_mock
                    )

                    manager_files.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'is_mock': is_mock,
                        'is_real': is_real,
                        'content_length': len(content)
                    })

            except (UnicodeDecodeError, PermissionError):
                continue

        # SSOT VALIDATION: Should have exactly ONE real implementation
        real_implementations = [f for f in manager_files if f['is_real']]
        mock_implementations = [f for f in manager_files if f['is_mock']]

        self.assertEqual(
            len(real_implementations), 1,
            f"SSOT VIOLATION: Found {len(real_implementations)} real UnifiedDockerManager implementations. "
            f"SSOT requires exactly 1 real implementation. Real implementations: {real_implementations}"
        )

        # Validate mock implementations are properly isolated
        for mock_impl in mock_implementations:
            mock_file = mock_impl['file']
            self.assertTrue(
                'test' in mock_file.lower() or 'mock' in mock_file.lower(),
                f"ARCHITECTURE VIOLATION: Mock implementation found outside test directory: {mock_file}. "
                f"Mock implementations must be clearly isolated in test-specific locations."
            )

    def test_docker_manager_ssot_registry_compliance(self):
        """
        CRITICAL SSOT TEST: Validates Docker Manager is properly registered in SSOT registry.

        EXPECTED BEHAVIOR (AFTER REMEDIATION):
        - UnifiedDockerManager should be documented in SSOT_IMPORT_REGISTRY.md
        - Should have canonical import path documented

        CURRENT BEHAVIOR (BEFORE REMEDIATION):
        - MAY HAVE inconsistent or missing registry entries
        """
        ssot_registry_path = self.project_root / "docs" / "SSOT_IMPORT_REGISTRY.md"

        if not ssot_registry_path.exists():
            self.fail(f"SSOT REGISTRY MISSING: {ssot_registry_path} not found. "
                     f"SSOT registry is required for import path validation.")

        with open(ssot_registry_path, 'r', encoding='utf-8') as f:
            registry_content = f.read()

        # Check for UnifiedDockerManager documentation
        self.assertIn(
            "UnifiedDockerManager", registry_content,
            "SSOT REGISTRY VIOLATION: UnifiedDockerManager not documented in SSOT registry. "
            "All SSOT classes must be properly documented."
        )

        # Check for canonical import path
        canonical_import = "test_framework.unified_docker_manager"
        self.assertIn(
            canonical_import, registry_content,
            f"SSOT REGISTRY VIOLATION: Canonical import path {canonical_import} not documented. "
            f"Registry must include proper import paths for SSOT compliance."
        )


if __name__ == '__main__':
    unittest.main()