#!/usr/bin/env python3
"""
Update placeholder secrets in Google Secret Manager for staging deployment.

This script helps you update the placeholder secrets that are blocking deployment.
You need to provide your actual API keys for the services.

Usage:
    python scripts/update_placeholder_secrets.py
"""

import subprocess
import sys
import getpass
from typing import Optional


def update_secret(secret_name: str, value: str, project: str = "netra-staging") -> bool:
    """Update a secret in Google Secret Manager."""
    try:
        # Create new version with the actual value
        process = subprocess.Popen(
            ["gcloud", "secrets", "versions", "add", secret_name, "--data-file=-", f"--project={project}"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=value)
        
        if process.returncode == 0:
            print(f" PASS:  Successfully updated {secret_name}")
            return True
        else:
            print(f" FAIL:  Failed to update {secret_name}: {stderr}")
            return False
    except Exception as e:
        print(f" FAIL:  Error updating {secret_name}: {e}")
        return False


def get_current_value(secret_name: str, project: str = "netra-staging") -> Optional[str]:
    """Get current value of a secret to check if it's a placeholder."""
    try:
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest", f"--secret={secret_name}", f"--project={project}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except:
        return None


def main():
    print("[U+1F510] Netra Staging Secrets Updater")
    print("=" * 50)
    print("\nThis script will help you update the placeholder secrets that are blocking deployment.")
    print("You'll need to provide your actual API keys.\n")
    
    secrets_to_update = {
        "anthropic-api-key-staging": {
            "description": "Anthropic API Key (starts with 'sk-ant-')",
            "placeholder": "REPLACE_WITH_REAL_ANTHROPIC_KEY"
        },
        "gemini-api-key-staging": {
            "description": "Google Gemini API Key",
            "placeholder": "REPLACE_WITH_REAL_GEMINI_KEY"
        },
        "redis-url-staging": {
            "description": "Redis URL (format: redis://user:password@host:port/db)",
            "placeholder": "redis://default:REPLACE_WITH_REAL_PASSWORD@localhost:6379/0",
            "default": "redis://default:staging-redis-password@redis:6379/0"
        }
    }
    
    updated_count = 0
    
    for secret_name, config in secrets_to_update.items():
        print(f"\n[U+1F4DD] {secret_name}")
        print(f"   {config['description']}")
        
        # Check current value
        current_value = get_current_value(secret_name)
        if current_value and config["placeholder"] not in current_value and "REPLACE" not in current_value:
            print(f"    PASS:  Already configured (not a placeholder)")
            continue
        
        # Special handling for redis-url
        if secret_name == "redis-url-staging":
            use_default = input("   Use default internal Redis URL? (y/n): ").lower().strip()
            if use_default == 'y':
                value = config["default"]
            else:
                value = input(f"   Enter {config['description']}: ").strip()
        else:
            # Use getpass for API keys to hide them from console
            value = getpass.getpass(f"   Enter {config['description']}: ").strip()
        
        if not value:
            print("    WARNING: [U+FE0F]  Skipped (no value provided)")
            continue
        
        if update_secret(secret_name, value):
            updated_count += 1
    
    print(f"\n{'='*50}")
    print(f" PASS:  Updated {updated_count} secrets")
    
    if updated_count > 0:
        print("\n[U+1F680] You can now deploy with:")
        print("   python scripts/deploy_to_gcp.py --project netra-staging --build-local")
    else:
        print("\n WARNING: [U+FE0F]  No secrets were updated. Make sure to update them before deployment.")


if __name__ == "__main__":
    main()