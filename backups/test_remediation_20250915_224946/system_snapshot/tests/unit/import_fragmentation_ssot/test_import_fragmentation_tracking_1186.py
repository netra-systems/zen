"""Test Issue #1186: Import Fragmentation Tracking - SSOT Consolidation

This test suite tracks and validates the reduction of import fragmentation identified
in Issue #1186 Phase 4 status update. These tests measure progress toward SSOT compliance.

Expected Behavior: These tests SHOULD FAIL to demonstrate:
1. 414 fragmented imports (target: <5)
2. 87.5% canonical import usage (target: >95%)
3. Multiple import patterns for UserExecutionEngine
4. Legacy execution engine import paths

Business Impact: Import fragmentation prevents SSOT compliance and creates
maintenance complexity, blocking enterprise-grade architecture consistency.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: SSOT compliance and code maintainability
- Value Impact: Reduces import fragmentation from 414 to <5 items
- Strategic Impact: Foundation for scalable architecture and developer productivity
"""

import ast
import os
import re
import sys
import unittest
import pytest
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional
from collections import defaultdict, Counter


@pytest.mark.unit
class TestImportFragmentationTracking(unittest.TestCase):
    """Test class to track and reduce UserExecutionEngine import fragmentation"""

    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.canonical_import = "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine"
        self.target_fragmentation_count = 5  # Target: <5 fragmented imports
        self.target_canonical_usage = 95.0  # Target: >95% canonical usage

    def test_1_canonical_import_usage_measurement(self):
        """
        Test 1: Measure canonical import usage percentage

        EXPECTED TO FAIL: Current 87.5%, Target >95%
        """
        print("\n📊 IMPORT FRAGMENTATION TEST 1: Measuring canonical import usage...")

        import_analysis = self._analyze_import_patterns()
        canonical_usage_percentage = self._calculate_canonical_usage_percentage(import_analysis)

        # This test should FAIL to demonstrate current usage below target
        self.assertGreaterEqual(
            canonical_usage_percentage,
            self.target_canonical_usage,
            f"❌ EXPECTED FAILURE: Canonical import usage is {canonical_usage_percentage:.1f}%, "
            f"target is >{self.target_canonical_usage}%. "
            f"Issue #1186 Phase 4 reported 87.5% usage. Import patterns found:\n"
            + '\n'.join([f"  - '{pattern}': {count} files ({count/sum(import_analysis.values())*100:.1f}%)"
                        for pattern, count in sorted(import_analysis.items(), key=lambda x: x[1], reverse=True)[:5]])
        )

    def test_2_fragmented_import_detection(self):
        """
        Test 2: Detect and count fragmented imports

        EXPECTED TO FAIL: Current 414 items, Target <5 items
        """
        print("\n📊 IMPORT FRAGMENTATION TEST 2: Detecting fragmented imports...")

        fragmented_imports = self._detect_fragmented_imports()
        fragmentation_count = len(fragmented_imports)

        # This test should FAIL to demonstrate current fragmentation
        self.assertLess(
            fragmentation_count,
            self.target_fragmentation_count,
            f"❌ EXPECTED FAILURE: Found {fragmentation_count} fragmented imports, "
            f"target is <{self.target_fragmentation_count}. "
            f"Issue #1186 Phase 4 identified 414 fragmented imports. Examples:\n"
            + '\n'.join([f"  - {path}: {pattern}" for path, pattern in fragmented_imports[:10]])
            + (f"\n  ... and {len(fragmented_imports) - 10} more" if len(fragmented_imports) > 10 else "")
        )

    def test_3_deprecated_import_elimination(self):
        """
        Test 3: Validate deprecated import path elimination

        EXPECTED TO FAIL: Should reveal deprecated execution_engine_consolidated imports
        """
        print("\n📊 IMPORT FRAGMENTATION TEST 3: Validating deprecated import elimination...")

        deprecated_imports = self._scan_for_deprecated_imports()

        # This test should FAIL to demonstrate deprecated imports still exist
        self.assertEqual(
            len(deprecated_imports),
            0,
            f"❌ EXPECTED FAILURE: Found {len(deprecated_imports)} deprecated imports. "
            f"These should be eliminated as part of SSOT consolidation:\n"
            + '\n'.join([f"  - {path}: {deprecated_import}" for path, deprecated_import in deprecated_imports[:5]])
            + (f"\n  ... and {len(deprecated_imports) - 5} more" if len(deprecated_imports) > 5 else "")
        )

    def test_4_import_pattern_consistency_validation(self):
        """
        Test 4: Validate import pattern consistency across services

        EXPECTED TO FAIL: Should reveal multiple import patterns for same functionality
        """
        print("\n📊 IMPORT FRAGMENTATION TEST 4: Validating import pattern consistency...")

        pattern_consistency = self._analyze_import_pattern_consistency()
        unique_patterns = len(pattern_consistency)

        # This test should FAIL to demonstrate pattern inconsistency
        self.assertLessEqual(
            unique_patterns,
            1,
            f"❌ EXPECTED FAILURE: Found {unique_patterns} different import patterns for UserExecutionEngine. "
            f"SSOT requires exactly 1 canonical pattern. Patterns found:\n"
            + '\n'.join([f"  - '{pattern}': {files} files" for pattern, files in pattern_consistency.items()])
        )

    def test_5_legacy_execution_engine_path_detection(self):
        """
        Test 5: Detect legacy execution engine import paths

        EXPECTED TO FAIL: Should reveal legacy execution engine imports
        """
        print("\n📊 IMPORT FRAGMENTATION TEST 5: Detecting legacy execution engine paths...")

        legacy_paths = self._scan_for_legacy_execution_engine_paths()

        # This test should FAIL to demonstrate legacy paths exist
        self.assertEqual(
            len(legacy_paths),
            0,
            f"❌ EXPECTED FAILURE: Found {len(legacy_paths)} legacy execution engine import paths. "
            f"These should be migrated to canonical UserExecutionEngine imports:\n"
            + '\n'.join([f"  - {path}: {legacy_import}" for path, legacy_import in legacy_paths[:5]])
            + (f"\n  ... and {len(legacy_paths) - 5} more" if len(legacy_paths) > 5 else "")
        )

    def _analyze_import_patterns(self) -> Dict[str, int]:
        """Analyze all UserExecutionEngine import patterns across codebase"""
        import_patterns = defaultdict(int)

        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Find all UserExecutionEngine-related imports
                import_lines = re.findall(
                    r'(?:from\s+[\w.]+\s+import\s+.*UserExecutionEngine.*|import\s+.*UserExecutionEngine.*)',
                    content,
                    re.MULTILINE
                )

                for import_line in import_lines:
                    # Normalize the import line
                    normalized_import = re.sub(r'\s+', ' ', import_line.strip())
                    import_patterns[normalized_import] += 1

            except (UnicodeDecodeError, PermissionError):
                continue

        return dict(import_patterns)

    def _calculate_canonical_usage_percentage(self, import_analysis: Dict[str, int]) -> float:
        """Calculate percentage of canonical import usage"""
        if not import_analysis:
            return 0.0

        total_imports = sum(import_analysis.values())
        canonical_imports = import_analysis.get(self.canonical_import, 0)

        # Also count variations of the canonical import
        canonical_variations = [
            self.canonical_import,
            "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine",
        ]

        total_canonical = sum(import_analysis.get(variation, 0) for variation in canonical_variations)

        if total_imports == 0:
            return 0.0

        return (total_canonical / total_imports) * 100.0

    def _detect_fragmented_imports(self) -> List[Tuple[str, str]]:
        """Detect fragmented UserExecutionEngine imports"""
        fragmented_imports = []

        # Patterns that indicate import fragmentation
        fragmentation_patterns = [
            r'from.*execution_engine_consolidated.*import.*',  # Legacy consolidated imports
            r'from.*execution_engine_unified_factory.*import.*',  # Legacy unified factory
            r'import.*UserExecutionEngine.*as.*ExecutionEngine',  # Alias fragmentation
            r'from.*\.execution_engine\s+import.*UserExecutionEngine',  # Old path patterns
            r'from.*supervisor\.execution_engine.*import.*',  # Deprecated supervisor paths
        ]

        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in fragmentation_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        fragmented_imports.append((str(py_file), match))

            except (UnicodeDecodeError, PermissionError):
                continue

        return fragmented_imports

    def _scan_for_deprecated_imports(self) -> List[Tuple[str, str]]:
        """Scan for deprecated import patterns"""
        deprecated_imports = []

        # Deprecated import patterns from Issue #1186
        deprecated_patterns = [
            r'from.*execution_engine_consolidated.*import.*ExecutionEngine',
            r'from.*execution_engine_unified_factory.*import.*UnifiedExecutionEngineFactory',
            r'from.*execution_engine\s+import.*ExecutionEngine\s*$',  # Direct ExecutionEngine import
            r'from.*execution_factory.*import.*ExecutionEngineFactory',  # Wrong factory path
        ]

        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in deprecated_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        deprecated_imports.append((str(py_file), match))

            except (UnicodeDecodeError, PermissionError):
                continue

        return deprecated_imports

    def _analyze_import_pattern_consistency(self) -> Dict[str, int]:
        """Analyze consistency of import patterns"""
        pattern_counts = defaultdict(int)

        # Group similar import patterns
        pattern_groups = {
            'canonical_user_execution_engine': [
                r'from netra_backend\.app\.agents\.supervisor\.user_execution_engine import UserExecutionEngine',
            ],
            'legacy_execution_engine': [
                r'from.*execution_engine.*import.*ExecutionEngine',
                r'from.*execution_engine.*import.*UserExecutionEngine',
            ],
            'factory_patterns': [
                r'from.*execution_engine_factory.*import.*ExecutionEngineFactory',
                r'from.*execution_factory.*import.*',
            ],
            'consolidated_patterns': [
                r'from.*execution_engine_consolidated.*import.*',
                r'from.*unified_factory.*import.*',
            ],
        }

        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for group_name, patterns in pattern_groups.items():
                    for pattern in patterns:
                        if re.search(pattern, content, re.MULTILINE):
                            pattern_counts[group_name] += 1
                            break  # Count file only once per group

            except (UnicodeDecodeError, PermissionError):
                continue

        return dict(pattern_counts)

    def _scan_for_legacy_execution_engine_paths(self) -> List[Tuple[str, str]]:
        """Scan for legacy execution engine import paths"""
        legacy_paths = []

        # Legacy execution engine patterns
        legacy_patterns = [
            r'from netra_backend\.app\.agents\.execution_engine import ExecutionEngine',
            r'from netra_backend\.app\.agents\.supervisor\.execution_engine import ExecutionEngine',
            r'from netra_backend\.app\.core\.user_execution_engine import UserExecutionEngine',
            r'ExecutionEngine\(\)',  # Direct instantiation without factory
        ]

        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in legacy_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        legacy_paths.append((str(py_file), match))

            except (UnicodeDecodeError, PermissionError):
                continue

        return legacy_paths

    def _get_python_files(self) -> List[Path]:
        """Get Python files for analysis"""
        python_files = []

        # Focus on main source directories to avoid timeout
        search_paths = [
            self.project_root / 'netra_backend' / 'app',
            self.project_root / 'tests' / 'unit',
            self.project_root / 'tests' / 'integration',
            self.project_root / 'tests' / 'e2e',
        ]

        for search_path in search_paths:
            if search_path.exists():
                try:
                    python_files.extend(list(search_path.rglob('*.py')))
                except (OSError, PermissionError):
                    continue

        return python_files


@pytest.mark.unit
class TestImportFragmentationMetrics(unittest.TestCase):
    """Test class to measure import fragmentation reduction metrics"""

    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent

    def test_6_import_fragmentation_progress_tracking(self):
        """
        Test 6: Track import fragmentation reduction progress

        EXPECTED TO FAIL: Should measure progress toward fragmentation targets
        """
        print("\n📊 IMPORT METRICS TEST 6: Tracking fragmentation reduction progress...")

        progress_metrics = self._measure_fragmentation_progress()

        # Expected metrics for SSOT compliance
        expected_metrics = {
            'total_fragmented_imports': 5,  # Target: <5
            'canonical_usage_percentage': 95.0,  # Target: >95%
            'deprecated_import_count': 0,  # Target: 0
            'unique_import_patterns': 1,  # Target: 1 (SSOT)
        }

        for metric, expected_value in expected_metrics.items():
            actual_value = progress_metrics.get(metric, -1)

            if metric == 'canonical_usage_percentage':
                self.assertGreaterEqual(
                    actual_value,
                    expected_value,
                    f"❌ EXPECTED FAILURE: {metric} = {actual_value}%, expected >={expected_value}%. "
                    f"Issue #1186 Phase 4 reported 87.5% canonical usage."
                )
            elif metric == 'total_fragmented_imports':
                self.assertLess(
                    actual_value,
                    expected_value,
                    f"❌ EXPECTED FAILURE: {metric} = {actual_value}, expected <{expected_value}. "
                    f"Issue #1186 Phase 4 reported 414 fragmented imports."
                )
            else:
                self.assertEqual(
                    actual_value,
                    expected_value,
                    f"❌ EXPECTED FAILURE: {metric} = {actual_value}, expected {expected_value}. "
                    f"This indicates incomplete import fragmentation consolidation."
                )

    def test_7_ssot_import_compliance_validation(self):
        """
        Test 7: Validate SSOT import compliance across all services

        EXPECTED TO FAIL: Should validate single source of truth for imports
        """
        print("\n📊 IMPORT METRICS TEST 7: Validating SSOT import compliance...")

        ssot_compliance = self._validate_ssot_import_compliance()

        # This test should FAIL to demonstrate SSOT compliance gaps
        self.assertTrue(
            ssot_compliance['is_compliant'],
            f"❌ EXPECTED FAILURE: SSOT import compliance failed. "
            f"Violations found: {ssot_compliance['violation_count']}. "
            f"Details:\n" + '\n'.join([f"  - {violation}" for violation in ssot_compliance['violations'][:5]])
            + (f"\n  ... and {ssot_compliance['violation_count'] - 5} more" if ssot_compliance['violation_count'] > 5 else "")
        )

    def _measure_fragmentation_progress(self) -> Dict[str, float]:
        """Measure import fragmentation reduction progress"""
        metrics = {}

        # Create test instance to access methods
        test_instance = TestImportFragmentationTracking()
        test_instance.setUp()

        try:
            # Measure total fragmented imports
            fragmented_imports = test_instance._detect_fragmented_imports()
            metrics['total_fragmented_imports'] = len(fragmented_imports)

            # Measure canonical usage percentage
            import_analysis = test_instance._analyze_import_patterns()
            metrics['canonical_usage_percentage'] = test_instance._calculate_canonical_usage_percentage(import_analysis)

            # Measure deprecated import count
            deprecated_imports = test_instance._scan_for_deprecated_imports()
            metrics['deprecated_import_count'] = len(deprecated_imports)

            # Measure unique import patterns
            pattern_consistency = test_instance._analyze_import_pattern_consistency()
            metrics['unique_import_patterns'] = len(pattern_consistency)

        except Exception as e:
            print(f"Warning: Error measuring fragmentation progress: {e}")
            metrics = {'error': -1}

        return metrics

    def _validate_ssot_import_compliance(self) -> Dict[str, any]:
        """Validate SSOT import compliance"""
        compliance_result = {
            'is_compliant': True,
            'violation_count': 0,
            'violations': []
        }

        try:
            # Create test instance to access methods
            test_instance = TestImportFragmentationTracking()
            test_instance.setUp()

            # Check for fragmented imports
            fragmented_imports = test_instance._detect_fragmented_imports()
            if fragmented_imports:
                compliance_result['is_compliant'] = False
                compliance_result['violation_count'] += len(fragmented_imports)
                compliance_result['violations'].extend([f"Fragmented import: {path}" for path, _ in fragmented_imports[:5]])

            # Check for deprecated imports
            deprecated_imports = test_instance._scan_for_deprecated_imports()
            if deprecated_imports:
                compliance_result['is_compliant'] = False
                compliance_result['violation_count'] += len(deprecated_imports)
                compliance_result['violations'].extend([f"Deprecated import: {path}" for path, _ in deprecated_imports[:5]])

            # Check canonical usage percentage
            import_analysis = test_instance._analyze_import_patterns()
            canonical_percentage = test_instance._calculate_canonical_usage_percentage(import_analysis)
            if canonical_percentage < 95.0:
                compliance_result['is_compliant'] = False
                compliance_result['violations'].append(f"Canonical usage below target: {canonical_percentage:.1f}% < 95%")

        except Exception as e:
            compliance_result['is_compliant'] = False
            compliance_result['violations'].append(f"Error validating compliance: {e}")

        return compliance_result


if __name__ == '__main__':
    print("🚨 Issue #1186 Import Fragmentation Tracking - SSOT Consolidation Tests")
    print("=" * 80)
    print("⚠️  WARNING: These tests are DESIGNED TO FAIL to demonstrate current fragmentation")
    print("📊 Expected: Test failures showing 414 fragmented imports (target: <5)")
    print("🎯 Current: 87.5% canonical usage (target: >95%)")
    print("🔧 Goal: Measure and track progress toward SSOT import compliance")
    print("=" * 80)

    unittest.main(verbosity=2)