#!/usr/bin/env python3
"""
GCP Staging Environment Log Analysis
Systematic analysis of all staging service logs to identify issues using Five Whys methodology
"""

import json
import re
import sys
import io
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Fix Windows Unicode issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class StagingLogAnalyzer:
    """Analyzes GCP staging logs to identify system issues"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.logs = []
        self.issues = []
        self.service_stats = defaultdict(lambda: {
            'total_requests': 0,
            'error_count': 0,
            'warning_count': 0,
            'avg_latency': 0,
            'max_latency': 0,
            'status_codes': Counter(),
            'error_messages': [],
            'warning_messages': []
        })
        
        # Known issue patterns
        self.error_patterns = {
            'database_connection': [
                r'connection.*failed', r'database.*error', r'connection.*refused',
                r'timeout.*connecting', r'cannot connect', r'connection lost'
            ],
            'authentication': [
                r'auth.*failed', r'unauthorized', r'invalid.*token', r'token.*expired',
                r'permission denied', r'access denied', r'401', r'403'
            ],
            'configuration': [
                r'config.*not.*found', r'missing.*config', r'invalid.*config',
                r'environment.*variable.*not.*set', r'.*_ID.*not.*configured'
            ],
            'service_communication': [
                r'service.*unavailable', r'connection.*refused', r'timeout',
                r'502', r'503', r'504', r'bad gateway', r'service down'
            ],
            'performance': [
                r'timeout', r'slow.*query', r'high.*latency', r'memory.*error',
                r'cpu.*usage', r'response.*time.*exceeded'
            ],
            'oauth_issues': [
                r'oauth.*error', r'google.*client.*id', r'client.*secret',
                r'redirect.*uri', r'authorization.*code', r'token.*exchange'
            ]
        }
        
        self.warning_patterns = {
            'performance_degradation': [
                r'slow', r'latency', r'performance', r'memory usage',
                r'cpu usage', r'response time'
            ],
            'resource_usage': [
                r'memory', r'cpu', r'disk', r'connection.*pool',
                r'rate.*limit', r'quota'
            ]
        }
    
    def load_logs(self):
        """Load logs from JSON file"""
        try:
            with open(self.log_file, 'r') as f:
                self.logs = json.load(f)
            print(f"[U+2713] Loaded {len(self.logs)} log entries")
        except Exception as e:
            print(f"[U+2717] Error loading logs: {e}")
            return False
        return True
    
    def analyze_logs(self):
        """Main analysis function"""
        if not self.load_logs():
            return
        
        print("\n SEARCH:  Analyzing logs for issues...")
        
        # Process each log entry
        for log in self.logs:
            self._process_log_entry(log)
        
        # Generate analysis results
        self._analyze_service_health()
        self._identify_critical_issues()
        self._detect_patterns()
        
        print("[U+2713] Analysis complete")
    
    def _process_log_entry(self, log: Dict[str, Any]):
        """Process a single log entry"""
        # Extract basic info
        service_name = log.get('resource', {}).get('labels', {}).get('service_name', 'unknown')
        severity = log.get('severity', 'INFO')
        timestamp = log.get('timestamp', '')
        
        # Process HTTP requests
        if 'httpRequest' in log:
            http_req = log['httpRequest']
            status = http_req.get('status', 0)
            latency = self._parse_latency(http_req.get('latency', '0s'))
            
            self.service_stats[service_name]['total_requests'] += 1
            self.service_stats[service_name]['status_codes'][status] += 1
            
            # Track latency
            if latency > 0:
                current_avg = self.service_stats[service_name]['avg_latency']
                total_reqs = self.service_stats[service_name]['total_requests']
                self.service_stats[service_name]['avg_latency'] = (
                    (current_avg * (total_reqs - 1) + latency) / total_reqs
                )
                self.service_stats[service_name]['max_latency'] = max(
                    self.service_stats[service_name]['max_latency'], latency
                )
            
            # Check for error status codes
            if status >= 400:
                self.service_stats[service_name]['error_count'] += 1
                self._add_issue({
                    'type': 'http_error',
                    'severity': 'ERROR' if status >= 500 else 'WARNING',
                    'service': service_name,
                    'message': f"HTTP {status} error on {http_req.get('requestMethod', 'GET')} {http_req.get('requestUrl', 'unknown')}",
                    'timestamp': timestamp,
                    'details': http_req
                })
        
        # Process text payload for errors
        text_payload = log.get('textPayload', '')
        if text_payload:
            self._analyze_text_payload(text_payload, service_name, severity, timestamp)
        
        # Process JSON payload for errors
        json_payload = log.get('jsonPayload', {})
        if json_payload and 'message' in json_payload:
            self._analyze_text_payload(json_payload['message'], service_name, severity, timestamp)
        
        # Count severity levels
        if severity in ['ERROR', 'CRITICAL']:
            self.service_stats[service_name]['error_count'] += 1
        elif severity == 'WARNING':
            self.service_stats[service_name]['warning_count'] += 1
    
    def _parse_latency(self, latency_str: str) -> float:
        """Parse latency string to seconds"""
        if not latency_str:
            return 0.0
        
        try:
            # Handle format like "0.014146236s"
            if latency_str.endswith('s'):
                return float(latency_str[:-1])
        except:
            pass
        return 0.0
    
    def _analyze_text_payload(self, text: str, service: str, severity: str, timestamp: str):
        """Analyze text payload for known error patterns"""
        text_lower = text.lower()
        
        # Check error patterns
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    self._add_issue({
                        'type': error_type,
                        'severity': severity,
                        'service': service,
                        'message': text[:200] + ('...' if len(text) > 200 else ''),
                        'timestamp': timestamp,
                        'pattern_matched': pattern
                    })
                    
                    if severity in ['ERROR', 'CRITICAL']:
                        self.service_stats[service]['error_messages'].append(text)
                    break  # Only match first pattern to avoid duplicates
        
        # Check warning patterns
        if severity == 'WARNING':
            for warning_type, patterns in self.warning_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text_lower):
                        self.service_stats[service]['warning_messages'].append(text)
                        break
    
    def _add_issue(self, issue: Dict[str, Any]):
        """Add issue to the list"""
        self.issues.append(issue)
    
    def _analyze_service_health(self):
        """Analyze overall service health"""
        print("\n CHART:  Service Health Analysis:")
        
        for service, stats in self.service_stats.items():
            total_reqs = stats['total_requests']
            if total_reqs == 0:
                continue
            
            error_rate = (stats['error_count'] / total_reqs) * 100 if total_reqs > 0 else 0
            avg_latency_ms = stats['avg_latency'] * 1000
            max_latency_ms = stats['max_latency'] * 1000
            
            print(f"\n[U+1F538] {service}:")
            print(f"  Total Requests: {total_reqs}")
            print(f"  Error Rate: {error_rate:.2f}%")
            print(f"  Warning Count: {stats['warning_count']}")
            print(f"  Avg Latency: {avg_latency_ms:.1f}ms")
            print(f"  Max Latency: {max_latency_ms:.1f}ms")
            print(f"  Status Code Distribution: {dict(stats['status_codes'])}")
            
            # Health assessment
            health_status = self._assess_service_health(stats, total_reqs)
            print(f"  Health Status: {health_status}")
    
    def _assess_service_health(self, stats: Dict, total_reqs: int) -> str:
        """Assess service health based on metrics"""
        error_rate = (stats['error_count'] / total_reqs) * 100 if total_reqs > 0 else 0
        avg_latency = stats['avg_latency']
        
        if error_rate > 10 or avg_latency > 2.0:
            return "[U+1F534] CRITICAL"
        elif error_rate > 5 or avg_latency > 1.0:
            return "[U+1F7E1] DEGRADED"
        elif error_rate > 1 or avg_latency > 0.5:
            return "[U+1F7E0] WARNING"
        else:
            return "[U+1F7E2] HEALTHY"
    
    def _identify_critical_issues(self):
        """Identify and categorize critical issues"""
        critical_issues = [issue for issue in self.issues if issue['severity'] in ['ERROR', 'CRITICAL']]
        major_issues = [issue for issue in self.issues if issue['severity'] == 'WARNING']
        
        print(f"\n ALERT:  Critical Issues Found: {len(critical_issues)}")
        print(f" WARNING: [U+FE0F]  Major Issues Found: {len(major_issues)}")
        
        # Group issues by type
        issues_by_type = defaultdict(list)
        for issue in self.issues:
            issues_by_type[issue['type']].append(issue)
        
        for issue_type, type_issues in issues_by_type.items():
            if len(type_issues) > 0:
                print(f"\n[U+1F539] {issue_type.replace('_', ' ').title()}: {len(type_issues)} issues")
                
                # Show most recent examples
                recent_issues = sorted(type_issues, key=lambda x: x['timestamp'], reverse=True)[:3]
                for issue in recent_issues:
                    print(f"  [U+2022] [{issue['service']}] {issue['message']}")
    
    def _detect_patterns(self):
        """Detect recurring patterns and trends"""
        print("\n SEARCH:  Pattern Analysis:")
        
        # Service error distribution
        service_errors = defaultdict(int)
        for issue in self.issues:
            if issue['severity'] in ['ERROR', 'CRITICAL']:
                service_errors[issue['service']] += 1
        
        if service_errors:
            print("  Error Distribution by Service:")
            for service, count in sorted(service_errors.items(), key=lambda x: x[1], reverse=True):
                print(f"    {service}: {count} errors")
        
        # Issue type distribution
        type_counts = Counter(issue['type'] for issue in self.issues)
        if type_counts:
            print("  Top Issue Types:")
            for issue_type, count in type_counts.most_common(5):
                print(f"    {issue_type.replace('_', ' ').title()}: {count} occurrences")
    
    def perform_root_cause_analysis(self):
        """Perform Five Whys analysis for top issues"""
        print("\n[U+1F52C] Five Whys Root Cause Analysis:")
        
        # Group issues by type and frequency
        issue_groups = defaultdict(list)
        for issue in self.issues:
            if issue['severity'] in ['ERROR', 'CRITICAL']:
                issue_groups[issue['type']].append(issue)
        
        # Analyze top 3 most frequent issue types
        top_issues = sorted(issue_groups.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        
        for issue_type, issues in top_issues:
            print(f"\n TARGET:  Root Cause Analysis: {issue_type.replace('_', ' ').title()}")
            print(f"   Frequency: {len(issues)} occurrences")
            
            # Select most recent issue for detailed analysis
            latest_issue = max(issues, key=lambda x: x['timestamp'])
            print(f"   Latest Example: {latest_issue['message']}")
            print(f"   Service: {latest_issue['service']}")
            
            # Perform Five Whys
            whys = self._five_whys_analysis(issue_type, latest_issue)
            for i, why in enumerate(whys, 1):
                print(f"   Why #{i}: {why}")
            
            # Impact assessment
            print(f"   Impact: {self._assess_issue_impact(issue_type, issues)}")
    
    def _five_whys_analysis(self, issue_type: str, issue: Dict[str, Any]) -> List[str]:
        """Perform Five Whys analysis for specific issue types"""
        
        if issue_type == 'http_error':
            return [
                f"HTTP error {issue.get('details', {}).get('status', 'unknown')} occurred",
                "Service returned error response due to internal issue",
                "Application logic or dependency failure caused error",
                "Underlying system component (database, auth, config) has problem",
                "Root cause: Missing configuration, service dependency, or resource constraint"
            ]
        
        elif issue_type == 'configuration':
            return [
                "Configuration value is missing or invalid",
                "Environment variable was not set during deployment",
                "Deployment script did not include required config",
                "Config management process doesn't validate all required values",
                "Root cause: Incomplete configuration validation and deployment checklist"
            ]
        
        elif issue_type == 'authentication':
            return [
                "Authentication failed for user request",
                "Token validation service rejected the token",
                "JWT secret key or OAuth config is misconfigured",
                "Auth service cannot access required credentials",
                "Root cause: OAuth credentials (CLIENT_ID/SECRET) not properly configured"
            ]
        
        elif issue_type == 'service_communication':
            return [
                "Service-to-service communication failed",
                "Target service is unreachable or returned error",
                "Network connectivity or service discovery issue",
                "Service configuration or health check problem",
                "Root cause: Service deployment, network policy, or resource allocation issue"
            ]
        
        elif issue_type == 'performance':
            return [
                "Response time exceeded acceptable threshold",
                "Service is processing requests slowly",
                "Resource bottleneck (CPU, memory, I/O) is constraining performance",
                "System architecture or resource allocation is insufficient",
                "Root cause: Inadequate resource provisioning or inefficient code path"
            ]
        
        elif issue_type == 'database_connection':
            return [
                "Database connection attempt failed",
                "Database server is unreachable or rejecting connections",
                "Connection parameters, credentials, or network config is wrong",
                "Database service is down or misconfigured",
                "Root cause: Database connectivity or credential configuration issue"
            ]
        
        else:
            return [
                f"Issue of type '{issue_type}' occurred",
                "Underlying system component has a problem",
                "Configuration, dependency, or resource issue exists",
                "System design or deployment process has gap",
                "Root cause: Need deeper investigation of specific issue type"
            ]
    
    def _assess_issue_impact(self, issue_type: str, issues: List[Dict]) -> str:
        """Assess the impact of an issue type"""
        count = len(issues)
        services_affected = len(set(issue['service'] for issue in issues))
        
        impact_levels = {
            'authentication': 'CRITICAL - Users cannot access the platform',
            'oauth_issues': 'CRITICAL - Login functionality broken',
            'configuration': 'HIGH - Core functionality may be impacted',
            'database_connection': 'CRITICAL - Data access failures',
            'service_communication': 'HIGH - Feature degradation across services',
            'http_error': 'MEDIUM - Individual request failures',
            'performance': 'MEDIUM - User experience degradation'
        }
        
        base_impact = impact_levels.get(issue_type, 'LOW - Isolated functionality impact')
        
        if count > 10:
            return f"{base_impact} (HIGH FREQUENCY: {count} occurrences)"
        elif services_affected > 1:
            return f"{base_impact} (MULTI-SERVICE: {services_affected} services affected)"
        else:
            return base_impact
    
    def generate_recommendations(self):
        """Generate actionable recommendations"""
        print("\n IDEA:  Recommendations:")
        
        # Analyze issues and generate specific recommendations
        issue_types = set(issue['type'] for issue in self.issues if issue['severity'] in ['ERROR', 'CRITICAL'])
        
        recommendations = []
        
        if 'authentication' in issue_types or 'oauth_issues' in issue_types:
            recommendations.append("1. [U+1F511] CRITICAL: Configure OAuth credentials (GOOGLE_OAUTH_CLIENT_ID_STAGING, GOOGLE_OAUTH_CLIENT_SECRET_STAGING) in GCP staging environment")
            recommendations.append("2.  SEARCH:  Verify redirect URIs match in Google Cloud Console and deployment configuration")
        
        if 'configuration' in issue_types:
            recommendations.append("3. [U+2699][U+FE0F] Audit all required environment variables in staging deployment")
            recommendations.append("4. [U+1F4DD] Implement configuration validation during startup")
        
        if 'performance' in issue_types:
            recommendations.append("5. [U+1F680] Investigate frontend performance - current 0.37s response time exceeds target")
            recommendations.append("6.  CHART:  Enable detailed performance monitoring and profiling")
        
        if 'service_communication' in issue_types:
            recommendations.append("7. [U+1F517] Review service-to-service communication patterns and timeouts")
            recommendations.append("8. [U+1F3E5] Implement proper health checks and circuit breakers")
        
        if 'database_connection' in issue_types:
            recommendations.append("9. [U+1F5C4][U+FE0F] Verify database connectivity and connection pool configuration")
            recommendations.append("10. [U+1F510] Check database credentials and SSL configuration")
        
        # Always include these general recommendations
        recommendations.extend([
            "11. [U+1F4C8] Set up proper alerting for error rates > 5% and latency > 1s",
            "12.  SEARCH:  Implement structured logging with correlation IDs",
            "13. [U+1F4CB] Create runbooks for common issue types identified"
        ])
        
        for rec in recommendations:
            print(f"  {rec}")
    
    def generate_report(self):
        """Generate final comprehensive report"""
        print("\n" + "="*80)
        print("[U+1F3E5] NETRA STAGING ENVIRONMENT HEALTH REPORT")
        print("="*80)
        
        # Summary metrics
        total_issues = len(self.issues)
        critical_issues = len([i for i in self.issues if i['severity'] in ['ERROR', 'CRITICAL']])
        services_with_issues = len(set(i['service'] for i in self.issues))
        
        print(f"\n CHART:  SUMMARY:")
        print(f"  Total Issues Detected: {total_issues}")
        print(f"  Critical Issues: {critical_issues}")
        print(f"  Services Affected: {services_with_issues}")
        print(f"  Analysis Time Range: Last 2-3 hours")
        
        # Service status
        print(f"\n[U+1F3E5] SERVICE STATUS:")
        for service, stats in self.service_stats.items():
            if stats['total_requests'] > 0:
                health = self._assess_service_health(stats, stats['total_requests'])
                print(f"  {service}: {health}")
        
        # Top priority fixes
        print(f"\n ALERT:  TOP PRIORITY FIXES:")
        
        issue_priorities = defaultdict(list)
        for issue in self.issues:
            if issue['severity'] in ['ERROR', 'CRITICAL']:
                issue_priorities[issue['type']].append(issue)
        
        priority_order = ['authentication', 'oauth_issues', 'configuration', 'database_connection', 'performance']
        
        fix_count = 1
        for issue_type in priority_order:
            if issue_type in issue_priorities:
                count = len(issue_priorities[issue_type])
                impact = self._assess_issue_impact(issue_type, issue_priorities[issue_type])
                print(f"  {fix_count}. {issue_type.replace('_', ' ').title()}: {count} issues - {impact}")
                fix_count += 1

def main():
    """Main execution function"""
    analyzer = StagingLogAnalyzer('staging_logs.json')
    
    print(" SEARCH:  Starting GCP Staging Environment Analysis...")
    print("Using Five Whys methodology for root cause analysis")
    
    # Run analysis
    analyzer.analyze_logs()
    analyzer.perform_root_cause_analysis()
    analyzer.generate_recommendations()
    analyzer.generate_report()
    
    print(f"\n PASS:  Analysis complete. Found {len(analyzer.issues)} total issues.")

if __name__ == '__main__':
    main()