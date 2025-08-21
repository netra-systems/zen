#!/usr/bin/env python3
"""
Setup All Required Secrets for Staging Environment
Python equivalent of setup-staging-secrets.ps1 and setup-staging-database-secret.ps1

This script creates/updates all required secrets in Google Secret Manager.
"""

import argparse
import base64
import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Configuration
PROJECT_ID = "netra-staging"
PROJECT_ID_NUMERICAL = "701982941522"
REGION = "us-central1"

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
            text=True,
            input=""  # Provide empty input to avoid hanging
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e


def ensure_authentication(project_id: str) -> bool:
    """Ensure we are authenticated with the correct project."""
    print_colored("Checking authentication...", Colors.YELLOW)
    
    try:
        current_project_result = run_command([
            "gcloud", "config", "get-value", "project"
        ], capture_output=True)
        current_project = current_project_result.stdout.strip()
        
        if current_project != project_id:
            print_colored(f"Setting project to {project_id}...", Colors.YELLOW)
            run_command(["gcloud", "config", "set", "project", project_id, "--quiet"])
        
        return True
    except subprocess.CalledProcessError:
        print_colored(f"Error: Cannot access project {project_id}", Colors.RED)
        return False


def generate_jwt_secret() -> str:
    """Generate a secure 256-bit JWT secret."""
    return base64.b64encode(secrets.token_bytes(32)).decode('ascii')


def generate_fernet_key() -> str:
    """Generate a Fernet encryption key (32 bytes, URL-safe base64)."""
    key_bytes = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(key_bytes).decode('ascii')


def set_secret(secret_name: str, secret_value: str, required: bool = True) -> bool:
    """Create or update a secret in Google Secret Manager."""
    if not secret_value and required:
        print_colored(f"  ERROR: {secret_name} is required but no value provided", Colors.RED)
        return False
    
    if not secret_value:
        print_colored(f"  Skipping {secret_name} (optional, no value provided)", Colors.YELLOW)
        return True
    
    print_colored(f"  Setting up {secret_name}...", Colors.CYAN)
    
    try:
        # Check if secret exists
        run_command([
            "gcloud", "secrets", "describe", secret_name,
            "--project", PROJECT_ID_NUMERICAL
        ], capture_output=True)
        
        # Update existing secret
        process = subprocess.Popen([
            "gcloud", "secrets", "versions", "add", secret_name,
            "--data-file=-", "--project", PROJECT_ID_NUMERICAL
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        stdout, stderr = process.communicate(input=secret_value)
        
        if process.returncode == 0:
            print_colored("    ✓ Updated successfully", Colors.GREEN)
        else:
            print_colored("    ✗ Failed to update", Colors.RED)
            return False
            
    except subprocess.CalledProcessError:
        # Create new secret
        try:
            run_command([
                "gcloud", "secrets", "create", secret_name,
                "--project", PROJECT_ID_NUMERICAL,
                "--replication-policy=automatic"
            ], capture_output=True)
            
            process = subprocess.Popen([
                "gcloud", "secrets", "versions", "add", secret_name,
                "--data-file=-", "--project", PROJECT_ID_NUMERICAL
            ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            stdout, stderr = process.communicate(input=secret_value)
            
            if process.returncode == 0:
                print_colored("    ✓ Created successfully", Colors.GREEN)
            else:
                print_colored("    ✗ Failed to add version", Colors.RED)
                return False
        except subprocess.CalledProcessError:
            print_colored("    ✗ Failed to create", Colors.RED)
            return False
    
    # Grant access to Cloud Run service accounts
    service_accounts = [
        f"netra-cloudrun@{PROJECT_ID}.iam.gserviceaccount.com",
        f"netra-staging-deploy@{PROJECT_ID}.iam.gserviceaccount.com"
    ]
    
    for sa in service_accounts:
        try:
            run_command([
                "gcloud", "secrets", "add-iam-policy-binding", secret_name,
                "--member", f"serviceAccount:{sa}",
                "--role", "roles/secretmanager.secretAccessor",
                "--project", PROJECT_ID_NUMERICAL,
                "--quiet"
            ], capture_output=True)
        except subprocess.CalledProcessError:
            # Policy binding may already exist
            pass
    
    return True


def get_or_prompt_database_url(args) -> Optional[str]:
    """Get database URL from various sources or prompt user."""
    if args.database_url:
        return args.database_url
    
    if args.use_default_db_url:
        print_colored("Using default database URL for staging...", Colors.YELLOW)
        print_colored("  WARNING: Using default URL - replace with actual staging database!", Colors.RED)
        return "postgresql://netra_user:staging_password@localhost:5432/netra"
    
    # Try to get from Cloud SQL instance
    print_colored("Looking for Cloud SQL instance...", Colors.YELLOW)
    try:
        instances_result = run_command([
            "gcloud", "sql", "instances", "list", "--format=value(name)"
        ], capture_output=True)
        
        instances = [line.strip() for line in instances_result.stdout.split('\n') if line.strip()]
        if instances:
            instance_name = instances[0]
            print_colored(f"  Found Cloud SQL instance: {instance_name}", Colors.GREEN)
            
            # Get instance IP
            ip_result = run_command([
                "gcloud", "sql", "instances", "describe", instance_name,
                "--format=value(ipAddresses[0].ipAddress)"
            ], capture_output=True)
            
            instance_ip = ip_result.stdout.strip()
            if instance_ip:
                print_colored(f"  Instance IP: {instance_ip}", Colors.GREEN)
                
                # Check for existing password secret
                try:
                    password_result = run_command([
                        "gcloud", "secrets", "versions", "access", "latest",
                        "--secret=netra-db-password",
                        "--project", PROJECT_ID_NUMERICAL
                    ], capture_output=True)
                    
                    db_password = password_result.stdout.strip()
                    if db_password:
                        db_url = f"postgresql://netra_user:{db_password}@{instance_ip}:5432/netra"
                        print_colored("  Constructed database URL from Cloud SQL instance", Colors.GREEN)
                        return db_url
                except subprocess.CalledProcessError:
                    pass
    except subprocess.CalledProcessError:
        pass
    
    if not args.non_interactive:
        print_colored("")
        print_colored("Could not auto-detect database URL.", Colors.YELLOW)
        print_colored("Please provide the database URL:", Colors.YELLOW)
        print_colored("  Example: postgresql://user:pass@host:5432/netra", Colors.CYAN)
        try:
            database_url = input("Database URL: ").strip()
            if database_url:
                return database_url
        except (KeyboardInterrupt, EOFError):
            print_colored("\nOperation cancelled by user", Colors.YELLOW)
    
    print_colored("No database URL provided. Skipping database secret.", Colors.YELLOW)
    return None


def main():
    """Main function to orchestrate the secrets setup."""
    parser = argparse.ArgumentParser(description="Netra Staging Secrets Setup")
    parser.add_argument("--force", action="store_true", 
                       help="Force update of existing secrets")
    parser.add_argument("--gemini-api-key", 
                       help="Gemini API key for LLM operations")
    parser.add_argument("--jwt-secret", 
                       help="JWT secret (generated if not provided)")
    parser.add_argument("--fernet-key", 
                       help="Fernet encryption key (generated if not provided)")
    parser.add_argument("--google-client-id", 
                       help="Google OAuth client ID (optional)")
    parser.add_argument("--google-client-secret", 
                       help="Google OAuth client secret (optional)")
    parser.add_argument("--database-url", 
                       help="Database URL for staging")
    parser.add_argument("--use-default-db-url", action="store_true",
                       help="Use default database URL (not recommended)")
    parser.add_argument("--non-interactive", action="store_true",
                       help="Don't prompt for missing values")
    
    args = parser.parse_args()
    
    print_colored("=" * 48, Colors.BLUE)
    print_colored("  STAGING SECRETS SETUP", Colors.BLUE)
    print_colored("=" * 48, Colors.BLUE)
    print_colored("")
    
    # Ensure authentication
    if not ensure_authentication(PROJECT_ID):
        sys.exit(1)
    
    # Prepare secrets
    print_colored("")
    print_colored("Preparing secrets...", Colors.YELLOW)
    
    # Generate JWT secret if not provided
    jwt_secret = args.jwt_secret
    if not jwt_secret:
        print_colored("  Generating JWT secret...", Colors.CYAN)
        jwt_secret = generate_jwt_secret()
        print_colored("    ✓ Generated 256-bit JWT secret", Colors.GREEN)
    
    # Generate Fernet key if not provided
    fernet_key = args.fernet_key
    if not fernet_key:
        print_colored("  Generating Fernet key...", Colors.CYAN)
        fernet_key = generate_fernet_key()
        print_colored("    ✓ Generated Fernet encryption key", Colors.GREEN)
    
    # Get Gemini API key
    gemini_api_key = args.gemini_api_key
    if not gemini_api_key and not args.non_interactive:
        print_colored("")
        print_colored("GEMINI API KEY REQUIRED", Colors.RED)
        print_colored("Please provide your Gemini API key (required for LLM operations):", Colors.YELLOW)
        print_colored("You can get one from: https://makersuite.google.com/app/apikey", Colors.CYAN)
        try:
            gemini_api_key = input("Gemini API Key: ").strip()
        except (KeyboardInterrupt, EOFError):
            print_colored("\nOperation cancelled by user", Colors.YELLOW)
            sys.exit(1)
    
    if not gemini_api_key:
        print_colored("ERROR: Gemini API key is required for staging deployment", Colors.RED)
        sys.exit(1)
    
    # Get database URL
    database_url = get_or_prompt_database_url(args)
    
    # Setup secrets
    print_colored("")
    print_colored("Setting up secrets in Google Secret Manager...", Colors.YELLOW)
    
    success = True
    
    # Required secrets
    success &= set_secret("gemini-api-key-staging", gemini_api_key, required=True)
    success &= set_secret("jwt-secret-staging", jwt_secret, required=True)
    success &= set_secret("fernet-key-staging", fernet_key, required=True)
    
    # Database secret
    if database_url:
        success &= set_secret("database-url-staging", database_url, required=True)
    else:
        print_colored("  WARNING: database-url-staging not configured!", Colors.RED)
        print_colored("  You may need to run this script again with --database-url", Colors.YELLOW)
    
    # Optional OAuth secrets
    success &= set_secret("google-client-id-staging", args.google_client_id, required=False)
    success &= set_secret("google-client-secret-staging", args.google_client_secret, required=False)
    
    # Final status
    if success:
        print_colored("")
        print_colored("=" * 48, Colors.GREEN)
        print_colored("  SECRETS SETUP COMPLETED", Colors.GREEN)
        print_colored("=" * 48, Colors.GREEN)
        print_colored("")
        print_colored("All required secrets have been configured in Google Secret Manager.", Colors.CYAN)
        print_colored("")
        print_colored("Created/Updated secrets:", Colors.YELLOW)
        print_colored("  - gemini-api-key-staging (REQUIRED)", Colors.GREEN)
        print_colored("  - jwt-secret-staging (REQUIRED)", Colors.GREEN)
        print_colored("  - fernet-key-staging (REQUIRED)", Colors.GREEN)
        if database_url:
            print_colored("  - database-url-staging (REQUIRED)", Colors.GREEN)
        if args.google_client_id:
            print_colored("  - google-client-id-staging (optional)", Colors.BLUE)
        if args.google_client_secret:
            print_colored("  - google-client-secret-staging (optional)", Colors.BLUE)
        print_colored("")
        print_colored("Next steps:", Colors.YELLOW)
        print_colored("  1. Run: python deploy_staging.py", Colors.CYAN)
        sys.exit(0)
    else:
        print_colored("")
        print_colored("=" * 48, Colors.RED)
        print_colored("  SECRETS SETUP FAILED", Colors.RED)
        print_colored("=" * 48, Colors.RED)
        print_colored("")
        print_colored("Some secrets could not be created or updated.", Colors.RED)
        print_colored("Please check the errors above and try again.", Colors.YELLOW)
        sys.exit(1)


if __name__ == "__main__":
    main()