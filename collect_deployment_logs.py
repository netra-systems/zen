#!/usr/bin/env python3
"""
Collect recent logs from GCP staging services to diagnose deployment issues.
"""
import subprocess
import json
import sys
from datetime import datetime, timedelta, UTC

def run_gcloud_command(command, timeout=30):
    """Run a gcloud command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"ERROR: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out"
    except Exception as e:
        return f"ERROR: {str(e)}"

def collect_service_logs(service_name, minutes_back=15, max_entries=50):
    """Collect recent logs for a service."""
    print(f"\n{'='*60}")
    print(f"Collecting logs for {service_name} (last {minutes_back} minutes)")
    print('='*60)

    # Calculate timestamp
    now = datetime.now(UTC)
    start_time = now - timedelta(minutes=minutes_back)
    start_timestamp = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Build log filter
    log_filter = f'''
resource.type="cloud_run_revision"
resource.labels.service_name="{service_name}"
timestamp>="{start_timestamp}"
(severity="ERROR" OR severity="WARNING" OR severity="CRITICAL" OR textPayload:"exit" OR textPayload:"failed" OR textPayload:"error")
'''.strip().replace('\n', ' ')

    # gcloud logging read command
    command = f'''gcloud logging read '{log_filter}' --project=netra-staging --limit={max_entries} --format="value(timestamp,severity,textPayload,jsonPayload.message)"'''

    output = run_gcloud_command(command, timeout=60)

    if "ERROR:" in output:
        print(f"Failed to collect logs: {output}")
        return

    if not output.strip():
        print("No error/warning logs found in the specified time period.")
        return

    lines = output.strip().split('\n')
    print(f"Found {len(lines)} log entries:")

    for i, line in enumerate(lines[-20:], 1):  # Show last 20 entries
        if line.strip():
            parts = line.split('\t', 3)
            if len(parts) >= 3:
                timestamp = parts[0] if len(parts) > 0 else 'N/A'
                severity = parts[1] if len(parts) > 1 else 'N/A'
                message = parts[2] if len(parts) > 2 else 'N/A'
                print(f"\n[{i:2d}] {timestamp} [{severity}]")
                print(f"     {message[:200]}{'...' if len(message) > 200 else ''}")

def main():
    """Main function to collect deployment logs."""
    print(f"GCP Staging Deployment Log Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Services to check
    services = [
        "netra-backend-staging",
        "netra-auth-service"
    ]

    for service in services:
        collect_service_logs(service)

    print(f"\n{'='*80}")
    print("Log collection complete. Check for patterns in startup failures.")
    print("Common issues to look for:")
    print("- ModuleNotFoundError for monitoring modules")
    print("- Database connection failures")
    print("- Missing environment variables")
    print("- Container exit codes")

if __name__ == "__main__":
    main()