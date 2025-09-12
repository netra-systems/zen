#!/usr/bin/env python3
"""
PostgreSQL Migration Script for GCP Cloud SQL
Migrates data from old PostgreSQL 14 instance to new PostgreSQL 17 instance
"""

import os
import sys
import subprocess
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports

def run_command(cmd, capture_output=True):
    """Execute a command and return output"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=capture_output, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

def check_gcloud_auth():
    """Verify gcloud authentication"""
    print("Checking gcloud authentication...")
    try:
        run_command(["gcloud", "auth", "list"])
        print("[U+2713] Authenticated with gcloud")
    except Exception as e:
        print(f"[U+2717] Not authenticated. Run: gcloud auth login")
        sys.exit(1)

def get_terraform_outputs():
    """Get Terraform outputs"""
    print("Getting Terraform outputs...")
    try:
        outputs_json = run_command(["terraform", "output", "-json"])
        outputs = json.loads(outputs_json)
        return {
            "new_instance": outputs["database_instance_name"]["value"],
            "new_connection": outputs["database_connection_name"]["value"],
            "new_public_ip": outputs["database_public_ip"]["value"],
            "new_private_ip": outputs["database_private_ip"]["value"],
        }
    except Exception as e:
        print(f"[U+2717] Failed to get Terraform outputs: {e}")
        print("Make sure Terraform has been applied first")
        sys.exit(1)

def backup_old_database(project_id, old_instance="staging-shared-postgres"):
    """Create a backup of the old database"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_name = f"pre-migration-backup-{timestamp}"
    
    print(f"\nCreating backup of {old_instance}...")
    
    # Create on-demand backup
    cmd = [
        "gcloud", "sql", "backups", "create",
        "--instance", old_instance,
        "--project", project_id,
        "--description", f"Backup before migration to PostgreSQL 17 - {timestamp}"
    ]
    
    try:
        run_command(cmd)
        print(f"[U+2713] Backup created: {backup_name}")
        return backup_name
    except Exception as e:
        print(f"[U+2717] Backup failed: {e}")
        if not args.force:
            print("Use --force to continue without backup")
            sys.exit(1)
        return None

def export_database(project_id, old_instance, bucket_name, database_name="netra"):
    """Export database to GCS bucket"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    export_file = f"gs://{bucket_name}/exports/postgres-14-export-{timestamp}.sql"
    
    print(f"\nExporting database from {old_instance}...")
    
    # Create GCS bucket if it doesn't exist
    try:
        run_command(["gsutil", "mb", "-p", project_id, f"gs://{bucket_name}"])
    except:
        pass  # Bucket might already exist
    
    # Export database
    export_request = {
        "exportContext": {
            "fileType": "SQL",
            "uri": export_file,
            "databases": [database_name],
            "offload": True
        }
    }
    
    cmd = [
        "gcloud", "sql", "export", "sql",
        old_instance, export_file,
        "--database", database_name,
        "--project", project_id,
        "--offload"
    ]
    
    try:
        run_command(cmd)
        print(f"[U+2713] Database exported to: {export_file}")
        return export_file
    except Exception as e:
        print(f"[U+2717] Export failed: {e}")
        sys.exit(1)

def import_database(project_id, new_instance, export_file, database_name="netra"):
    """Import database to new instance"""
    print(f"\nImporting database to {new_instance}...")
    
    cmd = [
        "gcloud", "sql", "import", "sql",
        new_instance, export_file,
        "--database", database_name,
        "--project", project_id
    ]
    
    try:
        run_command(cmd)
        print(f"[U+2713] Database imported successfully")
    except Exception as e:
        print(f"[U+2717] Import failed: {e}")
        sys.exit(1)

def update_deployment_script(new_instance_name):
    """Update the deployment script to use new instance"""
    deploy_script = Path(__file__).parent.parent / "scripts" / "deploy_to_gcp.py"
    
    if not deploy_script.exists():
        print(f" WARNING:  Deployment script not found: {deploy_script}")
        return
    
    print(f"\nUpdating deployment script...")
    
    with open(deploy_script, 'r') as f:
        content = f.read()
    
    # Update instance references
    old_patterns = [
        "staging-shared-postgres",
        "netra-postgres"
    ]
    
    updated = False
    for pattern in old_patterns:
        if pattern in content:
            content = content.replace(pattern, new_instance_name)
            updated = True
    
    if updated:
        with open(deploy_script, 'w') as f:
            f.write(content)
        print(f"[U+2713] Updated deployment script to use: {new_instance_name}")
    else:
        print(" WARNING:  No changes needed in deployment script")

def verify_migration(project_id, new_instance):
    """Verify the migration was successful"""
    print(f"\nVerifying migration...")
    
    # Check instance status
    cmd = [
        "gcloud", "sql", "instances", "describe",
        new_instance,
        "--project", project_id,
        "--format", "value(state)"
    ]
    
    try:
        state = run_command(cmd).strip()
        if state == "RUNNABLE":
            print(f"[U+2713] New instance is running")
        else:
            print(f" WARNING:  Instance state: {state}")
    except Exception as e:
        print(f"[U+2717] Failed to verify instance: {e}")

def main():
    parser = argparse.ArgumentParser(description="Migrate GCP Cloud SQL from PostgreSQL 14 to 17")
    parser.add_argument("--project", default="netra-staging", help="GCP project ID")
    parser.add_argument("--old-instance", default="staging-shared-postgres", help="Old instance name")
    parser.add_argument("--bucket", default="netra-staging-migrations", help="GCS bucket for exports")
    parser.add_argument("--database", default="netra", help="Database name to migrate")
    parser.add_argument("--force", action="store_true", help="Continue even if backup fails")
    parser.add_argument("--skip-backup", action="store_true", help="Skip backup step")
    parser.add_argument("--skip-export", action="store_true", help="Skip export (use existing export)")
    parser.add_argument("--export-file", help="Use existing export file")
    
    global args
    args = parser.parse_args()
    
    print("=" * 60)
    print("PostgreSQL Migration: v14  ->  v17")
    print("=" * 60)
    
    # Check prerequisites
    check_gcloud_auth()
    
    # Get new instance details from Terraform
    tf_outputs = get_terraform_outputs()
    new_instance = tf_outputs["new_instance"]
    
    print(f"\nMigration Plan:")
    print(f"  Source: {args.old_instance} (PostgreSQL 14)")
    print(f"  Target: {new_instance} (PostgreSQL 17)")
    print(f"  Database: {args.database}")
    
    # Step 1: Backup old database
    if not args.skip_backup:
        backup_old_database(args.project, args.old_instance)
    
    # Step 2: Export database
    if args.export_file:
        export_file = args.export_file
        print(f"Using existing export: {export_file}")
    elif not args.skip_export:
        export_file = export_database(args.project, args.old_instance, args.bucket, args.database)
    else:
        print("[U+2717] Must provide --export-file when using --skip-export")
        sys.exit(1)
    
    # Step 3: Import to new instance
    import_database(args.project, new_instance, export_file, args.database)
    
    # Step 4: Update deployment configuration
    update_deployment_script(new_instance)
    
    # Step 5: Verify migration
    verify_migration(args.project, new_instance)
    
    print("\n" + "=" * 60)
    print("[U+2713] Migration completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Test application connectivity to new instance")
    print("2. Run integration tests against staging")
    print("3. Monitor logs and performance")
    print("4. Once verified, decommission old instance")
    print(f"\nTo remove old instance:")
    print(f"  gcloud sql instances delete {args.old_instance} --project {args.project}")

if __name__ == "__main__":
    main()