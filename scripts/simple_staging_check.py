#!/usr/bin/env python3
"""Simple staging diagnostic script without unicode issues."""

import subprocess
import sys

def run_command(cmd):
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("STAGING INFRASTRUCTURE DIAGNOSTIC")
    print("=" * 50)

    # Check gcloud authentication
    success, stdout, stderr = run_command("gcloud auth list")
    print(f"Gcloud auth: {'OK' if success else 'FAILED'}")
    if not success:
        print(f"Error: {stderr}")

    # Check project
    success, stdout, stderr = run_command("gcloud config get-value project")
    print(f"Current project: {stdout.strip() if success else 'UNKNOWN'}")

    # Check Cloud Run services
    print("\\nCloud Run Services:")
    services = ["netra-backend-staging", "netra-auth-service", "netra-frontend-staging"]

    for service in services:
        cmd = f"gcloud run services describe {service} --region=us-central1 --project=netra-staging --format='value(status.url)'"
        success, stdout, stderr = run_command(cmd)
        if success:
            print(f"  {service}: {stdout.strip()}")
        else:
            print(f"  {service}: NOT FOUND or ERROR")

    # Check infrastructure components
    print("\\nInfrastructure Components:")

    # VPC Connectors
    success, stdout, stderr = run_command("gcloud compute networks vpc-access connectors list --region=us-central1 --project=netra-staging")
    print(f"  VPC Connectors: {'FOUND' if success and 'staging' in stdout else 'MISSING'}")

    # Redis
    success, stdout, stderr = run_command("gcloud redis instances list --region=us-central1 --project=netra-staging")
    print(f"  Redis Instances: {'FOUND' if success and stdout.strip() else 'MISSING'}")

    # Cloud SQL
    success, stdout, stderr = run_command("gcloud sql instances list --project=netra-staging")
    print(f"  Cloud SQL: {'FOUND' if success and stdout.strip() else 'MISSING'}")

    # Get recent error logs
    print("\\nRecent Error Logs:")
    success, stdout, stderr = run_command('gcloud logging read "severity>=ERROR" --limit=5 --project=netra-staging --format="value(timestamp,textPayload)"')
    if success and stdout.strip():
        lines = stdout.strip().split('\\n')[:3]  # Show first 3 errors
        for line in lines:
            print(f"  {line[:100]}...")
    else:
        print("  No recent errors or unable to access logs")

if __name__ == "__main__":
    main()