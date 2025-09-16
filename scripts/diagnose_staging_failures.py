#!/usr/bin/env python3
"""
Staging Infrastructure Diagnostic Script
CRITICAL: Diagnoses specific issues preventing staging services from starting

Checks:
- Cloud Run service status and logs
- Missing infrastructure components
- Configuration issues
- Secret availability
- Network connectivity
"""

import subprocess
import sys
import json
import time
from typing import Dict, List, Optional

def run_gcloud_command(cmd: List[str], description: str) -> tuple[bool, str]:
    """Run a gcloud command and return success status and output."""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(
            ["gcloud"] + cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True, result.stdout
        else:
            print(f"❌ {description} - FAILED")
            return False, result.stderr

    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False, "Command timed out"
    except Exception as e:
        print(f"💥 {description} - EXCEPTION: {e}")
        return False, str(e)

def check_cloud_run_services():
    """Check status of Cloud Run services."""
    print("🏃 CLOUD RUN SERVICES STATUS")
    print("============================")

    services = [
        "netra-backend-staging",
        "netra-auth-service",
        "netra-frontend-staging"
    ]

    for service in services:
        print(f"\\n📱 Checking {service}...")

        # Get service description
        success, output = run_gcloud_command(
            ["run", "services", "describe", service,
             "--region=us-central1", "--project=netra-staging", "--format=json"],
            f"Getting {service} description"
        )

        if success:
            try:
                service_data = json.loads(output)
                status = service_data.get("status", {})
                conditions = status.get("conditions", [])

                print(f"  Service URL: {status.get('url', 'Not available')}")
                print(f"  Ready: {status.get('observedGeneration', 'Unknown')}")

                # Check conditions
                for condition in conditions:
                    condition_type = condition.get("type", "Unknown")
                    condition_status = condition.get("status", "Unknown")
                    message = condition.get("message", "No message")

                    if condition_status == "True":
                        print(f"  ✅ {condition_type}: {message}")
                    else:
                        print(f"  ❌ {condition_type}: {message}")

            except json.JSONDecodeError:
                print(f"  ⚠️ Could not parse service description")

        # Get recent logs
        print(f"\\n📝 Recent logs for {service}:")
        success, logs = run_gcloud_command(
            ["logging", "read",
             f"resource.type=cloud_run_revision AND resource.labels.service_name={service}",
             "--limit=5", "--format=json", "--project=netra-staging"],
            f"Getting recent logs for {service}"
        )

        if success and logs.strip():
            try:
                log_entries = json.loads(logs)
                for entry in log_entries:
                    timestamp = entry.get("timestamp", "Unknown time")
                    severity = entry.get("severity", "UNKNOWN")
                    text_payload = entry.get("textPayload", "")
                    json_payload = entry.get("jsonPayload", {})

                    if text_payload:
                        print(f"    [{severity}] {timestamp}: {text_payload[:200]}...")
                    elif json_payload.get("message"):
                        message = json_payload["message"]
                        print(f"    [{severity}] {timestamp}: {message[:200]}...")

            except json.JSONDecodeError:
                print(f"    ⚠️ Could not parse logs")
        else:
            print(f"    ℹ️ No recent logs found")

def check_infrastructure_components():
    """Check status of infrastructure components."""
    print("\\n🏗️ INFRASTRUCTURE COMPONENTS")
    print("=============================")

    components = [
        {
            "name": "VPC Connector",
            "command": ["compute", "networks", "vpc-access", "connectors", "list",
                       "--region=us-central1", "--project=netra-staging"],
            "expected": "staging-connector"
        },
        {
            "name": "Redis Instance",
            "command": ["redis", "instances", "list",
                       "--region=us-central1", "--project=netra-staging"],
            "expected": "redis"
        },
        {
            "name": "Cloud SQL Instance",
            "command": ["sql", "instances", "list", "--project=netra-staging"],
            "expected": "postgres"
        },
        {
            "name": "Load Balancer",
            "command": ["compute", "url-maps", "list", "--project=netra-staging"],
            "expected": "staging"
        }
    ]

    for component in components:
        success, output = run_gcloud_command(
            component["command"],
            f"Checking {component['name']}"
        )

        if success and component["expected"] in output.lower():
            print(f"  ✅ {component['name']}: Found")
        else:
            print(f"  ❌ {component['name']}: Missing or not accessible")
            print(f"    Output: {output[:200] if output else 'No output'}")

def check_secrets_availability():
    """Check if required secrets are available."""
    print("\\n🔐 SECRET MANAGER SECRETS")
    print("==========================")

    required_secrets = [
        "postgres-host-staging",
        "postgres-port-staging",
        "postgres-password-staging",
        "redis-host-staging",
        "redis-port-staging",
        "redis-password-staging",
        "jwt-secret-key-staging",
        "openai-api-key-staging"
    ]

    for secret in required_secrets:
        success, output = run_gcloud_command(
            ["secrets", "versions", "access", "latest", "--secret", secret, "--project=netra-staging"],
            f"Checking secret {secret}"
        )

        if success:
            print(f"  ✅ {secret}: Available")
        else:
            print(f"  ❌ {secret}: Missing or inaccessible")

def check_network_connectivity():
    """Check network connectivity and DNS resolution."""
    print("\\n🌐 NETWORK CONNECTIVITY")
    print("========================")

    endpoints = [
        "https://api.staging.netrasystems.ai",
        "https://auth.staging.netrasystems.ai",
        "https://staging.netrasystems.ai"
    ]

    for endpoint in endpoints:
        try:
            import urllib.request
            with urllib.request.urlopen(endpoint + "/health", timeout=10) as response:
                status_code = response.getcode()
                if status_code == 200:
                    print(f"  ✅ {endpoint}: Reachable (200 OK)")
                else:
                    print(f"  ⚠️ {endpoint}: Reachable but returned {status_code}")
        except Exception as e:
            print(f"  ❌ {endpoint}: Not reachable - {str(e)[:100]}")

def main():
    """Main diagnostic function."""
    print("🚨 STAGING INFRASTRUCTURE DIAGNOSTIC")
    print("====================================")
    print("Analyzing why staging services are failing...")
    print()

    # Check Cloud Run services
    check_cloud_run_services()

    # Check infrastructure components
    check_infrastructure_components()

    # Check secrets
    check_secrets_availability()

    # Check network connectivity
    check_network_connectivity()

    print("\\n📋 DIAGNOSTIC COMPLETE")
    print("=======================")
    print("Review the results above to identify specific issues:")
    print("❌ Red items indicate problems that need immediate attention")
    print("⚠️ Yellow items indicate warnings or partial issues")
    print("✅ Green items indicate working components")
    print()
    print("Next steps:")
    print("1. Address any missing infrastructure components")
    print("2. Fix secret access issues")
    print("3. Resolve network connectivity problems")
    print("4. Redeploy services after fixes")

if __name__ == "__main__":
    main()