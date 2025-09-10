#!/usr/bin/env python3
"""
GCP Log Fetcher for Staging Issues Audit
Fetches recent logs from GCP staging environment focused on errors, warnings, and notices
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env

def setup_gcp_auth():
    """Setup GCP authentication using existing credentials"""
    # Check for service account key
    key_path = project_root / "config" / "netra-staging-sa-key.json"
    if key_path.exists():
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(key_path)
        print(f"✓ Using service account credentials: {key_path}")
        return True
    
    # Try other credential paths
    alt_paths = [
        project_root / "config" / "netra-staging-7a1059b7cf26.json",
        Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
    ]
    
    for path in alt_paths:
        if path.exists():
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(path)
            print(f"✓ Using credentials: {path}")
            return True
    
    print("❌ No GCP credentials found")
    return False

def get_recent_gcp_logs(project_id: str = "netra-staging", hours_back: int = 24):
    """Fetch recent logs from GCP Cloud Logging"""
    try:
        from google.cloud import logging as cloud_logging
        from google.cloud.logging_v2 import DESCENDING
        
        client = cloud_logging.Client(project=project_id)
        
        # Calculate time filter
        hours_ago = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        time_filter = f'timestamp >= "{hours_ago.isoformat()}"'
        
        # Focus on backend service errors, warnings, and notices
        service_filters = [
            'resource.type="cloud_run_revision"',
            'resource.labels.service_name="netra-backend"',
            'resource.labels.service_name="netra-auth"',
            'resource.labels.service_name="netra-frontend"'
        ]
        
        # Priority order: ERROR > WARNING > INFO (for notices)
        severity_filters = [
            'severity>=ERROR',
            'severity="WARNING"', 
            'severity="NOTICE"',
            'severity="INFO"'
        ]
        
        # Look for specific issue patterns
        issue_patterns = [
            'textPayload=~"(?i)(error|exception|failed|timeout|connection.*refused|unable.*connect)"',
            'textPayload=~"(?i)(warning|deprecated|retry|fallback)"',
            'jsonPayload.message=~"(?i)(error|exception|failed|timeout|connection.*refused)"',
            'jsonPayload.level="ERROR"',
            'jsonPayload.level="WARNING"',
            'httpRequest.status>=400'
        ]
        
        logs_by_severity = defaultdict(list)
        
        print(f"🔍 Fetching logs from {project_id} for last {hours_back} hours...")
        
        # Fetch ERROR logs first (highest priority)
        for severity in ['ERROR', 'WARNING', 'NOTICE', 'INFO']:
            print(f"  📋 Checking {severity} logs...")
            
            try:
                filters = [
                    time_filter,
                    f'severity="{severity}"',
                    '(' + ' OR '.join(service_filters) + ')'
                ]
                full_filter = ' AND '.join(filters)
                
                count = 0
                for entry in client.list_entries(
                    filter_=full_filter,
                    order_by=DESCENDING,
                    page_size=100
                ):
                    logs_by_severity[severity].append(parse_log_entry(entry))
                    count += 1
                    if count >= 100:  # Limit per severity
                        break
                
                print(f"    ✓ Found {len(logs_by_severity[severity])} {severity} entries")
                
            except Exception as e:
                print(f"    ❌ Error fetching {severity} logs: {e}")
        
        return logs_by_severity
        
    except ImportError:
        print("❌ google-cloud-logging not installed")
        return {}
    except Exception as e:
        print(f"❌ Error fetching logs: {e}")
        return {}

def parse_log_entry(entry) -> Dict[str, Any]:
    """Parse log entry into structured format"""
    parsed = {
        'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
        'severity': entry.severity,
        'resource': {
            'type': entry.resource.type,
            'labels': dict(entry.resource.labels) if entry.resource.labels else {}
        },
        'labels': dict(entry.labels) if entry.labels else {},
        'text_payload': getattr(entry, 'payload', None) if isinstance(getattr(entry, 'payload', None), str) else None,
        'json_payload': dict(entry.payload) if hasattr(entry, 'payload') and isinstance(entry.payload, dict) else {},
        'trace': getattr(entry, 'trace', None),
        'span_id': getattr(entry, 'span_id', None)
    }
    
    # Handle different payload types
    if hasattr(entry, 'text_payload'):
        parsed['text_payload'] = entry.text_payload
    elif hasattr(entry, 'json_payload') and entry.json_payload:
        parsed['json_payload'] = dict(entry.json_payload)
    
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

def analyze_logs_for_issues(logs_by_severity: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """Analyze logs to identify the most critical issues"""
    analysis = {
        'timestamp': datetime.now().isoformat(),
        'total_logs': sum(len(logs) for logs in logs_by_severity.values()),
        'issues_by_severity': {},
        'top_errors': [],
        'recurring_patterns': [],
        'service_issues': defaultdict(list),
        'http_errors': [],
        'connection_issues': [],
        'database_issues': [],
        'websocket_issues': [],
        'auth_issues': []
    }
    
    # Error patterns to look for
    error_patterns = {
        'connection': r'(?i)connection.*(?:refused|timeout|reset|failed|lost)',
        'database': r'(?i)(?:postgres|clickhouse|redis|database|sql).*(?:error|failed|timeout|connection)',
        'auth': r'(?i)(?:auth|token|jwt|oauth|login|permission).*(?:error|failed|invalid|expired)',
        'websocket': r'(?i)(?:websocket|ws).*(?:error|failed|connection|closed)',
        'timeout': r'(?i)timeout|timed.out',
        'memory': r'(?i)(?:memory|oom|out.of.memory)',
        'startup': r'(?i)(?:startup|initialization|bootstrap).*(?:error|failed)',
        'deployment': r'(?i)(?:deployment|deploy|build).*(?:error|failed)'
    }
    
    all_messages = []
    
    # Process each severity level
    for severity, logs in logs_by_severity.items():
        issue_counts = Counter()
        
        for log in logs:
            message = extract_log_message(log)
            all_messages.append(message)
            
            # Service identification
            service_name = log.get('resource', {}).get('labels', {}).get('service_name', 'unknown')
            
            # Check for specific error patterns
            for pattern_name, pattern in error_patterns.items():
                import re
                if re.search(pattern, message):
                    issue_counts[pattern_name] += 1
                    analysis['service_issues'][service_name].append({
                        'type': pattern_name,
                        'message': message[:200],
                        'timestamp': log.get('timestamp'),
                        'severity': severity
                    })
            
            # HTTP errors
            if log.get('http_request', {}).get('status', 0) >= 400:
                analysis['http_errors'].append({
                    'status': log['http_request']['status'],
                    'url': log['http_request'].get('url', ''),
                    'method': log['http_request'].get('method', ''),
                    'timestamp': log.get('timestamp'),
                    'service': service_name
                })
        
        analysis['issues_by_severity'][severity] = dict(issue_counts.most_common(10))
    
    # Find recurring patterns
    message_counter = Counter(all_messages)
    analysis['recurring_patterns'] = [
        {'message': msg[:200], 'count': count}
        for msg, count in message_counter.most_common(10)
        if count > 1
    ]
    
    return analysis

def extract_log_message(log: Dict) -> str:
    """Extract meaningful message from log entry"""
    # Try JSON payload first
    json_payload = log.get('json_payload', {})
    if json_payload:
        if 'message' in json_payload:
            return str(json_payload['message'])
        elif 'msg' in json_payload:
            return str(json_payload['msg'])
        elif 'error' in json_payload:
            return str(json_payload['error'])
    
    # Try text payload
    if log.get('text_payload'):
        return str(log['text_payload'])
    
    # Fallback to JSON dump
    if json_payload:
        return json.dumps(json_payload)[:200]
    
    return "No message content"

def identify_top_issue(analysis: Dict) -> Optional[Dict]:
    """Identify the single most critical issue to focus on"""
    
    # Priority order: ERROR > WARNING > NOTICE > INFO
    severity_priority = ['ERROR', 'WARNING', 'NOTICE', 'INFO']
    
    for severity in severity_priority:
        issues = analysis['issues_by_severity'].get(severity, {})
        if issues:
            # Get the most frequent issue type
            top_issue_type = max(issues.items(), key=lambda x: x[1])
            
            # Find example from service issues
            for service, service_issues in analysis['service_issues'].items():
                for issue in service_issues:
                    if issue['type'] == top_issue_type[0] and issue['severity'] == severity:
                        return {
                            'type': top_issue_type[0],
                            'severity': severity,
                            'count': top_issue_type[1],
                            'service': service,
                            'example_message': issue['message'],
                            'timestamp': issue['timestamp'],
                            'description': f"{top_issue_type[0].title()} issues occurring {top_issue_type[1]} times in {severity} logs"
                        }
    
    # Fallback to HTTP errors
    if analysis['http_errors']:
        http_error = analysis['http_errors'][0]
        return {
            'type': 'http_error',
            'severity': 'ERROR',
            'count': len(analysis['http_errors']),
            'service': http_error['service'],
            'example_message': f"HTTP {http_error['status']} on {http_error['url']}",
            'timestamp': http_error['timestamp'],
            'description': f"HTTP {http_error['status']} errors occurring {len(analysis['http_errors'])} times"
        }
    
    return None

def main():
    """Main execution"""
    print("🚀 Starting GCP Staging Log Audit - Cycle 1")
    
    if not setup_gcp_auth():
        return
    
    # Fetch logs
    logs = get_recent_gcp_logs(hours_back=6)  # Start with recent 6 hours
    
    if not logs:
        print("❌ No logs retrieved")
        return
    
    # Analyze for issues
    analysis = analyze_logs_for_issues(logs)
    
    # Create timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save analysis
    analysis_file = project_root / "audit" / "staging" / "auto-solve-loop" / f"cycle1_analysis_{timestamp}.json"
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"📊 Analysis saved to: {analysis_file}")
    
    # Identify top issue
    top_issue = identify_top_issue(analysis)
    
    if top_issue:
        print(f"\n🎯 IDENTIFIED TOP ISSUE:")
        print(f"   Type: {top_issue['type']}")
        print(f"   Severity: {top_issue['severity']}")
        print(f"   Count: {top_issue['count']}")
        print(f"   Service: {top_issue['service']}")
        print(f"   Description: {top_issue['description']}")
        print(f"   Example: {top_issue['example_message'][:100]}...")
        
        return top_issue
    else:
        print("✅ No critical issues identified in recent logs")
        return None

if __name__ == '__main__':
    main()