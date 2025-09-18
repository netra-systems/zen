#!/usr/bin/env python3
"""
Analyze GCP logs from the current log files
Focus on WARNING, ERROR, and CRITICAL logs from the last hour
"""

import json
import sys
from datetime import datetime, timedelta, UTC
from collections import defaultdict

def load_logs(file_path):
    """Load logs from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return []

def filter_logs_by_time_and_severity(logs, hours_back=1):
    """Filter logs to last N hours and WARNING+ severity"""
    now = datetime.now(UTC)
    cutoff_time = now - timedelta(hours=hours_back)
    
    filtered_logs = []
    
    for log in logs:
        # Parse timestamp
        timestamp_str = log.get('timestamp', '')
        if not timestamp_str:
            continue
            
        try:
            # Handle different timestamp formats
            if timestamp_str.endswith('Z'):
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.fromisoformat(timestamp_str)
            
            # Convert to UTC if needed
            if timestamp.tzinfo:
                timestamp = timestamp.utctimetimestamp()
                timestamp = datetime.utcfromtimestamp(timestamp.timestamp())
            
            # Check if within time range
            if timestamp >= cutoff_time:
                # Check severity
                severity = log.get('severity', 'INFO')
                if severity in ['WARNING', 'ERROR', 'CRITICAL']:
                    filtered_logs.append(log)
                    
        except Exception as e:
            print(f"Error parsing timestamp {timestamp_str}: {e}")
            continue
    
    return filtered_logs

def categorize_error(message):
    """Categorize error messages into types"""
    if not message:
        return "Unknown"
        
    message_lower = message.lower()
    
    if any(keyword in message_lower for keyword in ['startup', 'failed', 'exit']):
        return "Startup/Exit Error"
    elif any(keyword in message_lower for keyword in ['database', 'sql', 'postgres', 'clickhouse', 'connection']):
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

def analyze_logs(logs):
    """Analyze and group logs by error type and severity"""
    print("=" * 80)
    print("GCP BACKEND LOGS ANALYSIS - WARNING, ERROR, CRITICAL")
    print("=" * 80)
    
    if not logs:
        print("No warning/error/critical logs found in the specified time range")
        return
    
    # Group logs by severity and error type
    logs_by_severity = defaultdict(list)
    error_types = defaultdict(list)
    
    for log in logs:
        severity = log.get('severity', 'UNKNOWN')
        logs_by_severity[severity].append(log)
        
        # Extract message
        message = ""
        if 'textPayload' in log:
            message = log['textPayload']
        elif 'jsonPayload' in log:
            jp = log['jsonPayload']
            message = jp.get('message', str(jp))
        
        error_type = categorize_error(message)
        error_types[error_type].append({
            'log': log,
            'message': message,
            'severity': severity
        })
    
    # Summary
    total_logs = len(logs)
    critical_count = len(logs_by_severity.get('CRITICAL', []))
    error_count = len(logs_by_severity.get('ERROR', []))
    warning_count = len(logs_by_severity.get('WARNING', []))
    
    print(f"\n📊 SUMMARY:")
    print(f"  Total WARNING+ logs: {total_logs}")
    print(f"  CRITICAL: {critical_count}")
    print(f"  ERROR: {error_count}")
    print(f"  WARNING: {warning_count}")
    
    # Show logs by severity
    for severity in ['CRITICAL', 'ERROR', 'WARNING']:
        if severity in logs_by_severity:
            severity_logs = logs_by_severity[severity]
            print(f"\n{'🚨' if severity in ['CRITICAL', 'ERROR'] else '⚠️'} {severity} LOGS ({len(severity_logs)} found):")
            
            for i, log in enumerate(severity_logs[:10]):  # Show first 10
                timestamp = log.get('timestamp', 'No timestamp')
                service = log.get('resource', {}).get('labels', {}).get('service_name', 'unknown')
                
                # Extract message
                message = ""
                context = {}
                traceback = ""
                
                if 'textPayload' in log:
                    message = log['textPayload']
                elif 'jsonPayload' in log:
                    jp = log['jsonPayload']
                    message = jp.get('message', '')
                    context = jp.get('context', {})
                    traceback = jp.get('traceback', '')
                
                print(f"\n  [{i+1}] {timestamp}")
                print(f"      Service: {service}")
                print(f"      Message: {message[:200]}{'...' if len(message) > 200 else ''}")
                
                if context:
                    print(f"      Context: {context}")
                
                if traceback:
                    print(f"      Traceback: {traceback[:300]}{'...' if len(traceback) > 300 else ''}")
                
                # Show HTTP request info if available
                if 'httpRequest' in log:
                    http_req = log['httpRequest']
                    print(f"      HTTP: {http_req.get('requestMethod', '')} {http_req.get('requestUrl', '')} -> {http_req.get('status', '')}")
            
            if len(severity_logs) > 10:
                print(f"\n      ... and {len(severity_logs) - 10} more {severity} logs")
    
    # Show error types breakdown
    print(f"\n🔍 ERROR TYPES BREAKDOWN:")
    for error_type, error_list in sorted(error_types.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {error_type}: {len(error_list)} occurrences")
        
        # Show a few examples for each error type
        examples = error_list[:3]
        for j, example in enumerate(examples):
            print(f"    [{j+1}] {example['severity']}: {example['message'][:100]}{'...' if len(example['message']) > 100 else ''}")
    
    print("\n" + "=" * 80)

def main():
    """Main function to analyze recent log files"""
    
    # List of potential log files to check
    log_files = [
        "/Users/anthony/Desktop/netra-apex/gcp_logs_backend.json",
        "/Users/anthony/Desktop/netra-apex/netra_backend_logs_20250915_223711.json",
        "/Users/anthony/Desktop/netra-apex/gcp_backend_logs_last_1hour_20250915_183212.json"
    ]
    
    all_logs = []
    
    print("🔍 Loading log files...")
    
    for log_file in log_files:
        print(f"  Checking: {log_file}")
        logs = load_logs(log_file)
        if logs:
            print(f"    ✅ Loaded {len(logs)} logs")
            all_logs.extend(logs)
        else:
            print(f"    ❌ No logs found or file doesn't exist")
    
    if not all_logs:
        print("❌ No logs found in any file!")
        return
    
    print(f"\n📊 Total logs loaded: {len(all_logs)}")
    
    # Filter to last hour and WARNING+ severity
    print("🔍 Filtering to last 1 hour, WARNING+ severity...")
    recent_warning_logs = filter_logs_by_time_and_severity(all_logs, hours_back=1)
    
    print(f"📊 Found {len(recent_warning_logs)} WARNING+ logs in last hour")
    
    # Analyze the filtered logs
    analyze_logs(recent_warning_logs)
    
    # Also show all WARNING+ logs (not just last hour) for completeness
    print(f"\n" + "=" * 80)
    print("ALL WARNING+ LOGS (NOT TIME FILTERED)")
    print("=" * 80)
    
    all_warning_logs = []
    for log in all_logs:
        severity = log.get('severity', 'INFO')
        if severity in ['WARNING', 'ERROR', 'CRITICAL']:
            all_warning_logs.append(log)
    
    print(f"📊 Found {len(all_warning_logs)} total WARNING+ logs")
    
    if all_warning_logs:
        # Show breakdown by severity
        severity_counts = defaultdict(int)
        for log in all_warning_logs:
            severity = log.get('severity', 'UNKNOWN')
            severity_counts[severity] += 1
        
        print(f"\n📊 SEVERITY BREAKDOWN (ALL TIME):")
        for severity in ['CRITICAL', 'ERROR', 'WARNING']:
            count = severity_counts.get(severity, 0)
            if count > 0:
                print(f"  {severity}: {count}")
        
        # Show most recent errors
        print(f"\n🕐 MOST RECENT WARNING+ LOGS (up to 15):")
        
        # Sort by timestamp (most recent first)
        sorted_logs = sorted(all_warning_logs, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        for i, log in enumerate(sorted_logs[:15]):
            timestamp = log.get('timestamp', 'No timestamp')
            severity = log.get('severity', 'UNKNOWN')
            
            # Extract message
            message = ""
            if 'textPayload' in log:
                message = log['textPayload']
            elif 'jsonPayload' in log:
                jp = log['jsonPayload']
                message = jp.get('message', '')
            
            print(f"\n  [{i+1}] {timestamp} - {severity}")
            print(f"      {message[:150]}{'...' if len(message) > 150 else ''}")

if __name__ == "__main__":
    main()