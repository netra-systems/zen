"""
Issue #1083 Docker Manager SSOT Violation Detection - Refined Implementation Count

Focus on actual UnifiedDockerManager implementations (excluding test files).
This test specifically validates the core SSOT violation.
"""

import unittest
import os
import sys
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestDockerManagerImplementationCountRefined(unittest.TestCase):
    """Refined test focusing on actual Docker Manager implementations."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent.parent

    def test_actual_docker_manager_implementations_count(self):
        """Test: Count actual UnifiedDockerManager implementations (excluding tests)."""
        implementations = self._find_actual_docker_manager_implementations()

        # Expected findings based on initial analysis
        expected_implementations = [
            "test_framework/unified_docker_manager.py",  # Primary implementation
            "test_framework/docker/unified_docker_manager.py"  # Mock implementation
        ]

        actual_implementations = [
            str(impl.relative_to(self.project_root)) for impl in implementations
        ]

        print(f"\n🔍 IMPLEMENTATION ANALYSIS:")
        print(f"Found {len(implementations)} actual UnifiedDockerManager implementations:")
        for impl in actual_implementations:
            print(f"  - {impl}")

        print(f"\n📊 SSOT VIOLATION CONFIRMATION:")
        print(f"Expected implementations: {expected_implementations}")
        print(f"Actual implementations: {actual_implementations}")

        # Confirm SSOT violation exists
        if len(implementations) > 1:
            print(f"\n🚨 SSOT VIOLATION CONFIRMED:")
            print(f"  - Found {len(implementations)} implementations (target: 1)")
            print(f"  - This confirms Issue #1083 Docker Manager SSOT consolidation is needed")

        # The test succeeds if it detects the expected violation
        self.assertGreaterEqual(
            len(implementations),
            2,
            "Expected to find at least 2 Docker Manager implementations to confirm SSOT violation"
        )

    def test_implementation_type_analysis(self):
        """Test: Analyze the type of each Docker Manager implementation."""
        implementations = self._find_actual_docker_manager_implementations()

        implementation_analysis = {}

        for impl_path in implementations:
            analysis = self._analyze_implementation(impl_path)
            rel_path = str(impl_path.relative_to(self.project_root))
            implementation_analysis[rel_path] = analysis

        print(f"\n📋 IMPLEMENTATION TYPE ANALYSIS:")
        for path, analysis in implementation_analysis.items():
            print(f"\n{path}:")
            print(f"  - Type: {analysis['type']}")
            print(f"  - Methods: {len(analysis['methods'])}")
            print(f"  - Has real Docker logic: {analysis['has_docker_logic']}")
            print(f"  - Has mock logic: {analysis['has_mock_logic']}")

        # Validate we found expected implementation types
        types_found = [analysis['type'] for analysis in implementation_analysis.values()]

        print(f"\n📊 ANALYSIS SUMMARY:")
        print(f"Types found: {types_found}")

        # The test succeeds if we detect different implementation types or duplicates
        self.assertGreater(len(implementation_analysis), 0, "Should find at least one implementation")

        if len(types_found) > 1:
            print(f"✅ SSOT VIOLATION: Multiple implementations with different characteristics")
        elif len(types_found) == 1 and len(implementation_analysis) > 1:
            print(f"✅ SSOT VIOLATION: Multiple identical implementations (duplication)")
        else:
            print(f"ℹ️  Single implementation found")

    def _find_actual_docker_manager_implementations(self) -> List[Path]:
        """Find actual UnifiedDockerManager class implementations (excluding test files)."""
        implementations = []

        # Search for class definitions, excluding test files
        for py_file in self.project_root.rglob("*.py"):
            if self._is_excluded_path(py_file):
                continue

            # Skip test files for this analysis
            if self._is_test_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "class UnifiedDockerManager" in content:
                        implementations.append(py_file)
            except (UnicodeDecodeError, PermissionError):
                continue

        return implementations

    def _analyze_implementation(self, file_path: Path) -> dict:
        """Analyze a Docker Manager implementation to determine its type."""
        analysis = {
            'type': 'unknown',
            'methods': [],
            'has_docker_logic': False,
            'has_mock_logic': False
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # Check for mock indicators (specific mock imports/usage)
                mock_indicators = ['MagicMock', 'AsyncMock', 'from unittest.mock import']
                analysis['has_mock_logic'] = any(indicator in content for indicator in mock_indicators)

                # Check for real Docker logic (broader set of indicators)
                docker_indicators = [
                    'subprocess', 'docker compose', 'docker-compose', 'docker run',
                    'container.', 'docker ps', 'DockerClient', 'execute_docker_command'
                ]
                analysis['has_docker_logic'] = any(indicator in content for indicator in docker_indicators)

                # Determine type
                if analysis['has_mock_logic'] and not analysis['has_docker_logic']:
                    analysis['type'] = 'mock'
                elif analysis['has_docker_logic'] and not analysis['has_mock_logic']:
                    analysis['type'] = 'real'
                elif analysis['has_mock_logic'] and analysis['has_docker_logic']:
                    analysis['type'] = 'hybrid'
                else:
                    analysis['type'] = 'unknown'

                # Extract method names
                lines = content.split('\n')
                in_class = False
                for line in lines:
                    stripped = line.strip()

                    if stripped.startswith("class UnifiedDockerManager"):
                        in_class = True
                        continue

                    if in_class:
                        if stripped.startswith("class ") and not stripped.startswith("class UnifiedDockerManager"):
                            break

                        if stripped.startswith("def ") or stripped.startswith("async def "):
                            method_name = stripped.split('(')[0].replace('def ', '').replace('async ', '').strip()
                            analysis['methods'].append(method_name)

        except Exception:
            pass

        return analysis

    def _is_excluded_path(self, path: Path) -> bool:
        """Check if path should be excluded from search."""
        excluded_patterns = [
            ".git", "__pycache__", ".pytest_cache", "node_modules",
            ".venv", "venv", "env", ".env",
            "test_results", "reports", "SPEC/generated"
        ]

        path_str = str(path)
        return any(pattern in path_str for pattern in excluded_patterns)

    def _is_test_file(self, path: Path) -> bool:
        """Check if this is a test file."""
        path_str = str(path)
        # More specific test file detection - avoid catching test_framework itself
        test_indicators = ['/test_', '\\test_', '/tests/', '\\tests\\']

        # Exception: test_framework is not a test directory, it's the framework itself
        if 'test_framework' in path_str and not any(indicator in path_str for indicator in ['/tests/', '\\tests\\']):
            return False

        return any(indicator in path_str for indicator in test_indicators)


if __name__ == "__main__":
    unittest.main(verbosity=2)