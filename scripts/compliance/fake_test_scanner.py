#!/usr/bin/env python3
"""
Fake Test Scanner - Comprehensive fake test detection and reporting

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Platform/Internal - Quality assurance for all tiers
2. **Business Goal**: Platform Stability, Development Velocity, Risk Reduction
3. **Value Impact**: Prevents false confidence from fake tests, improves reliability
4. **Strategic Impact**: Reduces debugging time, accelerates issue resolution
5. **Platform Stability**: Ensures all tests provide real validation

This script provides comprehensive fake test detection across the entire codebase.
It integrates with existing test infrastructure and generates actionable reports.

Usage:
    python scripts/compliance/fake_test_scanner.py --scan-all
    python scripts/compliance/fake_test_scanner.py --directory app/tests
    python scripts/compliance/fake_test_scanner.py --file app/tests/test_example.py
    python scripts/compliance/fake_test_scanner.py --report-only
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path

from netra_backend.app.logging_config import central_logger
from test_framework.bad_test_detector import BadTestDetector
from test_framework.fake_test_detector import FakeTestDetector, FakeTestResult

logger = central_logger.get_logger(__name__)


class FakeTestScanner:
    """Comprehensive fake test scanner for the codebase"""
    
    def __init__(self):
        """Initialize the fake test scanner"""
        self.fake_detector = FakeTestDetector()
        self.bad_detector = BadTestDetector()
        
    def scan_all_tests(self) -> Dict[str, Any]:
        """Scan all test directories in the codebase
        
        Returns:
            Comprehensive scan results
        """
        logger.info("Starting comprehensive fake test scan...")
        
        # Define all test directories to scan
        test_directories = [
            PROJECT_ROOT / "app" / "tests",
            PROJECT_ROOT / "auth_service" / "tests", 
            PROJECT_ROOT / "frontend" / "tests",
            PROJECT_ROOT / "tests",
            PROJECT_ROOT / "integration_tests",
        ]
        
        all_results = []
        total_files = 0
        
        for test_dir in test_directories:
            if test_dir.exists():
                logger.info(f"Scanning {test_dir}...")
                results = self.fake_detector.scan_directory(test_dir, recursive=True)
                all_results.extend(results)
                
                # Count test files
                test_files = list(test_dir.glob("**/test_*.py"))
                total_files += len(test_files)
                logger.info(f"  Found {len(results)} fake tests in {len(test_files)} files")
        
        # Update bad test detector with fake test count
        fake_count = len(all_results)
        self.bad_detector.set_fake_tests_count(fake_count)
        
        # Generate comprehensive results
        results_summary = {
            "total_files_scanned": total_files,
            "total_fake_tests": fake_count,
            "fake_tests_by_directory": self._group_by_directory(all_results),
            "fake_tests_by_type": self.fake_detector.stats.fake_by_type,
            "fake_tests_by_severity": self.fake_detector.stats.fake_by_severity,
            "critical_files": self._get_critical_files(all_results),
            "recommendations": self._generate_recommendations(all_results)
        }
        
        logger.info(f"Scan complete: {fake_count} fake tests found in {total_files} files")
        return results_summary
    
    def scan_directory(self, directory: Path) -> Dict[str, Any]:
        """Scan specific directory for fake tests
        
        Args:
            directory: Directory to scan
            
        Returns:
            Scan results for directory
        """
        logger.info(f"Scanning directory: {directory}")
        
        if not directory.exists():
            logger.error(f"Directory does not exist: {directory}")
            return {"error": f"Directory not found: {directory}"}
        
        results = self.fake_detector.scan_directory(directory, recursive=True)
        test_files = list(directory.glob("**/test_*.py"))
        
        return {
            "directory": str(directory),
            "total_files_scanned": len(test_files),
            "total_fake_tests": len(results),
            "fake_tests_by_type": self.fake_detector.stats.fake_by_type,
            "fake_tests_by_severity": self.fake_detector.stats.fake_by_severity,
            "results": results
        }
    
    def scan_file(self, file_path: Path) -> Dict[str, Any]:
        """Scan specific file for fake tests
        
        Args:
            file_path: File to scan
            
        Returns:
            Scan results for file
        """
        logger.info(f"Scanning file: {file_path}")
        
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return {"error": f"File not found: {file_path}"}
        
        results = self.fake_detector.scan_file(file_path)
        
        return {
            "file": str(file_path),
            "total_fake_tests": len(results),
            "results": results
        }
    
    def _group_by_directory(self, results: List[FakeTestResult]) -> Dict[str, int]:
        """Group fake tests by directory"""
        by_directory = {}
        
        for result in results:
            directory = str(Path(result.test_file).parent)
            by_directory[directory] = by_directory.get(directory, 0) + 1
        
        return by_directory
    
    def _get_critical_files(self, results: List[FakeTestResult]) -> List[Dict[str, Any]]:
        """Get files with critical fake tests"""
        critical_files = {}
        
        for result in results:
            if result.severity in ['critical', 'high']:
                file_path = result.test_file
                if file_path not in critical_files:
                    critical_files[file_path] = {
                        "file": file_path,
                        "fake_tests": [],
                        "severities": set()
                    }
                
                critical_files[file_path]["fake_tests"].append(result.test_name)
                critical_files[file_path]["severities"].add(result.severity)
        
        # Convert to list and add counts
        critical_list = []
        for file_info in critical_files.values():
            file_info["fake_test_count"] = len(file_info["fake_tests"])
            file_info["severities"] = list(file_info["severities"])
            critical_list.append(file_info)
        
        # Sort by fake test count (most problematic first)
        return sorted(critical_list, key=lambda x: x["fake_test_count"], reverse=True)
    
    def _generate_recommendations(self, results: List[FakeTestResult]) -> List[str]:
        """Generate actionable recommendations based on scan results"""
        recommendations = []
        
        if not results:
            recommendations.append(" PASS:  No fake tests detected! Codebase follows testing best practices.")
            return recommendations
        
        # Count by severity
        severities = {}
        for result in results:
            severities[result.severity] = severities.get(result.severity, 0) + 1
        
        # Priority recommendations based on findings
        if severities.get('critical', 0) > 0:
            recommendations.append(
                f" ALERT:  CRITICAL: Remove {severities['critical']} empty/auto-pass tests immediately"
            )
        
        if severities.get('high', 0) > 0:
            recommendations.append(
                f" WARNING: [U+FE0F] HIGH: Address {severities['high']} mock-only tests in current sprint"
            )
        
        if severities.get('medium', 0) > 0:
            recommendations.append(
                f"[U+1F4CB] MEDIUM: Schedule {severities['medium']} trivial tests for refactoring"
            )
        
        if severities.get('low', 0) > 0:
            recommendations.append(
                f"[U+1F527] LOW: Consider consolidating {severities['low']} duplicate tests"
            )
        
        # General recommendations
        recommendations.extend([
            "[U+1F4DA] Use patterns from app/tests/examples/test_real_functionality_examples.py",
            " SEARCH:  Add fake test detection to CI pipeline to prevent regressions",
            "[U+1F4D6] Review SPEC/testing.xml for detailed fake test guidance",
            " TARGET:  Focus on testing real business logic, not mocks or constants"
        ])
        
        return recommendations
    
    def generate_comprehensive_report(self, results_summary: Dict[str, Any], 
                                    output_format: str = 'text') -> str:
        """Generate comprehensive report combining fake tests and bad tests
        
        Args:
            results_summary: Results from scan_all_tests()
            output_format: Format for output ('text', 'json')
            
        Returns:
            Formatted comprehensive report
        """
        if output_format == 'json':
            import json
            report_data = {
                "fake_tests": results_summary,
                "bad_tests": self.bad_detector.get_statistics(),
                "combined_recommendations": self._get_combined_recommendations(results_summary)
            }
            return json.dumps(report_data, indent=2, default=str)
        
        else:  # text format
            lines = [
                "=" * 80,
                "COMPREHENSIVE TEST QUALITY REPORT",
                "=" * 80,
                f"Generated: {self.fake_detector.results[0] if self.fake_detector.results else 'No fake tests found'}",
                ""
            ]
            
            # Fake tests section
            lines.extend([
                "FAKE TEST ANALYSIS:",
                "-" * 40,
                f"Total Files Scanned: {results_summary['total_files_scanned']}",
                f"Total Fake Tests Found: {results_summary['total_fake_tests']}",
                ""
            ])
            
            if results_summary['fake_tests_by_severity']:
                lines.append("Fake Tests by Severity:")
                for severity in ['critical', 'high', 'medium', 'low']:
                    count = results_summary['fake_tests_by_severity'].get(severity, 0)
                    if count > 0:
                        lines.append(f"  {severity.upper()}: {count}")
                lines.append("")
            
            if results_summary['fake_tests_by_type']:
                lines.append("Fake Tests by Type:")
                for fake_type, count in results_summary['fake_tests_by_type'].items():
                    lines.append(f"  {fake_type}: {count}")
                lines.append("")
            
            # Critical files
            if results_summary['critical_files']:
                lines.extend([
                    "CRITICAL FILES (Immediate Attention Required):",
                    "-" * 40
                ])
                for file_info in results_summary['critical_files'][:10]:  # Top 10
                    lines.append(
                        f"  {file_info['file']} "
                        f"({file_info['fake_test_count']} fake tests, "
                        f"severity: {', '.join(file_info['severities'])})"
                    )
                lines.append("")
            
            # Bad tests section (from existing detector)
            bad_stats = self.bad_detector.get_statistics()
            lines.extend([
                "FAILING TEST ANALYSIS:",
                "-" * 40,
                f"Consistently Failing Tests: {bad_stats['consistently_failing']}",
                f"High Failure Rate Tests: {bad_stats['high_failure_rate']}",
                f"Total Tracked Tests: {bad_stats['total_tracked_tests']}",
                ""
            ])
            
            # Recommendations
            lines.extend([
                "RECOMMENDATIONS:",
                "-" * 40
            ])
            for i, rec in enumerate(results_summary['recommendations'], 1):
                lines.append(f"{i}. {rec}")
            
            lines.extend([
                "",
                "=" * 80,
                "For detailed guidance:",
                "- SPEC/testing.xml (comprehensive testing standards)",
                "- app/tests/examples/test_real_functionality_examples.py (patterns)",
                "- CLAUDE.md (development standards)",
                "=" * 80
            ])
            
            return "\n".join(lines)
    
    def _get_combined_recommendations(self, results_summary: Dict[str, Any]) -> List[str]:
        """Get combined recommendations for fake tests and bad tests"""
        recommendations = results_summary['recommendations'].copy()
        
        bad_stats = self.bad_detector.get_statistics()
        if bad_stats['consistently_failing'] > 0:
            recommendations.insert(0, 
                f" FIRE:  URGENT: Fix {bad_stats['consistently_failing']} consistently failing tests"
            )
        
        if bad_stats['high_failure_rate'] > 0:
            recommendations.insert(1,
                f" LIGHTNING:  HIGH PRIORITY: Address {bad_stats['high_failure_rate']} high failure rate tests"
            )
        
        return recommendations
    
    def save_report(self, results_summary: Dict[str, Any], output_path: Path, 
                   format: str = 'text'):
        """Save comprehensive report to file
        
        Args:
            results_summary: Results from scanning
            output_path: Path to save report
            format: Report format ('text', 'json')
        """
        report_content = self.generate_comprehensive_report(results_summary, format)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"Comprehensive report saved to {output_path}")
        except Exception as e:
            logger.error(f"Could not save report to {output_path}: {e}")


def main():
    """Main entry point for fake test scanner"""
    parser = argparse.ArgumentParser(
        description='Comprehensive fake test detection and reporting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/compliance/fake_test_scanner.py --scan-all
  python scripts/compliance/fake_test_scanner.py --directory app/tests
  python scripts/compliance/fake_test_scanner.py --file app/tests/test_example.py
  python scripts/compliance/fake_test_scanner.py --report-only --format json
        """
    )
    
    # Scanning options (mutually exclusive)
    scan_group = parser.add_mutually_exclusive_group(required=True)
    scan_group.add_argument('--scan-all', action='store_true',
                           help='Scan all test directories in codebase')
    scan_group.add_argument('--directory', type=Path,
                           help='Scan specific directory')
    scan_group.add_argument('--file', type=Path,
                           help='Scan specific file')
    scan_group.add_argument('--report-only', action='store_true',
                           help='Generate report from existing scan results')
    
    # Output options
    parser.add_argument('--output', '-o', type=Path,
                       help='Output file path (default: print to console)')
    parser.add_argument('--format', '-f', choices=['text', 'json'], 
                       default='text', help='Output format')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel("DEBUG")
    
    scanner = FakeTestScanner()
    
    try:
        # Perform scanning based on arguments
        if args.scan_all:
            results_summary = scanner.scan_all_tests()
            report_title = "Comprehensive Fake Test Scan Results"
            
        elif args.directory:
            results_summary = scanner.scan_directory(args.directory)
            report_title = f"Fake Test Scan Results: {args.directory}"
            
        elif args.file:
            results_summary = scanner.scan_file(args.file)
            report_title = f"Fake Test Scan Results: {args.file}"
            
        elif args.report_only:
            # Generate report from existing fake test detector results
            results_summary = {
                "total_files_scanned": 0,
                "total_fake_tests": 0,
                "fake_tests_by_type": {},
                "fake_tests_by_severity": {},
                "critical_files": [],
                "recommendations": ["No scan performed - report only mode"]
            }
            report_title = "Test Quality Report (Report Only)"
        
        # Generate and output report
        if args.scan_all or args.report_only:
            report = scanner.generate_comprehensive_report(results_summary, args.format)
        else:
            # For specific directory/file scans, use the fake detector's report
            if args.format == 'json':
                import json
                report = json.dumps(results_summary, indent=2, default=str)
            else:
                report = scanner.fake_detector.generate_report('text')
        
        # Output report
        if args.output:
            scanner.save_report(results_summary, args.output, args.format)
            print(f"Report saved to {args.output}")
            
            # Also print summary to console
            if not args.report_only:
                fake_count = results_summary.get('total_fake_tests', 0)
                if fake_count > 0:
                    print(f"\n WARNING: [U+FE0F]  Found {fake_count} fake tests requiring attention")
                    critical_count = len([r for r in scanner.fake_detector.results 
                                        if r.severity in ['critical', 'high']])
                    if critical_count > 0:
                        print(f" ALERT:   {critical_count} are critical/high severity - immediate action required")
                else:
                    print(" PASS:   No fake tests detected - good job!")
        else:
            print(report)
            
        # Exit with appropriate code
        fake_count = results_summary.get('total_fake_tests', 0)
        critical_count = len([r for r in scanner.fake_detector.results 
                            if r.severity in ['critical', 'high']])
        
        if critical_count > 0:
            print(f"\n FAIL:  Exiting with error code due to {critical_count} critical/high severity fake tests")
            sys.exit(2)  # Critical fake tests found
        elif fake_count > 0:
            print(f"\n WARNING: [U+FE0F]  Exiting with warning due to {fake_count} fake tests found")
            sys.exit(1)  # Fake tests found but not critical
        else:
            print("\n PASS:  All tests appear to be legitimate - no fake tests detected!")
            sys.exit(0)  # Success
            
    except Exception as e:
        logger.error(f"Error during fake test scanning: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(3)  # Scanner error


if __name__ == "__main__":
    main()