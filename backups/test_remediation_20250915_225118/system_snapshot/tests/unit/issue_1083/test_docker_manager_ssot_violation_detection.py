"""
Issue #1083 Docker Manager SSOT Violation Detection Tests

Phase 1: Detection tests to identify and validate SSOT violations in Docker Manager implementations.
These tests confirm the existence of violations before remediation.

TESTING CONSTRAINTS:
- Unit tests only (no Docker dependency)
- Focus on SSOT violation detection
- Validate current state before remediation
"""

import pytest
import unittest
import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.unit
class DockerManagerSSOTViolationDetectionTests(unittest.TestCase):
    """Test suite to detect Docker Manager SSOT violations."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.expected_implementations = 2  # Current state before remediation
        self.target_implementations = 1   # Target after remediation

    def test_docker_manager_implementation_count(self):
        """Test: Detect multiple UnifiedDockerManager implementations (SSOT violation)."""
        implementations = self._find_docker_manager_implementations()

        # Phase 1: Confirm current violation state
        self.assertEqual(
            len(implementations),
            self.expected_implementations,
            f"Expected {self.expected_implementations} implementations before remediation, "
            f"found {len(implementations)}: {[str(p) for p in implementations]}"
        )

        # Document the violation for remediation planning
        if len(implementations) > self.target_implementations:
            violation_msg = (
                f"SSOT VIOLATION DETECTED: Found {len(implementations)} UnifiedDockerManager "
                f"implementations, target is {self.target_implementations}. "
                f"Implementations: {[str(p.relative_to(self.project_root)) for p in implementations]}"
            )
            print(f"\n🚨 {violation_msg}")

    def test_docker_manager_import_path_ssot_compliance(self):
        """Test: Detect import path fragmentation (SSOT violation)."""
        import_patterns = self._find_docker_manager_import_patterns()

        # Check for import path fragmentation
        unique_import_paths = set(import_patterns.keys())
        expected_single_path = 1  # Should have only one canonical import path

        if len(unique_import_paths) > expected_single_path:
            violation_msg = (
                f"SSOT VIOLATION: Found {len(unique_import_paths)} different import paths "
                f"for Docker Manager: {list(unique_import_paths)}"
            )
            print(f"\n🚨 {violation_msg}")

        # Document all import patterns found
        for import_path, files in import_patterns.items():
            print(f"Import path '{import_path}' used in {len(files)} files")

    def test_docker_manager_interface_consistency(self):
        """Test: Detect interface inconsistencies between implementations."""
        implementations = self._find_docker_manager_implementations()

        if len(implementations) < 2:
            self.skipTest("Need at least 2 implementations to test interface consistency")

        interfaces = {}
        for impl_path in implementations:
            try:
                interface = self._extract_class_interface(impl_path)
                interfaces[str(impl_path.relative_to(self.project_root))] = interface
            except Exception as e:
                print(f"Warning: Could not extract interface from {impl_path}: {e}")

        # Compare interfaces
        if len(interfaces) >= 2:
            interface_keys = list(interfaces.keys())
            primary_interface = interfaces[interface_keys[0]]

            for i in range(1, len(interface_keys)):
                other_interface = interfaces[interface_keys[i]]
                differences = self._compare_interfaces(primary_interface, other_interface)

                if differences:
                    violation_msg = (
                        f"INTERFACE INCONSISTENCY: {interface_keys[0]} vs {interface_keys[i]}\n"
                        f"Differences: {differences}"
                    )
                    print(f"\n⚠️  {violation_msg}")

    def test_legacy_docker_manager_detection(self):
        """Test: Detect legacy Docker Manager code that should be removed."""
        legacy_patterns = [
            "ServiceOrchestrator",
            "old_docker_manager",
            "deprecated_docker",
            "legacy_docker"
        ]

        legacy_files = []
        for pattern in legacy_patterns:
            files = self._search_for_pattern(pattern)
            legacy_files.extend([(pattern, f) for f in files])

        if legacy_files:
            print(f"\n📋 LEGACY CODE DETECTED: Found {len(legacy_files)} potential legacy references")
            for pattern, file_path in legacy_files[:10]:  # Show first 10
                print(f"  - Pattern '{pattern}' in {file_path.relative_to(self.project_root)}")

    def _find_docker_manager_implementations(self) -> List[Path]:
        """Find all UnifiedDockerManager class implementations."""
        implementations = []

        # Search for class definitions
        for py_file in self.project_root.rglob("*.py"):
            if self._is_excluded_path(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "class UnifiedDockerManager" in content:
                        implementations.append(py_file)
            except (UnicodeDecodeError, PermissionError):
                continue

        return implementations

    def _find_docker_manager_import_patterns(self) -> Dict[str, List[Path]]:
        """Find all import patterns for Docker Manager."""
        import_patterns = {}

        # Common import patterns to search for
        patterns = [
            "from test_framework.unified_docker_manager import",
            "from test_framework.docker.unified_docker_manager import",
            "import test_framework.unified_docker_manager",
            "import test_framework.docker.unified_docker_manager"
        ]

        for py_file in self.project_root.rglob("*.py"):
            if self._is_excluded_path(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in patterns:
                        if pattern in content:
                            if pattern not in import_patterns:
                                import_patterns[pattern] = []
                            import_patterns[pattern].append(py_file)
            except (UnicodeDecodeError, PermissionError):
                continue

        return import_patterns

    def _extract_class_interface(self, file_path: Path) -> Dict[str, List[str]]:
        """Extract class interface (methods and attributes)."""
        interface = {"methods": [], "attributes": []}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

                in_class = False
                for line in lines:
                    stripped = line.strip()

                    if stripped.startswith("class UnifiedDockerManager"):
                        in_class = True
                        continue

                    if in_class:
                        # Stop at next class definition
                        if stripped.startswith("class ") and not stripped.startswith("class UnifiedDockerManager"):
                            break

                        # Extract method definitions
                        if stripped.startswith("def ") or stripped.startswith("async def "):
                            method_name = stripped.split('(')[0].replace('def ', '').replace('async ', '').strip()
                            if method_name not in interface["methods"]:
                                interface["methods"].append(method_name)

        except Exception:
            pass

        return interface

    def _compare_interfaces(self, interface1: Dict, interface2: Dict) -> List[str]:
        """Compare two interfaces and return differences."""
        differences = []

        methods1 = set(interface1.get("methods", []))
        methods2 = set(interface2.get("methods", []))

        only_in_1 = methods1 - methods2
        only_in_2 = methods2 - methods1

        if only_in_1:
            differences.append(f"Methods only in first: {only_in_1}")
        if only_in_2:
            differences.append(f"Methods only in second: {only_in_2}")

        return differences

    def _search_for_pattern(self, pattern: str) -> List[Path]:
        """Search for a pattern in Python files."""
        matches = []

        for py_file in self.project_root.rglob("*.py"):
            if self._is_excluded_path(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if pattern.lower() in content.lower():
                        matches.append(py_file)
            except (UnicodeDecodeError, PermissionError):
                continue

        return matches

    def _is_excluded_path(self, path: Path) -> bool:
        """Check if path should be excluded from search."""
        excluded_patterns = [
            ".git", "__pycache__", ".pytest_cache", "node_modules",
            ".venv", "venv", "env", ".env",
            "test_results", "reports", "SPEC/generated"
        ]

        path_str = str(path)
        return any(pattern in path_str for pattern in excluded_patterns)


if __name__ == "__main__":
    unittest.main(verbosity=2)