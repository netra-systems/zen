"""
Fetch auth_core SQL errors using gcloud CLI.

This script uses gcloud logging commands to fetch and analyze
SQL-related issues with the auth_core service in staging.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta


def run_gcloud_command(cmd):
    """Run a gcloud command and return the output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        print(f"Exception running command: {e}")
        return None


def fetch_auth_sql_errors():
    """Fetch and analyze auth SQL errors from GCP staging."""
    
    print("=" * 80)
    print("AUTH SERVICE SQL ERROR ANALYSIS - GCP STAGING")
    print("=" * 80)
    
    # Set the project
    print("\nSetting GCP project to netra-staging...")
    run_gcloud_command("gcloud config set project netra-staging")
    
    # Define time range (last 24 hours)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    print(f"\nAnalyzing logs from {start_time.isoformat()}Z to {end_time.isoformat()}Z")
    print("-" * 80)
    
    # 1. Fetch Cloud SQL permission errors
    print("\n1. Fetching Cloud SQL permission errors...")
    sql_permission_filter = (
        f'resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="auth-service" '
        f'AND (textPayload=~"cloudsql" OR jsonPayload.message=~"cloudsql" '
        f'OR textPayload=~"403" OR textPayload=~"NOT_AUTHORIZED") '
        f'AND severity>=ERROR '
        f'AND timestamp>="{start_time.isoformat()}Z" '
        f'AND timestamp<="{end_time.isoformat()}Z"'
    )
    
    cmd = f"gcloud logging read '{sql_permission_filter}' --limit=50 --format=json"
    result = run_gcloud_command(cmd)
    
    if result:
        try:
            permission_errors = json.loads(result) if result.strip() else []
            print(f"   Found {len(permission_errors)} Cloud SQL permission errors")
            
            if permission_errors:
                print("\n   Sample permission errors:")
                for i, error in enumerate(permission_errors[:3], 1):
                    timestamp = error.get('timestamp', 'N/A')
                    text_payload = error.get('textPayload', '')
                    json_payload = error.get('jsonPayload', {})
                    message = json_payload.get('message', text_payload)[:200]
                    
                    print(f"\n   Error {i}:")
                    print(f"     Time: {timestamp}")
                    print(f"     Message: {message}...")
        except json.JSONDecodeError:
            print("   Could not parse permission error results")
    
    # 2. Fetch database connection errors
    print("\n2. Fetching database connection errors...")
    connection_filter = (
        f'resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="auth-service" '
        f'AND (textPayload=~"connection" OR textPayload=~"postgres" '
        f'OR textPayload=~"database" OR jsonPayload.message=~"connection" '
        f'OR jsonPayload.message=~"postgres") '
        f'AND severity>=ERROR '
        f'AND timestamp>="{start_time.isoformat()}Z" '
        f'AND timestamp<="{end_time.isoformat()}Z"'
    )
    
    cmd = f"gcloud logging read '{connection_filter}' --limit=50 --format=json"
    result = run_gcloud_command(cmd)
    
    if result:
        try:
            connection_errors = json.loads(result) if result.strip() else []
            print(f"   Found {len(connection_errors)} database connection errors")
            
            if connection_errors:
                print("\n   Sample connection errors:")
                for i, error in enumerate(connection_errors[:3], 1):
                    timestamp = error.get('timestamp', 'N/A')
                    text_payload = error.get('textPayload', '')
                    json_payload = error.get('jsonPayload', {})
                    message = json_payload.get('message', text_payload)[:200]
                    
                    print(f"\n   Error {i}:")
                    print(f"     Time: {timestamp}")
                    print(f"     Message: {message}...")
        except json.JSONDecodeError:
            print("   Could not parse connection error results")
    
    # 3. Fetch specific auth_core errors
    print("\n3. Fetching auth_core specific errors...")
    auth_core_filter = (
        f'resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="auth-service" '
        f'AND (textPayload=~"auth_core" OR jsonPayload.module=~"auth_core") '
        f'AND severity>=ERROR '
        f'AND timestamp>="{start_time.isoformat()}Z" '
        f'AND timestamp<="{end_time.isoformat()}Z"'
    )
    
    cmd = f"gcloud logging read '{auth_core_filter}' --limit=50 --format=json"
    result = run_gcloud_command(cmd)
    
    if result:
        try:
            auth_core_errors = json.loads(result) if result.strip() else []
            print(f"   Found {len(auth_core_errors)} auth_core specific errors")
        except json.JSONDecodeError:
            print("   Could not parse auth_core error results")
    
    # 4. Get recent auth service startup logs
    print("\n4. Fetching recent auth service startup logs...")
    startup_filter = (
        f'resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="auth-service" '
        f'AND (textPayload=~"Starting" OR textPayload=~"Initializing" '
        f'OR textPayload=~"startup" OR textPayload=~"Failed") '
        f'AND timestamp>="{start_time.isoformat()}Z" '
        f'AND timestamp<="{end_time.isoformat()}Z"'
    )
    
    cmd = f"gcloud logging read '{startup_filter}' --limit=20 --format=json"
    result = run_gcloud_command(cmd)
    
    if result:
        try:
            startup_logs = json.loads(result) if result.strip() else []
            print(f"   Found {len(startup_logs)} startup-related logs")
            
            if startup_logs:
                print("\n   Recent startup events:")
                for log in startup_logs[:5]:
                    timestamp = log.get('timestamp', 'N/A')
                    text_payload = log.get('textPayload', '')
                    json_payload = log.get('jsonPayload', {})
                    message = json_payload.get('message', text_payload)[:150]
                    severity = log.get('severity', 'INFO')
                    
                    print(f"     [{severity}] {timestamp}: {message}...")
        except json.JSONDecodeError:
            print("   Could not parse startup log results")
    
    # 5. Check for the specific 403 permission error
    print("\n5. Checking for specific Cloud SQL permission error (403)...")
    specific_403_filter = (
        f'resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="auth-service" '
        f'AND textPayload=~"NOT_AUTHORIZED" '
        f'AND textPayload=~"cloudsql" '
        f'AND timestamp>="{start_time.isoformat()}Z"'
    )
    
    cmd = f"gcloud logging read '{specific_403_filter}' --limit=5 --format=json"
    result = run_gcloud_command(cmd)
    
    if result:
        try:
            specific_errors = json.loads(result) if result.strip() else []
            if specific_errors:
                print(f"\n   WARNING - CRITICAL: Found {len(specific_errors)} instances of the Cloud SQL permission error!")
                print("   This confirms the auth service lacks Cloud SQL access permissions.")
                
                latest_error = specific_errors[0]
                print(f"\n   Latest occurrence: {latest_error.get('timestamp', 'N/A')}")
                print(f"   Full error message:")
                print(f"   {latest_error.get('textPayload', 'N/A')}")
            else:
                print("   No specific 403 Cloud SQL permission errors found")
        except json.JSONDecodeError:
            print("   Could not parse specific error results")
    
    # 6. Get service account being used
    print("\n6. Checking service account configuration...")
    sa_filter = (
        f'resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="auth-service" '
        f'AND textPayload=~"serviceAccount" '
        f'AND timestamp>="{(end_time - timedelta(hours=1)).isoformat()}Z"'
    )
    
    cmd = f"gcloud logging read '{sa_filter}' --limit=10 --format=json"
    result = run_gcloud_command(cmd)
    
    if result:
        try:
            sa_logs = json.loads(result) if result.strip() else []
            if sa_logs:
                print(f"   Found {len(sa_logs)} service account related logs")
        except json.JSONDecodeError:
            pass
    
    # Summary and recommendations
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)
    
    print("\n[Analysis Summary]")
    print("   - Checked logs for the last 24 hours")
    print("   - Searched for Cloud SQL permission errors")
    print("   - Analyzed database connection issues")
    print("   - Reviewed auth service startup logs")
    
    print("\n[Required Actions]")
    print("\n   1. IMMEDIATE FIX - Grant Cloud SQL permissions:")
    print("      Run this command with Owner/IAM Admin privileges:")
    print()
    print("      gcloud projects add-iam-policy-binding netra-staging \\")
    print("        --member='serviceAccount:701982941522-compute@developer.gserviceaccount.com' \\")
    print("        --role='roles/cloudsql.client'")
    print()
    print("   2. Verify the fix:")
    print("      - Restart the auth service: gcloud run services update auth-service --region=us-central1")
    print("      - Check logs: gcloud logging read 'resource.labels.service_name=\"auth-service\" severity>=ERROR' --limit=10")
    print()
    print("   3. Monitor service health:")
    print("      - Check service status: gcloud run services describe auth-service --region=us-central1")
    print("      - Monitor metrics: https://console.cloud.google.com/run/detail/us-central1/auth-service/metrics?project=netra-staging")
    
    print("\nSee URGENT_CLOUD_SQL_FIX.md for detailed instructions")


if __name__ == "__main__":
    print("Starting auth service SQL error analysis using gcloud CLI...")
    print("Note: This requires gcloud CLI to be installed and authenticated")
    print()
    
    try:
        # Check if gcloud is available
        result = subprocess.run("gcloud version", shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print("ERROR: gcloud CLI is not installed or not in PATH")
            print("   Please install: https://cloud.google.com/sdk/docs/install")
            sys.exit(1)
        
        fetch_auth_sql_errors()
        
    except Exception as e:
        print(f"\nERROR running analysis: {e}")
        import traceback
        traceback.print_exc()