#!/usr/bin/env python3
"""
Docker Compose Log Introspector with Error Extraction and Issue Generation

This tool provides comprehensive log analysis for Docker Compose services with:
- Real-time and historical log capture
- Error pattern detection and categorization
- Automatic issue generation for identified problems
- Detailed error reports with context
"""

import argparse
import json
import re
import subprocess
import sys
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import time
from collections import defaultdict

# Fix Unicode output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class ErrorSeverity(Enum):
    """Error severity levels."""
    CRITICAL = "critical"  # System crashes, data loss risks
    ERROR = "error"        # Failures that need fixing
    WARNING = "warning"    # Issues that may need attention
    INFO = "info"          # Informational, typically ignorable


class ErrorCategory(Enum):
    """Error categorization for issue tracking."""
    DATABASE_CONNECTION = "Database Connection"
    API_ERROR = "API Error"
    AUTHENTICATION = "Authentication"
    NETWORK = "Network"
    CONFIGURATION = "Configuration"
    MEMORY = "Memory/Resource"
    DEPENDENCY = "Dependency"
    TIMEOUT = "Timeout"
    PERMISSION = "Permission"
    SYNTAX = "Syntax/Code Error"
    MIGRATION = "Database Migration"
    WEBSOCKET = "WebSocket"
    CORS = "CORS"
    SSL_TLS = "SSL/TLS Certificate"
    UNKNOWN = "Unknown"


@dataclass
class ErrorPattern:
    """Definition of an error pattern to match in logs."""
    pattern: str
    category: ErrorCategory
    severity: ErrorSeverity
    description: str
    ignore_if_contains: List[str] = field(default_factory=list)
    extract_fields: List[str] = field(default_factory=list)


@dataclass
class DetectedError:
    """Represents a detected error from logs."""
    timestamp: datetime
    service: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    raw_log: str
    line_number: int
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    extracted_data: Dict[str, str] = field(default_factory=dict)
    count: int = 1
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None


@dataclass
class ServiceLogs:
    """Container for service log data."""
    service_name: str
    lines: List[str]
    errors: List[DetectedError]
    start_time: datetime
    end_time: datetime
    total_lines: int
    error_count: int
    warning_count: int


class DockerComposeLogIntrospector:
    """Main log introspection system for Docker Compose services."""
    
    # Comprehensive error patterns for detection
    ERROR_PATTERNS = [
        # Database Connection Errors
        ErrorPattern(
            r"(connection refused|connection reset|connection timeout|could not connect to|database is locked)",
            ErrorCategory.DATABASE_CONNECTION,
            ErrorSeverity.ERROR,
            "Database connection failure"
        ),
        ErrorPattern(
            r"(psycopg2\.OperationalError|sqlalchemy\.exc\.OperationalError|asyncpg\.exceptions)",
            ErrorCategory.DATABASE_CONNECTION,
            ErrorSeverity.ERROR,
            "PostgreSQL connection error"
        ),
        
        # Authentication Errors
        ErrorPattern(
            r"(401 unauthorized|403 forbidden|authentication failed|invalid token|token expired)",
            ErrorCategory.AUTHENTICATION,
            ErrorSeverity.ERROR,
            "Authentication failure",
            ignore_if_contains=["test", "expected"]
        ),
        ErrorPattern(
            r"(JWT.*error|invalid.*signature|token.*decode.*failed)",
            ErrorCategory.AUTHENTICATION,
            ErrorSeverity.ERROR,
            "JWT token error"
        ),
        
        # Network Errors - More specific pattern to catch ECONNREFUSED
        ErrorPattern(
            r"(ECONNREFUSED|ETIMEDOUT|EHOSTUNREACH|network unreachable|no route to host|Error:\s*ECON)",
            ErrorCategory.NETWORK,
            ErrorSeverity.ERROR,
            "Network connectivity issue"
        ),
        ErrorPattern(
            r"(Failed to fetch|fetch failed|network request failed|ERR_NETWORK)",
            ErrorCategory.NETWORK,
            ErrorSeverity.WARNING,
            "Network request failure"
        ),
        
        # Configuration Errors
        ErrorPattern(
            r"(missing required.*config|configuration.*error|invalid.*configuration|env.*var.*not set)",
            ErrorCategory.CONFIGURATION,
            ErrorSeverity.ERROR,
            "Configuration error"
        ),
        ErrorPattern(
            r"(KeyError.*DATABASE|KeyError.*SECRET|KeyError.*API)",
            ErrorCategory.CONFIGURATION,
            ErrorSeverity.WARNING,
            "Missing critical configuration value"
        ),
        ErrorPattern(
            r"(KeyError(?!.*DATABASE)(?!.*SECRET)(?!.*API)|missing.*environment|undefined.*variable)",
            ErrorCategory.CONFIGURATION,
            ErrorSeverity.WARNING,
            "Missing configuration value"
        ),
        
        # Memory/Resource Errors
        ErrorPattern(
            r"(out of memory|OOM|memory limit exceeded|cannot allocate memory)",
            ErrorCategory.MEMORY,
            ErrorSeverity.CRITICAL,
            "Out of memory error"
        ),
        ErrorPattern(
            r"(too many open files|resource temporarily unavailable|EMFILE|ENFILE)",
            ErrorCategory.MEMORY,
            ErrorSeverity.ERROR,
            "Resource exhaustion"
        ),
        
        # Dependency Errors
        ErrorPattern(
            r"(ModuleNotFoundError|ImportError|cannot import name|No module named)",
            ErrorCategory.DEPENDENCY,
            ErrorSeverity.ERROR,
            "Python import error"
        ),
        ErrorPattern(
            r"(npm.*ERR|yarn.*error|package.*not found|Cannot find module)",
            ErrorCategory.DEPENDENCY,
            ErrorSeverity.ERROR,
            "Node.js dependency error"
        ),
        
        # Timeout Errors
        ErrorPattern(
            r"(timeout|timed out|deadline exceeded|operation timed out)",
            ErrorCategory.TIMEOUT,
            ErrorSeverity.WARNING,
            "Operation timeout",
            ignore_if_contains=["health check", "expected"]
        ),
        
        # Permission Errors
        ErrorPattern(
            r"(permission denied|access denied|EACCES|EPERM)",
            ErrorCategory.PERMISSION,
            ErrorSeverity.ERROR,
            "Permission denied"
        ),
        
        # Syntax/Code Errors
        ErrorPattern(
            r"(SyntaxError|TypeError|ValueError|AttributeError|NameError)",
            ErrorCategory.SYNTAX,
            ErrorSeverity.ERROR,
            "Python runtime error"
        ),
        ErrorPattern(
            r"(ReferenceError|SyntaxError|TypeError).*at.*\(.*\.js",
            ErrorCategory.SYNTAX,
            ErrorSeverity.ERROR,
            "JavaScript runtime error"
        ),
        
        # Database Migration Errors
        ErrorPattern(
            r"(migration.*failed|alembic.*error|migrate.*error)",
            ErrorCategory.MIGRATION,
            ErrorSeverity.ERROR,
            "Database migration error"
        ),
        
        # WebSocket Errors - More specific pattern
        ErrorPattern(
            r"(websocket.*error|ws.*connection.*failed|websocket.*closed|websocket\s+co\w+\s+failed)",
            ErrorCategory.WEBSOCKET,
            ErrorSeverity.WARNING,
            "WebSocket error",
            ignore_if_contains=["graceful", "normal"]
        ),
        
        # CORS Errors
        ErrorPattern(
            r"(CORS.*blocked|cross-origin.*blocked|No.*Access-Control-Allow-Origin)",
            ErrorCategory.CORS,
            ErrorSeverity.ERROR,
            "CORS policy violation"
        ),
        
        # SSL/TLS Errors
        ErrorPattern(
            r"(SSL.*error|certificate.*verify.*failed|CERT.*INVALID|TLS.*handshake.*failed)",
            ErrorCategory.SSL_TLS,
            ErrorSeverity.ERROR,
            "SSL/TLS certificate error"
        ),
        
        # Generic Critical Errors
        ErrorPattern(
            r"(FATAL|CRITICAL|PANIC|kernel panic|segmentation fault|core dumped)",
            ErrorCategory.UNKNOWN,
            ErrorSeverity.CRITICAL,
            "Critical system error"
        ),
        
        # Generic Errors
        ErrorPattern(
            r"(ERROR|Exception|Failed|Failure)(?!.*test)(?!.*expected)",
            ErrorCategory.UNKNOWN,
            ErrorSeverity.ERROR,
            "Generic error"
        ),
        
        # Generic Warnings
        ErrorPattern(
            r"(WARNING|WARN|deprecated)(?!.*test)",
            ErrorCategory.UNKNOWN,
            ErrorSeverity.WARNING,
            "Generic warning"
        ),
    ]
    
    def __init__(self, compose_file: str = "docker-compose.yml", 
                 project_name: Optional[str] = None):
        """Initialize the log introspector."""
        self.compose_file = compose_file
        self.project_name = project_name
        self.project_root = Path.cwd()
        self.detected_errors: Dict[str, List[DetectedError]] = defaultdict(list)
        self.error_summary: Dict[str, Dict] = {}
        
    def run_docker_compose(self, args: List[str]) -> Tuple[int, str, str]:
        """Execute docker-compose command and capture output."""
        cmd = ["docker", "compose"]
        
        if self.compose_file:
            cmd.extend(["-f", self.compose_file])
            
        if self.project_name:
            cmd.extend(["-p", self.project_name])
            
        cmd.extend(args)
        
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        return result.returncode, result.stdout, result.stderr
    
    def get_service_logs(self, service: Optional[str] = None, 
                        tail: Optional[int] = None,
                        since: Optional[str] = None,
                        follow: bool = False) -> ServiceLogs:
        """Retrieve logs for a specific service or all services."""
        args = ["logs", "--no-color", "--timestamps"]
        
        if tail:
            args.extend(["--tail", str(tail)])
            
        if since:
            args.extend(["--since", since])
            
        if follow:
            args.append("--follow")
            
        if service:
            args.append(service)
            
        returncode, stdout, stderr = self.run_docker_compose(args)
        
        # Combine stdout and stderr as Docker logs can appear in both
        all_logs = stdout + stderr
        lines = all_logs.split('\n')
        
        # Parse and detect errors
        errors = self.detect_errors_in_logs(lines, service or "all")
        
        return ServiceLogs(
            service_name=service or "all",
            lines=lines,
            errors=errors,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_lines=len(lines),
            error_count=sum(1 for e in errors if e.severity == ErrorSeverity.ERROR),
            warning_count=sum(1 for e in errors if e.severity == ErrorSeverity.WARNING)
        )
    
    def detect_errors_in_logs(self, lines: List[str], 
                             service: str) -> List[DetectedError]:
        """Detect errors in log lines using patterns."""
        detected_errors = []
        
        for line_num, line in enumerate(lines):
            if not line.strip():
                continue
                
            # Extract timestamp if present
            timestamp = self.extract_timestamp(line)
            
            # Check against all error patterns
            for pattern_def in self.ERROR_PATTERNS:
                if self.matches_pattern(line, pattern_def):
                    # Get context lines
                    context_before = lines[max(0, line_num-3):line_num]
                    context_after = lines[line_num+1:min(len(lines), line_num+4)]
                    
                    error = DetectedError(
                        timestamp=timestamp or datetime.now(),
                        service=service,
                        category=pattern_def.category,
                        severity=pattern_def.severity,
                        message=pattern_def.description,
                        raw_log=line,
                        line_number=line_num + 1,
                        context_before=context_before,
                        context_after=context_after
                    )
                    
                    detected_errors.append(error)
                    break  # Only match first pattern
        
        return detected_errors
    
    def matches_pattern(self, line: str, pattern: ErrorPattern) -> bool:
        """Check if a log line matches an error pattern."""
        # Check if line contains pattern
        if not re.search(pattern.pattern, line, re.IGNORECASE):
            return False
            
        # Check ignore conditions
        for ignore_text in pattern.ignore_if_contains:
            if ignore_text.lower() in line.lower():
                return False
                
        return True
    
    def extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp from log line."""
        # Docker compose timestamp format: 2024-01-15T10:30:45.123456Z
        timestamp_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z?)'
        match = re.search(timestamp_pattern, line)
        
        if match:
            try:
                timestamp_str = match.group(1).replace('Z', '+00:00')
                return datetime.fromisoformat(timestamp_str)
            except:
                pass
                
        return None
    
    def analyze_all_services(self, tail: int = 1000) -> Dict[str, ServiceLogs]:
        """Analyze logs for all running services."""
        # Get list of services
        returncode, stdout, stderr = self.run_docker_compose(["ps", "--services"])
        
        if returncode != 0:
            print(f"Failed to get service list: {stderr}")
            return {}
            
        services = [s.strip() for s in stdout.split('\n') if s.strip()]
        
        results = {}
        for service in services:
            print(f"Analyzing {service}...")
            results[service] = self.get_service_logs(service, tail=tail)
            
        return results
    
    def generate_error_report(self, service_logs: Dict[str, ServiceLogs]) -> str:
        """Generate a detailed error report."""
        report = []
        report.append("=" * 80)
        report.append("DOCKER COMPOSE LOG INTROSPECTION REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary statistics
        total_errors = sum(logs.error_count for logs in service_logs.values())
        total_warnings = sum(logs.warning_count for logs in service_logs.values())
        total_lines = sum(logs.total_lines for logs in service_logs.values())
        
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Services Analyzed: {len(service_logs)}")
        report.append(f"Total Log Lines: {total_lines}")
        report.append(f"Total Errors: {total_errors}")
        report.append(f"Total Warnings: {total_warnings}")
        report.append("")
        
        # Error breakdown by category
        category_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for logs in service_logs.values():
            for error in logs.errors:
                category_counts[error.category.value] += 1
                severity_counts[error.severity.value] += 1
        
        if category_counts:
            report.append("ERRORS BY CATEGORY")
            report.append("-" * 40)
            for category, count in sorted(category_counts.items(), 
                                         key=lambda x: x[1], reverse=True):
                report.append(f"  {category}: {count}")
            report.append("")
        
        if severity_counts:
            report.append("ERRORS BY SEVERITY")
            report.append("-" * 40)
            for severity, count in sorted(severity_counts.items()):
                report.append(f"  {severity}: {count}")
            report.append("")
        
        # Detailed errors by service
        report.append("DETAILED ERRORS BY SERVICE")
        report.append("=" * 80)
        
        for service_name, logs in service_logs.items():
            if not logs.errors:
                continue
                
            report.append(f"\n{service_name.upper()}")
            report.append("-" * 40)
            
            # Group errors by category
            errors_by_category = defaultdict(list)
            for error in logs.errors:
                errors_by_category[error.category].append(error)
            
            for category, errors in errors_by_category.items():
                report.append(f"\n  [{category.value}] ({len(errors)} occurrences)")
                
                # Show up to 3 examples per category
                for error in errors[:3]:
                    report.append(f"    Line {error.line_number}: {error.raw_log[:100]}...")
                    
                if len(errors) > 3:
                    report.append(f"    ... and {len(errors) - 3} more")
        
        return "\n".join(report)
    
    def generate_github_issues(self, service_logs: Dict[str, ServiceLogs],
                              output_dir: Path = Path("./issues")) -> List[Path]:
        """Generate GitHub issue files for detected errors."""
        output_dir.mkdir(exist_ok=True)
        issue_files = []
        
        # Group errors by category and severity
        issues_to_create = defaultdict(list)
        
        for service_name, logs in service_logs.items():
            for error in logs.errors:
                # Only create issues for errors and critical issues
                if error.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
                    key = (error.category, error.severity)
                    issues_to_create[key].append((service_name, error))
        
        # Create issue files
        for (category, severity), errors in issues_to_create.items():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"issue_{category.value.lower().replace(' ', '_')}_{timestamp}.md"
            filepath = output_dir / filename
            
            # Generate issue content
            content = self.format_github_issue(category, severity, errors)
            
            filepath.write_text(content)
            issue_files.append(filepath)
            
        return issue_files
    
    def format_github_issue(self, category: ErrorCategory, 
                           severity: ErrorSeverity,
                           errors: List[Tuple[str, DetectedError]]) -> str:
        """Format a GitHub issue for a group of related errors."""
        lines = []
        
        # Title
        lines.append(f"## [{severity.value.upper()}] {category.value} Errors Detected")
        lines.append("")
        
        # Summary
        lines.append("### Summary")
        services_affected = list(set(service for service, _ in errors))
        lines.append(f"Multiple {category.value.lower()} errors detected across "
                    f"{len(services_affected)} service(s): {', '.join(services_affected)}")
        lines.append(f"Total occurrences: {len(errors)}")
        lines.append("")
        
        # Details
        lines.append("### Error Details")
        lines.append("")
        
        # Group by service
        errors_by_service = defaultdict(list)
        for service, error in errors:
            errors_by_service[service].append(error)
        
        for service, service_errors in errors_by_service.items():
            lines.append(f"#### Service: {service}")
            lines.append("")
            
            # Show first few examples
            for error in service_errors[:3]:
                lines.append("```")
                lines.append(f"Line {error.line_number}: {error.raw_log}")
                lines.append("```")
                
                if error.context_before or error.context_after:
                    lines.append("<details>")
                    lines.append("<summary>Context</summary>")
                    lines.append("")
                    lines.append("```")
                    for ctx_line in error.context_before:
                        lines.append(f"  {ctx_line}")
                    lines.append(f"> {error.raw_log}")
                    for ctx_line in error.context_after:
                        lines.append(f"  {ctx_line}")
                    lines.append("```")
                    lines.append("</details>")
                    lines.append("")
                    
            if len(service_errors) > 3:
                lines.append(f"_... and {len(service_errors) - 3} more similar errors_")
                lines.append("")
        
        # Recommended Actions
        lines.append("### Recommended Actions")
        lines.append("")
        lines.append(self.get_recommended_actions(category))
        lines.append("")
        
        # Labels
        lines.append("### Labels")
        labels = ["bug", f"severity-{severity.value}", f"category-{category.value.lower().replace(' ', '-')}"]
        lines.append(", ".join(f"`{label}`" for label in labels))
        
        return "\n".join(lines)
    
    def get_recommended_actions(self, category: ErrorCategory) -> str:
        """Get recommended actions for specific error categories."""
        recommendations = {
            ErrorCategory.DATABASE_CONNECTION: """
- [ ] Check database service is running
- [ ] Verify connection strings and credentials
- [ ] Check network connectivity between services
- [ ] Review database logs for additional details
""",
            ErrorCategory.AUTHENTICATION: """
- [ ] Verify JWT secrets are correctly configured
- [ ] Check token expiration settings
- [ ] Review authentication middleware configuration
- [ ] Ensure auth service is healthy
""",
            ErrorCategory.NETWORK: """
- [ ] Check service discovery configuration
- [ ] Verify network policies and firewall rules
- [ ] Review DNS resolution
- [ ] Check for port conflicts
""",
            ErrorCategory.CONFIGURATION: """
- [ ] Review environment variables
- [ ] Check configuration files for typos
- [ ] Verify all required settings are present
- [ ] Review deployment configuration
""",
            ErrorCategory.MEMORY: """
- [ ] Increase container memory limits
- [ ] Check for memory leaks
- [ ] Review resource usage patterns
- [ ] Consider scaling horizontally
""",
            ErrorCategory.DEPENDENCY: """
- [ ] Run dependency installation commands
- [ ] Check package versions for compatibility
- [ ] Review import statements
- [ ] Verify build process
""",
            ErrorCategory.MIGRATION: """
- [ ] Check migration files for errors
- [ ] Verify database schema state
- [ ] Review migration history
- [ ] Consider rolling back problematic migrations
""",
        }
        
        return recommendations.get(category, """
- [ ] Review error logs for root cause
- [ ] Check service health and dependencies
- [ ] Review recent changes
- [ ] Consider reverting problematic deployments
""")
    
    def monitor_realtime(self, interval_seconds: int = 30, 
                        max_iterations: Optional[int] = None):
        """Monitor logs in real-time and report errors."""
        print("Starting real-time monitoring...")
        print(f"Checking every {interval_seconds} seconds")
        print("Press Ctrl+C to stop")
        print("")
        
        iteration = 0
        try:
            while max_iterations is None or iteration < max_iterations:
                iteration += 1
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Checking logs (iteration {iteration})...")
                
                # Get logs from last interval
                since = f"{interval_seconds}s"
                all_logs = self.analyze_all_services(tail=100)
                
                # Report any new errors
                new_errors = 0
                for service, logs in all_logs.items():
                    if logs.errors:
                        print(f"  {service}: {len(logs.errors)} errors detected")
                        new_errors += len(logs.errors)
                
                if new_errors == 0:
                    print("  No errors detected")
                else:
                    # Generate quick summary
                    print(f"\n  Total: {new_errors} errors found")
                    
                    # Ask if user wants detailed report
                    if input("\n  Generate detailed report? (y/N): ").lower() == 'y':
                        report = self.generate_error_report(all_logs)
                        print("\n" + report)
                        
                        if input("\n  Create GitHub issues? (y/N): ").lower() == 'y':
                            issue_files = self.generate_github_issues(all_logs)
                            print(f"  Created {len(issue_files)} issue files")
                
                # Wait for next iteration
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Docker Compose Log Introspector with Error Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all services
  python docker_compose_log_introspector.py analyze
  
  # Analyze specific service
  python docker_compose_log_introspector.py analyze --service backend
  
  # Generate GitHub issues for errors
  python docker_compose_log_introspector.py analyze --create-issues
  
  # Monitor in real-time
  python docker_compose_log_introspector.py monitor --interval 30
  
  # Get recent logs only
  python docker_compose_log_introspector.py analyze --since 5m
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', 
                                          help='Analyze logs for errors')
    analyze_parser.add_argument('--service', help='Specific service to analyze')
    analyze_parser.add_argument('--tail', type=int, default=1000,
                               help='Number of lines to analyze (default: 1000)')
    analyze_parser.add_argument('--since', help='Time range (e.g., 5m, 1h, 2d)')
    analyze_parser.add_argument('--create-issues', action='store_true',
                               help='Create GitHub issue files')
    analyze_parser.add_argument('--output', help='Output report to file')
    analyze_parser.add_argument('-f', '--compose-file', 
                               default='docker-compose.yml',
                               help='Docker Compose file')
    analyze_parser.add_argument('-p', '--project', help='Project name')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', 
                                          help='Monitor logs in real-time')
    monitor_parser.add_argument('--interval', type=int, default=30,
                               help='Check interval in seconds (default: 30)')
    monitor_parser.add_argument('--max-iterations', type=int,
                               help='Maximum iterations (unlimited if not set)')
    monitor_parser.add_argument('-f', '--compose-file', 
                               default='docker-compose.yml',
                               help='Docker Compose file')
    monitor_parser.add_argument('-p', '--project', help='Project name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Create introspector
    compose_file = getattr(args, 'compose_file', 'docker-compose.yml')
    project = getattr(args, 'project', None)
    introspector = DockerComposeLogIntrospector(compose_file, project)
    
    if args.command == 'analyze':
        # Analyze logs
        if args.service:
            logs = introspector.get_service_logs(args.service, 
                                                tail=args.tail, 
                                                since=args.since)
            all_logs = {args.service: logs}
        else:
            all_logs = introspector.analyze_all_services(tail=args.tail)
        
        # Generate report
        report = introspector.generate_error_report(all_logs)
        
        # Output report
        if args.output:
            Path(args.output).write_text(report)
            print(f"Report saved to: {args.output}")
        else:
            print(report)
        
        # Create issues if requested
        if args.create_issues:
            issue_files = introspector.generate_github_issues(all_logs)
            if issue_files:
                print(f"\nCreated {len(issue_files)} issue files:")
                for filepath in issue_files:
                    print(f"  - {filepath}")
            else:
                print("\nNo issues to create (no errors found)")
                
    elif args.command == 'monitor':
        # Real-time monitoring
        introspector.monitor_realtime(
            interval_seconds=args.interval,
            max_iterations=args.max_iterations
        )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())