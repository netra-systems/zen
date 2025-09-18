#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Log Collector for Specific Time Range
Collects logs from netra-backend-staging service for the requested time period
Time Range: 2025-09-15 18:00:00 PDT to 2025-09-15 19:06:58 PDT
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

# Handle Windows encoding issues
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
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

def collect_gcp_logs_for_timerange():
    """Collect logs for the specific time range requested"""
    try:
        from google.cloud import logging as cloud_logging
        from google.cloud.logging_v2 import DESCENDING

        client = cloud_logging.Client(project="netra-staging")

        # Convert PDT to UTC for GCP
        # PDT is UTC-7, so 2025-09-15 18:00:00 PDT = 2025-09-16 01:00:00 UTC
        start_time = "2025-09-16T01:00:00Z"
        end_time = "2025-09-16T02:06:58Z"

        print(f"🔍 Collecting logs from netra-backend-staging")
        print(f"📅 Time range: {start_time} to {end_time}")
        print(f"🎯 Severity: WARNING and ERROR levels")

        # Build the filter
        filters = [
            f'timestamp>="{start_time}"',
            f'timestamp<="{end_time}"',
            'resource.type="cloud_run_revision"',
            'resource.labels.service_name="netra-backend-staging"',
            'severity>=WARNING'
        ]

        full_filter = ' AND '.join(filters)
        print(f"🔧 Filter: {full_filter}")

        collected_logs = []
        count = 0

        print("\n📋 Collecting log entries...")

        for entry in client.list_entries(
            filter_=full_filter,
            order_by=DESCENDING,
            page_size=1000
        ):
            parsed_log = parse_log_entry(entry)
            collected_logs.append(parsed_log)
            count += 1

            # Print progress
            if count % 10 == 0:
                print(f"   📊 Collected {count} log entries...")

        print(f"\n✅ Total collected: {count} log entries")

        return collected_logs

    except ImportError:
        print("❌ FAIL: google-cloud-logging not installed")
        print("   Install with: pip install google-cloud-logging")
        return []
    except Exception as e:
        print(f"❌ FAIL: Error fetching logs: {e}")
        return []

def parse_log_entry(entry) -> Dict[str, Any]:
    """Parse log entry into the requested format"""
    parsed = {
        'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
        'severity': entry.severity,
        'resource': {
            'type': entry.resource.type,
            'labels': dict(entry.resource.labels) if entry.resource.labels else {}
        }
    }

    # Handle JSON payload (preferred format)
    json_payload = {}
    if hasattr(entry, 'payload') and isinstance(entry.payload, dict):
        json_payload = dict(entry.payload)
    elif hasattr(entry, 'json_payload') and entry.json_payload:
        json_payload = dict(entry.json_payload)

    if json_payload:
        parsed['jsonPayload'] = {}

        # Extract context if available
        if any(key in json_payload for key in ['name', 'service', 'module', 'logger']):
            parsed['jsonPayload']['context'] = {}
            if 'name' in json_payload:
                parsed['jsonPayload']['context']['name'] = json_payload['name']
            if 'service' in json_payload:
                parsed['jsonPayload']['context']['service'] = json_payload['service']
            if 'module' in json_payload:
                parsed['jsonPayload']['context']['module'] = json_payload['module']
            if 'logger' in json_payload:
                parsed['jsonPayload']['context']['logger'] = json_payload['logger']

        # Extract labels if available
        if any(key in json_payload for key in ['function', 'line', 'module', 'method']):
            parsed['jsonPayload']['labels'] = {}
            if 'function' in json_payload:
                parsed['jsonPayload']['labels']['function'] = json_payload['function']
            if 'line' in json_payload:
                parsed['jsonPayload']['labels']['line'] = str(json_payload['line'])
            if 'module' in json_payload:
                parsed['jsonPayload']['labels']['module'] = json_payload['module']
            if 'method' in json_payload:
                parsed['jsonPayload']['labels']['method'] = json_payload['method']

        # Extract message
        if 'message' in json_payload:
            parsed['jsonPayload']['message'] = json_payload['message']
        elif 'msg' in json_payload:
            parsed['jsonPayload']['message'] = json_payload['msg']
        elif 'error' in json_payload:
            parsed['jsonPayload']['message'] = str(json_payload['error'])

        # Include any other relevant fields
        for key, value in json_payload.items():
            if key not in ['name', 'service', 'module', 'logger', 'function', 'line', 'method', 'message', 'msg', 'error']:
                if 'jsonPayload' not in parsed:
                    parsed['jsonPayload'] = {}
                parsed['jsonPayload'][key] = value

    # Handle text payload as fallback
    text_payload = None
    if hasattr(entry, 'text_payload') and entry.text_payload:
        text_payload = entry.text_payload
    elif hasattr(entry, 'payload') and isinstance(entry.payload, str):
        text_payload = entry.payload

    if text_payload and not json_payload:
        parsed['textPayload'] = text_payload

    # Add trace and span info if available
    if hasattr(entry, 'trace') and entry.trace:
        parsed['trace'] = entry.trace
    if hasattr(entry, 'span_id') and entry.span_id:
        parsed['spanId'] = entry.span_id

    # Add HTTP request info if available
    if hasattr(entry, 'http_request') and entry.http_request:
        parsed['httpRequest'] = {
            'method': entry.http_request.get('requestMethod'),
            'url': entry.http_request.get('requestUrl'),
            'status': entry.http_request.get('status'),
            'userAgent': entry.http_request.get('userAgent'),
            'latency': entry.http_request.get('latency')
        }

    return parsed

def format_logs_output(logs: List[Dict]) -> str:
    """Format logs in a readable structure"""
    if not logs:
        return "No logs found for the specified time range and criteria."

    output = []
    output.append("=" * 80)
    output.append(f"GCP LOGS COLLECTION REPORT")
    output.append("=" * 80)
    output.append(f"Service: netra-backend-staging")
    output.append(f"Time Range: 2025-09-15 18:00:00 PDT to 2025-09-15 19:06:58 PDT")
    output.append(f"Severity: WARNING and ERROR")
    output.append(f"Total Entries: {len(logs)}")
    output.append("=" * 80)
    output.append("")

    # Group by severity
    by_severity = {}
    for log in logs:
        severity = log.get('severity', 'UNKNOWN')
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(log)

    # Display logs grouped by severity
    for severity in ['ERROR', 'WARNING', 'NOTICE', 'INFO']:
        if severity in by_severity:
            output.append(f"\n{'='*20} {severity} LOGS ({len(by_severity[severity])} entries) {'='*20}")

            for i, log in enumerate(by_severity[severity], 1):
                output.append(f"\n--- {severity} LOG #{i} ---")
                output.append(f"Timestamp: {log.get('timestamp', 'N/A')}")
                output.append(f"Severity: {log.get('severity', 'N/A')}")

                # Format JSON payload nicely
                if 'jsonPayload' in log:
                    output.append("JSON Payload:")
                    json_str = json.dumps(log['jsonPayload'], indent=2)
                    for line in json_str.split('\n'):
                        output.append(f"  {line}")

                # Format text payload
                if 'textPayload' in log:
                    output.append(f"Text Payload: {log['textPayload']}")

                # Additional fields
                if 'httpRequest' in log:
                    output.append(f"HTTP Request: {json.dumps(log['httpRequest'], indent=2)}")

                if 'trace' in log:
                    output.append(f"Trace: {log['trace']}")

                output.append("")

    return "\n".join(output)

def main():
    """Main execution"""
    print("🚀 Starting GCP Log Collection for Specific Time Range")

    if not setup_gcp_auth():
        return

    # Collect logs
    logs = collect_gcp_logs_for_timerange()

    if not logs:
        print("❌ No logs retrieved")
        return

    # Format output
    formatted_output = format_logs_output(logs)

    # Create output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = project_root / "gcp" / "log-gardener" / f"GCP-LOG-GARDENER-WORKLOG-last-1-hour-{timestamp}.md"

    # Ensure directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save formatted output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(formatted_output)

    print(f"📄 Formatted logs saved to: {output_file}")

    # Also save raw JSON for analysis
    json_file = project_root / "gcp" / "log-gardener" / f"raw_logs_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, default=str)

    print(f"📊 Raw JSON saved to: {json_file}")

    # Print summary to console
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"  • Total logs collected: {len(logs)}")

    severity_counts = {}
    for log in logs:
        severity = log.get('severity', 'UNKNOWN')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    for severity, count in severity_counts.items():
        print(f"  • {severity}: {count} entries")

    print("="*60)

    return logs

if __name__ == '__main__':
    main()