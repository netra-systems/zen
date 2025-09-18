#!/usr/bin/env python3
"""
Emergency Staging Infrastructure Check
Simple diagnostic to verify timeout fix deployment results
"""

import subprocess
import sys
import json
import time
from typing import Dict, List, Optional

def run_gcloud_command(cmd: List[str], description: str) -> tuple[bool, str]:
    """Run a gcloud command and return success status and output."""
    print(f"Checking {description}...")
    try:
        result = subprocess.run(
            ["gcloud"] + cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print(f"SUCCESS: {description}")
            return True, result.stdout
        else:
            print(f"FAILED: {description}")
            return False, result.stderr

    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: {description}")
        return False, "Command timed out"
    except Exception as e:
        print(f"EXCEPTION: {description} - {e}")
        return False, str(e)

def check_auth_service_logs():
    """Check auth service logs for timeout-related errors."""
    print("\n=== AUTH SERVICE LOGS (Last 10 minutes) ===")

    success, output = run_gcloud_command([
        "logs", "read",
        'resource.type="cloud_run_revision" AND resource.labels.service_name="netra-auth-service"',
        "--project=netra-staging",
        "--limit=20",
        "--freshness=10m",
        "--format=value(timestamp,severity,textPayload)"
    ], "auth service recent logs")

    if success:
        print("Recent auth service logs:")
        print(output)

        # Check for timeout-related messages
        if "timeout" in output.lower():
            print("FOUND: Timeout-related messages in logs")
        if "database connection validation timeout" in output.lower():
            print("FOUND: Database validation timeout - our fix should address this")
        if "60.0" in output:
            print("FOUND: 60-second timeout value - indicates our fix is deployed")
    else:
        print(f"Failed to get auth service logs: {output}")

def check_backend_service_logs():
    """Check backend service logs for startup issues."""
    print("\n=== BACKEND SERVICE LOGS (Last 10 minutes) ===")

    success, output = run_gcloud_command([
        "logs", "read",
        'resource.type="cloud_run_revision" AND resource.labels.service_name="netra-backend-staging"',
        "--project=netra-staging",
        "--limit=20",
        "--freshness=10m",
        "--format=value(timestamp,severity,textPayload)"
    ], "backend service recent logs")

    if success:
        print("Recent backend service logs:")
        print(output)

        # Check for critical issues
        if "Container called exit(3)" in output:
            print("FOUND: Container startup failure (exit 3)")
        if "websocket" in output.lower():
            print("FOUND: WebSocket-related messages")
    else:
        print(f"Failed to get backend service logs: {output}")

def check_cloud_run_service_status():
    """Check current Cloud Run service status."""
    print("\n=== CLOUD RUN SERVICE STATUS ===")

    services = ["netra-auth-service", "netra-backend-staging"]

    for service in services:
        success, output = run_gcloud_command([
            "run", "services", "describe", service,
            "--region=us-central1",
            "--project=netra-staging",
            "--format=json"
        ], f"{service} status")

        if success:
            try:
                service_data = json.loads(output)
                status = service_data.get("status", {})
                conditions = status.get("conditions", [])

                print(f"\n{service} Status:")
                for condition in conditions:
                    condition_type = condition.get("type", "Unknown")
                    condition_status = condition.get("status", "Unknown")
                    message = condition.get("message", "No message")
                    print(f"  {condition_type}: {condition_status} - {message}")

            except json.JSONDecodeError:
                print(f"Failed to parse {service} status JSON")
        else:
            print(f"Failed to get {service} status")

def main():
    """Main diagnostic function."""
    print("EMERGENCY STAGING INFRASTRUCTURE CHECK")
    print("=====================================")
    print("Checking deployment status after timeout fix...")

    # Check current service status
    check_cloud_run_service_status()

    # Check recent logs for timeout fixes
    check_auth_service_logs()
    check_backend_service_logs()

    print("\n=== SUMMARY ===")
    print("Look for:")
    print("1. '60.0' timeout values indicating our fix is deployed")
    print("2. Reduced 'Database connection validation timeout' errors")
    print("3. Service status showing Ready=True")
    print("4. Any new error patterns after deployment")

if __name__ == "__main__":
    main()