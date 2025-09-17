#!/usr/bin/env python3
"""
Get the most recent GCP logs for Netra Apex backend service
Focus on last 15 minutes with full JSON payloads and timezone information
"""

import json
import os
import sys
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess

# Handle Windows encoding issues
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_gcp_auth():
    """Setup GCP authentication using existing service account key"""
    key_path = project_root / "config" / "netra-deployer-netra-staging.json"
    if key_path.exists():
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(key_path)
        print(f"[✓] Using service account credentials: {key_path}")
        return True

    print("❌ FAIL: No GCP credentials found")
    return False

def get_latest_logs_via_gcloud():
    """Get the latest logs using gcloud command"""
    # Calculate time range (last 15 minutes)
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(minutes=15)

    print(f"🔍 Getting logs for the last 15 minutes")
    print(f"📅 Start time: {start_time.isoformat()}Z")
    print(f"📅 End time: {end_time.isoformat()}Z")

    # Build the gcloud command
    filter_parts = [
        f'timestamp>="{start_time.isoformat()}Z"',
        f'timestamp<="{end_time.isoformat()}Z"',
        'resource.type="cloud_run_revision"',
        'resource.labels.service_name="netra-backend-staging"',
        'severity>=NOTICE'  # Get NOTICE, WARNING, ERROR, and CRITICAL
    ]

    filter_query = ' AND '.join(filter_parts)

    command = [
        'gcloud', 'logging', 'read', filter_query,
        '--project', 'netra-staging',
        '--format', 'json',
        '--limit', '100'
    ]

    print(f"🔧 Filter: {filter_query}")
    print(f"🔧 Command: {' '.join(command)}")
    print()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"❌ Command failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            return []

        if not result.stdout.strip():
            print("⚠️ No logs found in the last 15 minutes")
            return []

        logs = json.loads(result.stdout)
        print(f"✅ Retrieved {len(logs)} log entries")
        return logs

    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        return []
    except Exception as e:
        print(f"❌ Error running gcloud command: {e}")
        return []

def analyze_timezone_info(logs: List[Dict[str, Any]]):
    """Analyze timezone information from the logs"""
    print("\n" + "="*80)
    print("🕐 TIMEZONE AND TIMESTAMP ANALYSIS")
    print("="*80)

    if not logs:
        print("No logs to analyze for timezone information")
        return

    # Extract timestamps and analyze patterns
    timestamps = []
    for log in logs:
        if 'timestamp' in log:
            timestamps.append(log['timestamp'])

    print(f"📊 Total timestamps analyzed: {len(timestamps)}")

    if timestamps:
        print(f"🕐 Latest timestamp: {timestamps[0]}")
        print(f"🕐 Oldest timestamp: {timestamps[-1]}")

        # Analyze timestamp format
        sample_timestamp = timestamps[0]
        print(f"🔍 Timestamp format: {sample_timestamp}")

        # Try to parse and show timezone info
        try:
            if sample_timestamp.endswith('Z'):
                print("✅ Timezone: UTC (indicated by 'Z' suffix)")
            elif '+' in sample_timestamp or sample_timestamp.count('-') > 2:
                print("✅ Timezone: Has timezone offset information")
            else:
                print("⚠️ Timezone: No explicit timezone information found")
        except:
            print("❌ Unable to parse timestamp format")

    # Show current time for comparison
    current_utc = datetime.now(UTC)
    print(f"🕐 Current UTC time: {current_utc.isoformat()}Z")

    # Calculate time difference if possible
    if timestamps:
        try:
            latest_time = timestamps[0].replace('Z', '+00:00')
            latest_dt = datetime.fromisoformat(latest_time)
            time_diff = current_utc.replace(tzinfo=None) - latest_dt.replace(tzinfo=None)
            print(f"⏰ Time difference from now: {time_diff}")
        except:
            print("⏰ Unable to calculate time difference")

def format_logs_for_analysis(logs: List[Dict[str, Any]]):
    """Format logs with full JSON payloads for analysis"""
    print("\n" + "="*80)
    print("📋 DETAILED LOG ENTRIES")
    print("="*80)

    # Group by severity
    by_severity = {}
    for log in logs:
        severity = log.get('severity', 'UNKNOWN')
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(log)

    # Display logs by severity
    for severity in ['CRITICAL', 'ERROR', 'WARNING', 'NOTICE', 'INFO']:
        if severity not in by_severity:
            continue

        entries = by_severity[severity]
        print(f"\n🚨 {severity} LOGS ({len(entries)} entries)")
        print("-" * 60)

        for i, log in enumerate(entries[:5], 1):  # Show first 5 of each severity
            print(f"\n--- {severity} LOG #{i} ---")
            print(f"Timestamp: {log.get('timestamp', 'N/A')}")
            print(f"Severity: {log.get('severity', 'N/A')}")

            # Resource info
            if 'resource' in log:
                resource = log['resource']
                print(f"Resource Type: {resource.get('type', 'N/A')}")
                if 'labels' in resource:
                    labels = resource['labels']
                    print(f"Service: {labels.get('service_name', 'N/A')}")
                    print(f"Revision: {labels.get('revision_name', 'N/A')}")
                    print(f"Location: {labels.get('location', 'N/A')}")

            # Labels
            if 'labels' in log:
                print(f"Labels: {json.dumps(log['labels'], indent=2)}")

            # JSON payload
            if 'jsonPayload' in log and log['jsonPayload']:
                print("JSON Payload:")
                print(json.dumps(log['jsonPayload'], indent=2))

            # Text payload
            if 'textPayload' in log:
                print(f"Text Payload: {log['textPayload']}")

            # HTTP request info
            if 'httpRequest' in log and log['httpRequest']:
                print(f"HTTP Request: {json.dumps(log['httpRequest'], indent=2)}")

            # Trace info
            if log.get('trace'):
                print(f"Trace: {log['trace']}")
            if log.get('spanId'):
                print(f"Span ID: {log['spanId']}")

            print()

def main():
    """Main execution"""
    print("🚀 Getting Most Recent GCP Logs for Netra Apex Backend")
    print("📅 Collecting logs from the last 15 minutes")
    print("🎯 Focus: Timezone, timestamp format, and error analysis")
    print()

    if not setup_gcp_auth():
        return

    # Get the latest logs
    logs = get_latest_logs_via_gcloud()

    if not logs:
        print("❌ No recent logs retrieved")
        return

    # Analyze timezone information
    analyze_timezone_info(logs)

    # Format and display detailed logs
    format_logs_for_analysis(logs)

    # Save raw logs for further analysis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = project_root / f"latest_gcp_logs_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, default=str)

    print(f"\n📄 Raw logs saved to: {output_file}")

    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)

    severity_counts = {}
    for log in logs:
        severity = log.get('severity', 'UNKNOWN')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    print(f"Total logs: {len(logs)}")
    for severity, count in sorted(severity_counts.items()):
        print(f"  {severity}: {count}")

    return logs

if __name__ == '__main__':
    main()