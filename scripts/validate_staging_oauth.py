#!/usr/bin/env python3
"""
Validate and fix OAuth configuration for staging environment.

This script:
1. Validates OAuth credentials are properly configured
2. Tests OAuth flow with Google 
3. Ensures redirect URIs match staging environment
4. Validates secrets in GCP Secret Manager
"""

import os
import sys

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlencode, quote

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class OAuthStagingValidator:
    """Validates OAuth configuration for staging deployment."""
    
    def __init__(self):
        self.project_id = "netra-staging"
        self.issues_found = []
        self.fixes_applied = []
        
    def log_issue(self, issue: str, severity: str = "ERROR"):
        """Log an issue found during validation."""
        self.issues_found.append(f"[{severity}] {issue}")
        print(f" FAIL:  {severity}: {issue}")
        
    def log_fix(self, fix: str):
        """Log a fix that was applied."""
        self.fixes_applied.append(fix)
        print(f" PASS:  FIXED: {fix}")
        
    def check_local_env_file(self) -> bool:
        """Check if .env.staging has proper OAuth credentials."""
        print("\n SEARCH:  Checking local .env.staging file...")
        
        env_file = project_root / ".env.staging"
        if not env_file.exists():
            self.log_issue(".env.staging file not found")
            return False
            
        with open(env_file, 'r') as f:
            content = f.read()
            
        issues = []
        if "your-staging-google-client-id" in content:
            issues.append("GOOGLE_CLIENT_ID contains placeholder value")
        if "your-staging-google-client-secret" in content:
            issues.append("GOOGLE_CLIENT_SECRET contains placeholder value")
            
        if issues:
            for issue in issues:
                self.log_issue(issue)
            
            # Offer to fix with development credentials for testing
            print("\n WARNING: [U+FE0F]  OAuth credentials are not configured for staging.")
            print("Options:")
            print("1. Use development OAuth credentials (for testing only)")
            print("2. Configure production OAuth credentials (recommended)")
            print("3. Skip (will cause OAuth to fail)")
            
            choice = input("\nEnter choice (1/2/3): ").strip()
            
            if choice == "1":
                # Copy development credentials
                dev_env = project_root / ".env"
                if dev_env.exists():
                    with open(dev_env, 'r') as f:
                        for line in f:
                            if line.startswith("GOOGLE_CLIENT_ID="):
                                client_id = line.split("=", 1)[1].strip()
                            elif line.startswith("GOOGLE_CLIENT_SECRET="):
                                client_secret = line.split("=", 1)[1].strip()
                    
                    # Update .env.staging
                    with open(env_file, 'r') as f:
                        lines = f.readlines()
                    
                    with open(env_file, 'w') as f:
                        for line in lines:
                            if line.startswith("GOOGLE_CLIENT_ID="):
                                f.write(f"GOOGLE_CLIENT_ID={client_id}\n")
                                self.log_fix(f"Updated GOOGLE_CLIENT_ID in .env.staging")
                            elif line.startswith("GOOGLE_CLIENT_SECRET="):
                                f.write(f"GOOGLE_CLIENT_SECRET={client_secret}\n")
                                self.log_fix(f"Updated GOOGLE_CLIENT_SECRET in .env.staging")
                            else:
                                f.write(line)
                    
                    print("\n WARNING: [U+FE0F]  Using development OAuth credentials for staging.")
                    print("Note: Redirect URIs must be configured in Google Console for:")
                    print("  - https://app.staging.netrasystems.ai/auth/callback")
                    print("  - https://auth.staging.netrasystems.ai/auth/callback")
                    return True
                    
            elif choice == "2":
                print("\nTo configure production OAuth credentials:")
                print("1. Go to https://console.cloud.google.com/apis/credentials")
                print("2. Create or select OAuth 2.0 Client ID")
                print("3. Add authorized redirect URIs:")
                print("   - https://app.staging.netrasystems.ai/auth/callback")
                print("   - https://auth.staging.netrasystems.ai/auth/callback")
                print("4. Update .env.staging with the client ID and secret")
                return False
                
        else:
            print(" PASS:  OAuth credentials are configured in .env.staging")
            return True
            
    def check_gcp_secrets(self) -> bool:
        """Check if OAuth secrets exist in GCP Secret Manager."""
        print("\n SEARCH:  Checking GCP Secret Manager...")
        
        secrets_to_check = [
            "google-oauth-client-id-staging",
            "google-oauth-client-secret-staging"
        ]
        
        all_exist = True
        for secret_name in secrets_to_check:
            try:
                cmd = [
                    "gcloud", "secrets", "describe", secret_name,
                    "--project", self.project_id
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                print(f" PASS:  Secret exists: {secret_name}")
                
                # Get the secret value to check if it's a placeholder
                cmd_value = [
                    "gcloud", "secrets", "versions", "access", "latest",
                    "--secret", secret_name,
                    "--project", self.project_id
                ]
                result = subprocess.run(cmd_value, capture_output=True, text=True, check=True)
                value = result.stdout.strip()
                
                if "your-" in value or value == "placeholder":
                    self.log_issue(f"Secret {secret_name} contains placeholder value: {value[:20]}...")
                    all_exist = False
                    
            except subprocess.CalledProcessError:
                self.log_issue(f"Secret not found or inaccessible: {secret_name}")
                all_exist = False
            except FileNotFoundError:
                self.log_issue("gcloud command not found. Install Google Cloud CLI to validate GCP secrets.")
                return False
                
        return all_exist
        
    def create_or_update_gcp_secret(self, secret_name: str, secret_value: str) -> bool:
        """Create or update a secret in GCP Secret Manager."""
        try:
            # Check if secret exists
            cmd_check = [
                "gcloud", "secrets", "describe", secret_name,
                "--project", self.project_id
            ]
            secret_exists = subprocess.run(cmd_check, capture_output=True, text=True).returncode == 0
            
            if secret_exists:
                # Update existing secret
                cmd = ["gcloud", "secrets", "versions", "add", secret_name,
                       "--data-file=-", "--project", self.project_id]
            else:
                # Create new secret
                cmd = ["gcloud", "secrets", "create", secret_name,
                       "--data-file=-", "--project", self.project_id,
                       "--replication-policy", "automatic"]
            
            result = subprocess.run(cmd, input=secret_value, text=True, 
                                    capture_output=True, check=True)
            
            action = "Updated" if secret_exists else "Created"
            self.log_fix(f"{action} GCP secret: {secret_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log_issue(f"Failed to create/update secret {secret_name}: {e.stderr}")
            return False
            
    def sync_secrets_to_gcp(self) -> bool:
        """Sync OAuth credentials from .env.staging to GCP Secret Manager."""
        print("\n CYCLE:  Syncing OAuth credentials to GCP Secret Manager...")
        
        env_file = project_root / ".env.staging"
        if not env_file.exists():
            self.log_issue(".env.staging not found for syncing")
            return False
            
        # Load credentials from .env.staging
        credentials = {}
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith("GOOGLE_CLIENT_ID="):
                    credentials["google-oauth-client-id-staging"] = line.split("=", 1)[1].strip()
                elif line.startswith("GOOGLE_CLIENT_SECRET="):
                    credentials["google-oauth-client-secret-staging"] = line.split("=", 1)[1].strip()
                    
        # Check for placeholders
        if any("your-" in v for v in credentials.values()):
            self.log_issue("Cannot sync placeholder OAuth credentials to GCP")
            return False
            
        # Sync to GCP
        success = True
        for secret_name, secret_value in credentials.items():
            if not self.create_or_update_gcp_secret(secret_name, secret_value):
                success = False
                
        return success
        
    def validate_redirect_uris(self) -> bool:
        """Validate that OAuth redirect URIs are configured correctly."""
        print("\n SEARCH:  Validating OAuth redirect URIs...")
        
        required_uris = [
            "https://app.staging.netrasystems.ai/auth/callback",
            "https://auth.staging.netrasystems.ai/auth/callback",
            "https://api.staging.netrasystems.ai/auth/callback"
        ]
        
        print("\n[U+1F4CB] Required redirect URIs for staging:")
        for uri in required_uris:
            print(f"  - {uri}")
            
        print("\n WARNING: [U+FE0F]  Manual Action Required:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Select your OAuth 2.0 Client ID")
        print("3. Ensure all redirect URIs above are added")
        print("4. Save the changes")
        
        try:
            confirmed = input("\nHave you added all redirect URIs? (y/n): ").strip().lower()
            return confirmed == 'y'
        except (EOFError, KeyboardInterrupt):
            # When running non-interactively, assume this is a validation check
            print("(Running non-interactively - assuming manual validation is needed)")
            return False
        
    async def test_oauth_flow(self) -> bool:
        """Test the OAuth flow with actual credentials."""
        print("\n[U+1F9EA] Testing OAuth flow...")
        
        # Load credentials
        env_file = project_root / ".env.staging"
        if not env_file.exists():
            self.log_issue("Cannot test OAuth flow - .env.staging not found")
            return False
            
        client_id = None
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith("GOOGLE_CLIENT_ID="):
                    client_id = line.split("=", 1)[1].strip()
                    break
                    
        if not client_id or "your-" in client_id:
            self.log_issue("Cannot test OAuth flow - invalid credentials")
            return False
            
        # Generate OAuth URL
        auth_params = {
            "client_id": client_id,
            "redirect_uri": "https://auth.staging.netrasystems.ai/auth/callback",
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"
        
        print(f"\n[U+1F517] OAuth Authorization URL:")
        print(f"   {auth_url}")
        
        print("\n PASS:  OAuth URL generated successfully")
        print("   Test the URL in a browser to verify the flow")
        
        return True
        
    def generate_summary_report(self) -> None:
        """Generate a summary report of the validation."""
        print("\n" + "="*60)
        print(" CHART:  OAUTH STAGING VALIDATION SUMMARY")
        print("="*60)
        
        if self.issues_found:
            print(f"\n FAIL:  Issues Found ({len(self.issues_found)}):")
            for issue in self.issues_found:
                print(f"  {issue}")
        else:
            print("\n PASS:  No issues found!")
            
        if self.fixes_applied:
            print(f"\n PASS:  Fixes Applied ({len(self.fixes_applied)}):")
            for fix in self.fixes_applied:
                print(f"  {fix}")
                
        print("\n" + "="*60)
        
        # Create report file
        report_path = project_root / "docs" / "reports" / "OAUTH_STAGING_VALIDATION.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write("# OAuth Staging Validation Report\n\n")
            f.write(f"**Date**: {os.popen('date').read().strip()}\n\n")
            
            f.write("## Issues Found\n\n")
            if self.issues_found:
                for issue in self.issues_found:
                    f.write(f"- {issue}\n")
            else:
                f.write("No issues found.\n")
                
            f.write("\n## Fixes Applied\n\n")
            if self.fixes_applied:
                for fix in self.fixes_applied:
                    f.write(f"- {fix}\n")
            else:
                f.write("No fixes applied.\n")
                
            f.write("\n## Next Steps\n\n")
            f.write("1. Ensure OAuth credentials are properly configured\n")
            f.write("2. Add redirect URIs to Google Console\n")
            f.write("3. Sync secrets to GCP Secret Manager\n")
            f.write("4. Deploy services with updated configuration\n")
            
        print(f"\n[U+1F4C4] Report saved to: {report_path}")
        

async def main():
    """Main validation flow."""
    print("[U+1F680] Starting OAuth Staging Validation\n")
    
    validator = OAuthStagingValidator()
    
    # Run validation steps
    steps = [
        ("Local .env.staging", validator.check_local_env_file()),
        ("GCP Secrets", validator.check_gcp_secrets()),
        ("Redirect URIs", validator.validate_redirect_uris()),
    ]
    
    # If local env is configured, sync to GCP
    if steps[0][1]:  # Local env check passed
        if not steps[1][1]:  # GCP secrets need updating
            print("\n CYCLE:  Syncing credentials to GCP...")
            if validator.sync_secrets_to_gcp():
                print(" PASS:  Secrets synced to GCP successfully")
            else:
                print(" FAIL:  Failed to sync secrets to GCP")
    
    # Test OAuth flow
    await validator.test_oauth_flow()
    
    # Generate summary
    validator.generate_summary_report()
    
    # Return success if no critical issues
    return len([s for s in validator.issues_found if "[ERROR]" in s]) == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n WARNING: [U+FE0F]  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n FAIL:  Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)