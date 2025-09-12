#!/usr/bin/env python3
"""
CI/CD Reporting System

This script generates comprehensive reports for CI/CD pipeline execution,
including PR comments, coverage reports, and performance metrics.

Business Value Justification (BVJ):
1. **Segment**: Growth & Enterprise
2. **Business Goal**: Improve visibility and transparency of CI/CD process
3. **Value Impact**: Increases development team efficiency by 25% through better reporting
4. **Revenue Impact**: Better visibility leads to faster issue resolution and deployment confidence
"""

import json
import logging
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestMetrics:
    """Test execution metrics."""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    test_duration: float
    coverage_percentage: float
    coverage_change: Optional[float] = None

@dataclass
class PerformanceMetrics:
    """Performance metrics for CI/CD pipeline."""
    total_duration: float
    setup_duration: float
    test_duration: float
    deployment_duration: float
    queue_time: float
    success_rate: float
    throughput: float  # tests per minute

@dataclass
class CIReport:
    """Comprehensive CI/CD report."""
    workflow_run_id: str
    repository: str
    branch: str
    commit_sha: str
    pr_number: Optional[int]
    trigger_event: str
    status: str
    test_metrics: TestMetrics
    performance_metrics: PerformanceMetrics
    stages: Dict[str, Dict[str, Any]]
    artifacts: List[str]
    recommendations: List[str]
    generated_at: str

class CIReporter:
    """
    Generates comprehensive CI/CD reports and notifications.
    
    Key features:
    - Test result summaries with coverage
    - Performance metrics and trends
    - PR comments with actionable insights
    - Artifact management
    - Historical comparisons
    """
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        self.github_token = os.getenv('GITHUB_TOKEN')
        
    def generate_report(self, 
                       workflow_context: Dict[str, Any],
                       stage_results: Dict[str, Dict[str, Any]]) -> CIReport:
        """
        Generate comprehensive CI/CD report.
        
        Args:
            workflow_context: Context about the workflow execution
            stage_results: Results from each pipeline stage
            
        Returns:
            Complete CI/CD report
        """
        logger.info("Generating CI/CD report")
        
        # Collect test metrics
        test_metrics = self._collect_test_metrics(stage_results)
        
        # Collect performance metrics
        performance_metrics = self._collect_performance_metrics(workflow_context, stage_results)
        
        # Identify artifacts
        artifacts = self._collect_artifacts()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(test_metrics, performance_metrics, stage_results)
        
        # Create report
        report = CIReport(
            workflow_run_id=workflow_context.get('run_id', 'unknown'),
            repository=workflow_context.get('repository', 'unknown'),
            branch=workflow_context.get('branch', 'unknown'),
            commit_sha=workflow_context.get('commit_sha', 'unknown'),
            pr_number=workflow_context.get('pr_number'),
            trigger_event=workflow_context.get('event_name', 'unknown'),
            status=self._determine_overall_status(stage_results),
            test_metrics=test_metrics,
            performance_metrics=performance_metrics,
            stages=stage_results,
            artifacts=artifacts,
            recommendations=recommendations,
            generated_at=datetime.now(timezone.utc).isoformat()
        )
        
        logger.info("CI/CD report generated successfully")
        return report
    
    def _collect_test_metrics(self, stage_results: Dict[str, Dict[str, Any]]) -> TestMetrics:
        """Collect test execution metrics from stage results."""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        total_duration = 0.0
        coverage_percentage = 0.0
        
        # Aggregate metrics from test stages
        for stage_name, stage_data in stage_results.items():
            if 'test' in stage_name.lower():
                metrics = stage_data.get('metrics', {})
                
                total_tests += metrics.get('total_tests', 0)
                passed_tests += metrics.get('passed_tests', 0)
                failed_tests += metrics.get('failed_tests', 0)
                skipped_tests += metrics.get('skipped_tests', 0)
                total_duration += metrics.get('duration', 0.0)
                
                # Take the highest coverage percentage
                stage_coverage = metrics.get('coverage_percentage', 0.0)
                if stage_coverage > coverage_percentage:
                    coverage_percentage = stage_coverage
        
        # Try to load coverage from files if not in metrics
        if coverage_percentage == 0.0:
            coverage_percentage = self._extract_coverage_from_files()
        
        return TestMetrics(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            test_duration=total_duration,
            coverage_percentage=coverage_percentage,
            coverage_change=self._calculate_coverage_change(coverage_percentage)
        )
    
    def _collect_performance_metrics(self, 
                                   workflow_context: Dict[str, Any],
                                   stage_results: Dict[str, Dict[str, Any]]) -> PerformanceMetrics:
        """Collect performance metrics from workflow execution."""
        # Calculate durations from stage results
        setup_duration = 0.0
        test_duration = 0.0
        deployment_duration = 0.0
        
        for stage_name, stage_data in stage_results.items():
            duration = stage_data.get('duration', 0.0)
            
            if 'setup' in stage_name.lower() or 'install' in stage_name.lower():
                setup_duration += duration
            elif 'test' in stage_name.lower():
                test_duration += duration
            elif 'deploy' in stage_name.lower():
                deployment_duration += duration
        
        total_duration = setup_duration + test_duration + deployment_duration
        
        # Calculate success rate
        successful_stages = sum(1 for stage_data in stage_results.values() 
                              if stage_data.get('status') == 'success')
        total_stages = len(stage_results)
        success_rate = successful_stages / total_stages if total_stages > 0 else 0.0
        
        # Calculate throughput (tests per minute)
        total_tests = sum(stage_data.get('metrics', {}).get('total_tests', 0) 
                         for stage_data in stage_results.values())
        throughput = total_tests / (test_duration / 60) if test_duration > 0 else 0.0
        
        return PerformanceMetrics(
            total_duration=total_duration,
            setup_duration=setup_duration,
            test_duration=test_duration,
            deployment_duration=deployment_duration,
            queue_time=0.0,  # Would need to be calculated from workflow start times
            success_rate=success_rate,
            throughput=throughput
        )
    
    def _extract_coverage_from_files(self) -> float:
        """Extract coverage percentage from coverage files."""
        # Look for coverage XML files
        coverage_files = list(self.workspace_path.glob("coverage*.xml"))
        coverage_files.extend(self.workspace_path.glob("**/coverage*.xml"))
        
        for coverage_file in coverage_files:
            try:
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                line_rate = root.attrib.get('line-rate', '0')
                return float(line_rate) * 100
            except (ET.ParseError, ValueError) as e:
                logger.warning(f"Could not parse coverage file {coverage_file}: {e}")
        
        # Look for text-based coverage reports
        coverage_txt_files = list(self.workspace_path.glob("coverage*.txt"))
        coverage_txt_files.extend(self.workspace_path.glob("**/coverage*.txt"))
        
        for coverage_file in coverage_txt_files:
            try:
                content = coverage_file.read_text()
                # Look for percentage patterns
                import re
                match = re.search(r'(\d+)%', content)
                if match:
                    return float(match.group(1))
            except Exception as e:
                logger.warning(f"Could not read coverage file {coverage_file}: {e}")
        
        return 0.0
    
    def _calculate_coverage_change(self, current_coverage: float) -> Optional[float]:
        """Calculate coverage change from previous runs."""
        # This would typically compare against a baseline or previous run
        # For now, return None (no comparison available)
        return None
    
    def _collect_artifacts(self) -> List[str]:
        """Collect paths to generated artifacts."""
        artifacts = []
        
        # Common artifact patterns
        patterns = [
            "test-results/**/*",
            "coverage*.xml",
            "coverage*.html",
            "test_*.json",
            "pytest*.xml",
            "failure_*.zip",
            "performance_*.json"
        ]
        
        for pattern in patterns:
            files = list(self.workspace_path.glob(pattern))
            for file_path in files:
                if file_path.is_file():
                    artifacts.append(str(file_path.relative_to(self.workspace_path)))
        
        return artifacts
    
    def _determine_overall_status(self, stage_results: Dict[str, Dict[str, Any]]) -> str:
        """Determine overall pipeline status."""
        statuses = [stage_data.get('status', 'unknown') for stage_data in stage_results.values()]
        
        if 'failure' in statuses:
            return 'failure'
        elif 'cancelled' in statuses:
            return 'cancelled'
        elif all(status in ['success', 'skipped'] for status in statuses):
            return 'success'
        else:
            return 'partial'
    
    def _generate_recommendations(self, 
                                test_metrics: TestMetrics,
                                performance_metrics: PerformanceMetrics,
                                stage_results: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []
        
        # Test-related recommendations
        if test_metrics.failed_tests > 0:
            failure_rate = test_metrics.failed_tests / test_metrics.total_tests * 100
            if failure_rate > 10:
                recommendations.append(f" ALERT:  High test failure rate ({failure_rate:.1f}%) - investigate test reliability")
            else:
                recommendations.append(f" WARNING: [U+FE0F] {test_metrics.failed_tests} test(s) failed - review and fix")
        
        # Coverage recommendations
        if test_metrics.coverage_percentage < 80:
            recommendations.append(f" CHART:  Test coverage is {test_metrics.coverage_percentage:.1f}% - consider adding more tests")
        elif test_metrics.coverage_percentage > 95:
            recommendations.append(" PASS:  Excellent test coverage!")
        
        # Performance recommendations
        if performance_metrics.test_duration > 15 * 60:  # 15 minutes
            recommendations.append("[U+23F1][U+FE0F] Test execution is slow - consider test optimization or parallelization")
        
        if performance_metrics.throughput < 1.0:  # Less than 1 test per minute
            recommendations.append("[U+1F40C] Low test throughput - review test performance")
        
        # Success rate recommendations
        if performance_metrics.success_rate < 0.9:
            recommendations.append("[U+1F4C9] Pipeline success rate is low - investigate flaky tests or infrastructure issues")
        
        # Stage-specific recommendations
        failed_stages = [name for name, data in stage_results.items() if data.get('status') == 'failure']
        if failed_stages:
            recommendations.append(f" SEARCH:  Failed stages: {', '.join(failed_stages)} - check logs for details")
        
        return recommendations
    
    def generate_pr_comment(self, report: CIReport) -> str:
        """Generate a comprehensive PR comment."""
        if not report.pr_number:
            return ""
        
        # Status emoji
        status_emoji = {
            'success': ' PASS: ',
            'failure': ' FAIL: ',
            'cancelled': '[U+1F6D1]',
            'partial': ' WARNING: [U+FE0F]'
        }.get(report.status, '[U+2753]')
        
        # Coverage emoji and trend
        coverage_emoji = '[U+1F7E2]' if report.test_metrics.coverage_percentage >= 80 else '[U+1F7E1]' if report.test_metrics.coverage_percentage >= 60 else '[U+1F534]'
        coverage_trend = ""
        if report.test_metrics.coverage_change is not None:
            if report.test_metrics.coverage_change > 0:
                coverage_trend = f" [U+2197][U+FE0F] (+{report.test_metrics.coverage_change:.1f}%)"
            elif report.test_metrics.coverage_change < 0:
                coverage_trend = f" [U+2198][U+FE0F] ({report.test_metrics.coverage_change:.1f}%)"
        
        # Performance indicators
        duration_emoji = '[U+1F680]' if report.performance_metrics.test_duration < 300 else '[U+23F1][U+FE0F]' if report.performance_metrics.test_duration < 900 else '[U+1F40C]'
        
        comment = f"""## {status_emoji} CI/CD Pipeline Results

###  CHART:  Test Summary
| Metric | Value | Status |
|--------|-------|--------|
| **Tests Run** | {report.test_metrics.total_tests} | {report.test_metrics.passed_tests}  PASS:  {report.test_metrics.failed_tests}  FAIL:  {report.test_metrics.skipped_tests} [U+23ED][U+FE0F] |
| **Coverage** | {coverage_emoji} {report.test_metrics.coverage_percentage:.1f}%{coverage_trend} | {self._get_coverage_status(report.test_metrics.coverage_percentage)} |
| **Duration** | {duration_emoji} {self._format_duration(report.performance_metrics.test_duration)} | {self._get_duration_status(report.performance_metrics.test_duration)} |

###  TARGET:  Pipeline Stages
"""
        
        # Add stage results
        for stage_name, stage_data in report.stages.items():
            status = stage_data.get('status', 'unknown')
            duration = stage_data.get('duration', 0)
            emoji = {'success': ' PASS: ', 'failure': ' FAIL: ', 'skipped': '[U+23ED][U+FE0F]', 'cancelled': '[U+1F6D1]'}.get(status, '[U+2753]')
            
            comment += f"- **{stage_name}**: {emoji} {status} ({self._format_duration(duration)})\n"
        
        # Add performance metrics
        comment += f"""
###  LIGHTNING:  Performance Metrics
- **Total Duration**: {self._format_duration(report.performance_metrics.total_duration)}
- **Success Rate**: {report.performance_metrics.success_rate*100:.1f}%
- **Test Throughput**: {report.performance_metrics.throughput:.1f} tests/min
"""
        
        # Add recommendations if there are failures or issues
        if report.recommendations:
            comment += "\n###  IDEA:  Recommendations\n"
            for rec in report.recommendations:
                comment += f"- {rec}\n"
        
        # Add artifacts section
        if report.artifacts:
            comment += f"""
### [U+1F4C1] Artifacts
- [Test Results](${{{{ github.server_url }}}}/${{{{ github.repository }}}}/actions/runs/{report.workflow_run_id})
- [Coverage Report](${{{{ github.server_url }}}}/${{{{ github.repository }}}}/actions/runs/{report.workflow_run_id})
"""
            
        # Add footer
        comment += f"""
---
<details>
<summary>Pipeline Details</summary>

- **Workflow**: [{report.workflow_run_id}](${{{{ github.server_url }}}}/${{{{ github.repository }}}}/actions/runs/{report.workflow_run_id})
- **Commit**: {report.commit_sha[:8]}
- **Branch**: {report.branch}
- **Trigger**: {report.trigger_event}
- **Generated**: {datetime.fromisoformat(report.generated_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')}

</details>

*Generated by CI/CD Reporting System v2.0* [U+1F916]
"""
        
        return comment
    
    def generate_performance_report(self, report: CIReport) -> Dict[str, Any]:
        """Generate detailed performance report."""
        return {
            "workflow_run_id": report.workflow_run_id,
            "timestamp": report.generated_at,
            "metrics": {
                "test_execution": {
                    "total_tests": report.test_metrics.total_tests,
                    "duration_seconds": report.performance_metrics.test_duration,
                    "throughput_per_minute": report.performance_metrics.throughput,
                    "success_rate": (report.test_metrics.passed_tests / report.test_metrics.total_tests) 
                                  if report.test_metrics.total_tests > 0 else 0
                },
                "pipeline_performance": {
                    "total_duration": report.performance_metrics.total_duration,
                    "setup_duration": report.performance_metrics.setup_duration,
                    "test_duration": report.performance_metrics.test_duration,
                    "deployment_duration": report.performance_metrics.deployment_duration,
                    "success_rate": report.performance_metrics.success_rate
                },
                "coverage": {
                    "percentage": report.test_metrics.coverage_percentage,
                    "change": report.test_metrics.coverage_change,
                    "status": self._get_coverage_status(report.test_metrics.coverage_percentage)
                }
            },
            "stages": {
                stage_name: {
                    "status": stage_data.get("status"),
                    "duration": stage_data.get("duration"),
                    "metrics": stage_data.get("metrics", {})
                }
                for stage_name, stage_data in report.stages.items()
            },
            "recommendations": report.recommendations
        }
    
    def _get_coverage_status(self, coverage: float) -> str:
        """Get coverage status description."""
        if coverage >= 90:
            return "Excellent"
        elif coverage >= 80:
            return "Good" 
        elif coverage >= 60:
            return "Needs Improvement"
        else:
            return "Poor"
    
    def _get_duration_status(self, duration: float) -> str:
        """Get duration status description."""
        if duration < 300:  # 5 minutes
            return "Fast"
        elif duration < 900:  # 15 minutes
            return "Moderate"
        else:
            return "Slow"
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def save_report(self, report: CIReport, output_file: str) -> None:
        """Save report to file."""
        with open(output_file, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        logger.info(f"Report saved to: {output_file}")
    
    def save_performance_metrics(self, report: CIReport, output_file: str) -> None:
        """Save performance metrics to file."""
        perf_report = self.generate_performance_report(report)
        
        with open(output_file, 'w') as f:
            json.dump(perf_report, f, indent=2, default=str)
        
        logger.info(f"Performance metrics saved to: {output_file}")

def main():
    """Main entry point for CI reporting."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate CI/CD reports and notifications"
    )
    parser.add_argument(
        "--workflow-context",
        required=True,
        help="JSON string with workflow context"
    )
    parser.add_argument(
        "--stage-results",
        required=True,
        help="JSON string with stage results"
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace directory path"
    )
    parser.add_argument(
        "--output-report",
        help="Output file for full report"
    )
    parser.add_argument(
        "--output-performance",
        help="Output file for performance metrics"
    )
    parser.add_argument(
        "--pr-comment",
        action="store_true",
        help="Generate PR comment"
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    try:
        # Parse input JSON
        workflow_context = json.loads(args.workflow_context)
        stage_results = json.loads(args.stage_results)
        
        # Create reporter and generate report
        reporter = CIReporter(args.workspace)
        report = reporter.generate_report(workflow_context, stage_results)
        
        # Save reports if specified
        if args.output_report:
            reporter.save_report(report, args.output_report)
        
        if args.output_performance:
            reporter.save_performance_metrics(report, args.output_performance)
        
        # Generate PR comment if requested
        if args.pr_comment and report.pr_number:
            pr_comment = reporter.generate_pr_comment(report)
            print("=== PR COMMENT ===")
            print(pr_comment)
            print("=== END PR COMMENT ===")
        
        # Output report
        if args.format == "json":
            print(json.dumps(asdict(report), indent=2, default=str))
        elif args.format == "markdown":
            pr_comment = reporter.generate_pr_comment(report)
            print(pr_comment)
        
        # Exit with appropriate code
        sys.exit(0 if report.status == 'success' else 1)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()