#!/usr/bin/env python3
"""
GCP Log Collection for Backend Service - Current Hour
MANUAL EXECUTION REQUIRED: This script requires manual execution due to gcloud authentication
Collects logs from netra-backend-staging service from the last hour (Sept 17, 2025)
Time: 00:30 UTC to current time (approximately 01:30 UTC)
"""

import subprocess
import json
import os
import sys
from datetime import datetime, timedelta

# Set UTF-8 encoding for cross-platform compatibility
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class GCPLogCollector:
    def __init__(self):
        self.project = "netra-staging"
        self.service_name = "netra-backend-staging"
        
        # Current time: Sept 17, 2025 at 18:30 PDT (01:30 UTC)
        # Target logs from last hour: 00:30 UTC to 01:30 UTC
        self.target_start_time = "2025-09-17T00:30:00Z"
        self.output_file = "/Users/anthony/Desktop/netra-apex/gcp_logs_backend.json"
        
    def check_authentication(self):
        """Check GCP authentication status"""
        print("🔐 Checking GCP Authentication...")
        try:
            result = subprocess.run(
                "gcloud auth list --filter=status:ACTIVE --format=\"value(account)\"",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                print(f"✅ Authenticated as: {result.stdout.strip()}")
                return True
            else:
                print("❌ Not authenticated or no active account")
                print("Please run: gcloud auth login")
                return False
                
        except Exception as e:
            print(f"❌ Authentication check failed: {e}")
            return False

    def collect_logs(self):
        """Collect backend service logs from the last hour"""
        print("=" * 80)
        print("GCP BACKEND LOG COLLECTION - LAST HOUR")
        print("=" * 80)
        print(f"Project: {self.project}")
        print(f"Service: {self.service_name}")
        print(f"Start Time: {self.target_start_time}")
        print(f"Severity: WARNING and above")
        print(f"Limit: 500 entries")
        print(f"Output File: {self.output_file}")
        print("=" * 80)

        # Check authentication first
        if not self.check_authentication():
            return None

        # Construct the exact command as requested
        cmd = f'''gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name={self.service_name} AND severity>=WARNING AND timestamp>="{self.target_start_time}"' --limit=500 --format=json --project={self.project}'''
        
        print("\n📊 Executing log collection command...")
        print(f"Command: {cmd}")
        print("\n⏳ This may take up to 2 minutes...")
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes timeout
            )
            
            if result.returncode == 0:
                if result.stdout.strip():
                    try:
                        logs = json.loads(result.stdout)
                        print(f"\n✅ Successfully collected {len(logs)} log entries")
                        
                        # Save to file
                        with open(self.output_file, 'w', encoding='utf-8') as f:
                            json.dump(logs, f, indent=2, ensure_ascii=False)
                        
                        print(f"📁 Saved to: {self.output_file}")
                        
                        # Analyze the logs
                        self.analyze_logs(logs)
                        
                        return logs
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON parsing error: {e}")
                        print(f"Raw output (first 500 chars): {result.stdout[:500]}")
                        return None
                else:
                    print("⚠️ No logs found in the specified time range")
                    # Create empty file to indicate completion
                    with open(self.output_file, 'w', encoding='utf-8') as f:
                        json.dump([], f)
                    return []
            else:
                print(f"❌ Command failed with exit code: {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("❌ Command timed out after 3 minutes")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None

    def analyze_logs(self, logs):
        """Analyze collected logs and provide comprehensive summary"""
        print("\n" + "=" * 80)
        print("LOG ANALYSIS SUMMARY")
        print("=" * 80)

        if not logs:
            print("📊 RESULT: No logs found in the specified time range")
            print("✅ This indicates the backend service was healthy with no WARNING+ events")
            return {
                'total_entries': 0,
                'severity_counts': {},
                'error_patterns': [],
                'timestamp_range': None,
                'critical_errors': []
            }

        # Initialize analysis variables
        severity_counts = {}
        error_patterns = {}
        timestamps = []
        critical_errors = []
        p0_errors = []
        
        # Process each log entry
        for log in logs:
            # Extract timestamp
            timestamp = log.get('timestamp', '')
            if timestamp:
                timestamps.append(timestamp)
            
            # Count severities
            severity = log.get('severity', 'UNKNOWN')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Extract and categorize messages
            message = self.extract_message(log)
            if message:
                pattern = self.categorize_error_pattern(message)
                error_patterns[pattern] = error_patterns.get(pattern, 0) + 1
                
                # Identify critical/P0 errors
                if self.is_critical_error(severity, message):
                    critical_errors.append({
                        'timestamp': timestamp,
                        'severity': severity,
                        'message': message[:400],  # Keep more context for analysis
                        'service': log.get('resource', {}).get('labels', {}).get('service_name', 'unknown'),
                        'pattern': pattern
                    })
                    
                    # Mark as P0 if it's a business-critical issue
                    if self.is_p0_error(message):
                        p0_errors.append(critical_errors[-1])

        # Generate comprehensive summary
        print(f"📊 TOTAL LOG ENTRIES: {len(logs)}")
        
        if timestamps:
            timestamps.sort()
            print(f"\n📅 TIMESTAMP RANGE:")
            print(f"  Earliest: {timestamps[0]}")
            print(f"  Latest:   {timestamps[-1]}")
            
            # Calculate time span
            try:
                start_dt = datetime.fromisoformat(timestamps[0].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(timestamps[-1].replace('Z', '+00:00'))
                span = end_dt - start_dt
                print(f"  Duration: {span}")
            except:
                print(f"  Duration: Unable to calculate")

        print(f"\n⚠️ SEVERITY BREAKDOWN:")
        total_issues = 0
        for severity in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTICE']:
            count = severity_counts.get(severity, 0)
            if count > 0:
                print(f"  {severity}: {count}")
                if severity in ['CRITICAL', 'ERROR', 'WARNING']:
                    total_issues += count

        print(f"\n🔍 ERROR PATTERNS ({len(error_patterns)} types):")
        sorted_patterns = sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)
        for pattern, count in sorted_patterns:
            print(f"  {pattern}: {count}")

        if critical_errors:
            print(f"\n🚨 CRITICAL ERRORS IDENTIFIED ({len(critical_errors)} found):")
            for i, error in enumerate(critical_errors[:5]):  # Show top 5
                print(f"\n  [{i+1}] {error['severity']} - {error['pattern']}")
                print(f"      Time: {error['timestamp']}")
                print(f"      Service: {error['service']}")
                print(f"      Message: {error['message']}")
                
            if len(critical_errors) > 5:
                print(f"\n  ... and {len(critical_errors) - 5} more critical errors")

        if p0_errors:
            print(f"\n🔥 P0 BUSINESS-CRITICAL ERRORS ({len(p0_errors)} found):")
            for i, error in enumerate(p0_errors[:3]):
                print(f"\n  [P0-{i+1}] {error['severity']} - {error['pattern']}")
                print(f"         Time: {error['timestamp']}")
                print(f"         Message: {error['message']}")

        print("\n" + "=" * 80)

        # Return analysis summary
        return {
            'total_entries': len(logs),
            'severity_counts': severity_counts,
            'error_patterns': dict(sorted_patterns),
            'timestamp_range': {
                'earliest': timestamps[0] if timestamps else None,
                'latest': timestamps[-1] if timestamps else None
            },
            'critical_errors': critical_errors,
            'p0_errors': p0_errors,
            'total_issues': total_issues
        }

    def extract_message(self, log):
        """Extract message from log entry"""
        if 'textPayload' in log:
            return log['textPayload']
        elif 'jsonPayload' in log:
            jp = log['jsonPayload']
            return jp.get('message', str(jp))
        return ""

    def categorize_error_pattern(self, message):
        """Categorize error message into specific patterns"""
        message_lower = message.lower()
        
        # Database-related errors
        if any(keyword in message_lower for keyword in ['database', 'sql', 'postgres', 'clickhouse', 'connection pool']):
            return "Database Connection Error"
        
        # WebSocket-related errors
        elif any(keyword in message_lower for keyword in ['websocket', 'ws', 'socket', '1011', 'connection closed']):
            return "WebSocket Connection Error"
        
        # Authentication errors
        elif any(keyword in message_lower for keyword in ['auth', 'jwt', 'token', 'oauth', 'unauthorized']):
            return "Authentication Error"
        
        # Timeout errors
        elif any(keyword in message_lower for keyword in ['timeout', 'deadline', 'timed out']):
            return "Timeout Error"
        
        # Resource/Infrastructure errors
        elif any(keyword in message_lower for keyword in ['memory', 'cpu', 'resource', 'oom', 'killed']):
            return "Resource/Infrastructure Error"
        
        # Permission errors
        elif any(keyword in message_lower for keyword in ['permission', 'access denied', 'forbidden', 'secret']):
            return "Permission/Access Error"
        
        # Configuration errors
        elif any(keyword in message_lower for keyword in ['config', 'environment', 'variable', 'missing']):
            return "Configuration Error"
        
        # Network errors
        elif any(keyword in message_lower for keyword in ['network', 'proxy', 'load balancer', 'ssl']):
            return "Network/SSL Error"
        
        # Application logic errors
        elif any(keyword in message_lower for keyword in ['exception', 'traceback', 'error', 'failed']):
            return "Application Logic Error"
        
        else:
            return "Other/Unclassified Error"

    def is_critical_error(self, severity, message):
        """Determine if this is a critical error requiring attention"""
        if severity in ['ERROR', 'CRITICAL']:
            return True
        
        # Critical keywords that indicate serious issues
        critical_keywords = [
            'fatal', 'crash', 'exception', 'failed', 'timeout', 
            'connection refused', 'access denied', 'out of memory',
            '500', '503', '502', '504', 'internal server error'
        ]
        
        return any(keyword in message.lower() for keyword in critical_keywords)

    def is_p0_error(self, message):
        """Determine if this is a P0 business-critical error"""
        p0_keywords = [
            'websocket', 'auth', 'database', 'login', 'user',
            'agent', 'chat', 'message', 'core', 'startup'
        ]
        
        return any(keyword in message.lower() for keyword in p0_keywords)

def main():
    """Main execution function"""
    print("🚀 GCP Backend Log Collector - Current Hour")
    print("=" * 80)
    print("Target: netra-backend-staging service logs")
    print("Time: Last hour (00:30 UTC to current time)")
    print("Severity: WARNING and above")
    print("=" * 80)
    
    collector = GCPLogCollector()
    logs = collector.collect_logs()
    
    if logs is not None:
        print(f"\n🎉 LOG COLLECTION COMPLETED!")
        print(f"📄 Results saved to: {collector.output_file}")
        if logs:
            print(f"📊 Total entries: {len(logs)}")
        else:
            print("✅ No WARNING+ logs found (service appears healthy)")
    else:
        print(f"\n❌ LOG COLLECTION FAILED")
        print("Common issues:")
        print("  - GCP authentication not configured")
        print("  - Insufficient permissions")
        print("  - Network connectivity issues")
        print("  - Service name mismatch")

if __name__ == "__main__":
    main()