"""
Fetch and analyze auth_core SQL errors from GCP Cloud Logging.

This script uses the GCP error log tools to identify and analyze
SQL-related issues with the auth_core service in staging.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add the project root to path

from test_framework.gcp_integration.base import GCPConfig
from test_framework.gcp_integration.log_reader import GCPLogReader, LogFilter


async def analyze_auth_sql_errors():
    """Fetch and analyze auth_core SQL errors from staging."""
    
    # Initialize GCP config for staging
    gcp_config = GCPConfig(
        project_id="netra-staging",
        region="us-central1"
    )
    
    # Initialize the log reader
    log_reader = GCPLogReader(gcp_config)
    await log_reader.initialize()
    
    print("=" * 80)
    print("AUTH_CORE SQL ERROR ANALYSIS")
    print("=" * 80)
    
    # Define time range (last 24 hours)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=24)
    
    print(f"\nAnalyzing logs from {start_time} to {end_time}")
    print("-" * 80)
    
    # 1. Fetch all auth service errors
    print("\n1. Fetching all auth service errors...")
    auth_error_filter = LogFilter(
        service_name="auth-service",
        severity="ERROR",
        start_time=start_time,
        end_time=end_time
    )
    
    auth_errors = await log_reader.fetch_logs_by_filter(auth_error_filter)
    print(f"   Found {len(auth_errors)} error logs")
    
    # 2. Filter for SQL-related errors
    print("\n2. Filtering for SQL-related errors...")
    sql_errors = []
    permission_errors = []
    connection_errors = []
    
    for error in auth_errors:
        message_lower = error.message.lower()
        payload_str = json.dumps(error.json_payload).lower() if error.json_payload else ""
        
        # Check for SQL/database related keywords
        if any(keyword in message_lower or keyword in payload_str for keyword in 
               ['sql', 'postgres', 'database', 'cloudsql', 'db', 'connection']):
            sql_errors.append(error)
            
            # Categorize the error
            if 'permission' in message_lower or 'not_authorized' in message_lower or '403' in message_lower:
                permission_errors.append(error)
            elif 'connection' in message_lower or 'connect' in message_lower:
                connection_errors.append(error)
    
    print(f"   Found {len(sql_errors)} SQL-related errors")
    print(f"   - Permission errors: {len(permission_errors)}")
    print(f"   - Connection errors: {len(connection_errors)}")
    
    # 3. Search for specific Cloud SQL permission errors
    print("\n3. Searching for Cloud SQL permission errors...")
    cloudsql_filter = LogFilter(
        service_name="auth-service",
        text_search="cloudsql.instances.get",
        start_time=start_time,
        end_time=end_time
    )
    
    cloudsql_errors = await log_reader.fetch_logs_by_filter(cloudsql_filter)
    print(f"   Found {len(cloudsql_errors)} Cloud SQL permission errors")
    
    # 4. Display detailed error information
    print("\n" + "=" * 80)
    print("DETAILED ERROR ANALYSIS")
    print("=" * 80)
    
    if permission_errors:
        print("\n--- PERMISSION ERRORS ---")
        for i, error in enumerate(permission_errors[:5], 1):  # Show first 5
            print(f"\nError {i}:")
            print(f"  Timestamp: {error.timestamp}")
            print(f"  Message: {error.message[:200]}...")
            if error.json_payload:
                print(f"  Payload: {json.dumps(error.json_payload, indent=2)[:500]}...")
    
    if connection_errors:
        print("\n--- CONNECTION ERRORS ---")
        for i, error in enumerate(connection_errors[:5], 1):  # Show first 5
            print(f"\nError {i}:")
            print(f"  Timestamp: {error.timestamp}")
            print(f"  Message: {error.message[:200]}...")
            if error.source_location:
                print(f"  Source: {error.source_location}")
    
    # 5. Generate error summary
    print("\n" + "=" * 80)
    print("ERROR SUMMARY")
    print("=" * 80)
    
    error_analysis = await log_reader.analyze_errors(
        service_name="auth-service",
        duration_minutes=1440  # 24 hours
    )
    
    print(f"\nService: {error_analysis['service']}")
    print(f"Time Range: {error_analysis['time_range']['start']} to {error_analysis['time_range']['end']}")
    print(f"\nStatistics:")
    stats = error_analysis['statistics']
    print(f"  - Total Errors: {stats['total_errors']}")
    print(f"  - Unique Error Types: {stats['unique_error_types']}")
    print(f"  - Error Rate: {stats['error_rate_per_minute']:.2f} errors/minute")
    if stats['most_common_error']:
        print(f"  - Most Common Error: {stats['most_common_error']}")
    
    print("\nErrors by Type:")
    for error_type, count in stats['errors_by_type'].items():
        print(f"  - {error_type}: {count}")
    
    # 6. Save detailed report
    report_file = "auth_sql_error_report.json"
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "time_range": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        },
        "summary": {
            "total_auth_errors": len(auth_errors),
            "sql_related_errors": len(sql_errors),
            "permission_errors": len(permission_errors),
            "connection_errors": len(connection_errors),
            "cloudsql_permission_errors": len(cloudsql_errors)
        },
        "error_analysis": error_analysis,
        "sample_errors": {
            "permission": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "message": e.message,
                    "payload": e.json_payload
                } for e in permission_errors[:3]
            ],
            "connection": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "message": e.message,
                    "payload": e.json_payload
                } for e in connection_errors[:3]
            ]
        }
    }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n PASS:  Detailed report saved to: {report_file}")
    
    # 7. Provide recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if permission_errors:
        print("\n[WARNING] CRITICAL: Cloud SQL permission errors detected!")
        print("   The auth service cannot access the Cloud SQL instance.")
        print("\n   Required Actions:")
        print("   1. Grant 'Cloud SQL Client' role to the service account")
        print("   2. Run: gcloud projects add-iam-policy-binding netra-staging \\")
        print("          --member='serviceAccount:701982941522-compute@developer.gserviceaccount.com' \\")
        print("          --role='roles/cloudsql.client'")
        print("\n   See URGENT_CLOUD_SQL_FIX.md for detailed instructions.")
    
    if connection_errors and not permission_errors:
        print("\n[WARNING] Connection errors detected (permissions OK)")
        print("   Possible causes:")
        print("   - Cloud SQL instance is down or not accessible")
        print("   - Network configuration issues")
        print("   - Invalid connection string or credentials")
    
    if not sql_errors:
        print("\n PASS:  No SQL-related errors found in the last 24 hours")


if __name__ == "__main__":
    print("Starting auth_core SQL error analysis...")
    try:
        asyncio.run(analyze_auth_sql_errors())
    except Exception as e:
        print(f"\n[ERROR] Error running analysis: {e}")
        import traceback
        traceback.print_exc()