from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Audit and validate OAuth secrets configuration in GCP staging.

This script:
1. Checks if OAuth secrets exist in GCP Secret Manager
2. Validates their format
3. Shows what environment variables are being used
4. Can optionally update the secrets with correct values
"""

import os
import sys
import json
import subprocess
import argparse
from typing import Dict, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_gcloud_command(command: str) -> Tuple[bool, str]:
    """Run a gcloud command and return success status and output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return False, str(e)

def check_secret_exists(project_id: str, secret_name: str) -> bool:
    """Check if a secret exists in GCP Secret Manager."""
    cmd = f"gcloud secrets describe {secret_name} --project={project_id}"
    success, _ = run_gcloud_command(cmd)
    return success

def get_secret_value(project_id: str, secret_name: str) -> Optional[str]:
    """Get the current value of a secret from GCP Secret Manager."""
    cmd = f"gcloud secrets versions access latest --secret={secret_name} --project={project_id}"
    success, output = run_gcloud_command(cmd)
    return output if success else None

def validate_oauth_client_id(client_id: str) -> Tuple[bool, str]:
    """Validate OAuth client ID format."""
    if not client_id:
        return False, "Client ID is empty"
    
    if client_id.startswith("REPLACE_") or client_id == "REPLACE_WITH_REAL_OAUTH_CLIENT_ID":
        return False, "Client ID is a placeholder value"
    
    if not client_id.endswith(".apps.googleusercontent.com"):
        return False, "Client ID should end with .apps.googleusercontent.com"
    
    if len(client_id) < 50:
        return False, f"Client ID seems too short ({len(client_id)} chars)"
    
    return True, "Valid format"

def validate_oauth_client_secret(secret: str) -> Tuple[bool, str]:
    """Validate OAuth client secret format."""
    if not secret:
        return False, "Secret is empty"
    
    if secret.startswith("REPLACE_") or secret == "REPLACE_WITH_REAL_OAUTH_CLIENT_SECRET":
        return False, "Secret is a placeholder value"
    
    if len(secret) < 20:
        return False, f"Secret seems too short ({len(secret)} chars)"
    
    return True, "Valid format"

def audit_oauth_secrets(project_id: str) -> Dict[str, Dict]:
    """Audit OAuth secrets in GCP."""
    logger.info(f"\n{'='*60}")
    logger.info(f" SEARCH:  AUDITING OAUTH SECRETS IN PROJECT: {project_id}")
    logger.info(f"{'='*60}\n")
    
    secrets_to_check = {
        "google-oauth-client-id-staging": {
            "env_var": "GOOGLE_OAUTH_CLIENT_ID_STAGING",
            "validator": validate_oauth_client_id,
            "description": "Google OAuth Client ID for staging"
        },
        "google-oauth-client-secret-staging": {
            "env_var": "GOOGLE_OAUTH_CLIENT_SECRET_STAGING", 
            "validator": validate_oauth_client_secret,
            "description": "Google OAuth Client Secret for staging"
        }
    }
    
    # Also check for legacy/duplicate secrets
    legacy_secrets = [
        "google-client-id",
        "google-client-secret",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET"
    ]
    
    results = {}
    
    # Check main OAuth secrets
    for secret_name, config in secrets_to_check.items():
        logger.info(f"\n[U+1F4CB] Checking: {secret_name}")
        logger.info(f"   Description: {config['description']}")
        
        result = {
            "exists": False,
            "value": None,
            "valid": False,
            "validation_message": "",
            "env_var": config['env_var']
        }
        
        # Check if secret exists
        if check_secret_exists(project_id, secret_name):
            result["exists"] = True
            logger.info(f"    PASS:  Secret exists in GCP")
            
            # Get and validate secret value
            value = get_secret_value(project_id, secret_name)
            if value:
                result["value"] = value
                valid, message = config['validator'](value)
                result["valid"] = valid
                result["validation_message"] = message
                
                if valid:
                    logger.info(f"    PASS:  Secret format is valid: {message}")
                    # Show partial value for verification
                    if "client-id" in secret_name:
                        logger.info(f"   [U+1F4DD] Client ID starts with: {value[:30]}...")
                    else:
                        logger.info(f"   [U+1F4DD] Secret length: {len(value)} chars")
                else:
                    logger.error(f"    FAIL:  Invalid secret: {message}")
                    if "placeholder" in message.lower():
                        logger.error(f"    WARNING: [U+FE0F]  Current value: {value}")
            else:
                logger.error(f"    FAIL:  Could not retrieve secret value")
        else:
            logger.error(f"    FAIL:  Secret does NOT exist in GCP")
            logger.info(f"    IDEA:  Create it with: gcloud secrets create {secret_name} --project={project_id}")
        
        results[secret_name] = result
    
    # Check for legacy secrets
    logger.info(f"\n{'='*60}")
    logger.info(" SEARCH:  CHECKING FOR LEGACY/DUPLICATE SECRETS")
    logger.info(f"{'='*60}")
    
    for legacy_secret in legacy_secrets:
        if check_secret_exists(project_id, legacy_secret):
            logger.warning(f"    WARNING: [U+FE0F]  Found legacy secret: {legacy_secret}")
            logger.warning(f"      This should be removed to avoid confusion")
    
    # Check environment variables
    logger.info(f"\n{'='*60}")
    logger.info(" SEARCH:  CHECKING LOCAL ENVIRONMENT VARIABLES")
    logger.info(f"{'='*60}\n")
    
    for secret_name, result in results.items():
        env_var = result["env_var"]
        env_value = os.environ.get(env_var)
        if env_value:
            logger.info(f"    PASS:  {env_var} is set locally")
            valid, message = secrets_to_check[secret_name]['validator'](env_value)
            if valid:
                logger.info(f"      Valid format: {message}")
            else:
                logger.warning(f"       WARNING: [U+FE0F]  Invalid: {message}")
        else:
            logger.warning(f"    WARNING: [U+FE0F]  {env_var} is NOT set locally")
    
    return results

def update_secret(project_id: str, secret_name: str, value: str) -> bool:
    """Update or create a secret in GCP Secret Manager."""
    # Check if secret exists
    if not check_secret_exists(project_id, secret_name):
        # Create the secret
        logger.info(f"Creating secret: {secret_name}")
        cmd = f"gcloud secrets create {secret_name} --project={project_id}"
        success, output = run_gcloud_command(cmd)
        if not success:
            logger.error(f"Failed to create secret: {output}")
            return False
    
    # Add new version with the value
    logger.info(f"Updating secret: {secret_name}")
    cmd = f'echo -n "{value}" | gcloud secrets versions add {secret_name} --data-file=- --project={project_id}'
    success, output = run_gcloud_command(cmd)
    if success:
        logger.info(f" PASS:  Successfully updated {secret_name}")
    else:
        logger.error(f" FAIL:  Failed to update {secret_name}: {output}")
    return success

def main():
    parser = argparse.ArgumentParser(description="Audit OAuth secrets in GCP staging")
    parser.add_argument("--project", default="netra-staging", help="GCP project ID")
    parser.add_argument("--update", action="store_true", help="Update secrets with environment variables")
    parser.add_argument("--client-id", help="OAuth Client ID to set")
    parser.add_argument("--client-secret", help="OAuth Client Secret to set")
    
    args = parser.parse_args()
    
    # Audit current state
    results = audit_oauth_secrets(args.project)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(" CHART:  SUMMARY")
    logger.info(f"{'='*60}\n")
    
    all_valid = True
    for secret_name, result in results.items():
        status = " PASS: " if result["valid"] else " FAIL: "
        logger.info(f"{status} {secret_name}: {'Valid' if result['valid'] else 'Invalid'}")
        if not result["valid"]:
            all_valid = False
            logger.info(f"   Issue: {result['validation_message']}")
    
    # Update if requested
    if args.update or args.client_id or args.client_secret:
        logger.info(f"\n{'='*60}")
        logger.info("[U+1F527] UPDATING SECRETS")
        logger.info(f"{'='*60}\n")
        
        updates = {}
        
        # Determine what to update
        if args.client_id:
            updates["google-oauth-client-id-staging"] = args.client_id
        elif os.environ.get("GOOGLE_OAUTH_CLIENT_ID_STAGING"):
            updates["google-oauth-client-id-staging"] = os.environ["GOOGLE_OAUTH_CLIENT_ID_STAGING"]
        
        if args.client_secret:
            updates["google-oauth-client-secret-staging"] = args.client_secret
        elif os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_STAGING"):
            updates["google-oauth-client-secret-staging"] = os.environ["GOOGLE_OAUTH_CLIENT_SECRET_STAGING"]
        
        # Validate before updating
        for secret_name, value in updates.items():
            config = {
                "google-oauth-client-id-staging": validate_oauth_client_id,
                "google-oauth-client-secret-staging": validate_oauth_client_secret
            }.get(secret_name)
            
            if config:
                valid, message = config(value)
                if not valid:
                    logger.error(f" FAIL:  Cannot update {secret_name}: {message}")
                    continue
                
                if update_secret(args.project, secret_name, value):
                    logger.info(f" PASS:  Updated {secret_name}")
                else:
                    logger.error(f" FAIL:  Failed to update {secret_name}")
    
    # Final recommendations
    if not all_valid:
        logger.info(f"\n{'='*60}")
        logger.info(" WARNING: [U+FE0F]  ACTION REQUIRED")
        logger.info(f"{'='*60}\n")
        logger.info("To fix OAuth in staging:")
        logger.info("1. Get your OAuth credentials from Google Cloud Console")
        logger.info("2. Run this script with --update flag and credentials:")
        logger.info("   python scripts/audit_staging_oauth_secrets.py --update \\")
        logger.info("     --client-id YOUR_CLIENT_ID \\")
        logger.info("     --client-secret YOUR_SECRET")
        logger.info("\n3. Then redeploy the auth service:")
        logger.info("   python scripts/deploy_to_gcp.py --service auth --build-local")
        
        return 1
    else:
        logger.info(f"\n PASS:  All OAuth secrets are properly configured!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
