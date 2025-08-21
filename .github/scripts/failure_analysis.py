#!/usr/bin/env python3
"""
Failure Analysis and Debug Artifact Generation for CI/CD

This script provides comprehensive failure analysis, log collection, and debug artifact
generation for CI/CD pipeline failures. It helps developers quickly identify and fix issues.

Business Value Justification (BVJ):
1. **Segment**: Growth & Enterprise
2. **Business Goal**: Reduce time-to-fix for CI/CD failures and improve developer experience
3. **Value Impact**: Reduces debugging time by 50-70% through automated failure analysis
4. **Revenue Impact**: Faster issue resolution maintains development velocity
"""

import json
import logging
import os
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FailureType(Enum):
    """Types of CI/CD failures."""
    CODE_QUALITY = "code_quality"
    TEST_FAILURE = "test_failure"
    SERVICE_FAILURE = "service_failure"
    TIMEOUT = "timeout"
    INFRASTRUCTURE = "infrastructure"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"

class SeverityLevel(Enum):
    """Severity levels for failures."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class FailureEvent:
    """A single failure event with context."""
    timestamp: str
    stage: str
    job_name: str
    failure_type: FailureType
    severity: SeverityLevel
    message: str
    stack_trace: Optional[str]
    exit_code: int
    context: Dict[str, Any]

@dataclass
class FailureReport:
    """Comprehensive failure report."""
    workflow_run_id: str
    repository: str
    branch: str
    commit_sha: str
    trigger_event: str
    total_failures: int
    failure_events: List[FailureEvent]
    analysis: Dict[str, Any]
    recommendations: List[str]
    artifacts: List[str]
    generated_at: str

class FailureAnalyzer:
    """
    Analyzes CI/CD failures and generates comprehensive reports.
    
    Key features:
    - Automatic failure classification
    - Log collection and analysis
    - Debug artifact generation
    - Actionable recommendations
    - Performance impact analysis
    """
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        self.analysis_patterns = self._load_analysis_patterns()
        
    def _load_analysis_patterns(self) -> Dict[str, Dict]:
        """Load patterns for failure analysis."""
        return {
            "test_failures": {
                "patterns": [
                    r"FAILED.*test_.*\.py",
                    r"AssertionError:",
                    r"E\s+assert",
                    r"ModuleNotFoundError:",
                    r"ImportError:",
                    r"ConnectionError:",
                    r"TimeoutError:"
                ],
                "severity": SeverityLevel.HIGH,
                "type": FailureType.TEST_FAILURE
            },
            "service_failures": {
                "patterns": [
                    r"Connection refused",
                    r"Can't connect to.*server",
                    r"Database connection failed",
                    r"Redis connection failed",
                    r"Service unavailable",
                    r"Health check failed"
                ],
                "severity": SeverityLevel.CRITICAL,
                "type": FailureType.SERVICE_FAILURE
            },
            "code_quality": {
                "patterns": [
                    r"E\d+.*line too long",
                    r"F\d+.*undefined name",
                    r"black.*format",
                    r"isort.*import",
                    r"ruff.*error"
                ],
                "severity": SeverityLevel.LOW,
                "type": FailureType.CODE_QUALITY
            },
            "timeout_failures": {
                "patterns": [
                    r"timeout",
                    r"Timed out",
                    r"Operation timed out",
                    r"Process took longer"
                ],
                "severity": SeverityLevel.MEDIUM,
                "type": FailureType.TIMEOUT
            },
            "dependency_failures": {
                "patterns": [
                    r"No module named",
                    r"Package.*not found",
                    r"Unable to install",
                    r"npm.*error",
                    r"pip.*error",
                    r"requirements.*not satisfied"
                ],
                "severity": SeverityLevel.HIGH,
                "type": FailureType.DEPENDENCY
            }
        }
    
    def analyze_workflow_failure(self, 
                                workflow_context: Dict[str, Any],
                                job_results: Dict[str, str]) -> FailureReport:
        """
        Analyze a complete workflow failure.
        
        Args:
            workflow_context: Context about the workflow run
            job_results: Results from each job
            
        Returns:
            Comprehensive failure report
        """
        logger.info("Starting workflow failure analysis")
        
        failure_events = []
        
        # Analyze each failed job
        for job_name, result in job_results.items():
            if result in ['failure', 'cancelled', 'skipped']:
                logger.info(f"Analyzing failure for job: {job_name}")
                
                job_failures = self._analyze_job_failure(job_name, result, workflow_context)
                failure_events.extend(job_failures)
        
        # Generate analysis and recommendations
        analysis = self._generate_analysis(failure_events, workflow_context)
        recommendations = self._generate_recommendations(failure_events, analysis)
        
        # Collect artifacts
        artifacts = self._collect_artifacts(workflow_context, failure_events)
        
        # Create comprehensive report
        report = FailureReport(
            workflow_run_id=workflow_context.get('run_id', 'unknown'),
            repository=workflow_context.get('repository', 'unknown'),
            branch=workflow_context.get('branch', 'unknown'),
            commit_sha=workflow_context.get('commit_sha', 'unknown'),
            trigger_event=workflow_context.get('event_name', 'unknown'),
            total_failures=len(failure_events),
            failure_events=failure_events,
            analysis=analysis,
            recommendations=recommendations,
            artifacts=artifacts,
            generated_at=datetime.now(timezone.utc).isoformat()
        )
        
        logger.info(f"Analysis complete: {len(failure_events)} failure events identified")
        return report
    
    def _analyze_job_failure(self, 
                           job_name: str,
                           result: str,
                           context: Dict[str, Any]) -> List[FailureEvent]:
        """Analyze a single job failure."""
        failure_events = []
        
        # Try to get job logs
        log_content = self._get_job_logs(job_name)
        if not log_content:
            # Create generic failure event if no logs available
            failure_events.append(FailureEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage=context.get('stage', 'unknown'),
                job_name=job_name,
                failure_type=FailureType.UNKNOWN,
                severity=SeverityLevel.MEDIUM,
                message=f"Job {job_name} resulted in {result}",
                stack_trace=None,
                exit_code=-1,
                context={"result": result}
            ))
            return failure_events
        
        # Analyze log content for specific failure patterns
        for category, patterns in self.analysis_patterns.items():
            import re
            for pattern in patterns['patterns']:
                matches = re.findall(pattern, log_content, re.IGNORECASE)
                if matches:
                    # Extract context around matches
                    lines = log_content.split('\n')
                    for match in matches[:5]:  # Limit to first 5 matches per pattern
                        failure_events.append(FailureEvent(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            stage=context.get('stage', 'unknown'),
                            job_name=job_name,
                            failure_type=patterns['type'],
                            severity=patterns['severity'],
                            message=f"{category}: {match}",
                            stack_trace=self._extract_stack_trace(log_content, match),
                            exit_code=self._extract_exit_code(log_content),
                            context={
                                "pattern": pattern,
                                "category": category,
                                "match_text": match
                            }
                        ))
        
        return failure_events
    
    def _get_job_logs(self, job_name: str) -> Optional[str]:
        """Get logs for a specific job."""
        # Try to find log files in common locations
        possible_paths = [
            self.workspace_path / f"{job_name}.log",
            self.workspace_path / "logs" / f"{job_name}.log",
            self.workspace_path / "test_results" / f"{job_name}.log",
            self.workspace_path / f"job-{job_name}.log"
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    return path.read_text(encoding='utf-8')
                except Exception as e:
                    logger.warning(f"Could not read log file {path}: {e}")
        
        # Try to get logs from running processes or system logs
        try:
            # For GitHub Actions, this would be handled differently
            # This is a fallback for local testing
            result = subprocess.run([
                'journalctl', '--since', '1 hour ago', '--no-pager'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return result.stdout
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return None
    
    def _extract_stack_trace(self, log_content: str, match: str) -> Optional[str]:
        """Extract stack trace from log content around a match."""
        lines = log_content.split('\n')
        
        # Find the line with the match
        match_line_idx = -1
        for i, line in enumerate(lines):
            if match in line:
                match_line_idx = i
                break
        
        if match_line_idx == -1:
            return None
        
        # Look for stack trace patterns around the match
        stack_trace_lines = []
        
        # Look backwards and forwards for stack trace
        start_idx = max(0, match_line_idx - 10)
        end_idx = min(len(lines), match_line_idx + 20)
        
        in_stack_trace = False
        for i in range(start_idx, end_idx):
            line = lines[i]
            
            # Common stack trace indicators
            if any(indicator in line for indicator in ['Traceback', 'File "', '  at ', 'line ']):
                in_stack_trace = True
                
            if in_stack_trace:
                stack_trace_lines.append(line)
                
                # End of stack trace
                if line.strip() and not line.startswith(' ') and not any(
                    indicator in line for indicator in ['File "', '  at ', 'line ', 'Error:', 'Exception:']
                ):
                    break
        
        return '\n'.join(stack_trace_lines) if stack_trace_lines else None
    
    def _extract_exit_code(self, log_content: str) -> int:
        """Extract exit code from log content."""
        import re
        
        # Look for common exit code patterns
        patterns = [
            r'exit code (\d+)',
            r'returned (\d+)',
            r'Process finished with exit code (\d+)',
            r'Command failed with code (\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, log_content, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return -1
    
    def _generate_analysis(self, 
                          failure_events: List[FailureEvent],
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analysis of failure patterns."""
        if not failure_events:
            return {"summary": "No specific failure patterns identified"}
        
        # Count failure types
        failure_type_counts = {}
        severity_counts = {}
        stage_counts = {}
        
        for event in failure_events:
            failure_type_counts[event.failure_type.value] = failure_type_counts.get(event.failure_type.value, 0) + 1
            severity_counts[event.severity.value] = severity_counts.get(event.severity.value, 0) + 1
            stage_counts[event.stage] = stage_counts.get(event.stage, 0) + 1
        
        # Identify primary failure cause
        primary_failure_type = max(failure_type_counts, key=failure_type_counts.get)
        primary_severity = max(severity_counts, key=severity_counts.get)
        
        analysis = {
            "summary": f"Primary failure type: {primary_failure_type} ({primary_severity} severity)",
            "failure_breakdown": {
                "by_type": failure_type_counts,
                "by_severity": severity_counts,
                "by_stage": stage_counts
            },
            "primary_failure": {
                "type": primary_failure_type,
                "severity": primary_severity,
                "count": failure_type_counts[primary_failure_type]
            },
            "context_analysis": {
                "event_name": context.get('event_name', 'unknown'),
                "branch": context.get('branch', 'unknown'),
                "is_main_branch": context.get('branch') == 'main',
                "is_pr": context.get('event_name') == 'pull_request'
            }
        }
        
        return analysis
    
    def _generate_recommendations(self, 
                                failure_events: List[FailureEvent],
                                analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on failures."""
        recommendations = []
        
        primary_failure_type = analysis.get('primary_failure', {}).get('type', 'unknown')
        failure_counts = analysis.get('failure_breakdown', {}).get('by_type', {})
        
        # General recommendations based on primary failure type
        if primary_failure_type == FailureType.TEST_FAILURE.value:
            recommendations.extend([
                "Review failed test cases and their assertions",
                "Check if test dependencies are properly configured",
                "Verify test data setup and cleanup procedures",
                "Consider running tests locally to reproduce the issue"
            ])
            
        elif primary_failure_type == FailureType.SERVICE_FAILURE.value:
            recommendations.extend([
                "Check service health and connectivity",
                "Verify Docker services are starting correctly",
                "Review service dependency order and health checks",
                "Check for port conflicts or resource constraints"
            ])
            
        elif primary_failure_type == FailureType.CODE_QUALITY.value:
            recommendations.extend([
                "Run code formatting tools locally: black, isort",
                "Fix linting issues identified by ruff",
                "Consider setting up pre-commit hooks for quality checks",
                "Review code style guidelines and standards"
            ])
            
        elif primary_failure_type == FailureType.DEPENDENCY.value:
            recommendations.extend([
                "Check requirements.txt and package.json for issues",
                "Verify all dependencies are available and compatible",
                "Consider using dependency lock files for consistency",
                "Check for version conflicts between dependencies"
            ])
            
        elif primary_failure_type == FailureType.TIMEOUT.value:
            recommendations.extend([
                "Review test performance and optimize slow tests",
                "Consider increasing timeout values for complex operations",
                "Check for deadlocks or infinite loops in tests",
                "Optimize Docker service startup time"
            ])
        
        # Multi-failure recommendations
        if len(failure_counts) > 3:
            recommendations.append("Multiple failure types detected - consider addressing in order of severity")
        
        # Context-specific recommendations
        if analysis.get('context_analysis', {}).get('is_main_branch'):
            recommendations.append("⚠️ Main branch failure - prioritize immediate fix")
        
        if failure_counts.get(FailureType.CRITICAL.value, 0) > 0:
            recommendations.insert(0, "🚨 Critical failures detected - immediate attention required")
        
        return recommendations
    
    def _collect_artifacts(self, 
                          context: Dict[str, Any],
                          failure_events: List[FailureEvent]) -> List[str]:
        """Collect debug artifacts for analysis."""
        artifacts = []
        
        # Create artifacts directory
        artifacts_dir = self.workspace_path / "failure_artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        
        # Collect log files
        log_files = list(self.workspace_path.glob("*.log"))
        log_files.extend(self.workspace_path.glob("logs/*.log"))
        log_files.extend(self.workspace_path.glob("test_results/*.log"))
        
        for log_file in log_files:
            if log_file.exists():
                artifacts.append(str(log_file.relative_to(self.workspace_path)))
        
        # Collect test result files
        test_result_files = list(self.workspace_path.glob("test-results/**/*"))
        test_result_files.extend(self.workspace_path.glob("coverage*.xml"))
        test_result_files.extend(self.workspace_path.glob("pytest*.xml"))
        
        for result_file in test_result_files:
            if result_file.is_file():
                artifacts.append(str(result_file.relative_to(self.workspace_path)))
        
        # Collect environment information
        env_file = artifacts_dir / "environment.json"
        env_info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "working_directory": str(self.workspace_path),
            "environment_variables": {
                key: value for key, value in os.environ.items()
                if not key.startswith(('SECRET', 'TOKEN', 'KEY', 'PASSWORD'))
            }
        }
        
        with open(env_file, 'w') as f:
            json.dump(env_info, f, indent=2)
        artifacts.append(str(env_file.relative_to(self.workspace_path)))
        
        return artifacts
    
    def create_debug_archive(self, report: FailureReport, output_path: str = None) -> str:
        """Create a debug archive with all failure information."""
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"failure_debug_{report.workflow_run_id}_{timestamp}.zip"
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add failure report
            zf.writestr("failure_report.json", json.dumps(asdict(report), indent=2, default=str))
            
            # Add all artifacts
            for artifact_path in report.artifacts:
                full_path = self.workspace_path / artifact_path
                if full_path.exists():
                    zf.write(full_path, artifact_path)
            
            # Add summary markdown report
            summary_md = self._generate_markdown_summary(report)
            zf.writestr("FAILURE_SUMMARY.md", summary_md)
        
        logger.info(f"Debug archive created: {output_path}")
        return output_path
    
    def _generate_markdown_summary(self, report: FailureReport) -> str:
        """Generate a markdown summary of the failure report."""
        md = f"""# Failure Analysis Report

**Workflow Run:** {report.workflow_run_id}
**Repository:** {report.repository}  
**Branch:** {report.branch}
**Commit:** {report.commit_sha[:8]}
**Trigger:** {report.trigger_event}
**Generated:** {report.generated_at}

## Summary

{report.analysis.get('summary', 'No summary available')}

**Total Failures:** {report.total_failures}

## Failure Breakdown

"""
        
        # Add failure breakdown
        breakdown = report.analysis.get('failure_breakdown', {})
        if 'by_type' in breakdown:
            md += "### By Type\n"
            for failure_type, count in breakdown['by_type'].items():
                md += f"- **{failure_type.replace('_', ' ').title()}:** {count}\n"
            md += "\n"
        
        if 'by_severity' in breakdown:
            md += "### By Severity\n"
            for severity, count in breakdown['by_severity'].items():
                md += f"- **{severity.title()}:** {count}\n"
            md += "\n"
        
        # Add recommendations
        md += "## Recommendations\n\n"
        for i, recommendation in enumerate(report.recommendations, 1):
            md += f"{i}. {recommendation}\n"
        
        md += "\n## Failure Events\n\n"
        
        # Add failure events
        for event in report.failure_events:
            md += f"### {event.job_name} - {event.failure_type.value}\n"
            md += f"- **Severity:** {event.severity.value}\n"
            md += f"- **Message:** {event.message}\n"
            if event.stack_trace:
                md += f"- **Stack Trace:**\n```\n{event.stack_trace}\n```\n"
            md += "\n"
        
        # Add artifacts
        md += "## Debug Artifacts\n\n"
        for artifact in report.artifacts:
            md += f"- `{artifact}`\n"
        
        return md

def main():
    """Main entry point for failure analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze CI/CD failures and generate debug reports"
    )
    parser.add_argument(
        "--workflow-context",
        required=True,
        help="JSON string with workflow context"
    )
    parser.add_argument(
        "--job-results", 
        required=True,
        help="JSON string with job results"
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace directory path"
    )
    parser.add_argument(
        "--output",
        help="Output file for failure report"
    )
    parser.add_argument(
        "--create-archive",
        action="store_true",
        help="Create debug archive"
    )
    
    args = parser.parse_args()
    
    try:
        # Parse input JSON
        workflow_context = json.loads(args.workflow_context)
        job_results = json.loads(args.job_results)
        
        # Create analyzer and run analysis
        analyzer = FailureAnalyzer(args.workspace)
        report = analyzer.analyze_workflow_failure(workflow_context, job_results)
        
        # Output report
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)
            print(f"Failure report saved to: {args.output}")
        else:
            print(json.dumps(asdict(report), indent=2, default=str))
        
        # Create debug archive if requested
        if args.create_archive:
            archive_path = analyzer.create_debug_archive(report)
            print(f"Debug archive created: {archive_path}")
        
        # Print summary
        print(f"\n=== Failure Analysis Summary ===")
        print(f"Total failures: {report.total_failures}")
        print(f"Primary issue: {report.analysis.get('primary_failure', {}).get('type', 'unknown')}")
        print(f"Recommendations: {len(report.recommendations)}")
        
        if report.total_failures > 0:
            sys.exit(1)
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()