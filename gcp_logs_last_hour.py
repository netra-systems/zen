#!/usr/bin/env python3
"""
GCP Log Fetcher for Last 1 Hour - Detailed Analysis
Fetches logs from netra-backend-staging service for the last 1 hour with full JSON payloads
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env

def setup_gcp_auth():
    """Setup GCP authentication using existing credentials"""
    # Check for service account key
    key_path = project_root / "config" / "netra-staging-sa-key.json"
    if key_path.exists():
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(key_path)
        print(f"[OK] Using service account credentials: {key_path}")
        return True

    # Try other credential paths
    alt_paths = [
        project_root / "config" / "netra-staging-7a1059b7cf26.json",
        Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
    ]

    for path in alt_paths:
        if path.exists():
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(path)
            print(f"[OK] Using credentials: {path}")
            return True

    print("[ERROR] No GCP credentials found")
    return False

def get_last_hour_logs(project_id: str = "netra-staging"):
    """Fetch logs from last 1 hour with full details"""
    try:
        from google.cloud import logging as cloud_logging
        from google.cloud.logging_v2 import DESCENDING

        client = cloud_logging.Client(project=project_id)

        # Calculate exactly 1 hour back
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        print(f"[TIME] Current time (UTC): {now.isoformat()}")
        print(f"[TIME] Collecting from: {one_hour_ago.isoformat()}")
        print(f"[TIME] Time range: {one_hour_ago.strftime('%H:%M:%S')} to {now.strftime('%H:%M:%S')} UTC")

        # Build comprehensive filter for netra-backend-staging specifically
        filter_parts = [
            f'timestamp >= "{one_hour_ago.isoformat()}"',
            f'timestamp <= "{now.isoformat()}"',
            'resource.type="cloud_run_revision"',
            'resource.labels.service_name="netra-backend-staging"',
            '(severity>="NOTICE" OR severity="INFO")'  # Include NOTICE, WARNING, ERROR, CRITICAL, INFO
        ]

        full_filter = ' AND '.join(filter_parts)
        print(f"[FILTER] {full_filter}")

        logs_by_severity = defaultdict(list)
        total_count = 0

        print(f"[SEARCH] Fetching logs from {project_id} for netra-backend-staging...")

        try:
            for entry in client.list_entries(
                filter_=full_filter,
                order_by=DESCENDING,
                page_size=5000  # Get up to 5000 entries
            ):
                parsed_entry = parse_log_entry_detailed(entry)
                severity = parsed_entry['severity']
                logs_by_severity[severity].append(parsed_entry)
                total_count += 1

                if total_count >= 5000:  # Limit total entries
                    break

            print(f"[SUMMARY] Total logs collected: {total_count}")
            for severity, logs in logs_by_severity.items():
                print(f"   {severity}: {len(logs)} entries")

        except Exception as e:
            print(f"[ERROR] Error fetching logs: {e}")
            return {}

        return logs_by_severity, one_hour_ago, now

    except ImportError:
        print("[ERROR] google-cloud-logging not installed")
        return {}, None, None
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return {}, None, None

def parse_log_entry_detailed(entry) -> Dict[str, Any]:
    """Parse log entry with complete details including all JSON payload fields"""
    parsed = {
        'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
        'severity': entry.severity,
        'resource': {
            'type': entry.resource.type,
            'labels': dict(entry.resource.labels) if entry.resource.labels else {}
        },
        'labels': dict(entry.labels) if entry.labels else {},
        'insert_id': getattr(entry, 'insert_id', None),
        'trace': getattr(entry, 'trace', None),
        'span_id': getattr(entry, 'span_id', None),
        'text_payload': None,
        'json_payload': {},
        'http_request': {},
        'source_location': {}
    }

    # Handle text payload
    if hasattr(entry, 'text_payload') and entry.text_payload:
        parsed['text_payload'] = entry.text_payload

    # Handle JSON payload - capture ALL fields
    if hasattr(entry, 'json_payload') and entry.json_payload:
        payload = dict(entry.json_payload)
        parsed['json_payload'] = payload

        # Extract common structured fields if present
        if 'level' in payload:
            parsed['log_level'] = payload['level']
        if 'logger' in payload:
            parsed['logger'] = payload['logger']
        if 'message' in payload:
            parsed['message'] = payload['message']
        if 'module' in payload:
            parsed['module'] = payload['module']
        if 'lineno' in payload:
            parsed['line_number'] = payload['lineno']
        if 'pathname' in payload:
            parsed['file_path'] = payload['pathname']
        if 'funcName' in payload:
            parsed['function_name'] = payload['funcName']
        if 'traceback' in payload:
            parsed['traceback'] = payload['traceback']
        if 'exc_info' in payload:
            parsed['exception_info'] = payload['exc_info']

    # Handle HTTP request details
    if hasattr(entry, 'http_request') and entry.http_request:
        parsed['http_request'] = {
            'method': entry.http_request.get('requestMethod'),
            'url': entry.http_request.get('requestUrl'),
            'status': entry.http_request.get('status'),
            'user_agent': entry.http_request.get('userAgent'),
            'remote_ip': entry.http_request.get('remoteIp'),
            'referer': entry.http_request.get('referer'),
            'latency': entry.http_request.get('latency'),
            'cache_hit': entry.http_request.get('cacheHit'),
            'cache_lookup': entry.http_request.get('cacheLookup'),
            'response_size': entry.http_request.get('responseSize'),
            'request_size': entry.http_request.get('requestSize')
        }

    # Handle source location
    if hasattr(entry, 'source_location') and entry.source_location:
        parsed['source_location'] = {
            'file': entry.source_location.get('file'),
            'line': entry.source_location.get('line'),
            'function': entry.source_location.get('function')
        }

    return parsed

def analyze_detailed_logs(logs_by_severity: Dict[str, List[Dict]], start_time, end_time) -> Dict[str, Any]:
    """Detailed analysis of logs with clustering and patterns"""
    analysis = {
        'collection_info': {
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'duration_hours': 1.0,
            'collection_timestamp': datetime.now().isoformat()
        },
        'summary': {
            'total_logs': sum(len(logs) for logs in logs_by_severity.values()),
            'logs_by_severity': {severity: len(logs) for severity, logs in logs_by_severity.items()},
        },
        'detailed_by_severity': {},
        'unique_messages': {},
        'traceback_analysis': [],
        'timing_patterns': [],
        'service_modules': set(),
        'error_categories': defaultdict(list)
    }

    # Process each severity level
    for severity, logs in logs_by_severity.items():
        severity_analysis = {
            'count': len(logs),
            'unique_messages': {},
            'modules': set(),
            'files': set(),
            'functions': set(),
            'sample_entries': []
        }

        message_counts = Counter()

        for i, log in enumerate(logs):
            # Extract meaningful message
            message = extract_meaningful_message(log)
            message_counts[message] += 1

            # Track modules and locations
            if log.get('module'):
                severity_analysis['modules'].add(log['module'])
                analysis['service_modules'].add(log['module'])
            if log.get('file_path'):
                severity_analysis['files'].add(log['file_path'])
            if log.get('function_name'):
                severity_analysis['functions'].add(log['function_name'])

            # Categorize errors
            if 'traceback' in log.get('json_payload', {}):
                analysis['traceback_analysis'].append({
                    'timestamp': log['timestamp'],
                    'severity': severity,
                    'traceback': log['json_payload']['traceback'][:500],  # Truncate for readability
                    'message': message[:200]
                })

            # Sample first few entries for each severity
            if i < 3:
                severity_analysis['sample_entries'].append(log)

        # Get top unique messages
        severity_analysis['unique_messages'] = dict(message_counts.most_common(10))
        severity_analysis['modules'] = list(severity_analysis['modules'])
        severity_analysis['files'] = list(severity_analysis['files'])
        severity_analysis['functions'] = list(severity_analysis['functions'])

        analysis['detailed_by_severity'][severity] = severity_analysis

    # Overall unique messages
    all_messages = []
    for logs in logs_by_severity.values():
        for log in logs:
            all_messages.append(extract_meaningful_message(log))

    analysis['unique_messages'] = dict(Counter(all_messages).most_common(20))
    analysis['service_modules'] = list(analysis['service_modules'])

    return analysis

def extract_meaningful_message(log: Dict) -> str:
    """Extract the most meaningful message from a log entry"""
    # Priority order for message extraction
    json_payload = log.get('json_payload', {})

    # Check for standard message fields
    if 'message' in json_payload:
        return str(json_payload['message'])
    elif 'msg' in json_payload:
        return str(json_payload['msg'])
    elif log.get('text_payload'):
        return str(log['text_payload'])
    elif 'error' in json_payload:
        return str(json_payload['error'])
    elif 'traceback' in json_payload:
        # For tracebacks, get the last line which usually has the error
        traceback_lines = str(json_payload['traceback']).split('\n')
        return traceback_lines[-1].strip() if traceback_lines else 'Traceback'
    elif json_payload:
        # Fallback to JSON representation
        return json.dumps(json_payload)[:200]
    else:
        return "No message content"

def save_detailed_results(logs_by_severity, analysis, start_time):
    """Save results with detailed formatting"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save raw logs
    raw_file = project_root / f"gcp_logs_raw_{timestamp}.json"
    with open(raw_file, 'w') as f:
        # Convert sets to lists for JSON serialization
        serializable_logs = {}
        for severity, logs in logs_by_severity.items():
            serializable_logs[severity] = logs

        json.dump(serializable_logs, f, indent=2, default=str)

    # Save analysis
    analysis_file = project_root / f"gcp_logs_analysis_{timestamp}.json"
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)

    print(f"[SAVE] Raw logs saved: {raw_file}")
    print(f"[SAVE] Analysis saved: {analysis_file}")

    return raw_file, analysis_file

def main():
    """Main execution for last 1 hour log collection"""
    print("GCP Logs Collection - Last 1 Hour (netra-backend-staging)")
    print("=" * 70)

    if not setup_gcp_auth():
        return

    # Fetch logs
    result = get_last_hour_logs()
    if len(result) == 3:
        logs_by_severity, start_time, end_time = result
    else:
        logs_by_severity = result
        start_time = end_time = None

    if not logs_by_severity:
        print("[ERROR] No logs retrieved")
        return

    # Analyze logs
    analysis = analyze_detailed_logs(logs_by_severity, start_time, end_time)

    # Save results
    raw_file, analysis_file = save_detailed_results(logs_by_severity, analysis, start_time)

    # Print summary
    print("\n[SUMMARY] RESULTS")
    print("=" * 50)
    print(f"Time Range: {analysis['collection_info']['start_time']} to {analysis['collection_info']['end_time']}")
    print(f"Total Logs: {analysis['summary']['total_logs']}")
    print("\nLogs by Severity:")
    for severity, count in analysis['summary']['logs_by_severity'].items():
        print(f"  {severity}: {count}")

    print(f"\nTop Unique Messages:")
    for i, (message, count) in enumerate(list(analysis['unique_messages'].items())[:5], 1):
        print(f"  {i}. ({count}x) {message[:100]}...")

    print(f"\nService Modules Found: {len(analysis['service_modules'])}")
    for module in sorted(analysis['service_modules'])[:10]:
        print(f"  - {module}")

    if analysis['traceback_analysis']:
        print(f"\nTracebacks Found: {len(analysis['traceback_analysis'])}")
        for i, tb in enumerate(analysis['traceback_analysis'][:3], 1):
            print(f"  {i}. {tb['timestamp']} [{tb['severity']}] {tb['message'][:60]}...")

    print(f"\n[COMPLETE] Results available in:")
    print(f"   Raw logs: {raw_file}")
    print(f"   Analysis: {analysis_file}")

if __name__ == '__main__':
    main()