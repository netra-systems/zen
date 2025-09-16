#!/usr/bin/env python3
"""
GCP Log Collection for Last Hour
Collects logs from netra-backend service for the last 1 hour
Target: 4:43 PM PDT to 5:43 PM PDT (23:43 UTC Sept 15 to 00:43 UTC Sept 16)
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

class GCPLogCollector:
    def __init__(self):
        self.project = "netra-staging"
        self.region = "us-central1"

    def run_command(self, cmd, timeout=60):
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

    def collect_logs_last_hour(self):
        """Collect logs from the last hour with all severities and full JSON payload"""
        print("=" * 60)
        print("GCP LOG COLLECTION - LAST 1 HOUR")
        print("=" * 60)
        print(f"Project: {self.project}")
        print(f"Time: 4:43 PM PDT to 5:43 PM PDT (Sept 15, 2025)")
        print(f"UTC: 23:43 Sept 15 to 00:43 Sept 16, 2025")
        print(f"Current time: {datetime.now()}")
        print("=" * 60)

        # Check authentication first
        print("\n🔐 Checking GCP Authentication...")
        auth_cmd = "gcloud auth list --filter=status:ACTIVE --format=\"value(account)\""
        stdout, stderr, code = self.run_command(auth_cmd)

        if code == 0 and stdout.strip():
            print(f"✅ Authenticated as: {stdout.strip()}")
        else:
            print("❌ Not authenticated. Please run: gcloud auth login")
            return None

        # Collect logs with comprehensive query
        print("\n📊 Collecting logs from netra-backend service...")

        # Multiple queries for different service name patterns
        service_patterns = [
            "netra-backend-staging",
            "netra-service",
            "backend-staging",
            "netra-backend"
        ]

        all_logs = []

        for service_name in service_patterns:
            print(f"\n🔍 Searching for service: {service_name}")

            # Query for ALL logs (not just errors) to get complete picture
            cmd = f'''gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name={service_name} AND timestamp>=\\"2025-09-15T23:43:00.000Z\\" AND timestamp<=\\"2025-09-16T00:43:00.000Z\\"" --limit=1000 --format=json --project={self.project}'''

            stdout, stderr, code = self.run_command(cmd, timeout=120)

            if code == 0 and stdout.strip():
                try:
                    logs = json.loads(stdout)
                    if logs:
                        print(f"  Found {len(logs)} log entries for {service_name}")
                        all_logs.extend(logs)
                    else:
                        print(f"  No logs found for {service_name}")
                except json.JSONDecodeError as e:
                    print(f"  JSON decode error for {service_name}: {e}")
            else:
                if stderr:
                    print(f"  Error querying {service_name}: {stderr}")
                else:
                    print(f"  No logs found for {service_name}")

        # Save and analyze results
        if all_logs:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"gcp_logs_last_hour_{timestamp}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_logs, f, indent=2, ensure_ascii=False)

            print(f"\n✅ Successfully collected {len(all_logs)} log entries")
            print(f"📁 Saved to: {output_file}")

            # Analyze the logs
            self.analyze_logs(all_logs)

            return all_logs
        else:
            print("\n⚠️ No logs found in the specified time range")
            print("This could mean:")
            print("  - Service was not active during this period")
            print("  - Service name pattern doesn't match")
            print("  - Time range is outside available log retention")
            return None

    def analyze_logs(self, logs):
        """Analyze collected logs and provide summary"""
        print("\n" + "=" * 60)
        print("LOG ANALYSIS SUMMARY")
        print("=" * 60)

        # Count by severity
        severity_counts = {}
        service_counts = {}
        error_patterns = []

        for log in logs:
            severity = log.get('severity', 'UNKNOWN')
            service = log.get('resource', {}).get('labels', {}).get('service_name', 'unknown')

            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            service_counts[service] = service_counts.get(service, 0) + 1

            # Collect error messages
            if severity in ['ERROR', 'CRITICAL', 'WARNING']:
                message = ""
                if 'textPayload' in log:
                    message = log['textPayload']
                elif 'jsonPayload' in log:
                    jp = log['jsonPayload']
                    message = jp.get('message', str(jp))

                if message:
                    error_patterns.append({
                        'severity': severity,
                        'service': service,
                        'message': message[:200],  # Truncate for readability
                        'timestamp': log.get('timestamp', '')
                    })

        print("\n📊 SEVERITY BREAKDOWN:")
        for severity, count in sorted(severity_counts.items()):
            print(f"  {severity}: {count}")

        print("\n🏷️ SERVICE BREAKDOWN:")
        for service, count in sorted(service_counts.items()):
            print(f"  {service}: {count}")

        if error_patterns:
            print(f"\n🚨 ERROR/WARNING PATTERNS ({len(error_patterns)} found):")
            for i, error in enumerate(error_patterns[:10]):  # Show first 10
                print(f"\n  [{i+1}] {error['severity']} - {error['service']}")
                print(f"      Time: {error['timestamp']}")
                print(f"      Message: {error['message']}")
        else:
            print("\n✅ No errors, warnings, or critical issues found!")

        print("\n" + "=" * 60)
        return {
            'severity_counts': severity_counts,
            'service_counts': service_counts,
            'error_patterns': error_patterns,
            'total_logs': len(logs)
        }

if __name__ == "__main__":
    collector = GCPLogCollector()
    logs = collector.collect_logs_last_hour()

    if logs:
        print(f"\n🎉 Collection completed successfully!")
        print(f"Total logs collected: {len(logs)}")
    else:
        print(f"\n⚠️ No logs collected. Check authentication and service availability.")