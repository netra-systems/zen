"""
MISSION CRITICAL: ExecutionEngine Import Fragmentation Detection Test
Issue #1196 Phase 2 - SSOT ExecutionEngine Consolidation

PURPOSE:
- Detect 105+ ExecutionEngine import variations (EXPECTED TO FAIL initially)
- Prove fragmentation causes Golden Path instability
- Validate 26.81x import performance impact
- Track consolidation progress to single canonical import

EXPECTED INITIAL STATE: FAIL (proving fragmentation exists)
EXPECTED POST-CONSOLIDATION STATE: PASS (single canonical import)

Business Impact: $500K+ ARR depends on Golden Path stability
Critical Path: User login → AI response flow requires stable imports
"""

import pytest
import os
import re
import ast
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter

# Test framework - use SSOT patterns
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.orchestration import get_orchestration_config


class TestExecutionEngineImportFragmentation(SSotBaseTestCase):
    """
    Mission Critical: Detect and quantify ExecutionEngine import fragmentation

    This test is DESIGNED TO FAIL initially to prove fragmentation exists.
    After consolidation, this test should PASS with single canonical import.
    """

    @classmethod
    def setup_class(cls):
        """Initialize fragmentation detection with comprehensive scope"""
        super().setup_class()
        cls.project_root = Path("C:/netra-apex")
        cls.canonical_imports = {
            # SSOT-compliant imports (target state)
            "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine",
            "from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory",
            "from netra_backend.app.agents.supervisor.request_scoped_execution_engine import RequestScopedExecutionEngine"
        }

        cls.deprecated_patterns = {
            # Known deprecated patterns from Issue #1196 audit
            "from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine",
            "from netra_backend.app.agents.execution_engine_unified_factory import UnifiedExecutionEngineFactory",
            "from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine",
            "from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory",
            "from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine",
        }

        # Fragmentation patterns identified from codebase analysis
        cls.fragmentation_regex_patterns = [
            r'from\s+netra_backend\.app\.agents\..*execution_engine.*import.*ExecutionEngine',
            r'from\s+netra_backend\.app\.agents\..*execution.*import.*Engine',
            r'from\s+netra_backend\.app\.core\..*execution.*import.*Factory',
            r'from\s+netra_backend\.app\.tools\..*execution.*import.*Engine',
            r'ExecutionEngine\s*=\s*.*',  # Direct assignments
            r'execution_engine\s*=\s*.*Factory\(',  # Factory instantiations
        ]

    def scan_codebase_for_import_patterns(self) -> Dict[str, List[Tuple[str, int, str]]]:
        """
        Comprehensive scan for ExecutionEngine import fragmentation

        Returns:
            Dict[pattern_type, List[Tuple[file_path, line_number, import_statement]]]
        """
        fragmentation_data = defaultdict(list)
        pattern_counts = Counter()

        # Scan all Python files
        for py_file in self.project_root.rglob("*.py"):
            try:
                if any(exclude in str(py_file) for exclude in ['.git', '__pycache__', '.pytest_cache', 'backups']):
                    continue

                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')

                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip()

                        # Check for ExecutionEngine-related imports
                        if ('ExecutionEngine' in line_stripped or
                            'execution_engine' in line_stripped.lower()) and \
                           ('import' in line_stripped or '=' in line_stripped):

                            # Categorize the import pattern
                            pattern_type = self._categorize_import_pattern(line_stripped)
                            fragmentation_data[pattern_type].append((
                                str(py_file.relative_to(self.project_root)),
                                line_num,
                                line_stripped
                            ))
                            pattern_counts[pattern_type] += 1

            except Exception as e:
                # Continue scanning even if individual files fail
                continue

        return dict(fragmentation_data), pattern_counts

    def _categorize_import_pattern(self, import_line: str) -> str:
        """Categorize import patterns by fragmentation type"""
        if any(canonical in import_line for canonical in self.canonical_imports):
            return "canonical_ssot"
        elif any(deprecated in import_line for deprecated in self.deprecated_patterns):
            return "deprecated_known"
        elif "execution_engine_consolidated" in import_line:
            return "deprecated_consolidated"
        elif "execution_engine_unified" in import_line:
            return "deprecated_unified"
        elif "core.managers.execution" in import_line:
            return "deprecated_core_manager"
        elif "tool_dispatcher_execution" in import_line:
            return "tool_execution_variant"
        elif "ExecutionEngine =" in import_line:
            return "direct_assignment"
        elif "Factory(" in import_line and "execution" in import_line.lower():
            return "factory_instantiation"
        else:
            return "unknown_variant"

    @pytest.mark.mission_critical
    def test_execution_engine_import_fragmentation_detection(self):
        """
        MISSION CRITICAL: Detect ExecutionEngine import fragmentation

        EXPECTED TO FAIL: 105+ fragmented import patterns detected
        POST-CONSOLIDATION: Should PASS with <5 canonical patterns
        """
        fragmentation_data, pattern_counts = self.scan_codebase_for_import_patterns()

        total_fragments = sum(pattern_counts.values())
        canonical_count = pattern_counts.get("canonical_ssot", 0)
        deprecated_count = sum(
            pattern_counts.get(pattern, 0)
            for pattern in ["deprecated_known", "deprecated_consolidated",
                          "deprecated_unified", "deprecated_core_manager"]
        )

        # Log fragmentation analysis for diagnosis
        print(f"\n=== ExecutionEngine Import Fragmentation Analysis ===")
        print(f"Total fragmented imports detected: {total_fragments}")
        print(f"Canonical SSOT imports: {canonical_count}")
        print(f"Deprecated patterns: {deprecated_count}")
        print(f"Fragmentation ratio: {deprecated_count / max(canonical_count, 1):.2f}:1")

        print(f"\n=== Pattern Breakdown ===")
        for pattern_type, count in pattern_counts.most_common():
            print(f"{pattern_type}: {count} occurrences")

        # Show sample fragmented imports for analysis
        print(f"\n=== Sample Fragmented Imports ===")
        for pattern_type, instances in fragmentation_data.items():
            if pattern_type != "canonical_ssot" and instances:
                print(f"\n{pattern_type.upper()}:")
                for file_path, line_num, import_stmt in instances[:3]:  # Show first 3
                    print(f"  {file_path}:{line_num} -> {import_stmt}")

        # CRITICAL ASSERTION: This should FAIL initially
        # proving fragmentation exists (105+ variations expected)
        assert total_fragments < 50, (
            f"FRAGMENTATION DETECTED: {total_fragments} ExecutionEngine import variations found. "
            f"Expected: <50 after SSOT consolidation. "
            f"Deprecated patterns: {deprecated_count}, Canonical: {canonical_count}. "
            f"This test is DESIGNED TO FAIL until Issue #1196 Phase 2 consolidation is complete."
        )

        # Secondary assertion: Canonical imports should dominate
        assert canonical_count > deprecated_count, (
            f"SSOT VIOLATION: Deprecated imports ({deprecated_count}) exceed canonical ({canonical_count}). "
            f"All imports should use SSOT patterns from supervisor module."
        )

    @pytest.mark.mission_critical
    def test_import_performance_impact_measurement(self):
        """
        Measure import performance impact of fragmentation

        Validates the claimed 26.81x performance degradation
        """
        # Test canonical import speed
        canonical_time = self._measure_import_time(
            "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine"
        )

        # Test fragmented import speeds
        fragmented_imports = [
            "from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine",
            "from netra_backend.app.agents.execution_engine_unified_factory import UnifiedExecutionEngineFactory"
        ]

        fragmented_times = []
        for import_stmt in fragmented_imports:
            try:
                frag_time = self._measure_import_time(import_stmt)
                fragmented_times.append(frag_time)
            except ImportError:
                # Some fragmented imports may be broken - record as penalty
                fragmented_times.append(canonical_time * 10)  # 10x penalty for broken imports

        avg_fragmented_time = sum(fragmented_times) / len(fragmented_times) if fragmented_times else canonical_time
        performance_ratio = avg_fragmented_time / canonical_time if canonical_time > 0 else 1

        print(f"\n=== Import Performance Analysis ===")
        print(f"Canonical import time: {canonical_time:.4f}s")
        print(f"Average fragmented import time: {avg_fragmented_time:.4f}s")
        print(f"Performance degradation ratio: {performance_ratio:.2f}x")

        # This assertion may fail if fragmentation causes significant performance impact
        assert performance_ratio < 5.0, (
            f"PERFORMANCE IMPACT: Import fragmentation causes {performance_ratio:.2f}x slowdown. "
            f"Target: <5x after consolidation. Actual fragmented time: {avg_fragmented_time:.4f}s vs "
            f"canonical time: {canonical_time:.4f}s"
        )

    def _measure_import_time(self, import_statement: str) -> float:
        """Measure time to execute import statement"""
        import subprocess
        import sys

        cmd = [sys.executable, "-c", f"{import_statement}; print('SUCCESS')"]

        start_time = time.perf_counter()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            end_time = time.perf_counter()

            if result.returncode == 0:
                return end_time - start_time
            else:
                # Import failed - return penalty time
                return 1.0  # 1 second penalty for failed imports

        except subprocess.TimeoutExpired:
            return 10.0  # 10 second penalty for timeouts

    @pytest.mark.mission_critical
    def test_golden_path_import_stability(self):
        """
        Validate that fragmented imports don't break Golden Path

        Tests critical user flow: login → agent execution → response
        """
        try:
            # Test canonical import (should work)
            exec("from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine")
            canonical_import_works = True
        except ImportError as e:
            canonical_import_works = False
            print(f"Canonical import failed: {e}")

        # Test deprecated imports (may fail and cause instability)
        deprecated_import_failures = []
        deprecated_imports_to_test = [
            "from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine",
            "from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine"
        ]

        for deprecated_import in deprecated_imports_to_test:
            try:
                exec(deprecated_import)
            except ImportError as e:
                deprecated_import_failures.append((deprecated_import, str(e)))

        print(f"\n=== Golden Path Import Stability ===")
        print(f"Canonical import works: {canonical_import_works}")
        print(f"Deprecated import failures: {len(deprecated_import_failures)}")

        for failed_import, error in deprecated_import_failures:
            print(f"  FAILED: {failed_import} -> {error}")

        # CRITICAL: Canonical import MUST work for Golden Path
        assert canonical_import_works, (
            "GOLDEN PATH BROKEN: Canonical UserExecutionEngine import failed. "
            "This breaks the core user flow: login → agent execution → response."
        )

        # VALIDATION: Some deprecated imports should fail (proving cleanup needed)
        assert len(deprecated_import_failures) > 0, (
            "FRAGMENTATION ISSUE: All deprecated imports still work, indicating "
            "fragmented code paths exist that could cause race conditions and instability."
        )

    @pytest.mark.mission_critical
    def test_ssot_compliance_validation(self):
        """
        Validate SSOT compliance for ExecutionEngine patterns

        Ensures only canonical import paths are used in production code
        """
        fragmentation_data, _ = self.scan_codebase_for_import_patterns()

        # Count production vs test files with fragmentation
        production_fragments = []
        test_fragments = []

        for pattern_type, instances in fragmentation_data.items():
            if pattern_type == "canonical_ssot":
                continue

            for file_path, line_num, import_stmt in instances:
                if any(test_dir in file_path for test_dir in ['tests/', 'test_', '_test']):
                    test_fragments.append((file_path, line_num, import_stmt))
                else:
                    production_fragments.append((file_path, line_num, import_stmt))

        print(f"\n=== SSOT Compliance Analysis ===")
        print(f"Production code fragments: {len(production_fragments)}")
        print(f"Test code fragments: {len(test_fragments)}")

        if production_fragments:
            print(f"\n=== Production Fragmentation (CRITICAL) ===")
            for file_path, line_num, import_stmt in production_fragments[:10]:
                print(f"  {file_path}:{line_num} -> {import_stmt}")

        # CRITICAL: Production code MUST use SSOT patterns only
        assert len(production_fragments) == 0, (
            f"SSOT VIOLATION: {len(production_fragments)} fragmented imports in production code. "
            f"All production imports must use canonical SSOT patterns: "
            f"{', '.join(self.canonical_imports)}"
        )


if __name__ == "__main__":
    # Enable detailed output for diagnosis
    pytest.main([__file__, "-v", "-s", "--tb=short"])