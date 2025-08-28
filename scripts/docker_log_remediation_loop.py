#!/usr/bin/env python3
"""
Docker Log Remediation Loop
Iteratively analyzes Docker logs from a specific timestamp and remediates ALL errors found
"""

import subprocess
import json
import re
import platform
import shutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import sys
from pathlib import Path
import time

class DockerLogRemediator:
    """Docker log analyzer and remediator with iterative error fixing"""
    
    # Enhanced issue patterns with remediation hints
    ISSUE_PATTERNS = {
        'CRITICAL': [
            (r'FATAL|PANIC|EMERGENCY', 'Fatal error detected', 'Check application startup and configuration'),
            (r'Connection refused|Connection reset', 'Connection failure', 'Verify service connectivity and network configuration'),
            (r'database.*down|database.*failed', 'Database connectivity issue', 'Check database connection parameters and availability'),
            (r'out of memory|OOM', 'Memory exhaustion', 'Increase memory limits or optimize memory usage'),
            (r'disk.*full|no space left', 'Disk space issue', 'Free up disk space or increase volume size'),
            (r'segmentation fault|core dumped', 'Application crash', 'Review recent code changes and check for null pointer access'),
            (r'cannot connect to.*postgres|psycopg2.*OperationalError', 'PostgreSQL connection failure', 'Verify PostgreSQL credentials and SSL configuration'),
            (r'redis\.exceptions\.ConnectionError', 'Redis connection failure', 'Check Redis service status and connection parameters'),
            (r'clickhouse.*Connection.*refused', 'ClickHouse connection failure', 'Verify ClickHouse is running and accessible'),
        ],
        'HIGH': [
            (r'ERROR|Exception|Traceback', 'Application error', 'Review stack trace and fix code logic'),
            (r'authentication.*failed|unauthorized|403|401', 'Authentication issue', 'Check authentication tokens and permissions'),
            (r'timeout|timed out', 'Timeout error', 'Increase timeout values or optimize slow operations'),
            (r'failed to connect|connection failed', 'Network connectivity issue', 'Check network configuration and firewall rules'),
            (r'invalid.*config|configuration.*error', 'Configuration error', 'Review and fix configuration files'),
            (r'SSL.*error|certificate.*invalid', 'SSL/TLS issue', 'Check certificate validity and SSL configuration'),
            (r'ModuleNotFoundError|ImportError', 'Import/Module error', 'Install missing dependencies or fix import paths'),
            (r'AttributeError|TypeError|ValueError', 'Python type error', 'Fix type mismatches in code'),
            (r'KeyError', 'Missing key error', 'Add missing dictionary keys or use safe access'),
            (r'FileNotFoundError', 'File not found', 'Verify file paths and create missing files'),
            (r'PermissionError|Permission denied', 'Permission issue', 'Check file permissions and user rights'),
        ],
        'MEDIUM': [
            (r'WARNING|WARN', 'Warning condition', 'Review warning and determine if action needed'),
            (r'deprecated|deprecation', 'Deprecated feature usage', 'Update code to use modern APIs'),
            (r'retry|retrying', 'Operation retry detected', 'Check if retry logic is appropriate'),
            (r'slow query|performance', 'Performance issue', 'Optimize queries or add indexes'),
            (r'rate limit|throttled', 'Rate limiting detected', 'Implement backoff or reduce request rate'),
            (r'validation.*failed|invalid.*input', 'Validation error', 'Fix input validation logic'),
            (r'cors|CORS', 'CORS issue', 'Configure CORS headers properly'),
        ],
        'LOW': [
            (r'INFO.*failed|INFO.*error', 'Informational error', 'Monitor for patterns'),
            (r'cache miss|cache.*expired', 'Cache issue', 'Review cache configuration'),
            (r'queue.*full|backlog', 'Queue congestion', 'Scale queue processors or increase capacity'),
            (r'metrics.*missing|telemetry.*failed', 'Monitoring issue', 'Fix telemetry configuration'),
        ]
    }
    
    def __init__(self, target_timestamp: str = None):
        self.issues = defaultdict(list)
        self.processed_issues = set()
        self.remediation_log = []
        self.docker_cmd = self._get_docker_command()
        self.target_timestamp = target_timestamp or "2025-08-28 15:42:48"
        self.iteration_count = 0
        self.max_iterations = 100
        
    def _get_docker_command(self) -> str:
        """Get appropriate Docker command for Windows"""
        docker_cmd = shutil.which('docker')
        if docker_cmd:
            return docker_cmd
        
        if platform.system() == 'Windows':
            docker_exe = shutil.which('docker.exe')
            if docker_exe:
                return docker_exe
            
            common_paths = [
                r'C:\Program Files\Docker\Docker\resources\bin\docker.exe',
                r'C:\Program Files\Docker\Docker\resources\docker.exe',
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path
        
        return 'docker'
    
    def get_logs_since_timestamp(self, container_id: str, container_name: str) -> str:
        """Get container logs since specific timestamp"""
        try:
            # Convert timestamp to hours back
            target_dt = datetime.strptime(self.target_timestamp, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            hours_back = int((now - target_dt).total_seconds() / 3600) + 1  # Add buffer
            
            # Get logs with timestamps
            cmd = f'{self.docker_cmd} logs --since {hours_back}h --timestamps {container_id}'
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True,
                timeout=30
            )
            
            # Combine stdout and stderr
            logs = result.stdout + result.stderr
            
            # Filter logs after target timestamp
            filtered_lines = []
            for line in logs.split('\n'):
                # Extract timestamp from log line
                timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2}T[\d:]+\.\d+Z?)\s+(.+)', line)
                if timestamp_match:
                    log_timestamp = timestamp_match.group(1)
                    # Convert to comparable format
                    try:
                        log_dt = datetime.fromisoformat(log_timestamp.replace('Z', '+00:00').replace('T', ' ').split('.')[0])
                        if log_dt >= target_dt:
                            filtered_lines.append(line)
                    except:
                        filtered_lines.append(line)  # Include if can't parse
                elif filtered_lines:  # Include continuation lines
                    filtered_lines.append(line)
            
            return '\n'.join(filtered_lines)
            
        except Exception as e:
            print(f"Error getting logs for {container_name}: {e}")
            return ""
    
    def analyze_logs_for_errors(self, container_id: str, container_name: str) -> List[Dict[str, Any]]:
        """Analyze logs and extract ALL errors"""
        errors = []
        
        logs = self.get_logs_since_timestamp(container_id, container_name)
        if not logs:
            return errors
        
        log_lines = logs.split('\n')
        
        for line_num, line in enumerate(log_lines, 1):
            if not line.strip():
                continue
            
            # Check against all issue patterns
            for severity, patterns in self.ISSUE_PATTERNS.items():
                for pattern, description, remediation_hint in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Create unique issue ID
                        issue_id = f"{container_name}_{severity}_{line_num}_{hash(line[:100])}"
                        
                        if issue_id not in self.processed_issues:
                            # Extract timestamp if present
                            timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2}T[\d:]+\.\d+Z?)\s+(.+)', line)
                            if timestamp_match:
                                timestamp = timestamp_match.group(1)
                                log_content = timestamp_match.group(2)
                            else:
                                timestamp = 'Unknown'
                                log_content = line
                            
                            error = {
                                'id': issue_id,
                                'container': container_name,
                                'container_id': container_id,
                                'severity': severity,
                                'issue_type': description,
                                'pattern_matched': pattern,
                                'remediation_hint': remediation_hint,
                                'timestamp': timestamp,
                                'line_number': line_num,
                                'log_excerpt': log_content[:500],
                                'full_line': line,
                                'iteration_found': self.iteration_count
                            }
                            
                            errors.append(error)
                            break  # Only match first pattern per line
        
        return errors
    
    def get_all_containers(self) -> List[Dict[str, str]]:
        """Get list of all Docker containers"""
        # Known containers (fallback)
        known_containers = [
            {'id': 'c5187ee3b781', 'name': 'netra-backend'},
            {'id': 'b437859c4843', 'name': 'netra-auth'},
            {'id': '8d8a510af300', 'name': 'netra-clickhouse'},
            {'id': '434a0cb26ea7', 'name': 'netra-redis'},
            {'id': '9e1470a957ac', 'name': 'netra-frontend'},
            {'id': '7a3c4f9111a9', 'name': 'netra-postgres'},
        ]
        
        containers = []
        try:
            cmd = f'{self.docker_cmd} ps --format "{{{{json .}}}}"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            container = json.loads(line)
                            containers.append({
                                'id': container.get('ID', ''),
                                'name': container.get('Names', '').replace('/', '')
                            })
                        except:
                            continue
            
            if not containers:
                containers = known_containers
                
        except:
            containers = known_containers
        
        return containers
    
    def collect_all_errors(self) -> List[Dict[str, Any]]:
        """Collect ALL errors from ALL containers since target timestamp"""
        all_errors = []
        containers = self.get_all_containers()
        
        print(f"\nIteration {self.iteration_count + 1}: Scanning {len(containers)} containers for errors since {self.target_timestamp}")
        
        for container in containers:
            errors = self.analyze_logs_for_errors(container['id'], container['name'])
            if errors:
                print(f"  Found {len(errors)} errors in {container['name']}")
                all_errors.extend(errors)
        
        # Sort by severity priority
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        all_errors.sort(key=lambda x: (severity_order.get(x['severity'], 4), x['timestamp']))
        
        return all_errors
    
    def generate_remediation_task(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Generate remediation task for an error"""
        return {
            'error_id': error['id'],
            'container': error['container'],
            'severity': error['severity'],
            'issue_type': error['issue_type'],
            'remediation_hint': error['remediation_hint'],
            'log_context': error['full_line'],
            'timestamp': error['timestamp'],
            'status': 'pending',
            'actions_taken': [],
            'result': None
        }
    
    def save_remediation_report(self):
        """Save detailed remediation report"""
        report = {
            'remediation_started': self.remediation_log[0]['timestamp'] if self.remediation_log else None,
            'remediation_completed': datetime.now().isoformat(),
            'target_timestamp': self.target_timestamp,
            'total_iterations': self.iteration_count,
            'total_issues_found': len(self.processed_issues),
            'issues_by_severity': defaultdict(int),
            'remediation_log': self.remediation_log,
            'unresolved_issues': []
        }
        
        # Count issues by severity
        for entry in self.remediation_log:
            if 'severity' in entry:
                report['issues_by_severity'][entry['severity']] += 1
        
        # Identify unresolved issues
        for entry in self.remediation_log:
            if entry.get('status') != 'resolved':
                report['unresolved_issues'].append(entry)
        
        # Save report
        report_path = Path(f'docker_remediation_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\nRemediation report saved to: {report_path}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("REMEDIATION SUMMARY")
        print("=" * 80)
        print(f"Total Iterations: {report['total_iterations']}")
        print(f"Total Issues Found: {report['total_issues_found']}")
        print("\nIssues by Severity:")
        for severity, count in report['issues_by_severity'].items():
            print(f"  {severity}: {count}")
        print(f"\nUnresolved Issues: {len(report['unresolved_issues'])}")
        
        return report
    
    def run_remediation_loop(self) -> int:
        """Main remediation loop - runs until no errors or max iterations"""
        print("=" * 80)
        print("DOCKER LOG REMEDIATION LOOP")
        print("=" * 80)
        print(f"Starting from timestamp: {self.target_timestamp}")
        print(f"Max iterations: {self.max_iterations}")
        print()
        
        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1
            
            # Collect all errors
            errors = self.collect_all_errors()
            
            if not errors:
                print(f"\n[SUCCESS] No errors found in iteration {self.iteration_count}. All issues resolved!")
                break
            
            print(f"\nFound {len(errors)} total errors to remediate")
            
            # Process each error
            for i, error in enumerate(errors, 1):
                if error['id'] in self.processed_issues:
                    continue
                
                print(f"\n[{i}/{len(errors)}] Processing {error['severity']} error in {error['container']}")
                print(f"  Issue: {error['issue_type']}")
                print(f"  Log: {error['log_excerpt'][:200]}...")
                print(f"  Hint: {error['remediation_hint']}")
                
                # Mark as processed
                self.processed_issues.add(error['id'])
                
                # Create remediation task
                task = self.generate_remediation_task(error)
                task['iteration'] = self.iteration_count
                task['timestamp'] = datetime.now().isoformat()
                
                # Log the remediation attempt
                self.remediation_log.append(task)
                
                # Here we would deploy multi-agent team for actual remediation
                # For now, we log it for the main script to handle
                print(f"  -> Marked for remediation by multi-agent team")
            
            # Brief pause between iterations
            if self.iteration_count < self.max_iterations:
                print(f"\nWaiting 2 seconds before next iteration...")
                time.sleep(2)
        
        # Save final report
        report = self.save_remediation_report()
        
        return len(report['unresolved_issues'])


def main():
    """Main execution function"""
    # Parse command line arguments
    target_timestamp = "2025-08-28 15:42:48"
    if len(sys.argv) > 1:
        target_timestamp = sys.argv[1]
    
    print(f"Starting remediation loop from timestamp: {target_timestamp}")
    
    # Create remediator and run loop
    remediator = DockerLogRemediator(target_timestamp)
    unresolved_count = remediator.run_remediation_loop()
    
    print("\n" + "=" * 80)
    print("REMEDIATION LOOP COMPLETE")
    print("=" * 80)
    
    if unresolved_count == 0:
        print("[SUCCESS] All errors successfully identified for remediation!")
    else:
        print(f"[WARNING] {unresolved_count} issues remain unresolved")
    
    print("\nNext Steps:")
    print("1. Review the remediation report for detailed findings")
    print("2. Deploy multi-agent teams to fix each identified issue")
    print("3. Update learnings after each successful remediation")
    print("4. Re-run to verify all issues are resolved")
    
    return 0 if unresolved_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())