#!/usr/bin/env python3
"""
Fix WebSocket timeout configuration issues in GCP staging.
This script validates and updates the staging deployment configuration.

Run: python scripts/fix_staging_websocket_timeouts.py
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_current_config() -> Dict[str, Any]:
    """Check current GCP Cloud Run configuration for staging."""
    print(" SEARCH:  Checking current staging configuration...")
    
    try:
        # Get current service configuration
        cmd = [
            "gcloud", "run", "services", "describe", 
            "netra-backend-staging",
            "--region", "us-central1",
            "--project", "netra-staging",
            "--format", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f" FAIL:  Failed to get service config: {result.stderr}")
            return {}
            
        config = json.loads(result.stdout)
        
        # Extract environment variables
        env_vars = {}
        spec = config.get("spec", {})
        template = spec.get("template", {})
        containers = template.get("spec", {}).get("containers", [])
        
        if containers:
            container = containers[0]
            env_list = container.get("env", [])
            for env_var in env_list:
                name = env_var.get("name")
                value = env_var.get("value")
                if name:
                    env_vars[name] = value
        
        return env_vars
        
    except Exception as e:
        print(f" FAIL:  Error checking config: {e}")
        return {}


def validate_websocket_config(env_vars: Dict[str, str]) -> Dict[str, str]:
    """Validate WebSocket configuration and identify missing variables."""
    print("\n[U+1F4CB] Validating WebSocket configuration...")
    
    required_vars = {
        "WEBSOCKET_CONNECTION_TIMEOUT": "900",
        "WEBSOCKET_HEARTBEAT_INTERVAL": "25", 
        "WEBSOCKET_HEARTBEAT_TIMEOUT": "75",
        "WEBSOCKET_CLEANUP_INTERVAL": "180",
        "WEBSOCKET_STALE_TIMEOUT": "900"
    }
    
    missing_vars = {}
    incorrect_vars = {}
    
    for var, expected_value in required_vars.items():
        if var not in env_vars:
            missing_vars[var] = expected_value
            print(f"   FAIL:  MISSING: {var} (should be {expected_value})")
        elif env_vars[var] != expected_value:
            incorrect_vars[var] = {
                "current": env_vars[var],
                "expected": expected_value
            }
            print(f"   WARNING: [U+FE0F]  INCORRECT: {var} = {env_vars[var]} (should be {expected_value})")
        else:
            print(f"   PASS:  OK: {var} = {env_vars[var]}")
    
    return missing_vars


def update_deployment_script() -> bool:
    """Update the deployment script with correct WebSocket configuration."""
    print("\n[U+1F527] Updating deployment script...")
    
    deploy_script = project_root / "scripts" / "deploy_to_gcp.py"
    
    if not deploy_script.exists():
        print(f" FAIL:  Deployment script not found: {deploy_script}")
        return False
    
    # Read current script
    content = deploy_script.read_text()
    
    # Check if WebSocket vars already added
    if "WEBSOCKET_CONNECTION_TIMEOUT" in content:
        print(" PASS:  Deployment script already updated with WebSocket configuration")
        return True
    
    # Find the backend service config and add WebSocket vars
    search_str = '"CLICKHOUSE_SECURE": "true",'
    replace_str = '''"CLICKHOUSE_SECURE": "true",
                    # CRITICAL FIX: WebSocket timeout configuration for GCP staging
                    "WEBSOCKET_CONNECTION_TIMEOUT": "900",  # 15 minutes for GCP load balancer
                    "WEBSOCKET_HEARTBEAT_INTERVAL": "25",   # Send heartbeat every 25s
                    "WEBSOCKET_HEARTBEAT_TIMEOUT": "75",    # Wait 75s for heartbeat response  
                    "WEBSOCKET_CLEANUP_INTERVAL": "180",    # Cleanup every 3 minutes
                    "WEBSOCKET_STALE_TIMEOUT": "900",       # 15 minutes before marking connection stale'''
    
    if search_str not in content:
        print(" FAIL:  Could not find insertion point in deployment script")
        return False
    
    updated_content = content.replace(search_str, replace_str)
    
    # Write updated script
    deploy_script.write_text(updated_content)
    print(" PASS:  Deployment script updated successfully")
    return True


def update_cloud_run_env_vars(missing_vars: Dict[str, str]) -> bool:
    """Update Cloud Run service with missing environment variables."""
    if not missing_vars:
        print("\n PASS:  No missing variables to update")
        return True
    
    print(f"\n[U+1F680] Updating Cloud Run service with {len(missing_vars)} missing variables...")
    
    # Build gcloud command
    cmd = [
        "gcloud", "run", "services", "update",
        "netra-backend-staging",
        "--region", "us-central1",
        "--project", "netra-staging"
    ]
    
    # Add each missing environment variable
    for var, value in missing_vars.items():
        cmd.extend(["--set-env-vars", f"{var}={value}"])
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f" FAIL:  Failed to update service: {result.stderr}")
            return False
        
        print(" PASS:  Cloud Run service updated successfully")
        return True
        
    except Exception as e:
        print(f" FAIL:  Error updating service: {e}")
        return False


def verify_deployment() -> bool:
    """Verify the deployment has correct WebSocket configuration."""
    print("\n SEARCH:  Verifying deployment configuration...")
    
    env_vars = check_current_config()
    missing_vars = validate_websocket_config(env_vars)
    
    if not missing_vars:
        print("\n PASS:  All WebSocket environment variables are correctly configured!")
        return True
    else:
        print(f"\n FAIL:  {len(missing_vars)} WebSocket variables still missing")
        return False


def main():
    """Main function to fix staging WebSocket timeouts."""
    print("=" * 60)
    print("GCP STAGING WEBSOCKET TIMEOUT FIX")
    print("=" * 60)
    
    # Step 1: Check current configuration
    env_vars = check_current_config()
    
    if not env_vars:
        print("\n WARNING: [U+FE0F]  Could not retrieve current configuration")
        print("Make sure you're authenticated with gcloud:")
        print("  gcloud auth login")
        print("  gcloud config set project netra-staging")
        return 1
    
    # Step 2: Validate WebSocket configuration
    missing_vars = validate_websocket_config(env_vars)
    
    # Step 3: Update deployment script for future deployments
    script_updated = update_deployment_script()
    
    # Step 4: Update Cloud Run service immediately
    if missing_vars:
        print("\n WARNING: [U+FE0F]  Missing WebSocket configuration detected!")
        response = input("\nUpdate Cloud Run service now? (y/n): ")
        
        if response.lower() == 'y':
            if update_cloud_run_env_vars(missing_vars):
                # Step 5: Verify the update
                if verify_deployment():
                    print("\n CELEBRATION:  SUCCESS: WebSocket timeouts fixed in staging!")
                    print("\nNext steps:")
                    print("1. Monitor WebSocket connections in staging")
                    print("2. Run E2E tests: python tests/unified_test_runner.py --category e2e --env staging")
                    print("3. Deploy to production when stable")
                    return 0
                else:
                    print("\n WARNING: [U+FE0F]  Update may have partially succeeded. Please verify manually.")
                    return 1
            else:
                print("\n FAIL:  Failed to update Cloud Run service")
                return 1
        else:
            print("\n[U+23ED][U+FE0F]  Skipping Cloud Run update")
            print("Run this script again when ready to update")
            return 0
    else:
        print("\n PASS:  WebSocket configuration is already correct!")
        return 0


if __name__ == "__main__":
    sys.exit(main())