#!/usr/bin/env python3
"""
Deploy to GCP Staging - Python Script
Handles both backend and auth service deployments with proper environment variables
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Optional

# Configuration
PROJECT_ID = "netra-staging"
REGION = "us-central1"
REGISTRY = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/netra-staging"

# Services configuration
SERVICES = {
    "backend": {
        "name": "netra-backend-staging",
        "dockerfile": "Dockerfile.backend",
        "image": f"{REGISTRY}/netra-backend-staging:latest",
        "env_vars": {
            "ENVIRONMENT": "staging"
        },
        "secrets": {
            "DATABASE_URL": "database-url-staging:latest",
            "JWT_SECRET_KEY": "jwt-secret-key-staging:latest",
            "FERNET_KEY": "fernet-key-staging:latest",
            "GEMINI_API_KEY": "gemini-api-key-staging:latest"
        },
        "cloudsql_instances": "netra-staging:us-central1:staging-shared-postgres"
    },
    "auth": {
        "name": "netra-auth-service",
        "dockerfile": "Dockerfile.auth",
        "image": f"{REGISTRY}/netra-auth-service:latest",
        "env_vars": {
            "ENVIRONMENT": "staging"
        },
        "secrets": {
            "DATABASE_URL": "database-url-staging:latest",
            "JWT_SECRET_KEY": "jwt-secret-staging:latest",
            "GOOGLE_CLIENT_ID": "google-client-id-staging:latest",
            "GOOGLE_CLIENT_SECRET": "google-client-secret-staging:latest"
        },
        "cloudsql_instances": "netra-staging:us-central1:staging-shared-postgres"
    },
    "frontend": {
        "name": "netra-frontend-staging",
        "dockerfile": "Dockerfile.frontend.staging",
        "image": f"{REGISTRY}/netra-frontend-staging:latest",
        "env_vars": {
            "NEXT_PUBLIC_API_URL": "https://netra-backend-staging-pnovr5vsba-uc.a.run.app",
            "NEXT_PUBLIC_AUTH_URL": "https://netra-auth-service-pnovr5vsba-uc.a.run.app"
        },
        "secrets": {},
        "cloudsql_instances": None
    }
}

def run_command(cmd: List[str], check: bool = True, capture_output: bool = False) -> Optional[subprocess.CompletedProcess]:
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=check, capture_output=capture_output, text=True)
        if capture_output and result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if capture_output and e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return None

def authenticate():
    """Authenticate with GCP using service account."""
    key_file = "gcp-staging-sa-key.json"
    if not Path(key_file).exists():
        print(f"Error: Service account key file {key_file} not found")
        print("Run: python setup_staging_auth.py")
        sys.exit(1)
    
    run_command(["gcloud", "auth", "activate-service-account", f"--key-file={key_file}"])
    run_command(["gcloud", "config", "set", "project", PROJECT_ID])
    run_command(["gcloud", "auth", "configure-docker", f"{REGION}-docker.pkg.dev", "--quiet"])
    print("✓ Authentication successful")

def build_image(service: str, config: Dict):
    """Build Docker image for a service."""
    print(f"\n📦 Building {service} image...")
    dockerfile = config["dockerfile"]
    image = config["image"]
    
    if not Path(dockerfile).exists():
        print(f"Error: Dockerfile {dockerfile} not found")
        return False
    
    run_command(["docker", "build", "-t", image, "-f", dockerfile, "."])
    print(f"✓ Built {service} image")
    return True

def push_image(service: str, config: Dict):
    """Push Docker image to registry."""
    print(f"\n🚀 Pushing {service} image...")
    image = config["image"]
    
    # Retry logic for push
    max_retries = 3
    for attempt in range(max_retries):
        result = run_command(["docker", "push", image], check=False)
        if result and result.returncode == 0:
            print(f"✓ Pushed {service} image")
            return True
        
        if attempt < max_retries - 1:
            print(f"Push failed, retrying in 5 seconds... (attempt {attempt + 2}/{max_retries})")
            time.sleep(5)
    
    print(f"Error: Failed to push {service} image after {max_retries} attempts")
    return False

def deploy_service(service: str, config: Dict):
    """Deploy service to Cloud Run."""
    print(f"\n🌐 Deploying {service}...")
    
    cmd = [
        "gcloud", "run", "deploy", config["name"],
        "--image", config["image"],
        "--region", REGION,
        "--project", PROJECT_ID,
        "--platform", "managed",
        "--allow-unauthenticated"
    ]
    
    # Add environment variables
    if config["env_vars"]:
        env_vars = ",".join([f"{k}={v}" for k, v in config["env_vars"].items()])
        cmd.extend(["--set-env-vars", env_vars])
    
    # Add secrets
    if config["secrets"]:
        secrets = ",".join([f"{k}={v}" for k, v in config["secrets"].items()])
        cmd.extend(["--update-secrets", secrets])
    
    # Add Cloud SQL instances
    if config["cloudsql_instances"]:
        cmd.extend(["--set-cloudsql-instances", config["cloudsql_instances"]])
    
    # Add service-specific configurations
    if service == "backend":
        cmd.extend(["--memory", "2Gi", "--cpu", "2", "--min-instances", "1", "--max-instances", "10"])
    elif service == "auth":
        cmd.extend(["--memory", "1Gi", "--cpu", "1", "--min-instances", "1", "--max-instances", "5"])
    elif service == "frontend":
        cmd.extend(["--memory", "512Mi", "--cpu", "1", "--min-instances", "1", "--max-instances", "5"])
    
    result = run_command(cmd, check=False)
    if result and result.returncode == 0:
        print(f"✓ Deployed {service}")
        return True
    else:
        print(f"Error: Failed to deploy {service}")
        return False

def check_service_health(service: str, config: Dict):
    """Check if service is healthy."""
    print(f"\n🔍 Checking {service} health...")
    
    # Get service URL
    result = run_command([
        "gcloud", "run", "services", "describe", config["name"],
        "--region", REGION,
        "--project", PROJECT_ID,
        "--format", "value(status.url)"
    ], capture_output=True, check=False)
    
    if not result or not result.stdout:
        print(f"Warning: Could not get URL for {service}")
        return False
    
    url = result.stdout.strip()
    health_endpoint = f"{url}/health/ready" if service in ["backend", "auth"] else url
    
    # Check health with curl
    result = run_command(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", health_endpoint], 
                         capture_output=True, check=False)
    
    if result and result.stdout:
        status_code = result.stdout.strip()
        if status_code == "200":
            print(f"✓ {service} is healthy (HTTP {status_code})")
            return True
        else:
            print(f"⚠️ {service} health check returned HTTP {status_code}")
            return False
    
    return False

def main():
    """Main deployment function."""
    print("🚀 Starting GCP Staging Deployment")
    print(f"Project: {PROJECT_ID}")
    print(f"Region: {REGION}")
    
    # Parse arguments
    services_to_deploy = sys.argv[1:] if len(sys.argv) > 1 else ["backend", "auth", "frontend"]
    
    # Validate services
    for service in services_to_deploy:
        if service not in SERVICES:
            print(f"Error: Unknown service '{service}'")
            print(f"Available services: {', '.join(SERVICES.keys())}")
            sys.exit(1)
    
    # Authenticate
    authenticate()
    
    # Deploy each service
    success_count = 0
    failed_services = []
    
    for service in services_to_deploy:
        config = SERVICES[service]
        print(f"\n{'='*50}")
        print(f"Deploying {service.upper()}")
        print(f"{'='*50}")
        
        # Build
        if not build_image(service, config):
            failed_services.append(service)
            continue
        
        # Push
        if not push_image(service, config):
            failed_services.append(service)
            continue
        
        # Deploy
        if not deploy_service(service, config):
            failed_services.append(service)
            continue
        
        # Health check
        time.sleep(10)  # Wait for service to start
        if check_service_health(service, config):
            success_count += 1
        else:
            print(f"Warning: {service} deployed but health check failed")
            success_count += 1  # Count as success if deployed
    
    # Summary
    print(f"\n{'='*50}")
    print("Deployment Summary")
    print(f"{'='*50}")
    print(f"✓ Successfully deployed: {success_count}/{len(services_to_deploy)} services")
    
    if failed_services:
        print(f"✗ Failed services: {', '.join(failed_services)}")
        sys.exit(1)
    else:
        print("\n🎉 All services deployed successfully!")
        
        # Print service URLs
        print("\nService URLs:")
        for service in services_to_deploy:
            config = SERVICES[service]
            result = run_command([
                "gcloud", "run", "services", "describe", config["name"],
                "--region", REGION,
                "--project", PROJECT_ID,
                "--format", "value(status.url)"
            ], capture_output=True, check=False)
            
            if result and result.stdout:
                print(f"  {service}: {result.stdout.strip()}")

if __name__ == "__main__":
    main()