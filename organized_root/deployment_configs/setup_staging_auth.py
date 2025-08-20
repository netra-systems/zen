#!/usr/bin/env python3
"""
Netra Staging Authentication Setup Script
Python equivalent of setup-staging-auth.ps1

This script ensures GCP authentication always works for staging deployments.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


# Configuration
PROJECT_ID = "netra-staging"
SERVICE_ACCOUNT_NAME = "netra-staging-deploy"
SERVICE_ACCOUNT_EMAIL = f"{SERVICE_ACCOUNT_NAME}@{PROJECT_ID}.iam.gserviceaccount.com"

# Colors for terminal output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'


def print_colored(message: str, color: str = Colors.ENDC):
    """Print colored output to terminal."""
    print(f"{color}{message}{Colors.ENDC}")


def run_command(cmd: List[str], check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e


def check_gcp_access(project_id: str) -> bool:
    """Check if we can access the GCP project."""
    print_colored("[1/7] Checking GCP project access...", Colors.GREEN)
    
    try:
        current_project_result = run_command([
            "gcloud", "config", "get-value", "project"
        ], capture_output=True)
        current_project = current_project_result.stdout.strip()
        
        if current_project != project_id:
            print_colored(f"  Setting project to {project_id}...", Colors.YELLOW)
            run_command(["gcloud", "config", "set", "project", project_id, "--quiet"])
        
        print_colored(f"  OK: Project set to: {project_id}", Colors.GREEN)
        return True
    except subprocess.CalledProcessError:
        print_colored(f"  Error: Cannot access project {project_id}", Colors.RED)
        print_colored("  Please ensure you have access to this project", Colors.YELLOW)
        return False


def check_service_account(project_id: str, service_account_email: str) -> bool:
    """Check if service account exists, create if not."""
    print_colored("[2/7] Checking service account...", Colors.GREEN)
    
    try:
        run_command([
            "gcloud", "iam", "service-accounts", "describe", service_account_email,
            "--project", project_id
        ], capture_output=True)
        
        print_colored(f"  OK: Service account exists: {service_account_email}", Colors.GREEN)
        return True
    except subprocess.CalledProcessError:
        print_colored(f"  Creating service account: {SERVICE_ACCOUNT_NAME}...", Colors.YELLOW)
        
        try:
            run_command([
                "gcloud", "iam", "service-accounts", "create", SERVICE_ACCOUNT_NAME,
                "--display-name", "Netra Staging Deployment Account",
                "--project", project_id
            ])
            print_colored("  OK: Service account created", Colors.GREEN)
            return True
        except subprocess.CalledProcessError:
            print_colored("  Error: Failed to create service account", Colors.RED)
            return False


def grant_iam_roles(project_id: str, service_account_email: str) -> bool:
    """Grant necessary IAM roles to the service account."""
    print_colored("[3/7] Granting IAM roles...", Colors.GREEN)
    
    roles = [
        "roles/artifactregistry.writer",
        "roles/run.developer", 
        "roles/storage.admin",
        "roles/secretmanager.admin",
        "roles/cloudbuild.builds.editor"
    ]
    
    success = True
    for role in roles:
        print_colored(f"  Granting {role}...", Colors.CYAN)
        try:
            run_command([
                "gcloud", "projects", "add-iam-policy-binding", project_id,
                "--member", f"serviceAccount:{service_account_email}",
                "--role", role,
                "--quiet"
            ], capture_output=True)
        except subprocess.CalledProcessError:
            print_colored(f"  Warning: Failed to grant {role}", Colors.YELLOW)
            success = False
    
    if success:
        print_colored("  OK: IAM roles granted", Colors.GREEN)
    else:
        print_colored("  Warning: Some IAM roles may not have been granted", Colors.YELLOW)
    
    return success


def manage_service_account_key(project_id: str, service_account_email: str, 
                              key_file_path: Path, force_new_key: bool = False) -> bool:
    """Manage service account key file."""
    print_colored("[4/7] Managing service account key...", Colors.GREEN)
    
    if key_file_path.exists() and not force_new_key:
        print_colored(f"  OK: Key file exists: {key_file_path}", Colors.GREEN)
        return True
    
    if key_file_path.exists():
        print_colored("  Removing old key file...", Colors.YELLOW)
        key_file_path.unlink()
    
    print_colored("  Creating new key file...", Colors.YELLOW)
    try:
        run_command([
            "gcloud", "iam", "service-accounts", "keys", "create", str(key_file_path),
            "--iam-account", service_account_email,
            "--project", project_id
        ])
        print_colored(f"  OK: Key file created: {key_file_path}", Colors.GREEN)
        return True
    except subprocess.CalledProcessError:
        print_colored("  Error: Failed to create key file", Colors.RED)
        return False


def set_environment_variables(key_file_path: Path) -> bool:
    """Set environment variables for the current session."""
    print_colored("[5/7] Setting environment variables...", Colors.GREEN)
    
    # Set for current session
    os.environ["GCP_STAGING_SA_KEY_PATH"] = str(key_file_path)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_file_path)
    
    # On Windows, try to set user environment variables persistently
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "GCP_STAGING_SA_KEY_PATH", 0, winreg.REG_SZ, str(key_file_path))
                winreg.SetValueEx(key, "GOOGLE_APPLICATION_CREDENTIALS", 0, winreg.REG_SZ, str(key_file_path))
        except Exception:
            print_colored("  Warning: Could not set persistent environment variables", Colors.YELLOW)
    
    print_colored("  OK: Environment variables set", Colors.GREEN)
    print_colored(f"    GCP_STAGING_SA_KEY_PATH={key_file_path}", Colors.CYAN)
    print_colored(f"    GOOGLE_APPLICATION_CREDENTIALS={key_file_path}", Colors.CYAN)
    return True


def authenticate_with_service_account(key_file_path: Path) -> bool:
    """Authenticate with the service account."""
    print_colored("[6/7] Authenticating with service account...", Colors.GREEN)
    
    try:
        run_command([
            "gcloud", "auth", "activate-service-account",
            f"--key-file={key_file_path}"
        ])
        
        # Configure Docker
        run_command([
            "gcloud", "auth", "configure-docker", 
            "us-central1-docker.pkg.dev", "--quiet"
        ])
        
        print_colored("  OK: Authenticated and Docker configured", Colors.GREEN)
        return True
    except subprocess.CalledProcessError:
        print_colored("  Error: Failed to authenticate", Colors.RED)
        return False


def create_env_file(key_file_path: Path, project_id: str, env_file_path: Path) -> bool:
    """Create/update .env.staging.local file."""
    print_colored("[7/7] Creating .env.staging.local file...", Colors.GREEN)
    
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    env_content = f"""# Staging Environment Service Account Configuration
# Generated by setup_staging_auth.py
# Last updated: {timestamp}

# GCP Service Account Key Path
GCP_STAGING_SA_KEY_PATH={key_file_path}
GOOGLE_APPLICATION_CREDENTIALS={key_file_path}

# GCP Project Configuration
GCP_PROJECT_ID={project_id}
GCP_REGION=us-central1
GCP_ZONE=us-central1-a

# Service Account Details
SERVICE_ACCOUNT_EMAIL={SERVICE_ACCOUNT_EMAIL}
"""
    
    try:
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print_colored(f"  OK: Created {env_file_path}", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"  Error: Failed to create env file: {e}", Colors.RED)
        return False


def verify_setup() -> bool:
    """Verify the authentication setup."""
    print_colored("")
    print_colored("=" * 48, Colors.GREEN)
    print_colored("  AUTHENTICATION SETUP COMPLETED", Colors.GREEN)
    print_colored("=" * 48, Colors.GREEN)
    print_colored("")
    
    print_colored("Verification:", Colors.YELLOW)
    
    try:
        # Get active account
        active_account_result = run_command([
            "gcloud", "auth", "list", "--filter=status:ACTIVE", 
            "--format=value(account)"
        ], capture_output=True)
        active_account = active_account_result.stdout.strip()
        
        # Get current project
        current_project_result = run_command([
            "gcloud", "config", "get-value", "project"
        ], capture_output=True)
        current_project = current_project_result.stdout.strip()
        
        print_colored(f"  Active account: {active_account}", Colors.CYAN)
        print_colored(f"  Project: {current_project}", Colors.CYAN)
        
        script_dir = Path(__file__).parent
        key_file = script_dir / "gcp-staging-sa-key.json"
        print_colored(f"  Key file: {key_file}", Colors.CYAN)
        
        print_colored("")
        print_colored("You can now run deployments with:", Colors.YELLOW)
        print_colored("  python deploy_staging.py", Colors.GREEN)
        print_colored("")
        
        return True
    except Exception as e:
        print_colored(f"  Warning: Verification failed: {e}", Colors.YELLOW)
        return False


def main():
    """Main function to orchestrate the authentication setup."""
    parser = argparse.ArgumentParser(description="Netra Staging Authentication Setup")
    parser.add_argument("--force-new-key", action="store_true", 
                       help="Force creation of new service account key")
    parser.add_argument("--project-id", default=PROJECT_ID,
                       help=f"GCP Project ID (default: {PROJECT_ID})")
    
    args = parser.parse_args()
    
    print_colored("=" * 48, Colors.BLUE)
    print_colored("  NETRA STAGING AUTHENTICATION SETUP", Colors.BLUE)
    print_colored("=" * 48, Colors.BLUE)
    print_colored("")
    
    script_dir = Path(__file__).parent
    key_file_path = script_dir / "gcp-staging-sa-key.json"
    env_file_path = script_dir / ".env.staging.local"
    service_account_email = f"{SERVICE_ACCOUNT_NAME}@{args.project_id}.iam.gserviceaccount.com"
    
    # Execute setup steps
    success = True
    success &= check_gcp_access(args.project_id)
    success &= check_service_account(args.project_id, service_account_email)
    success &= grant_iam_roles(args.project_id, service_account_email)
    success &= manage_service_account_key(args.project_id, service_account_email, 
                                        key_file_path, args.force_new_key)
    success &= set_environment_variables(key_file_path)
    success &= authenticate_with_service_account(key_file_path)
    success &= create_env_file(key_file_path, args.project_id, env_file_path)
    
    if success:
        verify_setup()
        sys.exit(0)
    else:
        print_colored("")
        print_colored("=" * 48, Colors.RED)
        print_colored("  AUTHENTICATION SETUP FAILED", Colors.RED)
        print_colored("=" * 48, Colors.RED)
        print_colored("")
        print_colored("Please check the errors above and try again.", Colors.YELLOW)
        sys.exit(1)


if __name__ == "__main__":
    main()