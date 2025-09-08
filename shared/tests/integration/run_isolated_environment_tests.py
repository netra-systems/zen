#!/usr/bin/env python3
"""
IsolatedEnvironment Integration Test Runner

This script provides a dedicated test runner for the IsolatedEnvironment integration tests
with comprehensive reporting and analysis capabilities.

Business Value: Platform/Internal - Test Infrastructure Automation
Ensures the critical IsolatedEnvironment SSOT module is thoroughly validated
before deployment to prevent platform-wide cascade failures.

Usage:
    python run_isolated_environment_tests.py [options]
    
Options:
    --fast           Run only fast tests (< 5 seconds each)
    --full           Run comprehensive test suite including performance tests
    --concurrent     Test thread safety with high concurrency
    --report         Generate detailed HTML report
    --verbose        Enable verbose output
    --profile        Enable performance profiling
    --coverage       Generate code coverage report
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import tempfile
import pytest
from datetime import datetime


class IsolatedEnvironmentTestRunner:
    """Comprehensive test runner for IsolatedEnvironment integration tests."""
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        self.coverage_data = {}
        self.start_time = None
        self.end_time = None
        
    def run_tests(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the integration tests with specified configuration.
        
        Args:
            config: Test configuration dictionary
            
        Returns:
            Comprehensive test results and metrics
        """
        self.start_time = time.time()
        
        print("=" * 80)
        print("🧪 NETRA ISOLATED ENVIRONMENT INTEGRATION TESTS")
        print("=" * 80)
        print(f"Configuration: {config}")
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Prepare pytest arguments
        pytest_args = self._build_pytest_args(config)
        
        # Run tests
        try:
            if config.get('coverage', False):
                result = self._run_with_coverage(pytest_args, config)
            else:
                result = self._run_standard_tests(pytest_args, config)
                
            self.end_time = time.time()
            
            # Generate comprehensive report
            report = self._generate_report(result, config)
            
            if config.get('report', False):
                self._save_html_report(report, config)
            
            return report
            
        except Exception as e:
            self.end_time = time.time()
            error_report = {
                'success': False,
                'error': str(e),
                'duration': self.end_time - self.start_time if self.start_time else 0
            }
            print(f"❌ Test execution failed: {e}")
            return error_report
    
    def _build_pytest_args(self, config: Dict[str, Any]) -> List[str]:
        """Build pytest command line arguments based on configuration."""
        args = [
            "shared/tests/integration/test_isolated_environment_comprehensive_integration.py",
            "-v" if config.get('verbose', False) else "-q",
            "--tb=short",
            "-x" if config.get('fail_fast', False) else "--tb=line",
        ]
        
        # Add markers based on configuration
        if config.get('fast', False):
            args.extend(["-m", "not slow"])
        elif config.get('full', False):
            args.extend(["--runxfail"])  # Run expected failures too
            
        if config.get('concurrent', False):
            args.extend(["-n", "auto"])  # Parallel execution
            
        # Add performance profiling
        if config.get('profile', False):
            args.extend(["--profile-svg"])
            
        # Additional pytest plugins
        if config.get('report', False):
            args.extend([
                "--html=isolated_env_test_report.html",
                "--self-contained-html"
            ])
            
        return args
    
    def _run_standard_tests(self, pytest_args: List[str], config: Dict[str, Any]) -> Any:
        """Run tests using standard pytest execution."""
        print("Running integration tests...")
        
        # Execute pytest
        result = pytest.main(pytest_args)
        
        return result
    
    def _run_with_coverage(self, pytest_args: List[str], config: Dict[str, Any]) -> Any:
        """Run tests with code coverage analysis."""
        print("Running integration tests with coverage analysis...")
        
        coverage_args = [
            "--cov=shared.isolated_environment",
            "--cov-report=html:isolated_env_coverage_html",
            "--cov-report=json:isolated_env_coverage.json",
            "--cov-report=term",
            "--cov-config=.coveragerc"
        ] + pytest_args
        
        result = pytest.main(coverage_args)
        
        # Load coverage data
        try:
            coverage_file = Path("isolated_env_coverage.json")
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    self.coverage_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load coverage data: {e}")
            
        return result
    
    def _generate_report(self, test_result: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'configuration': config,
            'execution': {
                'duration': duration,
                'start_time': self.start_time,
                'end_time': self.end_time,
                'success': test_result == 0 if isinstance(test_result, int) else False
            },
            'test_results': self.test_results,
            'performance_metrics': self.performance_metrics,
            'coverage': self.coverage_data,
            'summary': self._generate_summary(test_result, duration)
        }
        
        return report
    
    def _generate_summary(self, test_result: Any, duration: float) -> Dict[str, Any]:
        """Generate executive summary of test results."""
        success = test_result == 0 if isinstance(test_result, int) else False
        
        summary = {
            'overall_status': 'PASSED' if success else 'FAILED',
            'execution_time': f"{duration:.2f} seconds",
            'tests_run': self.test_results.get('total', 0),
            'tests_passed': self.test_results.get('passed', 0),
            'tests_failed': self.test_results.get('failed', 0),
            'tests_skipped': self.test_results.get('skipped', 0),
            'coverage_percentage': self.coverage_data.get('totals', {}).get('percent_covered', 0),
            'critical_issues': [],
            'recommendations': []
        }
        
        # Add recommendations based on results
        if not success:
            summary['critical_issues'].append("Test failures detected - investigate before deployment")
            
        if summary['coverage_percentage'] < 90:
            summary['recommendations'].append("Increase test coverage to at least 90%")
            
        if duration > 300:  # 5 minutes
            summary['recommendations'].append("Consider optimizing test performance")
            
        return summary
    
    def _save_html_report(self, report: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Save detailed HTML report."""
        report_file = Path("isolated_env_integration_report.html")
        
        html_content = self._generate_html_report(report)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"📊 Detailed HTML report saved: {report_file.absolute()}")
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML report content."""
        summary = report.get('summary', {})
        execution = report.get('execution', {})
        
        status_color = "#4CAF50" if summary.get('overall_status') == 'PASSED' else "#F44336"
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IsolatedEnvironment Integration Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .status {{ display: inline-block; padding: 10px 20px; border-radius: 5px; color: white; font-weight: bold; background-color: {status_color}; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .metric-label {{ color: #666; margin-top: 5px; }}
        .section {{ margin: 30px 0; }}
        .section-title {{ font-size: 20px; font-weight: bold; margin-bottom: 15px; color: #333; }}
        .issue {{ background: #ffebee; border-left: 4px solid #f44336; padding: 10px; margin: 5px 0; }}
        .recommendation {{ background: #e3f2fd; border-left: 4px solid #2196f3; padding: 10px; margin: 5px 0; }}
        .timestamp {{ color: #666; font-size: 14px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 IsolatedEnvironment Integration Test Report</h1>
            <div class="status">{summary.get('overall_status', 'UNKNOWN')}</div>
            <div class="timestamp">Generated: {report.get('timestamp', 'Unknown')}</div>
        </div>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{summary.get('tests_run', 0)}</div>
                <div class="metric-label">Tests Run</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary.get('tests_passed', 0)}</div>
                <div class="metric-label">Tests Passed</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary.get('tests_failed', 0)}</div>
                <div class="metric-label">Tests Failed</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary.get('execution_time', 'N/A')}</div>
                <div class="metric-label">Execution Time</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary.get('coverage_percentage', 0):.1f}%</div>
                <div class="metric-label">Code Coverage</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📋 Executive Summary</div>
            <p>The IsolatedEnvironment integration test suite validates the critical SSOT environment 
            management module that serves as the foundation for ALL Netra services.</p>
            
            <p><strong>Business Impact:</strong> This module prevents configuration drift, ensures 
            service independence, and enables reliable multi-user isolation. Any failure cascades 
            to the entire platform.</p>
        </div>
        
        {self._generate_issues_section(summary.get('critical_issues', []))}
        {self._generate_recommendations_section(summary.get('recommendations', []))}
        {self._generate_coverage_section(report.get('coverage', {}))}
        {self._generate_performance_section(report.get('performance_metrics', {}))}
        
        <div class="section">
            <div class="section-title">⚙️ Configuration</div>
            <pre style="background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto;">
{json.dumps(report.get('configuration', {}), indent=2)}
            </pre>
        </div>
    </div>
</body>
</html>"""
        return html
    
    def _generate_issues_section(self, issues: List[str]) -> str:
        """Generate critical issues section."""
        if not issues:
            return '<div class="section"><div class="section-title">✅ No Critical Issues</div><p>All tests passed successfully!</p></div>'
        
        issues_html = '<div class="section"><div class="section-title">🚨 Critical Issues</div>'
        for issue in issues:
            issues_html += f'<div class="issue">{issue}</div>'
        issues_html += '</div>'
        return issues_html
    
    def _generate_recommendations_section(self, recommendations: List[str]) -> str:
        """Generate recommendations section."""
        if not recommendations:
            return ''
        
        rec_html = '<div class="section"><div class="section-title">💡 Recommendations</div>'
        for rec in recommendations:
            rec_html += f'<div class="recommendation">{rec}</div>'
        rec_html += '</div>'
        return rec_html
    
    def _generate_coverage_section(self, coverage: Dict[str, Any]) -> str:
        """Generate code coverage section."""
        if not coverage:
            return ''
        
        return f'''
        <div class="section">
            <div class="section-title">📈 Code Coverage Analysis</div>
            <p>Coverage analysis ensures comprehensive testing of the IsolatedEnvironment module.</p>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Lines Covered</td><td>{coverage.get('totals', {}).get('covered_lines', 0)}</td></tr>
                <tr><td>Total Lines</td><td>{coverage.get('totals', {}).get('num_statements', 0)}</td></tr>
                <tr><td>Coverage Percentage</td><td>{coverage.get('totals', {}).get('percent_covered', 0):.1f}%</td></tr>
                <tr><td>Missing Lines</td><td>{coverage.get('totals', {}).get('missing_lines', 0)}</td></tr>
            </table>
        </div>'''
    
    def _generate_performance_section(self, metrics: Dict[str, Any]) -> str:
        """Generate performance metrics section."""
        if not metrics:
            return ''
        
        perf_html = '<div class="section"><div class="section-title">⚡ Performance Metrics</div>'
        perf_html += '<table><tr><th>Operation</th><th>Duration</th><th>Status</th></tr>'
        
        for operation, data in metrics.items():
            duration = data.get('duration', 0)
            status = '✅ Success' if data.get('success', False) else '❌ Failed'
            perf_html += f'<tr><td>{operation}</td><td>{duration:.3f}s</td><td>{status}</td></tr>'
        
        perf_html += '</table></div>'
        return perf_html


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Run IsolatedEnvironment integration tests")
    
    parser.add_argument('--fast', action='store_true', 
                       help='Run only fast tests (< 5 seconds each)')
    parser.add_argument('--full', action='store_true',
                       help='Run comprehensive test suite including performance tests')
    parser.add_argument('--concurrent', action='store_true',
                       help='Test thread safety with high concurrency')
    parser.add_argument('--report', action='store_true',
                       help='Generate detailed HTML report')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--profile', action='store_true',
                       help='Enable performance profiling')
    parser.add_argument('--coverage', action='store_true',
                       help='Generate code coverage report')
    parser.add_argument('--fail-fast', action='store_true',
                       help='Stop on first test failure')
    
    args = parser.parse_args()
    
    # Convert arguments to configuration
    config = {
        'fast': args.fast,
        'full': args.full,
        'concurrent': args.concurrent,
        'report': args.report,
        'verbose': args.verbose,
        'profile': args.profile,
        'coverage': args.coverage,
        'fail_fast': args.fail_fast
    }
    
    # Default to full comprehensive testing if no specific mode selected
    if not any([args.fast, args.full]):
        config['full'] = True
    
    # Always generate report for comprehensive testing
    if config['full'] or config['coverage']:
        config['report'] = True
    
    # Create and run test runner
    runner = IsolatedEnvironmentTestRunner()
    report = runner.run_tests(config)
    
    # Print final summary
    print("\n" + "=" * 80)
    print("📊 TEST EXECUTION SUMMARY")
    print("=" * 80)
    
    summary = report.get('summary', {})
    print(f"Status: {summary.get('overall_status', 'UNKNOWN')}")
    print(f"Duration: {summary.get('execution_time', 'N/A')}")
    print(f"Tests: {summary.get('tests_run', 0)} run, {summary.get('tests_passed', 0)} passed, {summary.get('tests_failed', 0)} failed")
    
    if summary.get('coverage_percentage', 0) > 0:
        print(f"Coverage: {summary.get('coverage_percentage', 0):.1f}%")
    
    if summary.get('critical_issues'):
        print("\n🚨 CRITICAL ISSUES:")
        for issue in summary['critical_issues']:
            print(f"  - {issue}")
    
    if summary.get('recommendations'):
        print("\n💡 RECOMMENDATIONS:")
        for rec in summary['recommendations']:
            print(f"  - {rec}")
    
    print("\n" + "=" * 80)
    
    # Exit with appropriate code
    exit_code = 0 if summary.get('overall_status') == 'PASSED' else 1
    sys.exit(exit_code)


if __name__ == '__main__':
    main()