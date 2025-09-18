#!/usr/bin/env python3
"""
Direct gcloud command execution to get logs with actual content
"""

import subprocess
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Setup
project_root = Path(__file__).parent

def setup_gcp_auth():
    """Setup GCP authentication"""
    key_path = project_root / "config" / "netra-staging-sa-key.json"
    if key_path.exists():
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(key_path)
        print(f"[AUTH] Using service account credentials: {key_path}")
        return True
    print("[ERROR] No GCP credentials found")
    return False

def run_gcloud_logs_command():
    """Run gcloud logging read command directly"""
    try:
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        print(f"[TIME] Current time (UTC): {now.isoformat()}")
        print(f"[TIME] Collecting from: {one_hour_ago.isoformat()}")

        # Construct gcloud command
        filter_str = (
            f'resource.type="cloud_run_revision" AND '
            f'resource.labels.service_name="netra-backend-staging" AND '
            f'timestamp>="{one_hour_ago.isoformat()}" AND '
            f'severity>="WARNING"'
        )

        cmd = [
            'gcloud', 'logging', 'read',
            filter_str,
            '--limit=200',
            '--format=json',
            f'--project=netra-staging'
        ]

        print(f"[COMMAND] {' '.join(cmd)}")

        # Execute command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            logs = json.loads(result.stdout) if result.stdout.strip() else []
            print(f"[SUCCESS] Retrieved {len(logs)} log entries")

            # Save raw output
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = project_root / f"gcloud_direct_logs_{timestamp}.json"

            with open(output_file, 'w') as f:
                json.dump(logs, f, indent=2)

            # Analyze content
            analyze_gcloud_logs(logs, output_file)

        else:
            print(f"[ERROR] gcloud command failed:")
            print(f"  Return code: {result.returncode}")
            print(f"  Stderr: {result.stderr}")
            print(f"  Stdout: {result.stdout}")

    except subprocess.TimeoutExpired:
        print("[ERROR] gcloud command timed out")
    except Exception as e:
        print(f"[ERROR] Exception: {e}")

def analyze_gcloud_logs(logs, output_file):
    """Analyze logs from gcloud direct output"""
    print(f"\n[ANALYSIS] Processing {len(logs)} log entries")

    by_severity = {}
    messages_with_content = []

    for log in logs:
        severity = log.get('severity', 'UNKNOWN')
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(log)

        # Extract meaningful content
        content = None

        # Check textPayload
        if log.get('textPayload'):
            content = log['textPayload']

        # Check jsonPayload
        elif log.get('jsonPayload'):
            json_payload = log['jsonPayload']
            for field in ['message', 'msg', 'error', 'description']:
                if json_payload.get(field):
                    content = json_payload[field]
                    break

        if content:
            messages_with_content.append({
                'timestamp': log.get('timestamp'),
                'severity': severity,
                'content': content,
                'resource': log.get('resource', {}).get('labels', {}),
                'labels': log.get('labels', {}),
                'insertId': log.get('insertId')
            })

    # Print summary
    print("\n[SUMMARY] Logs by Severity:")
    for severity, entries in by_severity.items():
        print(f"  {severity}: {len(entries)} entries")

    print(f"\n[CONTENT] Found {len(messages_with_content)} entries with actual content:")

    for i, msg in enumerate(messages_with_content[:10], 1):
        print(f"\n  {i}. [{msg['severity']}] {msg['timestamp']}")
        print(f"     Content: {msg['content'][:150]}...")
        if msg.get('labels'):
            print(f"     Labels: {msg['labels']}")

    # Save analysis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_file = project_root / f"gcloud_analysis_{timestamp}.json"

    analysis = {
        'summary': {
            'total_logs': len(logs),
            'by_severity': {k: len(v) for k, v in by_severity.items()},
            'with_content': len(messages_with_content)
        },
        'content_messages': messages_with_content
    }

    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)

    print(f"\n[SAVED] Files:")
    print(f"  Raw logs: {output_file}")
    print(f"  Analysis: {analysis_file}")

    return analysis

def main():
    """Main execution"""
    print("Direct gcloud Logs Collection - Last 1 Hour")
    print("=" * 60)

    if not setup_gcp_auth():
        return

    run_gcloud_logs_command()

if __name__ == '__main__':
    main()