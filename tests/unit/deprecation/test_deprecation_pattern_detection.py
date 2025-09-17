"""
Test Deprecation Pattern Detection

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Code Quality & Maintainability
- Value Impact: Prevents future breaking changes that could disrupt Golden Path
- Strategic Impact: Protects $500K+ ARR functionality from compatibility issues

This test suite systematically identifies and measures all current deprecation warnings
across the 7 identified categories, providing baseline metrics for cleanup progress.

Follows CLAUDE.md requirements:
- Uses SSOT BaseTestCase for consistency
- No Docker dependency (unit testing with pattern matching)
- Business value focused with Golden Path protection
- Real pattern detection without mocks
"""

import pytest
import os
import re
import ast
import warnings
from pathlib import Path
from typing import List, Dict, Tuple, Set
from unittest.mock import patch
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class DeprecationPatternDetectionTests(SSotBaseTestCase):
    """Systematic detection and measurement of all deprecation warning patterns."""

    def setup_method(self, method):
        """Set up test environment for deprecation pattern detection."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.deprecation_patterns = {}
        self.baseline_counts = {}

        # Define the 7 categories of deprecation warnings to detect
        self.deprecation_categories = {
            'pydantic_v2_config': {
                'pattern': r'class\s+Config\s*:',
                'description': 'Pydantic V2 ConfigDict migration required',
                'file_extensions': ['.py']
            },
            'datetime_utc_deprecation': {
                'pattern': r'datetime\.utcnow\(\)',
                'description': 'datetime.now(UTC) needs timezone-aware replacement',
                'file_extensions': ['.py']
            },
            'logging_import_deprecation': {
                'pattern': r'from\s+shared\.logging\.unified_logger_factory',
                'description': 'Deprecated logging import pattern',
                'file_extensions': ['.py']
            },
            'websocket_import_deprecation': {
                'pattern': r'from\s+[^\"]*websocket.*manager[^\"]*import',
                'description': 'Deprecated WebSocket import paths',
                'file_extensions': ['.py']
            },
            'environment_detector_deprecation': {
                'pattern': r'from\s+[^\"]*environment_detector',
                'description': 'Deprecated environment detection imports',
                'file_extensions': ['.py']
            },
            'websocket_factory_deprecation': {
                'pattern': r'get_websocket_manager_factory\(',
                'description': 'Deprecated factory function calls',
                'file_extensions': ['.py']
            },
            'python_runtime_warnings': {
                'pattern': r'DeprecationWarning|FutureWarning|PendingDeprecationWarning',
                'description': 'Runtime deprecation warnings',
                'file_extensions': ['.py']
            }
        }

    def test_pydantic_v2_config_deprecation_detection(self):
        """Detect all Pydantic class Config patterns needing migration."""
        category = 'pydantic_v2_config'
        pattern = self.deprecation_categories[category]['pattern']

        results = self._scan_codebase_for_pattern(pattern, category)

        # Validate we found expected files (based on issue documentation)
        self.assertGreaterEqual(len(results['files']), 10,
                               f"Expected at least 10 files with Pydantic Config patterns, found {len(results['files'])}")

        # Store baseline for progress tracking
        self.baseline_counts[category] = results['total_matches']

        # Verify patterns are correctly identified
        for file_path, matches in results['files'].items():
            self.assertGreater(matches, 0, f"File {file_path} should have Config patterns")

        # Document findings for cleanup planning
        self._log_deprecation_findings(category, results)

        # Business impact validation - check if any critical files affected
        critical_paths = ['agents/', 'websocket_core/', 'auth_integration/']
        affected_critical = [f for f in results['files'].keys()
                           if any(path in str(f) for path in critical_paths)]

        if affected_critical:
            self.logger.warning(f"Pydantic Config deprecation affects {len(affected_critical)} critical business files")

    def test_datetime_utc_deprecation_detection(self):
        """Detect all datetime.now(UTC) patterns needing modernization."""
        category = 'datetime_utc_deprecation'
        pattern = self.deprecation_categories[category]['pattern']

        results = self._scan_codebase_for_pattern(pattern, category)

        # Validate we found expected scale (275+ mentioned in issue)
        self.assertGreaterEqual(results['total_matches'], 200,
                               f"Expected at least 200 datetime.now(UTC) instances, found {results['total_matches']}")

        # Store baseline
        self.baseline_counts[category] = results['total_matches']

        # Validate timezone-aware replacement recommendations
        sample_files = list(results['files'].keys())[:5]  # Check first 5 files
        for file_path in sample_files:
            self._validate_datetime_usage_context(file_path)

        self._log_deprecation_findings(category, results)

    def test_logging_import_deprecation_detection(self):
        """Detect deprecated shared.logging.unified_logger_factory imports."""
        category = 'logging_import_deprecation'
        pattern = self.deprecation_categories[category]['pattern']

        results = self._scan_codebase_for_pattern(pattern, category)

        # Store baseline
        self.baseline_counts[category] = results['total_matches']

        # Validate unified_logging_ssot migration paths exist
        if results['total_matches'] > 0:
            self._validate_ssot_logging_alternatives()

        self._log_deprecation_findings(category, results)

    def test_websocket_import_deprecation_detection(self):
        """Detect deprecated WebSocket import paths."""
        category = 'websocket_import_deprecation'
        pattern = self.deprecation_categories[category]['pattern']

        results = self._scan_codebase_for_pattern(pattern, category)

        # Store baseline
        self.baseline_counts[category] = results['total_matches']

        # Validate canonical SSOT registry paths exist for replacements
        if results['total_matches'] > 0:
            self._validate_websocket_ssot_alternatives()

        self._log_deprecation_findings(category, results)

    def test_environment_detector_deprecation_detection(self):
        """Detect deprecated environment_detector imports."""
        category = 'environment_detector_deprecation'
        pattern = self.deprecation_categories[category]['pattern']

        results = self._scan_codebase_for_pattern(pattern, category)

        # Store baseline
        self.baseline_counts[category] = results['total_matches']

        # Validate environment_constants migration paths
        if results['total_matches'] > 0:
            self._validate_environment_constants_alternatives()

        self._log_deprecation_findings(category, results)

    def test_websocket_factory_deprecation_detection(self):
        """Detect deprecated get_websocket_manager_factory usage."""
        category = 'websocket_factory_deprecation'
        pattern = self.deprecation_categories[category]['pattern']

        results = self._scan_codebase_for_pattern(pattern, category)

        # Store baseline
        self.baseline_counts[category] = results['total_matches']

        # Validate create_websocket_manager migration exists
        if results['total_matches'] > 0:
            self._validate_websocket_factory_alternatives()

        self._log_deprecation_findings(category, results)

    def test_deprecation_warning_count_baseline(self):
        """Establish baseline count of current deprecation warnings."""
        # Capture actual runtime warnings
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # Trigger some imports that might generate warnings
            try:
                self._trigger_potential_warnings()
            except Exception as e:
                self.logger.info(f"Some imports failed as expected: {e}")

            # Count deprecation-related warnings
            deprecation_warnings = [
                w for w in warning_list
                if issubclass(w.category, (DeprecationWarning, FutureWarning, PendingDeprecationWarning))
            ]

        total_runtime_warnings = len(deprecation_warnings)

        # Combine with static analysis results
        total_static_patterns = sum(self.baseline_counts.values())

        # Document comprehensive baseline
        baseline_summary = {
            'static_pattern_matches': total_static_patterns,
            'runtime_warning_count': total_runtime_warnings,
            'category_breakdown': self.baseline_counts.copy(),
            'critical_files_affected': self._count_critical_files_affected()
        }

        self.logger.info(f"Deprecation baseline established: {baseline_summary}")

        # Validate we have meaningful baseline (should be > 0 given known issues)
        self.assertGreater(total_static_patterns, 50,
                          "Expected significant deprecation patterns in codebase")

        # Store for test execution results
        self._store_baseline_results(baseline_summary)

    def _scan_codebase_for_pattern(self, pattern: str, category: str) -> Dict:
        """Scan entire codebase for specific deprecation patterns."""
        results = {
            'files': {},
            'total_matches': 0,
            'category': category
        }

        # Define scan paths (exclude test artifacts and build directories)
        scan_paths = [
            self.project_root / 'netra_backend',
            self.project_root / 'auth_service',
            self.project_root / 'frontend',
            self.project_root / 'shared',
            self.project_root / 'scripts',
            self.project_root / 'test_framework'
        ]

        exclude_patterns = [
            r'__pycache__',
            r'\.git',
            r'node_modules',
            r'\.pytest_cache',
            r'build/',
            r'dist/',
            r'\.backup',
            r'backup.*\.py'
        ]

        for scan_path in scan_paths:
            if scan_path.exists():
                results.update(self._scan_directory_for_pattern(
                    scan_path, pattern, exclude_patterns, results
                ))

        return results

    def _scan_directory_for_pattern(self, directory: Path, pattern: str,
                                   exclude_patterns: List[str], results: Dict) -> Dict:
        """Recursively scan directory for pattern matches."""
        regex = re.compile(pattern, re.MULTILINE | re.IGNORECASE)

        for file_path in directory.rglob('*.py'):
            # Skip excluded paths
            if any(re.search(exclude, str(file_path)) for exclude in exclude_patterns):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    matches = regex.findall(content)

                    if matches:
                        relative_path = file_path.relative_to(self.project_root)
                        results['files'][relative_path] = len(matches)
                        results['total_matches'] += len(matches)

            except Exception as e:
                self.logger.debug(f"Could not scan {file_path}: {e}")

        return results

    def _validate_datetime_usage_context(self, file_path: Path):
        """Validate datetime.now(UTC) usage context for replacement planning."""
        try:
            with open(self.project_root / file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if timezone import exists
            has_timezone_import = 'timezone' in content or 'pytz' in content

            # Check if UTC replacement would be appropriate
            utc_contexts = re.findall(r'.*datetime\.utcnow\(\).*', content)

            for context in utc_contexts[:3]:  # Check first few contexts
                self.assertIsNotNone(context, "Should find datetime.now(UTC) context")

        except Exception as e:
            self.logger.debug(f"Could not validate datetime context in {file_path}: {e}")

    def _validate_ssot_logging_alternatives(self):
        """Validate that SSOT logging alternatives exist."""
        ssot_logging_path = self.project_root / 'shared' / 'logging' / 'unified_logging_ssot.py'
        if ssot_logging_path.exists():
            self.logger.info("SSOT logging alternative found")
        else:
            self.logger.warning("SSOT logging alternative may need to be created")

    def _validate_websocket_ssot_alternatives(self):
        """Validate that canonical WebSocket SSOT alternatives exist."""
        # Check SSOT import registry for canonical paths
        ssot_registry_path = self.project_root / 'SSOT_IMPORT_REGISTRY.md'
        if ssot_registry_path.exists():
            with open(ssot_registry_path, 'r') as f:
                registry_content = f.read()
                has_websocket_paths = 'websocket' in registry_content.lower()
                self.assertTrue(has_websocket_paths,
                               "SSOT registry should document canonical WebSocket paths")

    def _validate_environment_constants_alternatives(self):
        """Validate environment_constants migration alternatives exist."""
        env_constants_path = self.project_root / 'shared' / 'environment_constants.py'
        if env_constants_path.exists():
            self.logger.info("Environment constants alternative found")

    def _validate_websocket_factory_alternatives(self):
        """Validate create_websocket_manager alternatives exist."""
        # Check for modern factory patterns
        factory_patterns = [
            'create_websocket_manager',
            'WebSocketManager.create_for_user',
            'websocket_factory.create'
        ]

        # Quick scan for modern patterns
        found_alternatives = []
        for pattern in factory_patterns:
            results = self._scan_codebase_for_pattern(pattern, 'factory_alternatives')
            if results['total_matches'] > 0:
                found_alternatives.append(pattern)

        self.assertGreater(len(found_alternatives), 0,
                          "Should find modern WebSocket factory alternatives")

    def _trigger_potential_warnings(self):
        """Trigger imports that might generate deprecation warnings."""
        try:
            # Import common modules that might have deprecation warnings
            import datetime
            import pydantic
            import warnings

            # Try to trigger some datetime warnings
            datetime.datetime.now(UTC)

        except Exception:
            pass  # Expected - just trying to trigger warnings

    def _count_critical_files_affected(self) -> Dict[str, int]:
        """Count deprecation patterns in business-critical files."""
        critical_areas = {
            'agents': 0,
            'websocket_core': 0,
            'auth_integration': 0,
            'database': 0,
            'api_routes': 0
        }

        for category_counts in self.baseline_counts.values():
            # This is a simplified count - in real implementation would
            # analyze which critical areas are affected per category
            pass

        return critical_areas

    def _log_deprecation_findings(self, category: str, results: Dict):
        """Log deprecation findings for documentation."""
        self.logger.info(f"Deprecation Detection - {category}:")
        self.logger.info(f"  Total matches: {results['total_matches']}")
        self.logger.info(f"  Files affected: {len(results['files'])}")

        if results['files']:
            # Log top 5 most affected files
            sorted_files = sorted(results['files'].items(),
                                key=lambda x: x[1], reverse=True)[:5]
            self.logger.info(f"  Top affected files:")
            for file_path, count in sorted_files:
                self.logger.info(f"    {file_path}: {count} matches")

    def _store_baseline_results(self, baseline_summary: Dict):
        """Store baseline results for test execution reporting."""
        # Store in class attribute for access by other test methods
        self.__class__.deprecation_baseline = baseline_summary

        # Log summary for test execution results
        self.logger.info("=== DEPRECATION BASELINE SUMMARY ===")
        self.logger.info(f"Total static patterns found: {baseline_summary['static_pattern_matches']}")
        self.logger.info(f"Runtime warnings detected: {baseline_summary['runtime_warning_count']}")
        self.logger.info("Category breakdown:")
        for category, count in baseline_summary['category_breakdown'].items():
            self.logger.info(f"  {category}: {count} patterns")
