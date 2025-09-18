#!/usr/bin/env python3
"""
GCP Log Fetcher for Last 1 Hour - Backend Service Focus
Fetches logs from the last 1 hour with timezone awareness
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_gcp_auth():
    """Setup GCP authentication using existing credentials"""
    # Check for service account key
    key_path = project_root / "config" / "netra-staging-sa-key.json"
    if key_path.exists():
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(key_path)
        print(f"Using service account credentials: {key_path}")
        return True

    print("No GCP credentials found")
    return False

def get_last_hour_logs(project_id: str = "netra-staging"):
    """Fetch logs from the last 1 hour with timezone awareness"""
    try:
        from google.cloud import logging as cloud_logging
        from google.cloud.logging_v2 import DESCENDING

        client = cloud_logging.Client(project=project_id)

        # Get current time in UTC and calculate 1 hour ago
        now_utc = datetime.now(timezone.utc)
        one_hour_ago = now_utc - timedelta(hours=1)

        print(f"Current time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Fetching logs from: {one_hour_ago.strftime('%Y-%m-%d %H:%M:%S %Z')} to {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        # Time filter for last 1 hour
        time_filter = f'timestamp >= "{one_hour_ago.isoformat()}"'

        # Focus on all netra services with different severities
        services_filter = 'resource.type="cloud_run_revision" AND (resource.labels.service_name="netra-backend-staging" OR resource.labels.service_name="netra-auth" OR resource.labels.service_name="netra-frontend-staging")'

        logs_by_severity = {}

        # Get different severity levels
        severities = ['ERROR', 'WARNING', 'NOTICE', 'INFO']

        for severity in severities:
            print(f"Checking {severity} logs...")

            filters = [
                time_filter,
                services_filter,
                f'severity="{severity}"'
            ]
            full_filter = ' AND '.join(filters)

            entries = []
            count = 0

            try:
                for entry in client.list_entries(
                    filter_=full_filter,
                    order_by=DESCENDING,
                    page_size=100
                ):
                    parsed_entry = parse_log_entry(entry)
                    entries.append(parsed_entry)
                    count += 1
                    if count >= 50:  # Limit per severity to avoid overwhelming output
                        break

                logs_by_severity[severity] = entries
                print(f"   Found {len(entries)} {severity} entries")

            except Exception as e:
                print(f"   Error fetching {severity} logs: {e}")
                logs_by_severity[severity] = []

        return logs_by_severity, one_hour_ago, now_utc

    except ImportError:
        print("google-cloud-logging not installed")
        return {}, None, None
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return {}, None, None

def parse_log_entry(entry) -> Dict[str, Any]:
    """Parse log entry into structured format with full context"""
    parsed = {
        'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
        'severity': entry.severity,
        'insert_id': entry.insert_id,
        'resource': {
            'type': entry.resource.type,
            'labels': dict(entry.resource.labels) if entry.resource.labels else {}
        },
        'labels': dict(entry.labels) if entry.labels else {},
        'trace': getattr(entry, 'trace', None),
        'span_id': getattr(entry, 'span_id', None)
    }

    # Handle different payload types - be more aggressive in capturing
    if hasattr(entry, 'text_payload'):
        parsed['text_payload'] = entry.text_payload
    elif hasattr(entry, 'payload') and isinstance(entry.payload, str):
        parsed['text_payload'] = entry.payload

    if hasattr(entry, 'json_payload'):
        parsed['json_payload'] = dict(entry.json_payload) if entry.json_payload else {}
    elif hasattr(entry, 'payload') and isinstance(entry.payload, dict):
        parsed['json_payload'] = dict(entry.payload)

    # Also capture the raw payload for debugging
    if hasattr(entry, 'payload'):
        parsed['raw_payload_type'] = type(entry.payload).__name__
        if entry.payload:
            parsed['raw_payload'] = str(entry.payload)[:500]  # Limit size

    # Parse HTTP request if present
    if hasattr(entry, 'http_request') and entry.http_request:
        parsed['http_request'] = {
            'method': entry.http_request.get('requestMethod'),
            'url': entry.http_request.get('requestUrl'),
            'status': entry.http_request.get('status'),
            'user_agent': entry.http_request.get('userAgent'),
            'latency': entry.http_request.get('latency')
        }

    return parsed

def format_log_for_display(log_entry: Dict[str, Any]) -> str:
    """Format log entry for readable display"""
    output = []

    # Header with timestamp and severity
    timestamp = log_entry.get('timestamp', 'Unknown')
    severity = log_entry.get('severity', 'UNKNOWN')
    insert_id = log_entry.get('insert_id', 'N/A')

    output.append(f"=== {severity} - {timestamp} ===")
    output.append(f"Insert ID: {insert_id}")

    # Service info
    resource = log_entry.get('resource', {})
    service_name = resource.get('labels', {}).get('service_name', 'unknown')
    output.append(f"Service: {service_name}")

    # JSON payload (preferred)
    json_payload = log_entry.get('json_payload', {})
    if json_payload:
        output.append("JSON Payload:")

        # Key fields
        for key in ['message', 'error', 'logger', 'module', 'function', 'line']:
            if key in json_payload:
                value = json_payload[key]
                if isinstance(value, str) and len(value) > 200:
                    value = value[:200] + "..."
                output.append(f"  {key}: {value}")

        # Context fields
        context = json_payload.get('context', {})
        if context:
            output.append("  context:")
            for k, v in context.items():
                if isinstance(v, str) and len(v) > 100:
                    v = v[:100] + "..."
                output.append(f"    {k}: {v}")

        # Error details
        error = json_payload.get('error', {})
        if isinstance(error, dict):
            output.append("  error:")
            for k, v in error.items():
                if isinstance(v, str) and len(v) > 200:
                    v = v[:200] + "..."
                output.append(f"    {k}: {v}")

    # Text payload (fallback)
    text_payload = log_entry.get('text_payload')
    if text_payload and not json_payload:
        output.append("Text Payload:")
        if len(text_payload) > 300:
            output.append(f"  {text_payload[:300]}...")
        else:
            output.append(f"  {text_payload}")

    # HTTP request info
    http_request = log_entry.get('http_request')
    if http_request:
        output.append("HTTP Request:")
        for k, v in http_request.items():
            if v:
                output.append(f"  {k}: {v}")

    output.append("")  # Empty line separator
    return "\n".join(output)

def main():
    """Main execution"""
    print("GCP Backend Service Log Collection - Last 1 Hour")
    print("=" * 60)

    if not setup_gcp_auth():
        return

    # Fetch logs from last 1 hour
    logs_by_severity, start_time, end_time = get_last_hour_logs()

    if not logs_by_severity:
        print("No logs retrieved")
        return

    # Create output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = project_root / f"gcp_backend_logs_last_1hour_{timestamp}.json"
    display_file = project_root / f"gcp_backend_logs_last_1hour_{timestamp}.md"

    # Save raw JSON
    full_data = {
        'collection_time': datetime.now().isoformat(),
        'time_range': {
            'start': start_time.isoformat() if start_time else None,
            'end': end_time.isoformat() if end_time else None,
            'duration_hours': 1
        },
        'logs_by_severity': logs_by_severity,
        'summary': {
            'total_logs': sum(len(entries) for entries in logs_by_severity.values()),
            'counts_by_severity': {sev: len(entries) for sev, entries in logs_by_severity.items()}
        }
    }

    with open(output_file, 'w') as f:
        json.dump(full_data, f, indent=2)

    # Create readable markdown display
    markdown_content = []
    markdown_content.append("# GCP Backend Service Logs - Last 1 Hour")
    markdown_content.append("")
    markdown_content.append(f"**Collection Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    if start_time and end_time:
        markdown_content.append(f"**Time Range:** {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')} to {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    markdown_content.append(f"**Total Logs:** {full_data['summary']['total_logs']}")
    markdown_content.append("")

    # Summary by severity
    markdown_content.append("## Summary by Severity")
    for severity, count in full_data['summary']['counts_by_severity'].items():
        markdown_content.append(f"- **{severity}:** {count} entries")
    markdown_content.append("")

    # Display logs by severity (ERROR first, then WARNING, etc.)
    severity_order = ['ERROR', 'WARNING', 'NOTICE', 'INFO']

    for severity in severity_order:
        entries = logs_by_severity.get(severity, [])
        if entries:
            markdown_content.append(f"## {severity} Logs ({len(entries)} entries)")
            markdown_content.append("")

            for i, entry in enumerate(entries, 1):
                markdown_content.append(f"### {severity} Entry #{i}")
                markdown_content.append("")
                markdown_content.append("```")
                markdown_content.append(format_log_for_display(entry))
                markdown_content.append("```")
                markdown_content.append("")

    with open(display_file, 'w') as f:
        f.write("\n".join(markdown_content))

    print(f"Raw data saved to: {output_file}")
    print(f"Readable report saved to: {display_file}")

    # Print summary
    print("\nSUMMARY:")
    for severity, count in full_data['summary']['counts_by_severity'].items():
        if count > 0:
            print(f"   {severity}: {count} entries")

    # Show first few ERROR entries if any
    error_entries = logs_by_severity.get('ERROR', [])
    if error_entries:
        print(f"\nRECENT ERROR ENTRIES (showing first 3 of {len(error_entries)}):")
        for i, entry in enumerate(error_entries[:3], 1):
            timestamp = entry.get('timestamp', 'Unknown')
            json_payload = entry.get('json_payload', {})
            message = json_payload.get('message', entry.get('text_payload', 'No message'))
            if len(message) > 100:
                message = message[:100] + "..."
            print(f"   {i}. [{timestamp}] {message}")

    return full_data

if __name__ == '__main__':
    main()