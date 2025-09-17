#!/usr/bin/env python3
"""
Analysis of Existing GCP Log Data
Analyzes the most recent available log file to provide insights while waiting for current hour collection
"""

import json
import sys
from datetime import datetime
from collections import defaultdict, Counter

def analyze_log_file(file_path):
    """Analyze existing log file and provide comprehensive summary"""
    
    print("=" * 80)
    print("EXISTING GCP LOG ANALYSIS")
    print("=" * 80)
    print(f"File: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        
        print(f"Successfully loaded {len(logs)} log entries")
        
    except Exception as e:
        print(f"Error loading log file: {e}")
        return None
    
    if not logs:
        print("No log entries found")
        return None
    
    # Initialize analysis variables
    severity_counts = Counter()
    error_patterns = Counter()
    service_counts = Counter()
    timestamps = []
    critical_errors = []
    warnings = []
    
    # Pattern matching for error types
    error_keywords = {
        'Database Error': ['database', 'sql', 'postgres', 'clickhouse', 'connection pool'],
        'WebSocket Error': ['websocket', 'ws', 'socket', '1011', 'connection closed'],
        'Authentication Error': ['auth', 'jwt', 'token', 'oauth', 'unauthorized'],
        'Timeout Error': ['timeout', 'deadline', 'timed out'],
        'Resource Error': ['memory', 'cpu', 'resource', 'oom', 'killed'],
        'Permission Error': ['permission', 'access denied', 'forbidden', 'secret'],
        'Configuration Error': ['config', 'environment', 'variable', 'missing'],
        'Network Error': ['network', 'proxy', 'load balancer', 'ssl'],
        'Application Error': ['exception', 'traceback', 'error', 'failed']
    }
    
    # Process each log entry
    for log in logs:
        # Extract basic info
        timestamp = log.get('timestamp', '')
        severity = log.get('severity', 'UNKNOWN')
        service = log.get('resource', {}).get('labels', {}).get('service_name', 'unknown')
        
        # Count occurrences
        if timestamp:
            timestamps.append(timestamp)
        severity_counts[severity] += 1
        service_counts[service] += 1
        
        # Extract message
        message = ""
        if 'textPayload' in log:
            message = log['textPayload']
        elif 'jsonPayload' in log:
            jp = log['jsonPayload']
            message = jp.get('message', str(jp))
        
        # Categorize errors
        if message:
            message_lower = message.lower()
            pattern_found = False
            
            for pattern, keywords in error_keywords.items():
                if any(keyword in message_lower for keyword in keywords):
                    error_patterns[pattern] += 1
                    pattern_found = True
                    break
            
            if not pattern_found and severity in ['ERROR', 'WARNING', 'CRITICAL']:
                error_patterns['Other/Unclassified'] += 1
        
        # Collect critical issues
        if severity in ['ERROR', 'CRITICAL']:
            critical_errors.append({
                'timestamp': timestamp,
                'severity': severity,
                'service': service,
                'message': message[:300],
                'insertId': log.get('insertId', 'unknown')
            })
        elif severity == 'WARNING':
            warnings.append({
                'timestamp': timestamp,
                'service': service,
                'message': message[:200],
                'insertId': log.get('insertId', 'unknown')
            })
    
    # Generate summary report
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    
    print(f"\n📊 TOTAL LOG ENTRIES: {len(logs)}")
    
    # Timestamp range
    if timestamps:
        timestamps.sort()
        print(f"\n📅 TIMESTAMP RANGE:")
        print(f"  Earliest: {timestamps[0]}")
        print(f"  Latest:   {timestamps[-1]}")
        
        # Calculate span
        try:
            start_dt = datetime.fromisoformat(timestamps[0].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(timestamps[-1].replace('Z', '+00:00'))
            span = end_dt - start_dt
            print(f"  Duration: {span}")
        except:
            print("  Duration: Unable to calculate")
    
    # Severity breakdown
    print(f"\n⚠️ SEVERITY BREAKDOWN:")
    total_issues = 0
    for severity in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTICE']:
        count = severity_counts.get(severity, 0)
        if count > 0:
            print(f"  {severity}: {count:,}")
            if severity in ['CRITICAL', 'ERROR', 'WARNING']:
                total_issues += count
    
    print(f"\n  Total Issues (CRITICAL/ERROR/WARNING): {total_issues:,}")
    
    # Service breakdown
    print(f"\n🏷️ SERVICE BREAKDOWN:")
    for service, count in service_counts.most_common():
        print(f"  {service}: {count:,}")
    
    # Error pattern analysis
    if error_patterns:
        print(f"\n🔍 ERROR PATTERNS ({len(error_patterns)} types):")
        for pattern, count in error_patterns.most_common():
            print(f"  {pattern}: {count:,}")
    
    # Critical errors
    if critical_errors:
        print(f"\n🚨 CRITICAL/ERROR ISSUES ({len(critical_errors)} found):")
        
        # Group by pattern for better analysis
        critical_by_pattern = defaultdict(list)
        for error in critical_errors:
            message_lower = error['message'].lower()
            pattern = 'Other'
            
            for pattern_name, keywords in error_keywords.items():
                if any(keyword in message_lower for keyword in keywords):
                    pattern = pattern_name
                    break
            
            critical_by_pattern[pattern].append(error)
        
        # Show top patterns
        for pattern, errors in critical_by_pattern.items():
            print(f"\n  {pattern}: {len(errors)} occurrences")
            # Show sample
            for i, error in enumerate(errors[:2]):  # Show first 2 samples
                print(f"    [{i+1}] {error['severity']} at {error['timestamp']}")
                print(f"        {error['message']}")
    
    # Warning summary
    if warnings:
        print(f"\n⚠️ WARNING ISSUES ({len(warnings)} found):")
        warning_messages = Counter(w['message'][:100] for w in warnings)
        for msg, count in warning_messages.most_common(5):
            print(f"  [{count}x] {msg}...")
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    return {
        'total_entries': len(logs),
        'severity_counts': dict(severity_counts),
        'error_patterns': dict(error_patterns),
        'service_counts': dict(service_counts),
        'critical_errors': len(critical_errors),
        'warnings': len(warnings),
        'timestamp_range': {
            'earliest': timestamps[0] if timestamps else None,
            'latest': timestamps[-1] if timestamps else None
        }
    }

if __name__ == "__main__":
    # Analyze the most recent available log file
    log_file = "/Users/anthony/Desktop/netra-apex/gcp_logs_last_hour_20250915_175001.json"
    
    print("🔍 Analyzing existing GCP log data...")
    print("Note: This is the most recent available log file from Sept 15, 2025")
    print("For current hour logs, please run the collection scripts manually")
    
    result = analyze_log_file(log_file)
    
    if result:
        print(f"\n✅ Analysis completed successfully!")
        print(f"📊 Key findings:")
        print(f"  - Total entries: {result['total_entries']:,}")
        print(f"  - Critical/Error issues: {result['critical_errors']:,}")
        print(f"  - Warnings: {result['warnings']:,}")
        print(f"  - Error patterns identified: {len(result['error_patterns'])}")
    else:
        print("❌ Analysis failed")