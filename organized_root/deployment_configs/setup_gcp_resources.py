#!/usr/bin/env python3
"""
Setup GCP Staging Resources
Python equivalent of setup-gcp-staging-resources.ps1

Pre-creates all required GCP resources for staging deployment.
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
PROJECT_ID = "netra-staging"
REGION = "us-central1"
ZONE = "us-central1-a"
REGISTRY_NAME = "netra-containers"

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


def authenticate(service_account_key_path: Optional[str] = None) -> bool:
    """Authenticate with GCP."""
    if service_account_key_path and Path(service_account_key_path).exists():
        print_colored("Using service account authentication...", Colors.GREEN)
        try:
            run_command([
                "gcloud", "auth", "activate-service-account",
                f"--key-file={service_account_key_path}"
            ])
            return True
        except subprocess.CalledProcessError:
            print_colored("Service account authentication failed", Colors.RED)
            return False
    else:
        print_colored("Using default authentication...", Colors.YELLOW)
        try:
            current_user_result = run_command([
                "gcloud", "config", "get-value", "account"
            ], capture_output=True)
            
            if not current_user_result.stdout.strip():
                print_colored("No authenticated user found, running gcloud auth login...", Colors.YELLOW)
                run_command(["gcloud", "auth", "login"])
            
            return True
        except subprocess.CalledProcessError:
            print_colored("Authentication failed", Colors.RED)
            return False


def set_project(project_id: str) -> bool:
    """Set the GCP project."""
    print_colored(f"Setting project to {project_id}...", Colors.GREEN)
    try:
        run_command(["gcloud", "config", "set", "project", project_id])
        return True
    except subprocess.CalledProcessError:
        print_colored(f"Failed to set project to {project_id}", Colors.RED)
        return False


def enable_apis(project_id: str) -> bool:
    """Enable required GCP APIs."""
    print_colored("")
    print_colored("Enabling required APIs...", Colors.GREEN)
    
    apis = [
        "run.googleapis.com",
        "cloudbuild.googleapis.com",
        "secretmanager.googleapis.com",
        "compute.googleapis.com",
        "artifactregistry.googleapis.com",
        "cloudresourcemanager.googleapis.com",
        "iam.googleapis.com",
        "monitoring.googleapis.com",
        "logging.googleapis.com"
    ]
    
    success = True
    for api in apis:
        print_colored(f"  Enabling {api}...", Colors.CYAN)
        try:
            run_command([
                "gcloud", "services", "enable", api,
                "--project", project_id, "--quiet"
            ])
        except subprocess.CalledProcessError:
            print_colored(f"  Failed to enable {api}", Colors.RED)
            success = False
    
    return success


def setup_service_account(project_id: str, service_account_email: str) -> bool:
    """Setup service account with required roles."""
    print_colored("")
    print_colored("Setting up service account...", Colors.GREEN)
    
    # Check if service account exists
    try:
        run_command([
            "gcloud", "iam", "service-accounts", "describe", service_account_email,
            "--project", project_id
        ], capture_output=True)
        print_colored("  Service account already exists", Colors.GREEN)
    except subprocess.CalledProcessError:
        print_colored("  Creating service account...", Colors.YELLOW)
        try:
            run_command([
                "gcloud", "iam", "service-accounts", "create", "netra-staging-deploy",
                "--display-name", "Netra Staging Deployment Account",
                "--project", project_id
            ])
            
            # Grant necessary roles
            print_colored("  Granting roles to service account...", Colors.CYAN)
            roles = [
                "roles/run.admin",
                "roles/artifactregistry.admin",
                "roles/secretmanager.admin",
                "roles/iam.serviceAccountUser",
                "roles/cloudbuild.builds.editor",
                "roles/storage.admin"
            ]
            
            for role in roles:
                try:
                    run_command([
                        "gcloud", "projects", "add-iam-policy-binding", project_id,
                        "--member", f"serviceAccount:{service_account_email}",
                        "--role", role,
                        "--quiet"
                    ])
                except subprocess.CalledProcessError:
                    print_colored(f"  Warning: Failed to grant {role}", Colors.YELLOW)
            
            print_colored("  Service account created and configured", Colors.GREEN)
        except subprocess.CalledProcessError:
            print_colored("  Failed to create service account", Colors.RED)
            return False
    
    return True


def create_artifact_registry(project_id: str, region: str, registry_name: str) -> bool:
    """Create Artifact Registry repository."""
    print_colored("")
    print_colored("Creating Artifact Registry...", Colors.GREEN)
    
    try:
        run_command([
            "gcloud", "artifacts", "repositories", "describe", registry_name,
            "--location", region,
            "--project", project_id
        ], capture_output=True)
        print_colored(f"  Artifact Registry already exists: {registry_name}", Colors.GREEN)
    except subprocess.CalledProcessError:
        try:
            run_command([
                "gcloud", "artifacts", "repositories", "create", registry_name,
                "--repository-format", "docker",
                "--location", region,
                "--description", "Container images for Netra staging deployment",
                "--project", project_id
            ])
            print_colored(f"  Artifact Registry created: {registry_name}", Colors.GREEN)
        except subprocess.CalledProcessError:
            print_colored(f"  Failed to create Artifact Registry: {registry_name}", Colors.RED)
            return False
    
    return True


def create_secrets(project_id: str) -> bool:
    """Create initial secrets with placeholder values."""
    print_colored("")
    print_colored("Creating secrets...", Colors.GREEN)
    
    secrets_to_create = {
        "jwt-secret": str(uuid.uuid4()) + str(uuid.uuid4()),
        "auth-database-url": "postgresql://user:pass@localhost:5432/auth_db",
        "openai-api-key": "sk-placeholder-replace-with-real-key",
        "anthropic-api-key": "sk-ant-placeholder-replace-with-real-key",
        "gemini-api-key": "placeholder-replace-with-real-key"
    }
    
    # Get existing secrets
    try:
        existing_secrets_result = run_command([
            "gcloud", "secrets", "list",
            "--project", project_id,
            "--format", "value(name)"
        ], capture_output=True)
        existing_secrets = [line.strip() for line in existing_secrets_result.stdout.split('\n') if line.strip()]
    except subprocess.CalledProcessError:
        existing_secrets = []
    
    success = True
    for secret_name, secret_value in secrets_to_create.items():
        if secret_name not in existing_secrets:
            print_colored(f"  Creating secret: {secret_name}", Colors.CYAN)
            try:
                # Create secret
                run_command([
                    "gcloud", "secrets", "create", secret_name,
                    "--project", project_id,
                    "--replication-policy", "automatic"
                ])
                
                # Add initial version
                process = subprocess.Popen([
                    "gcloud", "secrets", "versions", "add", secret_name,
                    "--data-file=-",
                    "--project", project_id
                ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                stdout, stderr = process.communicate(input=secret_value)
                
                if process.returncode != 0:
                    print_colored(f"  Failed to add value to secret: {secret_name}", Colors.RED)
                    success = False
                    
            except subprocess.CalledProcessError:
                print_colored(f"  Failed to create secret: {secret_name}", Colors.RED)
                success = False
        else:
            print_colored(f"  Secret already exists: {secret_name}", Colors.GREEN)
    
    return success


def create_storage_bucket(project_id: str, region: str) -> bool:
    """Create Cloud Storage bucket for backups."""
    print_colored("")
    print_colored("Creating Cloud Storage bucket...", Colors.GREEN)
    
    bucket_name = f"{project_id}-backups"
    
    try:
        run_command([
            "gsutil", "ls", "-b", f"gs://{bucket_name}"
        ], capture_output=True)
        print_colored(f"  Bucket already exists: {bucket_name}", Colors.GREEN)
    except subprocess.CalledProcessError:
        try:
            run_command([
                "gsutil", "mb", "-p", project_id, "-c", "STANDARD", 
                "-l", region, f"gs://{bucket_name}"
            ])
            print_colored(f"  Bucket created: {bucket_name}", Colors.GREEN)
        except subprocess.CalledProcessError:
            print_colored(f"  Failed to create bucket: {bucket_name}", Colors.RED)
            return False
    
    return True


def setup_monitoring() -> None:
    """Setup monitoring workspace."""
    print_colored("")
    print_colored("Setting up monitoring...", Colors.GREEN)
    print_colored("  Please visit https://console.cloud.google.com/monitoring to complete monitoring setup", Colors.YELLOW)


def configure_networking() -> None:
    """Configure networking for Cloud Run."""
    print_colored("")
    print_colored("Configuring networking...", Colors.GREEN)
    print_colored("  Cloud Run networking is automatically configured", Colors.GREEN)


def generate_service_account_key(service_account_email: str, project_id: str, key_path: str) -> bool:
    """Generate service account key if requested."""
    print_colored("")
    print_colored("Service Account Key Management...", Colors.GREEN)
    
    if not os.path.exists(key_path):
        try:
            response = input("  Do you want to generate a service account key? (Y/N): ").strip().lower()
            if response in ['y', 'yes']:
                run_command([
                    "gcloud", "iam", "service-accounts", "keys", "create", key_path,
                    "--iam-account", service_account_email,
                    "--project", project_id
                ])
                
                print_colored(f"  Service account key saved to: {key_path}", Colors.GREEN)
                print_colored("  IMPORTANT: Keep this key secure and add to .gitignore!", Colors.RED)
                return True
        except (KeyboardInterrupt, EOFError):
            print_colored("  Key generation skipped", Colors.YELLOW)
    else:
        print_colored(f"  Service account key already exists: {key_path}", Colors.GREEN)
    
    return False


def save_configuration(project_id: str, region: str, zone: str, registry_name: str, 
                      bucket_name: str, service_account_email: str) -> None:
    """Save configuration to JSON file."""
    config = {
        "project_id": project_id,
        "region": region,
        "zone": zone,
        "registry_name": registry_name,
        "bucket_name": bucket_name,
        "service_account": service_account_email
    }
    
    config_path = "gcp-staging-config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print_colored(f"Configuration saved to {config_path}", Colors.YELLOW)


def main():
    """Main function to orchestrate the GCP resources setup."""
    parser = argparse.ArgumentParser(description="Setup GCP Staging Resources")
    parser.add_argument("--service-account-key-path", 
                       default=os.environ.get("GCP_SA_KEY_PATH"),
                       help="Path to service account key file")
    parser.add_argument("--service-account-email", 
                       default="netra-staging-deploy@netra-staging.iam.gserviceaccount.com",
                       help="Service account email")
    parser.add_argument("--project-id", default=PROJECT_ID,
                       help=f"GCP Project ID (default: {PROJECT_ID})")
    
    args = parser.parse_args()
    
    print_colored("=" * 48, Colors.BLUE)
    print_colored("  GCP STAGING RESOURCES SETUP", Colors.BLUE)
    print_colored("=" * 48, Colors.BLUE)
    print_colored("")
    
    # Execute setup steps
    success = True
    success &= authenticate(args.service_account_key_path)
    success &= set_project(args.project_id)
    success &= enable_apis(args.project_id)
    success &= setup_service_account(args.project_id, args.service_account_email)
    success &= create_artifact_registry(args.project_id, REGION, REGISTRY_NAME)
    success &= create_secrets(args.project_id)
    success &= create_storage_bucket(args.project_id, REGION)
    
    setup_monitoring()
    configure_networking()
    
    # Generate service account key if needed
    key_path = "./gcp-sa-key.json"
    generate_service_account_key(args.service_account_email, args.project_id, key_path)
    
    # Save configuration
    bucket_name = f"{args.project_id}-backups"
    save_configuration(args.project_id, REGION, ZONE, REGISTRY_NAME, 
                      bucket_name, args.service_account_email)
    
    # Summary
    if success:
        print_colored("")
        print_colored("=" * 48, Colors.GREEN)
        print_colored("  RESOURCE SETUP COMPLETED", Colors.GREEN)
        print_colored("=" * 48, Colors.GREEN)
        print_colored("")
        print_colored("Resources created/verified:", Colors.CYAN)
        print_colored("  ✓ APIs enabled", Colors.GREEN)
        print_colored(f"  ✓ Service account: {args.service_account_email}", Colors.GREEN)
        print_colored(f"  ✓ Artifact Registry: {REGISTRY_NAME}", Colors.GREEN)
        print_colored("  ✓ Secrets created", Colors.GREEN)
        print_colored(f"  ✓ Storage bucket: {bucket_name}", Colors.GREEN)
        print_colored("")
        print_colored("Next steps:", Colors.YELLOW)
        print_colored("  1. Update secret values with real API keys", Colors.CYAN)
        print_colored("  2. Run deployment script: python deploy_staging.py", Colors.CYAN)
        print_colored("  3. Configure monitoring dashboards", Colors.CYAN)
        print_colored("")
        sys.exit(0)
    else:
        print_colored("")
        print_colored("=" * 48, Colors.RED)
        print_colored("  RESOURCE SETUP FAILED", Colors.RED)
        print_colored("=" * 48, Colors.RED)
        print_colored("")
        print_colored("Some resources could not be created.", Colors.RED)
        print_colored("Please check the errors above and try again.", Colors.YELLOW)
        sys.exit(1)


if __name__ == "__main__":
    main()