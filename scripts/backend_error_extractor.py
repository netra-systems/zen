#!/usr/bin/env python3
"""
Backend Error Extractor and Remediation Coordinator
Focuses specifically on netra-backend service errors for systematic remediation
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

class BackendErrorExtractor:
    """Extract and categorize ALL errors from backend service logs"""
    
    def __init__(self, since_timestamp: str = "2025-08-28 15:42:48"):
        self.since_timestamp = since_timestamp
        self.errors = []
        self.error_signatures = set()
        
    def get_backend_logs(self, hours_back: int = 24) -> str:
        """Get backend container logs"""
        try:
            # Get backend container ID
            cmd = 'docker ps --filter "name=netra-backend" --format "{{.ID}}"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding='utf-8', errors='replace')
            container_id = result.stdout.strip()
            
            if not container_id:
                print("Backend container not found")
                return ""
            
            # Get logs with timestamps
            cmd = f'docker logs --since {hours_back}h --timestamps {container_id} 2>&1'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=60, encoding='utf-8', errors='replace')
            
            return result.stdout
        except Exception as e:
            print(f"Error getting backend logs: {e}")
            return ""
    
    def extract_errors(self, logs: str) -> List[Dict[str, Any]]:
        """Extract ALL errors from logs"""
        errors = []
        log_lines = logs.split('\n')
        
        # Pattern groups for different error types
        error_patterns = [
            # Python exceptions
            (r'ERROR.*', 'ERROR', 'Application Error'),
            (r'Traceback \(most recent call last\)', 'CRITICAL', 'Python Exception'),
            (r'AttributeError.*', 'HIGH', 'AttributeError'),
            (r'KeyError.*', 'HIGH', 'KeyError'),
            (r'TypeError.*', 'HIGH', 'TypeError'),
            (r'ValueError.*', 'HIGH', 'ValueError'),
            (r'ImportError.*', 'CRITICAL', 'Import Error'),
            (r'ModuleNotFoundError.*', 'CRITICAL', 'Module Not Found'),
            (r'FileNotFoundError.*', 'HIGH', 'File Not Found'),
            (r'PermissionError.*', 'HIGH', 'Permission Error'),
            (r'ConnectionError.*', 'HIGH', 'Connection Error'),
            (r'TimeoutError.*', 'MEDIUM', 'Timeout Error'),
            
            # Database errors
            (r'psycopg2\..*Error.*', 'HIGH', 'PostgreSQL Error'),
            (r'redis\.exceptions\..*', 'HIGH', 'Redis Error'),
            (r'clickhouse.*error.*', 'HIGH', 'ClickHouse Error', re.IGNORECASE),
            (r'database.*error.*', 'HIGH', 'Database Error', re.IGNORECASE),
            
            # Connection issues
            (r'Connection refused', 'HIGH', 'Connection Refused'),
            (r'Connection reset', 'HIGH', 'Connection Reset'),
            (r'Failed to connect', 'HIGH', 'Connection Failed'),
            (r'Cannot connect to', 'HIGH', 'Cannot Connect'),
            (r'Connection timeout', 'MEDIUM', 'Connection Timeout'),
            
            # Authentication/Security
            (r'Authentication failed', 'HIGH', 'Authentication Failed'),
            (r'Unauthorized', 'MEDIUM', 'Unauthorized Access'),
            (r'Forbidden', 'MEDIUM', 'Forbidden Access'),
            (r'Invalid token', 'MEDIUM', 'Invalid Token'),
            (r'Token expired', 'MEDIUM', 'Token Expired'),
            
            # WebSocket errors
            (r'WebSocket.*error.*', 'MEDIUM', 'WebSocket Error', re.IGNORECASE),
            (r'WebSocket.*failed.*', 'MEDIUM', 'WebSocket Failed', re.IGNORECASE),
            (r'WebSocket.*disconnect.*', 'LOW', 'WebSocket Disconnect', re.IGNORECASE),
            
            # Application specific
            (r'Agent.*error.*', 'MEDIUM', 'Agent Error', re.IGNORECASE),
            (r'Thread.*error.*', 'MEDIUM', 'Thread Error', re.IGNORECASE),
            (r'Execution.*failed.*', 'HIGH', 'Execution Failed', re.IGNORECASE),
            (r'Task.*failed.*', 'MEDIUM', 'Task Failed', re.IGNORECASE),
            
            # Warnings that might need attention
            (r'WARNING.*', 'LOW', 'Warning'),
            (r'deprecated', 'LOW', 'Deprecation Warning', re.IGNORECASE),
            (r'CRITICAL.*', 'CRITICAL', 'Critical Error'),
            (r'FATAL.*', 'CRITICAL', 'Fatal Error'),
            (r'PANIC.*', 'CRITICAL', 'Panic'),
            
            # System errors
            (r'Out of memory', 'CRITICAL', 'Out of Memory'),
            (r'Disk full', 'CRITICAL', 'Disk Full'),
            (r'No space left', 'CRITICAL', 'No Space'),
            (r'Resource exhausted', 'HIGH', 'Resource Exhausted'),
        ]
        
        # Track context for multiline errors
        in_traceback = False
        traceback_lines = []
        traceback_start_line = 0
        
        for line_num, line in enumerate(log_lines, 1):
            if not line.strip():
                continue
            
            # Check if line has timestamp
            timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[\.\d]*Z?)\s*(.*)$', line)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                log_content = timestamp_match.group(2)
                
                # Check if this is after our target timestamp
                try:
                    log_timestamp = datetime.strptime(timestamp_str[:19].replace('T', ' '), "%Y-%m-%d %H:%M:%S")
                    target_timestamp = datetime.strptime(self.since_timestamp, "%Y-%m-%d %H:%M:%S")
                    
                    if log_timestamp < target_timestamp:
                        continue
                except:
                    pass  # Include if we can't parse
            else:
                log_content = line
                timestamp_str = "Unknown"
            
            # Handle Python tracebacks
            if 'Traceback (most recent call last)' in line:
                if in_traceback and traceback_lines:
                    # Save previous traceback
                    self._save_traceback_error(errors, traceback_lines, traceback_start_line)
                in_traceback = True
                traceback_lines = [line]
                traceback_start_line = line_num
                continue
            elif in_traceback:
                traceback_lines.append(line)
                # Check if this is the end of traceback
                if re.match(r'^[A-Za-z]+Error:|^[A-Za-z]+Exception:', line):
                    self._save_traceback_error(errors, traceback_lines, traceback_start_line)
                    in_traceback = False
                    traceback_lines = []
                continue
            
            # Check against error patterns
            for pattern, severity, error_type, *flags in error_patterns:
                regex_flags = flags[0] if flags else 0
                if re.search(pattern, log_content, regex_flags):
                    # Create unique signature
                    sig = self._create_error_signature(error_type, log_content)
                    
                    if sig not in self.error_signatures:
                        self.error_signatures.add(sig)
                        
                        error = {
                            'line_number': line_num,
                            'timestamp': timestamp_str,
                            'severity': severity,
                            'error_type': error_type,
                            'pattern': pattern,
                            'log_line': line,
                            'log_content': log_content,
                            'signature': sig,
                            'context_lines': []
                        }
                        
                        # Add context lines (2 before, 2 after)
                        start = max(0, line_num - 3)
                        end = min(len(log_lines), line_num + 2)
                        error['context_lines'] = log_lines[start:end]
                        
                        errors.append(error)
                        break  # Only match first pattern
        
        # Don't forget last traceback if exists
        if in_traceback and traceback_lines:
            self._save_traceback_error(errors, traceback_lines, traceback_start_line)
        
        return errors
    
    def _create_error_signature(self, error_type: str, content: str) -> str:
        """Create unique signature for error deduplication"""
        # Remove timestamps and line numbers for signature
        cleaned = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[\.\d]*Z?', '', content)
        cleaned = re.sub(r'line \d+', 'line X', cleaned)
        cleaned = re.sub(r':\d+', ':X', cleaned)
        
        sig_text = f"{error_type}:{cleaned[:200]}"
        return hashlib.md5(sig_text.encode()).hexdigest()
    
    def _save_traceback_error(self, errors: List, traceback_lines: List, start_line: int):
        """Save a complete traceback as an error"""
        if not traceback_lines:
            return
        
        # Extract error type from last line
        error_type = "Unknown Exception"
        for line in reversed(traceback_lines):
            match = re.match(r'^([A-Za-z]+(?:Error|Exception)):', line)
            if match:
                error_type = match.group(1)
                break
        
        # Create signature
        sig = self._create_error_signature(error_type, '\n'.join(traceback_lines[:3]))
        
        if sig not in self.error_signatures:
            self.error_signatures.add(sig)
            
            error = {
                'line_number': start_line,
                'timestamp': self._extract_timestamp(traceback_lines[0]),
                'severity': 'CRITICAL',
                'error_type': error_type,
                'pattern': 'Traceback',
                'log_line': traceback_lines[0],
                'log_content': '\n'.join(traceback_lines),
                'signature': sig,
                'context_lines': traceback_lines,
                'is_traceback': True
            }
            errors.append(error)
    
    def _extract_timestamp(self, line: str) -> str:
        """Extract timestamp from log line"""
        match = re.match(r'^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[\.\d]*Z?)', line)
        return match.group(1) if match else "Unknown"
    
    def categorize_errors(self, errors: List[Dict]) -> Dict[str, List]:
        """Categorize errors by type and severity"""
        categorized = {
            'by_severity': defaultdict(list),
            'by_type': defaultdict(list),
            'by_time': defaultdict(list),
        }
        
        for error in errors:
            categorized['by_severity'][error['severity']].append(error)
            categorized['by_type'][error['error_type']].append(error)
            
            # Group by hour
            if error['timestamp'] != "Unknown":
                try:
                    dt = datetime.strptime(error['timestamp'][:19].replace('T', ' '), "%Y-%m-%d %H:%M:%S")
                    hour_key = dt.strftime("%Y-%m-%d %H:00")
                    categorized['by_time'][hour_key].append(error)
                except:
                    pass
        
        return categorized
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive error report"""
        logs = self.get_backend_logs()
        if not logs:
            return {'error': 'No logs found'}
        
        errors = self.extract_errors(logs)
        categorized = self.categorize_errors(errors)
        
        report = {
            'scan_timestamp': datetime.now().isoformat(),
            'since_timestamp': self.since_timestamp,
            'total_errors': len(errors),
            'unique_errors': len(self.error_signatures),
            'summary': {
                'CRITICAL': len(categorized['by_severity']['CRITICAL']),
                'HIGH': len(categorized['by_severity']['HIGH']),
                'MEDIUM': len(categorized['by_severity']['MEDIUM']),
                'LOW': len(categorized['by_severity']['LOW']),
            },
            'error_types': {k: len(v) for k, v in categorized['by_type'].items()},
            'errors': errors,
            'categorized': categorized
        }
        
        return report
    
    def print_summary(self, report: Dict[str, Any]):
        """Print error summary"""
        print("\n" + "=" * 80)
        print("BACKEND ERROR ANALYSIS REPORT")
        print("=" * 80)
        print(f"Scan Time: {report['scan_timestamp']}")
        print(f"Analyzing logs since: {report['since_timestamp']}")
        print(f"\nTotal Errors Found: {report['total_errors']}")
        print(f"Unique Error Patterns: {report['unique_errors']}")
        
        print("\nErrors by Severity:")
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = report['summary'][severity]
            if count > 0:
                print(f"  {severity}: {count}")
        
        print("\nTop Error Types:")
        sorted_types = sorted(report['error_types'].items(), key=lambda x: x[1], reverse=True)
        for error_type, count in sorted_types[:10]:
            print(f"  {error_type}: {count}")
        
        # Show first few critical errors
        if report['categorized']['by_severity']['CRITICAL']:
            print("\n" + "=" * 80)
            print("CRITICAL ERRORS (First 3):")
            print("=" * 80)
            for error in report['categorized']['by_severity']['CRITICAL'][:3]:
                print(f"\n[{error['timestamp']}] {error['error_type']}")
                print(f"Line {error['line_number']}: {error['log_content'][:200]}")
        
        # Show first few high priority errors
        if report['categorized']['by_severity']['HIGH']:
            print("\n" + "=" * 80)
            print("HIGH PRIORITY ERRORS (First 3):")
            print("=" * 80)
            for error in report['categorized']['by_severity']['HIGH'][:3]:
                print(f"\n[{error['timestamp']}] {error['error_type']}")
                print(f"Line {error['line_number']}: {error['log_content'][:200]}")


def main():
    """Main execution"""
    # Parse arguments
    since_timestamp = "2025-08-28 15:42:48"
    if len(sys.argv) > 1:
        since_timestamp = sys.argv[1]
    
    print(f"Extracting backend errors since: {since_timestamp}")
    
    # Extract errors
    extractor = BackendErrorExtractor(since_timestamp)
    report = extractor.generate_report()
    
    if 'error' in report:
        print(f"Error: {report['error']}")
        return 1
    
    # Print summary
    extractor.print_summary(report)
    
    # Save detailed report
    report_path = Path(f'backend_errors_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(report_path, 'w') as f:
        # Remove context lines for JSON (too verbose)
        clean_report = report.copy()
        for error in clean_report.get('errors', []):
            error.pop('context_lines', None)
        json.dump(clean_report, f, indent=2, default=str)
    
    print(f"\nDetailed report saved to: {report_path}")
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Review the detailed error report")
    print("2. Deploy multi-agent teams to fix each error category")
    print("3. Start with CRITICAL errors, then HIGH, MEDIUM, LOW")
    print("4. Update learnings after each fix")
    print("5. Re-run to verify errors are resolved")
    
    return 0 if report['total_errors'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())