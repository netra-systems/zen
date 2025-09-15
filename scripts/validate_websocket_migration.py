#!/usr/bin/env python3
"""
WebSocket Migration Validation Tools

This script provides comprehensive validation tools for measuring collection
performance improvements and ensuring functional preservation during the
Issue #1041 TestWebSocketConnection SSOT migration.

BUSINESS IMPACT:
- Validates resolution of pytest collection failures
- Measures collection performance improvements (target: 85-90% reduction)
- Ensures Golden Path functionality preservation
- Protects $500K+ ARR business value during migration

USAGE:
    # Measure collection performance
    python scripts/validate_websocket_migration.py --performance --directory tests/mission_critical/

    # Validate SSOT compliance
    python scripts/validate_websocket_migration.py --ssot-compliance --directory tests/

    # Test functionality preservation
    python scripts/validate_websocket_migration.py --functionality --file tests/mission_critical/test_websocket_agent_events_suite.py

    # Generate comprehensive validation report
    python scripts/validate_websocket_migration.py --full-report --directory tests/

VALIDATION AREAS:
- Collection performance (time and memory usage)
- SSOT compliance (import patterns and class elimination)
- Test functionality (success rates and behavior preservation)
- Warning reduction (pytest collection warnings)
- Golden Path protection (mission critical test validation)
"""

import os
import sys
import time
import json
import subprocess
import tempfile
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass, asdict
import argparse
import psutil
import threading


@dataclass
class PerformanceMetrics:
    """Performance measurement results for test collection."""
    directory: str
    collection_time: float
    memory_peak_mb: float
    memory_average_mb: float
    files_collected: int
    tests_collected: int
    warnings_count: int
    errors_count: int
    success: bool
    timestamp: str


@dataclass
class ComplianceReport:
    """SSOT compliance validation results."""
    file_path: str
    has_duplicate_classes: bool
    duplicate_class_count: int
    uses_ssot_imports: bool
    import_patterns: List[str]
    compliance_score: float  # 0-100%
    violations: List[str]
    recommendations: List[str]


@dataclass
class FunctionalityReport:
    """Test functionality validation results."""
    file_path: str
    test_success_rate: float
    execution_time: float
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    functionality_preserved: bool
    performance_change: float  # percentage change
    errors: List[str]


class WebSocketMigrationValidator:
    """
    Comprehensive validation utility for WebSocket test migration.

    This class provides performance measurement, compliance validation,
    and functionality testing to ensure successful Issue #1041 resolution.
    """

    def __init__(self, verbose: bool = False, baseline_dir: Optional[str] = None):
        """
        Initialize validator with configuration options.

        Args:
            verbose: Enable detailed logging output
            baseline_dir: Directory to store baseline measurements
        """
        self.verbose = verbose
        self.baseline_dir = Path(baseline_dir) if baseline_dir else Path("./baselines/websocket_migration")
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

        # Performance monitoring
        self.memory_samples = []
        self.monitoring_active = False

        # Test execution patterns
        self.test_patterns = [
            'test_websocket',
            'test_agent',
            'test_connection',
            'test_mission_critical'
        ]

        # Compliance patterns
        self.duplicate_class_patterns = [
            r'class TestWebSocketConnection[:\(]',
            r'class MockWebSocketConnection[:\(]',
            r'class WebSocketConnectionMock[:\(]',
        ]

        self.ssot_import_pattern = r'from test_framework\.ssot\.websocket_connection_test_utility import'

    def measure_collection_performance(self, directory: str, baseline: bool = False) -> PerformanceMetrics:
        """
        Measure pytest collection performance for given directory.

        Args:
            directory: Directory to measure collection performance
            baseline: If True, save as baseline for comparison

        Returns:
            PerformanceMetrics with detailed performance data
        """
        if self.verbose:
            print(f"Measuring collection performance for: {directory}")

        # Start memory monitoring
        self._start_memory_monitoring()

        start_time = time.time()
        collection_success = True
        files_collected = 0
        tests_collected = 0
        warnings_count = 0
        errors_count = 0

        try:
            # Run pytest collection with timing and output capture
            cmd = [
                sys.executable, '-m', 'pytest',
                '--collect-only',
                '--tb=no',
                '--quiet',
                directory
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout to prevent hanging
            )

            collection_time = time.time() - start_time

            # Parse output for metrics
            if result.returncode == 0:
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if 'collected' in line and 'item' in line:
                        # Extract test count from "collected X items"
                        match = re.search(r'collected (\d+) items?', line)
                        if match:
                            tests_collected = int(match.group(1))

                # Count files by looking for .py files in output
                files_collected = len([line for line in output_lines if '.py::' in line])

            # Count warnings and errors
            stderr_output = result.stderr
            warnings_count = stderr_output.count('warning')
            errors_count = stderr_output.count('ERROR')

            if result.returncode != 0:
                collection_success = False
                if self.verbose:
                    print(f"Collection failed with return code: {result.returncode}")

        except subprocess.TimeoutExpired:
            collection_time = 300.0  # Timeout value
            collection_success = False
            if self.verbose:
                print(f"Collection timed out after 5 minutes")

        except Exception as e:
            collection_time = time.time() - start_time
            collection_success = False
            if self.verbose:
                print(f"Collection error: {e}")

        finally:
            # Stop memory monitoring
            self._stop_memory_monitoring()

        # Calculate memory metrics
        memory_peak = max(self.memory_samples) if self.memory_samples else 0.0
        memory_average = sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0.0

        metrics = PerformanceMetrics(
            directory=directory,
            collection_time=collection_time,
            memory_peak_mb=memory_peak,
            memory_average_mb=memory_average,
            files_collected=files_collected,
            tests_collected=tests_collected,
            warnings_count=warnings_count,
            errors_count=errors_count,
            success=collection_success,
            timestamp=datetime.now().isoformat()
        )

        # Save baseline if requested
        if baseline:
            self._save_baseline(metrics)

        if self.verbose:
            print(f"Collection time: {collection_time:.2f}s")
            print(f"Memory peak: {memory_peak:.1f}MB")
            print(f"Tests collected: {tests_collected}")
            print(f"Warnings: {warnings_count}")

        return metrics

    def validate_ssot_compliance(self, file_path: str) -> ComplianceReport:
        """
        Validate SSOT compliance for a test file.

        Args:
            file_path: Path to test file to validate

        Returns:
            ComplianceReport with detailed compliance assessment
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for duplicate class definitions
            duplicate_classes = []
            for pattern in self.duplicate_class_patterns:
                matches = re.findall(pattern, content)
                duplicate_classes.extend(matches)

            has_duplicates = len(duplicate_classes) > 0
            duplicate_count = len(duplicate_classes)

            # Check for SSOT imports
            uses_ssot_imports = bool(re.search(self.ssot_import_pattern, content))

            # Extract all import patterns
            import_patterns = []
            for line in content.split('\n'):
                if 'import' in line and 'websocket' in line.lower():
                    import_patterns.append(line.strip())

            # Calculate compliance score
            compliance_score = self._calculate_compliance_score(
                has_duplicates, uses_ssot_imports, duplicate_count
            )

            # Generate violations and recommendations
            violations = []
            recommendations = []

            if has_duplicates:
                violations.append(f"Found {duplicate_count} duplicate class definitions")
                recommendations.append("Remove duplicate classes and use SSOT imports")

            if not uses_ssot_imports and has_duplicates:
                violations.append("Missing SSOT imports")
                recommendations.append("Add: from test_framework.ssot.websocket_connection_test_utility import TestWebSocketConnection")

            return ComplianceReport(
                file_path=file_path,
                has_duplicate_classes=has_duplicates,
                duplicate_class_count=duplicate_count,
                uses_ssot_imports=uses_ssot_imports,
                import_patterns=import_patterns,
                compliance_score=compliance_score,
                violations=violations,
                recommendations=recommendations
            )

        except Exception as e:
            return ComplianceReport(
                file_path=file_path,
                has_duplicate_classes=False,
                duplicate_class_count=0,
                uses_ssot_imports=False,
                import_patterns=[],
                compliance_score=0.0,
                violations=[f"Analysis error: {e}"],
                recommendations=["Fix file access/parsing issues"]
            )

    def validate_test_functionality(self, file_path: str, compare_to_baseline: bool = False) -> FunctionalityReport:
        """
        Validate test functionality after migration.

        Args:
            file_path: Path to test file to validate
            compare_to_baseline: If True, compare to baseline performance

        Returns:
            FunctionalityReport with detailed functionality assessment
        """
        if self.verbose:
            print(f"Validating functionality for: {file_path}")

        start_time = time.time()
        tests_passed = 0
        tests_failed = 0
        tests_skipped = 0
        execution_success = True
        errors = []

        try:
            # Run the specific test file
            cmd = [
                sys.executable, '-m', 'pytest',
                file_path,
                '-v',
                '--tb=short'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout per file
            )

            execution_time = time.time() - start_time

            # Parse test results
            output = result.stdout + result.stderr

            # Count test outcomes
            tests_passed = output.count('PASSED')
            tests_failed = output.count('FAILED')
            tests_skipped = output.count('SKIPPED')

            # Check for errors
            if result.returncode != 0:
                execution_success = False
                errors.append(f"Test execution failed with return code: {result.returncode}")

            # Extract error messages
            error_lines = [line for line in output.split('\n') if 'ERROR' in line or 'FAILED' in line]
            errors.extend(error_lines[:5])  # Limit to first 5 errors

        except subprocess.TimeoutExpired:
            execution_time = 180.0
            execution_success = False
            errors.append("Test execution timed out")

        except Exception as e:
            execution_time = time.time() - start_time
            execution_success = False
            errors.append(f"Execution error: {e}")

        # Calculate success rate
        total_tests = tests_passed + tests_failed + tests_skipped
        success_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0.0

        # Determine if functionality is preserved (>90% success rate)
        functionality_preserved = success_rate >= 90.0 and execution_success

        # Calculate performance change (if baseline available)
        performance_change = 0.0
        if compare_to_baseline:
            baseline_time = self._get_baseline_execution_time(file_path)
            if baseline_time > 0:
                performance_change = ((execution_time - baseline_time) / baseline_time) * 100

        return FunctionalityReport(
            file_path=file_path,
            test_success_rate=success_rate,
            execution_time=execution_time,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            tests_skipped=tests_skipped,
            functionality_preserved=functionality_preserved,
            performance_change=performance_change,
            errors=errors
        )

    def compare_performance(self, before_metrics: PerformanceMetrics, after_metrics: PerformanceMetrics) -> Dict[str, float]:
        """
        Compare performance metrics before and after migration.

        Args:
            before_metrics: Performance metrics before migration
            after_metrics: Performance metrics after migration

        Returns:
            Dictionary with performance improvement percentages
        """
        comparison = {}

        # Calculate improvements (positive values are improvements)
        if before_metrics.collection_time > 0:
            time_improvement = ((before_metrics.collection_time - after_metrics.collection_time) / before_metrics.collection_time) * 100
            comparison['collection_time_improvement'] = time_improvement

        if before_metrics.memory_peak_mb > 0:
            memory_improvement = ((before_metrics.memory_peak_mb - after_metrics.memory_peak_mb) / before_metrics.memory_peak_mb) * 100
            comparison['memory_improvement'] = memory_improvement

        if before_metrics.warnings_count > 0:
            warning_reduction = ((before_metrics.warnings_count - after_metrics.warnings_count) / before_metrics.warnings_count) * 100
            comparison['warning_reduction'] = warning_reduction

        # Add absolute values for context
        comparison['collection_time_before'] = before_metrics.collection_time
        comparison['collection_time_after'] = after_metrics.collection_time
        comparison['warnings_before'] = before_metrics.warnings_count
        comparison['warnings_after'] = after_metrics.warnings_count

        return comparison

    def validate_directory_compliance(self, directory: str) -> List[ComplianceReport]:
        """
        Validate SSOT compliance for entire directory.

        Args:
            directory: Directory to validate

        Returns:
            List of ComplianceReport for all test files
        """
        reports = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    report = self.validate_ssot_compliance(file_path)
                    reports.append(report)

        return reports

    def generate_comprehensive_report(self, directory: str, baseline_metrics: Optional[PerformanceMetrics] = None) -> str:
        """
        Generate comprehensive validation report for directory.

        Args:
            directory: Directory to generate report for
            baseline_metrics: Optional baseline metrics for comparison

        Returns:
            Formatted comprehensive report
        """
        if self.verbose:
            print(f"Generating comprehensive report for: {directory}")

        # Measure current performance
        current_metrics = self.measure_collection_performance(directory)

        # Validate compliance
        compliance_reports = self.validate_directory_compliance(directory)

        # Calculate summary statistics
        total_files = len(compliance_reports)
        compliant_files = len([r for r in compliance_reports if r.compliance_score >= 90.0])
        files_with_duplicates = len([r for r in compliance_reports if r.has_duplicate_classes])
        total_duplicate_classes = sum(r.duplicate_class_count for r in compliance_reports)

        # Generate report
        report = f"""
# WebSocket Migration Validation Report
Generated: {datetime.now().isoformat()}
Directory: {directory}

## Performance Metrics
- Collection Time: {current_metrics.collection_time:.2f} seconds
- Memory Peak: {current_metrics.memory_peak_mb:.1f} MB
- Tests Collected: {current_metrics.tests_collected}
- Files Collected: {current_metrics.files_collected}
- Warnings: {current_metrics.warnings_count}
- Errors: {current_metrics.errors_count}
- Collection Success: {'✅' if current_metrics.success else '❌'}

"""

        # Add performance comparison if baseline available
        if baseline_metrics:
            comparison = self.compare_performance(baseline_metrics, current_metrics)
            report += f"""
## Performance Improvements
- Collection Time Improvement: {comparison.get('collection_time_improvement', 0):.1f}%
- Memory Usage Improvement: {comparison.get('memory_improvement', 0):.1f}%
- Warning Reduction: {comparison.get('warning_reduction', 0):.1f}%

"""

        # Add compliance summary
        report += f"""
## SSOT Compliance Summary
- Total Files Analyzed: {total_files}
- Compliant Files (≥90%): {compliant_files} ({(compliant_files/total_files*100) if total_files > 0 else 0:.1f}%)
- Files with Duplicate Classes: {files_with_duplicates}
- Total Duplicate Classes: {total_duplicate_classes}

"""

        # Add file-by-file compliance details
        if files_with_duplicates > 0:
            report += "## Files Requiring Migration\n"
            for r in compliance_reports:
                if r.has_duplicate_classes:
                    report += f"❌ {r.file_path} ({r.duplicate_class_count} duplicates, {r.compliance_score:.1f}% compliant)\n"

        # Add success stories
        if compliant_files > 0:
            report += "\n## Successfully Migrated Files\n"
            for r in compliance_reports:
                if r.compliance_score >= 90.0:
                    report += f"✅ {r.file_path} ({r.compliance_score:.1f}% compliant)\n"

        # Add recommendations
        report += """
## Recommendations

### Immediate Actions:
1. Migrate files with duplicate classes to SSOT imports
2. Remove class definitions in favor of SSOT utility
3. Validate test functionality after migration

### Performance Targets (Issue #1041):
- Collection time reduction: 85-90%
- Warning reduction: 80%+
- Zero duplicate TestWebSocketConnection classes

### Next Steps:
1. Run migration script on high-priority files
2. Validate Golden Path functionality
3. Monitor collection performance improvements
"""

        return report

    def _start_memory_monitoring(self):
        """Start background memory monitoring."""
        self.memory_samples = []
        self.monitoring_active = True

        def monitor_memory():
            process = psutil.Process()
            while self.monitoring_active:
                try:
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    self.memory_samples.append(memory_mb)
                    time.sleep(0.1)  # Sample every 100ms
                except:
                    break

        self.monitor_thread = threading.Thread(target=monitor_memory)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def _stop_memory_monitoring(self):
        """Stop background memory monitoring."""
        self.monitoring_active = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1.0)

    def _calculate_compliance_score(self, has_duplicates: bool, uses_ssot_imports: bool, duplicate_count: int) -> float:
        """Calculate SSOT compliance score (0-100%)."""
        score = 100.0

        if has_duplicates:
            # Deduct points for duplicate classes
            score -= min(duplicate_count * 20, 60)  # Max 60 point deduction

        if has_duplicates and not uses_ssot_imports:
            # Deduct additional points for missing SSOT imports
            score -= 30

        return max(score, 0.0)

    def _save_baseline(self, metrics: PerformanceMetrics):
        """Save performance metrics as baseline."""
        baseline_file = self.baseline_dir / f"baseline_{metrics.directory.replace('/', '_').replace('\\', '_')}.json"
        with open(baseline_file, 'w') as f:
            json.dump(asdict(metrics), f, indent=2)

    def _get_baseline_execution_time(self, file_path: str) -> float:
        """Get baseline execution time for file."""
        # Simplified - would need actual baseline storage
        return 0.0


def main():
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Validate WebSocket test migration performance and compliance"
    )

    parser.add_argument('--performance', action='store_true',
                        help='Measure collection performance')
    parser.add_argument('--ssot-compliance', action='store_true',
                        help='Validate SSOT compliance')
    parser.add_argument('--functionality', action='store_true',
                        help='Validate test functionality')
    parser.add_argument('--full-report', action='store_true',
                        help='Generate comprehensive validation report')
    parser.add_argument('--directory', type=str,
                        help='Directory to validate')
    parser.add_argument('--file', type=str,
                        help='Specific file to validate')
    parser.add_argument('--baseline', action='store_true',
                        help='Save current measurements as baseline')
    parser.add_argument('--compare-baseline', action='store_true',
                        help='Compare against saved baseline')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--baseline-dir', type=str,
                        help='Custom baseline directory')

    args = parser.parse_args()

    if not any([args.performance, args.ssot_compliance, args.functionality, args.full_report]):
        parser.print_help()
        return

    validator = WebSocketMigrationValidator(verbose=args.verbose, baseline_dir=args.baseline_dir)

    if args.performance:
        if not args.directory:
            print("Error: --directory required for performance measurement")
            return

        metrics = validator.measure_collection_performance(args.directory, baseline=args.baseline)
        print(f"\nPerformance Results for {args.directory}:")
        print(f"Collection Time: {metrics.collection_time:.2f} seconds")
        print(f"Memory Peak: {metrics.memory_peak_mb:.1f} MB")
        print(f"Tests Collected: {metrics.tests_collected}")
        print(f"Warnings: {metrics.warnings_count}")
        print(f"Success: {'✅' if metrics.success else '❌'}")

    if args.ssot_compliance:
        if args.file:
            report = validator.validate_ssot_compliance(args.file)
            print(f"\nSSoT Compliance for {args.file}:")
            print(f"Compliance Score: {report.compliance_score:.1f}%")
            print(f"Duplicate Classes: {report.duplicate_class_count}")
            print(f"Uses SSOT Imports: {'✅' if report.uses_ssot_imports else '❌'}")
            if report.violations:
                print("Violations:")
                for violation in report.violations:
                    print(f"  - {violation}")

        elif args.directory:
            reports = validator.validate_directory_compliance(args.directory)
            compliant_files = len([r for r in reports if r.compliance_score >= 90.0])
            print(f"\nSSoT Compliance for {args.directory}:")
            print(f"Total Files: {len(reports)}")
            print(f"Compliant Files: {compliant_files} ({(compliant_files/len(reports)*100) if reports else 0:.1f}%)")

    if args.functionality:
        if not args.file:
            print("Error: --file required for functionality validation")
            return

        report = validator.validate_test_functionality(args.file, compare_to_baseline=args.compare_baseline)
        print(f"\nFunctionality Validation for {args.file}:")
        print(f"Success Rate: {report.test_success_rate:.1f}%")
        print(f"Tests Passed: {report.tests_passed}")
        print(f"Tests Failed: {report.tests_failed}")
        print(f"Functionality Preserved: {'✅' if report.functionality_preserved else '❌'}")

    if args.full_report:
        if not args.directory:
            print("Error: --directory required for full report")
            return

        baseline_metrics = None
        if args.compare_baseline:
            # Would load baseline here
            pass

        report = validator.generate_comprehensive_report(args.directory, baseline_metrics)
        print(report)


if __name__ == '__main__':
    main()