#!/usr/bin/env python3
"""
Validation script for GCP Terraform infrastructure
Ensures all prerequisites are met before deployment
"""

import subprocess
import sys
import json
import os
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    import locale
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    sys.stdout.reconfigure(encoding='utf-8')

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_status(status, message):
    """Print colored status message"""
    if status == "success":
        print(f"{Colors.GREEN}[U+2713]{Colors.NC} {message}")
    elif status == "error":
        print(f"{Colors.RED}[U+2717]{Colors.NC} {message}")
    elif status == "warning":
        print(f"{Colors.YELLOW} WARNING: {Colors.NC} {message}")
    elif status == "info":
        print(f"{Colors.BLUE}[U+2139]{Colors.NC} {message}")

def run_command(cmd, capture=True):
    """Run a command and return output"""
    try:
        result = subprocess.run(
            cmd, 
            capture_output=capture, 
            text=True, 
            check=True,
            shell=True if sys.platform == "win32" else False
        )
        return result.stdout.strip() if capture else None
    except subprocess.CalledProcessError as e:
        return None

def check_command_exists(command):
    """Check if a command exists"""
    return run_command(["which", command] if sys.platform != "win32" else ["where", command]) is not None

def check_gcloud():
    """Validate gcloud CLI installation and configuration"""
    print("\n[U+1F4CB] Checking GCloud CLI...")
    
    # Check if gcloud is installed
    if not check_command_exists("gcloud"):
        print_status("error", "gcloud CLI is not installed")
        print("  Install from: https://cloud.google.com/sdk/docs/install")
        return False
    
    print_status("success", "gcloud CLI is installed")
    
    # Check authentication
    auth_check = run_command(["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=json"])
    if not auth_check or auth_check == "[]":
        print_status("error", "Not authenticated with gcloud")
        print("  Run: gcloud auth login")
        print("  Run: gcloud auth application-default login")
        return False
    
    auth_data = json.loads(auth_check)
    print_status("success", f"Authenticated as: {auth_data[0]['account']}")
    
    # Check project
    project = run_command(["gcloud", "config", "get-value", "project"])
    if not project:
        print_status("error", "No GCP project set")
        print("  Run: gcloud config set project netra-staging")
        return False
    
    print_status("success", f"Project set to: {project}")
    
    # Check required APIs
    print("\n[U+1F4CB] Checking required GCP APIs...")
    required_apis = [
        "sqladmin.googleapis.com",
        "compute.googleapis.com",
        "servicenetworking.googleapis.com",
        "redis.googleapis.com",
        "secretmanager.googleapis.com",
        "run.googleapis.com"
    ]
    
    for api in required_apis:
        api_check = run_command([
            "gcloud", "services", "list", 
            f"--filter=name:{api}", 
            "--format=value(name)",
            f"--project={project}"
        ])
        if api_check == api:
            print_status("success", f"API enabled: {api}")
        else:
            print_status("warning", f"API may not be enabled: {api}")
            print(f"  Terraform will enable it automatically")
    
    return True

def check_terraform():
    """Validate Terraform installation"""
    print("\n[U+1F4CB] Checking Terraform...")
    
    if not check_command_exists("terraform"):
        print_status("error", "Terraform is not installed")
        print("  Install from: https://www.terraform.io/downloads")
        return False
    
    # Check version
    version_output = run_command(["terraform", "version", "-json"])
    if version_output:
        version_data = json.loads(version_output)
        version = version_data.get("terraform_version", "unknown")
        print_status("success", f"Terraform version: {version}")
        
        # Check minimum version (1.5.0)
        if version != "unknown":
            major, minor, _ = version.split(".")
            if int(major) < 1 or (int(major) == 1 and int(minor) < 5):
                print_status("warning", "Terraform version is below 1.5.0")
                print("  Consider upgrading for best compatibility")
    else:
        print_status("warning", "Could not determine Terraform version")
    
    return True

def check_terraform_files():
    """Validate Terraform configuration files"""
    print("\n[U+1F4CB] Checking Terraform configuration...")
    
    required_files = [
        "main.tf",
        "variables.tf",
        "cloud-sql.tf",
        "redis.tf",
        "secrets.tf",
        "outputs.tf",
        "versions.tf"
    ]
    
    all_present = True
    for file in required_files:
        if Path(file).exists():
            print_status("success", f"Found: {file}")
        else:
            print_status("error", f"Missing: {file}")
            all_present = False
    
    # Check for tfvars
    if Path("terraform.tfvars").exists():
        print_status("success", "terraform.tfvars exists")
    elif Path("terraform.tfvars.example").exists():
        print_status("warning", "terraform.tfvars not found, but example exists")
        print("  Run: cp terraform.tfvars.example terraform.tfvars")
    else:
        print_status("error", "No terraform.tfvars or example found")
        all_present = False
    
    # Validate Terraform configuration
    if all_present:
        print("\n[U+1F4CB] Validating Terraform configuration...")
        
        # Initialize if needed
        if not Path(".terraform").exists():
            print_status("info", "Initializing Terraform...")
            init_result = run_command(["terraform", "init", "-backend=false"])
            if init_result is not None:
                print_status("success", "Terraform initialized")
            else:
                print_status("error", "Terraform init failed")
                return False
        
        # Validate configuration
        validate_result = run_command(["terraform", "validate", "-json"])
        if validate_result:
            validate_data = json.loads(validate_result)
            if validate_data.get("valid"):
                print_status("success", "Terraform configuration is valid")
            else:
                print_status("error", "Terraform configuration has errors")
                for diag in validate_data.get("diagnostics", []):
                    print(f"  {diag.get('summary', 'Unknown error')}")
                return False
    
    return all_present

def check_existing_resources():
    """Check for existing GCP resources"""
    print("\n[U+1F4CB] Checking existing GCP resources...")
    
    project = run_command(["gcloud", "config", "get-value", "project"])
    if not project:
        print_status("warning", "Could not determine project")
        return
    
    # Check for existing Cloud SQL instances
    instances = run_command([
        "gcloud", "sql", "instances", "list",
        f"--project={project}",
        "--format=json"
    ])
    
    if instances:
        instance_data = json.loads(instances)
        if instance_data:
            print_status("info", f"Found {len(instance_data)} existing Cloud SQL instance(s):")
            for instance in instance_data:
                name = instance.get("name")
                version = instance.get("databaseVersion")
                state = instance.get("state")
                print(f"    - {name} ({version}) - {state}")
                
                if "staging-shared-postgres" in name.lower():
                    print_status("warning", f"Found old staging instance: {name}")
                    print("  This will be migrated to PostgreSQL 17")
    
    # Check for state bucket
    bucket_name = f"{project}-terraform-state"
    bucket_check = run_command([
        "gsutil", "ls", f"gs://{bucket_name}"
    ])
    
    if bucket_check is not None:
        print_status("success", f"State bucket exists: {bucket_name}")
    else:
        print_status("info", f"State bucket will be created: {bucket_name}")

def check_python():
    """Check Python and required packages"""
    print("\n[U+1F4CB] Checking Python environment...")
    
    if not check_command_exists("python3") and not check_command_exists("python"):
        print_status("error", "Python is not installed")
        return False
    
    python_cmd = "python3" if check_command_exists("python3") else "python"
    
    # Check version
    version = run_command([python_cmd, "--version"])
    if version:
        print_status("success", f"Python version: {version}")
    
    # Check for migration script
    if Path("migrate.py").exists():
        print_status("success", "Migration script found")
    else:
        print_status("error", "Migration script (migrate.py) not found")
        return False
    
    return True

def main():
    """Main validation function"""
    print("=" * 60)
    print(f"{Colors.BLUE}GCP Terraform Infrastructure Validation{Colors.NC}")
    print("=" * 60)
    
    all_checks_passed = True
    
    # Run all checks
    if not check_gcloud():
        all_checks_passed = False
    
    if not check_terraform():
        all_checks_passed = False
    
    if not check_terraform_files():
        all_checks_passed = False
    
    if not check_python():
        all_checks_passed = False
    
    check_existing_resources()
    
    # Summary
    print("\n" + "=" * 60)
    if all_checks_passed:
        print(f"{Colors.GREEN}[U+2713] All validation checks passed!{Colors.NC}")
        print(f"\nNext steps:")
        print(f"1. Review and edit terraform.tfvars if needed")
        print(f"2. Run: terraform init")
        print(f"3. Run: terraform plan")
        print(f"4. Run: terraform apply")
        print(f"5. Run: python migrate.py --project netra-staging")
    else:
        print(f"{Colors.RED}[U+2717] Some validation checks failed{Colors.NC}")
        print(f"\nPlease fix the issues above before proceeding")
        sys.exit(1)

if __name__ == "__main__":
    main()