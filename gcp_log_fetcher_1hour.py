#!/usr/bin/env python3
"""
GCP Log Fetcher for Last 1 Hour - Backend Service
Fetches notices, warnings, and errors from the last 1 hour specifically
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
        print(f"SUCCESS: Using service account credentials: {key_path}")
        return True

    # Try other credential paths
    alt_paths = [
        project_root / "config" / "netra-deployer-netra-staging.json",
        project_root / "config" / "netra-staging-7a1059b7cf26.json",
        Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
    ]

    for path in alt_paths:
        if path.exists():
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(path)
            print(f"SUCCESS: Using credentials: {path}")
            return True

    print("ERROR: No GCP credentials found")
    return False

def get_recent_backend_logs(project_id: str = "netra-staging", hours_back: int = 1):
    """Fetch backend logs from last 1 hour focusing on notices, warnings, and errors"""
    try:
        from google.cloud import logging as cloud_logging
        from google.cloud.logging_v2 import DESCENDING

        client = cloud_logging.Client(project=project_id)

        # Get current time in UTC
        now_utc = datetime.now(timezone.utc)
        hours_ago = now_utc - timedelta(hours=hours_back)

        print(f"FETCHING: Logs from {project_id}")
        print(f"CURRENT TIME (UTC): {now_utc.isoformat()}")
        print(f"SEARCHING FROM: {hours_ago.isoformat()}")
        print(f"TIME RANGE: Last {hours_back} hour(s)")

        # Time filter
        time_filter = f'timestamp >= "{hours_ago.isoformat()}"'

        # Try different service name patterns for backend
        service_filters = [
            'resource.labels.service_name="netra-backend"',
            'resource.labels.service_name="netra-backend-staging"',
            'resource.labels.service_name=~".*backend.*"',
            'resource.type="cloud_run_revision"'  # Any cloud run service
        ]

        # Get severity levels: NOTICE, WARNING, ERROR (excluding DEBUG and INFO)
        target_severities = ['NOTICE', 'WARNING', 'ERROR']

        all_logs = []

        for severity in target_severities:
            print(f"SEARCHING: {severity} logs...")

            # Try each service filter pattern
            for i, service_filter in enumerate(service_filters):
                try:
                    filters = [
                        time_filter,
                        f'severity="{severity}"',
                        service_filter
                    ]
                    full_filter = ' AND '.join(filters)

                    count = 0
                    for entry in client.list_entries(
                        filter_=full_filter,
                        order_by=DESCENDING,
                        page_size=50
                    ):
                        parsed_entry = parse_log_entry(entry)
                        all_logs.append(parsed_entry)
                        count += 1
                        if count >= 50:  # Limit per filter
                            break

                    if count > 0:
                        print(f"  FOUND: {count} {severity} entries with filter {i+1}: {service_filter}")
                        break  # Found logs with this filter, move to next severity
                    else:
                        print(f"  FILTER {i+1}: No {severity} entries with {service_filter}")

                except Exception as e:
                    print(f"  ERROR: Error with filter {i+1} for {severity}: {e}")

        # Sort all logs by timestamp (newest first)
        all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return all_logs

    except ImportError:
        print("ERROR: google-cloud-logging not installed")
        return []
    except Exception as e:
        print(f"ERROR: Error fetching logs: {e}")
        return []

def parse_log_entry(entry) -> Dict[str, Any]:
    """Parse log entry into structured format with focus on required fields"""
    parsed = {
        'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
        'severity': entry.severity,
        'insertId': getattr(entry, 'insert_id', None),
        'resource': {
            'type': entry.resource.type if entry.resource else None,
            'labels': dict(entry.resource.labels) if entry.resource and entry.resource.labels else {}
        },
        'labels': dict(entry.labels) if entry.labels else {},
        'jsonPayload': {},
        'textPayload': None,
        'httpRequest': None,
        'trace': getattr(entry, 'trace', None),
        'spanId': getattr(entry, 'span_id', None)
    }

    # Handle different payload types
    if hasattr(entry, 'payload'):
        if isinstance(entry.payload, dict):
            parsed['jsonPayload'] = dict(entry.payload)
        elif isinstance(entry.payload, str):
            parsed['textPayload'] = entry.payload

    # Handle specific text and json payloads
    if hasattr(entry, 'text_payload'):
        parsed['textPayload'] = entry.text_payload

    if hasattr(entry, 'json_payload') and entry.json_payload:
        parsed['jsonPayload'] = dict(entry.json_payload)

    # Parse HTTP request if present
    if hasattr(entry, 'http_request') and entry.http_request:
        parsed['httpRequest'] = {
            'method': entry.http_request.get('requestMethod'),
            'url': entry.http_request.get('requestUrl'),
            'status': entry.http_request.get('status'),
            'userAgent': entry.http_request.get('userAgent'),
            'latency': entry.http_request.get('latency')
        }

    return parsed

def format_log_for_display(log_entry: Dict[str, Any]) -> str:
    """Format log entry for human-readable display"""
    timestamp = log_entry.get('timestamp', 'N/A')
    severity = log_entry.get('severity', 'N/A')
    insert_id = log_entry.get('insertId', 'N/A')

    # Extract key information from jsonPayload
    json_payload = log_entry.get('jsonPayload', {})
    context = json_payload.get('context', {})
    labels = json_payload.get('labels', {})
    message = json_payload.get('message', '')

    # Fallback to textPayload if no jsonPayload message
    if not message:
        message = log_entry.get('textPayload', 'No message content')

    formatted = f"""
---
Timestamp: {timestamp}
Severity: {severity}
Insert ID: {insert_id}
"""

    if context:
        formatted += f"Context:\n"
        if 'name' in context:
            formatted += f"  name: {context['name']}\n"
        if 'service' in context:
            formatted += f"  service: {context['service']}\n"

    if labels:
        formatted += f"Labels:\n"
        if 'function' in labels:
            formatted += f"  function: {labels['function']}\n"
        if 'line' in labels:
            formatted += f"  line: {labels['line']}\n"
        if 'module' in labels:
            formatted += f"  module: {labels['module']}\n"

    formatted += f"Message: {message}\n"

    # Add additional fields if present
    if json_payload.get('error'):
        formatted += f"Error: {json_payload['error']}\n"

    if json_payload.get('traceback'):
        formatted += f"Traceback: {json_payload['traceback'][:200]}...\n"

    return formatted

def detect_timezone_info(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze log timestamps to understand timezone information"""
    if not logs:
        return {'status': 'no_logs', 'timezone': 'unknown'}

    # Get the most recent log
    most_recent = logs[0]  # Already sorted by timestamp desc
    timestamp_str = most_recent.get('timestamp')

    if not timestamp_str:
        return {'status': 'no_timestamp', 'timezone': 'unknown'}

    try:
        # Parse the timestamp
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        # Determine timezone
        if dt.tzinfo:
            tz_name = str(dt.tzinfo)
            if '+00:00' in timestamp_str or timestamp_str.endswith('Z'):
                tz_interpretation = 'UTC'
            else:
                tz_interpretation = 'other'
        else:
            tz_name = 'naive'
            tz_interpretation = 'unknown'

        return {
            'status': 'detected',
            'most_recent_timestamp': timestamp_str,
            'parsed_datetime': dt.isoformat(),
            'timezone_name': tz_name,
            'timezone_interpretation': tz_interpretation,
            'is_utc': tz_interpretation == 'UTC'
        }
    except Exception as e:
        return {
            'status': 'parse_error',
            'error': str(e),
            'raw_timestamp': timestamp_str
        }

def main():
    """Main execution"""
    print("GCP Backend Log Fetcher - Last 1 Hour")
    print("=" * 50)

    if not setup_gcp_auth():
        return

    # Fetch logs from last 1 hour, but check longer if none found
    logs = get_recent_backend_logs(hours_back=1)

    if not logs:
        print("No logs in last 1 hour, expanding to last 6 hours to check log availability...")
        logs = get_recent_backend_logs(hours_back=6)

    if not logs:
        print("ERROR: No logs retrieved")
        return

    print(f"\nRETRIEVED: {len(logs)} log entries")

    # Detect timezone information
    timezone_info = detect_timezone_info(logs)
    print("\nTIMEZONE ANALYSIS:")
    print(json.dumps(timezone_info, indent=2))

    # Group by severity
    logs_by_severity = {}
    for log in logs:
        severity = log.get('severity', 'UNKNOWN')
        if severity not in logs_by_severity:
            logs_by_severity[severity] = []
        logs_by_severity[severity].append(log)

    print(f"\nLOG DISTRIBUTION:")
    for severity, severity_logs in logs_by_severity.items():
        print(f"  {severity}: {len(severity_logs)} entries")

    # Save detailed logs to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = project_root / f"gcp_backend_logs_1hour_{timestamp}.json"

    output_data = {
        'fetch_time': datetime.now().isoformat(),
        'timezone_analysis': timezone_info,
        'total_logs': len(logs),
        'logs_by_severity': {k: len(v) for k, v in logs_by_severity.items()},
        'raw_logs': logs
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSAVED: Detailed logs saved to: {output_file}")

    # Display formatted logs
    print(f"\nBACKEND LOGS (Last 1 Hour):")
    print("=" * 50)

    for i, log in enumerate(logs[:20]):  # Show first 20 logs
        print(format_log_for_display(log))
        if i >= 19 and len(logs) > 20:
            print(f"\n... ({len(logs) - 20} more logs in JSON file)")
            break

    return {
        'timezone_info': timezone_info,
        'logs_count': len(logs),
        'logs_by_severity': logs_by_severity,
        'output_file': str(output_file)
    }

if __name__ == '__main__':
    main()