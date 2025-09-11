#!/usr/bin/env python3
"""
Quick JWT secret fix deployment for staging.
This script ensures the JWT secret in GCP matches what tests expect.
"""

import subprocess
import sys
import os

def run_command(cmd, capture=True):
    """Run a command and return output."""
    print(f"Running: {cmd}")
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
            return result.stdout.strip()
        else:
            return subprocess.run(cmd, shell=True).returncode == 0
    except Exception as e:
        print(f"Command failed: {e}")
        return "" if capture else False

def main():
    project = "netra-staging"
    
    # The correct JWT secret from config/staging.env
    jwt_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
    
    print("=" * 60)
    print("QUICK JWT SECRET FIX FOR STAGING")
    print("=" * 60)
    
    # Set the project
    print(f"\n1. Setting GCP project to {project}...")
    run_command(f"gcloud config set project {project}")
    
    # Update the JWT secret
    print("\n2. Updating JWT secret in GCP Secret Manager...")
    
    # First, delete existing version if it exists
    print("   Checking if jwt-secret-staging exists...")
    existing = run_command(f"gcloud secrets describe jwt-secret-staging --project={project} 2>&1")
    
    if "NOT_FOUND" not in existing:
        print("   Secret exists, creating new version...")
        # Create new version
        cmd = f'echo -n "{jwt_secret}" | gcloud secrets versions add jwt-secret-staging --data-file=- --project={project}'
        run_command(cmd)
    else:
        print("   Creating new secret...")
        cmd = f'echo -n "{jwt_secret}" | gcloud secrets create jwt-secret-staging --data-file=- --project={project}'
        run_command(cmd)
    
    # Also update jwt-secret-key-staging to use the same value
    print("\n3. Updating jwt-secret-key-staging...")
    existing = run_command(f"gcloud secrets describe jwt-secret-key-staging --project={project} 2>&1")
    
    if "NOT_FOUND" not in existing:
        print("   Secret exists, creating new version...")
        cmd = f'echo -n "{jwt_secret}" | gcloud secrets versions add jwt-secret-key-staging --data-file=- --project={project}'
        run_command(cmd)
    else:
        print("   Creating new secret...")
        cmd = f'echo -n "{jwt_secret}" | gcloud secrets create jwt-secret-key-staging --data-file=- --project={project}'
        run_command(cmd)
    
    # Restart the backend service to pick up new secret
    print("\n4. Restarting backend service to pick up new secret...")
    run_command(f"gcloud run services update netra-backend-staging --region=us-central1 --project={project}")
    
    # Verify the service is running
    print("\n5. Verifying service health...")
    import time
    time.sleep(10)  # Wait for service to restart
    
    health_check = run_command(f"curl -s https://api.staging.netrasystems.ai/health")
    if health_check:
        print(f"   Health check response: {health_check[:100]}")
    
    print("\n" + "=" * 60)
    print("JWT SECRET FIX COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run the WebSocket tests to verify the fix:")
    print("   python tests/e2e/staging/test_1_websocket_events_staging.py")
    print("2. Or run all staging tests:")
    print("   python tests/unified_test_runner.py --env staging --category e2e")

if __name__ == "__main__":
    main()