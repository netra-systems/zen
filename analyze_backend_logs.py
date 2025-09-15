#!/usr/bin/env python3
"""
GCP Backend Logs Analyzer
Analyzes GCP logs from backend-staging service to extract meaningful error information
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse GCP timestamp format"""
    try:
        # Remove 'Z' and parse
        clean_timestamp = timestamp_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean_timestamp)
    except Exception:
        return datetime.now()

def extract_error_info(log_entry: Dict[str, Any]) -> Dict[str, Any]:
    """Extract meaningful error information from a log entry"""
    info = {
        'timestamp': log_entry.get('timestamp', ''),
        'severity': log_entry.get('severity', ''),
        'message': '',
        'context': {},
        'traceback': '',
        'source': '',
        'labels': {}
    }

    # Extract message from various possible locations
    if 'textPayload' in log_entry:
        info['message'] = log_entry['textPayload']
    elif 'jsonPayload' in log_entry:
        json_payload = log_entry['jsonPayload']

        # Try different message fields
        for msg_field in ['message', 'msg', 'error', 'description']:
            if msg_field in json_payload:
                info['message'] = str(json_payload[msg_field])
                break

        # Extract context
        for context_field in ['context', 'extra', 'data']:
            if context_field in json_payload:
                info['context'] = json_payload[context_field]

        # Extract traceback
        for tb_field in ['traceback', 'stack_trace', 'exception', 'exc_info']:
            if tb_field in json_payload:
                info['traceback'] = str(json_payload[tb_field])

        # Extract labels
        if 'labels' in json_payload:
            info['labels'] = json_payload['labels']

    # Extract source information
    if 'sourceLocation' in log_entry:
        source_loc = log_entry['sourceLocation']
        info['source'] = f"{source_loc.get('file', '')}:{source_loc.get('line', '')}"

    return info

def group_similar_errors(errors: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group similar errors together"""
    groups = defaultdict(list)

    for error in errors:
        # Create a key based on the error message pattern
        message = error['message']

        # Simple grouping by first few words or error type
        if message:
            # Extract first 50 characters or until first newline
            key_message = message.split('\n')[0][:50]
            # Remove timestamps and variable parts
            key_message = key_message.replace('2025-09-15', 'YYYY-MM-DD')
            key_message = key_message.replace('2025-09-14', 'YYYY-MM-DD')
            groups[key_message].append(error)
        else:
            groups['UNKNOWN_ERROR'].append(error)

    return groups

def analyze_logs(log_file_path: str) -> None:
    """Main analysis function"""
    try:
        with open(log_file_path, 'r') as f:
            logs = json.load(f)

        if not logs:
            print("No logs found in the specified time range.")
            return

        print(f"📊 ANALYSIS OF {len(logs)} LOG ENTRIES")
        print("=" * 50)

        # Extract error information
        errors = []
        severity_counts = defaultdict(int)

        for log_entry in logs:
            error_info = extract_error_info(log_entry)
            errors.append(error_info)
            severity_counts[error_info['severity']] += 1

        # Print severity summary
        print("\n🚨 SEVERITY BREAKDOWN:")
        for severity, count in sorted(severity_counts.items()):
            print(f"  {severity}: {count}")

        # Group similar errors
        error_groups = group_similar_errors(errors)

        print(f"\n📝 ERROR GROUPS ({len(error_groups)} unique patterns):")
        print("-" * 50)

        for i, (error_pattern, error_list) in enumerate(sorted(error_groups.items(), key=lambda x: len(x[1]), reverse=True), 1):
            print(f"\n{i}. ERROR PATTERN: {error_pattern}")
            print(f"   Occurrences: {len(error_list)}")

            # Show first occurrence details
            first_error = error_list[0]
            print(f"   Severity: {first_error['severity']}")
            print(f"   First seen: {first_error['timestamp']}")

            if first_error['message']:
                print(f"   Full message: {first_error['message'][:200]}...")

            if first_error['context']:
                print(f"   Context: {first_error['context']}")

            if first_error['traceback']:
                print(f"   Traceback: {first_error['traceback'][:300]}...")

            if first_error['source']:
                print(f"   Source: {first_error['source']}")

            # Show timestamps of all occurrences
            if len(error_list) > 1:
                timestamps = [e['timestamp'] for e in error_list]
                print(f"   All timestamps: {', '.join(timestamps[:5])}{'...' if len(timestamps) > 5 else ''}")

        # Time analysis
        print("\n⏰ TIME ANALYSIS:")
        print("-" * 30)

        # Sort errors by timestamp
        sorted_errors = sorted(errors, key=lambda x: parse_timestamp(x['timestamp']))

        if sorted_errors:
            print(f"First error: {sorted_errors[0]['timestamp']}")
            print(f"Last error: {sorted_errors[-1]['timestamp']}")

            # Count errors per 10-minute window
            time_buckets = defaultdict(int)
            for error in sorted_errors:
                dt = parse_timestamp(error['timestamp'])
                bucket = dt.replace(minute=(dt.minute // 10) * 10, second=0, microsecond=0)
                time_buckets[bucket] += 1

            print("\nError frequency (10-minute windows):")
            for bucket, count in sorted(time_buckets.items()):
                print(f"  {bucket.strftime('%H:%M')}: {count} errors")

        print("\n" + "=" * 50)
        print("Analysis complete!")

    except FileNotFoundError:
        print(f"Error: Log file not found at {log_file_path}")
        print("Please run the fetch script first:")
        print("  bash fetch_and_analyze_logs.sh")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in log file {log_file_path}")
    except Exception as e:
        print(f"Error analyzing logs: {e}")

if __name__ == "__main__":
    log_file = "/tmp/backend_logs_last_hour.json"
    if len(sys.argv) > 1:
        log_file = sys.argv[1]

    analyze_logs(log_file)