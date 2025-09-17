"""
MISSION CRITICAL: Docker Manager SSOT Regression Prevention Tests

BUSINESS VALUE JUSTIFICATION (BVJ):
1. Segment: Platform/Infrastructure - Quality Assurance and Stability
2. Business Goal: Prevent future SSOT violations and maintain architectural integrity
3. Value Impact: Ensures long-term maintainability, prevents developer confusion and bugs
4. Revenue Impact: Protects $500K+ ARR by preventing regression of Docker infrastructure

PURPOSE:
This test suite implements proactive regression prevention for Docker Manager SSOT
violations. These tests will enforce SSOT compliance and prevent future duplication.

REGRESSION SCENARIOS PREVENTED:
"""
1. Accidental creation of duplicate Docker Manager classes
2. Import path fragmentation causing inconsistent behavior
3. Mock implementations leaking into production code paths
4. Configuration inconsistencies between test and production environments
"

# CRITICAL: Import path configuration for direct test execution
# Ensures tests work both directly and through unified_test_runner.py
import sys
import os
from pathlib import Path

# Get project root (two levels up from tests/mission_critical/)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import ast
import importlib
import inspect
from typing import List, Dict, Set, Any
import unittest
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotBaseTestCase


class DockerManagerRegressionPreventionTests(SSotBaseTestCase, unittest.TestCase):
    "
    CRITICAL: Regression prevention tests for Docker Manager SSOT compliance.

    These tests enforce architectural rules to prevent SSOT violations
    from being reintroduced in the future.
"

    def setUp(self):
        "Set up regression prevention test environment.
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.canonical_docker_manager_path = test_framework.unified_docker_manager""

    def test_prevent_duplicate_docker_manager_creation(self):

        REGRESSION PREVENTION: Prevents accidental creation of duplicate Docker Manager classes.

        PROTECTION GOAL:
        - Block creation of new UnifiedDockerManager classes outside canonical location
        - Enforce single implementation rule for critical infrastructure
        - Alert developers to SSOT violations during development

        ENFORCEMENT RULES:
        - Only ONE UnifiedDockerManager class allowed in codebase
        - Must be located at test_framework/unified_docker_manager.py
        - Any duplicates should trigger immediate test failure
        ""
        # Comprehensive search for UnifiedDockerManager classes
        docker_manager_implementations = []

        # Search all Python files for class definitions
        for python_file in self.project_root.rglob(*.py):
            if self._should_skip_file(python_file):
                continue

            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse AST to find class definitions
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if (isinstance(node, ast.ClassDef) and
                            node.name == UnifiedDockerManager):"

                            docker_manager_implementations.append({
                                'file': str(python_file.relative_to(self.project_root)),
                                'line': node.lineno,
                                'class_name': node.name
                            }
                except SyntaxError:
                    # Skip files with syntax errors
                    continue

            except (UnicodeDecodeError, PermissionError):
                continue

        # REGRESSION PREVENTION: Enforce exactly one implementation
        self.assertLessEqual(
            len(docker_manager_implementations), 1,
            fSSOT REGRESSION DETECTED: Found {len(docker_manager_implementations)} "
            fUnifiedDockerManager implementations. Maximum allowed: 1. 
            fImplementations: {docker_manager_implementations}. "
            f"Remove duplicate implementations to maintain SSOT compliance.
        )

        if len(docker_manager_implementations) == 1:
            # Validate canonical location
            canonical_file = test_framework/unified_docker_manager.py
            actual_file = docker_manager_implementations[0]['file'].replace('\\', '/')

            self.assertEqual(
                actual_file, canonical_file,
                fSSOT LOCATION VIOLATION: UnifiedDockerManager found at {actual_file}, 
                fbut must be at canonical location {canonical_file}. ""
                fMove implementation to maintain SSOT compliance.
            )

    def test_prevent_import_path_fragmentation(self):
        
        REGRESSION PREVENTION: Prevents import path fragmentation.

        PROTECTION GOAL:
        - Enforce consistent import paths for Docker Manager
        - Prevent creation of alternative import locations
        - Block non-canonical import patterns

        ENFORCEMENT RULES:
        - All imports must use canonical path: test_framework.unified_docker_manager
        - No imports from test_framework.docker.* paths allowed
        - Direct file imports are forbidden
""
        forbidden_import_patterns = [
            test_framework.docker.unified_docker_manager,
            from test_framework.docker","
            import test_framework.docker
        ]

        violating_imports = []

        # Search for import violations
        for python_file in self.project_root.rglob(*.py):"
            if self._should_skip_file(python_file):
                continue

            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    line_content = line.strip()

                    # Check for forbidden import patterns
                    for forbidden_pattern in forbidden_import_patterns:
                        if forbidden_pattern in line_content:
                            violating_imports.append({
                                'file': str(python_file.relative_to(self.project_root)),
                                'line': line_num,
                                'content': line_content,
                                'pattern': forbidden_pattern
                            }

            except (UnicodeDecodeError, PermissionError):
                continue

        # REGRESSION PREVENTION: No forbidden imports allowed
        self.assertEqual(
            len(violating_imports), 0,
            f"IMPORT PATH REGRESSION DETECTED: Found {len(violating_imports)} forbidden import patterns. 
            fAll imports must use canonical SSOT path. Violations: {violating_imports}. 
            fUpdate imports to use: from test_framework.unified_docker_manager import UnifiedDockerManager
        )

    def test_prevent_mock_implementation_leakage(self):
        ""
        REGRESSION PREVENTION: Prevents mock implementations from leaking into production.

        PROTECTION GOAL:
        - Ensure mock Docker Managers stay in test directories
        - Prevent accidental use of mocks in production code
        - Maintain clear separation between real and test implementations

        ENFORCEMENT RULES:
        - Mock implementations only allowed in test directories
        - Production code must not import mock implementations
        - Clear naming conventions for test utilities

        mock_implementations = []

        # Search for mock Docker Manager implementations
        for python_file in self.project_root.rglob("*.py):"
            if self._should_skip_file(python_file):
                continue

            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for Docker Manager classes with mock characteristics
                if class UnifiedDockerManager in content:
                    is_mock = (
                        Mock in content or"
                        mock" in content.lower() or
                        AsyncMock in content or
                        MagicMock" in content"
                    )

                    if is_mock:
                        file_path = str(python_file.relative_to(self.project_root))
                        is_in_test_directory = (
                            'test' in file_path.lower() or
                            file_path.startswith('tests/') or
                            file_path.startswith('test_framework/')
                        )

                        mock_implementations.append({
                            'file': file_path,
                            'is_in_test_directory': is_in_test_directory
                        }

            except (UnicodeDecodeError, PermissionError):
                continue

        # REGRESSION PREVENTION: Mock implementations must be in test directories
        production_mocks = [impl for impl in mock_implementations if not impl['is_in_test_directory']]

        self.assertEqual(
            len(production_mocks), 0,
            fMOCK LEAKAGE REGRESSION DETECTED: Found {len(production_mocks)} mock Docker Manager 
            fimplementations outside test directories. Mock implementations must be isolated in test code. 
            f"Production mocks: {production_mocks}. Move to test directories or convert to real implementation.
        )

    def test_prevent_configuration_inconsistencies(self):
        "
        REGRESSION PREVENTION: Prevents Docker configuration inconsistencies.

        PROTECTION GOAL:
        - Ensure Docker Manager configurations are consistent
        - Prevent environment-specific configuration drift
        - Maintain predictable behavior across environments

        ENFORCEMENT RULES:
        - Docker Manager must have consistent interface
        - Configuration parameters must be standardized
        - No environment-specific behavior in core class
"
        try:
            # Import the canonical Docker Manager
            from test_framework.unified_docker_manager import UnifiedDockerManager

            # Validate class has required interface
            required_methods = [
                '__init__',
                'start_services',
                'stop_services',
                'get_service_status',
                'cleanup'
            ]

            missing_methods = []
            for method_name in required_methods:
                if not hasattr(UnifiedDockerManager, method_name):
                    missing_methods.append(method_name)

            self.assertEqual(
                len(missing_methods), 0,
                f"INTERFACE REGRESSION DETECTED: UnifiedDockerManager missing required methods: {missing_methods}. 
                fAll required methods must be implemented to maintain consistent interface.
            )

            # Validate constructor signature is consistent
            init_signature = inspect.signature(UnifiedDockerManager.__init__)

            # Should have reasonable parameter structure
            self.assertIsNotNone(
                init_signature,
                CONSTRUCTOR REGRESSION: UnifiedDockerManager.__init__ signature not accessible. "
                Constructor must have well-defined interface."
            )

        except ImportError as e:
            self.fail(
                fIMPORT REGRESSION DETECTED: Cannot import canonical UnifiedDockerManager: {e}. 
                fCanonical implementation must be importable for SSOT compliance."
            )

    def test_enforce_docker_manager_naming_conventions(self):
    "
        REGRESSION PREVENTION: Enforces Docker Manager naming conventions.

        PROTECTION GOAL:
        - Prevent creation of alternative Docker Manager classes
        - Enforce consistent naming patterns
        - Block circumvention through naming variations

        ENFORCEMENT RULES:
        - Only UnifiedDockerManager" class name allowed
        - No variations like DockerManager, DockerHelper, etc.
        - Clear distinction from other Docker utilities
"
        docker_related_classes = []

        # Search for Docker-related class names that might circumvent SSOT
        suspicious_patterns = [
            DockerManager,"
            DockerHelper",
            DockerOrchestrator,
            DockerService","
            DockerController,
            ContainerManager"
        ]

        for python_file in self.project_root.rglob("*.py):
            if self._should_skip_file(python_file):
                continue

            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse AST to find class definitions
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            for pattern in suspicious_patterns:
                                if pattern in node.name and node.name != UnifiedDockerManager:
                                    docker_related_classes.append({
                                        'file': str(python_file.relative_to(self.project_root)),
                                        'line': node.lineno,
                                        'class_name': node.name,
                                        'pattern': pattern
                                    }
                except SyntaxError:
                    continue

            except (UnicodeDecodeError, PermissionError):
                continue

        # Allow some specific exceptions for legacy or specialized classes
        allowed_exceptions = [
            # Add any legitimate exceptions here
        ]

        violations = [
            cls for cls in docker_related_classes
            if cls['class_name'] not in allowed_exceptions
        ]

        # REGRESSION PREVENTION: Flag potential SSOT circumvention
        if violations:
            self.fail(
                f"NAMING CONVENTION VIOLATION: Found {len(violations)} Docker-related classes 
                fthat may circumvent SSOT. Classes: {violations}. "
                fEnsure these classes have distinct purposes or consolidate with UnifiedDockerManager.
            )

    def _should_skip_file(self, file_path: Path) -> bool:
        "
        Determine if a file should be skipped during analysis.

        Args:
            file_path: Path to the file to check

        Returns:
            True if file should be skipped, False otherwise
"""
        skip_patterns = [
            '__pycache__',
            '.git',
            '.pytest_cache',
            'node_modules',
            '.venv',
            'venv',
            '.env'
        ]

        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)


if __name__ == '__main__':
    unittest.main()