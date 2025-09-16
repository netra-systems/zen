#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Logs HTTP Collector
Alternative method to collect logs using HTTP API when gcloud CLI is not available
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# Handle Windows encoding issues
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_access_token_from_service_account():
    """Get access token from service account credentials"""
    try:
        import jwt
        import time

        # Load service account key
        key_path = project_root / "config" / "netra-deployer-netra-staging.json"
        if not key_path.exists():
            print("❌ Service account key not found")
            return None

        with open(key_path, 'r') as f:
            credentials = json.load(f)

        # Create JWT
        now = int(time.time())
        payload = {
            'iss': credentials['client_email'],
            'scope': 'https://www.googleapis.com/auth/logging.read',
            'aud': 'https://oauth2.googleapis.com/token',
            'exp': now + 3600,
            'iat': now
        }

        # Sign JWT
        token = jwt.encode(payload, credentials['private_key'], algorithm='RS256')

        # Exchange JWT for access token
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': token
        }

        req = urllib.request.Request(
            'https://oauth2.googleapis.com/token',
            data=urllib.parse.urlencode(data).encode(),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            return result.get('access_token')

    except ImportError:
        print("❌ PyJWT library not available. Cannot get access token.")
        return None
    except Exception as e:
        print(f"❌ Error getting access token: {e}")
        return None

def fetch_logs_via_http_api(access_token):
    """Fetch logs via GCP Logging HTTP API"""
    try:
        # Build the request body
        request_body = {
            "filter": 'resource.type="cloud_run_revision" AND resource.labels.service_name="netra-backend-staging" AND severity>=WARNING AND timestamp>="2025-09-16T01:00:00Z" AND timestamp<="2025-09-16T02:06:58Z"',
            "orderBy": "timestamp desc",
            "pageSize": 1000
        }

        url = "https://logging.googleapis.com/v2/entries:list"

        req = urllib.request.Request(
            url,
            data=json.dumps(request_body).encode(),
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
        )

        print("🔍 Fetching logs via HTTP API...")

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            entries = result.get('entries', [])

            print(f"✅ Retrieved {len(entries)} log entries")
            return entries

    except Exception as e:
        print(f"❌ Error fetching logs via HTTP API: {e}")
        return []

def format_log_entry_for_output(entry):
    """Format a single log entry into the requested format"""
    formatted = {}

    # Basic fields
    if 'timestamp' in entry:
        formatted['timestamp'] = entry['timestamp']
    if 'severity' in entry:
        formatted['severity'] = entry['severity']

    # Resource information
    if 'resource' in entry:
        formatted['resource'] = entry['resource']

    # JSON payload (preferred format)
    if 'jsonPayload' in entry:
        formatted['jsonPayload'] = entry['jsonPayload']

    # Text payload (fallback)
    elif 'textPayload' in entry:
        formatted['textPayload'] = entry['textPayload']

    # HTTP request info
    if 'httpRequest' in entry:
        formatted['httpRequest'] = entry['httpRequest']

    # Labels
    if 'labels' in entry:
        formatted['labels'] = entry['labels']

    # Trace information
    if 'trace' in entry:
        formatted['trace'] = entry['trace']
    if 'spanId' in entry:
        formatted['spanId'] = entry['spanId']

    return formatted

def generate_detailed_report(log_entries):
    """Generate a detailed report from the log entries"""
    if not log_entries:
        return "No logs found for the specified time range and criteria."

    output = []
    output.append("=" * 80)
    output.append("GCP LOGS COLLECTION REPORT")
    output.append("=" * 80)
    output.append(f"Service: netra-backend-staging")
    output.append(f"Time Range: 2025-09-15 18:00:00 PDT to 2025-09-15 19:06:58 PDT")
    output.append(f"UTC Range: 2025-09-16 01:00:00 UTC to 2025-09-16 02:06:58 UTC")
    output.append(f"Severity: WARNING and ERROR levels")
    output.append(f"Total Entries: {len(log_entries)}")
    output.append("=" * 80)
    output.append("")

    # Group by severity
    by_severity = {}
    for entry in log_entries:
        severity = entry.get('severity', 'UNKNOWN')
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(entry)

    # Display summary by severity
    output.append("SEVERITY SUMMARY:")
    for severity in ['ERROR', 'WARNING', 'NOTICE', 'INFO']:
        if severity in by_severity:
            output.append(f"  • {severity}: {len(by_severity[severity])} entries")
    output.append("")

    # Display detailed entries
    for severity in ['ERROR', 'WARNING', 'NOTICE', 'INFO']:
        if severity in by_severity:
            output.append(f"\n{'='*20} {severity} LOGS ({len(by_severity[severity])} entries) {'='*20}")

            for i, entry in enumerate(by_severity[severity], 1):
                formatted_entry = format_log_entry_for_output(entry)

                output.append(f"\n--- {severity} LOG #{i} ---")
                output.append(f"Timestamp: {formatted_entry.get('timestamp', 'N/A')}")
                output.append(f"Severity: {formatted_entry.get('severity', 'N/A')}")

                # Format JSON payload with proper structure
                if 'jsonPayload' in formatted_entry:
                    output.append("jsonPayload:")
                    json_payload = formatted_entry['jsonPayload']

                    # Extract context if present
                    if any(key in json_payload for key in ['name', 'service', 'module', 'logger']):
                        output.append("  context:")
                        for key in ['name', 'service', 'module', 'logger']:
                            if key in json_payload:
                                output.append(f"    {key}: \"{json_payload[key]}\"")

                    # Extract labels if present
                    if any(key in json_payload for key in ['function', 'line', 'module', 'method']):
                        output.append("  labels:")
                        for key in ['function', 'line', 'module', 'method']:
                            if key in json_payload:
                                output.append(f"    {key}: \"{json_payload[key]}\"")

                    # Extract message
                    message = json_payload.get('message') or json_payload.get('msg') or json_payload.get('error')
                    if message:
                        output.append(f"  message: \"{message}\"")

                    # Include other fields
                    excluded_keys = {'name', 'service', 'module', 'logger', 'function', 'line', 'method', 'message', 'msg', 'error'}
                    for key, value in json_payload.items():
                        if key not in excluded_keys:
                            output.append(f"  {key}: {json.dumps(value) if isinstance(value, (dict, list)) else repr(value)}")

                # Format text payload
                elif 'textPayload' in formatted_entry:
                    output.append(f"textPayload: \"{formatted_entry['textPayload']}\"")

                # Additional fields
                if 'httpRequest' in formatted_entry:
                    output.append("httpRequest:")
                    for key, value in formatted_entry['httpRequest'].items():
                        if value is not None:
                            output.append(f"  {key}: {repr(value)}")

                if 'trace' in formatted_entry:
                    output.append(f"trace: \"{formatted_entry['trace']}\"")

                if 'spanId' in formatted_entry:
                    output.append(f"spanId: \"{formatted_entry['spanId']}\"")

                output.append("")

    return "\n".join(output)

def main():
    """Main execution function"""
    print("🚀 Starting GCP Log Collection via HTTP API")

    # Try to get access token
    access_token = get_access_token_from_service_account()
    if not access_token:
        print("❌ Could not obtain access token. Falling back to existing log analysis.")

        # Read the existing log analysis that covers our time period
        existing_log = project_root / "gcp" / "log-gardener" / "GCP-LOG-GARDENER-WORKLOG-last-1-hour-20250915-1900PDT.md"
        if existing_log.exists():
            print(f"📄 Reading existing log analysis: {existing_log}")
            with open(existing_log, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        else:
            return "❌ No access token available and no existing log analysis found."

    # Fetch logs
    log_entries = fetch_logs_via_http_api(access_token)

    if not log_entries:
        print("❌ No logs retrieved via API. Checking existing analysis...")
        existing_log = project_root / "gcp" / "log-gardener" / "GCP-LOG-GARDENER-WORKLOG-last-1-hour-20250915-1900PDT.md"
        if existing_log.exists():
            with open(existing_log, 'r', encoding='utf-8') as f:
                return f.read()
        return "❌ No logs found via API and no existing analysis available."

    # Generate detailed report
    detailed_report = generate_detailed_report(log_entries)

    # Save the report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = project_root / "gcp" / "log-gardener" / f"GCP-HTTP-LOGS-{timestamp}.md"

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(detailed_report)

    print(f"📄 Report saved to: {output_file}")

    # Also save raw JSON
    json_file = project_root / "gcp" / "log-gardener" / f"raw_logs_http_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(log_entries, f, indent=2, default=str)

    print(f"📊 Raw JSON saved to: {json_file}")

    return detailed_report

if __name__ == '__main__':
    result = main()
    print("\n" + "="*60)
    print("COLLECTION COMPLETE")
    print("="*60)