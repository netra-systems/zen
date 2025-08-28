#!/usr/bin/env python3
"""
Docker Log Introspection and Issue Audit Tool
Analyzes Docker container logs to identify and categorize issues for remediation
"""

import subprocess
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import sys
from pathlib import Path

class DockerLogIntrospector:
    """Analyzes Docker logs to identify issues requiring remediation"""
    
    # Issue patterns with severity levels
    ISSUE_PATTERNS = {
        'CRITICAL': [
            (r'FATAL|PANIC|EMERGENCY', 'Fatal error detected'),
            (r'Connection refused|Connection reset', 'Connection failure'),
            (r'database.*down|database.*failed', 'Database connectivity issue'),
            (r'out of memory|OOM', 'Memory exhaustion'),
            (r'disk.*full|no space left', 'Disk space issue'),
            (r'segmentation fault|core dumped', 'Application crash'),
        ],
        'HIGH': [
            (r'ERROR|Exception|Traceback', 'Application error'),
            (r'authentication.*failed|unauthorized|403|401', 'Authentication issue'),
            (r'timeout|timed out', 'Timeout error'),
            (r'failed to connect|connection failed', 'Network connectivity issue'),
            (r'invalid.*config|configuration.*error', 'Configuration error'),
            (r'SSL.*error|certificate.*invalid', 'SSL/TLS issue'),
        ],
        'MEDIUM': [
            (r'WARNING|WARN', 'Warning condition'),
            (r'deprecated|deprecation', 'Deprecated feature usage'),
            (r'retry|retrying', 'Operation retry detected'),
            (r'slow query|performance', 'Performance issue'),
            (r'rate limit|throttled', 'Rate limiting detected'),
            (r'validation.*failed|invalid.*input', 'Validation error'),
        ],
        'LOW': [
            (r'INFO.*failed|INFO.*error', 'Informational error'),
            (r'cache miss|cache.*expired', 'Cache issue'),
            (r'queue.*full|backlog', 'Queue congestion'),
            (r'metrics.*missing|telemetry.*failed', 'Monitoring issue'),
        ]
    }
    
    def __init__(self):
        self.issues = defaultdict(list)
        self.container_stats = {}
        
    def get_running_containers(self) -> List[Dict[str, str]]:
        """Get list of running Docker containers"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{json .}}'],
                capture_output=True,
                text=True,
                check=True
            )
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    container = json.loads(line)
                    containers.append({
                        'id': container.get('ID', ''),
                        'name': container.get('Names', ''),
                        'image': container.get('Image', ''),
                        'status': container.get('Status', ''),
                        'ports': container.get('Ports', '')
                    })
            
            return containers
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting Docker containers: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []
    
    def analyze_container_logs(self, container_id: str, container_name: str, hours_back: int = 24) -> Dict[str, Any]:
        """Analyze logs from a specific container"""
        issues_found = defaultdict(list)
        
        try:
            # Get logs from the last N hours
            since = (datetime.now() - timedelta(hours=hours_back)).isoformat()
            
            result = subprocess.run(
                ['docker', 'logs', '--since', since, '--timestamps', container_id],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            logs = result.stdout + result.stderr
            log_lines = logs.split('\n')
            
            # Analyze each log line
            for line_num, line in enumerate(log_lines, 1):
                if not line.strip():
                    continue
                    
                # Check against issue patterns
                for severity, patterns in self.ISSUE_PATTERNS.items():
                    for pattern, description in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Extract timestamp if present
                            timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2}T[\d:]+\.\d+Z?)\s+(.+)', line)
                            if timestamp_match:
                                timestamp = timestamp_match.group(1)
                                log_content = timestamp_match.group(2)
                            else:
                                timestamp = 'Unknown'
                                log_content = line
                            
                            issues_found[severity].append({
                                'container': container_name,
                                'container_id': container_id,
                                'severity': severity,
                                'issue_type': description,
                                'pattern_matched': pattern,
                                'timestamp': timestamp,
                                'line_number': line_num,
                                'log_excerpt': log_content[:500],  # Limit excerpt length
                                'full_line': line
                            })
                            break  # Only match first pattern per line
            
            # Get container resource stats
            stats_result = subprocess.run(
                ['docker', 'stats', container_id, '--no-stream', '--format', '{{json .}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if stats_result.stdout:
                stats = json.loads(stats_result.stdout.strip())
                self.container_stats[container_name] = {
                    'cpu_usage': stats.get('CPUPerc', 'N/A'),
                    'memory_usage': stats.get('MemUsage', 'N/A'),
                    'memory_percent': stats.get('MemPerc', 'N/A'),
                    'network_io': stats.get('NetIO', 'N/A'),
                    'block_io': stats.get('BlockIO', 'N/A')
                }
                
                # Check for resource-related issues
                if stats.get('MemPerc', '').replace('%', ''):
                    try:
                        mem_percent = float(stats.get('MemPerc', '0%').replace('%', ''))
                        if mem_percent > 90:
                            issues_found['HIGH'].append({
                                'container': container_name,
                                'container_id': container_id,
                                'severity': 'HIGH',
                                'issue_type': 'High memory usage',
                                'pattern_matched': 'resource_check',
                                'timestamp': datetime.now().isoformat(),
                                'line_number': 0,
                                'log_excerpt': f"Memory usage at {mem_percent}%",
                                'full_line': f"Resource check: Memory usage at {mem_percent}%"
                            })
                    except:
                        pass
                        
        except subprocess.TimeoutExpired:
            print(f"Timeout analyzing logs for container {container_name}")
        except Exception as e:
            print(f"Error analyzing container {container_name}: {e}")
            
        return dict(issues_found)
    
    def generate_audit_report(self) -> Dict[str, Any]:
        """Generate comprehensive audit report"""
        report = {
            'audit_timestamp': datetime.now().isoformat(),
            'summary': {
                'total_issues': 0,
                'critical_count': 0,
                'high_count': 0,
                'medium_count': 0,
                'low_count': 0,
                'containers_analyzed': 0,
                'containers_with_issues': set()
            },
            'issues_by_severity': defaultdict(list),
            'issues_by_container': defaultdict(lambda: defaultdict(list)),
            'issue_categories': defaultdict(int),
            'container_stats': self.container_stats,
            'remediation_priorities': []
        }
        
        # Aggregate all issues
        for severity, issue_list in self.issues.items():
            report['issues_by_severity'][severity] = issue_list
            report['summary'][f'{severity.lower()}_count'] = len(issue_list)
            report['summary']['total_issues'] += len(issue_list)
            
            for issue in issue_list:
                container = issue['container']
                report['summary']['containers_with_issues'].add(container)
                report['issues_by_container'][container][severity].append(issue)
                report['issue_categories'][issue['issue_type']] += 1
        
        report['summary']['containers_with_issues'] = list(report['summary']['containers_with_issues'])
        
        # Determine remediation priorities
        priority_score = {
            'CRITICAL': 1000,
            'HIGH': 100,
            'MEDIUM': 10,
            'LOW': 1
        }
        
        container_scores = {}
        for container, severities in report['issues_by_container'].items():
            score = sum(
                priority_score[sev] * len(issues)
                for sev, issues in severities.items()
            )
            container_scores[container] = score
        
        # Sort containers by priority score
        sorted_containers = sorted(
            container_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for container, score in sorted_containers:
            if score > 0:
                report['remediation_priorities'].append({
                    'container': container,
                    'priority_score': score,
                    'issues': {
                        sev: len(issues)
                        for sev, issues in report['issues_by_container'][container].items()
                    }
                })
        
        return dict(report)
    
    def run_introspection(self, hours_back: int = 24) -> Dict[str, Any]:
        """Run complete Docker log introspection"""
        print("=" * 80)
        print("DOCKER LOG INTROSPECTION - ISSUE AUDIT")
        print("=" * 80)
        print(f"Analyzing logs from the last {hours_back} hours...")
        print()
        
        # Get running containers
        containers = self.get_running_containers()
        
        if not containers:
            print("No running Docker containers found.")
            return {'error': 'No containers found'}
        
        print(f"Found {len(containers)} running containers:")
        for container in containers:
            print(f"  - {container['name']} ({container['image']})")
        print()
        
        # Analyze each container
        for container in containers:
            print(f"Analyzing container: {container['name']}...")
            container_issues = self.analyze_container_logs(
                container['id'],
                container['name'],
                hours_back
            )
            
            # Merge issues
            for severity, issues in container_issues.items():
                self.issues[severity].extend(issues)
        
        # Generate audit report
        report = self.generate_audit_report()
        report['summary']['containers_analyzed'] = len(containers)
        
        # Display summary
        print("\n" + "=" * 80)
        print("AUDIT SUMMARY")
        print("=" * 80)
        print(f"Total Issues Found: {report['summary']['total_issues']}")
        print(f"  - CRITICAL: {report['summary']['critical_count']}")
        print(f"  - HIGH: {report['summary']['high_count']}")
        print(f"  - MEDIUM: {report['summary']['medium_count']}")
        print(f"  - LOW: {report['summary']['low_count']}")
        print(f"\nContainers Analyzed: {report['summary']['containers_analyzed']}")
        print(f"Containers with Issues: {len(report['summary']['containers_with_issues'])}")
        
        if report['issue_categories']:
            print("\nIssue Categories:")
            for category, count in sorted(report['issue_categories'].items(), key=lambda x: x[1], reverse=True):
                print(f"  - {category}: {count}")
        
        if report['remediation_priorities']:
            print("\nRemediation Priorities (by container):")
            for priority in report['remediation_priorities'][:10]:  # Show top 10
                print(f"  - {priority['container']} (Score: {priority['priority_score']})")
                for sev, count in priority['issues'].items():
                    if count > 0:
                        print(f"      {sev}: {count}")
        
        # Save detailed report
        report_path = Path('docker_audit_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nDetailed report saved to: {report_path}")
        
        # Generate remediation plan
        self.generate_remediation_plan(report)
        
        return report
    
    def generate_remediation_plan(self, report: Dict[str, Any]):
        """Generate multi-agent remediation plan"""
        plan_path = Path('remediation_plan.json')
        
        remediation_plan = {
            'generated_at': datetime.now().isoformat(),
            'agent_assignments': [],
            'immediate_actions': [],
            'scheduled_tasks': []
        }
        
        # Assign agents based on issue types
        agent_mapping = {
            'Database connectivity issue': 'database_remediation_agent',
            'Authentication issue': 'auth_remediation_agent',
            'Configuration error': 'config_remediation_agent',
            'SSL/TLS issue': 'security_remediation_agent',
            'Memory exhaustion': 'resource_optimization_agent',
            'High memory usage': 'resource_optimization_agent',
            'Application error': 'error_remediation_agent',
            'Fatal error detected': 'critical_remediation_agent',
            'Connection failure': 'network_remediation_agent',
            'Performance issue': 'performance_optimization_agent'
        }
        
        # Create agent assignments
        for issue_type, count in report['issue_categories'].items():
            agent = agent_mapping.get(issue_type, 'general_remediation_agent')
            
            # Find all issues of this type
            type_issues = []
            for severity, issues in report['issues_by_severity'].items():
                type_issues.extend([
                    issue for issue in issues
                    if issue['issue_type'] == issue_type
                ])
            
            if type_issues:
                remediation_plan['agent_assignments'].append({
                    'agent_type': agent,
                    'issue_type': issue_type,
                    'severity': max(issue['severity'] for issue in type_issues),
                    'issue_count': count,
                    'affected_containers': list(set(issue['container'] for issue in type_issues)),
                    'sample_issues': type_issues[:3]  # Include sample issues for context
                })
        
        # Prioritize immediate actions for CRITICAL issues
        for issue in report['issues_by_severity'].get('CRITICAL', []):
            remediation_plan['immediate_actions'].append({
                'action': 'IMMEDIATE_REMEDIATION',
                'container': issue['container'],
                'issue': issue['issue_type'],
                'timestamp': issue['timestamp'],
                'assigned_agent': agent_mapping.get(issue['issue_type'], 'critical_remediation_agent')
            })
        
        # Schedule tasks for other issues
        for severity in ['HIGH', 'MEDIUM', 'LOW']:
            for issue in report['issues_by_severity'].get(severity, [])[:10]:  # Limit per severity
                remediation_plan['scheduled_tasks'].append({
                    'priority': severity,
                    'container': issue['container'],
                    'issue': issue['issue_type'],
                    'scheduled_for': (
                        datetime.now() + 
                        timedelta(minutes=5 if severity == 'HIGH' else 30 if severity == 'MEDIUM' else 60)
                    ).isoformat(),
                    'assigned_agent': agent_mapping.get(issue['issue_type'], 'general_remediation_agent')
                })
        
        # Save remediation plan
        with open(plan_path, 'w') as f:
            json.dump(remediation_plan, f, indent=2, default=str)
        
        print(f"\nRemediation plan saved to: {plan_path}")
        print(f"Agent Assignments: {len(remediation_plan['agent_assignments'])}")
        print(f"Immediate Actions Required: {len(remediation_plan['immediate_actions'])}")
        print(f"Scheduled Tasks: {len(remediation_plan['scheduled_tasks'])}")
        
        return remediation_plan


def main():
    """Main execution function"""
    introspector = DockerLogIntrospector()
    
    # Run introspection (default: last 24 hours)
    hours_back = 24
    if len(sys.argv) > 1:
        try:
            hours_back = int(sys.argv[1])
        except:
            print(f"Invalid hours parameter, using default: {hours_back}")
    
    report = introspector.run_introspection(hours_back)
    
    if 'error' not in report:
        print("\n" + "=" * 80)
        print("INTROSPECTION COMPLETE")
        print("=" * 80)
        print("Next Steps:")
        print("1. Review docker_audit_report.json for detailed findings")
        print("2. Execute remediation_plan.json with multi-agent teams")
        print("3. Monitor container health metrics")
        print("4. Re-run introspection after remediation to verify fixes")
    
    return 0 if report.get('summary', {}).get('total_issues', 0) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())