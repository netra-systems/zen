"""
Docker Introspection Module - SSOT for Docker Analysis

This module consolidates all Docker log analysis, introspection, and monitoring
capabilities from multiple scattered tools into a single, unified interface.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity, Risk Reduction
2. Business Goal: Eliminate Docker debugging tool fragmentation
3. Value Impact: Faster issue detection and resolution, reduced downtime
4. Revenue Impact: Protects development velocity and system reliability

Consolidated Features From:
- DockerComposeLogIntrospector
- DockerLogIntrospector  
- WindowsDockerIntrospector
- DockerLogRemediator
- DockerServicesAuditor
- DockerCleaner
- DockerFileChecker
"""

import json
import logging
import re
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

# CRITICAL: Import Docker rate limiter to prevent daemon crashes
from test_framework.docker_rate_limiter import execute_docker_command

# Windows Unicode fix
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logger = logging.getLogger(__name__)


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
    STARTUP = "Startup"
    SHUTDOWN = "Shutdown"
    UNKNOWN = "Unknown"


class LogLevel(Enum):
    """Log level matching."""
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"
    FATAL = "FATAL"


@dataclass
class LogEntry:
    """Individual log entry with metadata."""
    timestamp: datetime
    service: str
    level: LogLevel
    message: str
    raw_line: str
    line_number: int = 0
    
    @property
    def is_error(self) -> bool:
        return self.level in [LogLevel.ERROR, LogLevel.FATAL]
    
    @property
    def is_warning(self) -> bool:
        return self.level == LogLevel.WARN


@dataclass 
class DockerIssue:
    """Docker issue with context and suggested remediation."""
    service: str
    category: ErrorCategory
    severity: ErrorSeverity
    title: str
    description: str
    first_seen: datetime
    last_seen: datetime
    count: int = 1
    log_entries: List[LogEntry] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.suggested_fixes:
            self.suggested_fixes = self._generate_suggestions()
    
    def _generate_suggestions(self) -> List[str]:
        """Generate suggested fixes based on category and description."""
        suggestions = []
        
        if self.category == ErrorCategory.DATABASE_CONNECTION:
            suggestions.extend([
                "Check if database service is running: docker-compose ps postgres",
                "Verify database connection string in environment variables",
                "Check database logs: docker-compose logs postgres",
                "Restart database service: docker-compose restart postgres"
            ])
        
        elif self.category == ErrorCategory.AUTHENTICATION:
            suggestions.extend([
                "Check JWT_SECRET_KEY environment variable",
                "Verify OAuth configuration",
                "Check authentication service logs",
                "Validate API keys and tokens"
            ])
            
        elif self.category == ErrorCategory.NETWORK:
            suggestions.extend([
                "Check network connectivity between services",
                "Verify port mappings in docker-compose.yml",
                "Check for port conflicts: netstat -tulpn",
                "Restart Docker network: docker-compose down && docker-compose up"
            ])
            
        elif self.category == ErrorCategory.MEMORY:
            suggestions.extend([
                "Check container memory limits",
                "Monitor system memory usage: free -h",
                "Restart memory-intensive services",
                "Consider increasing memory limits in docker-compose.yml"
            ])
            
        elif self.category == ErrorCategory.STARTUP:
            suggestions.extend([
                "Check service dependencies in docker-compose.yml",
                "Verify environment variables are set",
                "Check for missing files or configurations",
                "Review container logs for initialization errors"
            ])
        
        return suggestions


@dataclass
class IntrospectionReport:
    """Comprehensive Docker introspection report."""
    generated_at: datetime
    services_analyzed: List[str]
    total_log_lines: int
    issues_found: List[DockerIssue]
    service_status: Dict[str, str]
    resource_usage: Dict[str, Any]
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def critical_issues(self) -> List[DockerIssue]:
        return [i for i in self.issues_found if i.severity == ErrorSeverity.CRITICAL]
    
    @property
    def error_issues(self) -> List[DockerIssue]:
        return [i for i in self.issues_found if i.severity == ErrorSeverity.ERROR]
    
    @property
    def has_critical_issues(self) -> bool:
        return len(self.critical_issues) > 0


class DockerIntrospector:
    """
    Unified Docker introspection and analysis engine.
    
    Consolidates all Docker analysis capabilities into a single SSOT interface.
    """
    
    # Error pattern matching (consolidated from all introspection tools)
    ERROR_PATTERNS = {
        ErrorCategory.DATABASE_CONNECTION: [
            re.compile(r"connection.*refused", re.I),
            re.compile(r"could not connect.*database", re.I),
            re.compile(r"database.*unavailable", re.I),
            re.compile(r"psql.*error", re.I),
            re.compile(r"connection.*timeout.*database", re.I),
            re.compile(r"fatal.*database.*error", re.I)
        ],
        ErrorCategory.API_ERROR: [
            re.compile(r"http.*error.*[45]\d\d", re.I),
            re.compile(r"api.*error", re.I),
            re.compile(r"request.*failed", re.I),
            re.compile(r"internal server error", re.I),
            re.compile(r"bad gateway", re.I)
        ],
        ErrorCategory.AUTHENTICATION: [
            re.compile(r"authentication.*failed", re.I),
            re.compile(r"unauthorized", re.I),
            re.compile(r"invalid.*token", re.I),
            re.compile(r"permission.*denied", re.I),
            re.compile(r"jwt.*error", re.I)
        ],
        ErrorCategory.NETWORK: [
            re.compile(r"network.*unreachable", re.I),
            re.compile(r"connection.*reset", re.I),
            re.compile(r"host.*unreachable", re.I),
            re.compile(r"dns.*resolution.*failed", re.I),
            re.compile(r"bind.*address.*already.*in.*use", re.I)
        ],
        ErrorCategory.MEMORY: [
            re.compile(r"out of memory", re.I),
            re.compile(r"memory.*allocation.*failed", re.I),
            re.compile(r"oom.*killed", re.I),
            re.compile(r"cannot allocate memory", re.I)
        ],
        ErrorCategory.TIMEOUT: [
            re.compile(r"timeout", re.I),
            re.compile(r"timed.*out", re.I),
            re.compile(r"deadline.*exceeded", re.I)
        ],
        ErrorCategory.STARTUP: [
            re.compile(r"failed.*to.*start", re.I),
            re.compile(r"initialization.*failed", re.I),
            re.compile(r"startup.*error", re.I),
            re.compile(r"cannot.*initialize", re.I)
        ]
    }
    
    def __init__(self, compose_file: str = "docker-compose.test.yml", project_name: str = "netra-test"):
        self.compose_file = Path(compose_file)
        self.project_name = project_name
        self.issues: Dict[str, DockerIssue] = {}  # Issue deduplication
        
    def analyze_services(self, 
                        services: Optional[List[str]] = None,
                        since: Optional[str] = None,
                        follow: bool = False,
                        max_lines: int = 1000) -> IntrospectionReport:
        """
        Perform comprehensive analysis of Docker services.
        
        Args:
            services: Services to analyze, None for all
            since: Time to start analysis from (e.g., '1h', '30m')
            follow: Follow logs in real-time
            max_lines: Maximum log lines to analyze
            
        Returns:
            Comprehensive introspection report
        """
        logger.info(f"Starting Docker introspection for services: {services or 'all'}")
        
        # Get service status
        service_status = self._get_service_status(services)
        
        # Collect logs
        log_entries = self._collect_logs(services, since, max_lines)
        
        # Analyze logs for issues
        issues = self._analyze_log_entries(log_entries)
        
        # Get resource usage
        resource_usage = self._get_resource_usage(services)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(issues, service_status, resource_usage)
        
        report = IntrospectionReport(
            generated_at=datetime.now(),
            services_analyzed=list(service_status.keys()),
            total_log_lines=len(log_entries),
            issues_found=list(issues.values()),
            service_status=service_status,
            resource_usage=resource_usage,
            recommendations=recommendations
        )
        
        logger.info(f"Analysis complete: {len(issues)} issues found across {len(log_entries)} log lines")
        return report
    
    def _get_service_status(self, services: Optional[List[str]]) -> Dict[str, str]:
        """Get current status of Docker services."""
        cmd = ["docker-compose", "-f", str(self.compose_file), "-p", self.project_name, "ps", "--format", "json"]
        
        if services:
            cmd.extend(services)
        
        try:
            # Use rate-limited Docker execution to prevent daemon overload
            docker_result = execute_docker_command(cmd, timeout=30)
            
            if docker_result.returncode != 0:
                logger.warning(f"Failed to get service status: {docker_result.stderr}")
                return {}
            
            result_stdout = docker_result.stdout
            
            status = {}
            for line in result_stdout.strip().split('\\n'):
                if line:
                    try:
                        data = json.loads(line)
                        service = data.get('Service', '')
                        state = data.get('State', 'unknown')
                        if service:
                            status[service] = state
                    except json.JSONDecodeError:
                        continue
            
            return status
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout getting service status")
            return {}
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {}
    
    def _collect_logs(self, 
                     services: Optional[List[str]], 
                     since: Optional[str],
                     max_lines: int) -> List[LogEntry]:
        """Collect and parse log entries from Docker services."""
        cmd = ["docker-compose", "-f", str(self.compose_file), "-p", self.project_name, "logs", "--timestamps"]
        
        if since:
            cmd.extend(["--since", since])
            
        if max_lines > 0:
            cmd.extend(["--tail", str(max_lines)])
            
        if services:
            cmd.extend(services)
        
        try:
            # Use rate-limited Docker execution to prevent daemon overload
            docker_result = execute_docker_command(cmd, timeout=60)
            
            if docker_result.returncode != 0:
                logger.warning(f"Failed to collect logs: {docker_result.stderr}")
                return []
            
            return self._parse_log_lines(docker_result.stdout)
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout collecting logs")
            return []
        except Exception as e:
            logger.error(f"Error collecting logs: {e}")
            return []
    
    def _parse_log_lines(self, log_output: str) -> List[LogEntry]:
        """Parse Docker Compose log output into structured entries."""
        entries = []
        line_number = 0
        
        for line in log_output.split('\\n'):
            if not line.strip():
                continue
                
            line_number += 1
            
            # Parse Docker Compose log format: service_1 | timestamp level message
            match = re.match(r'^([^|]+)\\s*\\|\\s*(.*)$', line)
            if not match:
                continue
                
            service_part = match.group(1).strip()
            log_part = match.group(2).strip()
            
            # Extract service name
            service = service_part.split('_')[0] if '_' in service_part else service_part
            
            # Parse timestamp and level from log part
            timestamp = datetime.now()  # Fallback
            level = LogLevel.INFO  # Default
            message = log_part
            
            # Try to extract timestamp (ISO format or custom)
            ts_match = re.match(r'^(\\d{4}-\\d{2}-\\d{2}[T\\s]\\d{2}:\\d{2}:\\d{2}[\\w\\-\\.:]*)', log_part)
            if ts_match:
                try:
                    timestamp_str = ts_match.group(1)
                    # Handle different timestamp formats
                    for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
                        try:
                            timestamp = datetime.strptime(timestamp_str, fmt)
                            break
                        except ValueError:
                            continue
                    
                    message = log_part[len(ts_match.group(1)):].strip()
                except Exception:
                    pass
            
            # Extract log level
            level_match = re.search(r'\\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\\b', message, re.I)
            if level_match:
                level_str = level_match.group(1).upper()
                if level_str in ['WARNING', 'WARN']:
                    level = LogLevel.WARN
                elif level_str in ['ERROR']:
                    level = LogLevel.ERROR
                elif level_str in ['FATAL', 'CRITICAL']:
                    level = LogLevel.FATAL
                elif level_str == 'DEBUG':
                    level = LogLevel.DEBUG
                else:
                    level = LogLevel.INFO
            
            entries.append(LogEntry(
                timestamp=timestamp,
                service=service,
                level=level,
                message=message,
                raw_line=line,
                line_number=line_number
            ))
        
        return entries
    
    def _analyze_log_entries(self, log_entries: List[LogEntry]) -> Dict[str, DockerIssue]:
        """Analyze log entries to identify issues and patterns."""
        issues = {}
        
        for entry in log_entries:
            # Skip non-error entries for issue detection
            if not entry.is_error and not entry.is_warning:
                continue
            
            # Classify error
            category = self._classify_error(entry.message)
            severity = self._determine_severity(entry, category)
            
            # Create issue key for deduplication
            issue_key = f"{entry.service}_{category.value}_{self._hash_message(entry.message)}"
            
            if issue_key in issues:
                # Update existing issue
                issues[issue_key].count += 1
                issues[issue_key].last_seen = entry.timestamp
                issues[issue_key].log_entries.append(entry)
            else:
                # Create new issue
                issues[issue_key] = DockerIssue(
                    service=entry.service,
                    category=category,
                    severity=severity,
                    title=self._generate_issue_title(entry, category),
                    description=self._generate_issue_description(entry, category),
                    first_seen=entry.timestamp,
                    last_seen=entry.timestamp,
                    count=1,
                    log_entries=[entry]
                )
        
        return issues
    
    def _classify_error(self, message: str) -> ErrorCategory:
        """Classify error message into category."""
        for category, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(message):
                    return category
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, entry: LogEntry, category: ErrorCategory) -> ErrorSeverity:
        """Determine issue severity based on log level and category."""
        if entry.level == LogLevel.FATAL:
            return ErrorSeverity.CRITICAL
        
        if category in [ErrorCategory.DATABASE_CONNECTION, ErrorCategory.MEMORY]:
            return ErrorSeverity.ERROR if entry.is_error else ErrorSeverity.WARNING
        
        if category == ErrorCategory.AUTHENTICATION:
            return ErrorSeverity.ERROR
        
        if entry.is_error:
            return ErrorSeverity.ERROR
        elif entry.is_warning:
            return ErrorSeverity.WARNING
        else:
            return ErrorSeverity.INFO
    
    def _hash_message(self, message: str) -> str:
        """Create a hash for message deduplication."""
        # Remove timestamps, IDs, and other variable parts
        cleaned = re.sub(r'\\d{4}-\\d{2}-\\d{2}[T\\s]\\d{2}:\\d{2}:\\d{2}[\\w\\-\\.:]*', '', message)
        cleaned = re.sub(r'\\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\b', 'UUID', cleaned)
        cleaned = re.sub(r'\\b\\d+\\b', 'NUM', cleaned)
        
        return str(hash(cleaned))
    
    def _generate_issue_title(self, entry: LogEntry, category: ErrorCategory) -> str:
        """Generate a concise issue title."""
        return f"{entry.service}: {category.value} - {entry.message[:100]}"
    
    def _generate_issue_description(self, entry: LogEntry, category: ErrorCategory) -> str:
        """Generate detailed issue description."""
        return (f"Service '{entry.service}' experiencing {category.value.lower()} issues. "
                f"First observed at {entry.timestamp}. Message: {entry.message}")
    
    def _get_resource_usage(self, services: Optional[List[str]]) -> Dict[str, Any]:
        """Get resource usage information for services."""
        usage = {}
        
        try:
            # Get container stats using rate-limited execution
            cmd = ["docker", "stats", "--no-stream", "--format", "json"]
            docker_result = execute_docker_command(cmd, timeout=30)
            
            if docker_result.returncode == 0:
                for line in docker_result.stdout.strip().split('\\n'):
                    if line:
                        try:
                            data = json.loads(line)
                            name = data.get('Name', '')
                            if name:
                                usage[name] = {
                                    'cpu_usage': data.get('CPUPerc', '0%'),
                                    'memory_usage': data.get('MemUsage', '0B'),
                                    'memory_percent': data.get('MemPerc', '0%'),
                                    'network_io': data.get('NetIO', '0B / 0B'),
                                    'block_io': data.get('BlockIO', '0B / 0B')
                                }
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning(f"Failed to get resource usage: {e}")
        
        return usage
    
    def _generate_recommendations(self, 
                                 issues: Dict[str, DockerIssue],
                                 service_status: Dict[str, str],
                                 resource_usage: Dict[str, Any]) -> List[str]:
        """Generate system-wide recommendations based on analysis."""
        recommendations = []
        
        # Critical issue recommendations
        critical_issues = [i for i in issues.values() if i.severity == ErrorSeverity.CRITICAL]
        if critical_issues:
            recommendations.append(" ALERT:  CRITICAL: Address critical issues immediately")
            for issue in critical_issues[:3]:  # Top 3
                recommendations.extend(issue.suggested_fixes[:2])  # Top 2 fixes per issue
        
        # Service status recommendations
        down_services = [svc for svc, status in service_status.items() if status != 'running']
        if down_services:
            recommendations.append(f" WARNING: [U+FE0F] Restart down services: {', '.join(down_services)}")
        
        # Resource usage recommendations
        high_cpu_services = []
        high_memory_services = []
        
        for service, stats in resource_usage.items():
            try:
                cpu_pct = float(stats.get('cpu_usage', '0%').replace('%', ''))
                mem_pct = float(stats.get('memory_percent', '0%').replace('%', ''))
                
                if cpu_pct > 80:
                    high_cpu_services.append(service)
                if mem_pct > 80:
                    high_memory_services.append(service)
            except ValueError:
                continue
        
        if high_cpu_services:
            recommendations.append(f" WARNING: [U+FE0F] High CPU usage: {', '.join(high_cpu_services)} - consider scaling")
        
        if high_memory_services:
            recommendations.append(f" WARNING: [U+FE0F] High memory usage: {', '.join(high_memory_services)} - check for leaks")
        
        # General maintenance recommendations
        error_issues = [i for i in issues.values() if i.severity == ErrorSeverity.ERROR]
        if len(error_issues) > 5:
            recommendations.append(" CHART:  Consider reviewing error patterns for systemic issues")
        
        return recommendations
    
    def export_report(self, report: IntrospectionReport, output_file: Optional[Path] = None) -> Path:
        """Export introspection report to JSON file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = Path(f"docker_introspection_report_{timestamp}.json")
        
        # Convert report to JSON-serializable format
        report_data = {
            'generated_at': report.generated_at.isoformat(),
            'services_analyzed': report.services_analyzed,
            'total_log_lines': report.total_log_lines,
            'service_status': report.service_status,
            'resource_usage': report.resource_usage,
            'recommendations': report.recommendations,
            'issues': []
        }
        
        for issue in report.issues_found:
            issue_data = {
                'service': issue.service,
                'category': issue.category.value,
                'severity': issue.severity.value,
                'title': issue.title,
                'description': issue.description,
                'first_seen': issue.first_seen.isoformat(),
                'last_seen': issue.last_seen.isoformat(),
                'count': issue.count,
                'suggested_fixes': issue.suggested_fixes,
                'sample_messages': [entry.message for entry in issue.log_entries[:5]]
            }
            report_data['issues'].append(issue_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report exported to: {output_file}")
        return output_file
    
    def cleanup_docker_resources(self) -> Dict[str, Any]:
        """Clean up unused Docker resources (containers, networks, volumes)."""
        cleanup_results = {}
        
        try:
            # Remove orphaned containers using rate-limited execution
            cmd = ["docker-compose", "-f", str(self.compose_file), "-p", self.project_name, 
                   "down", "--remove-orphans"]
            docker_result = execute_docker_command(cmd, timeout=60)
            cleanup_results['containers'] = docker_result.returncode == 0
            
            # Prune unused networks using rate-limited execution
            docker_result = execute_docker_command(["docker", "network", "prune", "-f"], timeout=30)
            cleanup_results['networks'] = docker_result.returncode == 0
            
            # Prune unused volumes using rate-limited execution
            docker_result = execute_docker_command(["docker", "volume", "prune", "-f"], timeout=30)
            cleanup_results['volumes'] = docker_result.returncode == 0
            
            # Get cleanup statistics using rate-limited execution
            docker_result = execute_docker_command(["docker", "system", "df"], timeout=30)
            cleanup_results['disk_usage'] = docker_result.stdout if docker_result.returncode == 0 else "Unknown"
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            cleanup_results['error'] = str(e)
        
        return cleanup_results


# CLI interface for the introspector
def main():
    """Command-line interface for Docker introspection."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Docker Introspection Tool")
    parser.add_argument("--services", nargs="+", help="Services to analyze")
    parser.add_argument("--since", help="Time to start analysis from (e.g., '1h', '30m')")
    parser.add_argument("--compose-file", default="docker-compose.test.yml", 
                        help="Docker Compose file to use")
    parser.add_argument("--project-name", default="netra-test", 
                        help="Docker Compose project name")
    parser.add_argument("--max-lines", type=int, default=1000, 
                        help="Maximum log lines to analyze")
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument("--cleanup", action="store_true", help="Clean up Docker resources")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    introspector = DockerIntrospector(args.compose_file, args.project_name)
    
    if args.cleanup:
        print("[U+1F9F9] Cleaning up Docker resources...")
        results = introspector.cleanup_docker_resources()
        print(f"Cleanup results: {results}")
    
    print(" SEARCH:  Analyzing Docker services...")
    report = introspector.analyze_services(
        services=args.services,
        since=args.since,
        max_lines=args.max_lines
    )
    
    # Print summary
    print(f"\\n CHART:  Analysis Summary:")
    print(f"Services analyzed: {len(report.services_analyzed)}")
    print(f"Log lines processed: {report.total_log_lines}")
    print(f"Issues found: {len(report.issues_found)}")
    print(f"Critical issues: {len(report.critical_issues)}")
    
    if report.critical_issues:
        print("\\n ALERT:  CRITICAL ISSUES:")
        for issue in report.critical_issues:
            print(f"  - {issue.title}")
    
    if report.recommendations:
        print("\\n IDEA:  RECOMMENDATIONS:")
        for rec in report.recommendations:
            print(f"  - {rec}")
    
    # Export report
    output_file = Path(args.output) if args.output else None
    exported_file = introspector.export_report(report, output_file)
    print(f"\\n[U+1F4C4] Full report exported to: {exported_file}")


if __name__ == "__main__":
    main()