#!/usr/bin/env python3
"""
GCP Logs Audit Script for Netra Apex Platform
Comprehensive analysis of Cloud Logging data for production issues

MISSION: Audit GCP logs to identify production issues, error patterns, and system health indicators.

Usage:
    python scripts/gcp_logs_audit.py --project netra-staging --hours 24
    python scripts/gcp_logs_audit.py --project netra-staging --service backend --severity ERROR
"""

import json
import sys
import argparse
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import subprocess
import re

class GCPLogsAuditor:
    """Comprehensive GCP logs auditor for Netra Apex platform"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.services = {
            'backend': 'netra-backend-staging',
            'auth': 'netra-auth-staging',
            'frontend': 'netra-frontend-staging'
        }
        self.error_patterns = {
            'database_timeout': [
                'connection timeout',
                'database connection failed',
                'PostgreSQL.*timeout',
                'Redis ping timeout',
                'sqlalchemy.*timeout'
            ],
            'vpc_connector': [
                'VPC.*connector',
                'vpc-access-connector',
                'staging-connector',
                'network.*not.*reachable'
            ],
            'websocket_issues': [
                'websocket.*failed',
                'handshake.*failed',
                'connection.*dropped',
                'websocket.*timeout',
                '1011.*error'
            ],
            'auth_failures': [
                'JWT.*invalid',
                'token.*expired',
                'authorization.*failed',
                'OAuth.*error',
                'authentication.*failed'
            ],
            'ssl_certificate': [
                'SSL.*certificate',
                'certificate.*expired',
                'TLS.*handshake',
                'certificate.*invalid'
            ],
            'load_balancer': [
                'health.*check.*failed',
                'upstream.*error',
                '502.*bad.*gateway',
                '503.*service.*unavailable',
                'backend.*unhealthy'
            ],
            'agent_execution': [
                'agent.*failed',
                'supervisor.*timeout',
                'execution.*error',
                'agent.*startup.*failed'
            ]
        }

    def _run_gcloud_command(self, command: List[str]) -> Optional[str]:
        """Execute gcloud command and return output"""
        try:
            result = subprocess.run(
                ['gcloud'] + command,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"Command failed: {' '.join(command)}")
                print(f"Error: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            print(f"Command timed out: {' '.join(command)}")
            return None
        except Exception as e:
            print(f"Error running command: {e}")
            return None

    def get_cloud_run_services(self) -> Dict[str, str]:
        """Get list of Cloud Run services in the project"""
        command = [
            'run', 'services', 'list',
            '--project', self.project_id,
            '--format', 'json'
        ]

        output = self._run_gcloud_command(command)
        if not output:
            return {}

        try:
            services = json.loads(output)
            return {
                service['metadata']['name']: service['status']['url']
                for service in services
                if service.get('status', {}).get('url')
            }
        except json.JSONDecodeError:
            print("Failed to parse Cloud Run services JSON")
            return {}

    def query_logs(self,
                   hours_back: int = 24,
                   severity: Optional[str] = None,
                   service: Optional[str] = None,
                   limit: int = 1000) -> List[Dict[str, Any]]:
        """Query Cloud Logging for the specified time range and filters"""

        # Build the filter
        filter_parts = []

        # Time filter
        time_filter = f'timestamp >= "{(datetime.utcnow() - timedelta(hours=hours_back)).isoformat()}Z"'
        filter_parts.append(time_filter)

        # Service filter
        if service and service in self.services:
            service_filter = f'resource.labels.service_name="{self.services[service]}"'
            filter_parts.append(service_filter)

        # Resource type filter for Cloud Run
        filter_parts.append('resource.type="cloud_run_revision"')

        # Severity filter
        if severity:
            filter_parts.append(f'severity >= {severity}')

        filter_query = ' AND '.join(filter_parts)

        command = [
            'logging', 'read', filter_query,
            '--project', self.project_id,
            '--format', 'json',
            '--limit', str(limit)
        ]

        print(f"Querying logs with filter: {filter_query}")
        output = self._run_gcloud_command(command)

        if not output:
            return []

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            print("Failed to parse logs JSON")
            return []

    def analyze_error_patterns(self, logs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Analyze logs for specific error patterns"""
        pattern_analysis = {}

        for pattern_name, patterns in self.error_patterns.items():
            pattern_analysis[pattern_name] = {
                'count': 0,
                'examples': [],
                'services': Counter(),
                'severity_distribution': Counter(),
                'timeline': []
            }

        for log_entry in logs:
            log_text = ""
            if 'textPayload' in log_entry:
                log_text = log_entry['textPayload']
            elif 'jsonPayload' in log_entry and 'message' in log_entry['jsonPayload']:
                log_text = log_entry['jsonPayload']['message']

            if not log_text:
                continue

            log_text_lower = log_text.lower()
            service_name = log_entry.get('resource', {}).get('labels', {}).get('service_name', 'unknown')
            severity = log_entry.get('severity', 'DEFAULT')
            timestamp = log_entry.get('timestamp', '')

            for pattern_name, patterns in self.error_patterns.items():
                for pattern in patterns:
                    if re.search(pattern.lower(), log_text_lower):
                        analysis = pattern_analysis[pattern_name]
                        analysis['count'] += 1
                        analysis['services'][service_name] += 1
                        analysis['severity_distribution'][severity] += 1
                        analysis['timeline'].append({
                            'timestamp': timestamp,
                            'service': service_name,
                            'severity': severity
                        })

                        if len(analysis['examples']) < 5:
                            analysis['examples'].append({
                                'timestamp': timestamp,
                                'service': service_name,
                                'severity': severity,
                                'message': log_text[:200] + ('...' if len(log_text) > 200 else '')
                            })
                        break

        return pattern_analysis

    def analyze_service_health(self, logs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Analyze service health based on logs"""
        service_health = {}

        for log_entry in logs:
            service_name = log_entry.get('resource', {}).get('labels', {}).get('service_name', 'unknown')
            severity = log_entry.get('severity', 'DEFAULT')

            if service_name not in service_health:
                service_health[service_name] = {
                    'total_logs': 0,
                    'error_count': 0,
                    'warning_count': 0,
                    'critical_count': 0,
                    'last_activity': '',
                    'error_rate': 0.0,
                    'status': 'UNKNOWN'
                }

            health = service_health[service_name]
            health['total_logs'] += 1

            if severity in ['ERROR', 'CRITICAL']:
                health['error_count'] += 1
                if severity == 'CRITICAL':
                    health['critical_count'] += 1
            elif severity == 'WARNING':
                health['warning_count'] += 1

            timestamp = log_entry.get('timestamp', '')
            if timestamp > health['last_activity']:
                health['last_activity'] = timestamp

        # Calculate health status
        for service_name, health in service_health.items():
            if health['total_logs'] > 0:
                health['error_rate'] = (health['error_count'] / health['total_logs']) * 100

                if health['critical_count'] > 0:
                    health['status'] = 'CRITICAL'
                elif health['error_rate'] > 10:
                    health['status'] = 'UNHEALTHY'
                elif health['error_rate'] > 5:
                    health['status'] = 'WARNING'
                else:
                    health['status'] = 'HEALTHY'

        return service_health

    def analyze_performance_metrics(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance metrics from logs"""
        response_times = []
        memory_usage = []
        cpu_usage = []

        for log_entry in logs:
            # Look for performance indicators in logs
            if 'jsonPayload' in log_entry:
                payload = log_entry['jsonPayload']

                # Response time analysis
                if 'response_time' in payload:
                    try:
                        response_times.append(float(payload['response_time']))
                    except (ValueError, TypeError):
                        pass

                # Memory usage
                if 'memory_usage' in payload:
                    try:
                        memory_usage.append(float(payload['memory_usage']))
                    except (ValueError, TypeError):
                        pass

                # CPU usage
                if 'cpu_usage' in payload:
                    try:
                        cpu_usage.append(float(payload['cpu_usage']))
                    except (ValueError, TypeError):
                        pass

        performance_metrics = {
            'response_times': {
                'count': len(response_times),
                'average': sum(response_times) / len(response_times) if response_times else 0,
                'max': max(response_times) if response_times else 0,
                'min': min(response_times) if response_times else 0
            },
            'memory_usage': {
                'count': len(memory_usage),
                'average': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                'max': max(memory_usage) if memory_usage else 0
            },
            'cpu_usage': {
                'count': len(cpu_usage),
                'average': sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                'max': max(cpu_usage) if cpu_usage else 0
            }
        }

        return performance_metrics

    def generate_recommendations(self,
                               error_patterns: Dict[str, Dict[str, Any]],
                               service_health: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []

        # Database timeout recommendations
        if error_patterns['database_timeout']['count'] > 0:
            recommendations.append({
                'priority': 'P0',
                'category': 'Database Connectivity',
                'issue': f"Database timeout errors detected ({error_patterns['database_timeout']['count']} occurrences)",
                'recommendation': 'Increase database timeout to 600s and verify VPC connector configuration',
                'action_items': [
                    'Verify staging-connector is READY state',
                    'Check database connection pool settings',
                    'Validate Cloud SQL instance performance',
                    'Review VPC network configuration'
                ]
            })

        # VPC connector recommendations
        if error_patterns['vpc_connector']['count'] > 0:
            recommendations.append({
                'priority': 'P0',
                'category': 'Infrastructure',
                'issue': f"VPC connector issues detected ({error_patterns['vpc_connector']['count']} occurrences)",
                'recommendation': 'Verify VPC connector staging-connector is properly configured and READY',
                'action_items': [
                    'Check VPC connector status: gcloud compute networks vpc-access connectors describe staging-connector',
                    'Validate Cloud Run services have VPC annotations',
                    'Verify IP CIDR ranges do not overlap with Redis/SQL networks'
                ]
            })

        # WebSocket recommendations
        if error_patterns['websocket_issues']['count'] > 0:
            recommendations.append({
                'priority': 'P1',
                'category': 'WebSocket Connectivity',
                'issue': f"WebSocket connection issues detected ({error_patterns['websocket_issues']['count']} occurrences)",
                'recommendation': 'Investigate WebSocket handshake failures and connection drops',
                'action_items': [
                    'Check websocket endpoint accessibility',
                    'Validate WebSocket upgrade headers',
                    'Review CORS configuration for WebSocket endpoints',
                    'Check for race conditions in WebSocket initialization'
                ]
            })

        # SSL certificate recommendations
        if error_patterns['ssl_certificate']['count'] > 0:
            recommendations.append({
                'priority': 'P1',
                'category': 'SSL/TLS',
                'issue': f"SSL certificate issues detected ({error_patterns['ssl_certificate']['count']} occurrences)",
                'recommendation': 'Validate SSL certificates for *.netrasystems.ai domains',
                'action_items': [
                    'Check certificate expiration dates',
                    'Validate certificate chain',
                    'Ensure load balancer SSL configuration is correct',
                    'Verify domain DNS resolution'
                ]
            })

        # Service health recommendations
        for service_name, health in service_health.items():
            if health['status'] in ['CRITICAL', 'UNHEALTHY']:
                recommendations.append({
                    'priority': 'P0' if health['status'] == 'CRITICAL' else 'P1',
                    'category': 'Service Health',
                    'issue': f"Service {service_name} is {health['status']} (Error rate: {health['error_rate']:.1f}%)",
                    'recommendation': f'Investigate and resolve issues in {service_name} service',
                    'action_items': [
                        f'Review detailed logs for {service_name}',
                        'Check service resource allocation',
                        'Validate service dependencies',
                        'Consider service restart if needed'
                    ]
                })

        return sorted(recommendations, key=lambda x: x['priority'])

    async def run_comprehensive_audit(self,
                                    hours_back: int = 24,
                                    service: Optional[str] = None,
                                    severity: Optional[str] = None) -> Dict[str, Any]:
        """Run comprehensive GCP logs audit"""

        print("🔍 Starting GCP Logs Audit for Netra Apex Platform")
        print(f"Project: {self.project_id}")
        print(f"Time range: Last {hours_back} hours")
        print(f"Service filter: {service or 'All services'}")
        print(f"Severity filter: {severity or 'All severities'}")
        print("-" * 60)

        # Get Cloud Run services
        print("📋 Discovering Cloud Run services...")
        cloud_run_services = self.get_cloud_run_services()
        print(f"Found {len(cloud_run_services)} Cloud Run services")

        # Query logs
        print("📥 Querying Cloud Logging...")
        logs = self.query_logs(hours_back, severity, service, limit=2000)
        print(f"Retrieved {len(logs)} log entries")

        if not logs:
            print("⚠️  No logs found matching the criteria")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'project_id': self.project_id,
                'summary': 'No logs found',
                'services': cloud_run_services,
                'error_patterns': {},
                'service_health': {},
                'performance_metrics': {},
                'recommendations': []
            }

        # Analyze error patterns
        print("🔍 Analyzing error patterns...")
        error_patterns = self.analyze_error_patterns(logs)

        # Analyze service health
        print("🏥 Analyzing service health...")
        service_health = self.analyze_service_health(logs)

        # Analyze performance metrics
        print("📊 Analyzing performance metrics...")
        performance_metrics = self.analyze_performance_metrics(logs)

        # Generate recommendations
        print("💡 Generating recommendations...")
        recommendations = self.generate_recommendations(error_patterns, service_health)

        audit_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'project_id': self.project_id,
            'parameters': {
                'hours_back': hours_back,
                'service_filter': service,
                'severity_filter': severity,
                'total_logs_analyzed': len(logs)
            },
            'services': cloud_run_services,
            'error_patterns': error_patterns,
            'service_health': service_health,
            'performance_metrics': performance_metrics,
            'recommendations': recommendations
        }

        return audit_results

def print_audit_summary(audit_results: Dict[str, Any]):
    """Print a formatted summary of the audit results"""

    print("\n" + "="*80)
    print("🔍 GCP LOGS AUDIT SUMMARY")
    print("="*80)

    print(f"📅 Audit Timestamp: {audit_results['timestamp']}")
    print(f"🏗️  Project: {audit_results['project_id']}")
    print(f"📊 Logs Analyzed: {audit_results['parameters']['total_logs_analyzed']}")

    # Error patterns summary
    print("\n🚨 ERROR PATTERN ANALYSIS:")
    print("-" * 40)
    error_patterns = audit_results['error_patterns']
    total_errors = sum(pattern['count'] for pattern in error_patterns.values())

    if total_errors == 0:
        print("✅ No significant error patterns detected")
    else:
        print(f"Total error occurrences: {total_errors}")
        for pattern_name, data in error_patterns.items():
            if data['count'] > 0:
                print(f"  {pattern_name}: {data['count']} occurrences")
                top_services = data['services'].most_common(3)
                if top_services:
                    services_str = ", ".join([f"{svc}({cnt})" for svc, cnt in top_services])
                    print(f"    Top services: {services_str}")

    # Service health summary
    print("\n🏥 SERVICE HEALTH STATUS:")
    print("-" * 40)
    service_health = audit_results['service_health']

    if not service_health:
        print("❓ No service health data available")
    else:
        for service, health in service_health.items():
            status_emoji = {
                'HEALTHY': '✅',
                'WARNING': '⚠️',
                'UNHEALTHY': '🔴',
                'CRITICAL': '💀',
                'UNKNOWN': '❓'
            }.get(health['status'], '❓')

            print(f"  {status_emoji} {service}: {health['status']} (Error rate: {health['error_rate']:.1f}%)")

    # Recommendations summary
    print("\n💡 RECOMMENDATIONS:")
    print("-" * 40)
    recommendations = audit_results['recommendations']

    if not recommendations:
        print("✅ No specific recommendations generated")
    else:
        p0_count = sum(1 for r in recommendations if r['priority'] == 'P0')
        p1_count = sum(1 for r in recommendations if r['priority'] == 'P1')

        print(f"🔴 P0 (Critical): {p0_count} issues")
        print(f"🟡 P1 (High): {p1_count} issues")

        print("\nTop Priority Issues:")
        for rec in recommendations[:5]:  # Show top 5
            priority_emoji = '🔴' if rec['priority'] == 'P0' else '🟡'
            print(f"  {priority_emoji} [{rec['priority']}] {rec['category']}: {rec['issue']}")

    print("\n" + "="*80)

async def main():
    """Main function to run the GCP logs audit"""
    parser = argparse.ArgumentParser(description='GCP Logs Audit for Netra Apex Platform')
    parser.add_argument('--project', default='netra-staging', help='GCP project ID')
    parser.add_argument('--hours', type=int, default=24, help='Hours back to analyze logs')
    parser.add_argument('--service', choices=['backend', 'auth', 'frontend'], help='Specific service to analyze')
    parser.add_argument('--severity', choices=['DEFAULT', 'DEBUG', 'INFO', 'NOTICE', 'WARNING', 'ERROR', 'CRITICAL'], help='Minimum log severity')
    parser.add_argument('--output', default='gcp_logs_audit_report.json', help='Output file for detailed results')
    parser.add_argument('--summary-only', action='store_true', help='Show only summary, do not save detailed report')

    args = parser.parse_args()

    try:
        auditor = GCPLogsAuditor(args.project)
        audit_results = await auditor.run_comprehensive_audit(
            hours_back=args.hours,
            service=args.service,
            severity=args.severity
        )

        # Print summary
        print_audit_summary(audit_results)

        # Save detailed results
        if not args.summary_only:
            with open(args.output, 'w') as f:
                json.dump(audit_results, f, indent=2, default=str)
            print(f"\n📄 Detailed audit report saved to: {args.output}")

        # Exit with error code if critical issues found
        critical_recommendations = [r for r in audit_results['recommendations'] if r['priority'] == 'P0']
        if critical_recommendations:
            print(f"\n🚨 {len(critical_recommendations)} critical issues found!")
            sys.exit(1)
        else:
            print("\n✅ No critical issues detected")
            sys.exit(0)

    except Exception as e:
        print(f"❌ Error running audit: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())