#!/usr/bin/env python3
"""
Comprehensive Error Hunter - Captures ALL errors, warnings, and issues from Docker logs
Runs iteratively and remediates each error with multi-agent teams
"""

import subprocess
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict
import sys
from pathlib import Path
import hashlib
import time

class ComprehensiveErrorHunter:
    """Hunt down EVERY error in backend logs and coordinate remediation"""
    
    def __init__(self, since_timestamp: str = "2025-08-28 15:42:48"):
        self.since_timestamp = since_timestamp
        self.all_issues = []
        self.processed_signatures = set()
        self.remediation_log = []
        self.iteration = 0
        self.max_iterations = 100
        
    def get_backend_logs_raw(self) -> str:
        """Get raw backend logs without filtering"""
        try:
            # Get backend container ID
            cmd = 'docker ps --filter "name=netra-backend" --format "{{.ID}}"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding='utf-8', errors='replace')
            container_id = result.stdout.strip()
            
            if not container_id:
                print("Backend container not found")
                return ""
            
            print(f"Found backend container: {container_id}")
            
            # Get ALL logs (no time filter initially to ensure we get everything)
            cmd = f'docker logs --timestamps {container_id} 2>&1'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=120, encoding='utf-8', errors='replace')
            
            return result.stdout
        except Exception as e:
            print(f"Error getting backend logs: {e}")
            return ""
    
    def aggressive_error_detection(self, logs: str) -> List[Dict[str, Any]]:
        """Aggressively detect ALL errors, warnings, and issues"""
        issues = []
        log_lines = logs.split('\n')
        
        # Filter by timestamp
        target_dt = datetime.strptime(self.since_timestamp, "%Y-%m-%d %H:%M:%S")
        
        # Much more aggressive patterns - capture EVERYTHING that could be an issue
        patterns = [
            # Critical/Fatal
            (r'CRITICAL', 'CRITICAL', 'Critical Issue'),
            (r'FATAL', 'CRITICAL', 'Fatal Error'),
            (r'PANIC', 'CRITICAL', 'Panic'),
            (r'EMERGENCY', 'CRITICAL', 'Emergency'),
            
            # Errors - be very aggressive
            (r'ERROR', 'HIGH', 'Error'),
            (r'Error:', 'HIGH', 'Error Message'),
            (r'error:', 'HIGH', 'Error Message'),
            (r'error\s', 'HIGH', 'Error Mention'),
            (r'Exception', 'HIGH', 'Exception'),
            (r'exception', 'HIGH', 'Exception'),
            (r'Traceback', 'CRITICAL', 'Python Traceback'),
            (r'traceback', 'HIGH', 'Traceback'),
            
            # Python specific errors
            (r'AttributeError', 'HIGH', 'AttributeError'),
            (r'KeyError', 'HIGH', 'KeyError'),
            (r'TypeError', 'HIGH', 'TypeError'),
            (r'ValueError', 'HIGH', 'ValueError'),
            (r'NameError', 'HIGH', 'NameError'),
            (r'ImportError', 'CRITICAL', 'ImportError'),
            (r'ModuleNotFoundError', 'CRITICAL', 'ModuleNotFoundError'),
            (r'FileNotFoundError', 'HIGH', 'FileNotFoundError'),
            (r'PermissionError', 'HIGH', 'PermissionError'),
            (r'ConnectionError', 'HIGH', 'ConnectionError'),
            (r'TimeoutError', 'MEDIUM', 'TimeoutError'),
            (r'RuntimeError', 'HIGH', 'RuntimeError'),
            (r'IndexError', 'HIGH', 'IndexError'),
            (r'ZeroDivisionError', 'HIGH', 'ZeroDivisionError'),
            (r'OverflowError', 'HIGH', 'OverflowError'),
            (r'RecursionError', 'CRITICAL', 'RecursionError'),
            (r'MemoryError', 'CRITICAL', 'MemoryError'),
            (r'SystemError', 'CRITICAL', 'SystemError'),
            
            # Failed/Failure
            (r'[Ff]ailed', 'HIGH', 'Failed Operation'),
            (r'[Ff]ailure', 'HIGH', 'Failure'),
            (r'FAILED', 'HIGH', 'Failed'),
            (r'FAIL', 'HIGH', 'Fail'),
            (r'fail to', 'HIGH', 'Failed To'),
            (r'unable to', 'MEDIUM', 'Unable To'),
            (r'could not', 'MEDIUM', 'Could Not'),
            (r'cannot', 'MEDIUM', 'Cannot'),
            (r"can't", 'MEDIUM', 'Cannot'),
            (r"couldn't", 'MEDIUM', 'Could Not'),
            (r"won't", 'MEDIUM', 'Will Not'),
            (r'not found', 'MEDIUM', 'Not Found'),
            (r'missing', 'MEDIUM', 'Missing'),
            
            # Connection issues
            (r'Connection refused', 'HIGH', 'Connection Refused'),
            (r'Connection reset', 'HIGH', 'Connection Reset'),
            (r'Connection timeout', 'MEDIUM', 'Connection Timeout'),
            (r'Connection lost', 'HIGH', 'Connection Lost'),
            (r'disconnect', 'MEDIUM', 'Disconnect'),
            (r'refused', 'HIGH', 'Refused'),
            (r'rejected', 'HIGH', 'Rejected'),
            (r'denied', 'HIGH', 'Denied'),
            
            # Warnings
            (r'WARNING', 'MEDIUM', 'Warning'),
            (r'WARN', 'MEDIUM', 'Warning'),
            (r'warning:', 'MEDIUM', 'Warning'),
            (r'deprecated', 'LOW', 'Deprecated'),
            (r'deprecation', 'LOW', 'Deprecation'),
            
            # Database
            (r'database', 'HIGH', 'Database Issue'),
            (r'postgres', 'HIGH', 'PostgreSQL Issue'),
            (r'psycopg', 'HIGH', 'PostgreSQL Driver Issue'),
            (r'redis', 'HIGH', 'Redis Issue'),
            (r'clickhouse', 'HIGH', 'ClickHouse Issue'),
            (r'SQL', 'MEDIUM', 'SQL Issue'),
            
            # Performance
            (r'timeout', 'MEDIUM', 'Timeout'),
            (r'timed out', 'MEDIUM', 'Timed Out'),
            (r'slow', 'LOW', 'Slow Performance'),
            (r'performance', 'LOW', 'Performance Issue'),
            (r'bottleneck', 'MEDIUM', 'Bottleneck'),
            (r'lag', 'LOW', 'Lag'),
            (r'delay', 'LOW', 'Delay'),
            
            # Security
            (r'unauthorized', 'HIGH', 'Unauthorized'),
            (r'forbidden', 'HIGH', 'Forbidden'),
            (r'authentication', 'HIGH', 'Authentication Issue'),
            (r'permission', 'HIGH', 'Permission Issue'),
            (r'access denied', 'HIGH', 'Access Denied'),
            (r'invalid token', 'HIGH', 'Invalid Token'),
            (r'expired', 'MEDIUM', 'Expired'),
            
            # System
            (r'crash', 'CRITICAL', 'Crash'),
            (r'abort', 'CRITICAL', 'Abort'),
            (r'kill', 'HIGH', 'Kill'),
            (r'terminate', 'HIGH', 'Terminate'),
            (r'shutdown', 'MEDIUM', 'Shutdown'),
            (r'restart', 'MEDIUM', 'Restart'),
            (r'out of memory', 'CRITICAL', 'Out of Memory'),
            (r'memory leak', 'HIGH', 'Memory Leak'),
            (r'disk full', 'CRITICAL', 'Disk Full'),
            (r'no space', 'CRITICAL', 'No Space'),
            
            # Application specific
            (r'agent.*error', 'HIGH', 'Agent Error'),
            (r'thread.*error', 'HIGH', 'Thread Error'),
            (r'task.*error', 'HIGH', 'Task Error'),
            (r'websocket.*error', 'MEDIUM', 'WebSocket Error'),
            (r'api.*error', 'HIGH', 'API Error'),
            (r'request.*error', 'MEDIUM', 'Request Error'),
            (r'response.*error', 'MEDIUM', 'Response Error'),
            
            # Generic problems
            (r'problem', 'MEDIUM', 'Problem'),
            (r'issue', 'MEDIUM', 'Issue'),
            (r'bug', 'HIGH', 'Bug'),
            (r'broken', 'HIGH', 'Broken'),
            (r'corrupt', 'CRITICAL', 'Corrupt'),
            (r'invalid', 'MEDIUM', 'Invalid'),
            (r'unexpected', 'MEDIUM', 'Unexpected'),
            (r'unhandled', 'HIGH', 'Unhandled'),
            (r'uncaught', 'HIGH', 'Uncaught'),
            (r'undefined', 'MEDIUM', 'Undefined'),
            (r'null', 'MEDIUM', 'Null'),
            (r'NoneType', 'HIGH', 'NoneType'),
        ]
        
        # Process each line
        for line_num, line in enumerate(log_lines, 1):
            if not line.strip():
                continue
            
            # Extract timestamp
            timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[\.\d]*Z?)\s*(.*)$', line)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                log_content = timestamp_match.group(2)
                
                # Check timestamp
                try:
                    log_dt = datetime.strptime(timestamp_str[:19].replace('T', ' '), "%Y-%m-%d %H:%M:%S")
                    if log_dt < target_dt:
                        continue
                except:
                    pass
            else:
                continue  # Skip lines without timestamp
            
            # Check ALL patterns
            for pattern, severity, issue_type in patterns:
                if re.search(pattern, log_content, re.IGNORECASE):
                    # Create signature
                    sig = self._create_signature(issue_type, log_content)
                    
                    if sig not in self.processed_signatures:
                        issue = {
                            'line_number': line_num,
                            'timestamp': timestamp_str,
                            'severity': severity,
                            'issue_type': issue_type,
                            'pattern': pattern,
                            'log_line': line,
                            'log_content': log_content[:500],
                            'signature': sig,
                            'iteration_found': self.iteration
                        }
                        issues.append(issue)
                        # Don't break - check ALL patterns for each line
        
        return issues
    
    def _create_signature(self, issue_type: str, content: str) -> str:
        """Create unique signature for deduplication"""
        # Clean content for signature
        cleaned = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[\.\d]*Z?', '', content)
        cleaned = re.sub(r'line \d+', 'line X', cleaned)
        cleaned = re.sub(r':\d+', ':X', cleaned)
        cleaned = re.sub(r'0x[0-9a-fA-F]+', '0xXXX', cleaned)
        
        sig_text = f"{issue_type}:{cleaned[:200]}"
        return hashlib.md5(sig_text.encode()).hexdigest()
    
    def run_remediation_loop(self) -> int:
        """Main remediation loop - iterate until no errors or max iterations"""
        print("=" * 80)
        print("COMPREHENSIVE ERROR HUNTER - BACKEND SERVICE")
        print("=" * 80)
        print(f"Hunting ALL errors since: {self.since_timestamp}")
        print(f"Max iterations: {self.max_iterations}")
        print()
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            print(f"\n{'='*80}")
            print(f"ITERATION {self.iteration}")
            print(f"{'='*80}")
            
            # Get logs and find issues
            logs = self.get_backend_logs_raw()
            if not logs:
                print("No logs found")
                break
            
            print(f"Analyzing {len(logs.split(chr(10)))} log lines...")
            
            # Find ALL issues
            new_issues = self.aggressive_error_detection(logs)
            
            # Filter out already processed
            unique_new_issues = []
            for issue in new_issues:
                if issue['signature'] not in self.processed_signatures:
                    unique_new_issues.append(issue)
                    self.processed_signatures.add(issue['signature'])
                    self.all_issues.append(issue)
            
            if not unique_new_issues:
                print(f"\n[SUCCESS] No new issues found in iteration {self.iteration}")
                if self.iteration == 1:
                    print("All logs are clean!")
                else:
                    print(f"All {len(self.all_issues)} issues have been identified")
                break
            
            print(f"\nFound {len(unique_new_issues)} NEW issues in this iteration")
            print(f"Total issues found so far: {len(self.all_issues)}")
            
            # Categorize new issues
            by_severity = defaultdict(list)
            for issue in unique_new_issues:
                by_severity[issue['severity']].append(issue)
            
            print("\nNew Issues by Severity:")
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if by_severity[severity]:
                    print(f"  {severity}: {len(by_severity[severity])}")
            
            # Process each new issue
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                for issue in by_severity[severity]:
                    try:
                        print(f"\n[{severity}] {issue['issue_type']} at {issue['timestamp']}")
                        print(f"  Pattern: {issue['pattern']}")
                        # Handle Unicode safely
                        log_snippet = issue['log_content'][:200].encode('ascii', 'replace').decode('ascii')
                        print(f"  Log: {log_snippet}...")
                    except Exception as e:
                        print(f"\n[{severity}] {issue['issue_type']} - (Unicode display error)")
                    
                    # Log remediation task
                    task = {
                        'iteration': self.iteration,
                        'timestamp': datetime.now().isoformat(),
                        'severity': issue['severity'],
                        'issue_type': issue['issue_type'],
                        'signature': issue['signature'],
                        'log_line': issue['log_line'],
                        'status': 'identified',
                        'remediation': 'Pending multi-agent deployment'
                    }
                    self.remediation_log.append(task)
            
            # Check if we should continue
            if len(unique_new_issues) < 5 and self.iteration > 1:
                print(f"\nFound only {len(unique_new_issues)} new issues. Stopping iteration.")
                break
            
            if self.iteration < self.max_iterations:
                print(f"\nWaiting 2 seconds before next iteration...")
                time.sleep(2)
        
        # Generate final report
        self.generate_final_report()
        
        return len(self.all_issues)
    
    def generate_final_report(self):
        """Generate comprehensive final report"""
        # Categorize all issues
        by_severity = defaultdict(list)
        by_type = defaultdict(list)
        
        for issue in self.all_issues:
            by_severity[issue['severity']].append(issue)
            by_type[issue['issue_type']].append(issue)
        
        report = {
            'scan_completed': datetime.now().isoformat(),
            'since_timestamp': self.since_timestamp,
            'total_iterations': self.iteration,
            'total_issues': len(self.all_issues),
            'unique_signatures': len(self.processed_signatures),
            'summary': {
                'CRITICAL': len(by_severity['CRITICAL']),
                'HIGH': len(by_severity['HIGH']),
                'MEDIUM': len(by_severity['MEDIUM']),
                'LOW': len(by_severity['LOW'])
            },
            'top_issue_types': sorted(
                [(k, len(v)) for k, v in by_type.items()],
                key=lambda x: x[1],
                reverse=True
            )[:20],
            'all_issues': self.all_issues,
            'remediation_log': self.remediation_log
        }
        
        # Save report
        report_path = Path(f'comprehensive_error_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print("\n" + "=" * 80)
        print("FINAL REPORT")
        print("=" * 80)
        print(f"Total Issues Found: {report['total_issues']}")
        print(f"Unique Signatures: {report['unique_signatures']}")
        print(f"Iterations Run: {report['total_iterations']}")
        
        print("\nIssues by Severity:")
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = report['summary'][severity]
            if count > 0:
                print(f"  {severity}: {count}")
        
        print("\nTop 10 Issue Types:")
        for issue_type, count in report['top_issue_types'][:10]:
            print(f"  {issue_type}: {count}")
        
        print(f"\nDetailed report saved to: {report_path}")
        
        # Show critical issues
        if by_severity['CRITICAL']:
            print("\n" + "=" * 80)
            print("CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
            print("=" * 80)
            for i, issue in enumerate(by_severity['CRITICAL'][:5], 1):
                try:
                    print(f"\n{i}. [{issue['timestamp']}] {issue['issue_type']}")
                    log_snippet = issue['log_content'][:150].encode('ascii', 'replace').decode('ascii')
                    print(f"   {log_snippet}...")
                except:
                    print(f"\n{i}. {issue['issue_type']} - (Unicode display error)")


def main():
    """Main execution"""
    since_timestamp = "2025-08-28 15:42:48"
    if len(sys.argv) > 1:
        since_timestamp = sys.argv[1]
    
    print(f"Starting comprehensive error hunt from: {since_timestamp}")
    
    hunter = ComprehensiveErrorHunter(since_timestamp)
    total_issues = hunter.run_remediation_loop()
    
    print("\n" + "=" * 80)
    print("HUNT COMPLETE")
    print("=" * 80)
    print(f"Total issues identified: {total_issues}")
    
    if total_issues == 0:
        print("[SUCCESS] No issues found - system is clean!")
    else:
        print("\nNext Steps:")
        print("1. Review comprehensive_error_report_*.json")
        print("2. Deploy multi-agent teams for CRITICAL issues first")
        print("3. Fix issues in order of severity")
        print("4. Update learnings after each fix")
        print("5. Re-run to verify all issues resolved")
    
    return 0 if total_issues == 0 else 1


if __name__ == '__main__':
    sys.exit(main())