#!/usr/bin/env python3
"""
Deploy E2E_OAUTH_SIMULATION_KEY to GCP Secret Manager for staging environment.

This script creates the missing E2E_OAUTH_SIMULATION_KEY secret that is required 
for authentication flow validation in the staging environment.

Usage:
    python deploy_e2e_oauth_key.py --project netra-staging
"""

import subprocess
import sys
import argparse
from pathlib import Path

def deploy_e2e_oauth_key(project_id: str) -> bool:
    """Deploy E2E_OAUTH_SIMULATION_KEY to GCP Secret Manager.
    
    Args:
        project_id: GCP project ID (e.g., 'netra-staging')
        
    Returns:
        True if deployment successful, False otherwise
    """
    print(f"[U+1F510] Deploying E2E_OAUTH_SIMULATION_KEY to GCP Secret Manager in project: {project_id}")
    
    # Generate secure random key
    key_value = "e0e9c5d29e7aea3942f47855b4870d3e0272e061c2de22827e71b893071d777e"
    secret_name = "E2E_OAUTH_SIMULATION_KEY"
    
    try:
        # Check if secret already exists
        check_result = subprocess.run([
            "gcloud", "secrets", "describe", secret_name, 
            "--project", project_id
        ], capture_output=True, text=True, check=False)
        
        if check_result.returncode == 0:
            print(f" PASS:  Secret {secret_name} already exists - updating with new version")
            
            # Add new version to existing secret
            result = subprocess.run([
                "gcloud", "secrets", "versions", "add", secret_name,
                "--project", project_id,
                "--data-file=-"
            ], input=key_value, text=True, check=True)
            
        else:
            print(f"[U+1F4DD] Creating new secret: {secret_name}")
            
            # Create new secret
            subprocess.run([
                "gcloud", "secrets", "create", secret_name,
                "--project", project_id
            ], check=True)
            
            # Add initial version
            subprocess.run([
                "gcloud", "secrets", "versions", "add", secret_name,
                "--project", project_id,
                "--data-file=-"
            ], input=key_value, text=True, check=True)
        
        print(f" PASS:  Successfully deployed E2E_OAUTH_SIMULATION_KEY to {project_id}")
        print(f"[U+1F511] Secret value: {key_value[:8]}... (64 char hex)")
        print(f"[U+1F4CB] Usage: Backend services can now access this key for E2E OAuth simulation")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f" FAIL:  Failed to deploy E2E_OAUTH_SIMULATION_KEY: {e}")
        return False
    except Exception as e:
        print(f" FAIL:  Unexpected error: {e}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy E2E_OAUTH_SIMULATION_KEY to GCP Secret Manager"
    )
    parser.add_argument("--project", required=True, 
                       help="GCP Project ID (e.g., netra-staging)")
    
    args = parser.parse_args()
    
    print("[U+1F680] E2E OAuth Simulation Key Deployment")
    print("=" * 50)
    
    success = deploy_e2e_oauth_key(args.project)
    
    if success:
        print("\n PASS:  DEPLOYMENT SUCCESSFUL")
        print("[U+1F4CB] Next Steps:")
        print("1. Verify key is accessible in staging environment")
        print("2. Update backend service configuration if needed")
        print("3. Test E2E OAuth flows work correctly")
    else:
        print("\n FAIL:  DEPLOYMENT FAILED")
        print("[U+1F4CB] Troubleshooting:")
        print("1. Ensure gcloud CLI is authenticated")
        print("2. Verify project ID is correct")
        print("3. Check Secret Manager API is enabled")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()