#!/usr/bin/env python3
"""
GCP Log Collection for Backend Service - Last Hour
Collects logs from netra-backend-staging service from the last hour
Target: WARNING+ severity logs with current timestamp (Sept 17, 2025)
"""

import subprocess
import json
import time
import os
import sys
from datetime import datetime, timedelta

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class GCPBackendLogCollector:
    def __init__(self):
        self.project = "netra-staging"
        self.region = "us-central1"
        
    def run_command(self, cmd, timeout=120):
        """Execute command and return output"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8'
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", 1
        except Exception as e:
            return "", str(e), 1

    def collect_backend_logs_last_hour(self):
        """Collect backend service logs from the last hour"""
        # Calculate time range - last hour from now
        now_utc = datetime.utcnow()
        one_hour_ago_utc = now_utc - timedelta(hours=1)
        
        start_time = one_hour_ago_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        print("=" * 70)
        print("GCP BACKEND LOG COLLECTION - LAST HOUR")
        print("=" * 70)
        print(f"Project: {self.project}")
        print(f"Service: netra-backend-staging")
        print(f"Start Time (UTC): {start_time}")
        print(f"Current Time (UTC): {now_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}")
        print(f"Local Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Severity: WARNING and above")
        print("=" * 70)

        # Check authentication first
        print("\n🔐 Checking GCP Authentication...")
        auth_cmd = "gcloud auth list --filter=status:ACTIVE --format=\"value(account)\""
        stdout, stderr, code = self.run_command(auth_cmd)

        if code == 0 and stdout.strip():
            print(f"✅ Authenticated as: {stdout.strip()}")
        else:
            print("❌ Not authenticated. Please run: gcloud auth login")
            return None

        # Collect logs from backend service
        print("\n📊 Collecting logs from netra-backend-staging service...")
        
        # Updated query to match the exact command format requested
        cmd = f'''gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=netra-backend-staging AND severity>=WARNING AND timestamp>="{start_time}"' --limit=500 --format=json --project={self.project}'''
        
        print(f"\n🔍 Running query...")
        print(f"Command: {cmd}")
        
        stdout, stderr, code = self.run_command(cmd, timeout=180)

        if code == 0 and stdout.strip():
            try:
                logs = json.loads(stdout)
                print(f"\n✅ Successfully collected {len(logs)} log entries")
                
                # Save to the specified file location
                output_file = "/Users/anthony/Desktop/netra-apex/gcp_logs_backend.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, indent=2, ensure_ascii=False)
                
                print(f"📁 Saved to: {output_file}")
                
                # Analyze the logs
                analysis = self.analyze_logs(logs)
                
                return logs, analysis
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                print(f"Raw output: {stdout[:500]}...")
                return None, None
        else:
            if stderr:
                print(f"❌ Error executing command: {stderr}")
            if code != 0:
                print(f"❌ Command failed with exit code: {code}")
            if not stdout.strip():
                print("⚠️ No logs found in the specified time range")
            return None, None

    def analyze_logs(self, logs):
        """Analyze collected logs and provide summary"""
        print("\n" + "=" * 70)
        print("LOG ANALYSIS SUMMARY")
        print("=" * 70)

        if not logs:
            print("No logs to analyze")
            return {}

        # Initialize counters
        severity_counts = {}
        error_types = {}
        timestamps = []
        critical_errors = []
        
        # Process each log entry
        for log in logs:
            # Extract timestamp
            timestamp = log.get('timestamp', '')
            if timestamp:
                timestamps.append(timestamp)
            
            # Count severities
            severity = log.get('severity', 'UNKNOWN')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Extract error messages and patterns
            message = ""
            if 'textPayload' in log:
                message = log['textPayload']
            elif 'jsonPayload' in log:
                jp = log['jsonPayload']
                message = jp.get('message', str(jp))
            
            # Categorize error types
            if message:
                error_type = self.categorize_error(message)
                error_types[error_type] = error_types.get(error_type, 0) + 1
                
                # Flag critical errors
                if severity in ['ERROR', 'CRITICAL'] or any(keyword in message.lower() for keyword in ['fatal', 'crash', 'exception', 'failed', 'timeout']):
                    critical_errors.append({
                        'timestamp': timestamp,
                        'severity': severity,
                        'message': message[:300],  # Truncate for readability
                        'service': log.get('resource', {}).get('labels', {}).get('service_name', 'unknown')
                    })

        # Print summary
        print(f"\n📊 TOTAL LOG ENTRIES: {len(logs)}")
        
        print(f"\n📅 TIMESTAMP RANGE:")
        if timestamps:
            timestamps.sort()
            print(f"  Earliest: {timestamps[0]}")
            print(f"  Latest: {timestamps[-1]}")
        
        print(f"\n⚠️ SEVERITY BREAKDOWN:")
        for severity in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
            count = severity_counts.get(severity, 0)
            if count > 0:
                print(f"  {severity}: {count}")
        
        print(f"\n🔍 ERROR TYPES/PATTERNS:")
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {error_type}: {count}")
        
        if critical_errors:
            print(f"\n🚨 CRITICAL/P0 ERRORS ({len(critical_errors)} found):")
            for i, error in enumerate(critical_errors[:5]):  # Show first 5
                print(f"\n  [{i+1}] {error['severity']} - {error['service']}")
                print(f"      Time: {error['timestamp']}")
                print(f"      Message: {error['message']}")
                if i == 4 and len(critical_errors) > 5:
                    print(f"\n  ... and {len(critical_errors) - 5} more critical errors")
        else:
            print("\n✅ No critical errors identified!")

        print("\n" + "=" * 70)
        
        analysis_result = {
            'total_entries': len(logs),
            'severity_counts': severity_counts,
            'error_types': error_types,
            'critical_errors': critical_errors,
            'timestamp_range': {
                'earliest': timestamps[0] if timestamps else None,
                'latest': timestamps[-1] if timestamps else None
            }
        }
        
        return analysis_result

    def categorize_error(self, message):
        """Categorize error messages into types"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ['database', 'sql', 'postgres', 'clickhouse', 'connection']):
            return "Database Error"
        elif any(keyword in message_lower for keyword in ['websocket', 'ws', 'socket']):
            return "WebSocket Error"
        elif any(keyword in message_lower for keyword in ['auth', 'jwt', 'token', 'oauth']):
            return "Authentication Error"
        elif any(keyword in message_lower for keyword in ['timeout', 'deadline']):
            return "Timeout Error"
        elif any(keyword in message_lower for keyword in ['memory', 'cpu', 'resource']):
            return "Resource Error"
        elif any(keyword in message_lower for keyword in ['permission', 'access', 'forbidden']):
            return "Permission Error"
        elif any(keyword in message_lower for keyword in ['config', 'environment', 'variable']):
            return "Configuration Error"
        elif any(keyword in message_lower for keyword in ['network', 'connection', 'proxy']):
            return "Network Error"
        else:
            return "Other Error"

if __name__ == "__main__":
    collector = GCPBackendLogCollector()
    logs, analysis = collector.collect_backend_logs_last_hour()
    
    if logs:
        print(f"\n🎉 LOG COLLECTION COMPLETED SUCCESSFULLY!")
        print(f"📄 File saved to: /Users/anthony/Desktop/netra-apex/gcp_logs_backend.json")
        print(f"📊 Total logs: {len(logs)}")
        if analysis:
            print(f"🚨 Critical errors: {len(analysis.get('critical_errors', []))}")
    else:
        print(f"\n⚠️ LOG COLLECTION FAILED")
        print("Possible reasons:")
        print("  - No logs in the specified time range")
        print("  - Authentication issues")
        print("  - Service name mismatch")
        print("  - Network connectivity issues")