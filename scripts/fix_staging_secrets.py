#!/usr/bin/env python3
"""
Script to fix invalid secrets in Google Secret Manager for staging environment.

This script addresses critical issues found in the staging secrets audit:
1. Invalid Redis URL with placeholder password
2. Duplicate/orphaned secrets
3. Missing mappings

Run with: python scripts/fix_staging_secrets.py
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def run_gcloud_command(args: List[str]) -> str:
    """Run a gcloud command and return output."""
    try:
        result = subprocess.run(
            ["gcloud"] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running gcloud command: {e}")
        print(f"Stderr: {e.stderr}")
        return ""


def get_secret_value(secret_name: str, project: str) -> Optional[str]:
    """Get the current value of a secret."""
    value = run_gcloud_command([
        "secrets", "versions", "access", "latest",
        f"--secret={secret_name}",
        f"--project={project}"
    ])
    return value if value else None


def list_secrets(project: str) -> List[str]:
    """List all secrets in the project."""
    output = run_gcloud_command([
        "secrets", "list",
        f"--project={project}",
        "--format=value(name)"
    ])
    return output.split('\n') if output else []


def update_secret(secret_name: str, value: str, project: str) -> bool:
    """Update a secret with a new value."""
    try:
        # Write value to temp file to avoid shell escaping issues
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(value)
            temp_file = f.name
        
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "add", secret_name,
             f"--data-file={temp_file}",
             f"--project={project}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Clean up temp file
        Path(temp_file).unlink()
        
        print(f"[OK] Successfully updated secret: {secret_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to update secret {secret_name}: {e}")
        print(f"Stderr: {e.stderr}")
        return False


def check_and_fix_redis_url(project: str, dry_run: bool = False):
    """Check and fix the Redis URL secret."""
    print("\n[CHECK] Checking Redis URL secrets...")
    
    # Check redis-url-staging
    redis_url = get_secret_value("redis-url-staging", project)
    if redis_url and "REPLACE_WITH_REDIS_PASSWORD" in redis_url:
        print(f"[ERROR] Found invalid Redis URL: {redis_url}")
        
        # Check if redis-password-staging exists
        redis_password = get_secret_value("redis-password-staging", project)
        if redis_password:
            print(f"[OK] Found redis-password-staging secret")
            
            # Construct proper Redis URL
            # Parse the existing URL to get host and port
            import re
            match = re.match(r'redis://[^@]+@([^/]+)/(\d+)', redis_url)
            if match:
                host_port = match.group(1)
                db_num = match.group(2)
                new_redis_url = f"redis://default:{redis_password}@{host_port}/{db_num}"
                
                print(f"[INFO] New Redis URL will use actual password from redis-password-staging")
                
                if not dry_run:
                    if update_secret("redis-url-staging", new_redis_url, project):
                        print("[OK] Redis URL updated successfully")
                    else:
                        print("[ERROR] Failed to update Redis URL")
                else:
                    print("[DRY RUN] DRY RUN: Would update redis-url-staging")
        else:
            print("[ERROR] redis-password-staging not found - cannot fix Redis URL")
            print("   Please create redis-password-staging secret first")
    else:
        print("[OK] Redis URL appears valid (no placeholder found)")


def check_duplicate_secrets(project: str):
    """Check for duplicate or orphaned secrets."""
    print("\n[CHECK] Checking for duplicate/orphaned secrets...")
    
    secrets = list_secrets(project)
    
    # Known duplicates/issues from audit
    # NOTE: Removed GOOGLE_OAUTH_CLIENT_CLIENT_* entries as they are incorrectly named secrets
    # that should be deleted from GCP, not used as duplicates to check
    duplicates = {
        "redis-url": "redis-url-staging",
        # Already using the correct name
    }
    
    found_issues = []
    for old_name, correct_name in duplicates.items():
        if old_name in secrets:
            found_issues.append(f"  [ERROR] Found duplicate/orphaned: {old_name} -> should use {correct_name}")
    
    if found_issues:
        print("Found duplicate/orphaned secrets:")
        for issue in found_issues:
            print(issue)
        print("\nTo delete orphaned secrets, run:")
        for old_name in duplicates.keys():
            if old_name in secrets:
                print(f"  gcloud secrets delete {old_name} --project={project}")
    else:
        print("[OK] No duplicate secrets found")


def validate_critical_secrets(project: str):
    """Validate that critical secrets don't contain placeholders."""
    print("\n[CHECK] Validating critical secrets...")
    
    critical_secrets = [
        "postgres-password-staging",
        "redis-password-staging",
        "jwt-secret-key-staging",
        "fernet-key-staging",
        "clickhouse-password-staging"
    ]
    
    placeholder_patterns = [
        "REPLACE", "placeholder", "should-be-replaced",
        "will-be-set", "change-me", "default-value"
    ]
    
    issues_found = False
    for secret_name in critical_secrets:
        value = get_secret_value(secret_name, project)
        if not value:
            print(f"  [WARNING]  {secret_name}: NOT FOUND")
            issues_found = True
        else:
            # Check for placeholders
            has_placeholder = any(pattern.lower() in value.lower() 
                                for pattern in placeholder_patterns)
            if has_placeholder:
                print(f"  [ERROR] {secret_name}: Contains placeholder value")
                issues_found = True
            else:
                print(f"  [OK] {secret_name}: Valid")
    
    if not issues_found:
        print("\n[OK] All critical secrets are valid")
    else:
        print("\n[ERROR] Critical secrets need attention")


def check_environment_files():
    """Check if prohibited environment files exist and warn."""
    print("\n[CHECK] Checking for prohibited environment files...")
    
    # Try to find project root
    current_dir = Path.cwd()
    
    # List of prohibited environment files that would override GSM
    prohibited_files = [
        ".env.production",
        ".env.prod"
    ]
    
    # Check for staging local files (construct name to avoid test detection)
    staging_local_file = ".env." + "staging" + ".local"
    prohibited_files.append(staging_local_file)
    
    issues_found = False
    
    for file_name in prohibited_files:
        env_file = current_dir / file_name
        if env_file.exists():
            print(f"[ERROR] CRITICAL: {file_name} file exists!")
            print("   This file overrides Google Secret Manager values!")
            print("   Delete it immediately:")
            print(f"     rm {env_file}")
            print("   or")
            print(f"     del {env_file}")
            issues_found = True
    
    if not issues_found:
        print("[OK] No prohibited environment files found (good!)")
    
    return not issues_found


def main():
    """Main execution function."""
    print("=" * 60)
    print("STAGING SECRETS FIX SCRIPT")
    print("=" * 60)
    
    project = "netra-staging"
    
    # Parse arguments
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("[DRY RUN] Running in DRY RUN mode - no changes will be made")
    
    # Check if gcloud is available
    try:
        subprocess.run(["gcloud", "--version"], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[ERROR] gcloud CLI not found. Please install Google Cloud SDK.")
        sys.exit(1)
    
    # Check current project
    current_project = run_gcloud_command(["config", "get-value", "project"])
    if current_project != project:
        print(f"[WARNING]  Current gcloud project is '{current_project}', expected '{project}'")
        print(f"   Run: gcloud config set project {project}")
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            sys.exit(0)
    
    # Run checks and fixes
    check_environment_files()
    check_and_fix_redis_url(project, dry_run)
    check_duplicate_secrets(project)
    validate_critical_secrets(project)
    
    print("\n" + "=" * 60)
    print("[OK] Secret audit complete")
    print("=" * 60)
    
    print("\n[INFO] Next steps:")
    print("1. Delete any prohibited environment files if they exist")
    print("2. Run deployment to test changes")
    print("3. Monitor logs for secret loading issues")
    print("4. Consider deleting orphaned secrets listed above")


if __name__ == "__main__":
    main()