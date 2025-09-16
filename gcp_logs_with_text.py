#!/usr/bin/env python3
"""
GCP Log Fetcher with Text Content - Focus on logs with actual content
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
    key_path = project_root / "config" / "netra-staging-sa-key.json"
    if key_path.exists():
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(key_path)
        print(f"[AUTH] Using service account credentials: {key_path}")
        return True
    print("[ERROR] No GCP credentials found")
    return False

def get_logs_with_content(project_id: str = "netra-staging"):
    """Fetch logs that have actual text content"""
    try:
        from google.cloud import logging as cloud_logging
        from google.cloud.logging_v2 import DESCENDING

        client = cloud_logging.Client(project=project_id)

        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        print(f"[TIME] Current time (UTC): {now.isoformat()}")
        print(f"[TIME] Collecting from: {one_hour_ago.isoformat()}")

        all_logs = {}

        # Try different filter strategies to get actual log content
        filter_strategies = [
            # Strategy 1: Get logs with text payload
            {
                'name': 'Text Payload Logs',
                'filter': [
                    f'timestamp >= "{one_hour_ago.isoformat()}"',
                    'resource.type="cloud_run_revision"',
                    'resource.labels.service_name="netra-backend-staging"',
                    'textPayload!=""',
                    'severity>="WARNING"'
                ]
            },
            # Strategy 2: Get logs with JSON message field
            {
                'name': 'JSON Message Logs',
                'filter': [
                    f'timestamp >= "{one_hour_ago.isoformat()}"',
                    'resource.type="cloud_run_revision"',
                    'resource.labels.service_name="netra-backend-staging"',
                    'jsonPayload.message!=""',
                    'severity>="WARNING"'
                ]
            },
            # Strategy 3: Error-specific logs
            {
                'name': 'Error Pattern Logs',
                'filter': [
                    f'timestamp >= "{one_hour_ago.isoformat()}"',
                    'resource.type="cloud_run_revision"',
                    'resource.labels.service_name="netra-backend-staging"',
                    '(textPayload=~"(?i)(error|exception|failed|timeout)" OR jsonPayload.level="ERROR")',
                    'severity>="ERROR"'
                ]
            },
            # Strategy 4: Specific application logs
            {
                'name': 'Application Logs',
                'filter': [
                    f'timestamp >= "{one_hour_ago.isoformat()}"',
                    'resource.type="cloud_run_revision"',
                    'resource.labels.service_name="netra-backend-staging"',
                    '(jsonPayload.logger!="" OR textPayload=~"(?i)(auth|database|websocket|agent)")'
                ]
            }
        ]

        for strategy in filter_strategies:
            filter_str = ' AND '.join(strategy['filter'])
            print(f"\n[STRATEGY] {strategy['name']}")
            print(f"[FILTER] {filter_str}")

            try:
                logs = []
                count = 0
                for entry in client.list_entries(
                    filter_=filter_str,
                    order_by=DESCENDING,
                    page_size=100
                ):
                    logs.append(parse_entry_with_content(entry))
                    count += 1
                    if count >= 100:  # Limit per strategy
                        break

                print(f"[RESULT] Found {len(logs)} entries")
                all_logs[strategy['name']] = logs

                # Show sample content
                if logs:
                    sample = logs[0]
                    print(f"[SAMPLE] {sample.get('timestamp')} - {sample.get('extracted_message', 'No message')[:100]}")

            except Exception as e:
                print(f"[ERROR] Strategy failed: {e}")
                all_logs[strategy['name']] = []

        return all_logs, one_hour_ago, now

    except Exception as e:
        print(f"[ERROR] {e}")
        return {}, None, None

def parse_entry_with_content(entry) -> Dict[str, Any]:
    """Parse log entry and extract meaningful content"""
    parsed = {
        'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
        'severity': entry.severity,
        'resource_labels': dict(entry.resource.labels) if entry.resource.labels else {},
        'labels': dict(entry.labels) if entry.labels else {},
        'insert_id': getattr(entry, 'insert_id', None),
        'extracted_message': None,
        'raw_text_payload': None,
        'raw_json_payload': None,
        'http_request': None
    }

    # Get raw payloads
    if hasattr(entry, 'text_payload') and entry.text_payload:
        parsed['raw_text_payload'] = entry.text_payload
        parsed['extracted_message'] = entry.text_payload

    if hasattr(entry, 'json_payload') and entry.json_payload:
        json_payload = dict(entry.json_payload)
        parsed['raw_json_payload'] = json_payload

        # Extract message from various JSON fields
        message_fields = ['message', 'msg', 'error', 'description', 'text']
        for field in message_fields:
            if field in json_payload and json_payload[field]:
                parsed['extracted_message'] = str(json_payload[field])
                break

        # Additional structured fields
        if 'level' in json_payload:
            parsed['log_level'] = json_payload['level']
        if 'logger' in json_payload:
            parsed['logger'] = json_payload['logger']
        if 'module' in json_payload:
            parsed['module'] = json_payload['module']

    # HTTP request info
    if hasattr(entry, 'http_request') and entry.http_request:
        parsed['http_request'] = {
            'method': entry.http_request.get('requestMethod'),
            'url': entry.http_request.get('requestUrl'),
            'status': entry.http_request.get('status'),
            'user_agent': entry.http_request.get('userAgent')
        }

    return parsed

def analyze_content_logs(all_logs):
    """Analyze logs with actual content"""
    analysis = {
        'collection_timestamp': datetime.now().isoformat(),
        'strategies': {},
        'all_messages': [],
        'error_patterns': [],
        'common_issues': defaultdict(int)
    }

    for strategy_name, logs in all_logs.items():
        strategy_analysis = {
            'count': len(logs),
            'messages': [],
            'severity_breakdown': defaultdict(int),
            'unique_messages': {}
        }

        message_counter = Counter()

        for log in logs:
            # Count by severity
            strategy_analysis['severity_breakdown'][log['severity']] += 1

            # Extract and count messages
            message = log.get('extracted_message', 'No message')
            if message and message != 'No message':
                message_counter[message] += 1
                strategy_analysis['messages'].append({
                    'timestamp': log['timestamp'],
                    'severity': log['severity'],
                    'message': message,
                    'logger': log.get('logger'),
                    'module': log.get('module')
                })

                analysis['all_messages'].append(message)

                # Look for error patterns
                if any(pattern in message.lower() for pattern in ['error', 'exception', 'failed', 'timeout', 'connection']):
                    analysis['error_patterns'].append({
                        'timestamp': log['timestamp'],
                        'severity': log['severity'],
                        'message': message[:200],
                        'strategy': strategy_name
                    })

        strategy_analysis['unique_messages'] = dict(message_counter.most_common(10))
        strategy_analysis['severity_breakdown'] = dict(strategy_analysis['severity_breakdown'])

        analysis['strategies'][strategy_name] = strategy_analysis

    # Overall message analysis
    all_message_counter = Counter(analysis['all_messages'])
    analysis['top_messages'] = dict(all_message_counter.most_common(20))

    return analysis

def main():
    """Main execution"""
    print("GCP Logs with Content - Last 1 Hour (netra-backend-staging)")
    print("=" * 70)

    if not setup_gcp_auth():
        return

    # Fetch logs
    all_logs, start_time, end_time = get_logs_with_content()

    if not any(all_logs.values()):
        print("[ERROR] No logs with content retrieved")
        return

    # Analyze
    analysis = analyze_content_logs(all_logs)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logs_file = project_root / f"gcp_logs_with_content_{timestamp}.json"
    with open(logs_file, 'w') as f:
        json.dump(all_logs, f, indent=2, default=str)

    analysis_file = project_root / f"gcp_content_analysis_{timestamp}.json"
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)

    # Print results
    print(f"\n[RESULTS] Summary")
    print("=" * 50)
    for strategy_name, strategy_data in analysis['strategies'].items():
        print(f"\n{strategy_name}: {strategy_data['count']} logs")
        if strategy_data['severity_breakdown']:
            print(f"  Severities: {strategy_data['severity_breakdown']}")

        if strategy_data['unique_messages']:
            print(f"  Top messages:")
            for i, (msg, count) in enumerate(list(strategy_data['unique_messages'].items())[:3], 1):
                print(f"    {i}. ({count}x) {msg[:80]}...")

    if analysis['error_patterns']:
        print(f"\n[ERROR PATTERNS] Found {len(analysis['error_patterns'])} error-related logs:")
        for i, error in enumerate(analysis['error_patterns'][:5], 1):
            print(f"  {i}. [{error['severity']}] {error['timestamp']} - {error['message'][:100]}...")

    print(f"\n[FILES] Results saved:")
    print(f"  Logs: {logs_file}")
    print(f"  Analysis: {analysis_file}")

if __name__ == '__main__':
    main()